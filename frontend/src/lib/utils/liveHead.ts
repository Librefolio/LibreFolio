/**
 * The head of a card's series follows the live quote (Y6-1).
 *
 * A live quote (`/assets/prices/current`) carries the day it belongs to. The series a card draws already holds that day or ends before
 * it: the last point is brought up to the quote, on the spot, without asking the series again.
 *
 * @module utils/liveHead
 */

import type {ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
import type {DerivedChartPoint} from '$lib/utils/assetPriceDerived';

/**
 * `points` with their last one brought up to a quote of `asOfDate` at `value`, or null when there is nothing to change.
 *
 * - The quote's day is the last point's: that point takes the price (and turns fresh: a quote is no backward fill).
 * - The quote's day is after the last point: a daily series gets one more day; a weekly or monthly sample has one point per bucket,
 *   so its last point moves to the quote instead, and the bucket count (the step the cache answers) does not change.
 * - The quote's day is before the last point, or the series is empty: nothing to do.
 *
 * The array given is not touched.
 */
export function withLiveHead(points: readonly DerivedChartPoint[], resolution: ChartResolution, asOfDate: string, value: number): DerivedChartPoint[] | null {
    const last = points[points.length - 1];
    if (!last || !Number.isFinite(value) || asOfDate < last.date) return null;
    const head: DerivedChartPoint = {date: asOfDate, value, staleDays: 0};
    if (asOfDate === last.date) {
        return last.value === value && last.staleDays === 0 ? null : [...points.slice(0, -1), head];
    }
    return resolution === 'daily' ? [...points, head] : [...points.slice(0, -1), head];
}
