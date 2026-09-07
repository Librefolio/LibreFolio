/**
 * Pure helpers extracted from CandlestickChart.svelte.
 *
 * CandlestickChart renders on a canvas, but the interesting part is arithmetic it
 * does *before* handing data to ECharts: synthesizing an OHLC quad from a sparse
 * point, applying the percentage transform, formatting prices and volumes, and
 * decoding the tooltip value ECharts hands back. That last one hides a genuine
 * trap (ECharts prepends the category ordinal), so it earns a regression test.
 * None of this needs a DOM, so it lives here and is unit-tested in node.
 *
 * The month label and the bucket span are shared with PriceChartFull — see
 * `./priceChartHelpers` — so they are not duplicated here.
 *
 * @module charts/candlestickChartHelpers
 */

import type {LineDataPoint} from './LineChart.svelte';

/**
 * Baseline for percentage mode: the first point's open (falling back to its
 * value). Returns 1 when percentage mode is off or the series is empty, so the
 * transform below becomes an identity.
 */
export function computePercentageBase(data: LineDataPoint[], isPercentage: boolean): number {
    return isPercentage && data.length > 0 ? (data[0].open ?? data[0].value) : 1;
}

/**
 * Transform a raw value into a percentage delta versus `baseValue`. Passes the
 * value through unchanged when percentage mode is off or the base is zero (which
 * would otherwise divide by zero).
 */
export function toPercent(v: number, isPercentage: boolean, baseValue: number): number {
    return isPercentage && baseValue !== 0 ? ((v - baseValue) / baseValue) * 100 : v;
}

/**
 * ECharts candlestick data: one `[open, close, low, high]` quad per point, with
 * the percentage transform applied. DB values win; missing fields are
 * synthesized (open borrows the previous close — the first point opens at its own
 * close; high/low default to the open/close envelope). A point whose close and
 * value are both null yields a `null` slot, which ECharts renders as a gap.
 */
export function buildCandleSeriesData(data: LineDataPoint[], isPercentage: boolean, baseValue: number): (number[] | null)[] {
    return data.map((d, i) => {
        const c = d.close ?? d.value;
        if (c == null) return null;
        const prevClose = i > 0 ? (data[i - 1].close ?? data[i - 1].value) : c;
        const o = d.open ?? prevClose;
        const h = d.high ?? Math.max(o, c);
        const l = d.low ?? Math.min(o, c);
        return [toPercent(o, isPercentage, baseValue), toPercent(c, isPercentage, baseValue), toPercent(l, isPercentage, baseValue), toPercent(h, isPercentage, baseValue)];
    });
}

/** Whether any point carries a positive volume — gates the lower volume grid. */
export function hasRenderableVolume(data: LineDataPoint[]): boolean {
    return data.some((d) => d.volume != null && d.volume > 0);
}

/**
 * A bar is bullish when its close is at or above its open (open defaulting to the
 * close when absent). Drives the derived green/red bar color — the color is a
 * contract of this rule, not of any particular hex.
 */
export function isBullishBar(d: LineDataPoint): boolean {
    const c = d.close ?? d.value;
    const o = d.open ?? c;
    return c >= o;
}

/**
 * Format a price for the tooltip. Percentage mode → signed two-decimal percent.
 * Absolute mode scales precision to magnitude: ≥100 → 2 dp, ≥1 → 4 dp, otherwise
 * 6 dp with trailing zeros trimmed (a bare integer such as 0 is kept as "0.0").
 * Built on `toFixed`, so the decimal separator is always '.', independent of the
 * process locale.
 */
export function formatCandlePrice(v: number, isPercentage: boolean): string {
    if (isPercentage) return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
    if (Math.abs(v) >= 100) return v.toFixed(2);
    if (Math.abs(v) >= 1) return v.toFixed(4);
    return v.toFixed(6).replace(/0+$/, '').replace(/\.$/, '.0');
}

/** Compact volume label: millions → "…M", thousands → "…K", otherwise integer. */
export function formatVolume(vol: number): string {
    return vol >= 1_000_000 ? `${(vol / 1_000_000).toFixed(2)}M` : vol >= 1_000 ? `${(vol / 1_000).toFixed(1)}K` : vol.toFixed(0);
}

/**
 * Decode an ECharts candlestick tooltip value. For a category x-axis ECharts
 * prepends the ordinal index, so the array is either `[index, open, close, low,
 * high]` (5 items) or `[open, close, low, high]` (4 items). Taking the last four
 * is robust to both. Bullish = close ≥ open.
 */
export function parseCandleTooltipValue(value: number[]): {open: number; close: number; low: number; high: number; bullish: boolean} {
    const [open, close, low, high] = value.slice(-4);
    return {open, close, low, high, bullish: close >= open};
}
