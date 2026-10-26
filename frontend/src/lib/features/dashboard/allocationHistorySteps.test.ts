/**
 * The rows of the allocation history chart, from steps (D-P4, Y5-3): one row per date on which the allocation changes (and
 * on the ends of the range, and on the bucket ends of a coarser resolution), each with the share of every category that day.
 *
 * Parity is the contract: the weekly and monthly rows of the steps are the rows the day-by-day history gave. The expected side
 * is the day-by-day series the steps stand for, expanded here with the test kit.
 */
import {describe, expect, it} from 'vitest';
import {dailyFromSteps} from '$lib/utils/__tests__/stepSeriesTestKit';
import {aggregateLineSeries} from '$lib/components/charts/timeSeriesAggregation';
import {allocationCoverage, allocationRows, allocationWitnessDays, type AllocationStep} from './allocationHistorySteps';

const component = (name: string, value: number) => ({name, value: String(value), amount: String(value * 100), emoji: null, id: null});

/** Alpha 60 / Beta 40 until 10 January, then Alpha 50 / Beta 30 / Gamma 20 until 19 February, then Alpha 70 / Cash 30. */
const STEPS: AllocationStep[] = [
    {date: '2026-01-01', through: '2026-01-10', components: [component('Alpha', 60), component('Beta', 40)]},
    {date: '2026-01-11', through: '2026-02-19', components: [component('Alpha', 50), component('Beta', 30), component('Gamma', 20)]},
    {date: '2026-02-20', through: '2026-03-01', components: [component('Alpha', 70), component('Cash', 30)]},
];
const NAMES = ['Alpha', 'Beta', 'Gamma', 'Cash'];

describe('allocationCoverage', () => {
    it('is the first date to the last `through`', () => {
        expect(allocationCoverage(STEPS)).toEqual({start: '2026-01-01', end: '2026-03-01'});
        expect(allocationCoverage([])).toBeNull();
    });
});

describe('allocationWitnessDays', () => {
    it('is the first day of every step and the last day of the range', () => {
        expect(allocationWitnessDays(STEPS, [])).toEqual(['2026-01-01', '2026-01-11', '2026-02-20', '2026-03-01']);
    });

    it('adds the extra days it is given, once, in order, inside the range', () => {
        expect(allocationWitnessDays(STEPS, ['2026-01-04', '2026-01-11', '2027-01-01'])).toEqual(['2026-01-01', '2026-01-04', '2026-01-11', '2026-02-20', '2026-03-01']);
    });

    it('is empty for no steps', () => {
        expect(allocationWitnessDays([], [])).toEqual([]);
    });
});

describe('allocationRows', () => {
    it('gives each witness day the shares of the step holding it, and 0 for a category the step does not have', () => {
        const rows = allocationRows(STEPS, NAMES, ['2026-01-01', '2026-01-11', '2026-03-01']);
        expect(rows.map((row) => row.date)).toEqual(['2026-01-01', '2026-01-11', '2026-03-01']);
        expect(rows[0].valuesByName).toEqual({Alpha: 60, Beta: 40, Gamma: 0, Cash: 0});
        expect(rows[1].valuesByName).toEqual({Alpha: 50, Beta: 30, Gamma: 20, Cash: 0});
        expect(rows[2].valuesByName).toEqual({Alpha: 70, Beta: 0, Gamma: 0, Cash: 30});
        expect(rows.every((row) => row.bucketStart === row.date && row.bucketEnd === row.date)).toBe(true);
    });

    it('leaves out a day no step holds', () => {
        expect(allocationRows(STEPS, NAMES, ['2025-12-31', '2026-01-01']).map((row) => row.date)).toEqual(['2026-01-01']);
    });
});

describe('PARITY with the day-by-day history', () => {
    const daily = dailyFromSteps(STEPS);

    it.each(['weekly', 'monthly'] as const)('the %s buckets of the steps (with the bucket ends added) are the buckets of every day', (resolution) => {
        const ends = resolution === 'weekly' ? ['2026-01-04', '2026-01-11', '2026-01-18', '2026-01-25', '2026-02-01', '2026-02-08', '2026-02-15', '2026-02-22', '2026-03-01'] : ['2026-01-31', '2026-02-28'];
        const fromSteps = allocationRows(STEPS, NAMES, allocationWitnessDays(STEPS, ends));
        const fromDays = allocationRows(
            daily.map((day) => ({...day, through: day.date})) as AllocationStep[],
            NAMES,
            daily.map((day) => day.date),
        );
        for (const name of NAMES) {
            const stepped = aggregateLineSeries(
                fromSteps.map((row) => ({date: row.date, value: row.valuesByName[name]})),
                resolution,
            ).map((point) => [point.date, point.value]);
            const everyDay = aggregateLineSeries(
                fromDays.map((row) => ({date: row.date, value: row.valuesByName[name]})),
                resolution,
            ).map((point) => [point.date, point.value]);
            expect(stepped, `${resolution} ${name}`).toEqual(everyDay);
        }
    });
});

describe('a history that starts in the year 1', () => {
    it('has a row per step, not per day', () => {
        const typo: AllocationStep[] = [{date: '0001-01-01', through: '2025-12-31', components: [component('Alpha', 100)]}, ...STEPS];
        const days = allocationWitnessDays(typo, []);
        expect(days).toHaveLength(5);
        expect(allocationRows(typo, ['Alpha'], days)).toHaveLength(5);
    });
});
