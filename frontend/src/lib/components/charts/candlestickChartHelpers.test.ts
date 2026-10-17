/**
 * candlestickChartHelpers — pure unit tests (node env, no jsdom).
 *
 * Everything here is arithmetic CandlestickChart performs before handing data to
 * ECharts. The numeric formatters write their figures in the interface language
 * (M-18): the English cases run under an English UI on an en-US browser, where the
 * text is today's except for the thousands separator, and are asserted directly;
 * the M-18 describe switches the UI to French. The tooltip-value decoder is the one
 * with a real trap — ECharts prepends the category ordinal — so it gets an
 * explicit 5-element regression case. C-97c-3 (the last block): a price under
 * 0.001 keeps its significant digits in the candle tooltip.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

// The interface locale is the UI language regionalised by `navigator.language` (M-18). Node's tag
// follows the host's ICU locale, so it is pinned to en-US — jsdom's own — before any import.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatFixed} from '$lib/utils/core/formatFixed';
import {formatPercent} from '$lib/utils/core/formatPercent';
import type {LineDataPoint} from './LineChart.svelte';
import {buildCandleSeriesData, buildOhlcQuad, computePercentageBase, formatCandlePrice, formatVolume, hasRenderableVolume, isBullishBar, parseCandleTooltipValue, toPercent} from './candlestickChartHelpers';

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

describe('buildOhlcQuad', () => {
    // Generalized out of buildCandleSeriesData (G1b, for GrowthChart.svelte's P&L
    // candles) — these tests exercise it directly, as its own unit, rather than only
    // indirectly through buildCandleSeriesData below.
    it('orders the quad as [open, close, low, high] — NOT open/high/low/close — using four distinct values so a swapped pair would be caught', () => {
        // high (115) and close (110) are close but distinct, and low (95) sits before
        // both open/close numerically: a low<->high or close<->high transposition
        // mistake would change this exact result.
        expect(buildOhlcQuad(100, 110, 95, 115, false, 1)).toEqual([100, 110, 95, 115]);
    });

    it('applies the percentage transform to each of the four legs independently, against the same base', () => {
        // base = 100: open +10%, close +20%, low -10%, high +30% — four different signs/
        // magnitudes so a mixed-up leg would produce a visibly wrong percentage.
        expect(buildOhlcQuad(110, 120, 90, 130, true, 100)).toEqual([10, 20, -10, 30]);
    });

    it('passes all four legs through unchanged when percentage mode is off, regardless of baseValue', () => {
        expect(buildOhlcQuad(100, 110, 95, 115, false, 999)).toEqual([100, 110, 95, 115]);
    });

    it('passes all four legs through unchanged when the base is zero, even in percentage mode (no divide-by-zero)', () => {
        expect(buildOhlcQuad(100, 110, 95, 115, true, 0)).toEqual([100, 110, 95, 115]);
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

    it('applies the percentage transform to explicit OHLC fields too, not just synthesized ones', () => {
        // Neither existing percentage test exercises the explicit-fields branch, so a
        // regression that special-cased synthesis-vs-explicit under percentage mode
        // would slip through both. base = 100: open +5%, close +11%, low +3%, high +20%.
        const out = buildCandleSeriesData([pt({value: 111, open: 105, high: 120, low: 103, close: 111})], true, 100);
        expect(out[0]).toEqual([5, 11, 3, 20]);
    });

    it('delegates its per-point quad construction to buildOhlcQuad rather than re-deriving the [open, close, low, high] order independently (pure-refactor regression guard)', () => {
        // Synthesized case (second point borrows the first's close as its open).
        const synthesized = buildCandleSeriesData([pt({date: 'd0', value: 10}), pt({date: 'd1', value: 12})], false, 1);
        expect(synthesized[1]).toEqual(buildOhlcQuad(10, 12, 10, 12, false, 1));

        // Explicit-fields + percentage case.
        const explicit = buildCandleSeriesData([pt({value: 111, open: 105, high: 120, low: 103, close: 111})], true, 100);
        expect(explicit[0]).toEqual(buildOhlcQuad(105, 111, 103, 120, true, 100));
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
    it('formats percentage mode as a signed two-decimal percent, with no sign on a zero', () => {
        expect(formatCandlePrice(5, true)).toBe('+5.00%');
        // Why (re-pin, M-18 CP2): percentage mode goes through `formatPercent`, whose rule (CP1) is that a
        // zero is not a gain: `+0.00%` becomes `0.00%`, and a negative zero prints as a plain one.
        expect(formatCandlePrice(0, true)).toBe('0.00%');
        expect(formatCandlePrice(-0, true)).toBe('0.00%');
        expect(formatCandlePrice(-3.5, true)).toBe('-3.50%');
    });

    it('uses 2 decimals for magnitudes >= 100', () => {
        // Why (re-pin, M-18 CP2): the digits are written in the interface locale, en-US here, which
        // groups from 1,000: `1234.50` becomes `1,234.50`. Below 1,000 the text is today's.
        expect(formatCandlePrice(1234.5, false)).toBe('1,234.50');
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

    it('groups a volume of a thousand millions or more, as the interface locale writes it (M-18)', () => {
        // New contract (M-18 CP2): the digits are written in the interface locale, en-US here, which
        // groups from 1,000 — `2500.00M` becomes `2,500.00M`.
        expect(formatVolume(2_500_000_000)).toBe('2,500.00M');
    });
});

/**
 * M-18 CP2: the candle tooltip and the volume labels in the interface language.
 *
 * `formatCandlePrice` and `formatVolume` are built on `toFixed`, so a French reader gets `1234.50` and
 * `2.50M` beside amounts written `1 234,50`. Every figure is written in the interface language (the
 * developer's decision M-18, 2026-10-12), through the formatters of CP1:
 *
 *   - percentage mode is `formatPercent(v)`: `+` on a gain, no sign on a zero;
 *   - absolute mode keeps its precision by magnitude — 2 decimals from 100, 4 from 1, below 1 up to 6
 *     with the trailing zeros trimmed but at least one kept (`0` reads `0.0` in English, `0,0` in French);
 *   - a volume keeps its M with two decimals, its K with one, and is whole below a thousand.
 *
 * Expectations come from `formatPercent`/`formatFixed` given an explicit locale, never typed; each case
 * also checks that French differs from English, so a runtime without French data proves nothing.
 */
describe('formatCandlePrice and formatVolume in the interface language (M-18)', () => {
    const FR = {locale: 'fr'} as const;

    /** `value` as JSON with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
    function spelled(value: unknown): string {
        return JSON.stringify(value).replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
    }

    /** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
    async function uiLanguage(lang: 'en' | 'fr'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it('French UI: percentage mode is a French percentage — `+` on a gain, no sign on a zero', async () => {
        await uiLanguage('fr');
        const expected = {gain: formatPercent(5, FR), zero: formatPercent(0, FR), loss: formatPercent(-3.5, FR), grouped: formatPercent(1234.5, FR)};
        // Controls: French differs from English, and a zero carries no sign in either.
        expect(expected.gain, 'French differs from English').not.toBe('+5.00%');
        expect(expected.zero).not.toMatch(/^[+\-\u2212]/);

        const written = {gain: formatCandlePrice(5, true), zero: formatCandlePrice(0, true), loss: formatCandlePrice(-3.5, true), grouped: formatCandlePrice(1234.5, true)};
        expect(written, spelled(expected)).toEqual(expected);
    });

    it('French UI: absolute mode keeps its precision by magnitude — 2, 4, up to 6 decimals and at least one — in French notation', async () => {
        await uiLanguage('fr');
        const expected = {
            '1234.5': formatFixed(1234.5, 2, FR),
            '-100': formatFixed(-100, 2, FR),
            '1': formatFixed(1, 4, FR),
            '-5.25': formatFixed(-5.25, 4, FR),
            '0.5': formatFixed(0.5, 6, {trim: true, ...FR}),
            '0.123456': formatFixed(0.123456, 6, {trim: true, ...FR}),
            '-0.05': formatFixed(-0.05, 6, {trim: true, ...FR}),
            // At least one decimal: a bare zero keeps one, as English keeps `0.0`.
            '0': formatFixed(0, 1, FR),
        };
        expect(expected['0'], 'French differs from English').not.toBe('0.0');

        const written = Object.fromEntries([1234.5, -100, 1, -5.25, 0.5, 0.123456, -0.05, 0].map((value) => [String(value), formatCandlePrice(value, false)]));
        expect(written, spelled(expected)).toEqual(expected);
    });

    it('French UI: volumes in M with two decimals, in K with one, whole below a thousand — in French notation', async () => {
        await uiLanguage('fr');
        const expected = {
            '2500000000': `${formatFixed(2500, 2, FR)}M`,
            '2500000': `${formatFixed(2.5, 2, FR)}M`,
            '1234567': `${formatFixed(1.234567, 2, FR)}M`,
            '12345': `${formatFixed(12.345, 1, FR)}K`,
            '1500': `${formatFixed(1.5, 1, FR)}K`,
            '999': formatFixed(999, 0, FR),
            '0': formatFixed(0, 0, FR),
        };
        expect(expected['1500'], 'French differs from English').not.toBe('1.5K');

        const written = Object.fromEntries([2_500_000_000, 2_500_000, 1_234_567, 12_345, 1500, 999, 0].map((volume) => [String(volume), formatVolume(volume)]));
        expect(written, spelled(expected)).toEqual(expected);
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

/**
 * C-97c-3 (decision D-C97c-1 of the coordinator, 17/10): a price on screen keeps its significant digits.
 *
 * Below 1, the candle tooltip shows up to six decimals with the trailing zeros trimmed and at least one kept
 * (`toFixed(6)` decides how many): a price under 0.001 loses its digits there — 0.0000034573 reads `0.000003`,
 * 0.0000004 reads `0.0`. The contract: `formatPrice(v, {minDecimals: 1, floorDecimals: 6})` — still at least one
 * decimal and still six where the price has them, but as many as its first four significant digits need
 * (`priceFractionDigits`, formatFixed.ts). From 0.001 up the text is today's, and so are the two upper bands
 * (`formatPrice(v)` from 100, `{minDecimals: 4}` from 1) and percentage mode: the guards.
 *
 * Reds: 0.0000034573 (today `0.000003`), its negative, 0.0000004 (today `0.0`). Guards, green today and after: a
 * value of each band and on both sides of 0.001, and percentage mode. English UI on an en-US browser, checked before
 * each case: the expected digits are typed.
 */
describe('formatCandlePrice — a price under 0.001 keeps its significant digits (C-97c-3, D-C97c-1)', () => {
    beforeEach(() => {
        // The expected digits are typed: the premise that the tooltip writes en-US, checked.
        expect(uiLocale(), 'control: an English UI on the en-US browser this file pins is written en-US').toBe('en-US');
    });

    it('0.0000034573 reads 0.000003457: four significant digits, not 0.000003', () => {
        expect(formatCandlePrice(0.0000034573, false), 'below 1 (today cut at the sixth decimal: 0.000003)').toBe('0.000003457');
    });

    it('a negative price under 0.001, -0.0000034573, reads -0.000003457, not -0.000003', () => {
        expect(formatCandlePrice(-0.0000034573, false), 'below 1, negative (today -0.000003)').toBe('-0.000003457');
    });

    it('0.0000004 reads 0.0000004, not 0.0: a price under a millionth is not zero', () => {
        expect(formatCandlePrice(0.0000004, false), 'below 1 (today 0.0: toFixed(6) leaves no digit, the one kept decimal is a zero)').toBe('0.0000004');
    });

    it('guard: from 0.001 up the text is today’s — 0.00123456, 0.123456789, 0.5, 0, and the 4- and 2-decimal bands', () => {
        const written = Object.fromEntries([0.00123456, 0.123456789, 0.5, 0, 12.345678, 1234.5].map((value) => [String(value), formatCandlePrice(value, false)]));

        expect(written).toEqual({'0.00123456': '0.001235', '0.123456789': '0.123457', '0.5': '0.5', '0': '0.0', '12.345678': '12.3457', '1234.5': '1,234.50'});
    });

    it('guard: percentage mode is formatPercent’s, a tiny value included', () => {
        expect(formatCandlePrice(0.0000034573, true)).toBe(formatPercent(0.0000034573));
    });
});
