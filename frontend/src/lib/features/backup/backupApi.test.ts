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
 * The outcome of a restart read without a session (lot B5c, the one-time ticket), written red first against the approved
 * contract. The generated client knows neither `RestoreRestartAccepted` nor `RestoreOutcome` yet: both are written out
 * below, as `instance_blocked` was.
 *   - `requestRestart()` hands back the accepted restart untouched — the status and its `outcome_ticket`; replayed on the
 *     generated client as the app builds it (`validate: 'response'`: Zodios then hands back what the route's schema
 *     parsed, and a plain zod object drops the keys it does not know), the ticket must survive the schema of the restart
 *     route — red until the client is generated again from the B5c backend;
 *   - `RESTORE_TICKET_HEADER` is `X-Restore-Ticket`;
 *   - `restoreOutcome(ticket)`, with a ticket: first one plain `fetch` of `GET /api/v1/backup/restore/outcome` on this
 *     origin — `credentials: 'same-origin'`, `cache: 'no-store'`, `Accept: application/json`, the ticket in
 *     `X-Restore-Ticket` and nowhere in the URL —, never through Zodios. A 200 that is a valid outcome — `state` one of
 *     `pending`, `in_progress`, `committed`, `rolled_back`; `reason` a rollback reason or null; `waiting` a waiting reason
 *     (`instance_blocked` included: the route answers on a blocked instance) or null; either may be left out — is
 *     `status`, holding `{state, reason, waiting}` and nothing else. A 404, a 401 or a 423 says the route cannot be
 *     reached by this caller — a ticket that does not hold, a server without the route, a blocked instance whose
 *     allow-list lacks the route, a proxy —, not that the server is starting: it is today's read, a second request, the
 *     status route, mapped as today (401 `signed_out`, 423 `instance_blocked` `blocked`, 200 `status`, anything else
 *     `down`). Any other status of the outcome route (a 5xx included: the server may still be starting), a 200 that is
 *     not a valid outcome, or no answer is `down`, and the status is not read. Without a ticket (`null`, or left out):
 *     today's read alone, one request.
 *
 * Where that contract is silent, the choices of this file, each one place to change: a 404, a 401 or a 423 falls back
 * whatever its body (a 423 with the code `instance_blocked` or without it, a JSON detail, none, a page that is not
 * JSON); the status read of the fallback is today's request, so it carries no ticket; an outcome with keys besides its
 * three is still read, and only its three reach the status; one left out is null or absent in it, never anything else.
 *
 * The 401 and the 423 of the outcome route were first written as `down`. The contract was amended at 15:40: read as
 * `down`, they would keep the overlay waiting for ever with no hint, worse than B5b, so they fall back like a 404.
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
    // B4: the rules of a secure archive's password, `GET /backup/instance/options` (handler `get_instance_backup_options`).
    get_instance_backup_options_api_v1_backup_instance_options_get: vi.fn(),
}));
/** The generated zod schemas, filled in by the group that may need them (the status `restoreOutcome()` reads). */
const generatedSchemas = vi.hoisted((): Record<string, unknown> => ({}));
vi.mock('$lib/api', () => ({zodiosApi: zodios, schemas: generatedSchemas}));

import {backupErrorCode, backupFailureCode, deleteInstanceBackupJob, getInstanceBackupJob, instanceBackupFileUrl, RESTORE_TICKET_HEADER, startInstanceBackup, type InstanceBackupJob} from './backupApi';
import * as backupApiModule from './backupApi';

type Alias = keyof typeof zodios;

const START: Alias = 'start_instance_backup_api_v1_backup_instance_post';
const GET: Alias = 'get_instance_backup_job_api_v1_backup_instance_jobs__job_id__get';
const DELETE: Alias = 'delete_instance_backup_job_api_v1_backup_instance_jobs__job_id__delete';

const JOB_ID = '0123456789abcdef0123456789abcdef';

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
        expect(body, 'a backup is started with an empty body').toBeNull();
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
/** B4 (§5): an upload says what was stored, a zip or an envelope. Written out until the client is generated again from the B4 backend. */
type RestoreUpload = z.infer<typeof schemas.RestoreUpload> & {kind: 'zip' | 'envelope'};
type UploadOptions = {onProgress?: (loaded: number, total: number) => void; signal?: AbortSignal};
/** `unreadable` (SEC-3/4/5 wave, «the status 500»): the server cannot read the state of the restore, with why when it says. */
type RestoreOutcomeAnswer = {kind: 'signed_out'} | {kind: 'status'; status: RestoreStatus} | {kind: 'blocked'} | {kind: 'unreadable'; reason: string | null} | {kind: 'down'};
/** The answer of an accepted restart (B5c): the status, and the one-time ticket that reads its outcome. Not generated yet. */
type RestoreRestartAccepted = RestoreStatus & {outcome_ticket: string};
type RollbackReason = NonNullable<RestoreStatus['reason']>;
type WaitingReason = NonNullable<RestoreStatus['waiting']>;
/** The answer of `GET /backup/restore/outcome` (B5c): the state, why it rolled back, why it waits; nothing else. Not generated yet. */
type OutcomeState = 'pending' | 'in_progress' | 'committed' | 'rolled_back';

interface RestoreRequests {
    getRestoreStatus: () => Promise<RestoreStatus>;
    uploadRestoreArchive: (file: File, options?: UploadOptions) => Promise<RestoreUpload>;
    startRestoreCheck: (uploadId: string) => Promise<RestoreStage>;
    getRestoreCheck: (stageId: string) => Promise<RestoreStage>;
    deleteRestoreCheck: (stageId: string) => Promise<void>;
    /** B5-1b: `ownerUserId`, the account of the backup that becomes the owner's (managed only), `null` by default. */
    confirmRestore: (stageId: string, ownerUserId?: number | null) => Promise<RestoreStatus>;
    cancelPendingRestore: () => Promise<void>;
    requestRestart: () => Promise<RestoreRestartAccepted>;
    probeServer: () => Promise<'up' | 'down'>;
    restoreOutcome: (ticket?: string | null) => Promise<RestoreOutcomeAnswer>;
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
/** A ticket as the server makes it (`secrets.token_urlsafe(32)`): URL-safe, so nothing would stop it from riding in a URL. */
const TICKET = 'kq8Z3vR-wT0yN5mB_xH2cL7pJ4sF9dG1eA6uK0iO3rY';

const ROLLBACK_REASONS: RollbackReason[] = ['first_start_failed', 'swap_interrupted', 'swap_failed', 'stage_missing'];
const WAITING_REASONS: WaitingReason[] = ['backup_running', 'other_data_directory', 'server_running', 'instance_blocked'];

function restoreStatus(overrides: Partial<RestoreStatus> = {}): RestoreStatus {
    return {state: 'none', stage_id: null, confirmed_at: null, confirmed_by: null, backup_created_at: null, backup_app_version: null, action: null, finished_at: null, reason: null, waiting: null, upload_limit_mb: 500, ...overrides};
}

/** What an accepted restart answers (B5c): the restore still pending, and its outcome ticket. */
const acceptedRestart = (): RestoreRestartAccepted => ({...restoreStatus({state: 'pending', stage_id: STAGE_ID, confirmed_at: '2026-10-16T11:20:00Z', confirmed_by: 'admin', action: 'same'}), outcome_ticket: TICKET});

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
        const answer: RestoreUpload = {upload_id: UPLOAD_ID, size: file.size, kind: 'zip'};
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
        zodios[UPLOAD].mockResolvedValue({upload_id: UPLOAD_ID, size: file.size, kind: 'zip'});

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

    // B5-1b (interface §8): the body is `{owner_user_id}` — `null` when no owner is named (self-hosted, or the default).
    it.each<[string, (fn: RestoreRequests['confirmRestore']) => Promise<RestoreStatus>, number | null]>([
        ['no owner given: owner_user_id null', (fn) => fn(STAGE_ID), null],
        ['null given: owner_user_id null', (fn) => fn(STAGE_ID, null), null],
        ['the owner 7 given: owner_user_id 7', (fn) => fn(STAGE_ID, 7), 7],
    ])('confirmRestore posts {owner_user_id} (%s), the id as the path parameter, and returns the status', async (_case, call, owner) => {
        const answer = restoreStatus({state: 'pending', stage_id: STAGE_ID});
        zodios[CONFIRM].mockResolvedValue(answer);

        await expect(call(restore('confirmRestore'))).resolves.toBe(answer);

        expect(zodios[CONFIRM]).toHaveBeenCalledTimes(1);
        const [body, config] = argumentsOf(CONFIRM);
        expect(body, 'the body of the confirmation (RestoreConfirmRequest)').toEqual({owner_user_id: owner});
        expect(config, 'the id travels as the path parameter, the second argument of a Zodios post').toEqual({params: {stage_id: STAGE_ID}});
        expect(touchedBesides(CONFIRM)).toEqual([]);
    });

    it('confirmRestore with an owner: the body replayed on the generated client is the JSON {"owner_user_id": 7}', async () => {
        zodios[CONFIRM].mockResolvedValue(undefined);
        await restore('confirmRestore')(STAGE_ID, 7);
        const passed = argumentsOf(CONFIRM);

        const {createApiClient} = await import('$lib/api/generated');
        const requests: InternalAxiosRequestConfig[] = [];
        const adapter: AxiosAdapter = async (config) => {
            requests.push(config);
            return {data: undefined, status: 200, statusText: 'OK', headers: new AxiosHeaders(), config, request: {}};
        };
        const client = createApiClient('/', {axiosInstance: axios.create({adapter}), validate: false}) as unknown as Record<string, (...args: unknown[]) => Promise<unknown>>;
        await client[CONFIRM](...passed);

        expect(requests).toHaveLength(1);
        const data = requests[0].data;
        expect(typeof data === 'string' ? JSON.parse(data) : data).toEqual({owner_user_id: 7});
    });

    it('cancelPendingRestore deletes the pending restore with no body and no parameter, and resolves to nothing', async () => {
        zodios[CANCEL].mockResolvedValue('');

        await expect(restore('cancelPendingRestore')()).resolves.toBeUndefined();

        expect(zodios[CANCEL]).toHaveBeenCalledTimes(1);
        expect(argumentsOf(CANCEL).filter((argument) => argument !== undefined)).toEqual([]);
        expect(touchedBesides(CANCEL)).toEqual([]);
    });

    it('requestRestart posts with no body and no parameter, and returns the accepted restart untouched — its outcome_ticket with it (B5c)', async () => {
        const answer = acceptedRestart();
        zodios[RESTART].mockResolvedValue(answer);

        const accepted = await restore('requestRestart')();

        expect(accepted).toBe(answer);
        expect(accepted.outcome_ticket, 'the ticket of the restart was lost on the way').toBe(TICKET);
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

        const {client, requests} = recordingClient({upload_id: UPLOAD_ID, size: file.size, kind: 'zip'});
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

    it('requestRestart: on the generated client as the app builds it (its answers validated, then handed back as parsed), the accepted restart keeps its outcome_ticket (B5c)', async () => {
        zodios[RESTART].mockResolvedValue(undefined);
        await restore('requestRestart')();
        const passed = argumentsOf(RESTART);
        // A JSON answer, as the server's: Zodios checks only those, and replaces the answer with what the route's schema parsed.
        const adapter: AxiosAdapter = async (config) => ({data: acceptedRestart(), status: 202, statusText: 'Accepted', headers: AxiosHeaders.from({'content-type': 'application/json'}), config, request: {}});
        // `validate: 'response'`, as zodios-client.ts builds the client of the app.
        const client = createApiClient('/', {axiosInstance: axios.create({adapter}), validate: 'response'}) as unknown as Replayable;

        const answer = (await client[RESTART](...passed)) as Partial<RestoreRestartAccepted>;

        expect(answer.state, 'precondition: the answer went through the schema of the restart route').toBe('pending');
        expect(answer.outcome_ticket, "the schema of the restart route drops the ticket: the page could never read the restore's outcome without a session").toBe(TICKET);
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
            return {href, origin: url.origin, path: url.pathname, search: url.search, hash: url.hash, init, headers: new Headers(init?.headers)};
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

    // -----------------------------------------------------------------------------------------------------------------
    // B5c — the outcome read with the one-time ticket the restart answered, without a session
    // -----------------------------------------------------------------------------------------------------------------

    describe('restoreOutcome(ticket): the outcome route first, the ticket in a header; the status read only after a 404, a 401 or a 423 (B5c)', () => {
        const OUTCOME_PATH = '/api/v1/backup/restore/outcome';
        const STATUS_PATH = '/api/v1/backup/restore/status';
        /** The one 404 the outcome route answers for every ticket that does not hold: unknown, expired, used, of another restore. */
        const NO_OUTCOME = JSON.stringify({detail: {code: 'restore_outcome_not_found', message: 'No outcome for this ticket'}});

        /** The answer of the outcome route: its three fields, and nothing else. */
        const outcome = (state: OutcomeState, reason: RollbackReason | null = null, waiting: WaitingReason | null = null) => JSON.stringify({state, reason, waiting});

        /** The request a ticket makes first: GET /outcome on this origin, never cached, JSON asked, the ticket in its header and nowhere in the URL. */
        function expectOutcomeRequest(request: ReturnType<typeof fetched>[number]): void {
            expect(request.origin, 'the outcome was asked of another origin').toBe(ORIGIN);
            expect(request.path).toBe(OUTCOME_PATH);
            expect(request.init).toMatchObject({credentials: 'same-origin', cache: 'no-store'});
            expect(request.init?.method ?? 'GET').toBe('GET');
            expect(request.headers.get('Accept')).toBe('application/json');
            expect(request.headers.get('X-Restore-Ticket'), 'the ticket did not travel in its header').toBe(TICKET);
            expect(request.search, 'the ticket must never travel in the URL').toBe('');
            expect(request.hash).toBe('');
            expect(request.href).not.toContain(TICKET);
        }

        it('RESTORE_TICKET_HEADER is X-Restore-Ticket, the header the ticket travels in', () => {
            expect(RESTORE_TICKET_HEADER, 'backupApi.ts exports no RESTORE_TICKET_HEADER (B5c)').toBe('X-Restore-Ticket');
        });

        it('with a ticket: one GET /api/v1/backup/restore/outcome on this origin — same-origin credentials, never cached, JSON asked, the ticket in X-Restore-Ticket and nowhere in the URL —, nothing through Zodios', async () => {
            fetchStub.mockResolvedValueOnce(answer(200, outcome('rolled_back', 'swap_failed')));

            const read = await restore('restoreOutcome')(TICKET);

            const requests = fetched();
            expect(
                requests.map((request) => request.path),
                'with a ticket the outcome route is asked first, and alone once it answers',
            ).toEqual([OUTCOME_PATH]);
            expectOutcomeRequest(requests[0]);
            expect(read).toStrictEqual({kind: 'status', status: {state: 'rolled_back', reason: 'swap_failed', waiting: null}});
            expect(zodiosCalls(), 'Zodios navigates to the login on a 401 and turns the block page on for a 423').toEqual([]);
        });

        it.each<[string, OutcomeState, RollbackReason | null, WaitingReason | null]>([
            ['committed', 'committed', null, null],
            ...ROLLBACK_REASONS.map((reason): [string, OutcomeState, RollbackReason, null] => [`rolled back, ${reason}`, 'rolled_back', reason, null]),
            ['pending, waiting for nothing', 'pending', null, null],
            ...WAITING_REASONS.map((waiting): [string, OutcomeState, null, WaitingReason] => [`pending, waiting for ${waiting}`, 'pending', null, waiting]),
            ['in progress', 'in_progress', null, null],
        ])('with a ticket, a 200 outcome — %s → status, holding {state, reason, waiting} and nothing else; one request', async (_case, state, reason, waiting) => {
            fetchStub.mockResolvedValueOnce(answer(200, outcome(state, reason, waiting)));

            const read = await restore('restoreOutcome')(TICKET);

            const requests = fetched();
            expect(requests.map((request) => request.path)).toEqual([OUTCOME_PATH]);
            expectOutcomeRequest(requests[0]);
            expect(read).toStrictEqual({kind: 'status', status: {state, reason, waiting}});
        });

        it('with a ticket, an outcome that leaves reason and waiting out → status with its state; neither filled with anything but null', async () => {
            fetchStub.mockResolvedValueOnce(answer(200, JSON.stringify({state: 'committed'})));

            const read = await restore('restoreOutcome')(TICKET);

            expect(fetched().map((request) => request.path)).toEqual([OUTCOME_PATH]);
            expect(read).toMatchObject({kind: 'status', status: {state: 'committed'}});
            const {status} = read as Extract<RestoreOutcomeAnswer, {kind: 'status'}>;
            expect(status.reason ?? null).toBeNull();
            expect(status.waiting ?? null).toBeNull();
            expect(
                Object.keys(status).filter((key) => !['state', 'reason', 'waiting'].includes(key)),
                'the status holds more than the outcome said',
            ).toEqual([]);
        });

        it('with a ticket, an outcome carrying keys besides its three → still read, and only its three reach the status', async () => {
            fetchStub.mockResolvedValueOnce(answer(200, JSON.stringify({state: 'rolled_back', reason: 'swap_failed', waiting: null, stage_id: STAGE_ID, confirmed_by: 'admin'})));

            const read = await restore('restoreOutcome')(TICKET);

            expect(fetched().map((request) => request.path)).toEqual([OUTCOME_PATH]);
            expect(read).toStrictEqual({kind: 'status', status: {state: 'rolled_back', reason: 'swap_failed', waiting: null}});
        });

        /**
         * The answers of the outcome route that say it cannot be reached by this caller, not that the server is starting —
         * a ticket that does not hold (unknown, expired, used, or a restart asked from the command line), a server without
         * the route, a blocked instance whose allow-list lacks the route, a proxy in between: each falls back on today's
         * read. One of each, so that each is followed by every answer that read may get.
         */
        const UNREACHABLE: [string, () => Promise<Response>][] = [
            ['404 restore_outcome_not_found', async () => answer(404, NO_OUTCOME)],
            ['401', async () => answer(401, JSON.stringify({detail: 'Not authenticated'}))],
            ['423 instance_blocked', async () => answer(423, BLOCKED)],
            ['423 without the code instance_blocked', async () => answer(423, JSON.stringify({detail: {code: 'instance_locked', message: 'refused'}}))],
        ];

        it.each<[string, () => Promise<Response>]>([
            ...UNREACHABLE,
            ["404, FastAPI's default: a server without the route", async () => answer(404, JSON.stringify({detail: 'Not Found'}))],
            ['404 with no body: a proxy', async () => answer(404)],
            ['404 with a page that is not JSON: a proxy', async () => answer(404, '<html><body>Not Found</body></html>', 'text/html')],
            ['401 with no body: a proxy', async () => answer(401)],
            ['401 with a page that is not JSON: the sign-in page of a proxy', async () => answer(401, '<html><body>Sign in</body></html>', 'text/html')],
            ["423 with a detail that is a string (FastAPI's default)", async () => answer(423, JSON.stringify({detail: 'Locked'}))],
            ['423 with no body', async () => answer(423)],
            ['423 with a page that is not JSON: a proxy', async () => answer(423, '<html><body>Locked</body></html>', 'text/html')],
        ])("with a ticket, the outcome route answers %s → today's read, whatever the body: a second request, GET /api/v1/backup/restore/status, as today, without the ticket", async (_case, first) => {
            const status = restoreStatus({state: 'rolled_back', stage_id: STAGE_ID, reason: 'first_start_failed', finished_at: '2026-10-16T11:21:00Z'});
            fetchStub.mockImplementationOnce(first).mockResolvedValueOnce(answer(200, JSON.stringify(status)));

            const read = await restore('restoreOutcome')(TICKET);

            const requests = fetched();
            expect(
                requests.map((request) => request.path),
                "the outcome route cannot be reached by this caller: today's read follows, once",
            ).toEqual([OUTCOME_PATH, STATUS_PATH]);
            expectOutcomeRequest(requests[0]);
            expect(requests[1].origin).toBe(ORIGIN);
            expect(requests[1].init).toMatchObject({credentials: 'same-origin', cache: 'no-store'});
            expect(requests[1].init?.method ?? 'GET').toBe('GET');
            expect(requests[1].headers.has('X-Restore-Ticket'), 'the ticket went to the status route too').toBe(false);
            expect(requests[1].href).not.toContain(TICKET);
            expect(read).toEqual({kind: 'status', status});
            expect(zodiosCalls()).toEqual([]);
        });

        /** What today's read may answer once it follows, and what it gives: the status route's mapping, as today. */
        const TODAYS_READ: [string, () => Promise<Response>, RestoreOutcomeAnswer][] = [
            ['401, the session ended → signed_out', async () => answer(401, JSON.stringify({detail: 'Not authenticated'})), {kind: 'signed_out'}],
            ['423 instance_blocked → blocked', async () => answer(423, BLOCKED), {kind: 'blocked'}],
            ['423 with another code → down', async () => answer(423, JSON.stringify({detail: {code: 'instance_locked', message: 'refused'}})), {kind: 'down'}],
            ['404 → down, and no third request', async () => answer(404, NO_OUTCOME), {kind: 'down'}],
            ['503 → down', async () => answer(503), {kind: 'down'}],
            ['200 with a page that is not JSON → down', async () => answer(200, '<html><body>Starting…</body></html>', 'text/html'), {kind: 'down'}],
            ['no answer → down', () => Promise.reject(new TypeError('Failed to fetch')), {kind: 'down'}],
        ];

        type FallbackRow = [string, string, () => Promise<Response>, () => Promise<Response>, RestoreOutcomeAnswer];

        it.each<FallbackRow>(UNREACHABLE.flatMap(([first, firstAnswer]) => TODAYS_READ.map(([second, secondAnswer, expected]): FallbackRow => [first, second, firstAnswer, secondAnswer, expected])))(
            'with a ticket, the outcome route answers %s; then the status read as today answers %s',
            async (_first, _second, firstAnswer, secondAnswer, expected) => {
                fetchStub.mockImplementationOnce(firstAnswer).mockImplementationOnce(secondAnswer);

                const read = await restore('restoreOutcome')(TICKET);

                expect(
                    fetched().map((request) => request.path),
                    "the outcome route cannot be reached by this caller: today's read follows, once, and nothing after it",
                ).toEqual([OUTCOME_PATH, STATUS_PATH]);
                expect(read).toEqual(expected);
                expect(zodiosCalls()).toEqual([]);
            },
        );

        it.each<[string, () => Promise<Response>]>([
            ['403', async () => answer(403, JSON.stringify({detail: 'Forbidden'}))],
            ['500', async () => answer(500)],
            ['502, a page of the proxy while the server starts', async () => answer(502, '<html><body>Bad Gateway</body></html>', 'text/html')],
            ['503', async () => answer(503)],
            ['504, a proxy that waited for the server to start', async () => answer(504)],
            ['200, a page that is not JSON', async () => answer(200, '<html><body>Starting…</body></html>', 'text/html')],
            ['200, JSON null', async () => answer(200, 'null')],
            ['200, a list', async () => answer(200, '[]')],
            ['200, no state', async () => answer(200, JSON.stringify({reason: null, waiting: null}))],
            ['200, the state none: no outcome has it', async () => answer(200, JSON.stringify({state: 'none', reason: null, waiting: null}))],
            ['200, an unknown state', async () => answer(200, JSON.stringify({state: 'applied', reason: null, waiting: null}))],
            ['200, a state that is not a string', async () => answer(200, JSON.stringify({state: 3, reason: null, waiting: null}))],
            ['200, an unknown reason', async () => answer(200, JSON.stringify({state: 'rolled_back', reason: 'exploded', waiting: null}))],
            ['200, an unknown waiting', async () => answer(200, JSON.stringify({state: 'pending', reason: null, waiting: 'tea_break'}))],
            ['no answer (fetch rejects)', () => Promise.reject(new TypeError('Failed to fetch'))],
        ])('with a ticket, the outcome route answers %s → down, and the status is not read', async (_case, first) => {
            fetchStub.mockImplementationOnce(first);

            const read = await restore('restoreOutcome')(TICKET);

            const requests = fetched();
            expect(
                requests.map((request) => request.path),
                'only a 404, a 401 or a 423 falls back on the status read',
            ).toEqual([OUTCOME_PATH]);
            expectOutcomeRequest(requests[0]);
            expect(read).toEqual({kind: 'down'});
            expect(zodiosCalls()).toEqual([]);
        });

        it.each<[string, () => Promise<RestoreOutcomeAnswer>]>([
            ['null', () => restore('restoreOutcome')(null)],
            ['left out', () => restore('restoreOutcome')()],
        ])("without a ticket (%s): today's read alone — one GET /api/v1/backup/restore/status, no X-Restore-Ticket, the outcome route never asked", async (_case, read) => {
            const status = restoreStatus({state: 'pending', stage_id: STAGE_ID, waiting: 'server_running'});
            fetchStub.mockResolvedValueOnce(answer(200, JSON.stringify(status)));

            await expect(read()).resolves.toEqual({kind: 'status', status});

            const requests = fetched();
            expect(requests.map((request) => request.path)).toEqual([STATUS_PATH]);
            expect(requests[0].headers.has('X-Restore-Ticket')).toBe(false);
            expect(requests[0].init).toMatchObject({credentials: 'same-origin', cache: 'no-store'});
            expect(zodiosCalls()).toEqual([]);
        });
    });

    // -----------------------------------------------------------------------------------------------------------------
    // The status 500 — a state of the restore the server cannot read (SEC-3/4/5 wave, written red first)
    // -----------------------------------------------------------------------------------------------------------------

    /*
     * `GET /api/v1/backup/restore/status` answers `500 {detail: {code: 'restore_state_unreadable', message, reason}}`,
     * `reason` one of `io`, `not_a_file`, `invalid`, when the server cannot read the state of the restore. The status read
     * (`readStatusWithSession`, today's read: without a ticket, or after the outcome route answered 404, 401 or 423) gives
     * `{kind: 'unreadable', reason}` for it — `reason` the detail's when it is a string, `null` when it is absent or not a
     * string —, so the restart page stops polling a state that will not become readable by waiting. Any other 500, the
     * code anywhere but in `detail`, the code on another status, or a body that is not JSON stays `down`.
     *
     * Red today: the read knows no `unreadable`, and gives `down` for every 500.
     */
    describe('restoreOutcome: the status route answers 500 restore_state_unreadable → unreadable, with its reason', () => {
        const OUTCOME_PATH = '/api/v1/backup/restore/outcome';
        const STATUS_PATH = '/api/v1/backup/restore/status';
        const NO_OUTCOME = JSON.stringify({detail: {code: 'restore_outcome_not_found', message: 'No outcome for this ticket'}});
        const STATE_REASONS = ['io', 'not_a_file', 'invalid'] as const;
        const MESSAGE = 'The state of the pending restore cannot be read';

        /** The refusal of an unreadable state, `reason` written in the detail as given (left out when `undefined`). */
        const unreadable = (reason?: unknown) => JSON.stringify({detail: {code: 'restore_state_unreadable', message: MESSAGE, ...(reason === undefined ? {} : {reason})}});

        it.each(STATE_REASONS)('without a ticket, 500 restore_state_unreadable, reason %s → unreadable with that reason; one GET of the status, nothing through Zodios', async (reason) => {
            fetchStub.mockResolvedValueOnce(answer(500, unreadable(reason)));

            const read = await restore('restoreOutcome')();

            expect(read).toStrictEqual({kind: 'unreadable', reason});
            const requests = fetched();
            expect(
                requests.map((request) => request.path),
                'one read, one request',
            ).toEqual([STATUS_PATH]);
            expect(requests[0].origin).toBe(ORIGIN);
            expect(requests[0].init).toMatchObject({credentials: 'same-origin', cache: 'no-store'});
            expect(zodiosCalls()).toEqual([]);
        });

        it.each<[string, unknown]>([
            ['left out', undefined],
            ['null', null],
            ['a number', 3],
            ['an object', {kind: 'io'}],
            ['a list', ['io']],
            ['a boolean', true],
        ])('without a ticket, 500 restore_state_unreadable whose reason is %s → unreadable, reason null', async (_case, reason) => {
            fetchStub.mockResolvedValueOnce(answer(500, unreadable(reason)));

            const read = await restore('restoreOutcome')();

            expect(read).toStrictEqual({kind: 'unreadable', reason: null});
            expect(fetchStub).toHaveBeenCalledTimes(1);
        });

        it.each(STATE_REASONS)('with a ticket, the outcome route answers 404, then the status read answers 500 restore_state_unreadable (%s) → unreadable with that reason; two requests, the status without the ticket', async (reason) => {
            fetchStub.mockResolvedValueOnce(answer(404, NO_OUTCOME)).mockResolvedValueOnce(answer(500, unreadable(reason)));

            const read = await restore('restoreOutcome')(TICKET);

            expect(read).toStrictEqual({kind: 'unreadable', reason});
            const requests = fetched();
            expect(
                requests.map((request) => request.path),
                "the outcome route cannot be reached: today's read follows, once",
            ).toEqual([OUTCOME_PATH, STATUS_PATH]);
            expect(requests[1].headers.has('X-Restore-Ticket'), 'the ticket went to the status route too').toBe(false);
            expect(zodiosCalls()).toEqual([]);
        });

        it.each<[string, () => Response]>([
            ['401', () => answer(401, JSON.stringify({detail: 'Not authenticated'}))],
            ['423 instance_blocked', () => answer(423, JSON.stringify({detail: {code: 'instance_blocked', message: 'blocked'}}))],
        ])('with a ticket, the outcome route answers %s, then the status read answers 500 restore_state_unreadable → unreadable, as after a 404', async (_case, first) => {
            fetchStub.mockResolvedValueOnce(first()).mockResolvedValueOnce(answer(500, unreadable('io')));

            const read = await restore('restoreOutcome')(TICKET);

            expect(fetched().map((request) => request.path)).toEqual([OUTCOME_PATH, STATUS_PATH]);
            expect(read).toStrictEqual({kind: 'unreadable', reason: 'io'});
        });

        it('with a ticket, the outcome route answers 404, then the status read answers 500 restore_state_unreadable without a reason → unreadable, reason null', async () => {
            fetchStub.mockResolvedValueOnce(answer(404, NO_OUTCOME)).mockResolvedValueOnce(answer(500, unreadable()));

            await expect(restore('restoreOutcome')(TICKET)).resolves.toStrictEqual({kind: 'unreadable', reason: null});
        });

        /** The answers of the status route that are not the refusal of an unreadable state: each stays `down`. */
        const NOT_UNREADABLE: [string, number, string | null, string?][] = [
            ['500 with another code', 500, JSON.stringify({detail: {code: 'backup_upload_failed', message: 'failed', reason: 'io'}})],
            ['500 with a detail without a code', 500, JSON.stringify({detail: {message: MESSAGE, reason: 'io'}})],
            ["500 with a detail that is a string (FastAPI's default)", 500, JSON.stringify({detail: 'Internal Server Error'})],
            ['500 with the code outside detail', 500, JSON.stringify({code: 'restore_state_unreadable', reason: 'io'})],
            ['500 whose body is JSON null', 500, 'null'],
            ['500 with no body', 500, null],
            ['500 with a page that is not JSON, naming the code', 500, '<html><body>restore_state_unreadable</body></html>', 'text/html'],
            ['500 with a broken JSON body', 500, '{"detail": {"code": "restore_state_unreadable"'],
            ['the code restore_state_unreadable on a 503', 503, unreadable('io')],
            ['the code restore_state_unreadable on a 502', 502, unreadable('io')],
            ['the code restore_state_unreadable on a 409', 409, unreadable('io')],
            ['the code restore_state_unreadable on a 200, a body that is not a status', 200, unreadable('io')],
        ];

        it.each(NOT_UNREADABLE)('without a ticket, %s → down, never unreadable', async (_case, status, body, contentType) => {
            fetchStub.mockResolvedValueOnce(answer(status, body, contentType));

            await expect(restore('restoreOutcome')()).resolves.toEqual({kind: 'down'});

            expect(fetchStub, 'one read, one request').toHaveBeenCalledTimes(1);
            expect(zodiosCalls()).toEqual([]);
        });

        it.each(NOT_UNREADABLE)('with a ticket, the outcome route answers 404, then %s → down, never unreadable', async (_case, status, body, contentType) => {
            fetchStub.mockResolvedValueOnce(answer(404, NO_OUTCOME)).mockResolvedValueOnce(answer(status, body, contentType));

            await expect(restore('restoreOutcome')(TICKET)).resolves.toEqual({kind: 'down'});

            expect(fetched().map((request) => request.path)).toEqual([OUTCOME_PATH, STATUS_PATH]);
        });
    });
});

// =====================================================================================================================
// B4 — the «secure» backup: the password of a new archive, the rules it must meet, the password of an envelope to
// restore, and the envelope told from a zip (B4 brief §4, §5, §7; written red first)
// =====================================================================================================================

/*
 * The contract under test:
 *   - `startInstanceBackup(password?)`: without a password, the request of before (no body: a clear backup); with one,
 *     the body `{password}`; replayed on the generated client, `POST /api/v1/backup/instance` with that JSON body;
 *   - `getInstanceBackupOptions()`: `GET /backup/instance/options`, no parameter, the answer handed back untouched
 *     (`{password_rules: [{code, value}]}`); its alias is `get_instance_backup_options_api_v1_backup_instance_options_get`,
 *     the name FastAPI gives a handler `get_instance_backup_options` on that path — the choice of this file, one place to
 *     change;
 *   - `startRestoreCheck(uploadId, password?)`: the body `{upload_id, password}` with a password, and `{upload_id}` alone
 *     on the wire without one, as today;
 *   - refusals go through untouched, so that `password_too_weak` or `wrong_password` can be read off them;
 *   - `isEnvelopeFile(blob)`: true exactly when the first four bytes are `LFBK` — the name, the type and anything after
 *     them never decide —, and it reads the head of the file, never the whole archive into the page.
 *
 * Red today: the functions take no password and send none; `getInstanceBackupOptions` and `isEnvelopeFile` do not exist;
 * the options route is not in the generated client. Green today, and to stay so: the guards of «without a password, as
 * today», and the refusals of the two requests that exist already, let through. `isEnvelopeFile` runs here in Node, as
 * the rest of this file: a Blob's own readers (`slice`, `arrayBuffer`), not a FileReader, which Node does not have.
 */

const OPTIONS: Alias = 'get_instance_backup_options_api_v1_backup_instance_options_get';
const PASSWORD = 'Correct-Horse-Battery-9';

/** B4 (§4): the answer of `GET /backup/instance/options`. Written out until the client is generated again from the B4 backend. */
type InstanceBackupOptions = {password_rules: Array<{code: string; value?: number | null}>};

/** The archive's rules while A's minimum is eight: A's five, at least twelve characters (B4 §2). */
const OPTIONS_ANSWER: InstanceBackupOptions = {
    password_rules: [
        {code: 'min_length', value: 12},
        {code: 'uppercase', value: null},
        {code: 'lowercase', value: null},
        {code: 'digit', value: null},
        {code: 'special', value: null},
    ],
};

interface SecureRequests {
    startInstanceBackup: (password?: string) => Promise<InstanceBackupJob>;
    getInstanceBackupOptions: () => Promise<InstanceBackupOptions>;
    startRestoreCheck: (uploadId: string, password?: string) => Promise<RestoreStage>;
    isEnvelopeFile: (file: Blob) => Promise<boolean>;
}

/** One function of backupApi.ts as B4 makes it, or a failure that names it: each case fails on its own until it exists. */
function secure<K extends keyof SecureRequests>(name: K): SecureRequests[K] {
    const fn = (backupApiModule as unknown as Partial<SecureRequests>)[name];
    expect(typeof fn, `backupApi.ts exports no ${name}() (B4 §7)`).toBe('function');
    return fn as SecureRequests[K];
}

/** What a request carried on the wire: its JSON body parsed, or undefined when it had none. */
function wireBody(request: InternalAxiosRequestConfig): unknown {
    return request.data === undefined ? undefined : JSON.parse(String(request.data));
}

describe('B4 — the requests of a secure backup and of an envelope', () => {
    beforeEach(() => {
        for (const fn of Object.values(zodios)) fn.mockReset();
    });

    it.each<[string, () => Promise<unknown>]>([
        ['startInstanceBackup()', () => secure('startInstanceBackup')()],
        ['startInstanceBackup(undefined)', () => secure('startInstanceBackup')(undefined)],
    ])('%s: a clear backup, the request of before — no body, no parameter (green today: the guard)', async (_case, call) => {
        zodios[START].mockResolvedValue(job());

        await call();

        expect(zodios[START]).toHaveBeenCalledTimes(1);
        const [body, config] = argumentsOf(START);
        expect(body, 'a clear backup sends no password').toBeNull();
        expect(config).toBeUndefined();
    });

    it('startInstanceBackup(password): the body {password}, nothing else, and the job the server answers handed back', async () => {
        const answer = job({phase: 'preparing'});
        zodios[START].mockResolvedValue(answer);

        await expect(secure('startInstanceBackup')(PASSWORD)).resolves.toBe(answer);

        expect(zodios[START]).toHaveBeenCalledTimes(1);
        const [body, config] = argumentsOf(START);
        expect(body, 'the body of POST /backup/instance').toStrictEqual({password: PASSWORD});
        expect(config).toBeUndefined();
    });

    it('getInstanceBackupOptions() reads the options with no parameter, and hands the answer back untouched', async () => {
        zodios[OPTIONS].mockResolvedValue(OPTIONS_ANSWER);

        await expect(secure('getInstanceBackupOptions')()).resolves.toBe(OPTIONS_ANSWER);

        expect(zodios[OPTIONS]).toHaveBeenCalledTimes(1);
        expect(
            argumentsOf(OPTIONS).filter((argument) => argument !== undefined),
            'the options take no parameter',
        ).toEqual([]);
    });

    it('startRestoreCheck(uploadId, password): the body {upload_id, password}', async () => {
        zodios[STAGE].mockResolvedValue(runningStage());

        await secure('startRestoreCheck')(UPLOAD_ID, PASSWORD);

        expect(zodios[STAGE]).toHaveBeenCalledTimes(1);
        expect(argumentsOf(STAGE)[0], 'the body of POST /restore/stage').toStrictEqual({upload_id: UPLOAD_ID, password: PASSWORD});
    });

    it('startRestoreCheck(uploadId): {upload_id} alone on the wire, as today (green today: the guard)', async () => {
        zodios[STAGE].mockResolvedValue(runningStage());

        await secure('startRestoreCheck')(UPLOAD_ID);

        const body = argumentsOf(STAGE)[0];
        expect(JSON.parse(JSON.stringify(body)), 'what JSON sends of the body').toStrictEqual({upload_id: UPLOAD_ID});
    });

    it.each<[string, Alias, string, () => Promise<unknown>]>([
        ['startInstanceBackup(password), refused as password_too_weak', START, 'password_too_weak', () => secure('startInstanceBackup')(PASSWORD)],
        ['getInstanceBackupOptions(), refused', OPTIONS, 'backup_busy', () => secure('getInstanceBackupOptions')()],
        ['startRestoreCheck(uploadId, password), refused as wrong_password', STAGE, 'wrong_password', () => secure('startRestoreCheck')(UPLOAD_ID, PASSWORD)],
    ])('%s: the refusal goes through untouched, its code readable', async (_case, alias, code, call) => {
        const refused = refusal(400, code);
        zodios[alias].mockRejectedValue(refused);

        await expect(call()).rejects.toBe(refused);
        expect(backupErrorCode(refused)).toBe(code);
    });
});

describe('B4 — the same requests, replayed on the generated client', () => {
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

    it('startInstanceBackup(password): POST /api/v1/backup/instance, the JSON body {password}', async () => {
        zodios[START].mockResolvedValue(job());
        await secure('startInstanceBackup')(PASSWORD);
        const passed = argumentsOf(START);

        const {client, requests} = recordingClient(job());
        await client[START](...passed);

        expect(requests.map((request) => ({method: request.method, url: request.url}))).toEqual([{method: 'post', url: '/api/v1/backup/instance'}]);
        expect(requests[0].data, 'the request carries no body: the password never left').toBeDefined();
        expect(wireBody(requests[0])).toStrictEqual({password: PASSWORD});
    });

    it('getInstanceBackupOptions: GET /api/v1/backup/instance/options', async () => {
        zodios[OPTIONS].mockResolvedValue(OPTIONS_ANSWER);
        await secure('getInstanceBackupOptions')();
        const passed = argumentsOf(OPTIONS);

        const {client, requests} = recordingClient(OPTIONS_ANSWER);
        expect(typeof client[OPTIONS], `the generated client has no ${OPTIONS}: generate it again from the B4 backend (dev.py api sync)`).toBe('function');
        await client[OPTIONS](...passed);

        expect(requests.map((request) => ({method: request.method, url: request.url}))).toEqual([{method: 'get', url: '/api/v1/backup/instance/options'}]);
    });

    it('startRestoreCheck(uploadId, password): POST /api/v1/backup/restore/stage, the JSON body {upload_id, password}', async () => {
        zodios[STAGE].mockResolvedValue(runningStage());
        await secure('startRestoreCheck')(UPLOAD_ID, PASSWORD);
        const passed = argumentsOf(STAGE);

        const {client, requests} = recordingClient(runningStage());
        await client[STAGE](...passed);

        expect(requests.map((request) => ({method: request.method, url: request.url}))).toEqual([{method: 'post', url: '/api/v1/backup/restore/stage'}]);
        expect(wireBody(requests[0])).toStrictEqual({upload_id: UPLOAD_ID, password: PASSWORD});
    });
});

describe('B4 — isEnvelopeFile: the first four bytes are LFBK', () => {
    const bytes = (...values: number[]) => new Uint8Array(values);
    /** The head of an envelope (B4 §1): LFBK, version 1, scrypt, log2(n) 15, r 8, p 1. */
    const ENVELOPE_HEAD = bytes(0x4c, 0x46, 0x42, 0x4b, 0x01, 0x01, 0x0f, 0x08, 0x01);
    /** The head of a zip: PK\x03\x04, then its version. */
    const ZIP_HEAD = bytes(0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0x08, 0x00);

    it.each<[string, () => Blob, boolean]>([
        ['an envelope: LFBK, then its header', () => new File([ENVELOPE_HEAD], 'librefolio-backup-20261016-230000.lfbk'), true],
        ['exactly the four bytes LFBK', () => new File([bytes(0x4c, 0x46, 0x42, 0x4b)], 'four.lfbk'), true],
        ['a Blob, not a File, that starts with LFBK', () => new Blob([ENVELOPE_HEAD]), true],
        ['an envelope named and typed as a zip: the bytes decide', () => new File([ENVELOPE_HEAD], 'backup.zip', {type: 'application/zip'}), true],
        ['a zip, PK\\x03\\x04', () => new File([ZIP_HEAD], 'librefolio-backup-20261015-120000.zip', {type: 'application/zip'}), false],
        ['a zip named .lfbk: the bytes decide, not the name', () => new File([ZIP_HEAD], 'renamed.lfbk'), false],
        ['an empty file', () => new File([], 'empty.lfbk'), false],
        ['three bytes, LFB', () => new File([bytes(0x4c, 0x46, 0x42)], 'short.lfbk'), false],
        ['lfbk in lower case', () => new File([bytes(0x6c, 0x66, 0x62, 0x6b, 0x01)], 'lower.lfbk'), false],
        ['LFBK one byte in', () => new File([bytes(0x00, 0x4c, 0x46, 0x42, 0x4b)], 'shifted.lfbk'), false],
    ])('%s → %s', async (_case, make, expected) => {
        await expect(secure('isEnvelopeFile')(make())).resolves.toBe(expected);
    });

    it('reads the head of the file only: an archive whose whole content may not be read is still told apart', async () => {
        const content = new Uint8Array(64 * 1024);
        content.set(ENVELOPE_HEAD);
        const wholeRead = () => Promise.reject(new Error('isEnvelopeFile read the whole archive into the page: only its first four bytes decide'));
        /** An archive that refuses to be read whole; a slice of it is an ordinary Blob of those bytes. */
        class WholeReadRefused extends Blob {
            arrayBuffer() {
                return wholeRead();
            }
            bytes() {
                return wholeRead();
            }
            text() {
                return wholeRead();
            }
            slice(start?: number, end?: number, contentType?: string): Blob {
                return new Blob([content]).slice(start, end, contentType);
            }
        }

        await expect(secure('isEnvelopeFile')(new WholeReadRefused([content]))).resolves.toBe(true);
    });
});

// =====================================================================================================================
// B-15 + B-8 — a proxy's 413 on the upload; the running job a backup_busy names (written red first)
// =====================================================================================================================

/*
 * The contract under test (the B-15 + B-8 contract):
 *   - `uploadFailureCode(error)`, what to tell about a failed upload of an archive: what `backupFailureCode` tells — the
 *     refusal's `detail.code` whatever the status, `network` for an AxiosError that got no answer, `unexpected`
 *     otherwise —, except that an AxiosError answered 413 with no LibreFolio code is `proxy_too_large`: the page of a
 *     proxy in front of LibreFolio (nginx's `client_max_body_size`, Fly, a CDN), an empty body, JSON without
 *     `detail.code`. LibreFolio's own 413 carries `backup_too_large` (with `limit_mb`), and keeps it. The upload is the
 *     one request read this way: `backupFailureCode` itself is unchanged (B-15);
 *   - `backupBusyJob(error)`: `{jobId, origin}` from a `backup_busy` refusal whose detail names the running job —
 *     `job_id` 32 lowercase hex digits, `origin` a string —; `null` for anything else: the refusal of before
 *     (`{code, message}`), another code, an id that is not 32 lowercase hex digits, no id, no origin, no answer (B-8).
 *     The origin is handed over as named — `ui`, `cli` or `panel` —: which one a tab follows is the controller's
 *     business (backupJob.test.ts).
 *
 * Where the contract is silent, the choices of this file, each one place to change: «no LibreFolio code» is what
 * `backupErrorCode` reads as none, an empty code included; an error axios did not raise is neither `proxy_too_large`
 * nor a busy job, as it carries no code for `backupErrorCode`; the job is read inside `detail`, beside the code, never
 * elsewhere in the body; a `job_id` or an `origin` that is null or not a string names no job.
 *
 * Red today: neither function exists. Both are reached through `refusalReader()`, so each case fails on its own and
 * names the missing export, and the type check does not wait for them. Green today, and to stay so: `backupFailureCode`
 * still reads a 413 without a code as `unexpected`.
 */

/** The two readers of a refusal B-15 and B-8 add to backupApi.ts. */
interface RefusalReaders {
    uploadFailureCode: (error: unknown) => string;
    backupBusyJob: (error: unknown) => {jobId: string; origin: string} | null;
}

/** One reader of backupApi.ts as B-15 or B-8 makes it, or a failure that names it: each case fails on its own until it exists. */
function refusalReader<K extends keyof RefusalReaders>(name: K): RefusalReaders[K] {
    const fn = (backupApiModule as unknown as Partial<RefusalReaders>)[name];
    expect(typeof fn, `backupApi.ts exports no ${name}() (B-15 + B-8 contract)`).toBe('function');
    return fn as RefusalReaders[K];
}

/** What nginx answers an upload over its `client_max_body_size`: its own HTML page, nothing of LibreFolio's. */
const NGINX_413 = '<html>\r\n<head><title>413 Request Entity Too Large</title></head>\r\n<body>\r\n<center><h1>413 Request Entity Too Large</h1></center>\r\n<hr><center>nginx</center>\r\n</body>\r\n</html>\r\n';

/** LibreFolio's own 413 on the upload: `backup_too_large`, and its limit in megabytes. */
const LIBREFOLIO_413 = {detail: {code: 'backup_too_large', message: 'refused: backup_too_large', limit_mb: 250}};

describe('B-15 — uploadFailureCode: a 413 without a LibreFolio code was refused by a proxy', () => {
    it.each<[string, string, unknown]>([
        // A proxy refused the archive.
        ["a 413 with nginx's page", 'proxy_too_large', answered(413, NGINX_413)],
        ['a 413 with an empty body', 'proxy_too_large', answered(413, '')],
        ['a 413 with no body at all', 'proxy_too_large', answered(413, undefined)],
        ['a 413 with a null body', 'proxy_too_large', answered(413, null)],
        ['a 413 with JSON that has no detail (an API gateway)', 'proxy_too_large', answered(413, {message: 'Request Too Long'})],
        ['a 413 whose detail is a string', 'proxy_too_large', answered(413, {detail: 'Request Entity Too Large'})],
        ['a 413 whose detail has no code', 'proxy_too_large', answered(413, {detail: {message: 'Request Entity Too Large'}})],
        ['a 413 with an empty code', 'proxy_too_large', refusal(413, '')],
        ["a 413 with nginx's page, raised by axios itself", 'proxy_too_large', realAxiosError(413, NGINX_413)],
        // LibreFolio's own 413, and every other answer: as backupFailureCode.
        ["LibreFolio's own 413: backup_too_large, kept", 'backup_too_large', answered(413, LIBREFOLIO_413)],
        ["LibreFolio's own 413, raised by axios itself: backup_too_large, kept", 'backup_too_large', realAxiosError(413, LIBREFOLIO_413)],
        ['a 413 with any other code: that code', 'backup_upload_incomplete', refusal(413, 'backup_upload_incomplete')],
        ['another status with a code: the code', 'backup_no_space', refusal(507, 'backup_no_space')],
        ['a proxy page of another status (502): unexpected', 'unexpected', answered(502, '<html><body>Bad Gateway</body></html>')],
        ['another status without a code (500): unexpected', 'unexpected', answered(500, {detail: 'Internal Server Error'})],
        ['another status with an empty body (400): unexpected', 'unexpected', answered(400, '')],
        ['no answer (a proxy that drops the connection): network', 'network', noAnswer()],
        ['a timeout: network', 'network', noAnswer('ECONNABORTED')],
        ['no answer, raised by axios itself: network', 'network', realAxiosError(null)],
        ['a plain Error: unexpected', 'unexpected', new Error('boom')],
        ['an object shaped like a 413 that axios did not raise: unexpected', 'unexpected', {response: {status: 413, data: NGINX_413}}],
        ['null: unexpected', 'unexpected', null],
    ])('%s → %s', (_case, expected, error) => {
        expect(refusalReader('uploadFailureCode')(error)).toBe(expected);
    });

    it.each<[string, unknown]>([
        ["nginx's page", answered(413, NGINX_413)],
        ['an empty body', answered(413, '')],
        ['JSON without detail.code', answered(413, {detail: 'Request Entity Too Large'})],
    ])('backupFailureCode, the reader of every request but the upload, still reads a 413 with %s as unexpected (green today: the guard)', (_case, error) => {
        expect(backupFailureCode(error)).toBe('unexpected');
    });
});

/** The 409 of a start while a backup runs: `detail: {code: 'backup_busy', message}`, and the running job when the caller may read it (B-8). */
function busy(job: Record<string, unknown> = {}) {
    return answered(409, {detail: {code: 'backup_busy', message: 'refused: backup_busy', ...job}});
}

describe('B-8 — backupBusyJob: the running job a backup_busy refusal names', () => {
    it.each<[string, unknown, {jobId: string; origin: string}]>([
        ['started from a Backup tab (ui)', busy({job_id: JOB_ID, origin: 'ui'}), {jobId: JOB_ID, origin: 'ui'}],
        ['started from the command line (cli)', busy({job_id: JOB_ID, origin: 'cli'}), {jobId: JOB_ID, origin: 'cli'}],
        ['started from the hosting panel (panel)', busy({job_id: JOB_ID, origin: 'panel'}), {jobId: JOB_ID, origin: 'panel'}],
        ['started from a Backup tab, the refusal raised by axios itself', realAxiosError(409, {detail: {code: 'backup_busy', message: 'refused', job_id: JOB_ID, origin: 'ui'}}), {jobId: JOB_ID, origin: 'ui'}],
    ])('a refusal naming a job %s → {jobId, origin}, as it names them', (_case, error, expected) => {
        expect(refusalReader('backupBusyJob')(error)).toEqual(expected);
    });

    it.each<[string, unknown]>([
        ['the refusal of before: {code, message}, no job', busy()],
        ['another code naming a job', answered(409, {detail: {code: 'backup_job_running', message: 'refused: backup_job_running', job_id: JOB_ID, origin: 'ui'}})],
        ['a job id in upper case', busy({job_id: JOB_ID.toUpperCase(), origin: 'ui'})],
        ['a job id of 31 digits', busy({job_id: JOB_ID.slice(1), origin: 'ui'})],
        ['a job id of 33 digits', busy({job_id: `${JOB_ID}a`, origin: 'ui'})],
        ['a job id that is not hex', busy({job_id: 'not-a-backup-job-id-at-all-00000', origin: 'ui'})],
        ['a path around a valid id', busy({job_id: `../${JOB_ID}`, origin: 'ui'})],
        ['a valid id and a newline', busy({job_id: `${JOB_ID}\n`, origin: 'ui'})],
        ['an empty job id', busy({job_id: '', origin: 'ui'})],
        ['a job id that is a number', busy({job_id: 1234, origin: 'ui'})],
        ['a null job id', busy({job_id: null, origin: 'ui'})],
        ['no job id', busy({origin: 'ui'})],
        ['no origin', busy({job_id: JOB_ID})],
        ['a null origin', busy({job_id: JOB_ID, origin: null})],
        ['an origin that is not a string', busy({job_id: JOB_ID, origin: 1})],
        ['the job named outside detail', answered(409, {detail: {code: 'backup_busy', message: 'refused: backup_busy'}, job_id: JOB_ID, origin: 'ui'})],
        ['no answer', noAnswer()],
        ['no answer, raised by axios itself', realAxiosError(null)],
        ['an object shaped like a busy refusal that axios did not raise', {response: {status: 409, data: {detail: {code: 'backup_busy', message: 'refused', job_id: JOB_ID, origin: 'ui'}}}}],
        ['a plain Error', new Error('boom')],
        ['null', null],
        ['undefined', undefined],
    ])('%s → null', (_case, error) => {
        expect(refusalReader('backupBusyJob')(error)).toBeNull();
    });
});
