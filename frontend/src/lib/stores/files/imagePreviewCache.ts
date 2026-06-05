/**
 * imagePreviewCache — Client-side cache for image preview objectUrls.
 *
 * Stores the highest-resolution fetched objectUrl per fileId.
 * When a lower resolution is requested, the cached version is reused
 * and CSS object-fit handles the visual downscaling.
 * objectUrls are held for page lifetime (~2MB for 100 images — acceptable).
 *
 * @module stores/files/imagePreviewCache
 */

interface CachedPreview {
    /** objectUrl created from blob */
    objectUrl: string;
    /** The pixel width of the fetched image (e.g. 120 for "120x120") */
    maxWidth: number;
}

const cache = new Map<string, CachedPreview>();

/**
 * Register a fetched image in the cache.
 * Only updates if the new resolution is higher than what's stored.
 */
export function cachePreview(fileId: string, objectUrl: string, width: number): void {
    const existing = cache.get(fileId);
    if (!existing || width > existing.maxWidth) {
        if (existing) URL.revokeObjectURL(existing.objectUrl);
        cache.set(fileId, {objectUrl, maxWidth: width});
    }
}

/**
 * Look up a cached preview. Returns objectUrl if cached width >= requestedWidth, else null.
 */
export function getCachedPreview(fileId: string, requestedWidth: number): string | null {
    const cached = cache.get(fileId);
    if (cached && cached.maxWidth >= requestedWidth) return cached.objectUrl;
    return null;
}

/**
 * Parse pixel width from a preview URL query param like "?img_preview=120x120".
 * Returns 0 if parsing fails.
 */
export function parsePreviewWidth(url: string): number {
    const match = url.match(/img_preview=(\d+)x/);
    return match ? parseInt(match[1], 10) : 0;
}

/**
 * Extract fileId (UUID) from a preview URL like /api/v1/uploads/file/{uuid}?img_preview=WxH.
 * Returns null if the URL doesn't match the expected pattern.
 */
export function extractFileIdFromUrl(url: string): string | null {
    const match = url.match(/\/api\/v1\/uploads\/file\/([a-f0-9-]+)/);
    return match ? match[1] : null;
}

/** Free all blob memory. Call on logout. */
export function clearImagePreviewCache(): void {
    for (const entry of cache.values()) URL.revokeObjectURL(entry.objectUrl);
    cache.clear();
}
