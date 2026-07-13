/**
 * echartsDataZoomTouchPan.ts — manual two-finger drag-to-pan bridge for "inside"
 * dataZoom charts (line/candlestick/scatter) on touch devices.
 *
 * WHY TWO FINGERS, NOT ONE (same rationale as echartsTreemapZoomGuard.ts's touch-pan
 * bridge — see that file's handleTouchPanStart doc comment for the full zrender-verified
 * background): touch-sourced pointer movement is unreliable for RoamController-driven
 * pan (`moveOnMouseMove`) on modern mobile browsers, and a browser locks in its
 * native-scroll-vs-JS-gesture decision at the START of a touch sequence, never handing
 * it back mid-gesture even once nothing is left to pan. Reserving ONE finger exclusively
 * for native page scroll (zero exceptions, zero JS involvement — this file never attaches
 * any single-finger handling) and TWO fingers for chart pan sidesteps both problems
 * identically to the treemap's own bridge. Two-finger pinch-to-zoom (already working via
 * ECharts' own dedicated pinch path) is untouched by this — this only ever shifts the
 * dataZoom window, never its width, so a real 2-finger gesture that both translates and
 * pinches at once still composes naturally.
 */
import type {ECharts} from 'echarts';
import {getChartZoomWindow} from './chartCoreHelpers';

export interface DataZoomTouchPanHandle {
    /** Detach the bridge's touch listeners. Call on chart disposal. */
    dispose: () => void;
}

/**
 * Attach the two-finger touch-pan bridge to a chart using "inside" dataZoom.
 *
 * @param chart The ECharts instance hosting the dataZoom.
 * @param container The DOM element to listen for touch gestures on (typically the same
 *   element passed to `echarts.init()`).
 */
export function attachDataZoomTouchPan(chart: ECharts, container: HTMLElement): DataZoomTouchPanHandle {
    let panState: {x: number} | null = null;

    function centroidX(touches: TouchList): number {
        let x = 0;
        for (let i = 0; i < touches.length; i++) x += touches[i].clientX;
        return x / touches.length;
    }

    function handleStart(e: TouchEvent) {
        panState = e.touches.length === 2 ? {x: centroidX(e.touches)} : null;
    }

    function handleMove(e: TouchEvent) {
        if (e.touches.length !== 2) {
            // Finger count changed mid-gesture (e.g. one lifted) — stop tracking rather
            // than computing a bogus delta against a stale reference point.
            panState = null;
            return;
        }
        if (!panState) return;
        const x = centroidX(e.touches);
        const dx = x - panState.x;
        panState = {x};
        if (dx === 0) return;

        const zoom = getChartZoomWindow(chart);
        if (!zoom) return;
        const width = zoom.end - zoom.start;
        if (width <= 0) return;
        const containerWidth = container.clientWidth || 1;
        // Content follows the finger: dragging right reveals earlier data, i.e. the
        // visible window shifts backward (start/end decrease) — same convention as
        // ECharts' own built-in inside-dataZoom drag-pan.
        const percentDelta = (dx / containerWidth) * width;

        let newStart = zoom.start - percentDelta;
        let newEnd = zoom.end - percentDelta;
        if (newStart < 0) {
            newEnd -= newStart;
            newStart = 0;
        }
        if (newEnd > 100) {
            newStart -= newEnd - 100;
            newEnd = 100;
        }
        newStart = Math.max(0, newStart);
        newEnd = Math.min(100, newEnd);

        // Two-finger gestures never compete with native single-finger scroll, so this
        // preventDefault only ever suppresses the browser's own pinch-zoom-the-page
        // gesture — it can't block page scroll, which is exactly the point.
        e.preventDefault();
        chart.dispatchAction({type: 'dataZoom', start: newStart, end: newEnd});
    }

    function handleEnd(e: TouchEvent) {
        // Re-arm if exactly 2 touches remain (e.g. a 3rd finger lifted back to 2);
        // otherwise stop — a drop to 0 or 1 remaining touch ends the pan gesture.
        panState = e.touches.length === 2 ? {x: centroidX(e.touches)} : null;
    }

    container.addEventListener('touchstart', handleStart, {passive: true});
    container.addEventListener('touchmove', handleMove, {passive: false});
    container.addEventListener('touchend', handleEnd, {passive: true});
    container.addEventListener('touchcancel', handleEnd, {passive: true});

    return {
        dispose: () => {
            container.removeEventListener('touchstart', handleStart);
            container.removeEventListener('touchmove', handleMove);
            container.removeEventListener('touchend', handleEnd);
            container.removeEventListener('touchcancel', handleEnd);
        },
    };
}
