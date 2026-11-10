/**
 * emailLinks — the check, from the administrator's browser, that the base of the emailed links reaches *this* instance
 * (workstream E, lot E3p, developer decision 45).
 *
 * The contract under test, `probeEmailLinks(base, {pageProtocol, issueNonce, loadImage?, timeoutMs?})`:
 *   - a base the browser cannot read as an http(s) address (`normalizeBase` refuses it: empty, another scheme, no
 *     scheme, credentials, a `?` or a `#`, a scheme alone) is `invalid`, whatever the page: no nonce is asked for and
 *     nothing is loaded;
 *   - on an https page, a base whose normalized form is http is `insecure` — the browser would refuse the request
 *     (mixed content) —: no nonce, no image;
 *   - otherwise one nonce and one probe, through workstream A's real `checkAddress` (`settings/users/addressProbe.ts`),
 *     to the NORMALIZED base — spaces around trimmed, trailing slashes removed, a path prefix kept — which is an IMAGE
 *     (H-55 v2: under the enforced `connect-src`, a `fetch` to another origin is blocked; `img-src` is not enforced):
 *     `loadImage(<base>/api/v1/auth/address-probe.png?nonce=<the nonce, encoded>, signal)`: an https page probes an
 *     https base, an http page an http or an https base;
 *   - A's verdict, mapped: an image of 1×1 is `match`; of 2×1 is `otherInstance`; whatever cannot be read is
 *     `unreachable` — an image of another size, an image that fails to load (a 404, a proxy's page, a refused
 *     connection, DNS, a local-network permission), the deadline passed (the load then aborted through its signal), a
 *     nonce that cannot be issued (and then nothing is loaded);
 *   - it never throws: a loader or a nonce issuer that throws synchronously, an image whose size cannot be read, all end
 *     as `unreachable`.
 *
 * Fakes, all owned here: the nonce issuer and `loadImage` are spies built per case (A's `checkAddress` is real, so a
 * change of its mapping shows here); the global `fetch` is a failing spy in every case, so a probe sent through it —
 * the transport this check no longer has — would fail loudly instead of reaching the network. The deadline case runs on
 * fake timers — A's deadline is a global `setTimeout` — so nothing here waits on the clock.
 *
 * Red today: `checkAddress` still probes with `fetch` and ignores `loadImage`, and `PROBE_IMAGE_PATH` does not exist.
 *
 * Node environment: nothing here renders.
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import {PROBE_IMAGE_PATH} from '$lib/features/settings/users/addressProbe';
import {probeEmailLinks, type LinksOutcome} from './emailLinks';

const NONCE = 'zq-nonce_0123';
/** A nonce with characters a query string must encode: the probe carries it encoded. */
const AWKWARD_NONCE = 'a+b/c=d&e f';

/** What a loaded image tells: its natural size, the only thing of it that is read. */
interface LoadedImage {
    naturalWidth: number;
    naturalHeight: number;
}
type LoadImage = (url: string, signal: AbortSignal) => Promise<LoadedImage>;

/** A loader answering an image of `width`×`height`: 1×1 is this instance's, 2×1 another one's. */
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

/** The global fetch of every case: a probe sent through it — the transport this check no longer has — fails here, loudly. */
let globalFetch: Mock<typeof fetch>;

beforeEach(() => {
    globalFetch = vi.fn<typeof fetch>(async () => {
        throw new Error('the global fetch is not to be reached by these tests: the probe is an image');
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
    ])('ELK-01: %s is invalid, on an http page and on an https page — no nonce, no image', async (_label, base) => {
        for (const pageProtocol of ['http:', 'https:']) {
            const issueNonce = issuing();
            const loadImage = drawing(1, 1);

            await expect(probeEmailLinks(base, {pageProtocol, issueNonce, loadImage}), `${pageProtocol} page`).resolves.toBe('invalid');

            expect(issueNonce, `${pageProtocol} page: no nonce for a base the browser cannot read`).not.toHaveBeenCalled();
            expect(loadImage, `${pageProtocol} page: nothing loaded`).not.toHaveBeenCalled();
        }
        expect(globalFetch).not.toHaveBeenCalled();
    });

    it.each([
        ['an http base', 'http://folio.example.com'],
        ['an http base with a port and a path prefix', 'http://192.168.1.10:6040/folio/'],
        ['an http base written in capitals, with spaces around', '  HTTP://Folio.Example.com  '],
    ])('ELK-02: on an https page, %s is insecure — the browser would refuse the request: no nonce, no image', async (_label, base) => {
        const issueNonce = issuing();
        const loadImage = drawing(1, 1);

        await expect(probeEmailLinks(base, {pageProtocol: 'https:', issueNonce, loadImage})).resolves.toBe('insecure');

        expect(issueNonce).not.toHaveBeenCalled();
        expect(loadImage).not.toHaveBeenCalled();
        expect(globalFetch).not.toHaveBeenCalled();
    });
});

// =====================================================================================================================
/** The page and base pairs a browser can probe: an https page an https base, an http page either. */
const PROBED: Array<{label: string; pageProtocol: string; base: string; url: string}> = [
    {label: 'an https page, an https base', pageProtocol: 'https:', base: 'https://folio.example.com', url: `https://folio.example.com${PROBE_IMAGE_PATH}`},
    {label: 'an http page, an http base', pageProtocol: 'http:', base: 'http://192.168.1.10:6040', url: `http://192.168.1.10:6040${PROBE_IMAGE_PATH}`},
    {label: 'an http page, an https base', pageProtocol: 'http:', base: 'https://folio.example.com', url: `https://folio.example.com${PROBE_IMAGE_PATH}`},
];

describe('probeEmailLinks — the probe, through workstream A’s checkAddress', () => {
    it.each(
        PROBED.flatMap((pair) => [
            {...pair, size: [1, 1] as const, outcome: 'match' as LinksOutcome},
            {...pair, size: [2, 1] as const, outcome: 'otherInstance' as LinksOutcome},
        ]),
    )('ELK-03: $label, an image of $size: $outcome — one nonce, one probe at the base', async ({pageProtocol, base, url, size, outcome}) => {
        const issueNonce = issuing();
        const loadImage = drawing(size[0], size[1]);

        await expect(probeEmailLinks(base, {pageProtocol, issueNonce, loadImage})).resolves.toBe(outcome);

        expect(issueNonce, 'one nonce per check').toHaveBeenCalledTimes(1);
        expect(loadImage, 'one probe per check').toHaveBeenCalledTimes(1);
        expect(loadImage.mock.calls[0][0]).toBe(`${url}?nonce=${NONCE}`);
        expect(loadImage.mock.calls[0][1], 'with a signal').toBeInstanceOf(AbortSignal);
        expect(globalFetch).not.toHaveBeenCalled();
    });

    it.each([
        ['spaces around and a trailing slash', '  https://folio.example.com/  ', 'https://folio.example.com'],
        ['a path prefix with trailing slashes', 'https://folio.example.com:8443/app//', 'https://folio.example.com:8443/app'],
        ['the scheme and the host in capitals', 'HTTPS://Folio.Example.COM/App/', 'https://folio.example.com/App'],
    ])('ELK-04: the probe goes to the normalized base — %s — with the nonce encoded', async (_label, base, normalized) => {
        const loadImage = drawing(1, 1);

        await expect(probeEmailLinks(base, {pageProtocol: 'https:', issueNonce: issuing(AWKWARD_NONCE), loadImage})).resolves.toBe('match');

        expect(loadImage.mock.calls[0][0]).toBe(`${normalized}${PROBE_IMAGE_PATH}?nonce=${encodeURIComponent(AWKWARD_NONCE)}`);
    });

    it.each<{label: string; loadImage: () => Mock<LoadImage>}>([
        {label: 'an image that fails to load (a 404, or a proxy’s page that is no image)', loadImage: () => vi.fn<LoadImage>(async () => Promise.reject(new Event('error')))},
        {label: 'an image of 3×1', loadImage: () => drawing(3, 1)},
        {label: 'an image of 1×2', loadImage: () => drawing(1, 2)},
        {label: 'a broken image, of 0×0 (a page that answers every path with a picture the browser cannot draw)', loadImage: () => drawing(0, 0)},
        {label: 'a picture of 300×150, as a single-page app’s logo might be', loadImage: () => drawing(300, 150)},
    ])('ELK-05: $label is unreachable: nothing could be read', async ({loadImage: build}) => {
        const loadImage = build();

        await expect(probeEmailLinks('https://folio.example.com', {pageProtocol: 'https:', issueNonce: issuing(), loadImage})).resolves.toBe('unreachable');

        expect(loadImage, 'one probe: a failed one is not retried').toHaveBeenCalledTimes(1);
    });

    it('ELK-06: a network error (the error event a browser raises for DNS, a refused connection or mixed content) is unreachable', async () => {
        const loadImage = vi.fn<LoadImage>(async () => {
            throw new Event('error');
        });

        await expect(probeEmailLinks('https://folio.example.com', {pageProtocol: 'https:', issueNonce: issuing(), loadImage})).resolves.toBe('unreachable');
        expect(loadImage).toHaveBeenCalledTimes(1);
    });

    it('ELK-07: a nonce that cannot be issued is unreachable, and nothing is loaded', async () => {
        const issueNonce = vi.fn(async (): Promise<string> => {
            throw new Error('403 Admin privileges required');
        });
        const loadImage = drawing(1, 1);

        await expect(probeEmailLinks('https://folio.example.com', {pageProtocol: 'https:', issueNonce, loadImage})).resolves.toBe('unreachable');

        expect(issueNonce).toHaveBeenCalledTimes(1);
        expect(loadImage).not.toHaveBeenCalled();
        expect(globalFetch).not.toHaveBeenCalled();
    });

    it('ELK-08: a probe still unanswered at timeoutMs is aborted through its signal, and the outcome is unreachable — on fake timers', async () => {
        vi.useFakeTimers();
        const loadImage = hanging();
        let outcome: LinksOutcome | 'pending' = 'pending';
        const checking = probeEmailLinks('https://folio.example.com', {pageProtocol: 'https:', issueNonce: issuing(), loadImage, timeoutMs: 50}).then((value) => {
            outcome = value;
        });

        await vi.advanceTimersByTimeAsync(49);
        const signal = loadImage.mock.calls[0]?.[1];
        expect(loadImage, 'premise: the probe was sent').toHaveBeenCalledTimes(1);
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
    it.each<{label: string; issueNonce: () => Promise<string>; loadImage: LoadImage}>([
        {
            label: 'a loader that throws synchronously',
            issueNonce: async () => NONCE,
            loadImage: (() => {
                throw new Error('a loader that throws before returning a promise');
            }) as LoadImage,
        },
        {
            label: 'a nonce issuer that throws synchronously',
            issueNonce: (() => {
                throw new Error('a nonce issuer that throws before returning a promise');
            }) as () => Promise<string>,
            loadImage: async () => ({naturalWidth: 1, naturalHeight: 1}),
        },
        {
            label: 'an image whose size cannot be read',
            issueNonce: async () => NONCE,
            loadImage: async () =>
                ({
                    get naturalWidth(): number {
                        throw new Error('the size of an image that is gone');
                    },
                    naturalHeight: 1,
                }) as LoadedImage,
        },
    ])('ELK-09: $label ends as unreachable, never as an exception', async ({issueNonce, loadImage}) => {
        await expect(probeEmailLinks('https://folio.example.com', {pageProtocol: 'https:', issueNonce, loadImage})).resolves.toBe('unreachable');
    });
});
