/**
 * pluginSettingsApi — the seam of the plugin settings interface on the generated client (workstream X, lot CP11b;
 * backend `api/v1/plugin_settings.py`, plan 03 §4.4).
 *
 * The contract under test:
 *   - `fieldOf` and `entryOf` narrow what the server answers into what the components trust: the generated type of an
 *     optional field is wider than its runtime schema, so a value of the wrong shape is dropped to its default, never
 *     carried — a type, a source or a family it does not know reads as `string`, `none`, `asset` (`asset`, `fx` and `brim`
 *     are the families it knows: the import sources, W-BS, keep theirs); a scope other than
 *     `system` as `user`; a flag that is not `true` as false; a key text that is empty or not text as null; a bound
 *     that is not a finite number as null; a label missing as the key (a name missing as the code); a problem that is not
 *     one of its three words, as text, as none (a list included, which the generated type admits); options and fields
 *     that are not a list as none. A secret never carries a `value` nor a `default`, whatever the answer held. A
 *     plugin's icon (`icon_url`), a remote URL or a path of this instance, is kept as it is; missing, empty or not
 *     text, it is null;
 *   - `fetchPluginSettings(filter)` asks `GET /settings/plugins` once, through its generated alias, with the filter
 *     as queries (`family`, `plugin_code`) and no query for what the filter leaves out, and answers each plugin
 *     narrowed; `fetchPluginEntry(family, code)` asks for that one plugin and answers its entry, or null when the
 *     answer holds none for that family and code. A refusal reaches the caller as the client raised it;
 *   - `savePluginSettings(items)` patches `/settings/plugins/bulk` once with `{items}` and never throws: `saved`;
 *     `conflict` on a 409; `keyUnavailable` on a 503; `refused` on a 422 whose body is `{detail: {results: [...]}}`,
 *     each result narrowed to `{field_key, success, error_code}` (the server's message dropped); `failed` for
 *     anything else — a 422 without a list of results, any other status, a request that reached no server, anything
 *     thrown that is neither an `AxiosError` nor an `ApiError`. The status is read from both carriers;
 *   - through the real client, only the transport faked: what is sent (method, path, queries, body), what a 200 comes
 *     back as through the generated schema (an icon included: the schema keeps only the keys it declares), and what
 *     each refusal comes back as.
 *
 * Mocks: the two aliases are spied on the real generated client (`vi.spyOn`, restored after each test) — the `$lib/api`
 * boundary, as in `emailApi.test.ts` — which also proves they exist on it; `ApiError` is the real class
 * `savePluginSettings` tests with `instanceof`. Axios errors are built with axios's own `AxiosError`. The last block
 * replaces `axiosInstance.defaults.adapter` and puts it back after each test.
 *
 * Node environment: nothing here renders.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {AxiosError, AxiosHeaders, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {ApiError, axiosInstance, zodiosApi} from '$lib/api';
import {entryOf, fetchPluginEntry, fetchPluginSettings, fieldOf, savePluginSettings, type PluginSettingsEntry, type PluginSettingWriteItem, type SaveOutcome, type SettingField} from './pluginSettingsApi';

/** What `GET /settings/plugins` answers, as the generated client types it. */
type CatalogAnswer = Awaited<ReturnType<typeof zodiosApi.get_plugin_settings_api_v1_settings_plugins_get>>;

const readAlias = () => vi.spyOn(zodiosApi, 'get_plugin_settings_api_v1_settings_plugins_get');
const writeAlias = () => vi.spyOn(zodiosApi, 'update_plugin_settings_api_v1_settings_plugins_bulk_patch');

/** An answer of the wrong shape, handed to the alias as the client would hand it over. */
const answered = (value: unknown) => value as CatalogAnswer;
/** What the write alias resolves with, as the generated client types it. */
const writeAnswered = (value: unknown) => value as Awaited<ReturnType<typeof zodiosApi.update_plugin_settings_api_v1_settings_plugins_bulk_patch>>;

// --- Fixtures --------------------------------------------------------------------------------------------------------

/** A select field as the server sends it (`PluginSettingFieldRead`), every key present and well formed: narrowing keeps it as it is. */
const CURRENCY: SettingField = {
    key: 'preferred_currency',
    type: 'select',
    scope: 'user',
    secret: false,
    required: false,
    label: 'Preferred currency',
    description: 'Which currency rows a search keeps',
    label_key: 'pluginSettings.asset.justetf.label.preferred_currency',
    description_key: 'pluginSettings.asset.justetf.description.preferred_currency',
    options: [
        {value: 'all', label: 'All currencies', label_key: 'pluginSettings.asset.justetf.option.preferred_currency.all'},
        {value: 'fund', label: 'The fund’s own currency', label_key: null},
    ],
    min_length: null,
    max_length: null,
    minimum: null,
    maximum: null,
    default: 'all',
    value: 'fund',
    is_set: true,
    source: 'db',
    locked: false,
    env_variable: null,
    editable: true,
    problem: null,
    updated_at: '2026-10-15T10:00:00Z',
};

/** A secret as the server sends it: no `value`, no `default`. */
const RAW_API_KEY: Omit<SettingField, 'value' | 'default'> = {
    key: 'api_key',
    type: 'string',
    scope: 'system',
    secret: true,
    required: true,
    label: 'API key',
    description: '',
    label_key: null,
    description_key: null,
    options: [],
    min_length: 8,
    max_length: null,
    minimum: null,
    maximum: null,
    is_set: true,
    source: 'db',
    locked: false,
    env_variable: null,
    editable: true,
    problem: null,
    updated_at: '2026-10-14T09:30:00Z',
};

/** The same secret narrowed: `value` and `default` present, and null. */
const API_KEY: SettingField = {...RAW_API_KEY, value: null, default: null};

/** What a secret's value must never become: carried anywhere after the narrowing. */
const LEAKED_SECRET = 'sk-live-5f3a9c0d1e2b';

const JUSTETF: PluginSettingsEntry = {family: 'asset', plugin_code: 'justetf', plugin_name: 'justETF', icon_url: null, configured: true, fields: [CURRENCY]};

/** Icons a plugin may publish: a remote URL (a reserved domain, which never resolves) and a path of this instance. */
const REMOTE_ICON = 'https://icons.example/justetf.png?v2';
const INSTANCE_ICON = '/api/v1/uploads/plugin/asset/cssscraper.png';

/** Every key of a field at its default: what anything that is not a field narrows to. */
const DEFAULT_FIELD: SettingField = {
    key: '',
    type: 'string',
    scope: 'user',
    secret: false,
    required: false,
    label: '',
    description: '',
    label_key: null,
    description_key: null,
    options: [],
    min_length: null,
    max_length: null,
    minimum: null,
    maximum: null,
    default: null,
    value: null,
    is_set: false,
    source: 'none',
    locked: false,
    env_variable: null,
    editable: false,
    problem: null,
    updated_at: null,
};

const ITEMS: PluginSettingWriteItem[] = [
    {family: 'asset', plugin_code: 'mockprov', field_key: 'api_key', scope: 'system', secret_value: LEAKED_SECRET},
    {family: 'asset', plugin_code: 'mockprov', field_key: 'region', scope: 'user', value: 'us'},
    {family: 'asset', plugin_code: 'mockprov', field_key: 'nickname', scope: 'user', clear: true},
];

/** `detail.results` of a refused write as the server words it (`PluginSettingWriteResult`): every item and its outcome. */
const RESULTS_ANSWERED = [
    {family: 'asset', plugin_code: 'mockprov', field_key: 'api_key', scope: 'system', success: false, error_code: 'INVALID_VALUE', message: 'The value is too short'},
    {family: 'asset', plugin_code: 'mockprov', field_key: 'region', scope: 'user', success: true, error_code: null, message: null},
];
/** The same results as `savePluginSettings` hands them over. */
const RESULTS_READ = [
    {field_key: 'api_key', success: false, error_code: 'INVALID_VALUE'},
    {field_key: 'region', success: true, error_code: null},
];

/** A successful write as the server answers it (`PluginSettingsWriteResponse`). */
const WRITTEN = {results: [{family: 'asset', plugin_code: 'mockprov', field_key: 'region', scope: 'user', success: true, error_code: null, message: null}], success_count: 1};

/** The config axios attaches to an error raised outside a request. */
const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** What axios rejects with when the server answers `status` (lib/core/settle.js): an AxiosError carrying the response. */
function axiosRefusal(status: number, data: unknown, config: InternalAxiosRequestConfig = REQUEST): AxiosError {
    const response: AxiosResponse = {status, statusText: '', headers: {'content-type': 'application/json'}, config, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, config, {}, response);
}

/** A request that reached no server: axios's own error, without a response. */
function networkError(config: InternalAxiosRequestConfig = REQUEST): AxiosError {
    return new AxiosError('Network Error', AxiosError.ERR_NETWORK, config, {});
}

afterEach(() => {
    vi.restoreAllMocks();
});

// =====================================================================================================================
describe('fieldOf — a field as the components trust it', () => {
    it('keeps a well-formed field as it is', () => {
        expect(fieldOf(structuredClone(CURRENCY))).toStrictEqual(CURRENCY);
        expect(fieldOf(structuredClone(RAW_API_KEY))).toStrictEqual(API_KEY);
    });

    it.each([null, undefined, 'a field', 42, true, [], ['api_key']])('narrows %j, which is no field, to every key at its default', (raw) => {
        expect(fieldOf(raw)).toStrictEqual(DEFAULT_FIELD);
    });

    it('never lets a secret carry a value or a default, whatever the answer held', () => {
        const narrowed = fieldOf({...RAW_API_KEY, value: LEAKED_SECRET, default: 'sk-default-0000'});

        expect(narrowed.value).toBeNull();
        expect(narrowed.default).toBeNull();
        expect(JSON.stringify(narrowed)).not.toContain(LEAKED_SECRET);
        expect(JSON.stringify(narrowed)).not.toContain('sk-default-0000');
    });

    it.each<[string, Record<string, unknown>, Partial<SettingField>]>([
        ['a type it does not know reads as a text', {type: 'date'}, {type: 'string'}],
        ['a type that is not text reads as a text', {type: 3}, {type: 'string'}],
        ['the system scope is kept', {scope: 'system'}, {scope: 'system'}],
        ['any other scope reads as the user’s', {scope: 'admin'}, {scope: 'user'}],
        ['a source it does not know reads as none', {source: 'cache'}, {source: 'none'}],
        ['a flag that is not true is false', {secret: 'true', required: 1, is_set: 'yes', locked: {}, editable: 'true'}, {secret: false, required: false, is_set: false, locked: false, editable: false}],
        ['a key text that is empty is none', {label_key: '', description_key: '', env_variable: '', updated_at: ''}, {label_key: null, description_key: null, env_variable: null, updated_at: null}],
        ['a key text that is not text is none', {label_key: 7, description_key: ['k'], env_variable: true, updated_at: 0}, {label_key: null, description_key: null, env_variable: null, updated_at: null}],
        ['a description that is not text is empty', {key: 'k', description: 42}, {description: ''}],
        ['a label missing reads as the key', {key: 'api_key'}, {key: 'api_key', label: 'api_key'}],
        ['bounds that are no finite number are none', {min_length: '3', max_length: Number.NaN, minimum: Number.POSITIVE_INFINITY, maximum: null}, {min_length: null, max_length: null, minimum: null, maximum: null}],
        ['bounds that are numbers are kept', {min_length: 3, max_length: 64, minimum: -1.5, maximum: 0}, {min_length: 3, max_length: 64, minimum: -1.5, maximum: 0}],
        ['a value and a default that are not plain are none', {value: {amount: 1}, default: [1]}, {value: null, default: null}],
        ['a value and a default that are no finite number are none', {value: Number.NaN, default: Number.NEGATIVE_INFINITY}, {value: null, default: null}],
        ['plain values are kept, a zero and a false too', {value: 0, default: false}, {value: 0, default: false}],
        ['a problem it does not know is none', {problem: 'expired'}, {problem: null}],
    ])('%s', (_label, raw, narrowed) => {
        expect(fieldOf(raw)).toMatchObject(narrowed);
    });

    it.each(['string', 'number', 'integer', 'boolean', 'select'])('keeps the type %s', (type) => {
        expect(fieldOf({type}).type).toBe(type);
    });

    it.each(['env', 'db', 'default', 'none'])('keeps the source %s', (source) => {
        expect(fieldOf({source}).source).toBe(source);
    });

    it.each(['unreadable', 'invalid_env', 'invalid_stored'])('keeps the problem %s', (problem) => {
        expect(fieldOf({problem}).problem).toBe(problem);
    });

    it.each<[string, unknown]>([
        ['a list holding one known word', ['unreadable']],
        ['a list holding several', ['invalid_env', 'unreadable']],
        ['an object', {problem: 'unreadable'}],
        ['a number', 3],
    ])('narrows a problem that is not text — %s, which the generated type admits or not — to none, never carried', (_label, problem) => {
        // The generated type of `problem` is `PluginSettingProblem | null | Array<PluginSettingProblem | null>`: the
        // components compare it with three words, so anything but one of them, as text, is no problem.
        expect(fieldOf({problem}).problem).toBeNull();
    });

    it('narrows each option: its value and label as text (the label falling back to the value), its key text or none; options that are not a list are none', () => {
        expect(fieldOf({options: {all: 'All'}}).options).toStrictEqual([]);
        expect(fieldOf({options: [null, {value: 'a'}, {value: 'b', label: 'B', label_key: 'k.b'}, {value: 3, label: 4, label_key: ''}]}).options).toStrictEqual([
            {value: '', label: '', label_key: null},
            {value: 'a', label: 'a', label_key: null},
            {value: 'b', label: 'B', label_key: 'k.b'},
            {value: '3', label: '4', label_key: null},
        ]);
    });
});

// =====================================================================================================================
describe('entryOf — a plugin’s entry as the components trust it', () => {
    it('keeps a well-formed entry as it is, its fields narrowed', () => {
        expect(entryOf(structuredClone(JUSTETF))).toStrictEqual(JUSTETF);
    });

    it.each([null, undefined, 'justetf', 42, []])('narrows %j, which is no entry, to an empty entry of the price sources', (raw) => {
        expect(entryOf(raw)).toStrictEqual({family: 'asset', plugin_code: '', plugin_name: '', icon_url: null, configured: false, fields: []});
    });

    it('keeps fx, reads a family it does not know as asset, a name missing as the code, configured only when true, fields that are not a list as none', () => {
        expect(entryOf({family: 'fx', plugin_code: 'ecb'})).toStrictEqual({family: 'fx', plugin_code: 'ecb', plugin_name: 'ecb', icon_url: null, configured: false, fields: []});
        expect(entryOf({family: 'crypto', plugin_code: 'x', plugin_name: 'X', configured: 'true', fields: {api_key: {}}})).toStrictEqual({family: 'asset', plugin_code: 'x', plugin_name: 'X', icon_url: null, configured: false, fields: []});
    });

    it('keeps brim, the family of the import sources (W-BS): it is not read as asset', () => {
        expect(entryOf({family: 'brim', plugin_code: 'broker_x', plugin_name: 'Broker X', icon_url: REMOTE_ICON, configured: true, fields: [CURRENCY]})).toStrictEqual({
            family: 'brim',
            plugin_code: 'broker_x',
            plugin_name: 'Broker X',
            icon_url: REMOTE_ICON,
            configured: true,
            fields: [CURRENCY],
        });
    });

    it('narrows every field: a secret’s value does not survive the entry', () => {
        const narrowed = entryOf({...JUSTETF, fields: [CURRENCY, {...RAW_API_KEY, value: LEAKED_SECRET}, 'garbage']});

        expect(narrowed.fields).toStrictEqual([CURRENCY, API_KEY, DEFAULT_FIELD]);
        expect(JSON.stringify(narrowed)).not.toContain(LEAKED_SECRET);
    });

    it.each<[string, string]>([
        ['a remote URL', REMOTE_ICON],
        ['a path of this instance', INSTANCE_ICON],
    ])('keeps an icon that is text as it is: %s', (_label, iconUrl) => {
        const withIcon: PluginSettingsEntry = {...JUSTETF, icon_url: iconUrl};

        expect(entryOf(structuredClone(withIcon))).toStrictEqual(withIcon);
    });

    it.each<[string, Record<string, unknown>]>([
        ['missing', {plugin_code: 'justetf'}],
        ['null', {plugin_code: 'justetf', icon_url: null}],
        ['empty text', {plugin_code: 'justetf', icon_url: ''}],
        ['a number', {plugin_code: 'justetf', icon_url: 42}],
        ['an object', {plugin_code: 'justetf', icon_url: {href: REMOTE_ICON}}],
        ['a list, which the generated type admits', {plugin_code: 'justetf', icon_url: [REMOTE_ICON]}],
    ])('narrows an icon that is %s to null: no icon, never carried as it came', (_label, raw) => {
        expect(entryOf(raw).icon_url).toBeNull();
    });
});

// =====================================================================================================================
describe('fetchPluginSettings and fetchPluginEntry — GET /settings/plugins', () => {
    it('control: both aliases exist on the generated client', () => {
        expect(typeof zodiosApi.get_plugin_settings_api_v1_settings_plugins_get).toBe('function');
        expect(typeof zodiosApi.update_plugin_settings_api_v1_settings_plugins_bulk_patch).toBe('function');
    });

    it.each<[string, Parameters<typeof fetchPluginSettings>[0], Record<string, string>]>([
        ['no filter', undefined, {}],
        ['an empty filter', {}, {}],
        ['a family', {family: 'fx'}, {family: 'fx'}],
        ['a plugin', {pluginCode: 'justetf'}, {plugin_code: 'justetf'}],
        ['a family and a plugin', {family: 'asset', pluginCode: 'justetf'}, {family: 'asset', plugin_code: 'justetf'}],
        ['an empty plugin code, which filters nothing', {family: 'asset', pluginCode: ''}, {family: 'asset'}],
    ])('asks once with %s as queries, and nothing for what the filter leaves out', async (_label, filter, queries) => {
        const alias = readAlias().mockResolvedValueOnce(answered({plugins: []}));

        await expect(fetchPluginSettings(filter)).resolves.toStrictEqual([]);

        expect(alias.mock.calls).toStrictEqual([[{queries}]]);
    });

    it('answers each plugin narrowed, in the order of the answer', async () => {
        const fx = {family: 'fx', plugin_code: 'ecb', plugin_name: 'ECB', icon_url: null, configured: false, fields: []};
        readAlias().mockResolvedValueOnce(answered({plugins: [{...JUSTETF, fields: [CURRENCY, {...RAW_API_KEY, value: LEAKED_SECRET}]}, fx]}));

        const entries = await fetchPluginSettings();

        expect(entries).toStrictEqual([{...JUSTETF, fields: [CURRENCY, API_KEY]}, fx]);
        expect(JSON.stringify(entries)).not.toContain(LEAKED_SECRET);
    });

    it('answers no plugin for an answer without a list', async () => {
        readAlias().mockResolvedValueOnce(answered({}));

        await expect(fetchPluginSettings()).resolves.toStrictEqual([]);
    });

    it('lets a refusal reach the caller as the client raised it', async () => {
        const refusal = axiosRefusal(500, {detail: 'Internal Server Error'});
        readAlias().mockRejectedValueOnce(refusal);

        await expect(fetchPluginSettings()).rejects.toBe(refusal);
    });

    it('fetchPluginEntry asks for that plugin of that family, and answers its entry', async () => {
        const alias = readAlias().mockResolvedValueOnce(answered({plugins: [JUSTETF]}));

        await expect(fetchPluginEntry('asset', 'justetf')).resolves.toStrictEqual(JUSTETF);

        expect(alias.mock.calls).toStrictEqual([[{queries: {family: 'asset', plugin_code: 'justetf'}}]]);
    });

    it('fetchPluginEntry picks the entry of that family and that code, wherever the answer lists it', async () => {
        const sameCodeOtherFamily = {...JUSTETF, family: 'fx', plugin_name: 'not this one'};
        const otherPlugin = {...JUSTETF, plugin_code: 'borsa_italiana', plugin_name: 'not this one either'};
        readAlias().mockResolvedValueOnce(answered({plugins: [sameCodeOtherFamily, otherPlugin, JUSTETF]}));

        await expect(fetchPluginEntry('asset', 'justetf')).resolves.toStrictEqual(JUSTETF);
    });

    it.each<[string, unknown]>([
        ['no plugin', {plugins: []}],
        ['only another plugin', {plugins: [{...JUSTETF, plugin_code: 'borsa_italiana'}]}],
        ['the same code under the other family', {plugins: [{...JUSTETF, family: 'fx'}]}],
    ])('fetchPluginEntry answers null when the answer holds %s', async (_label, answer) => {
        readAlias().mockResolvedValueOnce(answered(answer));

        await expect(fetchPluginEntry('asset', 'justetf')).resolves.toBeNull();
    });

    it('fetchPluginEntry lets a refusal reach the caller as the client raised it', async () => {
        const refusal = networkError();
        readAlias().mockRejectedValueOnce(refusal);

        await expect(fetchPluginEntry('asset', 'justetf')).rejects.toBe(refusal);
    });
});

// =====================================================================================================================
describe('savePluginSettings — PATCH /settings/plugins/bulk, all or nothing, never throwing', () => {
    it('sends {items} once, as given, and answers saved', async () => {
        const alias = writeAlias().mockResolvedValueOnce(writeAnswered(WRITTEN));

        await expect(savePluginSettings(ITEMS)).resolves.toStrictEqual({kind: 'saved'});

        expect(alias.mock.calls).toStrictEqual([[{items: ITEMS}]]);
    });

    describe.each([
        {carrier: 'an AxiosError', refuse: (status: number, body?: unknown): unknown => axiosRefusal(status, body)},
        {carrier: 'an ApiError', refuse: (status: number, body?: unknown): unknown => new ApiError(status, `HTTP ${status}`, body)},
    ])('a refusal carried by $carrier', ({refuse}) => {
        async function outcomeOf(status: number, body?: unknown): Promise<SaveOutcome> {
            writeAlias().mockRejectedValueOnce(refuse(status, body));
            return savePluginSettings(ITEMS);
        }

        it('409: conflict — another write changed the same settings meanwhile', async () => {
            await expect(outcomeOf(409)).resolves.toStrictEqual({kind: 'conflict'});
        });

        it('503: keyUnavailable — a secret cannot be encrypted with this instance’s key', async () => {
            await expect(outcomeOf(503, {detail: 'The instance key cannot be used'})).resolves.toStrictEqual({kind: 'keyUnavailable'});
        });

        it('422 with detail.results: refused, each result narrowed to its field, its outcome and its code — the server’s words dropped', async () => {
            const outcome = await outcomeOf(422, {detail: {results: RESULTS_ANSWERED}});

            expect(outcome).toStrictEqual({kind: 'refused', results: RESULTS_READ});
        });

        it('422: a result of the wrong shape is narrowed too, never carried as it came', async () => {
            await expect(outcomeOf(422, {detail: {results: [null, 'api_key', {field_key: 7, success: 'false', error_code: ''}, {success: true}]}})).resolves.toStrictEqual({
                kind: 'refused',
                results: [
                    {field_key: '', success: false, error_code: null},
                    {field_key: '', success: false, error_code: null},
                    {field_key: '7', success: false, error_code: null},
                    {field_key: '', success: true, error_code: null},
                ],
            });
        });

        it.each<[string, unknown]>([
            ['no body', undefined],
            ['FastAPI’s request validation (detail is a list)', {detail: [{loc: ['body', 'items', 0, 'family'], msg: "Input should be 'asset' or 'fx'", type: 'enum'}]}],
            ['a detail without results', {detail: {message: 'Refused'}}],
            ['results that are not a list', {detail: {results: {api_key: 'INVALID_VALUE'}}}],
            ['a detail that is text', {detail: 'Unprocessable Entity'}],
            ['results outside detail', {results: RESULTS_ANSWERED}],
        ])('422 with %s: failed, since nothing says which field', async (_label, body) => {
            await expect(outcomeOf(422, body)).resolves.toStrictEqual({kind: 'failed'});
        });

        it.each([400, 401, 403, 404, 423, 500, 502])('%i: failed', async (status) => {
            await expect(outcomeOf(status, {detail: 'Refused'})).resolves.toStrictEqual({kind: 'failed'});
        });
    });

    it('a request that reached no server (an AxiosError without a response): failed', async () => {
        writeAlias().mockRejectedValueOnce(networkError());

        await expect(savePluginSettings(ITEMS)).resolves.toStrictEqual({kind: 'failed'});
    });

    it('an error flagged as axios’s, as some callers build one, is read by its response too', async () => {
        writeAlias().mockRejectedValueOnce(Object.assign(new Error('Request failed with status code 409'), {isAxiosError: true, response: {status: 409, data: undefined}}));

        await expect(savePluginSettings(ITEMS)).resolves.toStrictEqual({kind: 'conflict'});
    });

    it.each<[string, unknown]>([
        ['a plain Error', new Error('boom')],
        ['a TypeError', new TypeError('items is not iterable')],
        ['a string', 'boom'],
        ['undefined', undefined],
        ['an object with a status, which is no carrier', {status: 409, data: {}}],
        ['an object shaped like an axios error, without its flag', {response: {status: 503, data: {}}}],
    ])('anything else thrown — %s —: failed, a status being read only from an AxiosError or an ApiError', async (_label, thrown) => {
        writeAlias().mockRejectedValueOnce(thrown);

        await expect(savePluginSettings(ITEMS)).resolves.toStrictEqual({kind: 'failed'});
    });
});

// =====================================================================================================================
describe('through the real client, only the transport faked: what is sent, and what each answer comes back as', () => {
    /** The requests the fake transport received. */
    const received: InternalAxiosRequestConfig[] = [];
    let realAdapter: typeof axiosInstance.defaults.adapter;

    beforeEach(() => {
        realAdapter = axiosInstance.defaults.adapter;
        received.length = 0;
    });

    afterEach(() => {
        axiosInstance.defaults.adapter = realAdapter;
    });

    /** The server answers `status` with `data`, settled as axios's own adapters settle it: a 2xx resolves, any other status rejects. */
    function serverAnswers(status: number, data: unknown): void {
        const adapter: AxiosAdapter = async (config) => {
            received.push(config);
            if (status >= 200 && status < 300) return {status, statusText: 'OK', headers: {'content-type': 'application/json'}, config, request: {}, data};
            throw axiosRefusal(status, data, config);
        };
        axiosInstance.defaults.adapter = adapter;
    }

    /** No server answers: the request fails before any response. */
    function noServer(): void {
        const adapter: AxiosAdapter = async (config) => {
            received.push(config);
            throw networkError(config);
        };
        axiosInstance.defaults.adapter = adapter;
    }

    const asked = () => received.map(({method, url}) => `${method} ${url}`);

    it('control: GET /api/v1/settings/plugins with family and plugin_code, and the answer through the generated schema, narrowed', async () => {
        serverAnswers(200, {plugins: [JUSTETF]});

        await expect(fetchPluginEntry('asset', 'justetf')).resolves.toStrictEqual(JUSTETF);

        expect(asked()).toEqual(['get /api/v1/settings/plugins']);
        expect(received[0]?.params).toEqual({family: 'asset', plugin_code: 'justetf'});
    });

    it('without a filter, no query is sent', async () => {
        serverAnswers(200, {plugins: []});

        await expect(fetchPluginSettings()).resolves.toStrictEqual([]);

        expect(asked()).toEqual(['get /api/v1/settings/plugins']);
        expect(received[0]?.params ?? {}).toEqual({});
    });

    it('a secret’s value a server put in its answer passes the generated schema, and is dropped by the narrowing', async () => {
        serverAnswers(200, {plugins: [{...JUSTETF, fields: [{...RAW_API_KEY, value: LEAKED_SECRET}]}]});

        const entry = await fetchPluginEntry('asset', 'justetf');

        expect(entry?.fields).toStrictEqual([API_KEY]);
        expect(JSON.stringify(entry)).not.toContain(LEAKED_SECRET);
    });

    it('a plugin’s icon passes the generated schema and comes back as it was sent', async () => {
        // The generated schema is a zod object, which drops every key it does not declare: a client generated without
        // the field would answer every plugin iconless, and every form would show its neutral icon, silently.
        const withIcon: PluginSettingsEntry = {...JUSTETF, icon_url: REMOTE_ICON};
        serverAnswers(200, {plugins: [withIcon]});

        await expect(fetchPluginEntry('asset', 'justetf')).resolves.toStrictEqual(withIcon);
    });

    it('the import sources’ family passes the generated client both ways: asked as a query, answered as an entry of its own (W-BS)', async () => {
        // The generated schema is a zod enum: a client generated before `brim` joined it refuses both the query and the answer.
        const importer: PluginSettingsEntry = {...JUSTETF, family: 'brim', plugin_code: 'broker_x', plugin_name: 'Broker X'};
        serverAnswers(200, {plugins: [importer]});

        await expect(fetchPluginSettings({family: 'brim'})).resolves.toStrictEqual([importer]);

        expect(received[0]?.params).toEqual({family: 'brim'});
    });

    it('PATCH /api/v1/settings/plugins/bulk carries {items} as given, and a 200 is saved', async () => {
        serverAnswers(200, WRITTEN);

        await expect(savePluginSettings(ITEMS)).resolves.toStrictEqual({kind: 'saved'});

        expect(asked()).toEqual(['patch /api/v1/settings/plugins/bulk']);
        expect(JSON.parse(String(received[0]?.data))).toEqual({items: ITEMS});
    });

    it.each<[number, SaveOutcome]>([
        [409, {kind: 'conflict'}],
        [503, {kind: 'keyUnavailable'}],
        [500, {kind: 'failed'}],
    ])('a %i comes back as its outcome', async (status, outcome) => {
        serverAnswers(status, {detail: 'Refused'});

        await expect(savePluginSettings(ITEMS)).resolves.toStrictEqual(outcome);
    });

    it('a 422 with detail.results comes back refused, with the results', async () => {
        serverAnswers(422, {detail: {results: RESULTS_ANSWERED}});

        await expect(savePluginSettings(ITEMS)).resolves.toStrictEqual({kind: 'refused', results: RESULTS_READ});
    });

    it('a 422 from the request validation (detail is a list) comes back failed', async () => {
        serverAnswers(422, {detail: [{loc: ['body', 'items'], msg: 'List should have at least 1 item', type: 'too_short'}]});

        await expect(savePluginSettings(ITEMS)).resolves.toStrictEqual({kind: 'failed'});
    });

    it('no server: failed, and the read rejects', async () => {
        noServer();

        await expect(savePluginSettings(ITEMS)).resolves.toStrictEqual({kind: 'failed'});
        await expect(fetchPluginSettings()).rejects.toBeInstanceOf(AxiosError);
        expect(asked()).toEqual(['patch /api/v1/settings/plugins/bulk', 'get /api/v1/settings/plugins']);
    });
});
