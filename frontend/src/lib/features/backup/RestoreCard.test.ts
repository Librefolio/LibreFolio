// @vitest-environment jsdom
/**
 * RestoreCard — the restore card of Settings › Administration › Backup, under the download card (component test,
 * Vitest + jsdom; workstream B, lot B5b). Written red first against `b5b-contract.md` §0 (P8 and P7, which override the
 * rest), §2, §2b, §2c, §3 and §4: the card does not exist yet. Lot B5c (the outcome read with the restart's one-time
 * ticket, and B-17) was written red first in its turn, against its approved contract.
 *
 * The card is the face of `RestoreFlowController` (pinned on its own in restoreFlow.test.ts). What it adds, and what this
 * file pins, is what the user sees and what the machine reads:
 *   - its root `restore-card` publishes `data-state`, `data-error-code` (empty when none), `data-busy` and `aria-busy`;
 *   - `loading`: busy, nothing offered; `idle`: `restore-file-input` (a picker suggesting `.zip`, one file),
 *     `restore-choose` (it opens the picker), `restore-limit` with the limit when there is one (not for 0 or an unknown
 *     limit); the last result only for a restore that rolled back — `restore-last-result` with `data-result` and
 *     `data-reason` —, never for one that was applied (§0.2); `in_progress`: nothing offered;
 *   - `uploading`: `restore-upload-progress` with a progress bar, `restore-cancel-check` aborting the PUT; `checking`:
 *     `restore-check-progress` with `data-phase`, `restore-cancel-check` sending the DELETE; `report`: the modal
 *     `restore-report`, whose `restore-drop` drops the check and whose `restore-confirm` confirms;
 *   - the confirmation restarts at once (§0.1): the modal closes and `restart-overlay` waits; a refused restart leaves the
 *     pending block with the error; a restore found pending at load shows `restore-pending` with `data-waiting` (and
 *     `restore-waiting`, worded by `backup.restore.waiting.<waiting>`, `instance_blocked` included, §0.5),
 *     `restore-restart` and `restore-cancel-pending`; the cancel is `cancelPendingRestore()` alone, then the status read
 *     again: the server drops the checked copy with the cancel, as the command line's `backup pending --cancel` does
 *     (B-17), and the card never calls `deleteRestoreCheck` for it;
 *   - the restart answers a one-time `outcome_ticket` (B5c), and the outcome of that restart is read with it —
 *     `restoreOutcome(ticket)`, without a session —: one case from the confirmation to the outcome, `rolled_back` or
 *     `committed` as answered; the ticket reaches neither `notify()` nor a storage of the browser;
 *   - a success shows no message (§0.2): the overlay keeps waiting as `restored` and `restoreNavigation.toSignIn()` is
 *     called once; a failure shows on the overlay (§0.3), whose `restart-back` reads the status again; `restart-sign-in`
 *     never exists. A restart that comes back on an instance its hosting provider blocked — `restoreOutcome()` answers
 *     `blocked`, the status route itself refused with 423 — is such a failure too (P8, `instance_blocked` included): the
 *     overlay `still_pending` with `data-waiting="instance_blocked"` and `restart-back`, no sign-in, nothing told;
 *   - `failed`: `restore-error` with `data-error-code`; `backup_too_large` refused before anything is sent;
 *   - every event of the controller becomes one `notify()` with its name and detail: `backup.restore.failed` with an
 *     error toast, the others silent (§4);
 *   - the polling stops, and late answers are dropped, once the card is unmounted; BackupTab shows it under the
 *     download card.
 *
 * Additions to §3 this file pins, each one test id or attribute, each one place to rename: the button of `failed` that
 * tries again is `restore-retry` (§2 offers «try again», §3 gives it no test id); `restore-cancel-check` also aborts an
 * upload (§2 offers a cancel while uploading, §3 lists one cancel id); `restore-upload-progress` holds a
 * `role="progressbar"` with `aria-valuenow` in percent, as the backup card's bar does.
 *
 * The seams. `$lib/i18n` renders every key as itself (with its values, when it has any), answers the word list of the
 * confirmation with one word, so any pick is that word, and records every key asked. `./backupApi` keeps its real
 * helpers and swaps the ten restore functions for `vi.fn`, each rejecting a call the case did not expect. A call the
 * card would send and swallow rejects unseen — the best-effort drop of a cancelled restore's copy did, until B-17 —, so
 * the case of the cancel asserts that `deleteRestoreCheck` was never called. `$lib/api` is a client that throws on any
 * request. `notify` is a spy; `restoreNavigation.toSignIn` is a spy on the exported object, so nothing navigates. The
 * clock is fake: the card's controller uses its defaults (`pollMs` 1000, `fastRestartMs` 30 000, `slowAfterMs`
 * 60 000). `sessionStorage` is the environment's own, emptied around every case. Not `localStorage`: Node 26 ships a
 * global one that is unavailable without `--localstorage-file`, and it hides jsdom's (`undefined` here), so a case that
 * inspects it owns an in-memory one, installed with `vi.stubGlobal` before the card exists — a write of the card lands
 * where the case reads it back —, and every case ends with `vi.unstubAllGlobals()`.
 *
 * The components are loaded through `import.meta.glob` in a hook: while the card does not exist, every case fails on its
 * own and names it.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import {readable, writable} from 'svelte/store';
import {tick, type Component} from 'svelte';
import type {z} from 'zod';
import type {schemas} from '$lib/api';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

const i18n = vi.hoisted(() => ({asked: [] as string[]}));

vi.mock('$lib/i18n', () => {
    const translate = (key: string, options?: {values?: Record<string, unknown>}) => {
        i18n.asked.push(key);
        // One word in the list: whatever the modal picks, the word to type is this one.
        if (key === 'backup.restore.confirm.words') return 'violet';
        if (key === 'backup.restore.confirm.word') return 'violet';
        return options?.values ? `${key} ${JSON.stringify(options.values)}` : key;
    };
    const translator = readable(translate);
    return {
        _: translator,
        t: translator,
        locale: writable('en'),
        date: readable((value: unknown) => String(value)),
        time: readable((value: unknown) => String(value)),
        number: readable((value: unknown) => String(value)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it', 'fr', 'es'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano', fr: 'Français', es: 'Español'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT', fr: 'FR', es: 'ES'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

// The card reaches the server only through the restore functions of ./backupApi, mocked below. Any other request would
// come through this client, and fails the case instead of leaving the page.
vi.mock('$lib/api', () => {
    const zodiosApi = new Proxy(
        {},
        {
            get: (_target, alias) =>
                typeof alias !== 'string' || alias === 'then'
                    ? undefined
                    : () => {
                          throw new Error(`RestoreCard.test: a request went through zodiosApi.${alias}`);
                      },
        },
    );
    return {zodiosApi, schemas: {}, axiosInstance: {}, ApiError: class ApiError extends Error {}};
});

vi.mock('./backupApi', async () => {
    const actual = await vi.importActual<Record<string, unknown>>('./backupApi');
    return {
        ...actual,
        getRestoreStatus: vi.fn(),
        uploadRestoreArchive: vi.fn(),
        startRestoreCheck: vi.fn(),
        getRestoreCheck: vi.fn(),
        deleteRestoreCheck: vi.fn(),
        confirmRestore: vi.fn(),
        cancelPendingRestore: vi.fn(),
        requestRestart: vi.fn(),
        probeServer: vi.fn(),
        restoreOutcome: vi.fn(),
        // B4: the download card beside this one in BackupTab may read the options of a secure backup as it mounts.
        getInstanceBackupOptions: vi.fn(() => Promise.resolve({password_rules: [{code: 'min_length', value: 12}, {code: 'uppercase'}, {code: 'lowercase'}, {code: 'digit'}, {code: 'special'}]})),
    };
});

vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));

import * as backupApi from './backupApi';
import {notify} from '$lib/stores/app/notify.svelte';

// --- The contract, as this file uses it -------------------------------------------------------------------------------

type RestoreStatus = z.infer<typeof schemas.RestoreStatus>;
type RestoreStage = z.infer<typeof schemas.RestoreStage>;
type RestoreStageReport = z.infer<typeof schemas.RestoreStageReport>;
type RestoreUpload = z.infer<typeof schemas.RestoreUpload>;
type RollbackReason = NonNullable<RestoreStatus['reason']>;
/** The waiting reasons of §0.5: the generated client does not know `instance_blocked` yet (P7). */
type WaitingReason = NonNullable<RestoreStatus['waiting']> | 'instance_blocked';
type UploadOptions = {onProgress?: (loaded: number, total: number) => void; signal?: AbortSignal};
type RestoreOutcomeAnswer = {kind: 'signed_out'} | {kind: 'status'; status: RestoreStatus} | {kind: 'blocked'} | {kind: 'down'};
/** The answer of an accepted restart (B5c): the status, and the one-time ticket that reads its outcome. Not generated yet. */
type RestoreRestartAccepted = RestoreStatus & {outcome_ticket: string};

interface RestoreRequests {
    getRestoreStatus: () => Promise<RestoreStatus>;
    uploadRestoreArchive: (file: File, options?: UploadOptions) => Promise<RestoreUpload>;
    startRestoreCheck: (uploadId: string) => Promise<RestoreStage>;
    getRestoreCheck: (stageId: string) => Promise<RestoreStage>;
    deleteRestoreCheck: (stageId: string) => Promise<void>;
    /** B5-1b: `ownerUserId`, the owner's account chosen in the report (managed only), `null` when none. */
    confirmRestore: (stageId: string, ownerUserId?: number | null) => Promise<RestoreStatus>;
    cancelPendingRestore: () => Promise<void>;
    requestRestart: () => Promise<RestoreRestartAccepted>;
    probeServer: () => Promise<'up' | 'down'>;
    restoreOutcome: (ticket?: string | null) => Promise<RestoreOutcomeAnswer>;
}

const RESTORE_FUNCTIONS = ['getRestoreStatus', 'uploadRestoreArchive', 'startRestoreCheck', 'getRestoreCheck', 'deleteRestoreCheck', 'confirmRestore', 'cancelPendingRestore', 'requestRestart', 'probeServer', 'restoreOutcome'] as const;

/** The ten restore functions of ./backupApi, as the mock above made them. */
const api = backupApi as unknown as {[K in keyof RestoreRequests]: Mock<RestoreRequests[K]>};

// --- The components ---------------------------------------------------------------------------------------------------

type Loaded = {RestoreCard: Component<Record<string, unknown>>; BackupTab: Component<Record<string, unknown>>; navigation: {toSignIn(): void} | undefined};

const CARD_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./RestoreCard.svelte');
const TAB_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./BackupTab.svelte');
const FLOW_MODULES = import.meta.glob<{restoreNavigation?: {toSignIn(): void}}>('./restoreFlow.svelte.ts');

let loaded: Loaded | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const loadCard = CARD_MODULES['./RestoreCard.svelte'];
        if (!loadCard) throw new Error('src/lib/features/backup/RestoreCard.svelte does not exist yet: Settings › Backup has no restore card (B5b contract §3)');
        const {default: RestoreCard} = await loadCard();
        const {default: BackupTab} = await TAB_MODULES['./BackupTab.svelte']!();
        const loadFlow = FLOW_MODULES['./restoreFlow.svelte.ts'];
        const navigation = loadFlow ? (await loadFlow()).restoreNavigation : undefined;
        loaded = {RestoreCard, BackupTab, navigation};
    } catch (error) {
        loaded = {error};
    }
}, 60_000);

function pieces(): Loaded {
    if (loaded === undefined) throw new Error('the components under test were never loaded: their beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded;
}

// --- Fixtures ---------------------------------------------------------------------------------------------------------

const UPLOAD_ID = '0123456789abcdef0123456789abcdef';
const STAGE_ID = 'fedcba9876543210fedcba9876543210';
const KEY = 'librefolio.backup.restore.stage';
const MIB = 1024 * 1024;
/** The pause of the card's controller (its default). */
const POLL_MS = 1000;
const WORD = 'violet';

const REASONS: RollbackReason[] = ['first_start_failed', 'swap_interrupted', 'swap_failed', 'stage_missing'];
const WAITINGS: WaitingReason[] = ['backup_running', 'other_data_directory', 'server_running', 'instance_blocked'];

type StatusFields = Omit<Partial<RestoreStatus>, 'waiting'> & {waiting?: WaitingReason | null};

function restoreStatus(overrides: StatusFields = {}): RestoreStatus {
    return {state: 'none', stage_id: null, confirmed_at: null, confirmed_by: null, backup_created_at: null, backup_app_version: null, action: null, finished_at: null, reason: null, waiting: null, upload_limit_mb: 500, ...overrides} as RestoreStatus;
}

const none = (overrides: StatusFields = {}) => restoreStatus({state: 'none', ...overrides});
const confirmedFields: StatusFields = {stage_id: STAGE_ID, confirmed_at: '2026-10-16T11:20:00Z', confirmed_by: 'admin', backup_created_at: '2026-10-15T12:00:00Z', backup_app_version: '0.9.0', action: 'same'};
const pending = (overrides: StatusFields = {}) => restoreStatus({state: 'pending', ...confirmedFields, ...overrides});
const committed = () => restoreStatus({state: 'committed', ...confirmedFields, finished_at: '2026-10-16T11:21:00Z'});
const rolledBack = (reason: RollbackReason) => restoreStatus({state: 'rolled_back', ...confirmedFields, finished_at: '2026-10-16T11:21:00Z', reason});

/** A ticket as the server makes it (`secrets.token_urlsafe(32)`), one per accepted restart (B5c). */
const TICKET = 'kq8Z3vR-wT0yN5mB_xH2cL7pJ4sF9dG1eA6uK0iO3rY';
/** What an accepted restart answers (B5c): the restore still pending, and the ticket that reads its outcome. */
const accepted = (ticket: string = TICKET): RestoreRestartAccepted => ({...pending(), outcome_ticket: ticket});

/** B4 (§5): what a report says of the archive's encryption and of the plugin secrets. Written out until the client is generated again. */
type ReportB4Fields = {encrypted: boolean; secrets_unreadable: {system: number; user: number}; secrets_rekeyed: number};
/** B4 (§5): an upload says what was stored, a zip or an envelope. Written out until the client is generated again. */
type Upload = RestoreUpload & {kind: 'zip' | 'envelope'};

function report(overrides: Partial<RestoreStageReport & ReportB4Fields> = {}): RestoreStageReport & ReportB4Fields {
    return {
        backup_created_at: '2026-10-15T12:00:00Z',
        backup_app_version: '0.9.0',
        backup_origin: 'ui',
        backup_revision: 'c0ffee000001',
        app_version: '0.9.0',
        head_revision: 'c0ffee000001',
        action: 'same',
        migrations: [],
        post_migration_fixes: [],
        tables: {asset: {before: 12, after: 12}},
        foreign_key_violations_before: 0,
        foreign_key_violations_after: 0,
        files: 3,
        files_size: 2048,
        database_size: MIB,
        instance_key_included: false,
        administrators: ['giulia.bianchi'],
        warnings: [],
        blockers: [],
        control_totals: 'same',
        control_totals_differences: [],
        control_totals_differences_count: 0,
        restorable: true,
        expires_at: '2026-10-16T12:00:00Z',
        encrypted: false,
        secrets_unreadable: {system: 0, user: 0},
        secrets_rekeyed: 0,
        ...overrides,
    };
}

function stage(overrides: Partial<RestoreStage> = {}): RestoreStage {
    return {stage_id: STAGE_ID, status: 'running', phase: 'checking', done_bytes: 0, total_bytes: 0, created_at: '2026-10-16T09:00:00Z', finished_at: null, error_code: null, report: null, ...overrides};
}

const runningStage = (overrides: Partial<RestoreStage> = {}) => stage({status: 'running', ...overrides});
const doneStage = (answer: RestoreStageReport = report()) => stage({status: 'done', phase: null, done_bytes: 4096, total_bytes: 4096, finished_at: '2026-10-16T09:01:00Z', report: answer});
const uploaded = (overrides: Partial<Upload> = {}): Upload => ({upload_id: UPLOAD_ID, size: 4096, kind: 'zip', ...overrides});

/** An archive of `size` bytes: the size is set on the File, so a large one costs no memory. */
function archive(size = 4096, name = 'librefolio-backup-20261015-120000.zip'): File {
    const file = new File(['PK\u0003\u0004'], name, {type: 'application/zip'});
    Object.defineProperty(file, 'size', {value: size});
    return file;
}

/** A refusal as the backup routes word it, raised by axios: `detail: {code, message, …}`. */
function refusal(status: number, code: string, extra: Record<string, unknown> = {}) {
    return {isAxiosError: true, message: `Request failed with status code ${status}`, response: {status, data: {detail: {code, message: `refused: ${code}`, ...extra}}}};
}

const noAnswer = () => ({isAxiosError: true, message: 'Network Error', code: 'ERR_NETWORK', response: undefined});
const canceled = () => ({isAxiosError: true, name: 'CanceledError', message: 'canceled', code: 'ERR_CANCELED', __CANCEL__: true, response: undefined});

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** An in-memory Web Storage the case can read back — what it holds, and every write — for a global the case owns (`vi.stubGlobal`). */
function memoryStorage() {
    const items = new Map<string, string>();
    return {
        items,
        get length() {
            return items.size;
        },
        key: vi.fn((index: number) => [...items.keys()][index] ?? null),
        getItem: vi.fn((key: string) => items.get(key) ?? null),
        setItem: vi.fn((key: string, value: string) => {
            items.set(key, String(value));
        }),
        removeItem: vi.fn((key: string) => {
            items.delete(key);
        }),
        clear: vi.fn(() => {
            items.clear();
        }),
    };
}

// --- Helpers ----------------------------------------------------------------------------------------------------------

const card = () => screen.getByTestId('restore-card');

/** What the card recorded through `notify()`, in order; only the events called `name` when it is given. */
function events(name?: string) {
    return vi
        .mocked(notify)
        .mock.calls.map(([options]) => options)
        .filter((options) => name === undefined || options.name === name);
}

/** Let every answer already given reach the card: a real macrotask drains the promise chains, a tick flushes Svelte. */
async function settle(): Promise<void> {
    await vi.advanceTimersByTimeAsync(0);
    await tick();
}

/** Move the clock by `ms`, firing what is due on the way, and let the answers reach the card. */
async function elapse(ms: number): Promise<void> {
    await vi.advanceTimersByTimeAsync(ms);
    await tick();
}

/** The progress bar of a progress block: the block itself when it is the bar. */
function progressbar(block: HTMLElement): HTMLElement {
    return block.getAttribute('role') === 'progressbar' ? block : within(block).getByRole('progressbar');
}

/** The card mounted, its status read with `status`. */
async function mount(status: RestoreStatus = none()) {
    api.getRestoreStatus.mockResolvedValueOnce(status);
    const view = render(pieces().RestoreCard);
    await settle();
    return view;
}

/** A file chosen in the picker. */
async function choose(file: File): Promise<void> {
    await fireEvent.change(screen.getByTestId('restore-file-input'), {target: {files: [file]}});
    await settle();
}

/** An archive uploaded and its check started: `checking`, its first read due in a second. */
async function checkingCard() {
    const view = await mount();
    api.uploadRestoreArchive.mockResolvedValueOnce(uploaded());
    api.startRestoreCheck.mockResolvedValueOnce(runningStage({phase: 'checking'}));
    await choose(archive());
    expect(card(), 'precondition: the check runs').toHaveAttribute('data-state', 'checking');
    return view;
}

/** The check done: the report open. */
async function reportCard(answer: RestoreStageReport = report()) {
    const view = await checkingCard();
    api.getRestoreCheck.mockResolvedValueOnce(doneStage(answer));
    await elapse(POLL_MS);
    expect(card(), 'precondition: the report is shown').toHaveAttribute('data-state', 'report');
    return view;
}

/** The word typed in the modal and the restore confirmed. */
async function typeAndConfirm(): Promise<void> {
    await fireEvent.input(screen.getByTestId('restore-confirm-input'), {target: {value: WORD}});
    await fireEvent.click(screen.getByTestId('restore-confirm'));
    await settle();
}

/** `probeServer()` answers what `server.state` holds, whenever it is asked. */
function serve(initial: 'up' | 'down') {
    const server = {state: initial};
    api.probeServer.mockImplementation(() => Promise.resolve(server.state));
    return server;
}

/** A restore found pending, its restart asked from the pending block and accepted with `TICKET`: the overlay waits. */
async function restartFromPending(initial: 'up' | 'down') {
    const view = await mount(pending());
    const server = serve(initial);
    api.requestRestart.mockResolvedValueOnce(accepted());
    await fireEvent.click(screen.getByTestId('restore-restart'));
    await settle();
    expect(screen.getByTestId('restart-overlay'), 'precondition: the overlay waits').toHaveAttribute('data-outcome', 'waiting');
    return {...view, server};
}

/** The restart seen happening: down for three seconds, then up for two. */
async function serverRestarts(server: {state: 'up' | 'down'}): Promise<void> {
    server.state = 'down';
    await elapse(3 * POLL_MS);
    server.state = 'up';
    await elapse(2 * POLL_MS);
}

let toSignIn: Mock<() => void> | undefined;

beforeEach(() => {
    vi.useFakeTimers();
    sessionStorage.clear();
    i18n.asked.length = 0;
    vi.mocked(notify).mockReset();
    for (const name of RESTORE_FUNCTIONS) {
        const fn = api[name] as unknown as Mock<(...args: unknown[]) => Promise<unknown>>;
        fn.mockReset();
        fn.mockImplementation(() => Promise.reject(new Error(`${name}(): a request this case did not expect`)));
    }
    const navigation = loaded && !('error' in loaded) ? loaded.navigation : undefined;
    toSignIn = navigation && typeof navigation.toSignIn === 'function' ? (vi.spyOn(navigation, 'toSignIn').mockImplementation(() => undefined) as unknown as Mock<() => void>) : undefined;
});

afterEach(() => {
    // Unmount on the fake clock that scheduled the card's timers, then hand the real one back.
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    sessionStorage.clear();
});

/** An action is not offered: its control is absent, or there and disabled. */
function notOffered(testId: string, why: string): void {
    const control = screen.queryByTestId(testId);
    expect(control === null || control.hasAttribute('disabled'), `${testId} is offered ${why}`).toBe(true);
}

// =====================================================================================================================
describe('RestoreCard — loading and idle', () => {
    it('loading: busy, nothing offered, until the status answers', async () => {
        const answer = deferred<RestoreStatus>();
        api.getRestoreStatus.mockReturnValueOnce(answer.promise);

        render(pieces().RestoreCard);
        await tick();

        expect(api.getRestoreStatus).toHaveBeenCalledTimes(1);
        expect(card()).toHaveAttribute('data-state', 'loading');
        expect(card()).toHaveAttribute('data-busy', 'true');
        expect(card()).toHaveAttribute('aria-busy', 'true');
        expect(card()).toHaveAttribute('data-error-code', '');
        notOffered('restore-choose', 'before the status is known');
        notOffered('restore-file-input', 'before the status is known');
        for (const absent of ['restore-pending', 'restore-error', 'restore-last-result', 'restore-report', 'restart-overlay']) {
            expect(screen.queryByTestId(absent), `${absent} while the status is read`).toBeNull();
        }

        answer.resolve(none());
        await settle();

        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(card()).toHaveAttribute('data-busy', 'false');
    });

    it('idle: the picker of one file suggesting .zip, restore-choose, the limit; no request but the status, nothing told', async () => {
        await mount(none({upload_limit_mb: 500}));

        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(card()).toHaveAttribute('aria-busy', 'false');
        expect(card()).toHaveAttribute('data-error-code', '');
        const input = screen.getByTestId('restore-file-input');
        expect(input).toHaveAttribute('type', 'file');
        expect(input.getAttribute('accept') ?? '', 'the picker suggests .zip').toContain('.zip');
        expect(input, 'one archive at a time').not.toHaveAttribute('multiple');
        expect(input).not.toBeDisabled();
        expect(screen.getByTestId('restore-choose')).toBeInTheDocument();
        expect(screen.getByTestId('restore-limit').textContent, 'the limit is not shown').toContain('500');
        for (const absent of ['restore-last-result', 'restore-pending', 'restore-error', 'restore-upload-progress', 'restore-check-progress', 'restore-report', 'restart-overlay']) {
            expect(screen.queryByTestId(absent), `${absent} on an idle card`).toBeNull();
        }
        expect(api.getRestoreStatus).toHaveBeenCalledTimes(1);
        expect(api.getRestoreCheck).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
    });

    it.each<[string, number | null]>([
        ['no limit (0)', 0],
        ['a limit that cannot be read', null],
    ])('%s: no restore-limit, the picker still offered', async (_case, limit) => {
        await mount(none({upload_limit_mb: limit}));

        expect(screen.queryByTestId('restore-limit')).toBeNull();
        expect(screen.getByTestId('restore-file-input')).not.toBeDisabled();
        expect(screen.getByTestId('restore-choose')).toBeInTheDocument();
    });

    it('restore-choose opens the picker', async () => {
        await mount();
        const opened = vi.fn((event: Event) => event.preventDefault());
        screen.getByTestId('restore-file-input').addEventListener('click', opened);

        await fireEvent.click(screen.getByTestId('restore-choose'));

        expect(opened).toHaveBeenCalledTimes(1);
    });

    it('after a restore that was applied: no last result — a success shows no message (§0.2)', async () => {
        await mount(committed());

        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(screen.queryByTestId('restore-last-result')).toBeNull();
        expect(i18n.asked.filter((key) => key.startsWith('backup.restore.last.committed'))).toEqual([]);
    });

    it.each(REASONS)('after a restore that rolled back (%s): restore-last-result with data-result and data-reason, and the picker', async (reason) => {
        await mount(rolledBack(reason));

        expect(card()).toHaveAttribute('data-state', 'idle');
        const last = screen.getByTestId('restore-last-result');
        expect(last).toHaveAttribute('data-result', 'rolled_back');
        expect(last).toHaveAttribute('data-reason', reason);
        expect(screen.getByTestId('restore-choose')).toBeInTheDocument();
    });

    it('a restore being applied: in_progress, not busy, nothing offered', async () => {
        await mount(restoreStatus({state: 'in_progress', ...confirmedFields}));

        expect(card()).toHaveAttribute('data-state', 'in_progress');
        expect(card()).toHaveAttribute('data-busy', 'false');
        for (const action of ['restore-choose', 'restore-file-input', 'restore-restart', 'restore-cancel-pending', 'restore-retry', 'restore-cancel-check']) {
            notOffered(action, 'while a start applies the restore');
        }
    });
});

describe('RestoreCard — the upload and the check', () => {
    it('a file chosen: uploading with its progress and the cancel; then checking through the phases; then the report', async () => {
        await mount();
        const upload = deferred<RestoreUpload>();
        let options: UploadOptions | undefined;
        api.uploadRestoreArchive.mockImplementationOnce((_file, given) => {
            options = given;
            return upload.promise;
        });
        api.startRestoreCheck.mockResolvedValueOnce(runningStage({phase: 'checking'}));
        api.getRestoreCheck.mockResolvedValueOnce(runningStage({phase: 'unpacking', done_bytes: 1024, total_bytes: 4096}));
        api.getRestoreCheck.mockResolvedValueOnce(runningStage({phase: 'upgrading'}));
        api.getRestoreCheck.mockResolvedValueOnce(runningStage({phase: 'verifying'}));
        api.getRestoreCheck.mockResolvedValueOnce(doneStage());
        const file = archive(1024);

        await choose(file);

        expect(api.uploadRestoreArchive).toHaveBeenCalledTimes(1);
        expect(api.uploadRestoreArchive.mock.calls[0][0], 'the chosen File is sent').toBe(file);
        expect(card()).toHaveAttribute('data-state', 'uploading');
        expect(card()).toHaveAttribute('data-busy', 'true');
        expect(screen.getByTestId('restore-cancel-check')).toBeInTheDocument();
        notOffered('restore-choose', 'during an upload');

        options?.onProgress?.(256, 1024);
        await settle();
        expect(progressbar(screen.getByTestId('restore-upload-progress'))).toHaveAttribute('aria-valuenow', '25');

        upload.resolve(uploaded({size: 1024}));
        await settle();

        expect(api.startRestoreCheck).toHaveBeenCalledWith(UPLOAD_ID);
        expect(card()).toHaveAttribute('data-state', 'checking');
        expect(card()).toHaveAttribute('data-busy', 'true');
        expect(screen.queryByTestId('restore-upload-progress')).toBeNull();
        expect(screen.getByTestId('restore-check-progress')).toHaveAttribute('data-phase', 'checking');
        expect(screen.getByTestId('restore-cancel-check')).toBeInTheDocument();
        for (const phase of ['unpacking', 'upgrading', 'verifying']) {
            await elapse(POLL_MS);
            expect(screen.getByTestId('restore-check-progress')).toHaveAttribute('data-phase', phase);
        }

        await elapse(POLL_MS);

        expect(card()).toHaveAttribute('data-state', 'report');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(screen.getByTestId('restore-report')).toBeInTheDocument();
        expect(screen.queryByTestId('restore-check-progress')).toBeNull();
        expect(sessionStorage.getItem(KEY), 'the report must survive a reload').toBe(STAGE_ID);
    });

    it('restore-cancel-check while uploading: the PUT aborted, back to idle, no failure told', async () => {
        await mount();
        api.getRestoreStatus.mockResolvedValue(none());
        let signal: AbortSignal | undefined;
        api.uploadRestoreArchive.mockImplementationOnce((_file, options) => {
            signal = options?.signal;
            return new Promise<RestoreUpload>((_resolve, reject) => {
                signal?.addEventListener('abort', () => reject(canceled()));
            });
        });
        await choose(archive());
        expect(card(), 'precondition: the upload is out').toHaveAttribute('data-state', 'uploading');

        await fireEvent.click(screen.getByTestId('restore-cancel-check'));
        await settle();

        expect(signal?.aborted, 'the PUT was not aborted').toBe(true);
        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(screen.getByTestId('restore-choose')).toBeInTheDocument();
        expect(api.startRestoreCheck).not.toHaveBeenCalled();
        expect(events('backup.restore.failed')).toEqual([]);
    });

    it('restore-cancel-check while checking: the DELETE of the check, then idle; cancelled told silently', async () => {
        await checkingCard();
        api.deleteRestoreCheck.mockResolvedValueOnce(undefined);
        api.getRestoreStatus.mockResolvedValue(none());

        await fireEvent.click(screen.getByTestId('restore-cancel-check'));
        await settle();

        expect(api.deleteRestoreCheck).toHaveBeenCalledWith(STAGE_ID);
        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(sessionStorage.getItem(KEY)).toBeNull();
        expect(events('backup.restore.cancelled')).toEqual([{name: 'backup.restore.cancelled', detail: {what: 'check'}}]);
    });

    it('a file over the limit: failed with backup_too_large before anything is sent', async () => {
        await mount(none({upload_limit_mb: 1}));

        await choose(archive(MIB + 1));

        expect(api.uploadRestoreArchive, 'a file over the limit was sent').not.toHaveBeenCalled();
        expect(card()).toHaveAttribute('data-state', 'failed');
        expect(card()).toHaveAttribute('data-error-code', 'backup_too_large');
        expect(screen.getByTestId('restore-error')).toHaveAttribute('data-error-code', 'backup_too_large');
    });

    it('the server refuses the archive as too large (413): restore-error with backup_too_large and the limit it named', async () => {
        await mount(none({upload_limit_mb: null}));
        api.uploadRestoreArchive.mockRejectedValueOnce(refusal(413, 'backup_too_large', {limit_mb: 250}));

        await choose(archive());

        expect(card()).toHaveAttribute('data-state', 'failed');
        const error = screen.getByTestId('restore-error');
        expect(error).toHaveAttribute('data-error-code', 'backup_too_large');
        expect(error.textContent, 'the limit the server named is not shown').toContain('250');
    });
});

// =====================================================================================================================
describe('RestoreCard — the report and the confirmation (§0.1)', () => {
    it('restore-drop: the DELETE of the check, then idle, the report closed; cancelled told silently', async () => {
        await reportCard();
        api.deleteRestoreCheck.mockResolvedValueOnce(undefined);
        api.getRestoreStatus.mockResolvedValue(none());

        await fireEvent.click(screen.getByTestId('restore-drop'));
        await settle();

        expect(api.deleteRestoreCheck).toHaveBeenCalledWith(STAGE_ID);
        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(screen.queryByTestId('restore-report')).toBeNull();
        expect(sessionStorage.getItem(KEY)).toBeNull();
        expect(events('backup.restore.cancelled')).toEqual([{name: 'backup.restore.cancelled', detail: {what: 'check'}}]);
    });

    it('restore-confirm with the word typed: confirmed, then restarted at once — the report closed, the overlay waiting; both told silently', async () => {
        await reportCard();
        const confirmation = deferred<RestoreStatus>();
        api.confirmRestore.mockReturnValueOnce(confirmation.promise);
        api.requestRestart.mockResolvedValueOnce(accepted());
        serve('down');

        await typeAndConfirm();

        // B5-1b (interface §8): no owner to choose → the confirmation names none, `null`.
        expect(api.confirmRestore).toHaveBeenCalledWith(STAGE_ID, null);
        expect(card()).toHaveAttribute('data-state', 'confirming');
        expect(card()).toHaveAttribute('data-busy', 'true');
        notOffered('restore-confirm', 'while the confirmation is out');

        confirmation.resolve(pending());
        await settle();

        expect(api.requestRestart, 'no «Restart now» step after a confirmation').toHaveBeenCalledTimes(1);
        expect(card()).toHaveAttribute('data-state', 'restarting');
        expect(card()).toHaveAttribute('data-busy', 'true');
        expect(screen.queryByTestId('restore-report')).toBeNull();
        expect(screen.getByTestId('restart-overlay')).toHaveAttribute('data-outcome', 'waiting');
        expect(events('backup.restore.confirmed')).toEqual([{name: 'backup.restore.confirmed', detail: {stage_id: STAGE_ID}}]);
        expect(events('backup.restore.restart.requested')).toEqual([{name: 'backup.restore.restart.requested', detail: {}}]);
        expect(
            events().filter(({toast}) => toast !== undefined),
            'a step of a restore that goes on was toasted',
        ).toEqual([]);
    });

    it('the restart refused after the confirmation: the pending block with the error, restore-restart and restore-cancel-pending, no overlay', async () => {
        await reportCard();
        api.confirmRestore.mockResolvedValueOnce(pending());
        api.requestRestart.mockRejectedValueOnce(noAnswer());

        await typeAndConfirm();

        expect(card()).toHaveAttribute('data-state', 'pending');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(card()).toHaveAttribute('data-error-code', 'network');
        expect(screen.getByTestId('restore-pending')).toBeInTheDocument();
        expect(screen.getByTestId('restore-error')).toHaveAttribute('data-error-code', 'network');
        expect(screen.getByTestId('restore-restart')).toBeEnabled();
        expect(screen.getByTestId('restore-cancel-pending')).toBeEnabled();
        expect(screen.queryByTestId('restart-overlay')).toBeNull();
        expect(screen.queryByTestId('restore-report')).toBeNull();
    });
});

describe('RestoreCard — a restore found pending (§0.1, §0.5)', () => {
    it('waiting for nothing: restore-pending with an empty data-waiting and no restore-waiting; restart and cancel offered, no picker', async () => {
        await mount(pending());

        expect(card()).toHaveAttribute('data-state', 'pending');
        expect(card()).toHaveAttribute('data-busy', 'false');
        const block = screen.getByTestId('restore-pending');
        expect(block).toHaveAttribute('data-waiting', '');
        expect(within(block).queryByTestId('restore-waiting')).toBeNull();
        expect(screen.getByTestId('restore-restart')).toBeEnabled();
        expect(screen.getByTestId('restore-cancel-pending')).toBeEnabled();
        notOffered('restore-choose', 'while a restore waits for the next start');
    });

    it.each(WAITINGS)('waiting for %s: data-waiting, and restore-waiting worded by backup.restore.waiting.<waiting>', async (waiting) => {
        await mount(pending({waiting}));

        const block = screen.getByTestId('restore-pending');
        expect(block).toHaveAttribute('data-waiting', waiting);
        expect(within(block).getByTestId('restore-waiting')).toHaveTextContent(`backup.restore.waiting.${waiting}`);
        expect(screen.getByTestId('restore-restart')).toBeEnabled();
        expect(screen.getByTestId('restore-cancel-pending')).toBeEnabled();
    });

    it('restore-cancel-pending: cancelling, busy, nothing offered while the DELETE is out; then the status read again: idle; cancelled told silently — and no deleteRestoreCheck: the server drops the checked copy with the cancel (B-17)', async () => {
        await mount(pending());
        const answer = deferred<void>();
        api.cancelPendingRestore.mockReturnValueOnce(answer.promise);
        api.getRestoreStatus.mockResolvedValueOnce(none());

        await fireEvent.click(screen.getByTestId('restore-cancel-pending'));
        await settle();

        expect(api.cancelPendingRestore).toHaveBeenCalledTimes(1);
        expect(card()).toHaveAttribute('data-state', 'cancelling');
        expect(card()).toHaveAttribute('data-busy', 'true');
        notOffered('restore-restart', 'while the cancel is out');
        notOffered('restore-cancel-pending', 'while the cancel is out');

        answer.resolve();
        await settle();

        expect(api.getRestoreStatus, 'the status is read again').toHaveBeenCalledTimes(2);
        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(card()).toHaveAttribute('data-error-code', '');
        expect(screen.queryByTestId('restore-pending')).toBeNull();
        expect(events('backup.restore.cancelled')).toEqual([{name: 'backup.restore.cancelled', detail: {what: 'pending'}}]);
        expect(events('backup.restore.failed')).toEqual([]);
        expect(api.deleteRestoreCheck, 'the copy of the cancelled restore was dropped by the card: since B-17 the cancel drops it on the server').not.toHaveBeenCalled();
    });
});

describe('RestoreCard — the restart and its outcome (§0.2, §0.3)', () => {
    it('restore-restart: restarting, busy, the overlay waiting; restart.requested told silently', async () => {
        await restartFromPending('down');

        expect(api.requestRestart).toHaveBeenCalledTimes(1);
        expect(card()).toHaveAttribute('data-state', 'restarting');
        expect(card()).toHaveAttribute('data-busy', 'true');
        expect(screen.getByTestId('restart-overlay')).toHaveAttribute('data-slow', 'false');
        expect(events('backup.restore.restart.requested')).toEqual([{name: 'backup.restore.restart.requested', detail: {}}]);
    });

    it.each<[string, RestoreStatus, string, number]>([
        ['rolled back: the overlay says why, no sign-in', {state: 'rolled_back', reason: 'swap_failed', waiting: null}, 'rolled_back', 0],
        ['committed: restored, on to the sign-in page', {state: 'committed', reason: null, waiting: null}, 'restored', 1],
    ])('confirmed, restarted with the outcome ticket the restart answered, the server down then up: restoreOutcome(ticket), without a session (B5c) — %s', async (_case, answered, outcome, signIns) => {
        // Owned by the case, before the card exists: a write to localStorage lands where it is read back below.
        const local = memoryStorage();
        vi.stubGlobal('localStorage', local);
        await reportCard();
        const server = serve('down');
        api.confirmRestore.mockResolvedValueOnce(pending());
        api.requestRestart.mockResolvedValueOnce(accepted(TICKET));
        // What the outcome route answers: its three fields, nothing else.
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: answered});

        await typeAndConfirm();
        expect(screen.getByTestId('restart-overlay'), 'precondition: the restart was accepted, the overlay waits').toHaveAttribute('data-outcome', 'waiting');
        expect(api.restoreOutcome, 'the server has not restarted yet: nothing to read').not.toHaveBeenCalled();

        await serverRestarts(server);

        expect(api.restoreOutcome.mock.calls, 'the outcome was read without the ticket of the restart').toEqual([[TICKET]]);
        const overlay = screen.getByTestId('restart-overlay');
        expect(overlay).toHaveAttribute('data-outcome', outcome);
        expect(overlay).toHaveAttribute('data-reason', answered.reason ?? '');
        expect(toSignIn).toHaveBeenCalledTimes(signIns);
        expect(JSON.stringify(vi.mocked(notify).mock.calls), 'notify() was told the ticket').not.toContain(TICKET);
        expect(localStorage, 'precondition: the localStorage read back is the one the case owns').toBe(local);
        expect(
            local.setItem.mock.calls.flat().filter((value) => value.includes(TICKET)),
            'the ticket was written to localStorage',
        ).toEqual([]);
        for (const [name, store] of [
            ['sessionStorage', sessionStorage],
            ['localStorage', localStorage],
        ] as const) {
            const values = Array.from({length: store.length}, (_, index) => store.getItem(store.key(index) ?? '') ?? '');
            expect(
                values.filter((value) => value.includes(TICKET)),
                `the ticket was written to ${name}`,
            ).toEqual([]);
        }
    });

    it('a success: no message — the overlay keeps waiting as restored, restoreNavigation.toSignIn() once, no sign-in link', async () => {
        const {server} = await restartFromPending('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'signed_out'});
        expect(toSignIn, 'restoreFlow.svelte.ts exports no restoreNavigation.toSignIn() (§0.2)').toBeDefined();

        await serverRestarts(server);

        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('restart-overlay')).toHaveAttribute('data-outcome', 'restored');
        expect(toSignIn).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('restart-sign-in'), 'restart-sign-in no longer exists (§0.6)').toBeNull();
        expect(screen.queryByTestId('restart-back')).toBeNull();
        expect(events('backup.restore.restored')).toEqual([{name: 'backup.restore.restored', detail: {}}]);
        expect(
            events().filter(({toast}) => toast !== undefined),
            'a success was toasted',
        ).toEqual([]);
    });

    it.each(REASONS)('rolled back (%s): the overlay tells it; restart-back reads the status again, and the card shows the last result', async (reason) => {
        const {server} = await restartFromPending('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: rolledBack(reason)});

        await serverRestarts(server);

        const overlay = screen.getByTestId('restart-overlay');
        expect(overlay).toHaveAttribute('data-outcome', 'rolled_back');
        expect(overlay).toHaveAttribute('data-reason', reason);
        expect(toSignIn).not.toHaveBeenCalled();
        expect(events('backup.restore.rolled_back')).toEqual([{name: 'backup.restore.rolled_back', detail: {reason}}]);

        api.getRestoreStatus.mockResolvedValueOnce(rolledBack(reason));
        await fireEvent.click(screen.getByTestId('restart-back'));
        await settle();

        expect(api.getRestoreStatus, 'back to the tab reads the status again').toHaveBeenCalledTimes(2);
        expect(screen.queryByTestId('restart-overlay')).toBeNull();
        expect(card()).toHaveAttribute('data-state', 'idle');
        const last = screen.getByTestId('restore-last-result');
        expect(last).toHaveAttribute('data-result', 'rolled_back');
        expect(last).toHaveAttribute('data-reason', reason);
    });

    it('still pending, waiting for the unblock of the instance (P7): the overlay tells it; restart-back shows the pending block again', async () => {
        const {server} = await restartFromPending('down');
        api.restoreOutcome.mockResolvedValueOnce({kind: 'status', status: pending({waiting: 'instance_blocked'})});

        await serverRestarts(server);

        const overlay = screen.getByTestId('restart-overlay');
        expect(overlay).toHaveAttribute('data-outcome', 'still_pending');
        expect(overlay).toHaveAttribute('data-waiting', 'instance_blocked');
        expect(toSignIn).not.toHaveBeenCalled();

        api.getRestoreStatus.mockResolvedValueOnce(pending({waiting: 'instance_blocked'}));
        await fireEvent.click(screen.getByTestId('restart-back'));
        await settle();

        expect(screen.queryByTestId('restart-overlay')).toBeNull();
        expect(card()).toHaveAttribute('data-state', 'pending');
        expect(screen.getByTestId('restore-pending')).toHaveAttribute('data-waiting', 'instance_blocked');
    });

    it('confirmed, restarted, and the restarted server refuses the status because its hosting provider blocked it (blocked, P8): the failure on the same screen — the overlay still_pending, waiting for the unblock, with restart-back; no sign-in, nothing told', async () => {
        await reportCard();
        const server = serve('down');
        api.confirmRestore.mockResolvedValueOnce(pending());
        api.requestRestart.mockResolvedValueOnce(accepted());
        api.restoreOutcome.mockResolvedValueOnce({kind: 'blocked'});

        await typeAndConfirm();
        expect(screen.getByTestId('restart-overlay'), 'precondition: the restart was accepted, the overlay waits').toHaveAttribute('data-outcome', 'waiting');
        vi.mocked(notify).mockClear();

        await serverRestarts(server);

        expect(api.restoreOutcome).toHaveBeenCalledTimes(1);
        const overlay = screen.getByTestId('restart-overlay');
        expect(overlay, 'a restart that came back on a blocked instance is a failure on the same screen').toHaveAttribute('data-outcome', 'still_pending');
        expect(overlay).toHaveAttribute('data-waiting', 'instance_blocked');
        expect(screen.getByTestId('restart-back')).toBeInTheDocument();
        expect(toSignIn).not.toHaveBeenCalled();
        expect(notify, 'a restore not applied is told by the overlay alone: no failure, no toast').not.toHaveBeenCalled();
    });

    it('a minute without the server: data-slow true, still waiting', async () => {
        await restartFromPending('down');

        await elapse(62 * POLL_MS);

        const overlay = screen.getByTestId('restart-overlay');
        expect(overlay).toHaveAttribute('data-outcome', 'waiting');
        expect(overlay).toHaveAttribute('data-slow', 'true');
    });
});

// =====================================================================================================================
describe('RestoreCard — a failure, and trying again', () => {
    it('a status read with no answer: failed with network, restore-error; restore-retry reads the status again', async () => {
        api.getRestoreStatus.mockRejectedValueOnce(noAnswer());
        render(pieces().RestoreCard);
        await settle();

        expect(card()).toHaveAttribute('data-state', 'failed');
        expect(card()).toHaveAttribute('data-error-code', 'network');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(screen.getByTestId('restore-error')).toHaveAttribute('data-error-code', 'network');

        api.getRestoreStatus.mockResolvedValueOnce(none());
        await fireEvent.click(screen.getByTestId('restore-retry'));
        await settle();

        expect(api.getRestoreStatus).toHaveBeenCalledTimes(2);
        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(card()).toHaveAttribute('data-error-code', '');
        expect(screen.queryByTestId('restore-error')).toBeNull();
    });
});

describe('RestoreCard — notify(): every event of the controller, the failures toasted (§4)', () => {
    it('a whole success, from the upload to restored: each event once, in order, with its detail, none toasted', async () => {
        await mount();
        const server = serve('down');
        api.uploadRestoreArchive.mockResolvedValueOnce(uploaded());
        api.startRestoreCheck.mockResolvedValueOnce(runningStage());
        api.getRestoreCheck.mockResolvedValueOnce(doneStage());
        api.confirmRestore.mockResolvedValueOnce(pending());
        api.requestRestart.mockResolvedValueOnce(accepted());
        api.restoreOutcome.mockResolvedValueOnce({kind: 'signed_out'});

        await choose(archive());
        await elapse(POLL_MS);
        await typeAndConfirm();
        await serverRestarts(server);

        expect(events().map(({name, detail}) => [name, detail])).toEqual([
            ['backup.restore.uploaded', {upload_id: UPLOAD_ID, size: 4096}],
            ['backup.restore.staged', {stage_id: STAGE_ID, restorable: true, action: 'same'}],
            ['backup.restore.confirmed', {stage_id: STAGE_ID}],
            ['backup.restore.restart.requested', {}],
            ['backup.restore.restored', {}],
        ]);
        expect(
            events().filter(({toast}) => toast !== undefined),
            'a step of a success was toasted',
        ).toEqual([]);
    });

    async function overTheLimit(): Promise<void> {
        await mount(none({upload_limit_mb: 1}));
        await choose(archive(MIB + 1));
    }

    async function checkRefused(): Promise<void> {
        await mount();
        api.uploadRestoreArchive.mockResolvedValueOnce(uploaded());
        api.startRestoreCheck.mockRejectedValueOnce(refusal(409, 'restore_busy'));
        await choose(archive());
    }

    async function confirmationRefused(): Promise<void> {
        await reportCard();
        api.confirmRestore.mockRejectedValueOnce(refusal(410, 'restore_stage_expired'));
        await typeAndConfirm();
    }

    async function restartRefused(): Promise<void> {
        await mount(pending());
        api.requestRestart.mockRejectedValueOnce(noAnswer());
        await fireEvent.click(screen.getByTestId('restore-restart'));
        await settle();
    }

    it.each<[string, () => Promise<void>, string, string]>([
        ['a file over the limit', overTheLimit, 'backup_too_large', 'upload'],
        ['a check that cannot start', checkRefused, 'restore_busy', 'check'],
        ['a confirmation refused', confirmationRefused, 'restore_stage_expired', 'confirm'],
        ['a restart refused', restartRefused, 'network', 'restart'],
    ])('%s: backup.restore.failed {code, what}, with an error toast', async (_case, arrive, code, what) => {
        await arrive();

        const failed = events('backup.restore.failed');
        expect(failed).toHaveLength(1);
        expect(failed[0].detail).toEqual({code, what});
        expect(failed[0].toast?.variant).toBe('error');
        expect(typeof failed[0].toast?.message, 'the toast has no message').toBe('string');
        expect(screen.getByTestId('restore-error')).toHaveAttribute('data-error-code', code);
    });
});

describe('RestoreCard — unmounted', () => {
    it('stops the polling: no read after unmount, no timer left, nothing told', async () => {
        const {unmount} = await checkingCard();
        vi.mocked(notify).mockClear();

        unmount();

        expect(vi.getTimerCount()).toBe(0);
        await vi.advanceTimersByTimeAsync(20 * POLL_MS);
        expect(api.getRestoreCheck).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
    });

    it('drops a read that answers after unmount', async () => {
        const {unmount} = await checkingCard();
        const read = deferred<RestoreStage>();
        api.getRestoreCheck.mockReturnValueOnce(read.promise);
        await elapse(POLL_MS);
        expect(api.getRestoreCheck, 'precondition: a read is out').toHaveBeenCalledTimes(1);
        vi.mocked(notify).mockClear();

        unmount();
        read.resolve(doneStage());
        await settle();

        expect(notify, 'a card that is gone told the end of a check').not.toHaveBeenCalled();
    });
});

describe('BackupTab', () => {
    it('shows the restore card under the download card', async () => {
        api.getRestoreStatus.mockResolvedValueOnce(none());

        render(pieces().BackupTab);
        await settle();

        const tab = screen.getByTestId('backup-tab');
        const download = within(tab).getByTestId('backup-download-card');
        const restoreCard = within(tab).getByTestId('restore-card');
        expect(download.compareDocumentPosition(restoreCard) & Node.DOCUMENT_POSITION_FOLLOWING, 'the restore card is not under the download card').toBeTruthy();
        expect(restoreCard).toHaveAttribute('data-state', 'idle');
    });
});

// =====================================================================================================================
// B4 — an envelope (.lfbk): its password asked on the card before anything is sent (written red first)
// =====================================================================================================================

/*
 * The contract (B4 brief §5, §7):
 *   - the picker suggests `.lfbk` as well as `.zip`;
 *   - an envelope chosen (its first bytes `LFBK`): `data-state="password"`, not busy, nothing sent; the card shows
 *     `restore-password-form` with `restore-password` (a password field), `restore-password-submit` and
 *     `restore-password-cancel`;
 *   - submitted: the archive sent once, then its check started with the upload id and the password
 *     (`startRestoreCheck(uploadId, password)`); `wrong_password` brings the form back with `restore-password-error`
 *     (`data-error-code`, worded by `backup.restore.errors.<code>`), and the next password checks the same upload — the
 *     archive is not sent again; cancel goes back to `idle` with the picker, nothing sent;
 *   - an envelope refused as damaged or unsupported fails as any check that cannot start, with its own sentence
 *     (`backup.restore.errors.envelope_damaged`, `…envelope_unsupported`); the check's first phase is `decrypting`, with
 *     its label (`backup.restore.phase.decrypting`).
 *
 * The envelope is told apart by the real `isEnvelopeFile` of ./backupApi (the mock above keeps the module's own
 * helpers): the File's bytes decide. Every fixture carries B4's fields: `kind` on an upload, `encrypted`,
 * `secrets_unreadable` and `secrets_rekeyed` on a report.
 *
 * Red today: the picker suggests `.zip` alone; an envelope is sent at once like a zip, so no password is ever asked;
 * the card has no phase `decrypting` and no sentence for the four codes of an envelope.
 */

/** An envelope as the server writes it (B4 §1): `LFBK`, then the rest of its header — version 1, scrypt, log2(n) 15, r 8, p 1. */
function envelope(name = 'librefolio-backup-20261016-230000.lfbk'): File {
    return new File(['LFBK\u0001\u0001\u000f\u0008\u0001'], name, {type: 'application/octet-stream'});
}

const PASSWORD = 'Correct-Horse-Battery-9';
const OTHER_PASSWORD = 'Staple-Battery-Horse-7';
/** B4's first phase of the check of an envelope: the generated client does not know it yet. */
const DECRYPTING = 'decrypting' as string as NonNullable<RestoreStage['phase']>;

/** Type `password` in the form and submit it. */
async function submitPassword(password: string): Promise<void> {
    await fireEvent.input(screen.getByTestId('restore-password'), {target: {value: password}});
    await fireEvent.click(screen.getByTestId('restore-password-submit'));
    await settle();
}

/** The card mounted, an envelope chosen: the form asks for its password. */
async function passwordCard(file: File = envelope()) {
    const view = await mount();
    await choose(file);
    expect(card(), 'precondition: the password of the envelope is asked').toHaveAttribute('data-state', 'password');
    return view;
}

describe('B4 — RestoreCard: an envelope and its password', () => {
    it('the picker suggests .lfbk as well as .zip', async () => {
        await mount();

        const suggested = (screen.getByTestId('restore-file-input').getAttribute('accept') ?? '').split(',').map((token) => token.trim());
        expect(suggested, 'an envelope cannot be chosen from the picker').toContain('.lfbk');
        expect(suggested).toContain('.zip');
    });

    it('an envelope chosen: data-state password, not busy, the password form — nothing sent yet', async () => {
        await mount();

        await choose(envelope());

        expect(card()).toHaveAttribute('data-state', 'password');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(card()).toHaveAttribute('data-error-code', '');
        const form = screen.getByTestId('restore-password-form');
        expect(within(form).getByTestId('restore-password')).toHaveAttribute('type', 'password');
        expect(within(form).getByTestId('restore-password-submit')).toBeInTheDocument();
        expect(within(form).getByTestId('restore-password-cancel')).toBeInTheDocument();
        expect(screen.queryByTestId('restore-password-error'), 'no error before a password was tried').toBeNull();
        expect(api.uploadRestoreArchive, 'the envelope was sent before its password was asked').not.toHaveBeenCalled();
        expect(api.startRestoreCheck).not.toHaveBeenCalled();
    });

    it('submitted: the archive sent once, then checked with the password; wrong_password brings the form back with restore-password-error, and the next password checks the same upload without sending the archive again', async () => {
        const file = envelope();
        await passwordCard(file);
        api.uploadRestoreArchive.mockResolvedValueOnce(uploaded({kind: 'envelope', size: file.size}));
        api.startRestoreCheck.mockRejectedValueOnce(refusal(400, 'wrong_password'));

        await submitPassword(PASSWORD);

        expect(api.uploadRestoreArchive).toHaveBeenCalledTimes(1);
        expect(api.uploadRestoreArchive.mock.calls[0][0], 'the File chosen is sent').toBe(file);
        expect(api.startRestoreCheck.mock.calls).toEqual([[UPLOAD_ID, PASSWORD]]);
        expect(card()).toHaveAttribute('data-state', 'password');
        expect(card()).toHaveAttribute('data-error-code', 'wrong_password');
        const error = screen.getByTestId('restore-password-error');
        expect(error).toHaveAttribute('data-error-code', 'wrong_password');
        expect(error).toHaveTextContent('backup.restore.errors.wrong_password');
        expect(screen.getByTestId('restore-password-form')).toBeInTheDocument();

        api.startRestoreCheck.mockResolvedValueOnce(runningStage({phase: DECRYPTING}));
        await submitPassword(OTHER_PASSWORD);

        expect(api.uploadRestoreArchive, 'the archive was sent again: the upload was not kept').toHaveBeenCalledTimes(1);
        expect(api.startRestoreCheck.mock.calls).toEqual([
            [UPLOAD_ID, PASSWORD],
            [UPLOAD_ID, OTHER_PASSWORD],
        ]);
        expect(card()).toHaveAttribute('data-state', 'checking');
        expect(screen.queryByTestId('restore-password-form')).toBeNull();
        expect(
            vi.mocked(notify).mock.calls.filter(([options]) => [PASSWORD, OTHER_PASSWORD].some((password) => JSON.stringify(options).includes(password))),
            'a notification told the password',
        ).toEqual([]);
    });

    it('restore-password-cancel: back to idle with the picker, nothing sent', async () => {
        await passwordCard();

        await fireEvent.click(screen.getByTestId('restore-password-cancel'));
        await settle();

        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(card()).toHaveAttribute('data-error-code', '');
        expect(screen.queryByTestId('restore-password-form')).toBeNull();
        expect(screen.getByTestId('restore-choose')).toBeInTheDocument();
        expect(api.uploadRestoreArchive).not.toHaveBeenCalled();
        expect(api.startRestoreCheck).not.toHaveBeenCalled();
    });

    it.each<[string, number]>([
        ['envelope_damaged', 400],
        ['envelope_unsupported', 409],
    ])('an envelope refused as %s: failed, restore-error with the code and its own sentence', async (code, status) => {
        const file = envelope();
        await passwordCard(file);
        api.uploadRestoreArchive.mockResolvedValueOnce(uploaded({kind: 'envelope', size: file.size}));
        api.startRestoreCheck.mockRejectedValueOnce(refusal(status, code));

        await submitPassword(PASSWORD);

        expect(card()).toHaveAttribute('data-state', 'failed');
        const error = screen.getByTestId('restore-error');
        expect(error).toHaveAttribute('data-error-code', code);
        expect(error).toHaveTextContent(`backup.restore.errors.${code}`);
        expect(error, 'the code fell back on the unexpected sentence').not.toHaveTextContent('backup.restore.errors.unexpected');
    });

    it('the check of an envelope: the phase decrypting, with its label and its share', async () => {
        const file = envelope();
        await passwordCard(file);
        api.uploadRestoreArchive.mockResolvedValueOnce(uploaded({kind: 'envelope', size: file.size}));
        api.startRestoreCheck.mockResolvedValueOnce(runningStage({phase: DECRYPTING, done_bytes: 1024, total_bytes: 4096}));

        await submitPassword(PASSWORD);

        const progress = screen.getByTestId('restore-check-progress');
        expect(progress).toHaveAttribute('data-phase', 'decrypting');
        expect(progress).toHaveTextContent('backup.restore.phase.decrypting');
        expect(progressbar(progress)).toHaveAttribute('aria-valuenow', '25');
    });
});

// =====================================================================================================================
// B4b — the password of an envelope is not the account's (B-25)
// =====================================================================================================================

/*
 * The contract (B4b brief §3, frontend): the restore card's `restore-password` keeps `autocomplete="off"`. The password
 * of an envelope is the one a backup was made with, and `current-password` would have a password manager offer the
 * account's. Green today: the guard that keeps it so.
 */

describe('B4b — RestoreCard: the password of an envelope keeps autocomplete="off" (B-25)', () => {
    it('restore-password says autocomplete="off": current-password would offer the password of the account (green today: the guard)', async () => {
        await passwordCard();

        const field = within(screen.getByTestId('restore-password-form')).getByTestId('restore-password');
        expect(field, 'precondition: the password field of the envelope').toHaveAttribute('type', 'password');
        expect(field, "an envelope's password, never the account's").toHaveAttribute('autocomplete', 'off');
    });
});

// =====================================================================================================================
// B-16 — a server that never stops: the card hands the flag to the overlay (written red first)
// =====================================================================================================================

/*
 * The contract (B-16 brief §2): RestoreCard passes `notStopping={controller.notStopping}` to the overlay; `onBack` stays
 * `() => controller.load()`, after which the card shows the restore waiting, with «Restart now» and «Cancel the restore».
 * This file renders the overlay through the real controller over the faked API, on fake timers and the controller's
 * defaults (`pollMs` 1 000, `fastRestartMs` 30 000, `slowAfterMs` 60 000): a server up all along, the restore pending at
 * every read, sixty seconds after the restart. Red today: the overlay publishes no `data-not-stopping`.
 */
describe('B-16 — RestoreCard: a server that never stops', () => {
    it('up all along, the restore pending at every read: slowAfterMs after the restart the overlay says the server has not stopped; its restart-back reads the status again — the restore waiting, to restart or cancel', async () => {
        await restartFromPending('up');
        api.restoreOutcome.mockResolvedValue({kind: 'status', status: pending()});

        await elapse(60_000 - 1);
        expect(screen.getByTestId('restart-overlay'), 'not before slowAfterMs after the restart').toHaveAttribute('data-not-stopping', 'false');
        await elapse(2 * POLL_MS + 1);
        const overlay = screen.getByTestId('restart-overlay');
        expect(overlay).toHaveAttribute('data-not-stopping', 'true');
        expect(overlay).toHaveAttribute('data-outcome', 'waiting');
        expect(screen.getByTestId('restart-not-stopped')).toBeInTheDocument();

        api.getRestoreStatus.mockResolvedValueOnce(pending());
        await fireEvent.click(screen.getByTestId('restart-back'));
        await settle();

        expect(screen.queryByTestId('restart-overlay'), 'back to the tab').toBeNull();
        expect(card()).toHaveAttribute('data-state', 'pending');
        expect(screen.getByTestId('restore-restart')).toBeInTheDocument();
        expect(screen.getByTestId('restore-cancel-pending')).toBeInTheDocument();
    });
});

// =====================================================================================================================
// B-32 — a refused cancel of a pending restore keeps the pending block (written red first)
// =====================================================================================================================

/*
 * The contract (B-32 §1): a refused `DELETE /restore/pending`, other than 404 `restore_not_pending`, leaves the
 * controller `pending` with the error, as a refused restart does; the card keeps its pending block, `restore-error`
 * with the code beside it, and both actions on offer again. Red today: the controller ends `failed`, so the card shows
 * the failed screen, with `restore-retry` and `restore-choose` — an archive whose confirmation the server would refuse
 * with `restore_already_pending`, since the restore still waits.
 */
describe('B-32 — RestoreCard: a refused cancel of a pending restore', () => {
    it('500 restore_cancel_failed: restore-pending and restore-error together, restore-restart and restore-cancel-pending enabled, no restore-retry, no restore-choose; the status not read again, no deleteRestoreCheck, failed told once with an error toast', async () => {
        await mount(pending());
        api.cancelPendingRestore.mockRejectedValueOnce(refusal(500, 'restore_cancel_failed'));

        await fireEvent.click(screen.getByTestId('restore-cancel-pending'));
        await settle();

        expect(api.cancelPendingRestore).toHaveBeenCalledTimes(1);
        expect(card()).toHaveAttribute('data-error-code', 'restore_cancel_failed');
        expect(card(), 'the restore still waits: the pending block, with the error').toHaveAttribute('data-state', 'pending');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(screen.getByTestId('restore-pending')).toBeInTheDocument();
        expect(screen.getByTestId('restore-error')).toHaveAttribute('data-error-code', 'restore_cancel_failed');
        expect(screen.getByTestId('restore-restart')).toBeEnabled();
        expect(screen.getByTestId('restore-cancel-pending')).toBeEnabled();
        expect(screen.queryByTestId('restore-retry'), "the failed screen's retry, while the restore still waits").toBeNull();
        notOffered('restore-choose', 'while a restore waits for the next start');
        expect(api.getRestoreStatus, 'the status is not read again').toHaveBeenCalledTimes(1);
        expect(api.deleteRestoreCheck, 'the copy of a restore still pending was dropped').not.toHaveBeenCalled();
        const failed = events('backup.restore.failed');
        expect(failed).toHaveLength(1);
        expect(failed[0].detail).toEqual({code: 'restore_cancel_failed', what: 'cancel'});
        expect(failed[0].toast?.variant).toBe('error');
    });
});

// =====================================================================================================================
// B5-1b — the owner's choice when confirming a restore (interface B-b51 §8; written red first)
// =====================================================================================================================

/*
 * The contract: the card wires `RestoreReportModal`'s `onConfirm(ownerUserId)` to `controller.confirm(ownerUserId)`, so
 * the owner chosen in A's `OwnerChoiceModal` reaches `confirmRestore(stage_id, ownerUserId)`. A report with no
 * `owner_choice` confirms with `null` (the case above). The four refusals of the owner's choice are the card's
 * `restore-error` with their code, worded by `backup.restore.errors.<code>`: `owner_choice_required`,
 * `owner_choice_invalid`, `owner_email_not_set` keep the check (`restore-retry` brings the report back),
 * `owner_conflict` forgets it (`restore-retry` → idle).
 *
 * OwnerChoiceModal is workstream A's (a stand-in until the merge): driven only through `owner-choice-option`
 * (`data-user-id`), `owner-choice-confirm` and `owner-choice-cancel`.
 *
 * Red today: the report modal confirms at once with no owner modal, and the card drops the argument.
 */

/** The generated type also admits an array (an artefact of the OpenAPI union): the object is the contract. */
type OwnerChoice = Exclude<NonNullable<RestoreStageReport['owner_choice']>, unknown[]>;

const CHOSEN_OWNER = 7;

function ownerChoice(): OwnerChoice {
    return {
        required: true,
        owner_email: 'owner@example.org',
        forced_user_id: null,
        candidates: [
            {user_id: 3, username: 'giulia.bianchi', email: 'giulia@example.org', owner_email: false, administrator: true, is_superuser: true, is_active: true},
            {user_id: CHOSEN_OWNER, username: 'operator7', email: null, owner_email: false, administrator: true, is_superuser: true, is_active: true},
        ],
    };
}

const ownerModal = () => screen.getByTestId('owner-choice-modal');

/** The report of a managed instance, the word typed and confirmed: the owner modal open, nothing sent. */
async function ownerModalCard() {
    const view = await reportCard(report({owner_choice: ownerChoice()}));
    await typeAndConfirm();
    expect(screen.getByTestId('owner-choice-modal'), 'precondition: the owner modal is open').toBeInTheDocument();
    expect(api.confirmRestore, 'confirmed before the owner was chosen').not.toHaveBeenCalled();
    return view;
}

/** The owner `CHOSEN_OWNER` picked and confirmed in the owner modal. */
async function chooseOwner(): Promise<void> {
    const options = within(ownerModal())
        .getAllByTestId('owner-choice-option')
        .filter((option) => option.getAttribute('data-user-id') === String(CHOSEN_OWNER));
    expect(options, `precondition: the user ${CHOSEN_OWNER} is offered`).toHaveLength(1);
    await fireEvent.click(options[0]);
    await fireEvent.click(within(ownerModal()).getByTestId('owner-choice-confirm'));
    await settle();
}

describe('B5-1b — RestoreCard: the owner chosen goes with the confirmation', () => {
    it('an administrator chosen: confirmRestore(stage_id, id) once, then the restart at once — the overlay waiting, no modal left', async () => {
        await ownerModalCard();
        api.confirmRestore.mockResolvedValueOnce(pending());
        api.requestRestart.mockResolvedValueOnce(accepted());
        serve('down');

        await chooseOwner();

        expect(api.confirmRestore).toHaveBeenCalledTimes(1);
        expect(api.confirmRestore).toHaveBeenCalledWith(STAGE_ID, CHOSEN_OWNER);
        expect(api.requestRestart).toHaveBeenCalledTimes(1);
        expect(card()).toHaveAttribute('data-state', 'restarting');
        expect(screen.getByTestId('restart-overlay')).toHaveAttribute('data-outcome', 'waiting');
        expect(screen.queryByTestId('owner-choice-modal')).toBeNull();
        expect(screen.queryByTestId('restore-report')).toBeNull();
    });

    it('owner-choice-cancel: nothing sent, the card still on its report', async () => {
        await ownerModalCard();

        await fireEvent.click(within(ownerModal()).getByTestId('owner-choice-cancel'));
        await settle();

        expect(screen.queryByTestId('owner-choice-modal')).toBeNull();
        expect(api.confirmRestore).not.toHaveBeenCalled();
        expect(card()).toHaveAttribute('data-state', 'report');
        expect(screen.getByTestId('restore-report')).toBeInTheDocument();
    });

    it.each(['owner_choice_required', 'owner_choice_invalid', 'owner_email_not_set'])('409 %s: restore-error with the code, worded by backup.restore.errors.<code>; restore-retry brings the report back', async (code) => {
        await ownerModalCard();
        api.confirmRestore.mockRejectedValueOnce(refusal(409, code));

        await chooseOwner();

        expect(card()).toHaveAttribute('data-state', 'failed');
        expect(screen.getByTestId('restore-error')).toHaveAttribute('data-error-code', code);
        expect(api.requestRestart).not.toHaveBeenCalled();
        expect(i18n.asked, 'the refusal is not worded by its own sentence').toContain(`backup.restore.errors.${code}`);
        expect(sessionStorage.getItem(KEY), 'the check is kept for another choice').toBe(STAGE_ID);

        api.getRestoreStatus.mockResolvedValueOnce(none());
        api.getRestoreCheck.mockResolvedValueOnce(doneStage(report({owner_choice: ownerChoice()})));
        await fireEvent.click(screen.getByTestId('restore-retry'));
        await settle();

        expect(card()).toHaveAttribute('data-state', 'report');
        expect(screen.getByTestId('restore-report')).toBeInTheDocument();
    });

    it('409 owner_conflict: restore-error with the code, worded by backup.restore.errors.owner_conflict, the check forgotten; restore-retry → idle', async () => {
        await ownerModalCard();
        api.confirmRestore.mockRejectedValueOnce(refusal(409, 'owner_conflict'));

        await chooseOwner();

        expect(card()).toHaveAttribute('data-state', 'failed');
        expect(screen.getByTestId('restore-error')).toHaveAttribute('data-error-code', 'owner_conflict');
        expect(i18n.asked).toContain('backup.restore.errors.owner_conflict');
        expect(sessionStorage.getItem(KEY), 'a check that cannot be confirmed is still remembered').toBeNull();

        const readsBefore = api.getRestoreCheck.mock.calls.length;
        api.getRestoreStatus.mockResolvedValueOnce(none());
        await fireEvent.click(screen.getByTestId('restore-retry'));
        await settle();

        expect(api.getRestoreCheck.mock.calls.length, 'the forgotten check was read again').toBe(readsBefore);
        expect(card()).toHaveAttribute('data-state', 'idle');
    });
});
