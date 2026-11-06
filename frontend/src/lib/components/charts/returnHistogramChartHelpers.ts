/**
 * returnHistogramChartHelpers — the option behind the histogram of daily returns.
 *
 * Split from `ReturnHistogramChart.svelte` as every chart here is (`scatterChartHelpers`): mounting ECharts in jsdom tests
 * the mock rather than the drawing, so the decisions live in a pure builder, asserted directly, and the component pins only
 * the wiring.
 *
 * ⚠️ WHY A `custom` SERIES AND A VALUE AXIS, NOT A `bar` SERIES.
 * The server bins the returns and hands back the edges: `validate_return_bins` polices only that the lower bounds ascend, not
 * that the bars are contiguous or of one width. A `bar` series on a category axis draws every bar the same width and writes
 * the labels under the bars, so it could neither keep a non-uniform grid honest nor put the thresholds on the axis. The bars
 * are drawn from their real edges, on an axis of returns (`type: 'value'`, the bounds of the first and last bin): a bar is as
 * wide as its `upperBound − lowerBound`, and the axis ticks are return thresholds, not bin numbers. (The first version of this
 * panel was CSS bars for want of a chart; the developer asked for ECharts, 05/11/2026, to have the axis, the threshold and the
 * tooltip a chart gives.)
 *
 * What each shading says is unchanged and is decided before this file, in `l1Helpers`: `holdsCut` the one bar the VaR falls
 * inside (where the number is), `belowCut` every bar entirely beyond it (the mass it speaks of); the straddling bar is in
 * neither, so the tail is never overstated by up to one bin.
 *
 * Every bar also carries a full-height transparent hit area, so an empty bin has a tooltip as a full one does: a bin with
 * nothing in it and a bin that is not there must not look alike.
 */

import {chartNeutrals, RETURN_HISTOGRAM_COLORS} from '$lib/theme/chartTheme';
import {themed} from '$lib/theme/themePair';

/** One bar, in percent units, with the flags `l1Helpers` computed. */
export interface HistogramBin {
    lowerBound: number;
    upperBound: number;
    count: number;
    holdsCut: boolean;
    belowCut: boolean;
}

export interface ReturnHistogramOptionInput {
    bins: readonly HistogramBin[];
    /** The VaR cut in percent units, or `null` when none was published. `0` is a real cut. */
    cut: number | null;
    /** `isDarkTheme()`, resolved by the caller. */
    dark?: boolean;
    /** The chart's own element, so the roles are read where the chart stands. */
    scope?: Element | null;
    /** A position on the return axis, in percent units, already written (the axis ends and ticks). */
    formatAxis: (percent: number) => string;
    /** The label at the top of the cut line, already written. */
    cutLabel: string;
}

/** A bar never rounds away to nothing: an invisible bar and an empty bin must not look the same. */
export const MIN_BAR_PX = 2;
/** The gap between two bars, in pixels. */
export const BAR_GAP_PX = 1;

/** What the bar under the pointer reports, in `params.data`. */
export interface HistogramDatum {
    value: [number, number, number];
    /** Position in the series, which the tooltip hands back to the caller. */
    binIndex: number;
    itemStyle: {color: string};
}

/** The bar's fill: the cut, the tail, or the neutral surface. */
export function binColor(bin: Pick<HistogramBin, 'holdsCut' | 'belowCut'>, dark: boolean, scope?: Element | null): string {
    if (bin.holdsCut) return themed(RETURN_HISTOGRAM_COLORS.cut, dark);
    if (bin.belowCut) return themed(RETURN_HISTOGRAM_COLORS.tail, dark);
    return chartNeutrals(dark, scope).returnHistogram.bar;
}

/** The geometry of one drawn bar, from the pixel of its two corners; tested without ECharts. */
export function barGeometry(topLeft: readonly number[], bottomRight: readonly number[], count: number): {x: number; y: number; width: number; height: number} {
    const width = Math.max(bottomRight[0] - topLeft[0] - BAR_GAP_PX, 1);
    const full = Math.max(bottomRight[1] - topLeft[1], 0);
    const height = count > 0 ? Math.max(full, MIN_BAR_PX) : 0;
    return {x: topLeft[0] + BAR_GAP_PX / 2, y: bottomRight[1] - height, width, height};
}

/**
 * The `renderItem` of the series: a hit area the height of the plot, and the bar over it. `api` is ECharts' custom-series api,
 * typed by what is used so a test can stand one in.
 */
export interface HistogramRenderApi {
    value(dimension: number): number;
    coord(point: [number, number]): number[];
    style(): Record<string, unknown>;
}

export function renderBin(params: {coordSys: {x: number; y: number; width: number; height: number}}, api: HistogramRenderApi, colors: {hoverBand: string; hitArea: string}): Record<string, unknown> {
    const lower = api.value(0);
    const upper = api.value(1);
    const count = api.value(2);
    const topLeft = api.coord([lower, count]);
    const bottomRight = api.coord([upper, 0]);
    const {x, y, width, height} = barGeometry(topLeft, bottomRight, count);
    const area = params.coordSys;
    return {
        type: 'group',
        children: [
            {type: 'rect', shape: {x: topLeft[0], y: area.y, width: Math.max(bottomRight[0] - topLeft[0], 1), height: area.height}, style: {fill: colors.hitArea}, emphasis: {style: {fill: colors.hoverBand}}, z2: 0},
            {type: 'rect', shape: {x, y, width, height, r: [2, 2, 0, 0]}, style: api.style(), z2: 1, silent: true},
        ],
    };
}

export interface ReturnHistogramOptionResult {
    isEmpty: boolean;
    /** An ECharts option; typed loosely because a custom series' `renderItem` and `markLine` are wider than the library's own type of a literal. */
    option: Record<string, unknown>;
}

export function buildReturnHistogramOption(input: ReturnHistogramOptionInput): ReturnHistogramOptionResult {
    const {bins, cut, dark = false, scope = null, formatAxis, cutLabel} = input;
    if (bins.length === 0) return {isEmpty: true, option: {}};

    const {returnHistogram} = chartNeutrals(dark, scope);
    const lowest = bins[0].lowerBound;
    const highest = bins[bins.length - 1].upperBound;
    const tallest = Math.max(...bins.map((bin) => bin.count), 0);

    const data: HistogramDatum[] = bins.map((bin, binIndex) => ({
        value: [bin.lowerBound, bin.upperBound, bin.count],
        binIndex,
        itemStyle: {color: binColor(bin, dark, scope)},
    }));

    const cutColor = themed(RETURN_HISTOGRAM_COLORS.cut, dark);

    return {
        isEmpty: false,
        option: {
            // A top margin the cut's label sits in; the bottom one is the axis labels', which `containLabel` measures.
            grid: {left: 8, right: 14, top: cut === null ? 8 : 22, bottom: 4, containLabel: true},
            xAxis: {
                type: 'value',
                min: lowest,
                max: highest,
                // A threshold every so often, never the two ends alone; labels that would collide give way.
                splitNumber: 6,
                axisLine: {lineStyle: {color: returnHistogram.axis}},
                axisTick: {lineStyle: {color: returnHistogram.axis}},
                axisLabel: {color: returnHistogram.axisText, fontSize: 10, hideOverlap: true, formatter: (value: number) => formatAxis(value)},
                splitLine: {show: false},
            },
            // The height is the count; no axis is drawn, the tooltip says the number.
            yAxis: {type: 'value', min: 0, max: tallest > 0 ? tallest : 1, show: false},
            series: [
                {
                    id: 'return-histogram',
                    type: 'custom',
                    data,
                    encode: {x: [0, 1], y: 2},
                    renderItem: (params: unknown, api: unknown) => renderBin(params as Parameters<typeof renderBin>[0], api as HistogramRenderApi, {hoverBand: returnHistogram.hoverBand, hitArea: returnHistogram.hitArea}),
                    ...(cut === null
                        ? {}
                        : {
                              markLine: {
                                  silent: true,
                                  symbol: 'none',
                                  animation: false,
                                  lineStyle: {color: cutColor, type: 'dashed', width: 1.5},
                                  label: {show: true, position: 'end', formatter: cutLabel, color: cutColor, fontSize: 10},
                                  data: [{xAxis: cut}],
                              },
                          }),
                },
            ],
        },
    };
}
