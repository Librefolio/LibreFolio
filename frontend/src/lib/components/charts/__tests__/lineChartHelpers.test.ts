/**
 * lineChartHelpers.test.ts — Unit tests for buildMainSeries() segment coloring/merging,
 * plus the overlay-series builders, arrow-rotation math and stale-opacity formula.
 *
 * @module components/charts/__tests__/lineChartHelpers.test
 */
import * as echarts from 'echarts';
import {describe, expect, it} from 'vitest';

import {buildBandSeries, buildBarSeries, buildMainSeries, buildSignalReferencePrimitives, COLORS, getStaleOpacity, updateArrowRotations} from '../lineChartHelpers';
// `toRgba` replaced `hexToRgba` (colour workstream R, R-4) and builds the expected colours below. On a #rrggbb it
// writes the old helper's string character for character — `$lib/theme/colorAlpha.test.ts` pins that against
// the old code — so these expectations are the strings they always were.
import {toRgba} from '$lib/theme/colorAlpha';
import type {RenderedSignal} from '$lib/charts/signals';

const BASE_COLOR = '#1a4031';
const GREEN = '#16a34a';
const RED = '#ef4444';

/**
 * Minimal-but-complete RenderedSignal, so tests only spell out the fields
 * they actually vary instead of re-declaring every required property.
 */
function makeSignal(overrides: Partial<RenderedSignal> = {}): RenderedSignal {
    return {
        id: 'sig1',
        label: 'Signal',
        data: [],
        color: '#3355ff',
        lineWidth: 2,
        lineType: 'solid',
        markerStart: null,
        markerEnd: null,
        aggregationProfile: 'last_with_range',
        ...overrides,
    };
}

describe('buildMainSeries', () => {
    it('colors a simple two-segment baseline crossing correctly (no merging needed)', () => {
        const values = [10, 10, 10, -5, -5, -5];
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);

        // 2 segments expected: green (above baseline) then red (below).
        expect(result.length).toBe(2);
        expect(result[0].itemStyle.color).toBe(toRgba(GREEN, 1));
        expect(result[1].itemStyle.color).toBe(toRgba(RED, 1));
    });

    it('keeps a single color as one series when there is no baseline crossing', () => {
        const values = new Array(50).fill(10);
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);
        expect(result.length).toBe(1);
        expect(result[0].itemStyle.color).toBe(toRgba(GREEN, 1));
    });

    it('keeps legacy output unchanged when no point is missing', () => {
        const values = [1.2, 1.25, 1.3];
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', false, 0, false);

        expect(result).toEqual([
            {
                type: 'line',
                name: 'Value',
                data: [1.2, 1.25, 1.3],
                smooth: false,
                symbol: 'none',
                showSymbol: false,
                sampling: 'lttb',
                yAxisIndex: 0,
                lineStyle: {width: 2, color: toRgba(BASE_COLOR, 1)},
                itemStyle: {color: toRgba(BASE_COLOR, 1)},
                emphasis: {focus: 'none'},
                z: 2,
            },
        ]);
    });

    it('renders null values as explicit gaps instead of connecting across missing rates', () => {
        const values = [1.2, null, 1.3];
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', false, 0, false);

        expect(result).toHaveLength(2);
        expect(result.every((series) => !('connectNulls' in series))).toBe(true);
        expect(result[0].data).toEqual([1.2, null, null]);
        expect(result[1].data).toEqual([null, null, 1.3]);
    });

    it('caps series count for a pathologically choppy baseline-crossing series (perf guard)', () => {
        // Alternating short runs (2-3 points each) crossing the baseline hundreds of
        // times — simulates decades of volatile daily prices. Without the Step 2b
        // merge cap in buildMainSeries, this would produce hundreds of ECharts series
        // (each a full-length array), which is what made a real setOption() call take
        // multiple seconds (see impl_plan_chart_resolution bugfix history).
        const values: number[] = [];
        for (let i = 0; i < 1000; i++) {
            values.push(i % 4 < 2 ? 10 : -10);
        }
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);

        expect(result.length).toBeLessThanOrEqual(150);
    });

    it('recomputes the MAJORITY color when merging short segments — regression test for the "stays green below 0%" bug', () => {
        // Regression test for a real user-reported bug: a below-baseline (red) span
        // was rendered as green after the Step 2b micro-segment merge was introduced,
        // because the merge only extended `last.end` without recomputing `last.color`
        // — so a merged block always kept whichever color happened to be first,
        // regardless of how much of its ACTUAL range was the opposite sign.
        //
        // Pattern: a 1-point ABOVE-baseline "anchor" point, followed by a 4-point
        // BELOW-baseline run, repeated many times — every cycle is short enough to be
        // merged (forced by making the whole series highly fragmented), and in each
        // merged block the below-baseline (red) points substantially outnumber the
        // anchor (green) point. The correct rendered color for the whole thing must be
        // predominantly RED, matching the true majority — not GREEN (the old, buggy,
        // "first segment wins" behavior).
        const values: number[] = [];
        for (let i = 0; i < 150; i++) {
            values.push(5); // 1 point above baseline (would-be anchor)
            values.push(-5, -5, -5, -5); // 4 points below baseline
        }
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);

        // The whole series collapses under the merge cap (750 points, 300 original
        // segments) — the resulting color must reflect the true 4:1 red majority.
        const colors = result.map((s) => s.itemStyle.color);
        expect(colors).not.toContain(toRgba(GREEN, 1));
        expect(colors).toContain(toRgba(RED, 1));
    });

    it('renders an all-missing series as a single untouched pass-through series', () => {
        // presentValues.length === 0: no segmentation, no color logic — the
        // function must not crash trying to color a series with nothing in it.
        const values = [null, null, null];
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);

        expect(result).toEqual([
            {
                name: 'Value',
                type: 'line',
                data: values,
                showSymbol: false,
                symbol: 'none',
                lineStyle: {width: 2, color: BASE_COLOR},
                areaStyle: undefined,
            },
        ]);
    });

    it('renders a single present value as a colored circle marker, not a line', () => {
        // presentValues.length === 1: a line needs two points, so this is the
        // dedicated circle-marker branch — and its color still respects baseline.
        const staleDays = [0, 0, 0];
        const above = buildMainSeries([null, 7, null], staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);
        expect(above).toEqual([
            {
                name: 'Value',
                type: 'line',
                data: [null, 7, null],
                showSymbol: true,
                symbol: 'circle',
                symbolSize: 8,
                itemStyle: {color: GREEN},
                lineStyle: {width: 0},
                areaStyle: undefined,
            },
        ]);

        const below = buildMainSeries([null, -7, null], staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);
        expect(below[0].itemStyle.color).toBe(RED);
    });

    it('a single present value at exactly the baseline counts as above it (>=)', () => {
        const result = buildMainSeries([null, 0, null], [0, 0, 0], BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);
        expect(result[0].itemStyle.color).toBe(GREEN);
    });

    it('paints a horizontal opacity gradient — not a solid color — across a stale run', () => {
        const values = [10, 10, 10, 10];
        const staleDays = [0, 0, 7, 14]; // fresh, fresh, half-stale, fully-stale
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', false, 0, true);

        // Fresh run + stale run: two segments, the second one gradient-colored.
        expect(result.length).toBe(2);
        const staleSeg = result[1];
        expect(staleSeg.lineStyle.color).toBeInstanceOf(echarts.graphic.LinearGradient);
        const stops = staleSeg.lineStyle.color.colorStops;
        // getStaleOpacity(7, 14) = 1 - (7/14)*0.85 = 0.575; getStaleOpacity(14,14) = 0.15
        expect(stops[0].color).toBe(toRgba(BASE_COLOR, getStaleOpacity(7)));
        expect(stops[1].color).toBe(toRgba(BASE_COLOR, getStaleOpacity(14)));
    });

    it('leaves data untouched when neither baseline nor stale coloring is requested', () => {
        const values = [1, 2, 3];
        const result = buildMainSeries(values, [0, 0, 0], BASE_COLOR, GREEN, RED, false, false, 2, 'Value', false, 0, false);
        expect(result).toHaveLength(1);
        expect(result[0].data).toEqual(values);
        expect(result[0].itemStyle.color).toBe(toRgba(BASE_COLOR, 1));
    });
});

describe('getStaleOpacity', () => {
    it('is fully opaque for fresh data (0, undefined, or negative stale days)', () => {
        expect(getStaleOpacity(0)).toBe(1.0);
        expect(getStaleOpacity(undefined)).toBe(1.0);
        expect(getStaleOpacity(-5)).toBe(1.0);
    });

    it('fades linearly from 1.0 to 0.15 as staleDays approaches maxDays', () => {
        // t = staleDays / maxDays; opacity = 1 - t * 0.85
        expect(getStaleOpacity(7, 14)).toBeCloseTo(0.575, 10);
        expect(getStaleOpacity(3.5, 14)).toBeCloseTo(1 - 0.25 * 0.85, 10);
    });

    it('reaches exactly the 0.15 floor at maxDays and clamps beyond it', () => {
        expect(getStaleOpacity(14, 14)).toBeCloseTo(0.15, 10);
        expect(getStaleOpacity(1000, 14)).toBeCloseTo(0.15, 10);
    });

    it('honors a custom maxDays instead of the default 14', () => {
        expect(getStaleOpacity(5, 10)).toBeCloseTo(1 - 0.5 * 0.85, 10);
    });
});

describe('buildBandSeries', () => {
    const signal = makeSignal({
        id: 'bb1',
        label: 'Bollinger',
        color: '#112233',
        opacity: 0.8,
        yAxisIndex: 1,
        data: [
            {date: '2026-01-01', value: 1},
            {date: '2026-01-02', value: 1},
            {date: '2026-01-03', value: 1},
        ],
        bandData: {
            upper: [10, 11, 12],
            middle: [5, 6, 7],
            lower: [0, 1, 2],
        },
    });
    const dates = ['2026-01-01', '2026-01-02', '2026-01-03'];

    it('returns an empty array when the signal has no bandData', () => {
        expect(buildBandSeries(makeSignal({bandData: undefined}), dates, false)).toEqual([]);
    });

    it('builds exactly 3 series sharing one stack key, in lower/delta/middle order', () => {
        const result = buildBandSeries(signal, dates, false);
        expect(result).toHaveLength(3);
        expect(result[0].name).toBe('Bollinger Lower');
        expect(result[1].name).toBe('Bollinger Band');
        expect(result[2].name).toBe('Bollinger');
        expect(result[0].stack).toBe('bb-bb1');
        expect(result[1].stack).toBe('bb-bb1');
        expect(result[0].data).toEqual([0, 1, 2]);
        expect(result[2].data).toEqual([5, 6, 7]);
    });

    it('computes the delta series as upper minus lower at each aligned date', () => {
        const result = buildBandSeries(signal, dates, false);
        expect(result[1].data).toEqual([10, 10, 10]); // [10-0, 11-1, 12-2]
    });

    it('bridges an axis date absent from the signal on the fill by axis position, and leaves the middle line empty there', () => {
        const result = buildBandSeries(signal, ['2026-01-01', '2099-12-31', '2026-01-03'], false);
        expect(result[0].data).toEqual([0, 1, 2]);
        expect(result[1].data).toEqual([10, 10, 10]);
        expect(result[2].data).toEqual([5, null, 7]);
    });

    it('scales the band fill opacity by isDark and the signal opacity, and colors it with the signal color', () => {
        const light = buildBandSeries(signal, dates, false);
        const dark = buildBandSeries(signal, dates, true);
        // areaStyle.color = toRgba(bandColor, (isDark ? 0.18 : 0.12) * opacity)
        expect(light[1].areaStyle.color).toBe(toRgba('#112233', 0.12 * 0.8));
        expect(dark[1].areaStyle.color).toBe(toRgba('#112233', 0.18 * 0.8));
    });

    it('defaults opacity to 1 when the signal does not specify one', () => {
        const noOpacity = makeSignal({...signal, opacity: undefined});
        const result = buildBandSeries(noOpacity, dates, false);
        expect(result[1].areaStyle.color).toBe(toRgba('#112233', 0.12));
    });

    it('forwards the signal yAxisIndex to every series, defaulting to 0 when unset', () => {
        const result = buildBandSeries(signal, dates, false);
        expect(result.every((s) => s.yAxisIndex === 1)).toBe(true);
        const defaulted = buildBandSeries(makeSignal({...signal, yAxisIndex: undefined}), dates, false);
        expect(defaulted.every((s) => s.yAxisIndex === 0)).toBe(true);
    });

    it('spreads buildSignalReferencePrimitives only onto the visible middle series', () => {
        const withLevels = makeSignal({...signal, referenceLevels: [{key: 'k', label: 'Upper band', semantic: 'upper', value: 42}]});
        const result = buildBandSeries(withLevels, dates, false);
        expect(result[0].markLine).toBeUndefined();
        expect(result[1].markLine).toBeUndefined();
        expect(result[2].markLine).toMatchObject({data: [{name: 'Upper band', yAxis: 42}]});
    });
});

describe('buildBarSeries', () => {
    it('colors each bar green/red by the sign of its own value, ignoring the signal color', () => {
        const signal = makeSignal({color: '#000000'});
        const result = buildBarSeries(signal, [5, -5, 0], false);
        expect(result.data[0].itemStyle.color).toBe(COLORS.greenLight);
        expect(result.data[1].itemStyle.color).toBe(COLORS.redLight);
        expect(result.data[2].itemStyle.color).toBe(COLORS.greenLight); // 0 >= 0 → green
    });

    it('uses dark-mode colors when isDark is true', () => {
        const signal = makeSignal();
        const result = buildBarSeries(signal, [5, -5], true);
        expect(result.data[0].itemStyle.color).toBe(COLORS.greenDark);
        expect(result.data[1].itemStyle.color).toBe(COLORS.redDark);
    });

    it('uses the flat signal color for every bar when barColorMode is "single"', () => {
        const signal = makeSignal({color: '#abcdef', barColorMode: 'single'});
        const result = buildBarSeries(signal, [5, -5], false);
        expect(result.data[0].itemStyle.color).toBe('#abcdef');
        expect(result.data[1].itemStyle.color).toBe('#abcdef');
    });

    it('preserves null and undefined bars as-is instead of wrapping them', () => {
        const signal = makeSignal();
        const result = buildBarSeries(signal, [null, undefined, 3], false);
        expect(result.data[0]).toBeNull();
        expect(result.data[1]).toBeUndefined();
        expect(result.data[2].value).toBe(3);
    });

    it('forwards the signal opacity to every bar and the series-level style', () => {
        const signal = makeSignal({opacity: 0.4});
        const result = buildBarSeries(signal, [5], false);
        expect(result.data[0].itemStyle.opacity).toBe(0.4);
        expect(result.itemStyle.opacity).toBe(0.4);
    });
});

describe('buildSignalReferencePrimitives', () => {
    it('returns an empty object when the signal declares neither levels nor regions', () => {
        expect(buildSignalReferencePrimitives(makeSignal(), false)).toEqual({});
    });

    it('builds a markLine data point per reference level, named and valued from the level', () => {
        const signal = makeSignal({
            referenceLevels: [
                {key: 'a', label: 'Overbought', semantic: 'high', value: 70},
                {key: 'b', label: 'Oversold', semantic: 'low', value: 30},
            ],
        });
        const {markLine} = buildSignalReferencePrimitives(signal, false);
        expect(markLine?.data).toEqual([
            {name: 'Overbought', yAxis: 70},
            {name: 'Oversold', yAxis: 30},
        ]);
    });

    it('formats the markLine label from params.name, defaulting to an empty string', () => {
        const signal = makeSignal({referenceLevels: [{key: 'a', label: 'X', semantic: 's', value: 1}]});
        const {markLine} = buildSignalReferencePrimitives(signal, false);
        const formatter = (markLine!.label as {formatter: (p: {name?: string}) => string}).formatter;
        expect(formatter({name: 'Foo'})).toBe('Foo');
        expect(formatter({})).toBe('');
    });

    it('falls back a region bound to "min"/"max" when the level is open-ended', () => {
        const signal = makeSignal({
            valueRegions: [{key: 'r', label: 'Danger zone', semantic: 'danger', lower: undefined, upper: 90, includeLower: false, includeUpper: true}],
        });
        const {markArea} = buildSignalReferencePrimitives(signal, false);
        expect(markArea?.data).toEqual([[{name: 'Danger zone', yAxis: 'min'}, {yAxis: 90}]]);
    });

    it('uses a bounded region as-is when both edges are given', () => {
        const signal = makeSignal({
            valueRegions: [{key: 'r', label: 'Band', semantic: 'band', lower: 10, upper: 20, includeLower: true, includeUpper: true}],
        });
        const {markArea} = buildSignalReferencePrimitives(signal, false);
        expect(markArea?.data).toEqual([[{name: 'Band', yAxis: 10}, {yAxis: 20}]]);
    });

    it('scales the region fill opacity by isDark mode', () => {
        const signal = makeSignal({valueRegions: [{key: 'r', label: 'Band', semantic: 'band', lower: 0, upper: 1, includeLower: true, includeUpper: true}]});
        const light = buildSignalReferencePrimitives(signal, false).markArea;
        const dark = buildSignalReferencePrimitives(signal, true).markArea;
        expect((light!.itemStyle as {color: string}).color).toBe(toRgba(signal.color, 0.06));
        expect((dark!.itemStyle as {color: string}).color).toBe(toRgba(signal.color, 0.08));
    });
});

describe('updateArrowRotations', () => {
    /** An arrow marker as the charts build it: `symbolRotate` is what `updateArrowRotations` writes. */
    type Marker = {symbol: string; coord: [number, number]; symbolRotate?: unknown};

    /**
     * Minimal echarts.ECharts stub: only the surface updateArrowRotations touches. `getOption()` answers the option object
     * itself — what a first call writes into a marker is what the next call reads, as ECharts' model answers the value
     * written back — and counts its calls (`reads.getOption`, Y-25).
     */
    function makeChart(option: Record<string, unknown>, pixelMap: Record<string, [number, number] | null>, opts: {disposed?: boolean; throwOnConvert?: boolean} = {}) {
        const setOptionCalls: unknown[] = [];
        const reads = {getOption: 0};
        const chart = {
            isDisposed: () => !!opts.disposed,
            getOption: () => {
                reads.getOption += 1;
                return option;
            },
            convertToPixel: (_axis: unknown, coord: unknown) => {
                if (opts.throwOnConvert) throw new Error('layout not ready');
                const key = JSON.stringify(coord);
                if (!(key in pixelMap)) throw new Error(`no pixel mapping stubbed for ${key}`);
                return pixelMap[key];
            },
            setOption: (opt: unknown) => {
                setOptionCalls.push(opt);
            },
        };
        return {chart: chart as unknown as echarts.ECharts, setOptionCalls, reads};
    }

    it('rotates an END marker (backward-found neighbor) to point away — neighbor due right ⇒ 90°', () => {
        // markerIdx=3 (last non-null); backward scan finds index 0. Pixel delta
        // is chosen as dx=10, dy=0: towardNeighborDeg = atan2(-0, 10) = 0°,
        // so symbolRotate = 0 + 90 = 90°.
        const dates = ['d0', 'd1', 'd2', 'd3'];
        const marker: {symbol: string; coord: [number, number]; symbolRotate?: number} = {symbol: 'arrow', coord: [3, 20]};
        const series = {data: [10, null, null, 20], markPoint: {data: [marker]}};
        const option = {xAxis: [{data: dates}], series: [series]};
        const {chart, setOptionCalls} = makeChart(option, {
            '[3,20]': [100, 100],
            '["d0",10]': [110, 100],
        });

        updateArrowRotations(chart);

        expect(marker.symbolRotate).toBeCloseTo(90, 9);
        expect(setOptionCalls).toHaveLength(1);
    });

    it('rotates a START marker (forward-found neighbor) — neighbor straight below in pixel space ⇒ 0°', () => {
        // markerIdx=1 (first non-null, seriesData[0] is null so backward scan
        // finds nothing); forward scan finds index 2. dx=0, dy=10:
        // towardNeighborDeg = atan2(-10, 0) = -90°, symbolRotate = -90+90 = 0°.
        const dates = ['d0', 'd1', 'd2', 'd3'];
        const marker: {symbol: string; coord: [number, number]; symbolRotate?: number} = {symbol: 'arrow', coord: [1, 10]};
        const series = {data: [null, 10, 20, 30], markPoint: {data: [marker]}};
        const option = {xAxis: [{data: dates}], series: [series]};
        const {chart, setOptionCalls} = makeChart(option, {
            '[1,10]': [100, 100],
            '["d2",20]': [100, 110],
        });

        updateArrowRotations(chart);

        expect(marker.symbolRotate).toBeCloseTo(0, 9);
        expect(setOptionCalls).toHaveLength(1);
    });

    it('computes a diagonal rotation exactly — neighbor up-and-left ⇒ 225°', () => {
        // dx=-10, dy=-10: towardNeighborDeg = atan2(10, -10) = 135°,
        // symbolRotate = 135 + 90 = 225°.
        const dates = ['d0', 'd1'];
        const marker: {symbol: string; coord: [number, number]; symbolRotate?: number} = {symbol: 'arrow', coord: [1, 20]};
        const series = {data: [10, 20], markPoint: {data: [marker]}};
        const option = {xAxis: [{data: dates}], series: [series]};
        const {chart, setOptionCalls} = makeChart(option, {
            '[1,20]': [100, 100],
            '["d0",10]': [90, 90],
        });

        updateArrowRotations(chart);

        expect(marker.symbolRotate).toBeCloseTo(225, 9);
        expect(setOptionCalls).toHaveLength(1);
    });

    it('does nothing when the chart is already disposed', () => {
        const marker: {symbol: string; coord: [number, number]; symbolRotate?: number} = {symbol: 'arrow', coord: [1, 20]};
        const series = {data: [10, 20], markPoint: {data: [marker]}};
        const option = {xAxis: [{data: ['d0', 'd1']}], series: [series]};
        const {chart, setOptionCalls} = makeChart(option, {'[1,20]': [100, 100], '["d0",10]': [90, 90]}, {disposed: true});

        updateArrowRotations(chart);

        expect(marker.symbolRotate).toBeUndefined();
        expect(setOptionCalls).toHaveLength(0);
    });

    it('skips markers that are not arrows, and never calls setOption for them', () => {
        const marker: {symbol: string; coord: [number, number]; symbolRotate?: number} = {symbol: 'pin', coord: [1, 20]};
        const series = {data: [10, 20], markPoint: {data: [marker]}};
        const option = {xAxis: [{data: ['d0', 'd1']}], series: [series]};
        const {chart, setOptionCalls} = makeChart(option, {});

        updateArrowRotations(chart);

        expect(marker.symbolRotate).toBeUndefined();
        expect(setOptionCalls).toHaveLength(0);
    });

    it('leaves the marker untouched when no non-null neighbor exists within the search window', () => {
        const marker: {symbol: string; coord: [number, number]; symbolRotate?: number} = {symbol: 'arrow', coord: [0, 10]};
        const series = {data: [10, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null]};
        const option = {xAxis: [{data: series.data.map((_, i) => `d${i}`)}], series: [{...series, markPoint: {data: [marker]}}]};
        const {chart, setOptionCalls} = makeChart(option, {});

        updateArrowRotations(chart);

        expect(marker.symbolRotate).toBeUndefined();
        expect(setOptionCalls).toHaveLength(0);
    });

    it('swallows a convertToPixel failure (chart not laid out yet) without throwing', () => {
        const marker: {symbol: string; coord: [number, number]; symbolRotate?: number} = {symbol: 'arrow', coord: [1, 20]};
        const series = {data: [10, 20], markPoint: {data: [marker]}};
        const option = {xAxis: [{data: ['d0', 'd1']}], series: [series]};
        const {chart, setOptionCalls} = makeChart(option, {}, {throwOnConvert: true});

        expect(() => updateArrowRotations(chart)).not.toThrow();
        expect(marker.symbolRotate).toBeUndefined();
        expect(setOptionCalls).toHaveLength(0);
    });

    it('does nothing when the option has no series at all', () => {
        const {chart, setOptionCalls} = makeChart({}, {});
        expect(() => updateArrowRotations(chart)).not.toThrow();
        expect(setOptionCalls).toHaveLength(0);
    });

    /**
     * Y-25 (a) — a re-aim that turns no arrow writes nothing back.
     *
     * What it protects: the cost of a re-aim with nothing to change. `updateArrowRotations` writes every series back
     * (`setOption({series}, false)`, the data with them) as soon as it aims one arrow, even at the angle the arrow already
     * holds: the stability pass's two resizes after a first draw, a settle that moved nothing, each merges every series
     * again. The contract, after the cure: the series are written back only when an arrow turns by more than
     * `ARROW_ROTATE_EPSILON_DEG` (0.01°), the angle computed being compared with the marker's `symbolRotate` as
     * `getOption()` answers it (a non-number counts as turned, as an arrow never aimed); an arrow within it is left as it
     * is; one arrow turning still writes every series back, the others in it.
     *
     * Red today: a second re-aim of an unchanged chart writes everything back again, and an arrow 0.005° off its angle is
     * rewritten.
     *
     * How it is tested: on `makeChart`, whose `getOption()` answers the option object itself, so the angle a first call
     * writes into a marker is the one the next call reads. The tolerance is probed at half of it and at twice it, never at
     * the boundary, which floating point blurs. Guards, green today and after: an arrow twice the tolerance off is
     * re-aimed, and one arrow turning among others brings one write-back, every series and every arrow in it.
     */
    describe('a re-aim that turns no arrow writes nothing back (Y-25)', () => {
        /** One series whose END arrow, on d3, has its neighbour d0 due right: its angle is exactly 90°. It holds `rotate`. */
        function endArrowDueRight(rotate: unknown) {
            const marker: Marker = {symbol: 'arrow', coord: [3, 20], symbolRotate: rotate};
            const option = {xAxis: [{data: ['d0', 'd1', 'd2', 'd3']}], series: [{data: [10, null, null, 20], markPoint: {data: [marker]}}]};
            return {marker, ...makeChart(option, {'[3,20]': [100, 100], '["d0",10]': [110, 100]})};
        }

        it('a second re-aim, nothing moved since the first, writes nothing back', () => {
            const {marker, chart, setOptionCalls} = endArrowDueRight(0);
            updateArrowRotations(chart);
            expect({rotate: marker.symbolRotate, writeBacks: setOptionCalls.length}, 'precondition: the first re-aim turns the arrow from the 0° it is built with to 90°, and writes the series back').toEqual({rotate: 90, writeBacks: 1});

            updateArrowRotations(chart);

            expect(setOptionCalls.length, 'Y-25: a second re-aim with nothing moved wrote every series back again, at the angle its arrow already held').toBe(1);
        });

        it('an arrow 0.005° off its angle — within the 0.01° tolerance — is left as it is, and nothing is written back', () => {
            const {marker, chart, setOptionCalls} = endArrowDueRight(90.005);

            updateArrowRotations(chart);

            expect({rotate: marker.symbolRotate, writeBacks: setOptionCalls.length}, 'Y-25: an arrow 0.005° off its angle — within ARROW_ROTATE_EPSILON_DEG, 0.01° — was rewritten, and every series written back').toEqual({rotate: 90.005, writeBacks: 0});
        });

        it('an arrow 0.02° off its angle — twice the tolerance — is re-aimed and written back (guard)', () => {
            const {marker, chart, setOptionCalls} = endArrowDueRight(90.02);

            updateArrowRotations(chart);

            expect({rotate: marker.symbolRotate, writeBacks: setOptionCalls.length}, 'an arrow off by more than the tolerance was not re-aimed and written back').toEqual({rotate: 90, writeBacks: 1});
        });

        it('one arrow turning among others brings one write-back, every series in it — the arrow that held its angle too (guard)', () => {
            // `held` (on d3, neighbour d0 due right) already holds its 90°; `turning` (on d1, neighbour d0 up and to the left)
            // is still at the 0° it is built with, and turns to 225°. The price line has no marker.
            const held: Marker = {symbol: 'arrow', coord: [3, 20], symbolRotate: 90};
            const turning: Marker = {symbol: 'arrow', coord: [1, 25], symbolRotate: 0};
            const option = {
                xAxis: [{data: ['d0', 'd1', 'd2', 'd3']}],
                series: [
                    {name: 'price', data: [5, 6, 7, 8]},
                    {name: 'held', data: [10, null, null, 20], markPoint: {data: [held]}},
                    {name: 'turning', data: [15, 25, null, null], markPoint: {data: [turning]}},
                ],
            };
            const {chart, setOptionCalls} = makeChart(option, {'[3,20]': [100, 100], '["d0",10]': [110, 100], '[1,25]': [100, 100], '["d0",15]': [90, 90]});

            updateArrowRotations(chart);

            const writeBacks = setOptionCalls as Array<{series?: Array<{name: string; markPoint?: {data: Marker[]}}>}>;
            expect(
                {
                    writeBacks: writeBacks.length,
                    series: writeBacks[0]?.series?.map((series) => series.name),
                    rotations: writeBacks[0]?.series?.flatMap((series) => series.markPoint?.data.map((marker) => marker.symbolRotate) ?? []),
                },
                'one arrow of two turned: not one write-back carrying every series, both arrows in it',
            ).toEqual({writeBacks: 1, series: ['price', 'held', 'turning'], rotations: [90, expect.closeTo(225, 9)]});
        });
    });

    /**
     * Y-25 (d) — a chart noted without arrow markers is not read for them.
     *
     * What it protects: the cost of re-aiming a chart that has no arrow. Most price charts carry none, yet each re-aim —
     * after every draw, twice in the stability pass that follows the first, at every zoom's settle — reads `getOption()`,
     * a deep copy of the whole option, only to find nothing to aim. The contract, after the cure:
     * `noteArrowMarkers(chart, option)`, called by each chart with the option it has just given whole (no clone), records
     * whether any series has an arrow — a `markPoint.data` item with `symbol: 'arrow'` and a `coord` —; a chart noted
     * without one is skipped by `updateArrowRotations` before `getOption()`. A chart noted again with an arrow is read and
     * aimed again; a chart never noted behaves as before.
     *
     * Red today: `noteArrowMarkers` does not exist — the barrier that reads it off the module fails, naming Y-25.
     *
     * How it is tested: on `makeChart`, which counts its `getOption()` calls. `noteArrowMarkers` is read off the module
     * inside each case (`noteArrowMarkersFn`), so the rest of the file loads while the export is still to come. Guard,
     * green today and after: a chart never noted is read once and aimed, as before.
     */
    describe('a chart noted without arrow markers is not read for them (Y-25)', () => {
        type NoteArrowMarkers = (chart: echarts.ECharts, option: {series?: unknown}) => void;

        /** `noteArrowMarkers`, read off the module when a case runs: the barrier that the export exists (Y-25). */
        async function noteArrowMarkersFn(): Promise<NoteArrowMarkers> {
            const helpers = (await import('../lineChartHelpers')) as {noteArrowMarkers?: unknown};
            expect(typeof helpers.noteArrowMarkers, 'barrier (Y-25): lineChartHelpers exports noteArrowMarkers(chart, option)').toBe('function');
            return helpers.noteArrowMarkers as NoteArrowMarkers;
        }

        /** Two series and a pin marker: markers, but no arrow. */
        const NO_ARROW = {
            xAxis: [{data: ['d0', 'd1']}],
            series: [
                {type: 'line', data: [10, 20]},
                {type: 'line', data: [10, 20], markPoint: {data: [{symbol: 'pin', coord: [1, 20]}]}},
            ],
        };

        it('a chart noted with an option that has no arrow is re-aimed without reading getOption(); a chart beside it, never noted, still reads', async () => {
            const note = await noteArrowMarkersFn();
            const noted = makeChart(NO_ARROW, {});
            const beside = makeChart(NO_ARROW, {});

            note(noted.chart, NO_ARROW);
            updateArrowRotations(noted.chart);
            updateArrowRotations(beside.chart);

            expect(noted.reads.getOption, 'Y-25: a chart noted without arrow markers was read — getOption(), a deep copy of the whole option — only to find none').toBe(0);
            expect(beside.reads.getOption, 'a chart never noted is read as before: a note holds for its own chart only').toBe(1);
        });

        it('the same chart, noted again with an arrow, is read and aimed again: a chart that gains arrows is not left unaimed (guard)', async () => {
            const note = await noteArrowMarkersFn();
            const option: {xAxis: unknown; series: unknown[]} = {xAxis: [{data: ['d0', 'd1']}], series: [{type: 'line', data: [10, 20]}]};
            const {chart, setOptionCalls, reads} = makeChart(option, {'[1,20]': [100, 100], '["d0",10]': [90, 90]});
            note(chart, option);
            updateArrowRotations(chart);
            expect(reads.getOption, 'precondition: noted without arrows, the chart is not read').toBe(0);

            const marker: Marker = {symbol: 'arrow', coord: [1, 20], symbolRotate: 0};
            option.series = [{type: 'line', data: [10, 20], markPoint: {data: [marker]}}];
            note(chart, option);
            updateArrowRotations(chart);

            expect({reads: reads.getOption, writeBacks: setOptionCalls.length, rotate: marker.symbolRotate}, 'a chart noted again, now with an arrow, was not read and aimed').toEqual({reads: 1, writeBacks: 1, rotate: expect.closeTo(225, 9)});
        });

        it('a chart never noted is read and aimed as before (guard)', () => {
            const marker: Marker = {symbol: 'arrow', coord: [1, 20], symbolRotate: 0};
            const option = {xAxis: [{data: ['d0', 'd1']}], series: [{data: [10, 20], markPoint: {data: [marker]}}]};
            const {chart, setOptionCalls, reads} = makeChart(option, {'[1,20]': [100, 100], '["d0",10]': [90, 90]});

            updateArrowRotations(chart);

            expect({reads: reads.getOption, writeBacks: setOptionCalls.length, rotate: marker.symbolRotate}, 'a chart never noted was not read and aimed as before').toEqual({reads: 1, writeBacks: 1, rotate: expect.closeTo(225, 9)});
        });
    });
});
