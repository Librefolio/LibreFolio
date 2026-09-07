/**
 * loadComparisonAssetsData — unit tests
 *
 * The loader behind the "compare with another asset" overlay, used by both the
 * asset detail page and the FX pair detail page. It had **no coverage at all** —
 * zero branches out of 38 — which is not the same as being unused: it is one of
 * the two comparison features in the app that no test had ever executed.
 *
 * What makes it worth pinning is that its real output is a *side effect*. It
 * returns a map of events, but the part the chart depends on is the resolved
 * price series it writes back into `cfg.params._resolvedData` — along with the
 * icon, the type, and the flags that say a currency conversion failed. A caller
 * that took the map and ignored the mutation would draw nothing.
 *
 * The currency filter is the subtle half. When a target currency is asked for,
 * points the backend could not convert are dropped rather than drawn, because
 * mixing two currencies on one line produces a staircase that reads as a price
 * movement and is not one. Both sides of that filter are exercised here.
 *
 * `zodiosApi` is mocked: what is under test is the shape the loader makes of the
 * answer, not the HTTP call. `getCurrencyInfo` is left real — it falls back to a
 * documented placeholder when its store is cold, so the flag lookup stays honest.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import type {SignalConfig} from '$lib/charts/signals';
import {loadComparisonAssetsData, type ComparisonAssetMeta} from '../loadComparisonData';

const {queryPrices} = vi.hoisted(() => ({queryPrices: vi.fn()}));
vi.mock('$lib/api', () => ({zodiosApi: {query_prices_bulk_api_v1_assets_prices_query_post: queryPrices}}));

const RANGE = {start: '2024-01-01', end: '2024-03-31'};

/** A comparison signal pointing at one asset. Only `params` matters here. */
function compSignal(assetId: number): SignalConfig {
    return {id: `sig-${assetId}`, signalType: 'asset-comparison', params: {assetId}, style: {}} as unknown as SignalConfig;
}

function pricePoint(over: Record<string, unknown> = {}) {
    return {date: '2024-02-01', close: 10, currency: 'EUR', ...over};
}

const ASSETS: ComparisonAssetMeta[] = [
    {id: 7, display_name: 'ACME', icon_url: 'https://x/acme.png', asset_type: 'STOCK', currency: 'EUR'},
    {id: 8, display_name: 'Bare', icon_url: null, asset_type: null},
];

beforeEach(() => queryPrices.mockReset());

describe('when there is nothing to load', () => {
    it('asks the server nothing and hands back the map it was given', async () => {
        const existing = new Map<number, unknown[]>([[1, ['kept']]]);
        const out = await loadComparisonAssetsData([], RANGE, ASSETS, existing);
        expect(queryPrices).not.toHaveBeenCalled();
        // The same object, not a copy: callers rely on the no-op being free.
        expect(out).toBe(existing);
    });

    it.each([
        ['the page owns the asset', [compSignal(7)], 7],
        ['the id is not a real one', [compSignal(0)], undefined],
        ['the id is negative', [compSignal(-3)], undefined],
    ])('skips the request when %s', async (_label, signals, exclude) => {
        await loadComparisonAssetsData(signals, RANGE, ASSETS, new Map(), exclude);
        expect(queryPrices).not.toHaveBeenCalled();
    });

    it('drops an unusable id but still asks for the good one', async () => {
        queryPrices.mockResolvedValue({items: []});
        await loadComparisonAssetsData([compSignal(0), compSignal(7)], RANGE, ASSETS, new Map());
        expect(queryPrices).toHaveBeenCalledWith([expect.objectContaining({asset_id: 7})]);
    });
});

describe('the query it builds', () => {
    it('asks for events, and passes the range through', async () => {
        queryPrices.mockResolvedValue({items: []});
        await loadComparisonAssetsData([compSignal(7)], RANGE, ASSETS, new Map());
        expect(queryPrices).toHaveBeenCalledWith([{asset_id: 7, date_range: RANGE, include_events: true, target_currency: undefined}]);
    });

    it('passes a target currency when one is wanted', async () => {
        queryPrices.mockResolvedValue({items: []});
        await loadComparisonAssetsData([compSignal(7)], RANGE, ASSETS, new Map(), undefined, 'USD');
        expect(queryPrices).toHaveBeenCalledWith([expect.objectContaining({target_currency: 'USD'})]);
    });

    it('treats an empty target currency as none', async () => {
        queryPrices.mockResolvedValue({items: []});
        await loadComparisonAssetsData([compSignal(7)], RANGE, ASSETS, new Map(), undefined, '');
        expect(queryPrices).toHaveBeenCalledWith([expect.objectContaining({target_currency: undefined})]);
    });

    it('survives an answer with no items at all', async () => {
        queryPrices.mockResolvedValue({});
        const out = await loadComparisonAssetsData([compSignal(7)], RANGE, ASSETS, new Map([[1, []]]));
        expect(out.size).toBe(1);
    });
});

describe('what it writes back into the signal', () => {
    it('injects the resolved series and the asset identity', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: [pricePoint({date: '2024-02-01', close: 12})], events: []}]});
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map());
        expect(sig.params._resolvedData).toEqual([{date: '2024-02-01', value: 12, originalValue: undefined, originalCurrency: undefined, originalCurrencyFlag: undefined}]);
        expect(sig.params._assetIconUrl).toBe('https://x/acme.png');
        expect(sig.params._assetType).toBe('STOCK');
        expect(sig.params._assetCurrency).toBe('EUR');
    });

    it('leaves the series undefined rather than empty when nothing came back', async () => {
        // An empty array and "no data" are different things to the renderer.
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: [], events: []}]});
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map());
        expect(sig.params._resolvedData).toBeUndefined();
    });

    it('treats a missing price list like an empty one', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, events: []}]});
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map());
        expect(sig.params._resolvedData).toBeUndefined();
    });

    it('nulls the identity fields for an asset it has no metadata for', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 99, prices: [pricePoint()], events: []}]});
        const sig = compSignal(99);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map());
        expect(sig.params._assetIconUrl).toBeNull();
        expect(sig.params._assetType).toBeNull();
        expect(sig.params._assetCurrency).toBeUndefined();
    });

    it('nulls them for metadata that exists but is blank', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 8, prices: [pricePoint()], events: []}]});
        const sig = compSignal(8);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map());
        expect(sig.params._assetIconUrl).toBeNull();
        expect(sig.params._assetType).toBeNull();
    });

    it('writes only into the signals that asked for that asset', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: [pricePoint()], events: []}]});
        const mine = compSignal(7);
        const other = compSignal(8);
        await loadComparisonAssetsData([mine, other], RANGE, ASSETS, new Map());
        expect(mine.params._resolvedData).toBeDefined();
        expect(other.params._resolvedData).toBeUndefined();
    });

    it('reads a missing close as zero rather than as NaN', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: [pricePoint({close: null})], events: []}]});
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map());
        expect((sig.params._resolvedData as Array<{value: number}>)[0].value).toBe(0);
    });
});

describe('the currency filter', () => {
    const mixed = [pricePoint({date: '2024-02-01', currency: 'USD', close: 11}), pricePoint({date: '2024-02-02', currency: 'EUR', close: 9})];

    it('keeps every point when no conversion was asked for', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: mixed, events: []}]});
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map());
        expect(sig.params._resolvedData).toHaveLength(2);
    });

    it('drops the points the backend could not convert', async () => {
        // Two currencies on one line is a staircase that reads as a price move.
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: mixed, events: []}]});
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map(), undefined, 'USD');
        const series = sig.params._resolvedData as Array<{date: string}>;
        expect(series).toHaveLength(1);
        expect(series[0].date).toBe('2024-02-01');
    });

    it('records the currency it was converted from, with its flag', async () => {
        queryPrices.mockResolvedValue({
            items: [{asset_id: 7, prices: [pricePoint({currency: 'USD', close: 11, original_close: 10, original_currency: 'EUR'})], events: []}],
        });
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map(), undefined, 'USD');
        const point = (sig.params._resolvedData as Array<Record<string, unknown>>)[0];
        expect(point.originalValue).toBe(10);
        expect(point.originalCurrency).toBe('EUR');
        expect(point.originalCurrencyFlag).toEqual(expect.any(String));
    });

    it('leaves the original untouched when the point was never converted', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: [pricePoint({original_close: null})], events: []}]});
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map());
        const point = (sig.params._resolvedData as Array<Record<string, unknown>>)[0];
        expect(point.originalValue).toBeUndefined();
        expect(point.originalCurrencyFlag).toBeUndefined();
    });

    it('keeps a zero original value, which is a price and not an absence', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: [pricePoint({original_close: 0})], events: []}]});
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map());
        expect((sig.params._resolvedData as Array<Record<string, unknown>>)[0].originalValue).toBe(0);
    });
});

describe('a conversion the backend refused', () => {
    it('flags it on the signal, with the first reason', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: [], events: [], errors: ['no route EUR-USD', 'second']}]});
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map(), undefined, 'USD');
        expect(sig.params._conversionFailed).toBe(true);
        expect(sig.params._conversionError).toBe('no route EUR-USD');
        expect(sig.params._targetCurrency).toBe('USD');
    });

    it.each([
        ['there is no error field', {}],
        ['the list is empty', {errors: []}],
        ['it is not a list', {errors: 'oops'}],
    ])('says nothing failed when %s', async (_label, over) => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: [pricePoint()], events: [], ...over}]});
        const sig = compSignal(7);
        await loadComparisonAssetsData([sig], RANGE, ASSETS, new Map());
        expect(sig.params._conversionFailed).toBe(false);
        expect(sig.params._conversionError).toBeUndefined();
    });
});

describe('the events map it returns', () => {
    it('adds what came back without discarding what was there', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: [], events: [{date: '2024-02-01', kind: 'DIVIDEND'}]}]});
        const existing = new Map<number, unknown[]>([[1, ['older']]]);
        const out = await loadComparisonAssetsData([compSignal(7)], RANGE, ASSETS, existing);
        expect(out.get(1)).toEqual(['older']);
        expect(out.get(7)).toEqual([{date: '2024-02-01', kind: 'DIVIDEND'}]);
        // A new map: the caller's copy is not written through.
        expect(out).not.toBe(existing);
        expect(existing.has(7)).toBe(false);
    });

    it('stores an empty list for an asset that reported no events', async () => {
        queryPrices.mockResolvedValue({items: [{asset_id: 7, prices: []}]});
        const out = await loadComparisonAssetsData([compSignal(7)], RANGE, ASSETS, new Map());
        expect(out.get(7)).toEqual([]);
    });
});
