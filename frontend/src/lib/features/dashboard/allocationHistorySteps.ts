/**
 * The rows of AllocationHistoryChart, from the report's steps (Y5-3, D-P4 cure B).
 *
 * The chart's pipeline reads rows, one per date, and groups them into weeks and months by the date of each row; it never
 * assumed the dates are consecutive days. So a step history becomes the rows of its **witness days**: the first day of every
 * step, the last day of the range, and (for a coarser resolution) the end of every bucket. Each row holds the share of every
 * category that day, read from the step that holds it. The cost is the steps, never the days of the range.
 *
 * @module features/dashboard/allocationHistorySteps
 */

import {coveredRange, valueAt, type StepSpan} from '$lib/utils/stepSeries';

/** One share of a step: a category and its share of the net total, in percent. */
export interface AllocationStepComponent {
    name: string;
    value: string;
}

/** A stretch of the allocation history: the shares hold from `date` to `through`, both included. */
export interface AllocationStep extends StepSpan {
    components: ReadonlyArray<AllocationStepComponent>;
}

/** One row of the chart: the shares of every category on one date. */
export interface AllocationRow {
    date: string;
    bucketStart: string;
    bucketEnd: string;
    valuesByName: Record<string, number>;
}

/** The days the history covers: the first date of the first step to the last day of the last. Steps in date order. */
export function allocationCoverage(steps: ReadonlyArray<AllocationStep>): {start: string; end: string} | null {
    return coveredRange(steps);
}

/** The dates of the rows, ascending, once each, inside the coverage: the first day of every step, its two ends, and `extra`. */
export function allocationWitnessDays(steps: ReadonlyArray<AllocationStep>, extra: readonly string[]): string[] {
    const coverage = allocationCoverage(steps);
    if (!coverage) return [];
    const days = new Set<string>([coverage.start, coverage.end, ...extra]);
    for (const step of steps) days.add(step.date);
    return [...days].filter((day) => day >= coverage.start && day <= coverage.end).sort();
}

/** The row of each given day: the shares of the step holding it, 0 for a category it does not have. A day no step holds has none. */
export function allocationRows(steps: ReadonlyArray<AllocationStep>, categoryNames: readonly string[], days: readonly string[]): AllocationRow[] {
    const rows: AllocationRow[] = [];
    for (const day of days) {
        const step = valueAt(steps, day);
        if (!step) continue;
        const shares = new Map(step.components.map((component) => [component.name, Number(component.value)]));
        const valuesByName: Record<string, number> = {};
        for (const name of categoryNames) valuesByName[name] = shares.get(name) ?? 0;
        rows.push({date: day, bucketStart: day, bucketEnd: day, valuesByName});
    }
    return rows;
}
