/**
 * Upload Utilities
 *
 * Centralised file upload function to avoid duplicated FormData/axios patterns.
 */

import {axiosInstance} from '$lib/api';
import {get} from 'svelte/store';
import {_} from '$lib/i18n';

/**
 * Upload a file to the backend static uploads endpoint.
 *
 * @param file - The File or Blob to upload
 * @param description - Optional description metadata
 * @returns The URL of the uploaded file
 * @throws Error if upload fails or response has no URL
 */
export async function uploadFile(file: File, description?: string): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);
    if (description) {
        formData.append('description', description);
    }

    const response = await axiosInstance.post('/api/v1/uploads', formData);
    const url = response.data.file?.url || response.data.url;

    if (!url) {
        throw new Error('No URL in upload response');
    }

    return url;
}

/**
 * Upload a BRIM (Broker Report Import) file to a specific broker.
 *
 * @param file - The File to upload
 * @param brokerId - Target broker ID
 * @param pluginName - BRIM plugin name (e.g. "directa", "degiro")
 * @returns The upload response data
 * @throws Error if upload fails
 */
export async function uploadBrimFile(file: File, brokerId: number, pluginName: string): Promise<unknown> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axiosInstance.post(`/api/v1/brokers/import/${brokerId}/${pluginName}`, formData);

    return response.data;
}

/**
 * Format byte sizes into human-readable strings with i18n-translated units.
 *
 * Uses svelte-i18n translation keys: common.bytes, common.kilobytes, common.megabytes, common.gigabytes.
 * Works both inside and outside Svelte components via get() from svelte/store.
 *
 * @param bytes - Size in bytes
 * @returns Formatted string (e.g. "1.5 MB" in EN, "1.5 Mo" in FR)
 */
export function formatBytes(bytes: number): string {
    const t = get(_);
    const b = t('common.bytes') || 'B';
    const kb = t('common.kilobytes') || 'KB';
    const mb = t('common.megabytes') || 'MB';
    const gb = t('common.gigabytes') || 'GB';

    if (bytes === 0) return `0 ${b}`;
    if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} ${gb}`;
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} ${mb}`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} ${kb}`;
    return `${bytes} ${b}`;
}
