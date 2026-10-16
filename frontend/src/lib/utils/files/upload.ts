/**
 * Upload Utilities
 *
 * Centralised file upload function to avoid duplicated FormData/axios patterns.
 */

import {axiosInstance, zodiosApi} from '$lib/api';
import {get} from 'svelte/store';
import {_} from '$lib/i18n';
import {formatFixed} from '$lib/utils/core/formatFixed';
import {uiLocale} from '$lib/stores/app/uiLocale';
import type {UploadScope, UploadedFile} from '$lib/types/files';

/**
 * Upload a file to the backend static uploads endpoint.
 *
 * @param file - The File or Blob to upload
 * @param description - Optional description metadata
 * @param scope - Who sees the file: `common` (the image pickers), `personal` (the Files page). Without it, the backend
 *   decides: images common, the rest personal
 * @returns The URL of the uploaded file
 * @throws Error if upload fails or response has no URL
 */
export async function uploadFile(file: File, description?: string, scope?: UploadScope): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);
    if (description) {
        formData.append('description', description);
    }
    if (scope) {
        formData.append('scope', scope);
    }

    const response = await axiosInstance.post('/api/v1/uploads', formData);
    const url = response.data.file?.url || response.data.url;

    if (!url) {
        throw new Error('No URL in upload response');
    }

    return url;
}

/**
 * Change who sees an uploaded file. Only its uploader and the admins may: the backend answers 403 or 404 otherwise.
 *
 * @returns The file as the backend now describes it
 */
export async function setUploadScope(fileId: string, scope: UploadScope): Promise<UploadedFile> {
    return (await zodiosApi.update_file_api_v1_uploads__file_id__patch({scope}, {params: {file_id: fileId}})) as UploadedFile;
}

/**
 * Format byte sizes into human-readable strings with i18n-translated units.
 *
 * Uses svelte-i18n translation keys: common.bytes, common.kilobytes, common.megabytes, common.gigabytes.
 * Works both inside and outside Svelte components via get() from svelte/store.
 *
 * `get()` is a one-off read that no effect tracks: a template that must follow a language change passes its own
 * `$t`, which the template does track.
 *
 * @param bytes - Size in bytes
 * @param translate - The translator to read the units with; defaults to the current one
 * @param locale - The locale to write the number in; defaults to the interface locale
 * @returns Formatted string (e.g. "1.5 MB" in EN, "1,5 Mo" in FR)
 */
export function formatBytes(bytes: number, translate: (key: string) => string = get(_), locale: string = uiLocale()): string {
    const t = translate;
    const b = t('common.bytes') || 'B';
    const kb = t('common.kilobytes') || 'KB';
    const mb = t('common.megabytes') || 'MB';
    const gb = t('common.gigabytes') || 'GB';

    if (bytes === 0) return `0 ${b}`;
    if (bytes >= 1024 * 1024 * 1024) return `${formatFixed(bytes / (1024 * 1024 * 1024), 1, {locale})} ${gb}`;
    if (bytes >= 1024 * 1024) return `${formatFixed(bytes / (1024 * 1024), 1, {locale})} ${mb}`;
    if (bytes >= 1024) return `${formatFixed(bytes / 1024, 1, {locale})} ${kb}`;
    return `${bytes} ${b}`;
}
