/**
 * Centralized ECharts animation configuration.
 *
 * All 2D charts (line, area, candlestick, pie) import from here
 * to ensure consistent animation behavior across the app.
 *
 * Design goals:
 * - Points that share the same date translate vertically to new Y position
 * - Timeline expands/contracts smoothly when period changes
 * - New points fade in, removed points fade out
 * - Pie segments morph smoothly between values
 *
 * Key insight from ECharts docs:
 * "This diff is based on the name of the data... data 'B','C' will be updated,
 *  data 'A' will be removed, and data 'D' will be added."
 *
 * For this to work:
 * - Use `notMerge: false` so ECharts performs diff against previous state
 * - Use `replaceMerge: ['series']` so series are matched by name and diffed
 * - With xAxis type='time', points at the same X coordinate get update animations
 *
 * @module components/charts/echartsAnimationConfig
 */

import type {EChartsOption} from 'echarts';

/**
 * Base animation options to spread into every ECharts option object.
 * Use with `xAxis: { type: 'time' }` and data as `[[date, value], ...]`
 * for best transition effect on period changes.
 */
export const CHART_ANIMATION_CONFIG: Partial<EChartsOption> = {
    animation: true,
    animationDuration: 600,
    animationDurationUpdate: 800,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicOut',
};

/**
 * setOption flags for chart updates with time axis and named data points.
 * `notMerge: false` + `replaceMerge: ['series']` enables ECharts diffing:
 * - Series matched by `name` → data points diffed → update animation
 * - New data points → enter animation (fade in)
 * - Removed data points → leave animation (fade out)
 * - Shared data points (same name/X coord) → translate to new Y position
 */
export const CHART_SET_OPTION_OPTS: {notMerge: boolean; replaceMerge: string[]} = {notMerge: false, replaceMerge: ['series']};

/**
 * Convert a date+value pair into an ECharts named data point.
 *
 * ECharts uses the `name` property to diff data between updates.
 * Points with the same `name` in old and new data get UPDATE animation
 * (translate to new Y position). Points with new `name`s ENTER,
 * removed `name`s EXIT.
 *
 * @see https://stackoverflow.com/questions/64010424/echarts-animation-after-append-data
 *
 * @param date  ISO date string (used as unique identifier)
 * @param value Numeric value (or null for gaps)
 */
export function namedPoint(date: string, value: number | null): {name: string; value: [string, number | null]} {
    return {name: date, value: [date, value]};
}
