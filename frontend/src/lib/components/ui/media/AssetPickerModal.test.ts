// @vitest-environment jsdom
/**
 * AssetPickerModal — component test (Vitest + jsdom).
 *
 * The picker's whole job is to hand its parent one thing — a URL — through a
 * `select` event, or to back out through `cancel`; the file upload path hands back
 * a `File` through `upload`. Those three payloads are the contract, and they are
 * what every test here asserts on, never a tab's active class or a translated
 * label. Events are captured with mount's `events` option (the component still
 * dispatches through the legacy `createEventDispatcher`).
 *
 * The only thing mocked is the file list endpoint, which would otherwise reach the
 * network; `ModalBase`, `FileGrid`, `LazyImage` and `DataTable` are the real
 * children, so a file is selected by clicking the card FileGrid actually renders.
 *
 * What is left to E2E: the parent-owned handoff to ImageEditModal after `upload`
 * (this component only emits the File; it never opens the editor itself).
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';

const {listFiles} = vi.hoisted(() => ({listFiles: vi.fn()}));
vi.mock('$lib/api', () => ({zodiosApi: {list_files_api_v1_uploads_get: listFiles}}));

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {UploadedFile} from '$lib/types';
import AssetPickerModal from './AssetPickerModal.svelte';

function file(id: string, name: string, mime = 'image/png'): UploadedFile {
    return {id, original_name: name, url: `/uploads/${id}/${name}`, mime_type: mime, size_bytes: 1234} as UploadedFile;
}

interface Handlers {
    select?: (e: CustomEvent) => void;
    cancel?: (e: CustomEvent) => void;
    upload?: (e: CustomEvent) => void;
}

function mount(props: Record<string, unknown> = {}, handlers: Handlers = {}) {
    const select = vi.fn();
    const cancel = vi.fn();
    const upload = vi.fn();
    const utils = render(AssetPickerModal, {
        props: {open: true, ...props},
        events: {
            select: (e: CustomEvent) => (handlers.select ?? select)(e),
            cancel: (e: CustomEvent) => (handlers.cancel ?? cancel)(e),
            upload: (e: CustomEvent) => (handlers.upload ?? upload)(e),
        },
    });
    return {select, cancel, upload, ...utils};
}

/** The url the picker handed back through its `select` event. */
function selectedUrl(select: ReturnType<typeof vi.fn>): string {
    return select.mock.calls.at(-1)?.[0]?.detail?.url;
}

beforeAll(async () => {
    await setupI18n();
});

describe('AssetPickerModal', () => {
    describe('URL tab', () => {
        it('opens straight to the URL tab when seeded, and hands back that URL on confirm', async () => {
            listFiles.mockResolvedValue({items: []});
            const {select} = mount({initialUrl: 'https://cdn.test/logo.png'});

            const confirm = screen.getByTestId('asset-picker-confirm');
            expect(confirm).not.toBeDisabled();
            await fireEvent.click(confirm);

            expect(select).toHaveBeenCalledTimes(1);
            expect(selectedUrl(select)).toBe('https://cdn.test/logo.png');
        });

        it('will not confirm an empty URL, but will once something is typed', async () => {
            listFiles.mockResolvedValue({items: []});
            const {select} = mount({});

            await fireEvent.click(screen.getByTestId('asset-picker-url-tab'));
            const confirm = screen.getByTestId('asset-picker-confirm');
            // Nothing typed yet, and no initial URL → the confirm is inert.
            expect(confirm).toBeDisabled();

            await fireEvent.input(screen.getByTestId('asset-picker-url-input'), {target: {value: 'assets/pic.png'}});
            await waitFor(() => expect(confirm).not.toBeDisabled());
            await fireEvent.click(confirm);
            expect(selectedUrl(select)).toBe('assets/pic.png');
        });

        it('treats clearing a seeded URL as a request to remove the image', async () => {
            listFiles.mockResolvedValue({items: []});
            const {select} = mount({initialUrl: 'https://cdn.test/old.png'});

            // Erase the field: the confirm now means "remove", emitting an empty url.
            await fireEvent.input(screen.getByTestId('asset-picker-url-input'), {target: {value: ''}});
            const confirm = screen.getByTestId('asset-picker-confirm');
            await waitFor(() => expect(confirm).not.toBeDisabled());
            await fireEvent.click(confirm);

            expect(select).toHaveBeenCalledTimes(1);
            expect(selectedUrl(select)).toBe('');
        });
    });

    describe('cancelling', () => {
        it('emits cancel from the footer Cancel button without selecting anything', async () => {
            listFiles.mockResolvedValue({items: []});
            const {select, cancel} = mount({initialUrl: 'https://cdn.test/x.png'});

            const modal = screen.getByTestId('asset-picker-modal');
            await fireEvent.click(within(modal).getByTestId('asset-picker-cancel'));

            expect(cancel).toHaveBeenCalledTimes(1);
            expect(select).not.toHaveBeenCalled();
        });
    });

    describe('existing files tab', () => {
        it('loads the file list, and confirms the file the user picks', async () => {
            listFiles.mockResolvedValue({items: [file('a1', 'alpha.png'), file('b2', 'beta.png')]});
            const {select} = mount({});

            // The existing tab is the default when no URL was seeded; the list loads async.
            // FileGrid renders each card's title as the file's own name, so select by it.
            const card = await screen.findByText('beta.png');
            const confirm = screen.getByTestId('asset-picker-confirm');
            // Nothing chosen yet — confirm is inert until a file is selected.
            expect(confirm).toBeDisabled();

            await fireEvent.click(card);
            await waitFor(() => expect(confirm).not.toBeDisabled());
            await fireEvent.click(confirm);

            expect(selectedUrl(select)).toBe('/uploads/b2/beta.png');
        });

        it('keeps only image files when filterImages is on', async () => {
            listFiles.mockResolvedValue({items: [file('img', 'pic.png', 'image/png'), file('doc', 'notes.pdf', 'application/pdf')]});
            mount({});

            await screen.findByText('pic.png');
            // The PDF is filtered out before it ever reaches the grid.
            expect(screen.queryByText('notes.pdf')).toBeNull();
        });

        it('narrows the grid by the search box', async () => {
            listFiles.mockResolvedValue({items: [file('a1', 'alpha.png'), file('b2', 'beta.png')]});
            mount({});

            await screen.findByText('alpha.png');
            await fireEvent.input(screen.getByTestId('asset-picker-search'), {target: {value: 'beta'}});

            await waitFor(() => expect(screen.queryByText('alpha.png')).toBeNull());
            expect(screen.getByText('beta.png')).toBeInTheDocument();
        });

        it('leaves confirm inert when there are no files to choose from', async () => {
            listFiles.mockResolvedValue({items: []});
            mount({});

            // Let the (empty) load resolve, then confirm must still be disabled.
            await waitFor(() => expect(listFiles).toHaveBeenCalled());
            expect(screen.getByTestId('asset-picker-confirm')).toBeDisabled();
        });
    });

    describe('upload path', () => {
        it('emits the chosen File through upload, without selecting or closing', async () => {
            listFiles.mockResolvedValue({items: []});
            const {select, cancel, upload} = mount({});

            const picked = new File(['x'], 'new.png', {type: 'image/png'});
            const input = screen.getByTestId('asset-picker-modal').querySelector<HTMLInputElement>('input[type="file"]')!;
            await fireEvent.change(input, {target: {files: [picked]}});

            expect(upload).toHaveBeenCalledTimes(1);
            expect(upload.mock.calls[0][0].detail.file).toBe(picked);
            // Upload is a handoff, not a selection: neither of the other two fires.
            expect(select).not.toHaveBeenCalled();
            expect(cancel).not.toHaveBeenCalled();
        });
    });
});
