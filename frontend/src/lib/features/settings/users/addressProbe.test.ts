/**
 * addressProbe — does this very instance answer at the address an administrator typed? (accounts lot A6b; H-55 v2: by image)
 *
 * `LinkShare` lets the administrator edit the address an invitation or reset link starts with (decision D-A3). When
 * the address differs from the prefill, the browser checks it: it asks its own instance for a nonce
 * (`POST /users/address-probe`, as an administrator) and loads, from `<address>`, the image
 * `GET <address>/api/v1/auth/address-probe.png?nonce=…`. Only an instance holding the same instance key draws it 1×1; any
 * other draws a 2×1 one (backend `api/v1/address_probe_image.py`, `services/accounts/address_probe.py`). The verdict is
 * advice — the link can be copied whatever it says — so the module never throws, and whatever it cannot read is
 * `unverifiable`.
 *
 * Why an image and no longer a `fetch`. The enforced Content-Security-Policy (H-55 v2) has a `connect-src` of `'self'` and
 * a few named origins: a `fetch` to the address an administrator typed is blocked, whatever that address is. An image is
 * governed by `img-src`, which the policy does not enforce, and its natural size is readable across origins with no CORS
 * (an `Image` with no `crossOrigin`). The size is the answer: the same status and type either way.
 *
 * The contract (plan A6b.1, then H-55 v2):
 *   - `normalizeBase(input)`: unchanged — the input trimmed; an absolute `http:`/`https:` URL with no query, no fragment
 *     and no credentials, its trailing slashes removed and its path prefix kept; `null` for anything else.
 *   - `PROBE_IMAGE_PATH = '/api/v1/auth/address-probe.png'`; `probeImageUrl(base, nonce)` =
 *     `${base}${PROBE_IMAGE_PATH}?nonce=${encodeURIComponent(nonce)}`. `probeUrl` and `PROBE_PATH`, the JSON probe's,
 *     are gone from the module.
 *   - `checkAddress(base, {issueNonce, loadImage?, timeoutMs?})`: one nonce, then one
 *     `loadImage(probeImageUrl(base, nonce), signal)`, a promise of `{naturalWidth, naturalHeight}`. 1×1 is `match`, 2×1
 *     `mismatch`; any other size, a load that rejects (`onerror`), a nonce that cannot be had, the deadline passed
 *     (`timeoutMs`, 8000 by default: the signal is then aborted) is `unverifiable`. Never throws.
 *   - The default `loadImage` (no `loadImage` given) builds an `Image` — `referrerPolicy = 'no-referrer'`, no
 *     `crossOrigin` —, sets its handlers before its `src`, resolves on `load` with the natural size, rejects on `error`,
 *     and on abort rejects too and clears `src` (so the browser stops loading it).
 *
 * The deadline runs on fake timers, so it must be set with the global `setTimeout` (an `AbortController` aborted by a
 * timer). `AbortSignal.timeout()` runs on a timer of Node's own that no fake clock reaches: the deadline cases say so in
 * their message instead of hanging.
 *
 * No case reaches the network: the global `fetch` is a failing stub in every case — and a fetch is not what the probe
 * sends any more, which the cases assert —, and `Image` is a fake class of this file or absent (the node environment has
 * none).
 *
 * Red today: `addressProbe.ts` still probes with `fetch` and exports `probeUrl` and `PROBE_PATH`: `probeImageUrl` and
 * `PROBE_IMAGE_PATH` do not exist, and `checkAddress` ignores `loadImage`.
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import * as addressProbe from './addressProbe';
import {checkAddress, normalizeBase, probeImageUrl, PROBE_IMAGE_PATH, type ProbeVerdict} from './addressProbe';

/** A nonce as the backend mints them: 75 base64url characters, `-` and `_` included, nothing to escape. */
const NONCE = 'q3Xk2Lw8-Np0Rt5Vy7Ab9Cd1Ef3_Gh5Ij7Kl9Mn1Op3Qr5St7Uv9Wx1Yz3AbCdEfGhIjKlMn-_p';
/** A nonce no backend mints, made to break out of a query that is not encoded: `&` opens a parameter, `#` a fragment. */
const HOSTILE_NONCE = 'abc&nonce=forged#tail+/?%';
/** `encodeURIComponent(HOSTILE_NONCE)`, written out. */
const HOSTILE_ENCODED = 'abc%26nonce%3Dforged%23tail%2B%2F%3F%25';
/** The address being checked: another origin, under the path prefix of a reverse proxy. */
const BASE = 'https://folio.example/librefolio';
/** Where the probe goes for BASE and NONCE, written out rather than computed with probeImageUrl. */
const PROBE_URL = `https://folio.example/librefolio/api/v1/auth/address-probe.png?nonce=${NONCE}`;

/** What a loaded image tells: its natural size, the only thing of it that is read. */
interface LoadedImage {
    naturalWidth: number;
    naturalHeight: number;
}
type LoadImage = (url: string, signal: AbortSignal) => Promise<LoadedImage>;

/** A loader answering an image of `width`×`height`. */
function drawing(width: number, height: number): Mock<LoadImage> {
    return vi.fn<LoadImage>(async () => ({naturalWidth: width, naturalHeight: height}));
}

/** A loader that never answers, and rejects as the default one does once its signal aborts. */
function hanging(): Mock<LoadImage> {
    return vi.fn<LoadImage>(
        (_url, signal) =>
            new Promise<LoadedImage>((_resolve, reject) => {
                const abort = () => reject(signal.reason ?? new DOMException('The operation was aborted.', 'AbortError'));
                if (signal.aborted) {
                    abort();
                } else {
                    signal.addEventListener('abort', abort, {once: true});
                }
            }),
    );
}

/** A nonce issuer answering `nonce`. */
function issuing(nonce: string = NONCE): Mock<() => Promise<string>> {
    return vi.fn(async () => nonce);
}

/** The global fetch of the case: a failing stub, so a probe sent through it is seen and never leaves the process. */
let globalFetch: Mock<typeof fetch>;

beforeEach(() => {
    globalFetch = vi.fn<typeof fetch>(async () => {
        throw new TypeError('the global fetch is not the transport of this case: the probe is an image');
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

describe('probeImageUrl — where the probe goes', () => {
    it('APR-09: the image route of the backend, under the base, with the nonce — and the JSON probe’s helpers are gone', () => {
        expect(PROBE_IMAGE_PATH, 'the route of the probe image').toBe('/api/v1/auth/address-probe.png');
        expect(
            Object.keys(addressProbe).filter((name) => name === 'probeUrl' || name === 'PROBE_PATH'),
            'the JSON probe’s URL helper and path leave the module with its fetch',
        ).toEqual([]);
        for (const [base, expected] of [
            ['https://folio.example', `https://folio.example/api/v1/auth/address-probe.png?nonce=${NONCE}`],
            [BASE, PROBE_URL],
            ['http://[::1]:6182', `http://[::1]:6182/api/v1/auth/address-probe.png?nonce=${NONCE}`],
        ] as const) {
            expect(probeImageUrl(base, NONCE), `under ${base}, the nonce as it is (base64url needs no escape)`).toBe(expected);
        }
    });

    it('APR-10: the nonce is URL-encoded: its & and # can neither add a parameter nor cut the query short', () => {
        expect(encodeURIComponent(HOSTILE_NONCE), 'premise: the literal below is what encodeURIComponent writes').toBe(HOSTILE_ENCODED);

        const url = probeImageUrl('http://127.0.0.1:6182', HOSTILE_NONCE);

        expect(url).toBe(`http://127.0.0.1:6182/api/v1/auth/address-probe.png?nonce=${HOSTILE_ENCODED}`);
        const parsed = new URL(url);
        expect(parsed.pathname, 'the probe image route').toBe('/api/v1/auth/address-probe.png');
        expect([...parsed.searchParams.keys()], 'one parameter: left unencoded, the & would have opened a second nonce').toEqual(['nonce']);
        expect(parsed.searchParams.get('nonce'), 'which decodes back to the nonce issued').toBe(HOSTILE_NONCE);
        expect(parsed.hash, 'no fragment: left unencoded, the # would have kept the end of the nonce in the browser').toBe('');
    });
});

describe('checkAddress — one nonce, one image, one verdict by its size, never a throw', () => {
    it.each([
        ['a nonce as the backend mints them', NONCE, PROBE_URL],
        ['a hostile nonce', HOSTILE_NONCE, `https://folio.example/librefolio/api/v1/auth/address-probe.png?nonce=${HOSTILE_ENCODED}`],
    ])('APR-11: asks for one nonce, then loads one image, probeImageUrl(base, nonce) with a signal — %s', async (_label, nonce, url) => {
        const issueNonce = issuing(nonce);
        const loadImage = drawing(1, 1);

        await checkAddress(BASE, {issueNonce, loadImage});

        expect(issueNonce, 'one nonce per check').toHaveBeenCalledTimes(1);
        expect(loadImage, 'one image per check').toHaveBeenCalledTimes(1);
        expect(loadImage.mock.calls[0][0], 'the image of the address being checked, the nonce encoded').toBe(url);
        expect(loadImage.mock.calls[0][1], 'a signal, through which the deadline aborts the load').toBeInstanceOf(AbortSignal);
        expect(globalFetch, 'the probe is no fetch: a connect-src would block it').not.toHaveBeenCalled();
    });

    it.each<[string, number, number, ProbeVerdict]>([
        ['APR-12', 1, 1, 'match'],
        ['APR-13', 2, 1, 'mismatch'],
    ])('%s: an image of %i×%i is %s', async (_id, width, height, verdict) => {
        const loadImage = drawing(width, height);

        await expect(checkAddress(BASE, {issueNonce: issuing(), loadImage})).resolves.toBe(verdict);
        expect(loadImage, 'one load').toHaveBeenCalledTimes(1);
    });

    it.each<[number, number]>([
        [0, 0],
        [1, 0],
        [0, 1],
        [1, 2],
        [2, 2],
        [3, 1],
        [2, 100],
        [300, 150],
    ])('APR-14: an image of %i×%i is unverifiable: only 1×1 and 2×1 are answers of the probe', async (width, height) => {
        // Another server, or the single-page app of this one answering every path with a picture: not this probe's word.
        await expect(checkAddress(BASE, {issueNonce: issuing(), loadImage: drawing(width, height)})).resolves.toBe('unverifiable');
    });

    it.each<[string, unknown]>([
        ['nothing', undefined],
        ['null', null],
        ['a size that is not numbers', {naturalWidth: '1', naturalHeight: '1'}],
        ['a size with NaN', {naturalWidth: Number.NaN, naturalHeight: 1}],
    ])('APR-15: a loader that resolves with %s is unverifiable, not an exception', async (_label, loaded) => {
        const loadImage = vi.fn(async () => loaded) as unknown as Mock<LoadImage>;

        await expect(checkAddress(BASE, {issueNonce: issuing(), loadImage})).resolves.toBe('unverifiable');
    });

    it('APR-16: an image that fails to load — network, mixed content, a local-network permission denied, not an image — is unverifiable, and not retried', async () => {
        const loadImage = vi.fn<LoadImage>(async () => {
            throw new Event('error');
        });

        await expect(checkAddress(BASE, {issueNonce: issuing(), loadImage}), 'a browser reports all of these with the same error event').resolves.toBe('unverifiable');
        expect(loadImage, 'one load: a failed one is not retried').toHaveBeenCalledTimes(1);
    });

    it('APR-17: when the nonce cannot be had, unverifiable — and no image is loaded', async () => {
        const issueNonce = vi.fn(async (): Promise<string> => {
            throw new Error('POST /users/address-probe answered 500');
        });
        const loadImage = drawing(1, 1);

        await expect(checkAddress(BASE, {issueNonce, loadImage})).resolves.toBe('unverifiable');
        expect(issueNonce, 'premise: the nonce was asked for').toHaveBeenCalledTimes(1);
        expect(loadImage, 'no nonce, no probe').not.toHaveBeenCalled();
        expect(globalFetch).not.toHaveBeenCalled();
    });

    it.each(['issueNonce', 'loadImage'] as const)('APR-18: never throws, even when %s throws instead of returning a rejected promise', async (thrower) => {
        const issueNonce =
            thrower === 'issueNonce'
                ? vi.fn((): Promise<string> => {
                      throw new Error('thrown, not rejected');
                  })
                : issuing();
        const loadImage =
            thrower === 'loadImage'
                ? vi.fn<LoadImage>(() => {
                      throw new TypeError('thrown, not rejected');
                  })
                : drawing(1, 1);

        await expect(checkAddress(BASE, {issueNonce, loadImage})).resolves.toBe('unverifiable');
    });

    it.each<[string, string, number, number | undefined]>([
        ['APR-19', 'timeoutMs 3000', 3_000, 3_000],
        ['APR-20', 'no timeoutMs (the default)', 8_000, undefined],
    ])('%s: with %s, an image still not loaded at %i ms has its signal aborted, and the verdict is unverifiable', async (_id, _given, deadline, timeoutMs) => {
        vi.useFakeTimers();
        const loadImage = hanging();
        let settled = false;
        const verdict = checkAddress(BASE, {issueNonce: issuing(), loadImage, ...(timeoutMs === undefined ? {} : {timeoutMs})}).finally(() => {
            settled = true;
        });

        await vi.advanceTimersByTimeAsync(deadline - 1);

        expect(loadImage, 'premise: exactly one image was asked for').toHaveBeenCalledTimes(1);
        const signal = loadImage.mock.calls[0][1];
        expect(signal, 'premise: the load carries a signal').toBeInstanceOf(AbortSignal);
        expect(signal.aborted, `at ${deadline - 1} ms the address may still answer: the load is not aborted yet`).toBe(false);
        expect(settled, `no verdict before ${deadline} ms`).toBe(false);

        await vi.advanceTimersByTimeAsync(1);

        expect(signal.aborted, `at ${deadline} ms the load is aborted through its signal, by a timer on the global setTimeout: AbortSignal.timeout() runs on a timer of Node's own, which no fake clock reaches`).toBe(true);
        await expect(verdict).resolves.toBe('unverifiable');
    });

    it('APR-21: a loader that ignores its signal and never settles still ends as unverifiable at the deadline', async () => {
        vi.useFakeTimers();
        const loadImage = vi.fn<LoadImage>(() => new Promise<LoadedImage>(() => {}));
        const verdict = checkAddress(BASE, {issueNonce: issuing(), loadImage, timeoutMs: 500});

        await vi.advanceTimersByTimeAsync(500);

        await expect(verdict, 'the deadline is the check’s own, not the loader’s good manners').resolves.toBe('unverifiable');
    });

    it('APR-22: an image that answers once the deadline has passed changes nothing: the verdict was unverifiable', async () => {
        vi.useFakeTimers();
        let resolveLate: (image: LoadedImage) => void = () => undefined;
        const loadImage = vi.fn<LoadImage>(() => new Promise<LoadedImage>((resolve) => (resolveLate = resolve)));
        const verdict = checkAddress(BASE, {issueNonce: issuing(), loadImage, timeoutMs: 500});

        await vi.advanceTimersByTimeAsync(500);
        resolveLate({naturalWidth: 1, naturalHeight: 1});

        await expect(verdict).resolves.toBe('unverifiable');
    });

    it('APR-23: an answer in time leaves no timer behind', async () => {
        vi.useFakeTimers();

        await expect(checkAddress(BASE, {issueNonce: issuing(), loadImage: drawing(1, 1)})).resolves.toBe('match');

        expect(vi.getTimerCount(), 'the deadline timer is cleared once the verdict is in').toBe(0);
    });
});

// =====================================================================================================================
/** An `Image` of this file: records what the default loader does to it, and plays the browser's part on demand. */
class FakeImage {
    static instances: FakeImage[] = [];
    /** Every assignment and listener registration, in order: `src` after the handlers is what a cached image needs. */
    log: string[] = [];
    naturalWidth = 0;
    naturalHeight = 0;
    private listeners = new Map<string, Array<() => void>>();
    private handlers = new Map<string, (() => void) | null>();
    private current = '';
    private policy = '';
    private cors: string | null | undefined = undefined;
    crossOriginWrites = 0;

    constructor() {
        FakeImage.instances.push(this);
    }
    get src(): string {
        return this.current;
    }
    set src(value: string) {
        this.log.push(`src=${value}`);
        this.current = value;
    }
    get referrerPolicy(): string {
        return this.policy;
    }
    set referrerPolicy(value: string) {
        this.log.push(`referrerPolicy=${value}`);
        this.policy = value;
    }
    get crossOrigin(): string | null | undefined {
        return this.cors;
    }
    set crossOrigin(value: string | null | undefined) {
        this.crossOriginWrites += 1;
        this.log.push(`crossOrigin=${String(value)}`);
        this.cors = value;
    }
    set onload(handler: (() => void) | null) {
        this.log.push('onload');
        this.handlers.set('load', handler);
    }
    set onerror(handler: (() => void) | null) {
        this.log.push('onerror');
        this.handlers.set('error', handler);
    }
    addEventListener(type: string, listener: () => void): void {
        this.log.push(`listen:${type}`);
        this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
    }
    removeEventListener(type: string, listener: () => void): void {
        this.listeners.set(
            type,
            (this.listeners.get(type) ?? []).filter((candidate) => candidate !== listener),
        );
    }
    /** The browser's part: the image loaded at `width`×`height`, or failed. */
    fire(type: 'load' | 'error', size?: [number, number]): void {
        if (size) {
            [this.naturalWidth, this.naturalHeight] = size;
        }
        this.handlers.get(type)?.();
        for (const listener of this.listeners.get(type) ?? []) listener();
    }
    /** The index in `log` of the first entry that starts with `prefix`; -1 without one. */
    firstIndex(prefix: string): number {
        return this.log.findIndex((entry) => entry.startsWith(prefix));
    }
}

/** The image the default loader built, once `src` is set: the case waits for the state, never the clock. */
async function theImage(): Promise<FakeImage> {
    await vi.waitFor(() =>
        expect(
            FakeImage.instances.filter((image) => image.firstIndex('src=') !== -1),
            'the default loader built an image and gave it a src',
        ).toHaveLength(1),
    );
    return FakeImage.instances[0];
}

describe('checkAddress — the default loader: an Image of the browser', () => {
    beforeEach(() => {
        FakeImage.instances = [];
        vi.stubGlobal('Image', FakeImage);
    });

    it.each<[string, number, number, ProbeVerdict]>([
        ['APR-24', 1, 1, 'match'],
        ['APR-25', 2, 1, 'mismatch'],
        ['APR-26', 5, 5, 'unverifiable'],
    ])('%s: an image that loads at %i×%i — its natural size read off the Image — is %s', async (_id, width, height, verdict) => {
        const checking = checkAddress(BASE, {issueNonce: issuing()});
        const image = await theImage();

        image.fire('load', [width, height]);

        await expect(checking).resolves.toBe(verdict);
        expect(image.src, 'the image of the address being checked').toBe(PROBE_URL);
        expect(FakeImage.instances, 'one Image per check').toHaveLength(1);
        expect(globalFetch, 'no fetch: img-src is not enforced, connect-src is').not.toHaveBeenCalled();
    });

    it('APR-27: the Image sends no referrer and asks for no CORS — the size of an image is readable across origins without it — and its handlers are set before its src', async () => {
        const checking = checkAddress(BASE, {issueNonce: issuing()});
        const image = await theImage();
        image.fire('load', [1, 1]);
        await checking;

        expect(image.referrerPolicy, 'the address being checked is not told which page asked').toBe('no-referrer');
        expect(image.crossOriginWrites, 'no crossOrigin: with one, the server would have to answer CORS headers, which the probe image does not need').toBe(0);
        expect(image.crossOrigin, 'and none is set').toBeUndefined();
        const handlers = [image.firstIndex('onload'), image.firstIndex('listen:load')].filter((index) => index !== -1);
        const errors = [image.firstIndex('onerror'), image.firstIndex('listen:error')].filter((index) => index !== -1);
        expect(handlers.length, 'a load handler is set').toBeGreaterThan(0);
        expect(errors.length, 'an error handler is set').toBeGreaterThan(0);
        expect(Math.max(Math.min(...handlers), Math.min(...errors)), 'both handlers are set before src: a cached image may fire as soon as its src is set').toBeLessThan(image.firstIndex('src='));
        expect(image.firstIndex('referrerPolicy='), 'the referrer policy is set before src: a request is made once src is').toBeLessThan(image.firstIndex('src='));
    });

    it('APR-28: an Image that errors rejects the load: unverifiable', async () => {
        const checking = checkAddress(BASE, {issueNonce: issuing()});
        const image = await theImage();

        image.fire('error');

        await expect(checking).resolves.toBe('unverifiable');
    });

    it('APR-29: at the deadline the Image is aborted — its src is cleared, so the browser stops loading it — and the verdict is unverifiable', async () => {
        vi.useFakeTimers();
        const checking = checkAddress(BASE, {issueNonce: issuing(), timeoutMs: 1_000});
        await vi.advanceTimersByTimeAsync(0);
        const image = FakeImage.instances[0];
        expect(image, 'premise: the loader built its Image').toBeDefined();
        expect(image.src, 'premise: the Image is loading the probe').toBe(PROBE_URL);

        await vi.advanceTimersByTimeAsync(1_000);

        await expect(checking).resolves.toBe('unverifiable');
        expect(image.src, 'the abort clears src').toBe('');
    });
});
