/**
 * Unit tests for lotComparisonChartHelpers — the pure logic lifted out of
 * LotComparisonChart.svelte. Every branch is exercised from plain inputs (no
 * ECharts, no canvas), and the assertions pin exact values so a regression in
 * the arithmetic or the guard order fails loudly rather than silently.
 *
 * The two money axes, formatAxisCurrency and formatAxisAmount, read the global
 * privacy flag, so their blocks reset it on both sides of each test: the store
 * is module level, so a flag left on by one test would still be on in the
 * next, and would mask its clear-text controls.
 *
 * The value-series block (parseValueSeriesPoint, pnlWithIncome,
 * comprehensiveValue, aggregateValuePoints, aggregateReturnPoints) pins the B3b
 * contract: a lot's cumulative income can be unknown (`null`: an income pool with
 * no FX rate). It stays unknown through every sum and ratio it enters and is never
 * read as 0. On fully known inputs the aggregates must equal what the component
 * computes before B3b. The expected numbers were checked against a verbatim
 * transcription of the component's `aggregatedValuePoints` and
 * `aggregateReturnPoints`. Ratios are chosen to be exact in binary, so `toEqual`
 * never depends on summation order.
 *
 * The last block (plan 52, C3) pins tooltipBucketInfo, the bucket the lots
 * tooltip header names, alone and through bucketSpanUpTo, and reads
 * LotComparisonChart.svelte's source to pin the header's glue.
 *
 * @vitest-environment node
 */

import {readFileSync} from 'node:fs';
import {afterEach, beforeEach, describe, it, expect} from 'vitest';
import {mapDateToBucket} from '$lib/components/charts/timeSeriesAggregation';
import {bucketSpanUpTo} from '$lib/components/charts/priceChartHelpers';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {formatAxisNumber} from './lotChartShared';
import {
    safeValueSource,
    parseRequiredNumber,
    pointKey,
    lotColor,
    incomeEventColor,
    formatAxisPercent,
    formatAxisCurrency,
    formatAxisAmount,
    lotIdFromSeriesId,
    isInternalSeriesId,
    seriesValue,
    parseTimeMs,
    tooltipXValue,
    tooltipRawDate,
    tooltipBucketInfo,
    tooltipTimestamp,
    findPointAtOrBefore,
    chartSeriesPointValue,
    paddedAutoYAxisRange,
    computeAutoYAxisRange,
    buildBucketInfos,
    computeBucketCounts,
    buildZoomWindowForRange,
    logicalRangeFromBuckets,
    parseValueSeriesPoint,
    pnlWithIncome,
    comprehensiveValue,
    aggregateValuePoints,
    aggregateReturnPoints,
    type AggregateReturnPoint,
    type AggregatedValuePoint,
    type BucketInfo,
    type LotValueSeriesPoint,
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
    it('uses gold for dividends and violet for interest, per theme', () => {
        // WHY: the developer's decision «Dividendo oro, anche nel pannello lotti» — the
        // dividend is gold here as in the dashboard's Income bars, the same pair
        // (GrowthChart's COLORS.dividend). Since D-T28 (C2) the pair is the role --lf-cat-crypto,
        // which tokens.css keeps at 3:1 on the card (WCAG 1.4.11); interest is --lf-cat-stock.
        expect(incomeEventColor('DIVIDEND', false)).toBe('#b87916');
        expect(incomeEventColor('DIVIDEND', true)).toBe('#e8bd69');
        expect(incomeEventColor('INTEREST', false)).toBe('#7041c6');
        expect(incomeEventColor('INTEREST', true)).toBe('#b69af0');
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

describe('formatAxisCurrency', () => {
    // The absolute-return axis: money with its currency marker, so the §1.8 gate sees its Intl exit — unlike the value-mode axis (formatAxisAmount), which carries none.
    beforeEach(() => setPrivacyEnabled(false));
    afterEach(() => setPrivacyEnabled(false));

    it('renders compact money with the narrow symbol while privacy is off', () => {
        // Measured with node (ICU 78.3) against Intl with the same options.
        expect(formatAxisCurrency(1234, 'USD', 'en-US')).toBe('$1.2K');
        expect(formatAxisCurrency(-1234, 'USD', 'en-US')).toBe('-$1.2K');
    });

    it('masks the number and keeps the symbol and the sign under privacy', () => {
        // Control: the same tick in the clear, so the lines below are a substitution.
        expect(formatAxisCurrency(1234, 'USD', 'en-US')).toBe('$1.2K');

        setPrivacyEnabled(true);
        // The compact suffix goes inside the placeholder: `$•••K` would still say "thousands".
        expect(formatAxisCurrency(1234, 'USD', 'en-US')).toBe('$•••');
        expect(formatAxisCurrency(-1234, 'USD', 'en-US')).toBe('-$•••');
    });

    it('falls back to the axis number and the code when Intl rejects the currency', () => {
        // Precondition, verified rather than assumed: a four-letter code is not a well-formed
        // currency, so Intl throws and the catch exit is the one under test.
        expect(() => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'EURO'})).toThrow(RangeError);

        expect(formatAxisCurrency(1234, 'EURO', 'en-US')).toBe(`${formatAxisNumber(1234, 'en-US')} EURO`);
        expect(formatAxisCurrency(-1234, 'EURO', 'en-US')).toBe(`${formatAxisNumber(-1234, 'en-US')} EURO`);
    });

    it('masks the fallback exit too, keeping the code and the sign', () => {
        setPrivacyEnabled(true);

        expect(formatAxisCurrency(1234, 'EURO', 'en-US')).toBe('••• EURO');
        expect(formatAxisCurrency(-1234, 'EURO', 'en-US')).toBe('-••• EURO');
    });

    it('keeps the U+2212 minus sv-SE writes on the fallback exit, in both states', () => {
        // Precondition, measured: sv-SE writes U+2212 MINUS SIGN, so the equality below can tell it from an ASCII hyphen.
        expect(formatAxisNumber(-1234, 'sv-SE').startsWith('\u2212')).toBe(true);

        // The same four-letter code as above, so the same catch exit. The ASCII hyphen this exit used to
        // rebuild the sign with broke this equality; pinned so it cannot come back.
        expect(formatAxisCurrency(-1234, 'EURO', 'sv-SE')).toBe(`${formatAxisNumber(-1234, 'sv-SE')} EURO`);

        setPrivacyEnabled(true);
        expect(formatAxisCurrency(-1234, 'EURO', 'sv-SE')).toBe('\u2212••• EURO');
    });

    it('renders -0 without a sign, on both exits and in both states', () => {
        // Intl exit. These lines depend on this function's normalizeZero: Intl alone prints -0 as `-$0`,
        // and its parts would carry the minus into the masked form as `-$•••`.
        expect(formatAxisCurrency(-0, 'USD', 'en-US')).toBe('$0');
        setPrivacyEnabled(true);
        expect(formatAxisCurrency(-0, 'USD', 'en-US')).toBe('$•••');
        setPrivacyEnabled(false);

        // Fallback exit. These lines do not: formatAxisNumber collapses -0 by itself, so they would pass
        // without this function's normalizeZero — they pin the output, not the layer that removes the sign.
        expect(formatAxisCurrency(-0, 'EURO', 'en-US')).toBe(`${formatAxisNumber(0, 'en-US')} EURO`);
        setPrivacyEnabled(true);
        expect(formatAxisCurrency(-0, 'EURO', 'en-US')).toBe('••• EURO');
    });
});

describe('formatAxisAmount', () => {
    // The value-mode axis is money with no currency marker on the tick, which is why neither the classification rule nor the §1.8 gate could see it.
    beforeEach(() => setPrivacyEnabled(false));
    afterEach(() => setPrivacyEnabled(false));

    it('renders the compact axis number while privacy is off', () => {
        expect(formatAxisAmount(1234, 'en-US')).toBe(formatAxisNumber(1234, 'en-US'));
        expect(formatAxisAmount(-1234, 'en-US')).toBe(formatAxisNumber(-1234, 'en-US'));
    });

    it('masks the number and keeps the sign under privacy', () => {
        // Control: the same tick in the clear, so the lines below are a substitution.
        expect(formatAxisAmount(1234, 'en-US')).toBe(formatAxisNumber(1234, 'en-US'));

        setPrivacyEnabled(true);
        expect(formatAxisAmount(1234, 'en-US')).toBe('•••');
        expect(formatAxisAmount(-1234, 'en-US')).toBe('-•••');
        // Zero is a value like any other: masked, with no sign to keep.
        expect(formatAxisAmount(0, 'en-US')).toBe('•••');
    });

    it('keeps the U+2212 minus sv-SE writes, in both states', () => {
        // Precondition, measured: sv-SE writes U+2212 MINUS SIGN, so the equality below can tell it from an ASCII hyphen.
        expect(formatAxisNumber(-1234, 'sv-SE').startsWith('\u2212')).toBe(true);

        // This is the regression the ASCII hyphen introduced — a tick rebuilt as `-` + the absolute value,
        // where the shared formatter writes U+2212 — pinned so it cannot come back.
        expect(formatAxisAmount(-1234, 'sv-SE')).toBe(formatAxisNumber(-1234, 'sv-SE'));

        setPrivacyEnabled(true);
        expect(formatAxisAmount(-1234, 'sv-SE')).toBe('\u2212•••');
    });

    it('renders -0 without a sign, in both states', () => {
        // This does not depend on formatAxisAmount's own normalizeZero: formatAxisNumber collapses -0 by
        // itself, so the check pins the output, not the layer that removes the sign.
        expect(formatAxisAmount(-0, 'en-US')).toBe(formatAxisNumber(0, 'en-US'));

        setPrivacyEnabled(true);
        expect(formatAxisAmount(-0, 'en-US')).toBe('•••');
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

// ---------------------------------------------------------------------------
// Value series: parsing & aggregation (B3b, a lot's income can be unknown)
// ---------------------------------------------------------------------------

/**
 * A lot's value series, frozen deep. A helper that mutated its input would throw
 * here instead of silently corrupting the next test's fixture. In the component,
 * the same per-lot arrays also feed the tooltips and the per-lot lines.
 */
function lotSeries(points: LotValueSeriesPoint[]): readonly LotValueSeriesPoint[] {
    return Object.freeze(points.map((point) => Object.freeze({...point})));
}

function seriesByLot(byLotId: Record<number, readonly LotValueSeriesPoint[]>): ReadonlyMap<number, readonly LotValueSeriesPoint[]> {
    return new Map(Object.entries(byLotId).map(([lotId, points]): [number, readonly LotValueSeriesPoint[]] => [Number(lotId), points]));
}

// In every fixture point, pnl = openValue + proceeds − originalCost.

/** Lot 1: cost 100, partly sold on 2024-01-04, income always known. */
const LOT_1 = lotSeries([
    {date: '2024-01-02', openValue: 100, proceeds: 0, originalCost: 100, pnl: 0, income: 0},
    {date: '2024-01-03', openValue: 120, proceeds: 0, originalCost: 100, pnl: 20, income: 5},
    {date: '2024-01-04', openValue: 75, proceeds: 70, originalCost: 100, pnl: 45, income: 5},
]);

/** Lot 2: cost 300, income always known. */
const LOT_2_KNOWN = lotSeries([
    {date: '2024-01-02', openValue: 320, proceeds: 0, originalCost: 300, pnl: 20, income: 5},
    {date: '2024-01-03', openValue: 280, proceeds: 0, originalCost: 300, pnl: -20, income: 45},
    {date: '2024-01-04', openValue: 310, proceeds: 0, originalCost: 300, pnl: 10, income: 90},
]);

/** The same lot 2 when an income pool with no FX rate lands on 2024-01-03: its income is unknown from that date on. */
const LOT_2_UNKNOWN_FROM_2ND = lotSeries([
    {date: '2024-01-02', openValue: 320, proceeds: 0, originalCost: 300, pnl: 20, income: 5},
    {date: '2024-01-03', openValue: 280, proceeds: 0, originalCost: 300, pnl: -20, income: null},
    {date: '2024-01-04', openValue: 310, proceeds: 0, originalCost: 300, pnl: 10, income: null},
]);

/** Lot 3: cost 100, opened a day before lot 1 and with no point on 2024-01-02, so each date has its own set of lots. */
const LOT_3 = lotSeries([
    {date: '2024-01-01', openValue: 112.5, proceeds: 0, originalCost: 100, pnl: 12.5, income: 0},
    {date: '2024-01-03', openValue: 120, proceeds: 0, originalCost: 100, pnl: 20, income: 5},
]);

/** Lot 3 with its income unknown on its last date, 2024-01-03, a date lot 1 shares. */
const LOT_3_UNKNOWN_ON_LAST = lotSeries([
    {date: '2024-01-01', openValue: 112.5, proceeds: 0, originalCost: 100, pnl: 12.5, income: 0},
    {date: '2024-01-03', openValue: 120, proceeds: 0, originalCost: 100, pnl: 20, income: null},
]);

/** Lot 4: no positive original cost, so even when listed among the percent lots it stays out of the ratio (today's per-point guard). */
const LOT_4 = lotSeries([{date: '2024-01-02', openValue: 8, proceeds: 0, originalCost: 0, pnl: 8, income: 0}]);
const LOT_4_UNKNOWN = lotSeries([{date: '2024-01-02', openValue: 8, proceeds: 0, originalCost: 0, pnl: 8, income: null}]);

/** Lot 1 aggregated alone. */
const LOT_1_VALUE_ALONE: AggregatedValuePoint[] = [
    {date: '2024-01-02', openValue: 100, proceeds: 0, originalCost: 100, income: 0},
    {date: '2024-01-03', openValue: 120, proceeds: 0, originalCost: 100, income: 5},
    {date: '2024-01-04', openValue: 75, proceeds: 70, originalCost: 100, income: 5},
];

/** Lot 1 alone, as a percent lot. */
const LOT_1_RETURN_ALONE: AggregateReturnPoint[] = [
    {date: '2024-01-02', totalReturn: 0, openingValue: 100, pnlWithIncome: 0},
    {date: '2024-01-03', totalReturn: 0.25, openingValue: 100, pnlWithIncome: 25},
    {date: '2024-01-04', totalReturn: 0.5, openingValue: 100, pnlWithIncome: 50},
];

describe('parseValueSeriesPoint', () => {
    it('parses the four amounts and a known income from the API decimal strings', () => {
        expect(parseValueSeriesPoint({date: '2024-01-04', proceeds: '70.5', open_value: '75.25', original_cost: '100', pnl: '45.75', income: '5.5'})).toEqual({
            date: '2024-01-04',
            proceeds: 70.5,
            openValue: 75.25,
            originalCost: 100,
            pnl: 45.75,
            income: 5.5,
        });
    });

    it('keeps a known zero income as 0', () => {
        expect(parseValueSeriesPoint({date: '2024-01-02', proceeds: '0', open_value: '100', original_cost: '100', pnl: '0', income: '0'}).income).toBe(0);
        expect(parseValueSeriesPoint({date: '2024-01-02', proceeds: 0, open_value: 100, original_cost: 100, pnl: 0, income: 0}).income).toBe(0);
    });

    it('keeps an unknown income (null: no FX rate) as null, never 0, while the amounts still parse', () => {
        expect(parseValueSeriesPoint({date: '2024-01-03', proceeds: '0', open_value: '280', original_cost: '300', pnl: '-20', income: null})).toEqual({
            date: '2024-01-03',
            proceeds: 0,
            openValue: 280,
            originalCost: 300,
            pnl: -20,
            income: null,
        });
    });

    it('reads an unparseable or non-finite income as unknown, as safeDecimal does', () => {
        // Control: the same point with a readable income.
        expect(parseValueSeriesPoint({date: '2024-01-03', proceeds: '0', open_value: '280', original_cost: '300', pnl: '-20', income: '45'}).income).toBe(45);

        expect(parseValueSeriesPoint({date: '2024-01-03', proceeds: '0', open_value: '280', original_cost: '300', pnl: '-20', income: 'n/a'}).income).toBeNull();
        expect(parseValueSeriesPoint({date: '2024-01-03', proceeds: '0', open_value: '280', original_cost: '300', pnl: '-20', income: 'Infinity'}).income).toBeNull();
    });

    it('unwraps the OpenAPI scalar-or-array shape of income, a null inside it staying unknown', () => {
        // The generated type of `income` is `(string | null) | Array<string | null>`; safeDecimal reads position 0.
        expect(parseValueSeriesPoint({date: '2024-01-03', proceeds: '0', open_value: '280', original_cost: '300', pnl: '-20', income: ['45']}).income).toBe(45);
        expect(parseValueSeriesPoint({date: '2024-01-03', proceeds: '0', open_value: '280', original_cost: '300', pnl: '-20', income: [null]}).income).toBeNull();
    });

    it('reads an absent income as unknown: the helper never infers a zero', () => {
        // Responses are validated against the API schema, which fills an absent `income` with its default '0'
        // before this point is built. That default is the API's statement; the helper itself never invents a 0.
        expect(parseValueSeriesPoint({date: '2024-01-03', proceeds: '0', open_value: '280', original_cost: '300', pnl: '-20'}).income).toBeNull();
    });

    it('still reads a missing or unparseable amount as 0, as before B3b', () => {
        expect(parseValueSeriesPoint({date: '2024-01-03', proceeds: null, open_value: undefined, original_cost: '', pnl: 'n/a', income: '5'})).toEqual({
            date: '2024-01-03',
            proceeds: 0,
            openValue: 0,
            originalCost: 0,
            pnl: 0,
            income: 5,
        });
    });
});

describe('pnlWithIncome', () => {
    it('adds the cumulative income to the FIFO P&L', () => {
        expect(pnlWithIncome({pnl: 20, income: 5})).toBe(25);
        expect(pnlWithIncome({pnl: -20, income: 5})).toBe(-15);
    });

    it('treats a zero income as known', () => {
        expect(pnlWithIncome({pnl: 20, income: 0})).toBe(20);
        expect(pnlWithIncome({pnl: 0, income: 0})).toBe(0);
    });

    it('is unknown when the income is unknown, whatever the P&L', () => {
        expect(pnlWithIncome({pnl: 20, income: null})).toBeNull();
        expect(pnlWithIncome({pnl: 0, income: null})).toBeNull();
    });
});

describe('comprehensiveValue', () => {
    it('is residual value + sale proceeds + cumulative income', () => {
        expect(comprehensiveValue({openValue: 75, proceeds: 70, income: 5})).toBe(150);
    });

    it('treats a zero income as known', () => {
        expect(comprehensiveValue({openValue: 100, proceeds: 0, income: 0})).toBe(100);
    });

    it('is unknown when the income is unknown, on a lot point or on an aggregated one', () => {
        expect(comprehensiveValue({openValue: 75, proceeds: 70, income: null})).toBeNull();
        const aggregated: AggregatedValuePoint = {date: '2024-01-03', openValue: 400, proceeds: 0, originalCost: 400, income: null};
        expect(comprehensiveValue(aggregated)).toBeNull();
    });
});

describe('aggregateValuePoints', () => {
    it('sums each amount per date across the lots, sorted by date, with the same totals as before B3b', () => {
        expect(aggregateValuePoints([1, 2], seriesByLot({1: LOT_1, 2: LOT_2_KNOWN}))).toEqual([
            {date: '2024-01-02', openValue: 420, proceeds: 0, originalCost: 400, income: 5},
            {date: '2024-01-03', openValue: 400, proceeds: 0, originalCost: 400, income: 50},
            {date: '2024-01-04', openValue: 385, proceeds: 70, originalCost: 400, income: 95},
        ]);
    });

    it('aggregates each date over the lots that have a point on it, sorting dates across lots', () => {
        // Lot 3 starts a day before lot 1, which is listed first, and has no point on 2024-01-02.
        expect(aggregateValuePoints([1, 3], seriesByLot({1: LOT_1, 3: LOT_3}))).toEqual([
            {date: '2024-01-01', openValue: 112.5, proceeds: 0, originalCost: 100, income: 0},
            {date: '2024-01-02', openValue: 100, proceeds: 0, originalCost: 100, income: 0},
            {date: '2024-01-03', openValue: 240, proceeds: 0, originalCost: 200, income: 10},
            {date: '2024-01-04', openValue: 75, proceeds: 70, originalCost: 100, income: 5},
        ]);
    });

    it('aggregates only the lots it is given', () => {
        // Lot 2's unknown income is in the map but not in the selection: it must not reach the totals.
        expect(aggregateValuePoints([1], seriesByLot({1: LOT_1, 2: LOT_2_UNKNOWN_FROM_2ND}))).toEqual(LOT_1_VALUE_ALONE);
    });

    it('skips a lot id that has no series in the map', () => {
        expect(aggregateValuePoints([1, 99], seriesByLot({1: LOT_1}))).toEqual(LOT_1_VALUE_ALONE);
    });

    it('returns no points for no lots, an empty map or an empty series', () => {
        expect(aggregateValuePoints([], seriesByLot({1: LOT_1}))).toEqual([]);
        expect(aggregateValuePoints([1, 2], seriesByLot({}))).toEqual([]);
        expect(aggregateValuePoints([1], seriesByLot({1: lotSeries([])}))).toEqual([]);
    });

    it('makes the income unknown from the date one lot income is, the other sums still summed', () => {
        expect(aggregateValuePoints([1, 2], seriesByLot({1: LOT_1, 2: LOT_2_UNKNOWN_FROM_2ND}))).toEqual([
            {date: '2024-01-02', openValue: 420, proceeds: 0, originalCost: 400, income: 5},
            {date: '2024-01-03', openValue: 400, proceeds: 0, originalCost: 400, income: null},
            {date: '2024-01-04', openValue: 385, proceeds: 70, originalCost: 400, income: null},
        ]);
    });

    it('does not let a known income listed after an unknown one bring the total back', () => {
        const series = seriesByLot({1: LOT_1, 2: LOT_2_UNKNOWN_FROM_2ND});
        const reversed = aggregateValuePoints([2, 1], series);
        expect(reversed).toEqual(aggregateValuePoints([1, 2], series));
        expect(reversed.map((point) => point.income)).toEqual([5, null, null]);
    });

    it('confines an unknown income to its own date', () => {
        // Lot 3's income is unknown on 2024-01-03 only. The dates where only one of the two lots has a point keep a known income.
        expect(aggregateValuePoints([1, 3], seriesByLot({1: LOT_1, 3: LOT_3_UNKNOWN_ON_LAST}))).toEqual([
            {date: '2024-01-01', openValue: 112.5, proceeds: 0, originalCost: 100, income: 0},
            {date: '2024-01-02', openValue: 100, proceeds: 0, originalCost: 100, income: 0},
            {date: '2024-01-03', openValue: 240, proceeds: 0, originalCost: 200, income: null},
            {date: '2024-01-04', openValue: 75, proceeds: 70, originalCost: 100, income: 5},
        ]);
    });
});

describe('aggregateReturnPoints', () => {
    it('sums P&L with income over every lot and the return over the percent lots, with the same totals as before B3b', () => {
        expect(aggregateReturnPoints([1, 2], new Set([1, 2]), seriesByLot({1: LOT_1, 2: LOT_2_KNOWN}))).toEqual([
            {date: '2024-01-02', totalReturn: 0.0625, openingValue: 400, pnlWithIncome: 25},
            {date: '2024-01-03', totalReturn: 0.125, openingValue: 400, pnlWithIncome: 50},
            {date: '2024-01-04', totalReturn: 0.375, openingValue: 400, pnlWithIncome: 150},
        ]);
    });

    it('keeps an abs-only lot in the P&L but out of the ratio and of the opening value', () => {
        expect(aggregateReturnPoints([1, 2], new Set([1]), seriesByLot({1: LOT_1, 2: LOT_2_KNOWN}))).toEqual([
            {date: '2024-01-02', totalReturn: 0, openingValue: 100, pnlWithIncome: 25},
            {date: '2024-01-03', totalReturn: 0.25, openingValue: 100, pnlWithIncome: 50},
            {date: '2024-01-04', totalReturn: 0.5, openingValue: 100, pnlWithIncome: 150},
        ]);
    });

    it('has no percent return without a percent lot: opening value 0, return null', () => {
        expect(aggregateReturnPoints([1, 2], new Set(), seriesByLot({1: LOT_1, 2: LOT_2_KNOWN}))).toEqual([
            {date: '2024-01-02', totalReturn: null, openingValue: 0, pnlWithIncome: 25},
            {date: '2024-01-03', totalReturn: null, openingValue: 0, pnlWithIncome: 50},
            {date: '2024-01-04', totalReturn: null, openingValue: 0, pnlWithIncome: 150},
        ]);
    });

    it('walks only the abs lots: a percent id outside them contributes nothing', () => {
        expect(aggregateReturnPoints([1], new Set([1, 2]), seriesByLot({1: LOT_1, 2: LOT_2_KNOWN}))).toEqual(LOT_1_RETURN_ALONE);
    });

    it('keeps a percent lot out of the ratio on a date its original cost is not positive', () => {
        // Lot 4's P&L counts on 2024-01-02; its cost and its return do not.
        expect(aggregateReturnPoints([1, 4], new Set([1, 4]), seriesByLot({1: LOT_1, 4: LOT_4}))).toEqual([
            {date: '2024-01-02', totalReturn: 0, openingValue: 100, pnlWithIncome: 8},
            {date: '2024-01-03', totalReturn: 0.25, openingValue: 100, pnlWithIncome: 25},
            {date: '2024-01-04', totalReturn: 0.5, openingValue: 100, pnlWithIncome: 50},
        ]);
    });

    it('aggregates each date over the lots that have a point on it, sorting dates across lots', () => {
        expect(aggregateReturnPoints([1, 3], new Set([1, 3]), seriesByLot({1: LOT_1, 3: LOT_3}))).toEqual([
            {date: '2024-01-01', totalReturn: 0.125, openingValue: 100, pnlWithIncome: 12.5},
            {date: '2024-01-02', totalReturn: 0, openingValue: 100, pnlWithIncome: 0},
            {date: '2024-01-03', totalReturn: 0.25, openingValue: 200, pnlWithIncome: 50},
            {date: '2024-01-04', totalReturn: 0.5, openingValue: 100, pnlWithIncome: 50},
        ]);
    });

    it('skips a lot id that has no series, and returns no points for no lots or an empty map', () => {
        expect(aggregateReturnPoints([1, 99], new Set([1, 99]), seriesByLot({1: LOT_1}))).toEqual(LOT_1_RETURN_ALONE);
        expect(aggregateReturnPoints([], new Set([1]), seriesByLot({1: LOT_1}))).toEqual([]);
        expect(aggregateReturnPoints([1], new Set([1]), seriesByLot({}))).toEqual([]);
    });

    it('makes P&L with income and the return unknown from the date a percent lot income is, keeping the opening value', () => {
        expect(aggregateReturnPoints([1, 2], new Set([1, 2]), seriesByLot({1: LOT_1, 2: LOT_2_UNKNOWN_FROM_2ND}))).toEqual([
            {date: '2024-01-02', totalReturn: 0.0625, openingValue: 400, pnlWithIncome: 25},
            {date: '2024-01-03', totalReturn: null, openingValue: 400, pnlWithIncome: null},
            {date: '2024-01-04', totalReturn: null, openingValue: 400, pnlWithIncome: null},
        ]);
    });

    it('keeps the return known when the unknown income belongs to an abs-only lot', () => {
        expect(aggregateReturnPoints([1, 2], new Set([1]), seriesByLot({1: LOT_1, 2: LOT_2_UNKNOWN_FROM_2ND}))).toEqual([
            {date: '2024-01-02', totalReturn: 0, openingValue: 100, pnlWithIncome: 25},
            {date: '2024-01-03', totalReturn: 0.25, openingValue: 100, pnlWithIncome: null},
            {date: '2024-01-04', totalReturn: 0.5, openingValue: 100, pnlWithIncome: null},
        ]);
    });

    it('does not let a known income listed after an unknown one bring the totals back', () => {
        const series = seriesByLot({1: LOT_1, 2: LOT_2_UNKNOWN_FROM_2ND});
        const reversed = aggregateReturnPoints([2, 1], new Set([1, 2]), series);
        expect(reversed).toEqual(aggregateReturnPoints([1, 2], new Set([1, 2]), series));
        expect(reversed.map((point) => [point.totalReturn, point.pnlWithIncome])).toEqual([
            [0.0625, 25],
            [null, null],
            [null, null],
        ]);
    });

    it('confines an unknown income to its own date', () => {
        expect(aggregateReturnPoints([1, 3], new Set([1, 3]), seriesByLot({1: LOT_1, 3: LOT_3_UNKNOWN_ON_LAST}))).toEqual([
            {date: '2024-01-01', totalReturn: 0.125, openingValue: 100, pnlWithIncome: 12.5},
            {date: '2024-01-02', totalReturn: 0, openingValue: 100, pnlWithIncome: 0},
            {date: '2024-01-03', totalReturn: null, openingValue: 200, pnlWithIncome: null},
            {date: '2024-01-04', totalReturn: 0.5, openingValue: 100, pnlWithIncome: 50},
        ]);
    });

    it('keeps the return known when the unknown income belongs to a percent lot that adds nothing to the ratio that day', () => {
        // Lot 4 is listed among the percent lots but has no positive cost on 2024-01-02, so it is not part of that day's
        // ratio and its unknown income cannot make the ratio unknown. Its P&L with income is unknown, as for any lot.
        expect(aggregateReturnPoints([1, 4], new Set([1, 4]), seriesByLot({1: LOT_1, 4: LOT_4_UNKNOWN}))).toEqual([
            {date: '2024-01-02', totalReturn: 0, openingValue: 100, pnlWithIncome: null},
            {date: '2024-01-03', totalReturn: 0.25, openingValue: 100, pnlWithIncome: 25},
            {date: '2024-01-04', totalReturn: 0.5, openingValue: 100, pnlWithIncome: 50},
        ]);
    });
});

// ---------------------------------------------------------------------------
// Plan 52, C3 — the lots tooltip header names the point's own day
// ---------------------------------------------------------------------------

/**
 * At weekly and monthly resolution every lot series point comes from the component's
 * `toChartSeriesPoints`: `{name: day, value: [day, y]}` on the bucket's last day with data, plus the
 * bucket meta `bucketStart`, `bucketEnd` (the bucket's theoretical end: the Sunday, the month's last
 * day), `resolution` and `sourcePointCount`. A header that names `bucketEnd` names, for the period
 * still running or for a lot that stops inside one, a day without data or still to come.
 *
 * The contract of `tooltipBucketInfo(params)`:
 * - it answers for the FIRST param, in order, whose `data` is a non-null object with
 *   `bucketStart: string`, `bucketEnd: string` and `resolution` 'daily' | 'weekly' | 'monthly'.
 *   Every other param is passed over: the internal series (axis-trigger anchor, hover dots, income
 *   markers) carry no meta, and neither does a `data` that is null, undefined, a primitive or an array;
 * - it returns exactly `{date, bucketStart, bucketEnd, resolution}`, nothing else `data` carries;
 * - `date` is the point's own day: `data.value[0]` when it is an ISO day (`YYYY-MM-DD`), else
 *   `data.name` when it is one, else `bucketEnd`. It is not clamped to the bucket: bucketSpanUpTo does that;
 * - no params, or none with meta → `null`;
 * - pure: the params and their `data` are left untouched, and the result is a new object.
 */

/** A bucket's meta as a coarse series point carries it, so the fixtures cannot invent a key the component does not emit. */
type BucketMeta = Omit<BucketInfo, 'date'>;

/** One tooltip param, typed from the helper itself because the module's CallbackParam is not exported. */
type TooltipParam = Parameters<typeof tooltipBucketInfo>[0][number];

/** The ISO week of Monday 11 March 2024, Sunday 17 included. */
const WEEK_OF_11_MARCH: BucketMeta = {bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'};

/** The next ISO week, Monday 18 to Sunday 24 March 2024: a second bucket, so two points can be told apart. */
const WEEK_OF_18_MARCH: BucketMeta = {bucketStart: '2024-03-18', bucketEnd: '2024-03-24', resolution: 'weekly'};

/** March 2024, the 31st included. */
const MARCH_2024: BucketMeta = {bucketStart: '2024-03-01', bucketEnd: '2024-03-31', resolution: 'monthly'};

/** Wednesday 13 March 2024 as a daily bucket: the component's daily meta spans the point's own day. */
const DAY_13_MARCH: BucketMeta = {bucketStart: '2024-03-13', bucketEnd: '2024-03-13', resolution: 'daily'};

/** A coarse point with the given name/value fields and the bucket meta, so a case can vary the day fields alone. */
function bucketPoint(meta: BucketMeta, fields: {name?: unknown; value?: unknown}): Record<string, unknown> {
    return {...fields, ...meta, sourcePointCount: 3};
}

/** The point toChartSeriesPoints emits on `day` (named and plotted there), so each case starts from the real shape. */
function seriesPoint(day: string, meta: BucketMeta): Record<string, unknown> {
    return bucketPoint(meta, {name: day, value: [day, 1234.5]});
}

/** A lot series' tooltip param, so the point under test reaches the helper as ECharts hands it over. */
function lotParam(data: unknown, seriesId = 'return-1'): TooltipParam {
    return {seriesId, data};
}

/** The axis-trigger anchor's param on `day`: a bare named point that carries a day but no bucket meta. */
function anchorParam(day: string): TooltipParam {
    return {seriesId: 'axis-trigger-anchor', data: {name: day, value: [day, 0]}};
}

/** A per-lot hover dot's param on `day`: x in epoch ms and a colour, no bucket meta. */
function hoverDotParam(day: string): TooltipParam {
    return {seriesId: 'per-lot-hover-dots', data: {value: [Date.parse(`${day}T00:00:00Z`), 1234.5], itemStyle: {color: '#155eef'}}};
}

/** An income marker's param on `day`: an ISO x and its income event, no bucket meta. */
function incomeMarkerParam(day: string): TooltipParam {
    return {seriesId: 'lot-income-markers', data: {value: [day, 1234.5], incomeEvent: {type: 'DIVIDEND', date: day, broker_id: 1, transaction_id: 41, amount: '12.50', lot_ids: [1]}, itemStyle: {color: '#18794e', opacity: 0.95}}};
}

/** The helper, once a barrier has proved the module exports it. */
function bucketInfoOf(params: Parameters<typeof tooltipBucketInfo>[0]): BucketInfo | null {
    expect(tooltipBucketInfo, 'barrier: lotComparisonChartHelpers exports tooltipBucketInfo').toBeTypeOf('function');
    return tooltipBucketInfo(params);
}

describe('tooltipBucketInfo', () => {
    // Why: the header must name the day the line draws the point on; only `date` moves, the bucket stays whole for the span.
    it.each([
        {name: 'open week, last data on Wed 13', day: '2024-03-13', meta: WEEK_OF_11_MARCH, info: {date: '2024-03-13', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'}},
        {name: 'whole week, point on Sun 17', day: '2024-03-17', meta: WEEK_OF_11_MARCH, info: {date: '2024-03-17', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'}},
        {name: 'a lot that stops on Tue 12, inside its week', day: '2024-03-12', meta: WEEK_OF_11_MARCH, info: {date: '2024-03-12', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'}},
        {name: 'open month, last data on the 13th', day: '2024-03-13', meta: MARCH_2024, info: {date: '2024-03-13', bucketStart: '2024-03-01', bucketEnd: '2024-03-31', resolution: 'monthly'}},
        {name: 'whole month, point on the 31st', day: '2024-03-31', meta: MARCH_2024, info: {date: '2024-03-31', bucketStart: '2024-03-01', bucketEnd: '2024-03-31', resolution: 'monthly'}},
        {name: 'a daily point', day: '2024-03-13', meta: DAY_13_MARCH, info: {date: '2024-03-13', bucketStart: '2024-03-13', bucketEnd: '2024-03-13', resolution: 'daily'}},
    ])('names the point’s own day — $name', ({day, meta, info}) => {
        expect(bucketInfoOf([lotParam(seriesPoint(day, meta))])).toEqual(info);
    });

    // Why: the result is a BucketInfo and nothing more; toEqual alone would let a key copied as undefined through.
    it('returns exactly the four bucket keys, not sourcePointCount nor the point’s name and value', () => {
        const info = bucketInfoOf([lotParam(seriesPoint('2024-03-13', WEEK_OF_11_MARCH))]);
        expect(Object.keys(info ?? {}).sort()).toEqual(['bucketEnd', 'bucketStart', 'date', 'resolution']);
    });

    // Why: the internal series carry no bucket meta, so neither they nor their day may reach the header.
    it('passes over the internal series and answers for the lot point after them', () => {
        const params = [anchorParam('2024-03-13'), hoverDotParam('2024-03-13'), incomeMarkerParam('2024-03-13'), lotParam(seriesPoint('2024-03-12', WEEK_OF_11_MARCH))];
        expect(bucketInfoOf(params)).toEqual({date: '2024-03-12', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'});
    });

    // Why: with several lots under the cursor the header follows the first param ECharts lists, not the latest day.
    it.each([
        {name: 'Tue 12 listed before Tue 19', params: () => [lotParam(seriesPoint('2024-03-12', WEEK_OF_11_MARCH), 'return-1'), lotParam(seriesPoint('2024-03-19', WEEK_OF_18_MARCH), 'return-2')], info: {date: '2024-03-12', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'}},
        {name: 'Tue 19 listed before Tue 12', params: () => [lotParam(seriesPoint('2024-03-19', WEEK_OF_18_MARCH), 'return-2'), lotParam(seriesPoint('2024-03-12', WEEK_OF_11_MARCH), 'return-1')], info: {date: '2024-03-19', bucketStart: '2024-03-18', bucketEnd: '2024-03-24', resolution: 'weekly'}},
    ])('answers for the first lot point in order — $name', ({params, info}) => {
        expect(bucketInfoOf(params())).toEqual(info);
    });

    // Why: a point whose plotted x cannot be read still names its own day when its name carries one.
    it.each([
        {name: 'value absent', point: () => bucketPoint(WEEK_OF_11_MARCH, {name: '2024-03-12'})},
        {name: 'value a bare number', point: () => bucketPoint(WEEK_OF_11_MARCH, {name: '2024-03-12', value: 1234.5})},
        {name: 'value null', point: () => bucketPoint(WEEK_OF_11_MARCH, {name: '2024-03-12', value: null})},
        {name: 'value an ISO day string, not an array', point: () => bucketPoint(WEEK_OF_11_MARCH, {name: '2024-03-12', value: '2024-03-13'})},
        {name: 'value[0] in epoch ms', point: () => bucketPoint(WEEK_OF_11_MARCH, {name: '2024-03-12', value: [Date.UTC(2024, 2, 13), 1234.5]})},
    ])('reads the day from name when value holds no ISO day — $name', ({point}) => {
        expect(bucketInfoOf([lotParam(point())])).toEqual({date: '2024-03-12', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'});
    });

    // Why: the plotted x is where the line draws the point, so it wins over a name that says otherwise.
    it.each([
        {name: 'name absent', point: () => bucketPoint(WEEK_OF_11_MARCH, {value: ['2024-03-12', 1234.5]})},
        {name: 'name a different ISO day', point: () => bucketPoint(WEEK_OF_11_MARCH, {name: '2024-03-13', value: ['2024-03-12', 1234.5]})},
    ])('reads the day from value[0], the plotted x — $name', ({point}) => {
        expect(bucketInfoOf([lotParam(point())])).toEqual({date: '2024-03-12', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'});
    });

    // Why: a point whose day cannot be read keeps the old header, the bucket end, rather than naming no day at all.
    it.each([
        {name: 'value[0] in epoch ms, no name', point: () => bucketPoint(WEEK_OF_11_MARCH, {value: [Date.UTC(2024, 2, 13), 1234.5]})},
        {name: 'name not a day, no value', point: () => bucketPoint(WEEK_OF_11_MARCH, {name: 'Lot A'})},
        {name: 'value[0] a timestamp, not a bare day, no name', point: () => bucketPoint(WEEK_OF_11_MARCH, {value: ['2024-03-13T00:00:00Z', 1234.5]})},
    ])('falls back to bucketEnd when no ISO day can be read — $name', ({point}) => {
        expect(bucketInfoOf([lotParam(point())])).toEqual({date: '2024-03-17', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'});
    });

    // Why: clamping here would turn a day before the bucket into a one-day span on its first day; bucketSpanUpTo keeps that bucket whole.
    it.each([
        {name: 'a day after the bucket end', day: '2024-03-18', info: {date: '2024-03-18', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'}},
        {name: 'a day before the bucket start', day: '2024-03-10', info: {date: '2024-03-10', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'}},
    ])('keeps a day outside the bucket as it is, unclamped — $name', ({day, info}) => {
        expect(bucketInfoOf([lotParam(seriesPoint(day, WEEK_OF_11_MARCH))])).toEqual(info);
    });

    /** Points whose meta misses one requirement, each built fresh, so the two tables below cannot share a mutated one. */
    const INCOMPLETE_META = [
        {name: 'bucketStart missing', data: () => ({name: '2024-03-13', value: ['2024-03-13', 1234.5], bucketEnd: '2024-03-17', resolution: 'weekly', sourcePointCount: 3})},
        {name: 'bucketEnd a number', data: () => ({name: '2024-03-13', value: ['2024-03-13', 1234.5], bucketStart: '2024-03-11', bucketEnd: Date.UTC(2024, 2, 17), resolution: 'weekly', sourcePointCount: 3})},
        {name: 'resolution quarterly', data: () => ({name: '2024-03-13', value: ['2024-03-13', 1234.5], bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'quarterly', sourcePointCount: 3})},
        {name: 'resolution missing', data: () => ({name: '2024-03-13', value: ['2024-03-13', 1234.5], bucketStart: '2024-03-11', bucketEnd: '2024-03-17', sourcePointCount: 3})},
    ];

    // Why: a param with partial meta is no bucket point; answering for it would build the header out of a hole.
    it.each(INCOMPLETE_META)('answers null for a lone point with incomplete meta — $name', ({data}) => {
        expect(bucketInfoOf([lotParam(data())])).toBeNull();
    });

    // Why: passing over means the scan goes on, so a complete lot point after the incomplete one still names its bucket.
    it.each(INCOMPLETE_META)('passes over incomplete meta to the next lot point — $name', ({data}) => {
        expect(bucketInfoOf([lotParam(data()), lotParam(seriesPoint('2024-03-19', WEEK_OF_18_MARCH), 'return-2')])).toEqual({date: '2024-03-19', bucketStart: '2024-03-18', bucketEnd: '2024-03-24', resolution: 'weekly'});
    });

    // Why: with no bucket point under the cursor the header falls back to the plain day, and only a null answer sends it there.
    it.each([
        {name: 'no params', params: (): TooltipParam[] => []},
        {name: 'data null', params: () => [lotParam(null)]},
        {name: 'data undefined', params: () => [lotParam(undefined)]},
        {name: 'data a number', params: () => [lotParam(42)]},
        {name: 'data a string', params: () => [lotParam('x')]},
        {name: 'data an array', params: () => [lotParam(['2024-03-13', 5])]},
        {name: 'a param with no data at all', params: () => [{seriesId: 'return-1', axisValue: Date.UTC(2024, 2, 13)}]},
        {name: 'only the internal series', params: () => [anchorParam('2024-03-13'), hoverDotParam('2024-03-13'), incomeMarkerParam('2024-03-13')]},
    ])('answers null when no param carries bucket meta — $name', ({params}) => {
        expect(bucketInfoOf(params())).toBeNull();
    });

    // Why: ECharts hands the formatter its own series data items; mutating them on hover would change what the chart draws.
    it('leaves the params untouched and returns a new object', () => {
        const point = seriesPoint('2024-03-13', WEEK_OF_11_MARCH);
        const params = [anchorParam('2024-03-13'), lotParam(point)];
        const before = structuredClone(params);

        const info = bucketInfoOf(params);

        expect(params, 'tooltipBucketInfo mutated its params').toStrictEqual(before);
        expect(info).toEqual({date: '2024-03-13', bucketStart: '2024-03-11', bucketEnd: '2024-03-17', resolution: 'weekly'});
        expect(info, 'tooltipBucketInfo returned the data object itself').not.toBe(point);
    });
});

describe('tooltipBucketInfo through bucketSpanUpTo — the dates the lots header names', () => {
    /*
     * This is what the header shows: the component spans the bucket as `bucketSpanUpTo(bucket.date, bucket)`,
     * and the week range and «Value at» end on the span's `bucketEnd` (the month label reads it too). Only the
     * span's two dates are pinned: for a whole bucket bucketSpanUpTo returns the info it was given, four keys
     * included, so a whole-object match would pin the wrong thing.
     */

    /** The two dates the header reads for `params`, so each case states its oracle as the user sees it. */
    function headerSpanOf(params: Parameters<typeof tooltipBucketInfo>[0]): {bucketStart: string; bucketEnd: string} {
        const info = bucketInfoOf(params);
        if (info == null) throw new Error('tooltipBucketInfo found no bucket in the params');
        const {bucketStart, bucketEnd} = bucketSpanUpTo(info.date, info);
        return {bucketStart, bucketEnd};
    }

    // Why: in the period still running, or for a lot that stops inside one, the header must end on the last day with data.
    it.each([
        {name: 'open week, last data on Wed 13', day: '2024-03-13', meta: WEEK_OF_11_MARCH, span: {bucketStart: '2024-03-11', bucketEnd: '2024-03-13'}},
        {name: 'open month, last data on the 13th', day: '2024-03-13', meta: MARCH_2024, span: {bucketStart: '2024-03-01', bucketEnd: '2024-03-13'}},
        {name: 'a lot that stopped on Tue 12, inside a past week', day: '2024-03-12', meta: WEEK_OF_11_MARCH, span: {bucketStart: '2024-03-11', bucketEnd: '2024-03-12'}},
    ])('ends the header on the point’s own day — $name', ({day, meta, span}) => {
        expect(headerSpanOf([lotParam(seriesPoint(day, meta))])).toEqual(span);
    });

    // Why: a whole bucket, or a point whose day cannot be read, must still span the whole bucket: the fix shortens only the open ones.
    it.each([
        {name: 'whole week, point on Sun 17', params: () => [lotParam(seriesPoint('2024-03-17', WEEK_OF_11_MARCH))], span: {bucketStart: '2024-03-11', bucketEnd: '2024-03-17'}},
        {name: 'whole month, point on the 31st', params: () => [lotParam(seriesPoint('2024-03-31', MARCH_2024))], span: {bucketStart: '2024-03-01', bucketEnd: '2024-03-31'}},
        {name: 'no readable day, value[0] in epoch ms and no name', params: () => [lotParam(bucketPoint(WEEK_OF_11_MARCH, {value: [Date.UTC(2024, 2, 13), 1234.5]}))], span: {bucketStart: '2024-03-11', bucketEnd: '2024-03-17'}},
    ])('keeps the whole bucket — $name', ({params, span}) => {
        expect(headerSpanOf(params())).toEqual(span);
    });
});

describe('LotComparisonChart tooltip header — the glue on the source', () => {
    /*
     * The header is built inside the component, out of reach of a node test, so its glue is pinned on the
     * source: tooltipBucketInfo comes from the helper module (no local copy left to drift), the bucket is spanned
     * with bucketSpanUpTo, and the header names the span, never `bucket.bucketEnd` or `bucket.bucketStart`.
     */

    /** LotComparisonChart.svelte as it is on disk, because a node test cannot render the header it builds. */
    function componentSource(): string {
        return readFileSync(new URL('./LotComparisonChart.svelte', import.meta.url), 'utf8');
    }

    /** The body of the block that `opener` (ending in `{`) opens first after `anchor`, braces balanced. */
    function blockAfter(source: string, anchor: string, opener: string): string | undefined {
        const at = source.indexOf(anchor);
        const open = at < 0 ? -1 : source.indexOf(opener, at + anchor.length);
        if (open < 0) return undefined;
        const bodyStart = open + opener.length;
        let depth = 1;
        for (let i = bodyStart; i < source.length; i++) {
            if (source[i] === '{') depth++;
            else if (source[i] === '}' && --depth === 0) return source.slice(bodyStart, i);
        }
        return undefined;
    }

    /** buildTooltipBucketHeader's body, so the pins cannot match code elsewhere in the component; throws when it is not found. */
    function headerBody(): string {
        const body = blockAfter(componentSource(), 'function buildTooltipBucketHeader(', '): string {');
        if (body === undefined) throw new Error('LotComparisonChart.svelte: the body of function buildTooltipBucketHeader(…): string { … } was not found');
        return body;
    }

    // Why: a local copy would keep naming bucketEnd whatever the tested export does.
    it('takes tooltipBucketInfo from the helper module and keeps no local copy', () => {
        const source = componentSource();
        expect(source, 'LotComparisonChart.svelte still defines a local function tooltipBucketInfo').not.toMatch(/\bfunction\s+tooltipBucketInfo\s*\(/);
        expect(source, 'LotComparisonChart.svelte does not import tooltipBucketInfo from ./lotComparisonChartHelpers').toMatch(/import\s*\{[^}]*\btooltipBucketInfo\b[^}]*\}\s*from\s*'\.\/lotComparisonChartHelpers'/);
    });

    // Why: the span is bucketSpanUpTo's, already unit-tested; the header must not derive its own.
    it('imports bucketSpanUpTo from priceChartHelpers', () => {
        expect(componentSource(), 'LotComparisonChart.svelte does not import bucketSpanUpTo from $lib/components/charts/priceChartHelpers').toMatch(/import\s*\{[^}]*\bbucketSpanUpTo\b[^}]*\}\s*from\s*'\$lib\/components\/charts\/priceChartHelpers'/);
    });

    // Why: «Value at», the week range and the month must read the span; one bucket.bucketEnd left would name a day without data again.
    it('spans the bucket up to the point’s day and names only the span', () => {
        const body = headerBody();
        expect(body, 'buildTooltipBucketHeader does not call bucketSpanUpTo(bucket.date, bucket)').toMatch(/bucketSpanUpTo\(\s*bucket\.date\s*,\s*bucket\s*\)/);
        expect(body, 'buildTooltipBucketHeader still reads bucket.bucketEnd or bucket.bucketStart').not.toMatch(/\bbucket\.bucket(?:End|Start)\b/);
    });

    // Why: positive control on the same slice — without it the pins above could pass on an empty or wrong slice.
    it('slices the header itself: the daily fallback and the three header keys', () => {
        const body = headerBody();
        expect(body).toContain('formatLongDate(fallbackDate)');
        expect(body).toContain('chart.tooltip.valueAt');
        expect(body).toContain('chart.tooltip.weekRange');
        expect(body).toContain('chart.tooltip.monthLabel');
    });
});
