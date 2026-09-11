import {describe, expect, it} from 'vitest';

import {backendSignalSchemas, normalizeBackendSignalSeries, type BackendSignalAreaSeries, type BackendSignalBandSeries, type BackendSignalBarSeries, type BackendSignalLineSeries, type BackendSignalResult} from '../backendTypes';

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

describe('backend signal series normalization', () => {
    it('preserves canonical line, area, and bar discriminants and flat point order', () => {
        const points: BackendSignalLineSeries['points'] = [
            {date: '2026-07-23', value: 101.5},
            {date: '2026-07-24', value: 102.5},
        ];
        const line: BackendSignalLineSeries = {
            key: 'line',
            label_key: 'signals.test.line',
            semantic_id: 'test.line',
            semantic_description: 'Canonical flat line fixture.',
            unit: 'price',
            axis: priceAxis,
            kind: 'line',
            points,
        };
        const area: BackendSignalAreaSeries = {...line, key: 'area', kind: 'area'};
        const bar: BackendSignalBarSeries = {...line, key: 'bar', kind: 'bar'};

        const normalized = [line, area, bar].map((series) => normalizeBackendSignalSeries(series));

        expect(normalized.map((series) => series.kind)).toEqual(['line', 'area', 'bar']);
        expect(normalized.map((series) => series.points)).toEqual([points, points, points]);
    });

    it('flattens generated point elements by exactly one level while preserving order', () => {
        const first = {date: '2026-07-23', value: 1};
        const second = {date: '2026-07-24', value: 2};
        const third = {date: '2026-07-25', value: 3};
        const generatedLine = {
            key: 'generated-line',
            label_key: 'signals.test.generated_line',
            semantic_id: 'test.generated-line',
            semantic_description: 'Generated nested line fixture.',
            unit: 'price',
            axis: priceAxis,
            kind: 'line',
            points: [[first, second], third],
        } satisfies Parameters<typeof normalizeBackendSignalSeries>[0];

        const normalized = normalizeBackendSignalSeries(generatedLine);

        expect(normalized.kind).toBe('line');
        expect(normalized.points).toEqual([first, second, third]);
    });

    it('leaves band series unchanged without flattening band points', () => {
        const band: BackendSignalBandSeries = {
            key: 'band',
            label_key: 'signals.test.band',
            semantic_id: 'test.band',
            semantic_description: 'Canonical band fixture.',
            unit: 'price',
            axis: priceAxis,
            kind: 'band',
            points: [
                {date: '2026-07-23', lower: 95, middle: 100, upper: 105},
                {date: '2026-07-24', lower: 96, middle: 101, upper: 106},
            ],
        };

        const normalized = normalizeBackendSignalSeries(band);

        expect(normalized.kind).toBe('band');
        expect(normalized).toEqual(band);
        expect(normalized.points).toEqual(band.points);
    });
});
