/**
 * addressProbe — does this very instance answer at the address an administrator typed? (accounts lot A6b)
 *
 * `LinkShare` lets the administrator edit the address an invitation or reset link starts with (decision D-A3). When
 * the address differs from the prefill, the browser checks it: it asks its own instance for a nonce
 * (`POST /users/address-probe`, as an administrator) and sends that nonce, with no credentials, to
 * `GET <address>/api/v1/auth/address-probe?nonce=…`. Only an instance holding the same instance key answers
 * `{match: true}` (backend `services/accounts/address_probe.py`). The verdict is advice — the link can be copied
 * whatever it says — so the module never throws, and whatever it cannot read is `unverifiable`.
 *
 * The contract (plan A6b.1):
 *   - `normalizeBase(input)`: the input trimmed; an absolute `http:`/`https:` URL with no query, no fragment and no
 *     credentials, its trailing slashes removed and its path prefix kept; `null` for anything else.
 *   - `probeUrl(base, nonce)`: `${base}/api/v1/auth/address-probe?nonce=${encodeURIComponent(nonce)}`.
 *   - `checkAddress(base, {issueNonce, fetchImpl?, timeoutMs?})`: one nonce, then one
 *     `fetchImpl(probeUrl(base, nonce), init)`. `res.ok` with `{match: true}` is `match`, with `{match: false}`
 *     `mismatch`; anything else is `unverifiable` — the nonce refused, the request failed (network, CORS, mixed content,
 *     a local-network permission denied), a status other than 2xx, a body that is not JSON or whose `match` is not a
 *     boolean, the deadline passed (`timeoutMs`, 8000 by default: the request is then aborted through its signal).
 *     Without `fetchImpl`, the `fetch` globalThis holds at the time of the call.
 *
 * Why `init` is compared key by key. The probe crosses origins on purpose, and the backend's `CORSMiddleware` refuses
 * every preflight (`400 Disallowed CORS origin`): the request must stay a CORS simple request — a GET with no header
 * of its own, no body, no mode — sending no cookie, reading no cache and naming no referrer. One header more (a
 * `Content-Type`, an `X-Requested-With`) and every real probe reads `unverifiable`, while a case that only checks
 * `method` stays green.
 *
 * Also pinned, beyond the letter of the contract: the transport is called as a plain function (APR-24). The native
 * `fetch` called as `opts.fetchImpl(…)` gets the options object as `this`, and a browser answers "Illegal invocation"
 * — which `checkAddress` would swallow into `unverifiable`, for every probe, while Node's fetch never complains.
 *
 * The deadline runs on fake timers, so it must be set with the global `setTimeout` (an `AbortController` aborted by a
 * timer). `AbortSignal.timeout()` runs on a timer of Node's own that no fake clock reaches: the deadline cases say so
 * in their message instead of hanging.
 *
 * No case reaches the network: the global `fetch` is a failing stub in every case, and already while the module is
 * imported (`vi.hoisted`), so a module that kept the `fetch` it found at import holds a stub, not the real one.
 *
 * Written red-first, before `addressProbe.ts` exists: every case fails on the import until it does.
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';

/** The fetch globalThis holds while addressProbe.ts is imported: a stub that fails. */
const importTimeFetch = vi.hoisted(() => {
    const stub = vi.fn(async (): Promise<Response> => {
        throw new TypeError('the fetch globalThis held while addressProbe.ts was imported');
    });
    vi.stubGlobal('fetch', stub);
    return stub;
});

import {checkAddress, normalizeBase, probeUrl, type ProbeVerdict} from './addressProbe';

/** A nonce as the backend mints them: 75 base64url characters, `-` and `_` included, nothing to escape. */
const NONCE = 'q3Xk2Lw8-Np0Rt5Vy7Ab9Cd1Ef3_Gh5Ij7Kl9Mn1Op3Qr5St7Uv9Wx1Yz3AbCdEfGhIjKlMn-_p';
/** A nonce no backend mints, made to break out of a query that is not encoded: `&` opens a parameter, `#` a fragment. */
const HOSTILE_NONCE = 'abc&nonce=forged#tail+/?%';
/** `encodeURIComponent(HOSTILE_NONCE)`, written out. */
const HOSTILE_ENCODED = 'abc%26nonce%3Dforged%23tail%2B%2F%3F%25';
/** The address being checked: another origin, under the path prefix of a reverse proxy. */
const BASE = 'https://folio.example/librefolio';
/** Where the probe goes for BASE and NONCE, written out rather than computed with probeUrl. */
const PROBE_URL = `https://folio.example/librefolio/api/v1/auth/address-probe?nonce=${NONCE}`;
/** The keys of the request's init, sorted: a CORS simple request and its signal. */
const INIT_KEYS = ['cache', 'credentials', 'method', 'referrerPolicy', 'signal'];

/** A response carrying `body` as JSON. */
function json(body: unknown, status = 200): Response {
    return new Response(JSON.stringify(body), {status, headers: {'content-type': 'application/json'}});
}

/** A fetch answering `respond()`: a fresh Response each call, a body is read only once. */
function answering(respond: () => Response): Mock<typeof fetch> {
    return vi.fn<typeof fetch>(async () => respond());
}

/** A fetch that never answers, and rejects as a browser's does once its signal aborts. */
function hanging(): Mock<typeof fetch> {
    return vi.fn<typeof fetch>(
        (_input: RequestInfo | URL, init?: RequestInit) =>
            new Promise<Response>((_resolve, reject) => {
                const signal = init?.signal;
                const abort = () => reject(signal?.reason ?? new DOMException('The operation was aborted.', 'AbortError'));
                if (signal?.aborted) {
                    abort();
                } else {
                    signal?.addEventListener('abort', abort, {once: true});
                }
            }),
    );
}

/** A nonce issuer answering `nonce`. */
function issuing(nonce: string = NONCE): Mock<() => Promise<string>> {
    return vi.fn(async () => nonce);
}

/** The init of the one request `fetchImpl` received. */
function initOf(fetchImpl: Mock<typeof fetch>): RequestInit {
    expect(fetchImpl, 'premise: exactly one probe was sent').toHaveBeenCalledTimes(1);
    return fetchImpl.mock.calls[0][1] ?? {};
}

/** What `this` was, in a few words: globalThis is too large to print. */
function describeThis(self: unknown): string {
    if (self === globalThis) return 'globalThis';
    if (self === null || typeof self !== 'object') return String(self);
    return `an object with the keys ${Object.keys(self).join(', ')}`;
}

/** The global fetch of the case: a failing stub, so a probe sent through it is seen and never leaves the process. */
let globalFetch: Mock<typeof fetch>;

beforeEach(() => {
    importTimeFetch.mockClear();
    globalFetch = vi.fn<typeof fetch>(async () => {
        throw new TypeError('the global fetch is not the transport of this case');
    });
    vi.stubGlobal('fetch', globalFetch);
});

afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
});

describe('normalizeBase — the address typed, as a base the link and the probe can start with, or null', () => {
    it.each(['https://folio.example', 'http://127.0.0.1:6182', 'https://folio.example:8443', 'http://[::1]:6182', 'http://localhost:5173'])('APR-01: %s is an http(s) address and is kept as it is, port and IPv6 literal included', (input) => {
        expect(normalizeBase(input)).toBe(input);
    });

    it.each(['https://x.example/librefolio', 'https://x.example/apps/librefolio', 'http://[::1]:6182/librefolio'])('APR-02: the path prefix of %s is kept: a reverse proxy may serve the instance under it', (input) => {
        expect(normalizeBase(input)).toBe(input);
    });

    it.each([
        ['https://folio.example/', 'https://folio.example'],
        ['https://x.example/librefolio/', 'https://x.example/librefolio'],
        ['https://x.example/apps/librefolio//', 'https://x.example/apps/librefolio'],
        ['http://[::1]:6182///', 'http://[::1]:6182'],
    ])('APR-03: %s loses its trailing slashes: %s', (input, expected) => {
        expect(normalizeBase(input), 'the link and the probe append a path that starts with /').toBe(expected);
    });

    it.each([
        ['  https://x.example/librefolio/  ', 'https://x.example/librefolio'],
        ['\thttps://folio.example\n', 'https://folio.example'],
    ])('APR-04: %j is trimmed first: %s', (input, expected) => {
        expect(normalizeBase(input), 'an address pasted with the blanks around it').toBe(expected);
    });

    it.each([
        ['', 'empty'],
        ['   ', 'blank'],
        ['folio.example', 'a host without a scheme: a relative reference'],
        ['localhost:6182', 'a host and a port without a scheme: read as the scheme localhost:'],
        ['/librefolio', 'a path alone'],
        ['//folio.example', 'a scheme-relative reference'],
        ['ftp://folio.example', 'ftp:'],
        ['javascript:alert(1)', 'javascript:'],
        ['file:///etc/passwd', 'file:'],
    ])('APR-05: %j is null — not an absolute http(s) URL (%s)', (input) => {
        expect(normalizeBase(input)).toBeNull();
    });

    it.each([
        ['https://folio.example/?next=/', 'a query'],
        ['https://x.example/librefolio?lang=it', 'a query after a path prefix'],
        ['https://folio.example/#token=abc', 'a fragment'],
        ['https://x.example/librefolio#top', 'a fragment after a path prefix'],
    ])('APR-06: %j is null — %s: the link and the probe append their own path to the base', (input) => {
        expect(normalizeBase(input)).toBeNull();
    });

    it.each([
        ['https://user:pass@folio.example', 'a user and a password'],
        ['https://admin@x.example/librefolio', 'a user alone'],
    ])('APR-07: %j is null — credentials in the address (%s)', (input) => {
        expect(normalizeBase(input), 'credentials would travel in every link copied, and a browser refuses to fetch a URL that carries them').toBeNull();
    });

    it.each([
        ['not a url', 'words'],
        ['http://', 'a scheme and no host'],
        ['https://', 'a scheme and no host'],
        ['http://exa mple.com', 'a space in the host'],
        ['https://[::1', 'an IPv6 literal left open'],
        ['https://folio.example:99999', 'a port out of range'],
    ])('APR-08: %j is null — not a URL at all (%s)', (input) => {
        expect(normalizeBase(input)).toBeNull();
    });
});

describe('probeUrl — where the probe goes', () => {
    it.each([
        ['https://folio.example', `https://folio.example/api/v1/auth/address-probe?nonce=${NONCE}`],
        [BASE, PROBE_URL],
        ['http://[::1]:6182', `http://[::1]:6182/api/v1/auth/address-probe?nonce=${NONCE}`],
    ])('APR-09: under %s, the probe route of the backend, the nonce as it is (base64url needs no escape)', (base, expected) => {
        expect(probeUrl(base, NONCE)).toBe(expected);
    });

    it('APR-10: the nonce is URL-encoded: its & and # can neither add a parameter nor cut the query short', () => {
        expect(encodeURIComponent(HOSTILE_NONCE), 'premise: the literal below is what encodeURIComponent writes').toBe(HOSTILE_ENCODED);

        const url = probeUrl('http://127.0.0.1:6182', HOSTILE_NONCE);

        expect(url).toBe(`http://127.0.0.1:6182/api/v1/auth/address-probe?nonce=${HOSTILE_ENCODED}`);
        const parsed = new URL(url);
        expect(parsed.pathname, 'the probe route').toBe('/api/v1/auth/address-probe');
        expect([...parsed.searchParams.keys()], 'one parameter: left unencoded, the & would have opened a second nonce').toEqual(['nonce']);
        expect(parsed.searchParams.get('nonce'), 'which decodes back to the nonce issued').toBe(HOSTILE_NONCE);
        expect(parsed.hash, 'no fragment: left unencoded, the # would have kept the end of the nonce in the browser').toBe('');
    });
});

describe('checkAddress — one nonce, one simple request, one verdict, never a throw', () => {
    it.each([
        ['a nonce as the backend mints them', NONCE, PROBE_URL],
        ['a hostile nonce', HOSTILE_NONCE, `https://folio.example/librefolio/api/v1/auth/address-probe?nonce=${HOSTILE_ENCODED}`],
    ])('APR-11: asks for one nonce, then sends one probe, to probeUrl(base, nonce) — %s', async (_label, nonce, url) => {
        const issueNonce = issuing(nonce);
        const fetchImpl = answering(() => json({match: true}));

        await checkAddress(BASE, {issueNonce, fetchImpl});

        expect(issueNonce, 'one nonce per check').toHaveBeenCalledTimes(1);
        expect(fetchImpl, 'one probe per check').toHaveBeenCalledTimes(1);
        expect(fetchImpl.mock.calls[0][0], 'the probe goes to the address being checked, the nonce encoded').toBe(url);
        expect(globalFetch, 'the fetch it is given replaces the global one').not.toHaveBeenCalled();
    });

    it('APR-12: sends a CORS simple request — init is exactly {method: GET, credentials: omit, cache: no-store, referrerPolicy: no-referrer, signal}', async () => {
        const fetchImpl = answering(() => json({match: true}));

        await checkAddress(BASE, {issueNonce: issuing(), fetchImpl});

        const init = initOf(fetchImpl);
        const forbidden: Record<string, string> = {
            headers: 'a header of its own makes the browser send a preflight, which the backend’s CORSMiddleware refuses',
            body: 'a GET carries no body, and fetch refuses one',
            mode: 'the default mode, cors, is the one whose answer can be read: no-cors makes it opaque, same-origin refuses another origin',
        };
        for (const [key, why] of Object.entries(forbidden)) {
            expect(init, `no ${key}: ${why}`).not.toHaveProperty(key);
        }
        expect(Object.keys(init).sort(), 'init holds these five keys, and nothing else').toEqual(INIT_KEYS);
        expect(init.method, 'a GET').toBe('GET');
        expect(init.credentials, 'no cookie of this instance travels to the address being checked').toBe('omit');
        expect(init.cache, 'an answer from a cache is not an answer about this nonce').toBe('no-store');
        expect(init.referrerPolicy, 'the address being checked is not told which page asked').toBe('no-referrer');
        expect(init.signal, 'a signal, through which the deadline aborts the request').toBeInstanceOf(AbortSignal);
    });

    it.each<[string, boolean, ProbeVerdict]>([
        ['APR-13', true, 'match'],
        ['APR-14', false, 'mismatch'],
    ])('%s: a 200 answering {match: %s} is %s', async (_id, match, verdict) => {
        const fetchImpl = answering(() => json({match}));

        await expect(checkAddress(BASE, {issueNonce: issuing(), fetchImpl})).resolves.toBe(verdict);
        expect(fetchImpl, 'one probe').toHaveBeenCalledTimes(1);
    });

    it.each<[string, unknown]>([
        ['match is the string "true"', {match: 'true'}],
        ['match is missing', {}],
        ['match is 1', {match: 1}],
        ['match is null', {match: null}],
        ['the body is null', null],
        ['the body is a bare true', true],
    ])('APR-15: a 200 where %s is unverifiable: only a boolean match is an answer', async (_label, body) => {
        await expect(checkAddress(BASE, {issueNonce: issuing(), fetchImpl: answering(() => json(body))})).resolves.toBe('unverifiable');
    });

    it.each([401, 404, 500])('APR-16: a %i is unverifiable, even with a body that says match', async (status) => {
        const fetchImpl = answering(() => json({match: true}, status));

        await expect(checkAddress(BASE, {issueNonce: issuing(), fetchImpl}), 'only an ok answer is read').resolves.toBe('unverifiable');
        expect(fetchImpl, 'one probe: a failed one is not retried').toHaveBeenCalledTimes(1);
    });

    it.each<[string, () => Response]>([
        ['an HTML page (another server, or a single-page app answering every path)', () => new Response('<!doctype html><html><body>LibreFolio</body></html>', {status: 200, headers: {'content-type': 'text/html'}})],
        ['an empty body', () => new Response('', {status: 200, headers: {'content-type': 'application/json'}})],
    ])('APR-17: a 200 whose body is not JSON — %s — is unverifiable', async (_label, respond) => {
        await expect(checkAddress(BASE, {issueNonce: issuing(), fetchImpl: answering(respond)})).resolves.toBe('unverifiable');
    });

    it('APR-18: a request that fails — network, CORS, mixed content, a local-network permission denied — is unverifiable', async () => {
        const fetchImpl = vi.fn<typeof fetch>(async () => {
            throw new TypeError('Failed to fetch');
        });

        await expect(checkAddress(BASE, {issueNonce: issuing(), fetchImpl}), 'a browser reports all of these with the same TypeError').resolves.toBe('unverifiable');
        expect(fetchImpl, 'one probe: a failed one is not retried').toHaveBeenCalledTimes(1);
    });

    it('APR-19: when the nonce cannot be had, unverifiable — and no probe is sent', async () => {
        const issueNonce = vi.fn(async (): Promise<string> => {
            throw new Error('POST /users/address-probe answered 500');
        });
        const fetchImpl = answering(() => json({match: true}));

        await expect(checkAddress(BASE, {issueNonce, fetchImpl})).resolves.toBe('unverifiable');
        expect(issueNonce, 'premise: the nonce was asked for').toHaveBeenCalledTimes(1);
        expect(fetchImpl, 'no nonce, no probe').not.toHaveBeenCalled();
        expect(globalFetch, 'not through the global fetch either').not.toHaveBeenCalled();
    });

    it.each(['issueNonce', 'fetchImpl'] as const)('APR-20: never throws, even when %s throws instead of returning a rejected promise', async (thrower) => {
        const issueNonce =
            thrower === 'issueNonce'
                ? vi.fn((): Promise<string> => {
                      throw new Error('thrown, not rejected');
                  })
                : issuing();
        const fetchImpl =
            thrower === 'fetchImpl'
                ? vi.fn<typeof fetch>(() => {
                      throw new TypeError('thrown, not rejected');
                  })
                : answering(() => json({match: true}));

        await expect(checkAddress(BASE, {issueNonce, fetchImpl})).resolves.toBe('unverifiable');
    });

    it.each<[string, string, number, number | undefined]>([
        ['APR-21', 'timeoutMs 3000', 3_000, 3_000],
        ['APR-22', 'no timeoutMs (the default)', 8_000, undefined],
    ])('%s: with %s, a probe still unanswered at %i ms is aborted through its signal, and the verdict is unverifiable', async (_id, _given, deadline, timeoutMs) => {
        vi.useFakeTimers();
        const fetchImpl = hanging();
        let settled = false;
        const verdict = checkAddress(BASE, {issueNonce: issuing(), fetchImpl, ...(timeoutMs === undefined ? {} : {timeoutMs})}).finally(() => {
            settled = true;
        });

        await vi.advanceTimersByTimeAsync(deadline - 1);

        const signal = initOf(fetchImpl).signal;
        expect(signal, 'premise: the request carries a signal').toBeInstanceOf(AbortSignal);
        expect(signal?.aborted, `at ${deadline - 1} ms the address may still answer: the request is not aborted yet`).toBe(false);
        expect(settled, `no verdict before ${deadline} ms`).toBe(false);

        await vi.advanceTimersByTimeAsync(1);

        expect(signal?.aborted, `at ${deadline} ms the request is aborted through its signal, by a timer on the global setTimeout: AbortSignal.timeout() runs on a timer of Node's own, which no fake clock reaches`).toBe(true);
        await expect(verdict).resolves.toBe('unverifiable');
    });

    it('APR-23: without fetchImpl, the probe goes through the fetch globalThis holds at the time of the call', async () => {
        const first = answering(() => json({match: true}));
        vi.stubGlobal('fetch', first);

        const verdict = await checkAddress(BASE, {issueNonce: issuing()});

        expect(importTimeFetch, 'the module kept the fetch globalThis held when it was imported').not.toHaveBeenCalled();
        expect(first, 'the fetch stubbed after the import carries the probe').toHaveBeenCalledTimes(1);
        expect(first.mock.calls[0][0]).toBe(PROBE_URL);
        expect(verdict).toBe('match');

        const second = answering(() => json({match: false}));
        vi.stubGlobal('fetch', second);

        await expect(checkAddress(BASE, {issueNonce: issuing()})).resolves.toBe('mismatch');
        expect(second, 'a fetch stubbed later carries the next probe: none is kept from a previous call').toHaveBeenCalledTimes(1);
        expect(first, 'the previous fetch is not called again').toHaveBeenCalledTimes(1);
    });

    it.each(['the global fetch', 'the fetchImpl it is given'] as const)('APR-24: calls %s as a plain function — a browser refuses fetch called as a method of another object', async (which) => {
        const transport = answering(() => json({match: true}));
        if (which === 'the global fetch') {
            vi.stubGlobal('fetch', transport);
        }

        const verdict = await checkAddress(BASE, which === 'the global fetch' ? {issueNonce: issuing()} : {issueNonce: issuing(), fetchImpl: transport});

        expect(transport, 'premise: the probe went through it').toHaveBeenCalledTimes(1);
        const self: unknown = transport.mock.contexts[0];
        expect(self === undefined || self === null || self === globalThis, `fetch was called with this = ${describeThis(self)}: called as opts.fetchImpl(…) the native fetch throws "Illegal invocation" in Chrome, and every real probe would read unverifiable`).toBe(true);
        expect(verdict).toBe('match');
    });
});
