/**
 * The shape of the lines of every chart (Y2 FB-3), and the one place that turns it into ECharts options.
 *
 * - `segments` (the default): two points are joined by a straight segment.
 * - `steps`: a point holds its value to the next one (`step: 'end'`), which is what a step report says.
 * - `spline`: a smooth curve through the points that never leaves the range of two neighbours
 *   (`smooth` with `smoothMonotone: 'x'`). A free spline is not offered: it draws values that never existed.
 *
 * A chart does not set `step` or `smooth` itself: it hands its finished series to `applyLineShape`, one line.
 *
 * @module components/charts/lineShape
 */

import type * as echarts from 'echarts';

export type LineShape = 'segments' | 'steps' | 'spline';

export const LINE_SHAPES: readonly LineShape[] = ['segments', 'steps', 'spline'];

export const DEFAULT_LINE_SHAPE: LineShape = 'segments';

export function isLineShape(value: unknown): value is LineShape {
    return LINE_SHAPES.includes(value as LineShape);
}

/** The ECharts options of one shape: always the three keys, so a shape change overwrites the previous one on a partial merge. */
export interface LineShapeOptions {
    step: 'end' | false;
    smooth: boolean;
    smoothMonotone?: 'x';
}

export function lineShapeOptions(shape: LineShape): LineShapeOptions {
    if (shape === 'steps') return {step: 'end', smooth: false};
    if (shape === 'spline') return {step: false, smooth: true, smoothMonotone: 'x'};
    return {step: false, smooth: false};
}

/**
 * The shape a chart can draw. Steps are drawn only where the points are real steps (`holdsValue`): a chart whose points are
 * a bucket's value (a week, a month) joins them with segments whatever the setting.
 */
export function effectiveLineShape(shape: LineShape, holdsValue = true): LineShape {
    return shape === 'steps' && !holdsValue ? 'segments' : shape;
}

/** Whether a chart on this setting draws steps its tooltip must read by the day under the pointer. */
export function drawsSteps(shape: LineShape, holdsValue = true): boolean {
    return effectiveLineShape(shape, holdsValue) === 'steps';
}

/** How a chart tells `applyLineShape` about its series. */
export interface ApplyLineShapeOptions {
    /** False when the points are a bucket's value, not steps: steps are then drawn as segments (see `effectiveLineShape`). Default true. */
    holdsValue?: boolean;
    /** A line of true values (the history's MWRR): it never takes steps, it takes segments in their place. */
    isTrueValues?: (entry: echarts.SeriesOption) => boolean;
}

/** The series with the shape applied to every line. Anything that is not a line is returned as it is. */
export function applyLineShape(series: readonly echarts.SeriesOption[], shape: LineShape, options: ApplyLineShapeOptions = {}): echarts.SeriesOption[] {
    const wanted = effectiveLineShape(shape, options.holdsValue ?? true);
    return series.map((entry) => {
        if (entry.type !== 'line') return entry;
        const applied = wanted === 'steps' && options.isTrueValues?.(entry) ? 'segments' : wanted;
        return {...entry, ...lineShapeOptions(applied)} as echarts.SeriesOption;
    });
}
