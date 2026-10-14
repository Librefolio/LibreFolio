/**
 * updateCheck.ts — unit tests (F14 update probe, shipped in the F12 batch).
 *
 * Pure client-side logic: version comparison, the 24h probe throttle, the
 * dismissed-version memory, and the never-throw probe. All storage is faked
 * with an in-memory map (the functions accept a Storage-like seam), all
 * fetching is a stub — nothing here touches the network or the clock's wall
 * time (timestamps are injected).
 *
 * The GHCR image gate (E9 — GHCR-auth round, see the `describe` block near the
 * bottom) is exercised the same way: through its typed `ImageProbe` seam, never
 * through `fetchFn`. The handshake itself is same-origin backend work — see the
 * comment on that block for why, and for what is deliberately out of reach here.
 *
 * Node env: no DOM needed.
 */

import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const imageStatusApi = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({
    zodiosApi: {
        get_container_image_status_api_v1_system_container_image_status_get: imageStatusApi,
    },
}));

import {CHECK_INTERVAL_MS, checkForUpdates, compareVersions, isProbeDue, probeLatestRelease, readCache, shouldPrompt, writeCache, type ImageProbeResult} from './updateCheck';

/** An in-memory Storage seam. */
function fakeStorage() {
    const map = new Map<string, string>();
    return {
        getItem: (k: string) => map.get(k) ?? null,
        setItem: (k: string, v: string) => void map.set(k, v),
        removeItem: (k: string) => void map.delete(k),
        map,
    };
}

function jsonResponse(body: unknown, status = 200): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: {'content-type': 'application/json'},
    });
}

describe('compareVersions', () => {
    it('orders numeric triples', () => {
        expect(compareVersions('1.2.0', '1.10.0')).toBeLessThan(0); // numeric, not lexical
        expect(compareVersions('1.10.0', '1.2.0')).toBeGreaterThan(0);
        expect(compareVersions('1.2.0', '1.2.0')).toBe(0);
    });

    it('ignores a leading v and any pre-release suffix', () => {
        expect(compareVersions('v1.2.0', '1.2.0')).toBe(0);
        expect(compareVersions('V2.0.0', '1.9.9')).toBeGreaterThan(0);
        expect(compareVersions('1.3.0-rc.1', '1.3.0')).toBe(0);
        expect(compareVersions('1.1.0', '1.0.1-114')).toBeGreaterThan(0);
    });

    it('treats missing segments as 0 and malformed input as NaN', () => {
        expect(compareVersions('1.2', '1.2.0')).toBe(0);
        expect(compareVersions('1.2.1', '1.2')).toBeGreaterThan(0);
        expect(Number.isNaN(compareVersions('1..0', '1.0.0'))).toBe(true);
        expect(Number.isNaN(compareVersions('definitely-not-a-version', '1.0.0'))).toBe(true);
    });
});

describe('shouldPrompt', () => {
    const release = {version: '2.0.0', tag: 'v2.0.0', url: 'https://example.com/rel', name: 'v2'};

    it('prompts when the latest release is newer than the running version', () => {
        const {prompt, release: got} = shouldPrompt({checkedAt: 1, latest: release}, '1.9.0');
        expect(prompt).toBe(true);
        expect(got).toEqual(release);
    });

    it('does not prompt for an older or equal release', () => {
        expect(shouldPrompt({checkedAt: 1, latest: release}, '2.0.0').prompt).toBe(false);
        expect(shouldPrompt({checkedAt: 1, latest: release}, '2.1.0').prompt).toBe(false);
    });

    it('does not prompt when nothing was probed', () => {
        expect(shouldPrompt(null, '1.0.0').prompt).toBe(false);
        expect(shouldPrompt({checkedAt: 1, latest: null}, '1.0.0').prompt).toBe(false);
    });

    it('honours the dismissed version, but prompts again for a newer one', () => {
        expect(shouldPrompt({checkedAt: 1, latest: release, dismissedVersion: '2.0.0'}, '1.9.0').prompt).toBe(false);
        const newer = {version: '2.1.0', tag: 'v2.1.0', url: 'https://example.com/rel21', name: ''};
        expect(shouldPrompt({checkedAt: 1, latest: newer, dismissedVersion: '2.0.0'}, '1.9.0').prompt).toBe(true);
    });
});

describe('isProbeDue', () => {
    it('is due with no cache and after 24h, not before', () => {
        expect(isProbeDue(null, 1_000)).toBe(true);
        expect(isProbeDue({checkedAt: 1_000, latest: null}, 1_000 + CHECK_INTERVAL_MS - 1)).toBe(false);
        expect(isProbeDue({checkedAt: 1_000, latest: null}, 1_000 + CHECK_INTERVAL_MS)).toBe(true);
    });
});

describe('probeLatestRelease', () => {
    it('maps a GitHub release payload, retaining the raw tag', async () => {
        const fetcher = vi.fn(async () => jsonResponse({tag_name: 'v1.4.2', html_url: 'https://example.com/r', name: 'Release 1.4.2'}));
        await expect(probeLatestRelease(fetcher as unknown as typeof fetch)).resolves.toEqual({
            version: '1.4.2',
            tag: 'v1.4.2',
            url: 'https://example.com/r',
            name: 'Release 1.4.2',
        });
    });

    it('never throws: network failure, non-200 and malformed payloads all become null', async () => {
        const rejecting = vi.fn(async () => {
            throw new Error('offline install');
        });
        await expect(probeLatestRelease(rejecting as unknown as typeof fetch)).resolves.toBeNull();

        const notFound = vi.fn(async () => new Response('nope', {status: 404}));
        await expect(probeLatestRelease(notFound as unknown as typeof fetch)).resolves.toBeNull();

        const malformed = vi.fn(async () => jsonResponse({tag_name: 'v1.0.0'}));
        await expect(probeLatestRelease(malformed as unknown as typeof fetch)).resolves.toBeNull();

        const prerelease = vi.fn(async () => jsonResponse({tag_name: 'v1.0.0', html_url: 'https://example.com/r', name: 'Draft', prerelease: true}));
        await expect(probeLatestRelease(prerelease as unknown as typeof fetch)).resolves.toBeNull();

        const notJson = vi.fn(async () => new Response('<html>rate limited</html>', {status: 200}));
        await expect(probeLatestRelease(notJson as unknown as typeof fetch)).resolves.toBeNull();
    });
});

describe('checkForUpdates', () => {
    let storage: ReturnType<typeof fakeStorage>;

    beforeEach(() => {
        storage = fakeStorage();
        vi.stubGlobal('localStorage', storage);
        imageStatusApi.mockReset();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('returns an error for malformed current versions without probing', async () => {
        const fetcher = vi.fn(async () => {
            throw new Error('should not fetch');
        });

        await expect(checkForUpdates('not-a-version', {}, fetcher as unknown as typeof fetch)).resolves.toEqual({
            status: 'error',
            latest: null,
            source: 'none',
            checkedAt: null,
            reason: 'invalid-current-version',
        });
        expect(fetcher).not.toHaveBeenCalled();
    });

    it('serves a fresh cached release and preserves the cached shape', async () => {
        const now = 1_700_000_000_000;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        writeCache(
            {
                checkedAt: now,
                latest: {version: '9.9.9', tag: 'v9.9.9', url: 'https://example.com/r', name: 'Release 9.9.9'},
                dismissedVersion: '9.8.0',
                probeStatus: 'success',
            },
            storage,
        );

        const fetcher = vi.fn(async () => {
            throw new Error('cache should have short-circuited');
        });
        const result = await checkForUpdates('9.9.9', {}, fetcher as unknown as typeof fetch);

        expect(result).toEqual({
            status: 'up-to-date',
            latest: {version: '9.9.9', tag: 'v9.9.9', url: 'https://example.com/r', name: 'Release 9.9.9'},
            source: 'cache',
            checkedAt: now,
        });
        expect(fetcher).not.toHaveBeenCalled();
        expect(readCache(storage)).toEqual({
            checkedAt: now,
            latest: {version: '9.9.9', tag: 'v9.9.9', url: 'https://example.com/r', name: 'Release 9.9.9'},
            dismissedVersion: '9.8.0',
            probeStatus: 'success',
        });
    });

    it('manual checks ignore dismissal but keep the remembered version', async () => {
        const now = 1_700_000_000_001;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        writeCache(
            {
                checkedAt: now - CHECK_INTERVAL_MS - 1,
                latest: {version: '1.2.3', tag: 'v1.2.3', url: 'https://example.com/old', name: 'Old'},
                dismissedVersion: '1.2.3',
                probeStatus: 'success',
            },
            storage,
        );

        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v1.2.4', html_url: 'https://example.com/r', name: 'Release 1.2.4'});
            }
            throw new Error(`unexpected url: ${url}`);
        });
        // The image gate is a separate seam (`imageProbe`), never `fetchFn`: GHCR's
        // public-token handshake is same-origin backend work (see the "GHCR public-
        // token image gate" block below), so `checkForUpdates` never fetches a
        // manifest URL itself.
        const imageProbe = vi.fn(async (): Promise<ImageProbeResult> => ({status: 'published'}));

        const result = await checkForUpdates('1.2.3', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch, imageProbe);

        expect(result).toEqual({
            status: 'update-available',
            latest: {version: '1.2.4', tag: 'v1.2.4', url: 'https://example.com/r', name: 'Release 1.2.4'},
            source: 'network',
            checkedAt: now,
        });
        expect(fetcher).toHaveBeenCalledTimes(1);
        expect(imageProbe).toHaveBeenCalledTimes(1);
        expect(imageProbe).toHaveBeenCalledWith('1.2.4');
        expect(readCache(storage)?.dismissedVersion).toBe('1.2.3');
    });

    it('treats a missing release as no-release rather than up-to-date', async () => {
        const now = 1_700_000_000_002;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) return new Response('nope', {status: 404});
            throw new Error(`unexpected url: ${url}`);
        });

        const result = await checkForUpdates('1.2.3', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch);

        expect(result).toEqual({
            status: 'no-release',
            latest: null,
            source: 'network',
            checkedAt: now,
        });
        expect(result.status).not.toBe('up-to-date');
    });

    it('treats a release-request failure as error with no latest', async () => {
        const now = 1_700_000_000_003;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) return new Response('nope', {status: 401});
            throw new Error(`unexpected url: ${url}`);
        });

        await expect(checkForUpdates('1.2.3', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch)).resolves.toEqual({
            status: 'error',
            latest: null,
            source: 'network',
            checkedAt: now,
            reason: 'release-request-failed',
        });
    });

    it('maps a pending image probe to image-pending', async () => {
        const now = 1_700_000_000_004;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v1.2.4', html_url: 'https://example.com/r', name: 'Release 1.2.4'});
            }
            throw new Error(`unexpected url: ${url}`);
        });
        // The backend maps an authenticated manifest 404 to this pending result.
        const imageProbe = vi.fn(async (): Promise<ImageProbeResult> => ({status: 'pending'}));

        const result = await checkForUpdates('1.2.3', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch, imageProbe);

        expect(result).toEqual({
            status: 'image-pending',
            latest: {version: '1.2.4', tag: 'v1.2.4', url: 'https://example.com/r', name: 'Release 1.2.4'},
            source: 'network',
            checkedAt: now,
        });
        expect(imageProbe).toHaveBeenCalledWith('1.2.4');
    });

    it('preserves a manifest-phase image failure distinctly from an auth-phase failure', async () => {
        const now = 1_700_000_000_005;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v1.2.4', html_url: 'https://example.com/r', name: 'Release 1.2.4'});
            }
            throw new Error(`unexpected url: ${url}`);
        });
        // The backend maps an authenticated manifest 401 to this reason.
        const imageProbe = vi.fn(async (): Promise<ImageProbeResult> => ({status: 'error', reason: 'image-request-failed'}));

        const result = await checkForUpdates('1.2.3', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch, imageProbe);

        expect(result).toEqual({
            status: 'error',
            latest: {version: '1.2.4', tag: 'v1.2.4', url: 'https://example.com/r', name: 'Release 1.2.4'},
            source: 'network',
            checkedAt: now,
            reason: 'image-request-failed',
        });
        expect(result.reason).not.toBe('image-auth-request-failed');
        expect(result.status).not.toBe('update-available');
        expect(result.status).not.toBe('up-to-date');
    });

    /**
     * GHCR public-token image gate (E9 — GHCR-auth round).
     *
     * The GHCR token/manifest handshake (challenge parsing and trust checks,
     * the credential-free token fetch, the Bearer-only retry) is same-origin
     * backend work with no client-observable HTTP surface — see
     * `backend/app/services/container_registry.py`. From here,
     * `checkForUpdates` only ever sees the typed `ImageProbe` seam's result, so
     * these cases pin down consumption of that result only: every reported
     * reason maps to the correct outcome and no error path is ever reported as
     * an available update.
     */
    it('preserves an auth-phase image failure distinctly from a manifest failure', async () => {
        const now = 1_700_000_000_006;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v1.3.0', html_url: 'https://example.com/r130', name: 'Release 1.3.0'});
            }
            throw new Error(`unexpected url: ${url}`);
        });
        // Token failures and rejected challenges arrive from the backend with
        // this reason; the frontend must not collapse them into manifest errors.
        const imageProbe = vi.fn(async (): Promise<ImageProbeResult> => ({status: 'error', reason: 'image-auth-request-failed'}));

        const result = await checkForUpdates('1.0.0', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch, imageProbe);

        expect(result).toEqual({
            status: 'error',
            latest: {version: '1.3.0', tag: 'v1.3.0', url: 'https://example.com/r130', name: 'Release 1.3.0'},
            source: 'network',
            checkedAt: now,
            reason: 'image-auth-request-failed',
        });
        expect(result.reason).not.toBe('image-request-failed');
        expect(result.status).not.toBe('update-available');
        expect(result.status).not.toBe('up-to-date');
    });

    it('normalizes a real registry release tag for the image probe while preserving the display tag', async () => {
        const now = 1_700_000_000_009;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v1.1.0', html_url: 'https://example.com/r110', name: 'Release 1.1.0'});
            }
            throw new Error(`unexpected url: ${url}`);
        });
        const imageProbe = vi.fn(async (): Promise<ImageProbeResult> => ({status: 'published'}));

        const result = await checkForUpdates('1.0.0', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch, imageProbe);

        expect(result.status).toBe('update-available');
        expect(result.latest).toEqual({version: '1.1.0', tag: 'v1.1.0', url: 'https://example.com/r110', name: 'Release 1.1.0'});
        expect(imageProbe).toHaveBeenCalledTimes(1);
        expect(imageProbe).toHaveBeenCalledWith('1.1.0');
        expect(imageProbe).not.toHaveBeenCalledWith('v1.1.0');
    });

    it('suppresses an automatic prompt for a version the admin already dismissed, without touching the network or the image gate', async () => {
        const now = 1_700_000_000_010;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        writeCache(
            {
                checkedAt: now,
                latest: {version: '2.0.0', tag: 'v2.0.0', url: 'https://example.com/r200', name: 'Release 2.0.0'},
                dismissedVersion: '2.0.0',
                probeStatus: 'success',
            },
            storage,
        );
        const fetcher = vi.fn(async () => {
            throw new Error('cache is fresh — the automatic path must never re-probe');
        });
        const imageProbe = vi.fn(async (): Promise<ImageProbeResult> => ({status: 'published'}));

        const result = await checkForUpdates('1.0.0', {}, fetcher as unknown as typeof fetch, imageProbe);

        expect(result).toEqual({
            status: 'dismissed',
            latest: {version: '2.0.0', tag: 'v2.0.0', url: 'https://example.com/r200', name: 'Release 2.0.0'},
            source: 'cache',
            checkedAt: now,
        });
        expect(fetcher).not.toHaveBeenCalled();
        // A dismissed release is never worth an image probe: nothing will be
        // shown regardless of whether the tag turns out to be pullable.
        expect(imageProbe).not.toHaveBeenCalled();
    });

    it('a forced refresh still honours dismissal when ignoreDismissed is not set', async () => {
        const now = 1_700_000_000_011;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        writeCache(
            {
                checkedAt: now - CHECK_INTERVAL_MS - 1,
                latest: {version: '2.0.0', tag: 'v2.0.0', url: 'https://example.com/old200', name: 'Old 2.0.0'},
                dismissedVersion: '2.0.0',
                probeStatus: 'success',
            },
            storage,
        );
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v2.0.0', html_url: 'https://example.com/r200', name: 'Release 2.0.0'});
            }
            throw new Error(`unexpected url: ${url}`);
        });
        const imageProbe = vi.fn(async (): Promise<ImageProbeResult> => ({status: 'published'}));

        // `force` alone refreshes the network probe; `ignoreDismissed` is
        // deliberately omitted, so the freshly-probed release must still be
        // suppressed — the two flags are independent, not a single switch.
        const result = await checkForUpdates('1.0.0', {force: true}, fetcher as unknown as typeof fetch, imageProbe);

        expect(result).toEqual({
            status: 'dismissed',
            latest: {version: '2.0.0', tag: 'v2.0.0', url: 'https://example.com/r200', name: 'Release 2.0.0'},
            source: 'network',
            checkedAt: now,
        });
        expect(fetcher).toHaveBeenCalledTimes(1);
        expect(imageProbe).not.toHaveBeenCalled();
        expect(readCache(storage)?.dismissedVersion).toBe('2.0.0');
    });

    it('never sends the injected GitHub fetch to GHCR — the image gate goes through imageProbe only', async () => {
        const now = 1_700_000_000_012;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            // A call reaching a registry host directly from the browser fetch is
            // exactly the defect this round fixed: GHCR's public-token handshake
            // must stay same-origin backend work, never a client fetch (CORS
            // rules it out — see the block comment above this describe).
            if (/ghcr\.io/i.test(url)) {
                throw new Error(`fetchFn must never reach GHCR directly, got: ${url}`);
            }
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v3.0.0', html_url: 'https://example.com/r300', name: 'Release 3.0.0'});
            }
            throw new Error(`unexpected url: ${url}`);
        });
        const imageProbe = vi.fn(async (): Promise<ImageProbeResult> => ({status: 'published'}));

        const result = await checkForUpdates('1.0.0', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch, imageProbe);

        expect(result.status).toBe('update-available');
        expect(fetcher).toHaveBeenCalledTimes(1);
        expect(fetcher.mock.calls.every(([url]) => !/ghcr\.io/i.test(String(url)))).toBe(true);
        expect(imageProbe).toHaveBeenCalledTimes(1);
    });

    it('uses the typed same-origin image endpoint when no image probe is injected', async () => {
        const now = 1_700_000_000_013;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v3.1.0', html_url: 'https://example.com/r310', name: 'Release 3.1.0'});
            }
            throw new Error(`unexpected URL outside the GitHub release probe: ${url}`);
        });
        imageStatusApi.mockResolvedValue({status: 'published'});

        const result = await checkForUpdates('3.0.0', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch);

        expect(result.status).toBe('update-available');
        expect(fetcher).toHaveBeenCalledTimes(1);
        expect(fetcher.mock.calls.every(([url]) => !/ghcr\.io/i.test(String(url)))).toBe(true);
        expect(imageStatusApi).toHaveBeenCalledTimes(1);
        expect(imageStatusApi).toHaveBeenCalledWith({queries: {tag: '3.1.0'}});
    });

    it('fails closed as image-request-failed when the default same-origin API call itself throws (no image probe injected)', async () => {
        const now = 1_700_000_000_007;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v3.2.0', html_url: 'https://example.com/r320', name: 'Release 3.2.0'});
            }
            throw new Error(`unexpected URL outside the GitHub release probe: ${url}`);
        });
        // No `imageProbe` argument: exercises the default `probeImageWithApi` path
        // (the same zodios call as the success case above), rejecting the way a
        // network/backend failure would. This must fail closed exactly like a
        // rejected injected probe — never reported as published.
        imageStatusApi.mockRejectedValue(new Error('backend unreachable'));

        const result = await checkForUpdates('3.0.0', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch);

        expect(result).toEqual({
            status: 'error',
            latest: {version: '3.2.0', tag: 'v3.2.0', url: 'https://example.com/r320', name: 'Release 3.2.0'},
            source: 'network',
            checkedAt: now,
            reason: 'image-request-failed',
        });
        expect(result.status).not.toBe('update-available');
        expect(imageStatusApi).toHaveBeenCalledTimes(1);
        expect(imageStatusApi).toHaveBeenCalledWith({queries: {tag: '3.2.0'}});
    });

    it('fails closed when the injected image probe itself throws, never surfacing an available update', async () => {
        const now = 1_700_000_000_014;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v1.5.0', html_url: 'https://example.com/r150', name: 'Release 1.5.0'});
            }
            throw new Error(`unexpected url: ${url}`);
        });
        // A rejected imageProbe (the same-origin backend unreachable, an aborted
        // request, …) must be swallowed exactly like a reported manifest error —
        // the admin is told the tag could not be verified, never that it is safe
        // to pull.
        const imageProbe = vi.fn(async (): Promise<ImageProbeResult> => {
            throw new Error('backend unreachable');
        });

        const result = await checkForUpdates('1.0.0', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch, imageProbe);

        expect(result).toEqual({
            status: 'error',
            latest: {version: '1.5.0', tag: 'v1.5.0', url: 'https://example.com/r150', name: 'Release 1.5.0'},
            source: 'network',
            checkedAt: now,
            reason: 'image-request-failed',
        });
        expect(result.status).not.toBe('update-available');
    });

    it.each<[string, unknown]>([
        ['an empty object with no status', {}],
        ['an unrecognised status value', {status: 'unexpected-status'}],
        ['a null result', null],
        ['a bare string instead of a result object', 'published'],
    ])('fails closed for a malformed image probe result (%s), never surfacing an available update', async (_label, malformed) => {
        const now = 1_700_000_000_015;
        vi.spyOn(Date, 'now').mockReturnValue(now);
        const fetcher = vi.fn(async (url: string) => {
            if (url.includes('/releases/latest')) {
                return jsonResponse({tag_name: 'v1.6.0', html_url: 'https://example.com/r160', name: 'Release 1.6.0'});
            }
            throw new Error(`unexpected url: ${url}`);
        });
        // The seam is typed, but a probe implementation can still misbehave
        // (backend contract drift, a broken mock in a caller's own test, …) — the
        // consumer must not crash or silently treat that as a success.
        const imageProbe = vi.fn(async () => malformed as ImageProbeResult);

        const result = await checkForUpdates('1.0.0', {force: true, ignoreDismissed: true}, fetcher as unknown as typeof fetch, imageProbe);

        expect(result.status).toBe('error');
        expect(result.reason).toBe('image-request-failed');
        expect(result.status).not.toBe('update-available');
    });
});

describe('readCache robustness', () => {
    it('returns null for malformed or shapeless payloads', () => {
        const storage = fakeStorage();
        storage.setItem('librefolio-update-check', 'not json{');
        expect(readCache(storage)).toBeNull();

        storage.setItem('librefolio-update-check', JSON.stringify({latest: null}));
        expect(readCache(storage)).toBeNull(); // no numeric checkedAt

        storage.setItem('librefolio-update-check', JSON.stringify({checkedAt: 42, latest: {version: '1.2.3', tag: 'v1.2.3', url: 'https://example.com/r', name: 'Release 1.2.3'}, probeStatus: 'success'}));
        expect(readCache(storage)).toEqual({
            checkedAt: 42,
            latest: {version: '1.2.3', tag: 'v1.2.3', url: 'https://example.com/r', name: 'Release 1.2.3'},
            probeStatus: 'success',
        });
    });
});
