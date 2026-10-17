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
 * deterministic regardless of the machine's locale; without one it follows the
 * interface language (M-18), pinned in the last describe, which also writes the
 * tooltip delta in French.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

// The interface locale is the UI language regionalised by `navigator.language` (M-18). Node's tag
// follows the host's ICU locale, so it is pinned to en-US — jsdom's own — before any import.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import type {RenderedSignal} from '$lib/charts/signals';
import {backendSignalSchemas} from '$lib/charts/signals/backendTypes';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {currentLanguage} from '$lib/stores/app/language';
import {formatFixed} from '$lib/utils/core/formatFixed';
import {formatPercent} from '$lib/utils/core/formatPercent';
import type {LineDataPoint} from './LineChart.svelte';
import type {EventMarker} from './PriceChartFull.svelte';
import {CALENDAR_RETURN_PRESETS, DEFAULT_CALENDAR_RETURN_WINDOW, calendarReturnRangeDays, calendarReturnWindowDays, sanitizeCalendarReturnWindow, type CalendarReturnWindowSelection, type CalendarReturnWindowUnit} from './calendarReturnWindow';
import * as calendarReturnWindowModule from './calendarReturnWindow';
import {
    buildDeltaHtml,
    buildEventScatterGroups,
    buildStaleTooltipHtml,
    computeGhostSeries,
    computeZoomWindow,
    countBuckets,
    emptyCalendarReturnView,
    extractCalendarReturnView,
    extractCalendarReturnViewsByAsset,
    formatMonthLabel,
    formatTruncatedGhostLabel,
    getBucketInfo,
    bucketSpanUpTo,
    getVisibleDailyPoints,
    resolveActivePointIndex,
    resolveZoomBounds,
    resolveZoomIndex,
    splitGhostLabel,
    synthesizeDailyOHLC,
    toAbsoluteValue,
    toDisplaySeries,
    type BucketInfo,
    type EventScatterContext,
} from './priceChartHelpers';
import {aggregateLineSeries, downsampleRenderedSignal, type ChartResolution} from './timeSeriesAggregation';

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

describe('calendarReturnWindow — the window presets are labelled from the catalogues (P, item 8)', () => {
    // The rolling-return window presets carry English literal labels — '1W', '1M', '3M', '1Y' —
    // which the asset page prints as they are, so Italian reads «1W» beside a date picker that
    // reads the catalogue's week. The contract of the cure: a preset is a `count` of a `unit`
    // (`CalendarReturnWindowUnit`) instead of a label, and the module maps each unit to the
    // catalogue key of its count message, `CALENDAR_RETURN_UNIT_LABEL_KEYS` — the date picker's
    // keys, read by the page with `{values: {n: preset.count}}`, so the two say the same thing.
    // The keys and the windows do not change. The exports are read untyped, so this file compiles
    // before the cure and after it. Red today: no preset has a count or a unit, and no map exists.

    const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};
    const UNITS: readonly CalendarReturnWindowUnit[] = ['weeks', 'months', 'years'];
    /** The module's exports by name, read untyped: the map does not exist before the cure. */
    const moduleExports: Record<string, unknown> = {...calendarReturnWindowModule};
    /** Each preset's own fields, read untyped: the cure trades the literal label for a count and a unit. */
    const presetFields = CALENDAR_RETURN_PRESETS.map((preset): Record<string, unknown> => ({...preset}));

    /** The value behind a dotted key of a catalogue, if any. */
    const leafOf = (catalogue: unknown, key: string): unknown => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);

    /** Each of `keys` that some catalogue has no string for, with those catalogues: `{}` when all four have all of them. */
    function catalogueGaps(keys: readonly string[]): Record<string, string[]> {
        const gaps = keys.map((key) => [key, Object.entries(CATALOGUES).flatMap(([lang, catalogue]) => (typeof leafOf(catalogue, key) === 'string' ? [] : [lang]))] as const);
        return Object.fromEntries(gaps.filter(([, langs]) => langs.length > 0));
    }

    it('describes every preset by an integer count and a unit, not by a literal label', () => {
        const uncounted = presetFields.filter(({count, unit}) => !(Number.isInteger(count) && UNITS.includes(unit as CalendarReturnWindowUnit))).map(({key}) => key);
        const labelled = presetFields.filter((fields) => 'label' in fields).map(({key}) => key);
        expect(uncounted, 'presets without an integer count and a unit').toEqual([]);
        expect(labelled, 'presets that still carry a literal label').toEqual([]);
    });

    it('counts 1 week, 1 month, 3 months and 1 year, under the same keys and windows', () => {
        const presets = Object.fromEntries(presetFields.map(({key, count, unit, windowDays}) => [String(key), {count, unit, windowDays}]));

        expect(presets).toEqual({
            '1w': {count: 1, unit: 'weeks', windowDays: 7},
            '1m': {count: 1, unit: 'months', windowDays: 30},
            '3m': {count: 3, unit: 'months', windowDays: 90},
            '1y': {count: 1, unit: 'years', windowDays: 365},
        });
    });

    it('maps each unit to the date picker’s count message, which the four catalogues have', () => {
        const unitKeys = moduleExports.CALENDAR_RETURN_UNIT_LABEL_KEYS;

        expect(unitKeys, 'CALENDAR_RETURN_UNIT_LABEL_KEYS: unit → catalogue key').toEqual({weeks: 'datePicker.presets.weeks', months: 'datePicker.presets.months', years: 'datePicker.presets.years'});
        expect(catalogueGaps(Object.values(unitKeys as Record<string, string>)), 'key → the catalogues with no string for it').toEqual({});
    });
});

describe('emptyCalendarReturnView: no points and no context, idle and without a problem unless told otherwise (exported for the asset page, FE5c)', () => {
    it('defaults to an idle view with no points, an empty context map and no problem', () => {
        const view = emptyCalendarReturnView();

        expect(view).toEqual({state: 'idle', points: [], contextByDate: new Map(), problem: null});
        expect(view.contextByDate).toBeInstanceOf(Map);
    });

    it.each(['idle', 'loading', 'ready', 'partial', 'unavailable', 'error'] as const)('keeps the given %s state, with no problem by default', (state) => {
        expect(emptyCalendarReturnView(state)).toEqual({state, points: [], contextByDate: new Map(), problem: null});
    });

    it('keeps the given problem', () => {
        const problem = extractCalendarReturnView([typedUnavailableCalendarResult('Every selected Calendar output is undefined.')], CALENDAR_INSTANCE_ID).problem;
        expect(problem).toMatchObject({code: 'undefined_metric'});

        const view = emptyCalendarReturnView('unavailable', problem);

        expect(view.state).toBe('unavailable');
        expect(view.problem).toBe(problem);
        expect(view.points).toEqual([]);
        expect(view.contextByDate.size).toBe(0);
    });

    it('returns fresh points and a fresh context map on every call', () => {
        const first = emptyCalendarReturnView();
        const second = emptyCalendarReturnView();

        expect(second).not.toBe(first);
        expect(second.points).not.toBe(first.points);
        expect(second.contextByDate).not.toBe(first.contextByDate);
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
        const view = extractCalendarReturnView([{...requested, instance_id: 'another-instance'}, requested, {...requested, signal_code: 'RISK_ROLLING_VOLATILITY'}], CALENDAR_INSTANCE_ID);

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

// ===========================================================================
// bucketSpanUpTo — the span a coarse point's tooltip header names
// ===========================================================================

describe('bucketSpanUpTo', () => {
    /*
     * A weekly or monthly point is dated by its bucket's last data point (`aggregateLineSeries`,
     * `aggregateOHLCV`), while `bucketEnd` keeps the bucket's theoretical end: the Sunday, the month's last
     * day. In a whole bucket the two are one day; in the open one — the week or month still running, a series
     * that stops inside a period — the point sits on its last data day, and a header spanning to `bucketEnd`
     * names a day with no data, or one still to come.
     *
     * The contract: `bucketSpanUpTo(date, info)` is the span up to the point's own day. When
     * `info.bucketStart <= date < info.bucketEnd` (ISO string order) it is `{bucketStart, bucketEnd: date}`;
     * otherwise `info` as it is — a whole bucket (the point on its end), a date outside the bucket, or no day
     * at all. Pure: the bucket it is given is left untouched.
     */

    /** The ISO week of Monday 11 March 2024, Sunday 17 included. */
    const WEEK: BucketInfo = {bucketStart: '2024-03-11', bucketEnd: '2024-03-17'};
    /** March 2024, the 31st included. */
    const MONTH: BucketInfo = {bucketStart: '2024-03-01', bucketEnd: '2024-03-31'};

    /** The helper, once a barrier has proved `priceChartHelpers` exports it, next to `getBucketInfo`. */
    function spanUpTo(date: string, info: BucketInfo): BucketInfo {
        expect(bucketSpanUpTo, 'barrier: priceChartHelpers exports bucketSpanUpTo').toBeTypeOf('function');
        return bucketSpanUpTo(date, info);
    }

    it.each([
        {name: 'open week, last data on Wed 13', date: '2024-03-13', info: WEEK, span: {bucketStart: '2024-03-11', bucketEnd: '2024-03-13'}},
        {name: 'open month, last data on the 13th', date: '2024-03-13', info: MONTH, span: {bucketStart: '2024-03-01', bucketEnd: '2024-03-13'}},
        {name: 'point on its first day: one day', date: '2024-03-11', info: WEEK, span: {bucketStart: '2024-03-11', bucketEnd: '2024-03-11'}},
    ])('ends the span on the point’s own day — $name', ({date, info, span}) => {
        expect(spanUpTo(date, info)).toEqual(span);
    });

    it.each([
        {name: 'whole week, point on Sunday 17', date: '2024-03-17', info: WEEK},
        {name: 'whole month, point on the 31st', date: '2024-03-31', info: MONTH},
        {name: 'a date before the bucket', date: '2024-03-10', info: WEEK},
        {name: 'a date after the bucket', date: '2024-03-18', info: WEEK},
        {name: 'no day at all', date: '', info: WEEK},
    ])('keeps the bucket as it is — $name', ({date, info}) => {
        expect(spanUpTo(date, info)).toEqual(info);
    });

    it('leaves the bucket it is given untouched', () => {
        const info: BucketInfo = {...WEEK};

        spanUpTo('2024-03-13', info);

        expect(info, 'bucketSpanUpTo mutated the bucket it was given').toEqual(WEEK);
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

/** Every calendar day from `start` to `end`, both included: the calendar-filled series the asset and FX pages chart. */
function calendarDays(start: string, end: string): string[] {
    const days: string[] = [];
    const last = Date.parse(`${end}T00:00:00Z`);
    for (let time = Date.parse(`${start}T00:00:00Z`); time <= last; time += 86_400_000) {
        days.push(new Date(time).toISOString().slice(0, 10));
    }
    return days;
}

/**
 * The scatter context PriceChartFull builds at a coarse resolution, from the real aggregation: the
 * main line through `aggregateLineSeries`, overlays through `downsampleRenderedSignal` (keyed by the
 * main line's render dates). So a partial bucket renders at its last data point, as on screen.
 */
function aggregatedScatterCtx(daily: LineDataPoint[], resolution: ChartResolution, overlays: RenderedSignal[] = []): EventScatterContext {
    const resolvedLineData = aggregateLineSeries(daily, resolution);
    const dates = resolvedLineData.map((point) => point.date);
    const overlayDataByLabel = new Map<string, Map<string, number>>();
    for (const overlay of overlays) {
        const downsampled = downsampleRenderedSignal(overlay, resolution, resolvedLineData);
        if (downsampled.data.length > 0) overlayDataByLabel.set(downsampled.label, new Map(downsampled.data.map((point) => [point.date, point.value])));
    }
    return {
        dateIndexMap: new Map(dates.map((date, index) => [date, index])),
        resolvedLineData,
        overlayDataByLabel,
        bucketInfoByDate: new Map(dates.map((date, index) => [date, getBucketInfo(resolvedLineData[index], resolution)])),
        baseColor: '#123456',
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

    // R-5 (lot 51): an event bucket is keyed by its theoretical bucket end, while the aggregated line
    // renders each bucket at its last data point. On a calendar-filled series a full bucket's two dates
    // coincide; the last, partial one's never do (the default range ends today), and its markers vanished.

    it('places an event of the last, partial week on the bar that week renders at (R-5, lot 51)', () => {
        const ctx = aggregatedScatterCtx(dailyRun(calendarDays('2024-01-01', '2024-01-10')), 'weekly');
        // Precondition: the open week (Mon 01-08..Wed 01-10) renders at 01-10; its bucket end, Sun 01-14, is no axis date.
        expect([...ctx.dateIndexMap.keys()]).toEqual(['2024-01-07', '2024-01-10']);
        const dividend = evm('2024-01-09', 'DIVIDEND');
        const groups = buildEventScatterGroups([dividend], 'weekly', ctx);
        expect(groups, 'the marker of the open week vanished').toHaveLength(1);
        expect(groups[0].points).toEqual([{value: ['2024-01-10', 10], markers: [dividend], bucketInfo: {bucketStart: '2024-01-08', bucketEnd: '2024-01-14'}, bucketValue: 10}]);
    });

    it('places an event of the current, partial month on the bar that month renders at, beside a full month (R-5, lot 51)', () => {
        const ctx = aggregatedScatterCtx(dailyRun(calendarDays('2024-01-01', '2024-02-13')), 'monthly');
        // Precondition: January renders at its bucket end; the open February at its last data point, not at 02-29.
        expect([...ctx.dateIndexMap.keys()]).toEqual(['2024-01-31', '2024-02-13']);
        const january = evm('2024-01-15', 'DIVIDEND');
        const february = evm('2024-02-10', 'DIVIDEND');
        const groups = buildEventScatterGroups([january, february], 'monthly', ctx);
        expect(groups).toHaveLength(1);
        const pointAt = (date: string) => groups[0].points.find((point) => point.value[0] === date);
        // Guard: a full month renders at its bucket end, so its marker has always been placed.
        expect(pointAt('2024-01-31')).toEqual({value: ['2024-01-31', 31], markers: [january], bucketInfo: {bucketStart: '2024-01-01', bucketEnd: '2024-01-31'}, bucketValue: 31});
        expect(pointAt('2024-02-13'), 'the marker of the open month vanished').toEqual({value: ['2024-02-13', 44], markers: [february], bucketInfo: {bucketStart: '2024-02-01', bucketEnd: '2024-02-29'}, bucketValue: 44});
        expect(groups[0].points).toHaveLength(2);
    });

    it('places a comparison event of the open week on its overlay, at the bar that week renders at (R-5, lot 51)', () => {
        // The FX page form: the pair has no events of its own, only those of the comparison asset.
        const beta: RenderedSignal = {id: 'beta', label: 'Beta', data: calendarDays('2024-01-01', '2024-01-10').map((date, index) => pt(date, (index + 1) * 100)), color: '#ff0000', lineWidth: 1, lineType: 'solid', markerStart: null, markerEnd: null, aggregationProfile: 'last_with_range'};
        const ctx = aggregatedScatterCtx(dailyRun(calendarDays('2024-01-01', '2024-01-10')), 'weekly', [beta]);
        // Precondition: the downsampled overlay is keyed by the main line's render dates, with values of its own.
        expect(ctx.overlayDataByLabel.get('Beta')).toEqual(
            new Map([
                ['2024-01-07', 700],
                ['2024-01-10', 1000],
            ]),
        );
        const event = evm('2024-01-08', 'DIVIDEND', {assetLabel: 'Beta', signalColor: '#ff0000'});
        const groups = buildEventScatterGroups([event], 'weekly', ctx);
        expect(groups, 'the comparison marker of the open week vanished').toHaveLength(1);
        expect(groups[0]).toMatchObject({label: 'Beta DIVIDEND', color: '#ff0000', eventType: 'DIVIDEND'});
        // On the overlay (1000), not on the main line (10).
        expect(groups[0].points).toEqual([{value: ['2024-01-10', 1000], markers: [event], bucketInfo: {bucketStart: '2024-01-08', bucketEnd: '2024-01-14'}, bucketValue: 1000}]);
    });

    it('shows an event dated after the last data point on the bar of its open week, not one of a later week (R-5, lot 51)', () => {
        // A bar stands for its whole period: the first partial bucket already carries events dated
        // before its first data point, so the last one carries those dated after its last.
        const ctx = aggregatedScatterCtx(dailyRun(calendarDays('2024-01-01', '2024-01-10')), 'weekly');
        expect([...ctx.dateIndexMap.keys()]).toEqual(['2024-01-07', '2024-01-10']);
        const friday = evm('2024-01-12', 'DIVIDEND');
        const nextMonday = evm('2024-01-15', 'DIVIDEND');
        const groups = buildEventScatterGroups([friday, nextMonday], 'weekly', ctx);
        expect(groups, 'the marker of the open week vanished').toHaveLength(1);
        // Guard: a week with no data point renders no bar, so its event stays off the chart (as off-axis days do).
        expect(groups[0].points).toEqual([{value: ['2024-01-10', 10], markers: [friday], bucketInfo: {bucketStart: '2024-01-08', bucketEnd: '2024-01-14'}, bucketValue: 10}]);
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

    it('exactly 0 counts as non-negative: green, and no sign (M-18)', () => {
        const html = buildDeltaHtml(0, 0, true);
        expect(html).toContain('#10b981');
        // Why (re-pin, M-18 CP2): the delta goes through `formatPercent`, whose rule (CP1) is that a zero
        // is not a gain: `(Δ +0.00%)` becomes `(Δ 0.00%)`. The colour is unchanged.
        expect(html).toContain('(Δ 0.00%)');
        expect(html).not.toContain('+');
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

    it('reports no relative delta when the first value is 0: the move is unknown, not 0% (J-44, N65)', () => {
        const html = buildDeltaHtml(10, 0, false);
        // Red (J-44, N65): a change measured from a start of 0 has no percentage, so the relative delta
        // reads «—» (U+2014), as the chart ruler's Δ% does since CP-14b (`changePct` in MeasureSignal.ts,
        // the one copy of the rule). This test pinned `(Δ +10.0000 / 0.00%)` before — re-pinned by M-18
        // CP2 for the zero's missing `+` — because the old code answers the division by zero with 0
        // (`firstValue !== 0 ? … : 0`): a flat move that never happened. The absolute delta keeps its `+`:
        // it is a gain.
        expect(html).toContain('(Δ +10.0000 / —)');
    });

    it('colours a fall from a first value of 0 by the absolute delta: red, with no relative delta (J-44, N65)', () => {
        const html = buildDeltaHtml(-10, 0, false);
        // Red (J-44, N65): `(Δ -10.0000 / —)`. Before: `(Δ -10.0000 / 0.00%)`, the same 0 % as above. The red
        // is already right today and must survive the change: with no percentage left, the sign of the
        // absolute delta alone decides the colour.
        expect(html).toContain('#ef4444');
        expect(html).toContain('(Δ -10.0000 / —)');
    });
});

// ===========================================================================
// buildStaleTooltipHtml — the staleness warning line(s), in the caller's warning colour
// ===========================================================================

describe('buildStaleTooltipHtml', () => {
    /** The caller's warning colour — in the product the warning role, `chartNeutrals().tooltip.staleWarning` — one no table holds. */
    const WARNING = '#a1b2c3';

    it('emits nothing when the point is not stale', () => {
        expect(buildStaleTooltipHtml(undefined, undefined, WARNING)).toBe('');
    });

    it('emits a single price-stale line when FX is fresh', () => {
        const html = buildStaleTooltipHtml(3, 0, WARNING);
        expect(html).toContain('⚠');
        expect(html).toContain('Stale: 3d');
        // Only one warning line.
        expect(html.match(/⚠/g)).toHaveLength(1);
    });

    it('adds a second line when the FX rate is itself stale', () => {
        const html = buildStaleTooltipHtml(3, 5, WARNING);
        expect(html).toContain('Stale: 3d');
        expect(html).toContain('FX rate: 5d old');
        expect(html.match(/⚠/g)).toHaveLength(2);
    });

    it('substitutes {days} into a provided (translated) template', () => {
        const html = buildStaleTooltipHtml(4, 0, WARNING, 'Vecchio: {days}g');
        expect(html).toContain('Vecchio: 4g');
        expect(html).not.toContain('Stale:');
    });

    it('substitutes {days} into both provided templates when FX is stale', () => {
        const html = buildStaleTooltipHtml(4, 7, WARNING, 'P {days}', 'FX {days}');
        expect(html).toContain('P 4');
        expect(html).toContain('FX 7');
    });

    it("draws every warning line in the caller's colour, and still emits nothing when the point is not stale", () => {
        const cases = {
            'price only': buildStaleTooltipHtml(3, 0, WARNING),
            'price and FX': buildStaleTooltipHtml(3, 5, WARNING),
            'translated templates': buildStaleTooltipHtml(4, 7, WARNING, 'P {days}', 'FX {days}'),
        };
        for (const [name, html] of Object.entries(cases)) {
            const lines = html.match(/⚠/g)?.length ?? 0;
            expect(lines, `${name} barrier: a warning line was emitted, so the colour count is about something`).toBeGreaterThan(0);
            expect(html.split(`color:${WARNING}`).length - 1, `${name}: a warning line in another colour than the caller's — a colour of its own ignores the theme the caller read`).toBe(lines);
        }
        expect(buildStaleTooltipHtml(undefined, undefined, WARNING), 'a colour handed over must not make a line out of nothing').toBe('');
        expect(buildStaleTooltipHtml(undefined, 5, WARNING), 'a stale FX rate alone is no stale point: no line, in any colour').toBe('');
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

// ===========================================================================
// splitGhostLabel — the ghost label's name and currency, apart and uncut (K step 16, item 1)
// ===========================================================================

/**
 * The tooltip's ghost row — the asset in its original currency, while a conversion is active — reads
 * `💱 Name (🇺🇸 USD)`. Today `formatTruncatedGhostLabel` cuts the name at 30 characters in JS and keeps the currency
 * whole. In the fitted tooltip (`buildFittedTooltipRow`) the label item's CSS ellipsis does the cut, and the currency
 * travels with the value, in the item that never shrinks: the tooltip needs the two parts apart, and the name whole.
 * Same regex as `formatTruncatedGhostLabel` (`^💱\s*(.+?)\s*(\([^)]+\))$`), so both agree on what a ghost label is.
 */
describe('splitGhostLabel — the name and the currency apart, nothing cut (K step 16, item 1)', () => {
    it('splits `💱 Name (flag CUR)` into the 💱 name and the currency parenthetical', () => {
        expect(splitGhostLabel('💱 Some Name (🇺🇸 USD)')).toEqual({name: '💱 Some Name', currency: '(🇺🇸 USD)'});
    });

    it.each([
        {why: 'a plain name', label: 'Apple Inc.'},
        {why: 'a 💱 name with no parenthetical', label: '💱 Apple'},
        {why: 'a 40-character name, not cut either', label: 'Z'.repeat(40)},
    ])('returns a label with no currency parenthetical unchanged, with no currency — $why', ({label}) => {
        expect(splitGhostLabel(label)).toEqual({name: label, currency: null});
    });

    it('never truncates the name — the tooltip CSS does, where formatTruncatedGhostLabel cut it at 30 characters', () => {
        const longName = 'A'.repeat(40);
        expect(splitGhostLabel(`💱 ${longName} (🇺🇸 USD)`)).toEqual({name: `💱 ${longName}`, currency: '(🇺🇸 USD)'});
    });

    it("keeps the name's own parentheses in the name: only the last parenthetical is the currency", () => {
        expect(splitGhostLabel('💱 iShares Core MSCI World (Acc) (🇺🇸 USD)')).toEqual({name: '💱 iShares Core MSCI World (Acc)', currency: '(🇺🇸 USD)'});
    });

    it.each(['💱 Apple (🇺🇸 USD)', '💱 iShares World (Acc) (🇪🇺 EUR)', '💱 Apple', 'Apple (🇺🇸 USD)', 'Apple'])('agrees with formatTruncatedGhostLabel on what a ghost label is: rejoined, a label too short to cut reads the same — %s', (label) => {
        const {name, currency} = splitGhostLabel(label);
        expect(currency === null ? name : `${name} ${currency}`).toBe(formatTruncatedGhostLabel(label));
    });
});

/**
 * M-18 CP2: the tooltip delta and the month label in the interface language.
 *
 * `buildDeltaHtml` writes the `(Δ …)` suffix of the main tooltip row with `toFixed`, so a French reader
 * gets `(Δ +2.50%)` beside amounts written `1 234,50`; `formatMonthLabel`, called without a locale — as
 * PriceChartFull's tooltip header calls it — writes the month in the machine's language instead of the
 * interface's. Every figure follows the interface language (the developer's decision M-18, 2026-10-12):
 *
 *   - percentage view: `(Δ ${formatPercent(value)})`;
 *   - absolute view: `(Δ ${formatFixed(deltaAbs, 4, {signed: true})} / ${formatPercent(deltaPct)})`, with «—» for
 *     the relative part when the first value is 0 (N65, J-44: the move is unknown, not 0 %);
 *   - the colours stay derived from the sign, a zero green;
 *   - `formatMonthLabel(date)` defaults to the interface locale; an explicit locale still wins.
 *
 * Expectations come from `formatPercent`/`formatFixed` and `Intl.DateTimeFormat` given an explicit
 * locale, never typed; each case checks that the language under test differs from English, so a runtime
 * without its data cannot make the comparison vacuous.
 */
describe('buildDeltaHtml and formatMonthLabel in the interface language (M-18)', () => {
    const FR = {locale: 'fr'} as const;
    const GREEN = '#10b981';
    const RED = '#ef4444';

    /** `value` as JSON with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
    function spelled(value: unknown): string {
        return JSON.stringify(value).replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
    }

    /** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
    async function uiLanguage(lang: 'en' | 'it' | 'fr'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    /** What a delta suffix shows: the colour it is painted in and its `(Δ …)` text. */
    function deltaOf(html: string): {color: string; text: string} {
        const match = /color:\s*(#[0-9a-f]{3,8})[^>]*>([^<]*)</i.exec(html);
        return {color: match?.[1] ?? `(no colour in ${html})`, text: match?.[2] ?? `(no text in ${html})`};
    }

    /** The month as `Intl` writes it in `locale`, with the options and the UTC anchor `formatMonthLabel` uses. */
    function monthIn(locale: string, date: string): string {
        return new Intl.DateTimeFormat(locale, {month: 'long', year: 'numeric', timeZone: 'UTC'}).format(new Date(`${date}T00:00:00Z`));
    }

    it('French UI, percentage view: the delta is a French percentage — `+` on a gain, none on a zero — in the colour of its sign', async () => {
        await uiLanguage('fr');
        const cases = [
            {value: 2.5, color: GREEN},
            {value: -2.5, color: RED},
            {value: 0, color: GREEN},
            {value: 1234.5, color: GREEN},
        ];
        const expected = cases.map(({value, color}) => ({color, text: `(Δ ${formatPercent(value, FR)})`}));
        // Control: this runtime carries French data, so the French text is not today's English one.
        expect(expected[0].text, 'French differs from English').not.toBe('(Δ +2.50%)');

        expect(
            cases.map(({value}) => deltaOf(buildDeltaHtml(value, 0, true))),
            spelled(expected),
        ).toEqual(expected);
    });

    it('French UI, absolute view: the absolute delta with four decimals and its sign, the relative one as a French percentage', async () => {
        await uiLanguage('fr');
        const cases = [
            {value: 110, first: 100, color: GREEN},
            {value: 90, first: 100, color: RED},
            {value: 10, first: 0, color: GREEN},
            {value: 2234.5, first: 1000, color: GREEN},
        ];
        // The two deltas as the helper computes them: the difference, and its share of the first value
        // (none when the first value is 0, written «—»: the move is unknown, not 0 %).
        // Red (J-44, N65) on the third case, {value: 10, first: 0}. Before: the share was 0, so the helper
        // wrote `formatPercent(0, FR)`, a French 0 % for a move that has no percentage. The other three
        // cases keep their percentage, computed as before.
        const expected = cases.map(({value, first, color}) => {
            const deltaPct = first !== 0 ? ((value - first) / first) * 100 : null;
            return {color, text: `(Δ ${formatFixed(value - first, 4, {signed: true, ...FR})} / ${deltaPct === null ? '—' : formatPercent(deltaPct, FR)})`};
        });
        expect(expected[0].text, 'French differs from English').not.toBe('(Δ +10.0000 / +10.00%)');

        expect(
            cases.map(({value, first}) => deltaOf(buildDeltaHtml(value, first, false))),
            spelled(expected),
        ).toEqual(expected);
    });

    it('without a locale, the month label is written in the interface language — French, then Italian — not the machine’s', async () => {
        const written: Record<string, string> = {};
        for (const lang of ['fr', 'it'] as const) {
            await uiLanguage(lang);
            written[lang] = formatMonthLabel('2024-01-15');
        }
        const expected = {fr: monthIn('fr', '2024-01-15'), it: monthIn('it', '2024-01-15')};
        // Control: both languages name the month differently from English.
        expect(Object.values(expected), 'French and Italian differ from English').not.toContain(monthIn('en-US', '2024-01-15'));

        expect(written).toEqual(expected);
    });

    it('English UI on an en-US browser: the month label without a locale is today’s English; an explicit locale still wins in French', async () => {
        await uiLanguage('en');
        expect(formatMonthLabel('2024-01-15')).toBe('January 2024');

        await uiLanguage('fr');
        expect(formatMonthLabel('2024-01-15', 'de-DE')).toBe('Januar 2024');
    });
});
