/**
 * Update check (F14) — client-side "new stable release available" probe.
 *
 * After login, an admin's browser fetches the latest *stable* release from the
 * GitHub Releases API (`/releases/latest` never returns drafts or prereleases)
 * and compares it against the running app version. Self-hosted installs that
 * are offline simply fail the fetch and nothing is shown.
 *
 * Throttling: at most one fetch per 1h (the last result is cached in
 * localStorage). Dismissal: the admin can skip a specific version; a newer one
 * will prompt again.
 *
 * Release availability: a release is only reported once its Docker image for the
 * tag actually exists on GHCR — the CI pipeline builds for ~1.5h after the
 * release is created, and without this check an admin would be prompted to
 * `docker pull` a tag that does not exist yet. Both probes are anonymous and
 * fail-safe (any error → nothing shown).
 */

import {debug} from '$lib/debug';

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
export const CHECK_INTERVAL_MS = 60 * 60 * 1000;
const FETCH_TIMEOUT_MS = 5000;
const LATEST_RELEASE_URL = 'https://api.github.com/repos/Librefolio/LibreFolio/releases/latest';
const GHCR_MANIFEST_URL = (tag: string) => `https://ghcr.io/v2/librefolio/librefolio/manifests/${tag}`;

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
 * Whether the Docker image for a tag exists on GHCR. The public manifest
 * endpoint answers anonymously; a release is only announced once its image is
 * actually pullable. Any failure (offline, 404 while CI is still building,
 * rate limit) → false: better silent than prompting for an unpullable tag.
 */
export async function isImagePublished(version: string, fetchFn: typeof fetch = fetch): Promise<boolean> {
    try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
        // The tag carries no "v" prefix (v1.1.0 release → image tag 1.1.0).
        const res = await fetchFn(GHCR_MANIFEST_URL(version), {
            method: 'HEAD',
            headers: {Accept: 'application/vnd.oci.image.index.v1+json'},
            signal: controller.signal,
        });
        clearTimeout(timer);
        return res.ok;
    } catch {
        return false;
    }
}

/**
 * Full flow: use the cached probe when fresh, otherwise probe now and cache.
 * Returns the release to prompt about, or null. A release is only returned once
 * its Docker image for that tag is actually published on GHCR (the CI pipeline
 * needs ~1.5h after the GitHub release appears — the image probe prevents
 * prompting for a tag that cannot be pulled yet).
 */
export async function checkForNewerRelease(currentVersion: string, fetchFn?: typeof fetch): Promise<NewerRelease | null> {
    let cache = readCache();
    if (isProbeDue(cache)) {
        const latest = await probeLatestRelease(fetchFn);
        debug.log('UpdateCheck', 'probe →', {current: currentVersion, latest: latest?.version ?? null, fresh: true});
        cache = {checkedAt: Date.now(), latest, dismissedVersion: cache?.dismissedVersion};
        writeCache(cache);
    } else {
        debug.log('UpdateCheck', 'cache fresh →', {current: currentVersion, latest: cache?.latest?.version ?? null, ageMinutes: Math.round((Date.now() - (cache?.checkedAt ?? 0)) / 60000)});
    }
    const candidate = shouldPrompt(cache, currentVersion).release;
    if (!candidate) return null;
    // Second gate: only announce what can actually be pulled (image published).
    if (!(await isImagePublished(candidate.version, fetchFn))) {
        debug.log('UpdateCheck', 'release found but image not yet published →', candidate.version);
        return null;
    }
    return candidate;
}
