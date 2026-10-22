/**
 * Contract tests for the immutable load/apply split used by comparison overlays.
 *
 * Loading owns request normalization and detached response shaping. Applying owns
 * the deliberate mutation of only the signal configs that are still current.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {SignalConfig} from '$lib/charts/signals';
import {getAssetPriceStore, removeAssetPriceStore, type AssetPricePoint} from '$lib/stores/assetPriceStoreRegistry';
import {canonicalCacheKey} from '$lib/stores/signalResultCache';
import {
    applyComparisonAssetsData,
    buildComparisonSyncRange,
    clearComparisonAssetsData,
    collectConfiguredComparisonFxSlugs,
    comparisonAnswerGenerations,
    comparisonAnswerIsCacheable,
    comparisonAnswerKey,
    getComparisonEventFxDependency,
    loadComparisonAssetsData,
    type ComparisonAssetLoadItem,
    type ComparisonAssetMeta,
    type ComparisonAssetsLoadResult,
} from '../loadComparisonData';

const {queryPrices} = vi.hoisted(() => ({queryPrices: vi.fn()}));
vi.mock('$lib/api', () => ({
    zodiosApi: {query_prices_bulk_api_v1_assets_prices_query_post: queryPrices},
}));

const RANGE = Object.freeze({start: '2024-01-01', end: '2024-03-31'});

function compSignal(assetId: number, runtimeParams: Record<string, unknown> = {}): SignalConfig {
    return {
        id: `sig-${assetId}`,
        signalType: 'asset-comparison',
        params: {assetId, ...runtimeParams},
        style: {},
    } as unknown as SignalConfig;
}

function pricePoint(overrides: Record<string, unknown> = {}) {
    return {date: '2024-02-01', close: 10, currency: 'EUR', ...overrides};
}

const ASSETS: ComparisonAssetMeta[] = [
    {id: 7, display_name: 'ACME', icon_url: 'https://x/acme.png', asset_type: 'STOCK', currency: 'EUR'},
    {id: 8, display_name: 'Bare', icon_url: null, asset_type: null},
];

function itemById(result: ComparisonAssetsLoadResult, assetId: number): ComparisonAssetLoadItem {
    const item = result.items.find((candidate) => candidate.assetId === assetId);
    expect(item, `missing load item for asset ${assetId}`).toBeDefined();
    return item as ComparisonAssetLoadItem;
}

beforeEach(() => {
    queryPrices.mockReset();
});

describe('buildComparisonSyncRange', () => {
    it('pads a Monday start and Friday end across weekend boundaries by exactly seven calendar days', () => {
        expect(buildComparisonSyncRange({start: '2024-06-10', end: '2024-06-14'}, {today: '2024-07-01'})).toEqual({
            start: '2024-06-03',
            end: '2024-06-21',
        });
    });

    it("caps a past end's seven-day padding at today", () => {
        expect(buildComparisonSyncRange({start: '2024-06-01', end: '2024-06-14'}, {today: '2024-06-18'})).toEqual({
            start: '2024-05-25',
            end: '2024-06-18',
        });
    });

    it('keeps an end equal to today unchanged', () => {
        expect(buildComparisonSyncRange({start: '2024-06-01', end: '2024-06-18'}, {today: '2024-06-18'})).toEqual({
            start: '2024-05-25',
            end: '2024-06-18',
        });
    });

    it('caps a future calendar end at today', () => {
        expect(buildComparisonSyncRange({start: '2024-05-01', end: '2024-06-25'}, {today: '2024-06-18'})).toEqual({
            start: '2024-04-24',
            end: '2024-06-18',
        });
    });

    it('caps the max end sentinel at today', () => {
        expect(buildComparisonSyncRange({start: '2024-05-01', end: 'max'}, {today: '2024-06-18'})).toEqual({
            start: '2024-04-24',
            end: '2024-06-18',
        });
    });

    it('composes a 30-day Calendar warmup with seven additional start-padding days', () => {
        expect(buildComparisonSyncRange({start: '2024-06-20', end: '2024-06-21'}, {calendarLookbackDays: 30, today: '2024-07-31'})).toEqual({
            start: '2024-05-14',
            end: '2024-06-28',
        });
    });

    it('does not mutate the selected range or options while padding', () => {
        const selectedRange = Object.freeze({start: '2024-08-12', end: '2024-08-16'});
        const options = Object.freeze({calendarLookbackDays: 2, today: '2024-08-31'});

        const result = buildComparisonSyncRange(selectedRange, options);

        expect(result).toEqual({start: '2024-08-03', end: '2024-08-23'});
        expect(result).not.toBe(selectedRange);
        expect(selectedRange).toEqual({start: '2024-08-12', end: '2024-08-16'});
        expect(options).toEqual({calendarLookbackDays: 2, today: '2024-08-31'});
    });
});

describe('loadComparisonAssetsData', () => {
    it('accepts readonly IDs and skips the bulk call when no valid peer remains', async () => {
        const assetIds: readonly number[] = Object.freeze([0, -3, 7, 7.5, Number.MAX_SAFE_INTEGER + 1]);
        const range = Object.freeze({...RANGE});
        const assets = ASSETS.map((asset) => ({...asset}));
        const assetsBefore = structuredClone(assets);

        const result = await loadComparisonAssetsData(assetIds, range, assets, 7, 'USD');

        expect(queryPrices).not.toHaveBeenCalled();
        expect(result).toEqual({items: []});
        expect(assetIds).toEqual([0, -3, 7, 7.5, Number.MAX_SAFE_INTEGER + 1]);
        expect(range).toEqual(RANGE);
        expect(assets).toEqual(assetsBefore);
    });

    it('deduplicates valid peers and sends one exact query per peer in one bulk call', async () => {
        const assetIds: readonly number[] = Object.freeze([8, 7, 8, 0, -3, 7.5, 9]);
        const range = {start: RANGE.start, end: RANGE.end};
        const assets = ASSETS.map((asset) => ({...asset}));
        const assetIdsBefore = [...assetIds];
        const rangeBefore = {...range};
        const assetsBefore = structuredClone(assets);
        const response = {items: []};
        const responseBefore = structuredClone(response);
        let capturedQueries: Array<Record<string, unknown>> = [];
        queryPrices.mockImplementation(async (queries: Array<Record<string, unknown>>) => {
            capturedQueries = queries;
            return response;
        });

        const result = await loadComparisonAssetsData(assetIds, range, assets, 9, 'USD');

        expect(queryPrices).toHaveBeenCalledTimes(1);
        expect(capturedQueries).toHaveLength(2);
        const queriesByAssetId = new Map(capturedQueries.map((query) => [query.asset_id, query]));
        expect(new Set(queriesByAssetId.keys())).toEqual(new Set([7, 8]));
        expect(queriesByAssetId.get(7)).toEqual({
            asset_id: 7,
            date_range: {start: '2024-01-01', end: '2024-03-31'},
            include_events: true,
            target_currency: 'USD',
        });
        expect(queriesByAssetId.get(8)).toEqual({
            asset_id: 8,
            date_range: {start: '2024-01-01', end: '2024-03-31'},
            include_events: true,
            target_currency: 'USD',
        });
        expect(result.items).toHaveLength(2);
        expect(new Set(result.items.map((item) => item.assetId))).toEqual(new Set([7, 8]));
        expect(assetIds).toEqual(assetIdsBefore);
        expect(range).toEqual(rangeBefore);
        expect(assets).toEqual(assetsBefore);
        expect(response).toEqual(responseBefore);
    });

    it.each([
        ['an omitted target', undefined],
        ['an empty target', ''],
    ] as const)('normalizes %s to an undefined target currency', async (_label, targetCurrency) => {
        queryPrices.mockResolvedValue({items: []});

        await loadComparisonAssetsData([7], RANGE, ASSETS, undefined, targetCurrency);

        expect(queryPrices).toHaveBeenCalledTimes(1);
        expect(queryPrices).toHaveBeenCalledWith([
            {
                asset_id: 7,
                date_range: {start: '2024-01-01', end: '2024-03-31'},
                include_events: true,
                target_currency: undefined,
            },
        ]);
    });

    it('joins reversed response rows by asset ID and returns detached per-peer values', async () => {
        const row7 = {
            asset_id: 7,
            prices: [pricePoint({date: '2024-02-07', close: 17})],
            events: [{date: '2024-02-07', kind: 'DIVIDEND'}],
        };
        const row8 = {
            asset_id: 8,
            prices: [pricePoint({date: '2024-02-08', close: 28})],
            events: [{date: '2024-02-08', kind: 'SPLIT'}],
        };
        const response = {items: [row8, row7]};
        const responseBefore = structuredClone(response);
        queryPrices.mockResolvedValue(response);

        const result = await loadComparisonAssetsData([7, 8], RANGE, ASSETS);
        const item7 = itemById(result, 7);
        const item8 = itemById(result, 8);

        expect(item7.runtimeParams).toEqual({
            _resolvedData: [
                {
                    date: '2024-02-07',
                    value: 17,
                    originalValue: undefined,
                    originalCurrency: undefined,
                    originalCurrencyFlag: undefined,
                },
            ],
            _assetIconUrl: 'https://x/acme.png',
            _assetType: 'STOCK',
            _assetCurrency: 'EUR',
            _targetCurrency: undefined,
            _conversionFailed: false,
            _conversionError: undefined,
        });
        expect(item7.events).toEqual(row7.events);
        expect(item8.runtimeParams).toMatchObject({
            _resolvedData: [expect.objectContaining({date: '2024-02-08', value: 28})],
            _assetIconUrl: null,
            _assetType: null,
            _assetCurrency: undefined,
        });
        expect(item8.events).toEqual(row8.events);
        expect(result.items).not.toBe(response.items);
        expect(item7.runtimeParams).not.toBe(item8.runtimeParams);
        const resolved7 = item7.runtimeParams._resolvedData as Array<{date: string}>;
        const resolvedPoint7 = resolved7.find((point) => point.date === '2024-02-07');
        const responsePoint7 = row7.prices.find((point) => point.date === '2024-02-07');
        expect(resolved7).not.toBe(row7.prices);
        expect(resolvedPoint7).not.toBe(responsePoint7);
        expect(item7.events).not.toBe(row7.events);
        expect(item8.events).not.toBe(row8.events);
        expect(response).toEqual(responseBefore);
    });

    it.each([
        ['a null response', null],
        ['missing items', {}],
        ['non-array items', {items: {asset_id: 7}}],
        ['a missing peer among malformed rows', {items: [null, 'bad row', {asset_id: 8, prices: [], events: []}]}],
        ['malformed fields on the matching row', {items: [{asset_id: 7, prices: 'bad', events: {}, errors: [null, 3]}]}],
    ] as const)('emits an explicit stale-runtime reset for %s', async (_label, response) => {
        queryPrices.mockResolvedValue(response);

        const result = await loadComparisonAssetsData([7], RANGE, ASSETS, undefined, 'USD');
        const item = itemById(result, 7);

        expect(result.items).toHaveLength(1);
        expect(new Set(result.items.map((candidate) => candidate.assetId))).toEqual(new Set([7]));
        expect(item.runtimeParams).toHaveProperty('_resolvedData', undefined);
        expect(item.runtimeParams).toHaveProperty('_conversionError', undefined);
        expect(item.runtimeParams._conversionFailed).toBe(false);
        expect(item.events).toEqual([]);
    });

    it('keeps mixed-currency points when no target conversion was requested', async () => {
        queryPrices.mockResolvedValue({
            items: [
                {
                    asset_id: 7,
                    prices: [pricePoint({date: '2024-02-01', currency: 'USD', close: 11}), pricePoint({date: '2024-02-02', currency: 'EUR', close: null})],
                    events: [],
                },
            ],
        });

        const result = await loadComparisonAssetsData([7], RANGE, ASSETS);
        const data = itemById(result, 7).runtimeParams._resolvedData as Array<{date: string; value: number}>;
        const byDate = new Map(data.map((point) => [point.date, point]));

        expect(new Set(byDate.keys())).toEqual(new Set(['2024-02-01', '2024-02-02']));
        expect(byDate.get('2024-02-01')?.value).toBe(11);
        expect(byDate.get('2024-02-02')?.value).toBe(0);
    });

    it('filters unconverted target-currency gaps and preserves conversion provenance', async () => {
        queryPrices.mockResolvedValue({
            items: [
                {
                    asset_id: 7,
                    prices: [
                        pricePoint({
                            date: '2024-02-01',
                            currency: 'USD',
                            close: 11,
                            original_close: 0,
                            original_currency: 'EUR',
                        }),
                        pricePoint({
                            date: '2024-02-02',
                            currency: 'EUR',
                            close: 9,
                            original_close: null,
                            original_currency: null,
                        }),
                    ],
                    events: [],
                },
            ],
        });

        const result = await loadComparisonAssetsData([7], RANGE, ASSETS, undefined, 'USD');
        const data = itemById(result, 7).runtimeParams._resolvedData as Array<Record<string, unknown>>;
        const byDate = new Map(data.map((point) => [String(point.date), point]));

        expect(new Set(byDate.keys())).toEqual(new Set(['2024-02-01']));
        expect(byDate.get('2024-02-01')).toEqual({
            date: '2024-02-01',
            value: 11,
            originalValue: 0,
            originalCurrency: 'EUR',
            originalCurrencyFlag: expect.any(String),
        });
        expect(itemById(result, 7).runtimeParams._conversionFailed).toBe(true);
        expect(itemById(result, 7).runtimeParams).toHaveProperty('_conversionError', undefined);
    });

    it('records the first string conversion error when a price remains unconverted', async () => {
        const response = {
            items: [
                {
                    asset_id: 7,
                    prices: [pricePoint({currency: 'EUR', close: 9})],
                    events: [],
                    errors: [17, 'no route EUR-USD', 'second reason'],
                },
            ],
        };
        const responseBefore = structuredClone(response);
        queryPrices.mockResolvedValue(response);

        const result = await loadComparisonAssetsData([7], RANGE, ASSETS, undefined, 'USD');
        const item = itemById(result, 7);

        expect(item.runtimeParams).toEqual({
            _resolvedData: undefined,
            _assetIconUrl: 'https://x/acme.png',
            _assetType: 'STOCK',
            _assetCurrency: 'EUR',
            _targetCurrency: 'USD',
            _conversionFailed: true,
            _conversionError: 'no route EUR-USD',
        });
        expect(response).toEqual(responseBefore);
    });

    it('does not let event-only FX errors poison converted price data', async () => {
        const failedEvent = {
            date: '2024-02-03',
            kind: 'DIVIDEND',
            value: {amount: 3, code: 'GBP'},
        };
        queryPrices.mockResolvedValue({
            items: [
                {
                    asset_id: 7,
                    prices: [pricePoint({currency: 'USD', close: 11})],
                    events: [failedEvent],
                    errors: ['no route GBP-USD'],
                },
            ],
        });

        const result = await loadComparisonAssetsData([7], RANGE, ASSETS, undefined, 'USD');
        const item = itemById(result, 7);

        expect(item.runtimeParams).toEqual({
            _resolvedData: [
                {
                    date: '2024-02-01',
                    value: 11,
                    originalValue: undefined,
                    originalCurrency: undefined,
                    originalCurrencyFlag: undefined,
                },
            ],
            _assetIconUrl: 'https://x/acme.png',
            _assetType: 'STOCK',
            _assetCurrency: 'EUR',
            _targetCurrency: 'USD',
            _conversionFailed: false,
            _conversionError: undefined,
        });
        expect(item.events).toEqual([failedEvent]);
    });

    it('keeps the price route healthy and only the event dependency failed when an event-scoped error precedes a generic conversion error', async () => {
        const failedEvent = {
            date: '2024-02-03',
            kind: 'DIVIDEND',
            value: {amount: 3, code: 'GBP'},
        };
        queryPrices.mockResolvedValue({
            items: [
                {
                    asset_id: 7,
                    prices: [pricePoint({currency: 'USD', close: 11})],
                    events: [failedEvent],
                    errors: ['Missing FX rate GBP->USD for event on 2024-02-03', 'Conversion 1: No FX rate available for GBP->USD'],
                },
            ],
        });

        const result = await loadComparisonAssetsData([7], RANGE, ASSETS, undefined, 'USD');
        const item = itemById(result, 7);

        expect(item.runtimeParams._conversionFailed).toBe(false);
        expect(item.runtimeParams).toHaveProperty('_conversionError', undefined);
        expect(item.events).toEqual([failedEvent]);
        const returnedEvent = item.events.find((event) => event === failedEvent);
        expect(returnedEvent).toBeDefined();
        expect(getComparisonEventFxDependency(returnedEvent, 'USD')).toEqual({
            sourceCurrency: 'GBP',
            failed: true,
        });
    });

    it('keeps a true price-conversion failure on the price route when its error is ordered first', async () => {
        const priceError = 'Conversion 0: No FX rate available for EUR->USD';
        queryPrices.mockResolvedValue({
            items: [
                {
                    asset_id: 7,
                    prices: [pricePoint({currency: 'EUR', close: 9})],
                    events: [
                        {
                            date: '2024-02-03',
                            kind: 'DIVIDEND',
                            value: {amount: 3, code: 'GBP'},
                        },
                    ],
                    errors: [priceError, 'Missing FX rate GBP->USD for event on 2024-02-03'],
                },
            ],
        });

        const result = await loadComparisonAssetsData([7], RANGE, ASSETS, undefined, 'USD');
        const item = itemById(result, 7);

        expect(item.runtimeParams._conversionFailed).toBe(true);
        expect(item.runtimeParams._conversionError).toBe(priceError);
    });

    it('keeps price conversion failure flags when price and event FX errors are mixed', async () => {
        const failedEvent = {
            date: '2024-02-03',
            kind: 'DIVIDEND',
            value: {amount: 3, code: 'GBP'},
        };
        queryPrices.mockResolvedValue({
            items: [
                {
                    asset_id: 7,
                    prices: [
                        pricePoint({
                            date: '2024-02-01',
                            currency: 'USD',
                            close: 11,
                            original_close: 10,
                            original_currency: 'EUR',
                        }),
                        pricePoint({date: '2024-02-02', currency: 'EUR', close: 9}),
                    ],
                    events: [failedEvent],
                    errors: ['no route EUR-USD', 'no route GBP-USD'],
                },
            ],
        });

        const result = await loadComparisonAssetsData([7], RANGE, ASSETS, undefined, 'USD');
        const item = itemById(result, 7);

        expect(item.runtimeParams).toEqual({
            _resolvedData: [
                {
                    date: '2024-02-01',
                    value: 11,
                    originalValue: 10,
                    originalCurrency: 'EUR',
                    originalCurrencyFlag: expect.any(String),
                },
            ],
            _assetIconUrl: 'https://x/acme.png',
            _assetType: 'STOCK',
            _assetCurrency: 'EUR',
            _targetCurrency: 'USD',
            _conversionFailed: true,
            _conversionError: 'no route EUR-USD',
        });
        expect(item.events).toEqual([failedEvent]);
    });

    it('propagates a bulk-query failure without changing caller-owned inputs', async () => {
        const error = new Error('bulk query failed');
        const assetIds: readonly number[] = Object.freeze([7]);
        const range = {start: RANGE.start, end: RANGE.end};
        const assets = ASSETS.map((asset) => ({...asset}));
        const assetsBefore = structuredClone(assets);
        queryPrices.mockRejectedValue(error);

        await expect(loadComparisonAssetsData(assetIds, range, assets)).rejects.toBe(error);

        expect(assetIds).toEqual([7]);
        expect(range).toEqual(RANGE);
        expect(assets).toEqual(assetsBefore);
    });
});

describe('comparison event FX dependencies', () => {
    it('uses original_value as the source of a converted third-currency event', () => {
        expect(
            getComparisonEventFxDependency(
                {
                    value: {amount: 12, code: ' usd '},
                    original_value: {amount: 10, code: ' gbp '},
                },
                ' USD ',
            ),
        ).toEqual({sourceCurrency: 'GBP', failed: false});
    });

    it('uses value.code as the source of a failed third-currency event', () => {
        expect(
            getComparisonEventFxDependency(
                {
                    value: {amount: 10, code: ' gbp '},
                },
                ' USD ',
            ),
        ).toEqual({sourceCurrency: 'GBP', failed: true});
    });

    it('collects native and event routes once in canonical order', () => {
        const events = [
            {
                value: {amount: 12, code: 'EUR'},
                original_value: {amount: 10, code: 'GBP'},
            },
            {value: {amount: 7, code: 'JPY'}},
            {
                value: {amount: 15, code: 'EUR'},
                original_value: {amount: 13, code: 'GBP'},
            },
        ];

        expect(collectConfiguredComparisonFxSlugs(' usd ', ' eur ', events, ['EUR-USD', 'EUR-JPY', 'CHF-EUR', 'EUR-GBP'])).toEqual(['EUR-GBP', 'EUR-JPY', 'EUR-USD']);
    });

    it('omits target identities plus missing and unconfigured routes', () => {
        const targetIdentityEvent = {value: {amount: 5, code: 'EUR'}};
        const missingCurrencyEvent = {value: {amount: 5}};
        const events = [targetIdentityEvent, missingCurrencyEvent, {original_value: {amount: 5, code: ''}}, {value: {amount: 5, code: 'CHF'}}, null];

        expect(collectConfiguredComparisonFxSlugs('EUR', 'EUR', events, ['EUR-USD', 'EUR-GBP'])).toEqual([]);
        expect(getComparisonEventFxDependency(targetIdentityEvent, 'EUR')).toBeNull();
        expect(getComparisonEventFxDependency(missingCurrencyEvent, 'EUR')).toBeNull();
    });
});

describe('applyComparisonAssetsData', () => {
    it('rebuilds an empty events map when no comparison peer is still configured', () => {
        const configured = compSignal(7, {_resolvedData: [{date: 'current', value: 7}]});
        const loaded: ComparisonAssetsLoadResult = {
            items: [
                {
                    assetId: 7,
                    runtimeParams: {_resolvedData: [{date: 'loaded', value: 70}]},
                    events: [{date: 'loaded', kind: 'DIVIDEND'}],
                },
            ],
        };
        const previousEvents = applyComparisonAssetsData([configured], loaded);
        const paramsBeforeClearing = structuredClone(configured.params);

        const clearedEvents = applyComparisonAssetsData([], loaded);

        expect(previousEvents).toEqual(new Map([[7, [{date: 'loaded', kind: 'DIVIDEND'}]]]));
        expect(clearedEvents).toEqual(new Map());
        expect(clearedEvents).not.toBe(previousEvents);
        expect(configured.params).toEqual(paramsBeforeClearing);
    });

    it('applies only current matches and replaces old or removed event entries', () => {
        const current7 = compSignal(7, {
            _resolvedData: ['stale-seven'],
            _conversionFailed: true,
            _conversionError: 'stale seven error',
        });
        const removed8 = compSignal(8, {_resolvedData: ['stale-eight']});
        const unmatched9 = compSignal(9, {_resolvedData: ['keep-nine'], sentinel: 'unchanged'});
        const previousLoaded: ComparisonAssetsLoadResult = {
            items: [
                {
                    assetId: 7,
                    runtimeParams: {_resolvedData: [{date: 'old-seven', value: 7}]},
                    events: [{date: 'old-seven', kind: 'DIVIDEND'}],
                },
                {
                    assetId: 8,
                    runtimeParams: {_resolvedData: [{date: 'old-eight', value: 8}]},
                    events: [{date: 'old-eight', kind: 'SPLIT'}],
                },
            ],
        };
        const previousEvents = applyComparisonAssetsData([current7, removed8], previousLoaded);
        const removedParamsBefore = structuredClone(removed8.params);
        const unmatchedParamsBefore = structuredClone(unmatched9.params);
        const nextEvents7 = [{date: 'new-seven', kind: 'DIVIDEND'}];
        const nextEvents8 = [{date: 'new-eight', kind: 'SPLIT'}];
        const nextLoaded: ComparisonAssetsLoadResult = {
            items: [
                {
                    assetId: 7,
                    runtimeParams: {
                        _resolvedData: [{date: 'new-seven', value: 70}],
                        _conversionFailed: false,
                        _conversionError: undefined,
                    },
                    events: nextEvents7,
                },
                {
                    assetId: 8,
                    runtimeParams: {_resolvedData: [{date: 'new-eight', value: 80}]},
                    events: nextEvents8,
                },
            ],
        };
        const nextLoadedBefore = structuredClone(nextLoaded);

        const nextEvents = applyComparisonAssetsData([current7, unmatched9], nextLoaded);

        expect(current7.params).toMatchObject({
            _resolvedData: [{date: 'new-seven', value: 70}],
            _conversionFailed: false,
            _conversionError: undefined,
        });
        expect(removed8.params).toEqual(removedParamsBefore);
        expect(unmatched9.params).toEqual(unmatchedParamsBefore);
        expect(new Set(nextEvents.keys())).toEqual(new Set([7]));
        expect(nextEvents.has(8)).toBe(false);
        expect(nextEvents.has(9)).toBe(false);
        expect(nextEvents).not.toBe(previousEvents);
        expect(new Set(previousEvents.keys())).toEqual(new Set([7, 8]));
        expect(previousEvents.get(8)).toEqual([{date: 'old-eight', kind: 'SPLIT'}]);

        const appliedEvents = nextEvents.get(7);
        expect(appliedEvents).toEqual(nextEvents7);
        expect(appliedEvents).not.toBe(nextEvents7);
        appliedEvents?.push({date: 'local-only', kind: 'TEST'});
        expect(nextEvents7).toEqual([{date: 'new-seven', kind: 'DIVIDEND'}]);
        expect(nextLoaded).toEqual(nextLoadedBefore);
    });

    it('applies a missing-result item to clear stale runtime explicitly', async () => {
        queryPrices.mockResolvedValue({items: []});
        const loaded = await loadComparisonAssetsData([7], RANGE, ASSETS);
        const fallback = itemById(loaded, 7);
        const signal = compSignal(7, {
            _resolvedData: [{date: 'stale', value: 99}],
            _conversionFailed: true,
            _conversionError: 'stale error',
        });

        const events = applyComparisonAssetsData([signal], loaded);

        expect(fallback.runtimeParams).toHaveProperty('_resolvedData', undefined);
        expect(fallback.runtimeParams).toHaveProperty('_conversionError', undefined);
        expect(fallback.runtimeParams._conversionFailed).toBe(false);
        expect(signal.params).toHaveProperty('_resolvedData', undefined);
        expect(signal.params).toHaveProperty('_conversionError', undefined);
        expect(signal.params._conversionFailed).toBe(false);
        expect(events).toEqual(new Map([[7, []]]));
        expect(events.get(7)).not.toBe(fallback.events);
    });
});

describe('clearComparisonAssetsData', () => {
    it('removes every loader runtime field while preserving durable config and returns a fresh empty event map', () => {
        const runtimeKeys = ['_resolvedData', '_assetDisplayName', '_assetIconUrl', '_assetType', '_assetCurrency', '_targetCurrency', '_conversionFailed', '_conversionError'] as const;
        const current7: SignalConfig = {
            ...compSignal(7, {
                displayMode: 'relative',
                _resolvedData: [{date: '2024-02-07', value: 70}],
                _assetDisplayName: 'ACME',
                _assetIconUrl: 'https://x/acme.png',
                _assetType: 'STOCK',
                _assetCurrency: 'EUR',
                _targetCurrency: 'USD',
                _conversionFailed: true,
                _conversionError: 'stale seven error',
            }),
            style: {color: '#3b82f6', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null},
        };
        const current8: SignalConfig = {
            ...compSignal(8, {
                displayMode: 'absolute',
                _resolvedData: [{date: '2024-02-08', value: 80}],
                _assetDisplayName: 'Bare',
                _assetIconUrl: null,
                _assetType: 'FUND',
                _assetCurrency: 'GBP',
                _targetCurrency: 'EUR',
                _conversionFailed: false,
                _conversionError: 'stale eight error',
            }),
            style: {color: '#f59e0b', lineWidth: 3, lineType: 'dashed', markerStart: 'circle', markerEnd: 'arrow'},
        };
        const current = [current7, current8];
        const current7Params = current7.params;
        const current8Params = current8.params;
        const current7StyleBefore = structuredClone(current7.style);
        const current8StyleBefore = structuredClone(current8.style);

        for (const config of current) {
            for (const key of runtimeKeys) expect(config.params).toHaveProperty(key);
        }

        const clearedEvents = clearComparisonAssetsData(current);
        const nextClearedEvents = clearComparisonAssetsData([]);

        for (const config of current) {
            for (const key of runtimeKeys) expect(config.params).not.toHaveProperty(key);
        }
        expect(current7.params).toBe(current7Params);
        expect(current7.params).toEqual({assetId: 7, displayMode: 'relative'});
        expect(current8.params).toBe(current8Params);
        expect(current8.params).toEqual({assetId: 8, displayMode: 'absolute'});
        expect(current7.style).toEqual(current7StyleBefore);
        expect(current8.style).toEqual(current8StyleBefore);
        expect(clearedEvents).toEqual(new Map());
        expect(nextClearedEvents).toEqual(new Map());
        expect(clearedEvents).not.toBe(nextClearedEvents);
    });
});

// ---------------------------------------------------------------------------------------------------------------------
// N64b: the client cache of the comparison series. The three helpers below give the page the key of an answer, the
// generations of the price stores it was drawn over, and whether it may be kept. Red first: none exists yet.
// ---------------------------------------------------------------------------------------------------------------------

/** Asset ids no other case of the file uses: the stores of the registry are shared by the whole module. */
const N64B_IDS = [9101, 9102, 9103] as const;

const N64B_ASSETS: ComparisonAssetMeta[] = [
    {id: 9101, display_name: 'Peer EUR', currency: 'EUR'},
    {id: 9102, display_name: 'Peer GBP', currency: 'GBP'},
    {id: 9103, display_name: 'Peer without currency'},
];

const N64B_RANGE = {start: '2024-01-01', end: '2024-03-31'};

function storePoint(date: string): AssetPricePoint {
    return {date, close: 10, open: null, high: null, low: null, volume: null, currency: 'EUR', originalClose: null, backwardFillInfo: null};
}

afterEach(() => {
    for (const id of N64B_IDS) removeAssetPriceStore(id);
});

describe('comparisonAnswerKey: the canonical text of the request, blind to the order and the repeats of the ids', () => {
    it('is the canonical text of the distinct ids ascending, the range and the target currency (null when none)', () => {
        expect(comparisonAnswerKey([8, 7], N64B_RANGE, 'USD')).toBe(canonicalCacheKey({assets: [7, 8], range: {start: '2024-01-01', end: '2024-03-31'}, targetCurrency: 'USD'}));
        expect(comparisonAnswerKey([7], N64B_RANGE)).toBe(canonicalCacheKey({assets: [7], range: N64B_RANGE, targetCurrency: null}));
    });

    it('gives one key to the same ids in another order or repeated', () => {
        const key = comparisonAnswerKey([7, 8, 9], N64B_RANGE, 'EUR');

        expect(comparisonAnswerKey([9, 7, 8], N64B_RANGE, 'EUR')).toBe(key);
        expect(comparisonAnswerKey([8, 8, 9, 7, 7], N64B_RANGE, 'EUR')).toBe(key);
    });

    it('does not mutate the ids it is given', () => {
        const ids: readonly number[] = Object.freeze([9, 7, 9]);

        expect(() => comparisonAnswerKey(ids, N64B_RANGE)).not.toThrow();
        expect(ids).toEqual([9, 7, 9]);
    });

    it('tells apart another range, another set of ids and another currency', () => {
        const keys = [
            comparisonAnswerKey([7, 8], N64B_RANGE, 'EUR'),
            comparisonAnswerKey([7, 8], {start: '2024-01-02', end: N64B_RANGE.end}, 'EUR'),
            comparisonAnswerKey([7, 8], {start: N64B_RANGE.start, end: '2024-04-01'}, 'EUR'),
            comparisonAnswerKey([7, 9], N64B_RANGE, 'EUR'),
            comparisonAnswerKey([7], N64B_RANGE, 'EUR'),
            comparisonAnswerKey([7, 8], N64B_RANGE, 'USD'),
            comparisonAnswerKey([7, 8], N64B_RANGE),
        ];

        expect(new Set(keys).size).toBe(keys.length);
    });

    it('takes an undefined and an empty target currency as one: no conversion asked, and EUR is another request', () => {
        expect(comparisonAnswerKey([7], N64B_RANGE, '')).toBe(comparisonAnswerKey([7], N64B_RANGE, undefined));
        expect(comparisonAnswerKey([7], N64B_RANGE, '')).not.toBe(comparisonAnswerKey([7], N64B_RANGE, 'EUR'));
    });
});

describe('comparisonAnswerGenerations: the generations of the price stores the answer is drawn over', () => {
    it('is, for each distinct id ascending, the generation of the store of that asset in its own currency', () => {
        const generations = comparisonAnswerGenerations([9102, 9101, 9102], N64B_ASSETS);

        expect(generations).toEqual([getAssetPriceStore(9101, 'EUR').generation, getAssetPriceStore(9102, 'GBP').generation]);
    });

    it('changes when a peer’s store is marked stale or emptied, and only that peer’s position moves', () => {
        const before = comparisonAnswerGenerations([9101, 9102], N64B_ASSETS);
        expect(before, 'premise: every peer has a currency').not.toBeNull();

        getAssetPriceStore(9102, 'GBP').markStale();
        const afterStale = comparisonAnswerGenerations([9101, 9102], N64B_ASSETS);
        expect(afterStale).not.toEqual(before);
        expect(afterStale?.[0]).toBe(before?.[0]);
        expect(afterStale?.[1]).not.toBe(before?.[1]);

        getAssetPriceStore(9101, 'EUR').invalidateAll();
        const afterEmptied = comparisonAnswerGenerations([9101, 9102], N64B_ASSETS);
        expect(afterEmptied?.[0]).not.toBe(afterStale?.[0]);
        expect(afterEmptied?.[1]).toBe(afterStale?.[1]);
    });

    it('does not change when points are merged or a range is marked fetched: the answer is still the same data', () => {
        const before = comparisonAnswerGenerations([9101, 9102], N64B_ASSETS);
        expect(before).not.toBeNull();

        getAssetPriceStore(9101, 'EUR').merge([storePoint('2024-02-01'), storePoint('2024-02-02')]);
        getAssetPriceStore(9102, 'GBP').markFetched('2024-01-01', '2024-03-31');

        expect(comparisonAnswerGenerations([9101, 9102], N64B_ASSETS)).toEqual(before);
    });

    it('reads the stores of the TARGET currency when one is given, never the asset’s own', () => {
        const generations = comparisonAnswerGenerations([9101, 9102], N64B_ASSETS, 'USD');
        expect(generations).toEqual([getAssetPriceStore(9101, 'USD').generation, getAssetPriceStore(9102, 'USD').generation]);

        getAssetPriceStore(9101, 'EUR').invalidateAll(); // the native store: not what the converted answer was drawn over
        expect(comparisonAnswerGenerations([9101, 9102], N64B_ASSETS, 'USD'), 'a native store moved and the converted answer was dropped').toEqual(generations);

        getAssetPriceStore(9101, 'USD').markStale();
        expect(comparisonAnswerGenerations([9101, 9102], N64B_ASSETS, 'USD')).not.toEqual(generations);
    });

    it('takes an empty target currency as none: the asset’s own store', () => {
        expect(comparisonAnswerGenerations([9101], N64B_ASSETS, '')).toEqual([getAssetPriceStore(9101, 'EUR').generation]);
    });

    it('needs no currency of the asset when a target currency names the stores', () => {
        expect(comparisonAnswerGenerations([9103], N64B_ASSETS, 'EUR')).toEqual([getAssetPriceStore(9103, 'EUR').generation]);
    });

    it('is null when a peer has no meta in the asset list, or no currency can be found: nothing is cacheable', () => {
        expect(comparisonAnswerGenerations([9101, 9999], N64B_ASSETS)).toBeNull();
        expect(comparisonAnswerGenerations([9101, 9999], N64B_ASSETS, 'USD')).toBeNull();
        expect(comparisonAnswerGenerations([9101, 9103], N64B_ASSETS)).toBeNull();
        expect(comparisonAnswerGenerations([9103], N64B_ASSETS)).toBeNull();
    });

    it('gives an empty list for no ids, and does not mutate its inputs', () => {
        const ids: readonly number[] = Object.freeze([9102, 9101]);
        const assets = N64B_ASSETS.map((asset) => Object.freeze({...asset}));

        expect(comparisonAnswerGenerations([], N64B_ASSETS)).toEqual([]);
        expect(comparisonAnswerGenerations(ids, assets)).toHaveLength(2);
        expect(ids).toEqual([9102, 9101]);
    });
});

describe('comparisonAnswerIsCacheable: an answer with a failed conversion is not kept', () => {
    const item = (assetId: number, runtimeParams: Record<string, unknown>): ComparisonAssetLoadItem => ({assetId, runtimeParams, events: []});

    it('is false when any item failed its conversion', () => {
        expect(comparisonAnswerIsCacheable({items: [item(7, {_conversionFailed: false}), item(8, {_conversionFailed: true})]})).toBe(false);
        expect(comparisonAnswerIsCacheable({items: [item(7, {_conversionFailed: true, _conversionError: 'no rate'})]})).toBe(false);
    });

    it('is true when no item failed, an item with no prices included, and for no items at all', () => {
        expect(comparisonAnswerIsCacheable({items: [item(7, {_conversionFailed: false, _resolvedData: [{date: '2024-02-01', value: 10}]}), item(8, {})]})).toBe(true);
        expect(comparisonAnswerIsCacheable({items: [item(7, {_resolvedData: []})]})).toBe(true);
        expect(comparisonAnswerIsCacheable({items: []})).toBe(true);
    });
});
