// @vitest-environment jsdom
/**
 * BackupDownloadCard — component test (Vitest + jsdom), plus the BackupTab that hosts it.
 *
 * The card is the face of `BackupJobController` (tested on its own in backupJob.test.ts). What the card adds, and what
 * this file pins, is what the user sees and what the machine reads:
 *   - the state it publishes on its root: `data-state` (`idle|loading|starting|running|done|deleting|failed`),
 *     `data-error-code`, `data-busy`/`aria-busy`;
 *   - which part is on screen in each state: `backup-loading` while a followed job is read (never `backup-progress`),
 *     `backup-progress` while a backup starts or runs (indeterminate until the size is known, `aria-valuenow` after),
 *     `backup-ready` with the download link, the delete button and the retention note once done — and, while the
 *     archive is being deleted, `backup-deleting` in place of the link and the button, no action anywhere (decision
 *     3); one `backup-warning` per warning code; `backup-error` with its code, in `failed` and in `done` beside the
 *     archive still on offer after a refused start or delete (decision 1); `backup-recheck` only in `failed` with a job
 *     still followed, after a read with no usable answer (`network`, `unexpected`) or a refused start (decision 1,
 *     revised) — never from `done`, never after a delete, never with nothing followed;
 *   - the events of `notify()`: `backup.created` (a toast only when the archive has warnings, variant `warning`), once
 *     per job and only for a job started or seen running here (decision 2); `backup.failed` for a refused start, a
 *     failed read or a failed job, `backup.delete.failed` for a refused delete — both with `{code, what, job_id}` and an
 *     `error` toast; `backup.deleted` and `backup.download.started` (silent); none for a job picked up after a reload;
 *   - since B-8 (the developer, 19/10; the last group): a start refused by a running backup that the 409 names shows the
 *     busy sentence and never that backup's id or origin — following it, as before, when it is a `ui` one and nothing
 *     is on offer — and writes one `console.warn` with its details.
 *
 * The seams. `$lib/i18n` is an identity translator, so every label renders as its i18n key: the assertions name keys,
 * never translated text. `./backupApi` keeps its real helpers (the error-code readers, the file URL) and swaps the three
 * requests for `vi.fn`; `$lib/api` is replaced by a client that throws on any request, so nothing reaches the
 * network and the generated client is never loaded. `notify` is a spy. The clock is fake: the card's controller reads
 * a running job every second (its defaults: `pollMs` 1000, five failed reads in a row before it gives up), so a poll
 * is one `advanceTimersByTimeAsync`. `sessionStorage` is the real jsdom one, emptied around every test: it is where
 * the card finds the job of a previous page.
 *
 * What it deliberately does not assert: the translated sentences, the formatted size and date inside
 * `backup.download.readyDetails` (the identity translator drops the values), and any CSS class.
 */
import {afterEach, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import {readable, writable} from 'svelte/store';
import {tick} from 'svelte';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

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

// The card reaches the server only through the three requests of ./backupApi, mocked below. Any other request would
// come through this client, and fails the test instead of leaving the page.
vi.mock('$lib/api', () => {
    const zodiosApi = new Proxy(
        {},
        {
            get: (_target, alias) =>
                typeof alias !== 'string' || alias === 'then'
                    ? undefined
                    : () => {
                          throw new Error(`BackupDownloadCard.test: a request went through zodiosApi.${alias}`);
                      },
        },
    );
    return {zodiosApi, schemas: {}, axiosInstance: {}, ApiError: class ApiError extends Error {}};
});

// B4: the rules of a secure archive's password, as this file's server answers `GET /backup/instance/options` — A's
// five with twelve characters, in an order of their own, so that a card drawing rules of its own would be seen.
const b4 = vi.hoisted(() => ({
    options: {password_rules: [{code: 'special'}, {code: 'digit'}, {code: 'lowercase'}, {code: 'uppercase'}, {code: 'min_length', value: 12}]},
}));

vi.mock('./backupApi', async () => {
    const actual = await vi.importActual<typeof import('./backupApi')>('./backupApi');
    return {
        ...actual,
        startInstanceBackup: vi.fn(),
        getInstanceBackupJob: vi.fn(),
        deleteInstanceBackupJob: vi.fn(),
        // B4: the card may read the options as soon as it mounts: every case of this file gets the same answer.
        getInstanceBackupOptions: vi.fn(() => Promise.resolve(b4.options)),
    };
});

vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));

import BackupDownloadCard from './BackupDownloadCard.svelte';
import BackupTab from './BackupTab.svelte';
import {deleteInstanceBackupJob, getInstanceBackupJob, startInstanceBackup, type InstanceBackupJob} from './backupApi';
import {BACKUP_JOB_STORAGE_KEY} from './backupJob.svelte';
import {notify} from '$lib/stores/app/notify.svelte';

// --- Fixtures -------------------------------------------------------------------------------------------------------

const JOB_ID = '0123456789abcdef0123456789abcdef';
const KEY = BACKUP_JOB_STORAGE_KEY;
const FILE_NAME = 'librefolio-backup-20261015-120000.zip';
const FILE_SIZE = 7_340_032;
/** The pause of the card's controller (its default). */
const POLL_MS = 1000;
/** Five failed reads in a row (the default) come after 1 + 2 + 3 + 4 + 5 pauses. */
const POLLING_GIVES_UP_AFTER = 15 * POLL_MS;

/** B4 (§4): every job says whether its archive is encrypted. Written out until the client is generated again from the B4 backend. */
type Job = InstanceBackupJob & {encrypted: boolean};

function job(overrides: Partial<Job> = {}): Job {
    return {
        job_id: JOB_ID,
        status: 'running',
        phase: 'preparing',
        done_bytes: 0,
        total_bytes: 0,
        created_at: '2026-10-15T12:00:00Z',
        finished_at: null,
        file_name: null,
        file_size: null,
        warnings: [],
        error_code: null,
        encrypted: false,
        instance_key_included: false,
        ...overrides,
    };
}

const running = (overrides: Partial<Job> = {}) => job({status: 'running', ...overrides});

const done = (overrides: Partial<Job> = {}) => job({status: 'done', phase: null, done_bytes: FILE_SIZE, total_bytes: FILE_SIZE, finished_at: '2026-10-15T12:03:00Z', file_name: FILE_NAME, file_size: FILE_SIZE, ...overrides});

const failedJob = (errorCode: InstanceBackupJob['error_code']) => job({status: 'failed', phase: null, finished_at: '2026-10-15T12:03:00Z', error_code: errorCode});

/** A refusal as the backup routes word it, raised by axios: `detail: {code, message}`. */
function refusal(status: number, code: string) {
    return {isAxiosError: true, message: `Request failed with status code ${status}`, response: {status, data: {detail: {code, message: `refused: ${code}`}}}};
}

/** No answer came: axios rejects with no `response`. */
const noAnswer = () => ({isAxiosError: true, message: 'Network Error', code: 'ERR_NETWORK', response: undefined});

/** An answer without a code: FastAPI's default 500. */
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
    start: vi.mocked(startInstanceBackup),
    get: vi.mocked(getInstanceBackupJob),
    remove: vi.mocked(deleteInstanceBackupJob),
};

// --- Helpers --------------------------------------------------------------------------------------------------------

const card = () => screen.getByTestId('backup-download-card');
const progressBar = () => within(screen.getByTestId('backup-progress')).getByRole('progressbar');

/** The whole text of an element is this i18n key (the identity translator renders keys). */
const exactly = (key: string) => new RegExp(`^${key.replaceAll('.', '\\.')}$`);

/** What the card recorded through `notify()`, in order; only the events called `name` when it is given. */
function events(name?: string) {
    return vi
        .mocked(notify)
        .mock.calls.map(([options]) => options)
        .filter((options) => name === undefined || options.name === name);
}

/** Let every answer already given reach the card: a real macrotask drains the promise chains, a tick flushes Svelte. */
async function settle() {
    await vi.advanceTimersByTimeAsync(0);
    await tick();
}

/** Move the clock by `ms`, firing the reads due on the way, and let their answers reach the card. */
async function elapse(ms: number) {
    await vi.advanceTimersByTimeAsync(ms);
    await tick();
}

async function clickCreate() {
    await fireEvent.click(screen.getByTestId('backup-create'));
    await settle();
}

/** The card mounted, a backup started, and its first read answering `ready`. */
async function mountWithArchive(ready: InstanceBackupJob = done()) {
    api.start.mockResolvedValueOnce(running());
    api.get.mockResolvedValueOnce(ready);
    const view = render(BackupDownloadCard);
    await clickCreate();
    await elapse(POLL_MS);
    expect(card(), 'precondition: the archive is ready').toHaveAttribute('data-state', 'done');
    return view;
}

/** Mount, then press create while the start is refused with `refused()`. */
const refusedStart = (refused: () => unknown) => async () => {
    api.start.mockRejectedValueOnce(refused());
    render(BackupDownloadCard);
    await clickCreate();
};

/** Mount, start, and let the first read find the job failed with `errorCode`. */
const failedWhileRunning = (errorCode: InstanceBackupJob['error_code']) => async () => {
    api.start.mockResolvedValueOnce(running());
    api.get.mockResolvedValueOnce(failedJob(errorCode));
    render(BackupDownloadCard);
    await clickCreate();
    await elapse(POLL_MS);
};

/** Mount, start, and let every read of the running job fail with `failure()` until the polling gives up. */
const readsFailWhileRunning = (failure: () => unknown) => async () => {
    api.start.mockResolvedValueOnce(running());
    api.get.mockRejectedValue(failure());
    render(BackupDownloadCard);
    await clickCreate();
    await elapse(POLLING_GIVES_UP_AFTER);
};

/** Mount, start, and let the first read find the job gone. */
const goneWhileRunning = () => async () => {
    api.start.mockResolvedValueOnce(running());
    api.get.mockRejectedValueOnce(refusal(404, 'backup_job_not_found'));
    render(BackupDownloadCard);
    await clickCreate();
    await elapse(POLL_MS);
};

beforeEach(() => {
    vi.useFakeTimers();
    sessionStorage.clear();
    vi.mocked(notify).mockReset();
    api.start.mockReset();
    api.get.mockReset();
    api.remove.mockReset();
});

afterEach(() => {
    // Unmount on the fake clock that scheduled the card's timers, then hand the real one back.
    cleanup();
    vi.useRealTimers();
    sessionStorage.clear();
});

// =====================================================================================================================
describe('BackupDownloadCard — nothing followed', () => {
    it('idle: the privacy notice and the create button, no request, no event', () => {
        render(BackupDownloadCard);

        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(card()).toHaveAttribute('aria-busy', 'false');
        expect(card()).toHaveAttribute('data-error-code', '');
        expect(screen.getByTestId('backup-privacy-notice')).toHaveTextContent(exactly('backup.download.privacy'));
        expect(screen.getByTestId('backup-create')).toHaveTextContent(exactly('backup.download.create'));
        for (const absent of ['backup-loading', 'backup-progress', 'backup-ready', 'backup-error', 'backup-recheck']) {
            expect(screen.queryByTestId(absent), `${absent} on an idle card`).toBeNull();
        }
        expect(api.get).not.toHaveBeenCalled();
        expect(api.start).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
    });
});

// =====================================================================================================================
describe('BackupDownloadCard — creating a backup', () => {
    it('starting: an indeterminate bar; running: the phase, then the share written once the size is known', async () => {
        const answer = deferred<InstanceBackupJob>();
        api.start.mockReturnValueOnce(answer.promise);
        api.get.mockResolvedValueOnce(running({phase: 'files', done_bytes: 250, total_bytes: 1000}));
        render(BackupDownloadCard);

        await fireEvent.click(screen.getByTestId('backup-create'));

        expect(api.start).toHaveBeenCalledTimes(1);
        expect(card()).toHaveAttribute('data-state', 'starting');
        expect(card()).toHaveAttribute('data-busy', 'true');
        expect(card()).toHaveAttribute('aria-busy', 'true');
        expect(screen.getByTestId('backup-progress')).toHaveAttribute('data-phase', '');
        expect(screen.getByTestId('backup-progress')).toHaveTextContent(exactly('backup.download.creating'));
        expect(progressBar(), 'the share is unknown: the bar must not claim one').not.toHaveAttribute('aria-valuenow');
        expect(screen.queryByTestId('backup-loading'), 'starting a backup is not reading one').toBeNull();
        expect(screen.queryByTestId('backup-create'), 'a second backup can be asked for while one starts').toBeNull();

        answer.resolve(running({phase: 'preparing', total_bytes: 0}));
        await settle();

        expect(card()).toHaveAttribute('data-state', 'running');
        expect(card()).toHaveAttribute('data-busy', 'true');
        expect(screen.getByTestId('backup-progress')).toHaveAttribute('data-phase', 'preparing');
        expect(screen.getByTestId('backup-progress')).toHaveTextContent(exactly('backup.download.phase.preparing'));
        expect(progressBar()).not.toHaveAttribute('aria-valuenow');
        expect(screen.queryByTestId('backup-progress-bytes')).toBeNull();
        expect(screen.queryByTestId('backup-create')).toBeNull();

        await elapse(POLL_MS);

        expect(api.get).toHaveBeenCalledWith(JOB_ID);
        expect(screen.getByTestId('backup-progress')).toHaveAttribute('data-phase', 'files');
        expect(screen.getByTestId('backup-progress')).toHaveTextContent('backup.download.phase.files');
        expect(progressBar()).toHaveAttribute('aria-valuenow', '25');
        expect(screen.getByTestId('backup-progress-bytes')).toHaveTextContent(exactly('backup.download.progress'));
        expect(notify, 'nothing to announce while the backup runs').not.toHaveBeenCalled();
    });

    it('done: the archive link (href, download name), delete, retention; backup.created without a toast', async () => {
        await mountWithArchive();

        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(card()).toHaveAttribute('data-error-code', '');
        expect(screen.queryByTestId('backup-error'), 'a clean archive has no error beside it').toBeNull();
        expect(screen.queryByTestId('backup-recheck')).toBeNull();
        const ready = screen.getByTestId('backup-ready');
        const link = within(ready).getByTestId('backup-download-link');
        expect(link).toHaveAttribute('href', `/api/v1/backup/instance/jobs/${JOB_ID}/file`);
        expect(link).toHaveAttribute('download', FILE_NAME);
        expect(link).toHaveTextContent(exactly('backup.download.download'));
        expect(within(ready).getByTestId('backup-file-details')).toHaveTextContent(exactly('backup.download.readyDetails'));
        expect(within(ready).getByTestId('backup-delete')).toHaveTextContent(exactly('backup.download.delete'));
        expect(within(ready).getByTestId('backup-retention')).toHaveTextContent(exactly('backup.download.retention'));
        expect(screen.queryByTestId('backup-warnings'), 'a complete archive has no warnings box').toBeNull();
        expect(screen.queryByTestId('backup-progress')).toBeNull();
        expect(screen.getByTestId('backup-create')).toHaveTextContent(exactly('backup.download.createAgain'));
        expect(sessionStorage.getItem(KEY), 'a reload must find the archive again').toBe(JOB_ID);

        expect(events()).toEqual([{name: 'backup.created', detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings: [], encrypted: false}}]);
        expect(events()[0].toast, 'the archive is on the card: no toast is owed').toBeUndefined();
    });

    it.each<[string, Array<InstanceBackupJob['warnings'][number]>]>([
        ['one warning', ['files_skipped']],
        ['every warning', ['database_integrity', 'foreign_key_violations', 'files_skipped']],
    ])('done with %s: one line per warning code, and a warning toast', async (_case, warnings) => {
        await mountWithArchive(done({warnings}));

        const box = screen.getByTestId('backup-warnings');
        expect(box).toHaveTextContent('backup.download.warningsTitle');
        const lines = within(box).getAllByTestId('backup-warning');
        expect(lines.map((line) => line.getAttribute('data-warning'))).toEqual(warnings);
        for (const line of lines) {
            expect(line).toHaveTextContent(exactly(`backup.download.warnings.${line.getAttribute('data-warning')}`));
        }
        expect(screen.getByTestId('backup-download-link'), 'a partial archive is still an archive').toBeInTheDocument();

        expect(events()).toEqual([
            {
                name: 'backup.created',
                detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings, encrypted: false},
                toast: {variant: 'warning', message: 'backup.download.toast.warnings'},
            },
        ]);
    });
});

// =====================================================================================================================
describe('BackupDownloadCard — failures', () => {
    it.each<[string, string, 'start' | 'read' | 'job', string | null, () => Promise<void>]>([
        ['a start refused as busy (409)', 'backup_busy', 'start', null, refusedStart(() => refusal(409, 'backup_busy'))],
        ['a start refused: the backups folder is a link or a file (500)', 'backup_folder_unusable', 'start', null, refusedStart(() => refusal(500, 'backup_folder_unusable'))],
        ['a start refused: not enough free space on the server (507, B-30)', 'backup_no_space', 'start', null, refusedStart(() => refusal(507, 'backup_no_space'))],
        ['a start refused as failed (500)', 'backup_failed', 'start', null, refusedStart(() => refusal(500, 'backup_failed'))],
        ['a start with no answer', 'network', 'start', null, refusedStart(noAnswer)],
        ['a start answered without a code', 'unexpected', 'start', null, refusedStart(codelessAnswer)],
        ['the reads of a running job with no answer', 'network', 'read', JOB_ID, readsFailWhileRunning(noAnswer)],
        ['the reads of a running job answered without a code', 'unexpected', 'read', JOB_ID, readsFailWhileRunning(codelessAnswer)],
        ['a job gone from the server', 'backup_job_not_found', 'read', null, goneWhileRunning()],
        ['a job that ran out of space', 'backup_no_space', 'job', JOB_ID, failedWhileRunning('backup_no_space')],
        ['a job that failed', 'backup_failed', 'job', JOB_ID, failedWhileRunning('backup_failed')],
        ['a job that failed without a code', 'backup_failed', 'job', JOB_ID, failedWhileRunning(null)],
        ['a job interrupted', 'backup_interrupted', 'job', JOB_ID, failedWhileRunning('backup_interrupted')],
    ])('%s → backup-error %s, backup.failed (%s) with an error toast', async (_case, code, what, jobId, arrive) => {
        await arrive();

        expect(card()).toHaveAttribute('data-state', 'failed');
        expect(card()).toHaveAttribute('data-error-code', code);
        expect(card()).toHaveAttribute('data-busy', 'false');
        const error = screen.getByTestId('backup-error');
        expect(error).toHaveAttribute('data-error-code', code);
        expect(error).toHaveTextContent(exactly(`backup.download.errors.${code}`));
        expect(screen.getByTestId('backup-create'), 'a new attempt is always offered').toHaveTextContent(exactly('backup.download.retry'));
        expect(screen.queryByTestId('backup-progress')).toBeNull();
        expect(screen.queryByTestId('backup-ready')).toBeNull();

        expect(events()).toEqual([{name: 'backup.failed', detail: {code, what, job_id: jobId}, toast: {variant: 'error', message: `backup.download.errors.${code}`}}]);
    });

    it('a start refused with a code the card has no sentence for: the code published as it came, the unexpected sentence', async () => {
        await refusedStart(() => refusal(507, 'backup_quota_exceeded'))();

        expect(card()).toHaveAttribute('data-error-code', 'backup_quota_exceeded');
        const error = screen.getByTestId('backup-error');
        expect(error).toHaveAttribute('data-error-code', 'backup_quota_exceeded');
        expect(error).toHaveTextContent(exactly('backup.download.errors.unexpected'));
        expect(events()).toEqual([{name: 'backup.failed', detail: {code: 'backup_quota_exceeded', what: 'start', job_id: null}, toast: {variant: 'error', message: 'backup.download.errors.unexpected'}}]);
    });

    it.each<[string, string, () => Promise<void>]>([
        ['network, the job known: its reads failed', 'network', readsFailWhileRunning(noAnswer)],
        ['unexpected, the job known: its reads failed', 'unexpected', readsFailWhileRunning(codelessAnswer)],
        [
            'network, only its id known: the read after a reload failed',
            'network',
            async () => {
                sessionStorage.setItem(KEY, JOB_ID);
                api.get.mockRejectedValueOnce(noAnswer());
                render(BackupDownloadCard);
                await settle();
            },
        ],
        [
            'a start refused as busy after the polling gave up on the running job: J still followed (decision 1, revised)',
            'backup_busy',
            async () => {
                await readsFailWhileRunning(noAnswer)();
                api.start.mockRejectedValueOnce(refusal(409, 'backup_busy'));
                await clickCreate();
            },
        ],
        [
            'a start with no answer after a pick-up that got no answer: J still followed (decision 1, revised)',
            'network',
            async () => {
                sessionStorage.setItem(KEY, JOB_ID);
                api.get.mockRejectedValueOnce(noAnswer());
                render(BackupDownloadCard);
                await settle();
                api.start.mockRejectedValueOnce(noAnswer());
                await clickCreate();
            },
        ],
    ])('recheck offered — %s', async (_case, code, arrive) => {
        await arrive();

        expect(card()).toHaveAttribute('data-state', 'failed');
        expect(screen.getByTestId('backup-error')).toHaveAttribute('data-error-code', code);
        expect(screen.getByTestId('backup-recheck')).toHaveTextContent(exactly('backup.download.recheck'));
        expect(screen.getByTestId('backup-create')).toBeInTheDocument();
    });

    it.each<[string, 'failed' | 'done', () => Promise<void>]>([
        ['a start with no answer, nothing followed', 'failed', refusedStart(noAnswer)],
        ['a start answered without a code, nothing followed', 'failed', refusedStart(codelessAnswer)],
        ['a start refused as busy, nothing followed', 'failed', refusedStart(() => refusal(409, 'backup_busy'))],
        [
            'a start with no answer while an archive is on offer (decision 1)',
            'done',
            async () => {
                await mountWithArchive();
                api.start.mockRejectedValueOnce(noAnswer());
                await clickCreate();
            },
        ],
        [
            'a delete with no answer (decision 1)',
            'done',
            async () => {
                await mountWithArchive();
                api.remove.mockRejectedValueOnce(noAnswer());
                await fireEvent.click(screen.getByTestId('backup-delete'));
                await settle();
            },
        ],
        ['a job that ran out of space', 'failed', failedWhileRunning('backup_no_space')],
        ['a job gone from the server', 'failed', goneWhileRunning()],
    ])('recheck not offered — %s', async (_case, state, arrive) => {
        await arrive();

        expect(card()).toHaveAttribute('data-state', state);
        expect(screen.getByTestId('backup-error'), 'precondition: a failure is on the card').toBeInTheDocument();
        expect(screen.queryByTestId('backup-recheck')).toBeNull();
        expect(screen.getByTestId('backup-create')).toBeInTheDocument();
    });

    it.each<[string, () => unknown]>([
        ['backup_busy', () => refusal(409, 'backup_busy')],
        ['network', noAnswer],
    ])('the stranded job (decision 1, revised): the polling gave up on J, "Try again" refused (%s), "Check again" reads J, follows it running, backup.created once', async (code, refused) => {
        await readsFailWhileRunning(noAnswer)();
        api.start.mockRejectedValueOnce(refused());
        await clickCreate();

        expect(card()).toHaveAttribute('data-state', 'failed');
        expect(card()).toHaveAttribute('data-error-code', code);
        expect(screen.getByTestId('backup-error')).toHaveAttribute('data-error-code', code);
        expect(screen.getByTestId('backup-recheck'), 'J may be what keeps the server busy: checking it again must be offered').toBeInTheDocument();
        expect(sessionStorage.getItem(KEY), 'J is still followed').toBe(JOB_ID);

        api.get.mockReset();
        api.get.mockResolvedValueOnce(running({phase: 'finalizing', done_bytes: 900, total_bytes: 1000})).mockResolvedValueOnce(done());
        await fireEvent.click(screen.getByTestId('backup-recheck'));
        await settle();

        expect(api.get.mock.calls, '"Check again" must read J').toEqual([[JOB_ID]]);
        expect(card()).toHaveAttribute('data-state', 'running');
        expect(card()).toHaveAttribute('data-error-code', '');
        expect(screen.getByTestId('backup-progress')).toHaveAttribute('data-phase', 'finalizing');
        expect(progressBar()).toHaveAttribute('aria-valuenow', '90');
        expect(screen.queryByTestId('backup-error')).toBeNull();
        expect(events('backup.created'), 'nothing to announce while J runs').toEqual([]);

        await elapse(POLL_MS);

        expect(api.get).toHaveBeenCalledTimes(2);
        expect(card()).toHaveAttribute('data-state', 'done');
        expect(screen.getByTestId('backup-download-link')).toHaveAttribute('href', `/api/v1/backup/instance/jobs/${JOB_ID}/file`);
        expect(screen.queryByTestId('backup-recheck')).toBeNull();
        expect(events(), 'J was seen running here: its end is announced, once').toEqual([
            {name: 'backup.failed', detail: {code: 'network', what: 'read', job_id: JOB_ID}, toast: {variant: 'error', message: 'backup.download.errors.network'}},
            {name: 'backup.failed', detail: {code, what: 'start', job_id: null}, toast: {variant: 'error', message: `backup.download.errors.${code}`}},
            {name: 'backup.created', detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings: [], encrypted: false}},
        ]);
    });

    it('recheck: loading, busy and without the error while the job is read again, then the job as the server has it', async () => {
        await readsFailWhileRunning(noAnswer)();
        expect(api.get, 'precondition: five failed reads').toHaveBeenCalledTimes(5);
        vi.mocked(notify).mockClear();
        api.get.mockReset();
        const read = deferred<InstanceBackupJob>();
        api.get.mockReturnValueOnce(read.promise);

        await fireEvent.click(screen.getByTestId('backup-recheck'));

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith(JOB_ID);
        expect(card()).toHaveAttribute('data-state', 'loading');
        expect(card()).toHaveAttribute('data-busy', 'true');
        expect(card()).toHaveAttribute('data-error-code', '');
        expect(screen.getByTestId('backup-loading')).toHaveTextContent(exactly('backup.download.checking'));
        expect(screen.queryByTestId('backup-progress'), 'reading a job is not building one').toBeNull();
        expect(screen.queryByTestId('backup-error')).toBeNull();
        expect(screen.queryByTestId('backup-recheck')).toBeNull();
        expect(screen.queryByTestId('backup-create')).toBeNull();

        read.resolve(done());
        await settle();

        expect(card()).toHaveAttribute('data-state', 'done');
        expect(screen.queryByTestId('backup-loading')).toBeNull();
        expect(screen.getByTestId('backup-download-link')).toBeInTheDocument();
        expect(events(), 'a job seen running here that ended meanwhile is news: announced, once').toEqual([{name: 'backup.created', detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings: [], encrypted: false}}]);
    });

    it.each<[string, InstanceBackupJob, 'done' | 'failed']>([
        ['done', done(), 'done'],
        ['failed', failedJob('backup_interrupted'), 'failed'],
    ])('a pick-up that got no answer, then a recheck that finds the job %s: shown, never announced (decision 2)', async (_case, answer, state) => {
        sessionStorage.setItem(KEY, JOB_ID);
        api.get.mockRejectedValueOnce(noAnswer()).mockResolvedValueOnce(answer);
        render(BackupDownloadCard);
        await settle();
        expect(screen.getByTestId('backup-recheck'), 'precondition: the recheck is offered').toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('backup-recheck'));
        await settle();

        expect(card()).toHaveAttribute('data-state', state);
        expect(api.get).toHaveBeenCalledTimes(2);
        expect(notify, 'a job this card never saw running is not news, whatever it became').not.toHaveBeenCalled();
    });
});

// =====================================================================================================================
describe('BackupDownloadCard — the archive', () => {
    it.each<[string, () => unknown]>([
        ['the server deletes it', () => api.remove.mockResolvedValueOnce(undefined)],
        ['the server no longer has it', () => api.remove.mockRejectedValueOnce(refusal(404, 'backup_job_not_found'))],
    ])('delete, %s: back to idle, forgotten, backup.deleted without a toast', async (_case, answer) => {
        await mountWithArchive();
        vi.mocked(notify).mockClear();
        answer();

        await fireEvent.click(screen.getByTestId('backup-delete'));
        await settle();

        expect(api.remove).toHaveBeenCalledTimes(1);
        expect(api.remove).toHaveBeenCalledWith(JOB_ID);
        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(screen.queryByTestId('backup-ready')).toBeNull();
        expect(screen.queryByTestId('backup-error')).toBeNull();
        expect(screen.getByTestId('backup-create')).toHaveTextContent(exactly('backup.download.create'));
        expect(sessionStorage.getItem(KEY)).toBeNull();
        expect(events()).toEqual([{name: 'backup.deleted', detail: {job_id: JOB_ID}}]);
        expect(events()[0].toast, 'the archive leaving the card is visible: no toast is owed').toBeUndefined();
    });

    it('deleting (decision 3): busy, the archive still shown with backup-deleting in place of the link and the button, no action anywhere', async () => {
        await mountWithArchive(done({warnings: ['files_skipped']}));
        vi.mocked(notify).mockClear();
        const answer = deferred<void>();
        api.remove.mockReturnValueOnce(answer.promise);

        await fireEvent.click(screen.getByTestId('backup-delete'));

        expect(api.remove).toHaveBeenCalledTimes(1);
        expect(card()).toHaveAttribute('data-state', 'deleting');
        expect(card()).toHaveAttribute('data-busy', 'true');
        expect(card()).toHaveAttribute('aria-busy', 'true');
        expect(card()).toHaveAttribute('data-error-code', '');
        const ready = screen.getByTestId('backup-ready');
        expect(within(ready).getByTestId('backup-deleting')).toHaveTextContent(exactly('backup.download.deleting'));
        expect(within(ready).getByTestId('backup-file-details')).toBeInTheDocument();
        expect(within(ready).getByTestId('backup-warnings'), 'the archive being deleted is still described as it is').toBeInTheDocument();
        expect(screen.queryByTestId('backup-download-link'), 'an archive being deleted cannot be downloaded').toBeNull();
        expect(screen.queryByTestId('backup-delete'), 'a second delete can be asked for').toBeNull();
        expect(screen.queryByTestId('backup-create'), 'a backup can be started while the archive is being deleted').toBeNull();
        expect(screen.queryByTestId('backup-recheck')).toBeNull();
        expect(screen.queryByTestId('backup-error')).toBeNull();
        expect(screen.queryByTestId('backup-progress')).toBeNull();
        expect(screen.queryByTestId('backup-loading')).toBeNull();
        expect(notify).not.toHaveBeenCalled();

        answer.resolve();
        await settle();

        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(screen.queryByTestId('backup-ready')).toBeNull();
        expect(events()).toEqual([{name: 'backup.deleted', detail: {job_id: JOB_ID}}]);
    });

    it.each<[string, string, () => unknown]>([
        ['network', 'backup.download.errors.network', noAnswer],
        ['unexpected', 'backup.download.errors.unexpected', codelessAnswer],
        ['backup_job_running', 'backup.download.errors.unexpected', () => refusal(409, 'backup_job_running')],
    ])('a delete refused with %s (decision 3): done again, the archive on offer with the error beside it, backup.delete.failed, no recheck', async (code, message, refused) => {
        await mountWithArchive();
        vi.mocked(notify).mockClear();
        api.remove.mockRejectedValueOnce(refused());

        await fireEvent.click(screen.getByTestId('backup-delete'));
        await settle();

        expect(card()).toHaveAttribute('data-state', 'done');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(card()).toHaveAttribute('data-error-code', code);
        const error = screen.getByTestId('backup-error');
        expect(error).toHaveAttribute('data-error-code', code);
        expect(error).toHaveTextContent(exactly(message));
        expect(screen.getByTestId('backup-download-link'), 'the archive may still be on the server: it stays on offer').toHaveAttribute('href', `/api/v1/backup/instance/jobs/${JOB_ID}/file`);
        expect(screen.getByTestId('backup-delete'), 'the delete can be tried again').toBeInTheDocument();
        expect(screen.queryByTestId('backup-deleting')).toBeNull();
        expect(screen.queryByTestId('backup-recheck')).toBeNull();
        expect(screen.getByTestId('backup-create')).toHaveTextContent(exactly('backup.download.createAgain'));
        expect(sessionStorage.getItem(KEY)).toBe(JOB_ID);
        expect(events()).toEqual([{name: 'backup.delete.failed', detail: {code, what: 'remove', job_id: JOB_ID}, toast: {variant: 'error', message}}]);
    });

    it('create again, refused twice (no answer, then busy) (decision 1): the archive stays on offer with the error beside it, no recheck, nothing created', async () => {
        await mountWithArchive();
        vi.mocked(notify).mockClear();
        api.start.mockClear();
        const href = screen.getByTestId('backup-download-link').getAttribute('href');

        api.start.mockRejectedValueOnce(noAnswer());
        await clickCreate();

        expect(card()).toHaveAttribute('data-state', 'done');
        expect(card()).toHaveAttribute('data-error-code', 'network');
        expect(screen.getByTestId('backup-error')).toHaveTextContent(exactly('backup.download.errors.network'));
        expect(screen.getByTestId('backup-download-link'), 'the archive offered before must stay on offer').toHaveAttribute('href', href);
        expect(screen.queryByTestId('backup-recheck'), 'Check again would bring back the old archive as a new one').toBeNull();

        api.start.mockRejectedValueOnce(refusal(409, 'backup_busy'));
        await clickCreate();

        expect(api.start).toHaveBeenCalledTimes(2);
        expect(card()).toHaveAttribute('data-state', 'done');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(card()).toHaveAttribute('data-error-code', 'backup_busy');
        const error = screen.getByTestId('backup-error');
        expect(error).toHaveAttribute('data-error-code', 'backup_busy');
        expect(error).toHaveTextContent(exactly('backup.download.errors.backup_busy'));
        expect(screen.getByTestId('backup-download-link')).toHaveAttribute('href', href);
        expect(screen.getByTestId('backup-delete')).toBeInTheDocument();
        expect(screen.queryByTestId('backup-recheck')).toBeNull();
        expect(screen.getByTestId('backup-create')).toHaveTextContent(exactly('backup.download.createAgain'));
        expect(sessionStorage.getItem(KEY), 'a reload must still find the archive').toBe(JOB_ID);
        expect(api.get, 'a refused start reads no job').toHaveBeenCalledTimes(1);
        expect(events()).toEqual([
            {name: 'backup.failed', detail: {code: 'network', what: 'start', job_id: null}, toast: {variant: 'error', message: 'backup.download.errors.network'}},
            {name: 'backup.failed', detail: {code: 'backup_busy', what: 'start', job_id: null}, toast: {variant: 'error', message: 'backup.download.errors.backup_busy'}},
        ]);
    });

    it('download: a click on the link records backup.download.started, silently, and the archive stays on the card', async () => {
        await mountWithArchive();
        vi.mocked(notify).mockClear();
        // jsdom cannot navigate: stop the link's default action, after the card's own handler has run.
        const stopNavigation = (event: Event) => event.preventDefault();
        document.addEventListener('click', stopNavigation);
        try {
            await fireEvent.click(screen.getByTestId('backup-download-link'));
        } finally {
            document.removeEventListener('click', stopNavigation);
        }

        expect(events()).toEqual([{name: 'backup.download.started', detail: {job_id: JOB_ID}}]);
        expect(events()[0].toast).toBeUndefined();
        expect(card()).toHaveAttribute('data-state', 'done');
        expect(screen.getByTestId('backup-download-link')).toBeInTheDocument();
    });
});

// =====================================================================================================================
describe('BackupDownloadCard — the job of a previous page (sessionStorage)', () => {
    beforeEach(() => {
        sessionStorage.setItem(KEY, JOB_ID);
    });

    it('loading, busy and without progress until the read answers; a job already done shows its archive without backup.created', async () => {
        const read = deferred<InstanceBackupJob>();
        api.get.mockReturnValueOnce(read.promise);

        render(BackupDownloadCard);
        await tick();

        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith(JOB_ID);
        expect(card()).toHaveAttribute('data-state', 'loading');
        expect(card()).toHaveAttribute('data-busy', 'true');
        expect(card()).toHaveAttribute('aria-busy', 'true');
        expect(screen.getByTestId('backup-loading')).toHaveTextContent(exactly('backup.download.checking'));
        expect(screen.queryByTestId('backup-progress'), 'reading a job is not building one').toBeNull();
        expect(screen.queryByTestId('backup-create'), 'no action while the job is read').toBeNull();
        expect(screen.queryByTestId('backup-ready')).toBeNull();

        read.resolve(done());
        await settle();

        expect(card()).toHaveAttribute('data-state', 'done');
        expect(card()).toHaveAttribute('data-busy', 'false');
        expect(screen.queryByTestId('backup-loading')).toBeNull();
        expect(screen.getByTestId('backup-download-link')).toHaveAttribute('href', `/api/v1/backup/instance/jobs/${JOB_ID}/file`);
        expect(notify, 'an archive found after a reload is not news').not.toHaveBeenCalled();
    });

    it('a job still running: from loading to its progress, and its end is announced', async () => {
        api.get.mockResolvedValueOnce(running({phase: 'database', done_bytes: 600, total_bytes: 1200})).mockResolvedValueOnce(done());

        render(BackupDownloadCard);
        await settle();

        expect(card()).toHaveAttribute('data-state', 'running');
        expect(screen.queryByTestId('backup-loading')).toBeNull();
        expect(screen.getByTestId('backup-progress')).toHaveAttribute('data-phase', 'database');
        expect(progressBar()).toHaveAttribute('aria-valuenow', '50');
        expect(notify).not.toHaveBeenCalled();

        await elapse(POLL_MS);

        expect(card()).toHaveAttribute('data-state', 'done');
        expect(events()).toEqual([{name: 'backup.created', detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings: [], encrypted: false}}]);
    });

    it('a job the server no longer has: idle and forgotten, silently', async () => {
        api.get.mockRejectedValueOnce(refusal(404, 'backup_job_not_found'));

        render(BackupDownloadCard);
        await settle();

        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(card()).toHaveAttribute('data-error-code', '');
        expect(screen.queryByTestId('backup-error')).toBeNull();
        expect(screen.queryByTestId('backup-loading')).toBeNull();
        expect(screen.getByTestId('backup-create')).toHaveTextContent(exactly('backup.download.create'));
        expect(sessionStorage.getItem(KEY)).toBeNull();
        expect(notify).not.toHaveBeenCalled();
    });

    it('no answer: the network error with a recheck, silently', async () => {
        api.get.mockRejectedValueOnce(noAnswer());

        render(BackupDownloadCard);
        await settle();

        expect(card()).toHaveAttribute('data-state', 'failed');
        expect(screen.getByTestId('backup-error')).toHaveAttribute('data-error-code', 'network');
        expect(screen.getByTestId('backup-recheck')).toBeInTheDocument();
        expect(sessionStorage.getItem(KEY)).toBe(JOB_ID);
        expect(notify, 'a pick-up that failed is shown on the card, not toasted').not.toHaveBeenCalled();
    });

    it('a stored value that is not a job id is never read', () => {
        sessionStorage.setItem(KEY, 'not-a-backup-job');

        render(BackupDownloadCard);

        expect(api.get).not.toHaveBeenCalled();
        expect(card()).toHaveAttribute('data-state', 'idle');
        expect(screen.queryByTestId('backup-loading')).toBeNull();
    });
});

// =====================================================================================================================
describe('BackupDownloadCard — unmounted', () => {
    it('stops the polling: no read after unmount, nothing announced', async () => {
        api.start.mockResolvedValueOnce(running());
        const {unmount} = render(BackupDownloadCard);
        await clickCreate();
        expect(card(), 'precondition: the backup runs').toHaveAttribute('data-state', 'running');
        expect(vi.getTimerCount(), 'precondition: the next read is scheduled').toBe(1);

        unmount();

        expect(vi.getTimerCount()).toBe(0);
        await vi.advanceTimersByTimeAsync(60 * POLL_MS);
        expect(api.get).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
    });

    it('drops a read that answers after unmount', async () => {
        const read = deferred<InstanceBackupJob>();
        api.start.mockResolvedValueOnce(running());
        api.get.mockReturnValueOnce(read.promise);
        const {unmount} = render(BackupDownloadCard);
        await clickCreate();
        await elapse(POLL_MS);
        expect(api.get, 'precondition: a read is out').toHaveBeenCalledTimes(1);

        unmount();
        read.resolve(done());
        await settle();
        await vi.advanceTimersByTimeAsync(60 * POLL_MS);

        expect(notify, 'a card that is gone announced an archive').not.toHaveBeenCalled();
        expect(api.get).toHaveBeenCalledTimes(1);
    });
});

// =====================================================================================================================
describe('BackupTab', () => {
    it('is the backup card under the intro of the tab', () => {
        render(BackupTab);

        const tab = screen.getByTestId('backup-tab');
        expect(tab).toHaveTextContent('backup.intro');
        expect(within(tab).getByTestId('backup-download-card')).toHaveAttribute('data-state', 'idle');
    });
});

// =====================================================================================================================
// B4 — the «secure» backup: clear or secure, the password of a secure archive (workstream B, lot B4; written red first)
// =====================================================================================================================

/*
 * The contract (B4 brief §7, decisions 38 and 39, P12):
 *   - a radio group: `backup-mode-clear`, checked by default, and `backup-mode-secure`, each with its description
 *     (`backup-mode-clear-description`, `backup-mode-secure-description`); clear asks for nothing and creates the backup
 *     of before, with no password;
 *   - secure: `backup-password` and `backup-password-confirm` (type password), and the strength meter with the rules of
 *     `GET /backup/instance/options` — the meter's `password-rule-<key>` rows, in the options' order (this file's server
 *     answers them in an order of its own, mocked above); `backup-password-mismatch` when both fields are filled and
 *     differ; `backup-create` disabled while the password is empty, short of the rules, or not repeated alike;
 *   - create sends `startInstanceBackup(password)`, and the two fields are emptied once the job has started;
 *   - the phase `encrypting` has its label (`backup.download.phase.encrypting`); a start refused as `password_too_weak`
 *     has its sentence (`backup.download.errors.password_too_weak`); `backup.created` says `encrypted`.
 *
 * The meter (PasswordStrength) is the real one; the instance's rules it would read without the options are the app's
 * defaults here (eight characters): a card that gave it no rules would accept eleven characters. With B4 every job
 * carries `encrypted`: the fixture `job()` says `false`, and the details of `backup.created` expected above say it too.
 *
 * Red today: the card has no mode, no password field, no label for `encrypting` and no sentence for
 * `password_too_weak`, and `backup.created` does not say `encrypted`.
 */

/** A password that meets the archive's rules: twenty-three characters, upper and lower case, a digit, a symbol. */
const PASSWORD = 'Correct-Horse-Battery-9';
/** Every class in eleven characters: one short of the archive's twelve, enough for the instance's eight. */
const ELEVEN = 'Str0ng!pass';
/** The same and one more digit: twelve. */
const TWELVE = 'Str0ng!pass1';
const SECURE_FILE_NAME = 'librefolio-backup-20261016-230000.lfbk';
/** B4's new phase: the generated client does not know it yet. */
const ENCRYPTING = 'encrypting' as string as NonNullable<InstanceBackupJob['phase']>;

const modeClear = () => screen.getByTestId('backup-mode-clear');
const modeSecure = () => screen.getByTestId('backup-mode-secure');
const passwordField = () => screen.getByTestId('backup-password');
const confirmField = () => screen.getByTestId('backup-password-confirm');
const createButton = () => screen.getByTestId('backup-create');

/** Choose the secure mode — a radio: choosing it when it is already chosen keeps it chosen — and let the options land. */
async function chooseSecure(): Promise<void> {
    await fireEvent.click(modeSecure());
    await settle();
    expect(modeSecure(), 'precondition: the secure mode is chosen').toBeChecked();
}

/** Type the password, then its repetition. */
async function typePasswords(password: string, repeated: string = password): Promise<void> {
    await fireEvent.input(passwordField(), {target: {value: password}});
    await fireEvent.input(confirmField(), {target: {value: repeated}});
    await settle();
}

/** Secure, `PASSWORD` typed twice, create pressed. */
async function startSecure(): Promise<void> {
    await chooseSecure();
    await typePasswords(PASSWORD);
    expect(createButton(), 'precondition: the password is accepted').toBeEnabled();
    await clickCreate();
}

/** Every argument the request that starts a backup was given, `undefined` set aside. */
const startArguments = (call = 0): unknown[] => (api.start.mock.calls[call] as unknown[]).filter((argument) => argument !== undefined);

describe('B4 — BackupDownloadCard: clear or secure', () => {
    it('idle: the two modes, one radio group, clear checked by default, each with its description; no password asked', () => {
        render(BackupDownloadCard);

        expect(modeClear()).toBeChecked();
        expect(modeSecure()).not.toBeChecked();
        for (const radio of [modeClear(), modeSecure()]) expect(radio).toHaveAttribute('type', 'radio');
        expect(modeClear().getAttribute('name'), 'the two modes are one group').toBeTruthy();
        expect(modeSecure().getAttribute('name'), 'the two modes are one group').toBe(modeClear().getAttribute('name'));
        expect(screen.getByTestId('backup-mode-clear-description')).toHaveTextContent(exactly('backup.download.mode.clearDescription'));
        expect(screen.getByTestId('backup-mode-secure-description')).toHaveTextContent(exactly('backup.download.mode.secureDescription'));
        for (const absent of ['backup-password', 'backup-password-confirm', 'backup-password-mismatch', 'password-strength-meter']) {
            expect(screen.queryByTestId(absent), `${absent} while clear is chosen`).toBeNull();
        }
        expect(createButton()).toBeEnabled();
    });

    it('clear, the default: create sends no password — the backup of before', async () => {
        api.start.mockResolvedValueOnce(running());
        render(BackupDownloadCard);
        expect(modeClear(), 'precondition: clear is the default').toBeChecked();

        await clickCreate();

        expect(api.start).toHaveBeenCalledTimes(1);
        expect(startArguments(), 'a clear backup sent a password').toEqual([]);
        expect(card()).toHaveAttribute('data-state', 'running');
    });

    it("secure: two password fields, and the meter with the rules of GET /backup/instance/options — their rows, their order, twelve characters and not the instance's eight", async () => {
        render(BackupDownloadCard);
        await chooseSecure();

        expect(modeClear()).not.toBeChecked();
        expect(passwordField()).toHaveAttribute('type', 'password');
        expect(confirmField()).toHaveAttribute('type', 'password');

        await typePasswords(ELEVEN, '');

        expect(screen.getByTestId('password-strength-meter')).toBeInTheDocument();
        expect(
            screen.getAllByTestId(/^password-rule-/).map((rule) => rule.getAttribute('data-testid')),
            "the options' rules, in their order",
        ).toEqual(['password-rule-hasSpecial', 'password-rule-hasNumber', 'password-rule-hasLowercase', 'password-rule-hasUppercase', 'password-rule-minLength']);
        expect(screen.getByTestId('password-rule-minLength'), "eleven characters: one short of the archive's twelve").toHaveAttribute('data-passed', 'false');
        for (const key of ['hasSpecial', 'hasNumber', 'hasLowercase', 'hasUppercase']) {
            expect(screen.getByTestId(`password-rule-${key}`)).toHaveAttribute('data-passed', 'true');
        }

        await typePasswords(TWELVE, '');

        expect(screen.getByTestId('password-rule-minLength'), 'twelve characters').toHaveAttribute('data-passed', 'true');
    });

    it('create disabled while the password is empty, short of the rules, or not repeated alike; the mismatch shown only when both fields are filled and differ', async () => {
        render(BackupDownloadCard);
        await chooseSecure();

        expect(createButton(), 'nothing typed').toBeDisabled();
        expect(screen.queryByTestId('backup-password-mismatch')).toBeNull();

        await typePasswords(ELEVEN);
        expect(createButton(), 'the same eleven characters twice: short of the rules').toBeDisabled();
        expect(screen.queryByTestId('backup-password-mismatch'), 'the two fields agree').toBeNull();

        await typePasswords(PASSWORD, '');
        expect(createButton(), 'not repeated yet').toBeDisabled();
        expect(screen.queryByTestId('backup-password-mismatch'), 'one field empty: nothing to compare yet').toBeNull();

        await typePasswords(PASSWORD, `${PASSWORD}x`);
        expect(createButton(), 'repeated differently').toBeDisabled();
        expect(screen.getByTestId('backup-password-mismatch')).toHaveTextContent(exactly('backup.download.password.mismatch'));

        await typePasswords(PASSWORD);
        expect(screen.queryByTestId('backup-password-mismatch')).toBeNull();
        expect(createButton(), 'valid, and repeated alike').toBeEnabled();
        expect(api.start, 'nothing was sent on the way').not.toHaveBeenCalled();
    });

    it('valid and repeated alike: create sends that password; once the job has started no field holds it, and the next secure backup starts from empty fields', async () => {
        api.start.mockResolvedValueOnce(running({phase: 'database'}));
        api.get.mockResolvedValueOnce(done({file_name: SECURE_FILE_NAME, encrypted: true}));
        render(BackupDownloadCard);

        await startSecure();

        expect(api.start.mock.calls, 'the password typed, sent once').toEqual([[PASSWORD]]);
        expect(card()).toHaveAttribute('data-state', 'running');
        expect(
            [...card().querySelectorAll('input')].filter((input) => input.value.includes(PASSWORD)).map((input) => input.getAttribute('data-testid')),
            'a field still holds the password once the job has started',
        ).toEqual([]);

        await elapse(POLL_MS);
        expect(card(), 'precondition: the archive is ready').toHaveAttribute('data-state', 'done');
        await chooseSecure();

        expect(passwordField()).toHaveValue('');
        expect(confirmField()).toHaveValue('');
        expect(createButton(), 'a new secure backup asks for the password again').toBeDisabled();
    });

    it('back to clear after typing a password: create sends none — the archive is the clear one', async () => {
        api.start.mockResolvedValueOnce(running());
        render(BackupDownloadCard);
        await chooseSecure();
        await typePasswords(PASSWORD);
        expect(createButton(), 'precondition: the password would be accepted').toBeEnabled();

        await fireEvent.click(modeClear());
        await settle();

        expect(modeClear()).toBeChecked();
        expect(screen.queryByTestId('backup-password'), 'clear asks for no password').toBeNull();
        expect(createButton()).toBeEnabled();

        await clickCreate();

        expect(api.start).toHaveBeenCalledTimes(1);
        expect(startArguments(), 'a clear backup sent the password typed before').toEqual([]);
    });

    it('the phase encrypting: data-phase encrypting and its own label, with the share encrypted so far', async () => {
        api.start.mockResolvedValueOnce(running({phase: ENCRYPTING, done_bytes: 300, total_bytes: 1200}));
        render(BackupDownloadCard);

        await startSecure();

        const progress = screen.getByTestId('backup-progress');
        expect(progress).toHaveAttribute('data-phase', 'encrypting');
        expect(progress).toHaveTextContent('backup.download.phase.encrypting');
        expect(progressBar()).toHaveAttribute('aria-valuenow', '25');
    });

    it('a start refused as password_too_weak (the rules of the server): backup-error with its code and its own sentence, backup.failed with an error toast', async () => {
        api.start.mockRejectedValueOnce({
            isAxiosError: true,
            message: 'Request failed with status code 400',
            response: {status: 400, data: {detail: {code: 'password_too_weak', message: 'refused: password_too_weak', rules: ['min_length']}}},
        });
        render(BackupDownloadCard);

        await startSecure();

        expect(card()).toHaveAttribute('data-state', 'failed');
        expect(card()).toHaveAttribute('data-error-code', 'password_too_weak');
        const error = screen.getByTestId('backup-error');
        expect(error).toHaveAttribute('data-error-code', 'password_too_weak');
        expect(error).toHaveTextContent(exactly('backup.download.errors.password_too_weak'));
        expect(events()).toEqual([{name: 'backup.failed', detail: {code: 'password_too_weak', what: 'start', job_id: null}, toast: {variant: 'error', message: 'backup.download.errors.password_too_weak'}}]);
    });

    it.each<[string, boolean, () => Promise<void>]>([
        ['clear', false, clickCreate],
        ['secure', true, startSecure],
    ])('a %s archive ready: backup.created says encrypted: %s', async (_mode, encrypted, start) => {
        const fileName = encrypted ? SECURE_FILE_NAME : FILE_NAME;
        api.start.mockResolvedValueOnce(running());
        api.get.mockResolvedValueOnce(done({file_name: fileName, encrypted}));
        render(BackupDownloadCard);

        await start();
        await elapse(POLL_MS);

        expect(card()).toHaveAttribute('data-state', 'done');
        expect(screen.getByTestId('backup-download-link')).toHaveAttribute('download', fileName);
        expect(events()).toEqual([{name: 'backup.created', detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings: [], encrypted}}]);
    });
});

// =====================================================================================================================
// B4b — the password of a secure backup is a new password (B-25; written red first)
// =====================================================================================================================

/*
 * The contract (B4b brief §3, frontend): both password fields of a secure backup say `autocomplete="new-password"`, so
 * that a password manager offers to make a new password there and never fills in the account's own. `off` does not
 * say so: password managers commonly ignore it on a password field. Red today: both fields say `off`.
 */

describe('B4b — BackupDownloadCard: the password fields of a secure backup are new-password fields (B-25)', () => {
    it('backup-password and backup-password-confirm say autocomplete="new-password": a password manager fills in no account password there', async () => {
        render(BackupDownloadCard);
        await chooseSecure();
        const fields = [passwordField(), confirmField()];

        expect(
            fields.map((field) => field.getAttribute('type')),
            'precondition: the two password fields of a secure backup',
        ).toEqual(['password', 'password']);
        // One object, so that a red shows both fields at once.
        expect(Object.fromEntries(fields.map((field) => [field.getAttribute('data-testid'), field.getAttribute('autocomplete')])), "new passwords, never the account's").toEqual({'backup-password': 'new-password', 'backup-password-confirm': 'new-password'});
    });
});

// =====================================================================================================================
// B-8, developer 19/10 — on screen only «busy»; the console names the backup that runs (workstream B; written red first)
// =====================================================================================================================

/*
 * The developer's decision (19/10), relayed by the coordinator. Verbatim: «farei che a schermo compare solo "occupato",
 * in console magari più dettagli per permetterci di backuppare se serve, non è in vista ma se venisse letto da un utente
 * non sarebbe grave» (on screen only «busy»; in the console more details, to let us back up if need be; out of sight,
 * and no harm done if a user read them). The 409 stays as it is: it names the running backup (`detail.job_id`,
 * `detail.origin`). The card never names it, whatever its origin, and keeps following its own `ui` backup as before;
 * the console gets the details, always. Through the card:
 *   - on screen (the guards): refused by a running backup of origin `cli`, `panel` or `pre-restore` with nothing on
 *     offer, `failed` with `backup_busy`, and the `backup-error` alert says the busy sentence, nothing else; with an
 *     archive on offer, whatever the origin, that archive still on offer and the busy sentence beside it; a backup of
 *     origin `ui` with nothing on offer followed as one started here, its progress and then its archive. At no point
 *     does the card's text hold that backup's id, nor its origin as a word; the toast of `backup.failed` says the busy
 *     sentence (the event's `detail` is the event ring's, not the screen's: not asserted here);
 *   - in the console (the reds): one `console.warn` per refused start whose refusal names a backup — a sentence, its
 *     wording free, then exactly `{job_id, origin, status: 'running'}`; backupJob.test.ts pins the rest of the line
 *     (once, at the refusal; never otherwise).
 *
 * The needles: the id anywhere in the text, the origin as a whole word. The text is i18n keys here (the identity
 * translator), whose dots end a word and whose underscores do not: `backup.download.ui.x` would hold the word «ui»,
 * `ui_x` and `build` do not. Their premise, asserted first: none is in the text of a card refused by a busy server that
 * names no backup. Only the text is read: the link of an archive on offer holds its job id in its `href` by
 * construction, as it did before B-8.
 *
 * Red today: the console cases (the card writes nothing to the console: `console.warn` called 0 times, 1 or 3
 * expected). Green today, and to stay so: the screen and the toast.
 */

/** The running backup a refusal names: not the archive this file's card offers (`JOB_ID`). */
const RUNNING_JOB_ID = 'fedcba9876543210fedcba9876543210';
/** Every origin the server gives a backup (`BackupOrigin`, backend manifest.py). */
const ORIGINS = ['ui', 'cli', 'panel', 'pre-restore'];
/** The busy sentence, as the identity translator renders it: its key. */
const BUSY = 'backup.download.errors.backup_busy';

/** The 409 of a start while a backup runs, naming it as the server does since B-8: `detail: {code, message, job_id, origin}`. */
function busyRefusalNaming(jobId: string, origin: string) {
    return {isAxiosError: true, message: 'Request failed with status code 409', response: {status: 409, data: {detail: {code: 'backup_busy', message: 'refused: backup_busy', job_id: jobId, origin}}}};
}

/** What of the running backup `text` names: its id, anywhere; its origin, as a whole word (`ui` in «origin ui» or in a key's `.ui.`, never in `build` or `ui_`). */
function namesIn(text: string, jobId: string, origin: string): string[] {
    const named: string[] = [];
    if (text.includes(jobId)) named.push(jobId);
    if (new RegExp(`\\b${origin}\\b`).test(text)) named.push(origin);
    return named;
}

/** What of the running backup the card's whole text names: nothing, when the card keeps it to itself. */
const namedOnCard = (jobId: string, origin: string): string[] => namesIn(card().textContent ?? '', jobId, origin);

/** The toasts the card raised through `notify()`, in order: the part of its events the user reads. */
const toasts = () => events().flatMap((options) => (options.toast === undefined ? [] : [options.toast]));

describe('BackupDownloadCard — B-8, developer 19/10: the card never names the backup that runs; the console does', () => {
    let warn: MockInstance<typeof console.warn>;

    beforeEach(() => {
        warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    });

    afterEach(() => {
        warn.mockRestore();
    });

    /** The one line of a start refused by a running backup its refusal names: a non-empty string first, its wording free, then exactly its details. */
    function expectOneLine(jobId: string, origin: string, why = 'a start refused by a running backup that its refusal names must write exactly one console.warn'): void {
        expect(warn, why).toHaveBeenCalledTimes(1);
        const [sentence, details] = warn.mock.calls[0];
        expect(sentence, 'the line opens with a sentence of its own: a non-empty string').toEqual(expect.stringMatching(/\S/));
        expect(details, 'the details of the running backup, exactly: its id, its origin, running').toStrictEqual({job_id: jobId, origin, status: 'running'});
    }

    it('the needles find the id anywhere and the origin as a whole word: in a sentence or a key that names it, never in a word that only holds it', () => {
        for (const origin of ORIGINS) {
            expect(namesIn(`busy: backup ${RUNNING_JOB_ID}, started from ${origin}.`, RUNNING_JOB_ID, origin), `the needles miss a sentence naming a backup of origin ${origin}`).toEqual([RUNNING_JOB_ID, origin]);
            expect(namesIn(`backup.download.${origin}.running`, RUNNING_JOB_ID, origin), `the needles miss «${origin}» as a segment of a key`).toEqual([origin]);
            expect(namesIn('backup.download.ui_busy build client panels pre-restored', RUNNING_JOB_ID, origin), `a word that only holds «${origin}» counts as the origin`).toEqual([]);
        }
    });

    it.each<[string, () => Promise<void>]>([
        ['nothing on offer', refusedStart(() => refusal(409, 'backup_busy'))],
        [
            'an archive on offer',
            async () => {
                await mountWithArchive();
                api.start.mockRejectedValueOnce(refusal(409, 'backup_busy'));
                await clickCreate();
            },
        ],
    ])('the premise: refused by a busy server that names no backup, %s — no needle is in the text of the card', async (_case, arrive) => {
        await arrive();

        expect(card(), 'precondition: refused as busy').toHaveAttribute('data-error-code', 'backup_busy');
        expect(screen.getByRole('alert')).toHaveTextContent(exactly(BUSY));
        for (const origin of ORIGINS) {
            expect(namedOnCard(RUNNING_JOB_ID, origin), `the plain busy card already holds a needle of a backup of origin ${origin}: the guards below would be noise`).toEqual([]);
            expect(namedOnCard(JOB_ID, origin), `the plain busy card already holds a needle of a backup of origin ${origin}: the guards below would be noise`).toEqual([]);
        }
    });

    it.each(['cli', 'panel', 'pre-restore'])('origin %s, nothing on offer: failed, backup_busy, the alert and the toast say the busy sentence; neither the id nor the origin of the backup that runs on the card (green today: the guard)', async (origin) => {
        await refusedStart(() => busyRefusalNaming(RUNNING_JOB_ID, origin))();

        expect(card()).toHaveAttribute('data-state', 'failed');
        expect(card()).toHaveAttribute('data-error-code', 'backup_busy');
        const alert = screen.getByRole('alert');
        expect(alert, 'the alert is the error of the card').toHaveAttribute('data-testid', 'backup-error');
        expect(alert, 'the alert says the busy sentence, and nothing else').toHaveTextContent(exactly(BUSY));
        expect(api.get, 'a backup of another origin is not followed').not.toHaveBeenCalled();
        expect(namedOnCard(RUNNING_JOB_ID, origin), 'the card names the backup that runs').toEqual([]);
        expect(events('backup.failed'), 'precondition: the refused start announced, once').toHaveLength(1);
        expect(toasts(), 'the toast of backup.failed says the busy sentence, and no toast says anything else').toEqual([{variant: 'error', message: BUSY}]);
    });

    it.each(ORIGINS)('an archive on offer, a start refused by a running backup of origin %s: done, that archive still on offer, the busy sentence beside it; neither the id nor the origin on the card (green today: the guard)', async (origin) => {
        await mountWithArchive();
        vi.mocked(notify).mockClear();
        api.start.mockRejectedValueOnce(busyRefusalNaming(RUNNING_JOB_ID, origin));

        await clickCreate();

        expect(card()).toHaveAttribute('data-state', 'done');
        expect(card()).toHaveAttribute('data-error-code', 'backup_busy');
        const link = screen.getByTestId('backup-download-link');
        expect(link, 'the archive offered before must stay on offer').toHaveAttribute('href', `/api/v1/backup/instance/jobs/${JOB_ID}/file`);
        expect(link).toHaveAttribute('download', FILE_NAME);
        expect(screen.getByTestId('backup-file-details')).toHaveTextContent(exactly('backup.download.readyDetails'));
        const alert = screen.getByRole('alert');
        expect(alert, 'the alert is the error of the card').toHaveAttribute('data-testid', 'backup-error');
        expect(alert, 'the alert says the busy sentence, and nothing else').toHaveTextContent(exactly(BUSY));
        expect(api.get, 'one read, of the archive: with an archive on offer the backup that runs is not followed').toHaveBeenCalledTimes(1);
        expect(namedOnCard(RUNNING_JOB_ID, origin), 'the card names the backup that runs').toEqual([]);
        expect(events('backup.failed'), 'precondition: the refused start announced, once').toHaveLength(1);
        expect(toasts(), 'the toast of backup.failed says the busy sentence, and no toast says anything else').toEqual([{variant: 'error', message: BUSY}]);
    });

    it('a running backup of origin ui named, nothing on offer: followed as one started here — loading, its progress, then its archive —, and at no point its id or «ui» on the card; no toast (green today: the guard)', async () => {
        const read = deferred<InstanceBackupJob>();
        api.start.mockRejectedValueOnce(busyRefusalNaming(JOB_ID, 'ui'));
        api.get.mockReturnValueOnce(read.promise);
        api.get.mockResolvedValueOnce(running({phase: 'files', done_bytes: 250, total_bytes: 1000})).mockResolvedValueOnce(done());
        render(BackupDownloadCard);

        await clickCreate();

        expect(api.get.mock.calls, 'the backup the refusal names is read').toEqual([[JOB_ID]]);
        expect(card()).toHaveAttribute('data-state', 'loading');
        expect(screen.getByTestId('backup-loading')).toHaveTextContent(exactly('backup.download.checking'));
        expect(namedOnCard(JOB_ID, 'ui'), 'loading: the card names the backup it reads').toEqual([]);

        read.resolve(running({phase: 'database'}));
        await settle();

        expect(card()).toHaveAttribute('data-state', 'running');
        expect(screen.getByTestId('backup-progress')).toHaveAttribute('data-phase', 'database');
        expect(namedOnCard(JOB_ID, 'ui'), 'running: the card names the backup it follows').toEqual([]);

        await elapse(POLL_MS);

        expect(progressBar()).toHaveAttribute('aria-valuenow', '25');
        expect(screen.getByTestId('backup-progress-bytes')).toHaveTextContent(exactly('backup.download.progress'));
        expect(namedOnCard(JOB_ID, 'ui'), 'running, the share known: the card names the backup it follows').toEqual([]);

        await elapse(POLL_MS);

        expect(card()).toHaveAttribute('data-state', 'done');
        expect(screen.getByTestId('backup-file-details')).toHaveTextContent(exactly('backup.download.readyDetails'));
        expect(screen.getByTestId('backup-download-link')).toHaveAttribute('download', FILE_NAME);
        expect(screen.queryByTestId('backup-error'), 'the backup asked for runs: no error').toBeNull();
        expect(namedOnCard(JOB_ID, 'ui'), 'done: the card names the backup whose archive it offers').toEqual([]);
        expect(events('backup.failed'), 'the refused start is announced to no one').toEqual([]);
        expect(toasts(), 'no toast: no failure, and a complete archive raises none').toEqual([]);
    });

    it.each(ORIGINS)('the console: a start refused by a running backup of origin %s, nothing on offer — one console.warn, a sentence then {job_id, origin, status: running} (red today)', async (origin) => {
        // Of origin ui, the backup named is followed: its reads find it running.
        api.get.mockResolvedValue(running({job_id: RUNNING_JOB_ID}));
        render(BackupDownloadCard);
        expect(warn, 'precondition: the card wrote nothing to the console before the refusal').not.toHaveBeenCalled();
        api.start.mockRejectedValueOnce(busyRefusalNaming(RUNNING_JOB_ID, origin));

        await clickCreate();

        expect(card(), 'precondition: refused, or the backup named followed (origin ui)').toHaveAttribute('data-state', origin === 'ui' ? 'running' : 'failed');
        expectOneLine(RUNNING_JOB_ID, origin);
    });

    it.each(ORIGINS)('the console: an archive on offer, a start refused by a running backup of origin %s — one console.warn all the same (red today)', async (origin) => {
        await mountWithArchive();
        expect(warn, 'precondition: the card wrote nothing to the console before the refusal').not.toHaveBeenCalled();
        api.start.mockRejectedValueOnce(busyRefusalNaming(RUNNING_JOB_ID, origin));

        await clickCreate();

        expect(card(), 'precondition: the archive stays on offer').toHaveAttribute('data-state', 'done');
        expectOneLine(RUNNING_JOB_ID, origin);
    });

    it('the console: refused three times, nothing on offer — by a cli backup, by that same backup again, then by a pre-restore one: one line per refused start, each naming the backup its refusal names (red today)', async () => {
        render(BackupDownloadCard);
        expect(warn, 'precondition: the card wrote nothing to the console before the refusals').not.toHaveBeenCalled();
        api.start.mockRejectedValueOnce(busyRefusalNaming(RUNNING_JOB_ID, 'cli')).mockRejectedValueOnce(busyRefusalNaming(RUNNING_JOB_ID, 'cli'));
        api.start.mockRejectedValueOnce(busyRefusalNaming(JOB_ID, 'pre-restore'));

        await clickCreate();
        await clickCreate();
        await clickCreate();

        expect(api.start, 'precondition: three starts').toHaveBeenCalledTimes(3);
        expect(card(), 'precondition: each refused').toHaveAttribute('data-state', 'failed');
        expect(warn, 'one line per refused start, the same running backup named twice included').toHaveBeenCalledTimes(3);
        const details = warn.mock.calls.map(([, named]) => named);
        expect(details, 'each line names the backup its refusal names').toStrictEqual([
            {job_id: RUNNING_JOB_ID, origin: 'cli', status: 'running'},
            {job_id: RUNNING_JOB_ID, origin: 'cli', status: 'running'},
            {job_id: JOB_ID, origin: 'pre-restore', status: 'running'},
        ]);
    });

    it('the console: a running backup of origin ui named, nothing on offer, followed to its archive — one line, at the refusal; the follow writes nothing more (red today)', async () => {
        api.start.mockRejectedValueOnce(busyRefusalNaming(JOB_ID, 'ui'));
        api.get.mockResolvedValueOnce(running()).mockResolvedValueOnce(done());
        render(BackupDownloadCard);

        await clickCreate();

        expect(card(), 'precondition: the backup named is followed').toHaveAttribute('data-state', 'running');
        expectOneLine(JOB_ID, 'ui');

        await elapse(POLL_MS);

        expect(card(), 'precondition: followed to its archive').toHaveAttribute('data-state', 'done');
        expectOneLine(JOB_ID, 'ui', 'the follow wrote another line: the line is written once, at the refusal');
    });
});

// =====================================================================================================================
// B-8, defect of the review (19/10) — a secure request never follows a running backup; a clear one never presents a
// secure end (workstream B; written red first)
// =====================================================================================================================

/*
 * The defect, found by the automatic review and relayed by the coordinator: the secure mode chosen, the password typed
 * twice, «Create» refused `409 backup_busy` naming a running backup of origin `ui`, nothing on offer — the card followed
 * that backup whatever its mode (the B-8 group above follows one from the clear mode only). It may be another tab's, or
 * another administrator's, and clear: the card then said «Archive ready» for a clear .zip, without the privacy notice
 * (drawn in clear mode only), and `backup.created` announced it as the user's own. Conversely, a clear request could be
 * offered an .lfbk sealed with someone else's password. The server sets `encrypted` only when a backup ends: a running
 * one reads `encrypted: false`.
 *
 * The decision (the coordinator, 19/10 17:37), verbatim: «confermo la tabella di destra. Con una password, dal 409
 * nessun seguito; in chiaro, il controllo alla fine (`encrypted: true`, quindi non presentato, id dimenticato,
 * `backup_busy`)». Through the card, the refusal naming the running backup `RUNNING_JOB_ID`, nothing on offer:
 *   - secure, the password typed twice, «Create»: `failed` and the busy alert; never `backup-ready` nor the download
 *     link; `getInstanceBackupJob` never called; no `backup.created`; one `backup.failed`, with the busy toast;
 *   - clear, «Create», the backup named running, then done with `encrypted: true`: its progress while it runs, as
 *     today; at its end `failed` and the busy alert, no `backup-ready`, no link, no `backup.created`, one busy toast;
 *   - the guard: clear, the same backup done with `encrypted: false` — offered, the privacy notice on the card,
 *     `backup.created` once.
 * backupJob.test.ts pins the rest: the storage and the adoption key, a reload, «Check again», the console line.
 *
 * Red today: the first two cases — the card follows the backup named, then offers its archive and announces it. Green
 * today, and to stay so: the third.
 */

describe('BackupDownloadCard — B-8, defect of the review (19/10): a secure request never follows a running backup; a clear one never presents a secure end', () => {
    let warn: MockInstance<typeof console.warn>;

    // Every refusal here names a running backup: one console.warn each (the group above), kept off the run's output.
    beforeEach(() => {
        warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    });

    afterEach(() => {
        warn.mockRestore();
    });

    /** Clear (the default), «Create»: refused by the running backup `RUNNING_JOB_ID` of origin ui, nothing on offer — followed as today, its progress drawn while it runs, up to its last phase; the read after that answers `end`. */
    async function clearRequestFollowedUntil(end: InstanceBackupJob): Promise<void> {
        api.start.mockRejectedValueOnce(busyRefusalNaming(RUNNING_JOB_ID, 'ui'));
        api.get.mockResolvedValueOnce(running({job_id: RUNNING_JOB_ID, phase: 'database', done_bytes: 250, total_bytes: 1000}));
        api.get.mockResolvedValueOnce(running({job_id: RUNNING_JOB_ID, phase: ENCRYPTING, done_bytes: 900, total_bytes: 1000})).mockResolvedValueOnce(end);
        render(BackupDownloadCard);
        expect(modeClear(), 'precondition: clear, the default').toBeChecked();

        await clickCreate();

        expect(startArguments(), 'precondition: a clear request, no password').toEqual([]);
        expect(api.get.mock.calls, 'the backup the refusal names is read').toEqual([[RUNNING_JOB_ID]]);
        expect(card(), 'followed as today: its progress while it runs').toHaveAttribute('data-state', 'running');
        expect(screen.getByTestId('backup-progress')).toHaveAttribute('data-phase', 'database');
        expect(progressBar()).toHaveAttribute('aria-valuenow', '25');
        expect(sessionStorage.getItem(KEY), 'precondition: the backup followed is remembered').toBe(RUNNING_JOB_ID);

        await elapse(POLL_MS);

        expect(card(), 'followed up to its last phase: the check is at the end').toHaveAttribute('data-state', 'running');
        expect(screen.getByTestId('backup-progress')).toHaveAttribute('data-phase', 'encrypting');
        expect(progressBar()).toHaveAttribute('aria-valuenow', '90');
        expect(screen.queryByTestId('backup-error'), 'no error while it runs').toBeNull();
        expect(notify, 'nothing to announce while it runs').not.toHaveBeenCalled();

        await elapse(POLL_MS);

        expect(api.get, 'precondition: read three times, the last one its end').toHaveBeenCalledTimes(3);
    }

    it('secure, the password typed twice, «Create» refused by a running backup of origin ui, nothing on offer: failed, the busy alert; never an archive nor its link, that backup never read, no backup.created, one backup.failed with the busy toast (red today)', async () => {
        api.start.mockRejectedValueOnce(busyRefusalNaming(RUNNING_JOB_ID, 'ui'));
        // Another tab's or another administrator's clear backup: a read would find it running, then its .zip ready, and
        // the assertions below would say so.
        api.get.mockResolvedValueOnce(running({job_id: RUNNING_JOB_ID})).mockResolvedValue(done({job_id: RUNNING_JOB_ID}));
        render(BackupDownloadCard);

        await startSecure();

        expect(api.start.mock.calls, 'precondition: a secure request, its password sent').toEqual([[PASSWORD]]);
        expect(card(), 'a secure request followed a backup it may not have started').toHaveAttribute('data-state', 'failed');
        expect(card()).toHaveAttribute('data-error-code', 'backup_busy');
        expect(card()).toHaveAttribute('data-busy', 'false');
        const alert = screen.getByRole('alert');
        expect(alert, 'the alert is the error of the card').toHaveAttribute('data-testid', 'backup-error');
        expect(alert).toHaveAttribute('data-error-code', 'backup_busy');
        expect(alert, 'the alert says the busy sentence, and nothing else').toHaveTextContent(exactly(BUSY));

        await elapse(10 * POLL_MS);

        expect(api.get, 'the backup the 409 names was read: nothing proves it is the one asked for').not.toHaveBeenCalled();
        expect(card(), 'still failed: nothing followed').toHaveAttribute('data-state', 'failed');
        expect(screen.queryByTestId('backup-ready'), 'an archive offered to a secure request that may not be its own').toBeNull();
        expect(screen.queryByTestId('backup-download-link')).toBeNull();
        expect(screen.queryByTestId('backup-progress'), 'a backup this card did not start followed').toBeNull();
        expect(sessionStorage.getItem(KEY), 'a backup this card did not start remembered').toBeNull();
        expect(events('backup.created'), 'no archive announced').toEqual([]);
        expect(events(), 'one backup.failed, the refused start, with the busy toast').toEqual([{name: 'backup.failed', detail: {code: 'backup_busy', what: 'start', job_id: null}, toast: {variant: 'error', message: BUSY}}]);
    });

    it('clear, «Create» refused by a running backup of origin ui that runs, then ends done with encrypted: true: its progress while it runs, then failed with the busy alert — no archive, no link, no backup.created, one busy toast (red today)', async () => {
        await clearRequestFollowedUntil(done({job_id: RUNNING_JOB_ID, file_name: SECURE_FILE_NAME, encrypted: true}));

        expect(card(), 'a sealed archive offered to a clear request: another administrator may have asked for it, with a password this user never knew').toHaveAttribute('data-state', 'failed');
        expect(card()).toHaveAttribute('data-error-code', 'backup_busy');
        expect(card()).toHaveAttribute('data-busy', 'false');
        const alert = screen.getByRole('alert');
        expect(alert, 'the alert is the error of the card').toHaveAttribute('data-testid', 'backup-error');
        expect(alert, 'the alert says the busy sentence, and nothing else').toHaveTextContent(exactly(BUSY));
        expect(screen.queryByTestId('backup-ready'), 'not presented').toBeNull();
        expect(screen.queryByTestId('backup-download-link'), 'not presented: no link to it').toBeNull();
        expect(screen.queryByTestId('backup-encrypted-note')).toBeNull();
        expect(screen.queryByTestId('backup-progress'), 'its end is known: no progress left').toBeNull();
        expect(screen.queryByTestId('backup-recheck'), 'forgotten: nothing to check again').toBeNull();
        expect(sessionStorage.getItem(KEY), 'forgotten').toBeNull();
        expect(events('backup.created'), 'not presented: not announced as an archive either').toEqual([]);
        expect(events(), 'one backup.failed, with the busy toast').toEqual([{name: 'backup.failed', detail: {code: 'backup_busy', what: 'start', job_id: null}, toast: {variant: 'error', message: BUSY}}]);

        await elapse(10 * POLL_MS);

        expect(api.get, 'a forgotten backup was read again').toHaveBeenCalledTimes(3);
        expect(card()).toHaveAttribute('data-state', 'failed');
    });

    it('clear, the same backup ending done with encrypted: false: offered — its archive, its link, the privacy notice on the card —, backup.created once (green today: the guard)', async () => {
        await clearRequestFollowedUntil(done({job_id: RUNNING_JOB_ID}));

        expect(card()).toHaveAttribute('data-state', 'done');
        expect(card()).toHaveAttribute('data-error-code', '');
        const ready = screen.getByTestId('backup-ready');
        const link = within(ready).getByTestId('backup-download-link');
        expect(link).toHaveAttribute('href', `/api/v1/backup/instance/jobs/${RUNNING_JOB_ID}/file`);
        expect(link).toHaveAttribute('download', FILE_NAME);
        expect(within(ready).queryByTestId('backup-encrypted-note'), 'a clear archive').toBeNull();
        expect(screen.getByTestId('backup-privacy-notice'), 'a clear archive: the privacy notice is on the card').toHaveTextContent(exactly('backup.download.privacy'));
        expect(screen.queryByTestId('backup-error'), 'the backup asked for: no error').toBeNull();
        expect(sessionStorage.getItem(KEY), 'the archive must stay downloadable after a reload').toBe(RUNNING_JOB_ID);
        expect(events(), 'followed as one started here: its end announced, once, with no toast').toEqual([{name: 'backup.created', detail: {job_id: RUNNING_JOB_ID, file_size: FILE_SIZE, warnings: [], encrypted: false}}]);
    });
});
