/**
 * pluginSettingsApi — the core call-limit fields and the call usage, as the «Calls» block reads them (project 76, U4
 * then U5).
 *
 * From U4 the server lists five core fields, `call_limit_minute` … `call_limit_month`, on every plugin that calls an
 * external service and on every group that shares credits, and a `call_usage` block on the entry that owns the count.
 * U4 filtered both out; from U5 the API layer:
 *   - exports `CALL_LIMIT_KEYS`, the five keys in window order, and `CALL_WINDOWS`, the five windows;
 *   - keeps the limit fields in `fields`, after the plugin's own (in the server's order), in window order: the form's
 *     draft, problems and write go through them as through any field;
 *   - keeps every entry, one whose only fields are the limits and one listed only for its usage block (U4b, the
 *     managed profile) included;
 *   - maps `call_usage` into the entry, its windows checked and put in window order; no block (or a null one, or one
 *     that is not a block) leaves no `call_usage` key, so an entry without usage is exactly what it was before U4.
 *
 * From U5b it also maps `reason`, the readiness check's own (`missing_fields` | `invalid_locked_setting`); any other
 * value, or none, leaves no `reason` key.
 *
 * Mocks: the read alias is spied on the real generated client (`spyOnApi`), as in `pluginSettingsApi.test.ts`; the
 * last block fakes only the transport (`axiosInstance.defaults.adapter`) to go through the generated schema.
 *
 * Node environment: nothing here renders.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {spyOnApi} from '$test/spyOnApi';
import type {AxiosAdapter, InternalAxiosRequestConfig} from 'axios';
import {axiosInstance, zodiosApi} from '$lib/api';
import * as pluginSettingsApi from './pluginSettingsApi';
import {fetchPluginEntry, fetchPluginSettings, type PluginSettingsEntry, type SettingField} from './pluginSettingsApi';

type CatalogAnswer = Awaited<ReturnType<typeof zodiosApi.get_plugin_settings_api_v1_settings_plugins_get>>;

const readAlias = () => spyOnApi(zodiosApi, 'get_plugin_settings_api_v1_settings_plugins_get');
const answered = (value: unknown) => value as CatalogAnswer;

const WINDOWS = ['minute', 'hour', 'day', 'week', 'month'] as const;
const KEYS = WINDOWS.map((window) => `call_limit_${window}`);

/** A core limit field as the server sends it (`PluginSettingFieldRead`), every key present: narrowing keeps it as it is. */
function limitField(window: (typeof WINDOWS)[number], value: number | null = null): SettingField {
    return {
        key: `call_limit_${window}`,
        type: 'integer',
        scope: 'system',
        secret: false,
        required: false,
        label: `Calls per ${window}`,
        description: 'The most calls the instance lets through in this window',
        label_key: null,
        description_key: null,
        missing_key: null,
        options: [],
        min_length: null,
        max_length: null,
        minimum: 0,
        maximum: null,
        default: null,
        value,
        is_set: value !== null,
        source: value !== null ? 'db' : 'none',
        locked: false,
        env_variable: null,
        editable: true,
        problem: null,
        updated_at: null,
    };
}

const LIMITS: SettingField[] = WINDOWS.map((window) => limitField(window, window === 'day' ? 2000 : null));

/** A plugin's own field, kept by the filter. */
const CURRENCY: SettingField = {
    ...limitField('minute'),
    key: 'preferred_currency',
    type: 'select',
    scope: 'user',
    label: 'Preferred currency',
    description: 'Which currency rows a search keeps',
    options: [{value: 'all', label: 'All currencies', label_key: null}],
    minimum: null,
    default: 'all',
    value: 'all',
    is_set: false,
    source: 'default',
};

/** A group's own field, kept by the filter. */
const TIER: SettingField = {...CURRENCY, key: 'tier', scope: 'system', label: 'Tier', options: [{value: 'free', label: 'Free', label_key: null}], default: 'free', value: 'free'};

function entry(overrides: Partial<PluginSettingsEntry>): PluginSettingsEntry {
    return {family: 'asset', plugin_code: 'x', plugin_name: 'X', icon_url: null, configured: true, fields: [], groups: [], used_by: [], name_key: null, ...overrides};
}

/** yfinance from U4: only the five core fields. */
const YFINANCE = entry({plugin_code: 'yfinance', plugin_name: 'Yahoo Finance', fields: LIMITS});
/** ECB from U4: only the five core fields. */
const ECB = entry({family: 'fx', plugin_code: 'ECB', plugin_name: 'European Central Bank', fields: LIMITS});
/** justETF from U4: its own field first, then the five. */
const JUSTETF_RAW = entry({plugin_code: 'justetf', plugin_name: 'justETF', fields: [CURRENCY, ...LIMITS]});
/** A credit-sharing group whose only fields are the limits, and one with a field of its own. */
const LIMITS_ONLY_GROUP = entry({family: 'group', plugin_code: 'coingecko', plugin_name: 'CoinGecko', fields: LIMITS, used_by: [{family: 'asset', plugin_code: 'coingecko_price', plugin_name: 'CoinGecko'}]});
const TIER_GROUP_RAW = entry({family: 'group', plugin_code: 'mock_share', plugin_name: 'Mock share', fields: [TIER, ...LIMITS]});
/** An entry that arrives with no field and no group: not the filter's business. */
const ARRIVED_EMPTY = entry({family: 'fx', plugin_code: 'ecb_legacy', plugin_name: 'ECB', configured: false});

/** The usage block the catalogue adds from U4, on the entry that owns the count. */
const USAGE = {family: 'asset', plugin_code: 'justetf', windows: WINDOWS.map((window) => ({window, count: 3, limit: window === 'day' ? 2000 : null, resets_at: '2026-11-18T00:00:00Z', full: false}))};

afterEach(() => {
    vi.restoreAllMocks();
});

describe('U5: the core call-limit fields are kept, grouped after the plugin’s own', () => {
    it('CALL_LIMIT_KEYS names the five keys, in window order; CALL_WINDOWS the five windows', () => {
        expect([...pluginSettingsApi.CALL_LIMIT_KEYS]).toStrictEqual(KEYS);
        expect([...pluginSettingsApi.CALL_WINDOWS]).toStrictEqual([...WINDOWS]);
    });

    it('an entry with only the five core fields is listed, its fields the five in window order', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [YFINANCE, JUSTETF_RAW, ECB, ARRIVED_EMPTY]}));

        const entries = await fetchPluginSettings();

        expect(entries.map((listed) => listed.plugin_code)).toStrictEqual(['yfinance', 'justetf', 'ECB', 'ecb_legacy']);
        expect(entries[0]).toStrictEqual(YFINANCE);
        expect(entries[3]).toStrictEqual(ARRIVED_EMPTY);
    });

    it('an entry with fields of its own keeps them first, then the five limits', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [JUSTETF_RAW]}));

        const [only] = await fetchPluginSettings();

        expect(only.fields.map((field) => field.key)).toStrictEqual(['preferred_currency', ...KEYS]);
        expect(only).toStrictEqual(JUSTETF_RAW);
    });

    it('limit fields wherever the server put them come out grouped at the end, in window order; the own fields keep their order', async () => {
        const shuffled = entry({plugin_code: 'justetf', plugin_name: 'justETF', fields: [LIMITS[4], CURRENCY, LIMITS[0], TIER, LIMITS[2], LIMITS[1], LIMITS[3]]});
        readAlias().mockResolvedValueOnce(answered({plugins: [shuffled]}));

        const [only] = await fetchPluginSettings();

        expect(only.fields.map((field) => field.key)).toStrictEqual(['preferred_currency', 'tier', ...KEYS]);
    });

    it('a group whose only fields are the limits is listed, as is one with a field of its own', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [LIMITS_ONLY_GROUP, TIER_GROUP_RAW]}));

        await expect(fetchPluginSettings()).resolves.toStrictEqual([LIMITS_ONLY_GROUP, TIER_GROUP_RAW]);
    });

    it('fetchPluginEntry answers a plugin whose only fields are the limits', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [YFINANCE]}));

        await expect(fetchPluginEntry('asset', 'yfinance')).resolves.toStrictEqual(YFINANCE);
    });

    it('fetchPluginEntry answers a group whose only fields are the limits', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [LIMITS_ONLY_GROUP]}));

        await expect(fetchPluginEntry('group', 'coingecko')).resolves.toStrictEqual(LIMITS_ONLY_GROUP);
    });
});

describe('U5: the call_usage block is mapped into the entry', () => {
    it('a usage block comes through, its windows as the server sent them', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [{...JUSTETF_RAW, call_usage: USAGE}]}));

        const [only] = await fetchPluginSettings();

        expect(only.call_usage).toStrictEqual(USAGE);
    });

    it('no usage block, or a null one: the entry has no call_usage key, as before U4', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [JUSTETF_RAW, {...ARRIVED_EMPTY, call_usage: null}]}));

        const entries = await fetchPluginSettings();

        expect(entries).toStrictEqual([JUSTETF_RAW, ARRIVED_EMPTY]);
        expect(entries.every((narrowed) => !('call_usage' in narrowed))).toBe(true);
    });

    it('the windows are put in window order; an unknown window, a repeated one, a negative or missing count, a missing end are left out', async () => {
        const [minute, hour, day, week, month] = USAGE.windows;
        const messy = {
            family: 'asset',
            plugin_code: 'justetf',
            windows: [month, {...day, window: 'year'}, minute, {...hour, count: -1}, week, {...week, count: 99}, {...day, resets_at: null}, {...day, count: 'many'}, null, day],
        };
        readAlias().mockResolvedValueOnce(answered({plugins: [{...JUSTETF_RAW, call_usage: messy}]}));

        const [only] = await fetchPluginSettings();

        expect(only.call_usage?.windows).toStrictEqual([minute, day, week, month]);
    });

    it('a limit that is not a non-negative integer reads as none; full is true only when the server says true', async () => {
        const [minute] = USAGE.windows;
        readAlias().mockResolvedValueOnce(answered({plugins: [{...JUSTETF_RAW, call_usage: {...USAGE, windows: [{...minute, limit: 'ten', full: 'true'}]}}]}));

        const [only] = await fetchPluginSettings();

        expect(only.call_usage?.windows).toStrictEqual([{...minute, limit: null, full: false}]);
    });

    it('a block that is no object, or has no window list, is no block', async () => {
        readAlias().mockResolvedValueOnce(
            answered({
                plugins: [
                    {...JUSTETF_RAW, call_usage: 'full'},
                    {...YFINANCE, call_usage: {family: 'asset', plugin_code: 'yfinance'}},
                ],
            }),
        );

        const entries = await fetchPluginSettings();

        expect(entries.every((narrowed) => !('call_usage' in narrowed))).toBe(true);
    });
});

describe('U5b: the readiness reason is mapped into the entry', () => {
    it('the two reasons the server knows come through', async () => {
        readAlias().mockResolvedValueOnce(
            answered({
                plugins: [
                    {...YFINANCE, configured: false, reason: 'invalid_locked_setting'},
                    {...ECB, configured: false, reason: 'missing_fields'},
                ],
            }),
        );

        const [yahoo, ecb] = await fetchPluginSettings();

        expect(yahoo.reason).toBe('invalid_locked_setting');
        expect(ecb.reason).toBe('missing_fields');
    });

    it('no reason, a null one or an unknown one: the entry has no reason key', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [YFINANCE, {...ECB, reason: null}, {...JUSTETF_RAW, reason: 'something_else'}]}));

        const entries = await fetchPluginSettings();

        expect(entries.every((narrowed) => !('reason' in narrowed))).toBe(true);
    });
});

describe('U5: an entry that exists only for its usage block is listed', () => {
    it('a managed provider whose every limit is hidden (no field, no group, a call_usage) is listed with its usage', async () => {
        const managedYahoo = {...entry({plugin_code: 'yfinance', plugin_name: 'Yahoo Finance', fields: []}), call_usage: {...USAGE, plugin_code: 'yfinance'}};
        readAlias().mockResolvedValueOnce(answered({plugins: [managedYahoo, JUSTETF_RAW, ARRIVED_EMPTY]}));

        await expect(fetchPluginSettings()).resolves.toStrictEqual([managedYahoo, JUSTETF_RAW, ARRIVED_EMPTY]);
    });

    it('a managed credit-sharing group whose every limit is hidden (no field, a call_usage, its readers) is listed too', async () => {
        const managedGroup = {...entry({family: 'group', plugin_code: 'coingecko', plugin_name: 'CoinGecko', fields: [], used_by: [{family: 'asset', plugin_code: 'coingecko_price', plugin_name: 'CoinGecko'}]}), call_usage: {...USAGE, family: 'group', plugin_code: 'coingecko'}};
        readAlias().mockResolvedValueOnce(answered({plugins: [JUSTETF_RAW, managedGroup]}));

        await expect(fetchPluginSettings()).resolves.toStrictEqual([JUSTETF_RAW, managedGroup]);
    });
});

describe('through the real client, only the transport faked: the generated schema and the mapping together', () => {
    let realAdapter: typeof axiosInstance.defaults.adapter;

    beforeEach(() => {
        realAdapter = axiosInstance.defaults.adapter;
    });

    afterEach(() => {
        axiosInstance.defaults.adapter = realAdapter;
    });

    function serverAnswers(data: unknown): void {
        const adapter: AxiosAdapter = async (config: InternalAxiosRequestConfig) => ({status: 200, statusText: 'OK', headers: {'content-type': 'application/json'}, config, request: {}, data});
        axiosInstance.defaults.adapter = adapter;
    }

    it('a catalogue with limit fields and a call_usage block parses, and comes back whole, the block included', async () => {
        serverAnswers({
            plugins: [
                {...YFINANCE, call_usage: {...USAGE, plugin_code: 'yfinance'}},
                {...JUSTETF_RAW, call_usage: USAGE},
            ],
        });

        await expect(fetchPluginSettings()).resolves.toStrictEqual([
            {...YFINANCE, call_usage: {...USAGE, plugin_code: 'yfinance'}},
            {...JUSTETF_RAW, call_usage: USAGE},
        ]);
    });
});
