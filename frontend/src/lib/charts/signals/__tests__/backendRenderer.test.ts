import {describe, expect, it} from 'vitest';

import {secondaryAxisSettingsKey} from '$lib/components/charts/chartCoreHelpers';

import {renderBackendSignalResult as renderBackendSignalResultRaw} from '../backendRenderer';
import {backendSignalSchemas, type BackendSignalCatalogDefinition, type BackendSignalResult} from '../backendTypes';
import {mapBackendSignalDefinition} from '../catalogMapper';
import type {SignalConfig, SignalDefinition} from '../ChartSignal';
import {createSignalConfig} from '../registry';

const config: SignalConfig = {
    id: 'signal-instance',
    signalType: 'backend-signal',
    params: {},
    style: {
        color: '#3b82f6',
        lineWidth: 2,
        lineType: 'solid',
        markerStart: null,
        markerEnd: null,
    },
};

const baseData = [
    {date: '2026-07-22', value: 100},
    {date: '2026-07-23', value: 110},
];

const definition: SignalDefinition = {
    type: 'backend-signal',
    displayName: 'Backend signal',
    icon: 'activity',
    category: 'indicator',
    paramDescriptors: [],
    source: 'backend',
    visualComponents: [
        ...['macd', 'signal', 'histogram', 'ppo', 'adx', 'plus_di', 'minus_di', 'up', 'down', 'rsi'].map((key) => ({
            key,
            labelKey: `signals.${key}`,
            kind: key === 'histogram' ? ('bar' as const) : ('line' as const),
            aggregationProfile: 'last_with_range' as const,
            style: {
                colorRole: 'primary' as const,
                lineWidthDelta: 0,
                opacity: 1,
                fillOpacity: 0.2,
            },
            fullyPartitioned: false,
        })),
        {
            key: 'bands',
            labelKey: 'signals.bands',
            kind: 'band',
            aggregationProfile: 'band_envelope',
            style: {
                colorRole: 'primary',
                lineWidthDelta: 0,
                opacity: 1,
                fillOpacity: 0.2,
            },
            fullyPartitioned: false,
        },
        {
            key: 'drawdown',
            labelKey: 'signals.drawdown',
            kind: 'area',
            aggregationProfile: 'min_with_range',
            style: {
                colorRole: 'negative',
                lineWidthDelta: 0,
                opacity: 1,
                fillOpacity: 0.2,
            },
            fullyPartitioned: false,
        },
    ],
};

function renderBackendSignalResult(result: BackendSignalResult, signalConfig: SignalConfig, options: Omit<Parameters<typeof renderBackendSignalResultRaw>[2], 'definition'>) {
    return renderBackendSignalResultRaw(result, signalConfig, {...options, definition});
}

function resultWithSeries(signalCode: string, series: unknown[]): BackendSignalResult {
    return backendSignalSchemas.result.parse({
        instance_id: config.id,
        signal_code: signalCode,
        status: 'partial',
        series,
        warnings: [
            {
                code: 'incomplete_warmup',
                message: 'Warm-up incomplete',
            },
        ],
    });
}

function lineSeries(key: string, axisKey: string = 'momentum', values: Array<number | null> = [1, 2]) {
    return {
        key,
        label_key: `signals.${key}`,
        semantic_id: `test.${key.replaceAll('_', '.')}`,
        semantic_description: `Canonical test output for ${key}.`,
        unit: 'index',
        axis: {
            key: axisKey,
            role: 'independent',
        },
        kind: 'line',
        points: values.map((value, index) => ({
            date: baseData[index].date,
            value,
        })),
    };
}

function barSeries(key: string, axisKey: string = 'momentum') {
    return {
        ...lineSeries(key, axisKey),
        kind: 'bar',
    };
}

function areaSeries(key: string, axisKey: string = 'risk') {
    return {
        ...lineSeries(key, axisKey, [0, -12]),
        kind: 'area',
        style: {
            color_role: 'negative',
            fill_opacity: 0.2,
        },
    };
}

function bandSeries(key: string, axisKey: string = 'price') {
    return {
        key,
        label_key: `signals.${key}`,
        semantic_id: `test.${key.replaceAll('_', '.')}`,
        semantic_description: `Canonical test band output for ${key}.`,
        unit: 'price',
        axis: {
            key: axisKey,
            role: 'price',
        },
        view_transform: 'base_percentage',
        kind: 'band',
        points: [
            {
                date: baseData[0].date,
                lower: 90,
                middle: 100,
                upper: 110,
            },
            {
                date: baseData[1].date,
                lower: 99,
                middle: 110,
                upper: 121,
            },
        ],
    };
}

describe('canonical backend signal renderer', () => {
    it('renders MACD as two lines plus one flat histogram series', () => {
        const outcome = renderBackendSignalResult(resultWithSeries('MACD', [lineSeries('macd', 'macd'), lineSeries('signal', 'macd'), barSeries('histogram', 'macd')]), config, {
            baseData,
            viewMode: 'absolute',
        });

        expect(outcome.signals.map((signal) => signal.seriesType)).toEqual(['line', 'line', 'bar']);
        expect(outcome.signals.map((signal) => signal.axisKey)).toEqual(['macd', 'macd', 'macd']);
        expect(outcome.signals[1].lineType).toBe('dashed');
        expect(outcome.warnings).toEqual(['Warm-up incomplete']);
    });

    it('renders Bollinger and Donchian bands with base percentage transform', () => {
        for (const signalCode of ['BOLLINGER', 'DONCHIAN']) {
            const outcome = renderBackendSignalResult(resultWithSeries(signalCode, [bandSeries('bands')]), config, {
                baseData,
                viewMode: 'percentage',
            });

            const rendered = outcome.signals[0];

            expect(rendered.seriesType).toBe('band');
            expect(rendered.data.map((point) => point.value)).toEqual([0, 10]);
            expect(rendered.bandData).toEqual({
                lower: [-10, -1],
                middle: [0, 10],
                upper: [10, 21],
            });
        }
    });

    it('renders AREA output with plugin-owned MIN aggregation and fill opacity', () => {
        const rendered = renderBackendSignalResult(resultWithSeries('RISK_DRAWDOWN', [areaSeries('drawdown')]), config, {
            baseData,
            viewMode: 'absolute',
        }).signals[0];

        expect(rendered).toMatchObject({
            seriesType: 'area',
            aggregationProfile: 'min_with_range',
            fillOpacity: 0.2,
            color: '#c82838',
        });
    });

    it.each([
        ['PPO', [lineSeries('ppo', 'ppo'), lineSeries('signal', 'ppo'), barSeries('histogram', 'ppo')], 3],
        ['ADX', [lineSeries('adx', 'adx'), lineSeries('plus_di', 'adx'), lineSeries('minus_di', 'adx')], 3],
        ['AROON', [lineSeries('up', 'aroon'), lineSeries('down', 'aroon')], 2],
    ])('renders %s composite output without a signal-code switch', (signalCode, series, expectedCount) => {
        const outcome = renderBackendSignalResult(resultWithSeries(signalCode, series), config, {
            baseData,
            viewMode: 'absolute',
        });
        expect(outcome.signals).toHaveLength(expectedCount);
    });

    it('applies plugin-owned styles to ADX components', () => {
        const adx = lineSeries('adx', 'adx');
        const plusDi = lineSeries('plus_di', 'adx');
        const minusDi = lineSeries('minus_di', 'adx');
        Object.assign(adx, {style: {color_role: 'primary', line_pattern: 'solid', width_delta: 1, opacity: 1}});
        Object.assign(plusDi, {style: {color_role: 'positive', line_pattern: 'solid', width_delta: 0, opacity: 1}});
        Object.assign(minusDi, {style: {color_role: 'negative', line_pattern: 'solid', width_delta: 0, opacity: 1}});

        const outcome = renderBackendSignalResult(resultWithSeries('ADX', [adx, plusDi, minusDi]), config, {
            baseData,
            viewMode: 'absolute',
        });

        expect(outcome.signals.map((signal) => signal.color)).toEqual(['#3b82f6', '#18794e', '#c82838']);
        expect(outcome.signals.map((signal) => signal.lineType)).toEqual(['solid', 'solid', 'solid']);
        expect(outcome.signals.map((signal) => signal.lineWidth)).toEqual([3, 2, 2]);
    });

    it('applies per-component style overrides without changing sibling outputs', () => {
        const adx = lineSeries('adx', 'adx');
        const plusDi = lineSeries('plus_di', 'adx');
        const minusDi = lineSeries('minus_di', 'adx');
        Object.assign(adx, {style: {color_role: 'primary', line_pattern: 'solid', width_delta: 1, opacity: 1}});
        Object.assign(plusDi, {style: {color_role: 'positive', line_pattern: 'solid', width_delta: 0, opacity: 1}});
        Object.assign(minusDi, {style: {color_role: 'negative', line_pattern: 'solid', width_delta: 0, opacity: 1}});
        const customizedConfig: SignalConfig = {
            ...config,
            componentStyles: {
                plus_di: {
                    color: '#7c3aed',
                    lineWidth: 4,
                    lineType: 'dotted',
                    markerStart: 'circle',
                    markerEnd: 'diamond',
                },
            },
        };

        const outcome = renderBackendSignalResult(resultWithSeries('ADX', [adx, plusDi, minusDi]), customizedConfig, {
            baseData,
            viewMode: 'absolute',
        });

        expect(outcome.signals[0]).toMatchObject({color: '#3b82f6', lineWidth: 3, lineType: 'solid'});
        expect(outcome.signals[1]).toMatchObject({
            color: '#7c3aed',
            lineWidth: 4,
            lineType: 'dotted',
            markerStart: 'circle',
            markerEnd: 'diamond',
        });
        expect(outcome.signals[2]).toMatchObject({color: '#c82838', lineWidth: 2, lineType: 'solid'});
    });

    it('preserves axis metadata and applies backend value-region styling', () => {
        const rsi = lineSeries('rsi', 'rsi', [null, 72]);
        Object.assign(rsi, {
            axis: {
                key: 'rsi',
                role: 'independent',
                minimum: 0,
                maximum: 100,
            },
            reference_levels: [
                {
                    key: 'overbought',
                    label_key: 'signals.rsi.overbought',
                    semantic: 'overbought',
                    value: 70,
                },
            ],
            value_regions: [
                {
                    key: 'overbought',
                    label_key: 'signals.rsi.overboughtRegion',
                    semantic: 'overbought',
                    lower: 70,
                    line_style: {
                        pattern: 'solid',
                        width_delta: 1,
                    },
                },
            ],
        });

        const outcome = renderBackendSignalResult(resultWithSeries('RSI', [rsi]), config, {
            baseData,
            viewMode: 'absolute',
            translate: (key) => (key === 'signals.rsi.overbought' ? 'Overbought' : key),
        });
        const rendered = outcome.signals[0];

        expect(rendered.data).toEqual([{date: '2026-07-23', value: 72}]);
        expect(rendered.axisMinimum).toBe(0);
        expect(rendered.axisMaximum).toBe(100);
        expect(rendered.lineType).toBe('solid');
        expect(rendered.lineWidth).toBe(3);
        expect(rendered.referenceLevels).toBeUndefined();
        expect(rendered.valueRegions).toBeUndefined();
    });

    it('derives dashed and solid time slices from backend value-region rules', () => {
        const rsi = {
            ...lineSeries('rsi', 'rsi'),
            points: [
                {date: '2026-07-20', value: 20},
                {date: '2026-07-21', value: 40},
                {date: '2026-07-22', value: 80},
            ],
            value_regions: [
                {
                    key: 'oversold',
                    label_key: 'signals.rsi.oversoldRegion',
                    semantic: 'oversold',
                    upper: 30,
                    include_lower: true,
                    include_upper: false,
                    line_style: {pattern: 'solid', width_delta: 1},
                },
                {
                    key: 'neutral',
                    label_key: 'signals.rsi.neutralRegion',
                    semantic: 'neutral',
                    lower: 30,
                    upper: 70,
                    include_lower: true,
                    include_upper: true,
                    line_style: {pattern: 'dashed', width_delta: 0},
                },
                {
                    key: 'overbought',
                    label_key: 'signals.rsi.overboughtRegion',
                    semantic: 'overbought',
                    lower: 70,
                    include_lower: false,
                    include_upper: false,
                    line_style: {pattern: 'solid', width_delta: 1},
                },
            ],
        };

        const outcome = renderBackendSignalResult(resultWithSeries('RSI', [rsi]), config, {
            baseData,
            viewMode: 'absolute',
        });

        expect(outcome.signals.map((signal) => signal.lineType)).toEqual(['solid', 'dashed', 'solid']);
        expect(outcome.signals.map((signal) => signal.lineWidth)).toEqual([3, 2, 3]);
        expect(outcome.signals.map((signal) => signal.label)).toEqual(['RSI', 'RSI', 'RSI']);
        expect(outcome.signals[1].data.map((point) => point.date)).toEqual(['2026-07-20', '2026-07-21']);
    });

    it('applies a per-partition override only to the matching time slices', () => {
        const rsi = {
            ...lineSeries('rsi', 'rsi'),
            points: [
                {date: '2026-07-20', value: 20},
                {date: '2026-07-21', value: 40},
                {date: '2026-07-22', value: 80},
            ],
            value_regions: [
                {
                    key: 'oversold',
                    label_key: 'signals.rsi.oversoldRegion',
                    semantic: 'oversold',
                    upper: 30,
                    line_style: {pattern: 'solid', width_delta: 1},
                },
                {
                    key: 'neutral',
                    label_key: 'signals.rsi.neutralRegion',
                    semantic: 'neutral',
                    lower: 30,
                    upper: 70,
                    include_upper: true,
                    line_style: {pattern: 'dashed', width_delta: 0},
                },
                {
                    key: 'overbought',
                    label_key: 'signals.rsi.overboughtRegion',
                    semantic: 'overbought',
                    lower: 70,
                    line_style: {pattern: 'solid', width_delta: 1},
                },
            ],
        };
        const customizedConfig: SignalConfig = {
            ...config,
            partitionStyles: {
                'rsi:neutral': {
                    color: '#ec4899',
                    lineWidth: 4,
                    lineType: 'dotted',
                    markerStart: null,
                    markerEnd: null,
                },
            },
        };

        const outcome = renderBackendSignalResult(resultWithSeries('RSI', [rsi]), customizedConfig, {
            baseData,
            viewMode: 'absolute',
        });

        expect(outcome.signals.map((signal) => signal.color)).toEqual(['#3b82f6', '#ec4899', '#3b82f6']);
        expect(outcome.signals.map((signal) => signal.lineWidth)).toEqual([3, 4, 3]);
        expect(outcome.signals.map((signal) => signal.lineType)).toEqual(['solid', 'dotted', 'solid']);
    });

    it('switches a customized histogram from signed colors to its selected color', () => {
        const histogram = barSeries('histogram', 'macd');
        const customizedConfig: SignalConfig = {
            ...config,
            componentStyles: {
                histogram: {
                    color: '#06b6d4',
                    lineWidth: 2,
                    lineType: 'solid',
                    markerStart: null,
                    markerEnd: null,
                },
            },
        };

        const rendered = renderBackendSignalResult(resultWithSeries('MACD', [histogram]), customizedConfig, {
            baseData,
            viewMode: 'absolute',
        }).signals[0];

        expect(rendered).toMatchObject({
            color: '#06b6d4',
            barColorMode: 'single',
        });
    });

    it('returns explicit failed/unavailable state without chart series', () => {
        const failed = backendSignalSchemas.result.parse({
            instance_id: config.id,
            signal_code: 'EMA',
            status: 'failed',
            error: {
                code: 'compute_error',
                message: 'TA backend failed',
            },
        });

        const outcome = renderBackendSignalResult(failed, config, {
            baseData,
            viewMode: 'absolute',
        });

        expect(outcome.signals).toEqual([]);
        expect(outcome.error).toBe('TA backend failed');
    });
});

/**
 * The calendar Rolling Return as an overlay (workstream J, CP-10a; developer's decision 29: ONE Rolling Return,
 * measured in calendar days).
 *
 * Until decision 29 ASSET_CALENDAR_ROLLING_RETURN was hidden from the catalog and only fed the page's primary
 * calendar mode, which reads its result through `extractCalendarReturnView`. Now the signal tree offers it, so its
 * result also goes through this generic renderer, which had never been handed its shape: points that carry
 * `value: null` with a non-`available` status, and a warning rather than an error when some of them could not be
 * computed. The definition and the config are built the way the app builds them: the catalog entry through the
 * mapper, the config as the tree creates it.
 */
const CALENDAR_SIGNAL_CODE = 'ASSET_CALENDAR_ROLLING_RETURN';
const CALENDAR_OUTPUT_KEY = 'calendar_return';
const CALENDAR_WARNING_MESSAGE = 'One or more calendar-return points are unavailable';

/** What `calendar_rolling_return/plugin.py` publishes: one RISK line in percent, on an independent axis of its own. */
function calendarCatalogEntry(): BackendSignalCatalogDefinition {
    return backendSignalSchemas.catalog.parse({
        signal_code: CALENDAR_SIGNAL_CODE,
        implementation_version: '1.4.0',
        category: 'risk',
        display_name_key: 'signals.riskRollingReturn.name',
        description_key: 'signals.riskRollingReturn.description',
        semantic_id: 'calendar_rolling_return',
        semantic_description: 'Measures price-only return over an exact calendar-day window.',
        icon: '↗️',
        docs_path: 'financial-theory/fundamentals/returns/',
        params_schema: {
            type: 'object',
            additionalProperties: false,
            properties: {
                window_days: {
                    type: 'integer',
                    minimum: 1,
                    default: 30,
                    'x-i18n-key': 'chartSettings.params.window',
                    'x-control-order': 1,
                    'x-suffix': 'days',
                    'x-step': 1,
                    'x-tooltip-key': 'signals.riskRollingReturn.windowTooltip',
                },
            },
        },
        default_params: {window_days: 30},
        input_requirements: {price_fields: ['close'], data_policy: 'allow_partial_contiguous', minimum_coverage: 0},
        output_specs: [
            {
                key: CALENDAR_OUTPUT_KEY,
                label_key: 'signals.riskRollingReturn.output',
                description_key: 'signals.riskRollingReturn.outputDescription',
                semantic_id: 'calendar_rolling_return.value',
                semantic_description: 'Price-only return from the resolved value exactly N calendar days earlier.',
                unit: 'percentage',
                axis: {key: CALENDAR_OUTPUT_KEY, role: 'independent'},
                view_transform: 'none',
                kind: 'line',
                aggregation_profile: 'last_with_range',
                supports_reference_levels: true,
                default_reference_levels: [{key: 'zero', label_key: 'signals.reference.zero', semantic: 'No price-only gain or loss.', value: 0}],
            },
        ],
        compatible_domains: ['asset'],
    });
}

type CalendarPointStatus = 'available' | 'missing_reference' | 'invalid_current_price' | 'invalid_reference_price';

/** One point as the plugin sends it: the return, and why there is one or not. */
function calendarPoint(date: string, value: number | null, status: CalendarPointStatus, referenceTargetDate: string) {
    const referenceResolved = status === 'available' || status === 'invalid_current_price';
    return {
        date,
        value,
        provenance: {
            status,
            reference_target_date: referenceTargetDate,
            current_price_date: date,
            current_price_days_back: 0,
            reference_price_date: referenceResolved ? referenceTargetDate : null,
            reference_price_days_back: referenceResolved ? 0 : null,
        },
    };
}

/**
 * A partial result over five days: three computed returns (one of them exactly 0, which is a value and not a gap)
 * and two that could not be computed, reported by the plugin's UNDEFINED_METRIC_WINDOW warning.
 */
function calendarResult(instanceId: string): BackendSignalResult {
    return backendSignalSchemas.result.parse({
        instance_id: instanceId,
        signal_code: CALENDAR_SIGNAL_CODE,
        status: 'partial',
        series: [
            {
                key: CALENDAR_OUTPUT_KEY,
                label_key: 'signals.riskRollingReturn.output',
                description_key: 'signals.riskRollingReturn.outputDescription',
                semantic_id: 'calendar_rolling_return.value',
                semantic_description: 'Price-only return from the resolved value exactly N calendar days earlier.',
                unit: 'percentage',
                axis: {key: CALENDAR_OUTPUT_KEY, role: 'independent'},
                view_transform: 'none',
                kind: 'line',
                reference_levels: [{key: 'zero', label_key: 'signals.reference.zero', semantic: 'No price-only gain or loss.', value: 0}],
                points: [
                    calendarPoint('2026-07-20', 4.25, 'available', '2026-06-20'),
                    calendarPoint('2026-07-21', null, 'missing_reference', '2026-06-21'),
                    calendarPoint('2026-07-22', 0, 'available', '2026-06-22'),
                    calendarPoint('2026-07-23', null, 'invalid_reference_price', '2026-06-23'),
                    calendarPoint('2026-07-24', -1.5, 'available', '2026-06-24'),
                ],
            },
        ],
        warnings: [
            {
                code: 'undefined_metric_window',
                message: CALENDAR_WARNING_MESSAGE,
                details: {unavailable_points: 2, reasons: {invalid_reference_price: 1, missing_reference: 1}},
            },
        ],
    });
}

describe('calendar Rolling Return as a backend overlay', () => {
    it('maps the published catalog entry to a risk definition whose one component is calendar_return', () => {
        // Premise: the renderer finds each output's component in the definition, and throws without it.
        const calendarDefinition = mapBackendSignalDefinition(calendarCatalogEntry());

        expect(calendarDefinition.type).toBe('asset-calendar-rolling-return');
        expect(calendarDefinition.indicatorGroup).toBe('risk');
        expect(calendarDefinition.compatibleDomains).toEqual(['asset']);
        expect(calendarDefinition.visualComponents?.map((component) => component.key)).toEqual([CALENDAR_OUTPUT_KEY]);
        // The config the tree creates carries the default window, which is what the request sends.
        expect(createSignalConfig(calendarDefinition, 0).params).toEqual({window_days: 30});
    });

    it('breaks the line at each point the backend sent without a value: a gap, never a 0, and an exact 0 stays a value', () => {
        const calendarDefinition = mapBackendSignalDefinition(calendarCatalogEntry());
        const calendarConfig = createSignalConfig(calendarDefinition, 0);
        const result = calendarResult(calendarConfig.id);
        // Premise: the two gaps reach the renderer as null values, each with the status that explains it.
        const [sentSeries] = result.series ?? [];
        if (!sentSeries || sentSeries.kind === 'band') throw new Error('the calendar result must carry one line series');
        const gaps = sentSeries.points.flat().filter((point) => point.value === null);
        expect(gaps.map((point) => ('provenance' in point ? point.provenance.status : 'no provenance'))).toEqual(['missing_reference', 'invalid_reference_price']);

        // Percentage view: the calendar return is already a percentage (`view_transform: none`), so nothing is rebased.
        const outcome = renderBackendSignalResultRaw(result, calendarConfig, {baseData, viewMode: 'percentage', definition: calendarDefinition});

        // One run per stretch between two gaps, in date order (J-21). The exact 0 between the two gaps is a
        // one-point run: a value in the data and the tooltip, joined to neither neighbour, as the page's own
        // calendar comparison lines draw it (`connectNulls: false`).
        expect(outcome.signals.map((rendered) => rendered.data)).toEqual([[{date: '2026-07-20', value: 4.25}], [{date: '2026-07-22', value: 0}], [{date: '2026-07-24', value: -1.5}]]);
        const drawnDates = outcome.signals.flatMap((rendered) => rendered.data.map((point) => point.date));
        expect(drawnDates).not.toContain('2026-07-21');
        expect(drawnDates).not.toContain('2026-07-23');
        const ids = outcome.signals.map((rendered) => rendered.id);
        expect(ids.filter((id) => !id.startsWith(`${calendarConfig.id}:${CALENDAR_OUTPUT_KEY}:`))).toEqual([]);
        expect(new Set(ids).size).toBe(ids.length);
        for (const rendered of outcome.signals) {
            expect(rendered).toMatchObject({seriesType: 'line', unit: 'percentage', aggregationProfile: 'last_with_range'});
        }
        // The zero line is drawn once: the first run carries the reference level, the others do not.
        expect(outcome.signals.map((rendered) => rendered.referenceLevels?.map((level) => [level.key, level.value]))).toEqual([[['zero', 0]], undefined, undefined]);
    });

    it('puts the line on the independent calendar_return axis, the key its saved scale is stored under', () => {
        const calendarDefinition = mapBackendSignalDefinition(calendarCatalogEntry());
        const calendarConfig = createSignalConfig(calendarDefinition, 0);

        const [rendered] = renderBackendSignalResultRaw(calendarResult(calendarConfig.id), calendarConfig, {baseData, viewMode: 'absolute', definition: calendarDefinition}).signals;

        expect(rendered.axisKey).toBe(CALENDAR_OUTPUT_KEY);
        expect(rendered.axisRole).toBe('independent');
        // The key chartSettingsStore's version-3 migration moves a saved `independent:risk_return` scale to.
        expect(secondaryAxisSettingsKey(rendered)).toBe('independent:calendar_return');
    });

    it('passes the UNDEFINED_METRIC_WINDOW warning on, as a warning of a partial result and not as an error', () => {
        const calendarDefinition = mapBackendSignalDefinition(calendarCatalogEntry());
        const calendarConfig = createSignalConfig(calendarDefinition, 0);
        const result = calendarResult(calendarConfig.id);
        // Premise: the only warning of the result is the plugin's own.
        expect(result.warnings?.map((warning) => warning.code)).toEqual(['undefined_metric_window']);

        const outcome = renderBackendSignalResultRaw(result, calendarConfig, {baseData, viewMode: 'absolute', definition: calendarDefinition});

        // The outcome carries a warning's message, not its code.
        expect(outcome.warnings).toEqual([CALENDAR_WARNING_MESSAGE]);
        expect(outcome.status).toBe('partial');
        expect(outcome.error).toBeNull();
        // One run per stretch between the two unavailable days (J-21).
        expect(outcome.signals).toHaveLength(3);
    });
});
