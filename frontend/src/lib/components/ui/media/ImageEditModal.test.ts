// @vitest-environment jsdom
/**
 * ImageEditModal — component test (Vitest + jsdom).
 *
 * This modal wraps a canvas cropper (`cropperjs` v2, a Web Component that paints to
 * a `<canvas>`). In jsdom the wrapped image never loads and the canvas never paints,
 * so the real cropper never reports ready. The modal deliberately gates its whole
 * editing surface behind that readiness — `editReady` only flips ~500 ms after the
 * cropper's first change event (see the `handleCropperChange` init dance). The
 * output-size maths, quality/preset/aspect handlers and the discard-changes dialog
 * live in the `image-crop` E2E suite, where a browser actually paints the canvas.
 *
 * What a component test CAN pin down here is everything the modal derives and
 * decides *before* the cropper is in play: the not-ready gate the user sees, the
 * filename/format it infers from the incoming File, which preset rows it offers, and
 * the two exits (cancel / close) that stay live throughout. Those are the parts a
 * translation change or a refactor could silently break, and none of them needs the
 * canvas.
 *
 * The cropper is therefore a stub (`$test/harness/ImageCropperStub.svelte`) with the
 * real one's surface, which reports a selection only when a test clicks it: until
 * then the modal sees what it saw with the real cropper in jsdom, one that never
 * reports. The last block clicks it, waits for the state the modal publishes
 * (`data-edit-ready`) and so reaches the crop → upload path, to pin which scope the
 * upload carries (decision 36): the `scope` prop, `common` unless the parent says
 * otherwise, as the third argument of `uploadFile`. The upload and the canvas crop
 * (`getCroppedImageFromCropper`) are spies; the rest of `imageCrop` is real.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const media = vi.hoisted(() => ({uploadFile: vi.fn(), crop: vi.fn()}));
vi.mock('$lib/utils/files/upload', () => ({uploadFile: media.uploadFile}));
vi.mock('$lib/utils/files/imageCrop', async (importOriginal) => ({...(await importOriginal<typeof import('$lib/utils/files/imageCrop')>()), getCroppedImageFromCropper: media.crop}));
vi.mock('./ImageCropper.svelte', async () => ({default: (await import('$test/harness/ImageCropperStub.svelte')).default}));

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import type {PresetName} from '$lib/utils/files/imageCrop';
import ImageEditModal from './ImageEditModal.svelte';
import {get} from 'svelte/store';
import {_} from 'svelte-i18n';

function imageFile(name: string, type = 'image/png'): File {
    return new File(['binary'], name, {type});
}

function mount(props: {file?: File | null; open?: boolean; preset?: PresetName; allowPresetChange?: boolean; uploadOnComplete?: boolean; scope?: 'common' | 'personal'} = {}) {
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

    describe('the scope the cropped image is uploaded with (decision 36)', () => {
        beforeEach(() => {
            media.uploadFile.mockReset().mockResolvedValue('/uploads/cropped.png');
            media.crop.mockReset().mockResolvedValue(new Blob(['cropped'], {type: 'image/png'}));
        });

        /**
         * Let the cropper report, wait for the modal to say edits now count (`data-edit-ready`, after its own init
         * pass), crop and upload: the arguments `uploadFile` got.
         */
        async function cropAndUpload(): Promise<unknown[]> {
            const modal = screen.getByTestId('image-edit-modal');
            await fireEvent.click(screen.getByTestId('image-cropper-stub-report'));
            await waitFor(() => expect(modal).toHaveAttribute('data-edit-ready', 'true'), {timeout: 5_000});
            const confirm = screen.getByTestId('image-edit-confirm');
            expect(confirm).not.toBeDisabled();
            await fireEvent.click(confirm);
            await waitFor(() => expect(media.uploadFile).toHaveBeenCalledTimes(1));
            // The crop went through the cropper the stub handed over: the path is the real one, only the canvas is not.
            expect(media.crop).toHaveBeenCalledTimes(1);
            expect(media.crop.mock.calls[0][0]).toEqual({stub: 'image-cropper'});
            return media.uploadFile.mock.calls[0];
        }

        it('uploads as common when the parent says nothing: the image pickers share what they upload', async () => {
            const {complete} = mount();

            const [uploaded, , scope] = await cropAndUpload();

            expect((uploaded as File).name).toBe('holiday.photo.png');
            expect(scope).toBe('common');
            await waitFor(() => expect(complete).toHaveBeenCalledTimes(1));
            expect(complete.mock.calls[0][0].detail.url).toBe('/uploads/cropped.png');
        });

        it('uploads as personal when the parent passes scope="personal"', async () => {
            const {complete} = mount({scope: 'personal'});

            const [uploaded, , scope] = await cropAndUpload();

            expect((uploaded as File).name).toBe('holiday.photo.png');
            expect(scope).toBe('personal');
            await waitFor(() => expect(complete).toHaveBeenCalledTimes(1));
        });
    });
});

/**
 * The standard buttons (85 BTN-2b). While the editor is not ready its controls are off but reachable — `aria-disabled`
 * with `data-disabled-reason="edit-not-ready"`, in the tab order, a click doing nothing — and they come alive with
 * `data-edit-ready`. The presets, the ratios and the round preview are toggles (`aria-pressed` follows the choice). The
 * quality − / + are a `ButtonGroup` filled from this legacy component's markup: the group's context reaches them, so
 * they draw as segments. The confirm button is busy while the upload runs. The reset exists only with a change, which
 * needs the editor ready: its off state cannot be reached.
 */
describe('ImageEditModal — the standard buttons (85 BTN-2b)', () => {
    const jpeg = () => imageFile('portrait.jpg', 'image/jpeg');
    const NOT_READY_CONTROLS = ['image-edit-quality-down', 'image-edit-quality-up', 'image-edit-ellipse-toggle', 'image-edit-preset-avatar', 'image-edit-preset-broker-icon', 'image-edit-preset-custom', 'image-edit-aspect-1x1', 'image-edit-aspect-free'];
    const qualityValue = () => screen.getByTestId('image-edit-quality').textContent?.replace(/\s+/g, '') ?? '';

    async function ready(): Promise<void> {
        await fireEvent.click(screen.getByTestId('image-cropper-stub-report'));
        await waitFor(() => expect(screen.getByTestId('image-edit-modal')).toHaveAttribute('data-edit-ready', 'true'), {timeout: 5_000});
    }

    it('while not ready: every control is off with its reason, reachable, and a click does nothing', async () => {
        mount({file: jpeg(), preset: 'custom'});
        for (const id of NOT_READY_CONTROLS) {
            const control = screen.getByTestId(id);
            expect(control, id).toHaveAttribute('aria-disabled', 'true');
            expect(control, id).toHaveAttribute('data-disabled-reason', 'edit-not-ready');
            expect(control.hasAttribute('disabled'), `${id}: reachable, never natively disabled`).toBe(false);
            expect(control.tabIndex, id).toBe(0);
        }
        const quality = qualityValue();
        const avatar = screen.getByTestId('image-edit-preset-avatar');
        await fireEvent.click(screen.getByTestId('image-edit-quality-up'));
        await fireEvent.click(avatar);
        await fireEvent.click(screen.getByTestId('image-edit-ellipse-toggle'));
        expect(qualityValue(), 'the quality did not move').toBe(quality);
        expect(avatar).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId('image-edit-ellipse-toggle')).toHaveAttribute('aria-pressed', 'false');
        expect(screen.queryByTestId('image-edit-reset'), 'nothing changed').toBeNull();
    });

    it('once ready the controls are live: the presets and the ratios are toggles that follow the choice', async () => {
        mount({file: jpeg(), preset: 'custom'});
        await ready();
        for (const id of NOT_READY_CONTROLS) expect(screen.getByTestId(id), id).not.toHaveAttribute('aria-disabled');

        const sixteenNine = screen.getByTestId('image-edit-aspect-16x9');
        await fireEvent.click(sixteenNine);
        expect(sixteenNine).toHaveAttribute('aria-pressed', 'true');
        const pressedRatios = [...screen.getByTestId('image-edit-aspect-row').querySelectorAll('[aria-pressed="true"]')].map((el) => el.getAttribute('data-testid'));
        expect(pressedRatios, 'one ratio at a time').toEqual(['image-edit-aspect-16x9']);

        const avatar = screen.getByTestId('image-edit-preset-avatar');
        await fireEvent.click(avatar);
        expect(avatar).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('image-edit-preset-custom')).toHaveAttribute('aria-pressed', 'false');
        // Avatar turns the round preview on (selectPreset), and the toggle says so.
        expect(screen.getByTestId('image-edit-ellipse-toggle')).toHaveAttribute('aria-pressed', 'true');
        // A change was made: the reset is there, live.
        expect(screen.getByTestId('image-edit-reset')).not.toHaveAttribute('aria-disabled');
    });

    it('the quality − / + are a named group of segments, from a legacy parent', async () => {
        mount({file: jpeg(), preset: 'custom'});
        const group = screen.getByTestId('image-edit-quality');
        expect(group).toHaveAttribute('role', 'group');
        expect(group).toHaveAttribute('aria-label', get(_)('uploads.quality'));
        for (const id of ['image-edit-quality-down', 'image-edit-quality-up']) {
            const segment = screen.getByTestId(id);
            expect(group.contains(segment)).toBe(true);
            expect(segment.classList.contains('lf-btn-segment'), `${id}: the ButtonGroup context reached it`).toBe(true);
        }
        await ready();
        const before = qualityValue();
        await fireEvent.click(screen.getByTestId('image-edit-quality-down'));
        expect(qualityValue()).not.toBe(before);
    });

    it('confirm is busy while the upload runs: aria-busy, its busy word, a second click drops', async () => {
        let finish: (url: string) => void = () => {};
        media.uploadFile.mockReset().mockImplementation(() => new Promise<string>((resolve) => (finish = resolve)));
        media.crop.mockReset().mockResolvedValue(new Blob(['cropped'], {type: 'image/png'}));
        const {complete} = mount();
        await ready();
        const confirm = screen.getByTestId('image-edit-confirm');
        await fireEvent.click(confirm);
        await waitFor(() => expect(confirm).toHaveAttribute('aria-busy', 'true'));
        expect(confirm).toHaveAttribute('aria-disabled', 'true');
        expect(confirm.textContent).toContain(get(_)('common.uploading'));
        await fireEvent.click(confirm);
        expect(media.uploadFile, 'nothing starts twice').toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('image-edit-cancel'), 'cancel is natively off during the upload').toHaveAttribute('disabled');
        finish('/uploads/cropped.png');
        await waitFor(() => expect(complete).toHaveBeenCalledTimes(1));
    });
});
