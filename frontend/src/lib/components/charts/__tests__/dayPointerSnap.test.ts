/**
 * `attachDaySnap` — the pointer line of a step chart rests on a day (Y2 FB-2).
 *
 * A fake ECharts instance records the handlers and the dispatched actions: a pointer between two days is redispatched on the nearest day,
 * at that day's pixel and the mouse's height; a pointer already on a day is left alone (so the second event ends the loop).
 */
import {describe, expect, it} from 'vitest';
import {attachDaySnap, type DaySnapChart} from '../dayPointerSnap';

const at = (year: number, month: number, day: number, hours = 0) => new Date(year, month - 1, day, hours).getTime();

function fakeChart() {
    const handlers: Record<string, (event: any) => void> = {};
    const registered: Record<string, Array<(event: any) => void>> = {};
    let zrListeners = 0;
    const zr: Record<string, (event: any) => void> = {};
    const dispatched: Array<Record<string, unknown>> = [];
    const chart: DaySnapChart = {
        on: (name, handler) => {
            handlers[name] = handler;
            registered[name] = [...(registered[name] ?? []), handler];
        },
        off: (name, handler) => {
            registered[name] = (registered[name] ?? []).filter((entry) => entry !== handler);
        },
        getZr: () => ({
            on: (name, handler) => {
                zr[name] = handler;
                zrListeners += 1;
            },
        }),
        convertToPixel: (_finder, value) => value / 1_000_000_000,
        dispatchAction: (payload) => {
            dispatched.push(payload);
        },
    };
    return {chart, handlers, zr, dispatched, registered, zrListeners: () => zrListeners};
}

describe('attachDaySnap', () => {
    it('moves a pointer between two days to the nearest day, at the mouse height', () => {
        const {chart, handlers, zr, dispatched} = fakeChart();
        attachDaySnap(chart);
        zr.mousemove({offsetY: 77});
        handlers.updateAxisPointer({axesInfo: [{axisDim: 'x', axisIndex: 0, value: at(2026, 10, 12, 18)}]});
        expect(dispatched).toHaveLength(1);
        expect(dispatched[0]).toMatchObject({type: 'updateAxisPointer', currTrigger: 'mousemove', y: 77, x: at(2026, 10, 13) / 1_000_000_000, axesInfo: [{axisDim: 'x', axisIndex: 0, value: at(2026, 10, 13)}]});
    });

    it('leaves a pointer already on a day alone', () => {
        const {chart, handlers, dispatched} = fakeChart();
        attachDaySnap(chart);
        handlers.updateAxisPointer({axesInfo: [{axisDim: 'x', axisIndex: 0, value: at(2026, 10, 13)}]});
        expect(dispatched).toEqual([]);
    });

    it('ignores an event without a pointer value (the pointer left the chart)', () => {
        const {chart, handlers, dispatched} = fakeChart();
        attachDaySnap(chart);
        handlers.updateAxisPointer({});
        handlers.updateAxisPointer({axesInfo: [{value: undefined}]});
        expect(dispatched).toEqual([]);
    });

    it('called again on the same instance (a chart that redraws), replaces its pointer handler and adds no second mouse listener', () => {
        const {chart, registered, zrListeners} = fakeChart();
        attachDaySnap(chart);
        attachDaySnap(chart);
        attachDaySnap(chart);
        expect(registered.updateAxisPointer, 'one pointer handler, never stacked').toHaveLength(1);
        expect(zrListeners(), 'one mouse listener').toBe(1);
    });

    it('keeps a handler another caller registered on the same event', () => {
        const {chart, registered} = fakeChart();
        const other = () => {};
        chart.on('updateAxisPointer', other);
        attachDaySnap(chart);
        attachDaySnap(chart);
        expect(registered.updateAxisPointer).toContain(other);
        expect(registered.updateAxisPointer).toHaveLength(2);
    });
});
