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
