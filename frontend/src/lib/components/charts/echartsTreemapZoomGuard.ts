/**
 * echartsTreemapZoomGuard — enforces a hard cumulative zoom limit AND pan bounds for
 * ECharts treemaps.
 *
 * ROOT CAUSE (verified by reading node_modules/echarts/lib/chart/treemap/TreemapView.js):
 * `scaleLimit` IS read by `_onZoom` and clamps each individual wheel/pinch tick's delta —
 * but `_resetController` (called on EVERY render, including the internal re-render
 * triggered by the very `treemapRender` action that `_onZoom` itself dispatches) resets
 * `controllerHost.zoom = seriesModel.get('zoom')`, which is `undefined` because we never
 * declare a static `zoom` in the option. This means the clamp only ever sees a *single
 * tick's* delta (never the true cumulative scale), so repeated zoom-out ticks compound
 * multiplicatively with no floor — the treemap can be shrunk to a tiny dot. The same
 * broken bookkeeping also lets `_onPan` drag the root rect arbitrarily far off-screen
 * (no built-in "stay within container" constraint), leaving blank "walls" visible.
 *
 * FIX: listen for BOTH the `treemaprender` chart event (fired whenever `_onZoom`/drill-down
 * dispatches a `treemapRender` action) AND the `treemapmove` chart event (fired by `_onPan`,
 * which dispatches a SEPARATE `treemapMove` action — verified in TreemapView.js `_onPan`,
 * NOT `treemapRender` — this is why a scale-only guard on `treemaprender` alone still let
 * pan/drag move the rect arbitrarily far off-screen). Both handlers independently track the
 * *true* cumulative scale/position by comparing `rootRect` against the container's actual
 * current size (which is what the root rect equals at zoom=1, since the series is
 * `width/height:'100%'`). If the resulting scale or position falls outside our bounds,
 * immediately dispatch a corrective `treemapRender` action with a clamped rect — fully
 * bypassing ECharts' broken internal bookkeeping. Position clamping keeps the rect fully
 * covering the container (no edge of the container may ever show blank space beyond the rect,
 * regardless of whether the triggering gesture was a zoom or a pan).
 */
import type {ECharts} from 'echarts';

export interface TreemapZoomGuardOptions {
    minScale?: number;
    /** Fixed value, or a function evaluated LIVE on every event (e.g. derived from the
     *  current dataset — the smallest leaf's area relative to the total — so the max
     *  zoom stays meaningful even as holdings/period change without needing to re-attach
     *  the guard). */
    maxScale?: number | (() => number);
    /** Called with the current TRUE (guard-corrected) cumulative scale AND rect on every
     *  treemaprender/treemapmove event, including no-op ones. Lets callers drive UI that
     *  depends on "is the user currently zoomed in" — e.g. toggling `touch-action` so a
     *  single-finger drag pans the treemap only when there's actually something to pan
     *  (scale > 1), and falls through to native page scroll at the default 1:1 fit (where
     *  panning is a guaranteed no-op per the clamping below anyway). The rect is also the
     *  only reliable way for external code to read the treemap's current root rect without
     *  reaching into ECharts' internal `seriesModel.getData().tree.root.getLayout()` — used
     *  to compute manual pan deltas (see the touch-drag bridge in ExposureTreemap.svelte). */
    onScaleChange?: (scale: number, rect: {x: number; y: number; width: number; height: number}) => void;
}

export interface TreemapZoomGuardHandle {
    /** Detach the guard's event listener. Call on chart disposal. */
    dispose: () => void;
}

/** Tolerance (CSS px) below which a scale/position delta is treated as "already correct",
 *  to avoid dispatch loops from floating-point rounding. */
const EPSILON = 0.5;

/**
 * Attach a zoom+pan guard to a treemap chart instance.
 *
 * @param chart The ECharts instance hosting the treemap series.
 * @param getContainerSize Returns the current CSS pixel size of the chart's container
 *   (i.e. the rect at zoom=1) — read live on every event, so it stays correct across
 *   resizes/rebuilds without needing any manual "baseline" reset.
 */
export function attachTreemapZoomGuard(chart: ECharts, getContainerSize: () => {width: number; height: number}, options: TreemapZoomGuardOptions = {}): TreemapZoomGuardHandle {
    const minScale = options.minScale ?? 1;
    const resolveMaxScale = () => (typeof options.maxScale === 'function' ? options.maxScale() : (options.maxScale ?? 5));
    let correcting = false;

    const handler = (params: any) => {
        if (correcting) {
            // This event is our own corrective dispatch — ignore to avoid an infinite loop.
            correcting = false;
            return;
        }
        const rect = params?.rootRect;
        const {width: containerWidth, height: containerHeight} = getContainerSize();
        if (!rect || !rect.width || !rect.height || !containerWidth || !containerHeight) return;

        // 1. Clamp cumulative scale (uniform factor, preserves aspect ratio).
        const scale = rect.width / containerWidth;
        const maxScale = resolveMaxScale();
        const clampedScale = Math.min(Math.max(scale, minScale), maxScale);
        const factor = clampedScale / scale;
        const cx = rect.x + rect.width / 2;
        const cy = rect.y + rect.height / 2;
        let newWidth = rect.width * factor;
        let newHeight = rect.height * factor;
        let newX = cx - newWidth / 2;
        let newY = cy - newHeight / 2;

        // 2. Clamp pan so the rect always fully covers the container — no blank "walls".
        //    Since newWidth/newHeight are always >= container size (minScale >= 1), a valid
        //    range [container - rectSize, 0] always exists.
        if (newWidth >= containerWidth) {
            newX = Math.min(0, Math.max(containerWidth - newWidth, newX));
        } else {
            newX = (containerWidth - newWidth) / 2;
        }
        if (newHeight >= containerHeight) {
            newY = Math.min(0, Math.max(containerHeight - newHeight, newY));
        } else {
            newY = (containerHeight - newHeight) / 2;
        }

        options.onScaleChange?.(clampedScale, {x: newX, y: newY, width: newWidth, height: newHeight});

        const scaleChanged = Math.abs(newWidth - rect.width) > EPSILON || Math.abs(newHeight - rect.height) > EPSILON;
        const positionChanged = Math.abs(newX - rect.x) > EPSILON || Math.abs(newY - rect.y) > EPSILON;
        if (!scaleChanged && !positionChanged) return;

        correcting = true;
        chart.dispatchAction({
            type: 'treemapRender',
            rootRect: {x: newX, y: newY, width: newWidth, height: newHeight},
        });
    };

    chart.on('treemaprender', handler);
    chart.on('treemapmove', handler);
    return {
        dispose: () => {
            chart.off('treemaprender', handler);
            chart.off('treemapmove', handler);
        },
    };
}

/**
 * Resets a treemap to its natural, un-zoomed full-container view.
 * (Setting `series[0].zoom`/`center` via `setOption` is a no-op for treemap roam —
 * those fields are only consulted internally for per-tick bookkeeping, never used to
 * directly position the displayed root rect. The only way to actually move the view
 * is to dispatch a `treemapRender` action with an explicit target rect.)
 */
export function resetTreemapView(chart: ECharts): void {
    const width = chart.getWidth();
    const height = chart.getHeight();
    chart.dispatchAction({
        type: 'treemapRender',
        rootRect: {x: 0, y: 0, width, height},
    });
}

/**
 * Manually pan a treemap by a pixel delta, from a known current rect.
 *
 * WHY THIS EXISTS: ECharts' own `roam`-driven pan (`RoamController` → `_onPan` →
 * dispatches this SAME `treemapMove` action internally) never fires on touch devices
 * that support the Pointer Events API (virtually all modern mobile browsers). Verified
 * by reading `zrender/lib/dom/HandlerProxy.js`: its `pointermove` handler only forwards
 * to the internal `mousemove` (which `RoamController` listens to for drag/pan tracking)
 * `if (!isPointerFromTouch(event))` — i.e. touch-sourced pointer movement is explicitly
 * EXCLUDED from ever reaching the pan logic, regardless of `roam`/`touch-action` config.
 * `pointerdown`/`pointerup` have no such exclusion, so a touch drag still registers as a
 * "click", but the move-tracking that computes pan deltas never runs — matching the
 * exact reported symptom ("only clicks work, pan does nothing, even when zoomed in").
 *
 * This function lets a caller's OWN touchmove listener (which — unlike zrender's
 * internal bridge — DOES receive raw touch events fine) manually dispatch the exact
 * same `treemapMove` action ECharts' desktop mouse-drag path would have dispatched,
 * fully reusing ECharts' own rendering/transform logic (and this module's zoom+pan
 * guard, which listens to the SAME `treemapmove` event and will clamp the result if it
 * would go out of bounds) — no pan math is reimplemented beyond a plain offset.
 *
 * @param chart The ECharts instance hosting the treemap series.
 * @param dx Pixel delta since the last move (positive = drag right).
 * @param dy Pixel delta since the last move (positive = drag down).
 * @param currentRect The treemap's current root rect — e.g. from `attachTreemapZoomGuard`'s
 *   `onScaleChange` callback, which reports the guard-corrected rect on every render/move.
 */
export function panTreemapBy(chart: ECharts, dx: number, dy: number, currentRect: {x: number; y: number; width: number; height: number}): void {
    chart.dispatchAction({
        type: 'treemapMove',
        rootRect: {x: currentRect.x + dx, y: currentRect.y + dy, width: currentRect.width, height: currentRect.height},
    });
}
