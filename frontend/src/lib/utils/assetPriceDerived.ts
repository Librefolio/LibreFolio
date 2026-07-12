/**
 * assetPriceDerived.ts — Pure, side-effect-free computation of per-asset derived price
 * state (last price, deltas over multiple periods, chart-ready data) from a raw price
 * array.
 *
 * Extracted from the Assets list page (`assets/+page.svelte`) so the SAME logic can run
 * either on the main thread (cache-hit fast path, cheap) or inside a Web Worker (fetch
 * path, where the CPU cost of processing many assets at once can otherwise monopolize
 * the main thread long enough to delay click/navigation handling — see
 * `frontend/src/lib/workers/priceProcessing.worker.ts`).
 *
 * No Svelte/DOM dependency — safe to import from a Worker script.
 *
 * @module utils/assetPriceDerived
 */

/** A single normalized price point, as consumed by computeDerivedPriceState(). */
export interface RawPricePoint {
    date: string;
    close: number | string | null;
    // Only `days_back` is ever read from this — kept as a minimal structural shape
    // (not the full generated AssetBackwardFillInfo type) so this module stays
    // decoupled from API codegen types. Accepts any object-like value defensively via
    // extractDaysBack() below, since the generated type is a wider union than this.
    backward_fill_info?: object | null;
    // Legacy camelCase fallback — some cache-hit call sites historically normalized to
    // this shape instead of backward_fill_info. Kept for exact behavioral parity with
    // the pre-extraction implementation; both are checked defensively.
    backwardFillInfo?: {daysBack?: number} | null;
}

/** Defensively read the stale-days count from either the snake_case (raw API) or
 *  camelCase (legacy internal) backward-fill shape. */
function extractDaysBack(point: RawPricePoint): number {
    const info = point.backward_fill_info;
    if (info && typeof info === 'object' && 'days_back' in info) {
        const value = (info as {days_back: unknown}).days_back;
        if (typeof value === 'number') return value;
    }
    return point.backwardFillInfo?.daysBack ?? 0;
}

/** Chart-ready point (date/value pair, with optional staleness for opacity fade). */
export interface DerivedChartPoint {
    date: string;
    value: number;
    staleDays: number;
}

export interface DerivedPriceState {
    lastPrice: number | null;
    deltaAbs: number | null;
    deltaPercent: number | null;
    chartData: DerivedChartPoint[];
    deltas: Record<string, number | null>;
}

/** Delta periods shown as table/card columns — shared by Assets and (conceptually) FX. */
export const DELTA_PERIODS = [
    {key: '1W', days: 7},
    {key: '1M', days: 30},
    {key: '3M', days: 91},
    {key: '6M', days: 182},
    {key: '1Y', days: 365},
    {key: '2Y', days: 730},
    {key: '3Y', days: 1095},
    {key: '5Y', days: 1825},
] as const;

/**
 * Compute the % change between the last chart point and the point `periodDays` before it
 * (backward-filled: the closest point at-or-before the target date).
 *
 * Scans backward from the END of `chartData` — for a long price history, the target date
 * for a short period (e.g. "1W") sits near the end of the array, so this finds it in
 * O(periodDays) instead of O(full history length). Matches the equivalent
 * computePeriodDelta() in the FX list page, which already used this pattern; the Assets
 * list page used to scan forward from the start (O(full history) for every period),
 * fixed to match this one.
 */
export function computePeriodDelta(chartData: Array<{date: string; value: number}>, periodDays: number): number | null {
    if (chartData.length === 0) return null;

    const pn = chartData[chartData.length - 1];
    if (!pn || pn.value === 0) return null;

    const targetDate = new Date(pn.date);
    targetDate.setDate(targetDate.getDate() - periodDays);
    const targetStr = targetDate.toISOString().slice(0, 10);

    let startPoint: {date: string; value: number} | null = null;
    for (let i = chartData.length - 1; i >= 0; i--) {
        if (chartData[i].date <= targetStr) {
            startPoint = chartData[i];
            break;
        }
    }

    if (!startPoint || startPoint.value === 0) return null;
    return ((pn.value - startPoint.value) / startPoint.value) * 100;
}

/**
 * Compute all derived price state (last price, abs/percent delta, chart-ready points,
 * and the full DELTA_PERIODS table) from a raw price array for ONE asset.
 *
 * Pure function: same input always produces the same output, no shared/mutable state
 * touched — safe to call from a Worker as well as the main thread.
 */
export function computeDerivedPriceState(prices: RawPricePoint[]): DerivedPriceState {
    if (prices.length === 0) {
        return {lastPrice: null, deltaAbs: null, deltaPercent: null, chartData: [], deltas: {}};
    }

    const firstPrice = prices[0]?.close != null ? Number(prices[0].close) : null;
    const lastPrice = prices[prices.length - 1]?.close != null ? Number(prices[prices.length - 1].close) : null;

    let deltaAbs: number | null = null;
    let deltaPercent: number | null = null;
    if (firstPrice !== null && lastPrice !== null && firstPrice !== 0) {
        deltaAbs = lastPrice - firstPrice;
        deltaPercent = ((lastPrice - firstPrice) / firstPrice) * 100;
    }

    const chartData: DerivedChartPoint[] = prices.map((p) => ({
        date: p.date,
        value: Number(p.close ?? 0),
        staleDays: extractDaysBack(p),
    }));

    const deltas: Record<string, number | null> = {};
    for (const period of DELTA_PERIODS) {
        deltas[period.key] = computePeriodDelta(chartData, period.days);
    }

    return {lastPrice, deltaAbs, deltaPercent, chartData, deltas};
}
