/**
 * The one reader of the step series (Y5-3, D-P4 cure B).
 *
 * A series of the report, the lots and the positions is no longer one point per calendar day: it is one point per stretch
 * without news, and the point holds from its `date` to its `through`, both included. A day's value is the point whose
 * `date ≤ day ≤ through`. This module reads that shape for the charts, and is the only place that does.
 *
 * - `valueAt`, `bucketValue`, `nearestPoint`, `pointsBetween`, `coveredRange`: find points by date. A binary search over the
 *   text of the dates, which the backend writes as `YYYY-MM-DD` with four digits for the year, so the text sorts as the
 *   calendar does (`0024-03-01` before `2024-03-01`).
 * - `toStepSeries`, `toLineSeries`: the `[date, value]` pairs ECharts draws, with `step: 'end'` for the first.
 * - `expandDays`: the only function that makes days. It makes them for a window you name, and refuses (null) above a cap.
 *
 * **The rule: never build an array of all the days of a range.** A date typed in the year 1 makes that array 740 000 long.
 * Every function here costs the steps, not the days, except `expandDays`, whose cost is its cap.
 *
 * No financial quantity is computed here: a value is found, picked and handed over, never calculated. The only arithmetic
 * is on calendar days (`dateOnly`).
 *
 * @module utils/stepSeries
 */

import {addDays, daysBetween, localIso} from '$lib/utils/dateOnly';

/** The two days a point of a step series holds for. `through` ≥ `date`, and the next point's `date` is `through` + 1. */
export interface StepSpan {
    date: string;
    through: string;
}

/** A point of a line of true values, such as the history's MWRR (`mwrr_line`): no steps, the points as they arrive. */
export interface LinePoint {
    date: string;
    annualized: string | null;
    cumulative: string | null;
}

/** One pair a chart draws: the day, and the value (`null` is «not known», and breaks the line). */
export type ChartPair = [string, number | null];

/** The most days `expandDays` makes unless the caller names another cap. */
export const EXPAND_DAYS_CAP = 1000;

/** The index of the last point whose `date` is on or before `day`, or -1. */
function lastStartingOnOrBefore<T extends {date: string}>(points: readonly T[], day: string): number {
    let low = 0;
    let high = points.length - 1;
    let found = -1;
    while (low <= high) {
        const middle = (low + high) >> 1;
        if (points[middle].date <= day) {
            found = middle;
            low = middle + 1;
        } else {
            high = middle - 1;
        }
    }
    return found;
}

/** The index of the first point whose `through` is on or after `day`, or `points.length`. */
function firstEndingOnOrAfter(points: readonly StepSpan[], day: string): number {
    let low = 0;
    let high = points.length;
    while (low < high) {
        const middle = (low + high) >> 1;
        if (points[middle].through >= day) high = middle;
        else low = middle + 1;
    }
    return low;
}

/** The point holding `day` (`date ≤ day ≤ through`), or null before the series, after it and in a hole. */
export function valueAt<T extends StepSpan>(points: readonly T[], day: string): T | null {
    const index = lastStartingOnOrBefore(points, day);
    if (index < 0) return null;
    return points[index].through >= day ? points[index] : null;
}

/**
 * The point in force on the last day of a bucket the series covers: the point holding `bucketEnd`, or, when the series
 * ends or has a hole before `bucketEnd`, its last point that still touches the bucket. Null when the series does not
 * touch the bucket at all. What a weekly or monthly chart shows for the bucket, as it did with the last daily point.
 */
export function bucketValue<T extends StepSpan>(points: readonly T[], bucketStart: string, bucketEnd: string): T | null {
    const index = lastStartingOnOrBefore(points, bucketEnd);
    if (index < 0) return null;
    return points[index].through >= bucketStart ? points[index] : null;
}

/** The first day of the first point and the last day of the last: the days the series spans, holes included. */
export function coveredRange(points: readonly StepSpan[]): {start: string; end: string} | null {
    if (points.length === 0) return null;
    return {start: points[0].date, end: points[points.length - 1].through};
}

/** The indices of the points touching `from`..`to` (both included): `[first, afterLast)`. */
function touching(points: readonly StepSpan[], from: string, to: string): [number, number] {
    if (from > to || points.length === 0) return [0, 0];
    const first = firstEndingOnOrAfter(points, from);
    const afterLast = lastStartingOnOrBefore(points, to) + 1;
    return first < afterLast ? [first, afterLast] : [0, 0];
}

/**
 * The points touching the window `from`..`to`, cut to its edges: a point that starts before `from` starts on `from`, one
 * that ends after `to` ends on `to`. A point that needs no cut is given as it is (read it, never change it); a cut one is
 * a copy.
 */
export function pointsBetween<T extends StepSpan>(points: readonly T[], from: string, to: string): T[] {
    const [first, afterLast] = touching(points, from, to);
    const cut: T[] = [];
    for (let index = first; index < afterLast; index += 1) {
        const point = points[index];
        cut.push(point.date >= from && point.through <= to ? point : {...point, date: point.date < from ? from : point.date, through: point.through > to ? to : point.through});
    }
    return cut;
}

/**
 * The pairs of a step line for ECharts (`step: 'end'`): one per point, at its `date`, then one closing the line on the last
 * `through`. A point whose value is unknown (`pick` gives null) breaks the line, and so does a hole between two points.
 * One element per point, never one per day.
 */
export function toStepSeries<T extends StepSpan>(points: readonly T[], pick: (point: T) => number | null): ChartPair[] {
    const pairs: ChartPair[] = [];
    for (let index = 0; index < points.length; index += 1) {
        const point = points[index];
        pairs.push([point.date, pick(point)]);
        const next = points[index + 1];
        if (next === undefined) {
            pairs.push([point.through, pick(point)]);
        } else {
            const dayAfter = addDays(point.through, 1);
            if (next.date > dayAfter) pairs.push([dayAfter, null]);
        }
    }
    return pairs;
}

/** The pairs of a line of true values, as they arrive: each point at its own `date`, no steps. */
export function toLineSeries<T extends {date: string}>(line: readonly T[], pick: (point: T) => number | null): ChartPair[] {
    return line.map((point) => [point.date, pick(point)]);
}

/**
 * The true point nearest to `day`, with its own date (the history's MWRR shows it as «MWRR at 31/03»). Halfway between two
 * points the earlier wins. Outside the line, the first or the last point. Null for an empty line.
 */
export function nearestPoint<T extends {date: string}>(line: readonly T[], day: string): T | null {
    if (line.length === 0) return null;
    const before = lastStartingOnOrBefore(line, day);
    if (before < 0) return line[0];
    if (before === line.length - 1 || line[before].date === day) return line[before];
    const after = line[before + 1];
    return daysBetween(line[before].date, day) <= daysBetween(day, after.date) ? line[before] : after;
}

/**
 * The calendar day a time axis value stands for. ECharts reads a `YYYY-MM-DD` as local midnight and hands its pointer
 * back as milliseconds, so the day is read on the local calendar, never through `toISOString()` (a day behind east of
 * Greenwich).
 *
 * **The tooltip of a step line needs it.** On a time axis ECharts shows the data point nearest to the pointer, so the
 * right half of a step shows the next step's value while the line says another. Measured with ECharts 6.0.0:
 * `xAxis.axisPointer.snap: false` makes the `updateAxisPointer` event carry the pointed day exactly, before the tooltip
 * formatter runs, while `params[0].axisValue` stays the nearest point's. A chart sets that option, keeps
 * `dayOfAxisValue(event.axesInfo[0].value)` and has its formatter read `valueAt` on that day.
 */
export function dayOfAxisValue(axisValue: number): string {
    return localIso(new Date(axisValue));
}

/**
 * The days of the window `from`..`to` that the series covers, each with its point: the only function that makes days. It
 * makes them only for a window that stays within `maxDays` once cut to what the series covers, and gives null above that,
 * so the caller draws the steps (or a bucket) instead. The days are counted before any is made.
 */
export function expandDays<T extends StepSpan>(points: readonly T[], from: string, to: string, maxDays: number = EXPAND_DAYS_CAP): Array<{day: string; point: T}> | null {
    const [first, afterLast] = touching(points, from, to);
    let total = 0;
    for (let index = first; index < afterLast; index += 1) {
        const start = points[index].date < from ? from : points[index].date;
        const end = points[index].through > to ? to : points[index].through;
        total += daysBetween(start, end) + 1;
        if (total > maxDays) return null;
    }
    const days: Array<{day: string; point: T}> = [];
    for (let index = first; index < afterLast; index += 1) {
        const point = points[index];
        const end = point.through > to ? to : point.through;
        for (let day = point.date < from ? from : point.date; day <= end; day = addDays(day, 1)) days.push({day, point});
    }
    return days;
}
