/**
 * assetPriceDerived.test.ts — Unit tests for the pure price-derived-state computation
 * extracted from the Assets list page (see assetPriceDerived.ts header for rationale).
 *
 * @module utils/__tests__/assetPriceDerived.test
 */
import {describe, expect, it} from 'vitest';

import {computeDerivedPriceState, computePeriodDelta, DELTA_PERIODS, deltaPeriodLabel, extractDaysBack} from '../assetPriceDerived';

describe('computePeriodDelta', () => {
    it('computes a simple positive delta over a period', () => {
        const chartData = [
            {date: '2026-01-01', value: 100},
            {date: '2026-01-08', value: 110},
        ];
        expect(computePeriodDelta(chartData, 7)).toBeCloseTo(10, 5);
    });

    it('returns null for an empty series', () => {
        expect(computePeriodDelta([], 7)).toBeNull();
    });

    it('returns null when the last value is 0', () => {
        expect(computePeriodDelta([{date: '2026-01-01', value: 0}], 7)).toBeNull();
    });

    it('backward-fills to the closest point at or before the target date', () => {
        const chartData = [
            {date: '2026-01-01', value: 100},
            {date: '2026-01-03', value: 105}, // no data for 01-02 (e.g. weekend)
            {date: '2026-01-08', value: 110},
        ];
        // Target for a 5-day lookback from 01-08 is 01-03 -> should hit the 01-03 point.
        expect(computePeriodDelta(chartData, 5)).toBeCloseTo(((110 - 105) / 105) * 100, 5);
    });

    it('matches results for very long histories regardless of scan direction (regression: forward vs backward scan)', () => {
        // Build ~10 years of daily data and confirm the backward-scan implementation
        // used here gives the same answer a naive forward scan would.
        const chartData: Array<{date: string; value: number}> = [];
        const start = new Date('2016-01-01T00:00:00Z');
        for (let i = 0; i < 3650; i++) {
            const d = new Date(start.getTime() + i * 86400000);
            chartData.push({date: d.toISOString().slice(0, 10), value: 100 + i * 0.01});
        }

        function forwardScan(data: typeof chartData, periodDays: number): number | null {
            const pn = data[data.length - 1];
            const targetDate = new Date(pn.date);
            targetDate.setDate(targetDate.getDate() - periodDays);
            const targetStr = targetDate.toISOString().slice(0, 10);
            let startPoint: {date: string; value: number} | null = null;
            for (const point of data) {
                if (point.date <= targetStr) startPoint = point;
                else break;
            }
            if (!startPoint) return null;
            return ((pn.value - startPoint.value) / startPoint.value) * 100;
        }

        for (const days of [7, 30, 365, 1825]) {
            expect(computePeriodDelta(chartData, days)).toBeCloseTo(forwardScan(chartData, days) ?? NaN, 9);
        }
    });
});

describe('computeDerivedPriceState', () => {
    it('returns empty/null state for an empty price array', () => {
        const result = computeDerivedPriceState([]);
        expect(result).toEqual({lastPrice: null, deltaAbs: null, deltaPercent: null, chartData: [], deltas: {}});
    });

    it('computes lastPrice, deltaAbs, deltaPercent, chartData, and all DELTA_PERIODS deltas', () => {
        const prices = [
            {date: '2026-01-01', close: '100'},
            {date: '2026-01-08', close: '110'},
        ];
        const result = computeDerivedPriceState(prices);
        expect(result.lastPrice).toBe(110);
        expect(result.deltaAbs).toBeCloseTo(10, 5);
        expect(result.deltaPercent).toBeCloseTo(10, 5);
        expect(result.chartData).toEqual([
            {date: '2026-01-01', value: 100, staleDays: 0},
            {date: '2026-01-08', value: 110, staleDays: 0},
        ]);
        expect(Object.keys(result.deltas)).toEqual(['1D', ...DELTA_PERIODS.map((p) => p.key)]);
        expect(result.deltas['1D']).toBeCloseTo(10, 5);
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

    it('treats a zero first price as "no delta" (avoids division by zero)', () => {
        const prices = [
            {date: '2026-01-01', close: '0'},
            {date: '2026-01-08', close: '10'},
        ];
        const result = computeDerivedPriceState(prices);
        expect(result.deltaAbs).toBeNull();
        expect(result.deltaPercent).toBeNull();
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

    /** The label each DELTA_PERIODS key must read: its unit's catalogue key, its count as n. */
    const EXPECTED: Record<(typeof DELTA_PERIODS)[number]['key'], string> = {
        '1W': marked('datePicker.presets.weeks', {n: 1}),
        '1M': marked('datePicker.presets.months', {n: 1}),
        '3M': marked('datePicker.presets.months', {n: 3}),
        '6M': marked('datePicker.presets.months', {n: 6}),
        '1Y': marked('datePicker.presets.years', {n: 1}),
        '2Y': marked('datePicker.presets.years', {n: 2}),
        '3Y': marked('datePicker.presets.years', {n: 3}),
        '5Y': marked('datePicker.presets.years', {n: 5}),
    };

    it('labels every DELTA_PERIODS key from datePicker.presets.weeks, months or years, its count as n', () => {
        const labels = Object.fromEntries(DELTA_PERIODS.map(({key}) => [key, deltaPeriodLabel(key, markerT)]));

        expect(labels).toEqual(EXPECTED);
    });

    it('reads a count of more than one digit whole', () => {
        expect({'10Y': deltaPeriodLabel('10Y', markerT), '12M': deltaPeriodLabel('12M', markerT)}).toEqual({
            '10Y': marked('datePicker.presets.years', {n: 10}),
            '12M': marked('datePicker.presets.months', {n: 12}),
        });
    });

    it('labels 1D — the period of the fixed Δ column, outside DELTA_PERIODS — from datePicker.presets.days, its count as n', () => {
        expect(deltaPeriodLabel('1D', markerT)).toBe(marked('datePicker.presets.days', {n: 1}));
    });

    it('returns a key it does not recognise unchanged: empty, not a period, an unknown unit, a count that is not whole, no count', () => {
        const keys = ['', 'abc', '1Q', '1.5M', 'M'];

        expect(Object.fromEntries(keys.map((key) => [key, deltaPeriodLabel(key, markerT)]))).toEqual(Object.fromEntries(keys.map((key) => [key, key])));
    });
});
