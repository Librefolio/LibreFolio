/**
 * assetPriceDerived.test.ts — Unit tests for the pure price-derived-state computation
 * extracted from the Assets list page (see assetPriceDerived.ts header for rationale).
 *
 * The fixed-period changes (1D … 5Y) are no longer this module's: the Assets and FX lists read them from the backend
 * (MF-P2, X-R53; `utils/periodChanges.ts`). Their tests left with them; the last block below pins their absence.
 *
 * @module utils/__tests__/assetPriceDerived.test
 */
import {describe, expect, it} from 'vitest';

import * as derived from '../assetPriceDerived';
import {computeDerivedPriceState, deltaPeriodLabel, extractDaysBack} from '../assetPriceDerived';

describe('computeDerivedPriceState', () => {
    // The Δ over the range — from the first to the last point of the range on screen, the Assets cards’ — is the backend’s
    // (X-R59, decision N80): an item of `POST /assets/prices/period-changes` asks it with `range_start`, its result carries
    // it as `range_change`, and the page reads it through `utils/rangeChange.ts`. So the derived state keeps the last
    // price and the chart’s points, and carries no change: deltaAbs and deltaPercent would be a second copy of the figure,
    // computed in floats, that no card would read any more. Its own keys are exactly chartData and lastPrice.
    //
    // Red today: the state carries deltaAbs and deltaPercent.

    it('returns no last price and no chart point for an empty price array, and no change', () => {
        const result = computeDerivedPriceState([]);
        expect(result.lastPrice).toBeNull();
        expect(result.chartData).toEqual([]);
        expect(Object.keys(result).sort(), 'the state of an empty history: its base, its last price and its chart, no change over the range').toEqual(['base', 'chartData', 'lastPrice']);
        expect(result.base).toBeNull();
    });

    it('computes lastPrice and chartData, and no change over the range', () => {
        const prices = [
            {date: '2026-01-01', close: '100'},
            {date: '2026-01-08', close: '110'},
        ];
        const result = computeDerivedPriceState(prices);
        expect(result.lastPrice).toBe(110);
        expect(result.chartData).toEqual([
            {date: '2026-01-01', value: 100, staleDays: 0},
            {date: '2026-01-08', value: 110, staleDays: 0},
        ]);
        expect(Object.keys(result).sort(), 'the change over the range is the backend’s range_change: the state of a priced history carries none').toEqual(['base', 'chartData', 'lastPrice']);
    });

    it('reads staleDays from backward_fill_info.days_back when present', () => {
        const prices = [{date: '2026-01-01', close: '100', backward_fill_info: {days_back: 3}}];
        const result = computeDerivedPriceState(prices);
        expect(result.chartData[0].staleDays).toBe(3);
    });

    it('falls back to legacy camelCase backwardFillInfo.daysBack when snake_case is absent', () => {
        const prices = [{date: '2026-01-01', close: '100', backwardFillInfo: {daysBack: 5}}];
        const result = computeDerivedPriceState(prices);
        expect(result.chartData[0].staleDays).toBe(5);
    });

    it('defaults staleDays to 0 for a malformed/unexpected backward_fill_info shape', () => {
        const prices = [{date: '2026-01-01', close: '100', backward_fill_info: []}];
        const result = computeDerivedPriceState(prices);
        expect(result.chartData[0].staleDays).toBe(0);
    });

    it('reads a zero first price as any other: the last price and the chart are unaffected, and no change is derived', () => {
        const prices = [
            {date: '2026-01-01', close: '0'},
            {date: '2026-01-08', close: '10'},
        ];
        const result = computeDerivedPriceState(prices);
        expect(result.lastPrice).toBe(10);
        expect(result.chartData).toEqual([
            {date: '2026-01-01', value: 0, staleDays: 0},
            {date: '2026-01-08', value: 10, staleDays: 0},
        ]);
        expect(Object.keys(result).sort(), 'no delta keys, whatever the first price').toEqual(['base', 'chartData', 'lastPrice']);
    });
});

describe('extractDaysBack — the one home of the "filled backward" rule, shared with the sync dialog (C-66)', () => {
    // The sync dialog warns before replacing stored rows, and a point is a stored row only when it is not
    // filled backward from an earlier date: the same rule as staleDays above, so it is exported rather than
    // copied, and it takes a bare point — the two fill shapes, no date or close needed.
    //
    // Red today: `extractDaysBack` is private to the module.
    it('reads the snake_case and the camelCase shape from a bare point, and 0 when neither carries a count', () => {
        expect(extractDaysBack({backward_fill_info: {days_back: 3}})).toBe(3);
        expect(extractDaysBack({backwardFillInfo: {daysBack: 5}})).toBe(5);
        expect(extractDaysBack({backward_fill_info: {days_back: 0}})).toBe(0);
        expect(extractDaysBack({backward_fill_info: null, backwardFillInfo: null})).toBe(0);
        expect(extractDaysBack({})).toBe(0);
    });
});

describe('deltaPeriodLabel — a Δ period is labelled from the catalogues (T, duration labels)', () => {
    // The Δ columns of the asset and FX tables print their period's key, `Δ 1D` or `Δ 3M`: English unit
    // letters in every language. The contract is the date picker's and the rolling window's: a
    // `<n><D|W|M|Y>` key reads `datePicker.presets.days`, `.weeks`, `.months` or `.years` with its count
    // as `n` — the catalogues carry the reader's unit letter (1G, 1S, 1A in Italian) — and a key the helper
    // does not recognise comes back unchanged, never as a marker or a guess.
    //
    // Observed without reading a language, through a marker `t`: a label taken from the catalogue reads
    // as a marker of its key and values (`⟦datePicker.presets.months n=3⟧`).
    //
    // Red today: `deltaPeriodLabel` does not exist.

    type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

    /** How a label reads through the marker `t`: `⟦key⟧`, or `⟦key n=3⟧` for a message given values. */
    const marked = (key: string, values: Record<string, string | number> = {}): string => `⟦${[key, ...Object.entries(values).map(([name, value]) => `${name}=${value}`)].join(' ')}⟧`;

    /** A `t` that reads every key as its marker, with the values it is given. */
    const markerT: Translate = (key, options) => marked(key, options?.values);

    /** The keys of the period columns, 1W … 5Y: the periods the backend answers after the fixed 1D (MF-P2). */
    const PERIOD_KEYS = ['1W', '1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y'] as const;

    /** The label each period column's key must read: its unit's catalogue key, its count as n. */
    const EXPECTED: Record<(typeof PERIOD_KEYS)[number], string> = {
        '1W': marked('datePicker.presets.weeks', {n: 1}),
        '1M': marked('datePicker.presets.months', {n: 1}),
        '3M': marked('datePicker.presets.months', {n: 3}),
        '6M': marked('datePicker.presets.months', {n: 6}),
        '1Y': marked('datePicker.presets.years', {n: 1}),
        '2Y': marked('datePicker.presets.years', {n: 2}),
        '3Y': marked('datePicker.presets.years', {n: 3}),
        '5Y': marked('datePicker.presets.years', {n: 5}),
    };

    it('labels the key of every period column (1W … 5Y) from datePicker.presets.weeks, months or years, its count as n', () => {
        const labels = Object.fromEntries(PERIOD_KEYS.map((key) => [key, deltaPeriodLabel(key, markerT)]));

        expect(labels).toEqual(EXPECTED);
    });

    it('reads a count of more than one digit whole', () => {
        expect({'10Y': deltaPeriodLabel('10Y', markerT), '12M': deltaPeriodLabel('12M', markerT)}).toEqual({
            '10Y': marked('datePicker.presets.years', {n: 10}),
            '12M': marked('datePicker.presets.months', {n: 12}),
        });
    });

    it('labels 1D — the period of the fixed Δ column — from datePicker.presets.days, its count as n', () => {
        expect(deltaPeriodLabel('1D', markerT)).toBe(marked('datePicker.presets.days', {n: 1}));
    });

    it('returns a key it does not recognise unchanged: empty, not a period, an unknown unit, a count that is not whole, no count', () => {
        const keys = ['', 'abc', '1Q', '1.5M', 'M'];

        expect(Object.fromEntries(keys.map((key) => [key, deltaPeriodLabel(key, markerT)]))).toEqual(Object.fromEntries(keys.map((key) => [key, key])));
    });
});

describe('the Δ periods are the backend’s, not this module’s (MF-P2, X-R53)', () => {
    // One home for financial math: the backend. The Assets and FX lists read their fixed-period changes (1D … 5Y)
    // from `POST /assets/prices/period-changes` and `POST /fx/currencies/period-changes`, so the browser computes none:
    // this module offers neither the periods (`DELTA_PERIODS`) nor the change over one (`computePeriodDelta`), and the
    // derived state of an asset carries no `deltas` — a second copy of the figures, which no table would read any more.
    // `deltaPeriodLabel` stays: naming a period is the interface's.
    //
    // Read through the module's namespace, so an export still there fails its own case, by name.
    //
    // Red today: both are exported, and computeDerivedPriceState returns `deltas`.

    it('exports neither computePeriodDelta nor DELTA_PERIODS', () => {
        expect(
            Object.keys(derived).filter((name) => name === 'computePeriodDelta' || name === 'DELTA_PERIODS'),
            'the Δ periods are the backend’s: assetPriceDerived still offers its own computation of them',
        ).toEqual([]);
        expect(typeof derived.deltaPeriodLabel, 'control: the module is read, and the label of a period stays').toBe('function');
    });

    it('computeDerivedPriceState returns no deltas, for a priced history or an empty one', () => {
        const priced = computeDerivedPriceState([
            {date: '2026-01-01', close: '100'},
            {date: '2026-01-08', close: '110'},
        ]);

        expect(priced, 'the derived state of a priced asset still carries period changes computed in the browser').not.toHaveProperty('deltas');
        expect(computeDerivedPriceState([]), 'nor an empty one').not.toHaveProperty('deltas');
        expect(priced.lastPrice, 'control: the rest of the state is still computed').toBe(110);
    });
});

describe('computeDerivedPriceState: the base of a sampled series (Z-29b, MF n3)', () => {
    // The base of a card's percentage view and of its line's colour is the point on the fill's first day F. A daily series
    // opens on it. A weekly or monthly one opens on the end of the first bucket: F is `sample_bounds.first`, a point the
    // series does not draw — reading `prices[0]` there would measure from the wrong day.

    it('takes the base from the first price of a daily series', () => {
        const result = computeDerivedPriceState([
            {date: '2026-01-05', close: '100'},
            {date: '2026-01-06', close: '110'},
        ]);

        expect(result.base).toEqual({date: '2026-01-05', value: 100});
    });

    it('takes the base from sample_bounds.first when the backend gives it, not from the first bucket’s point', () => {
        const result = computeDerivedPriceState(
            [
                {date: '2026-01-11', close: '104'},
                {date: '2026-01-18', close: '108'},
            ],
            {first: {date: '2026-01-07', close: '100', backward_fill_info: {days_back: 2}}, last: {date: '2026-01-18', close: '108'}},
        );

        expect(result.base).toEqual({date: '2026-01-07', value: 100});
        expect(result.chartData.map((point) => point.value)).toEqual([104, 108]);
    });

    it('has no base for an empty series, whatever the bounds', () => {
        expect(computeDerivedPriceState([], null).base).toBeNull();
    });
});
