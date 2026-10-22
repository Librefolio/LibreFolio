/**
 * reducedPriceQuery.ts (Z-29b): what the Assets page asks `POST /assets/prices/query` for the cards of its grid. Each
 * card sends its own item — `key` `asset:<id>` and the `max_points` its measured plot takes — and each comparison target
 * of the card is an item `sample_like` that key, on the same range, so the target is drawn on the card's own buckets. An
 * item is sent only for what is not cached; the items of a card go together, in one group, for `bulkBatches.ts`.
 *
 * Red first: the module does not exist.
 */
import {describe, expect, it} from 'vitest';

import {BULK_SIGNAL_MARGIN_DAYS} from '$lib/api/bulkBatches';

import {buildReducedQuery, cardKey, cardsOfAnotherStep, comparisonTargetFrom, comparisonTargetIds, estimateEntryDays, signalBaseData, type CardQueryInput} from '../reducedPriceQuery';

const RANGE = {start: '2026-01-01', end: '2026-06-30'};
const EMA = {instance_id: 'ema', signal_code: 'EMA', params: {period: 5}};

const card = (assetId: number, extra: Partial<CardQueryInput> = {}): CardQueryInput => ({assetId, plotWidthPx: 290, ...RANGE, needsPrice: true, signals: [], targets: [], ...extra});

describe('cardKey', () => {
    it('names an item by the asset of its card, in the characters the backend allows for a key', () => {
        expect(cardKey(42)).toBe('asset:42');
        expect(cardKey(42)).toMatch(/^[A-Za-z0-9_.:-]{1,64}$/);
    });
});

describe('buildReducedQuery: a card’s own item', () => {
    it('sends the key, the max_points of the measured plot and the range', () => {
        const [entry] = buildReducedQuery([card(7)]);

        expect(entry.item).toEqual({asset_id: 7, date_range: RANGE, include_price: true, signals: [], key: 'asset:7', max_points: 377});
        expect([entry.group, entry.role, entry.cardId, entry.targetId]).toEqual(['asset:7', 'card', 7, null]);
    });

    it('takes the max_points from each card’s own width', () => {
        const entries = buildReducedQuery([card(1, {plotWidthPx: 100}), card(2, {plotWidthPx: 400})]);

        expect(entries.map((entry) => entry.item.max_points)).toEqual([130, 520]);
    });

    it('sends nothing for a card with nothing to read', () => {
        expect(buildReducedQuery([card(7, {needsPrice: false})])).toEqual([]);
    });

    it('asks no prices of a card that has them, if it has backend signals: the signals only', () => {
        const [entry] = buildReducedQuery([card(7, {needsPrice: false, signals: [EMA]})]);

        expect(entry.item).toMatchObject({asset_id: 7, include_price: false, signals: [EMA], key: 'asset:7', max_points: 377});
    });

    it('sends its signals with the prices, as one item', () => {
        const entries = buildReducedQuery([card(7, {signals: [EMA]})]);

        expect(entries).toHaveLength(1);
        expect(entries[0].item).toMatchObject({include_price: true, signals: [EMA]});
    });
});

describe('buildReducedQuery: the targets of a card’s comparisons', () => {
    it('sends each target to be read as an item sample_like the card’s key, on the same range, without signals', () => {
        const entries = buildReducedQuery([card(7, {targets: [{assetId: 9, needsRead: true}]})]);

        expect(entries.map((entry) => entry.item)).toEqual([
            {asset_id: 7, date_range: RANGE, include_price: true, signals: [], key: 'asset:7', max_points: 377},
            {asset_id: 9, date_range: RANGE, include_price: true, signals: [], sample_like: 'asset:7'},
        ]);
        expect(entries.map((entry) => [entry.group, entry.role, entry.cardId, entry.targetId])).toEqual([
            ['asset:7', 'card', 7, null],
            ['asset:7', 'target', 7, 9],
        ]);
    });

    it('keeps a card’s item even when it needs nothing itself, so that its targets can name it: a step only, no prices', () => {
        const entries = buildReducedQuery([card(7, {needsPrice: false, targets: [{assetId: 9, needsRead: true}]})]);

        expect(entries.map((entry) => entry.item)).toEqual([
            {asset_id: 7, date_range: RANGE, include_price: false, signals: [], key: 'asset:7', max_points: 377},
            {asset_id: 9, date_range: RANGE, include_price: true, signals: [], sample_like: 'asset:7'},
        ]);
    });

    it('does not send a target that is cached', () => {
        const entries = buildReducedQuery([
            card(7, {
                targets: [
                    {assetId: 9, needsRead: false},
                    {assetId: 10, needsRead: true},
                ],
            }),
        ]);

        expect(entries.map((entry) => entry.item.asset_id)).toEqual([7, 10]);
    });

    it('sends a target once per card: two cards comparing with one asset each get their own sample of it', () => {
        const entries = buildReducedQuery([card(7, {targets: [{assetId: 9, needsRead: true}]}), card(8, {targets: [{assetId: 9, needsRead: true}]})]);

        expect(entries.map((entry) => [entry.item.asset_id, entry.item.key ?? entry.item.sample_like])).toEqual([
            [7, 'asset:7'],
            [9, 'asset:7'],
            [8, 'asset:8'],
            [9, 'asset:8'],
        ]);
    });

    it('leaves out a target repeated for a card and the card itself', () => {
        const entries = buildReducedQuery([
            card(7, {
                targets: [
                    {assetId: 9, needsRead: true},
                    {assetId: 9, needsRead: true},
                    {assetId: 7, needsRead: true},
                ],
            }),
        ]);

        expect(entries.map((entry) => entry.item.asset_id)).toEqual([7, 9]);
    });

    it('keeps the members of a card together: its item, then its targets, before the next card’s', () => {
        const entries = buildReducedQuery([card(1, {targets: [{assetId: 3, needsRead: true}]}), card(2), card(4, {targets: [{assetId: 3, needsRead: true}]})]);

        expect(entries.map((entry) => entry.group)).toEqual(['asset:1', 'asset:1', 'asset:2', 'asset:4', 'asset:4']);
    });
});

describe('estimateEntryDays', () => {
    const TODAY = '2026-07-01';

    it('counts the range of an item that reads prices, and adds the margin for signals', () => {
        const [plain] = buildReducedQuery([card(7)]);
        const [signalled] = buildReducedQuery([card(7, {signals: [EMA]})]);

        expect(estimateEntryDays(plain, TODAY)).toBe(181);
        expect(estimateEntryDays(signalled, TODAY)).toBe(181 + BULK_SIGNAL_MARGIN_DAYS);
    });

    it('counts a placeholder, which only says its step, as nothing', () => {
        const [placeholder] = buildReducedQuery([card(7, {needsPrice: false, targets: [{assetId: 9, needsRead: true}]})]);

        expect(estimateEntryDays(placeholder, TODAY)).toBe(0);
    });
});

describe('comparisonTargetIds', () => {
    const comparison = (assetId: unknown) => ({signalType: 'asset-comparison', params: {assetId}});

    it('lists the assets of the comparison signals, once each, in order, without the card’s own and the unset', () => {
        const configs = [comparison('9'), {signalType: 'sma', params: {period: 5}}, comparison(11), comparison(9), comparison(7), comparison(''), comparison(undefined)];

        expect(comparisonTargetIds(configs as never, 7)).toEqual([9, 11]);
    });

    it('lists nothing for a card without comparisons', () => {
        expect(comparisonTargetIds([], 7)).toEqual([]);
    });
});

describe('comparisonTargetFrom', () => {
    const NAMES = {displayName: 'Nine', iconUrl: null, assetType: 'STOCK'};
    const chartData = [
        {date: '2026-01-11', value: 104, staleDays: 0},
        {date: '2026-01-18', value: 108, staleDays: 2},
    ];

    it('gives a sampled target its series and, as the percentage base, its point on the first day: the one the series does not draw', () => {
        const target = comparisonTargetFrom({resolution: 'weekly', derived: {lastPrice: 108, chartData, base: {date: '2026-01-07', value: 100}}}, NAMES);

        expect(target?.data).toEqual(chartData);
        expect(target?.basePoint).toEqual({date: '2026-01-07', value: 100});
        expect([target?.displayName, target?.assetType]).toEqual(['Nine', 'STOCK']);
    });

    it('gives a daily target no base point: its first point is the day the comparison starts', () => {
        const target = comparisonTargetFrom({resolution: 'daily', derived: {lastPrice: 108, chartData, base: {date: '2026-01-11', value: 104}}}, NAMES);

        expect(target?.basePoint).toBeNull();
    });

    it('gives nothing for an empty series', () => {
        expect(comparisonTargetFrom({resolution: 'weekly', derived: {lastPrice: null, chartData: [], base: null}}, NAMES)).toBeNull();
    });
});

describe('cardsOfAnotherStep (MF n2)', () => {
    /** A card that reports what it holds; `holds` answers for the max_points asked of it. */
    const probe =
        (extra: Partial<ReturnType<Parameters<typeof cardsOfAnotherStep>[1]>> = {}) =>
        () => ({settled: true, plotWidthPx: 290, holds: () => false, reloadedForWidth: false, ...extra});

    it('lists the cards whose series does not hold for the max_points of their width, asked with it', () => {
        const asked: number[] = [];
        const read = probe({
            holds: (maxPoints) => {
                asked.push(maxPoints);
                return false;
            },
        });

        expect(cardsOfAnotherStep([1, 2], read)).toEqual([1, 2]);
        expect(asked).toEqual([377, 377]);
    });

    it('leaves out a card whose series holds: a resize that keeps the step reads nothing', () => {
        expect(cardsOfAnotherStep([1], probe({holds: () => true}))).toEqual([]);
    });

    it('leaves out a card still loading or without a series, one not measured, and one already read again for this width', () => {
        expect(cardsOfAnotherStep([1], probe({settled: false}))).toEqual([]);
        expect(cardsOfAnotherStep([1], probe({plotWidthPx: undefined}))).toEqual([]);
        expect(cardsOfAnotherStep([1], probe({reloadedForWidth: true}))).toEqual([]);
    });

    it('lists a card once, in the order given', () => {
        expect(cardsOfAnotherStep([3, 1, 3], probe())).toEqual([3, 1]);
    });
});

describe('signalBaseData (MF n3, backlog O2)', () => {
    const chart = [
        {date: '2026-01-11', value: 104},
        {date: '2026-01-18', value: 108},
    ];

    it('hands a sampled card’s backend signals the point on the first day as their percentage base, not the first bucket’s point', () => {
        // The renderer measures a base_percentage series from the first point it is given as the chart's data.
        expect(signalBaseData(chart, {date: '2026-01-07', value: 100}, 'weekly')).toEqual([{date: '2026-01-07', value: 100}]);
        expect(signalBaseData(chart, {date: '2026-01-07', value: 100}, 'monthly')).toEqual([{date: '2026-01-07', value: 100}]);
    });

    it('leaves a daily card’s data alone: its first point is the first day', () => {
        expect(signalBaseData(chart, {date: '2026-01-11', value: 104}, 'daily')).toBe(chart);
        expect(signalBaseData(chart, {date: '2026-01-11', value: 104}, undefined)).toBe(chart);
    });

    it('leaves the data alone without a base', () => {
        expect(signalBaseData(chart, null, 'weekly')).toBe(chart);
        expect(signalBaseData(chart, undefined, 'weekly')).toBe(chart);
    });
});

/**
 * Y-40 — a card in the rolling-return view. The card asks its own rolling return as a backend signal (the page puts it in
 * `signals`), and each comparison target asks its rolling return on the card's buckets: an item `sample_like` the card,
 * with the signal, no prices — the target's price sample is not drawn in this view, and its cache is not its to fill — and
 * in the card's currency, as the detail page asks its comparisons (`target_currency`). Every target is sent, cached or
 * not: a signal is never cached.
 *
 * Red today: `CardQueryInput` has no `calendar`.
 */
describe('buildReducedQuery: a card in the rolling-return view (Y-40)', () => {
    const CAL = {instance_id: 'asset-calendar-return', signal_code: 'ASSET_CALENDAR_ROLLING_RETURN', params: {window_days: 90}};
    const calendarCard = (extra: Partial<CardQueryInput> = {}): CardQueryInput =>
        ({
            ...card(7, {
                needsPrice: false,
                signals: [CAL],
                targets: [
                    {assetId: 9, needsRead: false},
                    {assetId: 11, needsRead: true},
                ],
            }),
            calendar: {signals: [CAL], targetCurrency: 'EUR'},
            ...extra,
        }) as CardQueryInput;

    it('sends each target, cached or not, with the rolling return and no prices, in the card’s currency, sampled like the card', () => {
        const entries = buildReducedQuery([calendarCard()]);

        expect(entries.map((entry) => entry.item)).toEqual([
            {asset_id: 7, date_range: RANGE, include_price: false, signals: [CAL], key: 'asset:7', max_points: 377},
            {asset_id: 9, date_range: RANGE, include_price: false, signals: [CAL], sample_like: 'asset:7', target_currency: 'EUR'},
            {asset_id: 11, date_range: RANGE, include_price: false, signals: [CAL], sample_like: 'asset:7', target_currency: 'EUR'},
        ]);
        expect(entries.map((entry) => [entry.role, entry.targetId])).toEqual([
            ['card', null],
            ['target', 9],
            ['target', 11],
        ]);
    });

    it('counts a target’s rolling return against the day budget: its range and the signals’ margin', () => {
        const [, target] = buildReducedQuery([calendarCard()]);

        expect(estimateEntryDays(target, '2026-06-30')).toBe(estimateEntryDays({...target, item: {...target.item, include_price: true}}, '2026-06-30'));
        expect(estimateEntryDays(target, '2026-06-30')).toBeGreaterThan(BULK_SIGNAL_MARGIN_DAYS);
    });

    it('guard: a card in the price views sends its targets as before', () => {
        const entries = buildReducedQuery([card(7, {targets: [{assetId: 9, needsRead: true}]})]);

        expect(entries[1].item).toEqual({asset_id: 9, date_range: RANGE, include_price: true, signals: [], sample_like: 'asset:7'});
    });
});
