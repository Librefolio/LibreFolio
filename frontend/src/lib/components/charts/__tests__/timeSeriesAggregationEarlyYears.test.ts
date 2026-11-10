/**
 * The bucketing of a date before the year 100.
 *
 * WHY: a date typed with a short year (`0024-03-01` for `2024-03-01`) must stay in the year 24, where the backend keeps it.
 * `Date.UTC(24, 2, 1)` reads the year as 1924, so a bucket computed that way came back a century off and no longer matched
 * the date it was made for. The expected values below come from Python's `datetime` (proleptic Gregorian), outside this
 * repository.
 */
import {describe, expect, it} from 'vitest';
import {fillCounts, mapDateToBucket} from '../timeSeriesAggregation';

describe('the trap: Date.UTC reads a short year as 19xx', () => {
    it('is why the helpers set the year on its own', () => {
        expect(new Date(Date.UTC(24, 0, 1)).getUTCFullYear()).toBe(1924);
    });
});

describe('mapDateToBucket in the year 24', () => {
    it('puts 5 March (a Tuesday) in the ISO week of Monday 4 to Sunday 10', () => {
        expect(mapDateToBucket('0024-03-05', 'weekly')).toEqual({bucketStart: '0024-03-04', bucketEnd: '0024-03-10'});
    });

    it('puts February in a month of 29 days: the year 24 is a leap year', () => {
        expect(mapDateToBucket('0024-02-10', 'monthly')).toEqual({bucketStart: '0024-02-01', bucketEnd: '0024-02-29'});
    });

    it('keeps the year 1 as it is', () => {
        expect(mapDateToBucket('0001-01-01', 'monthly')).toEqual({bucketStart: '0001-01-01', bucketEnd: '0001-01-31'});
    });
});

describe('fillCounts in the year 24', () => {
    it('counts 20 days, 4 weeks and 1 month from Friday 1 March to Wednesday 20 March', () => {
        expect(fillCounts('0024-03-01', '0024-03-20')).toEqual({days: 20, weeks: 4, months: 1});
    });
});
