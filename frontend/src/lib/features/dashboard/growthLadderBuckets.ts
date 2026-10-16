/**
 * The calendar buckets of the GrowthChart ladder — P&L candles and Income alike.
 *
 * A rung names a calendar period, not a number of days (developer's decision of 06/10/2026,
 * which replaces D16-ii): `1W` is a week from Monday to Sunday, `1M` a month from the 1st,
 * `3M`, `6M` and `1Y` a quarter, a half and a year. `3D` and `2W` have no calendar unit, so
 * they are fixed blocks counted from a fixed origin — runs of three days from 1970-01-01,
 * pairs of weeks from Monday 1969-12-29 — and their edges never move as days go by.
 *
 * A series cuts the periods at its two ends. The period that has not ended yet is drawn whole:
 * its future is not written, so a short current month is not a weak one (`current`). A period
 * that is over and that the series covers only in part is not comparable with the others, so
 * it is marked (`partial`) and drawn faded. A period the series STARTS inside is partial even
 * when it is still running: what it lacks there is past days, not future ones.
 *
 * Pure: dates are ISO calendar days, and every computation runs on whole day numbers, so no
 * timezone ever moves a boundary.
 */

export type LadderRung = '1D' | '3D' | '1W' | '2W' | '1M' | '3M' | '6M' | '1Y';

/** A calendar period, both ends included. */
export interface CalendarPeriod {
    start: string;
    end: string;
}

/** One bucket of a series on a rung. */
export interface LadderPeriod {
    /** The series' indices the bucket covers, both included. */
    startIndex: number;
    endIndex: number;
    period: CalendarPeriod;
    /** Days of the period the series covers, and the period's own length. */
    coveredDays: number;
    periodDays: number;
    /** A period that is over and that the series covers only in part: not comparable, drawn faded. */
    partial: boolean;
    /** The period has not ended yet: drawn whole, because its missing days are the future. */
    current: boolean;
}

const DAY_MS = 86_400_000;
/** 1970-01-01, where the `3D` runs start. */
const TRIPLE_ORIGIN = 0;
/** Monday 1969-12-29, where the weeks of `1W` and the pairs of `2W` start. */
const MONDAY_ORIGIN = -3;
const MONTHS_PER_RUNG: Partial<Record<LadderRung, number>> = {'1M': 1, '3M': 3, '6M': 6, '1Y': 12};

/** Whole days since 1970-01-01 of an ISO date. */
function dayNumber(iso: string): number {
    const [year, month, day] = iso.split('-').map(Number);
    return Date.UTC(year, month - 1, day) / DAY_MS;
}

function isoOfDay(day: number): string {
    return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

/** The block of `span` days, counted from `origin`, that holds `day`. */
function block(day: number, origin: number, span: number): CalendarPeriod {
    const start = origin + Math.floor((day - origin) / span) * span;
    return {start: isoOfDay(start), end: isoOfDay(start + span - 1)};
}

/** The calendar period that `rung` puts the day `iso` in. */
export function calendarPeriodOf(iso: string, rung: LadderRung): CalendarPeriod {
    if (rung === '1D') return {start: iso, end: iso};
    const day = dayNumber(iso);
    if (rung === '3D') return block(day, TRIPLE_ORIGIN, 3);
    if (rung === '1W') return block(day, MONDAY_ORIGIN, 7);
    if (rung === '2W') return block(day, MONDAY_ORIGIN, 14);

    const months = MONTHS_PER_RUNG[rung] ?? 1;
    const [year, month] = iso.split('-').map(Number);
    const first = Math.floor((month - 1) / months) * months;
    return {start: isoOfDay(Date.UTC(year, first, 1) / DAY_MS), end: isoOfDay(Date.UTC(year, first + months, 1) / DAY_MS - 1)};
}

/**
 * The buckets of a series of consecutive calendar days, oldest first: one per period the series
 * touches. `today` decides which period has not ended yet.
 */
export function buildCalendarLadder(dates: readonly string[], rung: LadderRung, today: string): LadderPeriod[] {
    const out: LadderPeriod[] = [];
    for (let index = 0; index < dates.length; index++) {
        const last = out[out.length - 1];
        if (last && dates[index] <= last.period.end) {
            last.endIndex = index;
            continue;
        }
        const period = calendarPeriodOf(dates[index], rung);
        out.push({startIndex: index, endIndex: index, period, coveredDays: 0, periodDays: dayNumber(period.end) - dayNumber(period.start) + 1, partial: false, current: false});
    }
    for (const bucket of out) {
        bucket.coveredDays = bucket.endIndex - bucket.startIndex + 1;
        bucket.current = bucket.period.end >= today;
        const startCut = dates[bucket.startIndex] > bucket.period.start;
        const endCut = dates[bucket.endIndex] < bucket.period.end && !bucket.current;
        bucket.partial = startCut || endCut;
    }
    return out;
}

/** How many buckets the series makes on `rung`: what the ladder's offer weighs against the plot's width. */
export function countCalendarBuckets(dates: readonly string[], rung: LadderRung): number {
    let count = 0;
    let periodEnd = '';
    for (const date of dates) {
        if (date <= periodEnd) continue;
        periodEnd = calendarPeriodOf(date, rung).end;
        count++;
    }
    return count;
}
