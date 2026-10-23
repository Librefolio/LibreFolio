<!--
  LineChart — ECharts line chart with stale-data gradient, segment coloring, and zoom.

  Features:
  - Line series with configurable area fill
  - Per-point opacity based on staleDays (stale gradient)
  - Segment-based color by baseline: green above baseline, red below (both % and abs modes)
  - Y-axis always visible with values (also mini-axis mode for compact cards)
  - Tooltip with date, value, stale warning, and % note
  - Dark mode support with MutationObserver
  - ResizeObserver for responsive sizing
  - Mouse wheel zoom + drag-to-pan via ECharts inside dataZoom
  - Click event emission for parent components

  Used by: PriceChartCompact, PriceChartFull (line mode)
-->
<script lang="ts">
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';
    import {chartInitOptions} from '$lib/components/charts/chartPixelRatio';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {t} from '$lib/i18n';
    import type {RenderedSignal} from '$lib/charts/signals';
    import type {AxisScaleSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {buildBandSeries, buildBarSeries, buildMainSeries, buildSignalReferencePrimitives, COLORS, noteArrowMarkers, updateArrowRotations} from './lineChartHelpers';
    import {toRgba} from '$lib/theme/colorAlpha';
    import {assignOverlaySignalAxes, buildSecondaryYAxes, computeRightMargin} from './chartCoreHelpers';
    import {scheduleFirstRenderStabilityFix, tooltipPositionSide} from './echartsTooltipHelpers';
    import {aggregateLineSeries, chooseCompactResolution, compactPlotWidth, downsampleRenderedSignal, mapDateToBucket, type ChartResolution} from './timeSeriesAggregation';
    import {truncateName} from '$lib/utils/text';
    import {buildResponsiveXAxisPolicy, categoryAxisLabelPatch, visiblePointCountFromZoom, ZOOM_LABEL_SETTLE_MS} from './responsiveXAxis';
    import {clearTimer} from '$lib/utils/core/clearTimer';
    import {formatFixed, formatPrice} from '$lib/utils/core/formatFixed';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {chartNeutrals, PRICE_SERIES} from '$lib/theme/chartTheme';
    import {isDarkTheme, onChartColorsChange, onThemeClassChange} from '$lib/theme/themeMode';

    // =========================================================================
    // Types
    // =========================================================================

    export interface LineDataPoint {
        date: string;
        value: number;
        /** True when the point exists but its numeric value is unavailable; rendered as an ECharts null gap. */
        missing?: boolean;
        staleDays?: number;
        fxStaleDays?: number;
        originalCurrency?: string;
        /** Flag emoji for the original currency (e.g. 🇺🇸) — pre-computed by parent */
        originalCurrencyFlag?: string;
        /** Original (unconverted) value — from original_close when FX conversion is active */
        originalValue?: number;
        /** OHLCV fields — optional, used by CandlestickChart */
        open?: number | null;
        high?: number | null;
        low?: number | null;
        close?: number | null;
        volume?: number | null;
        /** Logical aggregation bucket boundaries. */
        bucketStart?: string;
        bucketEnd?: string;
        /** Real observation date selected as the bucket representative. */
        representativeDate?: string;
        /** Number of finite source points observed in this bucket. */
        sourcePointCount?: number;
    }

    interface Props {
        data: LineDataPoint[];
        /** Y-axis label / currency code */
        currency?: string;
        /** Show area fill under the line */
        areaFill?: boolean;
        /** Show stale-data gradient (per-point opacity) */
        showGradient?: boolean;
        /** Enable baseline coloring (red below baseline, green above) */
        colorByBaseline?: boolean;
        /**
         * The base of the colouring and of the dashed reference line in the absolute view. Without it, the base is the
         * first point of `data`; a compact chart draws a reduced series, so a page that knows a base the reduction hides
         * hands it in. The percentage view's base is 0 whatever this says.
         */
        baselineValue?: number;
        /** Show grid split lines */
        showGridLines?: boolean;
        /** CSS height */
        height?: string;
        /** Compact mode (no axis labels, no tooltip, thinner line) */
        compact?: boolean;
        /** Show mini Y-axis in compact mode (2-3 ticks, right side) */
        showMiniAxis?: boolean;
        /** Color for the line (light mode) — if undefined, uses theme default */
        lineColor?: string;
        /** Color for the line (dark mode) — if undefined, uses theme default */
        darkLineColor?: string;
        /** Color for pending edit points (overlay) */
        pendingColor?: string;
        /** Pending edit points to show as overlay */
        pendingData?: LineDataPoint[];
        /** Called when a data point is clicked */
        onPointClick?: (date: string, value: number) => void;
        /** Compact mode: told the static resolution chosen for the data it was given, each time it is drawn (Y5-F3) */
        onresolution?: (resolution: ChartResolution) => void;
        /** View mode (for tooltip formatting and segment colors) */
        viewMode?: 'absolute' | 'percentage';
        /** Y-axis mode: 'auto' = fit to data, 'include0' = always show 0, 'custom' = user-defined min/max */
        yAxisMode?: 'auto' | 'include0' | 'custom';
        /** Custom Y-axis minimum (only when yAxisMode === 'custom') */
        yAxisMin?: number;
        /** Custom Y-axis maximum (only when yAxisMode === 'custom') */
        yAxisMax?: number;
        /** Overlay signals to render as additional line series */
        overlaySignals?: RenderedSignal[];
        /** Stable semantic settings for active non-primary axes. */
        secondaryAxisScales?: Record<string, AxisScaleSettings>;
    }

    let {
        data = [],
        currency = '',
        areaFill = true,
        showGradient = true,
        colorByBaseline = true,
        baselineValue: baselineOverride,
        showGridLines = true,
        height = '300px',
        compact = false,
        showMiniAxis = false,
        lineColor,
        darkLineColor,
        pendingColor,
        pendingData = [],
        onPointClick,
        onresolution,
        viewMode = 'absolute',
        yAxisMode = 'auto',
        yAxisMin,
        yAxisMax,
        overlaySignals = [],
        secondaryAxisScales = {},
    }: Props = $props();

    // Default colors — imported from lineChartHelpers
    const DEFAULT_LINE_LIGHT = COLORS.lineLight;
    const DEFAULT_LINE_DARK = COLORS.lineDark;
    const GREEN_LIGHT = COLORS.greenLight;
    const GREEN_DARK = COLORS.greenDark;
    const RED_LIGHT = COLORS.redLight;
    const RED_DARK = COLORS.redDark;

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement;
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    /** Guard: prevents ResizeObserver from calling resize() before first setOption() */
    let chartOptionSet = false;
    let needsInitialLayoutStabilityPass = false;
    let currentRenderedData: LineDataPoint[] = [];
    let responsiveXAxisCompact = false;
    /** The last zoom window, and the timer that, once the gesture settles, re-spaces the x labels on it (47-1) and re-aims the arrow markers (Y-8). Plain variables: the teardown reads them. */
    let lastZoomEvent: unknown = null;
    let zoomLabelTimer: ReturnType<typeof setTimeout> | null = null;

    /** How many of the drawn categories the last zoom left visible; undefined before any zoom. */
    function zoomedCategoryCount(): number | undefined {
        return visiblePointCountFromZoom(lastZoomEvent, currentRenderedData.length) ?? undefined;
    }

    function scheduleZoomedAxisLabels(event: unknown) {
        lastZoomEvent = event;
        zoomLabelTimer = clearTimer(zoomLabelTimer);
        zoomLabelTimer = setTimeout(() => {
            zoomLabelTimer = null;
            applyZoomedAxisLabels();
            // Once per gesture, never per tick: it reads getOption(), a deep copy of the whole option, and writes every series back (Y-8).
            if (chartInstance) updateArrowRotations(chartInstance);
        }, ZOOM_LABEL_SETTLE_MS);
    }

    /** Re-space the category labels on the zoomed window: the step is computed on all the points otherwise (47-1). */
    function applyZoomedAxisLabels() {
        if (!chartInstance || compact || currentRenderedData.length === 0) return;
        const visibleCount = zoomedCategoryCount();
        if (visibleCount === undefined) return;
        const policy = buildResponsiveXAxisPolicy({
            width: chartContainer.clientWidth,
            values: currentRenderedData.map((point) => point.date),
            locale: uiLocale(),
            axisType: 'category',
            visibleCount,
        });
        responsiveXAxisCompact = policy.compact;
        chartInstance.setOption({xAxis: {axisLabel: categoryAxisLabelPatch(policy)}}, {lazyUpdate: true});
    }

    const COMPACT_RESIZE_EPSILON_PX = 4;

    let lastSourceRef: LineDataPoint[] | null = null;
    let aggregatedByResolution = new Map<ChartResolution, LineDataPoint[]>();
    let lastMeasuredWidthPx = 0;
    let lastChosenResolution: ChartResolution | null = null;
    let lastWeeklyBucketCount = 0;

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        const redraw = () => {
            if (chartContainer && data.length > 0) renderChart();
        };
        const observer = onThemeClassChange(redraw);
        const chartColors = onChartColorsChange(redraw);
        return () => {
            observer.disconnect();
            chartColors.disconnect();
            cleanup();
        };
    });

    $effect(() => {
        if (chartContainer && data) {
            // Touch all visual props to register reactive dependencies
            void overlaySignals;
            void areaFill;
            void colorByBaseline;
            void baselineOverride;
            void showGridLines;
            void showGradient;
            void viewMode;
            void compact;
            void showMiniAxis;
            void lineColor;
            void darkLineColor;
            // Touch yAxisMode to register reactive dependency
            void yAxisMode;
            void yAxisMin;
            void yAxisMax;
            void secondaryAxisScales;
            void uiLocale();
            tick().then(renderChart);
        }
    });

    function cleanup() {
        resizeObserver?.disconnect();
        resizeObserver = null;
        chartOptionSet = false;
        currentRenderedData = [];
        zoomLabelTimer = clearTimer(zoomLabelTimer);
        lastZoomEvent = null;
        chartInstance?.dispose();
        chartInstance = null;
    }

    function countWeeklyBuckets(points: LineDataPoint[]): number {
        const weeklyBuckets = new Set<string>();

        for (const point of points) {
            const {bucketStart, bucketEnd} = mapDateToBucket(point.date, 'weekly');
            weeklyBuckets.add(`${bucketStart}|${bucketEnd}`);
        }

        return weeklyBuckets.size;
    }

    function ensureCompactCache() {
        if (data === lastSourceRef) return;

        lastSourceRef = data;
        aggregatedByResolution = new Map<ChartResolution, LineDataPoint[]>([['daily', data]]);
        lastMeasuredWidthPx = 0;
        lastChosenResolution = null;
        lastWeeklyBucketCount = countWeeklyBuckets(data);
    }

    function getCompactAggregatedData(resolution: ChartResolution): LineDataPoint[] {
        ensureCompactCache();

        if (resolution === 'daily') return data;

        const cached = aggregatedByResolution.get(resolution);
        if (cached) return cached;

        const aggregated = aggregateLineSeries(data, resolution);
        aggregatedByResolution.set(resolution, aggregated);
        return aggregated;
    }

    function getCompactPlotWidthPx() {
        const measuredWidth = chartContainer?.getBoundingClientRect().width || chartInstance?.getWidth() || 0;
        return compactPlotWidth(measuredWidth, showMiniAxis);
    }

    /** The rule a card's `max_points` is sized by (`timeSeriesAggregation.ts`, Z-29b): a series sampled for this plot stays as it is. */
    function chooseStaticResolution(dailyPointCount: number, plotWidthPx: number): ChartResolution {
        return chooseCompactResolution({dailyCount: dailyPointCount, weeklyCount: lastWeeklyBucketCount}, plotWidthPx);
    }

    function resizeChartOnly() {
        try {
            chartInstance?.resize();
            if (chartInstance && !compact && currentRenderedData.length > 0) {
                const policy = buildResponsiveXAxisPolicy({
                    width: chartContainer.clientWidth,
                    values: currentRenderedData.map((point) => point.date),
                    locale: uiLocale(),
                    axisType: 'category',
                    visibleCount: zoomedCategoryCount(),
                });
                const wasCompact = responsiveXAxisCompact;
                responsiveXAxisCompact = policy.compact;
                if (policy.axisLabel) {
                    chartInstance.setOption({xAxis: {axisLabel: categoryAxisLabelPatch(policy)}}, {lazyUpdate: true});
                } else if (wasCompact) {
                    renderChart();
                }
            }
            // Re-aimed once the resize settles, by the settle that re-spaces the labels, never on each callback: a re-aim
            // deep-copies the whole option (Y-25)
            scheduleZoomedAxisLabels(lastZoomEvent);
        } catch (_) {
            /* ignore coord errors during resize */
        }
    }

    function handleCompactResize() {
        const plotWidthPx = getCompactPlotWidthPx();
        if (plotWidthPx === 0) return;

        if (lastMeasuredWidthPx > 0 && Math.abs(plotWidthPx - lastMeasuredWidthPx) < COMPACT_RESIZE_EPSILON_PX) {
            lastMeasuredWidthPx = plotWidthPx;
            resizeChartOnly();
            return;
        }

        ensureCompactCache();
        const targetResolution = chooseStaticResolution(data.length, plotWidthPx);
        lastMeasuredWidthPx = plotWidthPx;

        if (lastChosenResolution === targetResolution) {
            resizeChartOnly();
            return;
        }

        chartInstance?.resize();
        renderChart();
    }

    // =========================================================================
    // Helpers — see lineChartHelpers.ts for color utilities
    // =========================================================================

    // =========================================================================
    // Chart Rendering
    // =========================================================================

    function renderChart() {
        if (!chartContainer || data.length === 0) return;

        // Ensure ResizeObserver is set up even before first render,
        // so it can trigger renderChart when container becomes visible.
        if (!resizeObserver) {
            resizeObserver = new ResizeObserver(() => {
                if (chartOptionSet) {
                    if (compact) {
                        handleCompactResize();
                    } else {
                        resizeChartOnly();
                    }
                } else if (chartContainer && data.length > 0) {
                    // Chart not yet initialized (e.g. container was zero-size on first attempt).
                    renderChart();
                }
            });
            resizeObserver.observe(chartContainer);
        }

        // Skip if container has no dimensions (e.g. during modal open animation).
        // The ResizeObserver will trigger a re-render once the container is visible.
        const rect = chartContainer.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, CHART_INIT_THEME, chartInitOptions(chartContainer));
            attachChartReady(chartInstance, chartContainer, 'line');
            needsInitialLayoutStabilityPass = true;

            if (onPointClick) {
                chartInstance.on('click', 'series.line', (params: any) => {
                    if (params.dataIndex !== undefined && currentRenderedData[params.dataIndex]) {
                        const point = currentRenderedData[params.dataIndex];
                        if (!point.missing) onPointClick!(point.date, point.value);
                    }
                });
            }

            // A zoom changes the pixel aspect: the x labels are re-spaced on the window, and the arrow markers re-aimed, once the
            // gesture settles, never on each tick (47-1, Y-8)
            chartInstance.on('dataZoom', (event: unknown) => {
                scheduleZoomedAxisLabels(event);
            });
        }

        const isDark = isDarkTheme();
        const neutrals = chartNeutrals(isDark, chartContainer);
        const isPercentage = viewMode === 'percentage';

        const baseColor = isDark ? darkLineColor || DEFAULT_LINE_DARK : lineColor || DEFAULT_LINE_LIGHT;

        const greenColor = isDark ? GREEN_DARK : GREEN_LIGHT;
        const redColor = isDark ? RED_DARK : RED_LIGHT;

        let renderedData = data;
        let activeOverlaySignals = overlaySignals;

        if (compact) {
            ensureCompactCache();
            const plotWidthPx = getCompactPlotWidthPx();
            const resolution = chooseStaticResolution(data.length, plotWidthPx);

            lastMeasuredWidthPx = plotWidthPx;
            lastChosenResolution = resolution;
            onresolution?.(resolution);
            renderedData = getCompactAggregatedData(resolution);

            if (resolution !== 'daily') {
                activeOverlaySignals = overlaySignals.map((signal) => downsampleRenderedSignal(signal, resolution, renderedData)).filter((signal) => signal.data.length > 0);
            }
        }
        activeOverlaySignals = assignOverlaySignalAxes(activeOverlaySignals);
        const overlayPointMeta = new Map<string, LineDataPoint>();
        for (const signal of activeOverlaySignals) {
            for (const point of signal.data) {
                overlayPointMeta.set(`${signal.label}|${point.date}`, point);
            }
        }

        currentRenderedData = renderedData;

        // Build series data
        const dates = renderedData.map((d) => d.date);

        // Determine if we need baseline coloring (green above baseline, red below)
        // The base is the first point of the data it was given: a compact chart draws a reduced series, whose first point is
        // the end of the first bucket.
        const useBaselineColoring = colorByBaseline;
        const firstValue = data.find((point) => !point.missing)?.value ?? 0;
        const baselineValue = isPercentage ? 0 : Number.isFinite(baselineOverride) ? (baselineOverride as number) : firstValue;

        // Build per-point stale data array
        const staleDaysArr = renderedData.map((d) => d.staleDays ?? 0);

        const series: any[] = [];
        // Tooltip needs a stable series name for the main data — we use this name
        // for both single-series mode and the segmented baseline-color mode.
        const mainSeriesName = currency || 'Value';

        // ── Unified main series: handles baseline coloring + stale gradient together ──
        {
            const values = renderedData.map((d) => (d.missing ? null : d.value));
            const lineW = compact ? 1.5 : 2;
            const mainSeriesList = buildMainSeries(values, staleDaysArr, baseColor, greenColor, redColor, isDark, areaFill, lineW, mainSeriesName, useBaselineColoring, baselineValue, showGradient);
            series.push(...mainSeriesList);
        }

        // Pending edits overlay
        if (pendingData && pendingData.length > 0) {
            series.push({
                type: 'scatter',
                name: 'Pending',
                data: pendingData
                    .map((d) => {
                        const idx = dates.indexOf(d.date);
                        return idx >= 0 ? [idx, d.value] : null;
                    })
                    .filter(Boolean),
                symbol: 'diamond',
                symbolSize: 10,
                itemStyle: {
                    // Read here, not as the prop's default: a default is kept, and a theme switch would not reach it
                    color: pendingColor ?? PRICE_SERIES.pendingEditPoint,
                    borderColor: neutrals.price.pendingEditPointRing,
                    borderWidth: 2,
                },
                z: 10,
            });
        }

        // Overlay signals — rendered as additional series.
        // Supports three seriesType modes:
        //   'line' (default) — standard overlay line
        //   'bar'            — vertical bars (e.g. MACD histogram) on secondary axis
        //   'band'           — confidence band (e.g. Bollinger): stacked area lower→upper + middle line
        if (activeOverlaySignals && activeOverlaySignals.length > 0) {
            for (const signal of activeOverlaySignals) {
                if (!signal.data.length) continue;

                const sType = signal.seriesType ?? 'line';

                // Build date→value lookup, then align to main chart's date axis
                const signalLookup = new Map(signal.data.map((d) => [d.date, d.value]));
                const signalSeriesData: any[] = dates.map((date) => {
                    const val = signalLookup.get(date);
                    return val ?? null;
                });

                // ─── BAND (Confidence Band / Bollinger) ─────────────────────
                if (sType === 'band' && signal.bandData) {
                    const bandSeries = buildBandSeries(signal, dates, isDark);
                    series.push(...bandSeries);
                    continue;
                }

                // ─── BAR (MACD Histogram) ───────────────────────────────────
                if (sType === 'bar') {
                    series.push(buildBarSeries(signal, signalSeriesData, isDark));
                    continue;
                }

                // ─── LINE (default) ─────────────────────────────────────────
                const overlaySeries: any = {
                    type: 'line',
                    name: signal.label,
                    data: signalSeriesData,
                    connectNulls: signal.connectNulls ?? true,
                    smooth: false,
                    symbol: 'none',
                    showSymbol: false,
                    sampling: 'lttb',
                    yAxisIndex: signal.yAxisIndex ?? 0,
                    lineStyle: {
                        color: signal.color,
                        width: signal.lineWidth,
                        type: signal.lineType,
                        opacity: signal.opacity ?? 1,
                    },
                    itemStyle: {
                        color: signal.color,
                        opacity: signal.opacity ?? 1,
                    },
                    ...(sType === 'area'
                        ? {
                              areaStyle: {
                                  color: toRgba(signal.color, signal.fillOpacity ?? 0.2),
                                  origin: 0,
                              },
                          }
                        : {}),
                    emphasis: {
                        focus: 'none',
                    },
                    z: sType === 'area' ? 0 : 1, // below main series
                    ...buildSignalReferencePrimitives(signal, isDark),
                };

                // Endpoint markers at start/end of signal data
                // Arrow rotation is computed post-render by updateArrowRotations() using pixel coords.
                if ((signal.markerStart || signal.markerEnd) && signalSeriesData.length > 0) {
                    const markData: any[] = [];

                    if (signal.markerStart) {
                        for (let i = 0; i < signalSeriesData.length; i++) {
                            const v = signalSeriesData[i];
                            if (v !== null && v !== undefined) {
                                markData.push({
                                    coord: [dates[i], v],
                                    symbol: signal.markerStart,
                                    symbolSize: Math.max(signal.lineWidth * 3, 8),
                                    symbolRotate: 0, // real rotation set by updateArrowRotations()
                                    itemStyle: {color: signal.color},
                                });
                                break;
                            }
                        }
                    }
                    if (signal.markerEnd) {
                        for (let i = signalSeriesData.length - 1; i >= 0; i--) {
                            const v = signalSeriesData[i];
                            if (v !== null && v !== undefined) {
                                markData.push({
                                    coord: [dates[i], v],
                                    symbol: signal.markerEnd,
                                    symbolSize: Math.max(signal.lineWidth * 3, 8),
                                    symbolRotate: 0, // real rotation set by updateArrowRotations()
                                    itemStyle: {color: signal.color},
                                });
                                break;
                            }
                        }
                    }
                    if (markData.length > 0) {
                        overlaySeries.markPoint = {
                            data: markData,
                            label: {show: false},
                            animation: false,
                        };
                    }
                }

                series.push(overlaySeries);
            }
        }

        // Baseline reference line — drawn as a dedicated flat-line series instead of
        // markLine to avoid an ECharts bug where markLine + visualMap (piecewise,
        // dimension:1, tuple data) crashes with "Cannot read properties of undefined
        // (reading 'coord')" during setOption/resize.
        if (useBaselineColoring) {
            const baselineData = renderedData.map(() => baselineValue);
            series.push({
                type: 'line',
                name: '__baseline__',
                data: baselineData,
                symbol: 'none',
                showSymbol: false,
                sampling: 'lttb',
                lineStyle: {
                    color: neutrals.price.baseline,
                    type: 'dashed',
                    width: 1,
                },
                itemStyle: {color: 'transparent'},
                emphasis: {disabled: true},
                tooltip: {show: false},
                silent: true,
                z: 0,
                yAxisIndex: 0,
            });
        }

        // Grid configuration
        const showYAxis = !compact || showMiniAxis;
        const {axes: secondaryAxes, extraAxesCount} = buildSecondaryYAxes(activeOverlaySignals, isDark, 0, !compact, secondaryAxisScales);

        const gridConfig = compact
            ? {
                  top: 5,
                  right: showMiniAxis ? 45 : 5,
                  bottom: 5,
                  left: 5,
                  containLabel: false,
              }
            : {
                  top: 20,
                  right: computeRightMargin(extraAxesCount),
                  bottom: 25,
                  left: 10,
                  containLabel: true,
              };

        // Pre-compute stale lookup map for O(1) tooltip access (instead of O(n) data.find per hover)
        const staleLookup = new Map<string, number>();
        for (const d of renderedData) {
            if (d.staleDays && d.staleDays > 0) staleLookup.set(d.date, d.staleDays);
        }
        // Preserve user zoom state across re-renders (adding signals, toggling options).
        // Without this, setOption({...}, true) replaces dataZoom and resets scroll position.
        // Read before the axis policy, so the labels are spaced on the window about to be restored (47-1).
        let savedZoom: {start: number; end: number} | null = null;
        if (chartOptionSet && chartInstance) {
            try {
                const opt = chartInstance.getOption() as any;
                if (opt?.dataZoom?.[0]) {
                    const dz = opt.dataZoom[0];
                    if (typeof dz.start === 'number' && typeof dz.end === 'number') {
                        savedZoom = {start: dz.start, end: dz.end};
                    }
                }
            } catch (_) {
                /* ignore */
            }
        }
        const restoredZoomCount = savedZoom && !compact ? visiblePointCountFromZoom(savedZoom, dates.length) : null;
        const xAxisPolicy = buildResponsiveXAxisPolicy({
            width: rect.width,
            values: dates,
            locale: uiLocale(),
            axisType: 'category',
            visibleCount: restoredZoomCount ?? undefined,
        });
        responsiveXAxisCompact = xAxisPolicy.compact;

        const option: echarts.EChartsOption = {
            animation: false,
            grid: gridConfig,
            dataZoom: compact
                ? []
                : [
                      {
                          type: 'inside',
                          xAxisIndex: 0,
                          filterMode: 'filter',
                          zoomOnMouseWheel: true,
                          moveOnMouseMove: true,
                      },
                  ],
            xAxis: {
                type: 'category',
                data: dates,
                show: !compact,
                axisLine: {lineStyle: {color: neutrals.priceAxis.line}},
                axisLabel: {
                    color: neutrals.priceAxis.label,
                    fontSize: 11,
                    formatter: xAxisPolicy.formatter,
                    ...(xAxisPolicy.axisLabel ?? {}),
                },
                splitLine: {show: false},
            },
            yAxis: [
                // Axis 0 — Primary (price scale, right in compact / left in full)
                (() => {
                    // Compute min/max/scale based on yAxisMode
                    const isCustom = yAxisMode === 'custom';
                    const isInclude0 = yAxisMode === 'include0';
                    // 'auto' → scale:true (ECharts fits to data range, may not include 0)
                    // 'include0' → scale:false (ECharts default, always includes 0)
                    // 'custom' → explicit min/max
                    // Auto-swap if min > max to prevent chart explosion
                    let effectiveMin = isCustom && yAxisMin !== undefined ? yAxisMin : undefined;
                    let effectiveMax = isCustom && yAxisMax !== undefined ? yAxisMax : undefined;
                    if (effectiveMin !== undefined && effectiveMax !== undefined && effectiveMin > effectiveMax) {
                        [effectiveMin, effectiveMax] = [effectiveMax, effectiveMin];
                    }
                    return {
                        type: 'value' as const,
                        show: showYAxis,
                        position: compact && showMiniAxis ? ('right' as const) : ('left' as const),
                        min: effectiveMin,
                        max: effectiveMax,
                        axisLine: {show: !compact, lineStyle: {color: neutrals.priceAxis.line}},
                        axisTick: {show: !compact},
                        splitNumber: compact && showMiniAxis ? 2 : undefined,
                        axisLabel: {
                            show: showYAxis,
                            color: neutrals.priceAxis.label,
                            fontSize: compact && showMiniAxis ? 9 : 11,
                            formatter: isPercentage
                                ? (v: number) => formatPercent(v, {digits: 1, signed: false})
                                : (v: number) => {
                                      if (Math.abs(v) >= 1000) return `${formatFixed(v / 1000, 1)}k`;
                                      if (Math.abs(v) >= 1) return formatFixed(v, 2);
                                      return formatFixed(v, 4, {trim: true});
                                  },
                        },
                        splitLine: {
                            show: showGridLines && showYAxis,
                            lineStyle: {
                                color: neutrals.priceAxis.gridLine,
                                type: 'dashed' as const,
                                opacity: compact && showMiniAxis ? 0.5 : 1,
                            },
                        },
                        scale: !isInclude0,
                    };
                })(),
                ...secondaryAxes,
            ],
            tooltip: compact
                ? undefined
                : {
                      trigger: 'axis',
                      appendToBody: true,
                      confine: true,
                      position: tooltipPositionSide,
                      backgroundColor: neutrals.tooltip.box.background,
                      borderColor: neutrals.tooltip.box.border,
                      textStyle: {color: neutrals.tooltip.box.text, fontSize: 12},
                      formatter: (params: any) => {
                          const items = Array.isArray(params) ? params : [params];
                          if (!items.length) return '';
                          const date = items[0].axisValue || items[0].name;
                          let html = `<strong>${formatDay(String(date))}</strong>`;

                          // Build a set of band helper series names to skip in tooltip
                          const bandHelperNames = new Set<string>();
                          for (const sig of activeOverlaySignals) {
                              if ((sig.seriesType ?? 'line') === 'band') {
                                  bandHelperNames.add(`${sig.label} Lower`);
                                  bandHelperNames.add(`${sig.label} Band`);
                              }
                          }

                          // Build yAxisIndex lookup for overlay signals by name
                          const signalAxisMap = new Map<string, number>();
                          const signalAxisLabelMap = new Map<number, string>();
                          for (const sig of activeOverlaySignals) {
                              const axisIndex = sig.yAxisIndex ?? 0;
                              signalAxisMap.set(sig.label, axisIndex);
                              if (axisIndex > 0 && !signalAxisLabelMap.has(axisIndex)) {
                                  signalAxisLabelMap.set(axisIndex, sig.axisLabel ?? `AXIS ${axisIndex}`);
                              }
                          }

                          // Track already-shown series names to deduplicate segmented baseline entries
                          const shownNames = new Set<string>();

                          for (const p of items) {
                              // Skip pending scatter series
                              if (p.seriesName === 'Pending') continue;
                              // Skip baseline reference line
                              if (p.seriesName === '__baseline__') continue;
                              // Skip band helper series (Lower invisible + shaded delta)
                              if (bandHelperNames.has(p.seriesName)) continue;

                              // Extract value (plain number or object with .value)
                              const rawVal = p.value;
                              const value = typeof rawVal === 'object' && rawVal?.value !== undefined ? rawVal.value : rawVal;
                              if (value === null || value === undefined) continue;

                              // Deduplicate: for segmented baseline coloring, multiple series
                              // share the same name. Only show the first non-null one.
                              if (shownNames.has(p.seriesName)) continue;
                              shownNames.add(p.seriesName);

                              const suffix = isPercentage ? '%' : '';
                              const colorDot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px;"></span>`;
                              const axisIdx = signalAxisMap.get(p.seriesName) ?? 0;
                              // Signals on non-primary axes have their own scale — show without % suffix
                              const valueSuffix = axisIdx === 0 ? suffix : '';
                              const axisLabel = signalAxisLabelMap.get(axisIdx);
                              const axisNoteHtml = axisLabel ? ` <span style="font-size:10px;color:${neutrals.tooltip.aside}">[${escapeHtml(axisLabel)}]</span>` : '';
                              html += `<br/>${colorDot}${escapeHtml(truncateName(String(p.seriesName ?? '')))}: ${formatPrice(Number(value), {minDecimals: 4})}${valueSuffix}${axisNoteHtml}`;
                              const representativePoint = overlayPointMeta.get(`${p.seriesName}|${date}`);
                              if (representativePoint?.representativeDate && representativePoint.representativeDate !== date) {
                                  html += ` <span style="font-size:10px;color:${neutrals.tooltip.aside}">(${$t('chart.tooltip.valueAt', {values: {date: formatDay(representativePoint.representativeDate)}})})</span>`;
                              }

                              // For band signals, also show upper/lower in the tooltip
                              const bandSignal = activeOverlaySignals.find((s) => s.label === p.seriesName && (s.seriesType ?? 'line') === 'band' && s.bandData);
                              if (bandSignal?.bandData) {
                                  const dataIdx = bandSignal.data.findIndex((d) => d.date === date);
                                  if (dataIdx >= 0) {
                                      html += `<br/><span style="padding-left:12px;font-size:11px;color:${neutrals.tooltip.aside}">${$t('chart.tooltip.upper')}: ${formatPrice(bandSignal.bandData.upper[dataIdx], {minDecimals: 4})}${suffix} · ${$t('chart.tooltip.lower')}: ${formatPrice(bandSignal.bandData.lower[dataIdx], {minDecimals: 4})}${suffix}</span>`;
                                  }
                              }
                          }

                          // Stale warning for main series
                          const staleDays = staleLookup.get(date);
                          if (staleDays !== undefined) {
                              html += `<br/><span style="color:${neutrals.tooltip.staleWarning};font-size:11px">⚠ ${$t('chart.tooltip.stale', {values: {days: staleDays}})}</span>`;
                          }
                          if (isPercentage) {
                              html += `<br/><span style="color:${neutrals.tooltip.aside};font-size:10px">${$t('chart.tooltip.percentNote')}</span>`;
                          }
                          return html;
                      },
                  },
            series,
        };

        // Single pass: render everything at once — no visualMap needed
        // (baseline coloring is handled by segmented series above)

        chartInstance.setOption(option, true);
        noteArrowMarkers(chartInstance, option);
        chartOptionSet = true;

        // Restore zoom position if the user had zoomed/panned
        if (savedZoom && !compact) {
            chartInstance.dispatchAction({
                type: 'dataZoom',
                start: savedZoom.start,
                end: savedZoom.end,
            });
        }

        // Compute pixel-accurate arrow rotations after layout is established, on the zoom just restored: the restore's
        // dataZoom event only schedules the settle, so aiming them before it left them on the whole axis until then (Y-8)
        updateArrowRotations(chartInstance);
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer, updateArrowRotations);
        }
    }
</script>

<div bind:this={chartContainer} class="w-full" style="height: {height};"></div>
