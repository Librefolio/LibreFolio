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
 *     offer (`done`), `done` with that same archive still on offer and the error beside it (decision 1) — except, since
 *     B-8 (the last groups), a `backup_busy` naming a running `ui` job with nothing on offer: that job is followed, its
 *     id remembered before its first read;
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
 *     then the share written, clamped to [0, 1];
 *   - since the developer's decision of 19/10 (the last section): a `backup_busy` refusal naming a running job, whatever
 *     its origin, leaves one `console.warn` — a sentence, then `{job_id, origin, status: 'running'}` —, written once,
 *     at the refusal; no other path writes a `console.warn`.
 *
 * Every test injects a fake api and an in-memory storage, and runs on fake timers: a poll is a timer, so the clock is
 * advanced by exactly the pause the contract names, and "not before" is checked one millisecond short of it. `pollMs`
 * and `maxPollFailures` are not the defaults, so a controller that ignored them would be seen; the defaults have their
 * own cases. `$lib/api` is mocked with the three backup aliases, which only the last group (no `api` option) reaches.
 *
 * jsdom, not node: `busy` and `progress` are `$derived`, which the node environment leaves stale (see
 * `$test/runes.svelte`); `assertEffectsRun()` fails the whole file loudly if the docblock above is ever lost.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import {assertEffectsRun} from '$test/runes.svelte';
import type {InstanceBackupJob} from './backupApi';

const zodios = vi.hoisted(() => ({
    start_instance_backup_api_v1_backup_instance_post: vi.fn(),
    get_instance_backup_job_api_v1_backup_instance_jobs__job_id__get: vi.fn(),
    delete_instance_backup_job_api_v1_backup_instance_jobs__job_id__delete: vi.fn(),
}));
vi.mock('$lib/api', () => ({zodiosApi: zodios, schemas: {}}));

import {BACKUP_JOB_STORAGE_KEY, BackupJobController, backupProgress, type BackupFailure, type BackupJobApi, type BackupJobOptions, type BackupJobState} from './backupJob.svelte';
// The module's namespace as well: the last section (the B-8 review of 19/10) reads through it an export that does not
// exist yet, so that its red fails on an assertion, never on the import.
import * as backupJobModule from './backupJob.svelte';

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
        instance_key_included: false,
        sealed: false,
        sealed_recipients: [],
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

// --- B-8: a backup whose start answer was lost ----------------------------------------------------------------------

/*
 * B-8 (the B-15 + B-8 contract): when the answer of `POST /backup/instance` is lost (no answer, a timeout), the backup
 * runs on the server but the tab never learns its id, and the next start is refused `409 backup_busy`. The refusal now
 * names the running job when the caller may read it — `detail.job_id` and `detail.origin`, beside the code — and
 * `backupBusyJob` of backupApi.ts reads them. The contract under test:
 *   - nothing on offer, `start()` refused `backup_busy` naming a running job of origin `ui` (started from a Backup tab):
 *     the controller follows that job as if it had started it — `loading` while it reads the job the refusal names
 *     (that one, never a job followed before), then, the job read `running`, `running`: remembered in the storage (from
 *     before its first read: B-8 decision 3, below), read again every `pollMs`. Its end is news here: read `done`,
 *     `done` and `onDone` once with it; read `failed`, `onFailed(code, 'job', job)` once and the job forgotten, as for
 *     a job started here. The refused start itself is announced to no one: the backup asked for runs;
 *   - refused `backup_busy` naming a job of origin `cli` or `panel`, no job (the refusal of before), or an id that is
 *     not a job id: exactly as today — `failed`, `backup_busy`, failure `start`, no job,
 *     `onFailed('backup_busy', 'start', null)` once, `canRecheck` as before (only while another job is followed), the
 *     storage untouched —, and that job is never read: the command line moves its archive away at the end, and the
 *     panel's archive is the panel's.
 *
 * Where the contract was silent, the developer decided (19/10; B-8's own numbering, apart from the decisions 1 to 3 of
 * the groups above):
 *   - B-8 decision 1: with an archive on offer (`done`), a start refused `backup_busy` naming a running job — whatever
 *     its origin, `ui` included — keeps the archive on offer, `backup_busy` beside it, and the running job is not read,
 *     as decision 1 above keeps an archive on offer when a new start cannot start (the third B-8 group);
 *   - B-8 decision 2: a job of origin `ui` found already ended by its first read has its end announced, as the end of a
 *     start answered with an ended job is: «as if it had started it» (the first B-8 group);
 *   - B-8 decision 3: the id of the job the refusal names is remembered before its first read — in `followedJobId` and
 *     in the storage, in place of an id followed before —, so that when that read fails, «Check again» (`recheck()`)
 *     reads that job (the last B-8 group).
 *
 * Where it is still silent, the choice of this file, one place to change: no case awaits a start that follows a job —
 * the contract does not say whether `start()` settles before the job is read or after —, so every answer given so far
 * is let in instead (`settle()`).
 *
 * Red today: the first B-8 group and the last (B-8 decision 3). A refusal naming a `ui` job fails the start like any
 * `backup_busy` — `failed`, announced —, the job is never read, and its id never remembered. Green today, and to stay
 * so: a job of origin `cli` or `panel`, no job, an id that is not a job id (the second group), and the archive on offer
 * (the third, B-8 decision 1).
 */

/** The 409 of a start while a backup runs, raised by axios: `detail: {code: 'backup_busy', message}`, and the running job when the caller may read it. */
function busyRefusal(job: Record<string, unknown> = {}) {
    return {isAxiosError: true, message: 'Request failed with status code 409', response: {status: 409, data: {detail: {code: 'backup_busy', message: 'refused: backup_busy', ...job}}}};
}

/** Let every answer already given reach the controller; no time passes. */
const settle = () => vi.advanceTimersByTimeAsync(0);

/**
 * `console.warn`, spied around every case of the group that calls `spyOnConsoleWarn()`, and kept off the run's output.
 * The developer's decision of 19/10 (the last section of this file) has every `backup_busy` refusal naming a running
 * job leave one line there: the last section asserts it; the B-8 groups before it only keep the run quiet, and assert
 * nothing of it.
 */
let warn: MockInstance<typeof console.warn>;

function spyOnConsoleWarn(): void {
    beforeEach(() => {
        warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    });
    afterEach(() => {
        warn.mockRestore();
    });
}

describe('B-8 — start() refused backup_busy naming a running job of origin ui, nothing on offer: the job followed as if started here', () => {
    // Every refusal here names a running job: one console.warn each since 19/10 (the last section), kept quiet here.
    spyOnConsoleWarn();

    it.each<[string, () => Promise<ReturnType<typeof setup>>]>([
        ['nothing followed', async () => setup()],
        [
            'the answer of a first start lost',
            async () => {
                const context = setup();
                context.api.start.mockRejectedValueOnce(noAnswer());
                await context.controller.start();
                expect(context.onFailed.mock.calls, 'precondition: the start that got no answer was announced').toEqual([['network', 'start', null]]);
                context.onFailed.mockClear();
                return context;
            },
        ],
        ['another job followed, whose id a previous page left', async () => setup({stored: OTHER_JOB_ID})],
        [
            'this very job followed until its reads failed and the polling gave up',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                context.api.get.mockRejectedValue(noAnswer());
                await context.controller.start();
                await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);
                expect(context.controller.failure, 'precondition: the polling gave up').toBe('read');
                context.api.get.mockReset();
                context.onFailed.mockClear();
                return context;
            },
        ],
    ])('%s: loading while the job named is read; running, remembered, read every pollMs; done announced once, the refused start to no one', async (_case, arrive) => {
        const {controller, api, storage, onDone, onFailed} = await arrive();
        const read = deferred<InstanceBackupJob>();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        answerReads(api, [() => read.promise, ok(running({phase: 'files', done_bytes: 512, total_bytes: 2048})), ok(done())]);

        void controller.start();
        await settle();

        expect(api.get.mock.calls, 'the job the refusal names must be read, and no other').toEqual([[JOB_ID]]);
        expect(controller.state).toBe('loading');
        expect(controller.busy).toBe(true);

        read.resolve(running());
        await settle();

        expect(controller.state).toBe('running');
        expect(controller.busy).toBe(true);
        expect(controller.job).toEqual(running());
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY), 'a reload must find the job again').toBe(JOB_ID);
        expect(onFailed, 'the backup asked for runs: the refused start is no failure').not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(POLL_MS - 1);
        expect(api.get, 'the job was read again before pollMs').toHaveBeenCalledTimes(1);
        await vi.advanceTimersByTimeAsync(1);
        expect(api.get).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('running');
        expect(controller.progress).toBe(0.25);

        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(api.get.mock.calls, 'only the job named was read').toEqual([[JOB_ID], [JOB_ID], [JOB_ID]]);
        expect(controller.state).toBe('done');
        expect(controller.busy).toBe(false);
        expect(controller.job).toEqual(done());
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(storage.items.get(KEY), 'the archive must stay downloadable after a reload').toBe(JOB_ID);
        expect(onDone.mock.calls, 'its end is news here: once').toEqual([[done()]]);
        expect(onFailed).not.toHaveBeenCalled();
        expect(vi.getTimerCount(), 'a timer outlived the job').toBe(0);

        await vi.advanceTimersByTimeAsync(100 * POLL_MS);
        expect(api.get, 'a finished job was read again').toHaveBeenCalledTimes(3);
        expect(onDone).toHaveBeenCalledTimes(1);
    });

    it('the job named, followed running, then read failed: failed (job) with its error_code, forgotten, announced once as for a job started here', async () => {
        const {controller, api, storage, onDone, onFailed} = setup();
        const ended = failedJob('backup_no_space');
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        answerReads(api, [ok(running()), ok(ended)]);

        void controller.start();
        await settle();

        expect(api.get.mock.calls, 'the job the refusal names must be read').toEqual([[JOB_ID]]);
        expect(controller.state, 'the job named is followed').toBe('running');
        expect(storage.items.get(KEY), 'the job named is remembered').toBe(JOB_ID);

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get).toHaveBeenCalledTimes(2);
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('backup_no_space');
        expect(controller.failure).toBe('job');
        expect(controller.job).toEqual(ended);
        expect(controller.canRecheck, 'a job that failed has nothing left to tell').toBe(false);
        expect(controller.followedJobId).toBeNull();
        expect(storage.items.has(KEY), 'a failed job has no archive to pick up after a reload').toBe(false);
        expect(onFailed.mock.calls, 'its end is news here, once; the refused start never').toEqual([['backup_no_space', 'job', ended]]);
        expect(onDone).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });

    it.each<[string, InstanceBackupJob, 'onDone' | 'onFailed', unknown[]]>([
        ['done', done(), 'onDone', [done()]],
        ['failed', failedJob('backup_interrupted'), 'onFailed', ['backup_interrupted', 'job', failedJob('backup_interrupted')]],
    ])('the job named found already %s by its first read: as for a start answered with an ended job, its end announced once', async (status, ended, callback, args) => {
        const context = setup();
        context.api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        context.api.get.mockResolvedValueOnce(ended);

        void context.controller.start();
        await settle();

        expect(context.api.get.mock.calls, 'the job the refusal names must be read').toEqual([[JOB_ID]]);
        expect(context.controller.state).toBe(status);
        expect(context.controller.job).toEqual(ended);
        expect(context.storage.items.get(KEY), 'an archive on offer is remembered, a failed job is not').toBe(status === 'done' ? JOB_ID : undefined);
        expect(context[callback].mock.calls, 'its end is news here: once').toEqual([args]);
        expect(context[callback === 'onDone' ? 'onFailed' : 'onDone']).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });
});

describe('B-8 — start() refused backup_busy naming no job this tab may follow: exactly as today, and no job read', () => {
    // The refusals naming a job of origin cli or panel write one console.warn each since 19/10 (the last section), kept quiet here.
    spyOnConsoleWarn();

    it.each<[string, string, Record<string, unknown>, string | undefined, boolean]>([
        ['a running job started from the command line (origin cli)', 'nothing followed', {job_id: JOB_ID, origin: 'cli'}, undefined, false],
        ['a running job started from the command line (origin cli)', 'another job followed', {job_id: JOB_ID, origin: 'cli'}, OTHER_JOB_ID, true],
        ['a running job started from the hosting panel (origin panel)', 'nothing followed', {job_id: JOB_ID, origin: 'panel'}, undefined, false],
        ['a running job started from the hosting panel (origin panel)', 'another job followed', {job_id: JOB_ID, origin: 'panel'}, OTHER_JOB_ID, true],
        ['no job: {code, message}, the refusal of before', 'nothing followed', {}, undefined, false],
        ['no job: {code, message}, the refusal of before', 'another job followed', {}, OTHER_JOB_ID, true],
        ['a job of origin ui whose id is not 32 lowercase hex digits', 'nothing followed', {job_id: `../${JOB_ID}`, origin: 'ui'}, undefined, false],
        ['a job of origin ui whose id is not 32 lowercase hex digits', 'another job followed', {job_id: `../${JOB_ID}`, origin: 'ui'}, OTHER_JOB_ID, true],
        ['a job id without an origin', 'nothing followed', {job_id: JOB_ID}, undefined, false],
        ['a job id without an origin', 'another job followed', {job_id: JOB_ID}, OTHER_JOB_ID, true],
    ])('%s, %s: failed (start) with backup_busy and no job, announced once, canRecheck as before, the storage untouched, no job read (green today: the guard)', async (_refusal, _followed, job, stored, canRecheck) => {
        const {controller, api, storage, onDone, onFailed} = setup({stored});
        api.start.mockRejectedValueOnce(busyRefusal(job));
        // A job read would be found running, and followed: the assertions below would say so.
        api.get.mockResolvedValue(running());

        await controller.start();
        await settle();

        expect(api.get, 'a job this tab may not follow was read').not.toHaveBeenCalled();
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('backup_busy');
        expect(controller.failure).toBe('start');
        expect(controller.job).toBeNull();
        expect(controller.busy).toBe(false);
        expect(controller.followedJobId).toBe(stored ?? null);
        expect(controller.canRecheck).toBe(canRecheck);
        expect(onFailed.mock.calls).toEqual([['backup_busy', 'start', null]]);
        expect(onDone).not.toHaveBeenCalled();
        expect(storage.setItem).not.toHaveBeenCalled();
        expect(storage.removeItem).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });
});

describe('B-8 — start() from done refused backup_busy naming a running job: the archive stays on offer (B-8 decision 1, decided by the developer on 19/10)', () => {
    // Every refusal here names a running job: one console.warn each since 19/10 (the last section), kept quiet here.
    spyOnConsoleWarn();

    it.each(['ui', 'cli', 'panel'])('a running job of origin %s: done, the same archive on offer, backup_busy beside it, announced once, the running job not read (green today: pinned)', async (origin) => {
        const {controller, api, storage, onDone, onFailed} = setup();
        api.start.mockResolvedValueOnce(done());
        await controller.start();
        expect(controller.state, 'precondition: an archive is on offer').toBe('done');
        const archive = controller.job;
        onDone.mockClear();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: OTHER_JOB_ID, origin}));
        // A job read would be found running, and followed: the assertions below would say so.
        api.get.mockResolvedValue(running({job_id: OTHER_JOB_ID}));

        await controller.start();
        await settle();

        expect(api.get, 'the running job was read: with an archive on offer, the archive stays on offer and the running job is not followed (B-8 decision 1, decided by the developer on 19/10)').not.toHaveBeenCalled();
        expect(controller.state).toBe('done');
        expect(controller.job, 'the archive on offer must be the one offered before').toBe(archive);
        expect(controller.errorCode).toBe('backup_busy');
        expect(controller.failure).toBe('start');
        expect(controller.canRecheck).toBe(false);
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY), 'a reload must still find the archive').toBe(JOB_ID);
        expect(onFailed.mock.calls).toEqual([['backup_busy', 'start', null]]);
        expect(onDone).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });
});

/*
 * B-8 decision 3 (the developer, 19/10): nothing on offer, a start refused `backup_busy` naming a running job of origin
 * `ui`: the tab remembers that job's id before its first read — in `followedJobId` and in the storage, in place of an
 * id followed before —, so that when the first read fails, «Check again» (`recheck()`) reads that job. The first read
 * then fails as a read does: no usable answer (`network`, `unexpected`) → `failed`, failure `read`, no job, the job
 * named still followed and offered to recheck, announced once (the failed read; the refused start never), nothing
 * scheduled; the job found gone (404 `backup_job_not_found`) → forgotten by the rule of `#read`, as any job found gone
 * is: no new decision, only that rule meeting an id remembered first.
 *
 * Red today: the refusal fails the start like any `backup_busy` and no job is read, so each case fails at its first
 * expectation, the read of the job named. With the job named followed but its id remembered only once read `running`
 * (the first B-8 group green, this decision not applied), each case fails where it names decision 3.
 */
describe('B-8 — decision 3: the job the refusal names is remembered before its first read, so «Check again» reads it', () => {
    // Every refusal here names a running job: one console.warn each since 19/10 (the last section), kept quiet here.
    spyOnConsoleWarn();

    it.each<[string, () => Promise<ReturnType<typeof setup>>]>([
        ['nothing followed', async () => setup()],
        [
            'the answer of a first start lost',
            async () => {
                const context = setup();
                context.api.start.mockRejectedValueOnce(noAnswer());
                await context.controller.start();
                expect(context.onFailed.mock.calls, 'precondition: the start that got no answer was announced').toEqual([['network', 'start', null]]);
                context.onFailed.mockClear();
                return context;
            },
        ],
        ['another job followed, whose id a previous page left', async () => setup({stored: OTHER_JOB_ID})],
    ])('%s: while its first read is out, the job named is already followed and in the storage, in place of any id followed before; read running, it stays so', async (_case, arrive) => {
        const {controller, api, storage} = await arrive();
        const read = deferred<InstanceBackupJob>();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        answerReads(api, [() => read.promise]);

        void controller.start();
        await settle();

        expect(api.get.mock.calls, 'the job the refusal names must be read').toEqual([[JOB_ID]]);
        expect(controller.state, 'its first read is out').toBe('loading');
        expect(controller.followedJobId, 'decision 3: the job named is followed before its first read, in place of any job followed before').toBe(JOB_ID);
        expect(storage.items.get(KEY), 'decision 3: the job named is in the storage before its first read, in place of any id left there').toBe(JOB_ID);
        expect(controller.job, 'no job is drawn until the first read of the job named answers').toBeNull();
        expect(controller.errorCode, 'the refused start leaves no error on screen while the job named is read').toBeNull();
        expect(controller.failure, 'the refused start leaves no failure on screen while the job named is read').toBeNull();

        read.resolve(running());
        await settle();

        expect(controller.state).toBe('running');
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY)).toBe(JOB_ID);
    });

    it.each<[string, string, () => unknown, string | undefined]>([
        ['nothing followed', 'network', noAnswer, undefined],
        ['nothing followed', 'unexpected', codelessAnswer, undefined],
        ['another job followed, whose id a previous page left', 'network', noAnswer, OTHER_JOB_ID],
        ['another job followed, whose id a previous page left', 'unexpected', codelessAnswer, OTHER_JOB_ID],
    ])('%s, the first read of the job named fails with %s: failed (read), the job still followed, announced once; «Check again» reads that job, never the one followed before, and follows it to its end', async (_followed, code, readError, stored) => {
        const {controller, api, storage, onDone, onFailed} = setup({stored});
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        answerReads(api, [ko(readError()), ok(running({phase: 'finalizing'})), ok(done())]);

        void controller.start();
        await settle();

        expect(api.get.mock.calls, 'the job the refusal names must be read').toEqual([[JOB_ID]]);
        expect(controller.state).toBe('failed');
        expect(controller.failure, 'the read of the job named failed, not the start').toBe('read');
        expect(controller.errorCode).toBe(code);
        expect(controller.job, 'nothing of the job named was read').toBeNull();
        expect(controller.busy).toBe(false);
        expect(controller.followedJobId, 'decision 3: the job named stays followed when its first read fails').toBe(JOB_ID);
        expect(storage.items.get(KEY), 'decision 3: the job named stays in the storage, in place of any id left there').toBe(JOB_ID);
        expect(controller.canRecheck, 'only the id of the job named is known, and that is enough to read it again').toBe(true);
        expect(onFailed.mock.calls, 'the failed read announced once; the refused start never').toEqual([[code, 'read', null]]);
        expect(onDone).not.toHaveBeenCalled();
        expect(vi.getTimerCount(), 'only a job read running is read again on its own').toBe(0);

        const rechecked = controller.recheck();
        expect(controller.state).toBe('loading');
        expect(api.get.mock.calls, '«Check again» must read the job the refusal named, never the one followed before').toEqual([[JOB_ID], [JOB_ID]]);
        await rechecked;
        expect(controller.state, 'the job named, read running, is followed').toBe('running');
        expect(controller.job?.phase).toBe('finalizing');
        expect(onDone).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get.mock.calls, 'only the job named was ever read').toEqual([[JOB_ID], [JOB_ID], [JOB_ID]]);
        expect(controller.state).toBe('done');
        expect(controller.job).toEqual(done());
        expect(onDone.mock.calls, 'the job named was seen running here: its end is news, once').toEqual([[done()]]);
        expect(onFailed, 'nothing failed after the first read').toHaveBeenCalledTimes(1);
        expect(storage.items.get(KEY), 'the archive must stay downloadable after a reload').toBe(JOB_ID);
        expect(vi.getTimerCount(), 'a timer outlived the job').toBe(0);
    });

    it.each<[string, string | undefined]>([
        ['nothing followed', undefined],
        ['another job followed, whose id a previous page left', OTHER_JOB_ID],
    ])('%s, the job named found gone by its first read: remembered first, then forgotten by the rule of every read (no new decision) — failed (read) with backup_job_not_found, no recheck, announced once', async (_case, stored) => {
        const {controller, api, storage, onDone, onFailed} = setup({stored});
        const read = deferred<InstanceBackupJob>();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        answerReads(api, [() => read.promise]);

        void controller.start();
        await settle();
        expect(api.get.mock.calls, 'the job the refusal names must be read').toEqual([[JOB_ID]]);
        // The presence barrier: «forgotten», below, would also hold of an id never remembered.
        expect(storage.items.get(KEY), 'precondition, decision 3: the job named is in the storage before its first read').toBe(JOB_ID);

        // The job vanished between the refusal and the read.
        read.reject(refusal(404, 'backup_job_not_found'));
        await settle();

        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('backup_job_not_found');
        expect(controller.failure).toBe('read');
        expect(controller.job).toBeNull();
        expect(controller.busy).toBe(false);
        // No new decision: a job found gone is forgotten, whatever read finds it (`#read`); the id followed before was
        // replaced by the job named (decision 3), so nothing is left to follow.
        expect(controller.followedJobId, 'a job found gone is forgotten, and the id it replaced is not taken back').toBeNull();
        expect(storage.items.has(KEY), 'a job found gone is forgotten in the storage too').toBe(false);
        expect(controller.canRecheck, 'a job found gone has nothing left to tell').toBe(false);
        expect(onFailed.mock.calls, 'the job found gone announced once; the refused start never').toEqual([['backup_job_not_found', 'read', null]]);
        expect(onDone).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);

        await controller.recheck();
        expect(api.get, '«Check again» is not offered: no job is read, not the one followed before either').toHaveBeenCalledTimes(1);
    });
});

// --- B-8, developer 19/10: the card says only «busy», the console names the job ---------------------------------------

/*
 * The developer's decision of 19/10, relayed by the coordinator. Verbatim: «farei che a schermo compare solo
 * "occupato", in console magari più dettagli per permetterci di backuppare se serve, non è in vista ma se venisse letto
 * da un utente non sarebbe grave» (on screen only «busy»; in the console more details, to let us back up if need be;
 * out of sight, and no harm done if a user read them). The 409 stays as it is: it names the running job
 * (`detail.job_id`, `detail.origin`). The card never names it, whatever its origin, and keeps following its own `ui`
 * backup as the B-8 groups above say; the console gets the details, always. The contract under test:
 *   - every `start()` refused `backup_busy` whose refusal names a job (`backupBusyJob` not null) writes exactly one
 *     `console.warn` call, whatever the origin (`ui`, `cli`, `panel`, `pre-restore`: the server's `BackupOrigin`),
 *     whatever is on offer, the job followed or not: a non-empty string first, its wording not pinned, then exactly
 *     `{job_id, origin, status: 'running'}` — `running` by contract, the server naming a job only while its state says
 *     it runs: the line says so even when the first read of a followed job finds it ended;
 *   - once, at the refusal: the line is there while the first read of a followed job is still out, and the follow's
 *     reads and polls, a read that fails, `recheck()`, `resume()` after a reload write nothing more;
 *   - no line otherwise: a `backup_busy` naming no job, an id that is not 32 lowercase hex digits, a job id without an
 *     origin (or with an empty one); any other refusal of a start, even one carrying a job id and an origin; no answer;
 *     a start that succeeds; a read that fails while a job is followed; `resume()`; `recheck()`.
 * The state is the B-8 behaviour above, unchanged: asserted here only as far as each case needs it.
 *
 * Not pinned, the contract being silent: the wording of the sentence, any argument after the second, and a refusal
 * that arrives once the controller is disposed or reset (dropped as stale today, with no line).
 *
 * Red today: the controller writes nothing to the console, so every case of the first two groups fails at its first
 * console expectation — `console.warn` called 0 times, 1 (or 3) expected. Green today, and to stay so: the last group
 * (no line otherwise), and every expectation on the state.
 */

/** Every origin the server gives a backup (`BackupOrigin`, backend manifest.py). */
const ORIGINS = ['ui', 'cli', 'panel', 'pre-restore'];

/**
 * The one line of a start refused by a running job its refusal names (`jobId`, of `origin`): a non-empty string first,
 * its wording free, then exactly the job's details. Any argument after the second is not pinned.
 */
function expectOneLine(jobId: string, origin: string, why = 'a start refused backup_busy naming a running job must write exactly one console.warn'): void {
    expect(warn, why).toHaveBeenCalledTimes(1);
    const [sentence, details] = warn.mock.calls[0];
    expect(sentence, 'the line opens with a sentence of its own: a non-empty string').toEqual(expect.stringMatching(/\S/));
    expect(details, 'the details of the running job, exactly: its id, its origin, running').toStrictEqual({job_id: jobId, origin, status: 'running'});
}

/** A refusal of another code that carries a job id and an origin all the same (the server sends none such): only a `backup_busy` names a running job. */
function otherRefusalNaming(status: number, code: string) {
    return {isAxiosError: true, message: `Request failed with status code ${status}`, response: {status, data: {detail: {code, message: `refused: ${code}`, job_id: JOB_ID, origin: 'ui'}}}};
}

describe('B-8, developer 19/10 — start() refused backup_busy naming a running job: one console.warn with its details, whatever the origin, whatever is on offer (red today)', () => {
    spyOnConsoleWarn();

    it.each<[string, BackupJobState, string[][]]>([
        ['ui', 'running', [[JOB_ID]]],
        ['cli', 'failed', []],
        ['panel', 'failed', []],
        ['pre-restore', 'failed', []],
    ])('origin %s, nothing on offer: one line, a sentence then {job_id, origin, status: running}; the state as the B-8 groups above say (%s)', async (origin, state, reads) => {
        const {controller, api} = setup();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin}));
        // A job read would be found running, and followed: only the one of origin ui may be.
        api.get.mockResolvedValue(running());

        void controller.start();
        await settle();

        expect(api.get.mock.calls, 'only a job of origin ui is read, and followed').toEqual(reads);
        expect(controller.state).toBe(state);
        expect(controller.errorCode).toBe(origin === 'ui' ? null : 'backup_busy');
        expectOneLine(JOB_ID, origin);
    });

    it.each<[string, () => Promise<InstanceBackupJob>, BackupJobState]>([
        ['already done', ok(done()), 'done'],
        ['already failed', ok(failedJob('backup_interrupted')), 'failed'],
        ['gone from the server (404)', ko(refusal(404, 'backup_job_not_found')), 'failed'],
        ['unanswered', ko(noAnswer()), 'failed'],
    ])('origin ui, nothing on offer, the job named found %s by its first read: the line all the same, once, status running — what the refusal said', async (_case, firstRead, state) => {
        const {controller, api} = setup();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        answerReads(api, [firstRead]);

        void controller.start();
        await settle();

        expect(api.get.mock.calls, 'the job the refusal names must be read').toEqual([[JOB_ID]]);
        expect(controller.state).toBe(state);
        expectOneLine(JOB_ID, 'ui');
    });

    it.each(ORIGINS)('origin %s, an archive on offer: one line all the same; the archive stays on offer, backup_busy beside it, the running job not read', async (origin) => {
        const {controller, api} = setup();
        api.start.mockResolvedValueOnce(done());
        await controller.start();
        expect(controller.state, 'precondition: an archive is on offer').toBe('done');
        const archive = controller.job;
        api.start.mockRejectedValueOnce(busyRefusal({job_id: OTHER_JOB_ID, origin}));
        // A job read would be found running, and followed: the assertions below would say so.
        api.get.mockResolvedValue(running({job_id: OTHER_JOB_ID}));

        void controller.start();
        await settle();

        expect(api.get, 'with an archive on offer, the running job is not read').not.toHaveBeenCalled();
        expect(controller.state).toBe('done');
        expect(controller.job, 'the archive on offer must be the one offered before').toBe(archive);
        expect(controller.errorCode).toBe('backup_busy');
        expectOneLine(OTHER_JOB_ID, origin);
    });

    it('refused three times, nothing on offer — by a cli job, by that same job again, then by a panel job: one line per refused start, each naming the job its refusal names', async () => {
        const {controller, api} = setup();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'cli'})).mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'cli'}));
        api.start.mockRejectedValueOnce(busyRefusal({job_id: OTHER_JOB_ID, origin: 'panel'}));

        await controller.start();
        await controller.start();
        await controller.start();
        await settle();

        expect(api.start, 'precondition: three starts').toHaveBeenCalledTimes(3);
        expect(controller.state, 'precondition: each refused').toBe('failed');
        expect(warn, 'one line per refused start, the same running job named twice included').toHaveBeenCalledTimes(3);
        for (const [sentence] of warn.mock.calls) expect(sentence, 'each line opens with a sentence of its own').toEqual(expect.stringMatching(/\S/));
        const details = warn.mock.calls.map(([, named]) => named);
        expect(details, 'each line names the job its refusal names').toStrictEqual([
            {job_id: JOB_ID, origin: 'cli', status: 'running'},
            {job_id: JOB_ID, origin: 'cli', status: 'running'},
            {job_id: OTHER_JOB_ID, origin: 'panel', status: 'running'},
        ]);
    });
});

describe('B-8, developer 19/10 — the line is written once, at the refusal: the follow, a failed read, recheck() and resume() write nothing more (red today)', () => {
    spyOnConsoleWarn();

    it('origin ui, nothing on offer: the line is there while the first read of the job named is out; that read, two polls and the job done write nothing more', async () => {
        const {controller, api, onDone} = setup();
        const read = deferred<InstanceBackupJob>();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        answerReads(api, [() => read.promise, ok(running({phase: 'files', done_bytes: 512, total_bytes: 2048})), ok(done())]);

        void controller.start();
        await settle();

        expect(controller.state, 'precondition: the first read of the job named is out').toBe('loading');
        expectOneLine(JOB_ID, 'ui', 'written at the refusal: the line must be there while the first read of the job named is still out');

        read.resolve(running());
        await settle();
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(controller.state, 'precondition: polled once, still running').toBe('running');
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get.mock.calls, 'precondition: the first read of the job named, then two polls').toEqual([[JOB_ID], [JOB_ID], [JOB_ID]]);
        expect(controller.state, 'precondition: followed to its archive').toBe('done');
        expect(onDone, 'precondition: its end announced').toHaveBeenCalledTimes(1);
        expectOneLine(JOB_ID, 'ui', 'the follow wrote another line: the line is written once, at the refusal');
        expect(vi.getTimerCount(), 'a timer outlived the job').toBe(0);
    });

    it('origin ui, nothing on offer, its first read unanswered: that failed read writes nothing; «Check again» follows the job named to its archive and writes nothing either', async () => {
        const {controller, api} = setup();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        answerReads(api, [ko(noAnswer()), ok(running()), ok(done())]);

        void controller.start();
        await settle();

        expect(controller.failure, 'precondition: the first read of the job named failed').toBe('read');
        expect(controller.canRecheck, 'precondition: «Check again» is offered').toBe(true);
        expectOneLine(JOB_ID, 'ui');

        await controller.recheck();
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get.mock.calls, 'precondition: «Check again» read the job named, then polled it').toEqual([[JOB_ID], [JOB_ID], [JOB_ID]]);
        expect(controller.state, 'precondition: followed to its archive').toBe('done');
        expectOneLine(JOB_ID, 'ui', 'the failed read or «Check again» wrote another line: the line is written once, at the refusal');
    });

    it('origin ui, nothing on offer, the page reloaded while the job named runs: resume() on the next page follows it to its archive and writes nothing', async () => {
        const first = setup();
        first.api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        first.api.get.mockResolvedValueOnce(running());
        void first.controller.start();
        await settle();
        expect(first.controller.state, 'precondition: the job named is followed').toBe('running');
        expect(first.storage.items.get(KEY), 'precondition: the job named is remembered for the next page').toBe(JOB_ID);
        expectOneLine(JOB_ID, 'ui');
        // The page goes, and its controller with it; the next page finds the job in the storage.
        first.controller.dispose();
        const {controller, api} = setup({stored: first.storage.items.get(KEY)});
        answerReads(api, [ok(running()), ok(done())]);

        await controller.resume();
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get.mock.calls, 'precondition: the next page read the job named, then polled it').toEqual([[JOB_ID], [JOB_ID]]);
        expect(controller.state, 'precondition: followed to its archive').toBe('done');
        expectOneLine(JOB_ID, 'ui', 'resume() wrote another line: only a refused start writes one');
    });
});

describe('B-8, developer 19/10 — no line otherwise: no job named, any other failure of a start, a start that succeeds, a read that fails, resume(), recheck() (green today: the guard)', () => {
    spyOnConsoleWarn();

    it.each<[string, () => unknown, string]>([
        ['backup_busy naming no job: {code, message}, the refusal of before', () => busyRefusal(), 'backup_busy'],
        ['backup_busy naming a job whose id is not 32 lowercase hex digits (a path)', () => busyRefusal({job_id: `../${JOB_ID}`, origin: 'cli'}), 'backup_busy'],
        ['backup_busy naming a job whose id is in upper case', () => busyRefusal({job_id: JOB_ID.toUpperCase(), origin: 'ui'}), 'backup_busy'],
        ['backup_busy naming a job id without an origin', () => busyRefusal({job_id: JOB_ID}), 'backup_busy'],
        ['backup_busy naming a job id with an empty origin', () => busyRefusal({job_id: JOB_ID, origin: ''}), 'backup_busy'],
        ['backup_busy naming an origin without a job id', () => busyRefusal({origin: 'cli'}), 'backup_busy'],
        ['backup_no_space (507) carrying a job id and an origin: only backup_busy names a running job', () => otherRefusalNaming(507, 'backup_no_space'), 'backup_no_space'],
        ['backup_no_space (507)', () => refusal(507, 'backup_no_space'), 'backup_no_space'],
        ['backup_folder_unusable (500)', () => refusal(500, 'backup_folder_unusable'), 'backup_folder_unusable'],
        ['backup_failed (500)', () => refusal(500, 'backup_failed'), 'backup_failed'],
        ['no answer', noAnswer, 'network'],
        ['an answer without a code', codelessAnswer, 'unexpected'],
    ])('a start refused — %s: no line, with nothing on offer nor with an archive on offer', async (_case, refused, code) => {
        const {controller, api} = setup();
        api.start.mockRejectedValueOnce(refused()).mockResolvedValueOnce(done());
        api.start.mockRejectedValueOnce(refused());

        await controller.start();
        expect(controller.state, 'precondition: refused, nothing on offer').toBe('failed');
        await controller.start();
        expect(controller.state, 'precondition: an archive on offer').toBe('done');
        await controller.start();
        await settle();

        expect(controller.state, 'precondition: refused, the archive still on offer').toBe('done');
        expect(controller.errorCode, 'precondition: refused').toBe(code);
        expect(api.get, 'no job was read').not.toHaveBeenCalled();
        expect(warn, 'only a backup_busy naming a running job writes a line').not.toHaveBeenCalled();
    });

    it.each<[string, Array<() => Promise<InstanceBackupJob>>, BackupJobState, string | null]>([
        ['read running, then done', [ok(running()), ok(done())], 'done', null],
        ['unanswered until the polling gives up', [ko(noAnswer()), ko(noAnswer()), ko(noAnswer())], 'failed', 'network'],
        ['found gone from the server (404)', [ko(refusal(404, 'backup_job_not_found'))], 'failed', 'backup_job_not_found'],
        ['read failed on the server', [ok(failedJob('backup_no_space'))], 'failed', 'backup_no_space'],
    ])('a start that succeeds, its job %s: no line', async (_case, reads, state, code) => {
        const {controller, api} = setup();
        api.start.mockResolvedValueOnce(running());
        answerReads(api, reads);

        await controller.start();
        await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);

        expect(controller.state, 'precondition: the job reached its end, or the polling gave up').toBe(state);
        expect(controller.errorCode).toBe(code);
        expect(warn, 'a start that succeeds, and a read that fails, write no line').not.toHaveBeenCalled();
    });

    it.each<[string, Array<() => Promise<InstanceBackupJob>>, BackupJobState]>([
        ['running, then done', [ok(running()), ok(done())], 'done'],
        ['unanswered', [ko(noAnswer())], 'failed'],
        ['gone from the server (404)', [ko(refusal(404, 'backup_job_not_found'))], 'idle'],
    ])('resume() of the job a previous page followed, read %s: no line', async (_case, reads, state) => {
        const {controller, api} = setup({stored: JOB_ID});
        answerReads(api, reads);

        await controller.resume();
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(controller.state, 'precondition: the job picked up as the server has it').toBe(state);
        expect(warn, 'resume() writes no line').not.toHaveBeenCalled();
    });

    it('the polling gave up on a job started here, and «Check again» follows it to its archive: no line', async () => {
        const {controller, api} = setup();
        api.start.mockResolvedValueOnce(running());
        answerReads(api, [ko(noAnswer()), ko(noAnswer()), ko(noAnswer()), ok(running()), ok(done())]);
        await controller.start();
        await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);
        expect(controller.canRecheck, 'precondition: the polling gave up, «Check again» is offered').toBe(true);

        await controller.recheck();
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get, 'precondition: three failed reads, then «Check again» and one poll').toHaveBeenCalledTimes(5);
        expect(controller.state, 'precondition: followed to its archive').toBe('done');
        expect(warn, 'a failed read and «Check again» write no line').not.toHaveBeenCalled();
    });
});

// --- B-8, defect of the review (19/10): a secure request never follows; a clear one never presents a secure end -----

/*
 * The defect, found by the automatic review before B-15 + B-8 went in, relayed by the coordinator: `start(password)` — a
 * SECURE request — refused `409 backup_busy` naming a running job of origin `ui`, nothing on offer, follows that job
 * whatever its mode (the first B-8 group above; no B-8 case started with a password). The job may be another tab's, or
 * another administrator's, and clear: the card then offers «Archive ready» for a clear .zip after the user asked for a
 * secure one — the privacy notice is drawn in clear mode only —, and `onDone` fires `backup.created` as if it were the
 * user's backup. Conversely, a CLEAR request may end up offering an .lfbk sealed with someone else's password. The
 * client cannot tell before the end: the server sets `encrypted` on a job only when it ends (jobs.py), so a running job
 * always reads `encrypted: false`; and a job records no user, so whose backup a 409 names is unknown.
 *
 * The decision (the coordinator, 19/10 17:37), verbatim: «confermo la tabella di destra. Con una password, dal 409
 * nessun seguito; in chiaro, il controllo alla fine (`encrypted: true`, quindi non presentato, id dimenticato,
 * `backup_busy`)» (the right-hand table confirmed: with a password, no follow from the 409; in clear, the check at the
 * end — `encrypted: true`, so not presented, the id forgotten, `backup_busy`). The contract under test, the 409 naming a
 * running job of origin `ui`, nothing on offer:
 *   - a secure request (`start(password)`), whatever the job: not followed — no read, `failed`, `backup_busy`, failure
 *     `start`, no job, `onFailed('backup_busy', 'start', null)` once, `onDone` never, the storage untouched (no
 *     `setItem`, no `removeItem`), `followedJobId` as before (and `canRecheck` with it, as for the other origins),
 *     nothing scheduled; the console line as today: one;
 *   - a clear request (`start()`): followed as today, and the adoption remembered under `BACKUP_ADOPTED_STORAGE_KEY =
 *     'librefolio.backup.adopted'` (exported; its value the job id) from the moment the job is followed, next to
 *     `BACKUP_JOB_STORAGE_KEY`. Its end: `done` with `encrypted: false` → offered, `onDone` once, as today; `done` with
 *     `encrypted: true` → NOT presented: `failed`, `backup_busy`, failure `start`, no job, `followedJobId` null, both
 *     keys removed, `onDone` never, `onFailed('backup_busy', 'start', null)` once when the end is news (the usual rule:
 *     seen running here, or read here after the refusal), `canRecheck` false, nothing scheduled — whether the polling
 *     finds it, the first read, or «Check again» after a first read with no answer; `failed` (job) or gone (404) → as
 *     today, and the adoption key removed too;
 *   - after a reload, `resume()` applies the same check to the job a previous page adopted (both keys left): read
 *     running, then polled to `encrypted: true` → not presented, announced once; read ended with `encrypted: true`
 *     already → not presented, both keys removed, never announced (`resume()` never announces); `encrypted: false` →
 *     offered, as today;
 *   - housekeeping: a start that succeeds removes an adoption left over; a secure backup started here that ends
 *     `encrypted: true` is offered, as today; an adoption key naming another id than the job followed is dropped at
 *     construction, and has no effect; a path that adopts nothing writes and removes no adoption key, so the guards
 *     above that find the storage untouched still hold;
 *   - with an archive on offer, any request: as today — the offer stays, `backup_busy` beside it, nothing adopted.
 *
 * `BACKUP_ADOPTED_STORAGE_KEY` is not exported today: the storage is read through the literal (`ADOPTED_KEY`), and the
 * export is checked on the module's namespace (`backupJobModule`), so that every red fails on its assertion, never on
 * the import.
 *
 * Not pinned, the contract being silent: the adoption key once a clear end is offered (kept, or removed); a reload whose
 * `resume()` gets no answer, then «Check again» finds the adopted job sealed (not presented, but announced or not?). A
 * clear request whose 409 names the job this tab already follows by itself (a secure one started here, say) has since
 * been pinned by «B-8, review 19/10, refinement»: followed as its own, never adopted, its sealed end offered.
 *
 * Red today: a secure request follows the job named — its read is where each of those cases fails first —; a clear
 * request never writes the adoption key, and offers a sealed end (`done`, `onDone`); `resume()` offers a sealed end too,
 * and never removes an adoption key; a start that succeeds leaves the adoption key where it was; an adoption of another
 * job is not dropped; the export is missing. Green today, and to stay so: the guards — the archive on offer kept, the
 * clear end offered, an ordinary secure backup offered, a stale adoption without effect, a path that adopts nothing.
 */

/** The key of an adoption — a job followed from a 409 for a clear request —, as the decided contract names it (`BACKUP_ADOPTED_STORAGE_KEY`): written out, the export being missing today. */
const ADOPTED_KEY = 'librefolio.backup.adopted';

/** A job done whose archive is sealed (`encrypted: true`, an .lfbk): the end of a secure backup, perhaps with a password this tab never knew. */
const sealed = (overrides: Partial<Job> = {}) => done({encrypted: true, file_name: 'librefolio-backup-20261015-120000.lfbk', ...overrides});

/** What a case reads of the controller once a job has ended. */
interface Outcome {
    state: BackupJobState;
    errorCode: string | null;
    failure: BackupFailure | null;
    job: InstanceBackupJob | null;
}

const outcome = (controller: BackupJobController): Outcome => ({state: controller.state, errorCode: controller.errorCode, failure: controller.failure, job: controller.job});

/** A controller over an in-memory storage that holds `initial`: the page after a reload, the keys as the page before left them. */
function setupWith(initial: Record<string, string>) {
    const storage = memoryStorage(initial);
    return {...setup({storage}), storage};
}

/** Every write and every removal of the adoption key the storage received. */
const adoptionCalls = (storage: ReturnType<typeof memoryStorage>) => [...storage.setItem.mock.calls, ...storage.removeItem.mock.calls].filter(([key]) => key === ADOPTED_KEY);

/**
 * A clear start refused `backup_busy` by the running job `JOB_ID` of origin ui, nothing on offer: the job adopted, its
 * first read held out (the deferred returned); the reads after it answer `after`, in turn.
 */
async function adoptedFirstReadOut(context: ReturnType<typeof setup>, after: Array<() => Promise<InstanceBackupJob>> = []): Promise<Deferred<InstanceBackupJob>> {
    const first = deferred<InstanceBackupJob>();
    context.api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
    answerReads(context.api, [() => first.promise, ...after]);

    void context.controller.start();
    await settle();

    expect(context.api.start.mock.lastCall, 'precondition: a clear request, no password').toEqual([]);
    expect(context.api.get.mock.calls, 'precondition: the job the refusal names is read').toEqual([[JOB_ID]]);
    expect(context.controller.state, 'precondition: its first read is out').toBe('loading');
    return first;
}

describe('B-8, review 19/10 — start(password) refused backup_busy naming a running job of origin ui: never followed (red today); an archive on offer stays on offer, whatever the request (green today)', () => {
    // Every refusal here names a running job: one console.warn each, asserted where the contract names it.
    spyOnConsoleWarn();

    it.each<[string, () => Promise<ReturnType<typeof setup>>, string | null, boolean]>([
        ['nothing followed', async () => setup(), null, false],
        [
            'the answer of a first secure start lost: the very case of B-8, with a password',
            async () => {
                const context = setup();
                context.api.start.mockRejectedValueOnce(noAnswer());
                await context.controller.start(PASSWORD);
                expect(context.onFailed.mock.calls, 'precondition: the secure start that got no answer was announced').toEqual([['network', 'start', null]]);
                context.onFailed.mockClear();
                return context;
            },
            null,
            false,
        ],
        ['another job followed, whose id a previous page left', async () => setup({stored: OTHER_JOB_ID}), OTHER_JOB_ID, true],
        [
            'the job named itself, a secure backup started here and followed until its reads failed and the polling gave up',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                context.api.get.mockRejectedValue(noAnswer());
                await context.controller.start(PASSWORD);
                await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);
                expect(context.controller.failure, 'precondition: the polling gave up').toBe('read');
                context.api.get.mockReset();
                context.onFailed.mockClear();
                return context;
            },
            JOB_ID,
            true,
        ],
    ])('%s: not followed — no read; failed (start) with backup_busy and no job, announced once; the storage untouched, the job followed before still followed; nothing scheduled; one console line (red today)', async (_case, arrive, followedBefore, canRecheck) => {
        const {controller, api, storage, onDone, onFailed} = await arrive();
        const kept = storage.items.get(KEY);
        storage.setItem.mockClear();
        storage.removeItem.mockClear();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        // A job read would be found running, and followed: the assertions below would say so.
        api.get.mockResolvedValue(running());

        void controller.start(PASSWORD);
        await settle();

        expect(api.start.mock.lastCall, 'precondition: a secure request, its password sent').toEqual([PASSWORD]);
        expect(api.get, 'a secure request followed the job the 409 names: nothing proves it is the backup asked for').not.toHaveBeenCalled();
        expect(controller.state).toBe('failed');
        expect(controller.errorCode).toBe('backup_busy');
        expect(controller.failure).toBe('start');
        expect(controller.job).toBeNull();
        expect(controller.busy).toBe(false);
        expect(controller.followedJobId, 'the job followed before, as before').toBe(followedBefore);
        expect(controller.canRecheck, 'as for the other origins: only while a job is still followed').toBe(canRecheck);
        expect(onFailed.mock.calls, 'the refused start, announced once').toEqual([['backup_busy', 'start', null]]);
        expect(onDone).not.toHaveBeenCalled();
        expect(storage.setItem, 'the storage untouched: nothing of the job named is remembered, nothing adopted').not.toHaveBeenCalled();
        expect(storage.removeItem, 'the storage untouched').not.toHaveBeenCalled();
        expect(storage.items.get(KEY), 'the storage as it was').toBe(kept);
        expect(vi.getTimerCount(), 'nothing scheduled').toBe(0);
        expectOneLine(JOB_ID, 'ui', "the console line as today: one per refusal naming a job, the secure request's included");
    });

    it.each<[string, string | undefined]>([
        ['clear', undefined],
        ['secure', PASSWORD],
    ])('an archive on offer, a %s request refused naming a running job of origin ui: done, the same archive on offer, backup_busy beside it, the running job not read, nothing adopted (green today: the guard)', async (_request, password) => {
        const {controller, api, storage, onDone, onFailed} = setup();
        api.start.mockResolvedValueOnce(done());
        await controller.start();
        expect(controller.state, 'precondition: an archive is on offer').toBe('done');
        const archive = controller.job;
        onDone.mockClear();
        storage.setItem.mockClear();
        storage.removeItem.mockClear();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: OTHER_JOB_ID, origin: 'ui'}));
        // A job read would be found running, and followed: the assertions below would say so.
        api.get.mockResolvedValue(running({job_id: OTHER_JOB_ID}));

        void controller.start(password);
        await settle();

        expect(api.start.mock.lastCall, 'precondition: the request asked for').toEqual(password === undefined ? [] : [password]);
        expect(api.get, 'with an archive on offer, the running job is not read').not.toHaveBeenCalled();
        expect(controller.state).toBe('done');
        expect(controller.job, 'the archive on offer must be the one offered before').toBe(archive);
        expect(controller.errorCode).toBe('backup_busy');
        expect(controller.failure).toBe('start');
        expect(controller.canRecheck).toBe(false);
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY), 'a reload must still find the archive').toBe(JOB_ID);
        expect(storage.setItem, 'nothing of the running job remembered, nothing adopted').not.toHaveBeenCalled();
        expect(storage.removeItem).not.toHaveBeenCalled();
        expect(onFailed.mock.calls).toEqual([['backup_busy', 'start', null]]);
        expect(onDone).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });
});

describe('B-8, review 19/10 — start() refused backup_busy naming a running job of origin ui, nothing on offer: followed as today, the adoption remembered under BACKUP_ADOPTED_STORAGE_KEY from the moment it is followed (red today)', () => {
    // Every refusal here names a running job: one console.warn each since 19/10, kept quiet here.
    spyOnConsoleWarn();

    it('BACKUP_ADOPTED_STORAGE_KEY is exported beside BACKUP_JOB_STORAGE_KEY, and is librefolio.backup.adopted (red today)', () => {
        expect(Reflect.get(backupJobModule, 'BACKUP_JOB_STORAGE_KEY'), 'precondition: the namespace of backupJob.svelte.ts is read').toBe(KEY);
        expect(Reflect.get(backupJobModule, 'BACKUP_ADOPTED_STORAGE_KEY'), 'the key of an adoption, exported by backupJob.svelte.ts').toBe(ADOPTED_KEY);
    });

    it.each<[string, () => ReturnType<typeof setup>]>([
        ['nothing followed', () => setup()],
        ['another job followed, whose id a previous page left', () => setup({stored: OTHER_JOB_ID})],
        ['another job adopted, whose two keys a previous page left', () => setupWith({[KEY]: OTHER_JOB_ID, [ADOPTED_KEY]: OTHER_JOB_ID})],
    ])('%s: the job named adopted — its id under the adoption key before its first read, next to the job key, and while it runs; a clear end offered and announced once, as today (red today)', async (_case, arrive) => {
        const context = arrive();
        const {controller, api, storage, onDone, onFailed} = context;
        const first = await adoptedFirstReadOut(context, [ok(done())]);

        expect(storage.items.get(KEY), 'precondition, B-8 decision 3: the job named is in the storage before its first read').toBe(JOB_ID);
        expect(storage.items.get(ADOPTED_KEY), 'the adoption remembered from the moment the job is followed: before its first read, next to the job key, in place of any adoption left there').toBe(JOB_ID);

        first.resolve(running());
        await settle();

        expect(controller.state).toBe('running');
        expect(storage.items.get(ADOPTED_KEY), 'still adopted while it runs').toBe(JOB_ID);

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get.mock.calls, 'only the job named was read').toEqual([[JOB_ID], [JOB_ID]]);
        expect(controller.state, 'a clear end: offered, as today').toBe('done');
        expect(controller.job).toEqual(done());
        expect(controller.errorCode).toBeNull();
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY), 'the archive must stay downloadable after a reload').toBe(JOB_ID);
        expect(onDone.mock.calls, 'its end is news here: once').toEqual([[done()]]);
        expect(onFailed).not.toHaveBeenCalled();
        expect(vi.getTimerCount(), 'a timer outlived the job').toBe(0);
    });
});

describe('B-8, review 19/10 — the end of an adopted job: done with encrypted: true, not presented (red today); failed or gone, as today, the adoption key removed too (red today)', () => {
    // Every refusal here names a running job: one console.warn each, asserted where the contract names it.
    spyOnConsoleWarn();

    it.each<[string, Array<() => Promise<InstanceBackupJob>>, (first: Deferred<InstanceBackupJob>, controller: BackupJobController) => Promise<void>, unknown[][]]>([
        [
            'the polling finds it: read running, then done with encrypted: true',
            [ok(sealed())],
            async (first, controller) => {
                first.resolve(running());
                await settle();
                expect(controller.state, 'precondition: followed while it runs, as today (a running job reads encrypted: false)').toBe('running');
                await vi.advanceTimersByTimeAsync(POLL_MS);
            },
            [['backup_busy', 'start', null]],
        ],
        [
            'its first read finds it done with encrypted: true already',
            [],
            async (first) => {
                first.resolve(sealed());
                await settle();
            },
            [['backup_busy', 'start', null]],
        ],
        [
            'its first read gets no answer, then «Check again» finds it done with encrypted: true',
            [ok(sealed())],
            async (first, controller) => {
                first.reject(noAnswer());
                await settle();
                expect(controller.failure, 'precondition: its first read failed').toBe('read');
                expect(controller.canRecheck, 'precondition: «Check again» is offered').toBe(true);
                await controller.recheck();
            },
            [
                ['network', 'read', null],
                ['backup_busy', 'start', null],
            ],
        ],
    ])('a clear request, the job adopted — %s: not presented; failed (start) with backup_busy and no job, forgotten (both keys), onDone never, onFailed(backup_busy, start, null) once, no recheck, nothing scheduled (red today)', async (_path, after, reachEnd, announced) => {
        const context = setup();
        const {controller, api, storage, onDone, onFailed} = context;
        const first = await adoptedFirstReadOut(context, after);
        // The presence barrier of «both keys removed», below: taken while the job is followed, asserted once its end is
        // checked, so that the red names the end first.
        const whileFollowed = {job: storage.items.get(KEY), adopted: storage.items.get(ADOPTED_KEY)};

        await reachEnd(first, controller);

        expect(controller.state, 'a sealed archive offered to a clear request: another tab or another administrator may have asked for it, with a password this tab never knew').toBe('failed');
        expect(controller.errorCode).toBe('backup_busy');
        expect(controller.failure).toBe('start');
        expect(controller.job, 'not presented: no job drawn').toBeNull();
        expect(controller.busy).toBe(false);
        expect(onDone, 'not presented: no archive announced').not.toHaveBeenCalled();
        expect(onFailed.mock.calls, 'its end is news here: backup_busy, once').toEqual(announced);
        expect(controller.followedJobId, 'the id forgotten').toBeNull();
        expect(controller.canRecheck, 'forgotten: nothing left to check again').toBe(false);
        expect(vi.getTimerCount(), 'nothing scheduled').toBe(0);
        expect(whileFollowed, 'precondition, the presence barrier of the two expectations below: both keys named the job while it was followed').toEqual({job: JOB_ID, adopted: JOB_ID});
        expect(storage.items.has(KEY), 'forgotten: the job key removed').toBe(false);
        expect(storage.items.has(ADOPTED_KEY), 'forgotten: the adoption key removed').toBe(false);

        const reads = api.get.mock.calls.length;
        await controller.recheck();
        await vi.advanceTimersByTimeAsync(100 * POLL_MS);

        expect(api.get, 'a forgotten job was read again').toHaveBeenCalledTimes(reads);
        expect(onFailed.mock.calls, 'announced once, and once only').toEqual(announced);
        expectOneLine(JOB_ID, 'ui', 'the check at the end wrote a line: one per refusal, and only there');
    });

    it.each<[string, Array<() => Promise<InstanceBackupJob>>, (first: Deferred<InstanceBackupJob>) => Promise<void>, Outcome, unknown[][]]>([
        [
            'the polling finds it failed on the server',
            [ok(failedJob('backup_no_space'))],
            async (first) => {
                first.resolve(running());
                await settle();
                await vi.advanceTimersByTimeAsync(POLL_MS);
            },
            {state: 'failed', errorCode: 'backup_no_space', failure: 'job', job: failedJob('backup_no_space')},
            [['backup_no_space', 'job', failedJob('backup_no_space')]],
        ],
        [
            'its first read finds it failed already',
            [],
            async (first) => {
                first.resolve(failedJob('backup_interrupted'));
                await settle();
            },
            {state: 'failed', errorCode: 'backup_interrupted', failure: 'job', job: failedJob('backup_interrupted')},
            [['backup_interrupted', 'job', failedJob('backup_interrupted')]],
        ],
        [
            'its first read finds it gone (404)',
            [],
            async (first) => {
                first.reject(refusal(404, 'backup_job_not_found'));
                await settle();
            },
            {state: 'failed', errorCode: 'backup_job_not_found', failure: 'read', job: null},
            [['backup_job_not_found', 'read', null]],
        ],
        [
            'the polling finds it gone (404)',
            [ko(refusal(404, 'backup_job_not_found'))],
            async (first) => {
                first.resolve(running());
                await settle();
                await vi.advanceTimersByTimeAsync(POLL_MS);
            },
            {state: 'failed', errorCode: 'backup_job_not_found', failure: 'read', job: null},
            [['backup_job_not_found', 'read', null]],
        ],
    ])('a clear request, the job adopted — %s: as today, and the adoption key removed with the job key (red today)', async (_path, after, reachEnd, expected, announced) => {
        const context = setup();
        const {controller, storage, onDone, onFailed} = context;
        const first = await adoptedFirstReadOut(context, after);
        // The presence barrier of «the adoption key removed», below: taken while the job is followed, asserted after
        // what today already does.
        const whileFollowed = {job: storage.items.get(KEY), adopted: storage.items.get(ADOPTED_KEY)};

        await reachEnd(first);

        expect(outcome(controller), 'as today').toEqual(expected);
        expect(controller.followedJobId, 'as today: forgotten').toBeNull();
        expect(controller.canRecheck, 'as today: nothing left to tell').toBe(false);
        expect(onFailed.mock.calls, 'as today: its end is news here, once').toEqual(announced);
        expect(onDone).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
        expect(storage.items.has(KEY), 'as today: the job key removed').toBe(false);
        expect(whileFollowed, 'precondition, the presence barrier of the expectation below: both keys named the job while it was followed').toEqual({job: JOB_ID, adopted: JOB_ID});
        expect(storage.items.has(ADOPTED_KEY), 'the adoption key removed with the job key').toBe(false);
    });
});

describe('B-8, review 19/10 — after a reload: resume() applies the same check to the job a previous page adopted', () => {
    // The page that adopts the job in the last case is refused by a running job: one console.warn, kept quiet here.
    spyOnConsoleWarn();

    /** The page after a reload: the job `JOB_ID` followed and adopted by the page before, both keys left; its reads answer `reads`, in turn. */
    function reloadedAfterAdoption(reads: Array<() => Promise<InstanceBackupJob>>) {
        const context = setupWith({[KEY]: JOB_ID, [ADOPTED_KEY]: JOB_ID});
        expect(context.controller.followedJobId, 'precondition: the job the previous page followed').toBe(JOB_ID);
        expect(context.storage.items.get(ADOPTED_KEY), 'precondition: its adoption, which names it, kept at construction').toBe(JOB_ID);
        answerReads(context.api, [...reads]);
        return context;
    }

    it.each<[string, Array<() => Promise<InstanceBackupJob>>, unknown[][]]>([
        ['read running, then polled to done with encrypted: true — seen running here, so announced once', [ok(running()), ok(sealed())], [['backup_busy', 'start', null]]],
        ['read done with encrypted: true already — never announced: resume() never announces', [ok(sealed())], []],
    ])('a job the previous page adopted (both keys left), %s: not presented — failed (start) with backup_busy and no job, forgotten (both keys), onDone never, no recheck, nothing scheduled (red today)', async (_case, reads, announced) => {
        const {controller, api, storage, onDone, onFailed} = reloadedAfterAdoption(reads);

        await controller.resume();
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get.mock.calls.flat(), 'precondition: the job read, then polled while it ran').toEqual(reads.map(() => JOB_ID));
        expect(controller.state, 'the sealed end of a job the page before adopted, offered after a reload').toBe('failed');
        expect(controller.errorCode).toBe('backup_busy');
        expect(controller.failure).toBe('start');
        expect(controller.job, 'not presented').toBeNull();
        expect(controller.followedJobId, 'the id forgotten').toBeNull();
        expect(controller.canRecheck).toBe(false);
        expect(onDone, 'not presented: no archive announced').not.toHaveBeenCalled();
        expect(onFailed.mock.calls).toEqual(announced);
        expect(vi.getTimerCount()).toBe(0);
        expect(storage.items.has(KEY), 'forgotten: the job key removed').toBe(false);
        expect(storage.items.has(ADOPTED_KEY), 'forgotten: the adoption key removed').toBe(false);
    });

    it.each<[string, Array<() => Promise<InstanceBackupJob>>, Outcome]>([
        ['read failed on the server', [ok(failedJob('backup_interrupted'))], {state: 'failed', errorCode: 'backup_interrupted', failure: 'job', job: failedJob('backup_interrupted')}],
        ['found gone (404)', [ko(refusal(404, 'backup_job_not_found'))], {state: 'idle', errorCode: null, failure: null, job: null}],
    ])('a job the previous page adopted (both keys left), %s: as today, silently, and the adoption key removed with the job key (red today)', async (_case, reads, expected) => {
        const {controller, storage, onDone, onFailed} = reloadedAfterAdoption(reads);

        await controller.resume();

        expect(outcome(controller), 'as today').toEqual(expected);
        expect(controller.followedJobId, 'as today: forgotten').toBeNull();
        expect(onDone).not.toHaveBeenCalled();
        expect(onFailed, 'resume() never announces').not.toHaveBeenCalled();
        expect(storage.items.has(KEY), 'as today: the job key removed').toBe(false);
        expect(storage.items.has(ADOPTED_KEY), 'the adoption key removed with the job key').toBe(false);
    });

    it.each<[string, Array<() => Promise<InstanceBackupJob>>, unknown[][]]>([
        ['read done with encrypted: false already — silently', [ok(done())], []],
        ['read running, then polled to done with encrypted: false — seen running here, so announced once', [ok(running()), ok(done())], [[done()]]],
    ])('a job the previous page adopted (both keys left), %s: offered, as today (green today: the guard)', async (_case, reads, announced) => {
        const {controller, storage, onDone, onFailed} = reloadedAfterAdoption(reads);

        await controller.resume();
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(outcome(controller)).toEqual({state: 'done', errorCode: null, failure: null, job: done()});
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY), 'the archive must stay downloadable after a reload').toBe(JOB_ID);
        expect(onDone.mock.calls).toEqual(announced);
        expect(onFailed).not.toHaveBeenCalled();
        expect(vi.getTimerCount()).toBe(0);
    });

    it('the whole reload: the page that adopted the job goes while it runs; on the next page resume() follows it to done with encrypted: true — not presented, forgotten, announced once (red today)', async () => {
        const first = setup();
        first.api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        first.api.get.mockResolvedValueOnce(running());
        void first.controller.start();
        await settle();
        expect(first.controller.state, 'precondition: the job named is followed').toBe('running');
        expect(first.storage.items.get(KEY), 'precondition: the job named is remembered for the next page').toBe(JOB_ID);
        // The page goes, and its controller with it; the next page finds the storage as this one left it.
        first.controller.dispose();
        const left = Object.fromEntries(first.storage.items);
        const {controller, api, storage, onDone, onFailed} = setupWith(left);
        answerReads(api, [ok(running()), ok(sealed())]);

        await controller.resume();
        expect(controller.state, 'precondition: picked up running').toBe('running');
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get.mock.calls, 'precondition: the next page read the job, then polled it').toEqual([[JOB_ID], [JOB_ID]]);
        expect(controller.state, 'the next page offered the sealed end of a job the page before adopted').toBe('failed');
        expect(controller.errorCode).toBe('backup_busy');
        expect(controller.failure).toBe('start');
        expect(controller.job).toBeNull();
        expect(controller.followedJobId).toBeNull();
        expect(onDone).not.toHaveBeenCalled();
        expect(onFailed.mock.calls, 'seen running on this page: its end is news, once').toEqual([['backup_busy', 'start', null]]);
        expect(vi.getTimerCount()).toBe(0);
        // The presence barrier of the last expectation, asserted after the end so that the red names the end first.
        expect(left, 'precondition: the page before left both keys').toEqual({[KEY]: JOB_ID, [ADOPTED_KEY]: JOB_ID});
        expect(storage.items.size, 'forgotten: neither key is left').toBe(0);
    });
});

describe('B-8, review 19/10 — housekeeping: a start that succeeds ends an adoption left over; a secure backup started here is offered; an adoption of another job is dropped at construction; no other path touches the adoption key', () => {
    // No refusal here names a job: the spy only keeps a stray line off the run's output.
    spyOnConsoleWarn();

    it.each<[string, string | undefined, InstanceBackupJob]>([
        ['clear', undefined, done({job_id: OTHER_JOB_ID})],
        ['secure', PASSWORD, sealed({job_id: OTHER_JOB_ID})],
    ])('a %s start that succeeds removes the adoption a previous page left; the job started here, polled to its end, is offered and announced once (red today)', async (_request, password, end) => {
        const {controller, api, storage, onDone, onFailed} = setupWith({[KEY]: JOB_ID, [ADOPTED_KEY]: JOB_ID});
        expect(storage.items.get(ADOPTED_KEY), 'precondition: the adoption a previous page left, which names the job followed, kept at construction').toBe(JOB_ID);
        api.start.mockResolvedValueOnce(running({job_id: OTHER_JOB_ID}));
        answerReads(api, [ok(end)]);

        await controller.start(password);

        expect(api.start.mock.lastCall, 'precondition: the request asked for').toEqual(password === undefined ? [] : [password]);
        expect(controller.state, 'precondition: the job started here runs').toBe('running');
        expect(storage.items.get(KEY), 'the job started here is the one followed now').toBe(OTHER_JOB_ID);
        expect(storage.items.has(ADOPTED_KEY), 'a start that succeeds removes the adoption left over: the job followed now was started here').toBe(false);

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get.mock.calls, 'only the job started here was read').toEqual([[OTHER_JOB_ID]]);
        expect(controller.state, 'a job started here: offered, whatever its mode').toBe('done');
        expect(controller.job).toEqual(end);
        expect(onDone.mock.calls).toEqual([[end]]);
        expect(onFailed).not.toHaveBeenCalled();
        expect(storage.items.get(KEY)).toBe(OTHER_JOB_ID);
    });

    it.each<[string, () => Promise<ReturnType<typeof setup>>]>([
        [
            'polled to its end',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                answerReads(context.api, [ok(sealed())]);
                await context.controller.start(PASSWORD);
                await vi.advanceTimersByTimeAsync(POLL_MS);
                return context;
            },
        ],
        [
            'its start answered with the archive already sealed',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(sealed());
                await context.controller.start(PASSWORD);
                return context;
            },
        ],
        [
            'its reads failed until the polling gave up, then «Check again» finds it ended',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                answerReads(context.api, [ko(noAnswer()), ko(noAnswer()), ko(noAnswer()), ok(sealed())]);
                await context.controller.start(PASSWORD);
                await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);
                expect(context.controller.canRecheck, 'precondition: the polling gave up, «Check again» is offered').toBe(true);
                context.onFailed.mockClear();
                await context.controller.recheck();
                return context;
            },
        ],
        [
            'the page reloaded while it ran, picked up running by resume()',
            async () => {
                const context = setup({stored: JOB_ID});
                answerReads(context.api, [ok(running()), ok(sealed())]);
                await context.controller.resume();
                await vi.advanceTimersByTimeAsync(POLL_MS);
                return context;
            },
        ],
    ])('a secure backup started here — %s — ends done with encrypted: true: offered and announced once, as today; the check at the end is for an adopted job only (green today: the guard)', async (_case, reachEnd) => {
        const {controller, storage, onDone, onFailed} = await reachEnd();

        expect(controller.state).toBe('done');
        expect(controller.job).toEqual(sealed());
        expect(controller.errorCode).toBeNull();
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY), 'the archive must stay downloadable after a reload').toBe(JOB_ID);
        expect(onDone.mock.calls, 'its end is news here: once').toEqual([[sealed()]]);
        expect(onFailed).not.toHaveBeenCalled();
        expect(adoptionCalls(storage), 'nothing adopted: no call names the adoption key').toEqual([]);
        expect(vi.getTimerCount()).toBe(0);
    });

    it.each<[string, Record<string, string>, string | null]>([
        ['naming another job than the one followed', {[KEY]: JOB_ID, [ADOPTED_KEY]: OTHER_JOB_ID}, JOB_ID],
        ['naming a job, with no job followed', {[ADOPTED_KEY]: JOB_ID}, null],
        ['that is not a job id', {[KEY]: JOB_ID, [ADOPTED_KEY]: 'not-a-backup-job-id-at-all-00000'}, JOB_ID],
    ])('an adoption key %s is dropped at construction: removed, and nothing else touched (red today)', (_case, initial, followed) => {
        const {controller, storage} = setupWith(initial);

        expect(controller.followedJobId, 'precondition: the job followed, as the job key says').toBe(followed);
        expect(storage.removeItem.mock.calls, 'an adoption that does not name the job followed is dropped at construction, and only it').toEqual([[ADOPTED_KEY]]);
        expect(storage.items.has(ADOPTED_KEY)).toBe(false);
        expect(storage.items.get(KEY), 'the job key as it was').toBe(initial[KEY]);
        expect(storage.setItem).not.toHaveBeenCalled();
    });

    it('an adoption of another job has no effect: the job followed, picked up running by resume(), ends done with encrypted: true — offered and announced once, as a job this tab followed (green today: the guard)', async () => {
        const {controller, api, storage, onDone, onFailed} = setupWith({[KEY]: JOB_ID, [ADOPTED_KEY]: OTHER_JOB_ID});
        answerReads(api, [ok(running()), ok(sealed())]);

        await controller.resume();
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get.mock.calls, 'only the job followed is read').toEqual([[JOB_ID], [JOB_ID]]);
        expect(controller.state, 'an adoption of another job turned the check at the end on for this one').toBe('done');
        expect(controller.job).toEqual(sealed());
        expect(onDone.mock.calls).toEqual([[sealed()]]);
        expect(onFailed).not.toHaveBeenCalled();
        expect(storage.items.get(KEY)).toBe(JOB_ID);
    });

    it.each<[string, Record<string, string>]>([
        ['an adoption key naming the job followed', {[KEY]: JOB_ID, [ADOPTED_KEY]: JOB_ID}],
        ['a job followed, no adoption key', {[KEY]: JOB_ID}],
        ['nothing stored', {}],
    ])('at construction, %s: nothing written, nothing removed (green today: the guard)', (_case, initial) => {
        const {storage} = setupWith(initial);

        expect(storage.setItem).not.toHaveBeenCalled();
        expect(storage.removeItem).not.toHaveBeenCalled();
        expect(Object.fromEntries(storage.items), 'the storage as the previous page left it').toEqual(initial);
    });

    it.each<[string, () => Promise<ReturnType<typeof setup>>]>([
        [
            'a clear start that succeeds, its job polled to its archive, the archive deleted',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                answerReads(context.api, [ok(done())]);
                context.api.remove.mockResolvedValueOnce(undefined);
                await context.controller.start();
                await vi.advanceTimersByTimeAsync(POLL_MS);
                await context.controller.remove();
                expect(context.controller.state, 'precondition: the archive deleted').toBe('idle');
                return context;
            },
        ],
        [
            'a secure start that succeeds, its job read failed on the server',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                answerReads(context.api, [ok(failedJob('backup_no_space'))]);
                await context.controller.start(PASSWORD);
                await vi.advanceTimersByTimeAsync(POLL_MS);
                expect(context.controller.failure, 'precondition: the job failed').toBe('job');
                return context;
            },
        ],
        [
            'a start that succeeds, its job found gone (404)',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                answerReads(context.api, [ko(refusal(404, 'backup_job_not_found'))]);
                await context.controller.start();
                await vi.advanceTimersByTimeAsync(POLL_MS);
                expect(context.controller.errorCode, 'precondition: the job found gone').toBe('backup_job_not_found');
                return context;
            },
        ],
        [
            'a job a previous page followed, picked up by resume(), then reset()',
            async () => {
                const context = setup({stored: JOB_ID});
                answerReads(context.api, [ok(done())]);
                await context.controller.resume();
                context.controller.reset();
                expect(context.controller.state, 'precondition: reset').toBe('idle');
                return context;
            },
        ],
    ])('%s: the job key forgotten, the adoption key never written nor removed (green today: the guard)', async (_case, arrive) => {
        const {storage} = await arrive();

        expect(storage.removeItem.mock.calls, 'precondition: the job key was removed').toContainEqual([KEY]);
        expect(adoptionCalls(storage), 'a path that adopts nothing wrote or removed the adoption key').toEqual([]);
    });
});

// --- B-8, review 19/10, refinement: a tab's own backup is never adopted ---------------------------------------------

/*
 * The coordinator's refinement of the review's decision (19/10 18:10), verbatim: «sì alla rifinitura, decisione mia,
 * perché è nello spirito della tabella («si segue solo il proprio»): non adottare un job che la scheda sta già seguendo
 * da sé» (yes to the refinement, my decision, as it is in the spirit of the table — «one follows only one's own»: do
 * not adopt a job the tab is already following by itself). The contract under test, a clear start (`start()`), nothing
 * on offer, refused `409 backup_busy` naming a running job of origin `ui`:
 *   - the job this tab already follows by itself — `followedJobId` is its id, and no adoption key names it: a secure
 *     backup started here whose polling gave up, or the job a previous page of this tab followed (the job key only),
 *     its read by `resume()` unanswered — is followed as its own: never adopted, no adoption key written or removed,
 *     its end offered whatever its mode. Sealed (`done`, `encrypted: true`): `done`, the archive on offer, `onDone`
 *     once (its end is news: the refusal makes it watched again), the job key kept, no `onFailed` after the refusal;
 *   - the guards, as the review decided: a job that is not the one followed is adopted (the second and third review
 *     groups pin it), and so is the job this tab follows as an adoption (both keys left by a previous page): their
 *     sealed end is not presented.
 * The secure path does not change: a secure start never follows, its own job included — «Check again» stays the way
 * back (the first review group). The planned cure, not applied yet: adopt only when the job named is not the one
 * followed, or when the one followed is already an adoption.
 *
 * Red today: a clear start adopts every running `ui` job its 409 names, this tab's own included — the adoption key is
 * written at the refusal, where both red cases fail first —, so the sealed end is not presented: `failed`,
 * `backup_busy`, failure `start`, no job, both keys removed, `onDone` never, `onFailed('backup_busy', 'start', null)`.
 * Green today, and to stay so: the two guards.
 */
describe('B-8, review 19/10, refinement — a clear start refused by the job this tab already follows by itself: followed as its own, never adopted, its end offered whatever its mode (red today)', () => {
    // Every refusal here names a running job: one console.warn each since 19/10, kept quiet here.
    spyOnConsoleWarn();

    it.each<[string, () => Promise<ReturnType<typeof setup>>]>([
        [
            'a secure backup started here, its polling given up',
            async () => {
                const context = setup();
                context.api.start.mockResolvedValueOnce(running());
                context.api.get.mockRejectedValue(noAnswer());
                await context.controller.start(PASSWORD);
                await vi.advanceTimersByTimeAsync((1 + 2 + 3) * POLL_MS);
                expect(context.api.start.mock.lastCall, 'precondition: a secure backup, its password sent').toEqual([PASSWORD]);
                expect(context.api.get, 'precondition: its reads unanswered until maxPollFailures').toHaveBeenCalledTimes(MAX_FAILURES);
                context.api.get.mockReset();
                context.onFailed.mockClear();
                return context;
            },
        ],
        [
            'the job a previous page of this tab followed (the job key only), its read by resume() unanswered',
            async () => {
                const context = setup({stored: JOB_ID});
                context.api.get.mockRejectedValueOnce(noAnswer());
                await context.controller.resume();
                expect(context.api.get.mock.calls, 'precondition: resume() read the job the previous page left').toEqual([[JOB_ID]]);
                context.api.get.mockReset();
                return context;
            },
        ],
    ])('%s: a clear start refused naming that very job follows it as its own — never adopted, no adoption key at any point; its end, done with encrypted: true, offered: the sealed archive on offer, onDone once, the job key kept, no onFailed (red today)', async (_case, arrive) => {
        const {controller, api, storage, onDone, onFailed} = await arrive();
        expect(controller.state, 'precondition: nothing on offer, its reads unanswered').toBe('failed');
        expect(controller.failure, 'precondition: what failed is a read of the job').toBe('read');
        expect(controller.followedJobId, 'precondition: this tab follows the job by itself').toBe(JOB_ID);
        expect(storage.items.get(KEY), 'precondition: the job key names it').toBe(JOB_ID);
        expect(storage.items.has(ADOPTED_KEY), 'precondition: no adoption key names it').toBe(false);
        const first = deferred<InstanceBackupJob>();
        api.start.mockRejectedValueOnce(busyRefusal({job_id: JOB_ID, origin: 'ui'}));
        answerReads(api, [() => first.promise, ok(sealed())]);

        void controller.start();
        await settle();

        expect(api.start.mock.lastCall, 'precondition: a clear request, no password').toEqual([]);
        expect(api.get.mock.calls, 'the job the refusal names must be read').toEqual([[JOB_ID]]);
        expect(controller.state, 'its first read is out').toBe('loading');
        expect(storage.items.has(ADOPTED_KEY), 'the job this tab already follows by itself was adopted at the refusal: it is followed as its own, never adopted').toBe(false);
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY)).toBe(JOB_ID);

        first.resolve(running());
        await settle();

        expect(controller.state, 'followed while it runs').toBe('running');
        expect(storage.items.has(ADOPTED_KEY), 'adopted while it runs').toBe(false);

        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(api.get.mock.calls, 'only the job named was read').toEqual([[JOB_ID], [JOB_ID]]);
        expect(controller.state, "the sealed end of this tab's own backup was not offered: followed as its own, its end is offered whatever its mode").toBe('done');
        expect(controller.busy).toBe(false);
        expect(controller.job, 'the sealed archive on offer').toEqual(sealed());
        expect(controller.errorCode).toBeNull();
        expect(controller.failure).toBeNull();
        expect(controller.followedJobId).toBe(JOB_ID);
        expect(storage.items.get(KEY), 'the archive must stay downloadable after a reload: the job key kept').toBe(JOB_ID);
        expect(onDone.mock.calls, 'its end is news here (the refusal makes it watched again): once').toEqual([[sealed()]]);
        expect(onFailed, 'nothing failed after the refusal').not.toHaveBeenCalled();
        expect(storage.items.has(ADOPTED_KEY), 'an adoption key left at the end').toBe(false);
        expect(adoptionCalls(storage), 'the adoption key was written or removed: the job this tab follows by itself is never adopted, and a path that adopts nothing touches no adoption key').toEqual([]);
        expect(vi.getTimerCount(), 'a timer outlived the job').toBe(0);
    });

    it.each<[string, () => Promise<ReturnType<typeof setup>>]>([
        ['a job that is not the one followed (another job followed, whose id a previous page left)', async () => setup({stored: OTHER_JOB_ID})],
        [
            'the job this tab follows as an adoption (both keys left by a previous page), its read by resume() unanswered',
            async () => {
                const context = setupWith({[KEY]: JOB_ID, [ADOPTED_KEY]: JOB_ID});
                context.api.get.mockRejectedValueOnce(noAnswer());
                await context.controller.resume();
                expect(context.controller.failure, 'precondition: its read by resume() unanswered').toBe('read');
                expect(context.storage.items.get(ADOPTED_KEY), 'precondition: followed as an adoption, kept at construction').toBe(JOB_ID);
                context.api.get.mockReset();
                return context;
            },
        ],
    ])('a clear start refused naming %s: adopted, and its end, done with encrypted: true, not presented — as the review decided (green today: the guard)', async (_case, arrive) => {
        const context = await arrive();
        const first = await adoptedFirstReadOut(context, [ok(sealed())]);

        expect(context.storage.items.get(ADOPTED_KEY), 'adopted: the job named is not one this tab follows by itself').toBe(JOB_ID);

        first.resolve(running());
        await settle();
        await vi.advanceTimersByTimeAsync(POLL_MS);

        expect(outcome(context.controller), 'its sealed end not presented, as the review decided').toEqual({state: 'failed', errorCode: 'backup_busy', failure: 'start', job: null});
    });
});
