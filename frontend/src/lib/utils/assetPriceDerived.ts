/**
 * assetPriceDerived.ts — Pure, side-effect-free computation of per-asset derived price
 * state (last price, the delta over the range, chart-ready data) from a raw price
 * array. The Δ columns of fixed periods (1D … 5Y) are not computed here: the backend
 * does (`utils/periodChanges.ts`, X-R53).
 *
 * Extracted from the Assets list page (`assets/+page.svelte`) so the SAME logic can run
 * either on the main thread (cache-hit fast path, cheap) or inside a Web Worker (fetch
 * path, where the CPU cost of processing many assets at once can otherwise monopolize
 * the main thread long enough to delay click/navigation handling — see
 * `frontend/src/lib/workers/priceProcessing.worker.ts`).
 *
 * Also hosts `AssetPricePoint`/`apiPricesToAssetPricePoints` (moved here from
 * `assetPriceStoreRegistry.ts`, which re-exports them for backward compatibility): that
 * file imports the Zodios HTTP client for an unrelated function, and Vite's worker
 * bundler cannot resolve that client's SvelteKit runtime dependencies (`$app/environment`
 * and similar) outside the main app's build context. Keeping this module free of ANY
 * such dependency is what lets the Worker import it directly.
 *
 * No Svelte/DOM/Zodios dependency — safe to import from a Worker script.
 *
 * @module utils/assetPriceDerived
 */

import type {TimeSeriesPoint} from '$lib/stores/core/TimeSeriesStore';

/**
 * Asset price time-series data point.
 * Derived from POST /assets/prices/query response.
 */
export interface AssetPricePoint extends TimeSeriesPoint {
    date: string;
    close: number;
    open: number | null;
    high: number | null;
    low: number | null;
    volume: number | null;
    currency: string | null;
    originalClose: number | null;
    backwardFillInfo: {
        daysBack: number;
    } | null;
}

/**
 * Convert raw (already Zod-validated) API price points to the internal
 * AssetPricePoint cache format.
 */
export function apiPricesToAssetPricePoints(prices: any[]): AssetPricePoint[] {
    return prices.map((p) => ({
        date: p.date,
        close: Number(p.close ?? 0),
        open: p.open != null ? Number(p.open) : null,
        high: p.high != null ? Number(p.high) : null,
        low: p.low != null ? Number(p.low) : null,
        volume: p.volume != null ? Number(p.volume) : null,
        currency: p.currency ?? null,
        originalClose: p.original_close != null ? Number(p.original_close) : null,
        backwardFillInfo: p.backward_fill_info ? {daysBack: p.backward_fill_info.days_back ?? 0} : null,
    }));
}

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
 *  camelCase (legacy internal) backward-fill shape: 0 for a stored row, more for a point filled backward from one.
 *  The one home of that rule: the sync dialog's warning reads it too (C-66). */
export function extractDaysBack(point: Pick<RawPricePoint, 'backward_fill_info' | 'backwardFillInfo'>): number {
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
}

/** Catalog keys of a duration label by unit letter: `{n}` + the reader's unit letter, the date picker's presets. */
const DURATION_LABEL_KEYS: Readonly<Record<string, string>> = {
    D: 'datePicker.presets.days',
    W: 'datePicker.presets.weeks',
    M: 'datePicker.presets.months',
    Y: 'datePicker.presets.years',
};

export type DurationLabelTranslate = (key: string, options?: {values?: Record<string, string | number>}) => string;

/** The reader's label of a period key such as `1D`, `1W` or `3M` (`1G`, `1S`, `3M` in Italian); an unrecognised key is returned as it is. */
export function deltaPeriodLabel(key: string, t: DurationLabelTranslate): string {
    const match = /^(\d+)([DWMY])$/.exec(key);
    if (!match) return key;
    return t(DURATION_LABEL_KEYS[match[2]], {values: {n: Number(match[1])}});
}

/**
 * Compute all derived price state (last price, abs/percent delta over the range,
 * chart-ready points) from a raw price array for ONE asset.
 *
 * Pure function: same input always produces the same output, no shared/mutable state
 * touched — safe to call from a Worker as well as the main thread.
 */
export function computeDerivedPriceState(prices: RawPricePoint[]): DerivedPriceState {
    if (prices.length === 0) {
        return {lastPrice: null, deltaAbs: null, deltaPercent: null, chartData: []};
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

    return {lastPrice, deltaAbs, deltaPercent, chartData};
}
