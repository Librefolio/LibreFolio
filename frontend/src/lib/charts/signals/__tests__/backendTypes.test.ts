import {describe, expect, it} from 'vitest';

import {backendSignalSchemas, type BackendSignalBandSeries, type BackendSignalBarSeries, type BackendSignalLineSeries, type BackendSignalResult} from '../backendTypes';

const priceAxis = {
    key: 'price',
    role: 'price' as const,
};

const independentAxis = {
    key: 'momentum',
    role: 'independent' as const,
};

describe('backend signal runtime contracts', () => {
    it('parses a canonical line series', () => {
        const line: BackendSignalLineSeries = backendSignalSchemas.lineSeries.parse({
            key: 'ema',
            label_key: 'signals.ema.output',
            semantic_id: 'trend.ema',
            semantic_description: 'Exponential moving average of the observed close series.',
            unit: 'price',
            axis: priceAxis,
            kind: 'line',
            points: [{date: '2026-07-23', value: 101.5}],
        });

        expect(line.kind).toBe('line');
    });

    it('parses a canonical bar series', () => {
        const bar: BackendSignalBarSeries = backendSignalSchemas.barSeries.parse({
            key: 'histogram',
            label_key: 'signals.macd.histogram',
            semantic_id: 'momentum.macd.histogram',
            semantic_description: 'Difference between the MACD and signal lines.',
            unit: 'price',
            axis: independentAxis,
            kind: 'bar',
            points: [{date: '2026-07-23', value: -0.5}],
        });

        expect(bar.kind).toBe('bar');
    });

    it('parses a canonical band series', () => {
        const band: BackendSignalBandSeries = backendSignalSchemas.bandSeries.parse({
            key: 'bands',
            label_key: 'signals.bollinger.bands',
            semantic_id: 'volatility.bollinger.bands',
            semantic_description: 'Bollinger lower, middle, and upper price bands.',
            unit: 'price',
            axis: priceAxis,
            kind: 'band',
            points: [
                {
                    date: '2026-07-23',
                    lower: 95,
                    middle: 100,
                    upper: 105,
                },
            ],
        });

        expect(band.kind).toBe('band');
    });

    it('parses a flat composite result with discriminated series', () => {
        const result: BackendSignalResult = backendSignalSchemas.result.parse({
            instance_id: 'macd-1',
            signal_code: 'MACD',
            status: 'partial',
            series: [
                {
                    key: 'macd',
                    label_key: 'signals.macd.line',
                    semantic_id: 'momentum.macd.line',
                    semantic_description: 'Difference between the fast and slow exponential averages.',
                    unit: 'price',
                    axis: independentAxis,
                    kind: 'line',
                    points: [{date: '2026-07-23', value: 1.2}],
                },
                {
                    key: 'signal',
                    label_key: 'signals.macd.signal',
                    semantic_id: 'momentum.macd.signal',
                    semantic_description: 'Smoothed signal line derived from MACD.',
                    unit: 'price',
                    axis: independentAxis,
                    kind: 'line',
                    points: [{date: '2026-07-23', value: 1}],
                },
                {
                    key: 'histogram',
                    label_key: 'signals.macd.histogram',
                    semantic_id: 'momentum.macd.histogram',
                    semantic_description: 'Difference between the MACD and signal lines.',
                    unit: 'price',
                    axis: independentAxis,
                    kind: 'bar',
                    points: [{date: '2026-07-23', value: 0.2}],
                },
            ],
            warnings: [
                {
                    code: 'incomplete_warmup',
                    message: 'Warm-up incomplete',
                },
            ],
        });

        expect(result.series?.map((series) => series.kind)).toEqual(['line', 'line', 'bar']);
    });
});
