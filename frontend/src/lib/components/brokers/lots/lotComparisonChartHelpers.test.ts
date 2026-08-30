/**
 * Unit tests for lotComparisonChartHelpers — the pure logic lifted out of
 * LotComparisonChart.svelte. Every branch is exercised from plain inputs (no
 * ECharts, no canvas), and the assertions pin exact values so a regression in
 * the arithmetic or the guard order fails loudly rather than silently.
 *
 * @vitest-environment node
 */

import {describe, it, expect} from 'vitest';
import {mapDateToBucket} from '$lib/components/charts/timeSeriesAggregation';
import {
    safeValueSource,
    parseRequiredNumber,
    pointKey,
    lotColor,
    incomeEventColor,
    formatAxisPercent,
    lotIdFromSeriesId,
    isInternalSeriesId,
    seriesValue,
    parseTimeMs,
    tooltipXValue,
    tooltipRawDate,
    tooltipTimestamp,
    findPointAtOrBefore,
    chartSeriesPointValue,
    paddedAutoYAxisRange,
    computeAutoYAxisRange,
    buildBucketInfos,
    computeBucketCounts,
    buildZoomWindowForRange,
    logicalRangeFromBuckets,
    type BucketInfo,
} from './lotComparisonChartHelpers';

describe('safeValueSource', () => {
    it('accepts the two known provenances', () => {
        expect(safeValueSource('MARKET_PRICE')).toBe('MARKET_PRICE');
        expect(safeValueSource('ESTIMATED_AT_COST')).toBe('ESTIMATED_AT_COST');
    });

    it('rejects an unknown string, and non-strings, as null', () => {
        expect(safeValueSource('SOMETHING_ELSE')).toBeNull();
        expect(safeValueSource(null)).toBeNull();
        expect(safeValueSource(undefined)).toBeNull();
        expect(safeValueSource(42)).toBeNull();
    });

    it('unwraps the OpenAPI scalar-or-array shape via safeString', () => {
        // value_source is typed `(x | null) | Array<x | null>`; safeString takes
        // the first element, so a single-element array resolves to its value.
        expect(safeValueSource(['MARKET_PRICE'])).toBe('MARKET_PRICE');
        expect(safeValueSource([null])).toBeNull();
    });
});

describe('parseRequiredNumber', () => {
    it('parses a decimal-ish value', () => {
        expect(parseRequiredNumber('12.5')).toBe(12.5);
        expect(parseRequiredNumber(7)).toBe(7);
    });

    it('defaults a missing or unparseable value to 0', () => {
        expect(parseRequiredNumber(null)).toBe(0);
        expect(parseRequiredNumber(undefined)).toBe(0);
        expect(parseRequiredNumber('not-a-number')).toBe(0);
    });
});

describe('pointKey', () => {
    it('joins lot id and date', () => {
        expect(pointKey(42, '2024-03-15')).toBe('42:2024-03-15');
    });
});

describe('lotColor', () => {
    it('spreads the hue by the golden angle and brightens in dark mode', () => {
        // 1 * 137.508 = 137.508 -> round 138
        expect(lotColor(1, false)).toBe('hsl(138 68% 44%)');
        expect(lotColor(1, true)).toBe('hsl(138 78% 68%)');
    });

    it('wraps the hue into 0..359', () => {
        // 3 * 137.508 = 412.524 ; % 360 = 52.524 -> round 53
        expect(lotColor(3, false)).toBe('hsl(53 68% 44%)');
    });
});

describe('incomeEventColor', () => {
    it('uses teal for dividends and violet for interest, per theme', () => {
        expect(incomeEventColor('DIVIDEND', false)).toBe('#0f766e');
        expect(incomeEventColor('DIVIDEND', true)).toBe('#2dd4bf');
        expect(incomeEventColor('INTEREST', false)).toBe('#6d28d9');
        expect(incomeEventColor('INTEREST', true)).toBe('#a78bfa');
    });
});

describe('formatAxisPercent', () => {
    it('uses two fraction digits for small non-integers', () => {
        expect(formatAxisPercent(5.25, 'en-US')).toBe('5.25%');
        expect(formatAxisPercent(-3.14159, 'en-US')).toBe('-3.14%');
    });

    it('uses one fraction digit for whole values and for magnitudes >= 10', () => {
        expect(formatAxisPercent(5, 'en-US')).toBe('5%');
        expect(formatAxisPercent(12.5, 'en-US')).toBe('12.5%');
        expect(formatAxisPercent(10.25, 'en-US')).toBe('10.3%');
    });

    it('normalizes negative zero to 0%', () => {
        expect(formatAxisPercent(-0, 'en-US')).toBe('0%');
        expect(formatAxisPercent(0, 'en-US')).toBe('0%');
    });
});

describe('lotIdFromSeriesId', () => {
    it('recovers an integer lot id from a prefixed string series id', () => {
        expect(lotIdFromSeriesId({seriesId: 'return-42'}, 'return-')).toBe(42);
    });

    it('accepts a numeric series id coerced to string', () => {
        expect(lotIdFromSeriesId({seriesId: 7}, '')).toBe(7);
    });

    it('returns null when the prefix is absent', () => {
        expect(lotIdFromSeriesId({seriesId: 'value-42'}, 'return-')).toBeNull();
    });

    it('returns null when the suffix is not an integer', () => {
        expect(lotIdFromSeriesId({seriesId: 'return-4.2'}, 'return-')).toBeNull();
        expect(lotIdFromSeriesId({seriesId: 'return-x'}, 'return-')).toBeNull();
    });

    it('returns null when the series id is missing or non-scalar (raw becomes empty)', () => {
        expect(lotIdFromSeriesId({}, 'return-')).toBeNull();
        expect(lotIdFromSeriesId({seriesId: {}}, 'return-')).toBeNull();
    });
});

describe('isInternalSeriesId', () => {
    const internal = ['axis-trigger-anchor', 'per-lot-hover-dots'];

    it('is true for a member and false for a non-member', () => {
        expect(isInternalSeriesId('per-lot-hover-dots', internal)).toBe(true);
        expect(isInternalSeriesId('return-1', internal)).toBe(false);
    });

    it('coerces a nullish id to an empty string before testing', () => {
        expect(isInternalSeriesId(null, internal)).toBe(false);
        expect(isInternalSeriesId(undefined, [''])).toBe(true);
    });
});

describe('seriesValue', () => {
    it('unwraps the [x, y] array form', () => {
        expect(seriesValue({value: ['2024-01-01', 12.5]})).toBe(12.5);
    });

    it('reads a bare numeric value', () => {
        expect(seriesValue({value: 7})).toBe(7);
        expect(seriesValue({value: '7'})).toBe(7);
    });

    it('treats null, empty and non-finite as absent', () => {
        expect(seriesValue({value: null})).toBeNull();
        expect(seriesValue({value: ''})).toBeNull();
        expect(seriesValue({value: 'x'})).toBeNull();
        expect(seriesValue({value: ['d', null]})).toBeNull();
    });
});

describe('parseTimeMs', () => {
    it('reads a valid Date', () => {
        expect(parseTimeMs(new Date('2024-03-15T00:00:00Z'))).toBe(Date.parse('2024-03-15T00:00:00Z'));
    });

    it('rejects an invalid Date', () => {
        expect(parseTimeMs(new Date('nope'))).toBeNull();
    });

    it('accepts a finite number and rejects a non-finite one', () => {
        expect(parseTimeMs(1710460800000)).toBe(1710460800000);
        expect(parseTimeMs(Infinity)).toBeNull();
        expect(parseTimeMs(NaN)).toBeNull();
    });

    it('rejects non-string non-number and blank strings', () => {
        expect(parseTimeMs(null)).toBeNull();
        expect(parseTimeMs(undefined)).toBeNull();
        expect(parseTimeMs({})).toBeNull();
        expect(parseTimeMs('')).toBeNull();
        expect(parseTimeMs('   ')).toBeNull();
    });

    it('reads a numeric string as ms, before trying to date-parse it', () => {
        expect(parseTimeMs('1710460800000')).toBe(1710460800000);
    });

    it('date-parses a non-numeric date string, else null', () => {
        expect(parseTimeMs('2024-03-15')).toBe(Date.parse('2024-03-15'));
        expect(parseTimeMs('definitely not a date')).toBeNull();
    });
});

describe('tooltipXValue', () => {
    it('prefers axisValue when present', () => {
        expect(tooltipXValue({axisValue: '2024-01-01', data: ['other']})).toBe('2024-01-01');
    });

    it('reads a nested data.value array', () => {
        expect(tooltipXValue({data: {value: ['2024-02-02', 3]}})).toBe('2024-02-02');
    });

    it('reads a data array', () => {
        expect(tooltipXValue({data: ['2024-03-03', 3]})).toBe('2024-03-03');
    });

    it('reads a value array', () => {
        expect(tooltipXValue({value: ['2024-04-04', 3]})).toBe('2024-04-04');
    });

    it('returns null when nothing matches', () => {
        expect(tooltipXValue({data: 5})).toBeNull();
        expect(tooltipXValue({})).toBeNull();
    });
});

describe('tooltipRawDate', () => {
    it('returns the first usable numeric or non-blank string x', () => {
        expect(tooltipRawDate([{}, {value: ['', 1]}, {axisValue: '2024-05-05'}])).toBe('2024-05-05');
        expect(tooltipRawDate([{axisValue: 1710460800000}])).toBe(1710460800000);
    });

    it('skips blank strings and returns empty when none qualify', () => {
        expect(tooltipRawDate([{axisValue: '   '}, {data: 5}])).toBe('');
        expect(tooltipRawDate([])).toBe('');
    });
});

describe('tooltipTimestamp', () => {
    it('composes tooltipRawDate with parseTimeMs', () => {
        expect(tooltipTimestamp([{axisValue: '2024-03-15'}])).toBe(Date.parse('2024-03-15'));
        expect(tooltipTimestamp([{}])).toBeNull();
    });
});

describe('findPointAtOrBefore', () => {
    const pts = [
        {date: '2024-01-01', v: 1},
        {date: '2024-01-05', v: 2},
        {date: '2024-01-10', v: 3},
    ];

    it('returns the last point at or before the target', () => {
        expect(findPointAtOrBefore(pts, Date.parse('2024-01-07'))?.v).toBe(2);
        expect(findPointAtOrBefore(pts, Date.parse('2024-01-05'))?.v).toBe(2);
    });

    it('returns null when the target precedes every point', () => {
        expect(findPointAtOrBefore(pts, Date.parse('2023-12-31'))).toBeNull();
    });

    it('skips points whose date cannot be parsed', () => {
        const withBad = [
            {date: 'bad', v: 9},
            {date: '2024-01-01', v: 1},
        ];
        expect(findPointAtOrBefore(withBad, Date.parse('2024-01-02'))?.v).toBe(1);
    });

    it('returns the last point when the target is past every point', () => {
        expect(findPointAtOrBefore(pts, Date.parse('2024-06-01'))?.v).toBe(3);
    });
});

describe('chartSeriesPointValue', () => {
    it('reads an [x, y] tuple keyed by x', () => {
        expect(chartSeriesPointValue(['2024-01-01', 5], 0)).toEqual({key: '2024-01-01', value: 5});
        expect(chartSeriesPointValue([2, 5], 0)).toEqual({key: '2', value: 5});
    });

    it('rejects a tuple whose x is not a string or number', () => {
        expect(chartSeriesPointValue([true, 5], 0)).toBeNull();
    });

    it('maps a null or non-finite y to a null value (but keeps the key)', () => {
        expect(chartSeriesPointValue(['a', null], 0)).toEqual({key: 'a', value: null});
        expect(chartSeriesPointValue(['a', '5'], 0)).toEqual({key: 'a', value: null});
    });

    it('unwraps a {value} object', () => {
        expect(chartSeriesPointValue({value: [1, 2]}, 0)).toEqual({key: '1', value: 2});
        expect(chartSeriesPointValue({value: 7}, 3)).toEqual({key: '__index_3', value: 7});
    });

    it('reads a bare finite number under a synthetic per-index key', () => {
        expect(chartSeriesPointValue(5, 2)).toEqual({key: '__index_2', value: 5});
    });

    it('returns null for a null or non-finite bare value', () => {
        expect(chartSeriesPointValue(null, 0)).toBeNull();
        expect(chartSeriesPointValue(NaN, 0)).toBeNull();
        expect(chartSeriesPointValue('abc', 0)).toBeNull();
    });
});

describe('paddedAutoYAxisRange', () => {
    it('pads a positive-span range by 5%', () => {
        expect(paddedAutoYAxisRange(10, 20)).toEqual({min: 9.5, max: 20.5});
    });

    it('pads a zero-span range by 5% of the magnitude', () => {
        expect(paddedAutoYAxisRange(5, 5)).toEqual({min: 4.75, max: 5.25});
    });

    it('never lets a strictly positive series show a negative floor', () => {
        expect(paddedAutoYAxisRange(1, 100)).toEqual({min: 0.95, max: 104.95});
    });

    it('never lets a strictly negative series show a positive ceiling', () => {
        expect(paddedAutoYAxisRange(-100, -1)).toEqual({min: -104.95, max: -0.95});
    });
});

describe('computeAutoYAxisRange', () => {
    it('returns null when there is nothing plottable', () => {
        expect(computeAutoYAxisRange([])).toBeNull();
        expect(computeAutoYAxisRange([{data: 'not-an-array'}])).toBeNull();
        expect(computeAutoYAxisRange([{data: [['a', null]]}])).toBeNull();
    });

    it('takes the padded extent of an unstacked series', () => {
        expect(
            computeAutoYAxisRange([
                {
                    data: [
                        ['a', 10],
                        ['b', 20],
                    ],
                },
            ]),
        ).toEqual({min: 9.5, max: 20.5});
    });

    it('accumulates positive stack totals at the same x', () => {
        const range = computeAutoYAxisRange([
            {data: [['a', 10]], stack: 's'},
            {data: [['a', 5]], stack: 's'},
        ]);
        expect(range).toEqual({min: 9.75, max: 15.25}); // extent 10..15 padded
    });

    it('accumulates negative stack totals separately', () => {
        const range = computeAutoYAxisRange([
            {data: [['a', -10]], stack: 's'},
            {data: [['a', -5]], stack: 's'},
        ]);
        expect(range).toEqual({min: -15.25, max: -9.75}); // extent -15..-10 padded
    });

    it('ignores a blank stack key (treated as unstacked)', () => {
        expect(computeAutoYAxisRange([{data: [['a', 10]], stack: '  '}])).toEqual({min: 9.5, max: 10.5});
    });

    it('skips zero-height contributions', () => {
        expect(
            computeAutoYAxisRange([
                {
                    data: [
                        ['a', 0],
                        ['b', 5],
                    ],
                },
            ]),
        ).toEqual({min: 4.75, max: 5.25});
    });
});

describe('buildBucketInfos', () => {
    it('maps each date to its own bucket at daily resolution', () => {
        expect(buildBucketInfos(['2024-01-01', '2024-01-02'], 'daily')).toEqual([
            {date: '2024-01-01', bucketStart: '2024-01-01', bucketEnd: '2024-01-01', resolution: 'daily'},
            {date: '2024-01-02', bucketStart: '2024-01-02', bucketEnd: '2024-01-02', resolution: 'daily'},
        ]);
    });

    it('collapses consecutive dates that share a weekly bucket', () => {
        // 2024-03-11 (Mon) and 2024-03-12 (Tue) share the week ending 2024-03-17;
        // 2024-03-18 (Mon) opens the next week.
        const buckets = buildBucketInfos(['2024-03-11', '2024-03-12', '2024-03-18'], 'weekly');
        expect(buckets.map((b) => b.bucketEnd)).toEqual(['2024-03-17', '2024-03-24']);
        expect(buckets[0]).toEqual({date: '2024-03-17', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'});
    });

    it('collapses dates that share a monthly bucket', () => {
        const buckets = buildBucketInfos(['2024-03-15', '2024-03-20', '2024-04-10'], 'monthly');
        expect(buckets.map((b) => `${b.bucketStart}..${b.bucketEnd}`)).toEqual(['2024-03-01..2024-03-31', '2024-04-01..2024-04-30']);
    });
});

describe('computeBucketCounts', () => {
    const dates = ['2024-03-11', '2024-03-12', '2024-03-18', '2024-04-10'];

    it('counts daily/weekly/monthly buckets within the window', () => {
        const counts = computeBucketCounts(dates, '2024-03-01', '2024-04-30');
        expect(counts.dailyCount).toBe(4);
        // weeks: {03-11..03-17}, {03-18..03-24}, {04-08..04-14} -> 3
        expect(counts.weeklyCount).toBe(3);
        // months: March, April -> 2
        expect(counts.monthlyCount).toBe(2);
    });

    it('excludes dates outside the window', () => {
        const counts = computeBucketCounts(dates, '2024-03-12', '2024-03-18');
        expect(counts.dailyCount).toBe(2); // 03-12 and 03-18
        expect(counts.weeklyCount).toBe(2);
        expect(counts.monthlyCount).toBe(1);
    });

    it('returns zeros when no date falls in the window', () => {
        expect(computeBucketCounts(dates, '2025-01-01', '2025-12-31')).toEqual({dailyCount: 0, weeklyCount: 0, monthlyCount: 0});
    });
});

describe('buildZoomWindowForRange', () => {
    it('returns the whole range for one bucket or fewer', () => {
        expect(buildZoomWindowForRange(['2024-01-01'], 'daily', '2024-01-01', '2024-01-01')).toEqual({start: 0, end: 100});
        expect(buildZoomWindowForRange([], 'daily', '2024-01-01', '2024-01-02')).toEqual({start: 0, end: 100});
    });

    it('frames an interior window in percentages', () => {
        const window = buildZoomWindowForRange(['2024-01-01', '2024-01-02', '2024-01-03'], 'daily', '2024-01-02', '2024-01-03');
        expect(window).toEqual({start: 50, end: 100});
    });

    it('clamps a start bucket that is past every bucket end to index 0', () => {
        const window = buildZoomWindowForRange(['2024-01-01', '2024-01-02'], 'daily', '2024-06-01', '2024-06-01');
        expect(window.start).toBe(0);
        expect(window.end).toBe(100);
    });
});

describe('logicalRangeFromBuckets', () => {
    const buckets: BucketInfo[] = [
        {date: '2024-01-01', bucketStart: '2024-01-01', bucketEnd: '2024-01-01', resolution: 'daily'},
        {date: '2024-01-02', bucketStart: '2024-01-02', bucketEnd: '2024-01-02', resolution: 'daily'},
        {date: '2024-01-03', bucketStart: '2024-01-03', bucketEnd: '2024-01-03', resolution: 'daily'},
    ];

    it('returns null for an empty bucket list', () => {
        expect(logicalRangeFromBuckets([], 0, 100)).toBeNull();
    });

    it('maps the full 0..100 window to the whole range', () => {
        expect(logicalRangeFromBuckets(buckets, 0, 100)).toEqual({startDate: '2024-01-01', endDate: '2024-01-03'});
    });

    it('floors the start index and ceils the end index for a narrow window', () => {
        // maxIndex 2: start floor(0.4*2=0.8)=0, end ceil(0.45*2=0.9)=1
        expect(logicalRangeFromBuckets(buckets, 40, 45)).toEqual({startDate: '2024-01-01', endDate: '2024-01-02'});
    });

    it('clamps indices past the end back into range', () => {
        // start floor(0.9*2=1.8)=1, end ceil(2*2=4)=4 -> clamp to 2
        expect(logicalRangeFromBuckets(buckets, 90, 200)).toEqual({startDate: '2024-01-02', endDate: '2024-01-03'});
    });

    it('agrees with mapDateToBucket-derived bucket boundaries (sanity)', () => {
        const weekly = buildBucketInfos(['2024-03-11', '2024-03-18'], 'weekly');
        const range = logicalRangeFromBuckets(weekly, 0, 100);
        expect(range).toEqual({startDate: mapDateToBucket('2024-03-11', 'weekly').bucketStart, endDate: mapDateToBucket('2024-03-18', 'weekly').bucketEnd});
    });
});
