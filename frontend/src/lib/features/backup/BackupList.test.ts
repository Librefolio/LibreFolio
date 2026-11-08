// @vitest-environment jsdom
/**
 * BackupList — component test (Vitest + jsdom), lot FB-24, written red first against `B6r-fb24-frontend-interface.md` §3.
 *
 * The table of the backups an instance keeps (`GET /backup/instance/jobs`), under the Backup tab of Settings and in the
 * Files page. The real `DataTable` is mounted; the boundaries are the two requests of `./backupApi` (the list and the
 * delete), the clipboard writer, `notify()` and the storage key of the table's preferences.
 *
 * What this file pins:
 *   - the state it publishes on its root, `backup-list`: `data-state` (`loading|ready|error`), `data-busy`/`aria-busy`;
 *     it reads the list on its own at mount, once, and again at every change of `backupListSignal.version`
 *     (`notifyBackupListChanged()`: the card says «read again» when a backup ends or one is deleted);
 *   - the rows, found by the job id they carry (`tbody tr[data-row-id=<job_id>]`) — never by position — with the
 *     cells of their columns (`td[data-column-id=<id>]`): `origin` and `kind` as the i18n key of their value
 *     (`backup.list.origin.<ui|cli|pre-restore|panel>`, `backup.list.kind.<clear|password|sealed>`, the kind from
 *     `backupKind`), `size`, `sha256` as a button `backup-sha-copy-<job_id>` showing the short form and nothing more of
 *     the hash; and the order: the newest backup first, whatever order the server answers in;
 *   - the SHA button copies the WHOLE hash through `writeTextToClipboard` and notifies `backup.list.sha.copied`
 *     `{job_id}` with a toast (the outcome is invisible);
 *   - no selection column: no checkbox, no «select all»;
 *   - the row actions (`row-actions-<job_id>`, the kebab): `download` hands the browser a link to
 *     `instanceBackupFileUrl(job_id)` and notifies `backup.download.started` `{job_id}`; `delete` asks for a
 *     confirmation first (nothing is requested until it is given, and cancelling requests nothing), then calls
 *     `deleteInstanceBackupJob(job_id)`, reads the list again and notifies `backup.deleted` `{job_id}`; a refused delete
 *     notifies `backup.delete.failed` `{code, what: 'remove', job_id}` with an `error` toast;
 *   - a failed read: `data-state="error"`, `backup-list-error` with `data-error-code` (`backupFailureCode`) and
 *     `backup-list-retry`, which reads again; an empty list is `ready` and says `backup.list.empty`;
 *   - `restore` (never on a sealed backup) opens `RestoreKeptModal` for that backup at once, with no confirmation of its
 *     own (A10, T-15): the modal is `RestoreKeptModalStub` here, and goes when it calls `onClose`.
 *
 * The seams. `$lib/i18n` is an identity translator, so every label renders as its i18n key: the assertions name keys,
 * never translated text. `$lib/api` is a client that throws on any request, so nothing reaches the network.
 *
 * Each case loads the component inside itself (`await import`), so that while it does not exist each case fails on its
 * own instead of the whole file on a missing import.
 *
 * What it deliberately does not assert: the formatted date and size, the tooltip that carries the whole hash (a hover
 * delay of the design system's Tooltip — the E2E reads the hash a user can copy), and any CSS class.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

// --- Mocks ----------------------------------------------------------------------------------------------------------

vi.mock('$lib/i18n', () => {
    const identity = readable((key: string) => key);
    return {
        _: identity,
        t: identity,
        locale: writable('en'),
        date: readable((v: unknown) => String(v)),
        time: readable((v: unknown) => String(v)),
        number: readable((v: unknown) => String(v)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano', fr: 'Français', es: 'Español'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

vi.mock('$lib/api', () => {
    const zodiosApi = new Proxy(
        {},
        {
            get: (_target, alias) =>
                typeof alias !== 'string' || alias === 'then'
                    ? undefined
                    : () => {
                          throw new Error(`BackupList.test: a request went through zodiosApi.${alias}`);
                      },
        },
    );
    return {zodiosApi, schemas: {}, axiosInstance: {}, ApiError: class ApiError extends Error {}};
});

vi.mock('./backupApi', async () => {
    const actual = await vi.importActual<typeof import('./backupApi')>('./backupApi');
    return {...actual, listInstanceBackups: vi.fn(), deleteInstanceBackupJob: vi.fn()};
});

vi.mock('$lib/utils/clipboard', () => ({writeTextToClipboard: vi.fn(() => Promise.resolve())}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));
// A10: «Restore» opens a modal of its own, here; what the modal does is RestoreKeptModal.test.ts.
vi.mock('./RestoreKeptModal.svelte', async () => ({default: (await import('$test/harness/RestoreKeptModalStub.svelte')).default}));
// The table keeps its column preferences under a user-scoped key; the real one reaches the authentication store.
vi.mock('$lib/utils/storage', () => ({getUserStorageKey: (key: string) => `backup-list-test-${key}`}));

import {deleteInstanceBackupJob, listInstanceBackups, instanceBackupFileUrl} from './backupApi';
import {writeTextToClipboard} from '$lib/utils/clipboard';
import {notify} from '$lib/stores/app/notify.svelte';

// A literal path would fail the whole file at transform time while the module is missing; a variable path fails each case alone.
const MODULES = {list: './BackupList.svelte', signal: './backupList.svelte'};
const loadList = async () => (await import(/* @vite-ignore */ MODULES.list)).default;
const loadSignal = (): Promise<typeof import('./backupList.svelte')> => import(/* @vite-ignore */ MODULES.signal);

// --- Fixtures -------------------------------------------------------------------------------------------------------

type Entry = Awaited<ReturnType<typeof listInstanceBackups>>[number];

/** A job id: 32 lowercase hex digits, unique per `n`. */
const jobId = (n: number) => n.toString(16).padStart(32, '0');
/** A SHA-256, unique per `n`: its first twelve characters tell the backups apart. */
const sha = (n: number) => `${n.toString(16).padStart(12, '0')}${'ab'.repeat(26)}`;

function entry(n: number, overrides: Partial<Entry> = {}): Entry {
    return {
        job_id: jobId(n),
        status: 'done',
        phase: null,
        done_bytes: 1_048_576,
        total_bytes: 1_048_576,
        created_at: `2026-10-${String(10 + n).padStart(2, '0')}T12:00:00Z`,
        finished_at: `2026-10-${String(10 + n).padStart(2, '0')}T12:01:00Z`,
        file_name: `librefolio-backup-202610${10 + n}-120000.zip`,
        file_size: 1_048_576 * n,
        file_sha256: sha(n),
        warnings: [],
        error_code: null,
        encrypted: false,
        instance_key_included: false,
        sealed: false,
        sealed_recipients: [],
        origin: 'ui',
        ...overrides,
    } as Entry;
}

/** A refusal as the backup routes word it, raised by axios: `detail: {code, message}`. */
function refusal(status: number, code: string) {
    return {isAxiosError: true, message: `Request failed with status code ${status}`, response: {status, data: {detail: {code, message: `refused: ${code}`}}}};
}
const noAnswer = () => ({isAxiosError: true, message: 'Network Error', code: 'ERR_NETWORK', response: undefined});
const codelessAnswer = () => ({isAxiosError: true, message: 'Request failed with status code 500', response: {status: 500, data: {detail: 'Internal Server Error'}}});

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

const api = {
    list: vi.mocked(listInstanceBackups),
    remove: vi.mocked(deleteInstanceBackupJob),
};

// --- Helpers --------------------------------------------------------------------------------------------------------

const list = () => screen.getByTestId('backup-list');

/** The ids of the rows on screen, in the order of the table. */
const rowIds = () => [...list().querySelectorAll('tbody tr[data-row-id]')].map((row) => row.getAttribute('data-row-id'));

function rowOf(id: string): HTMLTableRowElement {
    const row = list().querySelector<HTMLTableRowElement>(`tbody tr[data-row-id="${id}"]`);
    if (!row) throw new Error(`Owned row ${id} not in the table: ${rowIds().join(', ')}`);
    return row;
}

function cellOf(id: string, column: string): HTMLElement {
    const cell = rowOf(id).querySelector<HTMLElement>(`td[data-column-id="${column}"]`);
    if (!cell) throw new Error(`Row ${id} has no ${column} cell`);
    return cell;
}

/** What `notify()` recorded, in order; only the events called `name` when it is given. */
function events(name?: string) {
    return vi
        .mocked(notify)
        .mock.calls.map(([options]) => options)
        .filter((options) => name === undefined || options.name === name);
}

/** Mount the table and wait for its first read to land. */
async function mountReady(entries: Entry[]) {
    api.list.mockResolvedValueOnce(entries);
    const BackupList = await loadList();
    const view = render(BackupList);
    await waitFor(() => expect(list()).toHaveAttribute('data-state', 'ready'));
    return view;
}

/** jsdom has no layout: the kebab gets a rect inside the viewport, or its menu closes as soon as it opens. */
function withLayout(element: HTMLElement): HTMLElement {
    vi.spyOn(element, 'getBoundingClientRect').mockReturnValue({x: 100, y: 100, top: 100, left: 100, right: 124, bottom: 124, width: 24, height: 24, toJSON: () => ({})} as DOMRect);
    return element;
}

/** Open a row's action menu from its kebab, as a user does. */
async function openRowMenu(id: string): Promise<HTMLElement> {
    await fireEvent.click(withLayout(within(rowOf(id)).getByTestId(`row-actions-${id}`)));
    return screen.findByTestId('context-menu');
}

// The first import of the table pulls in the whole DataTable: slower than a case's own 5 s on a loaded machine. It is done once, here.
beforeAll(async () => {
    await loadList();
}, 120_000);

beforeEach(() => {
    // The table keeps its column preferences in localStorage, which this Node's jsdom may not provide: an empty one of
    // its own, as FilesTable.test.ts does.
    vi.stubGlobal('localStorage', {getItem: () => null, setItem: vi.fn(), removeItem: vi.fn()});
    api.list.mockReset();
    api.remove.mockReset();
    vi.mocked(notify).mockReset();
    vi.mocked(writeTextToClipboard).mockClear();
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

// =====================================================================================================================
describe('BackupList — reading the list', () => {
    it('loading: busy while the first read is out; ready and idle once it lands; one read, with no argument', async () => {
        const answer = deferred<Entry[]>();
        api.list.mockReturnValueOnce(answer.promise);
        const BackupList = await loadList();
        render(BackupList);

        expect(list()).toHaveAttribute('data-state', 'loading');
        expect(list()).toHaveAttribute('data-busy', 'true');
        expect(list()).toHaveAttribute('aria-busy', 'true');
        expect(api.list).toHaveBeenCalledTimes(1);

        answer.resolve([entry(1)]);
        await waitFor(() => expect(list()).toHaveAttribute('data-state', 'ready'));

        expect(list()).toHaveAttribute('data-busy', 'false');
        expect(list()).toHaveAttribute('aria-busy', 'false');
        expect(api.list).toHaveBeenCalledTimes(1);
        expect(list().querySelector('tr[data-row-id="' + jobId(1) + '"]')).not.toBeNull();
        expect(screen.queryByTestId('backup-list-error')).toBeNull();
    });

    it('an empty list is ready, says there is no backup, and has no row', async () => {
        await mountReady([]);

        expect(list()).toHaveAttribute('data-state', 'ready');
        expect(list()).toHaveTextContent('backup.list.empty');
        expect(rowIds()).toEqual([]);
        expect(screen.queryByTestId('backup-list-error')).toBeNull();
    });

    it('reads again at every change of the signal, and shows the new backup', async () => {
        await mountReady([entry(1)]);
        const {notifyBackupListChanged} = await loadSignal();
        expect(api.list).toHaveBeenCalledTimes(1);
        api.list.mockResolvedValueOnce([entry(2), entry(1)]);

        notifyBackupListChanged();

        await waitFor(() => expect(api.list).toHaveBeenCalledTimes(2));
        await waitFor(() => expect(rowIds()).toContain(jobId(2)));
        expect(rowIds()).toContain(jobId(1));
        expect(list()).toHaveAttribute('data-state', 'ready');
        expect(list()).toHaveAttribute('data-busy', 'false');
    });

    it('a second change reads a second time', async () => {
        await mountReady([entry(1)]);
        const {notifyBackupListChanged} = await loadSignal();
        api.list.mockResolvedValue([entry(1)]);

        notifyBackupListChanged();
        await waitFor(() => expect(api.list).toHaveBeenCalledTimes(2));
        notifyBackupListChanged();
        await waitFor(() => expect(api.list).toHaveBeenCalledTimes(3));
    });
});

// =====================================================================================================================
describe('BackupList — the rows', () => {
    it('shows the newest backup first, whatever order the server answers in', async () => {
        // entry(n) is created on the (10 + n)th of October: 3 is the newest. The server answers the oldest first here.
        await mountReady([entry(1), entry(3), entry(2)]);

        expect(rowIds()).toEqual([jobId(3), jobId(2), jobId(1)]);
    });

    it('origin and kind: the i18n key of each value, the kind read from encrypted and sealed', async () => {
        await mountReady([entry(1, {origin: 'ui', encrypted: false, sealed: false}), entry(2, {origin: 'cli', encrypted: true, sealed: false}), entry(3, {origin: 'pre-restore', encrypted: true, sealed: true}), entry(4, {origin: 'panel', encrypted: false, sealed: false})]);

        expect(cellOf(jobId(1), 'origin')).toHaveTextContent('backup.list.origin.ui');
        expect(cellOf(jobId(2), 'origin')).toHaveTextContent('backup.list.origin.cli');
        expect(cellOf(jobId(3), 'origin')).toHaveTextContent('backup.list.origin.pre-restore');
        expect(cellOf(jobId(4), 'origin')).toHaveTextContent('backup.list.origin.panel');
        expect(cellOf(jobId(1), 'kind')).toHaveTextContent('backup.list.kind.clear');
        expect(cellOf(jobId(2), 'kind')).toHaveTextContent('backup.list.kind.password');
        expect(cellOf(jobId(3), 'kind')).toHaveTextContent('backup.list.kind.sealed');
        expect(cellOf(jobId(4), 'kind')).toHaveTextContent('backup.list.kind.clear');
    });

    it('size: a size is written; date: a date is written', async () => {
        await mountReady([entry(3)]);

        expect(cellOf(jobId(3), 'size').textContent?.trim(), 'the size of the archive is written').not.toBe('');
        expect(cellOf(jobId(3), 'date').textContent?.trim(), 'the date of the backup is written').not.toBe('');
    });

    it('sha256: a button with the first twelve characters of the hash, and no more of it', async () => {
        await mountReady([entry(5)]);

        const button = within(rowOf(jobId(5))).getByTestId(`backup-sha-copy-${jobId(5)}`);
        expect(button.tagName).toBe('BUTTON');
        expect(cellOf(jobId(5), 'sha256')).toContainElement(button);
        expect(button).toHaveTextContent(sha(5).slice(0, 12));
        expect(button.textContent, 'the hash is shortened').not.toContain(sha(5));
    });

    it('has no selection: no checkbox on a row, no «select all»', async () => {
        await mountReady([entry(1), entry(2)]);

        expect(screen.queryByTestId('dt-select-all')).toBeNull();
        expect(screen.queryByTestId(`dt-row-checkbox-${jobId(1)}`)).toBeNull();
        expect(screen.queryByTestId(`dt-select-cell-${jobId(2)}`)).toBeNull();
    });
});

// =====================================================================================================================
describe('BackupList — the space a backup takes once restored (A10, T-10)', () => {
    it('a backup that recorded it: its size, the parts in the tooltip; one made before: «—», said not known', async () => {
        const parts = {database_bytes: 3_000_000, uploads_bytes: 2_000_000, broker_reports_bytes: 1_000_000, other_bytes: 0};
        await mountReady([entry(1, {content_bytes: 6_000_000, content_parts: parts} as Partial<Entry>), entry(2)]);

        const known = cellOf(jobId(1), 'restored').querySelector('[data-restored]');
        expect(known).toHaveAttribute('data-restored', 'known');
        expect(known, 'the sum of the parts, not the archive').toHaveAttribute('data-bytes', '6000000');
        const unknown = cellOf(jobId(2), 'restored').querySelector('[data-restored]');
        expect(unknown).toHaveAttribute('data-restored', 'unknown');
        expect(unknown).toHaveTextContent('—');
    });
});

describe('BackupList — copying the hash', () => {
    it('copies the whole hash, and notifies backup.list.sha.copied with the job and a toast', async () => {
        await mountReady([entry(5), entry(6)]);

        await fireEvent.click(within(rowOf(jobId(5))).getByTestId(`backup-sha-copy-${jobId(5)}`));

        await waitFor(() => expect(writeTextToClipboard).toHaveBeenCalledTimes(1));
        expect(writeTextToClipboard).toHaveBeenCalledWith(sha(5));
        await waitFor(() => expect(events('backup.list.sha.copied')).toHaveLength(1));
        const [copied] = events('backup.list.sha.copied');
        expect(copied.detail).toEqual({job_id: jobId(5)});
        expect(copied.toast, 'the copy is invisible: a toast is owed').toBeDefined();
    });

    it('copying the hash of one row copies that row’s hash, not another’s', async () => {
        await mountReady([entry(5), entry(6)]);

        await fireEvent.click(within(rowOf(jobId(6))).getByTestId(`backup-sha-copy-${jobId(6)}`));

        await waitFor(() => expect(writeTextToClipboard).toHaveBeenCalledTimes(1));
        expect(writeTextToClipboard).toHaveBeenCalledWith(sha(6));
        expect(writeTextToClipboard).not.toHaveBeenCalledWith(sha(5));
    });
});

// =====================================================================================================================
describe('BackupList — the actions of a row', () => {
    it('the menu of a row offers download and delete', async () => {
        await mountReady([entry(1)]);

        const menu = await openRowMenu(jobId(1));

        expect(within(menu).getByTestId('context-menu-action-download')).toBeInTheDocument();
        expect(within(menu).getByTestId('context-menu-action-delete')).toBeInTheDocument();
    });

    it('download: a link to the archive of that job is followed, and backup.download.started names the job', async () => {
        await mountReady([entry(1), entry(2)]);
        const followed: Array<string | null> = [];
        vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
            followed.push(this.getAttribute('href'));
        });
        const menu = await openRowMenu(jobId(2));

        await fireEvent.click(within(menu).getByTestId('context-menu-action-download'));

        expect(followed).toEqual([instanceBackupFileUrl(jobId(2))]);
        expect(followed[0]).toBe(`/api/v1/backup/instance/jobs/${jobId(2)}/file`);
        expect(events('backup.download.started')).toEqual([expect.objectContaining({name: 'backup.download.started', detail: {job_id: jobId(2)}})]);
        expect(api.remove).not.toHaveBeenCalled();
    });

    it('delete: asks first — nothing is requested until the confirmation is given', async () => {
        await mountReady([entry(1)]);
        const menu = await openRowMenu(jobId(1));

        await fireEvent.click(within(menu).getByTestId('context-menu-action-delete'));

        expect(await screen.findByTestId('confirm-modal-confirm')).toBeInTheDocument();
        expect(api.remove).not.toHaveBeenCalled();
        expect(events('backup.deleted')).toEqual([]);
    });

    it('delete, cancelled: nothing is requested and the row stays', async () => {
        await mountReady([entry(1)]);
        const menu = await openRowMenu(jobId(1));
        await fireEvent.click(within(menu).getByTestId('context-menu-action-delete'));

        await fireEvent.click(await screen.findByTestId('confirm-modal-cancel'));

        await waitFor(() => expect(screen.queryByTestId('confirm-modal-confirm')).toBeNull());
        expect(api.remove).not.toHaveBeenCalled();
        expect(api.list).toHaveBeenCalledTimes(1);
        expect(rowIds()).toContain(jobId(1));
        expect(events('backup.deleted')).toEqual([]);
    });

    it('delete, confirmed: that job is deleted, the list is read again, the row is gone, backup.deleted names the job', async () => {
        await mountReady([entry(2), entry(1)]);
        api.remove.mockResolvedValueOnce(undefined);
        api.list.mockResolvedValueOnce([entry(1)]);
        const menu = await openRowMenu(jobId(2));
        await fireEvent.click(within(menu).getByTestId('context-menu-action-delete'));

        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));

        await waitFor(() => expect(api.remove).toHaveBeenCalledTimes(1));
        expect(api.remove).toHaveBeenCalledWith(jobId(2));
        await waitFor(() => expect(api.list).toHaveBeenCalledTimes(2));
        await waitFor(() => expect(rowIds()).not.toContain(jobId(2)));
        expect(rowIds()).toContain(jobId(1));
        await waitFor(() => expect(events('backup.deleted')).toHaveLength(1));
        expect(events('backup.deleted')[0].detail).toEqual({job_id: jobId(2)});
        expect(events('backup.delete.failed')).toEqual([]);
    });

    it.each<[string, string, () => unknown]>([
        ['network', 'network', noAnswer],
        ['unexpected', 'unexpected', codelessAnswer],
        ['a refusal with a code', 'backup_job_running', () => refusal(409, 'backup_job_running')],
    ])('delete, refused with %s: backup.delete.failed {code: %s, what: remove, job_id} with an error toast; the row is still there', async (_case, code, refused) => {
        await mountReady([entry(1)]);
        api.remove.mockRejectedValueOnce(refused());
        const menu = await openRowMenu(jobId(1));
        await fireEvent.click(within(menu).getByTestId('context-menu-action-delete'));

        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));

        await waitFor(() => expect(events('backup.delete.failed')).toHaveLength(1));
        const [failed] = events('backup.delete.failed');
        expect(failed.detail).toEqual({code, what: 'remove', job_id: jobId(1)});
        expect(failed.toast?.variant).toBe('error');
        expect(events('backup.deleted')).toEqual([]);
        expect(rowIds()).toContain(jobId(1));
    });
});

// =====================================================================================================================
describe('BackupList — a read that fails', () => {
    it.each<[string, string, () => unknown]>([
        ['no answer', 'network', noAnswer],
        ['an answer with no code', 'unexpected', codelessAnswer],
        ['a refusal with a code', 'backup_folder_unusable', () => refusal(500, 'backup_folder_unusable')],
    ])('%s: error state, the code on backup-list-error, a retry', async (_case, code, failure) => {
        api.list.mockRejectedValueOnce(failure());
        const BackupList = await loadList();
        render(BackupList);

        await waitFor(() => expect(list()).toHaveAttribute('data-state', 'error'));

        expect(list()).toHaveAttribute('data-busy', 'false');
        expect(screen.getByTestId('backup-list-error')).toHaveAttribute('data-error-code', code);
        expect(screen.getByTestId('backup-list-retry')).toBeEnabled();
        expect(rowIds()).toEqual([]);
    });

    it('retry reads again; the list that comes is shown and the error is gone', async () => {
        api.list.mockRejectedValueOnce(noAnswer());
        const BackupList = await loadList();
        render(BackupList);
        await waitFor(() => expect(list()).toHaveAttribute('data-state', 'error'));
        api.list.mockResolvedValueOnce([entry(1)]);

        await fireEvent.click(screen.getByTestId('backup-list-retry'));

        await waitFor(() => expect(list()).toHaveAttribute('data-state', 'ready'));
        expect(api.list).toHaveBeenCalledTimes(2);
        expect(screen.queryByTestId('backup-list-error')).toBeNull();
        expect(screen.queryByTestId('backup-list-retry')).toBeNull();
        expect(rowIds()).toEqual([jobId(1)]);
    });

    it('a change of the signal after an error reads again too', async () => {
        api.list.mockRejectedValueOnce(noAnswer());
        const BackupList = await loadList();
        render(BackupList);
        await waitFor(() => expect(list()).toHaveAttribute('data-state', 'error'));
        const {notifyBackupListChanged} = await loadSignal();
        api.list.mockResolvedValueOnce([entry(1)]);

        notifyBackupListChanged();

        await waitFor(() => expect(list()).toHaveAttribute('data-state', 'ready'));
        expect(rowIds()).toEqual([jobId(1)]);
    });
});

// =====================================================================================================================
// C9-9, A10 (T-15) — «Restore» on a kept backup opens its modal, where the list is
// =====================================================================================================================

describe('BackupList — restore a kept backup (C9-9)', () => {
    it('a plain or secure backup offers «Restore»; a sealed one does not', async () => {
        await mountReady([entry(1), entry(2, {encrypted: true}), entry(3, {sealed: true})]);

        expect(within(await openRowMenu(jobId(1))).getByTestId('context-menu-action-restore')).toHaveTextContent('backup.list.actions.restore');
        await fireEvent.keyDown(document, {key: 'Escape'});
        expect(within(await openRowMenu(jobId(3))).queryByTestId('context-menu-action-restore')).toBeNull();
    });

    it('A10: opens the modal of that backup at once, with no «are you sure?»; closed, the modal goes', async () => {
        // T-15: the developer expected a modal, not the restore card filled in, nor a jump to Settings.
        await mountReady([entry(1), entry(2)]);
        expect(screen.queryByTestId('restore-kept-modal-stub')).toBeNull();
        await fireEvent.click(within(await openRowMenu(jobId(2))).getByTestId('context-menu-action-restore'));

        const modal = await screen.findByTestId('restore-kept-modal-stub');
        expect(screen.queryByTestId('confirm-modal-confirm'), 'the modal itself says what a restore does').toBeNull();
        expect(modal).toHaveAttribute('data-job-id', jobId(2));
        expect(modal).toHaveAttribute('data-created-at', entry(2).created_at);

        await fireEvent.click(screen.getByTestId('restore-kept-modal-stub-close'));
        await waitFor(() => expect(screen.queryByTestId('restore-kept-modal-stub')).toBeNull());
    });
});
