/**
 * timeSeriesAggregation.ts — Shared chart bucketing, aggregation, density, and signal downsampling helpers.
 *
 * Implements contract defined in:
 * - impl_plan_chart_resolution_00_foundation.md
 * - impl_plan_chart_resolution_04_signals_overlay.md
 *
 * All date arithmetic uses UTC ISO-day logic to avoid timezone drift.
 */

import type {RenderedSignal} from '$lib/charts/signals';

import type {LineDataPoint} from './LineChart.svelte';

export type ChartResolution = 'daily' | 'weekly' | 'monthly';

export interface BucketMeta {
    bucketStart: string;
    bucketEnd: string;
    resolution: ChartResolution;
    sourcePointCount: number;
}

type BucketedLineDataPoint = LineDataPoint & BucketMeta;

interface BucketGroup {
    bucketStart: string;
    bucketEnd: string;
    key: string;
    points: LineDataPoint[];
    startIndex: number;
}

/**
 * Which visual grammar a chart renders in. It decides how narrow a bucket slot may get
 * before the resolution escalates — NOT how buckets are computed, which is identical for
 * every grammar.
 */
export type ChartGrammar = 'line' | 'candle';

const LINE_HIGH_DENSITY_THRESHOLD = 1.3;
const LINE_LOW_DENSITY_THRESHOLD = 0.8;

/**
 * PROVISIONAL (2026-09-21) — a legibility judgement, not a measurement.
 *
 * A line is continuous, so sub-pixel bucket density is harmless: the line grammar tolerates
 * 1.3 buckets/px, which lets a slot shrink to ~0.77px. A candle cannot live there — it has
 * to render a body with two visible edges plus a wick, or it degenerates into a vertical
 * stroke, which is exactly the reported symptom.
 *
 * 8px is derived from "body + 2 edges + inter-candle gap", NOT from measuring a real
 * rendering. Change it by looking at candles on screen rather than by reasoning about
 * pixels. Marked explicitly so it cannot become permanent by inertia.
 *
 * Exported precisely BECAUSE it is provisional: its regression test asserts that every
 * candle resolution clears this floor, and a test carrying its own copy of the number would
 * keep guarding the old floor — silently — the moment this one is adjusted.
 */
export const CANDLE_MIN_SLOT_PX = 8;

/**
 * The de-escalation threshold is deliberately NOT independently chosen: it is the high
 * threshold scaled by the line grammar's own ratio (0.8 / 1.3), so the hysteresis band keeps
 * the same relative width in every grammar. One number is a judgement; two would have been
 * two judgements.
 */
const HYSTERESIS_RATIO = LINE_LOW_DENSITY_THRESHOLD / LINE_HIGH_DENSITY_THRESHOLD;

const DENSITY_THRESHOLDS: Record<ChartGrammar, {high: number; low: number}> = {
    line: {high: LINE_HIGH_DENSITY_THRESHOLD, low: LINE_LOW_DENSITY_THRESHOLD},
    candle: {high: 1 / CANDLE_MIN_SLOT_PX, low: (1 / CANDLE_MIN_SLOT_PX) * HYSTERESIS_RATIO},
};

/** Parse ISO YYYY-MM-DD into UTC Date at midnight. */
function parseDate(iso: string): Date {
    const [year, month, day] = iso.split('-').map(Number);
    return new Date(Date.UTC(year, month - 1, day));
}

/** Format UTC Date back to ISO YYYY-MM-DD. */
function formatDate(date: Date): string {
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/** Return new UTC Date shifted by N calendar days. */
function addDays(date: Date, days: number): Date {
    const result = new Date(date.getTime());
    result.setUTCDate(result.getUTCDate() + days);
    return result;
}

/** Group sorted points by logical bucket while preserving input order. */
function groupPointsByBucket(points: LineDataPoint[], resolution: ChartResolution): BucketGroup[] {
    if (points.length === 0) return [];

    const groups: BucketGroup[] = [];

    for (const [index, point] of points.entries()) {
        const {bucketStart, bucketEnd} = mapDateToBucket(point.date, resolution);
        const key = `${bucketStart}|${bucketEnd}`;
        const current = groups[groups.length - 1];

        if (!current || current.key !== key) {
            groups.push({
                bucketStart,
                bucketEnd,
                key,
                points: [point],
                startIndex: index,
            });
            continue;
        }

        current.points.push(point);
    }

    return groups;
}

/** Shallow-clone point and attach canonical bucket metadata. */
function withBucketMeta(point: LineDataPoint, meta: BucketMeta, renderDate: string = point.date, representativeDate: string = point.date): BucketedLineDataPoint {
    return {
        ...point,
        ...meta,
        date: renderDate,
        representativeDate,
    };
}

/** Map a real date to its logical chart bucket. */
export function mapDateToBucket(date: string, resolution: ChartResolution): {bucketStart: string; bucketEnd: string} {
    if (resolution === 'daily') {
        return {bucketStart: date, bucketEnd: date};
    }

    const parsed = parseDate(date);

    if (resolution === 'weekly') {
        const utcDay = parsed.getUTCDay();
        const isoDay = utcDay === 0 ? 7 : utcDay;
        const weekStart = addDays(parsed, 1 - isoDay);
        const weekEnd = addDays(weekStart, 6);
        return {
            bucketStart: formatDate(weekStart),
            bucketEnd: formatDate(weekEnd),
        };
    }

    const year = parsed.getUTCFullYear();
    const month = parsed.getUTCMonth();
    const monthStart = new Date(Date.UTC(year, month, 1));
    const monthEnd = new Date(Date.UTC(year, month + 1, 0));

    return {
        bucketStart: formatDate(monthStart),
        bucketEnd: formatDate(monthEnd),
    };
}

/**
 * Aggregate line-like series with end-of-period semantics.
 * Daily path returns original array by reference.
 */
export function aggregateLineSeries(points: LineDataPoint[], resolution: ChartResolution): LineDataPoint[] {
    if (resolution === 'daily') return points;
    if (points.length === 0) return [];

    return groupPointsByBucket(points, resolution).map((group) => {
        const lastPoint = group.points[group.points.length - 1];
        return withBucketMeta(lastPoint, {
            bucketStart: group.bucketStart,
            bucketEnd: group.bucketEnd,
            resolution,
            sourcePointCount: group.points.length,
        });
    });
}

/**
 * Aggregate sparse economic-flow series (e.g. signed DIVIDEND/INTEREST buckets, G1c)
 * by SUMMING every point that falls in a bucket — never end-of-period/last-value
 * semantics (that would silently drop every day but the last one's flow). Distinct
 * from aggregateLineSeries (cumulative running totals: NAV, P&L) and aggregateOHLCV
 * (already-composed daily candles: first/max/min/last) — a flow value has no
 * "current balance" to read at the end of a bucket, only a sum of what occurred in it.
 * Daily path returns original array by reference.
 */
export function aggregateSumSeries(points: LineDataPoint[], resolution: ChartResolution): LineDataPoint[] {
    if (resolution === 'daily') return points;
    if (points.length === 0) return [];

    return groupPointsByBucket(points, resolution).map((group) => {
        const sum = group.points.reduce((total, point) => total + point.value, 0);
        const lastPoint = group.points[group.points.length - 1];
        return withBucketMeta(
            {...lastPoint, value: sum},
            {
                bucketStart: group.bucketStart,
                bucketEnd: group.bucketEnd,
                resolution,
                sourcePointCount: group.points.length,
            },
        );
    });
}

/**
 * Aggregate OHLCV series with standard candlestick semantics.
 * Daily path returns original array by reference.
 */
export function aggregateOHLCV(points: LineDataPoint[], resolution: ChartResolution): LineDataPoint[] {
    if (resolution === 'daily') return points;
    if (points.length === 0) return [];

    return groupPointsByBucket(points, resolution).map((group) => {
        const firstPoint = group.points[0];
        const lastPoint = group.points[group.points.length - 1];

        let open: number | null | undefined;
        let close: number | null | undefined;
        let high: number | null | undefined;
        let low: number | null | undefined;
        let volumeSum = 0;
        let sawVolume = false;

        for (const point of group.points) {
            if (open == null && point.open != null) open = point.open;
            if (point.close != null) close = point.close;
            if (point.high != null) high = high == null ? point.high : Math.max(high, point.high);
            if (point.low != null) low = low == null ? point.low : Math.min(low, point.low);

            if (point.volume != null) {
                volumeSum += point.volume;
                sawVolume = true;
            }
        }

        const aggregatedClose = close ?? lastPoint.close ?? lastPoint.value;

        return withBucketMeta(
            {
                ...lastPoint,
                open: open ?? firstPoint.open ?? null,
                close: close ?? lastPoint.close ?? null,
                high: high ?? lastPoint.high ?? null,
                low: low ?? lastPoint.low ?? null,
                volume: sawVolume ? volumeSum : null,
                value: aggregatedClose,
            },
            {
                bucketStart: group.bucketStart,
                bucketEnd: group.bucketEnd,
                resolution,
                sourcePointCount: group.points.length,
            },
        );
    });
}

/**
 * Aggregate Bollinger-style envelope data.
 * Daily path preserves input references.
 */
export function aggregateEnvelope(upper: number[], middleData: LineDataPoint[], lower: number[], resolution: ChartResolution): {upper: number[]; middle: LineDataPoint[]; lower: number[]} {
    if (resolution === 'daily') {
        return {upper, middle: middleData, lower};
    }

    if (middleData.length === 0) {
        return {upper: [], middle: [], lower: []};
    }

    const groups = groupPointsByBucket(middleData, resolution);
    const middle = aggregateLineSeries(middleData, resolution);

    const aggregatedUpper = groups.map((group) => {
        let maxValue = upper[group.startIndex];

        for (let offset = 1; offset < group.points.length; offset++) {
            maxValue = Math.max(maxValue, upper[group.startIndex + offset]);
        }

        return maxValue;
    });

    const aggregatedLower = groups.map((group) => {
        let minValue = lower[group.startIndex];

        for (let offset = 1; offset < group.points.length; offset++) {
            minValue = Math.min(minValue, lower[group.startIndex + offset]);
        }

        return minValue;
    });

    return {
        upper: aggregatedUpper,
        middle,
        lower: aggregatedLower,
    };
}

interface RenderBucket {
    key: string;
    bucketStart: string;
    bucketEnd: string;
    renderDate: string;
}

function renderBuckets(points: LineDataPoint[], resolution: ChartResolution): RenderBucket[] {
    return points.map((point) => {
        const mapped = mapDateToBucket(point.date, resolution);
        const bucketStart = point.bucketStart ?? mapped.bucketStart;
        const bucketEnd = point.bucketEnd ?? mapped.bucketEnd;
        return {
            key: `${bucketStart}|${bucketEnd}`,
            bucketStart,
            bucketEnd,
            renderDate: point.date,
        };
    });
}

function signalGroups(points: LineDataPoint[], resolution: ChartResolution): Map<string, LineDataPoint[]> {
    const grouped = new Map<string, LineDataPoint[]>();
    for (const point of points) {
        const {bucketStart, bucketEnd} = mapDateToBucket(point.date, resolution);
        const key = `${bucketStart}|${bucketEnd}`;
        const bucket = grouped.get(key);
        if (bucket) bucket.push(point);
        else grouped.set(key, [point]);
    }
    for (const bucket of grouped.values()) bucket.sort((left, right) => left.date.localeCompare(right.date));
    return grouped;
}

export function selectSignalRepresentative(points: LineDataPoint[], profile: RenderedSignal['aggregationProfile']): LineDataPoint | null {
    if (points.length === 0) return null;
    const ordered = [...points].sort((left, right) => left.date.localeCompare(right.date));
    if (profile === 'first_with_range') return ordered[0];
    if (profile === 'last_with_range') return ordered[ordered.length - 1];
    if (profile === 'min_with_range') {
        return ordered.reduce((selected, point) => (point.value < selected.value ? point : selected));
    }
    if (profile === 'max_with_range') {
        return ordered.reduce((selected, point) => (point.value > selected.value ? point : selected));
    }
    throw new Error(`Aggregation profile '${profile}' is not valid for a scalar signal series`);
}

function renderRepresentative(point: LineDataPoint, bucket: RenderBucket, resolution: ChartResolution, sourcePointCount: number): LineDataPoint {
    return withBucketMeta(
        point,
        {
            bucketStart: bucket.bucketStart,
            bucketEnd: bucket.bucketEnd,
            resolution,
            sourcePointCount,
        },
        bucket.renderDate,
        point.date,
    );
}

interface IndexedBandValue {
    index: number;
    value: number;
    date: string;
}

function bandRepresentative(values: number[], points: LineDataPoint[], indexes: number[], mode: 'min' | 'max' | 'last'): IndexedBandValue {
    const candidates = indexes.map((index) => ({index, value: values[index], date: points[index].date})).sort((left, right) => left.date.localeCompare(right.date));
    if (candidates.length === 0) throw new Error('Cannot aggregate an empty band bucket');
    if (mode === 'last') return candidates[candidates.length - 1];
    return candidates.reduce((selected, candidate) => {
        if (mode === 'min') return candidate.value < selected.value ? candidate : selected;
        return candidate.value > selected.value ? candidate : selected;
    });
}

/** Downsample rendered overlay signal by logical bucket key. */
export function downsampleRenderedSignal(signal: RenderedSignal, resolution: ChartResolution, bucketedData: LineDataPoint[]): RenderedSignal {
    if (resolution === 'daily') return signal;

    const buckets = renderBuckets(bucketedData, resolution);

    const isBandSignal =
        signal.seriesType === 'band' &&
        signal.bandData != null &&
        Array.isArray(signal.bandData.upper) &&
        Array.isArray(signal.bandData.middle) &&
        Array.isArray(signal.bandData.lower) &&
        signal.bandData.upper.length === signal.data.length &&
        signal.bandData.middle.length === signal.data.length &&
        signal.bandData.lower.length === signal.data.length;

    if (isBandSignal) {
        if (signal.aggregationProfile !== 'band_envelope') {
            throw new Error(`Band signal '${signal.id}' requires band_envelope aggregation`);
        }
        const bandData = signal.bandData!;
        const indexesByBucket = new Map<string, number[]>();
        signal.data.forEach((point, index) => {
            const {bucketStart, bucketEnd} = mapDateToBucket(point.date, resolution);
            const key = `${bucketStart}|${bucketEnd}`;
            const indexes = indexesByBucket.get(key);
            if (indexes) indexes.push(index);
            else indexesByBucket.set(key, [index]);
        });
        const filteredUpper: number[] = [];
        const filteredLower: number[] = [];
        const filteredMiddle: LineDataPoint[] = [];
        const observedDates: NonNullable<NonNullable<RenderedSignal['bandData']>['observedDates']> = [];

        for (const bucket of buckets) {
            const indexes = indexesByBucket.get(bucket.key);
            if (!indexes?.length) continue;
            const lower = bandRepresentative(bandData.lower, signal.data, indexes, 'min');
            const middle = bandRepresentative(bandData.middle, signal.data, indexes, 'last');
            const upper = bandRepresentative(bandData.upper, signal.data, indexes, 'max');
            if (lower.value > middle.value || middle.value > upper.value) {
                throw new Error(`Band signal '${signal.id}' produced an invalid aggregated envelope`);
            }
            filteredMiddle.push(renderRepresentative(signal.data[middle.index], bucket, resolution, indexes.length));
            filteredUpper.push(upper.value);
            filteredLower.push(lower.value);
            observedDates.push({
                lower: lower.date,
                middle: middle.date,
                upper: upper.date,
            });
        }

        return {
            ...signal,
            data: filteredMiddle,
            bandData: {
                middle: filteredMiddle.map((point) => point.value),
                upper: filteredUpper,
                lower: filteredLower,
                observedDates,
            },
        };
    }

    if (signal.seriesType === 'band') {
        throw new Error(`Band signal '${signal.id}' is missing aligned bandData`);
    }
    if (signal.aggregationProfile === 'band_envelope' || signal.aggregationProfile === 'events_verbatim') {
        throw new Error(`Signal '${signal.id}' has incompatible aggregation profile '${signal.aggregationProfile}'`);
    }

    const grouped = signalGroups(signal.data, resolution);
    const filteredData = buckets.flatMap((bucket) => {
        const points = grouped.get(bucket.key);
        if (!points?.length) return [];
        const representative = selectSignalRepresentative(points, signal.aggregationProfile);
        return representative ? [renderRepresentative(representative, bucket, resolution, points.length)] : [];
    });

    return {
        ...signal,
        data: filteredData,
    };
}

/** Compute bucket density in bucket/px. */
export function computeDensity(bucketCount: number, plotWidthPx: number): number {
    if (plotWidthPx <= 0) return 0;
    return bucketCount / plotWidthPx;
}

/**
 * Choose chart resolution using shared hysteresis thresholds.
 *
 * `grammar` defaults to 'line', so every existing caller keeps its exact previous behavior
 * by construction rather than by remembering to pass the old value.
 */
export function chooseResolution(current: ChartResolution, counts: {dailyCount: number; weeklyCount: number; monthlyCount: number}, plotWidthPx: number, grammar: ChartGrammar = 'line'): ChartResolution {
    const {high, low} = DENSITY_THRESHOLDS[grammar];

    if (current === 'daily') {
        const densityDaily = computeDensity(counts.dailyCount, plotWidthPx);
        return densityDaily > high ? 'weekly' : 'daily';
    }

    if (current === 'weekly') {
        const densityDaily = computeDensity(counts.dailyCount, plotWidthPx);
        const densityWeekly = computeDensity(counts.weeklyCount, plotWidthPx);

        if (densityDaily < low) return 'daily';
        if (densityWeekly > high) return 'monthly';
        return 'weekly';
    }

    const densityWeekly = computeDensity(counts.weeklyCount, plotWidthPx);
    return densityWeekly < low ? 'weekly' : 'monthly';
}

/**
 * Cascade the hysteresis state machine from `current` through as many hops as needed
 * until it stabilizes, instead of applying only one hop per call.
 *
 * `chooseResolution()` intentionally advances by at most one tier per call — that
 * one-hop-at-a-time behavior is what lets a CONTINUOUSLY firing zoom gesture (many rapid
 * dataZoom ticks, each re-evaluating hysteresis incrementally) settle correctly without
 * skipping a tier's dead zone. But a caller that only gets ONE settled evaluation per
 * gesture (e.g. a debounced "zoom finished" recompute firing once after a single decisive
 * zoom, or a cold-start render) needs the FULL cascade in that one evaluation — otherwise
 * a gesture that jumps 2+ tiers at once (e.g. from monthly-density straight to
 * daily-density in one fast zoom) gets stuck at the intermediate tier (weekly) until some
 * OTHER dataZoom tick happens to fire and trigger a second hop.
 *
 * Starting from the true current resolution (rather than always restarting from 'daily')
 * matters: in a hysteresis dead zone (density between the low/high thresholds), the
 * correct answer depends on where you came from — cascading from the real `current`
 * preserves that "stay put" memory, it only closes the gap for multi-tier jumps.
 */
export function cascadeResolution(current: ChartResolution, counts: {dailyCount: number; weeklyCount: number; monthlyCount: number}, plotWidthPx: number, grammar: ChartGrammar = 'line'): ChartResolution {
    let resolution = current;
    // At most 2 hops (daily->weekly->monthly, or the reverse) can ever be needed; loop defensively.
    for (let i = 0; i < 3; i++) {
        const next = chooseResolution(resolution, counts, plotWidthPx, grammar);
        if (next === resolution) break;
        resolution = next;
    }
    return resolution;
}

/**
 * Choose the resolution for a FRESH/cold render, where there is no prior "current"
 * resolution to be hysteretic about (e.g. first paint, or the visible range just reset
 * to the dataset's full span). Equivalent to cascading from 'daily'.
 */
export function chooseInitialResolution(counts: {dailyCount: number; weeklyCount: number; monthlyCount: number}, plotWidthPx: number, grammar: ChartGrammar = 'line'): ChartResolution {
    return cascadeResolution('daily', counts, plotWidthPx, grammar);
}

/** Group event markers by rendered bucket end date. */
export function bucketEventMarkers<M extends {date: string}>(markers: M[], resolution: ChartResolution): Map<string, M[]> {
    const grouped = new Map<string, M[]>();

    for (const marker of markers) {
        const key = resolution === 'daily' ? marker.date : mapDateToBucket(marker.date, resolution).bucketEnd;
        const bucket = grouped.get(key);

        if (bucket) {
            bucket.push(marker);
        } else {
            grouped.set(key, [marker]);
        }
    }

    for (const bucket of grouped.values()) {
        bucket.sort((left, right) => left.date.localeCompare(right.date));
    }

    return grouped;
}
