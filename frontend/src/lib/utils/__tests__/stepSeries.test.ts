import {describe, expect, it} from 'vitest';
import {alignAt, bucketValue, coveredRange, dayOfAxisValue, EXPAND_DAYS_CAP, expandDays, indexHoldingDay, nearestPoint, pointsBetween, toLineSeries, toStepSeries, valueAt, type LinePoint, type StepSpan} from '../stepSeries';
import {dailyFromSteps, stepsFromDaily} from './stepSeriesTestKit';

type Step = StepSpan & {nav: number | null};

const step = (date: string, through: string, nav: number | null): Step => ({date, through, nav});
const nav = (point: Step): number | null => point.nav;

/** Fri 23 – Sun 25 Oct held at 100, Mon 26 at 110, then a hole, then 28–30 at 120. */
const SERIES: Step[] = [step('2026-10-23', '2026-10-25', 100), step('2026-10-26', '2026-10-26', 110), step('2026-10-28', '2026-10-30', 120)];

describe('valueAt', () => {
    it('finds the step holding the day, edges included', () => {
        expect(valueAt(SERIES, '2026-10-23')?.nav).toBe(100);
        expect(valueAt(SERIES, '2026-10-24')?.nav).toBe(100);
        expect(valueAt(SERIES, '2026-10-25')?.nav).toBe(100);
        expect(valueAt(SERIES, '2026-10-26')?.nav).toBe(110);
        expect(valueAt(SERIES, '2026-10-30')?.nav).toBe(120);
    });

    it('is null before the first step, after the last and in a hole', () => {
        expect(valueAt(SERIES, '2026-10-22')).toBeNull();
        expect(valueAt(SERIES, '2026-10-27')).toBeNull();
        expect(valueAt(SERIES, '2026-10-31')).toBeNull();
    });

    it('is null for no steps and works for one', () => {
        expect(valueAt([], '2026-10-23')).toBeNull();
        expect(valueAt([step('2026-01-01', '2026-01-01', 1)], '2026-01-01')?.nav).toBe(1);
        expect(valueAt([step('2026-01-01', '2026-01-01', 1)], '2026-01-02')).toBeNull();
    });

    it('returns the very point, not a copy', () => {
        expect(valueAt(SERIES, '2026-10-26')).toBe(SERIES[1]);
    });

    it('reads a year before 1000 by its zero-padded text', () => {
        const typo = [step('0001-01-01', '0001-01-01', 5), step('0001-01-02', '2026-10-25', 7)];
        expect(valueAt(typo, '0024-03-01')?.nav).toBe(7);
        expect(valueAt(typo, '0001-01-01')?.nav).toBe(5);
    });

    it('agrees with the day-by-day series the steps stand for', () => {
        const days = [
            {date: '2026-01-01', nav: 1},
            {date: '2026-01-02', nav: 1},
            {date: '2026-01-03', nav: 2},
            {date: '2026-01-04', nav: 2},
            {date: '2026-01-05', nav: 1},
        ];
        const steps = stepsFromDaily(days);
        expect(steps).toHaveLength(3);
        for (const day of days) expect(valueAt(steps, day.date)?.nav).toBe(day.nav);
    });
});

describe('pointsBetween', () => {
    it('keeps the steps touching the window and cuts them to its edges', () => {
        const cut = pointsBetween(SERIES, '2026-10-25', '2026-10-28');
        expect(cut).toEqual([step('2026-10-25', '2026-10-25', 100), step('2026-10-26', '2026-10-26', 110), step('2026-10-28', '2026-10-28', 120)]);
    });

    it('does not touch the points it was given', () => {
        pointsBetween(SERIES, '2026-10-25', '2026-10-28');
        expect(SERIES[0]).toEqual(step('2026-10-23', '2026-10-25', 100));
    });

    it('gives the whole series for a window that covers it, and nothing for one that misses it', () => {
        expect(pointsBetween(SERIES, '2000-01-01', '2100-01-01')).toEqual(SERIES);
        expect(pointsBetween(SERIES, '2026-10-27', '2026-10-27')).toEqual([]);
        expect(pointsBetween(SERIES, '2030-01-01', '2031-01-01')).toEqual([]);
        expect(pointsBetween(SERIES, '2026-10-29', '2026-10-23')).toEqual([]);
        expect(pointsBetween([], '2026-01-01', '2026-12-31')).toEqual([]);
    });
});

describe('coveredRange', () => {
    it('spans the first date to the last through, holes included', () => {
        expect(coveredRange(SERIES)).toEqual({start: '2026-10-23', end: '2026-10-30'});
        expect(coveredRange([])).toBeNull();
    });
});

describe('toStepSeries', () => {
    it('gives one pair per step and closes the line on the last day', () => {
        const contiguous = [step('2026-10-23', '2026-10-25', 100), step('2026-10-26', '2026-10-26', 110)];
        expect(toStepSeries(contiguous, nav)).toEqual([
            ['2026-10-23', 100],
            ['2026-10-26', 110],
            ['2026-10-26', 110],
        ]);
    });

    it('breaks the line on an unknown value instead of dropping it to zero', () => {
        const withHole = [step('2026-10-23', '2026-10-24', 100), step('2026-10-25', '2026-10-25', null), step('2026-10-26', '2026-10-26', 110)];
        expect(toStepSeries(withHole, nav).map(([, value]) => value)).toEqual([100, null, 110, 110]);
    });

    it('breaks the line where the series has a hole', () => {
        expect(toStepSeries(SERIES, nav)).toEqual([
            ['2026-10-23', 100],
            ['2026-10-26', 110],
            ['2026-10-27', null],
            ['2026-10-28', 120],
            ['2026-10-30', 120],
        ]);
    });

    it('is empty for no steps', () => {
        expect(toStepSeries([], nav)).toEqual([]);
    });

    it('makes one element per step, never one per day', () => {
        const typo = [step('0001-01-01', '0001-01-01', 5), step('0001-01-02', '2026-10-25', 7)];
        const started = performance.now();
        const pairs = toStepSeries(typo, nav);
        expect(pairs).toHaveLength(3);
        expect(performance.now() - started).toBeLessThan(200);
    });

    it('scales with the steps: 398 steps over 2 000 years give 399 pairs', () => {
        const steps: Step[] = [];
        for (let year = 0; year < 398; year += 1) {
            const label = String(year * 5 + 1).padStart(4, '0');
            steps.push(step(`${label}-01-01`, `${label}-12-31`, year));
        }
        expect(toStepSeries(steps, nav).length).toBeLessThanOrEqual(398 * 2 + 1);
    });
});

describe('toLineSeries', () => {
    const line: LinePoint[] = [
        {date: '2026-01-01', annualized: null, cumulative: null},
        {date: '2026-01-02', annualized: '0.120000', cumulative: '0.000310'},
        {date: '2026-03-31', annualized: '0.118400', cumulative: '0.030000'},
    ];

    it('gives the points as they arrive, with an unknown rate as null', () => {
        expect(toLineSeries(line, (point) => (point.annualized === null ? null : Number(point.annualized)))).toEqual([
            ['2026-01-01', null],
            ['2026-01-02', 0.12],
            ['2026-03-31', 0.1184],
        ]);
    });

    it('is empty for no points', () => {
        expect(toLineSeries([], () => 1)).toEqual([]);
    });
});

describe('nearestPoint', () => {
    const line: LinePoint[] = [
        {date: '2026-01-01', annualized: '0.1', cumulative: '0'},
        {date: '2026-01-11', annualized: '0.2', cumulative: '0'},
        {date: '2026-01-31', annualized: '0.3', cumulative: '0'},
    ];

    it('gives the true point nearest to the day, with its own date', () => {
        expect(nearestPoint(line, '2026-01-03')?.date).toBe('2026-01-01');
        expect(nearestPoint(line, '2026-01-09')?.date).toBe('2026-01-11');
        expect(nearestPoint(line, '2026-01-11')?.date).toBe('2026-01-11');
        expect(nearestPoint(line, '2026-01-25')?.date).toBe('2026-01-31');
    });

    it('takes the earlier point when the day is in the middle', () => {
        expect(nearestPoint(line, '2026-01-06')?.date).toBe('2026-01-01');
    });

    it('gives the first or the last point outside the line', () => {
        expect(nearestPoint(line, '2025-06-01')?.date).toBe('2026-01-01');
        expect(nearestPoint(line, '2027-06-01')?.date).toBe('2026-01-31');
    });

    it('is null for no points', () => {
        expect(nearestPoint([], '2026-01-01')).toBeNull();
    });
});

describe('bucketValue', () => {
    it('reads the step in force on the last day of the bucket', () => {
        expect(bucketValue(SERIES, '2026-10-19', '2026-10-25')?.nav).toBe(100);
        expect(bucketValue(SERIES, '2026-10-26', '2026-11-01')?.nav).toBe(120);
    });

    it('reads the last step of a series that ends inside the bucket', () => {
        expect(bucketValue(SERIES, '2026-10-29', '2026-12-31')?.nav).toBe(120);
    });

    it('reads the step before a hole when the bucket ends in it', () => {
        expect(bucketValue(SERIES, '2026-10-26', '2026-10-27')?.nav).toBe(110);
    });

    it('is null when the series does not touch the bucket', () => {
        expect(bucketValue(SERIES, '2026-10-01', '2026-10-22')).toBeNull();
        expect(bucketValue(SERIES, '2026-11-01', '2026-11-30')).toBeNull();
        expect(bucketValue(SERIES, '2026-10-27', '2026-10-27')).toBeNull();
        expect(bucketValue([], '2026-10-01', '2026-10-31')).toBeNull();
    });
});

describe('expandDays', () => {
    it('repeats each step for its days inside the window', () => {
        const days = expandDays(SERIES, '2026-10-25', '2026-10-28');
        expect(days?.map(({day, point}) => [day, point.nav])).toEqual([
            ['2026-10-25', 100],
            ['2026-10-26', 110],
            ['2026-10-28', 120],
        ]);
    });

    it('agrees with the day-by-day series the steps stand for', () => {
        const days = dailyFromSteps(SERIES);
        const expanded = expandDays(SERIES, '2026-10-23', '2026-10-30');
        expect(expanded?.map(({day, point}) => ({date: day, nav: point.nav}))).toEqual(days.map(({date, nav: value}) => ({date, nav: value})));
    });

    it('takes the cap into account only for the days it would build', () => {
        const long = [step('0001-01-01', '0001-01-01', 5), step('0001-01-02', '0001-01-04', 7)];
        expect(expandDays(long, '0001-01-01', '2026-10-25')).toHaveLength(4);
    });

    it('is null when the window would need more days than the cap', () => {
        const wide = [step('2000-01-01', '2026-10-25', 1)];
        expect(expandDays(wide, '2000-01-01', '2026-10-25')).toBeNull();
        expect(expandDays(wide, '2026-01-01', '2026-10-25')).toHaveLength(298);
    });

    it('has a cap of exactly the days it names', () => {
        const one = [step('2000-01-01', '2100-01-01', 1)];
        expect(expandDays(one, '2000-01-01', '2000-01-01', 1)).toHaveLength(1);
        expect(expandDays(one, '2000-01-01', '2000-01-02', 1)).toBeNull();
        expect(expandDays(one, '2000-01-01', '2002-09-26', EXPAND_DAYS_CAP)).toHaveLength(EXPAND_DAYS_CAP);
        expect(expandDays(one, '2000-01-01', '2002-09-27', EXPAND_DAYS_CAP)).toBeNull();
    });

    it('is empty for a window outside the series', () => {
        expect(expandDays(SERIES, '2020-01-01', '2020-01-31')).toEqual([]);
        expect(expandDays([], '2020-01-01', '2020-01-31')).toEqual([]);
    });

    it('counts a 740 000-day step as one before it refuses, without building a day', () => {
        const typo = [step('0001-01-01', '2026-10-25', 5)];
        const started = performance.now();
        expect(expandDays(typo, '0001-01-01', '2026-10-25')).toBeNull();
        expect(performance.now() - started).toBeLessThan(200);
    });
});

describe('alignAt', () => {
    it('gives the value of each given day, null where the series does not cover it', () => {
        const days = ['2026-10-22', '2026-10-23', '2026-10-25', '2026-10-26', '2026-10-27', '2026-10-28', '2026-10-31'];
        expect(alignAt(SERIES, days, nav)).toEqual([null, 100, 100, 110, null, 120, null]);
    });

    it('agrees with valueAt on every day', () => {
        const days = dailyFromSteps(SERIES).map(({date}) => date);
        const every = ['2026-10-20', ...days, '2026-10-27', '2026-11-02'];
        expect(alignAt(SERIES, every, nav)).toEqual(every.map((day) => valueAt(SERIES, day)?.nav ?? null));
    });

    it('keeps an unknown value null and does not mistake it for a hole', () => {
        const unknown = [step('2026-01-01', '2026-01-03', null), step('2026-01-04', '2026-01-04', 7)];
        expect(alignAt(unknown, ['2026-01-02', '2026-01-04'], nav)).toEqual([null, 7]);
    });

    it('is empty for no days and all null for no steps', () => {
        expect(alignAt(SERIES, [], nav)).toEqual([]);
        expect(alignAt([], ['2026-01-01', '2026-01-02'], nav)).toEqual([null, null]);
    });

    it('costs the steps and the days given, not the days of the range', () => {
        const typo = [step('0001-01-01', '2026-10-25', 5)];
        const started = performance.now();
        expect(alignAt(typo, ['0001-01-01', '1500-06-01', '2026-10-25'], nav)).toEqual([5, 5, 5]);
        expect(performance.now() - started).toBeLessThan(200);
    });
});

describe('indexHoldingDay', () => {
    const rows = [{date: '2026-01-01'}, {date: '2026-01-11'}, {date: '2026-01-21'}];

    it('is the last date on or before the day', () => {
        expect(indexHoldingDay(rows, '2026-01-01')).toBe(0);
        expect(indexHoldingDay(rows, '2026-01-10')).toBe(0);
        expect(indexHoldingDay(rows, '2026-01-11')).toBe(1);
        expect(indexHoldingDay(rows, '2026-01-19')).toBe(1);
        expect(indexHoldingDay(rows, '2026-01-21')).toBe(2);
        expect(indexHoldingDay(rows, '2030-01-01')).toBe(2);
    });

    it('is the first row before the first date, and 0 for no rows', () => {
        expect(indexHoldingDay(rows, '2025-12-30')).toBe(0);
        expect(indexHoldingDay([], '2026-01-01')).toBe(0);
    });
});

describe('dayOfAxisValue', () => {
    it('reads the calendar day of a time axis value on the local calendar, as the axis draws it', () => {
        expect(dayOfAxisValue(new Date(2026, 0, 9).getTime())).toBe('2026-01-09');
        expect(dayOfAxisValue(new Date(2026, 0, 9, 23, 59).getTime())).toBe('2026-01-09');
        expect(dayOfAxisValue(new Date(2026, 11, 31).getTime())).toBe('2026-12-31');
    });
});

describe('the test kit', () => {
    it('gives the days back after a round trip', () => {
        const days = [
            {date: '2026-02-27', nav: 1},
            {date: '2026-02-28', nav: 1},
            {date: '2026-03-01', nav: 1},
            {date: '2026-03-02', nav: 2},
            {date: '2026-03-04', nav: 2},
        ];
        const steps = stepsFromDaily(days);
        expect(steps).toEqual([
            {date: '2026-02-27', through: '2026-03-01', nav: 1},
            {date: '2026-03-02', through: '2026-03-02', nav: 2},
            {date: '2026-03-04', through: '2026-03-04', nav: 2},
        ]);
        expect(dailyFromSteps(steps)).toEqual(days);
    });
});
