// @vitest-environment jsdom
/**
 * BackupJobController — one instance backup, followed from its start to its download (backupJob.svelte.ts).
 *
 * The contract under test:
 *   - `start()`: `starting` while the request is out; the job it answers is followed — `running` is remembered in the
 *     storage and read again every `pollMs`, `done` is announced once (`onDone`) and never read again; a refusal
 *     (`backup_busy`, `backup_folder_unusable`, `backup_failed`, `backup_no_space` — B-30's 507 on a full disk —,
 *     `network`, `unexpected`) is announced once as
 *     `onFailed(code, 'start', null)` and leaves the storage as it was — `failed` with no job, or, when an archive was on
 *     offer (`done`), `done` with that same archive still on offer and the error beside it (decision 1);
 *   - polling: a read that fails while the job runs is retried after `pollMs × (1 + failures in a row)`, capped at five
 *     times `pollMs`, and one good read resets the count; `maxPollFailures` failures in a row stop it — `failed`,
 *     `network`, failure `read`, the last job kept, announced once, no timer left; a job the server no longer has (404
 *     `backup_job_not_found`) fails at once (`read`) and is forgotten; a job read as `failed` fails (`job`) with its
 *     `error_code` (`backup_failed` when it has none) and is forgotten;
 *   - `resume()`: `loading` while it reads the job the storage names (an id that is not 32 lowercase hex digits is never
 *     read); running → polling, its end announced; done → `done`, silently; gone → `idle`, forgotten, silently; no
 *     answer → `failed`/`network`, silently, the id kept for a recheck; a no-op unless `idle`;
 *   - `recheck()`, only while `canRecheck` holds: `loading` while it reads the followed job again, then whatever the
 *     server says — a failed read announced, a job's end only when it is news; otherwise it does nothing at all (no
 *     request, no state change): not from `done`, not after a refused delete, not after a failed job, not while busy;
 *   - the end of a job — `onDone`, or `onFailed(code, 'job', job)` — is announced once, and only for a job this
 *     controller started or saw `running`: one picked up already finished, by `resume()` or `recheck()`, never is; one
 *     seen running whose reads then failed is, when a recheck finds it finished (decision 2);
 *   - `remove()`, from `done` only: `deleting` (busy) while the request is out; deleted, or already gone → `idle`,
 *     forgotten; any other answer → back to `done` with the same archive, the error beside it, announced once as
 *     `onFailed(code, 'remove', job)` (decision 3);
 *   - `failure` names what failed while `errorCode` is set, and both are null otherwise; `canRecheck` holds only in
 *     `failed`, with a job to read, after a refused start (any code: the followed job may be what keeps the server
 *     busy) or after a read with no usable answer (`network`, `unexpected`) (decision 1, revised);
 *   - `start()` while busy is ignored; `dispose()` and `reset()` drop every answer still on its way;
 *   - a storage that throws, or none at all, never breaks the flow; `backupProgress` is `null` until the size is known,
 *     then the share written, clamped to [0, 1].
 *
 * Every test injects a fake api and an in-memory storage, and runs on fake timers: a poll is a timer, so the clock is
 * advanced by exactly the pause the contract names, and "not before" is checked one millisecond short of it. `pollMs`
 * and `maxPollFailures` are not the defaults, so a controller that ignored them would be seen; the defaults have their
 * own cases. `$lib/api` is mocked with the three backup aliases, which only the last group (no `api` option) reaches.
 *
 * jsdom, not node: `busy` and `progress` are `$derived`, which the node environment leaves stale (see
 * `$test/runes.svelte`); `assertEffectsRun()` fails the whole file loudly if the docblock above is ever lost.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {assertEffectsRun} from '$test/runes.svelte';
import type {InstanceBackupJob} from './backupApi';

const zodios = vi.hoisted(() => ({
    start_instance_backup_api_v1_backup_instance_post: vi.fn(),
    get_instance_backup_job_api_v1_backup_instance_jobs__job_id__get: vi.fn(),
    delete_instance_backup_job_api_v1_backup_instance_jobs__job_id__delete: vi.fn(),
}));
vi.mock('$lib/api', () => ({zodiosApi: zodios, schemas: {}}));

import {BACKUP_JOB_STORAGE_KEY, BackupJobController, backupProgress, type BackupFailure, type BackupJobApi, type BackupJobOptions, type BackupJobState} from './backupJob.svelte';

// --- Fixtures -------------------------------------------------------------------------------------------------------

const JOB_ID = '0123456789abcdef0123456789abcdef';
const OTHER_JOB_ID = 'fedcba9876543210fedcba9876543210';
const KEY = BACKUP_JOB_STORAGE_KEY;
/** Not the default pause (1000 ms). */
const POLL_MS = 300;
/** Not the default count (5). */
const MAX_FAILURES = 3;

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
        ...overrides,
    };
}

const running = (overrides: Partial<Job> = {}) => job({status: 'running', phase: 'database', ...overrides});

const done = (overrides: Partial<Job> = {}) => job({status: 'done', phase: null, done_bytes: 4096, total_bytes: 4096, finished_at: '2026-10-15T12:01:00Z', file_name: 'librefolio-backup-20261015-120000.zip', file_size: 4096, ...overrides});

const failedJob = (errorCode: InstanceBackupJob['error_code'], overrides: Partial<Job> = {}) => job({status: 'failed', phase: null, finished_at: '2026-10-15T12:01:00Z', error_code: errorCode, ...overrides});

/** A refusal as the backup routes word it, raised by axios: `detail: {code, message}`. */
function refusal(status: number, code: string) {
    return {isAxiosError: true, message: `Request failed with status code ${status}`, response: {status, data: {detail: {code, message: `refused: ${code}`}}}};
}

/** No answer came (down, unreachable, timed out): axios rejects with no `response`. */
const noAnswer = () => ({isAxiosError: true, message: 'Network Error', code: 'ERR_NETWORK', response: undefined});

/** An answer without a code: FastAPI's default 500. */
const codelessAnswer = () => ({isAxiosError: true, message: 'Request failed with status code 500', response: {status: 500, data: {detail: 'Internal Server Error'}}});

interface Deferred<T> {
    promise: Promise<T>;
    resolve: (value: T) => void;
    reject: (reason: unknown) => void;
}

function deferred<T>(): Deferred<T> {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

function fakeApi() {
    return {
        start: vi.fn<BackupJobApi['start']>(),
        get: vi.fn<BackupJobApi['get']>(),
        remove: vi.fn<BackupJobApi['remove']>(),
    };
}

/** A sessionStorage stand-in the test can read back. */
function memoryStorage(initial: Record<string, string> = {}) {
    const items = new Map<string, string>(Object.entries(initial));
    return {
        items,
        getItem: vi.fn((key: string) => items.get(key) ?? null),
        setItem: vi.fn((key: string, value: string) => {
            items.set(key, String(value));
        }),
        removeItem: vi.fn((key: string) => {
            items.delete(key);
        }),
    };
}

const controllers: BackupJobController[] = [];

/** A controller over a fake api and an in-memory storage; `stored` is the job id a previous page left in it. */
function setup(options: BackupJobOptions & {stored?: string} = {}) {
    const {stored, ...overrides} = options;
    const api = fakeApi();
    const storage = memoryStorage(stored === undefined ? {} : {[KEY]: stored});
    const onDone = vi.fn<NonNullable<BackupJobOptions['onDone']>>();
    const onFailed = vi.fn<NonNullable<BackupJobOptions['onFailed']>>();
    const controller = new BackupJobController({api, storage, pollMs: POLL_MS, maxPollFailures: MAX_FAILURES, onDone, onFailed, ...overrides});
    controllers.push(controller);
    return {controller, api, storage, onDone, onFailed};
}

/** Every read answered in turn, and the time each one came, on the fake clock (0 when the test began). */
function answerReads(api: ReturnType<typeof fakeApi>, answers: Array<() => Promise<InstanceBackupJob>>): number[] {
    const at: number[] = [];
    api.get.mockImplementation(() => {
        at.push(Date.now());
        const answer = answers.shift();
        return answer ? answer() : Promise.reject(new Error('a read this test did not expect'));
    });
    return at;
}

const ok = (answer: InstanceBackupJob) => () => Promise.resolve(answer);
const ko = (error: unknown) => () => Promise.reject(error);

beforeAll(() => {
    assertEffectsRun();
});

beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(0);
    for (const fn of Object.values(zodios)) fn.mockReset();
});

afterEach(() => {
    for (const controller of controllers.splice(0)) controller.dispose();
    vi.useRealTimers();
    sessionStorage.clear();
});

// --- start() --------------------------------------------------------------------------------------------------------

describe('start(): a backup followed to its archive', () => {
    it('starting while the request is out; running, remembered and read again after pollMs; done announced once and never read again', async () => {
        const {controller, api, storage, onDone, onFailed} = setup();
        const answer = deferred<InstanceBackupJob>();
        api.start.mockReturnValueOnce(answer.promise);
        api.get.mockResolvedValueOnce(running({phase: 'files', done_bytes: 512, total_bytes: 2048})).mockResolvedValueOnce(done());

        const started = controller.start();
        expect(controller.state).toBe('starting');
        expect(controller.busy).toBe(true);
        expect(controller.job).toBeNull();
        expect(api.start).toHaveBeenCalledTimes(1);

        answer.resolve(running());
        await started;
        expect(controller.state).toBe('running');
        expect(controller.busy).toBe(true);
        expect(controller.job).toEqual(running());
        expect(controller.progress, 'the size is not known yet').toBeNull();
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY), 'a reload must find the job again').toBe(JOB_ID);

        await vi.advanceTimersByTimeAsync(POLL_MS - 1);
        expect(api.get, 'the job was read again before pollMs').not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(1);
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenLastCalledWith(JOB_ID);
        expect(controller.state).toBe('running');
        expect(controller.job?.phase).toBe('files');
        expect(controller.progress).toBe(0.25);

        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(api.get).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('done');
        expect(controller.busy).toBe(false);
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(controller.job).toEqual(done());
        expect(controller.progress).toBe(1);
        expect(storage.items.get(KEY), 'the archive must stay downloadable after a reload').toBe(JOB_ID);
        expect(onDone).toHaveBeenCalledTimes(1);
        expect(onDone).toHaveBeenCalledWith(done());
        expect(vi.getTimerCount(), 'a timer outlived the job').toBe(0);

        await vi.advanceTimersByTimeAsync(100 * POLL_MS);
        expect(api.get, 'a finished job was read again').toHaveBeenCalledTimes(2);
        expect(onDone).toHaveBeenCalledTimes(1);
        expect(onFailed).not.toHaveBeenCalled();
    });

    it.each<[string, () => unknown]>([
        ['backup_busy', () => refusal(409, 'backup_busy')],
        ['backup_folder_unusable', () => refusal(500, 'backup_folder_unusable')],
        ['backup_failed', () => refusal(500, 'backup_failed')],
        // B-30: a start on a full disk is refused before any job exists.
        ['backup_no_space', () => refusal(507, 'backup_no_space')],
        ['network', noAnswer],
        ['unexpected', codelessAnswer],
    ])('a start refused with %s: failed with that code and no job, announced once, the stored job left alone and offered to recheck', async (code, refused) => {
        const {controller, api, storage, onDone, onFailed} = setup({stored: OTHER_JOB_ID});
        api.start.mockRejectedValueOnce(refused());

        await controller.start();

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('start');
        expect(controller.job).toBeNull();
        expect(controller.busy).toBe(false);
        expect(controller.followedJobId).toBe(OTHER_JOB_ID);
        expect(controller.canRecheck, 'a job is still followed: reading it may tell its fate, whatever refused the start').toBe(true);
        expect(onFailed).toHaveBeenCalledTimes(1);
        expect(onFailed).toHaveBeenCalledWith(code, 'start', null);
        expect(onDone).not.toHaveBeenCalled();
        expect(storage.setItem).not.toHaveBeenCalled();
        expect(storage.removeItem).not.toHaveBeenCalled();
        expect(storage.items.get(KEY)).toBe(OTHER_JOB_ID);
        expect(api.get).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });

    it.each<[string, () => unknown]>([
        ['backup_busy', () => refusal(409, 'backup_busy')],
        ['network', noAnswer],
    ])('the stranded job: the polling gave up on J, "Try again" was refused (%s); the recheck reads J, follows it running, announces its end once', async (code, refused) => {
        const {controller, api, storage, onDone, onFailed} = setup();
        api.start.mockResolvedValueOnce(running()).mockRejectedValueOnce(refused());
        api.get.mockRejectedValue(noAnswer());
        await controller.start();
        await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);
        expect(controller.state, 'precondition: the polling gave up on J').toBe('failed');
        expect(controller.failure).toBe('read');

        await controller.start();

        expect(api.start).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('failed');
        expect(controller.failure).toBe('start');
        expect(controller.job, 'a failed start offers no job').toBeNull();
        expect(controller.followedJobId, 'J is still followed').toBe(JOB_ID);
        expect(storage.items.get(KEY)).toBe(JOB_ID);
        expect(controller.canRecheck, 'J may be what keeps the server busy: reading it again may tell its fate').toBe(true);

        api.get.mockReset();
        api.get.mockResolvedValueOnce(running({phase: 'finalizing'})).mockResolvedValueOnce(done());
        const rechecked = controller.recheck();
        expect(controller.state).toBe('loading');
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(api.get.mock.calls, 'the recheck must read J').toEqual([[JOB_ID]]);
        await rechecked;
        expect(controller.state).toBe('running');
        expect(controller.job?.phase).toBe('finalizing');
        expect(onDone).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('done');
        expect(controller.job).toEqual(done());
        expect(onDone.mock.calls, 'J was seen running here: its end is news, once').toEqual([[done()]]);
        expect(onFailed.mock.calls).toEqual([
            ['network', 'read', running()],
            [code, 'start', null],
        ]);
    });

    it.each<[string, () => unknown]>([
        ['backup_busy', () => refusal(409, 'backup_busy')],
        ['network', noAnswer],
    ])('a start refused (%s) with nothing followed: failed, no job, no recheck, and recheck() sends nothing', async (_case, refused) => {
        const {controller, api} = setup();
        api.start.mockRejectedValueOnce(refused());

        await controller.start();
        await controller.recheck();

        expect(controller.state).toBe('failed');
        expect(controller.failure).toBe('start');
        expect(controller.job).toBeNull();
        expect(controller.followedJobId).toBeNull();
        expect(controller.canRecheck).toBe(false);
        expect(api.get).not.toHaveBeenCalled();
    });
});

describe('start() from done: a new backup that cannot start leaves the archive on offer (decision 1)', () => {
    /** An archive ready to download, of a backup started here, its onDone already received. */
    async function archiveOnOffer() {
        const context = setup();
        context.api.start.mockResolvedValueOnce(done());
        await context.controller.start();
        expect(context.controller.state, 'precondition: the archive is on offer').toBe('done');
        expect(context.onDone, 'precondition: the archive was announced').toHaveBeenCalledTimes(1);
        context.onDone.mockClear();
        context.api.start.mockReset();
        return {...context, archive: context.controller.job!};
    }

    it('starting while the request is out: busy, no job, no error', async () => {
        const {controller, api} = await archiveOnOffer();
        const answer = deferred<InstanceBackupJob>();
        api.start.mockReturnValueOnce(answer.promise);

        const started = controller.start();

        expect(controller.state).toBe('starting');
        expect(controller.busy).toBe(true);
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        answer.reject(noAnswer());
        await started;
        expect(controller.state).toBe('done');
    });

    it.each<[string, () => unknown]>([
        ['network', noAnswer],
        ['backup_busy', () => refusal(409, 'backup_busy')],
        ['backup_folder_unusable', () => refusal(500, 'backup_folder_unusable')],
        ['unexpected', codelessAnswer],
    ])('refused with %s: done, the same archive on offer, the error beside it, no recheck, announced once', async (code, refused) => {
        const {controller, api, storage, onDone, onFailed, archive} = await archiveOnOffer();
        api.start.mockRejectedValueOnce(refused());

        await controller.start();

        expect(controller.state).toBe('done');
        expect(controller.job, 'the archive on offer must be the one offered before').toBe(archive);
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('start');
        expect(controller.busy).toBe(false);
        expect(controller.canRecheck).toBe(false);
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY), 'a reload must still find the archive').toBe(JOB_ID);
        expect(onFailed.mock.calls).toEqual([[code, 'start', null]]);
        expect(onDone, 'a refused start is not a new archive').not.toHaveBeenCalled();
        expect(api.get).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });

    it('refused twice in a row (network, then backup_busy): the archive stays on offer, each refusal announced once', async () => {
        const {controller, api, storage, onDone, onFailed, archive} = await archiveOnOffer();
        api.start.mockRejectedValueOnce(noAnswer()).mockRejectedValueOnce(refusal(409, 'backup_busy'));

        await controller.start();
        expect(controller.state).toBe('done');
        expect(controller.errorCode).toBe('network');

        await controller.start();

        expect(api.start).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('done');
        expect(controller.job).toBe(archive);
        expect(controller.errorCode).toBe('backup_busy');
        expect(controller.failure).toBe('start');
        expect(controller.canRecheck).toBe(false);
        expect(storage.items.get(KEY)).toBe(JOB_ID);
        expect(onFailed.mock.calls).toEqual([
            ['network', 'start', null],
            ['backup_busy', 'start', null],
        ]);
        expect(onDone).not.toHaveBeenCalled();
    });

    it('a new start that succeeds after a refusal replaces the archive: the error cleared, the new job followed', async () => {
        const {controller, api, storage, onFailed} = await archiveOnOffer();
        api.start.mockRejectedValueOnce(noAnswer()).mockResolvedValueOnce(running({job_id: OTHER_JOB_ID}));
        await controller.start();
        onFailed.mockClear();

        await controller.start();

        expect(controller.state).toBe('running');
        expect(controller.job?.job_id).toBe(OTHER_JOB_ID);
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(controller.followedJobId).toBe(OTHER_JOB_ID);
        expect(storage.items.get(KEY)).toBe(OTHER_JOB_ID);
        expect(onFailed).not.toHaveBeenCalled();
    });
});

describe('start(): ignored while busy', () => {
    it('start() is ignored while a start is out and while the job runs', async () => {
        const {controller, api} = setup();
        const answer = deferred<InstanceBackupJob>();
        api.start.mockReturnValueOnce(answer.promise);

        const started = controller.start();
        await controller.start();
        expect(api.start, 'a second backup was started while the first request was out').toHaveBeenCalledTimes(1);

        answer.resolve(running());
        await started;
        await controller.start();
        expect(api.start, 'a second backup was started while one runs').toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('running');
        expect(controller.job).toEqual(running());
        expect(vi.getTimerCount(), 'the polling of the running job was lost').toBe(1);
    });

    it('start() is ignored while the followed job is being read', async () => {
        const {controller, api} = setup({stored: JOB_ID});
        const read = deferred<InstanceBackupJob>();
        api.get.mockReturnValueOnce(read.promise);

        const resumed = controller.resume();
        expect(controller.state).toBe('loading');
        await controller.start();
        expect(api.start).not.toHaveBeenCalled();

        read.resolve(running());
        await resumed;
        expect(controller.state).toBe('running');
    });
});

// --- polling --------------------------------------------------------------------------------------------------------

describe('polling a running job', () => {
    it('a failed read is retried, and one good read resets the count: no failure while the reads recover', async () => {
        const {controller, api, onDone, onFailed} = setup();
        api.start.mockResolvedValueOnce(running());
        const readsAt = answerReads(api, [ko(noAnswer()), ko(codelessAnswer()), ok(running({done_bytes: 10, total_bytes: 20})), ko(noAnswer()), ok(done())]);
        await controller.start();

        await vi.advanceTimersByTimeAsync((1 + 2) * POLL_MS);
        expect(readsAt.map((at) => at / POLL_MS)).toEqual([1, 3]);
        expect(controller.state, `two failed reads of ${MAX_FAILURES} allowed`).toBe('running');
        expect(controller.errorCode).toBeNull();
        expect(controller.busy).toBe(true);
        expect(onFailed).not.toHaveBeenCalled();

        // The third read succeeds: the fourth fails, but it is the first of a new run, not the third in a row.
        await vi.advanceTimersByTimeAsync((3 + 1 + 2) * POLL_MS);
        expect(readsAt.map((at) => at / POLL_MS)).toEqual([1, 3, 6, 7, 9]);
        expect(controller.state).toBe('done');
        expect(onDone).toHaveBeenCalledTimes(1);
        expect(onFailed).not.toHaveBeenCalled();
    });

    it('after one failed read, the next comes at twice pollMs, not before', async () => {
        const {controller, api} = setup();
        api.start.mockResolvedValueOnce(running());
        api.get.mockRejectedValueOnce(noAnswer()).mockResolvedValueOnce(running());
        await controller.start();

        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('running');

        await vi.advanceTimersByTimeAsync(2 * POLL_MS - 1);
        expect(api.get, 'the read after a failure came before 2 × pollMs').toHaveBeenCalledTimes(1);
        await vi.advanceTimersByTimeAsync(1);
        expect(api.get).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('running');
    });

    it('the pause grows by pollMs with every failed read in a row, up to five times pollMs', async () => {
        const {controller, api, onFailed} = setup({maxPollFailures: 8});
        api.start.mockResolvedValueOnce(running());
        const readsAt: number[] = [];
        api.get.mockImplementation(() => {
            readsAt.push(Date.now());
            return Promise.reject(noAnswer());
        });
        await controller.start();

        await vi.advanceTimersByTimeAsync(100 * POLL_MS);

        const pauses = readsAt.map((at, index) => at - (index === 0 ? 0 : readsAt[index - 1]));
        expect(pauses.map((pause) => pause / POLL_MS)).toEqual([1, 2, 3, 4, 5, 5, 5, 5]);
        expect(controller.state).toBe('failed');
        expect(onFailed).toHaveBeenCalledTimes(1);
    });

    it('maxPollFailures failed reads in a row stop the polling: failed, network, the last job kept, announced once, no timer left', async () => {
        const {controller, api, storage, onDone, onFailed} = setup();
        const lastSeen = running({phase: 'files', done_bytes: 100, total_bytes: 400});
        api.start.mockResolvedValueOnce(running());
        api.get.mockResolvedValueOnce(lastSeen).mockRejectedValue(noAnswer());
        await controller.start();
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(controller.job).toEqual(lastSeen);

        await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);

        expect(api.get).toHaveBeenCalledTimes(1 + MAX_FAILURES);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('network');
        expect(controller.failure).toBe('read');
        expect(controller.canRecheck, 'the job may still be running: reading it again may still tell its fate').toBe(true);
        expect(controller.busy).toBe(false);
        expect(controller.job, 'the card keeps the last job it read').toEqual(lastSeen);
        expect(controller.followedJobId, 'the job may still be running: a recheck asks for it').toBe(JOB_ID);
        expect(storage.items.get(KEY)).toBe(JOB_ID);
        expect(onFailed).toHaveBeenCalledTimes(1);
        expect(onFailed).toHaveBeenCalledWith('network', 'read', lastSeen);
        expect(onDone).not.toHaveBeenCalled();
        expect(vi.getTimerCount(), 'a timer survived the end of the polling').toBe(0);

        await vi.advanceTimersByTimeAsync(100 * POLL_MS);
        expect(api.get).toHaveBeenCalledTimes(1 + MAX_FAILURES);
        expect(onFailed).toHaveBeenCalledTimes(1);
    });

    it.each<[string, number, number | undefined]>([
        ['by default', 5, undefined],
        ['at 1', 1, 1],
        ['at 0, read as 1', 1, 0],
        ['at -2, read as 1', 1, -2],
    ])('maxPollFailures %s: the polling stops after %i failed reads in a row', async (_case, reads, maxPollFailures) => {
        const {controller, api, onFailed} = setup({maxPollFailures});
        api.start.mockResolvedValueOnce(running());
        api.get.mockRejectedValue(noAnswer());
        await controller.start();

        await vi.advanceTimersByTimeAsync(100 * POLL_MS);

        expect(api.get).toHaveBeenCalledTimes(reads);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('network');
        expect(onFailed).toHaveBeenCalledTimes(1);
    });

    it('a job the server no longer has fails at once with backup_job_not_found, and is forgotten', async () => {
        const {controller, api, storage, onDone, onFailed} = setup();
        api.start.mockResolvedValueOnce(running());
        api.get.mockRejectedValue(refusal(404, 'backup_job_not_found'));
        await controller.start();

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get, 'a job that is gone is not asked for again').toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('backup_job_not_found');
        expect(controller.failure).toBe('read');
        expect(controller.canRecheck).toBe(false);
        expect(controller.job).toBeNull();
        expect(controller.followedJobId).toBeNull();
        expect(storage.items.has(KEY)).toBe(false);
        expect(onFailed).toHaveBeenCalledTimes(1);
        expect(onFailed).toHaveBeenCalledWith('backup_job_not_found', 'read', null);
        expect(onDone).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });

    it.each<[InstanceBackupJob['error_code'], string]>([
        ['backup_no_space', 'backup_no_space'],
        ['backup_interrupted', 'backup_interrupted'],
        ['backup_failed', 'backup_failed'],
        [null, 'backup_failed'],
        [undefined, 'backup_failed'],
    ])('a job read as failed with error_code %s fails with %s: kept for the card, forgotten, announced once', async (errorCode, expected) => {
        const {controller, api, storage, onDone, onFailed} = setup();
        const ended = failedJob(errorCode);
        api.start.mockResolvedValueOnce(running());
        api.get.mockResolvedValueOnce(ended);
        await controller.start();

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe(expected);
        expect(controller.failure).toBe('job');
        expect(controller.canRecheck, 'a job that failed has nothing left to tell').toBe(false);
        expect(controller.job).toEqual(ended);
        expect(controller.followedJobId).toBeNull();
        expect(storage.items.has(KEY), 'a failed job has no archive to pick up after a reload').toBe(false);
        expect(onFailed).toHaveBeenCalledTimes(1);
        expect(onFailed).toHaveBeenCalledWith(expected, 'job', ended);
        expect(onDone).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });
});

// --- resume() -------------------------------------------------------------------------------------------------------

describe('resume(): the job this tab followed before a reload', () => {
    it('loading while it reads the stored job; running → polled, and its end is announced', async () => {
        const {controller, api, onDone, onFailed} = setup({stored: JOB_ID});
        expect(controller.followedJobId).toBe(JOB_ID);
        const read = deferred<InstanceBackupJob>();
        api.get.mockReturnValueOnce(read.promise).mockResolvedValueOnce(done());

        const resumed = controller.resume();
        expect(controller.state).toBe('loading');
        expect(controller.busy).toBe(true);
        expect(api.get).toHaveBeenCalledWith(JOB_ID);

        read.resolve(running());
        await resumed;
        expect(controller.state).toBe('running');
        expect(controller.job).toEqual(running());
        expect(onDone).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(api.get).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('done');
        expect(onDone, 'a job followed here that ends here is news').toHaveBeenCalledTimes(1);
        expect(onFailed).not.toHaveBeenCalled();
    });

    it('a job already done: done, silently', async () => {
        const {controller, api, storage, onDone, onFailed} = setup({stored: JOB_ID});
        api.get.mockResolvedValueOnce(done());

        await controller.resume();

        expect(controller.state).toBe('done');
        expect(controller.busy).toBe(false);
        expect(controller.job).toEqual(done());
        expect(storage.items.get(KEY)).toBe(JOB_ID);
        expect(onDone, 'a job picked up already done is not news').not.toHaveBeenCalled();
        expect(onFailed).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });

    it('a job the server no longer has: idle, forgotten, silently', async () => {
        const {controller, api, storage, onFailed} = setup({stored: JOB_ID});
        api.get.mockRejectedValueOnce(refusal(404, 'backup_job_not_found'));

        await controller.resume();

        expect(controller.state).toBe('idle');
        expect(controller.errorCode).toBeNull();
        expect(controller.job).toBeNull();
        expect(controller.followedJobId).toBeNull();
        expect(storage.items.has(KEY)).toBe(false);
        expect(onFailed).not.toHaveBeenCalled();
    });

    it('no answer: failed with network, silently, the job still followed for a recheck', async () => {
        const {controller, api, storage, onFailed} = setup({stored: JOB_ID});
        api.get.mockRejectedValueOnce(noAnswer());

        await controller.resume();

        expect(api.get, 'only a running job is read again on its own').toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('network');
        expect(controller.failure).toBe('read');
        expect(controller.canRecheck, 'only the id is known, and that is enough to read the job again').toBe(true);
        expect(controller.job).toBeNull();
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY)).toBe(JOB_ID);
        expect(onFailed).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });

    it('a job that failed meanwhile: failed with its error_code, silently, forgotten', async () => {
        const {controller, api, storage, onFailed} = setup({stored: JOB_ID});
        api.get.mockResolvedValueOnce(failedJob('backup_interrupted'));

        await controller.resume();

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('backup_interrupted');
        expect(controller.failure).toBe('job');
        expect(controller.job).toEqual(failedJob('backup_interrupted'));
        expect(storage.items.has(KEY)).toBe(false);
        expect(onFailed, 'a job picked up already failed is not news').not.toHaveBeenCalled();
    });

    it.each([
        ['not hex', 'not-a-backup-job-id-at-all-00000'],
        ['upper-case hex', JOB_ID.toUpperCase()],
        ['31 digits', JOB_ID.slice(1)],
        ['33 digits', `${JOB_ID}a`],
        ['a path around a valid id', `../${JOB_ID}`],
        ['a valid id and a newline', `${JOB_ID}\n`],
        ['empty', ''],
    ])('a stored id that is %s is never read: nothing followed, no request', async (_case, stored) => {
        const {controller, api} = setup({stored});

        expect(controller.followedJobId).toBeNull();
        await controller.resume();

        expect(api.get).not.toHaveBeenCalled();
        expect(controller.state).toBe('idle');
    });

    it('nothing stored: no request', async () => {
        const {controller, api} = setup();

        await controller.resume();

        expect(api.get).not.toHaveBeenCalled();
        expect(controller.state).toBe('idle');
    });

    it('does nothing unless idle: while its read is out, once done, after a failure', async () => {
        const {controller, api} = setup({stored: JOB_ID});
        const read = deferred<InstanceBackupJob>();
        api.get.mockReturnValueOnce(read.promise);

        const first = controller.resume();
        await controller.resume();
        expect(api.get, 'the job was read twice at once').toHaveBeenCalledTimes(1);

        read.resolve(done());
        await first;
        await controller.resume();
        expect(controller.state).toBe('done');
        expect(api.get).toHaveBeenCalledTimes(1);

        // A refused start leaves the archive on offer: still done, now with an error.
        api.start.mockRejectedValueOnce(refusal(409, 'backup_busy'));
        await controller.start();
        await controller.resume();
        expect(controller.state).toBe('done');
        expect(controller.errorCode).toBe('backup_busy');
        expect(api.get).toHaveBeenCalledTimes(1);

        const other = setup({stored: JOB_ID});
        other.api.start.mockRejectedValueOnce(refusal(409, 'backup_busy'));
        await other.controller.start();
        expect(other.controller.state, 'precondition: a refused start from idle').toBe('failed');
        await other.controller.resume();
        expect(other.api.get).not.toHaveBeenCalled();
        expect(other.controller.errorCode).toBe('backup_busy');
    });
});

// --- recheck() ------------------------------------------------------------------------------------------------------

describe('recheck(): the followed job read again after its reads failed', () => {
    /** A job whose reads failed MAX_FAILURES times in a row while it ran. */
    async function pollingLostTrack() {
        const context = setup();
        context.api.start.mockResolvedValueOnce(running());
        context.api.get.mockRejectedValue(noAnswer());
        await context.controller.start();
        await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);
        expect(context.controller.state, 'precondition: the polling gave up').toBe('failed');
        expect(context.controller.errorCode).toBe('network');
        context.api.get.mockReset();
        context.onFailed.mockClear();
        return context;
    }

    it('loading while it reads, then the job as the server has it: finished meanwhile → done, announced once', async () => {
        const {controller, api, onDone, onFailed} = await pollingLostTrack();
        const read = deferred<InstanceBackupJob>();
        api.get.mockReturnValueOnce(read.promise);

        const rechecked = controller.recheck();
        expect(controller.state).toBe('loading');
        expect(controller.busy).toBe(true);
        expect(controller.errorCode, 'the error is cleared while the job is read again').toBeNull();
        expect(controller.failure).toBeNull();
        expect(controller.canRecheck).toBe(false);
        expect(api.get).toHaveBeenCalledWith(JOB_ID);

        read.resolve(done());
        await rechecked;
        expect(controller.state).toBe('done');
        expect(controller.job).toEqual(done());
        expect(onDone).toHaveBeenCalledTimes(1);
        expect(onFailed).not.toHaveBeenCalled();
    });

    it('a job still running goes back to being read every pollMs', async () => {
        const {controller, api, onDone} = await pollingLostTrack();
        api.get.mockResolvedValueOnce(running({phase: 'finalizing'})).mockResolvedValueOnce(done());

        await controller.recheck();
        expect(controller.state).toBe('running');
        expect(controller.job?.phase).toBe('finalizing');

        await vi.advanceTimersByTimeAsync(POLL_MS - 1);
        expect(api.get, 'the count of failed reads was not reset').toHaveBeenCalledTimes(1);
        await vi.advanceTimersByTimeAsync(1);
        expect(api.get).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('done');
        expect(onDone).toHaveBeenCalledTimes(1);
    });

    it('no answer again: failed with network at once, announced', async () => {
        const {controller, api, onFailed} = await pollingLostTrack();
        api.get.mockRejectedValue(noAnswer());

        await controller.recheck();

        expect(api.get, 'a recheck is one read, not a new polling').toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('network');
        expect(controller.failure).toBe('read');
        expect(controller.canRecheck).toBe(true);
        expect(controller.job).toEqual(running());
        expect(onFailed).toHaveBeenCalledTimes(1);
        expect(onFailed).toHaveBeenCalledWith('network', 'read', running());
        expect(vi.getTimerCount()).toBe(0);
    });

    it('after a failed resume, reads the followed job by its stored id', async () => {
        const {controller, api} = setup({stored: JOB_ID});
        api.get.mockRejectedValueOnce(noAnswer()).mockResolvedValueOnce(running());
        await controller.resume();
        expect(controller.job, 'precondition: only the id is known').toBeNull();

        await controller.recheck();

        expect(api.get).toHaveBeenCalledTimes(2);
        expect(api.get).toHaveBeenLastCalledWith(JOB_ID);
        expect(controller.state).toBe('running');
    });

    it('does nothing with no job to read, or while busy', async () => {
        const nothing = setup();
        nothing.api.start.mockRejectedValueOnce(noAnswer());
        await nothing.controller.start();
        expect(nothing.controller.state, 'precondition: a refused start, nothing followed').toBe('failed');
        await nothing.controller.recheck();
        expect(nothing.api.get).not.toHaveBeenCalled();
        expect(nothing.controller.errorCode).toBe('network');

        const busy = setup();
        busy.api.start.mockResolvedValueOnce(running());
        await busy.controller.start();
        await busy.controller.recheck();
        expect(busy.api.get, 'a running job was read outside its polling').not.toHaveBeenCalled();
        expect(busy.controller.state).toBe('running');
    });
});

// --- announcing -----------------------------------------------------------------------------------------------------

describe('the end of a job is announced once, and only when it is news (decision 2)', () => {
    /** The job seen running here — started here, or picked up running by resume() — then its reads failed until the polling gave up. */
    async function seenRunningThenLostTrack(how: 'started here' | 'picked up running') {
        const context = setup({stored: JOB_ID});
        const {controller, api, onFailed} = context;
        if (how === 'started here') {
            api.start.mockResolvedValueOnce(running());
            api.get.mockRejectedValue(noAnswer());
            await controller.start();
        } else {
            api.get.mockResolvedValueOnce(running()).mockRejectedValue(noAnswer());
            await controller.resume();
        }
        expect(controller.state, 'precondition: the job was seen running').toBe('running');
        await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);
        expect(controller.state, 'precondition: the polling gave up').toBe('failed');
        expect(onFailed.mock.calls, 'precondition: the failed reads were announced, once').toEqual([['network', 'read', running()]]);
        onFailed.mockClear();
        api.get.mockReset();
        return context;
    }

    it.each(['started here', 'picked up running'] as const)('a job %s whose reads failed: the recheck that finds it done announces it once; from done, a second recheck sends nothing', async (how) => {
        const {controller, api, onDone, onFailed} = await seenRunningThenLostTrack(how);
        api.get.mockResolvedValue(done());

        await controller.recheck();
        expect(controller.state).toBe('done');
        expect(onDone.mock.calls, 'a job seen running that ended meanwhile is news').toEqual([[done()]]);
        expect(controller.canRecheck).toBe(false);

        await controller.recheck();

        expect(api.get, 'a recheck from done went out').toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('done');
        expect(controller.job).toEqual(done());
        expect(onDone, 'the same archive was announced twice').toHaveBeenCalledTimes(1);
        expect(onFailed).not.toHaveBeenCalled();
    });

    it.each(['started here', 'picked up running'] as const)('a job %s whose reads failed: the recheck that finds it failed announces it once; a second recheck sends nothing', async (how) => {
        const {controller, api, onDone, onFailed} = await seenRunningThenLostTrack(how);
        const ended = failedJob('backup_no_space');
        api.get.mockResolvedValue(ended);

        await controller.recheck();
        expect(controller.state).toBe('failed');
        expect(controller.failure).toBe('job');
        expect(onFailed.mock.calls).toEqual([['backup_no_space', 'job', ended]]);
        expect(controller.canRecheck, 'a job that failed has nothing left to tell').toBe(false);

        await controller.recheck();

        expect(api.get, 'a failed job was read again').toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('backup_no_space');
        expect(onFailed, 'the same failed job was announced twice').toHaveBeenCalledTimes(1);
        expect(onDone).not.toHaveBeenCalled();
    });

    it('a job started here and polled to its end: announced once; a recheck of the archive sends nothing', async () => {
        const {controller, api, onDone} = setup();
        api.start.mockResolvedValueOnce(running());
        api.get.mockResolvedValue(done());
        await controller.start();
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(onDone, 'precondition: the end was announced').toHaveBeenCalledTimes(1);

        await controller.recheck();
        await controller.recheck();

        expect(api.get, 'a recheck from done went out').toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('done');
        expect(onDone).toHaveBeenCalledTimes(1);
    });

    it.each<[string, InstanceBackupJob, 'onDone' | 'onFailed', unknown[]]>([
        ['done', done(), 'onDone', [done()]],
        ['failed', failedJob('backup_interrupted'), 'onFailed', ['backup_interrupted', 'job', failedJob('backup_interrupted')]],
    ])('a start answered with a job already %s: started here, so announced once', async (_case, answer, callback, args) => {
        const context = setup();
        context.api.start.mockResolvedValueOnce(answer);

        await context.controller.start();

        expect(context[callback].mock.calls).toEqual([args]);
        expect(context[callback === 'onDone' ? 'onFailed' : 'onDone']).not.toHaveBeenCalled();
    });

    it('an archive picked up by resume: done, never announced, and a recheck from done sends nothing', async () => {
        const {controller, api, onDone, onFailed} = setup({stored: JOB_ID});
        api.get.mockResolvedValue(done());
        await controller.resume();
        expect(controller.state, 'precondition: picked up already done').toBe('done');

        await controller.recheck();
        await controller.recheck();

        expect(api.get, 'a recheck from done went out').toHaveBeenCalledTimes(1);
        expect(controller.state).toBe('done');
        expect(onDone, 'an archive picked up already finished is not news').not.toHaveBeenCalled();
        expect(onFailed).not.toHaveBeenCalled();
    });

    it.each<[string, InstanceBackupJob]>([
        ['done', done()],
        ['failed', failedJob('backup_failed')],
    ])('a resume that got no answer, then a recheck that finds the job %s: never seen running, so not announced', async (_case, answer) => {
        const {controller, api, onDone, onFailed} = setup({stored: JOB_ID});
        api.get.mockRejectedValueOnce(noAnswer()).mockResolvedValueOnce(answer);
        await controller.resume();
        expect(controller.canRecheck, 'precondition: a recheck is offered').toBe(true);

        await controller.recheck();

        expect(controller.state).toBe(answer.status);
        expect(controller.job).toEqual(answer);
        expect(onDone).not.toHaveBeenCalled();
        expect(onFailed).not.toHaveBeenCalled();
    });

    it('a pick-up with no answer, then a refused start, then a recheck that finds J done: never seen running, so not announced', async () => {
        const {controller, api, onDone, onFailed} = setup({stored: JOB_ID});
        api.get.mockRejectedValueOnce(noAnswer()).mockResolvedValueOnce(done());
        api.start.mockRejectedValueOnce(refusal(409, 'backup_busy'));
        await controller.resume();
        await controller.start();
        expect(controller.canRecheck, 'precondition: J is followed after the refused start').toBe(true);
        onFailed.mockClear();

        await controller.recheck();

        expect(api.get.mock.calls).toEqual([[JOB_ID], [JOB_ID]]);
        expect(controller.state).toBe('done');
        expect(onDone, 'J was never seen running here').not.toHaveBeenCalled();
        expect(onFailed).not.toHaveBeenCalled();
    });
});

// --- remove() -------------------------------------------------------------------------------------------------------

describe('remove(): the archive deleted from the server (decision 3)', () => {
    async function finished() {
        const context = setup();
        context.api.start.mockResolvedValueOnce(done());
        await context.controller.start();
        expect(context.controller.state, 'precondition: an archive is ready').toBe('done');
        context.onDone.mockClear();
        context.api.start.mockClear();
        return {...context, archive: context.controller.job!};
    }

    it('deleting while the request is out: busy, the same archive, no error; no other request can go out meanwhile', async () => {
        const {controller, api, archive} = await finished();
        const answer = deferred<void>();
        api.remove.mockReturnValueOnce(answer.promise);

        const removed = controller.remove();

        expect(controller.state).toBe('deleting');
        expect(controller.busy).toBe(true);
        expect(controller.job).toBe(archive);
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(controller.canRecheck).toBe(false);

        await controller.remove();
        await controller.start();
        await controller.recheck();
        await controller.resume();
        expect(api.remove, 'a second delete went out while the first was out').toHaveBeenCalledTimes(1);
        expect(api.start, 'a backup was started while the archive was being deleted').not.toHaveBeenCalled();
        expect(api.get, 'the job was read while it was being deleted').not.toHaveBeenCalled();
        expect(controller.state).toBe('deleting');

        answer.resolve();
        await removed;
        expect(controller.state).toBe('idle');
    });

    it.each<[string, () => Promise<void>]>([
        ['deleted', () => Promise.resolve()],
        ['already gone (backup_job_not_found)', () => Promise.reject(refusal(404, 'backup_job_not_found'))],
    ])('%s: idle, the job forgotten, nothing announced', async (_case, answer) => {
        const {controller, api, storage, onDone, onFailed} = await finished();
        api.remove.mockImplementationOnce(answer);

        await controller.remove();

        expect(api.remove).toHaveBeenCalledTimes(1);
        expect(api.remove).toHaveBeenCalledWith(JOB_ID);
        expect(controller.state).toBe('idle');
        expect(controller.busy).toBe(false);
        expect(controller.job).toBeNull();
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(controller.followedJobId).toBeNull();
        expect(storage.items.has(KEY)).toBe(false);
        expect(onFailed).not.toHaveBeenCalled();
        expect(onDone).not.toHaveBeenCalled();
    });

    it.each<[string, () => unknown]>([
        ['network', noAnswer],
        ['backup_job_running', () => refusal(409, 'backup_job_running')],
        ['unexpected', codelessAnswer],
    ])('refused with %s: back to done with the same archive, the error beside it, no recheck, announced once', async (code, refused) => {
        const {controller, api, storage, onDone, onFailed, archive} = await finished();
        api.remove.mockRejectedValueOnce(refused());

        await controller.remove();

        expect(controller.state).toBe('done');
        expect(controller.job, 'the archive may still be on the server: it stays on offer').toBe(archive);
        expect(controller.errorCode).toBe(code);
        expect(controller.failure).toBe('remove');
        expect(controller.busy).toBe(false);
        expect(controller.canRecheck).toBe(false);
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY)).toBe(JOB_ID);
        expect(onFailed.mock.calls).toEqual([[code, 'remove', archive]]);
        expect(onDone).not.toHaveBeenCalled();
    });

    it('a refused delete can be tried again: the error cleared while it is out, idle once it succeeds', async () => {
        const {controller, api, onFailed} = await finished();
        api.remove.mockRejectedValueOnce(noAnswer());
        await controller.remove();
        expect(controller.errorCode, 'precondition: the first delete was refused').toBe('network');
        const answer = deferred<void>();
        api.remove.mockReturnValueOnce(answer.promise);

        const removed = controller.remove();
        expect(controller.state).toBe('deleting');
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        answer.resolve();
        await removed;

        expect(api.remove).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('idle');
        expect(onFailed).toHaveBeenCalledTimes(1);
    });

    it.each<[string, () => Promise<ReturnType<typeof setup>>]>([
        ['with no job (idle)', async () => setup()],
        [
            'while a backup runs',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                await context.controller.start();
                return context;
            },
        ],
        [
            'while a backup starts',
            async () => {
                const context = setup();
                context.api.start.mockReturnValueOnce(deferred<InstanceBackupJob>().promise);
                void context.controller.start();
                return context;
            },
        ],
        [
            'while the job is being read',
            async () => {
                const context = setup({stored: JOB_ID});
                context.api.get.mockReturnValueOnce(deferred<InstanceBackupJob>().promise);
                void context.controller.resume();
                return context;
            },
        ],
        [
            'for a job read as failed (no archive)',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(failedJob('backup_no_space'));
                await context.controller.start();
                return context;
            },
        ],
        [
            'after the reads of a running job failed (the job kept, no archive)',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                context.api.get.mockRejectedValue(noAnswer());
                await context.controller.start();
                await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);
                return context;
            },
        ],
    ])('works from done only: ignored %s', async (_case, arrive) => {
        const {controller, api} = await arrive();
        const before = {state: controller.state, job: controller.job, errorCode: controller.errorCode};

        await controller.remove();

        expect({state: controller.state, job: controller.job, errorCode: controller.errorCode}).toEqual(before);
        expect(api.remove, 'a delete went out from a state that offers no archive').not.toHaveBeenCalled();
    });
});

// --- dispose() and reset() ------------------------------------------------------------------------------------------

describe('dispose() and reset(): answers still on their way are dropped', () => {
    it('dispose() clears the polling timer: no read follows', async () => {
        const {controller, api} = setup();
        api.start.mockResolvedValueOnce(running());
        await controller.start();
        expect(vi.getTimerCount(), 'precondition: the next read is scheduled').toBe(1);

        controller.dispose();

        expect(vi.getTimerCount()).toBe(0);
        await vi.advanceTimersByTimeAsync(100 * POLL_MS);
        expect(api.get).not.toHaveBeenCalled();
        expect(controller.state).toBe('running');
    });

    it.each<[string, (read: Deferred<InstanceBackupJob>) => void]>([
        ['a finished job', (read) => read.resolve(done())],
        ['a failed job', (read) => read.resolve(failedJob('backup_no_space'))],
        ['a job the server no longer has', (read) => read.reject(refusal(404, 'backup_job_not_found'))],
        ['no answer', (read) => read.reject(noAnswer())],
    ])('dispose() drops a read answered after it — %s: no state change, no callback, nothing forgotten', async (_case, answer) => {
        const {controller, api, storage, onDone, onFailed} = setup();
        const read = deferred<InstanceBackupJob>();
        api.start.mockResolvedValueOnce(running());
        api.get.mockReturnValueOnce(read.promise);
        await controller.start();
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(api.get, 'precondition: a read is out').toHaveBeenCalledTimes(1);

        controller.dispose();
        answer(read);
        await vi.advanceTimersByTimeAsync(100 * POLL_MS);

        expect(controller.state).toBe('running');
        expect(controller.job).toEqual(running());
        expect(controller.errorCode).toBeNull();
        expect(storage.items.get(KEY)).toBe(JOB_ID);
        expect(onDone).not.toHaveBeenCalled();
        expect(onFailed).not.toHaveBeenCalled();
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(vi.getTimerCount()).toBe(0);
    });

    it('dispose() drops a start answered after it: still starting, nothing remembered, nothing scheduled', async () => {
        const {controller, api, storage, onDone, onFailed} = setup();
        const answer = deferred<InstanceBackupJob>();
        api.start.mockReturnValueOnce(answer.promise);

        const started = controller.start();
        controller.dispose();
        answer.resolve(running());
        await started;

        expect(controller.state).toBe('starting');
        expect(controller.job).toBeNull();
        expect(storage.setItem).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
        expect(onDone).not.toHaveBeenCalled();
        expect(onFailed).not.toHaveBeenCalled();
    });

    it.each<[string, (pending: Deferred<InstanceBackupJob>) => void]>([
        ['a running job', (pending) => pending.resolve(running())],
        ['a finished job', (pending) => pending.resolve(done())],
        ['a refusal', (pending) => pending.reject(refusal(409, 'backup_busy'))],
    ])('reset() during a start drops its late answer — %s: idle, nothing remembered, nothing announced', async (_case, answer) => {
        const {controller, api, storage, onDone, onFailed} = setup();
        const pending = deferred<InstanceBackupJob>();
        api.start.mockReturnValueOnce(pending.promise);

        const started = controller.start();
        controller.reset();
        expect(controller.state).toBe('idle');
        answer(pending);
        await started;

        expect(controller.state).toBe('idle');
        expect(controller.job).toBeNull();
        expect(controller.errorCode).toBeNull();
        expect(controller.followedJobId).toBeNull();
        expect(storage.setItem).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
        expect(onDone).not.toHaveBeenCalled();
        expect(onFailed).not.toHaveBeenCalled();
    });

    it('reset() while a job runs stops the polling and forgets the job', async () => {
        const {controller, api, storage} = setup();
        api.start.mockResolvedValueOnce(running());
        await controller.start();

        controller.reset();

        expect(controller.state).toBe('idle');
        expect(controller.busy).toBe(false);
        expect(controller.followedJobId).toBeNull();
        expect(storage.items.has(KEY)).toBe(false);
        expect(vi.getTimerCount()).toBe(0);
        await vi.advanceTimersByTimeAsync(100 * POLL_MS);
        expect(api.get).not.toHaveBeenCalled();
    });

    it.each<[string, (answer: Deferred<void>) => void]>([
        ['deleted', (answer) => answer.resolve()],
        ['refused', (answer) => answer.reject(noAnswer())],
    ])('dispose() while deleting drops the answer (%s): still deleting, the archive still followed, nothing announced', async (_case, answerWith) => {
        const {controller, api, storage, onDone, onFailed} = setup();
        api.start.mockResolvedValueOnce(done());
        await controller.start();
        onDone.mockClear();
        const answer = deferred<void>();
        api.remove.mockReturnValueOnce(answer.promise);
        const removed = controller.remove();
        expect(controller.state, 'precondition: the delete is out').toBe('deleting');

        controller.dispose();
        answerWith(answer);
        await removed;

        expect(controller.state).toBe('deleting');
        expect(controller.errorCode).toBeNull();
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY)).toBe(JOB_ID);
        expect(onFailed).not.toHaveBeenCalled();
        expect(onDone).not.toHaveBeenCalled();
    });

    it('reset() while deleting: idle at once, and a refusal that comes late is dropped', async () => {
        const {controller, api, onFailed} = setup();
        api.start.mockResolvedValueOnce(done());
        await controller.start();
        const answer = deferred<void>();
        api.remove.mockReturnValueOnce(answer.promise);
        const removed = controller.remove();

        controller.reset();
        expect(controller.state).toBe('idle');
        answer.reject(noAnswer());
        await removed;

        expect(controller.state).toBe('idle');
        expect(controller.job).toBeNull();
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(onFailed).not.toHaveBeenCalled();
    });
});

// --- canRecheck -----------------------------------------------------------------------------------------------------

describe('canRecheck: in failed, with a job to read, after a refused start or a read with no usable answer — and recheck() acts only then (decision 1, revised)', () => {
    type Context = ReturnType<typeof setup>;
    interface Observed {
        state: BackupJobState;
        failure: BackupFailure | null;
        errorCode: string | null;
    }

    /** A running job, started here, whose reads all failed with `failure()` until the polling gave up. */
    async function pollingGaveUp(failure: () => unknown): Promise<Context> {
        const context = setup();
        context.api.start.mockResolvedValueOnce(running());
        context.api.get.mockRejectedValue(failure());
        await context.controller.start();
        await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);
        return context;
    }

    /** A start refused with `refused()` while a job is followed (an id left by a previous page, not resumed). */
    async function startRefusedWhileFollowing(refused: () => unknown): Promise<Context> {
        const context = setup({stored: JOB_ID});
        context.api.start.mockRejectedValueOnce(refused());
        await context.controller.start();
        return context;
    }

    /** A start refused with `refused()` with no job followed at all. */
    async function startRefusedFollowingNothing(refused: () => unknown): Promise<Context> {
        const context = setup();
        context.api.start.mockRejectedValueOnce(refused());
        await context.controller.start();
        return context;
    }

    /** An archive on offer, of a backup started here. */
    async function archiveOnOffer(): Promise<Context> {
        const context = setup();
        context.api.start.mockResolvedValueOnce(done());
        await context.controller.start();
        return context;
    }

    async function removeRefused(refused: () => unknown): Promise<Context> {
        const context = await archiveOnOffer();
        context.api.remove.mockRejectedValueOnce(refused());
        await context.controller.remove();
        return context;
    }

    async function jobFailed(errorCode: InstanceBackupJob['error_code']): Promise<Context> {
        const context = setup();
        context.api.start.mockResolvedValueOnce(running());
        context.api.get.mockResolvedValueOnce(failedJob(errorCode));
        await context.controller.start();
        await vi.advanceTimersByTimeAsync(POLL_MS);
        return context;
    }

    it.each<[string, boolean, Observed, () => Promise<Context>]>([
        // read: only with no usable answer.
        ['read, no answer: the polling gave up', true, {state: 'failed', failure: 'read', errorCode: 'network'}, () => pollingGaveUp(noAnswer)],
        ['read, answers without a code: the polling gave up', true, {state: 'failed', failure: 'read', errorCode: 'unexpected'}, () => pollingGaveUp(codelessAnswer)],
        [
            'read, no answer to a resume: only the stored id known',
            true,
            {state: 'failed', failure: 'read', errorCode: 'network'},
            async () => {
                const context = setup({stored: JOB_ID});
                context.api.get.mockRejectedValueOnce(noAnswer());
                await context.controller.resume();
                return context;
            },
        ],
        [
            'read, no answer to a recheck either',
            true,
            {state: 'failed', failure: 'read', errorCode: 'network'},
            async () => {
                const context = await pollingGaveUp(noAnswer);
                await context.controller.recheck();
                return context;
            },
        ],
        ['read, refused with any other code, the job kept (hypothetical: the read route answers only backup_job_not_found)', false, {state: 'failed', failure: 'read', errorCode: 'some_other_code'}, () => pollingGaveUp(() => refusal(409, 'some_other_code'))],
        ['read, the job gone (404)', false, {state: 'failed', failure: 'read', errorCode: 'backup_job_not_found'}, () => pollingGaveUp(() => refusal(404, 'backup_job_not_found'))],
        // start: whenever a job is still followed, whatever the code; never with nothing followed, never from done.
        ['start, no answer, a job followed', true, {state: 'failed', failure: 'start', errorCode: 'network'}, () => startRefusedWhileFollowing(noAnswer)],
        ['start, an answer without a code, a job followed', true, {state: 'failed', failure: 'start', errorCode: 'unexpected'}, () => startRefusedWhileFollowing(codelessAnswer)],
        ['start, refused as busy, a job followed', true, {state: 'failed', failure: 'start', errorCode: 'backup_busy'}, () => startRefusedWhileFollowing(() => refusal(409, 'backup_busy'))],
        ['start, refused: the backups folder is unusable, a job followed (any code qualifies)', true, {state: 'failed', failure: 'start', errorCode: 'backup_folder_unusable'}, () => startRefusedWhileFollowing(() => refusal(500, 'backup_folder_unusable'))],
        [
            'start, refused as busy after the polling gave up on the running job (the stranded job)',
            true,
            {state: 'failed', failure: 'start', errorCode: 'backup_busy'},
            async () => {
                const context = await pollingGaveUp(noAnswer);
                context.api.start.mockRejectedValueOnce(refusal(409, 'backup_busy'));
                await context.controller.start();
                return context;
            },
        ],
        [
            'start, no answer after a pick-up that got no answer',
            true,
            {state: 'failed', failure: 'start', errorCode: 'network'},
            async () => {
                const context = setup({stored: JOB_ID});
                context.api.get.mockRejectedValueOnce(noAnswer());
                await context.controller.resume();
                context.api.start.mockRejectedValueOnce(noAnswer());
                await context.controller.start();
                return context;
            },
        ],
        ['start, refused as busy, nothing followed', false, {state: 'failed', failure: 'start', errorCode: 'backup_busy'}, () => startRefusedFollowingNothing(() => refusal(409, 'backup_busy'))],
        ['start, no answer, nothing followed', false, {state: 'failed', failure: 'start', errorCode: 'network'}, () => startRefusedFollowingNothing(noAnswer)],
        [
            'start, refused after a job read as failed: that job is forgotten, nothing followed',
            false,
            {state: 'failed', failure: 'start', errorCode: 'backup_busy'},
            async () => {
                const context = await jobFailed('backup_no_space');
                context.api.start.mockRejectedValueOnce(refusal(409, 'backup_busy'));
                await context.controller.start();
                return context;
            },
        ],
        [
            'start, no answer while an archive is on offer: still done',
            false,
            {state: 'done', failure: 'start', errorCode: 'network'},
            async () => {
                const context = await archiveOnOffer();
                context.api.start.mockRejectedValueOnce(noAnswer());
                await context.controller.start();
                return context;
            },
        ],
        // remove: the archive stays on offer.
        ['remove, no answer', false, {state: 'done', failure: 'remove', errorCode: 'network'}, () => removeRefused(noAnswer)],
        ['remove, an answer without a code', false, {state: 'done', failure: 'remove', errorCode: 'unexpected'}, () => removeRefused(codelessAnswer)],
        ['remove, refused: the job still runs', false, {state: 'done', failure: 'remove', errorCode: 'backup_job_running'}, () => removeRefused(() => refusal(409, 'backup_job_running'))],
        // job: the job itself failed on the server.
        ['job, out of space', false, {state: 'failed', failure: 'job', errorCode: 'backup_no_space'}, () => jobFailed('backup_no_space')],
        ['job, failed without a code', false, {state: 'failed', failure: 'job', errorCode: 'backup_failed'}, () => jobFailed(null)],
        ['job, interrupted', false, {state: 'failed', failure: 'job', errorCode: 'backup_interrupted'}, () => jobFailed('backup_interrupted')],
        // no failure at all.
        ['nothing failed: idle', false, {state: 'idle', failure: null, errorCode: null}, async () => setup()],
        [
            'nothing failed: a backup starting',
            false,
            {state: 'starting', failure: null, errorCode: null},
            async () => {
                const context = setup();
                context.api.start.mockReturnValueOnce(deferred<InstanceBackupJob>().promise);
                void context.controller.start();
                return context;
            },
        ],
        [
            'nothing failed: a backup running',
            false,
            {state: 'running', failure: null, errorCode: null},
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                await context.controller.start();
                return context;
            },
        ],
        [
            'nothing failed: the job being read',
            false,
            {state: 'loading', failure: null, errorCode: null},
            async () => {
                const context = setup({stored: JOB_ID});
                context.api.get.mockReturnValueOnce(deferred<InstanceBackupJob>().promise);
                void context.controller.resume();
                return context;
            },
        ],
        ['nothing failed: an archive on offer', false, {state: 'done', failure: null, errorCode: null}, archiveOnOffer],
        [
            'nothing failed: the archive being deleted',
            false,
            {state: 'deleting', failure: null, errorCode: null},
            async () => {
                const context = await archiveOnOffer();
                context.api.remove.mockReturnValueOnce(deferred<void>().promise);
                void context.controller.remove();
                return context;
            },
        ],
    ])('%s → canRecheck %s, and recheck() acts only then', async (_case, canRecheck, observed, arrive) => {
        const {controller, api} = await arrive();

        expect({state: controller.state, failure: controller.failure, errorCode: controller.errorCode}, 'precondition: the row reached the state it names').toEqual(observed);
        expect(controller.canRecheck).toBe(canRecheck);

        const snapshot = () => ({state: controller.state, job: controller.job, errorCode: controller.errorCode, failure: controller.failure, followedJobId: controller.followedJobId, timers: vi.getTimerCount()});
        const before = snapshot();
        const reads = api.get.mock.calls.length;
        api.get.mockReturnValueOnce(deferred<InstanceBackupJob>().promise);

        void controller.recheck();

        if (canRecheck) {
            expect(api.get.mock.calls.slice(reads), 'the recheck must read the followed job, once').toEqual([[JOB_ID]]);
            expect(controller.state).toBe('loading');
            expect(controller.errorCode).toBeNull();
        } else {
            expect(api.get.mock.calls.length, 'recheck() sent a request while canRecheck is false').toBe(reads);
            expect(snapshot(), 'recheck() changed the state while canRecheck is false').toEqual(before);
        }
    });
});

// --- the storage ----------------------------------------------------------------------------------------------------

describe('the storage', () => {
    /** The whole life of a backup: start, one read, done, delete. */
    async function wholeFlow(context: ReturnType<typeof setup>) {
        const {controller, api, onDone} = context;
        api.start.mockResolvedValueOnce(running());
        api.get.mockResolvedValueOnce(done());
        api.remove.mockResolvedValueOnce(undefined);

        await controller.start();
        expect(controller.state).toBe('running');
        expect(controller.followedJobId, 'the job is followed in memory all the same').toBe(JOB_ID);

        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(controller.state).toBe('done');
        expect(onDone).toHaveBeenCalledTimes(1);

        await controller.remove();
        expect(controller.state).toBe('idle');
        expect(controller.followedJobId).toBeNull();
    }

    it('a storage that throws on every call never breaks the flow', async () => {
        const insecure = () => new DOMException('The operation is insecure.', 'SecurityError');
        const storage = {
            getItem: vi.fn((_key: string): string | null => {
                throw insecure();
            }),
            setItem: vi.fn((_key: string, _value: string): void => {
                throw new DOMException('The quota has been exceeded.', 'QuotaExceededError');
            }),
            removeItem: vi.fn((_key: string): void => {
                throw insecure();
            }),
        };
        const context = setup({storage});
        expect(storage.getItem).toHaveBeenCalledWith(KEY);
        expect(context.controller.followedJobId).toBeNull();

        await wholeFlow(context);

        expect(storage.setItem).toHaveBeenCalled();
        expect(storage.removeItem).toHaveBeenCalled();
    });

    it('storage: null keeps the job in memory only, and leaves sessionStorage alone', async () => {
        sessionStorage.setItem(KEY, OTHER_JOB_ID);
        const context = setup({storage: null});
        expect(context.controller.followedJobId, 'storage: null must not read sessionStorage').toBeNull();

        await wholeFlow(context);

        expect(sessionStorage.getItem(KEY)).toBe(OTHER_JOB_ID);
    });

    it('without a storage option, the job goes to sessionStorage, where the next page picks it up', async () => {
        const first = setup({storage: undefined});
        first.api.start.mockResolvedValueOnce(running());
        await first.controller.start();
        expect(sessionStorage.getItem(KEY)).toBe(JOB_ID);
        first.controller.dispose();

        const reloaded = setup({storage: undefined});
        expect(reloaded.controller.followedJobId).toBe(JOB_ID);
    });

    it.each<[string, PropertyDescriptor]>([
        ['missing (no DOM, as when rendered on the server)', {value: undefined}],
        [
            'refused on access (a sandboxed frame)',
            {
                get() {
                    throw new DOMException('The operation is insecure.', 'SecurityError');
                },
            },
        ],
    ])('a sessionStorage %s: the job is followed in memory', async (_case, descriptor) => {
        const original = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage');
        Object.defineProperty(globalThis, 'sessionStorage', {configurable: true, ...descriptor});
        try {
            const {controller, api} = setup({storage: undefined});
            expect(controller.followedJobId).toBeNull();
            api.start.mockResolvedValueOnce(running());

            await controller.start();

            expect(controller.state).toBe('running');
            expect(controller.followedJobId).toBe(JOB_ID);
        } finally {
            if (original) Object.defineProperty(globalThis, 'sessionStorage', original);
            else Reflect.deleteProperty(globalThis, 'sessionStorage');
        }
    });
});

// --- backupProgress -------------------------------------------------------------------------------------------------

describe('backupProgress', () => {
    it.each<[string, number | null, InstanceBackupJob | null]>([
        ['no job', null, null],
        ['a size not known yet', null, job({done_bytes: 0, total_bytes: 0})],
        ['a size not known yet, bytes already counted', null, job({done_bytes: 512, total_bytes: 0})],
        ['nothing written yet', 0, job({done_bytes: 0, total_bytes: 1000})],
        ['a quarter written', 0.25, job({done_bytes: 250, total_bytes: 1000})],
        ['all of it', 1, job({done_bytes: 1000, total_bytes: 1000})],
        ['more than announced: clamped', 1, job({done_bytes: 1500, total_bytes: 1000})],
        ['a negative count: clamped', 0, job({done_bytes: -10, total_bytes: 1000})],
    ])('%s → %s', (_case, expected, input) => {
        expect(backupProgress(input)).toBe(expected);
    });
});

// --- the server api -------------------------------------------------------------------------------------------------

describe('without an api option', () => {
    it('starts, reads every second and deletes through the backup endpoints', async () => {
        zodios.start_instance_backup_api_v1_backup_instance_post.mockResolvedValue(running());
        zodios.get_instance_backup_job_api_v1_backup_instance_jobs__job_id__get.mockResolvedValue(done());
        zodios.delete_instance_backup_job_api_v1_backup_instance_jobs__job_id__delete.mockResolvedValue('');
        const controller = new BackupJobController({storage: null});
        controllers.push(controller);

        await controller.start();
        expect(zodios.start_instance_backup_api_v1_backup_instance_post).toHaveBeenCalledTimes(1);

        await vi.advanceTimersByTimeAsync(999);
        expect(zodios.get_instance_backup_job_api_v1_backup_instance_jobs__job_id__get, 'the default pause is one second').not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(1);
        expect(zodios.get_instance_backup_job_api_v1_backup_instance_jobs__job_id__get.mock.calls).toEqual([[{params: {job_id: JOB_ID}}]]);
        expect(controller.state).toBe('done');

        await controller.remove();
        expect(zodios.delete_instance_backup_job_api_v1_backup_instance_jobs__job_id__delete).toHaveBeenCalledWith(undefined, {params: {job_id: JOB_ID}});
        expect(controller.state).toBe('idle');
    });
});

// --- B4: the password of a secure backup ------------------------------------------------------------------------------

/*
 * B4 (brief §7): `BackupJobController.start(password?)`. With a password, the controller hands it to the request that
 * starts the backup (`startInstanceBackup(password)`), and to nothing else; without one, the request of before. What the
 * controller keeps of the job is the server's answer, as before: the password is never remembered — not in the storage
 * that keeps the job id across a reload.
 *
 * Red today: `start()` takes no argument, so the password never reaches the api. The case of `start()` alone is the
 * guard of «without a password, as today», green today. `start(password)` is reached through a cast, so the type check
 * does not wait for the new parameter.
 */

const PASSWORD = 'Correct-Horse-Battery-9';

/** `controller.start(password)`, as B4 makes it. */
const startWith = (controller: BackupJobController, password?: string): Promise<void> => (controller as unknown as {start(password?: string): Promise<void>}).start(password);

describe('B4 — start(password): the password of a secure backup goes to the request, and nowhere else', () => {
    it('start(password) hands the password to the api, once, and follows the job it answers', async () => {
        const {controller, api, storage} = setup();
        api.start.mockResolvedValueOnce(running({phase: 'preparing'}));

        await startWith(controller, PASSWORD);

        expect(api.start.mock.calls, 'the password typed, handed to the request that starts the backup').toEqual([[PASSWORD]]);
        expect(controller.state).toBe('running');
        expect(controller.followedJobId).toBe(JOB_ID);
        // The presence barrier: the storage was written (the job id); the password is in none of its writes.
        expect(storage.items.get(KEY)).toBe(JOB_ID);
        expect(
            storage.setItem.mock.calls.flat().filter((value) => String(value).includes(PASSWORD)),
            'the password was written to the storage',
        ).toEqual([]);
    });

    it('start() hands no password: the api is called with no defined argument (green today: the guard)', async () => {
        const {controller, api} = setup();
        api.start.mockResolvedValueOnce(running());

        await controller.start();

        expect(api.start).toHaveBeenCalledTimes(1);
        expect(
            (api.start.mock.calls[0] as unknown[]).filter((argument) => argument !== undefined),
            'a clear backup sends no password',
        ).toEqual([]);
    });

    it.each<[string, string | undefined, unknown]>([
        ['start(password) posts {password}', PASSWORD, {password: PASSWORD}],
        ['start() posts no body, as before', undefined, null],
    ])('without an api option: %s', async (_case, password, body) => {
        zodios.start_instance_backup_api_v1_backup_instance_post.mockResolvedValue(running());
        const controller = new BackupJobController({storage: null});
        controllers.push(controller);

        await startWith(controller, password);

        expect(zodios.start_instance_backup_api_v1_backup_instance_post).toHaveBeenCalledTimes(1);
        expect(zodios.start_instance_backup_api_v1_backup_instance_post.mock.calls[0][0], 'the body of POST /backup/instance').toStrictEqual(body);
        expect(controller.state).toBe('running');
    });
});
