/**
 * Download helper for the ``/api/v1/backup/*`` snapshot endpoints.
 *
 * These endpoints return a streaming CSV or JSON response with a
 * ``Content-Disposition: attachment; filename=...`` header. The raw payload
 * is not JSON-shaped (Zodios can parse the body via ``z.unknown()`` but the
 * ``Content-Disposition`` would be lost), and we want the browser's native
 * "save as" flow with the server-picked filename.
 *
 * Strategy:
 *   1. Go through the shared ``axiosInstance`` so we inherit:
 *      - cookie-based auth (``withCredentials: true``),
 *      - 401 redirect interceptor,
 *      - ``Accept-Language`` header.
 *   2. Request ``responseType: 'blob'`` so the response body is binary-safe
 *      regardless of format.
 *   3. Parse ``Content-Disposition`` for the filename, with a sensible
 *      fallback built from the params.
 *   4. Trigger a programmatic download via an ephemeral ``<a>`` element
 *      + ``URL.createObjectURL``; revoke the URL in a microtask to free
 *      memory.
 *
 * Rationale for NOT using ``zodiosApi.<alias>()`` directly: the generated
 * client returns the parsed response *body* only, dropping the HTTP
 * headers we need for the filename. Using ``axiosInstance`` keeps the
 * single auth/error-handling pipeline while exposing the full response.
 */

import {axiosInstance} from '$lib/api';

export type BackupKind = 'prices' | 'events';
export type BackupFormat = 'csv' | 'json';

const FILENAME_PATTERN = /filename\*?=(?:UTF-8'')?"?([^"\n;]+)"?/i;

function extractFilename(contentDisposition: string | undefined, fallback: string): string {
    if (!contentDisposition) return fallback;
    const match = FILENAME_PATTERN.exec(contentDisposition);
    if (!match) return fallback;
    try {
        return decodeURIComponent(match[1]);
    } catch {
        return match[1] || fallback;
    }
}

function triggerBrowserDownload(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    // Some browsers (Firefox) require the element to be in the DOM.
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Free the blob in the next microtask.
    queueMicrotask(() => URL.revokeObjectURL(url));
}

/**
 * Download a per-asset backup snapshot (prices or events) and trigger
 * the native browser "save as" flow.
 *
 * @throws AxiosError on HTTP failure (401 handled by interceptor).
 */
export async function downloadAssetBackup(assetId: number, kind: BackupKind, format: BackupFormat): Promise<void> {
    await downloadBackup(`/api/v1/backup/asset/${assetId}/${kind}`, format, `${kind}_asset-${assetId}`);
}

/**
 * Download an FX pair's rates snapshot (FB-30) and trigger the native browser "save as" flow. The pair is asked in the
 * direction the page shows it; the server stores it in its own order and says so in the JSON envelope (`inverted`).
 *
 * @throws AxiosError on HTTP failure (401 handled by interceptor).
 */
export async function downloadFxRatesBackup(base: string, quote: string, format: BackupFormat): Promise<void> {
    await downloadBackup(`/api/v1/backup/fx/${encodeURIComponent(base)}/${encodeURIComponent(quote)}/rates`, format, `rates_fx-${base}-${quote}`);
}

async function downloadBackup(url: string, format: BackupFormat, fallbackStem: string): Promise<void> {
    const response = await axiosInstance.get<Blob>(url, {
        params: {format},
        responseType: 'blob',
    });
    const today = new Date().toISOString().slice(0, 10);
    const fallback = `${fallbackStem}_${today}.${format}`;
    const filename = extractFilename(response.headers?.['content-disposition'] as string | undefined, fallback);
    triggerBrowserDownload(response.data, filename);
}
