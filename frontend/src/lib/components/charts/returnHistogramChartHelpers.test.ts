/**
 * returnHistogramChartHelpers — the option behind the histogram of daily returns (F-5; Vitest).
 *
 * Pinned, on the builder and never on ECharts:
 *
 * - the axis is an axis of returns (`type: 'value'`) from the first lower bound to the last upper bound, with thresholds on it
 *   (a tick count, written by the caller's formatter) — the two ends alone were the CSS bars' axis;
 * - one datum per bin, carrying its real edges and count, so a non-uniform grid draws as it is;
 * - the fill: the bar holding the cut is the warning, the bars beyond it the loss at 80 %, the rest the neutral surface, and the
 *   straddling bar is never in the tail;
 * - the cut is a line at the published value, `0` included, and no line without one;
 * - a bar is as wide as its span less the gap, a bar with observations never rounds away to nothing, an empty bin draws no bar
 *   but keeps its hit area, so it has a tooltip.
 *
 * The expected colours are the literals of the light theme's stand-ins (tokens.css resolved), written here: one computed with the
 * code's own table would agree with it by construction and pin nothing.
 */
import {describe, expect, it} from 'vitest';

import {barGeometry, binColor, buildReturnHistogramOption, MIN_BAR_PX, renderBin, type HistogramBin, type HistogramDatum} from './returnHistogramChartHelpers';

const WARNING = '#ae4e00';
const LOSS_80 = 'rgba(200,40,56,0.8)';
const NEUTRAL = '#d8e0dc';

/** Seven bars, the cut at −2.1 inside bar 2: bars 0 and 1 lie entirely beyond it. */
const BINS: HistogramBin[] = [
    {lowerBound: -6, upperBound: -4, count: 1, holdsCut: false, belowCut: true},
    {lowerBound: -4, upperBound: -3, count: 2, holdsCut: false, belowCut: true},
    {lowerBound: -3, upperBound: -2, count: 9, holdsCut: true, belowCut: false},
    {lowerBound: -2, upperBound: -1, count: 14, holdsCut: false, belowCut: false},
    {lowerBound: -1, upperBound: 0, count: 20, holdsCut: false, belowCut: false},
    {lowerBound: 0, upperBound: 1, count: 0, holdsCut: false, belowCut: false},
    {lowerBound: 1, upperBound: 4, count: 14, holdsCut: false, belowCut: false},
];

const writeAxis = (percent: number) => `${percent.toFixed(1)}%`;

function build(overrides: Partial<Parameters<typeof buildReturnHistogramOption>[0]> = {}) {
    return buildReturnHistogramOption({bins: BINS, cut: -2.1, formatAxis: writeAxis, cutLabel: 'VaR −2.1%', ...overrides});
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Loose = any;

describe('buildReturnHistogramOption — the axis', () => {
    it('is an axis of returns from the first lower bound to the last upper bound, with thresholds on it', () => {
        const option = build().option as Loose;

        expect(option.xAxis.type).toBe('value');
        expect([option.xAxis.min, option.xAxis.max]).toEqual([-6, 4]);
        // More than the two ends: ECharts is asked for a handful of ticks, and the labels are the caller's figures.
        expect(option.xAxis.splitNumber).toBeGreaterThan(2);
        expect(option.xAxis.axisLabel.formatter(-3)).toBe('-3.0%');
        // Labels that would collide give way instead of overprinting.
        expect(option.xAxis.axisLabel.hideOverlap).toBe(true);
    });

    it('scales the height to the tallest bar and draws no y axis', () => {
        const option = build().option as Loose;

        expect(option.yAxis.max).toBe(20);
        expect(option.yAxis.min).toBe(0);
        expect(option.yAxis.show).toBe(false);
    });

    it('survives a histogram of nothing but empty bins', () => {
        const empty = BINS.map((bin) => ({...bin, count: 0}));
        const option = build({bins: empty}).option as Loose;

        expect(option.yAxis.max).toBe(1);
    });

    it('says it is empty when there is no bin', () => {
        expect(build({bins: []}).isEmpty).toBe(true);
        expect(build().isEmpty).toBe(false);
    });
});

describe('buildReturnHistogramOption — one datum per bin', () => {
    const data = () => (build().option as Loose).series[0].data as HistogramDatum[];

    it('carries the real edges and the count of each bin, in order', () => {
        expect(data().map((datum) => datum.value)).toEqual(BINS.map((bin) => [bin.lowerBound, bin.upperBound, bin.count]));
        expect(data().map((datum) => datum.binIndex)).toEqual([0, 1, 2, 3, 4, 5, 6]);
    });

    it('colours the bar that holds the cut, the bars beyond it and the rest apart', () => {
        const colors = data().map((datum) => datum.itemStyle.color);

        expect(colors).toEqual([LOSS_80, LOSS_80, WARNING, NEUTRAL, NEUTRAL, NEUTRAL, NEUTRAL]);
    });

    it('never puts the straddling bar in the tail', () => {
        const straddling = BINS.findIndex((bin) => bin.holdsCut);

        expect(data()[straddling].itemStyle.color).toBe(WARNING);
        expect(data()[straddling].itemStyle.color).not.toBe(LOSS_80);
    });

    it('reads the warning and the loss from the dark theme when it is dark', () => {
        expect(binColor({holdsCut: true, belowCut: false}, true)).toBe('#f59e0b');
        expect(binColor({holdsCut: false, belowCut: true}, true)).toBe('rgba(255,122,134,0.8)');
    });
});

describe('buildReturnHistogramOption — the cut', () => {
    const markLine = (cut: number | null) => (build({cut}).option as Loose).series[0].markLine;

    it('is a dashed line at the published value, with the caller’s label', () => {
        expect(markLine(-2.1).data).toEqual([{xAxis: -2.1}]);
        expect(markLine(-2.1).label.formatter).toBe('VaR −2.1%');
        expect(markLine(-2.1).lineStyle.color).toBe(WARNING);
        expect(markLine(-2.1).lineStyle.type).toBe('dashed');
    });

    it('is a line at exactly zero too: a threshold at break-even is an answer, not a missing one', () => {
        expect(markLine(0).data).toEqual([{xAxis: 0}]);
    });

    it('is no line when no threshold was published, and the top margin closes', () => {
        expect(markLine(null)).toBeUndefined();
        expect((build({cut: null}).option as Loose).grid.top).toBeLessThan((build().option as Loose).grid.top);
    });
});

describe('barGeometry — a bar is its span, less the gap', () => {
    it('is as wide as the pixels between its edges less the gap, and stands on the baseline', () => {
        const box = barGeometry([100, 40], [160, 140], 5);

        expect(box.width).toBe(59);
        expect(box.x).toBe(100.5);
        expect(box.y + box.height).toBe(140);
        expect(box.height).toBe(100);
    });

    it('keeps a bar with observations from rounding away to nothing', () => {
        const box = barGeometry([0, 139.9], [20, 140], 1);

        expect(box.height).toBe(MIN_BAR_PX);
    });

    it('draws no bar for an empty bin', () => {
        expect(barGeometry([0, 140], [20, 140], 0).height).toBe(0);
    });

    it('never gives a bar less than a pixel of width', () => {
        expect(barGeometry([10, 40], [10.2, 140], 3).width).toBe(1);
    });
});

describe('renderBin — the hit area and the bar', () => {
    const colors = {hoverBand: 'hover', hitArea: 'hit'};
    const area = {x: 0, y: 10, width: 400, height: 130};
    /** An axis from 0 to 100 over 400 px, a count scale of 10 per 13 px, the baseline at 140. */
    const api = (lower: number, upper: number, count: number) => ({
        value: (dimension: number) => [lower, upper, count][dimension],
        coord: ([x, y]: [number, number]) => [x * 4, 140 - y * 13],
        style: () => ({fill: 'bar'}),
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const children = (item: Loose) => item.children as {shape: {x: number; y: number; width: number; height: number}; style: {fill: string}}[];

    it('gives every bin a hit area as tall as the plot, empty ones included', () => {
        const [hit] = children(renderBin({coordSys: area}, api(20, 60, 0), colors));

        expect(hit.shape).toMatchObject({x: 80, y: 10, width: 160, height: 130});
        expect(hit.style.fill).toBe('hit');
    });

    it('draws the bar over it from the real edges: a wide bin is a wide bar', () => {
        const [, narrow] = children(renderBin({coordSys: area}, api(0, 10, 4), colors));
        const [, wide] = children(renderBin({coordSys: area}, api(10, 70, 4), colors));

        expect(wide.shape.width).toBeGreaterThan(narrow.shape.width * 5);
        expect(narrow.shape.height).toBe(52);
        expect(narrow.style.fill).toBe('bar');
    });

    it('draws no bar for an empty bin, but keeps its hit area', () => {
        const [hit, bar] = children(renderBin({coordSys: area}, api(20, 60, 0), colors));

        expect(hit.shape.height).toBe(130);
        expect(bar.shape.height).toBe(0);
    });
});
