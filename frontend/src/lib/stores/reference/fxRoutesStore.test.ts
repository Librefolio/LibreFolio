/**
 * fxRoutesStore — which currencies a display-currency menu may offer.
 *
 * The dashboard's display currency and the asset detail's «Convert to» list only
 * what `getConfiguredCurrencySet()` returns. A currency belongs there when the user
 * can actually convert to it, and that is true only for the two ENDPOINTS of a
 * configured pair: syncing a chain stores the composed rate of its own pair
 * (`fx.py` inserts `FxRate` on `route.base/route.quote`), while the rates of its
 * legs stay in memory. So the currency a chain passes through (GBP in
 * EUR→GBP→USD) is not convertible, and offering it lets the user pick a currency
 * whose every amount then fails to convert. It becomes convertible — and belongs
 * in the menu — only once it is itself an endpoint of a configured pair.
 *
 * Node env. `$lib/api` is mocked: the route list is the whole input, owned by each
 * case. The store keeps module-level state, so every case imports a fresh module
 * (`vi.resetModules()`) instead of trusting a reset helper to clear everything.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const {listRoutes} = vi.hoisted(() => ({listRoutes: vi.fn()}));

vi.mock('$lib/api', () => ({
    zodiosApi: {list_routes_api_v1_fx_providers_routes_get: listRoutes},
}));

type Step = {from: string; to: string; provider: string};

/** One configured route as GET /fx/providers/routes returns it (FXConversionRouteReadItem). */
function route(base: string, quote: string, chain_steps: Step[], priority = 1) {
    return {
        base,
        quote,
        priority,
        chain_steps,
        is_chain: chain_steps.length > 1,
        providers_used: [...new Set(chain_steps.map((step) => step.provider))].sort(),
    };
}

/** EUR-USD is configured, and reached through GBP: GBP is a leg, not an endpoint. */
const EUR_USD_VIA_GBP = route('EUR', 'USD', [
    {from: 'EUR', to: 'GBP', provider: 'ECB'},
    {from: 'GBP', to: 'USD', provider: 'BOE'},
]);
/** A configured pair of its own whose endpoint is the chain's intermediate. */
const GBP_JPY_DIRECT = route('GBP', 'JPY', [{from: 'GBP', to: 'JPY', provider: 'BOE'}]);
/** A MANUAL-only pair: rates are typed in by hand, the pair is still configured. */
const CHF_EUR_MANUAL = route('CHF', 'EUR', [{from: 'CHF', to: 'EUR', provider: 'MANUAL'}], 999);

/** A fresh store module, loaded once from exactly these routes. */
async function storeLoadedWith(items: unknown[]) {
    listRoutes.mockResolvedValue({items});
    const store = await import('./fxRoutesStore');
    await store.ensureFxRoutesLoaded();
    // Positive control: the sets below come from this response, not from an empty
    // fallback left behind by a load that never happened.
    expect(listRoutes).toHaveBeenCalledTimes(1);
    return store;
}

beforeEach(() => {
    vi.resetModules();
    listRoutes.mockReset();
});

describe('fxRoutesStore — getConfiguredCurrencySet() lists route endpoints only', () => {
    it('offers both endpoints of a chain route, never the currency it passes through', async () => {
        const store = await storeLoadedWith([EUR_USD_VIA_GBP]);

        expect(store.getConfiguredCurrencySet()).toEqual(new Set(['EUR', 'USD']));
        expect(store.getConfiguredCurrencySet().has('GBP')).toBe(false);
    });

    it('offers the intermediate once it is an endpoint of a configured pair of its own', async () => {
        const store = await storeLoadedWith([EUR_USD_VIA_GBP, GBP_JPY_DIRECT]);

        expect(store.getConfiguredCurrencySet()).toEqual(new Set(['EUR', 'GBP', 'JPY', 'USD']));
    });

    it('offers the endpoints of a MANUAL-only pair', async () => {
        const store = await storeLoadedWith([CHF_EUR_MANUAL]);

        expect(store.getConfiguredCurrencySet()).toEqual(new Set(['CHF', 'EUR']));
    });

    it('upper-cases lower-case codes, in currencies and slugs alike', async () => {
        const store = await storeLoadedWith([route('eur', 'usd', [{from: 'eur', to: 'usd', provider: 'ECB'}])]);

        expect(store.getConfiguredCurrencySet()).toEqual(new Set(['EUR', 'USD']));
        expect(store.getConfiguredPairSlugs()).toEqual(new Set(['EUR-USD']));
    });
});

describe('fxRoutesStore — getConfiguredPairSlugs() lists configured pairs only', () => {
    it('returns the alphabetical slug of each configured pair and none for the legs of a chain', async () => {
        const store = await storeLoadedWith([EUR_USD_VIA_GBP, GBP_JPY_DIRECT]);

        expect(store.getConfiguredPairSlugs()).toEqual(new Set(['EUR-USD', 'GBP-JPY']));
    });
});
