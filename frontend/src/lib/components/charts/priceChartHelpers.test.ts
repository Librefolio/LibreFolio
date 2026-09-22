/**
 * priceChartHelpers — pure unit tests (node env, no jsdom).
 *
 * These functions are the arithmetic core PriceChartFull hands to ECharts: they
 * synthesize OHLC, count buckets, resolve a dataZoom edge to a data index, and
 * translate a logical date range into a zoom window. None of this touches a
 * canvas, so it is tested here directly — this is exactly where an off-by-one or
 * a bad clamp would hide.
 *
 * The month label is asserted with an explicit locale so the expected string is
 * deterministic regardless of the machine's locale.
 */
import {describe, expect, it} from 'vitest';

import {backendSignalSchemas} from '$lib/charts/signals/backendTypes';
import type {LineDataPoint} from './LineChart.svelte';
import type {EventMarker} from './PriceChartFull.svelte';
import {CALENDAR_RETURN_PRESETS, DEFAULT_CALENDAR_RETURN_WINDOW, calendarReturnRangeDays, calendarReturnWindowDays, sanitizeCalendarReturnWindow, type CalendarReturnWindowSelection, type CalendarReturnWindowUnit} from './calendarReturnWindow';
import {
    buildDeltaHtml,
    buildEventScatterGroups,
    buildStaleTooltipHtml,
    computeGhostSeries,
    computeZoomWindow,
    countBuckets,
    extractCalendarReturnView,
    extractCalendarReturnViewsByAsset,
    formatMonthLabel,
    formatTruncatedGhostLabel,
    getBucketInfo,
    getVisibleDailyPoints,
    resolveActivePointIndex,
    resolveZoomBounds,
    resolveZoomIndex,
    synthesizeDailyOHLC,
    toAbsoluteValue,
    toDisplaySeries,
    type EventScatterContext,
} from './priceChartHelpers';

/** Minimal daily point; overrides layer on top. */
function pt(date: string, value: number, overrides: Partial<LineDataPoint> = {}): LineDataPoint {
    return {date, value, ...overrides};
}

/** A run of consecutive daily points 2024-01-01.. with value = index+1. */
function dailyRun(dates: string[]): LineDataPoint[] {
    return dates.map((date, index) => pt(date, index + 1));
}

const CALENDAR_INSTANCE_ID = 'asset-calendar-return';
const CALENDAR_SIGNAL_CODE = 'ASSET_CALENDAR_ROLLING_RETURN';

function calendarProvenance(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        status: 'available',
        reference_target_date: '2026-01-02',
        current_price_date: '2026-02-01',
        current_price_days_back: 0,
        reference_price_date: '2026-01-02',
        reference_price_days_back: 0,
        current_fx_date: null,
        current_fx_days_back: null,
        reference_fx_date: null,
        reference_fx_days_back: null,
        ...overrides,
    };
}

function calendarPoint(date: string, value: number | null, provenance: Record<string, unknown> = {}): Record<string, unknown> {
    return {date, value, provenance: calendarProvenance(provenance)};
}

function nestedCalendarResult(points: unknown[], overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        instance_id: CALENDAR_INSTANCE_ID,
        signal_code: CALENDAR_SIGNAL_CODE,
        status: 'ok',
        series: [{key: 'calendar_return', points}],
        ...overrides,
    };
}

function calendarInputCoverage(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        requested_points: 4,
        available_points: 0,
        contiguous_points: 0,
        observed_points: 0,
        backfilled_points: 0,
        missing_points: 4,
        max_consecutive_missing_points: 4,
        internal_gap_count: 0,
        coverage_ratio: 0,
        field_coverage: {close: 0},
        ...overrides,
    };
}

function typedUnavailableCalendarResult(message: string): Record<string, unknown> {
    return nestedCalendarResult([], {
        status: 'unavailable',
        series: [],
        availability: {
            domain_compatible: true,
            can_compute: false,
            input_coverage: calendarInputCoverage(),
            required_points: 7,
            warmup_complete: true,
            partial_coverage_used: false,
            reason_code: 'undefined_metric',
        },
        warmup: {
            requirement: {
                minimum_points: 1,
                stabilization_points: 6,
                total_points: 7,
            },
            loaded_points: 11,
            used_points: 7,
            complete: true,
        },
        warnings: [
            {
                code: 'undefined_metric_window',
                message,
                details: {
                    unavailable_points: 4,
                    reasons: {invalid_current_price: 4},
                },
            },
        ],
        error: null,
    });
}

function typedFailedCalendarResult(message: string): Record<string, unknown> {
    return nestedCalendarResult([], {
        status: 'failed',
        series: [],
        availability: {
            domain_compatible: true,
            can_compute: false,
            input_coverage: calendarInputCoverage({
                requested_points: 3,
                missing_points: 3,
                max_consecutive_missing_points: 3,
            }),
            required_points: 7,
            warmup_complete: false,
            partial_coverage_used: false,
            reason_code: null,
        },
        warmup: {
            requirement: {
                minimum_points: 1,
                stabilization_points: 6,
                total_points: 7,
            },
            loaded_points: 3,
            used_points: 0,
            complete: false,
        },
        warnings: [],
        error: {
            code: 'compute_error',
            message,
            details: {stage: 'calendar_return'},
            retryable: false,
        },
    });
}

describe('calendarReturnWindow', () => {
    it.each([
        ['1w', 7],
        ['1m', 30],
        ['3m', 90],
        ['1y', 365],
    ] as const)('maps the %s preset to exactly %i calendar days', (preset, expectedDays) => {
        const selection: CalendarReturnWindowSelection = {
            ...DEFAULT_CALENDAR_RETURN_WINDOW,
            kind: 'preset',
            preset,
        };

        expect(calendarReturnWindowDays(selection)).toBe(expectedDays);
        expect(CALENDAR_RETURN_PRESETS.find((candidate) => candidate.key === preset)?.windowDays).toBe(expectedDays);
    });

    it('measures availability by elapsed end-start days rather than an inclusive date count', () => {
        expect(calendarReturnRangeDays('2026-01-01', '2026-01-08')).toBe(7);
        expect(calendarReturnRangeDays('2026-01-08', '2026-01-08')).toBe(0);
    });

    it('keeps every preset as an exact positive request window even when it exceeds the visible span', () => {
        const span = calendarReturnRangeDays('2026-01-01', '2026-03-31');

        expect(span).toBe(89);
        expect(CALENDAR_RETURN_PRESETS.map(({key, windowDays}) => [key, windowDays])).toEqual([
            ['1w', 7],
            ['1m', 30],
            ['3m', 90],
            ['1y', 365],
        ]);
        expect(CALENDAR_RETURN_PRESETS.every(({windowDays}) => Number.isSafeInteger(windowDays) && windowDays > 0)).toBe(true);
        expect(CALENDAR_RETURN_PRESETS.find(({key}) => key === '1y')?.windowDays).toBeGreaterThan(span);
    });

    it.each([
        ['weeks', 7],
        ['months', 30],
        ['years', 365],
    ] as const)('converts a custom %s amount to an exact positive request window', (customUnit, multiplier) => {
        const selection: CalendarReturnWindowSelection = {
            ...DEFAULT_CALENDAR_RETURN_WINDOW,
            kind: 'custom',
            customAmount: 3,
            customUnit,
        };
        const convertedDays = 3 * multiplier;

        expect(calendarReturnWindowDays(selection)).toBe(convertedDays);
    });

    it('starts on 1M while remembering an independently valid 3Y custom request', () => {
        expect(DEFAULT_CALENDAR_RETURN_WINDOW).toEqual({
            kind: 'preset',
            preset: '1m',
            customAmount: 3,
            customUnit: 'years',
        });
        expect(calendarReturnWindowDays(DEFAULT_CALENDAR_RETURN_WINDOW)).toBe(30);
        const rememberedCustom: CalendarReturnWindowSelection = {
            ...DEFAULT_CALENDAR_RETURN_WINDOW,
            kind: 'custom',
        };
        expect(calendarReturnWindowDays(rememberedCustom)).toBe(1095);
    });

    it('keeps a positive custom N when the visible span is shorter than N', () => {
        const selection: CalendarReturnWindowSelection = {
            ...DEFAULT_CALENDAR_RETURN_WINDOW,
            kind: 'custom',
            customAmount: 2,
            customUnit: 'months',
        };
        const span = calendarReturnRangeDays('2026-01-01', '2026-03-01');
        const requestWindowDays = calendarReturnWindowDays(selection);

        expect(calendarReturnWindowDays(selection)).toBe(60);
        expect(span).toBe(59);
        expect(requestWindowDays).toBe(60);
        expect(requestWindowDays).toBeGreaterThan(span);
    });

    it('does not rewrite a valid stored selection after the visible range shrinks', () => {
        const previousSelection: CalendarReturnWindowSelection = {
            kind: 'custom',
            preset: '1y',
            customAmount: 3,
            customUnit: 'months',
        };
        const shrunkenSpan = calendarReturnRangeDays('2026-01-01', '2026-02-15');

        const persistedSelection = sanitizeCalendarReturnWindow(previousSelection);
        expect(shrunkenSpan).toBe(45);
        expect(calendarReturnWindowDays(persistedSelection)).toBe(90);
        expect(calendarReturnWindowDays(persistedSelection)).toBeGreaterThan(shrunkenSpan);
        expect(persistedSelection).toEqual({
            kind: 'custom',
            preset: '1y',
            customAmount: 3,
            customUnit: 'months',
        });
    });

    it('keeps Calendar mode requestable when the elapsed span is under seven days', () => {
        const span = calendarReturnRangeDays('2026-02-01', '2026-02-07');
        const requestedWindow = calendarReturnWindowDays({
            ...DEFAULT_CALENDAR_RETURN_WINDOW,
            kind: 'preset',
            preset: '1w',
        });

        expect(span).toBe(6);
        expect(requestedWindow).toBe(7);
        expect(requestedWindow).toBeGreaterThan(span);
    });

    it('preserves a valid stored selection and its inactive custom memory', () => {
        expect(
            sanitizeCalendarReturnWindow({
                kind: 'preset',
                preset: '1y',
                customAmount: 8,
                customUnit: 'months',
            }),
        ).toEqual({
            kind: 'preset',
            preset: '1y',
            customAmount: 8,
            customUnit: 'months',
        });
    });

    it('sanitizes malformed fields independently to their defaults', () => {
        expect(
            sanitizeCalendarReturnWindow({
                kind: 'custom',
                preset: '3m',
                customAmount: 0,
                customUnit: 'weeks',
            }),
        ).toEqual({
            kind: 'custom',
            preset: '3m',
            customAmount: 3,
            customUnit: 'weeks',
        });
        expect(
            sanitizeCalendarReturnWindow({
                kind: 'unexpected',
                preset: '2y',
                customAmount: 8,
                customUnit: 'days',
            }),
        ).toEqual({
            kind: 'preset',
            preset: '1m',
            customAmount: 8,
            customUnit: 'years',
        });
        expect(sanitizeCalendarReturnWindow(null)).toEqual(DEFAULT_CALENDAR_RETURN_WINDOW);
        expect(sanitizeCalendarReturnWindow([])).toEqual(DEFAULT_CALENDAR_RETURN_WINDOW);
    });

    it('falls back to the complete default when a stored custom product overflows', () => {
        expect(
            sanitizeCalendarReturnWindow({
                kind: 'custom',
                preset: '1y',
                customAmount: Number.MAX_SAFE_INTEGER,
                customUnit: 'years',
            }),
        ).toEqual(DEFAULT_CALENDAR_RETURN_WINDOW);
    });

    it.each([
        ['zero', 0, 'weeks'],
        ['negative', -1, 'months'],
        ['fractional', 1.5, 'years'],
        ['not finite', Number.POSITIVE_INFINITY, 'weeks'],
        ['unsafe amount', Number.MAX_SAFE_INTEGER + 1, 'months'],
        ['safe amount with unsafe product', Math.floor(Number.MAX_SAFE_INTEGER / 365) + 1, 'years'],
    ] as const)('returns no request value for a %s custom amount', (_label, customAmount, customUnit) => {
        const selection: CalendarReturnWindowSelection = {
            ...DEFAULT_CALENDAR_RETURN_WINDOW,
            kind: 'custom',
            customAmount,
            customUnit: customUnit as CalendarReturnWindowUnit,
        };

        expect(calendarReturnWindowDays(selection)).toBeNull();
    });

    it('returns no request value for unknown preset and unit variants', () => {
        const invalidPreset = {
            ...DEFAULT_CALENDAR_RETURN_WINDOW,
            kind: 'preset',
            preset: '2y',
        } as unknown as CalendarReturnWindowSelection;
        const invalidUnit = {
            ...DEFAULT_CALENDAR_RETURN_WINDOW,
            kind: 'custom',
            customUnit: 'days',
        } as unknown as CalendarReturnWindowSelection;

        expect(calendarReturnWindowDays(invalidPreset)).toBeNull();
        expect(calendarReturnWindowDays(invalidUnit)).toBeNull();
    });
});

describe('extractCalendarReturnView', () => {
    it('maps a runtime-flat ready result without rebasing its percentage values', () => {
        const view = extractCalendarReturnView(
            [
                {
                    instance_id: CALENDAR_INSTANCE_ID,
                    signal_code: CALENDAR_SIGNAL_CODE,
                    status: 'ok',
                    key: 'calendar_return',
                    points: [calendarPoint('2026-02-01', 12.5)],
                },
            ],
            CALENDAR_INSTANCE_ID,
        );

        expect(view.state).toBe('ready');
        expect(view.points.find((point) => point.date === '2026-02-01')).toMatchObject({
            date: '2026-02-01',
            value: 12.5,
        });
        expect(view.contextByDate.has('2026-02-01')).toBe(true);
    });

    it('accepts generated one-level series/points nesting and selects the requested instance, code, and series key', () => {
        const requested = nestedCalendarResult([calendarPoint('2026-02-02', -3.75)], {
            series: [
                {key: 'other_series', points: [calendarPoint('2026-02-02', 999)]},
                {key: 'calendar_return', points: [calendarPoint('2026-02-02', -3.75)]},
                {key: 'another_series', points: [calendarPoint('2026-02-02', -999)]},
            ],
        });
        const view = extractCalendarReturnView([{...requested, instance_id: 'another-instance'}, requested, {...requested, signal_code: 'RISK_ROLLING_RETURN'}], CALENDAR_INSTANCE_ID);

        expect(view.state).toBe('ready');
        expect(view.points.find((point) => point.date === '2026-02-02')).toMatchObject({
            date: '2026-02-02',
            value: -3.75,
        });
        expect(view.points.some((point) => point.value === 999)).toBe(false);
        expect(view.points.some((point) => point.value === -999)).toBe(false);
    });

    it('preserves every date and turns null values into explicit missing chart gaps', () => {
        const view = extractCalendarReturnView(
            [
                nestedCalendarResult([
                    calendarPoint('2026-02-01', null, {
                        status: 'missing_reference',
                        reference_target_date: '2026-01-02',
                        reference_price_date: null,
                        reference_price_days_back: null,
                    }),
                    calendarPoint('2026-02-02', 1.25, {
                        reference_target_date: '2026-01-03',
                        current_price_date: '2026-02-02',
                        reference_price_date: '2026-01-03',
                    }),
                ]),
            ],
            CALENDAR_INSTANCE_ID,
        );

        expect(view.points.map((point) => point.date)).toEqual(['2026-02-01', '2026-02-02']);
        expect(view.points.find((point) => point.date === '2026-02-01')).toMatchObject({
            value: 0,
            missing: true,
        });
        expect(view.points.find((point) => point.date === '2026-02-02')).toMatchObject({
            value: 1.25,
        });
        expect(view.points.find((point) => point.date === '2026-02-02')?.missing).not.toBe(true);
    });

    it('uses maximum price/FX staleness overall and keeps the FX-only maximum separate', () => {
        const view = extractCalendarReturnView(
            [
                nestedCalendarResult([
                    calendarPoint('2026-02-10', 4.5, {
                        reference_target_date: '2026-01-11',
                        current_price_date: '2026-02-08',
                        current_price_days_back: 2,
                        reference_price_date: '2026-01-05',
                        reference_price_days_back: 6,
                        current_fx_date: '2026-02-06',
                        current_fx_days_back: 4,
                        reference_fx_date: '2026-01-02',
                        reference_fx_days_back: 9,
                    }),
                ]),
            ],
            CALENDAR_INSTANCE_ID,
        );

        expect(view.points.find((point) => point.date === '2026-02-10')).toMatchObject({
            staleDays: 9,
            fxStaleDays: 9,
        });
        expect(view.contextByDate.get('2026-02-10')).toMatchObject({
            referenceTargetDate: '2026-01-11',
            currentPriceDate: '2026-02-08',
            referencePriceDate: '2026-01-05',
            currentFxDate: '2026-02-06',
            referenceFxDate: '2026-01-02',
        });
    });

    it('keeps usable points and reports a partial backend result as partial', () => {
        const view = extractCalendarReturnView([nestedCalendarResult([calendarPoint('2026-02-01', 2.5)], {status: 'partial'})], CALENDAR_INSTANCE_ID);

        expect(view.state).toBe('partial');
        expect(view.points.find((point) => point.date === '2026-02-01')).toMatchObject({
            value: 2.5,
        });
    });

    it('preserves an unavailable reason and warning detail without fabricating primary values', () => {
        const warning = 'Every selected Calendar output is undefined.';
        const typedUnavailable = typedUnavailableCalendarResult(warning);
        expect(backendSignalSchemas.result.safeParse(typedUnavailable).success).toBe(true);
        const view = extractCalendarReturnView([typedUnavailable], CALENDAR_INSTANCE_ID);

        expect(view).toMatchObject({
            state: 'unavailable',
            points: [],
            contextByDate: new Map(),
            problem: {
                code: 'undefined_metric',
                status: 'unavailable',
                message: warning,
                requestedPoints: 4,
                availablePoints: 0,
                minimumPoints: 1,
                warmupUsedPoints: 7,
                warmupRequiredPoints: 7,
                missingPoints: 4,
                maxConsecutiveMissingPoints: 4,
                coverageRatio: 0,
                coveragePercent: 0,
            },
        });
    });

    it('preserves a failed result and its typed backend error detail', () => {
        const detail = 'Calendar calculation rejected for the selected fingerprint.';
        const view = extractCalendarReturnView([typedFailedCalendarResult(detail)], CALENDAR_INSTANCE_ID);

        expect(view).toMatchObject({
            state: 'error',
            points: [],
            contextByDate: new Map(),
            problem: {
                code: 'calculation_failed',
                status: 'failed',
                message: detail,
                requestedPoints: 3,
                availablePoints: 0,
                minimumPoints: 1,
                warmupUsedPoints: 0,
                warmupRequiredPoints: 7,
                missingPoints: 3,
                maxConsecutiveMissingPoints: 3,
                coverageRatio: 0,
                coveragePercent: null,
            },
        });
    });

    it.each([
        {label: 'null results', rawResults: null},
        {
            label: 'missing calendar series',
            rawResults: [nestedCalendarResult([], {series: [{key: 'another_series', points: [calendarPoint('2026-02-01', 1)]}]})],
        },
        {
            label: 'non-array points',
            rawResults: [nestedCalendarResult([], {series: [{key: 'calendar_return', points: {date: '2026-02-01', value: 1}}]})],
        },
    ])('returns error for malformed $label payloads', ({rawResults}) => {
        expect(extractCalendarReturnView(rawResults, CALENDAR_INSTANCE_ID)).toEqual({
            state: 'error',
            points: [],
            contextByDate: new Map(),
            problem: null,
        });
    });
});

describe('extractCalendarReturnViewsByAsset', () => {
    it('rejects malformed string unavailable by owned asset id', () => {
        const malformedUnavailable = nestedCalendarResult([], {status: 'unavailable'});
        expect(backendSignalSchemas.result.safeParse(malformedUnavailable).success).toBe(false);

        const views = extractCalendarReturnViewsByAsset([{asset_id: 105, signals: [malformedUnavailable]}], [105], CALENDAR_INSTANCE_ID);
        expect(views.get(105)).toEqual({
            state: 'error',
            points: [],
            contextByDate: new Map(),
            problem: null,
        });
    });

    it('keeps independently sparse I60G Calendar subsets joined by asset id', () => {
        const views = extractCalendarReturnViewsByAsset(
            [
                {
                    asset_id: 104,
                    signals: [typedUnavailableCalendarResult('Every selected I60G Calendar output is undefined.')],
                },
                {
                    asset_id: 102,
                    signals: [
                        nestedCalendarResult(
                            [
                                calendarPoint('2026-04-13', 32, {
                                    reference_target_date: '2026-04-06',
                                    current_price_date: '2026-04-13',
                                    reference_price_date: '2026-04-06',
                                }),
                                calendarPoint('2026-04-11', 31, {
                                    reference_target_date: '2026-04-04',
                                    current_price_date: '2026-04-11',
                                    reference_price_date: '2026-04-04',
                                }),
                            ],
                            {status: 'partial'},
                        ),
                    ],
                },
                {
                    asset_id: 101,
                    signals: [
                        nestedCalendarResult(
                            [
                                calendarPoint('2026-04-05', 7.4, {
                                    reference_target_date: '2026-03-29',
                                    current_price_date: '2026-04-05',
                                    reference_price_date: '2026-03-29',
                                }),
                                calendarPoint('2026-04-01', 7, {
                                    reference_target_date: '2026-03-25',
                                    current_price_date: '2026-04-01',
                                    reference_price_date: '2026-03-25',
                                }),
                            ],
                            {status: 'partial'},
                        ),
                    ],
                },
                {
                    asset_id: 103,
                    signals: [
                        nestedCalendarResult(
                            [
                                calendarPoint('2026-04-01', 21, {
                                    reference_target_date: '2026-03-25',
                                    current_price_date: '2026-04-01',
                                    reference_price_date: '2026-03-25',
                                    current_fx_date: '2026-04-01',
                                    current_fx_days_back: 0,
                                    reference_fx_date: '2026-03-25',
                                    reference_fx_days_back: 0,
                                }),
                                calendarPoint('2026-04-10', null, {
                                    status: 'missing_reference',
                                    reference_target_date: '2026-04-03',
                                    current_price_date: '2026-04-10',
                                    reference_price_date: '2026-04-03',
                                    reference_price_days_back: 0,
                                    current_fx_date: '2026-04-10',
                                    current_fx_days_back: 0,
                                    reference_fx_date: null,
                                    reference_fx_days_back: null,
                                }),
                            ],
                            {status: 'partial'},
                        ),
                    ],
                },
            ],
            [101, 102, 103, 104],
            CALENDAR_INSTANCE_ID,
        );

        expect(views.get(101)?.state).toBe('partial');
        expect(views.get(101)?.points.map((point) => point.date)).toEqual(['2026-04-01', '2026-04-05']);
        expect(views.get(101)?.contextByDate.get('2026-04-01')).toMatchObject({
            referenceTargetDate: '2026-03-25',
            referencePriceDate: '2026-03-25',
        });

        expect(views.get(102)?.state).toBe('partial');
        expect(views.get(102)?.points.map((point) => point.date)).toEqual(['2026-04-11', '2026-04-13']);

        expect(views.get(103)?.state).toBe('partial');
        expect(views.get(103)?.points.map((point) => point.date)).toEqual(['2026-04-01', '2026-04-10']);
        expect(views.get(103)?.points.find((point) => point.date === '2026-04-10')).toMatchObject({
            value: 0,
            missing: true,
        });
        expect(views.get(103)?.contextByDate.get('2026-04-10')).toMatchObject({
            status: 'missing_reference',
            referenceTargetDate: '2026-04-03',
            referencePriceDate: '2026-04-03',
            currentFxDate: '2026-04-10',
            referenceFxDate: null,
        });

        expect(views.get(104)).toMatchObject({
            state: 'unavailable',
            points: [],
            contextByDate: new Map(),
            problem: {
                code: 'undefined_metric',
                status: 'unavailable',
            },
        });
    });
});

describe('formatMonthLabel', () => {
    it('formats a mid-month date as "Month YYYY" in the given locale', () => {
        expect(formatMonthLabel('2024-01-15', 'en-US')).toBe('January 2024');
        expect(formatMonthLabel('2024-12-01', 'en-US')).toBe('December 2024');
    });

    it('routes the locale argument through (non-English output)', () => {
        // de-DE keeps a full-ICU month name distinct from English, proving the
        // locale parameter is honored rather than ignored.
        expect(formatMonthLabel('2024-01-15', 'de-DE')).toBe('Januar 2024');
    });

    it('is anchored to UTC so the month never drifts across a timezone boundary', () => {
        // Midnight on the 1st: in any negative-offset zone the naive local date
        // would be the previous month. Anchored to UTC it stays February.
        expect(formatMonthLabel('2024-02-01', 'en-US')).toBe('February 2024');
        // Last day of a month, same guarantee at the other edge.
        expect(formatMonthLabel('2024-03-31', 'en-US')).toBe('March 2024');
    });
});

describe('getBucketInfo', () => {
    it('makes a daily point its own single-day bucket', () => {
        const info = getBucketInfo(pt('2024-01-03', 10), 'daily');
        expect(info).toEqual({bucketStart: '2024-01-03', bucketEnd: '2024-01-03'});
    });

    it('ignores stale bucket fields on a daily point', () => {
        // Even if a point carries bucket metadata, the daily branch treats it as
        // a single day.
        const info = getBucketInfo(pt('2024-01-03', 10, {bucketStart: '2023-12-01', bucketEnd: '2023-12-31'}), 'daily');
        expect(info).toEqual({bucketStart: '2024-01-03', bucketEnd: '2024-01-03'});
    });

    it('prefers the point\u2019s own bucket boundaries when present (weekly)', () => {
        const info = getBucketInfo(pt('2024-01-04', 10, {bucketStart: '2024-01-01', bucketEnd: '2024-01-07'}), 'weekly');
        expect(info).toEqual({bucketStart: '2024-01-01', bucketEnd: '2024-01-07'});
    });

    it('derives the bucket start from the resolution and uses the date as end (weekly, no meta)', () => {
        // 2024-01-03 is a Wednesday; the ISO week starts Monday 2024-01-01.
        const info = getBucketInfo(pt('2024-01-03', 10), 'weekly');
        expect(info).toEqual({bucketStart: '2024-01-01', bucketEnd: '2024-01-03'});
    });

    it('derives a monthly bucket start and keeps the point date as end', () => {
        const info = getBucketInfo(pt('2024-01-15', 10), 'monthly');
        expect(info).toEqual({bucketStart: '2024-01-01', bucketEnd: '2024-01-15'});
    });

    it('treats a non-string bucketStart as absent and derives instead', () => {
        // A numeric bucketStart is not a valid string boundary; the function must
        // fall back to mapDateToBucket rather than trust it.
        const point = {date: '2024-01-03', value: 10, bucketStart: 20240101 as unknown as string};
        const info = getBucketInfo(point as LineDataPoint, 'weekly');
        expect(info).toEqual({bucketStart: '2024-01-01', bucketEnd: '2024-01-03'});
    });
});

describe('synthesizeDailyOHLC', () => {
    it('opens the first point at its own close and boxes high/low to the envelope', () => {
        const [first] = synthesizeDailyOHLC([pt('2024-01-01', 10)]);
        expect(first.open).toBe(10);
        expect(first.close).toBe(10);
        expect(first.high).toBe(10);
        expect(first.low).toBe(10);
        expect(first.value).toBe(10);
    });

    it('opens each later point at the previous close', () => {
        const out = synthesizeDailyOHLC([pt('2024-01-01', 10), pt('2024-01-02', 12), pt('2024-01-03', 8)]);
        expect(out[1].open).toBe(10); // prev close
        expect(out[1].close).toBe(12);
        expect(out[1].high).toBe(12); // max(open=10, close=12)
        expect(out[1].low).toBe(10);
        expect(out[2].open).toBe(12); // prev close
        expect(out[2].close).toBe(8);
        expect(out[2].high).toBe(12); // max(12, 8)
        expect(out[2].low).toBe(8);
    });

    it('preserves explicit OHLC fields instead of synthesizing them', () => {
        const [only] = synthesizeDailyOHLC([pt('2024-01-01', 10, {open: 5, high: 20, low: 3, close: 11})]);
        expect(only).toMatchObject({open: 5, high: 20, low: 3, close: 11, value: 11});
    });

    it('falls back to value when close is null, and normalizes value to close', () => {
        // LineDataPoint allows close: null; the coalescing must reach value.
        const [only] = synthesizeDailyOHLC([pt('2024-01-01', 42, {close: null})]);
        expect(only.close).toBe(42);
        expect(only.value).toBe(42);
    });

    it('returns an empty array unchanged', () => {
        expect(synthesizeDailyOHLC([])).toEqual([]);
    });
});

describe('countBuckets', () => {
    it('counts one daily, weekly and monthly bucket for a single point', () => {
        expect(countBuckets([pt('2024-01-03', 1)])).toEqual({dailyCount: 1, weeklyCount: 1, monthlyCount: 1});
    });

    it('collapses days that share a week / month into one bucket each', () => {
        // 2024-01-01..2024-01-05 are all in ISO week 2024-01-01..07 and month Jan.
        const counts = countBuckets(dailyRun(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']));
        expect(counts).toEqual({dailyCount: 5, weeklyCount: 1, monthlyCount: 1});
    });

    it('separates points that cross a week and a month boundary', () => {
        // Jan 3 (wk Jan1-7), Jan 10 (wk Jan8-14), Feb 1 (wk Jan29-Feb4, month Feb).
        const counts = countBuckets(dailyRun(['2024-01-03', '2024-01-10', '2024-02-01']));
        expect(counts).toEqual({dailyCount: 3, weeklyCount: 3, monthlyCount: 2});
    });

    it('returns zeros for an empty series', () => {
        expect(countBuckets([])).toEqual({dailyCount: 0, weeklyCount: 0, monthlyCount: 0});
    });
});

describe('resolveZoomIndex', () => {
    const dates = ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'];

    it('rounds a numeric value to the nearest index', () => {
        expect(resolveZoomIndex(2.4, dates, 0)).toBe(2);
        expect(resolveZoomIndex(2.6, dates, 0)).toBe(3);
    });

    it('clamps a numeric value into [0, len-1]', () => {
        expect(resolveZoomIndex(-5, dates, 0)).toBe(0);
        expect(resolveZoomIndex(999, dates, 0)).toBe(dates.length - 1);
    });

    it('resolves a string to the exact matching date index', () => {
        expect(resolveZoomIndex('2024-01-04', dates, 0)).toBe(3);
    });

    it('falls back when a string date is not found', () => {
        expect(resolveZoomIndex('2020-06-06', dates, 2)).toBe(2);
    });

    it('falls back for a value that is neither number nor string', () => {
        expect(resolveZoomIndex(undefined, dates, 1)).toBe(1);
        expect(resolveZoomIndex(null, dates, 4)).toBe(4);
        expect(resolveZoomIndex({}, dates, 3)).toBe(3);
    });
});

describe('getVisibleDailyPoints', () => {
    const points = dailyRun(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']);

    it('returns the whole series when the range is null', () => {
        expect(getVisibleDailyPoints(points, null)).toBe(points);
    });

    it('filters inclusively on both ends of the range', () => {
        const visible = getVisibleDailyPoints(points, {startDate: '2024-01-02', endDate: '2024-01-04'});
        expect(visible.map((p) => p.date)).toEqual(['2024-01-02', '2024-01-03', '2024-01-04']);
    });

    it('returns empty when the range lies outside the data', () => {
        expect(getVisibleDailyPoints(points, {startDate: '2025-01-01', endDate: '2025-12-31'})).toEqual([]);
    });
});

describe('computeZoomWindow', () => {
    const points = dailyRun(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']);

    it('returns the full window when the range is null', () => {
        expect(computeZoomWindow(points, 'daily', null)).toEqual({start: 0, end: 100});
    });

    it('returns the full window when there are 0 or 1 points', () => {
        expect(computeZoomWindow([], 'daily', {startDate: '2024-01-01', endDate: '2024-01-05'})).toEqual({start: 0, end: 100});
        expect(computeZoomWindow([pt('2024-01-01', 1)], 'daily', {startDate: '2024-01-01', endDate: '2024-01-01'})).toEqual({start: 0, end: 100});
    });

    it('maps an interior range to start/end percentages of the last index', () => {
        // start at index 1 (2024-01-02), end at index 3 (2024-01-04), lastIndex 4.
        expect(computeZoomWindow(points, 'daily', {startDate: '2024-01-02', endDate: '2024-01-04'})).toEqual({start: 25, end: 75});
    });

    it('pins to the right edge when the range is entirely after the data', () => {
        expect(computeZoomWindow(points, 'daily', {startDate: '2024-02-01', endDate: '2024-02-05'})).toEqual({start: 100, end: 100});
    });

    it('pins to the left edge when the range is entirely before the data', () => {
        expect(computeZoomWindow(points, 'daily', {startDate: '2023-12-01', endDate: '2023-12-05'})).toEqual({start: 0, end: 0});
    });

    it('clamps end up to start for an inverted range', () => {
        // startDate after endDate: start resolves to index 3, end to index 1,
        // and the guard lifts end back to start -> {75, 75}.
        expect(computeZoomWindow(points, 'daily', {startDate: '2024-01-04', endDate: '2024-01-02'})).toEqual({start: 75, end: 75});
    });

    it('respects weekly bucket boundaries when locating the window', () => {
        // Three weekly points carrying explicit bucket meta.
        const weekly: LineDataPoint[] = [pt('2024-01-07', 1, {bucketStart: '2024-01-01', bucketEnd: '2024-01-07'}), pt('2024-01-14', 2, {bucketStart: '2024-01-08', bucketEnd: '2024-01-14'}), pt('2024-01-21', 3, {bucketStart: '2024-01-15', bucketEnd: '2024-01-21'})];
        // Range inside the second week: start bucketEnd >= 01-10 -> index 1;
        // end bucketStart <= 01-12 -> index 1. lastIndex 2 -> {50, 50}.
        expect(computeZoomWindow(weekly, 'weekly', {startDate: '2024-01-10', endDate: '2024-01-12'})).toEqual({start: 50, end: 50});
    });
});

// ===========================================================================
// View-mode transforms — the user toggles absolute ⇄ percentage
// ===========================================================================

describe('toDisplaySeries', () => {
    it('returns the raw series unchanged in absolute view', () => {
        const data = dailyRun(['2024-01-01', '2024-01-02']);
        // Same reference: absolute view never rebases.
        expect(toDisplaySeries(data, 'absolute')).toBe(data);
    });

    it('returns an empty series unchanged (nothing to rebase)', () => {
        const empty: LineDataPoint[] = [];
        expect(toDisplaySeries(empty, 'percentage')).toBe(empty);
    });

    it('leaves the series untouched when the first value is exactly 0 (no defined % change)', () => {
        const data = [pt('2024-01-01', 0), pt('2024-01-02', 5)];
        // Rebasing would divide by 0; the guard returns the series as-is.
        expect(toDisplaySeries(data, 'percentage')).toBe(data);
    });

    it('rebases every point to its percentage change from the first in percentage view', () => {
        const data = [pt('2024-01-01', 100), pt('2024-01-02', 110), pt('2024-01-03', 90)];
        const out = toDisplaySeries(data, 'percentage');
        expect(out.map((d) => d.value)).toEqual([0, 10, -10]);
        // Non-value fields are carried through.
        expect(out[1].date).toBe('2024-01-02');
    });
});

describe('toAbsoluteValue', () => {
    it('undoes the percentage rebase when a base value is known', () => {
        // 10% above a base of 100 → 110.
        expect(toAbsoluteValue(10, 'percentage', 100)).toBeCloseTo(110, 10);
        expect(toAbsoluteValue(-10, 'percentage', 100)).toBeCloseTo(90, 10);
    });

    it('returns the value untouched in percentage view when the base is unknown', () => {
        // No base (empty series): the click already carries an absolute value.
        expect(toAbsoluteValue(42, 'percentage', undefined)).toBe(42);
    });

    it('returns the value untouched in absolute view', () => {
        expect(toAbsoluteValue(42, 'absolute', 100)).toBe(42);
    });
});

// ===========================================================================
// resolveZoomBounds — projecting a dataZoom descriptor onto index bounds
// ===========================================================================

describe('resolveZoomBounds', () => {
    const dates = ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'];

    it('resolves explicit startValue/endValue by matching date', () => {
        expect(resolveZoomBounds({startValue: '2024-01-02', endValue: '2024-01-04'}, dates)).toEqual({startIndex: 1, endIndex: 3});
    });

    it('resolves a numeric startValue/endValue as a direct index', () => {
        expect(resolveZoomBounds({startValue: 1, endValue: 3}, dates)).toEqual({startIndex: 1, endIndex: 3});
    });

    it('projects a start/end percentage window onto the index range', () => {
        // start 0 → floor(0)=0; end 50 → ceil(0.5*4)=2.
        expect(resolveZoomBounds({start: 0, end: 50}, dates)).toEqual({startIndex: 0, endIndex: 2});
    });

    it('defaults a missing percentage window to the full 0..100 range', () => {
        // Neither startValue/endValue nor numeric start/end → full span.
        expect(resolveZoomBounds({}, dates)).toEqual({startIndex: 0, endIndex: 4});
    });

    it('treats a non-numeric start/end as the 0 / 100 default', () => {
        expect(resolveZoomBounds({start: 'x' as unknown as number, end: 'y' as unknown as number}, dates)).toEqual({startIndex: 0, endIndex: 4});
    });

    it('swaps inverted bounds so start ≤ end', () => {
        expect(resolveZoomBounds({startValue: 3, endValue: 1}, dates)).toEqual({startIndex: 1, endIndex: 3});
    });

    it('collapses to {0,0} for a single-date series (no percentage span possible)', () => {
        // lastIndex === 0 skips the percentage branch; both bounds stay at 0.
        expect(resolveZoomBounds({}, ['2024-01-01'])).toEqual({startIndex: 0, endIndex: 0});
    });
});

// ===========================================================================
// resolveActivePointIndex — hit-testing a pointer to a data index
// ===========================================================================

describe('resolveActivePointIndex', () => {
    it('rounds a grid X to the nearest index inside the series', () => {
        expect(resolveActivePointIndex(2.4, 5)).toBe(2);
        expect(resolveActivePointIndex(2.6, 5)).toBe(3);
    });

    it('accepts the first and last index (inclusive bounds)', () => {
        expect(resolveActivePointIndex(0, 5)).toBe(0);
        expect(resolveActivePointIndex(4, 5)).toBe(4);
    });

    it('returns null when the pointer rounds before the series', () => {
        // -0.4 rounds to -0 (≥0) but -0.6 rounds to -1 → outside.
        expect(resolveActivePointIndex(-0.6, 5)).toBeNull();
    });

    it('returns null when the pointer rounds past the last index', () => {
        // 4.5 rounds to 5, which is === length → outside.
        expect(resolveActivePointIndex(4.5, 5)).toBeNull();
    });

    it('returns null for an empty series', () => {
        expect(resolveActivePointIndex(0, 0)).toBeNull();
    });
});

// ===========================================================================
// computeGhostSeries — the dashed original-currency line for FX-converted data
// ===========================================================================

describe('computeGhostSeries', () => {
    it('returns null when no point carries an original value (the un-converted case)', () => {
        const data = dailyRun(['2024-01-01', '2024-01-02']);
        expect(computeGhostSeries(data, false, 'daily', 'Asset')).toBeNull();
    });

    it('labels the ghost with the main series name plus original flag+code', () => {
        const data = [pt('2024-01-01', 110, {originalValue: 100, originalCurrency: 'USD', originalCurrencyFlag: '🇺🇸'}), pt('2024-01-02', 121, {originalValue: 110})];
        const ghost = computeGhostSeries(data, false, 'daily', 'Apple');
        expect(ghost).not.toBeNull();
        expect(ghost!.label).toBe('💱 Apple (🇺🇸 USD)');
        // Absolute view: the lookup carries the raw original values by date.
        expect(ghost!.lookup.get('2024-01-01')).toBe(100);
        expect(ghost!.lookup.get('2024-01-02')).toBe(110);
    });

    it('falls back to just the currency when there is no main series label', () => {
        const data = [pt('2024-01-01', 110, {originalValue: 100, originalCurrency: 'USD'})];
        // No flag present → the flag slot is empty, currency still shown.
        const ghost = computeGhostSeries(data, false, 'daily', undefined);
        expect(ghost!.label).toBe('💱 USD');
    });

    it('rebases the ghost to its own first original value in percentage view', () => {
        const data = [pt('2024-01-01', 0, {originalValue: 100, originalCurrency: 'USD'}), pt('2024-01-02', 0, {originalValue: 130, originalCurrency: 'USD'})];
        const ghost = computeGhostSeries(data, true, 'daily', 'X');
        expect(ghost!.lookup.get('2024-01-01')).toBeCloseTo(0, 10);
        expect(ghost!.lookup.get('2024-01-02')).toBeCloseTo(30, 10);
    });

    it('keeps the ghost flat when its first original value is 0 (no divide-by-zero)', () => {
        const data = [pt('2024-01-01', 5, {originalValue: 0, originalCurrency: 'USD'}), pt('2024-01-02', 6, {originalValue: 50, originalCurrency: 'USD'})];
        const ghost = computeGhostSeries(data, true, 'daily', 'X');
        // firstOriginalValue === 0 → every normalized value is 0.
        expect(ghost!.lookup.get('2024-01-01')).toBe(0);
        expect(ghost!.lookup.get('2024-01-02')).toBe(0);
    });

    it('only maps points that actually carry an original value', () => {
        const data = [pt('2024-01-01', 110, {originalValue: 100, originalCurrency: 'USD'}), pt('2024-01-02', 90)];
        const ghost = computeGhostSeries(data, false, 'daily', 'X');
        // The second point has no originalValue → absent from the lookup.
        expect(ghost!.lookup.has('2024-01-02')).toBe(false);
        expect(ghost!.lookup.size).toBe(1);
    });

    it('degrades the label when the currency code is absent but the flag is present', () => {
        // Mirror of the flag-absent case: originalValue is present but no point
        // carries originalCurrency, so the code half of the label is empty while
        // the flag half still renders. A robustness path for partial FX metadata.
        const data = [pt('2024-01-01', 110, {originalValue: 100, originalCurrencyFlag: '🇺🇸'})];
        const ghost = computeGhostSeries(data, false, 'daily', 'X');
        expect(ghost!.label).toBe('💱 X (🇺🇸 )');
    });

    it('aggregates the ghost onto the coarser resolution, keyed by the bucket last date', () => {
        // Two daily points in the same ISO week collapse to one weekly point that
        // carries the last original value, keyed by the last daily date in the
        // bucket — the same key the main series uses, so the two stay aligned.
        const data = [pt('2024-01-01', 110, {originalValue: 100, originalCurrency: 'USD'}), pt('2024-01-03', 120, {originalValue: 130, originalCurrency: 'USD'})];
        const ghost = computeGhostSeries(data, false, 'weekly', 'X');
        expect(ghost!.lookup.get('2024-01-03')).toBe(130);
        expect(ghost!.lookup.size).toBe(1);
    });
});

// ===========================================================================
// buildEventScatterGroups — placing event markers on the price axis
// ===========================================================================

/** Minimal event marker; overrides layer on top. */
function evm(date: string, type: string, overrides: Partial<EventMarker> = {}): EventMarker {
    return {date, type, ...overrides};
}

/** A scatter context over a daily line, with optional overlays. */
function scatterCtx(dates: string[], values: number[], overrides: Partial<EventScatterContext> = {}): EventScatterContext {
    const resolvedLineData = dates.map((date, index) => pt(date, values[index]));
    return {
        dateIndexMap: new Map(dates.map((date, index) => [date, index])),
        resolvedLineData,
        overlayDataByLabel: new Map(),
        bucketInfoByDate: new Map(),
        baseColor: '#123456',
        ...overrides,
    };
}

describe('buildEventScatterGroups', () => {
    it('groups own-asset markers by type and colours them with the base colour', () => {
        const ctx = scatterCtx(['2024-01-01', '2024-01-02'], [10, 20]);
        const groups = buildEventScatterGroups([evm('2024-01-01', 'DIVIDEND'), evm('2024-01-02', 'DIVIDEND')], 'daily', ctx);
        expect(groups).toHaveLength(1);
        expect(groups[0].eventType).toBe('DIVIDEND');
        expect(groups[0].color).toBe('#123456');
        expect(groups[0].label).toBe('DIVIDEND');
        // Y follows the main price at each marker's date.
        expect(groups[0].points.map((p) => p.value)).toEqual([
            ['2024-01-01', 10],
            ['2024-01-02', 20],
        ]);
    });

    it('splits comparison markers per asset and colours them by their signal', () => {
        const ctx = scatterCtx(['2024-01-01'], [10]);
        const groups = buildEventScatterGroups([evm('2024-01-01', 'SIG', {assetLabel: 'Beta', signalColor: '#ff0000'}), evm('2024-01-01', 'SIG', {assetLabel: 'Gamma', signalColor: '#00ff00'})], 'daily', ctx);
        expect(groups).toHaveLength(2);
        const byLabel = new Map(groups.map((g) => [g.label, g.color]));
        expect(byLabel.get('Beta SIG')).toBe('#ff0000');
        expect(byLabel.get('Gamma SIG')).toBe('#00ff00');
    });

    it('falls back to a neutral colour for a comparison marker with no signal colour', () => {
        const ctx = scatterCtx(['2024-01-01'], [10]);
        const groups = buildEventScatterGroups([evm('2024-01-01', 'SIG', {assetLabel: 'Beta'})], 'daily', ctx);
        expect(groups[0].color).toBe('#6b7280');
    });

    it('places a comparison marker on its overlay line, not the main price', () => {
        const ctx = scatterCtx(['2024-01-01'], [10], {overlayDataByLabel: new Map([['Beta', new Map([['2024-01-01', 99]])]])});
        const groups = buildEventScatterGroups([evm('2024-01-01', 'SIG', {assetLabel: 'Beta'})], 'daily', ctx);
        expect(groups[0].points[0].value).toEqual(['2024-01-01', 99]);
    });

    it('falls back to the main price when the overlay has no value at that date', () => {
        const ctx = scatterCtx(['2024-01-01'], [10], {overlayDataByLabel: new Map([['Beta', new Map()]])});
        const groups = buildEventScatterGroups([evm('2024-01-01', 'SIG', {assetLabel: 'Beta'})], 'daily', ctx);
        // Overlay present but empty at this date → main price 10.
        expect(groups[0].points[0].value).toEqual(['2024-01-01', 10]);
    });

    it('skips a marker whose date is not on the axis', () => {
        const ctx = scatterCtx(['2024-01-01'], [10]);
        const groups = buildEventScatterGroups([evm('2024-06-01', 'DIVIDEND')], 'daily', ctx);
        // The only marker was off-axis → the group placed nothing and is dropped.
        expect(groups).toHaveLength(0);
    });

    it('buckets markers at a coarser resolution and carries the whole bucket on one point', () => {
        // Both markers fall in ISO week 01-01..01-07 (bucket-end 01-07), which is
        // on the axis; they collapse to a single placed point carrying both.
        const ctx = scatterCtx(['2024-01-07'], [42]);
        const groups = buildEventScatterGroups([evm('2024-01-01', 'DIVIDEND'), evm('2024-01-03', 'DIVIDEND')], 'weekly', ctx);
        expect(groups).toHaveLength(1);
        expect(groups[0].points).toHaveLength(1);
        expect(groups[0].points[0].value).toEqual(['2024-01-07', 42]);
        expect(groups[0].points[0].markers).toHaveLength(2);
        // The bucketInfo falls back to mapDateToBucket when not pre-computed.
        expect(groups[0].points[0].bucketInfo).toEqual({bucketStart: '2024-01-01', bucketEnd: '2024-01-07'});
    });

    it('prefers a pre-computed bucketInfo when the date is present in the map', () => {
        const ctx = scatterCtx(['2024-01-07'], [42], {bucketInfoByDate: new Map([['2024-01-07', {bucketStart: 'X', bucketEnd: 'Y'}]])});
        const groups = buildEventScatterGroups([evm('2024-01-03', 'DIVIDEND')], 'weekly', ctx);
        expect(groups[0].points[0].bucketInfo).toEqual({bucketStart: 'X', bucketEnd: 'Y'});
    });

    it('skips a bucketed marker whose bucket falls outside the plotted range', () => {
        // Coarse-resolution analog of the off-axis daily case: a June event buckets
        // to a June week-end date that the January-only axis does not contain, so
        // the bucket is skipped and the emptied group is dropped.
        const ctx = scatterCtx(['2024-01-07'], [42]);
        const groups = buildEventScatterGroups([evm('2024-06-05', 'DIVIDEND')], 'weekly', ctx);
        expect(groups).toHaveLength(0);
    });
});

// ===========================================================================
// buildDeltaHtml — the green/red delta suffix (colour derived from sign)
// ===========================================================================

describe('buildDeltaHtml', () => {
    it('uses green for a non-negative percentage delta and red for a negative one', () => {
        // The contract: colour is derived from the sign, not a fixed value.
        expect(buildDeltaHtml(2.5, 0, true)).toContain('#10b981');
        expect(buildDeltaHtml(2.5, 0, true)).toContain('(Δ +2.50%)');
        expect(buildDeltaHtml(-2.5, 0, true)).toContain('#ef4444');
        expect(buildDeltaHtml(-2.5, 0, true)).toContain('(Δ -2.50%)');
    });

    it('exactly 0 counts as non-negative (green, + sign)', () => {
        const html = buildDeltaHtml(0, 0, true);
        expect(html).toContain('#10b981');
        expect(html).toContain('(Δ +0.00%)');
    });

    it('shows both the absolute and percentage delta in absolute view', () => {
        // value 110 vs first 100 → +10.0000 absolute, +10.00% relative, green.
        const html = buildDeltaHtml(110, 100, false);
        expect(html).toContain('#10b981');
        expect(html).toContain('(Δ +10.0000 / +10.00%)');
    });

    it('colours by the absolute delta sign in absolute view', () => {
        const html = buildDeltaHtml(90, 100, false);
        expect(html).toContain('#ef4444');
        expect(html).toContain('(Δ -10.0000 / -10.00%)');
    });

    it('reports a 0% relative delta when the first value is 0 (no divide-by-zero)', () => {
        const html = buildDeltaHtml(10, 0, false);
        expect(html).toContain('(Δ +10.0000 / +0.00%)');
    });
});

// ===========================================================================
// buildStaleTooltipHtml — the amber staleness warning line(s)
// ===========================================================================

describe('buildStaleTooltipHtml', () => {
    it('emits nothing when the point is not stale', () => {
        expect(buildStaleTooltipHtml(undefined, undefined)).toBe('');
    });

    it('emits a single price-stale line when FX is fresh', () => {
        const html = buildStaleTooltipHtml(3, 0);
        expect(html).toContain('⚠');
        expect(html).toContain('Stale: 3d');
        // Only one warning line.
        expect(html.match(/⚠/g)).toHaveLength(1);
    });

    it('adds a second line when the FX rate is itself stale', () => {
        const html = buildStaleTooltipHtml(3, 5);
        expect(html).toContain('Stale: 3d');
        expect(html).toContain('FX rate: 5d old');
        expect(html.match(/⚠/g)).toHaveLength(2);
    });

    it('substitutes {days} into a provided (translated) template', () => {
        const html = buildStaleTooltipHtml(4, 0, 'Vecchio: {days}g');
        expect(html).toContain('Vecchio: 4g');
        expect(html).not.toContain('Stale:');
    });

    it('substitutes {days} into both provided templates when FX is stale', () => {
        const html = buildStaleTooltipHtml(4, 7, 'P {days}', 'FX {days}');
        expect(html).toContain('P 4');
        expect(html).toContain('FX 7');
    });
});

// ===========================================================================
// formatTruncatedGhostLabel — truncate the name, keep the 💱 and currency
// ===========================================================================

describe('formatTruncatedGhostLabel', () => {
    it('truncates only the name and keeps the 💱 prefix and currency suffix', () => {
        const longName = 'A'.repeat(40);
        const out = formatTruncatedGhostLabel(`💱 ${longName} (🇺🇸 USD)`);
        // truncateName keeps 29 chars + ellipsis for a 40-char name.
        expect(out).toBe(`💱 ${'A'.repeat(29)}… (🇺🇸 USD)`);
    });

    it('leaves a short well-formed label intact', () => {
        expect(formatTruncatedGhostLabel('💱 Apple (🇺🇸 USD)')).toBe('💱 Apple (🇺🇸 USD)');
    });

    it('truncates the whole string when it does not match the ghost shape', () => {
        const plain = 'Z'.repeat(40);
        expect(formatTruncatedGhostLabel(plain)).toBe(`${'Z'.repeat(29)}…`);
    });
});
