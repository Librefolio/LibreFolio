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
 * Apart from the scope boundaries below, the only thing mocked is the file list
 * endpoint, which would otherwise reach the network; `ModalBase`, `FileGrid`,
 * `LazyImage` and `DataTable` are the real children, so a file is selected by
 * clicking the card FileGrid actually renders.
 *
 * The scope of a picked file (decision 36, last block). The picker hands back a URL
 * other users will load — an avatar, a broker icon — so it offers only what they
 * can see, or what the user can make them see: common files, and the user's own.
 * Picking a personal file of one's own shares it first (`setUploadScope(id,
 * 'common')`) and hands back its URL only once that is done, with the event
 * `file.scope.shared-on-pick`; if sharing fails, nothing is handed back, the picker
 * stays open and `file.scope.change.failed` says why. The filter can leave the
 * list empty, and an empty list once made the picker ask again and again: it now
 * asks once per opening, which the last test pins. Three more boundaries serve
 * that block, inert for the others: `setUploadScope` (the rest of its module stays
 * real: FileGrid formats sizes with it), `notify` (asserted on its event name,
 * detail and toast variant, never on words) and the signed-in user, `currentUser`
 * (signed out unless a test signs someone in; the rest of the auth module is real).
 *
 * What is left to E2E: the parent-owned handoff to ImageEditModal after `upload`
 * (this component only emits the File; it never opens the editor itself).
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const {listFiles} = vi.hoisted(() => ({listFiles: vi.fn()}));
vi.mock('$lib/api', () => ({zodiosApi: {list_files_api_v1_uploads_get: listFiles}}));

const scopeBoundary = vi.hoisted(() => ({setUploadScope: vi.fn(), notify: vi.fn()}));
vi.mock('$lib/utils/files/upload', async (importOriginal) => ({...(await importOriginal<typeof import('$lib/utils/files/upload')>()), setUploadScope: scopeBoundary.setUploadScope}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: scopeBoundary.notify}));

/** The signed-in user, as `currentUser` publishes it; the rest of the auth module stays real. */
type SignedInUser = {id: number; username: string; is_superuser: boolean};
const signedIn = await vi.hoisted(async () => (await import('svelte/store')).writable<SignedInUser | null>(null));
vi.mock('$lib/stores/app/auth', async (importOriginal) => ({...(await importOriginal<typeof import('$lib/stores/app/auth')>()), currentUser: signedIn}));

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {tick} from 'svelte';
import type {UploadedFile} from '$lib/types';
import AssetPickerModal from './AssetPickerModal.svelte';

function file(id: string, name: string, mime = 'image/png', extra: Partial<UploadedFile> = {}): UploadedFile {
    return {id, original_name: name, url: `/uploads/${id}/${name}`, mime_type: mime, size_bytes: 1234, scope: 'common', ...extra} as UploadedFile;
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

/** A promise the test settles when it chooses: the PATCH still in flight is a state the test can hold. */
function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((yes, no) => {
        resolve = yes;
        reject = no;
    });
    return {promise, resolve, reject};
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    // Every test sets its own answer before mounting; the reset keeps call counts and one-shot answers per test.
    listFiles.mockReset();
    scopeBoundary.setUploadScope.mockReset();
    scopeBoundary.notify.mockReset();
    signedIn.set(null);
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

    describe('the scope of a picked file (decision 36)', () => {
        const ME: SignedInUser = {id: 7, username: 'review-me', is_superuser: false};
        const OTHER_ID = 41;

        /** Wait for the list, pick the file's card (by the size every card publishes), and confirm. */
        async function pickAndConfirm(id: string): Promise<void> {
            await fireEvent.click(await screen.findByTestId(`file-grid-size-${id}`));
            const confirm = screen.getByTestId('asset-picker-confirm');
            await waitFor(() => expect(confirm).not.toBeDisabled());
            await fireEvent.click(confirm);
        }

        it('lists only common files and the user’s own personal ones — even to an admin, whose list holds everyone’s', async () => {
            signedIn.set({...ME, is_superuser: true});
            listFiles.mockResolvedValue({
                items: [
                    file('shared', 'shared.png', 'image/png', {scope: 'common', uploaded_by_user_id: OTHER_ID}),
                    file('own-personal', 'own-personal.png', 'image/png', {scope: 'personal', uploaded_by_user_id: ME.id}),
                    file('foreign-personal', 'foreign-personal.png', 'image/png', {scope: 'personal', uploaded_by_user_id: OTHER_ID}),
                ],
            });
            mount({});

            // The list is in, and what it offers is drawn…
            expect(await screen.findByTestId('file-grid-size-shared')).toBeInTheDocument();
            expect(screen.getByTestId('file-grid-size-own-personal')).toBeInTheDocument();
            // …without someone else's personal file, which the other users of the URL could not load.
            expect(screen.queryByTestId('file-grid-size-foreign-personal')).toBeNull();
        });

        it('shares a personal file of the user’s own before handing back its url', async () => {
            signedIn.set(ME);
            const own = file('own-personal', 'own-personal.png', 'image/png', {scope: 'personal', uploaded_by_user_id: ME.id});
            listFiles.mockResolvedValue({items: [own]});
            const patch = deferred<UploadedFile>();
            scopeBoundary.setUploadScope.mockReturnValueOnce(patch.promise);
            const {select} = mount({});

            await pickAndConfirm('own-personal');

            // The PATCH is asked first, and the url waits for its answer.
            await waitFor(() => expect(scopeBoundary.setUploadScope).toHaveBeenCalledExactlyOnceWith('own-personal', 'common'));
            expect(select).not.toHaveBeenCalled();

            patch.resolve({...own, scope: 'common'});
            await waitFor(() => expect(select).toHaveBeenCalledTimes(1));
            expect(selectedUrl(select)).toBe(own.url);
            expect(scopeBoundary.notify).toHaveBeenCalledWith(expect.objectContaining({name: 'file.scope.shared-on-pick', detail: expect.objectContaining({fileId: 'own-personal'})}));
        });

        it('hands back nothing and stays open when sharing fails, and says so', async () => {
            signedIn.set(ME);
            listFiles.mockResolvedValue({items: [file('own-personal', 'own-personal.png', 'image/png', {scope: 'personal', uploaded_by_user_id: ME.id})]});
            scopeBoundary.setUploadScope.mockRejectedValueOnce(new Error('review-share-refused'));
            const {select, cancel} = mount({});

            await pickAndConfirm('own-personal');

            await waitFor(() => expect(scopeBoundary.setUploadScope).toHaveBeenCalledExactlyOnceWith('own-personal', 'common'));
            // An error is always owed a toast (the notify rules): asserted by its variant, never its words.
            await waitFor(() =>
                expect(scopeBoundary.notify).toHaveBeenCalledWith(
                    expect.objectContaining({
                        name: 'file.scope.change.failed',
                        detail: expect.objectContaining({fileId: 'own-personal'}),
                        toast: expect.objectContaining({variant: 'error'}),
                    }),
                ),
            );
            expect(select).not.toHaveBeenCalled();
            expect(cancel).not.toHaveBeenCalled();
            expect(screen.getByTestId('asset-picker-modal')).toBeInTheDocument();
            expect(scopeBoundary.notify).not.toHaveBeenCalledWith(expect.objectContaining({name: 'file.scope.shared-on-pick'}));
        });

        it.each([
            {whose: 'someone else’s', id: 'shared', owner: OTHER_ID},
            {whose: 'the user’s own', id: 'own-common', owner: ME.id},
        ])('hands back a common file ($whose) at once, without touching its scope', async ({id, owner}) => {
            signedIn.set(ME);
            const picked = file(id, `${id}.png`, 'image/png', {scope: 'common', uploaded_by_user_id: owner});
            listFiles.mockResolvedValue({items: [picked]});
            const {select} = mount({});

            await pickAndConfirm(id);

            await waitFor(() => expect(select).toHaveBeenCalledTimes(1));
            expect(selectedUrl(select)).toBe(picked.url);
            expect(scopeBoundary.setUploadScope).not.toHaveBeenCalled();
        });

        /** An answer of the list endpoint with only someone else's personal image; `onRead` records that the picker took it in. */
        function onlyForeignPersonal(onRead: () => void): {items: UploadedFile[]} {
            const items = [file('foreign-personal', 'foreign-personal.png', 'image/png', {scope: 'personal', uploaded_by_user_id: OTHER_ID})];
            return {
                get items() {
                    onRead();
                    return items;
                },
            };
        }

        it('loads the list once per opening, even when the filter leaves nothing to offer — and once more when opened again', async () => {
            signedIn.set(ME);
            // Each opening's request is answered when the test says; a request beyond those two would stay in flight.
            const answers = [deferred<{items: UploadedFile[]}>(), deferred<{items: UploadedFile[]}>()] as const;
            const read = [vi.fn(), vi.fn()] as const;
            listFiles
                .mockImplementation(() => new Promise(() => {}))
                .mockReturnValueOnce(answers[0].promise)
                .mockReturnValueOnce(answers[1].promise);

            /**
             * The picker settles on the answer of opening `n`: answered, read by the picker (the getter), applied by
             * Svelte (`tick`). Any request that answer provokes has been made by then.
             */
            async function settle(n: 0 | 1): Promise<void> {
                answers[n].resolve(onlyForeignPersonal(read[n]));
                await waitFor(() => expect(read[n], `the picker read the answer of opening ${n + 1}`).toHaveBeenCalled());
                await tick();
            }

            const {cancel, rerender} = mount({});
            expect(listFiles, 'opening on the existing tab asks for the list').toHaveBeenCalledTimes(1);
            await settle(0);
            // Applied: someone else's personal image is not offered, so the list is empty — and asks for nothing more.
            expect(screen.queryByTestId('file-grid-size-foreign-personal')).toBeNull();
            expect(listFiles, 'an empty list does not load again').toHaveBeenCalledTimes(1);

            // Closed by the user; the parent follows its cancel. Closing loads nothing.
            await fireEvent.click(screen.getByTestId('asset-picker-cancel'));
            expect(cancel).toHaveBeenCalledTimes(1);
            await rerender({open: false});
            await waitFor(() => expect(screen.queryByTestId('asset-picker-modal')).toBeNull());
            expect(listFiles, 'closing loads nothing').toHaveBeenCalledTimes(1);

            // Opened again: one request more, and no other once it has settled.
            await rerender({open: true});
            expect(screen.getByTestId('asset-picker-modal')).toBeInTheDocument();
            expect(listFiles, 'opening again asks for the list once more').toHaveBeenCalledTimes(2);
            await settle(1);
            expect(listFiles, 'the second opening, settled, asks for nothing more').toHaveBeenCalledTimes(2);
        });
    });
});
