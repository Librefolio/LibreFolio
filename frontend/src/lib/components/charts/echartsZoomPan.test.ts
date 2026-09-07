// @vitest-environment jsdom
/**
 * echarts zoom / pan / treemap-guard bridges — unit test (Vitest + jsdom).
 *
 * These three modules exist because ECharts' own touch and roam handling is
 * either absent (touch-sourced pan) or broken (treemap cumulative-scale
 * bookkeeping) on the paths the app relies on, so each reimplements the missing
 * arithmetic and drives ECharts back through `dispatchAction`. That arithmetic —
 * the ping-pong epsilon guard, the drag-to-window conversion with its edge
 * clamps, and the treemap scale/position clamping — is exactly where the bugs
 * are and exactly what a canvas cannot help test. So the ECharts instance is a
 * hand-written stub that records `dispatchAction` calls and lets the test fire
 * the chart events itself; nothing is drawn.
 *
 * jsdom (not node) because the touch-pan bridge attaches real listeners to a
 * real container and is driven with synthetic touch events.
 */
import {describe, expect, it, vi} from 'vitest';
import {attachDataZoomSync} from './echartsDataZoomSync';
import {attachDataZoomTouchPan} from './echartsDataZoomTouchPan';
import {attachTreemapZoomGuard, panTreemapBy, resetTreemapView} from './echartsTreemapZoomGuard';

// ---------------------------------------------------------------------------
// A minimal ECharts stub: enough surface for the three bridges, plus test hooks.
// ---------------------------------------------------------------------------
type Listener = (params?: unknown) => void;

function fakeChart(dz?: {start: number; end: number}) {
    const listeners: Record<string, Listener[]> = {};
    let dataZoom = dz ? [{start: dz.start, end: dz.end}] : undefined;
    return {
        on(ev: string, cb: Listener) {
            (listeners[ev] ??= []).push(cb);
        },
        off(ev: string, cb: Listener) {
            listeners[ev] = (listeners[ev] ?? []).filter((f) => f !== cb);
        },
        getOption: () => ({dataZoom}),
        getWidth: () => 640,
        getHeight: () => 480,
        dispatchAction: vi.fn((action: {type: string; start?: number; end?: number}) => {
            if (action.type === 'dataZoom' && action.start != null && action.end != null) {
                dataZoom = [{start: action.start, end: action.end}];
            }
        }),
        // test hooks
        _fire: (ev: string, params?: unknown) => (listeners[ev] ?? []).forEach((f) => f(params)),
        _setWindow: (start: number, end: number) => {
            dataZoom = [{start, end}];
        },
        _count: (ev: string) => (listeners[ev] ?? []).length,
    };
}

/** A synthetic TouchEvent good enough for the bridges (they read length/clientX). */
function touch(type: string, xs: number[]): TouchEvent {
    const e = new Event(type, {bubbles: true, cancelable: true}) as unknown as {touches: unknown};
    e.touches = xs.map((clientX) => ({clientX, clientY: 0}));
    return e as unknown as TouchEvent;
}

describe('attachDataZoomSync', () => {
    it('reports the zoom window to the callback when the chart fires dataZoom', () => {
        const chart = fakeChart({start: 10, end: 90});
        const onZoom = vi.fn();
        attachDataZoomSync(chart as never, onZoom);

        chart._setWindow(20, 80);
        chart._fire('dataZoom');
        expect(onZoom).toHaveBeenCalledWith(20, 80);
    });

    it('does not report when the chart has no dataZoom window', () => {
        const chart = fakeChart(); // no dataZoom in option
        const onZoom = vi.fn();
        attachDataZoomSync(chart as never, onZoom);
        chart._fire('dataZoom');
        expect(onZoom).not.toHaveBeenCalled();
    });

    it('pushes an out-of-sync external window onto the chart', () => {
        const chart = fakeChart({start: 0, end: 100});
        const {applyExternal} = attachDataZoomSync(chart as never, vi.fn());
        applyExternal(25, 75);
        expect(chart.dispatchAction).toHaveBeenCalledWith({type: 'dataZoom', start: 25, end: 75});
    });

    it('ignores an external window already within epsilon — the ping-pong guard', () => {
        const chart = fakeChart({start: 25, end: 75});
        const {applyExternal} = attachDataZoomSync(chart as never, vi.fn());
        applyExternal(25.01, 74.99); // both deltas < 0.05
        expect(chart.dispatchAction).not.toHaveBeenCalled();
    });

    it('applies an external window when the chart has no current window to compare', () => {
        const chart = fakeChart(); // getChartZoomWindow → null
        const {applyExternal} = attachDataZoomSync(chart as never, vi.fn());
        applyExternal(30, 70);
        expect(chart.dispatchAction).toHaveBeenCalledWith({type: 'dataZoom', start: 30, end: 70});
    });

    it('detaches its listener on dispose', () => {
        const chart = fakeChart({start: 0, end: 100});
        const onZoom = vi.fn();
        const {dispose} = attachDataZoomSync(chart as never, onZoom);
        expect(chart._count('dataZoom')).toBe(1);
        dispose();
        expect(chart._count('dataZoom')).toBe(0);
        chart._fire('dataZoom');
        expect(onZoom).not.toHaveBeenCalled();
    });
});

describe('attachDataZoomTouchPan', () => {
    function container() {
        const el = document.createElement('div');
        Object.defineProperty(el, 'clientWidth', {value: 1000, configurable: true});
        document.body.appendChild(el);
        return el;
    }

    it('shifts the zoom window backward when two fingers drag right', () => {
        const chart = fakeChart({start: 20, end: 60}); // width 40
        const el = container();
        attachDataZoomTouchPan(chart as never, el);

        el.dispatchEvent(touch('touchstart', [100, 200])); // centroid 150
        el.dispatchEvent(touch('touchmove', [200, 300])); // centroid 250 → dx +100
        // percentDelta = (100/1000)*40 = 4 → window shifts back by 4 → [16, 56]
        expect(chart.dispatchAction).toHaveBeenCalledWith({type: 'dataZoom', start: 16, end: 56});
    });

    it('clamps at the left edge without shrinking the window', () => {
        const chart = fakeChart({start: 2, end: 42}); // width 40
        const el = container();
        attachDataZoomTouchPan(chart as never, el);
        el.dispatchEvent(touch('touchstart', [100, 100]));
        // dx +100 → percentDelta 4 → newStart 2-4=-2, newEnd 42-4=38; clamp lifts
        // start to 0 and gives the 2 back to end (38-(-2)) → width 40 preserved.
        el.dispatchEvent(touch('touchmove', [200, 200]));
        expect(chart.dispatchAction).toHaveBeenCalledWith({type: 'dataZoom', start: 0, end: 40});
    });

    it('clamps at the right edge without shrinking the window', () => {
        const chart = fakeChart({start: 58, end: 98}); // width 40
        const el = container();
        attachDataZoomTouchPan(chart as never, el);
        el.dispatchEvent(touch('touchstart', [200, 200])); // centroid 200
        // drag left dx -100 → percentDelta -4 → newStart 62, newEnd 102 → clamp end 100, start 60
        el.dispatchEvent(touch('touchmove', [100, 100]));
        expect(chart.dispatchAction).toHaveBeenCalledWith({type: 'dataZoom', start: 60, end: 100});
    });

    it('does nothing on a one-finger drag', () => {
        const chart = fakeChart({start: 20, end: 60});
        const el = container();
        attachDataZoomTouchPan(chart as never, el);
        el.dispatchEvent(touch('touchstart', [100])); // 1 finger → not tracked
        el.dispatchEvent(touch('touchmove', [200]));
        expect(chart.dispatchAction).not.toHaveBeenCalled();
    });

    it('does nothing when the centroid did not move', () => {
        const chart = fakeChart({start: 20, end: 60});
        const el = container();
        attachDataZoomTouchPan(chart as never, el);
        el.dispatchEvent(touch('touchstart', [100, 200]));
        el.dispatchEvent(touch('touchmove', [100, 200])); // dx 0
        expect(chart.dispatchAction).not.toHaveBeenCalled();
    });

    it('stops tracking when a finger lifts mid-gesture', () => {
        const chart = fakeChart({start: 20, end: 60});
        const el = container();
        attachDataZoomTouchPan(chart as never, el);
        el.dispatchEvent(touch('touchstart', [100, 200]));
        el.dispatchEvent(touch('touchmove', [150])); // dropped to 1 finger → panState cleared
        el.dispatchEvent(touch('touchmove', [400])); // still 1 finger → ignored
        expect(chart.dispatchAction).not.toHaveBeenCalled();
    });

    it('re-arms from a two-finger touchend and detaches on dispose', () => {
        const chart = fakeChart({start: 20, end: 60});
        const el = container();
        const {dispose} = attachDataZoomTouchPan(chart as never, el);
        // touchend leaving 2 fingers re-seeds the reference centroid
        el.dispatchEvent(touch('touchend', [300, 500])); // centroid 400
        el.dispatchEvent(touch('touchmove', [350, 550])); // centroid 450 → dx +50 → shift back 2
        expect(chart.dispatchAction).toHaveBeenCalledWith({type: 'dataZoom', start: 18, end: 58});

        chart.dispatchAction.mockClear();
        dispose();
        el.dispatchEvent(touch('touchstart', [100, 200]));
        el.dispatchEvent(touch('touchmove', [200, 300]));
        expect(chart.dispatchAction).not.toHaveBeenCalled();
    });
});

describe('attachTreemapZoomGuard', () => {
    const CONTAINER = {width: 400, height: 300};

    /** Capture the guard's handler so the test can fire treemap events at will. */
    function guarded(options?: Parameters<typeof attachTreemapZoomGuard>[2]) {
        const chart = fakeChart();
        const handle = attachTreemapZoomGuard(chart as never, () => CONTAINER, options);
        return {chart, handle};
    }

    it('leaves a rect that exactly fills the container untouched but still reports scale 1', () => {
        const onScaleChange = vi.fn();
        const {chart} = guarded({onScaleChange});
        chart._fire('treemaprender', {rootRect: {x: 0, y: 0, width: 400, height: 300}});
        expect(chart.dispatchAction).not.toHaveBeenCalled();
        expect(onScaleChange).toHaveBeenCalledWith(1, {x: 0, y: 0, width: 400, height: 300});
    });

    it('clamps an over-zoomed rect down to maxScale', () => {
        const onScaleChange = vi.fn();
        const {chart} = guarded({maxScale: 5, onScaleChange});
        // width 4000 = scale 10 on a 400 container → clamp to 5 → width 2000
        chart._fire('treemaprender', {rootRect: {x: -1800, y: -850, width: 4000, height: 3000}});
        expect(onScaleChange.mock.calls[0][0]).toBe(5);
        expect(chart.dispatchAction).toHaveBeenCalledTimes(1);
        const arg = chart.dispatchAction.mock.calls[0][0] as unknown as {rootRect: {width: number; height: number}};
        expect(arg.rootRect.width).toBe(2000);
        expect(arg.rootRect.height).toBe(1500);
    });

    it('clamps a shrunk rect back up to minScale', () => {
        const {chart} = guarded({minScale: 1, maxScale: 5});
        // width 200 = scale 0.5 → clamp up to 1 → width 400
        chart._fire('treemaprender', {rootRect: {x: 100, y: 75, width: 200, height: 150}});
        const arg = chart.dispatchAction.mock.calls[0][0] as unknown as {rootRect: {width: number; height: number; x: number; y: number}};
        expect(arg.rootRect.width).toBe(400);
        expect(arg.rootRect.height).toBe(300);
    });

    it('clamps pan so a zoomed rect keeps covering the container (no blank walls)', () => {
        const {chart} = guarded({maxScale: 5});
        // scale 2 (width 800, height 600), but dragged far down-right so its top-left
        // is at +100/+100 — that would expose blank space top and left.
        chart._fire('treemaprender', {rootRect: {x: 100, y: 100, width: 800, height: 600}});
        const arg = chart.dispatchAction.mock.calls[0][0] as unknown as {rootRect: {x: number; y: number}};
        // x must be in [container-rect, 0] = [-400, 0] → clamped to 0; same for y in [-300,0]
        expect(arg.rootRect.x).toBe(0);
        expect(arg.rootRect.y).toBe(0);
    });

    it('centres the rect when it is smaller than the container (minScale below 1)', () => {
        const onScaleChange = vi.fn();
        const {chart} = guarded({minScale: 0.5, maxScale: 5, onScaleChange});
        // scale 0.5 allowed → width 200 < 400 → centred at (400-200)/2 = 100, (300-150)/2 = 75
        chart._fire('treemaprender', {rootRect: {x: 0, y: 0, width: 200, height: 150}});
        const reported = onScaleChange.mock.calls[0][1] as {x: number; y: number};
        expect(reported.x).toBe(100);
        expect(reported.y).toBe(75);
    });

    it('evaluates a function maxScale live on each event', () => {
        // A fresh guard per cap: with no real ECharts echo, `correcting` stays armed
        // after a correction, so re-firing the same chart would be swallowed. Two
        // independent guards keep each evaluation on a clean, non-correcting state.
        const capped = (cap: number) => {
            const {chart} = guarded({maxScale: () => cap});
            chart._fire('treemaprender', {rootRect: {x: 0, y: 0, width: 4000, height: 3000}});
            return (chart.dispatchAction.mock.calls[0][0] as unknown as {rootRect: {width: number}}).rootRect.width;
        };
        // container 400 wide → cap 2 clamps width to 800, cap 3 to 1200.
        expect(capped(2)).toBe(800);
        expect(capped(3)).toBe(1200);
    });

    it('ignores its own corrective event to avoid an infinite loop', () => {
        const {chart} = guarded({maxScale: 5});
        // First event triggers a correction (dispatchAction #1) and arms `correcting`.
        chart._fire('treemaprender', {rootRect: {x: 0, y: 0, width: 4000, height: 3000}});
        expect(chart.dispatchAction).toHaveBeenCalledTimes(1);
        // The echoed treemaprender from our own dispatch must be swallowed.
        chart._fire('treemaprender', {rootRect: {x: 0, y: 0, width: 2000, height: 1500}});
        expect(chart.dispatchAction).toHaveBeenCalledTimes(1);
    });

    it('ignores an event with no usable rect', () => {
        const {chart} = guarded();
        chart._fire('treemaprender', {rootRect: {x: 0, y: 0, width: 0, height: 0}});
        chart._fire('treemaprender', {});
        expect(chart.dispatchAction).not.toHaveBeenCalled();
    });

    it('detaches both listeners on dispose', () => {
        const {chart, handle} = guarded();
        expect(chart._count('treemaprender')).toBe(1);
        expect(chart._count('treemapmove')).toBe(1);
        handle.dispose();
        expect(chart._count('treemaprender')).toBe(0);
        expect(chart._count('treemapmove')).toBe(0);
    });
});

describe('treemap view actions', () => {
    it('resetTreemapView dispatches a full-container root rect', () => {
        const chart = fakeChart();
        resetTreemapView(chart as never);
        expect(chart.dispatchAction).toHaveBeenCalledWith({type: 'treemapRender', rootRect: {x: 0, y: 0, width: 640, height: 480}});
    });

    it('panTreemapBy offsets the given rect by the pixel delta', () => {
        const chart = fakeChart();
        panTreemapBy(chart as never, 15, -5, {x: 10, y: 20, width: 100, height: 80});
        expect(chart.dispatchAction).toHaveBeenCalledWith({type: 'treemapMove', rootRect: {x: 25, y: 15, width: 100, height: 80}});
    });
});
