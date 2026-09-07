/**
 * Image Crop Utilities
 *
 * Presets and helper functions for image cropping with cropperjs v2.
 */

import type Cropper from 'cropperjs';

// =============================================================================
// TYPES
// =============================================================================

export interface ImagePreset {
    aspectRatio: number; // 0 or NaN = free, 1 = square, 16/9, etc.
    outputWidth: number | null;
    outputHeight: number | null;
    outputFormat: 'png' | 'jpeg' | 'webp' | 'auto';
    outputQuality: number; // 0-1
    titleKey: string; // i18n key for modal title
}

export type PresetName = 'avatar' | 'broker-icon' | 'asset-icon' | 'custom';

// =============================================================================
// PRESETS
// =============================================================================

export const IMAGE_PRESETS: Record<PresetName, ImagePreset> = {
    avatar: {
        aspectRatio: 1, // 1:1 square
        outputWidth: 200,
        outputHeight: 200,
        outputFormat: 'png',
        outputQuality: 0.9,
        titleKey: 'uploads.editAvatar',
    },
    'broker-icon': {
        aspectRatio: 1, // 1:1 square
        outputWidth: 64,
        outputHeight: 64,
        outputFormat: 'png',
        outputQuality: 0.9,
        titleKey: 'uploads.editIcon',
    },
    'asset-icon': {
        aspectRatio: 1, // 1:1 square
        outputWidth: 256,
        outputHeight: 256,
        outputFormat: 'png',
        outputQuality: 0.9,
        titleKey: 'uploads.editIcon',
    },
    custom: {
        aspectRatio: 0, // Free aspect ratio (NaN in cropperjs)
        outputWidth: null, // User can set
        outputHeight: null,
        outputFormat: 'auto',
        outputQuality: 0.9,
        titleKey: 'uploads.editImage',
    },
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get cropped image from cropperjs v2 instance as Blob
 * Uses CropperSelection.$toCanvas() method
 */
export async function getCroppedImageFromCropper(cropper: Cropper, outputWidth: number | null = null, outputHeight: number | null = null, format: 'png' | 'jpeg' | 'webp' | 'auto' = 'png', quality: number = 0.9): Promise<Blob> {
    const selection = cropper.getCropperSelection();

    if (!selection) {
        throw new Error('No crop selection available');
    }

    // Build canvas options
    const canvasOptions: {width?: number; height?: number} = {};
    if (outputWidth) canvasOptions.width = outputWidth;
    if (outputHeight) canvasOptions.height = outputHeight;

    // Get cropped canvas from selection
    const canvas = await selection.$toCanvas(canvasOptions);

    if (!canvas) {
        throw new Error('Failed to get cropped canvas');
    }

    // Determine output MIME type
    const mimeType = format === 'auto' ? 'image/png' : `image/${format}`;

    return new Promise((resolve, reject) => {
        canvas.toBlob(
            (blob: Blob | null) => {
                if (blob) {
                    resolve(blob);
                } else {
                    reject(new Error('Canvas toBlob failed'));
                }
            },
            mimeType,
            quality,
        );
    });
}

/**
 * Convert a Blob to a File with a name
 */
export function blobToFile(blob: Blob, fileName: string): File {
    // Determine extension from MIME type
    const mimeToExt: Record<string, string> = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/webp': '.webp',
    };

    const ext = mimeToExt[blob.type] || '.png';
    const baseName = fileName.replace(/\.[^.]+$/, ''); // Remove existing extension

    return new File([blob], `${baseName}${ext}`, {type: blob.type});
}

/**
 * Check if a file is an image
 */
export function isImageFile(file: File): boolean {
    return file.type.startsWith('image/');
}
