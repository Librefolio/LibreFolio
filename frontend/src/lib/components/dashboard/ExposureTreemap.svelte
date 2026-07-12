<!--
  ExposureTreemap — ECharts treemap for portfolio exposure.

  Hierarchy: Broker → Asset Type → Asset.
  Area = current_value, color = gain_loss_percent (red→green gradient).
  Tooltip: asset name, broker, type, value, NAV weight, unrealized P&L.

  Pattern: ECharts lifecycle (init, MutationObserver, ResizeObserver),
  Svelte 5 Runes, dark mode, data-testid.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {ExternalLink, Layers, RotateCcw} from 'lucide-svelte';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import ContextMenu, {type ContextMenuItem} from '$lib/components/ui/ContextMenu.svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {buildTooltipTheme, buildTooltipRow, buildTooltipHeader, buildTooltipDivider, scheduleFirstRenderStabilityFix} from '$lib/components/charts/echartsTooltipHelpers';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {brokerStoreVersion, ensureBrokersLoaded, getBrokerInfo} from '$lib/stores/reference/brokerStore';
    import {ensurePluginIconsLoaded, getBrokerIconUrl} from '$lib/utils/broker/brokerHelpers';
    import {attachTreemapZoomGuard, resetTreemapView, panTreemapBy, type TreemapZoomGuardHandle} from '$lib/components/charts/echartsTreemapZoomGuard';

    interface Holding {
        asset_id: number;
        asset_name: string;
        asset_type: string;
        broker_id?: number | (number | null)[] | null;
        broker_name?: string | (string | null)[] | null;
        current_value?: string | (string | null)[] | null;
        nav_weight_percent?: string | (string | null)[] | null;
        gain_loss?: string | (string | null)[] | null;
        gain_loss_percent?: string | (string | null)[] | null;
    }

    interface Props {
        holdings: Holding[];
        displayCurrency?: string;
        onAnalyze?: (assetId: number) => void;
    }

    let {holdings = [], displayCurrency = 'EUR', onAnalyze}: Props = $props();

    let chartWrapper: HTMLDivElement | undefined = $state(undefined);
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let zoomGuard: TreemapZoomGuardHandle | null = null;
    let brokerIconsReady = $state(false);
    let chartWidth: number = $state(0);
    let chartHeight: number = $state(0);
    let windowResizeHandler: (() => void) | null = null;
    let pendingResizeFrame: number | null = null;
    let needsInitialLayoutStabilityPass = false;
    /** True once the user has zoomed in beyond the default 1:1 fit — i.e. there is
     *  actually something to pan. Gates the two-finger pan handler below so it never
     *  bothers dispatching a guaranteed no-op at the default fit. Two-finger touch never
     *  competes with native single-finger scroll, so — unlike an earlier single-finger
     *  attempt — this no longer needs to toggle `touch-action` on the container at all;
     *  a stray 1-finger swipe over the treemap always scrolls the page, zoomed or not. */
    let isZoomedIn = $state(false);
    /** Last guard-corrected root rect, kept in sync by attachTreemapZoomGuard's
     *  onScaleChange — the only externally-reachable source of "where is the treemap's
     *  content right now", needed to compute manual pan targets (see handleTouchPanMove
     *  below). */
    let lastKnownRect: {x: number; y: number; width: number; height: number} | null = null;
    /** Tracks an in-progress manual two-finger pan drag (see the doc comment on
     *  `handleTouchPanStart` below for why two fingers, not one). Null when not dragging. */
    let touchPanState: {x: number; y: number} | null = null;
    let contextMenu = $state<{x: number; y: number; assetId: number} | null>(null);

    const UPPER_LABEL_ICON_SIZE = 12;

    type TreeNodeLevel = 'broker' | 'type' | 'asset';

    function safeNum(v: string | (string | null)[] | null | undefined): number | null {
        const s = Array.isArray(v) ? (v[0] ?? null) : v;
        if (s == null) return null;
        const n = parseFloat(s);
        return isNaN(n) ? null : n;
    }

    function safeInt(v: number | (number | null)[] | null | undefined): number | null {
        if (v == null) return null;
        return Array.isArray(v) ? (v[0] ?? null) : v;
    }

    function safeStr(v: string | (string | null)[] | null | undefined): string | null {
        if (v == null) return null;
        return Array.isArray(v) ? (v[0] ?? null) : v;
    }

    /** Broker names are user-entered data (not translated); asset TYPE is a backend
     *  enum and must go through i18n (`assets.types.X`, plural namespace). */
    function translateAssetType(rawType: string): string {
        const key = `assets.types.${rawType.toUpperCase()}`;
        const translated = $_(key);
        return translated !== key ? translated : rawType;
    }

    onMount(() => {
        const observer = new MutationObserver(() => renderChart());
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        windowResizeHandler = () => updateChartSize();
        window.addEventListener('resize', windowResizeHandler);
        resizeObserver = new ResizeObserver(() => updateChartSize());
        if (chartWrapper) resizeObserver.observe(chartWrapper);
        updateChartSize();
        void (async () => {
            try {
                await ensureBrokersLoaded();
                await ensurePluginIconsLoaded();
            } finally {
                brokerIconsReady = true;
            }
        })();
        return () => {
            observer.disconnect();
            cleanup();
        };
    });

    function cleanup() {
        if (windowResizeHandler) {
            window.removeEventListener('resize', windowResizeHandler);
            windowResizeHandler = null;
        }
        if (pendingResizeFrame != null) {
            cancelAnimationFrame(pendingResizeFrame);
            pendingResizeFrame = null;
        }
        resizeObserver?.disconnect();
        resizeObserver = null;
        zoomGuard?.dispose();
        zoomGuard = null;
        if (chartContainer) {
            chartContainer.removeEventListener('touchstart', handleTouchPanStart);
            chartContainer.removeEventListener('touchmove', handleTouchPanMove);
            chartContainer.removeEventListener('touchend', handleTouchPanEnd);
            chartContainer.removeEventListener('touchcancel', handleTouchPanEnd);
        }
        chartInstance?.dispose();
        chartInstance = null;
    }

    /** Manual TWO-finger drag-to-pan bridge for touch devices.
     *
     *  WHY TWO FINGERS, NOT ONE (verified by reading zrender's source, not guessed): on any
     *  modern mobile browser (Pointer Events API support, `'onpointerdown' in window`),
     *  zrender's `HandlerProxy` translates `pointerdown`/`pointerup` into the internal
     *  mousedown/mouseup zrender relies on regardless of origin — but its `pointermove`
     *  handler does `if (!isPointerFromTouch(event)) { ...translate to mousemove... }`, i.e.
     *  touch-sourced pointer movement is explicitly EXCLUDED from ever reaching
     *  `RoamController`'s pan tracking. That alone was fixable by tracking touch drags
     *  ourselves — but a SECOND, unrelated and unfixable problem showed up with a
     *  single-finger implementation: a browser decides "this touch gesture is native scroll"
     *  vs "this touch gesture is handled by JS" once, at the START of the gesture, and will
     *  NOT hand it back to native scrolling mid-gesture — so once a single-finger drag starts
     *  panning a zoomed treemap, reaching the edge (nothing left to pan) could not seamlessly
     *  continue as page scroll within that same continuous drag; the user would have to lift
     *  and re-touch. Reserving ONE finger exclusively for scrolling (always, with zero
     *  exceptions) and using TWO fingers for pan sidesteps the conflict entirely — a
     *  single-finger drag is never intercepted at all, so it always scrolls the page
     *  normally, edge or no edge.
     *
     *  Dispatches the exact same `treemapMove` action ECharts' desktop mouse-drag path
     *  would have dispatched (see `panTreemapBy`), computed from the CENTROID of the two
     *  touches — fully reusing ECharts' rendering + this file's zoom/pan guard for clamping.
     *  Runs independently of whatever already drives pinch-to-zoom (untouched by this fix,
     *  it was already working) — this only ever adjusts position, never scale, so the two
     *  naturally compose on a real 2-finger gesture that both translates and pinches at once. */
    function centroidOf(touches: TouchList): {x: number; y: number} {
        let x = 0;
        let y = 0;
        for (let i = 0; i < touches.length; i++) {
            x += touches[i].clientX;
            y += touches[i].clientY;
        }
        return {x: x / touches.length, y: y / touches.length};
    }

    function handleTouchPanStart(e: TouchEvent) {
        if (e.touches.length !== 2 || !isZoomedIn) {
            touchPanState = null;
            return;
        }
        touchPanState = centroidOf(e.touches);
    }

    function handleTouchPanMove(e: TouchEvent) {
        if (e.touches.length !== 2) {
            // Finger count changed mid-gesture (e.g. one lifted) — stop tracking rather than
            // computing a bogus delta against a stale reference point.
            touchPanState = null;
            return;
        }
        if (!touchPanState || !chartInstance || !lastKnownRect) return;
        const centroid = centroidOf(e.touches);
        const dx = centroid.x - touchPanState.x;
        const dy = centroid.y - touchPanState.y;
        touchPanState = centroid;
        // Two-finger gestures never compete with native single-finger scroll, so this
        // preventDefault only ever suppresses the browser's own pinch-zoom-the-page
        // gesture — it can't block page scroll, which is exactly the point.
        e.preventDefault();
        panTreemapBy(chartInstance, dx, dy, lastKnownRect);
    }

    function handleTouchPanEnd(e: TouchEvent) {
        // Re-arm if exactly 2 touches remain (e.g. a 3rd finger lifted back to 2); otherwise
        // stop — a drop to 0 or 1 remaining touch ends the pan gesture.
        touchPanState = e.touches.length === 2 && isZoomedIn ? centroidOf(e.touches) : null;
    }

    $effect(() => {
        void holdings;
        void displayCurrency;
        void $brokerStoreVersion;
        void brokerIconsReady;
        void $currentLanguage;
        tick().then(() => renderChart());
    });

    /** JS-owned size: wrapper width stays 100% of panel; height = min(full-width square,
     *  65% viewport cap). Narrow screens stay 1:1, wide screens become landscape without
     *  shrinking width. Explicit px sizing avoids prior CSS aspect-ratio/max-height drift.
     *
     *  Width is measured off the `[data-testid="positions-panel"]` CARD itself (not the
     *  nested `chartWrapper`) — `clientWidth` already excludes the card's own 1px border,
     *  then its horizontal padding (16px each side, read live via `getComputedStyle` rather
     *  than hardcoded in case the card's padding classes ever change) is subtracted
     *  explicitly. Measuring the intermediate nested wrapper directly (previous approach)
     *  intermittently reported a width that included that padding/border instead of
     *  excluding it, bleeding the canvas a few pixels past the card's edge on the right/
     *  bottom — this bypasses whatever nested-flex sizing quirk caused that by anchoring
     *  the calculation to the one element whose padding/border we know for certain. */
    function updateChartSize() {
        if (!chartWrapper) return;
        const panel = chartWrapper.closest<HTMLElement>('[data-testid="positions-panel"]');
        let nextWidth: number;
        if (panel) {
            const panelStyle = getComputedStyle(panel);
            const paddingLeft = parseFloat(panelStyle.paddingLeft) || 0;
            const paddingRight = parseFloat(panelStyle.paddingRight) || 0;
            nextWidth = Math.floor(panel.clientWidth - paddingLeft - paddingRight);
        } else {
            nextWidth = Math.floor(chartWrapper.getBoundingClientRect().width);
        }
        const nextHeight = Math.floor(Math.min(nextWidth, window.innerHeight * 0.65));
        if (nextWidth === chartWidth && nextHeight === chartHeight) return;

        chartWidth = nextWidth;
        chartHeight = nextHeight;

        if (chartInstance) {
            scheduleChartResize();
        } else if (nextWidth > 0 && nextHeight > 0) {
            void tick().then(() => {
                renderChart();
                scheduleChartResize();
            });
        }
    }

    function scheduleChartResize() {
        if (!chartInstance) return;
        if (pendingResizeFrame != null) cancelAnimationFrame(pendingResizeFrame);
        const instanceAtSchedule = chartInstance;
        const widthAtSchedule = chartWidth;
        const heightAtSchedule = chartHeight;
        pendingResizeFrame = requestAnimationFrame(() => {
            pendingResizeFrame = null;
            if (instanceAtSchedule === chartInstance && !instanceAtSchedule.isDisposed()) {
                instanceAtSchedule.resize({width: widthAtSchedule, height: heightAtSchedule});
            }
        });
    }

    function sanitizeRichKeySegment(value: string | number | null | undefined): string {
        const sanitized = String(value ?? 'unknown')
            .trim()
            .replace(/[^a-zA-Z0-9_]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_+|_+$/g, '');
        return sanitized || 'unknown';
    }

    function buildUpperLabelRich(data: any[]): Record<string, any> {
        const rich: Record<string, any> = {};

        const visit = (nodes: any[]) => {
            for (const node of nodes) {
                const meta = node?._meta;
                if (meta?.iconUrl && meta?.iconRichKey) {
                    rich[meta.iconRichKey] = {
                        backgroundColor: {image: meta.iconUrl},
                        width: UPPER_LABEL_ICON_SIZE,
                        height: UPPER_LABEL_ICON_SIZE,
                        align: 'center',
                        verticalAlign: 'middle',
                        borderRadius: 3,
                    };
                }
                if (Array.isArray(node?.children) && node.children.length > 0) {
                    visit(node.children);
                }
            }
        };

        visit(data);
        return rich;
    }

    function formatUpperLabel(params: any): string {
        const meta = params.data?._meta;
        if (!meta || (meta.level as TreeNodeLevel) === 'asset') return params.name;
        return meta.iconRichKey ? `{${meta.iconRichKey}|} ${params.name}` : params.name;
    }

    /** Max zoom proportional to the data: at scale=1 the whole treemap area equals the
     *  total value, and a leaf's area is (roughly, modulo squarified-layout/border
     *  overhead) proportional to its own value — so area scales with the SQUARE of the
     *  zoom factor. Solving for "the smallest leaf's area should fill about a sixth of
     *  the viewport at max zoom" (viewport ≈ 6 × smallest_leaf_area — tightened from an
     *  initial 3× which still allowed too much zoom per user feedback):
     *    Z² × (total_area × smallest/total) = total_area / 6
     *    Z = sqrt((total / smallest) / 6)
     *  Pixel dimensions cancel out entirely — it only depends on the value ratio, so it
     *  doesn't need to be recomputed on resize, only when the underlying holdings change.
     *  Clamped to a sane [2, 12] range: a nearly-uniform portfolio (ratio ~1) would
     *  otherwise compute a max zoom barely above 1:1 (not worth zooming for at all), and
     *  one dominated by a single tiny sliver would otherwise compute an unusably huge one. */
    function computeMaxZoomScale(): number {
        let total = 0;
        let min = Infinity;
        for (const h of holdings) {
            const val = safeNum(h.current_value);
            if (val == null || val <= 0) continue;
            total += val;
            if (val < min) min = val;
        }
        if (total <= 0 || !isFinite(min) || min <= 0) return 5;
        return Math.min(12, Math.max(2, Math.sqrt(total / min / 6)));
    }

    function buildTreeData(): any[] {
        // Group: Broker → AssetType → Asset
        const brokerMap = new Map<
            string,
            {
                name: string;
                brokerId: number | null;
                iconUrl: string | null;
                iconRichKey: string | null;
                value: number;
                weight: number;
                gl: number;
                types: Map<
                    string,
                    {
                        name: string;
                        iconUrl: string;
                        iconRichKey: string;
                        assets: any[];
                        value: number;
                        weight: number;
                        gl: number;
                    }
                >;
            }
        >();

        for (const h of holdings) {
            const val = safeNum(h.current_value);
            if (val == null || val <= 0) continue;

            const bid = safeInt(h.broker_id);
            const brokerInfo = bid ? getBrokerInfo(bid) : null;
            const bName = safeStr(h.broker_name) || brokerInfo?.name || 'Unknown';
            const aType = h.asset_type || 'Unknown';
            const brokerKey = bid != null ? `broker_${bid}` : `broker_name_${bName}`;

            if (!brokerMap.has(brokerKey)) {
                const brokerIconUrl = getBrokerIconUrl(brokerInfo);
                brokerMap.set(brokerKey, {
                    name: bName,
                    brokerId: bid,
                    iconUrl: brokerIconUrl,
                    iconRichKey: brokerIconUrl ? `broker_${sanitizeRichKeySegment(bid ?? bName)}` : null,
                    value: 0,
                    weight: 0,
                    gl: 0,
                    types: new Map(),
                });
            }
            const brokerNode = brokerMap.get(brokerKey)!;

            if (!brokerNode.types.has(aType)) {
                const typeIconUrl = getAssetTypeIconUrl(aType);
                brokerNode.types.set(aType, {
                    name: translateAssetType(aType),
                    iconUrl: typeIconUrl,
                    iconRichKey: `type_${sanitizeRichKeySegment(aType.toUpperCase())}`,
                    assets: [],
                    value: 0,
                    weight: 0,
                    gl: 0,
                });
            }
            const typeNode = brokerNode.types.get(aType)!;

            const glPct = safeNum(h.gain_loss_percent);
            const gl = safeNum(h.gain_loss);
            const weight = safeNum(h.nav_weight_percent);

            // Roll up sums for the type/broker group tooltips below — value and
            // weight (both already NAV-normalized percentages/amounts) and gl
            // (absolute P&L) are additive; glPct is NOT additive and gets
            // recomputed from the aggregated value/gl once the group is built.
            typeNode.value += val;
            brokerNode.value += val;
            if (weight != null) {
                typeNode.weight += weight;
                brokerNode.weight += weight;
            }
            if (gl != null) {
                typeNode.gl += gl;
                brokerNode.gl += gl;
            }

            typeNode.assets.push({
                name: h.asset_name,
                value: val,
                itemStyle: {color: pnlColor(glPct)},
                _meta: {
                    level: 'asset' as TreeNodeLevel,
                    assetId: h.asset_id,
                    name: h.asset_name,
                    brokerId: bid,
                    broker: bName,
                    type: translateAssetType(aType),
                    value: val,
                    weight,
                    gl,
                    glPct,
                },
            });
        }

        /** glPct is a ratio (gl / cost_basis), not additive across positions — recompute
         *  it from the aggregated value/gl (cost_basis = value - gl) instead of leaving it
         *  undefined (which previously rendered as "NaN" in the type/broker tooltip). */
        function aggregateGlPct(value: number, gl: number): number | null {
            const costBasis = value - gl;
            return costBasis !== 0 ? gl / costBasis : null;
        }

        const tree: any[] = [];
        for (const brokerNode of brokerMap.values()) {
            const children: any[] = [];
            for (const typeNode of brokerNode.types.values()) {
                children.push({
                    name: typeNode.name,
                    children: typeNode.assets,
                    _meta: {
                        level: 'type' as TreeNodeLevel,
                        brokerId: brokerNode.brokerId,
                        broker: brokerNode.name,
                        type: typeNode.name,
                        iconUrl: typeNode.iconUrl,
                        iconRichKey: typeNode.iconRichKey,
                        value: typeNode.value,
                        weight: typeNode.weight,
                        gl: typeNode.gl,
                        glPct: aggregateGlPct(typeNode.value, typeNode.gl),
                    },
                });
            }
            tree.push({
                name: brokerNode.name,
                children,
                _meta: {
                    level: 'broker' as TreeNodeLevel,
                    brokerId: brokerNode.brokerId,
                    broker: brokerNode.name,
                    iconUrl: brokerNode.iconUrl,
                    iconRichKey: brokerNode.iconRichKey,
                    value: brokerNode.value,
                    weight: brokerNode.weight,
                    gl: brokerNode.gl,
                    glPct: aggregateGlPct(brokerNode.value, brokerNode.gl),
                },
            });
        }
        return tree;
    }

    function pnlColor(pct: number | null): string {
        if (pct == null) return '#6b7280';
        const isDark = document.documentElement.classList.contains('dark');
        if (pct >= 0) {
            const intensity = Math.min(pct * 100, 50) / 50;
            return isDark ? `rgb(${34 + intensity * 40}, ${197 + intensity * 40}, ${94 + intensity * 40})` : `rgb(${22 - intensity * 10}, ${163 - intensity * 30}, ${74 + intensity * 20})`;
        }
        const intensity = Math.min(Math.abs(pct * 100), 50) / 50;
        return isDark ? `rgb(${248}, ${113 - intensity * 40}, ${113 - intensity * 40})` : `rgb(${220 + intensity * 20}, ${38 + intensity * 20}, ${38 + intensity * 20})`;
    }

    function handleTreemapContextMenu(params: any) {
        const meta = params?.data?._meta;
        if (meta?.level === 'asset' && meta.assetId != null) {
            const nativeEvent = params?.event?.event as MouseEvent | PointerEvent | undefined;
            nativeEvent?.preventDefault();
            if (nativeEvent?.clientX == null || nativeEvent?.clientY == null) return;
            contextMenu = {x: nativeEvent.clientX, y: nativeEvent.clientY, assetId: meta.assetId};
        }
    }

    /** Centered ABOVE the tap/click point (clearing the finger and the hovered box
     *  itself), same convention as the Performance chart's tooltip. Unlike that chart
     *  (which has an internal scroll and is explicitly allowed to overflow above its
     *  canvas for top rows), the treemap has no scroll context, so this stays clamped
     *  within the chart's own container bounds on every side. `size.viewSize` here is
     *  the chart container's own size (ECharts tooltip DOM is appended inside it by
     *  default, not to document.body, since no `appendTo` is configured). */
    function treemapTooltipPosition(point: [number, number], _params: unknown, _dom: unknown, _rect: unknown, size: {contentSize: [number, number]; viewSize: [number, number]}): [number, number] {
        const tooltipW = size.contentSize[0];
        const tooltipH = size.contentSize[1];
        const viewW = size.viewSize[0];
        const viewH = size.viewSize[1];
        const gap = 12;

        let x = point[0] - tooltipW / 2;
        if (x < 4) x = 4;
        if (x + tooltipW > viewW - 4) x = viewW - tooltipW - 4;

        let y = point[1] - tooltipH - gap;
        if (y < 4) y = 4;
        if (y + tooltipH > viewH - 4) y = viewH - tooltipH - 4;

        return [x, y];
    }

    function renderChart() {
        if (!chartContainer || chartWidth <= 0 || chartHeight <= 0) return;
        const isDark = document.documentElement.classList.contains('dark');

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer);
            needsInitialLayoutStabilityPass = true;
            zoomGuard = attachTreemapZoomGuard(chartInstance, () => ({width: chartContainer?.clientWidth ?? 0, height: chartContainer?.clientHeight ?? 0}), {
                minScale: 0.9,
                maxScale: computeMaxZoomScale,
                onScaleChange: (scale, rect) => {
                    isZoomedIn = scale > 1.01;
                    lastKnownRect = rect;
                },
            });
            chartInstance.on('contextmenu', handleTreemapContextMenu);
            // {passive: false} is required — we conditionally call preventDefault() in
            // handleTouchPanMove, which a passive listener would silently ignore.
            chartContainer.addEventListener('touchstart', handleTouchPanStart, {passive: true});
            chartContainer.addEventListener('touchmove', handleTouchPanMove, {passive: false});
            chartContainer.addEventListener('touchend', handleTouchPanEnd, {passive: true});
            chartContainer.addEventListener('touchcancel', handleTouchPanEnd, {passive: true});
        }

        const theme = buildTooltipTheme(isDark);
        const data = buildTreeData();
        const upperLabelRich = buildUpperLabelRich(data);

        if (data.length === 0) {
            chartInstance.clear();
            return;
        }

        chartInstance.setOption(
            {
                tooltip: {
                    formatter: (params: any) => {
                        const meta = params.data?._meta;
                        if (!meta) return params.name;
                        let html = buildTooltipHeader(meta.broker, theme.textColor);
                        html += buildTooltipRow($_('common.asset'), meta.assetId ? (meta.name ?? '') : params.name);
                        html += buildTooltipRow($_('common.type'), meta.type);
                        html += buildTooltipRow($_('common.value'), formatCurrencyAmountPlain(meta.value, displayCurrency));
                        if (meta.weight != null) html += buildTooltipRow($_('dashboard.navWeight'), `${meta.weight.toFixed(1)}%`);
                        html += buildTooltipDivider(theme.border);
                        if (meta.gl != null) {
                            const glColor = meta.gl >= 0 ? (isDark ? '#4ade80' : '#16a34a') : isDark ? '#f87171' : '#dc2626';
                            html += buildTooltipRow($_('dashboard.unrealizedPnl'), `<span style="color:${glColor}">${formatCurrencyAmountPlain(meta.gl, displayCurrency, {showSign: true})}</span>`);
                        }
                        if (meta.glPct != null) {
                            html += buildTooltipRow('', `${(meta.glPct * 100).toFixed(2)}%`);
                        }
                        return `<div style="font-size:11px;color:${theme.textColor}">${html}</div>`;
                    },
                    backgroundColor: theme.bg,
                    borderColor: theme.border,
                    textStyle: {color: theme.textColor},
                    position: treemapTooltipPosition,
                    confine: false,
                    // Bugfix: `appendTo: document.body` was added earlier to escape an
                    // ancestor `overflow-hidden` that used to clip the tooltip near the
                    // container edges. That overflow-hidden was removed once the treemap's
                    // real root-cause sizing bug got fixed (see `left/top/right/bottom: 0`
                    // below), making `appendTo` unnecessary — and it was quietly causing a
                    // NEW bug: with `appendTo`, ECharts/zrender must convert our chart-local
                    // position into document-absolute coordinates (accounting for scroll),
                    // which can drift out of sync with the real scroll position. Without
                    // `appendTo`, the tooltip DOM stays nested inside this chart's own
                    // container (ECharts forces it to `position:relative`), scrolling as
                    // ONE unit with the rest of the page — no conversion, so no drift. Same
                    // class of bug already fixed once in PriceChartFull.svelte by dropping
                    // appendToBody (commit fcdd89e8, "Fix mobile tooltip scroll offset").
                },
                series: [
                    {
                        type: 'treemap',
                        data,
                        // ECharts' treemap defaultOption has NON-ZERO left/top/right/bottom
                        // (spacing tokens, not 0) — combined with width/height:'100%' this
                        // makes the root rect start a few px in from the top-left corner
                        // while still sizing itself to the FULL container, overflowing past
                        // the bottom-right edge by exactly that same offset. Found by the
                        // user panning the treemap and noticing the top-left corner wasn't
                        // at the canvas's actual origin. Explicit 0 on all 4 sides removes
                        // the implicit margin entirely — width/height:'100%' alone is not
                        // enough to override it.
                        left: 0,
                        top: 0,
                        right: 0,
                        bottom: 0,
                        width: '100%',
                        height: '100%',
                        roam: true,
                        // IMPORTANT: keep this declared scaleLimit permissive (NOT matching our
                        // real [1, 5] bound). ECharts resets its internal cumulative-zoom
                        // bookkeeping (controllerHost.zoom) to 1 on EVERY render (see
                        // echartsTreemapZoomGuard.ts for the full analysis), so each wheel/pinch
                        // tick's delta is computed against a baseline of 1, not the true current
                        // scale. Setting scaleLimit.min to our real floor (1) here made EVERY
                        // zoom-OUT tick's delta get clamped to exactly 1 => zoomScale = 1/1 = 1
                        // (a no-op) on every single attempt, completely disabling zoom-out
                        // regardless of the actual displayed scale — a real regression, not just
                        // a "cap at 100%". The real enforcement of the [1, 5] bound happens in
                        // attachTreemapZoomGuard() below, which independently tracks true
                        // cumulative scale from the live rect and corrects it after the fact —
                        // so this per-tick limit only needs to avoid interfering with normal
                        // ticks in either direction.
                        scaleLimit: {min: 0.1, max: 20},
                        nodeClick: false,
                        breadcrumb: {show: false},
                        upperLabel: {
                            show: true,
                            height: 20,
                            formatter: formatUpperLabel,
                            rich: upperLabelRich,
                            color: isDark ? '#e2e8f0' : '#334155',
                            fontSize: 10,
                            backgroundColor: isDark ? 'rgba(30,41,59,0.8)' : 'rgba(248,250,252,0.8)',
                        },
                        label: {
                            show: true,
                            formatter: '{b}',
                            fontSize: 10,
                            color: '#fff',
                            textShadowColor: 'rgba(0,0,0,0.5)',
                            textShadowBlur: 2,
                        },
                        levels: [{itemStyle: {borderWidth: 2, borderColor: isDark ? '#334155' : '#e2e8f0', gapWidth: 2}}, {itemStyle: {borderWidth: 1, borderColor: isDark ? '#475569' : '#cbd5e1', gapWidth: 1}}, {itemStyle: {borderWidth: 0, gapWidth: 1}}],
                    },
                ],
            },
            true,
        );
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer);
        }
    }

    /** Instantly restores the natural, un-zoomed full-container view — see
     *  resetTreemapView() in echartsTreemapZoomGuard.ts for why a plain
     *  `setOption({series:[{zoom:1,...}]})` does NOT work for treemap roam. */
    function resetView() {
        if (chartInstance) resetTreemapView(chartInstance);
    }
</script>

<!-- JS sizing: wrapper always spans full panel width. ResizeObserver reads actual
     wrapper clientWidth, viewport cap is recomputed as window.innerHeight * 0.75,
     then chart height = min(width, cap). Result: narrow screens keep full-width
     square; very wide screens keep full width and only clamp height, becoming
     landscape rectangle instead of shrinking. Explicit px width/height keeps chart
     perfectly inside card padding, no CSS aspect-ratio/max-height ambiguity. -->
<div bind:this={chartWrapper} class="relative w-full">
    <div bind:this={chartContainer} style="width:{chartWidth}px;height:{chartHeight}px" data-testid="exposure-treemap"></div>
    {#if contextMenu}
        <ContextMenu
            x={contextMenu.x}
            y={contextMenu.y}
            items={[
                {id: 'view-asset', label: $_('brokers.lots.viewAsset') || 'View Asset', icon: ExternalLink as unknown as ContextMenuItem['icon']},
                {id: 'analyze-lots', label: $_('brokers.lots.analyze') || 'Analyze Lots', icon: Layers as unknown as ContextMenuItem['icon']},
            ] satisfies ContextMenuItem[]}
            onAction={(id) => {
                if (!contextMenu) return;
                if (id === 'view-asset') void goto(`/assets/${contextMenu.assetId}`);
                else if (id === 'analyze-lots') onAnalyze?.(contextMenu.assetId);
                contextMenu = null;
            }}
            onClose={() => (contextMenu = null)}
        />
    {/if}
    <button
        type="button"
        class="absolute top-1 right-1 p-1 rounded bg-white/80 dark:bg-slate-800/80 border border-gray-200 dark:border-slate-600 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-white dark:hover:bg-slate-700 transition-colors"
        onclick={resetView}
        title={$_('dashboard.resetZoom')}
        data-testid="exposure-treemap-reset-zoom"
    >
        <RotateCcw size={12} />
    </button>
</div>
