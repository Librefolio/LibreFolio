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
 *     `error` toast; `backup.deleted` and `backup.download.started` (silent); none for a job picked up after a reload.
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
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
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

vi.mock('./backupApi', async () => {
    const actual = await vi.importActual<typeof import('./backupApi')>('./backupApi');
    return {...actual, startInstanceBackup: vi.fn(), getInstanceBackupJob: vi.fn(), deleteInstanceBackupJob: vi.fn()};
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

function job(overrides: Partial<InstanceBackupJob> = {}): InstanceBackupJob {
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
        ...overrides,
    };
}

const running = (overrides: Partial<InstanceBackupJob> = {}) => job({status: 'running', ...overrides});

const done = (overrides: Partial<InstanceBackupJob> = {}) => job({status: 'done', phase: null, done_bytes: FILE_SIZE, total_bytes: FILE_SIZE, finished_at: '2026-10-15T12:03:00Z', file_name: FILE_NAME, file_size: FILE_SIZE, ...overrides});

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

        expect(events()).toEqual([{name: 'backup.created', detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings: []}}]);
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
                detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings},
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
            {name: 'backup.created', detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings: []}},
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
        expect(events(), 'a job seen running here that ended meanwhile is news: announced, once').toEqual([{name: 'backup.created', detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings: []}}]);
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
        expect(events()).toEqual([{name: 'backup.created', detail: {job_id: JOB_ID, file_size: FILE_SIZE, warnings: []}}]);
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
