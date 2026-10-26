/**
 * The lot charts' rows, from steps (D-P4, Y5-3): the histories of the lots analysis give one point per stretch without news
 * (`date`, `through`), and the charts read points with one date each, summed and grouped by date. So every history becomes the points of its
 * **witness days**: the first day of every step of every lot, the last day each series holds, the ends of the range and, for a coarser
 * resolution, the ends of its weeks and months. A lot has a point on a witness day only while it exists.
 *
 * Parity is the contract: the sums by date of the expanded points are those of the day-by-day history they stand for, on every witness
 * day. The expected side is that day-by-day history, expanded here with the test kit.
 */
import {describe, expect, it} from 'vitest';
import {dailyFromSteps} from '$lib/utils/__tests__/stepSeriesTestKit';
import {expandAtDays, lotWitnessDays, withBucketEnds} from './lotStepRows';

type Row = {lot_id: number; date: string; through: string; open_value: string};
const row = (lot_id: number, date: string, through: string, open_value: number): Row => ({lot_id, date, through, open_value: String(open_value)});

/** Lot 1 lives the whole range; lot 2 opens on 11 January and is sold out after 20 January; lot 3 opens on 26 January. */
const HISTORY: Row[] = [row(1, '2026-01-01', '2026-01-10', 100), row(1, '2026-01-11', '2026-01-31', 120), row(2, '2026-01-11', '2026-01-15', 50), row(2, '2026-01-16', '2026-01-20', 55), row(3, '2026-01-26', '2026-01-31', 10)];
const RANGE = {start: '2026-01-01', end: '2026-01-31'};
const lot = (point: Row) => point.lot_id;

describe('lotWitnessDays', () => {
    it('is the first day of every step, the last day each lot holds and the ends of the range', () => {
        expect(lotWitnessDays([HISTORY], lot, RANGE)).toEqual(['2026-01-01', '2026-01-11', '2026-01-16', '2026-01-20', '2026-01-26', '2026-01-31']);
    });

    it('joins several histories: the days of all of them, once, in order', () => {
        const other: Row[] = [row(1, '2026-01-05', '2026-01-31', 1)];
        expect(lotWitnessDays([HISTORY, other], lot, RANGE)).toContain('2026-01-05');
        expect(new Set(lotWitnessDays([HISTORY, other], lot, RANGE)).size).toBe(lotWitnessDays([HISTORY, other], lot, RANGE).length);
    });

    it('adds the extra days it is given, inside the range', () => {
        const days = lotWitnessDays([HISTORY], lot, RANGE, ['2026-01-04', '2027-01-01']);
        expect(days).toContain('2026-01-04');
        expect(days).not.toContain('2027-01-01');
    });

    it('takes the range from the steps when the analysis gives none', () => {
        const days = lotWitnessDays([HISTORY], lot, null);
        expect(days[0]).toBe('2026-01-01');
        expect(days[days.length - 1]).toBe('2026-01-31');
    });

    it('is empty for no steps', () => {
        expect(lotWitnessDays([[] as Row[]], lot, RANGE)).toEqual([]);
    });
});

describe('expandAtDays', () => {
    const days = lotWitnessDays([HISTORY], lot, RANGE);
    const points = expandAtDays(HISTORY, (point) => point.lot_id, days);

    it('gives a lot a point on each witness day it exists, with the values of the step holding it', () => {
        const byLot = (id: number) => points.filter((point) => point.lot_id === id).map((point) => [point.date, point.open_value]);
        expect(byLot(1)).toEqual([
            ['2026-01-01', '100'],
            ['2026-01-11', '120'],
            ['2026-01-16', '120'],
            ['2026-01-20', '120'],
            ['2026-01-26', '120'],
            ['2026-01-31', '120'],
        ]);
        expect(byLot(2)).toEqual([
            ['2026-01-11', '50'],
            ['2026-01-16', '55'],
            ['2026-01-20', '55'],
        ]);
        expect(byLot(3)).toEqual([
            ['2026-01-26', '10'],
            ['2026-01-31', '10'],
        ]);
    });

    it('is sorted by date, and by the order the lots first appear within a date', () => {
        const dates = points.map((point) => point.date);
        expect(dates).toEqual([...dates].sort());
        expect(points.filter((point) => point.date === '2026-01-16').map((point) => point.lot_id)).toEqual([1, 2]);
    });

    it('keeps every other field of the step as it is', () => {
        expect(points.every((point) => 'through' in point && typeof point.open_value === 'string')).toBe(true);
    });

    it('does not mutate the steps', () => {
        const copy = JSON.parse(JSON.stringify(HISTORY));
        expandAtDays(HISTORY, (point) => point.lot_id, days);
        expect(HISTORY).toEqual(copy);
    });

    it('is empty for no steps and for no days', () => {
        expect(expandAtDays([], (point: Row) => point.lot_id, days)).toEqual([]);
        expect(expandAtDays(HISTORY, (point) => point.lot_id, [])).toEqual([]);
    });
});

describe('PARITY with the day-by-day history', () => {
    it('the sum over the lots on each witness day is the sum of the day-by-day history that day', () => {
        const days = lotWitnessDays([HISTORY], lot, RANGE);
        const expanded = expandAtDays(HISTORY, (point) => point.lot_id, days);
        const everyDay = dailyFromSteps(HISTORY.map(({through, ...rest}) => ({...rest, date: rest.date, through}))).map((day) => day as unknown as Row);
        const sumOn = (list: ReadonlyArray<{date: string; open_value: string}>, day: string) => list.filter((point) => point.date === day).reduce((total, point) => total + Number(point.open_value), 0);
        for (const day of days) expect(sumOn(expanded, day), day).toBe(sumOn(everyDay, day));
    });
});

describe('withBucketEnds', () => {
    it('gives the ends of the weeks and of the months of the range, for a coarser resolution', () => {
        const ends = withBucketEnds({start: '2026-01-01', end: '2026-03-10'});
        expect(ends).toContain('2026-01-04');
        expect(ends).toContain('2026-01-31');
        expect(ends).toContain('2026-02-28');
        expect(ends).not.toContain('2026-03-31');
    });

    it('gives none for a range with too many buckets (a date typed in the year 1)', () => {
        expect(withBucketEnds({start: '0001-01-01', end: '2026-10-25'})).toEqual([]);
    });

    it('gives none for no range', () => {
        expect(withBucketEnds(null)).toEqual([]);
    });
});

describe('a history that starts in the year 1', () => {
    it('has a handful of points', () => {
        const typo: Row[] = [row(1, '0001-01-01', '2025-12-31', 5), row(1, '2026-01-01', '2026-03-01', 7)];
        const range = {start: '0001-01-01', end: '2026-03-01'};
        const points = expandAtDays(typo, (point) => point.lot_id, lotWitnessDays([typo], lot, range, withBucketEnds(range)));
        expect(points.length).toBeLessThan(10);
    });
});
