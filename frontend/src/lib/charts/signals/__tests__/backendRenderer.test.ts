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

    it('preserves missing points and maps reference levels/value regions', () => {
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
        expect(rendered.referenceLevels).toEqual([
            {
                key: 'overbought',
                label: 'Overbought',
                semantic: 'overbought',
                value: 70,
            },
        ]);
        expect(rendered.valueRegions?.[0]).toMatchObject({
            lower: 70,
            semantic: 'overbought',
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
