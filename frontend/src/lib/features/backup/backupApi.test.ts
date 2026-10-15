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
 * `$lib/api` is mocked with the three aliases and nothing else, so a wrapper reaching for any other alias fails on a
 * missing function instead of passing. That mock proves which alias is called with which arguments; it cannot prove
 * that those arguments make the right request. The last group does: it replays the exact arguments each wrapper
 * passed on the generated client, over an axios adapter that records the request and answers without a network, and
 * asserts the method and the path — and that the hand-written file URL is the path of the generated download route.
 *
 * Errors are AxiosError-shaped literals (`isAxiosError: true` is what axios itself tests); a few cases build a real
 * `AxiosError`, so the literals are known to read the same as what axios throws.
 *
 * Node environment: nothing here touches the DOM or a rune.
 */
import axios, {AxiosError, AxiosHeaders, type AxiosAdapter, type InternalAxiosRequestConfig} from 'axios';
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const zodios = vi.hoisted(() => ({
    start_instance_backup_api_v1_backup_instance_post: vi.fn(),
    get_instance_backup_job_api_v1_backup_instance_jobs__job_id__get: vi.fn(),
    delete_instance_backup_job_api_v1_backup_instance_jobs__job_id__delete: vi.fn(),
}));
vi.mock('$lib/api', () => ({zodiosApi: zodios, schemas: {}}));

import {backupErrorCode, backupFailureCode, deleteInstanceBackupJob, getInstanceBackupJob, instanceBackupFileUrl, startInstanceBackup, type InstanceBackupJob} from './backupApi';

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
