/**
 * echartsDataZoomSync.ts — bidirectional dataZoom (zoom + pan) sync bridge between two
 * independent ECharts instances that share the SAME x-axis extent (e.g. both configured
 * with the same explicit `xAxis.min`/`max`), so a percentage-based start/end window means
 * the exact same absolute range on both.
 *
 * Deliberately NOT using echarts.connect() — that global API also cross-links tooltips
 * (showTip/hideTip) and other actions across every chart in the group, replaying each
 * chart's OWN dataIndex/seriesIndex on its peers, which doesn't correspond to anything
 * meaningful when the two charts have structurally different series (e.g. line-based
 * price/WAC chart vs scatter/timeline chart) — could show mismatched or empty
 * tooltips on hover. This module only ever propagates the numeric dataZoom start/end
 * window, nothing else.
 */
import type {ECharts} from 'echarts';
import {getChartZoomWindow} from './chartCoreHelpers';

/** Tolerance (percentage points) below which two zoom windows are treated as already
 *  matching, to avoid an infinite dispatch/event ping-pong between linked charts:
 *  chart A's user-driven zoom fires onZoomChange → shared parent state updates → both
 *  charts' applyExternal() are called (including A's own, echoed back) → without this
 *  guard, A would immediately re-dispatch its own already-current window, re-firing its
 *  'dataZoom' event, re-invoking onZoomChange, ad infinitum. */
const ZOOM_SYNC_EPSILON = 0.05;

export interface DataZoomSyncHandle {
    /** Call whenever the externally-shared zoom window changes (e.g. because a SECOND,
     *  linked chart's own dataZoom event fired). Applies it to this chart, but no-ops if
     *  this chart's own current window already (approximately) matches — see
     *  ZOOM_SYNC_EPSILON above for why that's essential. */
    applyExternal: (start: number, end: number) => void;
    /** Detach the bridge's dataZoom listener. Call on chart disposal. */
    dispose: () => void;
}

/**
 * Attach a dataZoom-change reporter to `chart`. Calls `onZoomChange(start, end)` — typically
 * writing to shared parent state — whenever the user, or a programmatic `dispatchAction`
 * (including one triggered by this same handle's own `applyExternal`), changes its zoom
 * window. The returned handle's `applyExternal` lets the caller push an externally-sourced
 * zoom window (e.g. from a second, linked chart) back onto this chart.
 */
export function attachDataZoomSync(chart: ECharts, onZoomChange: (start: number, end: number) => void): DataZoomSyncHandle {
    const handleDataZoom = () => {
        const zoom = getChartZoomWindow(chart);
        if (zoom) onZoomChange(zoom.start, zoom.end);
    };
    chart.on('dataZoom', handleDataZoom);

    return {
        applyExternal(start: number, end: number) {
            const current = getChartZoomWindow(chart);
            if (current && Math.abs(current.start - start) < ZOOM_SYNC_EPSILON && Math.abs(current.end - end) < ZOOM_SYNC_EPSILON) {
                return; // already in sync — avoids the re-dispatch/event ping-pong described above
            }
            chart.dispatchAction({type: 'dataZoom', start, end});
        },
        dispose() {
            chart.off('dataZoom', handleDataZoom);
        },
    };
}
