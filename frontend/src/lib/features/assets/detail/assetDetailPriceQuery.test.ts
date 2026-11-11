/**
 * Contract tests for the readings of the bulk price query answer on the asset detail page
 * (FE5c, piece 2). The bodies moved out of the page verbatim; the page's assets and display
 * currency now come in as `context`, and the items are looked up through one private helper.
 *
 * - Signal isolation: an invalid signal result never costs its item the prices, and the item is
 *   handed back with its raw signals so the page can still report the invalid ones.
 * - The FX conversion error of an item, then for each comparison peer: its calendar-return
 *   problem, its FX failure, and its last factual calendar view while a refresh reports it
 *   unavailable.
 *
 * Real schemas throughout: the fixtures are valid, or deliberately invalid, against the generated
 * `FAPriceQueryResult` and `SignalResult`, and the item errors copy the backend's own wording
 * (`price_query.py`, `fx/conversion.py`). Problems are asserted by code, never by a sentence.
 *
 * The last two blocks (N64) are the two helpers the page hands the client cache of signal answers
 * (`$lib/stores/signalResultCache`):
 * - `assetChartAnswerKey(body)`: which answer a request asks for. The request body the page posts, canonical, with
 *   each item's `include_price` removed — whether the prices travel or come from the price store does not change which
 *   signal answer it is — and so different for anything that does: the range, the target currency, a signal's id or
 *   params, a comparison peer. The order of the signals is not pinned.
 * - `assetChartAnswerForCache(answer)`: what the cache keeps of an answer, its items without `prices` (the price store
 *   holds them), every other field kept, the input untouched.
 *
 * Red first: both are read by name, so that their absence fails each case with the contract in the message, and the
 * type check does not wait for them.
 */
import {describe, expect, it} from 'vitest';
import type {SignalConfig} from '$lib/charts/signals';
import {CALENDAR_RETURN_INSTANCE_ID, CALENDAR_RETURN_SIGNAL_CODE, emptyCalendarReturnView, type CalendarReturnView, type CalendarReturnViewState} from '$lib/components/charts/priceChartHelpers';
import * as priceQuery from './assetDetailPriceQuery';
import {calendarComparisonFxFailuresFromResponse, calendarComparisonProblemsFromResponse, parseAssetPriceQueryWithSignalIsolation, preserveFactualCalendarPeersForCurrentUnavailable, priceConversionErrorFromItem, type CalendarComparisonContext} from './assetDetailPriceQuery';

type ViewPoint = CalendarReturnView['points'][number];

/** A price conversion failure, as the backend words it. */
const FX_ERROR = 'Conversion 0: No FX rate found for USD/EUR on or before 2026-02-02. Please sync rates using POST /api/v1/fx/currencies/sync';
/** An event conversion failure, as the backend words it: about an event, not about the prices. */
const EVENT_FX_ERROR = 'Missing FX rate USD->EUR for event on 2026-01-05';
/** A warning about something else than a conversion. */
const OTHER_ERROR = 'Provider timeout while loading prices';

/** The chart shows EUR. Peer 7 is in USD, 8 in EUR, 9 has no currency, 10 a null one; 11 is not a known asset. */
const CONTEXT: CalendarComparisonContext = {
    assets: [{id: 7, currency: 'USD'}, {id: 8, currency: 'EUR'}, {id: 9}, {id: 10, currency: null}],
    displayCurrency: 'EUR',
};

/** A price query item `FAPriceQueryResult` accepts. */
function priceItem(assetId: number, overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {asset_id: assetId, prices: [{date: '2026-02-02', close: '101.5'}], ...overrides};
}

/** A signal result `SignalResult` accepts. */
function signalResult(instanceId: string, overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {instance_id: instanceId, signal_code: 'SMA', status: 'ok', ...overrides};
}

function signalConfig(id: string, signalType: string, params: Record<string, unknown>): SignalConfig {
    return {id, signalType, params, style: {}} as unknown as SignalConfig;
}

function comparisonConfig(assetId: unknown): SignalConfig {
    return signalConfig(`cmp-${String(assetId)}`, 'asset-comparison', {assetId});
}

/** The calendar-return result of a peer; `ok` with no series unless told otherwise. */
function calendarResult(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, status: 'ok', ...overrides};
}

/** A typed `unavailable` calendar result whose availability gives `reasonCode`. */
function unavailableCalendarResult(reasonCode: string, missingPriceFields: string[] = []): Record<string, unknown> {
    return calendarResult({
        status: 'unavailable',
        series: [],
        availability: {
            domain_compatible: true,
            can_compute: false,
            missing_price_fields: missingPriceFields,
            input_coverage: {
                requested_points: 4,
                available_points: 0,
                contiguous_points: 0,
                observed_points: 0,
                backfilled_points: 0,
                missing_points: 4,
                max_consecutive_missing_points: 4,
                internal_gap_count: 0,
                coverage_ratio: 0,
                field_coverage: {close: 0},
            },
            required_points: 7,
            warmup_complete: false,
            reason_code: reasonCode,
        },
    });
}

/** A typed `failed` calendar result carrying `message` as its error. */
function failedCalendarResult(message: string): Record<string, unknown> {
    return calendarResult({status: 'failed', series: [], error: {code: 'compute_error', message}});
}

/** The problems of `assetIds`, each with a comparison config, no strict view and `CONTEXT` unless told otherwise. */
function problemsFor(responseItems: unknown[], assetIds: number[], options: {configs?: SignalConfig[]; views?: ReadonlyMap<number, CalendarReturnView>; context?: CalendarComparisonContext} = {}) {
    return calendarComparisonProblemsFromResponse(responseItems, options.configs ?? assetIds.map((assetId) => comparisonConfig(assetId)), assetIds, options.views ?? new Map(), options.context ?? CONTEXT);
}

function factualPoint(date: string, value: number): ViewPoint {
    return {date, value};
}

function missingPoint(date: string): ViewPoint {
    return {date, value: 0, missing: true};
}

function viewOf(state: CalendarReturnViewState, points: ViewPoint[] = []): CalendarReturnView {
    return {...emptyCalendarReturnView(state), points};
}

describe('parseAssetPriceQueryWithSignalIsolation: a malformed answer, items list, item or signal collection throws', () => {
    it.each([
        {label: 'null', data: null},
        {label: 'undefined', data: undefined},
        {label: 'an array', data: [priceItem(7)]},
        {label: 'a string', data: 'items'},
        {label: 'a number', data: 7},
    ])('rejects $label as the answer', ({data}) => {
        expect(() => parseAssetPriceQueryWithSignalIsolation(data)).toThrow(/^Invalid Asset price query response$/);
    });

    it.each([
        {label: 'null', items: null},
        {label: 'an object', items: {0: priceItem(7)}},
        {label: 'a string', items: 'items'},
    ])('rejects $label as the items', ({items}) => {
        expect(() => parseAssetPriceQueryWithSignalIsolation({items})).toThrow(/^Invalid Asset price query items$/);
    });

    it('rejects an item that is not a plain object, naming its index', () => {
        expect(() => parseAssetPriceQueryWithSignalIsolation({items: [priceItem(7), null]})).toThrow(/^Invalid Asset price query item at index 1$/);
        expect(() => parseAssetPriceQueryWithSignalIsolation({items: [[priceItem(7)]]})).toThrow(/^Invalid Asset price query item at index 0$/);
        expect(() => parseAssetPriceQueryWithSignalIsolation({items: [priceItem(7), priceItem(8), 'item']})).toThrow(/^Invalid Asset price query item at index 2$/);
    });

    it('rejects a signal collection that is not an array, naming the item index', () => {
        expect(() => parseAssetPriceQueryWithSignalIsolation({items: [priceItem(7), priceItem(8, {signals: {}})]})).toThrow(/^Invalid Asset signal collection at item index 1$/);
        expect(() => parseAssetPriceQueryWithSignalIsolation({items: [priceItem(7, {signals: null})]})).toThrow(/^Invalid Asset signal collection at item index 0$/);
        expect(() => parseAssetPriceQueryWithSignalIsolation({items: [priceItem(7, {signals: 'signals'})]})).toThrow(/^Invalid Asset signal collection at item index 0$/);
    });

    it.each([
        {label: 'without an asset id', item: {prices: [{date: '2026-02-02', close: '101.5'}]}},
        {label: 'with a numeric close', item: priceItem(8, {prices: [{date: '2026-02-02', close: 101.5}]})},
        {label: 'with errors that are not a list', item: priceItem(8, {errors: FX_ERROR})},
    ])('rejects an item $label as the schema does, naming its index', ({item}) => {
        expect(() => parseAssetPriceQueryWithSignalIsolation({items: [priceItem(7), item]})).toThrow(/^Invalid Asset price query item at index 1$/);
    });
});

describe('parseAssetPriceQueryWithSignalIsolation: each item is validated with its valid signals only, and returned with its raw signals', () => {
    it('gives no items when the answer has none', () => {
        expect(parseAssetPriceQueryWithSignalIsolation({})).toEqual({items: []});
        expect(parseAssetPriceQueryWithSignalIsolation({items: undefined})).toEqual({items: []});
        expect(parseAssetPriceQueryWithSignalIsolation({items: []})).toEqual({items: []});
    });

    it('keeps the prices of an item whose signals include an invalid one, and returns the raw signals', () => {
        // Each signal differs from what the schema would return: the first has a key the schema
        // drops, the second fails the schema, the third lacks a field the schema defaults.
        const valid = signalResult('sma-20', {note_from_backend: 'a key the schema does not know'});
        const invalid = signalResult('cci-14', {status: 'not-a-status'});
        const failed = signalResult('rsi-14', {status: 'failed', error: {code: 'compute_error', message: 'RSI computation failed'}});

        const {items} = parseAssetPriceQueryWithSignalIsolation({items: [priceItem(7, {signals: [valid, invalid, failed]})]});

        expect(items).toEqual([{asset_id: 7, prices: [{date: '2026-02-02', close: '101.5'}], signals: [valid, invalid, failed], resolution: 'daily'}]);
    });

    it('returns the schema output for the rest of the item', () => {
        const {items} = parseAssetPriceQueryWithSignalIsolation({items: [priceItem(7, {errors: [FX_ERROR], unknown_field: 'a key the schema does not know'})]});

        expect(items).toEqual([{asset_id: 7, prices: [{date: '2026-02-02', close: '101.5'}], errors: [FX_ERROR], signals: [], resolution: 'daily'}]);
        expect(items.find((item) => item.asset_id === 7)).not.toHaveProperty('unknown_field');
    });

    it('gives an item without signals an empty signal list', () => {
        const {items} = parseAssetPriceQueryWithSignalIsolation({items: [priceItem(7)]});

        expect(items).toEqual([{asset_id: 7, prices: [{date: '2026-02-02', close: '101.5'}], signals: [], resolution: 'daily'}]);
    });

    it('keeps the items in the order of the answer', () => {
        const {items} = parseAssetPriceQueryWithSignalIsolation({items: [priceItem(9), priceItem(7), priceItem(8)]});

        expect(items.map((item) => item.asset_id)).toEqual([9, 7, 8]);
    });

    it('keeps the resolution an item sends, defaults a missing one to daily, and adds no sample bounds', () => {
        // Z-29: `resolution` is the step of `prices`. The schema defaults it, so an item that does
        // not name its step reads as daily, an unsampled series; `sample_bounds` has no default.
        const {items} = parseAssetPriceQueryWithSignalIsolation({items: [priceItem(7, {resolution: 'weekly'}), priceItem(8)]});

        expect(items).toEqual([
            {asset_id: 7, prices: [{date: '2026-02-02', close: '101.5'}], signals: [], resolution: 'weekly'},
            {asset_id: 8, prices: [{date: '2026-02-02', close: '101.5'}], signals: [], resolution: 'daily'},
        ]);
        expect(items.find((item) => item.asset_id === 7)).not.toHaveProperty('sample_bounds');
        expect(items.find((item) => item.asset_id === 8)).not.toHaveProperty('sample_bounds');
    });
});

describe('priceConversionErrorFromItem: the first string error, when it is about FX, conversion or currency and not about an event', () => {
    it.each([
        {label: 'a price conversion failure', error: FX_ERROR},
        {label: 'an FX rate', error: 'FX rate USD/EUR unavailable for 2026-02-02'},
        {label: 'a currency route', error: 'No currency route from GBP to EUR'},
        {label: 'mixed currencies, in capitals', error: 'Technical signal computation excluded unconverted price dates because the series contains MIXED CURRENCIES: EUR, USD'},
    ])('returns an error about $label', ({error}) => {
        expect(priceConversionErrorFromItem({asset_id: 7, errors: [error]})).toBe(error);
    });

    it('skips the entries that are not strings', () => {
        expect(priceConversionErrorFromItem({asset_id: 7, errors: [42, null, {message: FX_ERROR}, FX_ERROR]})).toBe(FX_ERROR);
    });

    it('reads only the first string error', () => {
        expect(priceConversionErrorFromItem({asset_id: 7, errors: [OTHER_ERROR, FX_ERROR]})).toBeUndefined();
        expect(priceConversionErrorFromItem({asset_id: 7, errors: [EVENT_FX_ERROR, FX_ERROR]})).toBeUndefined();
    });

    it.each([
        {label: 'an event conversion failure', errors: [EVENT_FX_ERROR]},
        {label: 'an event conversion failure in capitals', errors: ['MISSING FX RATE USD->EUR FOR EVENT ON 2026-01-05']},
        {label: 'an error about something else', errors: [OTHER_ERROR]},
        {label: 'a word that only contains the letters fx', errors: ['Provider ETFX feed unavailable']},
        {label: 'no string error', errors: [404, null]},
        {label: 'an empty error list', errors: []},
    ])('gives nothing for $label', ({errors}) => {
        expect(priceConversionErrorFromItem({asset_id: 7, errors})).toBeUndefined();
    });

    it('gives nothing without an item, without errors, or with errors that are not a list', () => {
        expect(priceConversionErrorFromItem(undefined)).toBeUndefined();
        expect(priceConversionErrorFromItem({asset_id: 7})).toBeUndefined();
        expect(priceConversionErrorFromItem({asset_id: 7, errors: FX_ERROR})).toBeUndefined();
    });
});

describe('calendarComparisonProblemsFromResponse: the calendar-return problem of each comparison peer by asset id; a missing or invalid result is result_missing, a peer with no problem is absent', () => {
    it('reads only the peers with an asset-comparison config', () => {
        const configs = [comparisonConfig(7), signalConfig('fx-8', 'fx-pair', {assetId: 8}), comparisonConfig('10')];

        const problems = problemsFor([], [7, 8, 9, 10], {configs});

        expect([...problems.keys()]).toEqual([7, 10]);
        expect(problems.get(7)).toMatchObject({code: 'result_missing', status: 'missing'});
        expect(problems.get(10)).toMatchObject({code: 'result_missing', status: 'missing'});
    });

    it.each([
        {label: 'the peer has no item in the answer', items: [priceItem(8, {signals: [calendarResult()]})]},
        {label: 'the item has no signals', items: [priceItem(7)]},
        {label: 'the item signals are not a list', items: [priceItem(7, {signals: calendarResult()})]},
        {label: 'the item has only other signal results', items: [priceItem(7, {signals: [signalResult('sma-20'), calendarResult({instance_id: 'another-calendar'}), calendarResult({signal_code: 'RISK_ROLLING_RETURN'})]})]},
        {label: 'the calendar result has an unknown status', items: [priceItem(7, {signals: [calendarResult({status: 'not-a-status'})]})]},
        {label: 'the calendar result has a series without a kind', items: [priceItem(7, {signals: [calendarResult({series: [{key: 'calendar_return', points: []}]})]})]},
        {label: 'the failed calendar result is itself invalid', items: [priceItem(7, {signals: [calendarResult({status: 'failed', error: {code: 'not-an-error-code', message: 'Calendar computation failed'}})]})]},
    ])('reports result_missing when $label', ({items}) => {
        expect(problemsFor(items, [7]).get(7)).toMatchObject({code: 'result_missing', status: 'missing'});
    });

    it('leaves out a peer whose calendar result is ok, and carries the error message of a failed one', () => {
        const problems = problemsFor([priceItem(7, {signals: [calendarResult()]}), priceItem(8, {signals: [failedCalendarResult('Calendar computation failed')]})], [7, 8]);

        expect(problems.has(7)).toBe(false);
        expect(problems.get(8)).toMatchObject({code: 'calculation_failed', status: 'failed', message: 'Calendar computation failed'});
    });

    it('finds the item of each peer by asset id, past entries that are not items', () => {
        const problems = problemsFor([null, 'item', priceItem(8, {signals: [failedCalendarResult('Peer 8 failed')]}), priceItem(7, {signals: [calendarResult()]})], [7, 8]);

        expect(problems.has(7)).toBe(false);
        expect(problems.get(8)).toMatchObject({code: 'calculation_failed', message: 'Peer 8 failed'});
    });

    it('reads the problem of the result itself while the strict view is not error', () => {
        const views = new Map([
            [7, viewOf('unavailable')],
            [8, viewOf('ready', [factualPoint('2026-02-02', 1.5)])],
        ]);

        const problems = problemsFor([priceItem(7, {signals: [unavailableCalendarResult('undefined_metric')]}), priceItem(8, {signals: [calendarResult()]})], [7, 8], {views});

        expect(problems.get(7)).toMatchObject({code: 'undefined_metric', status: 'unavailable'});
        expect(problems.has(8)).toBe(false);
    });

    it.each([
        {label: 'an ok result', result: calendarResult()},
        {label: 'an unavailable result', result: unavailableCalendarResult('undefined_metric')},
    ])('reports $label as result_missing when the strict view of the peer is error', ({result}) => {
        const views = new Map([[7, viewOf('error')]]);

        expect(problemsFor([priceItem(7, {signals: [result]})], [7], {views}).get(7)).toMatchObject({code: 'result_missing', status: 'missing'});
    });

    it('keeps a failed result as calculation_failed when the strict view is error', () => {
        const views = new Map([[7, viewOf('error')]]);

        expect(problemsFor([priceItem(7, {signals: [failedCalendarResult('Calendar computation failed')]})], [7], {views}).get(7)).toMatchObject({code: 'calculation_failed', status: 'failed'});
    });
});

describe('calendarComparisonProblemsFromResponse: missing_input_fields becomes fx_conversion_unavailable, with the conversion error as message, when the peer currency failed to convert to the shown one', () => {
    /** The problem of a peer whose calendar result misses its close, with `errors` on its item. */
    function missingFieldsProblem(assetId: number, errors: unknown[], context: CalendarComparisonContext = CONTEXT) {
        const item = priceItem(assetId, {errors, signals: [unavailableCalendarResult('missing_input_fields', ['close'])]});
        return problemsFor([item], [assetId], {context}).get(assetId);
    }

    it('rewrites the code and the message, and keeps the rest of the problem', () => {
        const base = missingFieldsProblem(7, []);
        expect(base).toMatchObject({code: 'missing_input_fields', status: 'unavailable', missingPriceFields: ['close']});

        expect(missingFieldsProblem(7, [FX_ERROR])).toEqual({...base, code: 'fx_conversion_unavailable', message: FX_ERROR});
    });

    it.each([
        {label: 'the peer shares the shown currency', assetId: 8, errors: [FX_ERROR], context: CONTEXT},
        {label: 'the peer has no currency', assetId: 9, errors: [FX_ERROR], context: CONTEXT},
        {label: 'the peer currency is null', assetId: 10, errors: [FX_ERROR], context: CONTEXT},
        {label: 'the peer is not a known asset', assetId: 11, errors: [FX_ERROR], context: CONTEXT},
        {label: 'no currency is shown', assetId: 7, errors: [FX_ERROR], context: {...CONTEXT, displayCurrency: ''}},
        {label: 'the item error is not about a conversion', assetId: 7, errors: [OTHER_ERROR], context: CONTEXT},
        {label: 'the item error is about an event', assetId: 7, errors: [EVENT_FX_ERROR], context: CONTEXT},
    ])('keeps missing_input_fields when $label', ({assetId, errors, context}) => {
        expect(missingFieldsProblem(assetId, errors, context)).toMatchObject({code: 'missing_input_fields'});
    });

    it('rewrites no other problem', () => {
        expect(problemsFor([priceItem(7, {errors: [FX_ERROR], signals: [unavailableCalendarResult('undefined_metric')]})], [7]).get(7)).toMatchObject({code: 'undefined_metric'});
        expect(problemsFor([priceItem(7, {errors: [FX_ERROR], signals: [failedCalendarResult('Calendar computation failed')]})], [7]).get(7)).toMatchObject({code: 'calculation_failed'});
        expect(problemsFor([priceItem(7, {errors: [FX_ERROR]})], [7]).get(7)).toMatchObject({code: 'result_missing'});
    });
});

describe('calendarComparisonFxFailuresFromResponse: the peers whose item reports a conversion error; a peer absent from the answer keeps its previous outcome', () => {
    it('lists the peers whose item has a conversion error', () => {
        const items = [priceItem(7, {errors: [FX_ERROR]}), priceItem(8, {errors: [OTHER_ERROR]}), priceItem(9), priceItem(10, {errors: [EVENT_FX_ERROR]})];

        expect(calendarComparisonFxFailuresFromResponse(items, [7, 8, 9, 10], new Set())).toEqual(new Set([7]));
    });

    it('keeps the previous outcome of a peer absent from the answer, and only of such a peer', () => {
        // 7 fails now; 8 failed before and is fine now; 11 is absent and failed before; 12 is absent and did not.
        const failures = calendarComparisonFxFailuresFromResponse([priceItem(7, {errors: [FX_ERROR]}), priceItem(8)], [7, 8, 11, 12], new Set([8, 11]));

        expect(failures).toEqual(new Set([7, 11]));
    });

    it('reads only the given peers', () => {
        const failures = calendarComparisonFxFailuresFromResponse([priceItem(7, {errors: [FX_ERROR]}), priceItem(13, {errors: [FX_ERROR]})], [7], new Set([14]));

        expect(failures).toEqual(new Set([7]));
    });

    it('finds the item of each peer by asset id, past entries that are not items', () => {
        expect(calendarComparisonFxFailuresFromResponse([null, 'item', priceItem(7, {errors: [FX_ERROR]})], [7], new Set())).toEqual(new Set([7]));
    });

    it('returns a new set and leaves the previous one untouched', () => {
        const previous = new Set([7]);

        const failures = calendarComparisonFxFailuresFromResponse([priceItem(8, {errors: [FX_ERROR]})], [7, 8], previous);

        expect(failures).toEqual(new Set([7, 8]));
        expect(failures).not.toBe(previous);
        expect(previous).toEqual(new Set([7]));
    });
});

describe('preserveFactualCalendarPeersForCurrentUnavailable: a peer reported unavailable keeps its previous view when that view was ready or partial with a factual point and the peer is in the answer', () => {
    /** The merge for peer 7 alone, present in the answer. */
    function mergeFor(previous: CalendarReturnView, next: CalendarReturnView) {
        return preserveFactualCalendarPeersForCurrentUnavailable(new Map([[7, previous]]), new Map([[7, next]]), [priceItem(7)], [7]);
    }

    it.each([
        {label: 'ready view', previous: viewOf('ready', [factualPoint('2026-02-02', 1.5)])},
        {label: 'partial view with one factual point among missing ones', previous: viewOf('partial', [missingPoint('2026-02-01'), factualPoint('2026-02-02', 2.5)])},
    ])('keeps a previous $label', ({previous}) => {
        expect(mergeFor(previous, viewOf('unavailable')).get(7)).toBe(previous);
    });

    it.each([
        {label: 'it has only missing points', previous: viewOf('partial', [missingPoint('2026-02-01'), missingPoint('2026-02-02')])},
        {label: 'it has no points', previous: viewOf('ready')},
        {label: 'it is error', previous: viewOf('error', [factualPoint('2026-02-02', 1.5)])},
        {label: 'it is idle', previous: viewOf('idle', [factualPoint('2026-02-02', 1.5)])},
        {label: 'it is loading', previous: viewOf('loading', [factualPoint('2026-02-02', 1.5)])},
        {label: 'it is unavailable', previous: viewOf('unavailable', [factualPoint('2026-02-02', 1.5)])},
    ])('does not keep the previous view when $label', ({previous}) => {
        const next = viewOf('unavailable');

        expect(mergeFor(previous, next).get(7)).toBe(next);
    });

    it.each(['idle', 'loading', 'ready', 'partial', 'error'] as const)('keeps a next %s view as it is', (state) => {
        const next = viewOf(state);

        expect(mergeFor(viewOf('ready', [factualPoint('2026-02-02', 1.5)]), next).get(7)).toBe(next);
    });

    it('does not keep the previous view of a peer absent from the answer', () => {
        const next = viewOf('unavailable');

        const merged = preserveFactualCalendarPeersForCurrentUnavailable(new Map([[7, viewOf('ready', [factualPoint('2026-02-02', 1.5)])]]), new Map([[7, next]]), [priceItem(8), null], [7]);

        expect(merged.get(7)).toBe(next);
    });

    it('adds no view for a peer the next views do not have', () => {
        const merged = preserveFactualCalendarPeersForCurrentUnavailable(new Map([[7, viewOf('ready', [factualPoint('2026-02-02', 1.5)])]]), new Map(), [priceItem(7)], [7]);

        expect(merged.has(7)).toBe(false);
    });

    it('touches only the given peers and copies every other next view', () => {
        const previous = viewOf('ready', [factualPoint('2026-02-02', 1.5)]);
        const nextOf7 = viewOf('unavailable');
        const nextOf8 = viewOf('unavailable');
        const previousViews = new Map([
            [7, previous],
            [8, previous],
        ]);
        const nextViews = new Map([
            [7, nextOf7],
            [8, nextOf8],
        ]);

        const merged = preserveFactualCalendarPeersForCurrentUnavailable(previousViews, nextViews, [priceItem(7), priceItem(8)], [7]);

        expect(merged.get(7)).toBe(previous);
        expect(merged.get(8)).toBe(nextOf8);
    });

    it('returns a copy and leaves both inputs untouched', () => {
        const previous = viewOf('ready', [factualPoint('2026-02-02', 1.5)]);
        const next = viewOf('unavailable');
        const previousViews = new Map([[7, previous]]);
        const nextViews = new Map([[7, next]]);
        const previousBefore = structuredClone(previousViews);
        const nextBefore = structuredClone(nextViews);

        const merged = preserveFactualCalendarPeersForCurrentUnavailable(previousViews, nextViews, [priceItem(7)], [7]);

        expect(merged.get(7)).toBe(previous);
        expect(merged).not.toBe(nextViews);
        expect(nextViews.get(7)).toBe(next);
        expect(previousViews.get(7)).toBe(previous);
        expect(nextViews).toEqual(nextBefore);
        expect(previousViews).toEqual(previousBefore);
    });
});

// =============================================================================
//  The two helpers of the cache of signal answers (N64)
// =============================================================================

/** `assetChartAnswerKey(body)`, read by name (see the header). */
function answerKeyOf(body: readonly Record<string, unknown>[]): string {
    const key = (priceQuery as unknown as {assetChartAnswerKey?: (body: readonly Record<string, unknown>[]) => string}).assetChartAnswerKey;
    expect(typeof key, 'assetDetailPriceQuery.ts exports no assetChartAnswerKey(): the page cannot tell which signal answer a request asks for, so the client cache of signal answers has no key (N64)').toBe('function');
    return (key as (body: readonly Record<string, unknown>[]) => string)(body);
}

/** `assetChartAnswerForCache(answer)`, read by name (see the header). */
function forCache(answer: {items: Record<string, unknown>[]}): {items: Record<string, unknown>[]} {
    const keep = (priceQuery as unknown as {assetChartAnswerForCache?: (answer: {items: Record<string, unknown>[]}) => {items: Record<string, unknown>[]}}).assetChartAnswerForCache;
    expect(typeof keep, 'assetDetailPriceQuery.ts exports no assetChartAnswerForCache(): the cache would keep the prices the price store already holds (N64)').toBe('function');
    return (keep as (answer: {items: Record<string, unknown>[]}) => {items: Record<string, unknown>[]})(answer);
}

/** The item without one property. */
function without(item: Record<string, unknown>, key: string): Record<string, unknown> {
    return Object.fromEntries(Object.entries(item).filter(([name]) => name !== key));
}

/** The same value with the keys of every object written in the opposite order: the same request, said another way. */
function reordered(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(reordered);
    if (value !== null && typeof value === 'object') {
        return Object.fromEntries(
            Object.entries(value)
                .reverse()
                .map(([key, inner]) => [key, reordered(inner)]),
        );
    }
    return value;
}

interface BodyOptions {
    start?: string;
    end?: string;
    targetCurrency?: string;
    includePrice?: boolean;
    ownSignals?: Record<string, unknown>[];
    peers?: number[];
    includeEvents?: boolean;
}

/** An SMA of the page's own chart, as the request plan writes it. */
const SMA_20 = {instance_id: 'sma-1', signal_code: 'SMA', params: {window: 20}};

/** The calendar-return signal, as the page writes it into the request. */
function calendarSignal(windowDays = 30): Record<string, unknown> {
    return {instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, params: {window_days: windowDays}};
}

/**
 * The body the asset page posts to `/api/v1/assets/prices/query`: its own item, then one item per comparison peer.
 * The peers never ask for prices, whatever the page's own item does.
 */
function chartBody(options: BodyOptions = {}): Record<string, unknown>[] {
    const {start = '2026-01-01', end = '2026-06-30', targetCurrency = 'EUR', includePrice = true, ownSignals = [SMA_20, calendarSignal()], peers = [8], includeEvents = true} = options;
    return [
        {asset_id: 7, date_range: {start, end}, include_price: includePrice, include_events: includeEvents, target_currency: targetCurrency, signals: ownSignals},
        ...peers.map((assetId) => ({asset_id: assetId, date_range: {start, end}, include_price: false, include_events: includeEvents, target_currency: targetCurrency, signals: [calendarSignal()]})),
    ];
}

describe('assetChartAnswerKey: the same answer for the same request, whether the prices travel or not', () => {
    it('is the same for bodies that differ only in include_price, on the page’s own item or on every item', () => {
        const withPrices = answerKeyOf(chartBody({includePrice: true}));

        expect(answerKeyOf(chartBody({includePrice: false})), 'the price store serving the prices changed the key: the answer of a cache hit and of a cache miss would be filed apart').toBe(withPrices);

        const everyFlag = chartBody().map((item) => ({...item, include_price: true}));
        const noFlag = chartBody().map((item) => without(item, 'include_price'));
        expect(answerKeyOf(everyFlag), 'the peers’ include_price is part of the key').toBe(withPrices);
        expect(answerKeyOf(noFlag), 'a body with no include_price at all is another request').toBe(withPrices);
    });

    it('is the same for bodies that differ only in the order of their properties, at any depth', () => {
        const body = chartBody();

        expect(answerKeyOf(reordered(body) as Record<string, unknown>[]), 'the order the page wrote the properties in changed the key: the same request would miss').toBe(answerKeyOf(body));
    });

    it('is the same whether an undefined target currency is absent or undefined', () => {
        const native = chartBody().map((item) => ({...item, target_currency: undefined}));
        const absent = chartBody().map((item) => without(item, 'target_currency'));

        expect(answerKeyOf(native)).toBe(answerKeyOf(absent));
    });

    it('is a string that does not carry include_price', () => {
        const key = answerKeyOf(chartBody());

        expect(typeof key).toBe('string');
        expect(key, 'the flag that does not change the answer is in the key').not.toContain('include_price');
    });

    it('differs when the start or the end of the range differs', () => {
        const base = answerKeyOf(chartBody());

        expect(answerKeyOf(chartBody({start: '2026-02-01'})), 'start').not.toBe(base);
        expect(answerKeyOf(chartBody({end: '2026-05-31'})), 'end').not.toBe(base);
    });

    it('differs when the target currency differs, or the chart is not converted', () => {
        const base = answerKeyOf(chartBody({targetCurrency: 'EUR'}));
        const unconverted = chartBody().map((item) => without(item, 'target_currency'));

        expect(answerKeyOf(chartBody({targetCurrency: 'USD'})), 'another currency').not.toBe(base);
        expect(answerKeyOf(unconverted), 'no conversion').not.toBe(base);
    });

    it('differs when a signal’s params differ — a calendar window or an indicator’s own', () => {
        const base = answerKeyOf(chartBody());

        expect(answerKeyOf(chartBody({ownSignals: [SMA_20, calendarSignal(90)]})), 'the calendar window_days').not.toBe(base);
        expect(answerKeyOf(chartBody({ownSignals: [{...SMA_20, params: {window: 50}}, calendarSignal()]})), 'an indicator’s window').not.toBe(base);
    });

    it('differs when a signal’s instance_id differs, or a signal is added or removed', () => {
        const base = answerKeyOf(chartBody());

        expect(answerKeyOf(chartBody({ownSignals: [{...SMA_20, instance_id: 'sma-2'}, calendarSignal()]})), 'the instance_id: the answer is read back by it').not.toBe(base);
        expect(answerKeyOf(chartBody({ownSignals: [SMA_20]})), 'a signal removed').not.toBe(base);
        expect(answerKeyOf(chartBody({ownSignals: [SMA_20, calendarSignal(), {instance_id: 'rsi-1', signal_code: 'RSI', params: {window: 14}}]})), 'a signal added').not.toBe(base);
    });

    it('differs when a comparison peer differs: another peer, one more, or none', () => {
        const base = answerKeyOf(chartBody({peers: [8]}));

        expect(answerKeyOf(chartBody({peers: [9]})), 'another peer').not.toBe(base);
        expect(answerKeyOf(chartBody({peers: [8, 9]})), 'one more peer').not.toBe(base);
        expect(answerKeyOf(chartBody({peers: []})), 'no peer').not.toBe(base);
    });

    it('differs when the page asks for another asset, or for the events or not', () => {
        const base = answerKeyOf(chartBody());
        const another = chartBody().map((item, index) => (index === 0 ? {...item, asset_id: 70} : item));

        expect(answerKeyOf(another), 'another asset').not.toBe(base);
        expect(answerKeyOf(chartBody({includeEvents: false})), 'the events are part of the answer').not.toBe(base);
    });

    it('leaves the body as it found it: include_price stays on the page’s item', () => {
        const body = chartBody();
        const before = structuredClone(body);

        answerKeyOf(body);

        expect(body, 'the key edited the caller’s body: the request that follows would carry no include_price').toEqual(before);
        expect(body[0].include_price).toBe(true);
        expect(body[1].include_price).toBe(false);
    });
});

describe('assetChartAnswerForCache: the answer without the prices, which the price store holds', () => {
    /** An answer as the page reads it: prices, events, signals and errors on each item, and a field the cache has no business with. */
    function anAnswer(): {items: Record<string, unknown>[]} {
        return {
            items: [
                {
                    asset_id: 7,
                    prices: [
                        {date: '2026-01-02', close: 101.5},
                        {date: '2026-01-05', close: 102},
                    ],
                    events: [{date: '2026-01-03', type: 'DIVIDEND'}],
                    signals: [signalResult('sma-1'), signalResult(CALENDAR_RETURN_INSTANCE_ID)],
                    errors: ['Conversion 0: No FX rate found'],
                    currency: 'EUR',
                },
                {asset_id: 8, prices: [], events: [], signals: [signalResult(CALENDAR_RETURN_INSTANCE_ID)], errors: []},
            ],
        };
    }

    it('drops the prices field from every item', () => {
        const kept = forCache(anAnswer());

        expect(kept.items).toHaveLength(2);
        for (const item of kept.items) expect('prices' in item, `item ${String(item.asset_id)} kept its prices: the cache would hold what the price store already does, twice`).toBe(false);
    });

    it('keeps everything else of each item: asset_id, events, signals, errors and any other field', () => {
        const original = anAnswer();

        const kept = forCache(original);

        expect(kept.items, 'the items keep their order and every field but prices').toEqual(original.items.map((item) => without(item, 'prices')));
        expect(kept.items[0]).toMatchObject({asset_id: 7, events: [{type: 'DIVIDEND'}], errors: ['Conversion 0: No FX rate found'], currency: 'EUR'});
        expect((kept.items[0].signals as unknown[]).length, 'the signals are the point of the cache').toBe(2);
    });

    it('leaves an item with no prices field as it is, and an empty answer empty', () => {
        const noPrices = {items: [{asset_id: 8, events: [], signals: [], errors: []}]};

        expect(forCache(noPrices)).toEqual({items: [{asset_id: 8, events: [], signals: [], errors: []}]});
        expect(forCache({items: []})).toEqual({items: []});
    });

    it('does not change its input: the page keeps drawing from the answer it passed', () => {
        const input = anAnswer();
        const before = structuredClone(input);

        forCache(input);

        expect(input, 'the helper edited the page’s answer in place').toEqual(before);
        expect(input.items[0].prices, 'the page’s own answer lost its prices').toHaveLength(2);
    });
});
