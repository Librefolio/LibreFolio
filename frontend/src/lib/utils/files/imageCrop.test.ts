/**
 * imageCrop — unit tests
 *
 * The presets, file-naming and MIME rules behind the image editor. Everything
 * here except `getCroppedImageFromCropper` is a pure function of its arguments;
 * that one needs a cropper and a canvas, so the tests below hand it a fake that
 * records what it was asked for. The fake is not a stand-in for cropperjs — it
 * is the *contract* this module relies on: `getCropperSelection()`,
 * `$toCanvas(options)` and `canvas.toBlob(cb, mime, quality)`. If cropperjs
 * ever changes one of those three, these tests are the ones that should notice.
 *
 * The preset titles are asserted as **i18n keys**, never as text: the app ships
 * in four languages and the sentence differs in each, while the key does not.
 */
import {describe, expect, it} from 'vitest';
import type Cropper from 'cropperjs';

import {blobToFile, getCroppedImageFromCropper, IMAGE_PRESETS, isImageFile, type PresetName} from './imageCrop';
import en from '$lib/i18n/en.json';
import itLocale from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

// =============================================================================
//  A fake cropper — the three calls this module makes, and nothing else
// =============================================================================

interface FakeSelection {
    x?: number;
    y?: number;
    width?: number;
    height?: number;
}

interface CanvasCall {
    mime: string;
    quality: number;
}

function fakeCropper(opts: {selection?: FakeSelection | null; canvas?: 'ok' | 'null'; blob?: Blob | null} = {}) {
    const {selection = {x: 10, y: 20, width: 300, height: 150}, canvas = 'ok', blob = new Blob(['bytes'], {type: 'image/png'})} = opts;
    const canvasOptionsSeen: Array<Record<string, unknown>> = [];
    const toBlobCalls: CanvasCall[] = [];

    const fakeCanvas = {
        toBlob(cb: (b: Blob | null) => void, mime: string, quality: number) {
            toBlobCalls.push({mime, quality});
            cb(blob);
        },
    };

    const sel =
        selection === null
            ? null
            : {
                  ...selection,
                  $toCanvas: async (options: Record<string, unknown>) => {
                      canvasOptionsSeen.push(options);
                      return canvas === 'ok' ? fakeCanvas : null;
                  },
              };

    const cropper = {getCropperSelection: () => sel} as unknown as Cropper;
    return {cropper, canvasOptionsSeen, toBlobCalls};
}

// =============================================================================
//  Presets
// =============================================================================

describe('IMAGE_PRESETS', () => {
    const names: PresetName[] = ['avatar', 'broker-icon', 'asset-icon', 'custom'];

    it('covers exactly the four preset names the type declares', () => {
        expect(Object.keys(IMAGE_PRESETS).sort()).toEqual([...names].sort());
    });

    it.each(names)('names a title key that every locale defines, for %s', (name) => {
        const key = IMAGE_PRESETS[name].titleKey;
        const [namespace, leaf] = key.split('.');
        // A preset pointing at a missing key would render the raw key to the
        // user. Only *existence* is asserted — the sentence differs per locale.
        for (const [locale, bundle] of [
            ['en', en],
            ['it', itLocale],
            ['fr', fr],
            ['es', es],
        ] as const) {
            const value = (bundle as Record<string, Record<string, unknown>>)[namespace]?.[leaf];
            expect(typeof value, `${locale} is missing ${key}`).toBe('string');
        }
    });

    it.each(['avatar', 'broker-icon', 'asset-icon'] as const)('locks %s to a square with a fixed output size', (name) => {
        const preset = IMAGE_PRESETS[name];
        expect(preset.aspectRatio).toBe(1);
        expect(preset.outputWidth).toBe(preset.outputHeight);
        expect(preset.outputWidth).toBeGreaterThan(0);
        expect(preset.outputFormat).toBe('png');
    });

    it('leaves the custom preset free in shape, size and format', () => {
        // `aspectRatio: 0` is what the modal turns into cropperjs' NaN, and a
        // null size is what lets the user type one. Both are load-bearing.
        expect(IMAGE_PRESETS.custom).toMatchObject({aspectRatio: 0, outputWidth: null, outputHeight: null, outputFormat: 'auto'});
    });

    it.each(names)('keeps the quality of %s inside the 0-1 range toBlob expects', (name) => {
        const quality = IMAGE_PRESETS[name].outputQuality;
        expect(quality).toBeGreaterThan(0);
        expect(quality).toBeLessThanOrEqual(1);
    });
});

// =============================================================================
//  getCroppedImageFromCropper
// =============================================================================

describe('getCroppedImageFromCropper', () => {
    it('resolves with the blob the canvas produced', async () => {
        const blob = new Blob(['bytes'], {type: 'image/png'});
        const {cropper} = fakeCropper({blob});

        await expect(getCroppedImageFromCropper(cropper)).resolves.toBe(blob);
    });

    it('rejects when there is no selection to crop', async () => {
        const {cropper} = fakeCropper({selection: null});

        await expect(getCroppedImageFromCropper(cropper)).rejects.toThrow('No crop selection available');
    });

    it('rejects when the selection cannot produce a canvas', async () => {
        const {cropper} = fakeCropper({canvas: 'null'});

        await expect(getCroppedImageFromCropper(cropper)).rejects.toThrow('Failed to get cropped canvas');
    });

    it('rejects when the canvas hands back no blob', async () => {
        const {cropper} = fakeCropper({blob: null});

        await expect(getCroppedImageFromCropper(cropper)).rejects.toThrow('Canvas toBlob failed');
    });

    describe('the canvas options', () => {
        it('are empty when no output size is asked for', async () => {
            const {cropper, canvasOptionsSeen} = fakeCropper();

            await getCroppedImageFromCropper(cropper);

            expect(canvasOptionsSeen).toEqual([{}]);
        });

        it('carry both dimensions when both are given', async () => {
            const {cropper, canvasOptionsSeen} = fakeCropper();

            await getCroppedImageFromCropper(cropper, 200, 120);

            expect(canvasOptionsSeen).toEqual([{width: 200, height: 120}]);
        });

        it.each([
            ['width only', 200, null, {width: 200}],
            ['height only', null, 120, {height: 120}],
        ] as const)('carry %s when the other side is null', async (_label, w, h, expected) => {
            const {cropper, canvasOptionsSeen} = fakeCropper();

            await getCroppedImageFromCropper(cropper, w, h);

            expect(canvasOptionsSeen).toEqual([expected]);
        });

        it('drop a zero dimension instead of asking for a zero-pixel canvas', async () => {
            // The guard is truthiness, not `!= null`. Passing `width: 0` to
            // `$toCanvas` would ask for an empty image; dropping it means the
            // canvas keeps the selection's own size.
            const {cropper, canvasOptionsSeen} = fakeCropper();

            await getCroppedImageFromCropper(cropper, 0, 0);

            expect(canvasOptionsSeen).toEqual([{}]);
        });
    });

    describe('the output MIME type', () => {
        it.each([
            ['png', 'image/png'],
            ['jpeg', 'image/jpeg'],
            ['webp', 'image/webp'],
            ['auto', 'image/png'],
        ] as const)('is %s → %s', async (format, mime) => {
            const {cropper, toBlobCalls} = fakeCropper();

            await getCroppedImageFromCropper(cropper, null, null, format);

            expect(toBlobCalls[0].mime).toBe(mime);
        });
    });

    it('forwards the quality, and defaults it to 0.9', async () => {
        const explicit = fakeCropper();
        await getCroppedImageFromCropper(explicit.cropper, null, null, 'jpeg', 0.42);
        expect(explicit.toBlobCalls[0].quality).toBe(0.42);

        const implicit = fakeCropper();
        await getCroppedImageFromCropper(implicit.cropper);
        expect(implicit.toBlobCalls[0]).toEqual({mime: 'image/png', quality: 0.9});
    });
});

// =============================================================================
//  blobToFile
// =============================================================================

describe('blobToFile', () => {
    it.each([
        ['image/png', '.png'],
        ['image/jpeg', '.jpg'],
        ['image/webp', '.webp'],
    ] as const)('names a %s blob with %s', (type, ext) => {
        const file = blobToFile(new Blob(['x'], {type}), 'holiday.heic');

        expect(file.name).toBe(`holiday${ext}`);
        expect(file.type).toBe(type);
    });

    it('keeps the original name when it has no extension', () => {
        expect(blobToFile(new Blob(['x'], {type: 'image/png'}), 'avatar').name).toBe('avatar.png');
    });

    it('strips only the last extension', () => {
        expect(blobToFile(new Blob(['x'], {type: 'image/jpeg'}), 'my.photo.v2.png').name).toBe('my.photo.v2.jpg');
    });

    it('falls back to .png for a MIME type it has no extension for', () => {
        // Note the asymmetry this pins: the *name* becomes .png while the
        // File keeps the blob's own MIME type. See the note in the test report.
        const file = blobToFile(new Blob(['x'], {type: 'image/gif'}), 'anim.gif');

        expect(file.name).toBe('anim.png');
        expect(file.type).toBe('image/gif');
    });

    it('falls back to .png for a blob with no type at all', () => {
        expect(blobToFile(new Blob(['x']), 'anon').name).toBe('anon.png');
    });

    it('preserves the bytes', async () => {
        const file = blobToFile(new Blob(['hello'], {type: 'image/png'}), 'a.png');

        expect(await file.text()).toBe('hello');
    });
});

// =============================================================================
//  MIME guards
// =============================================================================

describe('isImageFile', () => {
    it.each(['image/png', 'image/jpeg', 'image/gif', 'image/svg+xml', 'image/heic'])('accepts %s', (type) => {
        expect(isImageFile(new File(['x'], 'f', {type}))).toBe(true);
    });

    it.each(['application/pdf', 'text/csv', 'video/mp4', ''])('rejects %s', (type) => {
        expect(isImageFile(new File(['x'], 'f', {type}))).toBe(false);
    });

    it('does not accept a type that merely contains "image/"', () => {
        expect(isImageFile(new File(['x'], 'f', {type: 'application/x-image/png'}))).toBe(false);
    });
});
