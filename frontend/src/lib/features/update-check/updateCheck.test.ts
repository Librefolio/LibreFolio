/**
 * updateCheck.ts — unit tests (F14 update probe, shipped in the F12 batch).
 *
 * Pure client-side logic: version comparison, the 24h probe throttle, the
 * dismissed-version memory, and the never-throw probe. All storage is faked
 * with an in-memory map (the functions accept a Storage-like seam), all
 * fetching is a stub — nothing here touches the network or the clock's wall
 * time (timestamps are injected).
 *
 * Node env: no DOM needed.
 */

import {beforeEach, describe, expect, it, vi} from 'vitest';
import {CHECK_INTERVAL_MS, checkForNewerRelease, compareVersions, dismissVersion, isProbeDue, probeLatestRelease, readCache, shouldPrompt, writeCache} from './updateCheck';

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
        expect(compareVersions('1.3.0-beta', '1.2.9')).toBeGreaterThan(0);
    });

    it('treats missing segments as 0', () => {
        expect(compareVersions('1.2', '1.2.0')).toBe(0);
        expect(compareVersions('1.2.1', '1.2')).toBeGreaterThan(0);
    });
});

describe('shouldPrompt', () => {
    const release = {version: '2.0.0', url: 'https://example.com/rel', name: 'v2'};

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
        const newer = {version: '2.1.0', url: 'https://example.com/rel21', name: ''};
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
    it('maps a GitHub release payload, stripping the v prefix', async () => {
        const fetcher = vi.fn(
            async () =>
                new Response(JSON.stringify({tag_name: 'v1.4.2', html_url: 'https://example.com/r', name: 'Release 1.4.2'}), {
                    status: 200,
                    headers: {'content-type': 'application/json'},
                }),
        );
        await expect(probeLatestRelease(fetcher as unknown as typeof fetch)).resolves.toEqual({
            version: '1.4.2',
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

        const malformed = vi.fn(
            async () => new Response(JSON.stringify({tag_name: 'v1.0.0'}), {status: 200, headers: {'content-type': 'application/json'}}), // no html_url
        );
        await expect(probeLatestRelease(malformed as unknown as typeof fetch)).resolves.toBeNull();

        const notJson = vi.fn(async () => new Response('<html>rate limited</html>', {status: 200}));
        await expect(probeLatestRelease(notJson as unknown as typeof fetch)).resolves.toBeNull();
    });
});

describe('checkForNewerRelease cache reuse', () => {
    // The module under test defaults to globalThis.localStorage; point it at a
    // per-test fake so nothing leaks between cases (node has a localStorage in
    // recent versions, but an explicit seam beats depending on it).
    let storage: ReturnType<typeof fakeStorage>;
    beforeEach(() => {
        storage = fakeStorage();
        vi.stubGlobal('localStorage', storage);
    });

    it('serves a fresh cache without fetching', async () => {
        writeCache({checkedAt: Date.now(), latest: {version: '9.9.9', url: 'u', name: ''}}, storage);
        const fetcher = vi.fn();
        const result = await checkForNewerRelease('1.0.0', fetcher as unknown as typeof fetch);
        expect(result?.version).toBe('9.9.9');
        expect(fetcher).not.toHaveBeenCalled();
    });

    it('probes when the cache is stale, and keeps a dismissal across the re-probe', async () => {
        dismissVersion('2.0.0', storage); // dismissal recorded against the old probe
        const stale = readCache(storage)!;
        writeCache({...stale, checkedAt: Date.now() - CHECK_INTERVAL_MS - 1}, storage);

        const fetcher = vi.fn(
            async () =>
                new Response(JSON.stringify({tag_name: 'v2.0.0', html_url: 'https://example.com/r2', name: ''}), {
                    status: 200,
                    headers: {'content-type': 'application/json'},
                }),
        );
        const result = await checkForNewerRelease('1.0.0', fetcher as unknown as typeof fetch);

        expect(fetcher).toHaveBeenCalledTimes(1);
        // The re-probed version equals the dismissed one → no prompt.
        expect(result).toBeNull();
    });

    it('caches a failed probe as null rather than throwing', async () => {
        const fetcher = vi.fn(async () => {
            throw new Error('offline');
        });
        const result = await checkForNewerRelease('1.0.0', fetcher as unknown as typeof fetch);

        expect(result).toBeNull();
        const cache = readCache(storage);
        expect(cache).not.toBeNull();
        expect(cache!.latest).toBeNull();
        // ...and the failure is remembered: an immediate second call must not re-fetch.
        const again = await checkForNewerRelease('1.0.0', fetcher as unknown as typeof fetch);
        expect(again).toBeNull();
        expect(fetcher).toHaveBeenCalledTimes(1);
    });
});

describe('readCache robustness', () => {
    it('returns null for malformed or shapeless payloads', () => {
        const storage = fakeStorage();
        storage.setItem('librefolio-update-check', 'not json{');
        expect(readCache(storage)).toBeNull();

        storage.setItem('librefolio-update-check', JSON.stringify({latest: null}));
        expect(readCache(storage)).toBeNull(); // no numeric checkedAt

        storage.setItem('librefolio-update-check', JSON.stringify({checkedAt: 42, latest: null}));
        expect(readCache(storage)).toEqual({checkedAt: 42, latest: null});
    });
});
