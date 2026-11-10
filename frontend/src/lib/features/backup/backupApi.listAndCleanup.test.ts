/**
 * backupApi — the list of the backups an instance keeps, and the settings of their clean-up (lot FB-24, written red
 * first against `B6r-fb24-frontend-interface.md` §1).
 *
 * The contract under test:
 *   - `listInstanceBackups()`: `GET /backup/instance/jobs` through its generated alias, called once with no argument,
 *     answering the `items` of the route (the order of the server kept: the newest first); a refusal goes through
 *     untouched;
 *   - `backupKind({encrypted, sealed})`: `sealed` first, whatever `encrypted` says; otherwise `password` when encrypted;
 *     otherwise `clear`;
 *   - `getCleanupSettings()`: one `GET /settings/global`, the two keys `backup_cleanup_max_mb` and
 *     `backup_cleanup_max_days` looked up by key (never by position, other keys ignored), each value read as an integer
 *     ≥ 0 — an absent key, an empty or non-numeric string, a negative number or a decimal one is 0, the rule turned off;
 *   - `saveCleanupSettings({maxMb, maxDays})`: ONE `PATCH /settings/global/bulk` whose body is
 *     `{items: [{key, value}, {key, value}]}` with both keys and the values as strings (the route is all or nothing, so
 *     two requests would leave one saved when the other is refused); nothing else is requested; a refusal goes through
 *     untouched; the order of the two items is not part of the contract;
 *   - `cleanupSaveCode(error)`: 422 → `invalid`, 403 → `forbidden`, an AxiosError with no answer → `network`, anything
 *     else → `unexpected`.
 *
 * `$lib/api` is mocked with the three aliases and nothing else, so a function reaching for any other alias fails on a
 * missing function. Errors are AxiosError-shaped literals (`isAxiosError: true` is what axios itself tests).
 *
 * Red today: none of the five functions exists in backupApi.ts, so each case fails on `… is not a function`.
 *
 * Node environment: nothing here touches the DOM or a rune.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const zodios = vi.hoisted(() => ({
    list_instance_backups_api_v1_backup_instance_jobs_get: vi.fn(),
    list_global_settings_api_v1_settings_global_get: vi.fn(),
    bulk_update_global_settings_api_v1_settings_global_bulk_patch: vi.fn(),
}));
vi.mock('$lib/api', () => ({zodiosApi: zodios, schemas: {}}));

import {backupKind, cleanupSaveCode, getCleanupSettings, listInstanceBackups, saveCleanupSettings} from './backupApi';

const LIST = zodios.list_instance_backups_api_v1_backup_instance_jobs_get;
const SETTINGS = zodios.list_global_settings_api_v1_settings_global_get;
const BULK = zodios.bulk_update_global_settings_api_v1_settings_global_bulk_patch;

const MAX_MB = 'backup_cleanup_max_mb';
const MAX_DAYS = 'backup_cleanup_max_days';

/** A global setting as `GET /settings/global` lists it. */
function setting(key: string, value: unknown) {
    return {key, value, value_type: 'int', updated_at: null};
}

/** A request the server answered with an error status: axios rejects with the response. */
function answered(status: number, data: unknown) {
    return {isAxiosError: true, name: 'AxiosError', message: `Request failed with status code ${status}`, response: {status, data}};
}

/** No answer: axios rejects with no `response`. */
function noAnswer() {
    return {isAxiosError: true, name: 'AxiosError', message: 'Network Error', code: 'ERR_NETWORK', response: undefined};
}

beforeEach(() => {
    LIST.mockReset();
    SETTINGS.mockReset();
    BULK.mockReset();
});

describe('listInstanceBackups', () => {
    it('asks the list route once, with no argument, and hands back its items in the order the server gave them', async () => {
        const items = [{job_id: 'b'.repeat(32)}, {job_id: 'a'.repeat(32)}];
        LIST.mockResolvedValueOnce({items});

        const result = await listInstanceBackups();

        expect(LIST).toHaveBeenCalledTimes(1);
        expect(LIST.mock.calls[0]).toEqual([]);
        expect(result).toEqual(items);
        expect(result.map((entry: {job_id: string}) => entry.job_id)).toEqual(['b'.repeat(32), 'a'.repeat(32)]);
    });

    it('an instance with no backup: an empty list, not undefined', async () => {
        LIST.mockResolvedValueOnce({items: []});

        expect(await listInstanceBackups()).toEqual([]);
    });

    it('lets a refusal through untouched', async () => {
        const refused = answered(403, {detail: 'Admin required'});
        LIST.mockRejectedValueOnce(refused);

        await expect(listInstanceBackups()).rejects.toBe(refused);
    });

    it('requests nothing else', async () => {
        LIST.mockResolvedValueOnce({items: []});

        await listInstanceBackups();

        expect(SETTINGS).not.toHaveBeenCalled();
        expect(BULK).not.toHaveBeenCalled();
    });
});

describe('backupKind', () => {
    it.each<[string, {encrypted: boolean; sealed: boolean}, string]>([
        ['neither encrypted nor sealed', {encrypted: false, sealed: false}, 'clear'],
        ['encrypted with a password', {encrypted: true, sealed: false}, 'password'],
        ['sealed (and encrypted, as a sealed backup is)', {encrypted: true, sealed: true}, 'sealed'],
        ['sealed whatever encrypted says', {encrypted: false, sealed: true}, 'sealed'],
    ])('%s → %s', (_case, entry, expected) => {
        expect(backupKind(entry)).toBe(expected);
    });
});

describe('getCleanupSettings', () => {
    it('reads the global settings once and finds the two keys by name, not by position', async () => {
        SETTINGS.mockResolvedValueOnce({items: [setting('session_ttl_hours', '24'), setting(MAX_DAYS, '30'), setting('default_currency', 'EUR'), setting(MAX_MB, '250')]});

        const result = await getCleanupSettings();

        expect(SETTINGS).toHaveBeenCalledTimes(1);
        expect(result).toEqual({maxMb: 250, maxDays: 30});
        expect(BULK).not.toHaveBeenCalled();
    });

    it('a rule turned off is 0', async () => {
        SETTINGS.mockResolvedValueOnce({items: [setting(MAX_MB, '0'), setting(MAX_DAYS, '0')]});

        expect(await getCleanupSettings()).toEqual({maxMb: 0, maxDays: 0});
    });

    it('a key the list does not hold is 0, the other one is read', async () => {
        SETTINGS.mockResolvedValueOnce({items: [setting(MAX_MB, '512')]});
        expect(await getCleanupSettings()).toEqual({maxMb: 512, maxDays: 0});

        SETTINGS.mockResolvedValueOnce({items: [setting(MAX_DAYS, '7')]});
        expect(await getCleanupSettings()).toEqual({maxMb: 0, maxDays: 7});
    });

    it.each<[string, {items?: unknown[]} | undefined]>([
        ['an empty list', {items: []}],
        ['an answer with no items (the schema makes them optional)', {}],
        ['no answer body', undefined],
    ])('%s: both rules are 0', async (_case, answer) => {
        SETTINGS.mockResolvedValueOnce(answer);

        expect(await getCleanupSettings()).toEqual({maxMb: 0, maxDays: 0});
    });

    it.each<[string, unknown]>([
        ['an empty string', ''],
        ['a word', 'abc'],
        ['a negative number', '-5'],
        ['a decimal number', '1.5'],
        ['a number followed by a word', '12abc'],
        ['null', null],
        ['undefined', undefined],
    ])('a value that is %s is 0, and the other key is still read', async (_case, garbage) => {
        SETTINGS.mockResolvedValueOnce({items: [setting(MAX_MB, garbage), setting(MAX_DAYS, '30')]});

        expect(await getCleanupSettings()).toEqual({maxMb: 0, maxDays: 30});
    });

    it('a refusal of the read goes through untouched', async () => {
        const failed = noAnswer();
        SETTINGS.mockRejectedValueOnce(failed);

        await expect(getCleanupSettings()).rejects.toBe(failed);
    });
});

describe('saveCleanupSettings', () => {
    it('sends ONE bulk PATCH with both keys, the values as strings', async () => {
        BULK.mockResolvedValueOnce([]);

        await saveCleanupSettings({maxMb: 250, maxDays: 30});

        expect(BULK).toHaveBeenCalledTimes(1);
        const body = BULK.mock.calls[0][0] as {items: Array<{key: string; value: unknown}>};
        expect(body.items).toHaveLength(2);
        expect(body.items).toEqual(
            expect.arrayContaining([
                {key: MAX_MB, value: '250'},
                {key: MAX_DAYS, value: '30'},
            ]),
        );
        for (const item of body.items) expect(typeof item.value, `the value of ${item.key} is a string`).toBe('string');
        expect(Object.keys(body), 'the body holds the items and nothing else').toEqual(['items']);
    });

    it('a rule turned off is the string "0", not an omitted key', async () => {
        BULK.mockResolvedValueOnce([]);

        await saveCleanupSettings({maxMb: 0, maxDays: 0});

        expect(BULK).toHaveBeenCalledTimes(1);
        const body = BULK.mock.calls[0][0] as {items: Array<{key: string; value: unknown}>};
        expect(body.items).toEqual(
            expect.arrayContaining([
                {key: MAX_MB, value: '0'},
                {key: MAX_DAYS, value: '0'},
            ]),
        );
        expect(body.items).toHaveLength(2);
    });

    it('resolves with nothing, and requests nothing else', async () => {
        BULK.mockResolvedValueOnce([setting(MAX_MB, '1'), setting(MAX_DAYS, '2')]);

        await expect(saveCleanupSettings({maxMb: 1, maxDays: 2})).resolves.toBeUndefined();

        expect(SETTINGS).not.toHaveBeenCalled();
        expect(LIST).not.toHaveBeenCalled();
    });

    it('lets a refusal through untouched: the panel reads the status off it', async () => {
        const refused = answered(422, {detail: `Invalid value for ${MAX_MB}`});
        BULK.mockRejectedValueOnce(refused);

        await expect(saveCleanupSettings({maxMb: 0, maxDays: 30})).rejects.toBe(refused);
        expect(BULK, 'a refused save is not retried as two single writes').toHaveBeenCalledTimes(1);
    });
});

describe('cleanupSaveCode', () => {
    it.each<[string, string, unknown]>([
        ['a 422 (the managed instance refuses max_mb = 0; the detail is a string naming the key)', 'invalid', answered(422, {detail: `Invalid value for ${MAX_MB}`})],
        ['a 422 whose detail is a list (the schema refused the body)', 'invalid', answered(422, {detail: [{loc: ['body', 'items'], msg: 'invalid', type: 'value_error'}]})],
        ['a 403 (not an administrator)', 'forbidden', answered(403, {detail: 'Admin required'})],
        ['no answer', 'network', noAnswer()],
        ['a 500', 'unexpected', answered(500, {detail: 'Internal Server Error'})],
        ['a 409 (a setting an environment variable pins)', 'unexpected', answered(409, {detail: 'SETTING_LOCKED_BY_ENV'})],
        ['a 404', 'unexpected', answered(404, {detail: 'Not Found'})],
        ['a proxy page', 'unexpected', answered(502, '<html><body>Bad Gateway</body></html>')],
        ['a plain Error', 'unexpected', new Error('boom')],
        ['an object shaped like an answer that axios did not raise', 'unexpected', {response: {status: 422, data: {}}}],
        ['null', 'unexpected', null],
        ['undefined', 'unexpected', undefined],
    ])('%s → %s', (_case, expected, error) => {
        expect(cleanupSaveCode(error)).toBe(expected);
    });
});
