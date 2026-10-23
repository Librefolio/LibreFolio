/**
 * fxDetailCalendar.ts (lot X5-F1): the rolling return of the FX pair detail page, as a pure request builder and answer reader.
 *
 * The detail page asks `POST /fx/currencies/convert` for the pair's daily return and for the return of every pair its saved
 * `fx-pair` signals compare, in ONE request, and reads the answer back by `request_index`:
 *
 * - `buildFxDetailCalendarQuery(input)`: entry 0 is the page's own pair, in the direction the page shows it
 *   (`from_amount {code: base, amount: '1'}`, `to: quote`), with the calendar rolling return as its one signal; it carries no
 *   `key`, no `max_points` and no `sample_like` (the detail asks the daily return, like its other signal requests; a list
 *   card names its conversion and reduces the plot, `reducedFxQuery.ts`). Then one entry per compared pair, same range and
 *   signals, the direction its signal shows the pair: `EUR-GBP` is EUR → GBP, inverted GBP → EUR. A pair that is empty,
 *   malformed (not exactly two codes) or the page's own is skipped; the entries keep the targets' order.
 * - `fxDetailCalendarViews(answer, entries)`: the view of each entry from the `signal_results` item whose `request_index`
 *   is its position; the own entry (`configId` null) gives `own`, the others `targets`, by `configId`. An own entry with no
 *   answer, or an answer that is no object, is an `error` view; a compared pair with no answer is absent from `targets`.
 *
 * Red first: the module does not exist.
 */
import {describe, expect, it} from 'vitest';
import {CALENDAR_RETURN_INSTANCE_ID, CALENDAR_RETURN_SIGNAL_CODE, emptyCalendarReturnView, extractCalendarReturnView} from '$lib/components/charts/priceChartHelpers';
import {fxCalendarRequest, type FxCalendarRequest} from '$lib/utils/reducedFxQuery';
import {buildFxDetailCalendarQuery, fxDetailCalendarViews, type FxDetailCalendarEntry, type FxDetailCalendarInput} from '../fxDetailCalendar';

// ---------------------------------------------------------------------------
// Fixtures: the request, and the raw signal results the backend answers with
// ---------------------------------------------------------------------------

function input(overrides: Partial<FxDetailCalendarInput> = {}): FxDetailCalendarInput {
    return {ownSlug: 'EUR-USD', base: 'EUR', quote: 'USD', start: '2026-01-01', end: '2026-06-30', windowDays: 90, pairTargets: [], ...overrides};
}

const target = (configId: string, pairSlug: string, inverted = false) => ({configId, pairSlug, inverted});

function calendarProvenance(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        status: 'available',
        reference_target_date: '2026-01-02',
        current_price_date: '2026-02-01',
        current_price_days_back: 0,
        reference_price_date: '2026-01-02',
        reference_price_days_back: 0,
        current_fx_date: null,
        current_fx_days_back: null,
        reference_fx_date: null,
        reference_fx_days_back: null,
        ...overrides,
    };
}

function calendarPoint(date: string, value: number | null, provenance: Record<string, unknown> = {}): Record<string, unknown> {
    return {date, value, provenance: calendarProvenance(value === null ? {status: 'missing_reference', reference_price_date: null, reference_price_days_back: null, ...provenance} : provenance)};
}

/** A calendar result with the given points; `status` 'ok' unless overridden. */
function calendarResult(points: unknown[], overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, status: 'ok', series: [{key: 'calendar_return', points}], ...overrides};
}

function inputCoverage(): Record<string, unknown> {
    return {
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
    };
}

/** A typed unavailable result the signal result schema accepts (as in priceChartHelpers.test.ts). */
function unavailableResult(): Record<string, unknown> {
    return calendarResult([], {
        status: 'unavailable',
        series: [],
        availability: {domain_compatible: true, can_compute: false, input_coverage: inputCoverage(), required_points: 7, warmup_complete: true, partial_coverage_used: false, reason_code: 'undefined_metric'},
        warmup: {requirement: {minimum_points: 1, stabilization_points: 6, total_points: 7}, loaded_points: 11, used_points: 7, complete: true},
        warnings: [{code: 'undefined_metric_window', message: 'Every selected Calendar output is undefined.', details: {unavailable_points: 4, reasons: {invalid_current_price: 4}}}],
        error: null,
    });
}

/** One item of the answer's `signal_results`. */
function answerItem(requestIndex: number, result: Record<string, unknown>): Record<string, unknown> {
    return {request_index: requestIndex, from_currency: 'EUR', to_currency: 'USD', date_range: {start: '2026-01-01', end: '2026-06-30'}, signals: [result]};
}

const readyResult = (value: number) => calendarResult([calendarPoint('2026-02-01', value), calendarPoint('2026-02-02', value + 1)]);
const partialResult = () => calendarResult([calendarPoint('2026-02-01', 4.5), calendarPoint('2026-02-02', null)]);

const entry = (configId: string | null, from = 'EUR', to = 'USD'): FxDetailCalendarEntry => ({
    request: {from_amount: {code: from, amount: '1'}, to, date_range: {start: '2026-01-01', end: '2026-06-30'}, signals: [fxCalendarRequest(90)]} satisfies FxCalendarRequest,
    configId,
});

// ---------------------------------------------------------------------------
// buildFxDetailCalendarQuery
// ---------------------------------------------------------------------------

describe('buildFxDetailCalendarQuery: the page’s own pair, then one entry per compared pair', () => {
    it('asks the page’s pair first, 1 unit of the base into the quote, over the range, with the calendar rolling return of the window', () => {
        const entries = buildFxDetailCalendarQuery(input({windowDays: 30}));

        expect(entries).toHaveLength(1);
        expect(entries[0]).toEqual({
            request: {
                from_amount: {code: 'EUR', amount: '1'},
                to: 'USD',
                date_range: {start: '2026-01-01', end: '2026-06-30'},
                signals: [{instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, params: {window_days: 30}}],
            },
            configId: null,
        });
    });

    it('asks the pair the way the page shows it, even when that is not the canonical one', () => {
        const [own] = buildFxDetailCalendarQuery(input({ownSlug: 'EUR-USD', base: 'USD', quote: 'EUR'}));

        expect(own.request.from_amount).toEqual({code: 'USD', amount: '1'});
        expect(own.request.to).toBe('EUR');
        expect(own.configId).toBeNull();
    });

    it('names no key, no max_points and no sample_like on any conversion: the detail asks the daily return', () => {
        const entries = buildFxDetailCalendarQuery(input({pairTargets: [target('cfg-1', 'EUR-GBP'), target('cfg-2', 'EUR-CHF', true)]}));

        expect(entries).toHaveLength(3);
        for (const {request} of entries) {
            expect(Object.keys(request).sort(), 'the fields of the conversion').toEqual(['date_range', 'from_amount', 'signals', 'to']);
        }
    });

    it('asks every conversion one signal, the calendar rolling return under the detail’s instance id and the window', () => {
        const entries = buildFxDetailCalendarQuery(input({windowDays: 365, pairTargets: [target('cfg-1', 'EUR-GBP')]}));

        for (const {request} of entries) {
            expect(request.signals).toEqual([{instance_id: CALENDAR_RETURN_INSTANCE_ID, signal_code: CALENDAR_RETURN_SIGNAL_CODE, params: {window_days: 365}}]);
        }
    });

    it('asks a compared pair the direction its signal shows it: EUR-GBP is EUR to GBP, inverted GBP to EUR', () => {
        const entries = buildFxDetailCalendarQuery(input({pairTargets: [target('cfg-1', 'EUR-GBP'), target('cfg-2', 'EUR-GBP', true)]}));

        expect(entries.map(({configId, request}) => [configId, request.from_amount.code, request.from_amount.amount, request.to])).toEqual([
            [null, 'EUR', '1', 'USD'],
            ['cfg-1', 'EUR', '1', 'GBP'],
            ['cfg-2', 'GBP', '1', 'EUR'],
        ]);
    });

    it('asks a compared pair over the same range as the page’s own', () => {
        const entries = buildFxDetailCalendarQuery(input({start: '2025-03-01', end: '2025-09-15', pairTargets: [target('cfg-1', 'EUR-GBP')]}));

        expect(entries.map(({request}) => request.date_range)).toEqual([
            {start: '2025-03-01', end: '2025-09-15'},
            {start: '2025-03-01', end: '2025-09-15'},
        ]);
    });

    it('skips a target whose slug is empty, malformed, or the page’s own pair', () => {
        const entries = buildFxDetailCalendarQuery(
            input({
                ownSlug: 'EUR-USD',
                pairTargets: [target('empty', ''), target('one-code', 'EUR'), target('trailing-dash', 'EUR-'), target('leading-dash', '-GBP'), target('three-codes', 'EUR-GBP-CHF'), target('own', 'EUR-USD'), target('ok', 'EUR-GBP')],
            }),
        );

        expect(entries.map(({configId}) => configId)).toEqual([null, 'ok']);
    });

    it('keeps the targets in order, and two targets of one pair as two entries with their own config ids', () => {
        const entries = buildFxDetailCalendarQuery(input({pairTargets: [target('b', 'EUR-GBP'), target('a', 'EUR-CHF'), target('c', 'EUR-GBP')]}));

        expect(entries.map(({configId, request}) => [configId, request.to])).toEqual([
            [null, 'USD'],
            ['b', 'GBP'],
            ['a', 'CHF'],
            ['c', 'GBP'],
        ]);
    });

    it('keeps duplicates by config id in order, never merging them', () => {
        const entries = buildFxDetailCalendarQuery(input({pairTargets: [target('dup', 'EUR-GBP'), target('dup', 'EUR-GBP')]}));

        expect(entries.map(({configId}) => configId)).toEqual([null, 'dup', 'dup']);
    });

    it('gives each entry its own signals array: changing one request does not change another', () => {
        const entries = buildFxDetailCalendarQuery(input({pairTargets: [target('cfg-1', 'EUR-GBP')]}));

        expect(entries[0].request.signals).not.toBe(entries[1].request.signals);
    });
});

// ---------------------------------------------------------------------------
// fxDetailCalendarViews
// ---------------------------------------------------------------------------

describe('fxDetailCalendarViews: each entry’s view, from the signal_results item at its request_index', () => {
    const entries = [entry(null), entry('cfg-gbp', 'EUR', 'GBP'), entry('cfg-chf', 'EUR', 'CHF')];

    it('reads the own view from the item at index 0 and the compared pairs’ from theirs, by config id', () => {
        const answer = {signal_results: [answerItem(0, readyResult(1)), answerItem(1, readyResult(10)), answerItem(2, readyResult(20))]};

        const {own, targets} = fxDetailCalendarViews(answer, entries);

        expect(own).toEqual(extractCalendarReturnView([readyResult(1)], CALENDAR_RETURN_INSTANCE_ID));
        expect(own.state).toBe('ready');
        expect([...targets.keys()]).toEqual(['cfg-gbp', 'cfg-chf']);
        expect(targets.get('cfg-gbp')?.points.map((point) => point.value)).toEqual([10, 11]);
        expect(targets.get('cfg-chf')?.points.map((point) => point.value)).toEqual([20, 21]);
    });

    it('maps by request_index, not by the order of the items', () => {
        const answer = {signal_results: [answerItem(2, readyResult(20)), answerItem(0, readyResult(1)), answerItem(1, readyResult(10))]};

        const {own, targets} = fxDetailCalendarViews(answer, entries);

        expect(own.points.map((point) => point.value)).toEqual([1, 2]);
        expect(targets.get('cfg-gbp')?.points.map((point) => point.value)).toEqual([10, 11]);
        expect(targets.get('cfg-chf')?.points.map((point) => point.value)).toEqual([20, 21]);
    });

    it('reads a ready, a partial and an unavailable answer as each state', () => {
        const answer = {signal_results: [answerItem(0, readyResult(1)), answerItem(1, partialResult()), answerItem(2, unavailableResult())]};

        const {own, targets} = fxDetailCalendarViews(answer, entries);

        expect(own.state).toBe('ready');
        expect(targets.get('cfg-gbp')?.state).toBe('partial');
        expect(targets.get('cfg-chf')?.state).toBe('unavailable');
        expect(targets.get('cfg-chf')?.points).toEqual([]);
        expect(targets.get('cfg-chf')?.problem).toMatchObject({code: 'undefined_metric', status: 'unavailable'});
    });

    it('reads a failed own answer as an error view and keeps the compared pairs’', () => {
        const failed = calendarResult([], {status: 'failed', series: []});
        const answer = {signal_results: [answerItem(0, failed), answerItem(1, readyResult(10))]};

        const {own, targets} = fxDetailCalendarViews(answer, entries.slice(0, 2));

        expect(own.state).toBe('error');
        expect(targets.get('cfg-gbp')?.state).toBe('ready');
    });

    it('gives the own entry an error view when the answer has no item for it, and still reads the others', () => {
        const answer = {signal_results: [answerItem(1, readyResult(10))]};

        const {own, targets} = fxDetailCalendarViews(answer, entries);

        expect(own).toEqual(emptyCalendarReturnView('error'));
        expect(targets.get('cfg-gbp')?.state).toBe('ready');
    });

    it('leaves a compared pair with no item out of targets: absent, not an error view', () => {
        const answer = {signal_results: [answerItem(0, readyResult(1)), answerItem(2, readyResult(20))]};

        const {own, targets} = fxDetailCalendarViews(answer, entries);

        expect(own.state).toBe('ready');
        expect(targets.has('cfg-gbp')).toBe(false);
        expect(targets.has('cfg-chf')).toBe(true);
    });

    it('ignores an item whose request_index names no entry', () => {
        const answer = {signal_results: [answerItem(0, readyResult(1)), answerItem(7, readyResult(70)), answerItem(-1, readyResult(80))]};

        const {own, targets} = fxDetailCalendarViews(answer, entries);

        expect(own.points.map((point) => point.value)).toEqual([1, 2]);
        expect(targets.size).toBe(0);
    });

    it.each([
        ['null', null],
        ['undefined', undefined],
        ['a string', 'nope'],
        ['a number', 42],
        ['an array', []],
        ['an object with no signal_results', {results: []}],
        ['an object whose signal_results is no array', {signal_results: 'x'}],
    ])('answers an error own view and no compared pair for %s', (_label, answer) => {
        const {own, targets} = fxDetailCalendarViews(answer, entries);

        expect(own).toEqual(emptyCalendarReturnView('error'));
        expect(targets.size).toBe(0);
    });

    it('answers an error own view for an empty list of entries, and reads nothing', () => {
        const {own, targets} = fxDetailCalendarViews({signal_results: [answerItem(0, readyResult(1))]}, []);

        expect(own.state).toBe('error');
        expect(targets.size).toBe(0);
    });

    it('survives an item that is no object, or has no signals, as an error view for its entry', () => {
        const answer = {signal_results: [null, 'x', {request_index: 0}, {request_index: 1, signals: []}]};

        const {own, targets} = fxDetailCalendarViews(answer, entries);

        expect(own.state).toBe('error');
        expect(targets.get('cfg-gbp')?.state).toBe('error');
        expect(targets.has('cfg-chf')).toBe(false);
    });

    it('reads the results of the entries a build produced, end to end', () => {
        const built = buildFxDetailCalendarQuery(input({pairTargets: [target('cfg-1', 'EUR-GBP', true)]}));
        const answer = {signal_results: [answerItem(0, readyResult(1)), answerItem(1, readyResult(10))]};

        const {own, targets} = fxDetailCalendarViews(answer, built);

        expect(own.state).toBe('ready');
        expect(targets.get('cfg-1')?.state).toBe('ready');
    });
});
