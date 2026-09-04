// @vitest-environment jsdom
/**
 * ImageEditModal — component test (Vitest + jsdom).
 *
 * This modal wraps a canvas cropper (`cropperjs` v2, a Web Component that paints to
 * a `<canvas>`). In jsdom the wrapped image never loads and the canvas never paints,
 * so the cropper never reports ready. The modal deliberately gates its whole editing
 * surface behind that readiness — `editReady` only flips ~500 ms after the cropper's
 * first change event (see the `handleCropperChange` init dance) — which means the
 * output-size maths, quality/preset/aspect handlers, the crop→upload flow and the
 * discard-changes dialog are all unreachable without a real cropper. Those live in
 * the `image-crop` E2E suite, where a browser actually paints the canvas.
 *
 * What a component test CAN pin down here, and does below, is everything the modal
 * derives and decides *before* the cropper is in play: the not-ready gate the user
 * sees, the filename/format it infers from the incoming File, which preset rows it
 * offers, and the two exits (cancel / close) that stay live throughout. Those are the
 * parts a translation change or a refactor could silently break, and none of them
 * needs the canvas.
 *
 * The upload endpoint is mocked purely so importing the module never reaches the
 * network; the crop→upload path that would call it is out of reach here anyway.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/utils/files/upload', () => ({uploadFile: vi.fn().mockResolvedValue('/uploads/cropped.png')}));

import {fireEvent, render, screen, setupI18n} from '$test/component';
import type {PresetName} from '$lib/utils/files/imageCrop';
import ImageEditModal from './ImageEditModal.svelte';

function imageFile(name: string, type = 'image/png'): File {
    return new File(['binary'], name, {type});
}

function mount(props: {file?: File | null; open?: boolean; preset?: PresetName; allowPresetChange?: boolean; uploadOnComplete?: boolean} = {}) {
    const complete = vi.fn();
    const cancel = vi.fn();
    const error = vi.fn();
    const utils = render(ImageEditModal, {
        props: {open: true, file: imageFile('holiday.photo.png'), preset: 'custom', ...props},
        events: {
            complete: (e: CustomEvent) => complete(e),
            cancel: (e: CustomEvent) => cancel(e),
            error: (e: CustomEvent) => error(e),
        },
    });
    return {complete, cancel, error, ...utils};
}

beforeAll(async () => {
    await setupI18n();
});

describe('ImageEditModal', () => {
    describe('the not-ready gate', () => {
        it('opens busy and locked until the cropper is ready', () => {
            mount();

            const modal = screen.getByTestId('image-edit-modal');
            // aria-busy for assistive tech; the data flag is the machine-readable twin.
            expect(modal).toHaveAttribute('aria-busy', 'true');
            expect(modal).not.toHaveAttribute('data-edit-ready');
            // The overlay that says "not yet" is up, and confirm cannot fire an upload.
            expect(screen.getByTestId('image-edit-init-guard')).toBeInTheDocument();
            expect(screen.getByTestId('image-edit-confirm')).toBeDisabled();
        });

        it('offers no reset control while there is nothing changed', () => {
            mount();
            // Reset only exists once hasChanges is true — which needs the cropper.
            expect(screen.queryByTestId('image-edit-reset')).toBeNull();
        });
    });

    describe('what it infers from the incoming file', () => {
        it('seeds the editable name from the file, without its extension', () => {
            mount({file: imageFile('holiday.photo.png')});
            // "holiday.photo.png" → only the final extension is dropped.
            expect((screen.getByTestId('image-edit-filename') as HTMLInputElement).value).toBe('holiday.photo');
        });

        it('defaults the output format to PNG and hides the quality control for it', () => {
            mount({file: imageFile('logo.png', 'image/png')});
            expect((screen.getByTestId('image-edit-format') as HTMLSelectElement).value).toBe('png');
            // Quality only matters for lossy formats, so it is absent for PNG.
            expect(screen.queryByTestId('image-edit-quality')).toBeNull();
        });

        it('picks JPEG from a JPEG file and surfaces the quality control', () => {
            mount({file: imageFile('snap.jpg', 'image/jpeg')});
            expect((screen.getByTestId('image-edit-format') as HTMLSelectElement).value).toBe('jpeg');
            expect(screen.getByTestId('image-edit-quality')).toBeInTheDocument();
        });

        it('picks WebP from a WebP file', () => {
            mount({file: imageFile('art.webp', 'image/webp')});
            expect((screen.getByTestId('image-edit-format') as HTMLSelectElement).value).toBe('webp');
        });
    });

    describe('which controls the preset offers', () => {
        it('shows the aspect-ratio row for the free-form custom preset', () => {
            mount({preset: 'custom'});
            expect(screen.getByTestId('image-edit-preset-row')).toBeInTheDocument();
            expect(screen.getByTestId('image-edit-aspect-row')).toBeInTheDocument();
        });

        it('hides the aspect-ratio row for a fixed-shape preset like avatar', () => {
            mount({preset: 'avatar'});
            // Avatar is locked to a shape, so free aspect choice is not offered.
            expect(screen.queryByTestId('image-edit-aspect-row')).toBeNull();
        });

        it('hides the preset row entirely when preset changes are disallowed', () => {
            mount({preset: 'custom', allowPresetChange: false});
            expect(screen.queryByTestId('image-edit-preset-row')).toBeNull();
        });
    });

    describe('the two exits that stay live throughout', () => {
        it('emits cancel from the footer Cancel button, and nothing else', async () => {
            const {cancel, complete} = mount();
            await fireEvent.click(screen.getByTestId('image-edit-cancel'));

            expect(cancel).toHaveBeenCalledTimes(1);
            expect(complete).not.toHaveBeenCalled();
        });

        it('treats the header X as a cancel while there are no changes to lose', async () => {
            const {cancel} = mount();
            await fireEvent.click(screen.getByTestId('image-edit-close'));

            // No unsaved changes → straight out, no discard dialog in the way.
            expect(cancel).toHaveBeenCalledTimes(1);
            expect(screen.queryByTestId('image-edit-confirm-dialog')).toBeNull();
        });
    });

    describe('the imageSrc render gate', () => {
        it('renders nothing until a file gives it something to show', () => {
            mount({file: null});
            // open is true, but with no file there is no object URL, so the modal body
            // is never mounted — the picker upstream owns the "no file" case.
            expect(screen.queryByTestId('image-edit-modal')).toBeNull();
        });

        it('tears the modal down when it is closed', async () => {
            const {rerender} = mount();
            expect(screen.getByTestId('image-edit-modal')).toBeInTheDocument();

            await rerender({open: false, file: imageFile('holiday.photo.png'), preset: 'custom'});
            expect(screen.queryByTestId('image-edit-modal')).toBeNull();
        });
    });
});
