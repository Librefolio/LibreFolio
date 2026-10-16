/**
 * backupApi — the instance backup endpoints, and the two readers of a refused request.
 *
 * The contract under test:
 *   - `backupErrorCode(error)`: the string `detail.code` an AxiosError's response carries, else `null` — no
 *     response, a `detail` that is a string (FastAPI's default) or a list (a 422), an object without a code, an
 *     empty or non-string code, a body that is not JSON (a proxy page), or an error axios did not raise, even one
 *     shaped like a refusal;
 *   - `backupFailureCode(error)`: that code, whatever the status (a 500 can carry one: `backup_folder_unusable`);
 *     `network` for an AxiosError that got no answer; `unexpected` for everything else;
 *   - `instanceBackupFileUrl(id)`: the same-origin path of the archive, the id one encoded path segment;
 *   - the three requests call their `zodiosApi` alias with the arguments Zodios expects, hand back what it answers,
 *     and let its refusal through untouched — the controller reads the code off it.
 *
 * `$lib/api` is mocked with the backup aliases (B5a's three, B5b's eight) and nothing else, so a wrapper reaching for
 * any other alias fails on a missing function instead of passing. That mock proves which alias is called with which
 * arguments; it cannot prove that those arguments make the right request. The replay groups do: they replay the exact
 * arguments each wrapper passed on the generated client, over an axios adapter that records the request and answers
 * without a network, and assert the method and the path — and that the hand-written file URL is the path of the
 * generated download route.
 *
 * Errors are AxiosError-shaped literals (`isAxiosError: true` is what axios itself tests); a few cases build a real
 * `AxiosError`, so the literals are known to read the same as what axios throws.
 *
 * The restore requests of B5b (`b5b-contract.md` §1), written red first — the functions do not exist yet, so each of
 * those cases fails on its own and names the missing export, and the type check does not wait for them:
 *   - the eight requests call their alias with the arguments Zodios expects, hand back what it answers, and let a
 *     refusal through untouched;
 *   - the upload sends the File itself as the raw body, hands the AbortSignal on, and maps axios's `onUploadProgress` to
 *     `onProgress(loaded, total)`; replayed on the generated client, its request is `PUT /api/v1/backup/restore/upload`
 *     with the File as its data and `Content-Type: application/octet-stream`;
 *   - `probeServer()` and `restoreOutcome()` go through a plain `fetch` on this origin — `credentials: 'same-origin'`,
 *     `cache: 'no-store'` — and never through Zodios, whose 401 interceptor would navigate to the login: `/system/ready`
 *     200 is `up`, any other status or no answer `down`; the status 401 is `signed_out`, 200 is `status` with the body
 *     parsed, any other status, a body that is not JSON, or no answer, `down`. `fetch` is a stub there, and `schemas`
 *     holds the generated ones, should `restoreOutcome()` parse the status with them;
 *   - an instance its hosting provider blocked (`LIBREFOLIO_BLOCKED`) refuses every restore route, the status's
 *     included, with `423 {detail: {code: 'instance_blocked', message}}`, while `/system/ready` still answers 200: so
 *     `restoreOutcome()` reads that refusal as `blocked` — still one request, the same — and the restart page can say
 *     why the restore was not applied (P8, written red first). Anything else a 423 may carry (another code, a detail
 *     without one, the code outside `detail`, a null body, no body, a page that is not JSON) stays `down`, and so does
 *     the code on any other status, a 200 included.
 *
 * Node environment: nothing here touches the DOM or a rune.
 */
import axios, {AxiosError, AxiosHeaders, type AxiosAdapter, type AxiosProgressEvent, type InternalAxiosRequestConfig} from 'axios';
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import type {z} from 'zod';
import type {schemas} from '$lib/api';

const zodios = vi.hoisted(() => ({
    start_instance_backup_api_v1_backup_instance_post: vi.fn(),
    get_instance_backup_job_api_v1_backup_instance_jobs__job_id__get: vi.fn(),
    delete_instance_backup_job_api_v1_backup_instance_jobs__job_id__delete: vi.fn(),
    get_restore_status_api_v1_backup_restore_status_get: vi.fn(),
    upload_restore_archive_api_v1_backup_restore_upload_put: vi.fn(),
    start_restore_check_api_v1_backup_restore_stage_post: vi.fn(),
    get_restore_check_api_v1_backup_restore_stage__stage_id__get: vi.fn(),
    delete_restore_check_api_v1_backup_restore_stage__stage_id__delete: vi.fn(),
    confirm_restore_check_api_v1_backup_restore_stage__stage_id__confirm_post: vi.fn(),
    cancel_pending_restore_api_v1_backup_restore_pending_delete: vi.fn(),
    restart_for_restore_api_v1_backup_restore_restart_post: vi.fn(),
}));
/** The generated zod schemas, filled in by the group that may need them (the status `restoreOutcome()` reads). */
const generatedSchemas = vi.hoisted((): Record<string, unknown> => ({}));
vi.mock('$lib/api', () => ({zodiosApi: zodios, schemas: generatedSchemas}));

import {backupErrorCode, backupFailureCode, deleteInstanceBackupJob, getInstanceBackupJob, instanceBackupFileUrl, startInstanceBackup, type InstanceBackupJob} from './backupApi';
import * as backupApiModule from './backupApi';

type Alias = keyof typeof zodios;

const START: Alias = 'start_instance_backup_api_v1_backup_instance_post';
const GET: Alias = 'get_instance_backup_job_api_v1_backup_instance_jobs__job_id__get';
const DELETE: Alias = 'delete_instance_backup_job_api_v1_backup_instance_jobs__job_id__delete';

const JOB_ID = '0123456789abcdef0123456789abcdef';

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

/** A request the server answered with an error status: axios rejects with the response, FastAPI's body in `data`. */
function answered(status: number, data: unknown) {
    return {isAxiosError: true, name: 'AxiosError', message: `Request failed with status code ${status}`, response: {status, data}};
}

/** A refusal as the backup routes word it: `detail: {code, message}`. */
function refusal(status: number, code: string) {
    return answered(status, {detail: {code, message: `refused: ${code}`}});
}

/** A request that got no answer — down, unreachable, timed out: axios rejects with no `response`. */
function noAnswer(code = 'ERR_NETWORK') {
    return {isAxiosError: true, name: 'AxiosError', message: 'Network Error', code, response: undefined};
}

/** The same two, raised by axios itself. */
function realAxiosError(status: number | null, data?: unknown): AxiosError {
    const config = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;
    if (status === null) return new AxiosError('Network Error', AxiosError.ERR_NETWORK, config, {});
    const response = {status, statusText: '', headers: new AxiosHeaders(), config, data};
    return new AxiosError(`Request failed with status code ${status}`, AxiosError.ERR_BAD_RESPONSE, config, {}, response);
}

describe('backupErrorCode', () => {
    it.each<[string, string | null, unknown]>([
        ['a 409 refusal: its code', 'backup_busy', refusal(409, 'backup_busy')],
        ['a 404 refusal: its code', 'backup_job_not_found', refusal(404, 'backup_job_not_found')],
        ['a 500 refusal with a code: its code, whatever the status', 'backup_folder_unusable', refusal(500, 'backup_folder_unusable')],
        ['a refusal raised by axios itself: its code', 'backup_busy', realAxiosError(409, {detail: {code: 'backup_busy', message: 'refused'}})],
        ['a detail without a code', null, answered(409, {detail: {message: 'refused'}})],
        ["a detail that is a string (FastAPI's default)", null, answered(404, {detail: 'Not Found'})],
        ['a detail that is a list (a 422)', null, answered(422, {detail: [{loc: ['path', 'job_id'], msg: 'invalid', type: 'value_error'}]})],
        ['an empty code', null, refusal(409, '')],
        ['a code that is not a string', null, answered(409, {detail: {code: 409}})],
        ['a null detail', null, answered(500, {detail: null})],
        ['a body that is not JSON (a proxy page)', null, answered(502, '<html><body>Bad Gateway</body></html>')],
        ['a null body', null, answered(500, null)],
        ['no body at all', null, answered(500, undefined)],
        ['no answer (network)', null, noAnswer()],
        ['no answer, raised by axios itself', null, realAxiosError(null)],
        ['a plain Error', null, new Error('boom')],
        ['an object shaped like a refusal that axios did not raise', null, {response: {status: 409, data: {detail: {code: 'backup_busy'}}}}],
        ['null', null, null],
        ['undefined', null, undefined],
        ['a bare string', null, 'backup_busy'],
    ])('%s → %s', (_case, expected, error) => {
        expect(backupErrorCode(error)).toBe(expected);
    });
});

describe('backupFailureCode', () => {
    it.each<[string, string, unknown]>([
        ['a refusal with a code: the code', 'backup_busy', refusal(409, 'backup_busy')],
        ['a 500 with backup_folder_unusable: the code, not unexpected', 'backup_folder_unusable', refusal(500, 'backup_folder_unusable')],
        ['a 500 with backup_failed: the code', 'backup_failed', refusal(500, 'backup_failed')],
        ['a 404 with backup_job_not_found: the code', 'backup_job_not_found', refusal(404, 'backup_job_not_found')],
        ['no answer', 'network', noAnswer()],
        ['a timeout', 'network', noAnswer('ECONNABORTED')],
        ['no answer, raised by axios itself', 'network', realAxiosError(null)],
        ['an answer without a code', 'unexpected', answered(500, {detail: 'Internal Server Error'})],
        ['an answer with an empty code', 'unexpected', refusal(500, '')],
        ['a proxy page', 'unexpected', answered(502, '<html><body>Bad Gateway</body></html>')],
        ['an answer without a code, raised by axios itself', 'unexpected', realAxiosError(500, {detail: 'Internal Server Error'})],
        ['a plain Error', 'unexpected', new Error('boom')],
        ['a TypeError of the page itself', 'unexpected', new TypeError("Cannot read properties of undefined (reading 'status')")],
        ['an object without a response that axios did not raise', 'unexpected', {message: 'Network Error'}],
        ['null', 'unexpected', null],
    ])('%s → %s', (_case, expected, error) => {
        expect(backupFailureCode(error)).toBe(expected);
    });
});

describe('instanceBackupFileUrl', () => {
    it('is the same-origin path of the job archive', () => {
        expect(instanceBackupFileUrl(JOB_ID)).toBe(`/api/v1/backup/instance/jobs/${JOB_ID}/file`);
    });

    it.each([
        ['a slash', 'a/b', 'a%2Fb'],
        ['a query and a fragment', 'id?download=1#top', 'id%3Fdownload%3D1%23top'],
        ['a percent sign and a space', '50% done', '50%25%20done'],
        ['a backslash', 'a\\b', 'a%5Cb'],
        ['a letter outside ASCII', 'è', '%C3%A8'],
    ])('encodes %s, so the id stays one path segment of the same origin', (_case, id, encoded) => {
        const url = instanceBackupFileUrl(id);
        expect(url).toBe(`/api/v1/backup/instance/jobs/${encoded}/file`);

        const parsed = new URL(url, 'https://librefolio.example');
        expect(parsed.origin, 'the link left the page origin: the session cookie would not go with it').toBe('https://librefolio.example');
        expect(parsed.search, 'the id opened a query string').toBe('');
        expect(parsed.hash, 'the id opened a fragment').toBe('');
        const segments = parsed.pathname.split('/');
        expect(segments, 'the id split into more than one path segment').toHaveLength(8);
        expect(decodeURIComponent(segments[6])).toBe(id);
        expect(segments[7]).toBe('file');
    });
});

describe('the three requests', () => {
    beforeEach(() => {
        for (const fn of Object.values(zodios)) fn.mockReset();
    });

    /** The aliases the call under test must leave alone. */
    function untouchedBesides(alias: Alias) {
        return (Object.keys(zodios) as Alias[]).filter((other) => other !== alias).filter((other) => zodios[other].mock.calls.length > 0);
    }

    it('startInstanceBackup posts with no body and no parameter, and returns the job the server answers', async () => {
        const answer = job();
        zodios[START].mockResolvedValue(answer);

        await expect(startInstanceBackup()).resolves.toBe(answer);

        expect(zodios[START]).toHaveBeenCalledTimes(1);
        const [body, config] = zodios[START].mock.calls[0];
        expect(body, 'a backup is started with an empty body').toBeUndefined();
        expect(config).toBeUndefined();
        expect(untouchedBesides(START)).toEqual([]);
    });

    it('getInstanceBackupJob reads the job by its id, as a path parameter, and returns it', async () => {
        const answer = job({status: 'done'});
        zodios[GET].mockResolvedValue(answer);

        await expect(getInstanceBackupJob(JOB_ID)).resolves.toBe(answer);

        expect(zodios[GET].mock.calls).toEqual([[{params: {job_id: JOB_ID}}]]);
        expect(untouchedBesides(GET)).toEqual([]);
    });

    it('deleteInstanceBackupJob deletes the job by its id, with no body, and resolves to nothing', async () => {
        // An empty 204 comes back from Zodios as an empty string: the wrapper answers void whatever it is.
        zodios[DELETE].mockResolvedValue('');

        await expect(deleteInstanceBackupJob(JOB_ID)).resolves.toBeUndefined();

        expect(zodios[DELETE]).toHaveBeenCalledTimes(1);
        const [body, config] = zodios[DELETE].mock.calls[0];
        expect(body).toBeUndefined();
        expect(config, 'the id must travel as the path parameter, the second argument of a Zodios delete').toEqual({params: {job_id: JOB_ID}});
        expect(untouchedBesides(DELETE)).toEqual([]);
    });

    it.each<[string, Alias, () => Promise<unknown>]>([
        ['startInstanceBackup', START, () => startInstanceBackup()],
        ['getInstanceBackupJob', GET, () => getInstanceBackupJob(JOB_ID)],
        ['deleteInstanceBackupJob', DELETE, () => deleteInstanceBackupJob(JOB_ID)],
    ])('%s lets a refusal through untouched, so its code can still be read', async (_name, alias, call) => {
        const refused = refusal(409, 'backup_busy');
        zodios[alias].mockRejectedValue(refused);

        await expect(call()).rejects.toBe(refused);
    });
});

describe('the same arguments, replayed on the generated client', () => {
    type Replayable = Record<string, (...args: unknown[]) => Promise<unknown>>;
    interface Recorded {
        method: string | undefined;
        url: string | undefined;
    }

    let createApiClient: typeof import('$lib/api/generated').createApiClient;

    beforeAll(async () => {
        // Loaded here rather than at the top: the generated client is large, and only this group needs it.
        ({createApiClient} = await import('$lib/api/generated'));
    });

    beforeEach(() => {
        for (const fn of Object.values(zodios)) fn.mockReset();
    });

    /** The generated client over an adapter that records each request and answers it at once, with no network. */
    function recordingClient(answer: unknown): {client: Replayable; requests: Recorded[]} {
        const requests: Recorded[] = [];
        const adapter: AxiosAdapter = async (config) => {
            requests.push({method: config.method, url: config.url});
            return {data: answer, status: 200, statusText: 'OK', headers: new AxiosHeaders(), config, request: {}};
        };
        const client = createApiClient('/', {axiosInstance: axios.create({adapter}), validate: false});
        return {client: client as unknown as Replayable, requests};
    }

    it.each<[string, string, string, Alias, () => Promise<unknown>]>([
        ['startInstanceBackup', 'post', '/api/v1/backup/instance', START, () => startInstanceBackup()],
        ['getInstanceBackupJob', 'get', `/api/v1/backup/instance/jobs/${JOB_ID}`, GET, () => getInstanceBackupJob(JOB_ID)],
        ['deleteInstanceBackupJob', 'delete', `/api/v1/backup/instance/jobs/${JOB_ID}`, DELETE, () => deleteInstanceBackupJob(JOB_ID)],
    ])('%s: its arguments make the request %s %s', async (_name, method, url, alias, call) => {
        zodios[alias].mockResolvedValue(job());
        await call();
        expect(zodios[alias]).toHaveBeenCalledTimes(1);
        const passed = zodios[alias].mock.calls[0];

        const {client, requests} = recordingClient(job());
        expect(typeof client[alias], `the generated client has no ${alias}: the route was renamed or removed`).toBe('function');
        await client[alias](...passed);

        expect(requests).toEqual([{method, url}]);
    });

    it('instanceBackupFileUrl is the path of the generated download route', async () => {
        const download = 'download_instance_backup_api_v1_backup_instance_jobs__job_id__file_get';
        const {client, requests} = recordingClient('');
        expect(typeof client[download], `the generated client has no ${download}`).toBe('function');

        await client[download]({params: {job_id: JOB_ID}});

        expect(requests).toEqual([{method: 'get', url: instanceBackupFileUrl(JOB_ID)}]);
    });
});

// =====================================================================================================================
// B5b — the restore requests (b5b-contract.md §1), written red first
// =====================================================================================================================

type RestoreStatus = z.infer<typeof schemas.RestoreStatus>;
type RestoreStage = z.infer<typeof schemas.RestoreStage>;
type RestoreUpload = z.infer<typeof schemas.RestoreUpload>;
type UploadOptions = {onProgress?: (loaded: number, total: number) => void; signal?: AbortSignal};
type RestoreOutcomeAnswer = {kind: 'signed_out'} | {kind: 'status'; status: RestoreStatus} | {kind: 'blocked'} | {kind: 'down'};

interface RestoreRequests {
    getRestoreStatus: () => Promise<RestoreStatus>;
    uploadRestoreArchive: (file: File, options?: UploadOptions) => Promise<RestoreUpload>;
    startRestoreCheck: (uploadId: string) => Promise<RestoreStage>;
    getRestoreCheck: (stageId: string) => Promise<RestoreStage>;
    deleteRestoreCheck: (stageId: string) => Promise<void>;
    confirmRestore: (stageId: string) => Promise<RestoreStatus>;
    cancelPendingRestore: () => Promise<void>;
    requestRestart: () => Promise<RestoreStatus>;
    probeServer: () => Promise<'up' | 'down'>;
    restoreOutcome: () => Promise<RestoreOutcomeAnswer>;
}

/** One restore function of backupApi.ts, or a failure that names it: each case fails on its own until it exists. */
function restore<K extends keyof RestoreRequests>(name: K): RestoreRequests[K] {
    const fn = (backupApiModule as unknown as Partial<RestoreRequests>)[name];
    expect(typeof fn, `backupApi.ts exports no ${name}() (B5b contract §1)`).toBe('function');
    return fn as RestoreRequests[K];
}

const STATUS: Alias = 'get_restore_status_api_v1_backup_restore_status_get';
const UPLOAD: Alias = 'upload_restore_archive_api_v1_backup_restore_upload_put';
const STAGE: Alias = 'start_restore_check_api_v1_backup_restore_stage_post';
const CHECK: Alias = 'get_restore_check_api_v1_backup_restore_stage__stage_id__get';
const DROP: Alias = 'delete_restore_check_api_v1_backup_restore_stage__stage_id__delete';
const CONFIRM: Alias = 'confirm_restore_check_api_v1_backup_restore_stage__stage_id__confirm_post';
const CANCEL: Alias = 'cancel_pending_restore_api_v1_backup_restore_pending_delete';
const RESTART: Alias = 'restart_for_restore_api_v1_backup_restore_restart_post';

const UPLOAD_ID = '0123456789abcdef0123456789abcdef';
const STAGE_ID = 'fedcba9876543210fedcba9876543210';

function restoreStatus(overrides: Partial<RestoreStatus> = {}): RestoreStatus {
    return {state: 'none', stage_id: null, confirmed_at: null, confirmed_by: null, backup_created_at: null, backup_app_version: null, action: null, finished_at: null, reason: null, waiting: null, upload_limit_mb: 500, ...overrides};
}

const runningStage = (): RestoreStage => ({stage_id: STAGE_ID, status: 'running', phase: 'checking', done_bytes: 0, total_bytes: 0, created_at: '2026-10-16T09:00:00Z', finished_at: null, error_code: null, report: null});

const archive = () => new File(['PK\u0003\u0004'], 'librefolio-backup-20261015-120000.zip', {type: 'application/zip'});

/** The arguments a mocked alias received; the arguments Zodios leaves out are `undefined`. */
const argumentsOf = (alias: Alias): unknown[] => zodios[alias].mock.calls[0] ?? [];

describe('the restore requests (B5b §1)', () => {
    beforeEach(() => {
        for (const fn of Object.values(zodios)) fn.mockReset();
    });

    /** The aliases called besides the one under test. */
    function touchedBesides(alias: Alias) {
        return (Object.keys(zodios) as Alias[]).filter((other) => other !== alias && zodios[other].mock.calls.length > 0);
    }

    it('getRestoreStatus reads the status with no parameter, and returns it', async () => {
        const answer = restoreStatus();
        zodios[STATUS].mockResolvedValue(answer);

        await expect(restore('getRestoreStatus')()).resolves.toBe(answer);

        expect(zodios[STATUS]).toHaveBeenCalledTimes(1);
        const given = argumentsOf(STATUS).filter((argument) => argument !== undefined);
        expect(given, 'the status takes no parameter').toEqual([]);
        expect(touchedBesides(STATUS)).toEqual([]);
    });

    it('uploadRestoreArchive puts the File itself as the body, hands the signal on, and reports progress as onProgress(loaded, total)', async () => {
        const file = archive();
        const answer: RestoreUpload = {upload_id: UPLOAD_ID, size: file.size};
        const onProgress = vi.fn();
        const abort = new AbortController();
        zodios[UPLOAD].mockResolvedValue(answer);

        await expect(restore('uploadRestoreArchive')(file, {onProgress, signal: abort.signal})).resolves.toBe(answer);

        expect(zodios[UPLOAD]).toHaveBeenCalledTimes(1);
        const [body, config] = argumentsOf(UPLOAD) as [unknown, {onUploadProgress?: (event: AxiosProgressEvent) => void; signal?: AbortSignal} | undefined];
        expect(body, 'the archive goes as the raw body: the File itself, never a FormData').toBe(file);
        expect(config?.signal, 'the upload could not be cancelled').toBe(abort.signal);
        expect(config?.onUploadProgress, 'axios was given no onUploadProgress').toBeTypeOf('function');

        config?.onUploadProgress?.({loaded: 512, total: 2048, bytes: 512, lengthComputable: true} as AxiosProgressEvent);
        config?.onUploadProgress?.({loaded: 2048, total: 2048, bytes: 1536, lengthComputable: true} as AxiosProgressEvent);

        expect(onProgress.mock.calls).toEqual([
            [512, 2048],
            [2048, 2048],
        ]);
        expect(touchedBesides(UPLOAD)).toEqual([]);
    });

    it('uploadRestoreArchive without options still puts the File itself', async () => {
        const file = archive();
        zodios[UPLOAD].mockResolvedValue({upload_id: UPLOAD_ID, size: file.size});

        await restore('uploadRestoreArchive')(file);

        expect(argumentsOf(UPLOAD)[0]).toBe(file);
    });

    it('startRestoreCheck posts the upload id as {upload_id}, and returns the check', async () => {
        const answer = runningStage();
        zodios[STAGE].mockResolvedValue(answer);

        await expect(restore('startRestoreCheck')(UPLOAD_ID)).resolves.toBe(answer);

        expect(zodios[STAGE]).toHaveBeenCalledTimes(1);
        expect(argumentsOf(STAGE)[0], 'the body of POST /stage').toEqual({upload_id: UPLOAD_ID});
        expect(touchedBesides(STAGE)).toEqual([]);
    });

    it('getRestoreCheck reads the check by its id, as a path parameter, and returns it', async () => {
        const answer = runningStage();
        zodios[CHECK].mockResolvedValue(answer);

        await expect(restore('getRestoreCheck')(STAGE_ID)).resolves.toBe(answer);

        expect(zodios[CHECK].mock.calls).toEqual([[{params: {stage_id: STAGE_ID}}]]);
        expect(touchedBesides(CHECK)).toEqual([]);
    });

    it('deleteRestoreCheck deletes the check by its id, with no body, and resolves to nothing', async () => {
        // An empty 204 comes back from Zodios as an empty string: the wrapper answers void whatever it is.
        zodios[DROP].mockResolvedValue('');

        await expect(restore('deleteRestoreCheck')(STAGE_ID)).resolves.toBeUndefined();

        expect(zodios[DROP]).toHaveBeenCalledTimes(1);
        const [body, config] = argumentsOf(DROP);
        expect(body).toBeUndefined();
        expect(config, 'the id travels as the path parameter, the second argument of a Zodios delete').toEqual({params: {stage_id: STAGE_ID}});
        expect(touchedBesides(DROP)).toEqual([]);
    });

    it('confirmRestore posts with no body, the id as the path parameter, and returns the status', async () => {
        const answer = restoreStatus({state: 'pending', stage_id: STAGE_ID});
        zodios[CONFIRM].mockResolvedValue(answer);

        await expect(restore('confirmRestore')(STAGE_ID)).resolves.toBe(answer);

        expect(zodios[CONFIRM]).toHaveBeenCalledTimes(1);
        const [body, config] = argumentsOf(CONFIRM);
        expect(body).toBeUndefined();
        expect(config, 'the id travels as the path parameter, the second argument of a Zodios post').toEqual({params: {stage_id: STAGE_ID}});
        expect(touchedBesides(CONFIRM)).toEqual([]);
    });

    it('cancelPendingRestore deletes the pending restore with no body and no parameter, and resolves to nothing', async () => {
        zodios[CANCEL].mockResolvedValue('');

        await expect(restore('cancelPendingRestore')()).resolves.toBeUndefined();

        expect(zodios[CANCEL]).toHaveBeenCalledTimes(1);
        expect(argumentsOf(CANCEL).filter((argument) => argument !== undefined)).toEqual([]);
        expect(touchedBesides(CANCEL)).toEqual([]);
    });

    it('requestRestart posts with no body and no parameter, and returns the status', async () => {
        const answer = restoreStatus({state: 'pending', stage_id: STAGE_ID});
        zodios[RESTART].mockResolvedValue(answer);

        await expect(restore('requestRestart')()).resolves.toBe(answer);

        expect(zodios[RESTART]).toHaveBeenCalledTimes(1);
        expect(argumentsOf(RESTART).filter((argument) => argument !== undefined)).toEqual([]);
        expect(touchedBesides(RESTART)).toEqual([]);
    });

    it.each<[keyof RestoreRequests, Alias, () => Promise<unknown>]>([
        ['getRestoreStatus', STATUS, () => restore('getRestoreStatus')()],
        ['uploadRestoreArchive', UPLOAD, () => restore('uploadRestoreArchive')(archive())],
        ['startRestoreCheck', STAGE, () => restore('startRestoreCheck')(UPLOAD_ID)],
        ['getRestoreCheck', CHECK, () => restore('getRestoreCheck')(STAGE_ID)],
        ['deleteRestoreCheck', DROP, () => restore('deleteRestoreCheck')(STAGE_ID)],
        ['confirmRestore', CONFIRM, () => restore('confirmRestore')(STAGE_ID)],
        ['cancelPendingRestore', CANCEL, () => restore('cancelPendingRestore')()],
        ['requestRestart', RESTART, () => restore('requestRestart')()],
    ])('%s lets a refusal through untouched, so its code can still be read', async (_name, alias, call) => {
        const refused = refusal(409, 'restore_busy');
        zodios[alias].mockRejectedValue(refused);

        await expect(call()).rejects.toBe(refused);
    });
});

describe('the restore requests, replayed on the generated client (B5b §1)', () => {
    type Replayable = Record<string, (...args: unknown[]) => Promise<unknown>>;

    let createApiClient: typeof import('$lib/api/generated').createApiClient;

    beforeAll(async () => {
        ({createApiClient} = await import('$lib/api/generated'));
    });

    beforeEach(() => {
        for (const fn of Object.values(zodios)) fn.mockReset();
    });

    /** The generated client over an adapter that keeps each request as axios hands it to the network, answered at once. */
    function recordingClient(answer: unknown): {client: Replayable; requests: InternalAxiosRequestConfig[]} {
        const requests: InternalAxiosRequestConfig[] = [];
        const adapter: AxiosAdapter = async (config) => {
            requests.push(config);
            return {data: answer, status: 200, statusText: 'OK', headers: new AxiosHeaders(), config, request: {}};
        };
        const client = createApiClient('/', {axiosInstance: axios.create({adapter}), validate: false});
        return {client: client as unknown as Replayable, requests};
    }

    it.each<[keyof RestoreRequests, string, string, Alias, () => Promise<unknown>]>([
        ['getRestoreStatus', 'get', '/api/v1/backup/restore/status', STATUS, () => restore('getRestoreStatus')()],
        ['uploadRestoreArchive', 'put', '/api/v1/backup/restore/upload', UPLOAD, () => restore('uploadRestoreArchive')(archive())],
        ['startRestoreCheck', 'post', '/api/v1/backup/restore/stage', STAGE, () => restore('startRestoreCheck')(UPLOAD_ID)],
        ['getRestoreCheck', 'get', `/api/v1/backup/restore/stage/${STAGE_ID}`, CHECK, () => restore('getRestoreCheck')(STAGE_ID)],
        ['deleteRestoreCheck', 'delete', `/api/v1/backup/restore/stage/${STAGE_ID}`, DROP, () => restore('deleteRestoreCheck')(STAGE_ID)],
        ['confirmRestore', 'post', `/api/v1/backup/restore/stage/${STAGE_ID}/confirm`, CONFIRM, () => restore('confirmRestore')(STAGE_ID)],
        ['cancelPendingRestore', 'delete', '/api/v1/backup/restore/pending', CANCEL, () => restore('cancelPendingRestore')()],
        ['requestRestart', 'post', '/api/v1/backup/restore/restart', RESTART, () => restore('requestRestart')()],
    ])('%s: its arguments make the request %s %s', async (_name, method, url, alias, call) => {
        zodios[alias].mockResolvedValue(undefined);
        await call();
        expect(zodios[alias]).toHaveBeenCalledTimes(1);
        const passed = argumentsOf(alias);

        const {client, requests} = recordingClient(undefined);
        expect(typeof client[alias], `the generated client has no ${alias}: the route was renamed or removed`).toBe('function');
        await client[alias](...passed);

        expect(requests.map((request) => ({method: request.method, url: request.url}))).toEqual([{method, url}]);
    });

    it('uploadRestoreArchive: the request carries the File itself as application/octet-stream, with the progress callback and the signal', async () => {
        const file = archive();
        const abort = new AbortController();
        zodios[UPLOAD].mockResolvedValue(undefined);
        await restore('uploadRestoreArchive')(file, {onProgress: () => undefined, signal: abort.signal});
        const passed = argumentsOf(UPLOAD);

        const {client, requests} = recordingClient({upload_id: UPLOAD_ID, size: file.size});
        await client[UPLOAD](...passed);

        expect(requests).toHaveLength(1);
        const [request] = requests;
        expect(request.method).toBe('put');
        expect(request.url).toBe('/api/v1/backup/restore/upload');
        expect(request.data, 'the archive must leave as the raw body').toBe(file);
        expect(AxiosHeaders.from(request.headers).get('Content-Type')).toBe('application/octet-stream');
        expect(request.onUploadProgress, 'the progress of the upload is not followed').toBeTypeOf('function');
        expect(request.signal, 'the upload cannot be cancelled').toBe(abort.signal);
    });
});

describe('probeServer and restoreOutcome: a plain fetch on this origin, never Zodios (B5b §1)', () => {
    const ORIGIN = 'https://librefolio.example';
    let fetchStub: Mock<typeof fetch>;

    beforeAll(async () => {
        // restoreOutcome() may parse the status with the generated schema: hand it the real one.
        Object.assign(generatedSchemas, (await import('$lib/api/generated')).schemas);
    });

    beforeEach(() => {
        for (const fn of Object.values(zodios)) fn.mockReset();
        fetchStub = vi.fn<typeof fetch>(async () => {
            throw new TypeError('this case gave fetch no answer');
        });
        vi.stubGlobal('fetch', fetchStub);
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    /** What fetch was asked, resolved against the page origin: a relative path stays on it. */
    function fetched() {
        return fetchStub.mock.calls.map(([input, init]) => {
            const href = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
            const url = new URL(href, ORIGIN);
            return {origin: url.origin, path: url.pathname, init};
        });
    }

    /** The Zodios aliases called: none may be, its 401 interceptor would navigate to the login. */
    function zodiosCalls() {
        return (Object.keys(zodios) as Alias[]).filter((alias) => zodios[alias].mock.calls.length > 0);
    }

    function answer(status: number, body: string | null = null, contentType = 'application/json'): Response {
        return new Response(body, {status, headers: body === null ? {} : {'Content-Type': contentType}});
    }

    it('probeServer asks GET /api/v1/system/ready on this origin, same-origin credentials, never cached, and nothing through Zodios', async () => {
        fetchStub.mockResolvedValueOnce(answer(200, '{"status":"ready"}'));

        await expect(restore('probeServer')()).resolves.toBe('up');

        const requests = fetched();
        expect(requests).toHaveLength(1);
        expect(requests[0].origin, 'the probe left the page origin').toBe(ORIGIN);
        expect(requests[0].path).toBe('/api/v1/system/ready');
        expect(requests[0].init).toMatchObject({credentials: 'same-origin', cache: 'no-store'});
        expect(requests[0].init?.method ?? 'GET').toBe('GET');
        expect(zodiosCalls()).toEqual([]);
    });

    it.each<[number, 'up' | 'down']>([
        [200, 'up'],
        [503, 'down'],
        [502, 'down'],
        [500, 'down'],
        [404, 'down'],
    ])('probeServer: /system/ready answered %s → %s', async (status, expected) => {
        fetchStub.mockResolvedValueOnce(answer(status, status === 200 ? '{"status":"ready"}' : null));

        await expect(restore('probeServer')()).resolves.toBe(expected);

        expect(zodiosCalls()).toEqual([]);
    });

    it('probeServer: no answer at all (fetch rejects) → down, never a rejection', async () => {
        fetchStub.mockRejectedValueOnce(new TypeError('Failed to fetch'));

        await expect(restore('probeServer')()).resolves.toBe('down');
    });

    it('restoreOutcome asks GET /api/v1/backup/restore/status on this origin, same-origin credentials, never cached, and nothing through Zodios', async () => {
        fetchStub.mockResolvedValueOnce(answer(401, JSON.stringify({detail: 'Not authenticated'})));

        await expect(restore('restoreOutcome')()).resolves.toEqual({kind: 'signed_out'});

        const requests = fetched();
        expect(requests).toHaveLength(1);
        expect(requests[0].origin, 'the status was asked of another origin').toBe(ORIGIN);
        expect(requests[0].path).toBe('/api/v1/backup/restore/status');
        expect(requests[0].init).toMatchObject({credentials: 'same-origin', cache: 'no-store'});
        expect(requests[0].init?.method ?? 'GET').toBe('GET');
        expect(zodiosCalls(), 'Zodios answers a 401 by navigating to the login').toEqual([]);
    });

    it('restoreOutcome: 200 → status, with the body parsed', async () => {
        const status = restoreStatus({state: 'rolled_back', stage_id: STAGE_ID, reason: 'first_start_failed', finished_at: '2026-10-16T11:21:00Z'});
        fetchStub.mockResolvedValueOnce(answer(200, JSON.stringify(status)));

        await expect(restore('restoreOutcome')()).resolves.toEqual({kind: 'status', status});

        expect(zodiosCalls()).toEqual([]);
    });

    it.each([500, 502, 503])('restoreOutcome: %s → down', async (status) => {
        fetchStub.mockResolvedValueOnce(answer(status));

        await expect(restore('restoreOutcome')()).resolves.toEqual({kind: 'down'});
    });

    it('restoreOutcome: no answer at all (fetch rejects) → down, never a rejection', async () => {
        fetchStub.mockRejectedValueOnce(new TypeError('Failed to fetch'));

        await expect(restore('restoreOutcome')()).resolves.toEqual({kind: 'down'});
    });

    it('restoreOutcome: 200 with a page that is not JSON (a proxy while the server starts) → down', async () => {
        fetchStub.mockResolvedValueOnce(answer(200, '<html><body>Starting…</body></html>', 'text/html'));

        await expect(restore('restoreOutcome')()).resolves.toEqual({kind: 'down'});
    });

    /** The refusal of every restore route on an instance its hosting provider blocked (backend/app/api/v1/instance_block.py). */
    const BLOCKED = JSON.stringify({detail: {code: 'instance_blocked', message: 'This instance is blocked by its hosting provider'}});

    it('restoreOutcome: 423 instance_blocked — the hosting provider blocked the instance, the status route with it (P8) → blocked; one request, as for any read, nothing through Zodios', async () => {
        fetchStub.mockResolvedValueOnce(answer(423, BLOCKED));

        await expect(restore('restoreOutcome')()).resolves.toEqual({kind: 'blocked'});

        const requests = fetched();
        expect(requests, 'the outcome of a blocked instance is read with one request').toHaveLength(1);
        expect(requests[0].origin).toBe(ORIGIN);
        expect(requests[0].path).toBe('/api/v1/backup/restore/status');
        expect(requests[0].init).toMatchObject({credentials: 'same-origin', cache: 'no-store'});
        expect(requests[0].init?.method ?? 'GET').toBe('GET');
        expect(zodiosCalls(), 'Zodios answers a 423 instance_blocked by turning the block page on').toEqual([]);
    });

    it.each<[string, number, string | null, string?]>([
        ['a 423 with another code', 423, JSON.stringify({detail: {code: 'instance_locked', message: 'refused'}})],
        ['a 423 with a detail without a code', 423, JSON.stringify({detail: {message: 'This instance is blocked by its hosting provider'}})],
        ["a 423 with a detail that is a string (FastAPI's default)", 423, JSON.stringify({detail: 'Locked'})],
        ['a 423 with the code outside detail', 423, JSON.stringify({code: 'instance_blocked'})],
        ['a 423 whose body is null', 423, 'null'],
        ['a 423 with no body', 423, null],
        ['a 423 with a page that is not JSON (a proxy)', 423, '<html><body>Locked</body></html>', 'text/html'],
        ['the code instance_blocked on a 403: only a 423 is the block', 403, BLOCKED],
        ['the code instance_blocked on a 409', 409, BLOCKED],
        ['the code instance_blocked on a 200, a body that is not a status', 200, BLOCKED],
    ])('restoreOutcome: %s → down, never blocked', async (_case, status, body, contentType) => {
        fetchStub.mockResolvedValueOnce(answer(status, body, contentType));

        await expect(restore('restoreOutcome')()).resolves.toEqual({kind: 'down'});

        expect(fetchStub, 'one read, one request').toHaveBeenCalledTimes(1);
        expect(zodiosCalls()).toEqual([]);
    });
});
