/**
 * The calendar buckets of the GrowthChart ladder, pinned (developer's decision of 06/10/2026,
 * which replaces D16-ii's day counts anchored at the last day).
 *
 * `growthLadderBuckets` decides, for P&L candles and Income alike, the calendar period a day
 * falls in on each rung, the periods a series touches, and which of them are not comparable
 * (`partial`, drawn faded) or not over yet (`current`, drawn whole). GrowthChart draws what
 * `buildCalendarLadder` returns, and its rung offer weighs what `countCalendarBuckets` counts.
 *
 * The decision, as these cases read it:
 *   - `1D` a day; `1W` an ISO week, Monday to Sunday; `1M` a month from the 1st; `3M` a quarter
 *     (Jan–Mar …); `6M` a half (Jan–Jun, Jul–Dec); `1Y` a calendar year.
 *   - `3D` fixed triples counted from 1970-01-01 (day 0), `2W` fixed pairs of weeks counted from
 *     Monday 1969-12-29: no calendar unit, so a fixed origin, and their edges never move.
 *   - A bucket is one period the series touches. `partial`: a period that is over and that the
 *     series covers only in part, or one the series starts after the period's first day.
 *     `current`: the period whose end is on or after today, drawn whole because its missing days
 *     are the future. A start-cut current period is both.
 *
 * WHERE THE EXPECTED VALUES COME FROM. Literals, written from the calendar and the decision's
 * text, and cross-checked before they were written down by an independent computation (Python's
 * `datetime`, outside this repository). Nothing here derives an expected value from the module:
 * the one case that compares two of its functions (the count against the ladder's length) does so
 * because their agreement is itself the contract — the offer and the drawing must count the same
 * buckets.
 *
 * TODAY IS AN ARGUMENT. `buildCalendarLadder` takes today explicitly (GrowthChart passes
 * `todayIso()`), so no case here touches the clock.
 */
import {describe, expect, it} from 'vitest';
import {buildCalendarLadder, calendarPeriodOf, countCalendarBuckets} from './growthLadderBuckets';
import type {LadderPeriod, LadderRung} from './growthLadderBuckets';

const DAY_MS = 86_400_000;

/** Every calendar day from `first` to `last`, both included. WHY: the fixtures are daily series, as the dashboard serves them; UTC arithmetic keeps them free of time zones. */
function days(first: string, last: string): string[] {
    const out: string[] = [];
    for (let ms = Date.parse(`${first}T00:00:00Z`); ms <= Date.parse(`${last}T00:00:00Z`); ms += DAY_MS) out.push(new Date(ms).toISOString().slice(0, 10));
    return out;
}

/** A bucket written the way the decision reads: its days in the series, its period, how much of it is covered, its two flags. WHY: a case states a whole bucket, so no field can drift unnoticed. */
function bucket(startIndex: number, endIndex: number, start: string, end: string, coveredDays: number, periodDays: number, flags: {partial?: boolean; current?: boolean} = {}): LadderPeriod {
    return {startIndex, endIndex, period: {start, end}, coveredDays, periodDays, partial: flags.partial ?? false, current: flags.current ?? false};
}

const RUNGS: readonly LadderRung[] = ['1D', '3D', '1W', '2W', '1M', '3M', '6M', '1Y'];

/**
 * The dashboard's preset windows on 2026-10-06, the day of the decision, and the two-year S7
 * series. WHY: these are the windows the developer's offer table was computed on, so their counts
 * are the table's own figures.
 */
const WINDOWS = {
    '1M': days('2026-09-06', '2026-10-06'),
    '3M': days('2026-07-06', '2026-10-06'),
    '6M': days('2026-04-06', '2026-10-06'),
    '9M': days('2026-01-06', '2026-10-06'),
    YTD: days('2026-01-01', '2026-10-06'),
    '1Y': days('2025-10-06', '2026-10-06'),
    '730 days': days('2024-10-01', '2026-09-30'),
} as const;

describe('calendarPeriodOf: the period each rung puts a day in', () => {
    it.each([
        // 1D: the day itself.
        {iso: '2026-10-06', rung: '1D', start: '2026-10-06', end: '2026-10-06', why: 'a day is its own period'},
        // 1W: ISO weeks, Monday to Sunday, across a year boundary.
        {iso: '2026-01-01', rung: '1W', start: '2025-12-29', end: '2026-01-04', why: 'a Thursday 1 January sits in a week that starts the year before'},
        {iso: '2025-12-29', rung: '1W', start: '2025-12-29', end: '2026-01-04', why: 'a Monday opens its own week'},
        {iso: '2026-01-04', rung: '1W', start: '2025-12-29', end: '2026-01-04', why: 'a Sunday closes its own week'},
        {iso: '2026-01-05', rung: '1W', start: '2026-01-05', end: '2026-01-11', why: 'the next Monday opens the next week'},
        {iso: '2020-12-31', rung: '1W', start: '2020-12-28', end: '2021-01-03', why: "ISO week 53 of 2020 runs into 2021: a week is seven days, not a year's slice"},
        {iso: '1970-01-01', rung: '1W', start: '1969-12-29', end: '1970-01-04', why: 'the origin week: day 0 is a Thursday'},
        {iso: '1969-12-28', rung: '1W', start: '1969-12-22', end: '1969-12-28', why: 'before the origin the block floors down, never toward zero'},
        // 2W: pairs of weeks counted from Monday 1969-12-29.
        {iso: '1969-12-29', rung: '2W', start: '1969-12-29', end: '1970-01-11', why: 'the origin opens the first pair'},
        {iso: '1970-01-11', rung: '2W', start: '1969-12-29', end: '1970-01-11', why: 'the fourteenth day closes it'},
        {iso: '1970-01-12', rung: '2W', start: '1970-01-12', end: '1970-01-25', why: 'the fifteenth day opens the next pair'},
        {iso: '2026-01-01', rung: '2W', start: '2025-12-29', end: '2026-01-11', why: '2025-12-29 is 1461 pairs after the origin'},
        {iso: '2026-10-04', rung: '2W', start: '2026-09-21', end: '2026-10-04', why: 'a Sunday closing a pair'},
        {iso: '2026-10-05', rung: '2W', start: '2026-10-05', end: '2026-10-18', why: 'a Monday opening a pair'},
        {iso: '2026-10-06', rung: '2W', start: '2026-10-05', end: '2026-10-18', why: "the decision's day"},
        {iso: '2026-10-18', rung: '2W', start: '2026-10-05', end: '2026-10-18', why: 'the Sunday that closes it'},
        {iso: '2026-10-19', rung: '2W', start: '2026-10-19', end: '2026-11-01', why: 'one week later is the next pair, not the second half of this one'},
        // 3D: triples counted from 1970-01-01.
        {iso: '1970-01-01', rung: '3D', start: '1970-01-01', end: '1970-01-03', why: 'day 0 opens the first triple'},
        {iso: '1970-01-03', rung: '3D', start: '1970-01-01', end: '1970-01-03', why: 'day 2 closes it'},
        {iso: '1970-01-04', rung: '3D', start: '1970-01-04', end: '1970-01-06', why: 'day 3 opens the next'},
        {iso: '1969-12-31', rung: '3D', start: '1969-12-29', end: '1969-12-31', why: 'before the origin the block floors down, never toward zero'},
        {iso: '2026-01-01', rung: '3D', start: '2026-01-01', end: '2026-01-03', why: 'day 20454 is 3 × 6818'},
        {iso: '2026-10-06', rung: '3D', start: '2026-10-04', end: '2026-10-06', why: 'day 20732 is the third day of its triple'},
        {iso: '2026-10-07', rung: '3D', start: '2026-10-07', end: '2026-10-09', why: 'and the next day opens a new one'},
        // 1M: months from the 1st, leap years included.
        {iso: '2026-10-06', rung: '1M', start: '2026-10-01', end: '2026-10-31', why: 'a 31-day month'},
        {iso: '2024-02-10', rung: '1M', start: '2024-02-01', end: '2024-02-29', why: 'a leap February'},
        {iso: '2026-02-10', rung: '1M', start: '2026-02-01', end: '2026-02-28', why: 'a common February'},
        {iso: '2000-02-15', rung: '1M', start: '2000-02-01', end: '2000-02-29', why: 'divisible by 400: leap'},
        {iso: '2100-02-15', rung: '1M', start: '2100-02-01', end: '2100-02-28', why: 'divisible by 100 and not by 400: common'},
        {iso: '2025-12-31', rung: '1M', start: '2025-12-01', end: '2025-12-31', why: "December's end is not January's"},
        // 3M: quarters.
        {iso: '2026-01-01', rung: '3M', start: '2026-01-01', end: '2026-03-31', why: 'Q1 from its first day'},
        {iso: '2026-03-31', rung: '3M', start: '2026-01-01', end: '2026-03-31', why: 'Q1 to its last day'},
        {iso: '2026-04-01', rung: '3M', start: '2026-04-01', end: '2026-06-30', why: 'Q2'},
        {iso: '2026-08-31', rung: '3M', start: '2026-07-01', end: '2026-09-30', why: 'Q3'},
        {iso: '2026-12-31', rung: '3M', start: '2026-10-01', end: '2026-12-31', why: 'Q4 ends the year'},
        // 6M: halves.
        {iso: '2026-06-30', rung: '6M', start: '2026-01-01', end: '2026-06-30', why: 'the first half to its last day'},
        {iso: '2026-07-01', rung: '6M', start: '2026-07-01', end: '2026-12-31', why: 'the second half from its first'},
        {iso: '2026-12-31', rung: '6M', start: '2026-07-01', end: '2026-12-31', why: 'the second half ends the year'},
        // 1Y: calendar years.
        {iso: '2026-10-06', rung: '1Y', start: '2026-01-01', end: '2026-12-31', why: 'a common year'},
        {iso: '2024-02-29', rung: '1Y', start: '2024-01-01', end: '2024-12-31', why: 'a leap year, from its leap day'},
    ] as Array<{iso: string; rung: LadderRung; start: string; end: string; why: string}>)('$rung puts $iso in $start → $end: $why', ({iso, rung, start, end}) => {
        expect(calendarPeriodOf(iso, rung)).toEqual({start, end});
    });
});

describe('buildCalendarLadder: one bucket per period the series touches', () => {
    /** 2026-09-17 (a Thursday) to 2026-10-06, read on 2026-10-06. WHY: it starts mid-week, mid-month, mid-quarter and mid-half, and ends today. */
    const MID = days('2026-09-17', '2026-10-06');
    const MID_TODAY = '2026-10-06';

    it('1W: a past week cut at the start is partial, whole weeks are plain, the week holding today is current and not partial', () => {
        // WHY: the three kinds of bucket side by side — the start-cut week is over and not comparable, the
        // whole weeks are comparable, and the running week misses only the future.
        expect(buildCalendarLadder(MID, '1W', MID_TODAY)).toEqual([bucket(0, 3, '2026-09-14', '2026-09-20', 4, 7, {partial: true}), bucket(4, 10, '2026-09-21', '2026-09-27', 7, 7), bucket(11, 17, '2026-09-28', '2026-10-04', 7, 7), bucket(18, 19, '2026-10-05', '2026-10-11', 2, 7, {current: true})]);
    });

    it('1M: the month the series starts in mid-month is partial, the month in progress is current', () => {
        // WHY: the most common case on the dashboard — a window that opens on a day other than the 1st and ends today.
        expect(buildCalendarLadder(MID, '1M', MID_TODAY)).toEqual([bucket(0, 13, '2026-09-01', '2026-09-30', 14, 30, {partial: true}), bucket(14, 19, '2026-10-01', '2026-10-31', 6, 31, {current: true})]);
    });

    it('6M and 1Y: one period, start-cut and not over, is both partial and current (faded, and its line says partial)', () => {
        // WHY: the decision's tie-break. The days before the series are history the chart does not have, not
        // future: the bucket is not comparable even though its period is still running.
        expect(buildCalendarLadder(MID, '6M', MID_TODAY)).toEqual([bucket(0, 19, '2026-07-01', '2026-12-31', 20, 184, {partial: true, current: true})]);
        expect(buildCalendarLadder(MID, '1Y', MID_TODAY)).toEqual([bucket(0, 19, '2026-01-01', '2026-12-31', 20, 365, {partial: true, current: true})]);
    });

    /** 93 days, 2026-01-01 to 2026-04-03: three whole months and three days of April. WHY: a range that ends three days into a month, read before and after that month ends. */
    const JAN_TO_APR_3 = days('2026-01-01', '2026-04-03');
    const WHOLE_Q1 = [bucket(0, 30, '2026-01-01', '2026-01-31', 31, 31), bucket(31, 58, '2026-02-01', '2026-02-28', 28, 28), bucket(59, 89, '2026-03-01', '2026-03-31', 31, 31)];

    it('1M, a range that ended on 3 April, read on 1 May: April is over and covered 3 of 30 days, so it is partial and not current', () => {
        // WHY: a custom range in the past. Its last month was cut by the range, not by time, and the cut is not
        // the future: the bucket is not comparable. The first day after the month ends is the first day it is so.
        expect(buildCalendarLadder(JAN_TO_APR_3, '1M', '2026-05-01')).toEqual([...WHOLE_Q1, bucket(90, 92, '2026-04-01', '2026-04-30', 3, 30, {partial: true})]);
    });

    it.each([
        {today: '2026-04-03', why: 'the last day of the series'},
        {today: '2026-04-20', why: 'a day after the series stopped, inside April'},
        {today: '2026-04-30', why: "April's last day: a period ending today has not ended"},
    ])('1M, the same range read on $today ($why): April is current, drawn whole, and not partial', ({today}) => {
        // WHY: `current` is decided by today, not by the last day with data — April is not over, so its missing
        // days are not a defect of the series.
        expect(buildCalendarLadder(JAN_TO_APR_3, '1M', today)).toEqual([...WHOLE_Q1, bucket(90, 92, '2026-04-01', '2026-04-30', 3, 30, {current: true})]);
    });

    it('2W: two series that start in the same pair of weeks share its edges; the later start makes it partial, the edges do not move', () => {
        // WHY: decision (b), the fixed origin. A pair anchored on the series start would begin on 2026-09-28 for the
        // second series, and its edges would follow whatever range the user picked.
        expect(buildCalendarLadder(days('2026-09-21', '2026-10-06'), '2W', '2026-10-06')).toEqual([bucket(0, 13, '2026-09-21', '2026-10-04', 14, 14), bucket(14, 15, '2026-10-05', '2026-10-18', 2, 14, {current: true})]);
        expect(buildCalendarLadder(days('2026-09-28', '2026-10-06'), '2W', '2026-10-06')).toEqual([bucket(0, 6, '2026-09-21', '2026-10-04', 7, 14, {partial: true}), bucket(7, 8, '2026-10-05', '2026-10-18', 2, 14, {current: true})]);
    });

    it('3D: two series that start inside the same triple share its edges, whatever day they start on', () => {
        // WHY: decision (b) for the triples counted from 1970-01-01.
        expect(buildCalendarLadder(days('2026-09-29', '2026-10-06'), '3D', '2026-10-06')).toEqual([bucket(0, 1, '2026-09-28', '2026-09-30', 2, 3, {partial: true}), bucket(2, 4, '2026-10-01', '2026-10-03', 3, 3), bucket(5, 7, '2026-10-04', '2026-10-06', 3, 3, {current: true})]);
        expect(buildCalendarLadder(days('2026-09-30', '2026-10-06'), '3D', '2026-10-06')).toEqual([bucket(0, 0, '2026-09-28', '2026-09-30', 1, 3, {partial: true}), bucket(1, 3, '2026-10-01', '2026-10-03', 3, 3), bucket(4, 6, '2026-10-04', '2026-10-06', 3, 3, {current: true})]);
    });

    it('2W: as days pass, a bucket keeps its edges — the next day opens a new pair instead of shifting the old one', () => {
        // WHY: decision (b), "their edges never move as days pass". Day counts anchored at the last day moved every
        // edge by one day each morning; here yesterday's pair is still the same pair, now over and whole.
        expect(buildCalendarLadder(days('2026-09-21', '2026-10-04'), '2W', '2026-10-04')).toEqual([bucket(0, 13, '2026-09-21', '2026-10-04', 14, 14, {current: true})]);
        expect(buildCalendarLadder(days('2026-09-21', '2026-10-05'), '2W', '2026-10-05')).toEqual([bucket(0, 13, '2026-09-21', '2026-10-04', 14, 14), bucket(14, 14, '2026-10-05', '2026-10-18', 1, 14, {current: true})]);
    });

    it('1D: every day is a whole period, never partial; the day that is today is current', () => {
        // WHY: a one-day period cannot be cut, and today is the one day not over yet. The flag is the module's fact;
        // GrowthChart shows no in-progress line for it, a day having nothing in progress to report (its B5).
        expect(buildCalendarLadder(['2026-10-05', '2026-10-06'], '1D', '2026-10-06')).toEqual([bucket(0, 0, '2026-10-05', '2026-10-05', 1, 1), bucket(1, 1, '2026-10-06', '2026-10-06', 1, 1, {current: true})]);
    });

    it('an empty series makes no bucket', () => {
        // WHY: the chart mounts before its data arrives; the ladder must stay empty, not invent a period.
        expect(RUNGS.map((rung) => buildCalendarLadder([], rung, '2026-10-06'))).toEqual(RUNGS.map(() => []));
    });

    it.each(Object.entries(WINDOWS).flatMap(([name, dates]) => RUNGS.map((rung) => ({name, dates, rung}))))('$name on $rung: the buckets cover the series in order, each day inside its own period, each period length its calendar length', ({dates, rung}) => {
        // WHY: the structure every bucket list must have, checked on every preset window and rung against the
        // dates themselves: contiguous indices from the first day to the last, every day of a bucket inside its
        // period, consecutive periods disjoint, and the counts the bucket reports equal to the days it spans.
        const ladder = buildCalendarLadder(dates, rung, dates[dates.length - 1]);
        const breaks = ladder.flatMap((entry, index) => {
            const problems: string[] = [];
            const expectedStart = index === 0 ? 0 : ladder[index - 1].endIndex + 1;
            if (entry.startIndex !== expectedStart) problems.push(`#${index} starts at ${entry.startIndex}, expected ${expectedStart}`);
            const inside = dates.slice(entry.startIndex, entry.endIndex + 1).every((date) => date >= entry.period.start && date <= entry.period.end);
            if (!inside) problems.push(`#${index} holds a day outside ${entry.period.start} → ${entry.period.end}`);
            if (index > 0 && entry.period.start <= ladder[index - 1].period.end) problems.push(`#${index} overlaps the previous period`);
            if (entry.coveredDays !== entry.endIndex - entry.startIndex + 1) problems.push(`#${index} covers ${entry.coveredDays} days for ${entry.endIndex - entry.startIndex + 1} indices`);
            const length = (Date.parse(`${entry.period.end}T00:00:00Z`) - Date.parse(`${entry.period.start}T00:00:00Z`)) / DAY_MS + 1;
            if (entry.periodDays !== length) problems.push(`#${index} reports ${entry.periodDays} days for a ${length}-day period`);
            return problems;
        });
        expect({breaks, last: ladder[ladder.length - 1]?.endIndex}).toEqual({breaks: [], last: dates.length - 1});
    });
});

describe('countCalendarBuckets: what the rung offer weighs', () => {
    it.each([
        {name: '1M', counts: {'1D': 31, '3D': 11, '1W': 6, '2W': 4, '1M': 2, '3M': 2, '6M': 1, '1Y': 1}},
        {name: '3M', counts: {'1D': 93, '3D': 31, '1W': 14, '2W': 8, '1M': 4, '3M': 2, '6M': 1, '1Y': 1}},
        {name: '6M', counts: {'1D': 184, '3D': 62, '1W': 27, '2W': 14, '1M': 7, '3M': 3, '6M': 2, '1Y': 1}},
        {name: '9M', counts: {'1D': 274, '3D': 92, '1W': 40, '2W': 21, '1M': 10, '3M': 4, '6M': 2, '1Y': 1}},
        {name: 'YTD', counts: {'1D': 279, '3D': 93, '1W': 41, '2W': 21, '1M': 10, '3M': 4, '6M': 2, '1Y': 1}},
        {name: '1Y', counts: {'1D': 366, '3D': 122, '1W': 53, '2W': 27, '1M': 13, '3M': 5, '6M': 3, '1Y': 2}},
        {name: '730 days', counts: {'1D': 730, '3D': 244, '1W': 105, '2W': 53, '1M': 24, '3M': 8, '6M': 5, '1Y': 3}},
    ] as Array<{name: keyof typeof WINDOWS; counts: Record<LadderRung, number>}>)('$name window on 2026-10-06: the calendar counts of the offer table', ({name, counts}) => {
        // WHY: the developer's table (06/10/2026) counts calendar buckets — YTD makes 41 weeks (2025-12-29 to
        // 2026-10-11), 21 pairs, 10 months, 4 quarters; nine months 40, 21 and 10 — where day counts said 40, 20,
        // 10 and 4. Where the two differ, the offer must weigh what the ladder will draw.
        expect(Object.fromEntries(RUNGS.map((rung) => [rung, countCalendarBuckets(WINDOWS[name], rung)]))).toEqual(counts);
    });

    it.each(Object.keys(WINDOWS) as Array<keyof typeof WINDOWS>)('%s window: on every rung the count is the number of buckets the ladder draws', (name) => {
        // WHY: the offer decides which rungs can be drawn from this count, so a count that disagreed with the
        // drawing would offer a rung the chart then draws with more, narrower buckets than it promised.
        const dates = WINDOWS[name];
        expect(RUNGS.map((rung) => countCalendarBuckets(dates, rung))).toEqual(RUNGS.map((rung) => buildCalendarLadder(dates, rung, dates[dates.length - 1]).length));
    });

    it('an empty series counts no bucket', () => {
        // WHY: the offer runs before the history arrives.
        expect(RUNGS.map((rung) => countCalendarBuckets([], rung))).toEqual(RUNGS.map(() => 0));
    });
});
