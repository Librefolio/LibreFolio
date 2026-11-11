import {describe, expect, it} from 'vitest';
import type {SignalConfig} from '$lib/features/signals/ChartSignal';
import {
    buildChartRequestBody,
    calendarComparisonFingerprint,
    calendarDataFingerprint,
    calendarPeerAssetIds,
    calendarReturnRequests,
    chartCurrencies,
    fxPairTargetsOf,
    heldPointsToChartPoints,
    priceComparisonLoadFingerprint,
    priceComparisonRuntimeIsAuthoritative,
} from './assetDetailChartRequest';

const config = (id: string, signalType: string, params: Record<string, unknown>): SignalConfig => ({id, signalType, params, style: {} as SignalConfig['style']});

describe('chartCurrencies', () => {
    it('converts when the display currency differs from the native one', () => {
        expect(chartCurrencies('USD', 'EUR')).toEqual({effectiveCurrency: 'USD', targetCurrency: 'USD'});
    });
    it('does not convert when they are the same or one is missing', () => {
        expect(chartCurrencies('EUR', 'EUR')).toEqual({effectiveCurrency: 'EUR', targetCurrency: undefined});
        expect(chartCurrencies('', 'EUR')).toEqual({effectiveCurrency: 'EUR', targetCurrency: undefined});
        expect(chartCurrencies('USD', '')).toEqual({effectiveCurrency: '', targetCurrency: undefined});
    });
});

describe('calendarPeerAssetIds', () => {
    it('keeps the distinct positive peers in config order and leaves the page asset out', () => {
        const configs = [config('a', 'asset-comparison', {assetId: 9}), config('b', 'asset-comparison', {assetId: 3}), config('c', 'asset-comparison', {assetId: 9}), config('d', 'asset-comparison', {assetId: 5}), config('e', 'sma', {assetId: 7}), config('f', 'asset-comparison', {assetId: 0})];
        expect(calendarPeerAssetIds(configs, 5)).toEqual([9, 3]);
    });
});

describe('buildChartRequestBody', () => {
    const base = {assetId: 5, askedFromMin: false, dateStart: '2024-01-01', dateEnd: '2024-12-31', includePrice: true, targetCurrency: 'USD', effectiveCurrency: 'USD', signals: [{signal_code: 'sma'}], calendarRequests: calendarReturnRequests(30), peerAssetIds: [9, 3]};
    it('puts the asset first and one price-less item per peer, all on the same range', () => {
        const body = buildChartRequestBody(base);
        expect(body.map((item) => item.asset_id)).toEqual([5, 9, 3]);
        expect(body[0]).toMatchObject({include_price: true, include_events: true, target_currency: 'USD', signals: [{signal_code: 'sma'}]});
        expect(body[1]).toMatchObject({include_price: false, include_events: true, target_currency: 'USD', signals: base.calendarRequests});
        expect(new Set(body.map((item) => JSON.stringify(item.date_range)))).toEqual(new Set([JSON.stringify({start: '2024-01-01', end: '2024-12-31'})]));
    });
    it('asks every item from the sentinel `min` when «All» is pending', () => {
        const body = buildChartRequestBody({...base, askedFromMin: true});
        expect(body.every((item) => item.date_range.start === 'min')).toBe(true);
    });
    it('leaves the peers\' currency undefined when the series has none', () => {
        expect(buildChartRequestBody({...base, effectiveCurrency: '', targetCurrency: undefined})[1].target_currency).toBeUndefined();
    });
    it('asks no price when the held prices answer the range', () => {
        expect(buildChartRequestBody({...base, includePrice: false})[0].include_price).toBe(false);
    });
});

describe('heldPointsToChartPoints', () => {
    it('maps the store fields to the server shape', () => {
        const [point] = heldPointsToChartPoints([{date: '2024-01-02', close: 10, open: 9, high: 11, low: 8, volume: 100, currency: 'EUR', originalClose: 12, backwardFillInfo: {daysBack: 2}}]);
        expect(point).toEqual({date: '2024-01-02', close: 10, open: 9, high: 11, low: 8, volume: 100, currency: 'EUR', original_close: 12, backward_fill_info: {days_back: 2}});
        expect(heldPointsToChartPoints([{date: 'd', close: 1}])[0].backward_fill_info).toBeNull();
    });
});

describe('fxPairTargetsOf', () => {
    it('keeps the fx-pair signals that name a pair, with their inversion', () => {
        const configs = [config('a', 'fx-pair', {pairSlug: 'EUR-USD', _inverted: true}), config('b', 'fx-pair', {}), config('c', 'sma', {pairSlug: 'X-Y'})];
        expect(fxPairTargetsOf(configs)).toEqual([{configId: 'a', pairSlug: 'EUR-USD', inverted: true}]);
    });
});

describe('fingerprints', () => {
    const configs = [config('a', 'asset-comparison', {assetId: 9}), config('b', 'asset-comparison', {assetId: 3})];
    it('calendarComparisonFingerprint lists the sorted peers, without the page asset', () => {
        expect(calendarComparisonFingerprint(configs, 9)).toBe('[3]');
        expect(calendarComparisonFingerprint(configs, 1)).toBe('[3,9]');
    });
    it('calendarDataFingerprint falls back from the display to the native currency', () => {
        const context = {assetId: 1, urlDateStart: 's', urlDateEnd: 'e', displayCurrency: '', nativeCurrency: 'EUR', windowDays: 30};
        expect(JSON.parse(calendarDataFingerprint(configs, context))).toEqual({assetId: 1, start: 's', end: 'e', targetCurrency: 'EUR', windowDays: 30, peers: [3, 9]});
        expect(JSON.parse(calendarDataFingerprint(configs, {...context, displayCurrency: 'USD'})).targetCurrency).toBe('USD');
    });
    it('priceComparisonLoadFingerprint sorts by config id and ignores the page asset', () => {
        const context = {assetId: 9, comparisonStart: 's', dateEnd: 'e', displayCurrency: ''};
        expect(JSON.parse(priceComparisonLoadFingerprint([...configs].reverse(), context))).toEqual({peers: [{configId: 'b', assetId: 3}], start: 's', end: 'e', targetCurrency: ''});
    });
    it('priceComparisonRuntimeIsAuthoritative needs the conversion flag and the events of every peer', () => {
        const answered = [config('a', 'asset-comparison', {assetId: 9, _conversionFailed: false})];
        expect(priceComparisonRuntimeIsAuthoritative(answered, 1, () => true)).toBe(true);
        expect(priceComparisonRuntimeIsAuthoritative(answered, 1, () => false)).toBe(false);
        expect(priceComparisonRuntimeIsAuthoritative([config('a', 'asset-comparison', {assetId: 9})], 1, () => true)).toBe(false);
        expect(priceComparisonRuntimeIsAuthoritative([], 1, () => false)).toBe(true);
    });
});
