/**
 * Update check (F14) — client-side "new stable release available" probe.
 *
 * After login, an admin's browser fetches the latest *stable* release from the
 * GitHub Releases API (`/releases/latest` never returns drafts or prereleases)
 * and compares it against the running app version. Self-hosted installs that
 * are offline simply fail the fetch and nothing is shown.
 *
 * Throttling: at most one fetch per 24h (the last result is cached in
 * localStorage). Dismissal: the admin can skip a specific version; a newer one
 * will prompt again.
 */

export interface NewerRelease {
    /** Tag without the leading "v", e.g. "0.11.0". */
    version: string;
    /** Release page URL on GitHub. */
    url: string;
    /** Release display name (may be empty). */
    name: string;
}

interface UpdateCheckCache {
    checkedAt: number;
    latest: NewerRelease | null;
    dismissedVersion?: string;
}

const STORAGE_KEY = 'librefolio-update-check';
export const CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;
const FETCH_TIMEOUT_MS = 5000;
const LATEST_RELEASE_URL = 'https://api.github.com/repos/Librefolio/LibreFolio/releases/latest';

/** Numeric triple comparison; ignores leading "v" and any pre-release suffix. */
export function compareVersions(a: string, b: string): number {
    const parse = (v: string) =>
        v
            .replace(/^v/i, '')
            .split('-')[0]
            .split('.')
            .map((p) => parseInt(p, 10) || 0);
    const pa = parse(a);
    const pb = parse(b);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
        const diff = (pa[i] ?? 0) - (pb[i] ?? 0);
        if (diff !== 0) return diff < 0 ? -1 : 1;
    }
    return 0;
}

export function readCache(storage: Pick<Storage, 'getItem'> = localStorage): UpdateCheckCache | null {
    try {
        const raw = storage.getItem(STORAGE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw) as UpdateCheckCache;
        return typeof parsed?.checkedAt === 'number' ? parsed : null;
    } catch {
        return null;
    }
}

export function writeCache(cache: UpdateCheckCache, storage: Pick<Storage, 'setItem'> = localStorage): void {
    try {
        storage.setItem(STORAGE_KEY, JSON.stringify(cache));
    } catch {
        // storage full/blocked — the check simply runs again next login
    }
}

export function dismissVersion(version: string, storage: Pick<Storage, 'getItem' | 'setItem'> = localStorage): void {
    const cache = readCache(storage) ?? {checkedAt: Date.now(), latest: null};
    writeCache({...cache, dismissedVersion: version}, storage);
}

/** True when the cached/probed release should be shown to the admin. */
export function shouldPrompt(cache: UpdateCheckCache | null, currentVersion: string): {prompt: boolean; release: NewerRelease | null} {
    const latest = cache?.latest ?? null;
    if (!latest) return {prompt: false, release: null};
    if (compareVersions(latest.version, currentVersion) <= 0) return {prompt: false, release: null};
    if (cache?.dismissedVersion && compareVersions(cache.dismissedVersion, latest.version) >= 0) return {prompt: false, release: null};
    return {prompt: true, release: latest};
}

/** Whether a fresh network probe is due (never checked or older than 24h). */
export function isProbeDue(cache: UpdateCheckCache | null, now = Date.now()): boolean {
    return !cache || now - cache.checkedAt >= CHECK_INTERVAL_MS;
}

/**
 * Probe GitHub for the latest stable release. Returns null on any failure
 * (offline install, rate limit, malformed payload) — never throws.
 */
export async function probeLatestRelease(fetchFn: typeof fetch = fetch): Promise<NewerRelease | null> {
    try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
        const res = await fetchFn(LATEST_RELEASE_URL, {
            headers: {Accept: 'application/vnd.github+json'},
            signal: controller.signal,
        });
        clearTimeout(timer);
        if (!res.ok) return null;
        const data = (await res.json()) as {tag_name?: string; html_url?: string; name?: string};
        if (!data.tag_name || !data.html_url) return null;
        return {version: data.tag_name.replace(/^v/i, ''), url: data.html_url, name: data.name ?? ''};
    } catch {
        return null;
    }
}

/**
 * Full flow: use the cached probe when fresh, otherwise probe now and cache.
 * Returns the release to prompt about, or null.
 */
export async function checkForNewerRelease(currentVersion: string, fetchFn?: typeof fetch): Promise<NewerRelease | null> {
    let cache = readCache();
    if (isProbeDue(cache)) {
        const latest = await probeLatestRelease(fetchFn);
        cache = {checkedAt: Date.now(), latest, dismissedVersion: cache?.dismissedVersion};
        writeCache(cache);
    }
    return shouldPrompt(cache, currentVersion).release;
}
