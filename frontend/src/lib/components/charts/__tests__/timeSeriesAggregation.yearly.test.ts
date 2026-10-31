/**
 * The yearly resolution of the density cascade (Y2 FB-6).
 *
 * A history that starts in 1920 has 1 200 months: over a plot of 800 px that is 1.5 buckets a pixel, more than a line takes, and the
 * monthly level — the coarsest there was — drew it anyway. The year is the next level: a calendar year, end-of-period like the
 * others. Only a chart that hands its `yearlyCount` to the cascade can reach it; every other caller keeps the three levels it had.
 */
import {describe, expect, it} from 'vitest';

import type {LineDataPoint} from '../LineChart.svelte';
import {aggregateLineSeries, cascadeResolution, chooseInitialResolution, chooseResolution, mapDateToBucket} from '../timeSeriesAggregation';

const point = (date: string, value: number): LineDataPoint => ({date, value});

describe('mapDateToBucket, yearly', () => {
    it('is the calendar year, 1 January to 31 December', () => {
        expect(mapDateToBucket('2024-06-15', 'yearly')).toEqual({bucketStart: '2024-01-01', bucketEnd: '2024-12-31'});
        expect(mapDateToBucket('1920-01-01', 'yearly')).toEqual({bucketStart: '1920-01-01', bucketEnd: '1920-12-31'});
        expect(mapDateToBucket('2023-12-31', 'yearly')).toEqual({bucketStart: '2023-01-01', bucketEnd: '2023-12-31'});
    });
});

describe('aggregateLineSeries, yearly', () => {
    it('keeps the last point of each year, with the year as its bucket', () => {
        const rows = aggregateLineSeries([point('2022-03-01', 10), point('2022-11-30', 12), point('2023-02-01', 20), point('2023-12-29', 25), point('2024-01-02', 30)], 'yearly');
        expect(rows.map((row) => [row.date, row.value])).toEqual([
            ['2022-11-30', 12],
            ['2023-12-29', 25],
            ['2024-01-02', 30],
        ]);
        expect(rows.map((row) => (row as unknown as {bucketStart: string; bucketEnd: string; resolution: string}).bucketEnd)).toEqual(['2022-12-31', '2023-12-31', '2024-12-31']);
        expect((rows[0] as unknown as {resolution: string}).resolution).toBe('yearly');
    });
});

describe('the cascade reaches the year only when the caller counts years', () => {
    /** 100 years: 36 500 days, 5 200 weeks, 1 200 months, 100 years. */
    const HUNDRED = {dailyCount: 36_500, weeklyCount: 5_200, monthlyCount: 1_200, yearlyCount: 100};
    const WITHOUT_YEARS = {dailyCount: 36_500, weeklyCount: 5_200, monthlyCount: 1_200};

    it('climbs from monthly to yearly when the months are over 1.3 a pixel', () => {
        // 1 200 / 800 = 1.5
        expect(chooseResolution('monthly', HUNDRED, 800)).toBe('yearly');
        expect(cascadeResolution('daily', HUNDRED, 800)).toBe('yearly');
        expect(chooseInitialResolution(HUNDRED, 800)).toBe('yearly');
    });

    it('stays monthly while the months fit (1 200 / 1 200 = 1.0)', () => {
        expect(cascadeResolution('daily', HUNDRED, 1_200)).toBe('monthly');
    });

    it('never goes to the year for a caller that does not count them', () => {
        expect(chooseResolution('monthly', WITHOUT_YEARS, 800)).toBe('monthly');
        expect(cascadeResolution('daily', WITHOUT_YEARS, 800)).toBe('monthly');
    });

    it('comes back from the year to the month under 0.8 months a pixel, and stays in between', () => {
        // 1 200 / 2 000 = 0.6, under 0.8
        expect(chooseResolution('yearly', HUNDRED, 2_000)).toBe('monthly');
        // 1 200 / 1 300 = 0.92, inside the dead zone: the year stays
        expect(chooseResolution('yearly', HUNDRED, 1_300)).toBe('yearly');
    });

    it('reaches the year from daily in one cascade, and back down in one', () => {
        expect(cascadeResolution('daily', HUNDRED, 800)).toBe('yearly');
        expect(cascadeResolution('yearly', HUNDRED, 100_000)).toBe('daily');
    });
});
