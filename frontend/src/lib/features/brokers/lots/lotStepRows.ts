/**
 * The rows of the lot charts, from the lots analysis' steps (Y5-3, D-P4 cure B).
 *
 * Every history of the analysis (value, return, price, market price, average costs, performance) is one point per stretch without news:
 * it holds from its `date` to its `through`. The charts read points with one date each and sum and group them by date, and never assumed
 * the dates are consecutive days. So a history becomes the points of its **witness days**: the first day of every step of every series,
 * the last day each series holds, the ends of the range and, for a coarser resolution, the ends of its weeks and months. A series has a
 * point on a witness day only while it exists. The cost is the steps, never the days of the range.
 *
 * @module features/brokers/lots/lotStepRows
 */

import {valueAt, type StepSpan} from '$lib/utils/stepSeries';
import {bucketEndDays} from '$lib/features/dashboard/growthStepInputs';

/** The ends of the weeks and of the months of the range: the days a coarser resolution needs a point on. None when the range has too many (a date typed in the year 1) or is absent. */
export function withBucketEnds(range: {start: string; end: string} | null | undefined): string[] {
    if (!range) return [];
    const weekly = bucketEndDays(range, 'weekly');
    const monthly = bucketEndDays(range, 'monthly');
    return weekly === null || monthly === null ? [] : [...weekly, ...monthly];
}

/**
 * The witness days of some histories of one analysis: ascending, once each, inside the range (else the days the steps cover): the first day
 * of every step, the last day of every series (the steps of a history sharing `keyOf`), the ends of the range, and `extra`.
 */
export function lotWitnessDays<T extends StepSpan>(histories: ReadonlyArray<readonly T[]>, keyOf: (point: T) => string | number, range: {start: string; end: string} | null | undefined, extra: readonly string[] = []): string[] {
    const all = histories.flat();
    if (all.length === 0) return [];
    let first = range?.start ?? all[0].date;
    let last = range?.end ?? all[0].through;
    const days = new Set<string>(extra);
    if (range) {
        days.add(range.start);
        days.add(range.end);
    }
    // The last day each series holds: a series is the steps of a history that share a key.
    const lastOfSeries = new Map<string, string>();
    for (const [index, history] of histories.entries()) {
        for (const point of history) {
            days.add(point.date);
            const id = `${index}|${keyOf(point)}`;
            if ((lastOfSeries.get(id) ?? '') < point.through) lastOfSeries.set(id, point.through);
            if (!range) {
                if (point.date < first) first = point.date;
                if (point.through > last) last = point.through;
            }
        }
    }
    for (const through of lastOfSeries.values()) days.add(through);
    return [...days].filter((day) => day >= first && day <= last).sort();
}

/**
 * The points of each series on the given days: for every series (steps sharing `keyOf`), one point per day it exists, a copy of the step
 * holding the day with that day as its `date`. Sorted by date, and within a date by the order the series first appear in `points`.
 */
export function expandAtDays<T extends StepSpan>(points: readonly T[], keyOf: (point: T) => string | number, days: readonly string[]): T[] {
    const series = new Map<string | number, T[]>();
    for (const point of points) {
        const list = series.get(keyOf(point));
        if (list) list.push(point);
        else series.set(keyOf(point), [point]);
    }
    const rows: Array<{day: string; order: number; point: T}> = [];
    let order = 0;
    for (const steps of series.values()) {
        const sorted = [...steps].sort((left, right) => left.date.localeCompare(right.date));
        const first = sorted[0].date;
        const last = sorted[sorted.length - 1].through;
        for (const day of days) {
            if (day < first || day > last) continue;
            const step = valueAt(sorted, day);
            if (step) rows.push({day, order, point: {...step, date: day}});
        }
        order += 1;
    }
    return rows.sort((left, right) => left.day.localeCompare(right.day) || left.order - right.order).map((entry) => entry.point);
}
