/**
 * crossTypeCalendar.ts (lot FB-11): the rolling return of the OTHER type on a detail page, as pure request builders.
 *
 * The rolling-return view of an asset detail compared only assets, and the FX pair detail only FX pairs. A comparison of the
 * other type is asked the way that page's own type is:
 *
 * - `buildFxPairComparisonQuery(input)` (asset detail → `POST /fx/currencies/convert`): one conversion per saved `fx-pair`
 *   signal, 1 unit in the direction the signal shows the pair (`EUR-GBP` is EUR → GBP, inverted GBP → EUR), over the range, with
 *   the calendar rolling return of the window as its only signal; no key, no `max_points`, no `sample_like`. A pair that is empty
 *   or malformed (not exactly two codes) is skipped, and the entries keep the targets' order. `fxPairComparisonViews(answer,
 *   entries)` reads the view of each entry by `request_index`, keyed by the signal's id: a pair with no answer is absent.
 * - `buildAssetComparisonQuery(input)` (FX detail → `POST /assets/prices/query`): one item per distinct asset, the page's own
 *   range and window, no prices and no events, the calendar rolling return as its only signal, in the asset's own currency.
 *
 * Red first: the module does not exist.
 */
import {describe, expect, it} from 'vitest';
import {CALENDAR_RETURN_INSTANCE_ID, CALENDAR_RETURN_SIGNAL_CODE} from '$lib/features/signals/calendarReturn';
import {buildAssetComparisonQuery, buildFxPairComparisonQuery, buildListFxPairComparisonQuery, fxPairComparisonViews, listFxPairComparisonViews, estimateListFxPairDays} from '../crossTypeCalendar';

const signal = (windowDays: number) => ({instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, params: {window_days: windowDays}});
const target = (configId: string, pairSlug: string, inverted = false) => ({configId, pairSlug, inverted});
const range = {start: '2026-01-01', end: '2026-06-30'};

describe('buildFxPairComparisonQuery: one conversion per compared pair', () => {
    it('asks 1 unit of the first code into the second, over the range, with the calendar return of the window', () => {
        const entries = buildFxPairComparisonQuery({...range, windowDays: 30, pairTargets: [target('cfg-1', 'EUR-GBP')]});

        expect(entries).toEqual([{request: {from_amount: {code: 'EUR', amount: '1'}, to: 'GBP', date_range: range, signals: [signal(30)]}, configId: 'cfg-1'}]);
    });

    it('asks an inverted pair the other way round, and keeps the targets’ order', () => {
        const entries = buildFxPairComparisonQuery({...range, windowDays: 90, pairTargets: [target('a', 'EUR-USD'), target('b', 'EUR-CHF', true)]});

        expect(entries.map((e) => [e.configId, e.request.from_amount.code, e.request.to])).toEqual([
            ['a', 'EUR', 'USD'],
            ['b', 'CHF', 'EUR'],
        ]);
    });

    it('skips an empty or malformed pair, and asks nothing for no target', () => {
        expect(buildFxPairComparisonQuery({...range, windowDays: 90, pairTargets: []})).toEqual([]);
        const entries = buildFxPairComparisonQuery({...range, windowDays: 90, pairTargets: [target('a', ''), target('b', 'EUR'), target('c', 'EUR-USD-GBP'), target('d', 'EUR-JPY')]});
        expect(entries.map((e) => e.configId)).toEqual(['d']);
    });

    it('names no key, no max_points and no sample_like: it asks the daily return', () => {
        const [entry] = buildFxPairComparisonQuery({...range, windowDays: 90, pairTargets: [target('a', 'EUR-USD')]});

        expect(Object.keys(entry.request).sort()).toEqual(['date_range', 'from_amount', 'signals', 'to']);
    });
});

describe('fxPairComparisonViews: the views by signal id', () => {
    const entries = buildFxPairComparisonQuery({...range, windowDays: 90, pairTargets: [target('a', 'EUR-USD'), target('b', 'EUR-GBP')]});

    it('reads the answer of each entry by its position, and leaves out a pair with no answer', () => {
        const answer = {signal_results: [{request_index: 1, signals: []}]};

        const views = fxPairComparisonViews(answer, entries);

        expect([...views.keys()]).toEqual(['b']);
    });

    it('an answer that is no object gives no view at all', () => {
        expect(fxPairComparisonViews(null, entries).size).toBe(0);
        expect(fxPairComparisonViews('nope', entries).size).toBe(0);
    });
});

describe('buildAssetComparisonQuery: one item per distinct asset', () => {
    it('asks the calendar return of each asset, no prices and no events, over the range', () => {
        const body = buildAssetComparisonQuery({...range, windowDays: 30, assetIds: [7, 9]});

        expect(body).toEqual([
            {asset_id: 7, date_range: range, include_price: false, include_events: false, signals: [signal(30)]},
            {asset_id: 9, date_range: range, include_price: false, include_events: false, signals: [signal(30)]},
        ]);
    });

    it('asks an asset once, however many signals compare it, in order of first appearance', () => {
        expect(buildAssetComparisonQuery({...range, windowDays: 90, assetIds: [9, 7, 9]}).map((item) => item.asset_id)).toEqual([9, 7]);
    });

    it('asks nothing for no asset', () => {
        expect(buildAssetComparisonQuery({...range, windowDays: 90, assetIds: []})).toEqual([]);
    });
});

describe('buildListFxPairComparisonQuery: one request for the pairs of every card of a list (FB-11 follow-up)', () => {
    const card = (cardKey: string, windowDays: number, pairTargets: ReturnType<typeof target>[], span = range) => ({cardKey, ...span, windowDays, pairTargets});

    it('asks the pairs of all the cards in one list, each entry owned by its card and signal', () => {
        const entries = buildListFxPairComparisonQuery([card('asset-1', 30, [target('a', 'EUR-USD')]), card('asset-2', 30, [target('b', 'EUR-GBP', true)])]);

        expect(entries.map((e) => [e.request.from_amount.code, e.request.to, e.owners])).toEqual([
            ['EUR', 'USD', [{cardKey: 'asset-1', configId: 'a'}]],
            ['GBP', 'EUR', [{cardKey: 'asset-2', configId: 'b'}]],
        ]);
    });

    it('shares one request between cards that compare the same pair the same way over the same window', () => {
        const entries = buildListFxPairComparisonQuery([card('asset-1', 30, [target('a', 'EUR-USD')]), card('asset-2', 30, [target('b', 'EUR-USD')]), card('asset-3', 90, [target('c', 'EUR-USD')])]);

        expect(entries).toHaveLength(2);
        expect(entries[0].owners).toEqual([
            {cardKey: 'asset-1', configId: 'a'},
            {cardKey: 'asset-2', configId: 'b'},
        ]);
        expect(entries[1].owners).toEqual([{cardKey: 'asset-3', configId: 'c'}]);
    });

    it('asks nothing when no card compares a pair', () => {
        expect(buildListFxPairComparisonQuery([card('asset-1', 30, [])])).toEqual([]);
        expect(buildListFxPairComparisonQuery([])).toEqual([]);
    });

    it('estimates a request by its range, for the batches', () => {
        const [entry] = buildListFxPairComparisonQuery([card('asset-1', 30, [target('a', 'EUR-USD')])]);
        expect(estimateListFxPairDays(entry, '2026-07-01')).toBeGreaterThan(170);
    });
});

describe('listFxPairComparisonViews: the views by card, then by signal id', () => {
    const entries = buildListFxPairComparisonQuery([
        {cardKey: 'asset-1', ...range, windowDays: 30, pairTargets: [target('a', 'EUR-USD')]},
        {cardKey: 'asset-2', ...range, windowDays: 30, pairTargets: [target('b', 'EUR-USD'), target('c', 'EUR-GBP')]},
    ]);

    it('gives each owner of an answered entry its view, and leaves out an entry with no answer', () => {
        const views = listFxPairComparisonViews([{entries, answer: {signal_results: [{request_index: 0, signals: []}]}}]);

        expect([...views.keys()].sort()).toEqual(['asset-1', 'asset-2']);
        expect([...views.get('asset-1')!.keys()]).toEqual(['a']);
        expect([...views.get('asset-2')!.keys()]).toEqual(['b']);
    });

    it('reads each batch against its own entries: a request_index is local to its request', () => {
        const views = listFxPairComparisonViews([
            {entries: [entries[0]], answer: {signal_results: [{request_index: 0, signals: []}]}},
            {entries: [entries[1]], answer: {signal_results: [{request_index: 0, signals: []}]}},
        ]);

        expect([...views.get('asset-2')!.keys()]).toEqual(['b', 'c']);
    });

    it('an answer that is no object gives no view', () => {
        expect(listFxPairComparisonViews([{entries, answer: null}]).size).toBe(0);
    });
});
