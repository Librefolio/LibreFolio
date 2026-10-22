/**
 * comparisonSeries.ts (lot Y-41): where a chart that holds no series of its own finds the ones its saved comparisons draw.
 *
 * The FX list asks no prices, and its cards draw daily rates; a card with a comparison with an ASSET needs that asset's
 * daily series, and a chart with a comparison with an FX PAIR needs that pair's rates in its store. This module is the
 * one door for both (the detail pages call the pair half, lot Y-42 follow-up). The contract:
 *
 * - `comparisonTargetFromStore(asset)`: the asset's cached daily series as the shape the renderers read
 *   (`ComparisonTarget`: its points, named, with icon and type); null while the cache holds none. The series is in the
 *   asset's own currency, as the FX detail page draws it (decision Q-Y41-1 a).
 * - `ensureComparisonSeries(assets, range)`: asks the backend for what the cache does not cover, in ONE request for all
 *   the assets (daily, no events, no conversion), and files the answers in the cache; nothing to ask when it covers every
 *   asset over the range, and only the assets with a gap otherwise. A failed request marks nothing fetched, so a later
 *   call asks again; a 404 (an asset the backend does not know) is final and marks it. It never throws.
 * - `fxPairSlugsOf(configs, ownSlug)`: the pairs the `fx-pair` signals name, once each, in order, without the chart's own
 *   pair and without an empty one.
 * - `ensureSignalFxPairs(configs, ownSlug, range)`: those pairs' rates in the FX stores over the range (the stores' own gap
 *   detection); one pair failing does not stop the others, and the call never throws.
 *
 * Red first: the module does not exist.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: {
        query_prices_bulk_api_v1_assets_prices_query_post: vi.fn(),
    },
}));
const fxRange = vi.hoisted(() => ({ensureFxRangeLoaded: vi.fn(async () => [])}));
vi.mock('$lib/stores/fxStoreRegistry', async (importOriginal) => ({...(await importOriginal<typeof import('$lib/stores/fxStoreRegistry')>()), ensureFxRangeLoaded: fxRange.ensureFxRangeLoaded}));

import {zodiosApi} from '$lib/api';
import type {SignalConfig} from '$lib/charts/signals';
import {apiPricesToAssetPricePoints, getAssetPriceStore, invalidateAssetPriceStore} from '$lib/stores/assetPriceStoreRegistry';

import {comparisonTargetFromStore, ensureComparisonSeries, ensureSignalFxPairs, fxPairSlugsOf} from '../comparisonSeries';

const query = vi.mocked(zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post);
const RANGE = {start: '2026-03-02', end: '2026-03-06'};
const DAYS = ['2026-03-02', '2026-03-03', '2026-03-04', '2026-03-05', '2026-03-06'];

const apiPoint = (date: string, close: number, daysBack: number | null = null) => ({date, close: String(close), open: null, high: null, low: null, volume: null, currency: 'USD', backward_fill_info: daysBack === null ? null : {days_back: daysBack}});
const answer = (...items: Array<{id: number; closes: number[]}>) => ({items: items.map((item) => ({asset_id: item.id, prices: item.closes.map((close, index) => apiPoint(DAYS[index], close)), events: [], errors: []}))}) as never;

/** Cache `closes` for asset `id` in USD over the whole range, as a past request left them. */
function cache(id: number, closes: number[]): void {
    const store = getAssetPriceStore(id, 'USD');
    store.merge(apiPricesToAssetPricePoints(closes.map((close, index) => apiPoint(DAYS[index], close))));
    store.markFetched(RANGE.start, RANGE.end);
}

const config = (id: string, signalType: string, params: Record<string, unknown>): SignalConfig => ({id, signalType, params, style: {color: '#000000', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null}});

beforeEach(() => {
    for (const id of [41, 42, 43]) invalidateAssetPriceStore(id);
    query.mockReset();
    fxRange.ensureFxRangeLoaded.mockReset();
    fxRange.ensureFxRangeLoaded.mockResolvedValue([]);
});

describe('comparisonTargetFromStore', () => {
    it('gives the cached daily series, named, with its icon and type', () => {
        cache(41, [100, 101, 99, 102, 103]);

        const target = comparisonTargetFromStore({id: 41, currency: 'USD', display_name: 'Peer', icon_url: '/peer.png', asset_type: 'ETF'});

        expect(target?.data.map((point) => [point.date, point.value])).toEqual(DAYS.map((day, index) => [day, [100, 101, 99, 102, 103][index]]));
        expect([target?.displayName, target?.iconUrl, target?.assetType]).toEqual(['Peer', '/peer.png', 'ETF']);
    });

    it('carries a backward-filled day’s staleness, as the cards’ own series do', () => {
        const store = getAssetPriceStore(42, 'USD');
        store.merge(apiPricesToAssetPricePoints([apiPoint('2026-03-02', 10), apiPoint('2026-03-03', 10, 1)]));

        const target = comparisonTargetFromStore({id: 42, currency: 'USD', display_name: 'Peer'});

        expect(target?.data.map((point) => point.staleDays ?? 0)).toEqual([0, 1]);
    });

    it('gives nothing while the cache holds no point of the asset', () => {
        expect(comparisonTargetFromStore({id: 43, currency: 'USD', display_name: 'Peer'})).toBeNull();
    });

    it('does not mix an asset’s currencies: the series read is the one of the asset’s own currency', () => {
        cache(41, [100, 101, 99, 102, 103]);

        expect(comparisonTargetFromStore({id: 41, currency: 'EUR', display_name: 'Peer'})).toBeNull();
    });
});

describe('ensureComparisonSeries', () => {
    it('asks ONE request for all the assets with a gap: daily, no events, no conversion', async () => {
        query.mockResolvedValue(answer({id: 41, closes: [1, 2, 3, 4, 5]}, {id: 42, closes: [6, 7, 8, 9, 10]}));

        await ensureComparisonSeries(
            [
                {id: 41, currency: 'USD'},
                {id: 42, currency: 'USD'},
            ],
            RANGE,
        );

        expect(query).toHaveBeenCalledTimes(1);
        expect(query.mock.calls[0][0]).toEqual([
            {asset_id: 41, date_range: RANGE, include_price: true, include_events: false},
            {asset_id: 42, date_range: RANGE, include_price: true, include_events: false},
        ]);
    });

    it('files the answers in the cache, and asks nothing the next time', async () => {
        query.mockResolvedValue(answer({id: 41, closes: [1, 2, 3, 4, 5]}));
        await ensureComparisonSeries([{id: 41, currency: 'USD'}], RANGE);

        expect(comparisonTargetFromStore({id: 41, currency: 'USD', display_name: 'Peer'})?.data).toHaveLength(5);
        await ensureComparisonSeries([{id: 41, currency: 'USD'}], RANGE);
        expect(query).toHaveBeenCalledTimes(1);
    });

    it('asks nothing when the cache covers every asset over the range', async () => {
        cache(41, [1, 2, 3, 4, 5]);
        cache(42, [1, 2, 3, 4, 5]);

        await ensureComparisonSeries(
            [
                {id: 41, currency: 'USD'},
                {id: 42, currency: 'USD'},
            ],
            RANGE,
        );

        expect(query).not.toHaveBeenCalled();
    });

    it('asks only the assets with a gap, each once even when named twice', async () => {
        cache(41, [1, 2, 3, 4, 5]);
        query.mockResolvedValue(answer({id: 42, closes: [1, 2, 3, 4, 5]}));

        await ensureComparisonSeries(
            [
                {id: 41, currency: 'USD'},
                {id: 42, currency: 'USD'},
                {id: 42, currency: 'USD'},
            ],
            RANGE,
        );

        expect(query.mock.calls[0][0]).toEqual([{asset_id: 42, date_range: RANGE, include_price: true, include_events: false}]);
    });

    it('marks nothing fetched when the request fails, so a later call asks again, and never throws', async () => {
        query.mockRejectedValueOnce(Object.assign(new Error('boom'), {response: {status: 500}}));
        await expect(ensureComparisonSeries([{id: 41, currency: 'USD'}], RANGE)).resolves.toBeUndefined();

        query.mockResolvedValueOnce(answer({id: 41, closes: [1, 2, 3, 4, 5]}));
        await ensureComparisonSeries([{id: 41, currency: 'USD'}], RANGE);

        expect(query).toHaveBeenCalledTimes(2);
        expect(comparisonTargetFromStore({id: 41, currency: 'USD', display_name: 'Peer'})?.data).toHaveLength(5);
    });

    it('takes a 404 as final: the asset is marked and not asked again', async () => {
        query.mockRejectedValueOnce(Object.assign(new Error('unknown'), {response: {status: 404}}));

        await ensureComparisonSeries([{id: 43, currency: 'USD'}], RANGE);
        await ensureComparisonSeries([{id: 43, currency: 'USD'}], RANGE);

        expect(query).toHaveBeenCalledTimes(1);
    });
});

describe('fxPairSlugsOf and ensureSignalFxPairs', () => {
    const configs = [
        config('a', 'fx-pair', {pairSlug: 'EUR-GBP'}),
        config('b', 'asset-comparison', {assetId: 41}),
        config('c', 'fx-pair', {pairSlug: 'USD-JPY', _inverted: true}),
        config('d', 'fx-pair', {pairSlug: 'EUR-GBP'}),
        config('e', 'fx-pair', {pairSlug: 'EUR-USD'}),
        config('f', 'fx-pair', {pairSlug: ''}),
    ];

    it('lists the pairs the fx-pair signals name, once each and in order, without the chart’s own pair and without an empty one', () => {
        expect(fxPairSlugsOf(configs, 'EUR-USD')).toEqual(['EUR-GBP', 'USD-JPY']);
        expect(fxPairSlugsOf(configs)).toEqual(['EUR-GBP', 'USD-JPY', 'EUR-USD']);
    });

    it('loads each of them over the range, the chart’s own apart', async () => {
        await ensureSignalFxPairs(configs, 'EUR-USD', RANGE);

        expect(fxRange.ensureFxRangeLoaded.mock.calls).toEqual([
            ['EUR-GBP', RANGE.start, RANGE.end],
            ['USD-JPY', RANGE.start, RANGE.end],
        ]);
    });

    it('lets the others finish when one pair fails, and never throws', async () => {
        fxRange.ensureFxRangeLoaded.mockRejectedValueOnce(new Error('down'));

        await expect(ensureSignalFxPairs(configs, 'EUR-USD', RANGE)).resolves.toBeUndefined();

        expect(fxRange.ensureFxRangeLoaded).toHaveBeenCalledTimes(2);
    });
});
