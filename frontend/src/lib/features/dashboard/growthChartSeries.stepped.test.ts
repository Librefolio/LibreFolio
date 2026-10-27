/**
 * The growth chart's series when the entry is the steps themselves (D-P4, Y5-3).
 *
 * A step line holds its value from one date to the next and then jumps, so ECharts draws it with `step: 'end'`; the P&L
 * halves (positive green, negative red) must change sign AT the next date, not at the interpolated crossing a slope has;
 * and the history's MWRR, a line of a few true values, stays joined by slopes whatever the rest does.
 */
import {describe, expect, it} from 'vitest';
import {namedPoint} from '$lib/components/charts/echartsAnimationConfig';
import type {AggregationInputs, SeriesPoint} from './growthChartData';
import {buildGrowthFullSeries, splitBySign, type GrowthSeriesContext, type GrowthSeriesData, type PctSeriesSpec} from './growthChartSeries';

const point = (date: string, value: number | null): SeriesPoint => ({...namedPoint(date, value), bucketStart: date, bucketEnd: date, resolution: 'daily'});
const xy = (points: SeriesPoint[]) => points.map((entry) => [entry.value[0], entry.value[1]]);

describe('splitBySign on a step line', () => {
    const points = [point('2026-01-01', 430), point('2026-01-11', -50), point('2026-01-21', -50)];

    it('changes sign at the next date: the positive half drops to the axis there and the negative one starts there', () => {
        const {positive, negative} = splitBySign(points, true);
        expect(xy(positive)).toEqual([
            ['2026-01-01', 430],
            ['2026-01-11', 0],
            ['2026-01-11', null],
            ['2026-01-21', null],
        ]);
        expect(xy(negative)).toEqual([
            ['2026-01-01', null],
            ['2026-01-11', 0],
            ['2026-01-11', -50],
            ['2026-01-21', -50],
        ]);
    });

    it('keeps the interpolated crossing for a line that is not stepped', () => {
        const {positive} = splitBySign(points, false);
        const crossing = positive.find((entry) => entry.value[1] === 0)!;
        expect(String(crossing.value[0])).toMatch(/^2026-01-0[1-9]T|^2026-01-1[01]T/);
        expect(crossing.value[0]).not.toBe('2026-01-11');
    });

    it('leaves a run of one sign, a zero and a gap alone', () => {
        const flat = [point('2026-01-01', 5), point('2026-01-02', 0), point('2026-01-03', null), point('2026-01-04', 6)];
        expect(xy(splitBySign(flat, true).positive)).toEqual(xy(splitBySign(flat, false).positive));
    });
});

describe('buildGrowthFullSeries with a stepped entry', () => {
    const labels = {bookAssetLike: 'Assets', bookAssetLikeTooltip: 'Assets', cashContributed: 'Cash', cashGenerated: 'Gen', nav: 'NAV', capitalBaseline: 'Baseline', capitalBaselineTooltip: 'Baseline'};
    const pnlLabels = {total: 'P&L', dividend: 'Div', interest: 'Int', costs: 'Costs', deposit: 'Dep', acqNewCapital: 'New', acqReinvested: 'Re', bookValue: 'Book'};
    const pct: PctSeriesSpec[] = [
        {key: 'mwrrCum', name: 'MWRR', values: [], lineStyle: 'solid', colorKey: 'nav'},
        {key: 'twrr', name: 'TWRR', values: [], lineStyle: 'dashed', colorKey: 'invested'},
    ];
    const context = (viewMode: 'eur' | 'pct' | 'pnl', stepped: boolean): GrowthSeriesContext => ({viewMode, pnlSubmode: 'line', eurLabels: labels, pnlLabels, pctSeries: pct, aggregationInputs: {} as AggregationInputs, stepped});
    const data = (count: number): GrowthSeriesData[] => Array.from({length: count}, (_, index) => ({name: `s${index}`, data: [point('2026-01-01', 1)]}));
    const stepOf = (series: unknown) => (series as {step?: unknown}).step;

    it('holds every Abs line and stacked area to the next date', () => {
        const series = buildGrowthFullSeries(context('eur', true), false, data(5));
        expect(series.map(stepOf)).toEqual(['end', 'end', 'end', 'end', 'end']);
    });

    it('draws no step when the entry is not the steps', () => {
        expect(buildGrowthFullSeries(context('eur', false), false, data(5)).map(stepOf)).toEqual([undefined, undefined, undefined, undefined, undefined]);
    });

    it('steps the P&L halves and the brokers, and the reference line too', () => {
        const series = buildGrowthFullSeries(context('pnl', true), false, data(4));
        expect(series.map(stepOf)).toEqual(['end', 'end', 'end', 'end']);
    });

    it('steps TWRR and ROI but joins the MWRR by its true points, across the days between them', () => {
        const series = buildGrowthFullSeries(context('pct', true), false, data(2));
        expect(series.map(stepOf)).toEqual([false, 'end']);
        expect(series.map((entry) => (entry as {connectNulls?: boolean}).connectNulls)).toEqual([true, false]);
    });

    it('joins the MWRR across a gap even when nothing is stepped', () => {
        const series = buildGrowthFullSeries(context('pct', false), false, data(2));
        expect(series.map((entry) => (entry as {connectNulls?: boolean}).connectNulls)).toEqual([true, false]);
    });
});
