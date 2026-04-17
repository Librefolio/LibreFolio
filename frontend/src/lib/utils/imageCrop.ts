/**
 * Image Crop Utilities
 *
 * Presets and helper functions for image cropping with cropperjs v2.
 */

import type Cropper from 'cropperjs';

// =============================================================================
// TYPES
// =============================================================================

/**
 * Configuration for image editing, saved per-file for re-editing
 */
export interface ImageEditConfig {
    // Crop area
    cropX: number;
    cropY: number;
    cropWidth: number;
    cropHeight: number;

    // Transform
    rotation: number; // degrees
    scaleX: number; // 1 or -1 (flip H)
    scaleY: number; // 1 or -1 (flip V)

    // Output
    outputWidth: number | null;
    outputHeight: number | null;
    outputFormat: 'png' | 'jpeg' | 'webp';
    outputQuality: number; // 0-1

    // File name
    outputFileName: string;
}

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
 * Create ImageEditConfig from cropperjs v2 selection state
 */
export function createImageEditConfig(
    cropper: Cropper,
    fileName: string,
    outputWidth: number | null = null,
    outputHeight: number | null = null,
    outputFormat: 'png' | 'jpeg' | 'webp' = 'png',
    outputQuality: number = 0.9,
    rotation: number = 0,
    scaleX: number = 1,
    scaleY: number = 1,
): ImageEditConfig {
    const selection = cropper.getCropperSelection();

    return {
        cropX: selection?.x || 0,
        cropY: selection?.y || 0,
        cropWidth: selection?.width || 0,
        cropHeight: selection?.height || 0,
        rotation,
        scaleX,
        scaleY,
        outputWidth,
        outputHeight,
        outputFormat,
        outputQuality,
        outputFileName: fileName,
    };
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

/**
 * Get supported image MIME types
 */
export const SUPPORTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

/**
 * Check if MIME type is supported for cropping
 */
export function isSupportedImageType(mimeType: string): boolean {
    return SUPPORTED_IMAGE_TYPES.includes(mimeType);
}

/**
 * Get default output filename from original file
 */
export function getDefaultOutputFileName(originalName: string, format: 'png' | 'jpeg' | 'webp'): string {
    const baseName = originalName.replace(/\.[^.]+$/, '');
    const ext = format === 'jpeg' ? 'jpg' : format;
    return `${baseName}.${ext}`;
}
