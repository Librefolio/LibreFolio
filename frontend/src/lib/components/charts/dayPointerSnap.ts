/**
 * The pointer of a step chart rests on a day, never between two (Y2 FB-2).
 *
 * The time axis of a step chart sets `axisPointer.snap: false` (the tooltip reads the pointed day, see `stepTooltip`), so ECharts leaves
 * the pointer line wherever the mouse is, even halfway between a Friday and a Saturday. `attachDaySnap` moves it to the nearest day: when an
 * `updateAxisPointer` event carries a value that is not a local midnight, it dispatches the same action again with the value of the
 * nearest day, at that day's pixel and at the mouse's height. The second event carries a midnight, so it ends there.
 *
 * @module components/charts/dayPointerSnap
 */

import {snapToDay} from '$lib/utils/stepSeries';

/** What `attachDaySnap` uses of an ECharts instance. */
export interface DaySnapChart {
    on: (event: string, handler: (event: any) => void) => void;
    off?: (event: string, handler: (event: any) => void) => void;
    getZr: () => {on: (event: string, handler: (event: {offsetY: number}) => void) => void};
    convertToPixel: (finder: {xAxisIndex: number}, value: number) => number | number[];
    dispatchAction: (payload: {type: string; [field: string]: unknown}) => void;
}

/** Per instance: the mouse height its one `mousemove` listener keeps, and the `updateAxisPointer` handler to replace on a second call. */
const attached = new WeakMap<object, {mouseY: number; handler: (event: any) => void}>();

/**
 * Make the pointer of `chart`'s first time axis rest on days. Safe to call again on the same instance (a chart that redraws calls it every
 * time): the mouse listener is added once and the pointer handler is replaced, never stacked.
 */
export function attachDaySnap(chart: DaySnapChart): void {
    let state = attached.get(chart);
    const again = state !== undefined;
    if (!state) {
        const fresh = {mouseY: 0, handler: (_event: any) => {}};
        chart.getZr?.()?.on('mousemove', (event) => {
            fresh.mouseY = event.offsetY;
        });
        state = fresh;
        attached.set(chart, state);
    }
    const kept = state;
    if (again) chart.off?.('updateAxisPointer', kept.handler);
    kept.handler = (event: {axesInfo?: Array<{value?: unknown; axisDim?: string; axisIndex?: number}>}) => {
        const info = event.axesInfo?.[0];
        const value = info?.value;
        if (typeof value !== 'number' || !Number.isFinite(value)) return;
        const {ms} = snapToDay(value);
        if (Math.abs(ms - value) < 1) return;
        const pixel = chart.convertToPixel({xAxisIndex: 0}, ms);
        const x = Array.isArray(pixel) ? pixel[0] : pixel;
        if (typeof x !== 'number' || !Number.isFinite(x)) return;
        chart.dispatchAction({type: 'updateAxisPointer', currTrigger: 'mousemove', x, y: kept.mouseY, axesInfo: [{axisDim: info?.axisDim ?? 'x', axisIndex: info?.axisIndex ?? 0, value: ms}]});
    };
    chart.on('updateAxisPointer', kept.handler);
}
