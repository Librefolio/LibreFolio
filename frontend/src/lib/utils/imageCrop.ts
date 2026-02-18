/**
 * Image Crop Utilities
 *
 * Presets and helper functions for image cropping.
 */

// Re-export CropArea from svelte-easy-crop for type consistency
export type {CropArea} from 'svelte-easy-crop';
import type {CropArea} from 'svelte-easy-crop';

// =============================================================================
// TYPES
// =============================================================================

export interface ImagePreset {
    aspectRatio: number;      // 0 = free, 1 = square, 16/9, etc.
    outputWidth: number | null;
    outputHeight: number | null;
    outputFormat: 'png' | 'jpeg' | 'webp' | 'auto';
    outputQuality: number;    // 0-1
    titleKey: string;         // i18n key for modal title
}

export type PresetName = 'avatar' | 'broker-icon' | 'custom';

// =============================================================================
// PRESETS
// =============================================================================

export const IMAGE_PRESETS: Record<PresetName, ImagePreset> = {
    avatar: {
        aspectRatio: 1,           // 1:1 square
        outputWidth: 200,
        outputHeight: 200,
        outputFormat: 'png',
        outputQuality: 0.9,
        titleKey: 'uploads.editAvatar',
    },
    'broker-icon': {
        aspectRatio: 1,           // 1:1 square
        outputWidth: 64,
        outputHeight: 64,
        outputFormat: 'png',
        outputQuality: 0.9,
        titleKey: 'uploads.editBrokerIcon',
    },
    custom: {
        aspectRatio: 0,           // Free aspect ratio
        outputWidth: null,        // Keep original (max 2000)
        outputHeight: null,
        outputFormat: 'auto',     // Keep original format
        outputQuality: 0.85,
        titleKey: 'uploads.editImage',
    }
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Create an image element from a source URL
 */
export function createImage(url: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
        const image = new Image();
        image.addEventListener('load', () => resolve(image));
        image.addEventListener('error', (error) => reject(error));
        image.setAttribute('crossOrigin', 'anonymous');
        image.src = url;
    });
}

/**
 * Get the cropped image as a Blob
 */
export async function getCroppedImage(
    imageSrc: string,
    pixelCrop: CropArea,
    outputWidth: number | null = null,
    outputHeight: number | null = null,
    format: 'png' | 'jpeg' | 'webp' | 'auto' = 'png',
    quality: number = 0.9
): Promise<Blob> {
    const image = await createImage(imageSrc);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (!ctx) {
        throw new Error('No 2d context');
    }

    // Determine output dimensions
    let finalWidth = pixelCrop.width;
    let finalHeight = pixelCrop.height;

    if (outputWidth && outputHeight) {
        finalWidth = outputWidth;
        finalHeight = outputHeight;
    } else if (outputWidth) {
        // Scale proportionally
        const ratio = outputWidth / pixelCrop.width;
        finalWidth = outputWidth;
        finalHeight = Math.round(pixelCrop.height * ratio);
    } else if (outputHeight) {
        const ratio = outputHeight / pixelCrop.height;
        finalHeight = outputHeight;
        finalWidth = Math.round(pixelCrop.width * ratio);
    }

    // Limit max dimensions
    const maxDimension = 2000;
    if (finalWidth > maxDimension || finalHeight > maxDimension) {
        const scale = maxDimension / Math.max(finalWidth, finalHeight);
        finalWidth = Math.round(finalWidth * scale);
        finalHeight = Math.round(finalHeight * scale);
    }

    canvas.width = finalWidth;
    canvas.height = finalHeight;

    // Draw the cropped image
    ctx.drawImage(
        image,
        pixelCrop.x,
        pixelCrop.y,
        pixelCrop.width,
        pixelCrop.height,
        0,
        0,
        finalWidth,
        finalHeight
    );

    // Determine output MIME type
    let mimeType: string;
    if (format === 'auto') {
        // Try to detect from original, default to PNG
        mimeType = 'image/png';
    } else {
        mimeType = `image/${format}`;
    }

    return new Promise((resolve, reject) => {
        canvas.toBlob(
            (blob) => {
                if (blob) {
                    resolve(blob);
                } else {
                    reject(new Error('Canvas toBlob failed'));
                }
            },
            mimeType,
            quality
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

    return new File([blob], `${baseName}${ext}`, { type: blob.type });
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
export const SUPPORTED_IMAGE_TYPES = [
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif'
];

/**
 * Check if MIME type is supported for cropping
 */
export function isSupportedImageType(mimeType: string): boolean {
    return SUPPORTED_IMAGE_TYPES.includes(mimeType);
}
