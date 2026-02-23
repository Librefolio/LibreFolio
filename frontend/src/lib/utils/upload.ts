/**
 * Upload Utilities
 *
 * Centralised file upload function to avoid duplicated FormData/axios patterns.
 */

import {axiosInstance} from '$lib/api';

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
export async function uploadBrimFile(
    file: File,
    brokerId: number,
    pluginName: string,
): Promise<unknown> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axiosInstance.post(
        `/api/v1/brokers/import/${brokerId}/${pluginName}`,
        formData,
    );

    return response.data;
}

/**
 * Format byte sizes into human-readable strings.
 *
 * @param bytes - Size in bytes
 * @returns Formatted string (e.g. "1.5 MB")
 */
export function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

