// @vitest-environment jsdom
/**
 * BrokerImportFilesModal — bulk delete of a broker's BRIM report files (backlog W-B37, decision 36).
 *
 * The contract under test. `GET /brokers/import/files` lists the broker's reports, and each item (`BRIMFileListItem`)
 * says whether the user may delete it: `can_delete`. A bulk delete — rows ticked, the SelectionBar's delete, the
 * destructive confirmation — sends a DELETE only for the selected files whose `can_delete` is not false, as the Files
 * page does since H's CP-U2 (`deletableSelection` and `handleBulkDeleteFiles` in `routes/(app)/files/+page.svelte`).
 * The files left out are announced once, with the page's own notice: `notify({name: 'file.delete.skipped', detail:
 * {count, isBrim: true}, toast: {variant: 'warning', message: $_('uploads.deleteSkipped')}})`, `count` being the files
 * left out. When nothing deletable remains the operation stops there: no DELETE, no error, no success toast. Otherwise
 * the success toast counts the deleted files only.
 *
 * Today (`817a2d37c`) `handleDeleteMultiple` sends a DELETE for every selected id and reports the 403s in the error
 * banner: the first two tests are red on their first assertion, the DELETEs sent. The third is the green guard of a
 * selection the user may wholly delete; the last is a control of the harness.
 *
 * The harness. The component runs as in the app — the modal, FilesTable, DataTable, SelectionBar, ConfirmModal and the
 * generated client (Zodios on axios, `validate: 'response'`) — and only the transport is faked:
 * `axiosInstance.defaults.adapter` answers as a server holding the broker's files would. A DELETE of a file whose
 * `can_delete` is false is refused with a 403, as the backend refuses it; an accepted one removes the file, so the list
 * asked again afterwards holds what is left. The real client is the point: the list answer is parsed by
 * `BRIMFileListItem`, and Zod drops every key a schema does not declare, so `can_delete` reaching the modal is part of
 * what is proved here — and every fixture must carry every required field of that schema, `can_delete` included (the
 * control shows the refusal of one that does not).
 *
 * What is read, and how:
 *   - the DELETEs, as the transport received them;
 *   - `notify`, spied with its real body kept, so the notice's toast still reaches the real toast store;
 *   - the toasts, from that store, by variant;
 *   - the counts, as numbers: `$_` (and `$t`, the same store) is wrapped to record each key with its values and the
 *     text it returned, so a toast is tied to the call that worded it by the identity of that text, never by reading it;
 *   - which confirmation opened (this ConfirmModal carries no testId): by the values its message was formatted with.
 *
 * The end of the operation: `confirmBulkDelete` clears the table's selection only once `handleDeleteMultiple` has
 * returned, and the SelectionBar's delete goes with it. The modal publishes no busy state for a delete, so that is the
 * barrier every test waits on before reading anything. Each test keeps a file listed after the operation, so the table
 * — and the selection the barrier reads — stays mounted throughout.
 */
import {afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {AxiosError, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {axiosInstance, zodiosApi} from '$lib/api';
import {notify, type NotifyOptions} from '$lib/stores/app/notify.svelte';
import {toasts, type ToastVariant} from '$lib/stores/app/toastStore.svelte';
import BrokerImportFilesModal from './BrokerImportFilesModal.svelte';

/** Every message formatted through `$_` or `$t`: its key, its values, and the text the catalogue returned. */
const formatted = vi.hoisted(() => [] as Array<{key: string; values: Record<string, unknown> | undefined; text: string}>);

// The real formatter, recorded: the catalogue still words every label, the test reads the arguments. `_` and `t` are
// one store in svelte-i18n, and the Files page words the same notice with `$t`: both are recorded, whichever the
// modal uses.
vi.mock('$lib/i18n', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/i18n')>();
    const {derived} = await import('svelte/store');
    const recording = derived(actual._, (format) => {
        const record: typeof format = (id, options) => {
            const text = format(id, options);
            formatted.push(typeof id === 'string' ? {key: id, values: options?.values, text} : {key: id.id, values: id.values, text});
            return text;
        };
        return record;
    });
    return {...actual, _: recording, t: recording};
});

// Spied, not replaced: the notice's toast must still reach the toast store.
vi.mock('$lib/stores/app/notify.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/app/notify.svelte')>();
    return {...actual, notify: vi.fn(actual.notify)};
});

/** A broker report as `GET /brokers/import/files` answers it, typed by the generated client. */
type ListedFile = Awaited<ReturnType<typeof zodiosApi.list_files_api_v1_brokers_import_files_get>>[number];

const BROKER_ID = 37;
const LIST_URL = '/api/v1/brokers/import/files';
const PLUGINS_URL = '/api/v1/brokers/import/plugins';
const FILE_URL = /^\/api\/v1\/brokers\/import\/files\/([^/]+)$/;

const DELETABLE_1 = 'w-b37-deletable-1';
const DELETABLE_2 = 'w-b37-deletable-2';
const DELETABLE_3 = 'w-b37-deletable-3';
const LOCKED_1 = 'w-b37-locked-1';
const LOCKED_2 = 'w-b37-locked-2';

/** A report of the broker with every required field of `BRIMFileListItem`, `can_delete` included. */
function listed(fileId: string, canDelete: boolean): ListedFile {
    return {
        file_id: fileId,
        filename: `${fileId}.csv`,
        size_bytes: 2048,
        status: 'uploaded',
        uploaded_at: '2026-10-15T08:00:00Z',
        uploaded_by_user_id: canDelete ? 11 : 12,
        target_broker_id: BROKER_ID,
        can_delete: canDelete,
    };
}

/** What the fake server holds, and what it was asked. */
const server = {
    /** The broker's files, as the list answers them; the control leaves a field out to watch the client refuse it. */
    files: [] as Array<Partial<ListedFile>>,
    /** The file id of every DELETE received, refused ones included, in arrival order. */
    deletes: [] as string[],
    /** Requests this server does not know: each one is a red of its own, read after every test. */
    unexpected: [] as string[],
};

/** A JSON answer: without that content type Zodios would skip the response schema, and the harness would prove less. */
function answer(config: InternalAxiosRequestConfig, status: number, data: unknown): AxiosResponse {
    return {status, statusText: String(status), headers: {'content-type': 'application/json'}, config, request: {}, data};
}

/** What axios rejects with when the server answers a status outside 2xx (axios/lib/core/settle.js). */
function refusal(config: InternalAxiosRequestConfig, status: number, detail: string): AxiosError {
    return new AxiosError(`Request failed with status code ${status}`, AxiosError.ERR_BAD_REQUEST, config, {}, answer(config, status, {detail}));
}

const fakeServer: AxiosAdapter = async (config) => {
    const method = (config.method ?? 'get').toLowerCase();
    const url = config.url ?? '';
    if (method === 'get' && url === LIST_URL) {
        // A copy per answer: what the modal receives never aliases what the server holds.
        const files = server.files.map((file) => ({...file}));
        return answer(config, 200, files);
    }
    // FilesTable asks once (it caches the answer) for the plugin catalogue behind its report-set badges: none here.
    if (method === 'get' && url === PLUGINS_URL) return answer(config, 200, []);
    const target = method === 'delete' ? FILE_URL.exec(url)?.[1] : undefined;
    if (target !== undefined) {
        server.deletes.push(target);
        const file = server.files.find((candidate) => candidate.file_id === target);
        if (!file) throw refusal(config, 404, 'w-b37 fake server: no such file');
        // The backend refuses whoever is neither EDITOR nor OWNER of the file's broker (decision 36).
        if (file.can_delete === false) throw refusal(config, 403, 'w-b37 fake server: not allowed to delete this file');
        server.files = server.files.filter((candidate) => candidate !== file);
        return answer(config, 200, {});
    }
    server.unexpected.push(`${method} ${url}`);
    throw refusal(config, 404, 'w-b37 fake server: unknown request');
};

const notified = vi.mocked(notify);

/** The `file.delete.skipped` notices raised during the test. */
function skippedNotices(): NotifyOptions[] {
    return notified.mock.calls.map(([options]) => options).filter((options) => options.name === 'file.delete.skipped');
}

/** What the formatter was asked for `key`, call by call. */
function formattedFor(key: string) {
    return formatted.filter((call) => call.key === key);
}

/** The messages of the toasts of one variant, as the toast store holds them. */
function toastMessages(variant: ToastVariant): string[] {
    return toasts.items.filter((toast) => toast.variant === variant).map((toast) => toast.message);
}

const ROW_CHECKBOX = 'dt-row-checkbox-';

/** The ids of the files the table lists, read from their selection checkboxes, sorted. */
function listedIds(modal: HTMLElement): string[] {
    return [...modal.querySelectorAll<HTMLElement>(`[data-testid^="${ROW_CHECKBOX}"]`)].map((checkbox) => (checkbox.dataset.testid ?? '').slice(ROW_CHECKBOX.length)).sort();
}

function renderModal(): HTMLElement {
    render(BrokerImportFilesModal, {open: true, brokerId: BROKER_ID, brokerName: 'W-B37 broker', onClose: vi.fn()});
    return screen.getByTestId('import-files-modal');
}

/** Open the modal on `files` and wait until the table lists every one of them, none ticked. */
async function openModal(files: ListedFile[]): Promise<HTMLElement> {
    server.files = files.map((file) => ({...file}));
    const modal = renderModal();
    await waitFor(
        () => {
            // A refused list answer shows the load error instead of a table: say so, rather than time out on a row.
            expect(within(modal).queryByTestId('info-banner-error'), 'the list answer was refused: every fixture must satisfy BRIMFileListItem').toBeNull();
            expect(listedIds(modal)).toEqual(files.map((file) => file.file_id).sort());
        },
        {timeout: 3_000},
    );
    for (const file of files) expect(within(modal).getByTestId(`${ROW_CHECKBOX}${file.file_id}`)).toHaveAttribute('data-state', 'unchecked');
    return modal;
}

/** Tick each file's row, as a user does. */
async function selectRows(modal: HTMLElement, ids: string[]): Promise<void> {
    for (const id of ids) await fireEvent.click(within(modal).getByTestId(`${ROW_CHECKBOX}${id}`));
    for (const id of ids) expect(within(modal).getByTestId(`${ROW_CHECKBOX}${id}`)).toHaveAttribute('data-state', 'checked');
}

/** The SelectionBar's delete, then the destructive confirmation; returns once the operation is over. */
async function bulkDelete(modal: HTMLElement, selected: number): Promise<void> {
    expect(screen.queryByTestId('confirm-modal-confirm'), 'no confirmation is open before the bulk action').toBeNull();
    await fireEvent.click(within(modal).getByTestId('selection-bar-action-delete'));
    const confirm = await screen.findByTestId('confirm-modal-confirm');
    // This ConfirmModal has no testId: the bulk confirmation is the one whose message counts the selection.
    expect(
        formattedFor('uploads.confirmBulkDelete.message').map((call) => call.values),
        'the bulk confirmation, for the selected files',
    ).toContainEqual({n: selected});
    await fireEvent.click(confirm);
    // confirmBulkDelete clears the selection only after handleDeleteMultiple has returned: the end of the operation.
    await waitFor(() => expect(within(modal).queryByTestId('selection-bar-action-delete')).toBeNull(), {timeout: 3_000});
}

let realAdapter: typeof axiosInstance.defaults.adapter;

beforeAll(async () => {
    await setupI18n();
    realAdapter = axiosInstance.defaults.adapter;
    axiosInstance.defaults.adapter = fakeServer;
});

afterAll(() => {
    axiosInstance.defaults.adapter = realAdapter;
});

beforeEach(() => {
    server.files = [];
    server.deletes.length = 0;
    server.unexpected.length = 0;
    formatted.length = 0;
    notified.mockClear();
    toasts.clear();
    // ModalBase gives the page its scroll back when it closes; jsdom implements no scrolling.
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    toasts.clear();
    expect(server.unexpected, 'requests the fake server does not answer').toEqual([]);
});

describe('BrokerImportFilesModal bulk delete — the files the user may not delete are left out (W-B37)', () => {
    // Red today: a DELETE goes out for the locked file too, its 403 lands in the error banner, no notice, no success.
    it('deletes only the deletable files of a mixed selection, with one skipped notice and a success toast counting the deleted ones', async () => {
        const modal = await openModal([listed(DELETABLE_1, true), listed(LOCKED_1, false), listed(DELETABLE_2, true)]);
        await selectRows(modal, [DELETABLE_1, LOCKED_1, DELETABLE_2]);
        await bulkDelete(modal, 3);

        expect([...server.deletes].sort(), 'a DELETE for each selected file the user may delete, none for the other').toEqual([DELETABLE_1, DELETABLE_2].sort());
        const notices = skippedNotices();
        expect(notices, 'one notice for the file left in place').toHaveLength(1);
        expect(notices[0].detail).toEqual({count: 1, isBrim: true});
        expect(notices[0].toast?.variant).toBe('warning');
        expect(
            formattedFor('uploads.deleteSkipped').map((call) => call.text),
            'the notice is worded by uploads.deleteSkipped',
        ).toContain(notices[0].toast?.message);
        expect(toastMessages('warning'), 'its toast reached the store, once').toEqual([notices[0].toast?.message]);
        const counted = formattedFor('uploads.deleteBatchSucceeded');
        expect(
            counted.map((call) => call.values),
            'the success toast counts the two deleted files, not the three selected',
        ).toEqual([{n: 2}]);
        expect(toastMessages('success'), 'one success toast, worded by that call').toEqual([counted[0].text]);
        expect(within(modal).queryByTestId('info-banner-error'), 'no refusal to report').toBeNull();
        expect(listedIds(modal), 'the list asked again holds the file left in place').toEqual([LOCKED_1]);
    });

    // Red today: a DELETE goes out for each locked file, both 403s land in the error banner.
    it('sends no DELETE for a selection the user may not delete at all: the skipped notice once, and neither an error nor a success', async () => {
        const modal = await openModal([listed(LOCKED_1, false), listed(DELETABLE_1, true), listed(LOCKED_2, false)]);
        await selectRows(modal, [LOCKED_1, LOCKED_2]);
        await bulkDelete(modal, 2);

        expect(server.deletes, 'nothing selected may be deleted: no DELETE at all').toEqual([]);
        const notices = skippedNotices();
        expect(notices, 'one notice for the two files left in place').toHaveLength(1);
        expect(notices[0].detail).toEqual({count: 2, isBrim: true});
        expect(notices[0].toast?.variant).toBe('warning');
        expect(formattedFor('uploads.deleteSkipped').map((call) => call.text)).toContain(notices[0].toast?.message);
        expect(toastMessages('warning'), 'its toast reached the store, once').toEqual([notices[0].toast?.message]);
        expect(within(modal).queryByTestId('info-banner-error'), 'no error: nothing was refused').toBeNull();
        expect(toastMessages('success'), 'no success toast: nothing was deleted').toEqual([]);
        expect(formattedFor('uploads.deleteBatchSucceeded')).toEqual([]);
        // The table is still there with every file, the unselected deletable one included: the absences above stand
        // beside what is present, and the filter worked on the selection, not on the list.
        expect(listedIds(modal)).toEqual([DELETABLE_1, LOCKED_1, LOCKED_2].sort());
    });

    // Green today, and after the cure: the guard of the path that must not change.
    it('deletes a selection the user may wholly delete file by file, without a skipped notice', async () => {
        const modal = await openModal([listed(DELETABLE_1, true), listed(DELETABLE_2, true), listed(DELETABLE_3, true)]);
        await selectRows(modal, [DELETABLE_1, DELETABLE_3]);
        await bulkDelete(modal, 2);

        expect([...server.deletes].sort(), 'a DELETE for each selected file').toEqual([DELETABLE_1, DELETABLE_3].sort());
        expect(skippedNotices(), 'nothing left out: no notice').toEqual([]);
        expect(toastMessages('warning')).toEqual([]);
        const counted = formattedFor('uploads.deleteBatchSucceeded');
        expect(
            counted.map((call) => call.values),
            'the success toast counts the two deleted files',
        ).toEqual([{n: 2}]);
        expect(toastMessages('success'), 'one success toast, worded by that call').toEqual([counted[0].text]);
        expect(within(modal).queryByTestId('info-banner-error')).toBeNull();
        expect(listedIds(modal), 'the list asked again holds the unselected file').toEqual([DELETABLE_2]);
    });

    // Green today, and after the cure: proves the list answer goes through the generated schema in this harness.
    it('control: a listed file without can_delete is refused by the generated client, and nothing is listed', async () => {
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
        const incomplete: Partial<ListedFile> = listed(DELETABLE_1, true);
        delete incomplete.can_delete;
        server.files = [incomplete];
        const modal = renderModal();

        await waitFor(() => expect(within(modal).getByTestId('info-banner-error')).toBeInTheDocument(), {timeout: 3_000});
        expect(within(modal).queryByTestId('files-table-brim'), 'nothing listed').toBeNull();
        const failure = consoleError.mock.calls.find(([label]) => label === 'Failed to load files:')?.[1] as {cause?: {issues?: Array<{path: unknown[]}>}} | undefined;
        expect(
            failure?.cause?.issues?.map((issue) => issue.path),
            'refused by BRIMFileListItem, for the missing flag',
        ).toContainEqual([0, 'can_delete']);
    });
});
