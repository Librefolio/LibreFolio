/**
 * Pure helpers extracted from LotComparisonChart.svelte.
 *
 * LotComparisonChart overlays several lots' value and return series on a shared
 * time axis, with stacked areas, income markers and a resolution cascade. As
 * with the WAC chart, everything that is a function of inputs — parsing a
 * tooltip callback's opaque payload, colouring a lot deterministically from its
 * id, padding an auto Y range, walking the stack totals to find the plotted
 * min/max, bucketing dates and turning a zoom window into a logical date range —
 * is lifted here so it can be unit tested without an ECharts canvas.
 *
 * What is deliberately NOT here: `formatShortDate` / `formatLongDate`. Those
 * build a `new Date(dateOnlyString)` (UTC midnight) and render it in the local
 * zone, so a date-only value shows a day early west of UTC — a product defect
 * reported separately. Extracting them would enshrine the bug behind a green
 * test, so they stay in the component until the parse is fixed.
 *
 * @module brokers/lots/lotComparisonChartHelpers
 */

import {safeDecimal, safeString} from '$lib/types';
import {finiteNumber} from '$lib/utils/core/finiteNumber';
import {mapDateToBucket, type ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
import {normalizeZero} from './lotChartShared';

/** The two value provenances a lot's series can carry. */
export type LotValueSource = 'MARKET_PRICE' | 'ESTIMATED_AT_COST';

/** A padded numeric axis range. */
export interface AutoYAxisRange {
    min: number;
    max: number;
}

/** One resolved chart bucket (a day, or a week/month rollup). */
export interface BucketInfo {
    date: string;
    bucketStart: string;
    bucketEnd: string;
    resolution: ChartResolution;
}

/** The running positive/negative stack totals, keyed by x, while scanning a stacked series. */
interface StackAccumulator {
    positive: Map<string, number>;
    negative: Map<string, number>;
}

/** The shape of an ECharts tooltip/label callback param this module reads from. */
interface CallbackParam {
    axisValue?: unknown;
    data?: unknown;
    value?: unknown;
    seriesId?: unknown;
}

// ---------------------------------------------------------------------------
// Small parsers & keys
// ---------------------------------------------------------------------------

/** Narrow an arbitrary `value_source` to a known provenance, or `null`. */
export function safeValueSource(value: unknown): LotValueSource | null {
    const source = safeString(value);
    return source === 'MARKET_PRICE' || source === 'ESTIMATED_AT_COST' ? source : null;
}

/** Parse a decimal-ish value, defaulting a missing/unparseable one to 0. */
export function parseRequiredNumber(value: unknown): number {
    return safeDecimal(value) ?? 0;
}

/** The `lotId:date` composite key used to look a point up by lot and day. */
export function pointKey(lotId: number, date: string): string {
    return `${lotId}:${date}`;
}

/**
 * A deterministic per-lot line color from the lot id, spread around the hue
 * wheel by the golden angle so adjacent ids stay visually distinct; brighter and
 * less saturated in dark mode.
 */
export function lotColor(lotId: number, isDark: boolean): string {
    const hue = Math.round((lotId * 137.508) % 360);
    return isDark ? `hsl(${hue} 78% 68%)` : `hsl(${hue} 68% 44%)`;
}

/** Teal for dividends, violet for interest, per theme. */
export function incomeEventColor(type: 'DIVIDEND' | 'INTEREST', isDark: boolean): string {
    if (type === 'DIVIDEND') return isDark ? '#2dd4bf' : '#0f766e';
    return isDark ? '#a78bfa' : '#6d28d9';
}

/**
 * Format a value that is already a percentage: the sign-normalised number with a
 * `%` suffix, using two fraction digits only for small non-integers (|v| < 10 and
 * not whole), one otherwise. `locale` is exposed for deterministic tests; it
 * defaults to the machine locale, matching the component.
 */
export function formatAxisPercent(value: number, locale?: string): string {
    const normalized = normalizeZero(value);
    const abs = Math.abs(normalized);
    const decimals = abs < 10 && abs % 1 !== 0 ? 2 : 1;
    return `${normalized.toLocaleString(locale, {minimumFractionDigits: 0, maximumFractionDigits: decimals})}%`;
}

/**
 * Recover a lot id encoded into a series id as `${prefix}${id}` (e.g.
 * `return-42`). Returns `null` when the series id is not a string/number, does
 * not carry the prefix, or the suffix is not an integer.
 */
export function lotIdFromSeriesId(param: CallbackParam, prefix: string): number | null {
    const raw = typeof param?.seriesId === 'string' || typeof param?.seriesId === 'number' ? String(param.seriesId) : '';
    if (!raw.startsWith(prefix)) return null;
    const lotId = Number(raw.slice(prefix.length));
    return Number.isInteger(lotId) ? lotId : null;
}

/** Whether a series id belongs to one of the chart's internal (non-tooltip) series. */
export function isInternalSeriesId(seriesId: unknown, internalIds: ReadonlyArray<string>): boolean {
    return internalIds.includes(String(seriesId ?? ''));
}

// ---------------------------------------------------------------------------
// Tooltip payload extraction
// ---------------------------------------------------------------------------

/**
 * The numeric y of a tooltip param, unwrapping the `[x, y]` array form, and
 * treating null / empty / non-finite as absent.
 */
export function seriesValue(param: CallbackParam): number | null {
    const rawValue = Array.isArray(param?.value) ? param.value[1] : param?.value;
    if (rawValue == null || rawValue === '') return null;
    const value = Number(rawValue);
    return Number.isFinite(value) ? value : null;
}

/**
 * Parse anything ECharts might hand back as an x value into an epoch ms: a Date,
 * a finite number (already ms), a numeric string, or a parseable date string.
 * Everything else (blank, non-finite, unparseable) is `null`.
 */
export function parseTimeMs(value: unknown): number | null {
    if (value instanceof Date) {
        const time = value.getTime();
        return Number.isFinite(time) ? time : null;
    }
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    if (typeof value !== 'string' || value.trim() === '') return null;

    const numeric = Number(value);
    if (Number.isFinite(numeric)) return numeric;

    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
}

/**
 * The x value of a single tooltip param, trying `axisValue` first and then the
 * various `[x, …]` array shapes ECharts uses for `data` / `value`.
 */
export function tooltipXValue(param: CallbackParam): unknown {
    if (param?.axisValue != null) return param.axisValue;
    const nestedValue = (param?.data as {value?: unknown} | null | undefined)?.value;
    if (Array.isArray(nestedValue)) return nestedValue[0];
    if (Array.isArray(param?.data)) return (param.data as unknown[])[0];
    if (Array.isArray(param?.value)) return (param.value as unknown[])[0];
    return null;
}

/** The first usable (number or non-blank string) x value across all hovered params. */
export function tooltipRawDate(params: ReadonlyArray<CallbackParam>): number | string {
    for (const param of params) {
        const raw = tooltipXValue(param);
        if (typeof raw === 'number' || (typeof raw === 'string' && raw.trim() !== '')) return raw;
    }
    return '';
}

/** {@link tooltipRawDate} parsed to epoch ms, or `null`. */
export function tooltipTimestamp(params: ReadonlyArray<CallbackParam>): number | null {
    return parseTimeMs(tooltipRawDate(params));
}

/**
 * The last point whose date is at or before `timestampMs`, scanning a
 * date-ordered array forward and stopping at the first point past the target.
 * Points with an unparseable date are skipped.
 */
export function findPointAtOrBefore<T extends {date: string}>(points: ReadonlyArray<T>, timestampMs: number): T | null {
    let found: T | null = null;
    for (const point of points) {
        const pointTime = parseTimeMs(point.date);
        if (pointTime == null) continue;
        if (pointTime > timestampMs) break;
        found = point;
    }
    return found;
}

// ---------------------------------------------------------------------------
// Auto Y-axis range
// ---------------------------------------------------------------------------

/**
 * Unwrap one series datum (an `[x, y]` tuple, a `{value}` wrapper, or a bare
 * number) into a `{key, value}` for stacking. The key is the x for tuples, or a
 * synthetic per-index key for bare values so unstacked points never collide.
 * Non-finite / null values yield `null` (skip).
 */
export function chartSeriesPointValue(raw: unknown, index: number): {key: string; value: number | null} | null {
    const source = Array.isArray(raw) ? raw : raw && typeof raw === 'object' && 'value' in raw ? (raw as {value?: unknown}).value : raw;

    if (Array.isArray(source)) {
        const x = source[0];
        if (typeof x !== 'string' && typeof x !== 'number') return null;
        const y = source[1];
        return {key: String(x), value: y == null ? null : finiteNumber(y)};
    }

    const value = source == null ? null : finiteNumber(source);
    return value == null ? null : {key: `__index_${index}`, value};
}

/**
 * Pad a `[min, max]` by 5% of its span (or 5% of the magnitude when the span is
 * zero, floored at EPSILON), then pull a padded bound back across zero so a
 * strictly-positive series never shows a negative floor and vice-versa.
 */
export function paddedAutoYAxisRange(min: number, max: number): AutoYAxisRange {
    const range = max - min;
    const magnitude = Math.max(Math.abs(min), Math.abs(max));
    const padding = range > 0 ? range * 0.05 : Math.max(magnitude * 0.05, Number.EPSILON);
    let paddedMin = min - padding;
    let paddedMax = max + padding;

    if (min > 0 && paddedMin <= 0) paddedMin = min * 0.95;
    if (max < 0 && paddedMax >= 0) paddedMax = max * 0.95;

    return {min: paddedMin, max: paddedMax};
}

/**
 * The padded auto Y range across a set of series, honouring stacks: within a
 * named stack, values at the same x accumulate (separately for the positive and
 * negative sides, as ECharts stacks them), and it is the running totals that set
 * the extent. Zero-height contributions are ignored. Returns `null` when nothing
 * plottable was found.
 */
export function computeAutoYAxisRange(series: ReadonlyArray<{data?: unknown; stack?: unknown}>): AutoYAxisRange | null {
    let min: number | null = null;
    let max: number | null = null;
    const stackTotals = new Map<string, StackAccumulator>();

    for (const item of series) {
        const data = item.data;
        if (!Array.isArray(data)) continue;

        const stack = item.stack;
        const stackKey = typeof stack === 'string' && stack.trim() !== '' ? stack : null;
        let accumulator: StackAccumulator | null = null;
        if (stackKey) {
            accumulator = stackTotals.get(stackKey) ?? {positive: new Map<string, number>(), negative: new Map<string, number>()};
            stackTotals.set(stackKey, accumulator);
        }

        for (const [index, raw] of data.entries()) {
            const point = chartSeriesPointValue(raw, index);
            if (!point || point.value == null) continue;

            let plottedValue = point.value;
            if (accumulator) {
                const totals = plottedValue >= 0 ? accumulator.positive : accumulator.negative;
                plottedValue = (totals.get(point.key) ?? 0) + plottedValue;
                totals.set(point.key, plottedValue);
            }

            if (plottedValue === 0) continue;
            min = min == null ? plottedValue : Math.min(min, plottedValue);
            max = max == null ? plottedValue : Math.max(max, plottedValue);
        }
    }

    return min == null || max == null ? null : paddedAutoYAxisRange(min, max);
}

// ---------------------------------------------------------------------------
// Bucketing, counts & zoom windows
// ---------------------------------------------------------------------------

/**
 * Collapse source dates into buckets for a resolution. At daily resolution each
 * date is its own bucket; otherwise consecutive dates that fall in the same
 * week/month bucket are merged, keyed by the bucket end.
 */
export function buildBucketInfos(sourceDates: ReadonlyArray<string>, resolution: ChartResolution): BucketInfo[] {
    if (resolution === 'daily') {
        return sourceDates.map((date) => ({date, bucketStart: date, bucketEnd: date, resolution}));
    }

    const buckets: BucketInfo[] = [];
    let lastBucketEnd: string | null = null;

    for (const date of sourceDates) {
        const {bucketStart, bucketEnd} = mapDateToBucket(date, resolution);
        if (bucketEnd === lastBucketEnd) continue;

        buckets.push({date: bucketEnd, bucketStart, bucketEnd, resolution});
        lastBucketEnd = bucketEnd;
    }

    return buckets;
}

/**
 * How many daily / weekly / monthly buckets the source dates span within an
 * inclusive `[startDate, endDate]` window. Weekly and monthly are distinct
 * bucket-end counts; dates outside the window are ignored.
 */
export function computeBucketCounts(sourceDates: ReadonlyArray<string>, startDate: string, endDate: string): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
    let dailyCount = 0;
    const weekly = new Set<string>();
    const monthly = new Set<string>();

    for (const date of sourceDates) {
        if (date < startDate || date > endDate) continue;
        dailyCount += 1;
        weekly.add(mapDateToBucket(date, 'weekly').bucketEnd);
        monthly.add(mapDateToBucket(date, 'monthly').bucketEnd);
    }

    return {dailyCount, weeklyCount: weekly.size, monthlyCount: monthly.size};
}

/**
 * The dataZoom `{start, end}` percentages that frame `[startDate, endDate]` at a
 * given resolution. With one bucket or fewer the whole 0..100 is returned; the
 * start bucket is the first ending at-or-after `startDate`, the end bucket the
 * last starting at-or-before `endDate`.
 */
export function buildZoomWindowForRange(sourceDates: ReadonlyArray<string>, resolution: ChartResolution, startDate: string, endDate: string): {start: number; end: number} {
    const buckets = buildBucketInfos(sourceDates, resolution);
    if (buckets.length <= 1) return {start: 0, end: 100};

    const startIndex = Math.max(
        0,
        buckets.findIndex((bucket) => bucket.bucketEnd >= startDate),
    );
    const endIndex = Math.max(
        startIndex,
        buckets.findLastIndex((bucket) => bucket.bucketStart <= endDate),
    );
    const denominator = buckets.length - 1;

    return {
        start: (startIndex / denominator) * 100,
        end: (endIndex / denominator) * 100,
    };
}

/**
 * Map a zoom `{start, end}` percentage window onto a bucket list to get the
 * visible `[startDate, endDate]`. Returns `null` for an empty bucket list. The
 * start index floors, the end index ceils (and never precedes start), so a
 * narrow window still resolves to at least one bucket.
 */
export function logicalRangeFromBuckets(buckets: ReadonlyArray<BucketInfo>, start: number, end: number): {startDate: string; endDate: string} | null {
    if (buckets.length === 0) return null;
    const maxIndex = Math.max(buckets.length - 1, 0);
    const startIndex = Math.max(0, Math.min(maxIndex, Math.floor((start / 100) * maxIndex)));
    const endIndex = Math.max(startIndex, Math.min(maxIndex, Math.ceil((end / 100) * maxIndex)));
    return {startDate: buckets[startIndex].bucketStart, endDate: buckets[endIndex].bucketEnd};
}
