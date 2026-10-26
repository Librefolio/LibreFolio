/**
 * Test support for the step series (`stepSeries.ts`): turns a day-by-day array into steps and back, so a fixture written
 * one point per day can feed a chart that now reads steps, and so a test can prove an expansion gives the days back.
 *
 * Tests only: production code never builds a day-by-day array (`stepSeries.ts`, `expandDays`, is the one capped exception).
 */
import {addDays} from '$lib/utils/dateOnly';
import type {StepSpan} from '../stepSeries';

/** One day of a day-by-day fixture. */
export type DayPoint = {date: string} & Record<string, unknown>;

/**
 * Merge the consecutive days whose fields are equal into one step each (`date` = the first day, `through` = the last).
 * A day that does not follow the previous one starts a new step, so a gap stays a gap.
 */
export function stepsFromDaily<T extends DayPoint>(days: readonly T[]): Array<Omit<T, 'date'> & StepSpan> {
    const steps: Array<Omit<T, 'date'> & StepSpan> = [];
    for (const day of days) {
        const {date, ...fields} = day;
        const last = steps[steps.length - 1];
        const sameFields = last !== undefined && JSON.stringify(withoutSpan(last)) === JSON.stringify(fields);
        if (last !== undefined && sameFields && addDays(last.through, 1) === date) {
            last.through = date;
        } else {
            steps.push({...fields, date, through: date} as Omit<T, 'date'> & StepSpan);
        }
    }
    return steps;
}

/** The step's fields without its two days. */
function withoutSpan(step: StepSpan & Record<string, unknown>): Record<string, unknown> {
    const {date: _date, through: _through, ...fields} = step;
    return fields;
}

/** Repeat each step for every day from its `date` to its `through`: the day-by-day series a step series stands for. */
export function dailyFromSteps<T extends StepSpan>(steps: readonly T[]): Array<Omit<T, 'through'>> {
    const days: Array<Omit<T, 'through'>> = [];
    for (const step of steps) {
        const {through, ...fields} = step;
        for (let day = step.date; day <= through; day = addDays(day, 1)) days.push({...fields, date: day} as Omit<T, 'through'>);
    }
    return days;
}
