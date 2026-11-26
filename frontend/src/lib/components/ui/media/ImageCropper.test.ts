// @vitest-environment jsdom
/**
 * ImageCropper — its six controls are standard icon Buttons (85 BTN-2b).
 *
 * Zoom out, zoom in, rotate left, rotate right, flip horizontal, flip vertical: each named from the catalogue (the
 * rotations by `uploads.rotateLeft` / `rotateRight`, new keys), `dense` (they sit side by side over the canvas), with no
 * native title. The two flips are toggles: `aria-pressed`, false until a flip. The flip itself needs the cropper's image,
 * which jsdom never loads (cropperjs paints a canvas): mounted with no image source, the cropper never starts, and the
 * toggled state is the E2E's (`image-crop` B3).
 */
import {beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';
import {_} from 'svelte-i18n';
import {render, screen, setupI18n} from '$test/component';
import ImageCropper from './ImageCropper.svelte';

beforeAll(async () => {
    await setupI18n();
});

const CONTROLS = [
    ['cropper-zoom-out', 'uploads.zoomOut'],
    ['cropper-zoom-in', 'uploads.zoomIn'],
    ['cropper-rotate-left', 'uploads.rotateLeft'],
    ['cropper-rotate-right', 'uploads.rotateRight'],
    ['cropper-flip-h', 'uploads.flipHorizontal'],
    ['cropper-flip-v', 'uploads.flipVertical'],
] as const;

describe('ImageCropper — the six controls (85 BTN-2b)', () => {
    it.each(CONTROLS)('%s is a Button named %s, dense, with no title', (testId, key) => {
        render(ImageCropper, {props: {imageSrc: ''}});
        const button = screen.getByTestId(testId);
        const name = get(_)(key);
        expect(name, `${key} is in the catalogue`).not.toBe(key);
        expect(button.tagName).toBe('BUTTON');
        expect(button).toHaveAttribute('aria-label', name);
        expect(button.hasAttribute('title')).toBe(false);
        expect(button.classList.contains('lf-btn-dense')).toBe(true);
    });

    it('the six names are six different names', () => {
        render(ImageCropper, {props: {imageSrc: ''}});
        const names = CONTROLS.map(([testId]) => screen.getByTestId(testId).getAttribute('aria-label'));
        expect(new Set(names).size).toBe(CONTROLS.length);
    });

    it('the flips are toggles, off at the start; zoom and rotate are plain buttons', () => {
        render(ImageCropper, {props: {imageSrc: ''}});
        expect(screen.getByTestId('cropper-flip-h')).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId('cropper-flip-v')).toHaveAttribute('aria-pressed', 'false');
        for (const testId of ['cropper-zoom-out', 'cropper-zoom-in', 'cropper-rotate-left', 'cropper-rotate-right']) {
            expect(screen.getByTestId(testId).hasAttribute('aria-pressed'), testId).toBe(false);
        }
    });

    it('without the rotate controls, neither the rotations nor the flips are drawn', () => {
        render(ImageCropper, {props: {imageSrc: '', showRotateControls: false}});
        for (const testId of ['cropper-rotate-left', 'cropper-rotate-right', 'cropper-flip-h', 'cropper-flip-v']) {
            expect(screen.queryByTestId(testId), testId).toBeNull();
        }
        expect(screen.getByTestId('cropper-zoom-in')).toBeInTheDocument();
    });
});
