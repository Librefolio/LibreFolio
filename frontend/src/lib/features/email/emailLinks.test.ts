/**
 * emailLinks — the check, from the administrator's browser, that the base of the emailed links reaches *this* instance
 * (workstream E, lot E3p, developer decision 45).
 *
 * The contract under test, `probeEmailLinks(base, {pageProtocol, issueNonce, fetchImpl?, timeoutMs?})`:
 *   - a base the browser cannot read as an http(s) address (`normalizeBase` refuses it: empty, another scheme, no
 *     scheme, credentials, a `?` or a `#`, a scheme alone) is `invalid`, whatever the page: no nonce is asked for and
 *     nothing is fetched;
 *   - on an https page, a base whose normalized form is http is `insecure` — the browser would refuse the request
 *     (mixed content) —: no nonce, no fetch;
 *   - otherwise one nonce and one probe, through workstream A's real `checkAddress` (`settings/users/addressProbe.ts`),
 *     to the NORMALIZED base — spaces around trimmed, trailing slashes removed, a path prefix kept — followed by
 *     `/api/v1/auth/address-probe?nonce=<the nonce, encoded>`: an https page probes an https base, an http page an
 *     http or an https base;
 *   - A's verdict, mapped: `{match: true}` in an ok answer is `match`; `{match: false}` is `otherInstance`; whatever
 *     cannot be read is `unreachable` — a non-2xx answer (even one saying `match: true`), a body that is not JSON, a
 *     JSON body without a boolean `match`, a network error (a `TypeError`, what a browser raises for DNS, CORS or a
 *     refused connection), the deadline passed (the request then aborted through its signal), a nonce that cannot be
 *     issued (and then nothing is fetched);
 *   - it never throws: a transport or a nonce issuer that throws synchronously, a body whose reading throws, all end
 *     as `unreachable`.
 *
 * Fakes, all owned here: the nonce issuer and `fetchImpl` are spies built per case (A's `checkAddress` is real, so a
 * change of its mapping shows here); the global `fetch` is a failing spy in every case, so a probe that slipped past
 * `fetchImpl` would fail loudly instead of reaching the network. The deadline case runs on fake timers — A's deadline is
 * a global `setTimeout` — so nothing here waits on the clock.
 *
 * Node environment: nothing here renders.
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import {PROBE_PATH} from '$lib/features/settings/users/addressProbe';
import {probeEmailLinks, type LinksOutcome} from './emailLinks';

const NONCE = 'zq-nonce_0123';
/** A nonce with characters a query string must encode: the probe carries it encoded. */
const AWKWARD_NONCE = 'a+b/c=d&e f';

/** A response carrying `body` as JSON. */
function json(body: unknown, status = 200): Response {
    return new Response(JSON.stringify(body), {status, headers: {'content-type': 'application/json'}});
}

/** A fetch answering `respond()`: a fresh Response each call. */
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

/** The global fetch of every case: a probe that slipped past `fetchImpl` fails here, loudly. */
let globalFetch: Mock<typeof fetch>;

beforeEach(() => {
    globalFetch = vi.fn<typeof fetch>(async () => {
        throw new Error('the global fetch is not to be reached by these tests');
    });
    vi.stubGlobal('fetch', globalFetch);
});

afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

// =====================================================================================================================
describe('probeEmailLinks — what the browser can tell without asking', () => {
    it.each([
        ['an empty base', ''],
        ['a base of spaces', '   '],
        ['another scheme', 'ftp://folio.example.com'],
        ['no scheme', 'folio.example.com'],
        ['credentials', 'https://zq-user:zq-secret@folio.example.com'],
        ['a query', 'https://folio.example.com/app?lang=it'],
        ['an empty query', 'https://folio.example.com/app?'],
        ['a fragment', 'https://folio.example.com/app#top'],
        ['a scheme alone', 'https://'],
        ['an unclosed IPv6 bracket', 'https://[::1'],
    ])('ELK-01: %s is invalid, on an http page and on an https page — no nonce, no fetch', async (_label, base) => {
        for (const pageProtocol of ['http:', 'https:']) {
            const issueNonce = issuing();
            const fetchImpl = answering(() => json({match: true}));

            await expect(probeEmailLinks(base, {pageProtocol, issueNonce, fetchImpl}), `${pageProtocol} page`).resolves.toBe('invalid');

            expect(issueNonce, `${pageProtocol} page: no nonce for a base the browser cannot read`).not.toHaveBeenCalled();
            expect(fetchImpl, `${pageProtocol} page: nothing fetched`).not.toHaveBeenCalled();
        }
        expect(globalFetch).not.toHaveBeenCalled();
    });

    it.each([
        ['an http base', 'http://folio.example.com'],
        ['an http base with a port and a path prefix', 'http://192.168.1.10:6040/folio/'],
        ['an http base written in capitals, with spaces around', '  HTTP://Folio.Example.com  '],
    ])('ELK-02: on an https page, %s is insecure — the browser would refuse the request: no nonce, no fetch', async (_label, base) => {
        const issueNonce = issuing();
        const fetchImpl = answering(() => json({match: true}));

        await expect(probeEmailLinks(base, {pageProtocol: 'https:', issueNonce, fetchImpl})).resolves.toBe('insecure');

        expect(issueNonce).not.toHaveBeenCalled();
        expect(fetchImpl).not.toHaveBeenCalled();
        expect(globalFetch).not.toHaveBeenCalled();
    });
});

// =====================================================================================================================
/** The page and base pairs a browser can probe: an https page an https base, an http page either. */
const PROBED: Array<{label: string; pageProtocol: string; base: string; url: string}> = [
    {label: 'an https page, an https base', pageProtocol: 'https:', base: 'https://folio.example.com', url: `https://folio.example.com${PROBE_PATH}`},
    {label: 'an http page, an http base', pageProtocol: 'http:', base: 'http://192.168.1.10:6040', url: `http://192.168.1.10:6040${PROBE_PATH}`},
    {label: 'an http page, an https base', pageProtocol: 'http:', base: 'https://folio.example.com', url: `https://folio.example.com${PROBE_PATH}`},
];

describe('probeEmailLinks — the probe, through workstream A’s checkAddress', () => {
    it.each(
        PROBED.flatMap((pair) => [
            {...pair, answer: {match: true}, outcome: 'match' as LinksOutcome},
            {...pair, answer: {match: false}, outcome: 'otherInstance' as LinksOutcome},
        ]),
    )('ELK-03: $label, answered $answer: $outcome — one nonce, one probe at the base', async ({pageProtocol, base, url, answer, outcome}) => {
        const issueNonce = issuing();
        const fetchImpl = answering(() => json(answer));

        await expect(probeEmailLinks(base, {pageProtocol, issueNonce, fetchImpl})).resolves.toBe(outcome);

        expect(issueNonce, 'one nonce per check').toHaveBeenCalledTimes(1);
        expect(fetchImpl, 'one probe per check').toHaveBeenCalledTimes(1);
        expect(fetchImpl.mock.calls[0][0]).toBe(`${url}?nonce=${NONCE}`);
        expect(globalFetch).not.toHaveBeenCalled();
    });

    it.each([
        ['spaces around and a trailing slash', '  https://folio.example.com/  ', 'https://folio.example.com'],
        ['a path prefix with trailing slashes', 'https://folio.example.com:8443/app//', 'https://folio.example.com:8443/app'],
        ['the scheme and the host in capitals', 'HTTPS://Folio.Example.COM/App/', 'https://folio.example.com/App'],
    ])('ELK-04: the probe goes to the normalized base — %s — with the nonce encoded', async (_label, base, normalized) => {
        const fetchImpl = answering(() => json({match: true}));

        await expect(probeEmailLinks(base, {pageProtocol: 'https:', issueNonce: issuing(AWKWARD_NONCE), fetchImpl})).resolves.toBe('match');

        expect(fetchImpl.mock.calls[0][0]).toBe(`${normalized}${PROBE_PATH}?nonce=${encodeURIComponent(AWKWARD_NONCE)}`);
    });

    it.each<{label: string; respond: () => Response}>([
        {label: 'a 404 answer', respond: () => json({detail: 'Not Found'}, 404)},
        {label: 'a 500 answer saying match: true', respond: () => json({match: true}, 500)},
        {label: 'a 503 answer from a proxy', respond: () => new Response('<html>Service Unavailable</html>', {status: 503, headers: {'content-type': 'text/html'}})},
        {label: 'an ok answer that is not JSON', respond: () => new Response('<html>a captive portal</html>', {status: 200, headers: {'content-type': 'text/html'}})},
        {label: 'an ok JSON answer without match', respond: () => json({})},
        {label: 'an ok JSON answer whose match is not a boolean', respond: () => json({match: 'true'})},
    ])('ELK-05: $label is unreachable: nothing could be read', async ({respond}) => {
        const fetchImpl = answering(respond);

        await expect(probeEmailLinks('https://folio.example.com', {pageProtocol: 'https:', issueNonce: issuing(), fetchImpl})).resolves.toBe('unreachable');

        expect(fetchImpl, 'one probe: a failed one is not retried').toHaveBeenCalledTimes(1);
    });

    it('ELK-06: a network error (the TypeError a browser raises for DNS, CORS or a refused connection) is unreachable', async () => {
        const fetchImpl = vi.fn<typeof fetch>(async () => {
            throw new TypeError('Failed to fetch');
        });

        await expect(probeEmailLinks('https://folio.example.com', {pageProtocol: 'https:', issueNonce: issuing(), fetchImpl})).resolves.toBe('unreachable');
        expect(fetchImpl).toHaveBeenCalledTimes(1);
    });

    it('ELK-07: a nonce that cannot be issued is unreachable, and nothing is fetched', async () => {
        const issueNonce = vi.fn(async (): Promise<string> => {
            throw new Error('403 Admin privileges required');
        });
        const fetchImpl = answering(() => json({match: true}));

        await expect(probeEmailLinks('https://folio.example.com', {pageProtocol: 'https:', issueNonce, fetchImpl})).resolves.toBe('unreachable');

        expect(issueNonce).toHaveBeenCalledTimes(1);
        expect(fetchImpl).not.toHaveBeenCalled();
        expect(globalFetch).not.toHaveBeenCalled();
    });

    it('ELK-08: a probe still unanswered at timeoutMs is aborted through its signal, and the outcome is unreachable — on fake timers', async () => {
        vi.useFakeTimers();
        const fetchImpl = hanging();
        let outcome: LinksOutcome | 'pending' = 'pending';
        const checking = probeEmailLinks('https://folio.example.com', {pageProtocol: 'https:', issueNonce: issuing(), fetchImpl, timeoutMs: 50}).then((value) => {
            outcome = value;
        });

        await vi.advanceTimersByTimeAsync(49);
        const signal = fetchImpl.mock.calls[0]?.[1]?.signal;
        expect(fetchImpl, 'premise: the probe was sent').toHaveBeenCalledTimes(1);
        expect(signal?.aborted, 'at 49 ms the address may still answer').toBe(false);
        expect(outcome, 'no outcome before the deadline').toBe('pending');

        await vi.advanceTimersByTimeAsync(1);
        await checking;

        expect(signal?.aborted, 'at the deadline the request is aborted').toBe(true);
        expect(outcome).toBe('unreachable');
    });
});

// =====================================================================================================================
describe('probeEmailLinks — never throws', () => {
    it.each<{label: string; issueNonce: () => Promise<string>; fetchImpl: typeof fetch}>([
        {
            label: 'a transport that throws synchronously',
            issueNonce: async () => NONCE,
            fetchImpl: (() => {
                throw new Error('a transport that throws before returning a promise');
            }) as typeof fetch,
        },
        {
            label: 'a nonce issuer that throws synchronously',
            issueNonce: (() => {
                throw new Error('a nonce issuer that throws before returning a promise');
            }) as () => Promise<string>,
            fetchImpl: async () => json({match: true}),
        },
        {
            label: 'a body whose reading throws',
            issueNonce: async () => NONCE,
            fetchImpl: async () =>
                ({
                    ok: true,
                    status: 200,
                    json: async () => {
                        throw new SyntaxError('Unexpected end of JSON input');
                    },
                }) as unknown as Response,
        },
    ])('ELK-09: $label ends as unreachable, never as an exception', async ({issueNonce, fetchImpl}) => {
        await expect(probeEmailLinks('https://folio.example.com', {pageProtocol: 'https:', issueNonce, fetchImpl})).resolves.toBe('unreachable');
    });
});
