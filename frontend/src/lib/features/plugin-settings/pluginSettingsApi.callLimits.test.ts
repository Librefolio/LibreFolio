/**
 * pluginSettingsApi — the core call-limit fields are filtered out until their interface lands (project 76, lot U4; U5
 * brings the limits' own controls).
 *
 * From U4 the server lists five core fields, `call_limit_minute` … `call_limit_month`, on every plugin that calls an
 * external service and on every group that shares credits — yfinance, the central banks and the others that list no
 * field today included. Until U5 the Plugins tab and «Configure» must show exactly what they show today, so the API layer:
 *   - exports `CALL_LIMIT_KEYS`, the five keys in window order;
 *   - drops, in `fetchPluginSettings` and `fetchPluginEntry`, every field whose key is one of them;
 *   - then drops an entry the filter left with no field and no group (a plugin or a group whose only fields were the
 *     limits): `fetchPluginEntry` answers null for it, as it does today for a plugin that declares nothing. An entry
 *     that arrives with no field at all is not the filter's business and stays as it is (the existing
 *     `pluginSettingsApi.test.ts` keeps such an `fx` entry, and a group entry with `fields: []`);
 *   - ignores the catalogue's new `call_usage` block (pinned: the narrowed entry has no `call_usage` key, so every
 *     existing `toStrictEqual` stays as it is); the generated schema lets it through without breaking the parse.
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
const JUSTETF = entry({plugin_code: 'justetf', plugin_name: 'justETF', fields: [CURRENCY]});
/** A credit-sharing group whose only fields are the limits, and one with a field of its own. */
const LIMITS_ONLY_GROUP = entry({family: 'group', plugin_code: 'coingecko', plugin_name: 'CoinGecko', fields: LIMITS, used_by: [{family: 'asset', plugin_code: 'coingecko_price', plugin_name: 'CoinGecko'}]});
const TIER_GROUP_RAW = entry({family: 'group', plugin_code: 'mock_share', plugin_name: 'Mock share', fields: [TIER, ...LIMITS]});
const TIER_GROUP = entry({family: 'group', plugin_code: 'mock_share', plugin_name: 'Mock share', fields: [TIER]});
/** A plugin that calls out and reads a plain group: the filter empties its fields, its group keeps it listed. */
const PLAIN_GROUP_READER_RAW = entry({plugin_code: 'reader', plugin_name: 'Reader', fields: LIMITS, groups: ['mock']});
const PLAIN_GROUP_READER = entry({plugin_code: 'reader', plugin_name: 'Reader', fields: [], groups: ['mock']});
/** An entry that arrives with no field and no group: not the filter's business. */
const ARRIVED_EMPTY = entry({family: 'fx', plugin_code: 'ecb_legacy', plugin_name: 'ECB', configured: false});

/** The usage block the catalogue adds from U4, on the entry that owns the count. */
const USAGE = {family: 'asset', plugin_code: 'justetf', windows: WINDOWS.map((window) => ({window, count: 3, limit: window === 'day' ? 2000 : null, resets_at: '2026-11-18T00:00:00Z', full: false}))};

afterEach(() => {
    vi.restoreAllMocks();
});

describe('the core call-limit fields are filtered out until U5', () => {
    it('CALL_LIMIT_KEYS names the five keys, in window order', () => {
        const exported = (pluginSettingsApi as unknown as Record<string, unknown>).CALL_LIMIT_KEYS;

        expect(exported, 'pluginSettingsApi exports no CALL_LIMIT_KEYS').toBeDefined();
        expect([...(exported as readonly string[])]).toStrictEqual(KEYS);
    });

    it('an entry with only the five core fields disappears; its neighbours stay, in order, an entry that arrived empty included', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [YFINANCE, JUSTETF_RAW, ECB, ARRIVED_EMPTY]}));

        await expect(fetchPluginSettings()).resolves.toStrictEqual([JUSTETF, ARRIVED_EMPTY]);
    });

    it('an entry with fields of its own keeps only its own, in order', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [JUSTETF_RAW]}));

        const [only] = await fetchPluginSettings();

        expect(only.fields.map((field) => field.key)).toStrictEqual(['preferred_currency']);
        expect(only).toStrictEqual(JUSTETF);
    });

    it('a limit field stands out wherever the server put it among the own fields', async () => {
        const shuffled = entry({plugin_code: 'justetf', plugin_name: 'justETF', fields: [LIMITS[1], CURRENCY, LIMITS[0], TIER, ...LIMITS.slice(2)]});
        readAlias().mockResolvedValueOnce(answered({plugins: [shuffled]}));

        const [only] = await fetchPluginSettings();

        expect(only.fields.map((field) => field.key)).toStrictEqual(['preferred_currency', 'tier']);
    });

    it('a group entry: the limits-only group is dropped, a group with a field of its own keeps it', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [LIMITS_ONLY_GROUP, TIER_GROUP_RAW]}));

        await expect(fetchPluginSettings()).resolves.toStrictEqual([TIER_GROUP]);
    });

    it('a plugin the filter empties stays listed while it reads a group', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [PLAIN_GROUP_READER_RAW, YFINANCE]}));

        await expect(fetchPluginSettings()).resolves.toStrictEqual([PLAIN_GROUP_READER]);
    });

    it('fetchPluginEntry answers null for a plugin whose only fields are the limits, as for one that declares nothing', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [YFINANCE]}));

        await expect(fetchPluginEntry('asset', 'yfinance')).resolves.toBeNull();
    });

    it('fetchPluginEntry answers null for a group whose only fields are the limits', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [LIMITS_ONLY_GROUP]}));

        await expect(fetchPluginEntry('group', 'coingecko')).resolves.toBeNull();
    });

    it('fetchPluginEntry answers a plugin with fields of its own, its limits dropped', async () => {
        readAlias().mockResolvedValueOnce(answered({plugins: [JUSTETF_RAW]}));

        await expect(fetchPluginEntry('asset', 'justetf')).resolves.toStrictEqual(JUSTETF);
    });

    it('the call_usage block is ignored: the entry narrows to exactly what it was before U4', async () => {
        readAlias().mockResolvedValueOnce(
            answered({
                plugins: [
                    {...JUSTETF_RAW, call_usage: USAGE},
                    {...ARRIVED_EMPTY, call_usage: null},
                ],
            }),
        );

        const entries = await fetchPluginSettings();

        expect(entries).toStrictEqual([JUSTETF, ARRIVED_EMPTY]);
        expect(entries.every((narrowed) => !('call_usage' in narrowed))).toBe(true);
    });
});

describe('U4b: an entry that exists only for its usage block is left out too until U5', () => {
    it('a managed provider whose every limit is hidden (no field, no group, a call_usage) disappears; one that arrived empty without usage stays', async () => {
        const managedYahoo = {...entry({plugin_code: 'yfinance', plugin_name: 'Yahoo Finance', fields: []}), call_usage: {...USAGE, plugin_code: 'yfinance'}};
        readAlias().mockResolvedValueOnce(answered({plugins: [managedYahoo, JUSTETF_RAW, ARRIVED_EMPTY]}));

        await expect(fetchPluginSettings()).resolves.toStrictEqual([JUSTETF, ARRIVED_EMPTY]);
    });

    it('a managed credit-sharing group whose every limit is hidden (no field, a call_usage, its readers) disappears too', async () => {
        const managedGroup = {...entry({family: 'group', plugin_code: 'coingecko', plugin_name: 'CoinGecko', fields: [], used_by: [{family: 'asset', plugin_code: 'coingecko_price', plugin_name: 'CoinGecko'}]}), call_usage: {...USAGE, family: 'group', plugin_code: 'coingecko'}};
        readAlias().mockResolvedValueOnce(answered({plugins: [JUSTETF_RAW, managedGroup]}));

        await expect(fetchPluginSettings()).resolves.toStrictEqual([JUSTETF]);
    });
});

describe('through the real client, only the transport faked: the generated schema and the filter together', () => {
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

    it('a catalogue with limit fields and a call_usage block parses, and comes back filtered, without the block', async () => {
        serverAnswers({
            plugins: [
                {...YFINANCE, call_usage: {...USAGE, plugin_code: 'yfinance'}},
                {...JUSTETF_RAW, call_usage: USAGE},
            ],
        });

        await expect(fetchPluginSettings()).resolves.toStrictEqual([JUSTETF]);
    });
});
