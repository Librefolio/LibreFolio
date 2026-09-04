/**
 * candlestickChartHelpers — pure unit tests (node env, no jsdom).
 *
 * Everything here is arithmetic CandlestickChart performs before handing data to
 * ECharts. The numeric formatters use toFixed (locale-independent), so the
 * expected strings are asserted directly. The tooltip-value decoder is the one
 * with a real trap — ECharts prepends the category ordinal — so it gets an
 * explicit 5-element regression case.
 */
import {describe, expect, it} from 'vitest';

import type {LineDataPoint} from './LineChart.svelte';
import {buildCandleSeriesData, computePercentageBase, formatCandlePrice, formatVolume, hasRenderableVolume, isBullishBar, parseCandleTooltipValue, toPercent} from './candlestickChartHelpers';

function pt(overrides: Partial<LineDataPoint> & {date?: string; value?: number} = {}): LineDataPoint {
    return {date: '2024-01-01', value: 0, ...overrides};
}

describe('computePercentageBase', () => {
    it('uses the first point\u2019s open when present', () => {
        expect(computePercentageBase([pt({value: 100, open: 95}), pt({value: 110})], true)).toBe(95);
    });

    it('falls back to the first point\u2019s value when open is absent', () => {
        expect(computePercentageBase([pt({value: 100}), pt({value: 110})], true)).toBe(100);
    });

    it('returns 1 (identity base) when percentage mode is off', () => {
        expect(computePercentageBase([pt({value: 100})], false)).toBe(1);
    });

    it('returns 1 for an empty series', () => {
        expect(computePercentageBase([], true)).toBe(1);
    });
});

describe('toPercent', () => {
    it('expresses the value as a delta versus the base', () => {
        expect(toPercent(110, true, 100)).toBe(10);
        expect(toPercent(90, true, 100)).toBe(-10);
        expect(toPercent(100, true, 100)).toBe(0);
    });

    it('passes the value through when percentage mode is off', () => {
        expect(toPercent(110, false, 100)).toBe(110);
    });

    it('passes the value through when the base is zero (no divide-by-zero)', () => {
        expect(toPercent(110, true, 0)).toBe(110);
    });
});

describe('buildCandleSeriesData', () => {
    it('emits [open, close, low, high] quads, synthesizing missing fields (absolute mode)', () => {
        const out = buildCandleSeriesData([pt({date: 'd0', value: 10}), pt({date: 'd1', value: 12}), pt({date: 'd2', value: 8})], false, 1);
        expect(out[0]).toEqual([10, 10, 10, 10]); // first opens at its own close
        expect(out[1]).toEqual([10, 12, 10, 12]); // open = prev close 10, high/low envelope
        expect(out[2]).toEqual([12, 8, 8, 12]);
    });

    it('prefers explicit OHLC fields over synthesis', () => {
        const out = buildCandleSeriesData([pt({value: 10, open: 5, high: 20, low: 3, close: 11})], false, 1);
        expect(out[0]).toEqual([5, 11, 3, 20]);
    });

    it('applies the percentage transform against the base', () => {
        // base = first open/value = 100; second point close 110 => +10%.
        const out = buildCandleSeriesData([pt({value: 100}), pt({value: 110})], true, 100);
        expect(out[0]).toEqual([0, 0, 0, 0]);
        expect(out[1]).toEqual([0, 10, 0, 10]);
    });

    it('yields a null slot (a gap) when a point has no usable close', () => {
        // Both close and value null: exercises the defensive `c == null` gap.
        const out = buildCandleSeriesData([{date: 'd0', value: null as unknown as number, close: null}], false, 1);
        expect(out[0]).toBeNull();
    });
});

describe('hasRenderableVolume', () => {
    it('is true when at least one point has positive volume', () => {
        expect(hasRenderableVolume([pt({volume: 0}), pt({volume: 100})])).toBe(true);
    });

    it('is false when every volume is zero, null or absent', () => {
        expect(hasRenderableVolume([pt({volume: 0}), pt({volume: null}), pt({})])).toBe(false);
        expect(hasRenderableVolume([])).toBe(false);
    });
});

describe('isBullishBar', () => {
    it('is bullish when close >= open', () => {
        expect(isBullishBar(pt({value: 10, open: 10, close: 12}))).toBe(true);
        expect(isBullishBar(pt({value: 10, open: 10, close: 10}))).toBe(true); // equal counts as bullish
    });

    it('is bearish when close < open', () => {
        expect(isBullishBar(pt({value: 10, open: 15, close: 8}))).toBe(false);
    });

    it('defaults open to close when open is absent', () => {
        expect(isBullishBar(pt({value: 10}))).toBe(true); // o = c = 10
    });

    it('falls back to value when close is null', () => {
        expect(isBullishBar(pt({value: 10, open: 5, close: null}))).toBe(true); // c = 10 >= o = 5
    });
});

describe('formatCandlePrice', () => {
    it('formats percentage mode as a signed two-decimal percent', () => {
        expect(formatCandlePrice(5, true)).toBe('+5.00%');
        expect(formatCandlePrice(0, true)).toBe('+0.00%');
        expect(formatCandlePrice(-3.5, true)).toBe('-3.50%');
    });

    it('uses 2 decimals for magnitudes >= 100', () => {
        expect(formatCandlePrice(1234.5, false)).toBe('1234.50');
        expect(formatCandlePrice(-100, false)).toBe('-100.00');
    });

    it('uses 4 decimals for magnitudes in [1, 100)', () => {
        expect(formatCandlePrice(1, false)).toBe('1.0000');
        expect(formatCandlePrice(-5.25, false)).toBe('-5.2500');
    });

    it('uses up to 6 decimals for magnitudes < 1, trimming trailing zeros', () => {
        expect(formatCandlePrice(0.5, false)).toBe('0.5');
        expect(formatCandlePrice(0.123456, false)).toBe('0.123456');
        expect(formatCandlePrice(-0.05, false)).toBe('-0.05');
    });

    it('keeps a bare zero as "0.0"', () => {
        expect(formatCandlePrice(0, false)).toBe('0.0');
    });
});

describe('formatVolume', () => {
    it('formats millions with an M suffix (2 dp)', () => {
        expect(formatVolume(2_500_000)).toBe('2.50M');
        expect(formatVolume(1_000_000)).toBe('1.00M');
        expect(formatVolume(1_234_567)).toBe('1.23M');
    });

    it('formats thousands with a K suffix (1 dp)', () => {
        expect(formatVolume(1500)).toBe('1.5K');
        expect(formatVolume(1000)).toBe('1.0K');
    });

    it('formats sub-thousand volumes as a bare integer', () => {
        expect(formatVolume(999)).toBe('999');
        expect(formatVolume(0)).toBe('0');
    });
});

describe('parseCandleTooltipValue', () => {
    it('reads a 4-element [open, close, low, high] value', () => {
        expect(parseCandleTooltipValue([100, 110, 90, 120])).toEqual({open: 100, close: 110, low: 90, high: 120, bullish: true});
    });

    it('reads a 5-element value where ECharts prepended the category ordinal', () => {
        // [index, open, close, low, high] — slice(-4) must drop the leading index.
        expect(parseCandleTooltipValue([7, 100, 110, 90, 120])).toEqual({open: 100, close: 110, low: 90, high: 120, bullish: true});
    });

    it('marks a bar bearish when close < open', () => {
        expect(parseCandleTooltipValue([110, 100, 90, 120]).bullish).toBe(false);
    });

    it('marks an equal open/close bar bullish', () => {
        expect(parseCandleTooltipValue([100, 100, 90, 120]).bullish).toBe(true);
    });
});
