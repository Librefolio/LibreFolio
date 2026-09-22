/**
 * scatterChartHelpers — unit tests.
 *
 * The scatter exists because `LineChart` cannot draw it: `LineChart` pins every
 * series to `{type: 'category', data: dates}`, and a risk/return plot has no
 * dates. So the first test here is not decorative — it pins the axis type, and
 * it fails the moment somebody "reuses" a time-series option builder for this
 * chart and reintroduces the very mismatch the component was created to avoid.
 *
 * The second thing pinned is the bubble encoding. Radius scales with the SQUARE
 * ROOT of the weight, because a bubble is read by area and area grows with the
 * square of the radius; a linear radius would make a 4× position look 16× as
 * big. That is a defect nobody reports, because the chart still looks like a
 * chart — so it gets an explicit test rather than a comment.
 */
import {describe, expect, it} from 'vitest';

import {buildScatterOption, capitalMarketLine, isPlaceable, MAX_SYMBOL_PX, MIN_SYMBOL_PX, symbolSizeForWeight, type RiskReturnPoint} from './scatterChartHelpers';

const LABELS = {volatility: 'Volatility', return: 'Return', capitalMarketLine: 'CML'};

function point(overrides: Partial<RiskReturnPoint> & Pick<RiskReturnPoint, 'id' | 'role'>): RiskReturnPoint {
    return {name: overrides.id, volatility: 0.1, annualReturn: 0.05, ...overrides};
}

describe('scatterChartHelpers', () => {
    describe('the axes', () => {
        it('puts both coordinates on a numeric axis, never a category one', () => {
            const {option} = buildScatterOption({points: [point({id: 'p', role: 'portfolio'})], labels: LABELS});

            expect(option.xAxis.type).toBe('value');
            expect(option.yAxis.type).toBe('value');
        });

        /** A category axis would silently reindex the data to 0,1,2… and still render. */
        it('never carries the date-series axis data that LineChart needs', () => {
            const {option} = buildScatterOption({points: [point({id: 'p', role: 'portfolio'})], labels: LABELS});

            expect(option.xAxis).not.toHaveProperty('data');
            expect(option.yAxis).not.toHaveProperty('data');
        });
    });

    describe('points it cannot place', () => {
        it('rejects a non-finite coordinate', () => {
            expect(isPlaceable(point({id: 'a', role: 'asset', volatility: Number.NaN}))).toBe(false);
            expect(isPlaceable(point({id: 'b', role: 'asset', annualReturn: Number.POSITIVE_INFINITY}))).toBe(false);
            expect(isPlaceable(point({id: 'c', role: 'asset'}))).toBe(true);
        });

        it('drops them and reports how many, instead of letting ECharts skip them in silence', () => {
            const {droppedCount, isEmpty, option} = buildScatterOption({
                points: [point({id: 'good', role: 'asset'}), point({id: 'bad', role: 'asset', volatility: Number.NaN}), point({id: 'worse', role: 'asset', annualReturn: Number.NaN})],
                labels: LABELS,
            });

            expect(droppedCount).toBe(2);
            expect(isEmpty).toBe(false);
            const assets = option.series.find((s: {id: string}) => s.id === 'scatter-asset');
            expect(assets.data).toHaveLength(1);
            expect(assets.data[0].id).toBe('good');
        });

        it('reports emptiness when nothing survives, so the caller can show an empty state', () => {
            const {isEmpty, droppedCount} = buildScatterOption({points: [point({id: 'bad', role: 'asset', volatility: Number.NaN})], labels: LABELS});

            expect(isEmpty).toBe(true);
            expect(droppedCount).toBe(1);
        });

        it('reports emptiness for no points at all', () => {
            const {isEmpty, option} = buildScatterOption({points: [], labels: LABELS});

            expect(isEmpty).toBe(true);
            expect(option.series).toEqual([]);
        });
    });

    describe('the bubble encoding', () => {
        it('scales area, not radius, with the weight', () => {
            const quarter = symbolSizeForWeight(0.25) - MIN_SYMBOL_PX;
            const whole = symbolSizeForWeight(1) - MIN_SYMBOL_PX;

            // 4x the weight must be 2x the excess diameter — not 4x.
            expect(quarter).toBeCloseTo(whole / 2, 10);
        });

        it('keeps a weightless point visible rather than collapsing it to nothing', () => {
            expect(symbolSizeForWeight(undefined)).toBe(MIN_SYMBOL_PX);
            expect(symbolSizeForWeight(0)).toBe(MIN_SYMBOL_PX);
            expect(symbolSizeForWeight(Number.NaN)).toBe(MIN_SYMBOL_PX);
            expect(symbolSizeForWeight(-0.3)).toBe(MIN_SYMBOL_PX);
        });

        it('never exceeds the ceiling, even for a weight above 1', () => {
            expect(symbolSizeForWeight(1)).toBe(MAX_SYMBOL_PX);
            expect(symbolSizeForWeight(5)).toBe(MAX_SYMBOL_PX);
        });
    });

    describe('the capital market line', () => {
        it('runs from the risk-free rate through the portfolio', () => {
            const line = capitalMarketLine([point({id: 'me', role: 'portfolio', volatility: 0.2, annualReturn: 0.1})], 0.02);

            expect(line).not.toBeNull();
            expect(line![0]).toEqual([0, 0.02]);
            // slope = (0.10 - 0.02) / 0.20 = 0.4, so at x = 0.20 the line is back on the portfolio.
            expect(line![1][0]).toBeCloseTo(0.2, 10);
            expect(line![1][1]).toBeCloseTo(0.1, 10);
        });

        it('extends to the widest volatility on the plot rather than stopping at the portfolio', () => {
            const line = capitalMarketLine([point({id: 'me', role: 'portfolio', volatility: 0.2, annualReturn: 0.1}), point({id: 'wild', role: 'asset', volatility: 0.5, annualReturn: 0.3})], 0.02);

            expect(line![1][0]).toBeCloseTo(0.5, 10);
            expect(line![1][1]).toBeCloseTo(0.02 + 0.4 * 0.5, 10);
        });

        /** No portfolio means no tangency point, so there is no line to assert. */
        it('is absent without a portfolio point', () => {
            expect(capitalMarketLine([point({id: 'a', role: 'asset'}), point({id: 'b', role: 'benchmark'})], 0.02)).toBeNull();
        });

        it('is absent when the portfolio has no volatility, because the slope is undefined', () => {
            expect(capitalMarketLine([point({id: 'me', role: 'portfolio', volatility: 0})], 0.02)).toBeNull();
        });

        it('ignores a non-finite point when choosing how far to extend', () => {
            const line = capitalMarketLine([point({id: 'me', role: 'portfolio', volatility: 0.2, annualReturn: 0.1}), point({id: 'broken', role: 'asset', volatility: Number.NaN})], 0);

            expect(Number.isFinite(line![1][0])).toBe(true);
            expect(line![1][0]).toBeCloseTo(0.2, 10);
        });

        it('is omitted from the series when it cannot be drawn', () => {
            const {option} = buildScatterOption({points: [point({id: 'a', role: 'asset'})], labels: LABELS});

            expect(option.series.some((s: {id: string}) => s.id === 'capital-market-line')).toBe(false);
        });

        it('is drawn beneath the points and takes no pointer events', () => {
            const {option} = buildScatterOption({points: [point({id: 'me', role: 'portfolio', volatility: 0.2, annualReturn: 0.1})], labels: LABELS});
            const cml = option.series.find((s: {id: string}) => s.id === 'capital-market-line');

            expect(cml.silent).toBe(true);
            expect(cml.z).toBeLessThan(option.series.find((s: {id: string}) => s.id === 'scatter-portfolio').z);
        });
    });

    describe('the three roles', () => {
        it('separates them into their own series', () => {
            const {option} = buildScatterOption({
                points: [point({id: 'me', role: 'portfolio'}), point({id: 'bench', role: 'benchmark'}), point({id: 'a1', role: 'asset'}), point({id: 'a2', role: 'asset'})],
                labels: LABELS,
            });

            const ids = option.series.map((s: {id: string}) => s.id);
            expect(ids).toContain('scatter-portfolio');
            expect(ids).toContain('scatter-benchmark');
            expect(ids).toContain('scatter-asset');
            expect(option.series.find((s: {id: string}) => s.id === 'scatter-asset').data).toHaveLength(2);
        });

        it('draws the individual assets behind the portfolio and the benchmark', () => {
            const {option} = buildScatterOption({
                points: [point({id: 'me', role: 'portfolio'}), point({id: 'bench', role: 'benchmark'}), point({id: 'a1', role: 'asset'})],
                labels: LABELS,
            });

            const z = (id: string) => option.series.find((s: {id: string}) => s.id === id).z;
            expect(z('scatter-asset')).toBeLessThan(z('scatter-portfolio'));
            expect(z('scatter-asset')).toBeLessThan(z('scatter-benchmark'));
        });

        it('omits a series entirely when that role has no points', () => {
            const {option} = buildScatterOption({points: [point({id: 'a1', role: 'asset'})], labels: LABELS});

            expect(option.series.map((s: {id: string}) => s.id)).toEqual(['scatter-asset']);
        });

        it('keeps every series a scatter except the line', () => {
            const {option} = buildScatterOption({
                points: [point({id: 'me', role: 'portfolio', volatility: 0.2, annualReturn: 0.1}), point({id: 'a1', role: 'asset'})],
                labels: LABELS,
            });

            for (const series of option.series) {
                expect(series.type).toBe(series.id === 'capital-market-line' ? 'line' : 'scatter');
            }
        });
    });

    describe('the theme', () => {
        it('gives the three roles distinguishable colours', () => {
            const {option} = buildScatterOption({
                points: [point({id: 'me', role: 'portfolio'}), point({id: 'bench', role: 'benchmark'}), point({id: 'a1', role: 'asset'})],
                labels: LABELS,
            });

            const colorOf = (id: string) => option.series.find((s: {id: string}) => s.id === id).data[0].itemStyle.color;
            const colors = [colorOf('scatter-portfolio'), colorOf('scatter-benchmark'), colorOf('scatter-asset')];

            expect(new Set(colors).size).toBe(3);
        });

        it('changes the palette between light and dark', () => {
            const points = [point({id: 'me', role: 'portfolio'})];
            const light = buildScatterOption({points, labels: LABELS, dark: false});
            const dark = buildScatterOption({points, labels: LABELS, dark: true});

            const colorOf = (result: typeof light) => result.option.series.find((s: {id: string}) => s.id === 'scatter-portfolio').data[0].itemStyle.color;

            expect(colorOf(light)).not.toBe(colorOf(dark));
        });

        it('uses the axis titles it was given rather than inventing any', () => {
            const {option} = buildScatterOption({points: [point({id: 'a', role: 'asset'})], labels: LABELS});

            expect(option.xAxis.name).toBe('Volatility');
            expect(option.yAxis.name).toBe('Return');
        });
    });
});
