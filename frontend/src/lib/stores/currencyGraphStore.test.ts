/**
 * currencyGraphStore — the session cache of the FX currency graph (Vitest, no DOM).
 *
 * B-4: right after a backend restart ECB can be too slow to list its currencies. `GET /fx/providers` then answers with
 * the provider and an empty list (`currencies_unavailable`), the graph built from it has no EUR → RON edge, and the
 * store used to keep that graph for the whole session: the add-pair modal found «no path» until the page was reloaded,
 * although ECB answered a minute later. The store now caches a graph only when every provider came with its currencies.
 *
 * Only the two network sources are mocked (`zodiosApi` and the currency reference store); the graph and the path search
 * are the real ones. The store keeps module state, so each test loads a fresh copy of it.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const api = vi.hoisted(() => ({list_providers_api_v1_fx_providers_get: vi.fn()}));

vi.mock('$lib/api', () => ({zodiosApi: api}));
vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: vi.fn().mockResolvedValue(undefined),
    isCurrenciesLoaded: vi.fn(() => true),
    getAllCurrencies: vi.fn(() => [{code: 'EUR'}, {code: 'USD'}, {code: 'RON'}]),
}));

const ECB_BASE = {code: 'ECB', name: 'European Central Bank', base_currency: 'EUR', base_currencies: ['EUR']};
const ECB_SLOW = {...ECB_BASE, target_currencies: [], currencies_unavailable: true};
const ECB_OK = {...ECB_BASE, target_currencies: ['EUR', 'RON', 'USD'], currencies_unavailable: false};

async function freshStore() {
    vi.resetModules();
    return import('./currencyGraphStore');
}

beforeEach(() => {
    api.list_providers_api_v1_fx_providers_get.mockReset();
});

describe('getCurrencyGraph', () => {
    it('does not keep a graph built while a provider had no currency list: the next call asks the backend again', async () => {
        api.list_providers_api_v1_fx_providers_get.mockResolvedValueOnce([ECB_SLOW]).mockResolvedValueOnce([ECB_OK]);
        const store = await freshStore();

        expect(await store.findConversionPaths('EUR', 'RON')).toEqual([]);
        expect(store.getCachedFxProviders()[0].currencies_unavailable).toBe(true);

        const paths = await store.findConversionPaths('EUR', 'RON');
        expect(api.list_providers_api_v1_fx_providers_get).toHaveBeenCalledTimes(2);
        expect(paths).toEqual([[{from: 'EUR', to: 'RON', provider: 'ECB'}]]);
        expect(store.getCachedFxProviders()[0].currencies_unavailable).toBe(false);
    });

    it('keeps a complete graph for the session: no second request once every provider came with its list', async () => {
        api.list_providers_api_v1_fx_providers_get.mockResolvedValue([ECB_OK]);
        const store = await freshStore();

        await store.findConversionPaths('EUR', 'RON');
        await store.findConversionPaths('EUR', 'USD');
        expect(api.list_providers_api_v1_fx_providers_get).toHaveBeenCalledTimes(1);
    });

    it('treats a provider answer without the flag as complete (an older backend)', async () => {
        const {currencies_unavailable: _flag, ...noFlag} = ECB_OK;
        api.list_providers_api_v1_fx_providers_get.mockResolvedValue([noFlag]);
        const store = await freshStore();

        await store.findConversionPaths('EUR', 'RON');
        await store.findConversionPaths('EUR', 'RON');
        expect(api.list_providers_api_v1_fx_providers_get).toHaveBeenCalledTimes(1);
    });

    it('shares one request between concurrent callers even when the graph will not be kept', async () => {
        api.list_providers_api_v1_fx_providers_get.mockResolvedValue([ECB_SLOW]);
        const store = await freshStore();

        await Promise.all([store.getCurrencyGraph(), store.getCurrencyGraph()]);
        expect(api.list_providers_api_v1_fx_providers_get).toHaveBeenCalledTimes(1);
    });
});

describe("the providers' readiness (76 N3c)", () => {
    const KEYFX_OFF = {code: 'KEYFX', name: 'Keyed FX', base_currency: 'EUR', base_currencies: ['EUR'], target_currencies: ['EUR', 'USD'], currencies_unavailable: false, configured: false, missing_settings: ['api_key'], missing_reason: 'missing_fields', invalid_variables: []};
    const KEYFX_ON = {...KEYFX_OFF, configured: true, missing_settings: [], missing_reason: null};

    it("N3c-S1: the cached providers keep the list's readiness fields; a list without them reads as configured", async () => {
        api.list_providers_api_v1_fx_providers_get.mockResolvedValue([ECB_OK, KEYFX_OFF]);
        const store = await freshStore();
        await store.getCurrencyGraph();

        const [ecb, keyfx] = store.getCachedFxProviders();
        expect(keyfx).toMatchObject({configured: false, missing_settings: ['api_key'], missing_reason: 'missing_fields', invalid_variables: []});
        expect(ecb.configured).toBe(true);
    });

    it('N3c-S2: refreshFxProviderReadiness reads the list again and updates the readiness, without rebuilding the graph', async () => {
        api.list_providers_api_v1_fx_providers_get.mockResolvedValueOnce([ECB_OK, KEYFX_OFF]).mockResolvedValueOnce([ECB_OK, KEYFX_ON]);
        const store = await freshStore();
        const graph = await store.getCurrencyGraph();
        const {get} = await import('svelte/store');
        const versionBefore = get(store.fxProvidersVersion);

        await store.refreshFxProviderReadiness();

        expect(api.list_providers_api_v1_fx_providers_get).toHaveBeenCalledTimes(2);
        expect(store.getCachedFxProviders().find((p) => p.code === 'KEYFX')?.configured).toBe(true);
        expect(await store.getCurrencyGraph(), 'the same graph').toBe(graph);
        expect(get(store.fxProvidersVersion)).toBeGreaterThan(versionBefore);
    });

    it('N3c-S3: a refresh that fails leaves the cached readiness as it was, and never throws', async () => {
        api.list_providers_api_v1_fx_providers_get.mockResolvedValueOnce([ECB_OK, KEYFX_OFF]).mockRejectedValueOnce(new Error('down'));
        const store = await freshStore();
        await store.getCurrencyGraph();

        await expect(store.refreshFxProviderReadiness()).resolves.toBeUndefined();
        expect(store.getCachedFxProviders().find((p) => p.code === 'KEYFX')?.configured).toBe(false);
    });
});

describe('findConversionPaths applies the depth rule (lane 75, L20b, decision Q6)', () => {
    // EUR→RON: direct (ECB), 2 steps (EUR→USD by ECB, USD→RON by FED), 3 steps (EUR→GBP by BOE, GBP→CHF by SNB, CHF→RON by SNB2).
    const provider = (code: string, base: string, targets: string[], extra: Record<string, unknown> = {}) => ({code, name: code, base_currency: base, base_currencies: [base], target_currencies: targets, currencies_unavailable: false, ...extra});
    const ECB_RON = provider('ECB', 'EUR', ['RON', 'USD']);
    const FED_RON = provider('FED', 'USD', ['RON']);
    const THREE_STEPS = [provider('BOE', 'EUR', ['GBP']), provider('SNB', 'GBP', ['CHF']), provider('SNB2', 'CHF', ['RON'])];

    it('returns only the direct and 2-step chains when a 3-step chain also exists', async () => {
        api.list_providers_api_v1_fx_providers_get.mockResolvedValue([ECB_RON, FED_RON, ...THREE_STEPS]);
        const store = await freshStore();

        const paths = await store.findConversionPaths('EUR', 'RON');

        expect(paths.map((path) => path.length)).toEqual([1, 2]);
        expect(paths[0]).toEqual([{from: 'EUR', to: 'RON', provider: 'ECB'}]);
        expect(paths[1]).toEqual([
            {from: 'EUR', to: 'USD', provider: 'ECB'},
            {from: 'USD', to: 'RON', provider: 'FED'},
        ]);
    });

    it('keeps the signature: a third argument caps the depth', async () => {
        api.list_providers_api_v1_fx_providers_get.mockResolvedValue([ECB_RON, FED_RON, ...THREE_STEPS]);
        const store = await freshStore();

        const paths = await store.findConversionPaths('EUR', 'RON', 1);

        expect(paths).toEqual([[{from: 'EUR', to: 'RON', provider: 'ECB'}]]);
    });

    it('an unconfigured provider does not set the levels, but its routes are still returned', async () => {
        // Configured: 2 and 3 steps → depth 3. Read from the full graph the levels would be 1 and 2 → depth 2 and the
        // 3-step chain would be missing. The unconfigured KEYFX direct route is returned all the same.
        const KEYFX = provider('KEYFX', 'EUR', ['RON'], {configured: false, missing_settings: ['api_key'], missing_reason: 'missing_fields'});
        api.list_providers_api_v1_fx_providers_get.mockResolvedValue([KEYFX, provider('ECB', 'EUR', ['USD']), FED_RON, ...THREE_STEPS]);
        const store = await freshStore();

        const paths = await store.findConversionPaths('EUR', 'RON');

        expect(paths.map((path) => path.length)).toEqual([1, 2, 3]);
        expect(paths[0], 'the unconfigured provider route is returned').toEqual([{from: 'EUR', to: 'RON', provider: 'KEYFX'}]);
    });

    it('configured 3 and 4 steps give depth 4 even though the only direct route is unconfigured', async () => {
        // Read from the full graph the levels would be 1 and 3 → depth 3, and the 4-step chain would be missing.
        const KEYFX = provider('KEYFX', 'EUR', ['RON'], {configured: false});
        const FOUR_STEPS = [provider('Q1', 'EUR', ['AUD']), provider('Q2', 'AUD', ['NZD']), provider('Q3', 'NZD', ['CAD']), provider('Q4', 'CAD', ['RON'])];
        api.list_providers_api_v1_fx_providers_get.mockResolvedValue([KEYFX, ...THREE_STEPS, ...FOUR_STEPS]);
        const store = await freshStore();

        const paths = await store.findConversionPaths('EUR', 'RON');

        expect(paths.map((path) => path.length)).toEqual([1, 3, 4]);
        expect(paths[0][0].provider).toBe('KEYFX');
    });

    it('returns [] when no chain exists in either graph', async () => {
        api.list_providers_api_v1_fx_providers_get.mockResolvedValue([provider('ECB', 'EUR', ['USD'])]);
        const store = await freshStore();

        expect(await store.findConversionPaths('EUR', 'RON')).toEqual([]);
    });
});
