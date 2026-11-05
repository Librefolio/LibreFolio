/**
 * backupApi — the space an instance uses, and its limit (lot FB-29, written red first against `B6r-fb29-interface.md` §5).
 *
 * The contract under test:
 *   - `getInstanceStorage()`: `GET /backup/instance/storage` through its generated alias
 *     `get_instance_storage_api_v1_backup_instance_storage_get`, called once with no argument, answering the route's
 *     body as it came; a refusal goes through untouched; nothing else is requested;
 *   - `saveStorageLimit(mb)`: ONE `PATCH /settings/global/bulk` whose body is
 *     `{items: [{key: 'storage_limit_mb', value: '<mb>'}]}` — one item, the value as a STRING, 0 included («no limit» is
 *     a value, not an omitted key); resolves with nothing; a refusal goes through untouched, with no second attempt;
 *   - `storageLimitSaveCode(error)`: 422 → `invalid`, 403 → `forbidden`, a 409 whose `detail.error_code` is
 *     `SETTING_LOCKED_BY_ENV` → `locked`, an AxiosError with no answer → `network`, anything else → `unexpected` — a 409
 *     with another code included (a conflict that is not the environment pinning the limit).
 *
 * `$lib/api` is mocked with the aliases these functions may reach and nothing else, so a function reaching for any
 * other alias fails on a missing function. Errors are AxiosError-shaped literals (`isAxiosError: true` is what axios
 * itself tests); the 409 is worded as `PATCH /settings/global/bulk` words it: `detail: {error_code, message, key, variable}`.
 *
 * Red today: the three functions do not exist in backupApi.ts, so each case fails on `… is not a function`.
 *
 * Node environment: nothing here touches the DOM or a rune.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const zodios = vi.hoisted(() => ({
    get_instance_storage_api_v1_backup_instance_storage_get: vi.fn(),
    list_instance_backups_api_v1_backup_instance_jobs_get: vi.fn(),
    list_global_settings_api_v1_settings_global_get: vi.fn(),
    bulk_update_global_settings_api_v1_settings_global_bulk_patch: vi.fn(),
}));
vi.mock('$lib/api', () => ({zodiosApi: zodios, schemas: {}}));

import {getInstanceStorage, saveStorageLimit, storageLimitSaveCode} from './backupApi';

const STORAGE = zodios.get_instance_storage_api_v1_backup_instance_storage_get;
const LIST = zodios.list_instance_backups_api_v1_backup_instance_jobs_get;
const SETTINGS = zodios.list_global_settings_api_v1_settings_global_get;
const BULK = zodios.bulk_update_global_settings_api_v1_settings_global_bulk_patch;

const KEY = 'storage_limit_mb';

/** The answer of the storage route, with its own numbers. */
function storageAnswer(overrides: Record<string, unknown> = {}) {
    return {
        database_bytes: 100 * 1048576,
        uploads_bytes: 50 * 1048576,
        broker_reports_bytes: 0,
        backups_bytes: 70 * 1048576,
        other_bytes: 10 * 1048576,
        data_bytes: 230 * 1048576,
        volume_total_bytes: 10 * 1073741824,
        volume_used_bytes: 6 * 1073741824,
        volume_free_bytes: 4 * 1073741824,
        limit_mb: null,
        limit_locked: false,
        ...overrides,
    };
}

/** A request the server answered with an error status: axios rejects with the response. */
function answered(status: number, data: unknown) {
    return {isAxiosError: true, name: 'AxiosError', message: `Request failed with status code ${status}`, response: {status, data}};
}

/** No answer: axios rejects with no `response`. */
function noAnswer() {
    return {isAxiosError: true, name: 'AxiosError', message: 'Network Error', code: 'ERR_NETWORK', response: undefined};
}

/** The 409 of `PATCH /settings/global/bulk` for a setting an environment variable pins. */
const lockedByEnv = () => answered(409, {detail: {error_code: 'SETTING_LOCKED_BY_ENV', message: 'storage_limit_mb is set by LIBREFOLIO_STORAGE_LIMIT_MB', key: KEY, variable: 'LIBREFOLIO_STORAGE_LIMIT_MB'}});

beforeEach(() => {
    STORAGE.mockReset();
    LIST.mockReset();
    SETTINGS.mockReset();
    BULK.mockReset();
});

describe('getInstanceStorage', () => {
    it('asks the storage route once, with no argument, and hands back its answer', async () => {
        const answer = storageAnswer({limit_mb: 1024, limit_locked: true});
        STORAGE.mockResolvedValueOnce(answer);

        const result = await getInstanceStorage();

        expect(STORAGE).toHaveBeenCalledTimes(1);
        expect(STORAGE.mock.calls[0]).toEqual([]);
        expect(result).toEqual(answer);
    });

    it('keeps the nullable fields null: an unknown volume and no limit are not 0', async () => {
        STORAGE.mockResolvedValueOnce(storageAnswer({volume_total_bytes: null, volume_used_bytes: null, volume_free_bytes: null, limit_mb: null}));

        const result = await getInstanceStorage();

        expect(result.volume_total_bytes).toBeNull();
        expect(result.volume_used_bytes).toBeNull();
        expect(result.volume_free_bytes).toBeNull();
        expect(result.limit_mb).toBeNull();
    });

    it('lets a refusal through untouched', async () => {
        const refused = answered(403, {detail: 'Admin required'});
        STORAGE.mockRejectedValueOnce(refused);

        await expect(getInstanceStorage()).rejects.toBe(refused);
    });

    it('requests nothing else', async () => {
        STORAGE.mockResolvedValueOnce(storageAnswer());

        await getInstanceStorage();

        expect(LIST).not.toHaveBeenCalled();
        expect(SETTINGS).not.toHaveBeenCalled();
        expect(BULK).not.toHaveBeenCalled();
    });
});

describe('saveStorageLimit', () => {
    it('sends ONE bulk PATCH with the one key, the value as a string', async () => {
        BULK.mockResolvedValueOnce([]);

        await saveStorageLimit(2048);

        expect(BULK).toHaveBeenCalledTimes(1);
        const body = BULK.mock.calls[0][0] as {items: Array<{key: string; value: unknown}>};
        expect(body.items).toEqual([{key: KEY, value: '2048'}]);
        expect(typeof body.items[0].value, 'the value is a string').toBe('string');
        expect(Object.keys(body), 'the body holds the items and nothing else').toEqual(['items']);
    });

    it('no limit is the string "0", not an omitted key', async () => {
        BULK.mockResolvedValueOnce([]);

        await saveStorageLimit(0);

        expect(BULK).toHaveBeenCalledTimes(1);
        const body = BULK.mock.calls[0][0] as {items: Array<{key: string; value: unknown}>};
        expect(body.items).toEqual([{key: KEY, value: '0'}]);
    });

    it('resolves with nothing, and requests nothing else', async () => {
        BULK.mockResolvedValueOnce([{key: KEY, value: '1', value_type: 'int', updated_at: null}]);

        await expect(saveStorageLimit(1)).resolves.toBeUndefined();

        expect(SETTINGS).not.toHaveBeenCalled();
        expect(STORAGE).not.toHaveBeenCalled();
    });

    it('lets a refusal through untouched, and does not send it twice: the component reads the status off it', async () => {
        const refused = lockedByEnv();
        BULK.mockRejectedValueOnce(refused);

        await expect(saveStorageLimit(512)).rejects.toBe(refused);
        expect(BULK).toHaveBeenCalledTimes(1);
    });
});

describe('storageLimitSaveCode', () => {
    it.each<[string, string, unknown]>([
        ['a 422 (a value outside 0..10485760; the detail is a string naming the key)', 'invalid', answered(422, {detail: `Invalid value for ${KEY}`})],
        ['a 422 whose detail is a list (the schema refused the body)', 'invalid', answered(422, {detail: [{loc: ['body', 'items'], msg: 'invalid', type: 'value_error'}]})],
        ['a 403 (not an administrator)', 'forbidden', answered(403, {detail: 'Admin required'})],
        ['a 409 SETTING_LOCKED_BY_ENV (LIBREFOLIO_STORAGE_LIMIT_MB pins the limit)', 'locked', lockedByEnv()],
        ['a 409 SETTING_LOCKED_BY_ENV with no other field', 'locked', answered(409, {detail: {error_code: 'SETTING_LOCKED_BY_ENV'}})],
        ['no answer', 'network', noAnswer()],
        ['a 409 with another code (a conflict that is not the environment pinning the limit)', 'unexpected', answered(409, {detail: {error_code: 'SOMETHING_ELSE', message: 'conflict'}})],
        ['a 409 whose detail is a string', 'unexpected', answered(409, {detail: 'SETTING_LOCKED_BY_ENV'})],
        ['a 409 with no detail', 'unexpected', answered(409, {})],
        ['a 500', 'unexpected', answered(500, {detail: 'Internal Server Error'})],
        ['a 404', 'unexpected', answered(404, {detail: 'Not Found'})],
        ['a proxy page', 'unexpected', answered(502, '<html><body>Bad Gateway</body></html>')],
        ['a plain Error', 'unexpected', new Error('boom')],
        ['an object shaped like an answer that axios did not raise', 'unexpected', {response: {status: 409, data: {detail: {error_code: 'SETTING_LOCKED_BY_ENV'}}}}],
        ['null', 'unexpected', null],
        ['undefined', 'unexpected', undefined],
    ])('%s → %s', (_case, expected, error) => {
        expect(storageLimitSaveCode(error)).toBe(expected);
    });
});
