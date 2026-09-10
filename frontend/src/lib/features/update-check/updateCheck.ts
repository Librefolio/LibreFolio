/**
 * Update check (F14) — client-side "new stable release available" probe.
 *
 * After login, an admin's browser fetches the latest *stable* release from the
 * GitHub Releases API (`/releases/latest` never returns drafts or prereleases)
 * and compares it against the running app version. Self-hosted installs that
 * are offline simply fail the fetch and nothing is shown.
 *
 * Automatic release metadata probes are cached in localStorage for 1h.
 * Explicit checks bypass that cache. Dismissal suppresses automatic prompts
 * for a specific version; a newer one will prompt again.
 *
 * Release availability: a release is only reported once its Docker image for the
 * tag actually exists on GHCR — the CI pipeline builds for ~1.5h after the
 * release is created, and without this check an admin would be prompted to
 * `docker pull` a tag that does not exist yet. The same-origin backend performs
 * GHCR's anonymous token handshake because the registry does not expose that
 * flow to browsers through CORS. Both probes fail closed: automatic errors stay
 * silent; manual checks report them.
 */

import {zodiosApi} from '$lib/api';
import {debug} from '$lib/debug';

export interface NewerRelease {
    /** Tag without the leading "v", e.g. "0.11.0". */
    version: string;
    /** Exact tag returned by GitHub; absent in older cached results. */
    tag?: string;
    /** Release page URL on GitHub. */
    url: string;
    /** Release display name (may be empty). */
    name: string;
}

type ProbeStatus = 'success' | 'no-release' | 'error';
type CheckFailure = 'invalid-current-version' | 'check-failed' | 'release-request-failed' | 'invalid-release' | 'image-auth-request-failed' | 'image-request-failed';

export interface ImageProbeResult {
    status: 'published' | 'pending' | 'error';
    reason?: 'image-auth-request-failed' | 'image-request-failed' | null;
}

export type ImageProbe = (version: string) => Promise<ImageProbeResult>;

export interface UpdateCheckResult {
    status: 'up-to-date' | 'update-available' | 'dismissed' | 'image-pending' | 'no-release' | 'error';
    latest: NewerRelease | null;
    source: 'network' | 'cache' | 'none';
    checkedAt: number | null;
    reason?: CheckFailure;
}

interface UpdateCheckCache {
    checkedAt: number;
    latest: NewerRelease | null;
    dismissedVersion?: string;
    probeStatus?: ProbeStatus;
    reason?: CheckFailure;
}

const STORAGE_KEY = 'librefolio-update-check';
export const CHECK_INTERVAL_MS = 60 * 60 * 1000;
const FETCH_TIMEOUT_MS = 5000;
const LATEST_RELEASE_URL = 'https://api.github.com/repos/Librefolio/LibreFolio/releases/latest';

function parseVersion(value: string): number[] | null {
    const match = value.trim().match(/^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-[0-9a-z-]+(?:\.[0-9a-z-]+)*)?(?:\+[0-9a-z-]+(?:\.[0-9a-z-]+)*)?$/i);
    if (!match) return null;
    const parts = match.slice(1, 4).map((part) => Number(part ?? 0));
    return parts.every(Number.isSafeInteger) ? parts : null;
}

/** Compare base versions, retaining the existing same-base nightly/prerelease policy. Invalid input returns NaN. */
export function compareVersions(a: string, b: string): number {
    const pa = parseVersion(a);
    const pb = parseVersion(b);
    if (!pa || !pb) return Number.NaN;
    for (let i = 0; i < 3; i++) {
        const diff = pa[i] - pb[i];
        if (diff !== 0) return diff < 0 ? -1 : 1;
    }
    return 0;
}

function isStableVersion(value: string): boolean {
    return /^v?\d+\.\d+\.\d+$/i.test(value) && parseVersion(value) !== null;
}

function isRelease(value: unknown): value is NewerRelease {
    if (!value || typeof value !== 'object') return false;
    const release = value as NewerRelease;
    return (
        typeof release.version === 'string' &&
        isStableVersion(release.version) &&
        typeof release.url === 'string' &&
        release.url.trim().length > 0 &&
        typeof release.name === 'string' &&
        (release.tag === undefined || (typeof release.tag === 'string' && isStableVersion(release.tag) && compareVersions(release.tag, release.version) === 0))
    );
}

export function readCache(storage?: Pick<Storage, 'getItem'>): UpdateCheckCache | null {
    try {
        const raw = (storage ?? localStorage).getItem(STORAGE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw) as UpdateCheckCache;
        if (!Number.isFinite(parsed?.checkedAt) || parsed.checkedAt < 0) return null;
        if (parsed.latest !== null && !isRelease(parsed.latest)) return null;
        if (parsed.dismissedVersion !== undefined && typeof parsed.dismissedVersion !== 'string') return null;
        if (parsed.probeStatus !== undefined && !['success', 'no-release', 'error'].includes(parsed.probeStatus)) return null;
        if (parsed.probeStatus === 'success' && !parsed.latest) return null;
        if ((parsed.probeStatus === 'error' || parsed.probeStatus === 'no-release') && parsed.latest) return null;
        return parsed;
    } catch {
        return null;
    }
}

export function writeCache(cache: UpdateCheckCache, storage?: Pick<Storage, 'setItem'>): void {
    try {
        (storage ?? localStorage).setItem(STORAGE_KEY, JSON.stringify(cache));
    } catch {
        // storage full/blocked — the check simply runs again next login
    }
}

export function dismissVersion(version: string, storage?: Pick<Storage, 'getItem' | 'setItem'>): void {
    const cache = readCache(storage) ?? {checkedAt: 0, latest: null};
    writeCache({...cache, dismissedVersion: version}, storage);
}

/** True when the cached/probed release should be shown to the admin. */
export function shouldPrompt(cache: UpdateCheckCache | null, currentVersion: string): {prompt: boolean; release: NewerRelease | null} {
    const latest = cache?.latest ?? null;
    if (!latest) return {prompt: false, release: null};
    const comparison = compareVersions(latest.version, currentVersion);
    if (!Number.isFinite(comparison) || comparison <= 0) return {prompt: false, release: null};
    if (cache?.dismissedVersion && compareVersions(cache.dismissedVersion, latest.version) >= 0) return {prompt: false, release: null};
    return {prompt: true, release: latest};
}

/** Whether a fresh network probe is due (never checked or at least one hour old). */
export function isProbeDue(cache: UpdateCheckCache | null, now = Date.now()): boolean {
    return !cache || !Number.isFinite(cache.checkedAt) || cache.checkedAt <= 0 || cache.checkedAt > now || now - cache.checkedAt >= CHECK_INTERVAL_MS;
}

async function probeRelease(fetchFn: typeof fetch = fetch): Promise<Pick<UpdateCheckCache, 'latest' | 'probeStatus' | 'reason'>> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
        const res = await fetchFn(LATEST_RELEASE_URL, {
            headers: {Accept: 'application/vnd.github+json'},
            signal: controller.signal,
            cache: 'no-store',
        });
        if (res.status === 404) return {latest: null, probeStatus: 'no-release'};
        if (!res.ok) return {latest: null, probeStatus: 'error', reason: 'release-request-failed'};
        const data = (await res.json()) as {tag_name?: unknown; html_url?: unknown; name?: unknown; draft?: unknown; prerelease?: unknown} | null;
        if (!data || typeof data.tag_name !== 'string' || (data.draft !== undefined && data.draft !== false) || (data.prerelease !== undefined && data.prerelease !== false)) {
            return {latest: null, probeStatus: 'error', reason: 'invalid-release'};
        }
        const latest = {version: data.tag_name.replace(/^v/i, ''), tag: data.tag_name, url: data.html_url, name: data.name ?? ''};
        if (!isRelease(latest)) return {latest: null, probeStatus: 'error', reason: 'invalid-release'};
        return {latest, probeStatus: 'success'};
    } catch {
        return {latest: null, probeStatus: 'error', reason: 'release-request-failed'};
    } finally {
        clearTimeout(timer);
    }
}

/** Compatibility seam for callers that only need a successfully detected release. */
export async function probeLatestRelease(fetchFn: typeof fetch = fetch): Promise<NewerRelease | null> {
    return (await probeRelease(fetchFn)).latest;
}

/**
 * Keep the image gate fail-closed. The backend distinguishes public-token
 * failures from manifest failures; either remains an error, never "up to date".
 */
async function probeImageWithApi(version: string): Promise<ImageProbeResult> {
    return zodiosApi.get_container_image_status_api_v1_system_container_image_status_get({
        queries: {tag: version},
    });
}

async function probeImage(version: string, imageProbe: ImageProbe = probeImageWithApi): Promise<'published' | 'pending' | 'image-auth-request-failed' | 'image-request-failed'> {
    try {
        const result = await imageProbe(version);
        if (result.status === 'published' || result.status === 'pending') return result.status;
        return result.reason === 'image-auth-request-failed' ? result.reason : 'image-request-failed';
    } catch {
        return 'image-request-failed';
    }
}

export async function isImagePublished(version: string, imageProbe?: ImageProbe): Promise<boolean> {
    return (await probeImage(version, imageProbe)) === 'published';
}

/**
 * Shared automatic/manual flow. Manual checks force a fresh probe and may
 * ignore prompt dismissal, without changing the stable channel or image gate.
 */
export async function checkForUpdates(currentVersion: string, options: {force?: boolean; ignoreDismissed?: boolean} = {}, fetchFn?: typeof fetch, imageProbe?: ImageProbe): Promise<UpdateCheckResult> {
    if (!parseVersion(currentVersion)) {
        return {status: 'error', latest: null, source: 'none', checkedAt: null, reason: 'invalid-current-version'};
    }
    let cache = readCache();
    let source: UpdateCheckResult['source'] = 'cache';
    if (!cache || options.force || isProbeDue(cache)) {
        const probe = await probeRelease(fetchFn);
        cache = {checkedAt: Date.now(), ...probe, dismissedVersion: cache?.dismissedVersion};
        writeCache(cache);
        source = 'network';
    }
    const details = {latest: cache.latest, source, checkedAt: cache.checkedAt};
    debug.log('UpdateCheck', 'release check', {current: currentVersion, latest: cache.latest?.version ?? null, source, probeStatus: cache.probeStatus});
    if (!cache.latest) {
        if (cache.probeStatus === 'no-release') return {...details, status: 'no-release'};
        // Older caches stored every failed/absent result as null.
        return {...details, status: 'error', reason: cache.reason ?? 'release-request-failed'};
    }
    if (compareVersions(cache.latest.version, currentVersion) <= 0) return {...details, status: 'up-to-date'};
    if (!options.ignoreDismissed && !shouldPrompt(cache, currentVersion).prompt) return {...details, status: 'dismissed'};
    const image = await probeImage(cache.latest.version, imageProbe);
    if (image === 'pending') return {...details, status: 'image-pending'};
    if (image !== 'published') return {...details, status: 'error', reason: image};
    return {...details, status: 'update-available'};
}

/** Automatic login checks stay silent unless an undismissed, pullable update exists. */
export async function checkForNewerRelease(currentVersion: string, fetchFn?: typeof fetch, imageProbe?: ImageProbe): Promise<NewerRelease | null> {
    const result = await checkForUpdates(currentVersion, {}, fetchFn, imageProbe);
    return result.status === 'update-available' ? result.latest : null;
}
