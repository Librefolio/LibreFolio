import {describe, expect, it} from 'vitest';

import {renderBackendSignalResult} from '../backendRenderer';
import {backendSignalSchemas, type BackendSignalResult} from '../backendTypes';
import type {SignalConfig} from '../ChartSignal';

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

        expect(outcome.signals.map((signal) => signal.color)).toEqual(['#3b82f6', '#16a34a', '#dc2626']);
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
        expect(outcome.signals[2]).toMatchObject({color: '#dc2626', lineWidth: 2, lineType: 'solid'});
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
