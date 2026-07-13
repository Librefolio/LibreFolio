<!--
  PriceChartFull — Full-featured price chart with unified ECharts instance.

  Architecture: Single ECharts instance with 1 grid + inside dataZoom.
  - grid[0]: Main chart with line/signal series, overlay markers, pending edits
  - dataZoom: 'inside' type for mouse wheel zoom/pan (no visible slider)

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {_ as t} from '$lib/i18n';
    import type {ChartType, ViewMode} from './ChartToolbar.svelte';
    import ChartToolbar from './ChartToolbar.svelte';
    import type {LineDataPoint} from './LineChart.svelte';
    import CandlestickChart from './CandlestickChart.svelte';
    import ResolutionBadge from './ResolutionBadge.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {buildMainSeries, COLORS, updateArrowRotations} from './lineChartHelpers';
    import {buildPriceYAxis, buildSecondaryYAxes, buildOverlaySignalSeries, buildDataZoom, computeRightMargin, getChartColors} from './chartCoreHelpers';
    import {scheduleFirstRenderStabilityFix, tooltipPositionSide} from './echartsTooltipHelpers';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from './echartsDataZoomTouchPan';
    import {signalLabelToHtml, type SignalLabelInfo} from '$lib/charts/signalLabel';
    import {ChartLine, ChartCandlestick} from 'lucide-svelte';
    import {aggregateLineSeries, aggregateOHLCV, bucketEventMarkers, cascadeResolution, chooseInitialResolution, downsampleRenderedSignal, mapDateToBucket, type ChartResolution} from './timeSeriesAggregation';

    // =========================================================================
    // Event Marker types and constants
    // =========================================================================

    export interface EventMarker {
        date: string;
        type: string; // DIVIDEND, INTEREST, PRICE_ADJUSTMENT, SPLIT, MATURITY_SETTLEMENT
        value?: number;
        currency?: string;
        notes?: string;
        assetLabel?: string; // only for comparison events
        signalColor?: string; // color of the overlay signal for comparison events
        // E.8 — FX conversion metadata (mirror of price conversion).
        // Populated iff the event was converted (target_currency ≠ event.currency AND
        // FX rate was available). If conversion requested but failed → all undefined
        // and caller should hide the marker from the chart.
        originalValue?: number;
        originalCurrency?: string;
        originalCurrencyFlag?: string;
        currencyFlag?: string; // flag for the display currency (after conversion, if any)
        fxRateDate?: string;
        fxDaysBack?: number;
    }

    const EVENT_SYMBOLS: Record<string, string> = {
        INTEREST: 'diamond',
        DIVIDEND: 'triangle',
        PRICE_ADJUSTMENT: 'rect',
        MATURITY_SETTLEMENT: 'roundRect',
        SPLIT: 'arrow',
    };

    interface LogicalVisibleRange {
        startDate: string;
        endDate: string;
    }

    interface ResolvedDataCacheEntry {
        lineData: LineDataPoint[];
        candleData: LineDataPoint[];
    }

    interface BucketInfo {
        bucketStart: string;
        bucketEnd: string;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        data: LineDataPoint[];
        currency?: string;
        chartHeight?: string;
        initialChartType?: ChartType;
        initialViewMode?: ViewMode;
        editMode?: boolean;
        onPointClick?: (date: string, value: number) => void;
        /** Overlay signals for the main chart */
        overlaySignals?: RenderedSignal[];
        /** Chart aesthetics from settings store */
        colorByBaseline?: boolean;
        areaFill?: boolean;
        showGridLines?: boolean;
        showGradient?: boolean;
        yAxisMode?: 'auto' | 'include0' | 'custom';
        yAxisMin?: number;
        yAxisMax?: number;
        /** Measure mode: enables click-to-place measurement points */
        measureMode?: boolean;
        onMeasureClick?: (date: string, value: number) => void;
        /** Called on mousemove during measure mode (for live preview) */
        onMeasureHover?: (date: string, value: number) => void;
        /** Hide the built-in toolbar (chart type + view mode toggles) */
        hideToolbar?: boolean;
        /** Externally controlled chart type (when toolbar is hidden) */
        externalChartType?: ChartType;
        /** Externally controlled view mode (when toolbar is hidden) */
        externalViewMode?: ViewMode;
        /** Custom label for the main series in the tooltip (overrides currency) */
        mainSeriesLabel?: string;
        /** Event markers to display as scatter points on the chart */
        eventMarkers?: EventMarker[];
        /** Signal label info for overlay signals — keyed by series name (label) */
        overlaySignalInfoMap?: Map<string, SignalLabelInfo>;
        /** Main series icon URL (for tooltip rendering) */
        mainIconUrl?: string | null;
        /** Main series asset type (for tooltip icon fallback) */
        mainAssetType?: string | null;
        /** Called on double-click on a data point (date, value) — for editor scroll */
        onDblClick?: (date: string, value: number) => void;
        /** Called on double-click on an event marker (date, eventType) — for editor scroll */
        onEventDblClick?: (date: string, eventType: string) => void;
        /** Translated label for stale indicator in tooltip (e.g. "Stale: {days}d") — receives `{days}` placeholder */
        staleLabel?: string;
        /** Translated label for FX stale indicator (e.g. "FX rate: {days}d old") — receives `{days}` placeholder */
        fxStaleLabel?: string;
        /** Display currency code (e.g. "EUR") — used for main label suffix when FX conversion active */
        displayCurrency?: string;
        /** Display currency flag emoji (e.g. "🇪🇺") — pre-computed by parent */
        displayCurrencyFlag?: string;
        /** Main asset native currency code (e.g. "USD") — shown in tooltip when no conversion */
        mainCurrency?: string;
        /** Main asset native currency flag emoji (e.g. "🇺🇸") */
        mainCurrencyFlag?: string;
        /** Disable the candlestick toggle (e.g. for FX charts without OHLCV data) */
        disableCandlestick?: boolean;
        /** Callback when chart type changes (for external state sync) */
        onChartTypeChange?: (type: ChartType) => void;
    }

    let {
        data = [],
        currency = '',
        chartHeight = '400px',
        initialChartType = 'line',
        initialViewMode = 'absolute',
        editMode = false,
        onPointClick,
        overlaySignals = [],
        colorByBaseline = true,
        areaFill = true,
        showGridLines = true,
        showGradient = true,
        yAxisMode = 'auto',
        yAxisMin,
        yAxisMax,
        measureMode = false,
        onMeasureClick,
        onMeasureHover,
        hideToolbar = false,
        externalChartType,
        externalViewMode,
        mainSeriesLabel,
        eventMarkers = [],
        overlaySignalInfoMap,
        mainIconUrl,
        mainAssetType,
        onDblClick,
        onEventDblClick,
        staleLabel,
        fxStaleLabel,
        displayCurrency: displayCurrencyProp,
        displayCurrencyFlag,
        mainCurrency: mainCurrencyProp,
        mainCurrencyFlag: mainCurrencyFlagProp,
        disableCandlestick = false,
        onChartTypeChange: onChartTypeChangeProp,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartType: ChartType = $state('line');
    let viewMode: ViewMode = $state('absolute');
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let chartOptionSet = false;
    let needsInitialLayoutStabilityPass = false;
    let resolution: ChartResolution = $state('daily');
    let logicalRange: LogicalVisibleRange | null = $state(null);
    let zoomDebounceTimer: ReturnType<typeof setTimeout> | null = null;
    let resolvedDataCache = new Map<ChartResolution, ResolvedDataCacheEntry>();
    let lastRawDataRef: LineDataPoint[] | null = null;
    let lastDisplayDataRef: LineDataPoint[] | null = null;
    let lastRenderedResolution: ChartResolution | null = null;

    $effect(() => {
        chartType = externalChartType ?? initialChartType;
    });
    $effect(() => {
        viewMode = externalViewMode ?? initialViewMode;
    });

    // =========================================================================
    // Derived data
    // =========================================================================

    let displayData = $derived.by(() => {
        if (viewMode === 'absolute' || data.length === 0) return data;
        const baseValue = data[0].value;
        if (baseValue === 0) return data;
        return data.map((d) => ({...d, value: ((d.value - baseValue) / baseValue) * 100}));
    });

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        const observer = new MutationObserver(() => {
            if (chartContainer && data.length > 0) renderChart();
        });
        observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        return () => {
            observer.disconnect();
            if (zoomDebounceTimer) clearTimeout(zoomDebounceTimer);
            resizeObserver?.disconnect();
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            chartInstance?.dispose();
            chartInstance = null;
        };
    });

    $effect(() => {
        if (data !== lastRawDataRef) {
            resolvedDataCache.clear();
            resolution = 'daily';
            logicalRange = null;
            chartOptionSet = false;
            lastRenderedResolution = null;
            lastRawDataRef = data;
            lastDisplayDataRef = displayData;
        } else if (displayData !== lastDisplayDataRef) {
            resolvedDataCache.clear();
            lastDisplayDataRef = displayData;
        }
    });

    $effect(() => {
        if (chartContainer && data) {
            void overlaySignals;
            void areaFill;
            void colorByBaseline;
            void showGridLines;
            void showGradient;
            void viewMode;
            void displayData;
            void resolution;
            void yAxisMode;
            void yAxisMin;
            void yAxisMax;
            void mainSeriesLabel;
            void eventMarkers;
            void overlaySignalInfoMap;
            void mainIconUrl;
            void mainAssetType;
            tick().then(renderChart);
        }
    });

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleChartTypeChange(type: ChartType) {
        chartType = type;
        onChartTypeChangeProp?.(type);
    }

    function handleViewModeChange(mode: ViewMode) {
        viewMode = mode;
    }

    function handlePointClick(date: string, value: number) {
        if (measureMode && onMeasureClick) {
            if (viewMode === 'percentage' && data.length > 0) {
                const baseValue = data[0].value;
                onMeasureClick(date, baseValue * (1 + value / 100));
            } else {
                onMeasureClick(date, value);
            }
        } else if (editMode && onPointClick) {
            if (viewMode === 'percentage' && data.length > 0) {
                const baseValue = data[0].value;
                onPointClick(date, baseValue * (1 + value / 100));
            } else {
                onPointClick(date, value);
            }
        }
    }

    function clearZoomDebounce() {
        if (zoomDebounceTimer) {
            clearTimeout(zoomDebounceTimer);
            zoomDebounceTimer = null;
        }
    }

    function formatMonthLabel(date: string): string {
        return new Intl.DateTimeFormat(undefined, {
            month: 'long',
            year: 'numeric',
            timeZone: 'UTC',
        }).format(new Date(`${date}T00:00:00Z`));
    }

    function getBucketInfo(point: LineDataPoint, currentResolution: ChartResolution): BucketInfo {
        if (currentResolution === 'daily') {
            return {
                bucketStart: point.date,
                bucketEnd: point.date,
            };
        }

        return {
            bucketStart: typeof (point as any).bucketStart === 'string' ? (point as any).bucketStart : mapDateToBucket(point.date, currentResolution).bucketStart,
            bucketEnd: typeof (point as any).bucketEnd === 'string' ? (point as any).bucketEnd : point.date,
        };
    }

    function buildTooltipHeader(date: string, currentResolution: ChartResolution, bucketInfo?: BucketInfo): string {
        if (currentResolution === 'daily') {
            return `<strong>${date}</strong>`;
        }

        const info = bucketInfo ?? {bucketStart: date, bucketEnd: date};

        if (currentResolution === 'weekly') {
            return `<strong>${$t('chart.tooltip.weekRange', {values: {start: info.bucketStart, end: info.bucketEnd}})}</strong>`;
        }

        return `<strong>${$t('chart.tooltip.monthLabel', {values: {month: formatMonthLabel(info.bucketEnd)}})}</strong><br/><span style="font-size:11px;opacity:0.8">${$t('chart.tooltip.valueAt', {values: {date: info.bucketEnd}})}</span>`;
    }

    function synthesizeDailyOHLC(points: LineDataPoint[]): LineDataPoint[] {
        return points.map((point, index) => {
            const close = point.close ?? point.value;
            const prevClose = index > 0 ? (points[index - 1].close ?? points[index - 1].value) : close;
            const open = point.open ?? prevClose;
            const high = point.high ?? Math.max(open, close);
            const low = point.low ?? Math.min(open, close);

            return {
                ...point,
                open,
                high,
                low,
                close,
                value: close,
            };
        });
    }

    function getResolvedSeries(currentResolution: ChartResolution): ResolvedDataCacheEntry {
        const cached = resolvedDataCache.get(currentResolution);
        if (cached) return cached;

        const synthesizedDailyData = synthesizeDailyOHLC(data);
        const entry: ResolvedDataCacheEntry =
            currentResolution === 'daily'
                ? {
                      lineData: displayData,
                      candleData: synthesizedDailyData,
                  }
                : {
                      lineData: aggregateLineSeries(displayData, currentResolution),
                      candleData: aggregateOHLCV(synthesizedDailyData, currentResolution),
                  };

        resolvedDataCache.set(currentResolution, entry);
        return entry;
    }

    function getVisibleDailyPoints(range: LogicalVisibleRange | null): LineDataPoint[] {
        if (!range) return displayData;
        return displayData.filter((point) => point.date >= range.startDate && point.date <= range.endDate);
    }

    function countBuckets(points: LineDataPoint[]): {dailyCount: number; weeklyCount: number; monthlyCount: number} {
        const weeklyBuckets = new Set<string>();
        const monthlyBuckets = new Set<string>();

        for (const point of points) {
            const weekly = mapDateToBucket(point.date, 'weekly');
            const monthly = mapDateToBucket(point.date, 'monthly');
            weeklyBuckets.add(`${weekly.bucketStart}|${weekly.bucketEnd}`);
            monthlyBuckets.add(`${monthly.bucketStart}|${monthly.bucketEnd}`);
        }

        return {
            dailyCount: points.length,
            weeklyCount: weeklyBuckets.size,
            monthlyCount: monthlyBuckets.size,
        };
    }

    function resolveZoomIndex(value: unknown, dates: string[], fallback: number): number {
        if (typeof value === 'number') {
            return Math.min(Math.max(Math.round(value), 0), dates.length - 1);
        }

        if (typeof value === 'string') {
            const index = dates.indexOf(value);
            if (index >= 0) return index;
        }

        return fallback;
    }

    function getLogicalRangeFromChart(points: LineDataPoint[], currentResolution: ChartResolution): LogicalVisibleRange | null {
        if (!chartInstance || points.length === 0) return null;

        try {
            const option = chartInstance.getOption() as any;
            const zoom = option?.dataZoom?.[0];
            if (!zoom) return null;

            const dates = points.map((point) => point.date);
            const lastIndex = dates.length - 1;
            if (lastIndex < 0) return null;

            let startIndex = 0;
            let endIndex = lastIndex;

            if (zoom.startValue !== undefined || zoom.endValue !== undefined) {
                startIndex = resolveZoomIndex(zoom.startValue, dates, 0);
                endIndex = resolveZoomIndex(zoom.endValue, dates, lastIndex);
            } else if (lastIndex > 0) {
                const start = typeof zoom.start === 'number' ? zoom.start : 0;
                const end = typeof zoom.end === 'number' ? zoom.end : 100;
                startIndex = Math.min(Math.max(Math.floor((start / 100) * lastIndex), 0), lastIndex);
                endIndex = Math.min(Math.max(Math.ceil((end / 100) * lastIndex), 0), lastIndex);
            }

            if (startIndex > endIndex) [startIndex, endIndex] = [endIndex, startIndex];

            const startBucket = getBucketInfo(points[startIndex], currentResolution);
            const endBucket = getBucketInfo(points[endIndex], currentResolution);

            return {
                startDate: startBucket.bucketStart,
                endDate: endBucket.bucketEnd,
            };
        } catch (_) {
            return null;
        }
    }

    function computeZoomWindow(points: LineDataPoint[], currentResolution: ChartResolution, range: LogicalVisibleRange | null): {start: number; end: number} {
        const lastIndex = points.length - 1;
        if (!range || lastIndex <= 0) return {start: 0, end: 100};

        let startIndex = lastIndex;
        let endIndex = 0;

        for (let index = 0; index < points.length; index++) {
            const bucket = getBucketInfo(points[index], currentResolution);
            if (bucket.bucketEnd >= range.startDate) {
                startIndex = index;
                break;
            }
        }

        for (let index = lastIndex; index >= 0; index--) {
            const bucket = getBucketInfo(points[index], currentResolution);
            if (bucket.bucketStart <= range.endDate) {
                endIndex = index;
                break;
            }
        }

        if (endIndex < startIndex) {
            endIndex = startIndex;
        }

        return {
            start: (startIndex / lastIndex) * 100,
            end: (endIndex / lastIndex) * 100,
        };
    }

    function scheduleResolutionRecompute() {
        clearZoomDebounce();
        zoomDebounceTimer = setTimeout(() => {
            if (!chartInstance || displayData.length === 0) return;

            // Read the settled zoom range ONCE here (not on every dataZoom tick) — this is
            // the only place getLogicalRangeFromChart()/getOption() runs for interactive
            // zoom, now that the gesture has paused for 200ms.
            const activeLineData = getResolvedSeries(resolution).lineData;
            const nextRange = getLogicalRangeFromChart(activeLineData, resolution);
            if (nextRange) {
                logicalRange = nextRange;
            }

            const visiblePoints = getVisibleDailyPoints(logicalRange);
            const counts = countBuckets(visiblePoints.length > 0 ? visiblePoints : displayData);
            const nextResolution = cascadeResolution(resolution, counts, chartInstance.getWidth());

            if (nextResolution !== resolution) {
                resolution = nextResolution;
            }
        }, 200);
    }

    // =========================================================================
    // Chart Rendering — Unified 2-grid layout
    // =========================================================================

    function renderChart() {
        if (!chartContainer || displayData.length === 0) return;

        // If the DOM element changed (e.g. after switching chart type), dispose stale instance
        if (chartInstance && chartInstance.getDom() !== chartContainer) {
            chartInstance.dispose();
            chartInstance = null;
            resizeObserver?.disconnect();
            resizeObserver = null;
            dataZoomTouchPanHandle?.dispose();
            dataZoomTouchPanHandle = null;
            chartOptionSet = false;
        }

        if (!resizeObserver) {
            resizeObserver = new ResizeObserver(() => {
                if (chartOptionSet) {
                    try {
                        chartInstance?.resize();
                        if (chartInstance) updateArrowRotations(chartInstance);
                        // Bugfix: resizing the container (e.g. rotating a device, or
                        // shrinking a browser window to a narrow/mobile width) changes
                        // plotWidthPx, which can push the density past the weekly/monthly
                        // threshold — but chartInstance.resize() only redraws the EXISTING
                        // resolution's data at the new pixel size, it never re-evaluates
                        // which resolution should be active. Without this, a chart loaded
                        // at a wide viewport (daily/weekly) never re-checks whether a
                        // narrower resize now needs a coarser resolution. Matches the same
                        // resize -> resolution-recheck pairing already used in
                        // GrowthChart.svelte/AllocationHistoryChart.svelte.
                        scheduleResolutionRecompute();
                    } catch (_) {}
                } else if (chartContainer && data.length > 0) {
                    renderChart();
                }
            });
            resizeObserver.observe(chartContainer);
        }

        const rect = chartContainer.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            needsInitialLayoutStabilityPass = true;
            dataZoomTouchPanHandle = attachDataZoomTouchPan(chartInstance, chartContainer);

            // Global dblclick handler for edit mode — scrolls editor to clicked date
            chartInstance.getZr().on('dblclick', (params: any) => {
                if (!chartInstance) return;
                const pointInPixel = [params.offsetX, params.offsetY];
                if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                    const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                    if (pointInGrid) {
                        const dateIdx = Math.round(pointInGrid[0]);
                        const activeLineData = getResolvedSeries(resolution).lineData;
                        if (dateIdx >= 0 && dateIdx < activeLineData.length) {
                            const point = activeLineData[dateIdx];
                            // Check if this date has an event marker
                            const hasEvent = eventMarkers.find((e) => e.date === point.date);
                            if (hasEvent && onEventDblClick) {
                                onEventDblClick(point.date, hasEvent.type);
                            } else if (onDblClick) {
                                onDblClick(point.date, point.value);
                            }
                            // Also handle edit mode point click (original behavior)
                            if (editMode && onPointClick) {
                                handlePointClick(point.date, point.value);
                            }
                        }
                    }
                }
            });

            // Global click handler for measure mode — catches clicks anywhere on the chart area
            chartInstance.getZr().on('click', (params: any) => {
                if (!measureMode || !onMeasureClick || !chartInstance) return;
                // Skip if already handled by touchEnd (prevents double-fire on mobile)
                if (touchMeasureHandled) {
                    touchMeasureHandled = false;
                    return;
                }
                const pointInPixel = [params.offsetX, params.offsetY];
                if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                    const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                    if (pointInGrid) {
                        const dateIdx = Math.round(pointInGrid[0]);
                        const activeLineData = getResolvedSeries(resolution).lineData;
                        if (dateIdx >= 0 && dateIdx < activeLineData.length) {
                            const point = activeLineData[dateIdx];
                            handlePointClick(point.date, point.value);
                        }
                    }
                }
            });

            // Mousemove for live measure preview (throttled via rAF)
            let hoverRafPending = false;
            chartInstance.getZr().on('mousemove', (params: any) => {
                if (!measureMode || !onMeasureHover || !chartInstance || hoverRafPending) return;
                hoverRafPending = true;
                requestAnimationFrame(() => {
                    hoverRafPending = false;
                    if (!chartInstance) return;
                    const pointInPixel = [params.offsetX, params.offsetY];
                    if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                        const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                        if (pointInGrid) {
                            const dateIdx = Math.round(pointInGrid[0]);
                            const activeLineData = getResolvedSeries(resolution).lineData;
                            if (dateIdx >= 0 && dateIdx < activeLineData.length) {
                                const point = activeLineData[dateIdx];
                                // Convert back from % to absolute if needed
                                if (viewMode === 'percentage' && data.length > 0) {
                                    const baseValue = data[0].value;
                                    onMeasureHover(point.date, baseValue * (1 + point.value / 100));
                                } else {
                                    onMeasureHover(point.date, point.value);
                                }
                            }
                        }
                    }
                });
            });

            // Recompute arrow rotations when zoom changes (aspect ratio shifts).
            // NOTE: do NOT read chartInstance.getOption() here — it deep-clones the entire
            // chart option (documented ECharts behavior) and this handler fires on every
            // single dataZoom tick during an interactive zoom/pan (up to ~60/sec), which
            // caused severe stutter on charts with years of daily data. The logical-range
            // read (which internally calls getOption()) is deferred to the debounced body
            // of scheduleResolutionRecompute(), so it only runs once the gesture settles.
            chartInstance.on('dataZoom', () => {
                if (!chartInstance) return;
                updateArrowRotations(chartInstance);
                scheduleResolutionRecompute();
            });

            // Long-press handler for mobile (1s hold = double-click equivalent)
            // + Tap detection for measure mode (short tap = click)
            let longPressTimer: ReturnType<typeof setTimeout> | null = null;
            let touchStartPos: {x: number; y: number} | null = null;
            let touchStartTime = 0;
            /** Guard: set by onTouchEnd to suppress the synthetic click event that follows */
            let touchMeasureHandled = false;

            function clearLongPress() {
                if (longPressTimer) {
                    clearTimeout(longPressTimer);
                    longPressTimer = null;
                }
                touchStartPos = null;
            }

            function onTouchStart(e: TouchEvent) {
                if (!chartInstance || e.touches.length !== 1) {
                    clearLongPress();
                    return;
                }
                const touch = e.touches[0];
                touchStartPos = {x: touch.clientX, y: touch.clientY};
                touchStartTime = Date.now();
                longPressTimer = setTimeout(() => {
                    if (!chartInstance || !chartContainer || !touchStartPos) return;
                    const rect = chartContainer.getBoundingClientRect();
                    const offsetX = touchStartPos.x - rect.left;
                    const offsetY = touchStartPos.y - rect.top;
                    const pointInPixel = [offsetX, offsetY];
                    if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                        const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                        if (pointInGrid) {
                            const dateIdx = Math.round(pointInGrid[0]);
                            const activeLineData = getResolvedSeries(resolution).lineData;
                            if (dateIdx >= 0 && dateIdx < activeLineData.length) {
                                const point = activeLineData[dateIdx];
                                navigator.vibrate?.(50);
                                // Mirror dblclick behavior: event marker → onEventDblClick, else → onDblClick
                                const hasEvent = eventMarkers.find((e) => e.date === point.date);
                                if (hasEvent && onEventDblClick) {
                                    onEventDblClick(point.date, hasEvent.type);
                                } else if (onDblClick) {
                                    onDblClick(point.date, point.value);
                                }
                                // Also handle edit mode point click (original behavior)
                                if (editMode && onPointClick) {
                                    handlePointClick(point.date, point.value);
                                }
                            }
                        }
                    }
                    clearLongPress();
                }, 800);
            }

            function onTouchMove(e: TouchEvent) {
                if (!touchStartPos || !longPressTimer) return;
                const touch = e.touches[0];
                const dx = touch.clientX - touchStartPos.x;
                const dy = touch.clientY - touchStartPos.y;
                if (dx * dx + dy * dy > 100) clearLongPress(); // 10px threshold
            }

            function onTouchEnd() {
                // Detect quick tap for measure mode (touchStartPos still alive = movement < 10px)
                if (measureMode && onMeasureClick && touchStartPos && longPressTimer && Date.now() - touchStartTime < 400) {
                    const pos = touchStartPos;
                    if (chartInstance && chartContainer) {
                        const rect = chartContainer.getBoundingClientRect();
                        const offsetX = pos.x - rect.left;
                        const offsetY = pos.y - rect.top;
                        const pointInPixel = [offsetX, offsetY];
                        if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                            const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                            if (pointInGrid) {
                                const dateIdx = Math.round(pointInGrid[0]);
                                const activeLineData = getResolvedSeries(resolution).lineData;
                                if (dateIdx >= 0 && dateIdx < activeLineData.length) {
                                    const point = activeLineData[dateIdx];
                                    handlePointClick(point.date, point.value);
                                    touchMeasureHandled = true; // suppress following synthetic click
                                }
                            }
                        }
                    }
                }
                clearLongPress();
                // Hide ECharts tooltip after finger lift (fade out)
                if (chartInstance) {
                    setTimeout(() => {
                        chartInstance?.dispatchAction({type: 'hideTip'});
                    }, 3000);
                }
            }

            chartContainer.addEventListener('touchstart', onTouchStart, {passive: true});
            chartContainer.addEventListener('touchmove', onTouchMove, {passive: true});
            chartContainer.addEventListener('touchend', onTouchEnd);
            chartContainer.addEventListener('touchcancel', onTouchEnd);
        }

        const isDark = document.documentElement.classList.contains('dark');
        const isPercentage = viewMode === 'percentage';
        const baseColor = isDark ? COLORS.lineDark : COLORS.lineLight;
        const greenColor = isDark ? COLORS.greenDark : COLORS.greenLight;
        const redColor = isDark ? COLORS.redDark : COLORS.redLight;

        let activeResolution = resolution;
        if (!chartOptionSet && chartInstance) {
            const initialVisiblePoints = getVisibleDailyPoints(logicalRange);
            const initialCounts = countBuckets(initialVisiblePoints.length > 0 ? initialVisiblePoints : displayData);
            activeResolution = chooseInitialResolution(initialCounts, chartInstance.getWidth());
            if (activeResolution !== resolution) {
                resolution = activeResolution;
            }
        }

        const {lineData: resolvedLineData} = getResolvedSeries(activeResolution);
        const dates = resolvedLineData.map((point) => point.date);
        const bucketInfoByDate = new Map(dates.map((date, index) => [date, getBucketInfo(resolvedLineData[index], activeResolution)]));
        const useBaselineColoring = colorByBaseline;
        const baselineValue = isPercentage ? 0 : (resolvedLineData[0]?.value ?? 0);
        const staleDaysArr = resolvedLineData.map((point) => point.staleDays ?? 0);
        const mainSeriesName = mainSeriesLabel || currency || 'Value';
        const series: any[] = [];
        const values = resolvedLineData.map((point) => point.value);
        const mainSeriesList = buildMainSeries(values, staleDaysArr, baseColor, greenColor, redColor, isDark, areaFill, 2, mainSeriesName, useBaselineColoring, baselineValue, showGradient);
        series.push(...mainSeriesList);

        const hasOriginalValues = data.some((point) => point.originalValue !== undefined);
        let ghostLabel = '';
        if (hasOriginalValues) {
            const origCur = data.find((point) => point.originalCurrency)?.originalCurrency ?? '';
            const origFlag = data.find((point) => point.originalCurrencyFlag)?.originalCurrencyFlag ?? '';
            ghostLabel = mainSeriesLabel ? `💱 ${mainSeriesLabel} (${origFlag} ${origCur})`.trim() : `💱 ${origCur}`;

            const dailyGhostPoints = data.flatMap((point) => {
                if (point.originalValue === undefined) return [];
                return [{...point, value: point.originalValue}];
            });
            const firstOriginalValue = dailyGhostPoints[0]?.value ?? 1;
            const normalizedGhostPoints = isPercentage
                ? dailyGhostPoints.map((point) => ({
                      ...point,
                      value: firstOriginalValue !== 0 ? ((point.value - firstOriginalValue) / firstOriginalValue) * 100 : 0,
                  }))
                : dailyGhostPoints;
            const resolvedGhostPoints = activeResolution === 'daily' ? normalizedGhostPoints : aggregateLineSeries(normalizedGhostPoints, activeResolution);
            const ghostLookup = new Map(resolvedGhostPoints.map((point) => [point.date, point.value]));

            series.push({
                type: 'line',
                name: ghostLabel,
                data: dates.map((date) => ghostLookup.get(date) ?? null),
                connectNulls: true,
                smooth: false,
                symbol: 'none',
                showSymbol: false,
                sampling: 'lttb',
                xAxisIndex: 0,
                yAxisIndex: 0,
                lineStyle: {
                    color: isDark ? COLORS.lineDark : COLORS.lineLight,
                    width: 1.5,
                    type: 'dashed',
                    opacity: 0.8,
                },
                itemStyle: {
                    color: isDark ? COLORS.lineDark : COLORS.lineLight,
                    opacity: 0.8,
                },
                emphasis: {focus: 'none'},
                z: 0,
            });
        }

        const resolvedOverlaySignals = activeResolution === 'daily' ? overlaySignals : overlaySignals.map((signal) => downsampleRenderedSignal(signal, activeResolution, dates)).filter((signal) => signal.data.length > 0);

        series.push(...buildOverlaySignalSeries(resolvedOverlaySignals, dates, isDark, 0));

        if (useBaselineColoring) {
            series.push({
                type: 'line',
                name: '__baseline__',
                data: resolvedLineData.map(() => baselineValue),
                xAxisIndex: 0,
                yAxisIndex: 0,
                symbol: 'none',
                showSymbol: false,
                sampling: 'lttb',
                lineStyle: {color: isDark ? '#64748b' : '#9ca3af', type: 'dashed', width: 1},
                itemStyle: {color: 'transparent'},
                emphasis: {disabled: true},
                tooltip: {show: false},
                silent: true,
                z: 0,
            });
        }

        const formatEventEntry = (marker: EventMarker, eventColor: string, includeDate: boolean): string => {
            const dot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${eventColor};margin-right:4px;"></span>`;
            let html = includeDate ? `<span style="font-size:11px;opacity:0.8">${marker.date}</span><br/>${dot}${marker.type}` : `${dot}${marker.type}`;

            if (marker.value !== undefined) {
                const isConverted = marker.originalValue !== undefined && marker.originalCurrency !== undefined;
                const currBadge = marker.currency ? ` <span style="font-size:10px;opacity:0.7">(${marker.currencyFlag ?? ''} ${marker.currency})${isConverted ? ' 💱' : ''}</span>` : '';
                html += `<br/>💰 ${marker.value.toFixed(4)}${currBadge}`;
                if (isConverted) {
                    const origBadge = ` <span style="font-size:10px;opacity:0.7">(${marker.originalCurrencyFlag ?? ''} ${marker.originalCurrency})</span>`;
                    html += `<br/><span style="font-size:10px;opacity:0.7">orig. ${marker.originalValue!.toFixed(4)}${origBadge}</span>`;
                    if (marker.fxRateDate) {
                        const backfillHint = marker.fxDaysBack && marker.fxDaysBack > 0 ? ` (${marker.fxDaysBack}d back)` : '';
                        html += `<br/><span style="font-size:10px;opacity:0.6">fx @ ${marker.fxRateDate}${backfillHint}</span>`;
                    }
                }
            }

            if (marker.notes) {
                html += `<br/>📝 ${marker.notes}`;
            }

            if (marker.assetLabel) {
                const sigDot = marker.signalColor ? `<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${marker.signalColor};margin-right:3px;"></span>` : '';
                html += `<br/>🔗 ${sigDot}${marker.assetLabel}`;
            }

            return html;
        };

        if (eventMarkers && eventMarkers.length > 0) {
            const dateIndexMap = new Map(dates.map((date, index) => [date, index]));
            const overlayDataByLabel = new Map<string, Map<string, number>>();

            for (const signal of resolvedOverlaySignals) {
                if (!signal.data.length) continue;
                overlayDataByLabel.set(signal.label, new Map(signal.data.map((point) => [point.date, point.value])));
            }

            const grouped = new Map<string, {markers: EventMarker[]; color: string; label: string}>();
            for (const marker of eventMarkers) {
                const isComparison = !!marker.assetLabel;
                const groupKey = isComparison ? `${marker.assetLabel}::${marker.type}` : marker.type;
                const color = isComparison ? (marker.signalColor ?? '#6b7280') : baseColor;
                const seriesLabel = isComparison ? `${marker.assetLabel} ${marker.type}` : marker.type;
                if (!grouped.has(groupKey)) {
                    grouped.set(groupKey, {markers: [], color, label: seriesLabel});
                }
                grouped.get(groupKey)!.markers.push(marker);
            }

            for (const [, group] of grouped) {
                const {markers, color: eventColor, label: seriesLabel} = group;
                const eventType = markers[0].type;
                const scatterData: any[] = [];

                if (activeResolution === 'daily') {
                    for (const marker of markers) {
                        const index = dateIndexMap.get(marker.date);
                        if (index === undefined) continue;

                        let yValue: number;
                        if (marker.assetLabel) {
                            const overlayLookup = overlayDataByLabel.get(marker.assetLabel);
                            yValue = overlayLookup?.get(marker.date) ?? resolvedLineData[index]?.value ?? 0;
                        } else {
                            yValue = resolvedLineData[index]?.value ?? 0;
                        }

                        scatterData.push({
                            value: [marker.date, yValue],
                            marker,
                            bucketInfo: {bucketStart: marker.date, bucketEnd: marker.date},
                            bucketValue: yValue,
                        });
                    }
                } else {
                    const bucketedMarkers = bucketEventMarkers(markers, activeResolution);

                    for (const [bucketDate, bucketEntries] of bucketedMarkers) {
                        const index = dateIndexMap.get(bucketDate);
                        if (index === undefined) continue;

                        let yValue: number;
                        if (bucketEntries[0]?.assetLabel) {
                            const overlayLookup = overlayDataByLabel.get(bucketEntries[0].assetLabel);
                            yValue = overlayLookup?.get(bucketDate) ?? resolvedLineData[index]?.value ?? 0;
                        } else {
                            yValue = resolvedLineData[index]?.value ?? 0;
                        }

                        scatterData.push({
                            value: [bucketDate, yValue],
                            markers: bucketEntries,
                            bucketInfo: bucketInfoByDate.get(bucketDate) ?? mapDateToBucket(bucketDate, activeResolution),
                            bucketValue: yValue,
                        });
                    }
                }

                if (scatterData.length === 0) continue;

                series.push({
                    type: 'scatter',
                    name: `Events: ${seriesLabel}`,
                    data: scatterData,
                    xAxisIndex: 0,
                    yAxisIndex: 0,
                    symbol: EVENT_SYMBOLS[eventType] ?? 'diamond',
                    symbolSize: 10,
                    itemStyle: {
                        color: eventColor,
                    },
                    emphasis: {
                        scale: 1.5,
                    },
                    tooltip: {
                        trigger: 'item' as const,
                        formatter: (params: any) => {
                            const marker = params.data?.marker as EventMarker | undefined;
                            const bucketMarkers = (params.data?.markers as EventMarker[] | undefined) ?? (marker ? [marker] : []);
                            if (bucketMarkers.length === 0) return '';

                            const bucketDate = params.data?.value?.[0] ?? bucketMarkers[bucketMarkers.length - 1]?.date;
                            const bucketInfo = params.data?.bucketInfo as BucketInfo | undefined;
                            let html = buildTooltipHeader(bucketDate, activeResolution, bucketInfo);

                            if (params.data?.bucketValue !== undefined) {
                                html += `<br/>💰 ${Number(params.data.bucketValue).toFixed(4)}`;
                            }

                            if (activeResolution === 'daily' && marker) {
                                html += `<br/>${formatEventEntry(marker, eventColor, false)}`;
                                return html;
                            }

                            html += `<br/><span style="font-size:11px;opacity:0.8">${$t('chart.tooltip.eventsInPeriod')}</span>`;
                            for (const bucketMarker of bucketMarkers) {
                                html += `<br/>${formatEventEntry(bucketMarker, eventColor, true)}`;
                            }
                            return html;
                        },
                        backgroundColor: isDark ? '#1e293b' : '#ffffff',
                        borderColor: isDark ? '#334155' : '#e2e8f0',
                        textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                    },
                    z: 20,
                });
            }
        }

        const {axes: secondaryAxes, extraAxesCount} = buildSecondaryYAxes(resolvedOverlaySignals, isDark, 0);
        const colors = getChartColors(isDark);
        const staleLookup = new Map<string, number>();
        const fxStaleLookup = new Map<string, number>();
        for (const point of resolvedLineData) {
            if (point.staleDays && point.staleDays > 0) staleLookup.set(point.date, point.staleDays);
            if (point.fxStaleDays && point.fxStaleDays > 0) fxStaleLookup.set(point.date, point.fxStaleDays);
        }
        const zoomWindow = computeZoomWindow(resolvedLineData, activeResolution, logicalRange);

        const option: echarts.EChartsOption = {
            animation: false,
            grid: [{top: 20, right: computeRightMargin(extraAxesCount), bottom: 20, left: 10, containLabel: true}],
            xAxis: [
                {
                    type: 'category',
                    data: dates,
                    gridIndex: 0,
                    axisLine: {lineStyle: {color: isDark ? '#475569' : '#d1d5db'}},
                    axisLabel: {color: isDark ? '#94a3b8' : '#6b7280', fontSize: 14},
                    splitLine: {show: false},
                },
            ],
            yAxis: [buildPriceYAxis({mode: yAxisMode, min: yAxisMin, max: yAxisMax, isPercentage}, colors, {gridIndex: 0, showGridLines}), ...secondaryAxes],
            dataZoom: [{...buildDataZoom([0])[0], start: zoomWindow.start, end: zoomWindow.end}],
            tooltip: {
                trigger: 'axis',
                backgroundColor: isDark ? '#1e293b' : '#ffffff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                confine: true,
                position: tooltipPositionSide,
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    if (!items.length) return '';
                    const date = String(items[0].axisValue || items[0].name || '');
                    let html = buildTooltipHeader(date, activeResolution, bucketInfoByDate.get(date));
                    const bandHelperNames = new Set<string>();
                    for (const sig of resolvedOverlaySignals) {
                        if ((sig.seriesType ?? 'line') === 'band') {
                            bandHelperNames.add(`${sig.label} Lower`);
                            bandHelperNames.add(`${sig.label} Band`);
                        }
                    }
                    const signalAxisMap = new Map<string, number>();
                    for (const sig of resolvedOverlaySignals) {
                        signalAxisMap.set(sig.label, sig.yAxisIndex ?? 0);
                    }
                    const shownNames = new Set<string>();
                    const firstValue = resolvedLineData.length > 0 ? resolvedLineData[0].value : null;
                    const conversionActive = hasOriginalValues && displayCurrencyProp && displayCurrencyFlag;
                    for (const p of items) {
                        if (p.seriesName === 'Pending' || p.seriesName === '__baseline__' || p.seriesName === '__overview__' || p.seriesType === 'scatter' || String(p.seriesName).startsWith('Events: ')) continue;
                        if (bandHelperNames.has(p.seriesName)) continue;
                        const rawVal = p.value;
                        const value = typeof rawVal === 'object' && rawVal?.value !== undefined ? rawVal.value : rawVal;
                        if (value === null || value === undefined) continue;
                        if (shownNames.has(p.seriesName)) continue;
                        shownNames.add(p.seriesName);
                        const suffix = isPercentage ? '%' : '';
                        const isGhost = hasOriginalValues && p.seriesName === ghostLabel;
                        const axisIdx = isGhost ? 0 : (signalAxisMap.get(p.seriesName) ?? 0);
                        const valueSuffix = axisIdx === 0 ? suffix : '';
                        const axisNote = axisIdx === 1 ? ' <span style="font-size:10px;color:#94a3b8">[RSI]</span>' : axisIdx === 2 ? ' <span style="font-size:10px;color:#a78bfa">[MACD]</span>' : '';

                        // Use signalLabelToHtml for proper icon rendering
                        let labelHtml: string;
                        let isGhostRow = false;
                        if (isGhost) {
                            // Ghost label: "💱 Name (flag CUR)" — truncate Name to same length as main (15)
                            const ghostDot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px;"></span>`;
                            // Extract name part from ghostLabel format "💱 Name (flag CUR)"
                            const nameMatch = ghostLabel.match(/^💱\s*(.+?)\s*(\([^)]+\))$/);
                            let truncatedGhost: string;
                            if (nameMatch) {
                                const name = nameMatch[1];
                                const currPart = nameMatch[2];
                                const truncName = name.length > 15 ? name.slice(0, 15) + '…' : name;
                                truncatedGhost = `💱 ${truncName} ${currPart}`;
                            } else {
                                truncatedGhost = ghostLabel.length > 30 ? ghostLabel.slice(0, 30) + '…' : ghostLabel;
                            }
                            labelHtml = `${ghostDot}<span title="${ghostLabel}">${truncatedGhost}</span>`;
                            isGhostRow = true;
                        } else {
                            const sigInfo = overlaySignalInfoMap?.get(p.seriesName);
                            if (sigInfo) {
                                // Append (flag currency) to overlay signal labels
                                // Skip for ghost signals — currency is already embedded in their label
                                const currSuffix = sigInfo.currency && !sigInfo.isGhost ? ` <span style="font-size:10px;opacity:0.7">(${sigInfo.currencyFlag || ''} ${sigInfo.currency})</span>` : '';
                                labelHtml = signalLabelToHtml(sigInfo, 15) + currSuffix;
                                if (sigInfo.isGhost) isGhostRow = true;
                            } else if (p.seriesName === mainSeriesName) {
                                // Main signal: 💱(flag currency) when conversion active, (flag currency) when not
                                let mainLabel: string;
                                let currSuffix = '';
                                if (conversionActive) {
                                    mainLabel = mainSeriesName;
                                    currSuffix = ` <span style="font-size:10px">(${displayCurrencyFlag} ${displayCurrencyProp}) 💱</span>`;
                                } else if (mainCurrencyProp) {
                                    mainLabel = mainSeriesName;
                                    currSuffix = ` <span style="font-size:10px">(${mainCurrencyFlagProp || ''} ${mainCurrencyProp})</span>`;
                                } else {
                                    mainLabel = mainSeriesName;
                                }
                                labelHtml =
                                    signalLabelToHtml(
                                        {
                                            label: mainLabel,
                                            iconUrl: mainIconUrl,
                                            assetType: mainAssetType,
                                            isCrown: true,
                                        },
                                        15,
                                    ) + currSuffix;
                            } else {
                                const colorDot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px;"></span>`;
                                labelHtml = `${colorDot}${p.seriesName}`;
                            }
                        }
                        let rowHtml = `${labelHtml}: ${Number(value).toFixed(4)}${valueSuffix}${axisNote}`;
                        if (isGhostRow) {
                            rowHtml = `<span style="opacity:0.7">${rowHtml}</span>`;
                        }
                        html += `<br/>${rowHtml}`;
                        // Show delta from first visible point for the main axis (yAxisIndex 0)
                        if (axisIdx === 0 && firstValue !== null && !isGhost) {
                            const numVal = Number(value);
                            if (isPercentage) {
                                // In % mode, value IS already the delta %
                                html += ` <span style="font-size:10px;color:${numVal >= 0 ? '#10b981' : '#ef4444'}">(Δ ${numVal >= 0 ? '+' : ''}${numVal.toFixed(2)}%)</span>`;
                            } else {
                                const deltaAbs = numVal - firstValue;
                                const deltaPct = firstValue !== 0 ? ((numVal - firstValue) / firstValue) * 100 : 0;
                                html += ` <span style="font-size:10px;color:${deltaAbs >= 0 ? '#10b981' : '#ef4444'}">(Δ ${deltaAbs >= 0 ? '+' : ''}${deltaAbs.toFixed(4)} / ${deltaPct >= 0 ? '+' : ''}${deltaPct.toFixed(2)}%)</span>`;
                            }
                        }
                    }
                    const dataPoint = staleLookup.get(date);
                    if (dataPoint !== undefined) {
                        const fxStale = fxStaleLookup.get(date);
                        if (fxStale !== undefined && fxStale > 0) {
                            const priceDaysBack = dataPoint;
                            const label = staleLabel ? staleLabel.replace('{days}', String(priceDaysBack)) : `Stale: ${priceDaysBack}d`;
                            html += `<br/><span style="color:#f59e0b;font-size:11px">⚠ ${label}</span>`;
                            const fxLabel = fxStaleLabel ? fxStaleLabel.replace('{days}', String(fxStale)) : `FX rate: ${fxStale}d old`;
                            html += `<br/><span style="color:#f59e0b;font-size:11px">⚠ ${fxLabel}</span>`;
                        } else {
                            const label = staleLabel ? staleLabel.replace('{days}', String(dataPoint)) : `Stale: ${dataPoint}d`;
                            html += `<br/><span style="color:#f59e0b;font-size:11px">⚠ ${label}</span>`;
                        }
                    }
                    return html;
                },
            },
            series,
        };

        // Resolution switch: the number of data points/series changes drastically
        // (daily <-> weekly/monthly). If a tooltip is currently showing (user hovering
        // while zooming — the exact gesture that triggers a resolution switch), ECharts
        // can crash inside its internal _showAxisTooltip trying to read stale
        // series/dataIndex references once the series are replaced by this full rebuild.
        // Hiding the tooltip first clears that internal state safely. Documented ECharts
        // workaround for this exact class of crash (series/axis structure changing while
        // an axis-trigger tooltip + mousewheel dataZoom are both active).
        if (lastRenderedResolution !== null && lastRenderedResolution !== activeResolution) {
            chartInstance.dispatchAction({type: 'hideTip'});
        }

        chartInstance.setOption(option, true);
        chartOptionSet = true;
        lastRenderedResolution = activeResolution;

        // Compute pixel-accurate arrow rotations after layout is established
        updateArrowRotations(chartInstance);
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer, updateArrowRotations);
        }
    }
</script>

<div class="space-y-2">
    <!-- Toolbar (hidden when parent provides external controls) -->
    {#if !hideToolbar}
        <ChartToolbar {chartType} {viewMode} onChartTypeChange={handleChartTypeChange} onViewModeChange={handleViewModeChange} {disableCandlestick} />
    {/if}

    <!-- Unified Chart -->
    <div class="relative">
        {#if !disableCandlestick}
            <!-- Floating chart-type toggle (top-left on chart) -->
            <div class="absolute top-2 left-12 z-10 flex rounded-lg border border-gray-200/70 dark:border-slate-600/70 overflow-hidden shadow-sm opacity-75 hover:opacity-100 transition-opacity">
                <button
                    class="p-1.5 transition-colors {chartType === 'line' ? 'bg-libre-green text-white' : 'bg-white/90 dark:bg-slate-800/90 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    data-testid="chart-type-line"
                    title="Line chart"
                    onclick={() => handleChartTypeChange('line')}><ChartLine size={14} /></button
                >
                <button
                    class="p-1.5 transition-colors {chartType === 'candlestick' ? 'bg-libre-green text-white' : 'bg-white/90 dark:bg-slate-800/90 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    data-testid="chart-type-candlestick"
                    title="Candlestick chart"
                    onclick={() => handleChartTypeChange('candlestick')}><ChartCandlestick size={14} /></button
                >
            </div>
        {/if}
        <div class="absolute top-2 left-28 z-10 pointer-events-none">
            <ResolutionBadge {resolution} />
        </div>
        {#if chartType === 'line'}
            <div bind:this={chartContainer} class="w-full" style="height: {chartHeight};" class:cursor-crosshair={measureMode}></div>
        {:else}
            <CandlestickChart
                data={getResolvedSeries(resolution).candleData}
                currency={currency || undefined}
                height={chartHeight}
                {showGridLines}
                {overlaySignals}
                {resolution}
                {viewMode}
                {measureMode}
                {onMeasureClick}
                {onMeasureHover}
                {onDblClick}
                {mainSeriesLabel}
                {mainIconUrl}
                {mainAssetType}
                displayCurrency={displayCurrencyProp}
                {displayCurrencyFlag}
                mainCurrency={mainCurrencyProp}
                mainCurrencyFlag={mainCurrencyFlagProp}
                {yAxisMode}
                {yAxisMin}
                {yAxisMax}
            />
        {/if}
    </div>
</div>
