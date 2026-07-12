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
    key: string;
    points: LineDataPoint[];
    startIndex: number;
}

const HIGH_DENSITY_THRESHOLD = 1.3;
const LOW_DENSITY_THRESHOLD = 0.8;

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
function withBucketMeta(point: LineDataPoint, meta: BucketMeta): BucketedLineDataPoint {
    return {
        ...point,
        ...meta,
        date: meta.bucketEnd,
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
            bucketEnd: lastPoint.date,
            resolution,
            sourcePointCount: group.points.length,
        });
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
                bucketEnd: lastPoint.date,
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

/** Downsample rendered overlay signal to chart bucket resolution. */
export function downsampleRenderedSignal(signal: RenderedSignal, resolution: ChartResolution, bucketedDates: string[]): RenderedSignal {
    if (resolution === 'daily') return signal;

    const allowedDates = new Set(bucketedDates);

    const isBandSignal = signal.seriesType === 'band' && signal.bandData != null && Array.isArray(signal.bandData.upper) && Array.isArray(signal.bandData.lower) && signal.bandData.upper.length === signal.data.length && signal.bandData.lower.length === signal.data.length;

    if (isBandSignal) {
        const bandData = signal.bandData!;
        const aggregated = aggregateEnvelope(bandData.upper, signal.data, bandData.lower, resolution);
        const filteredUpper: number[] = [];
        const filteredLower: number[] = [];
        const filteredMiddle: LineDataPoint[] = [];

        for (let i = 0; i < aggregated.middle.length; i++) {
            const point = aggregated.middle[i];
            if (!allowedDates.has(point.date)) continue;

            filteredMiddle.push(point);
            filteredUpper.push(aggregated.upper[i]);
            filteredLower.push(aggregated.lower[i]);
        }

        return {
            ...signal,
            data: filteredMiddle,
            bandData: {
                middle: filteredMiddle.map((point) => point.value),
                upper: filteredUpper,
                lower: filteredLower,
            },
        };
    }

    const filteredData = aggregateLineSeries(signal.data, resolution).filter((point) => allowedDates.has(point.date));

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

/** Choose chart resolution using shared hysteresis thresholds. */
export function chooseResolution(current: ChartResolution, counts: {dailyCount: number; weeklyCount: number; monthlyCount: number}, plotWidthPx: number): ChartResolution {
    if (current === 'daily') {
        const densityDaily = computeDensity(counts.dailyCount, plotWidthPx);
        return densityDaily > HIGH_DENSITY_THRESHOLD ? 'weekly' : 'daily';
    }

    if (current === 'weekly') {
        const densityDaily = computeDensity(counts.dailyCount, plotWidthPx);
        const densityWeekly = computeDensity(counts.weeklyCount, plotWidthPx);

        if (densityDaily < LOW_DENSITY_THRESHOLD) return 'daily';
        if (densityWeekly > HIGH_DENSITY_THRESHOLD) return 'monthly';
        return 'weekly';
    }

    const densityWeekly = computeDensity(counts.weeklyCount, plotWidthPx);
    return densityWeekly < LOW_DENSITY_THRESHOLD ? 'weekly' : 'monthly';
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
export function cascadeResolution(current: ChartResolution, counts: {dailyCount: number; weeklyCount: number; monthlyCount: number}, plotWidthPx: number): ChartResolution {
    let resolution = current;
    // At most 2 hops (daily->weekly->monthly, or the reverse) can ever be needed; loop defensively.
    for (let i = 0; i < 3; i++) {
        const next = chooseResolution(resolution, counts, plotWidthPx);
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
export function chooseInitialResolution(counts: {dailyCount: number; weeklyCount: number; monthlyCount: number}, plotWidthPx: number): ChartResolution {
    return cascadeResolution('daily', counts, plotWidthPx);
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
