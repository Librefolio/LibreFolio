<!--
  CandlestickChart — ECharts candlestick chart with optional volume bars.

  Architecture: Two ECharts grids in a single instance.
  - grid[0]: Price — candlestick series + overlay signals (EMA, BB, RSI, MACD…)
  - grid[1]: Volume — bar series (hidden when showVolume=false)
  - dataZoom: 'inside' type, links both x-axes for synchronised zoom/pan

  Y-axes:
    yAxis[0] = price (scale:true, grid[0])
    yAxis[1] = RSI / secondary (right, grid[0]) — always declared to avoid coord crash
    yAxis[2] = MACD / tertiary (right+offset, grid[0]) — always declared
    yAxis[3] = volume (hidden, auto-scale, grid[1]) — only rendered when showVolume=true

  Overlay signals keep their original yAxisIndex (0 / 1 / 2) unchanged — same
  as LineChart. Volume is on yAxis[3] so no conflict.

  Used by: PriceChartFull (candlestick mode)
-->
<script lang="ts">
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {CHART_INIT_THEME} from '$lib/components/charts/chartFont';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {_ as t} from '$lib/i18n';
    import type {RenderedSignal} from '$lib/charts/signals';
    import type {LineDataPoint} from './LineChart.svelte';
    import {COLORS, noteArrowMarkers, updateArrowRotations} from './lineChartHelpers';
    import {toRgba} from '$lib/theme/colorAlpha';
    import {signalLabelToHtml} from '$lib/charts/signalLabel';
    import {assignOverlaySignalAxes, buildPriceYAxis, buildSecondaryYAxes, buildOverlaySignalSeries, buildDataZoom, computeRightMargin, getChartColors} from './chartCoreHelpers';
    import {scheduleFirstRenderStabilityFix, tooltipPositionSide} from './echartsTooltipHelpers';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from './echartsDataZoomTouchPan';
    import {downsampleRenderedSignal, type ChartResolution} from './timeSeriesAggregation';
    import {bucketSpanUpTo, formatMonthLabel, getBucketInfo} from './priceChartHelpers';
    import {buildCandleSeriesData, computePercentageBase, formatCandlePrice, formatVolume, hasRenderableVolume, isBullishBar, parseCandleTooltipValue} from './candlestickChartHelpers';
    import type {AxisScaleSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {truncateName} from '$lib/utils/text';
    import {buildResponsiveXAxisPolicy, categoryAxisLabelPatch, visiblePointCountFromZoom, ZOOM_LABEL_SETTLE_MS} from './responsiveXAxis';
    import {clearTimer} from '$lib/utils/core/clearTimer';
    import {formatFixed} from '$lib/utils/core/formatFixed';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {CHART_TOOLTIP_COLORS, chartNeutrals} from '$lib/theme/chartTheme';
    import {isDarkTheme, onChartColorsChange, onThemeClassChange} from '$lib/theme/themeMode';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** OHLCV data aligned to dateAxis */
        data: LineDataPoint[];
        /** Whether dark mode is active (passed from parent to avoid flicker) */
        isDark?: boolean;
        /** Show volume bars in the lower grid (default: true) */
        showVolume?: boolean;
        /** CSS height for the price grid area */
        height?: string;
        /** Show grid split lines */
        showGridLines?: boolean;
        /** Signal overlays — same RenderedSignal used by LineChart */
        overlaySignals?: RenderedSignal[];
        /** Y-axis currency label */
        currency?: string;
        /** View mode — 'percentage' transforms OHLCV relative to first data point */
        viewMode?: 'absolute' | 'percentage';
        /** Measure mode: enables click-to-place measurement points */
        measureMode?: boolean;
        /** Called on click in measure mode (date, close value) */
        onMeasureClick?: (date: string, value: number) => void;
        /**
         * Called on mousemove in measure mode (date, close value). Answers `true` on a day the measure
         * refuses (its start: no measure of one day), and the chart shows the not-allowed cursor.
         */
        onMeasureHover?: (date: string, value: number) => boolean | void;
        /** Called on double-click on a data point (date, value) — for editor scroll */
        onDblClick?: (date: string, value: number) => void;
        /** Main series label for tooltip header (e.g. asset name) */
        mainSeriesLabel?: string;
        /** Main series icon URL (for tooltip rendering) */
        mainIconUrl?: string | null;
        /** Main series asset type (for tooltip icon fallback) */
        mainAssetType?: string | null;
        /** Display currency (when FX conversion active) */
        displayCurrency?: string;
        /** Display currency flag emoji */
        displayCurrencyFlag?: string;
        /** Main asset native currency code */
        mainCurrency?: string;
        /** Main asset native currency flag emoji */
        mainCurrencyFlag?: string;
        /** Y-axis mode: 'auto' (scale:true), 'include0', or 'custom' */
        yAxisMode?: 'auto' | 'include0' | 'custom';
        /** Y-axis minimum (when yAxisMode='custom') */
        yAxisMin?: number;
        /** Y-axis maximum (when yAxisMode='custom') */
        yAxisMax?: number;
        /** Stable semantic settings for active non-primary axes. */
        secondaryAxisScales?: Record<string, AxisScaleSettings>;
        /** Shared chart resolution decided by PriceChartFull */
        resolution?: ChartResolution;
    }

    let {
        data = [],
        isDark: isDarkProp,
        showVolume = true,
        height = '400px',
        showGridLines = true,
        overlaySignals = [],
        currency = '',
        resolution = 'daily',
        viewMode = 'absolute',
        measureMode = false,
        onMeasureClick,
        onMeasureHover,
        onDblClick,
        mainSeriesLabel,
        mainIconUrl,
        mainAssetType,
        displayCurrency: displayCurrencyProp,
        displayCurrencyFlag,
        mainCurrency: mainCurrencyProp,
        mainCurrencyFlag: mainCurrencyFlagProp,
        yAxisMode = 'auto',
        yAxisMin,
        yAxisMax,
        secondaryAxisScales = {},
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement;
    let chartInstance: echarts.ECharts | null = null;
    /**
     * The last resolved measure hover: `blocked` over a day `onMeasureHover` refuses, `free`
     * elsewhere, null out of measure mode. It picks the cursor, and the container publishes it.
     */
    let measureHover = $state<'blocked' | 'free' | null>(null);

    // Out of measure mode the container publishes no hover, and the next measure starts free.
    $effect(() => {
        if (!measureMode) measureHover = null;
    });
    let resizeObserver: ResizeObserver | null = null;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let chartOptionSet = false;
    let needsInitialLayoutStabilityPass = false;
    let lastRenderedResolution: ChartResolution | null = null;
    let lastRenderedDates: string[] = [];
    let responsiveXAxisCompact = false;
    /** The last zoom window, and the timer that, once the gesture settles, re-spaces the x labels on it (47-1) and re-aims the arrow markers (Y-8). Plain variables: the teardown reads them. */
    let lastZoomEvent: unknown = null;
    let zoomLabelTimer: ReturnType<typeof setTimeout> | null = null;

    /** How many of the drawn categories the last zoom left visible; undefined before any zoom. */
    function zoomedCategoryCount(): number | undefined {
        return visiblePointCountFromZoom(lastZoomEvent, lastRenderedDates.length) ?? undefined;
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
        if (!chartInstance || !chartContainer || lastRenderedDates.length === 0) return;
        const visibleCount = zoomedCategoryCount();
        if (visibleCount === undefined) return;
        const policy = buildResponsiveXAxisPolicy({
            width: chartContainer.clientWidth,
            values: lastRenderedDates,
            locale: uiLocale(),
            axisType: 'category',
            visibleCount,
        });
        responsiveXAxisCompact = policy.compact;
        chartInstance.setOption({xAxis: {axisLabel: categoryAxisLabelPatch(policy)}}, {lazyUpdate: true});
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        // Watch for dark-mode class changes on <html>, and for the Designer Lab's colour edits (C4)
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
            void overlaySignals;
            void showVolume;
            void showGridLines;
            void height;
            void viewMode;
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
        lastRenderedResolution = null;
        lastRenderedDates = [];
        zoomLabelTimer = clearTimer(zoomLabelTimer);
        lastZoomEvent = null;
        dataZoomTouchPanHandle?.dispose();
        dataZoomTouchPanHandle = null;
        if (chartContainer) {
            delete (chartContainer as unknown as Record<string, unknown>).__lfChart;
        }
        chartInstance?.dispose();
        chartInstance = null;
    }

    function buildTooltipHeader(date: string, bucketInfo?: {bucketStart: string; bucketEnd: string}): string {
        const heading = chartNeutrals(isDarkProp ?? isDarkTheme(), chartContainer).tooltip.candlestickBox.heading;
        if (resolution === 'daily') {
            return `<div style="font-size:12px;font-weight:600;margin-bottom:2px;color:${heading}">${formatDay(date)}</div>`;
        }

        // The point stands for its bucket up to its own day, the last one with data: the period still running ends there.
        const info = bucketSpanUpTo(date, bucketInfo ?? {bucketStart: date, bucketEnd: date});

        if (resolution === 'weekly') {
            return `<div style="font-size:12px;font-weight:600;margin-bottom:2px;color:${heading}">${$t('chart.tooltip.weekRange', {values: {start: formatDay(info.bucketStart), end: formatDay(info.bucketEnd)}})}</div>`;
        }

        return `<div style="font-size:12px;font-weight:600;margin-bottom:2px;color:${heading}">${$t('chart.tooltip.monthLabel', {values: {month: formatMonthLabel(info.bucketEnd)}})}</div><div style="font-size:11px;margin-bottom:3px;opacity:0.8">${$t('chart.tooltip.valueAt', {values: {date: formatDay(info.bucketEnd)}})}</div>`;
    }

    // =========================================================================
    // Chart Rendering
    // =========================================================================

    function renderChart() {
        if (!chartContainer || data.length === 0) return;

        if (!resizeObserver) {
            resizeObserver = new ResizeObserver(() => {
                if (chartOptionSet) {
                    try {
                        chartInstance?.resize();
                        if (chartInstance && lastRenderedDates.length > 0) {
                            const policy = buildResponsiveXAxisPolicy({
                                width: chartContainer.clientWidth,
                                values: lastRenderedDates,
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
                } else if (chartContainer && data.length > 0) {
                    renderChart();
                }
            });
            resizeObserver.observe(chartContainer);
        }

        const rect = chartContainer.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, CHART_INIT_THEME, {renderer: 'canvas'});
            (chartContainer as unknown as Record<string, unknown>).__lfChart = chartInstance;
            attachChartReady(chartInstance, chartContainer, 'candlestick');
            needsInitialLayoutStabilityPass = true;
            dataZoomTouchPanHandle = attachDataZoomTouchPan(chartInstance, chartContainer);
            // A zoom changes the pixel aspect: the x labels are re-spaced on the window, and the arrow markers re-aimed, once the
            // gesture settles, never on each tick (47-1, Y-8)
            chartInstance.on('dataZoom', (event: unknown) => {
                scheduleZoomedAxisLabels(event);
            });

            // Measure mode: click handler
            chartInstance.getZr().on('click', (params: any) => {
                if (!measureMode || !onMeasureClick || !chartInstance) return;
                const pointInPixel = [params.offsetX, params.offsetY];
                if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                    const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                    if (pointInGrid) {
                        const dateIdx = Math.round(pointInGrid[0]);
                        if (dateIdx >= 0 && dateIdx < data.length) {
                            const d = data[dateIdx];
                            const closeVal = d.close ?? d.value;
                            onMeasureClick(d.date, closeVal);
                        }
                    }
                }
            });

            // Measure mode: hover handler
            let hoverRaf = false;
            chartInstance.getZr().on('mousemove', (params: any) => {
                if (!measureMode || !onMeasureHover || !chartInstance) return;
                // zrender puts its own default cursor back on every move, before its listeners: in
                // measure mode the chart sets its own at once — not-allowed while the last hover was refused.
                chartInstance.getZr().setCursorStyle(measureHover === 'blocked' ? 'not-allowed' : 'crosshair');
                if (hoverRaf) return;
                hoverRaf = true;
                requestAnimationFrame(() => {
                    hoverRaf = false;
                    if (!chartInstance || !measureMode || !onMeasureHover) return;
                    let blocked = false;
                    const pointInPixel = [params.offsetX, params.offsetY];
                    if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                        const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                        if (pointInGrid) {
                            const dateIdx = Math.round(pointInGrid[0]);
                            if (dateIdx >= 0 && dateIdx < data.length) {
                                const d = data[dateIdx];
                                const closeVal = d.close ?? d.value;
                                blocked = onMeasureHover(d.date, closeVal) === true;
                            }
                        }
                    }
                    measureHover = blocked ? 'blocked' : 'free';
                    chartInstance.getZr().setCursorStyle(blocked ? 'not-allowed' : 'crosshair');
                });
            });

            // Double-click handler — scrolls editor to clicked date (works on both price and volume grids)
            chartInstance.getZr().on('dblclick', (params: any) => {
                if (!onDblClick || !chartInstance) return;
                const pointInPixel = [params.offsetX, params.offsetY];
                // Check price grid first, then volume grid
                for (const gi of [0, 1]) {
                    if (chartInstance.containPixel({gridIndex: gi}, pointInPixel)) {
                        const pointInGrid = chartInstance.convertFromPixel({gridIndex: gi}, pointInPixel);
                        if (pointInGrid) {
                            const dateIdx = Math.round(pointInGrid[0]);
                            if (dateIdx >= 0 && dateIdx < data.length) {
                                const d = data[dateIdx];
                                onDblClick(d.date, d.close ?? d.value);
                            }
                        }
                        break;
                    }
                }
            });
        }

        const dark = isDarkProp ?? isDarkTheme();
        const neutrals = chartNeutrals(dark, chartContainer);

        const greenColor = dark ? COLORS.greenDark : COLORS.greenLight;
        const redColor = dark ? COLORS.redDark : COLORS.redLight;
        const axisColor = neutrals.priceAxis.line;
        const labelColor = neutrals.priceAxis.label;

        const dates = data.map((d) => d.date);
        lastRenderedDates = dates;
        const bucketInfoByDate = new Map(dates.map((date, index) => [date, getBucketInfo(data[index], resolution)]));

        // ── Percentage mode: transform prices relative to first data point ──
        const isPercentage = viewMode === 'percentage';
        const baseValue = computePercentageBase(data, isPercentage);

        // ── Candlestick series data: ECharts format = [open, close, low, high] ──
        // DB values have priority; synthesize only fields that are null/undefined.
        // Synthesis: open = prev close, high = max(open, close), low = min(open, close)
        const candleData: (number[] | null)[] = buildCandleSeriesData(data, isPercentage, baseValue);

        // ── Volume series data ──
        const hasAnyVolume = hasRenderableVolume(data);
        const actualShowVolume = showVolume && hasAnyVolume;

        const volumeData: any[] = data.map((d) => ({
            value: d.volume ?? 0,
            itemStyle: {
                color: isBullishBar(d) ? toRgba(greenColor, 0.55) : toRgba(redColor, 0.55),
            },
        }));

        // ── Overlay signals ──
        const downsampledOverlaySignals = resolution === 'daily' ? overlaySignals : overlaySignals.map((signal) => downsampleRenderedSignal(signal, resolution, data)).filter((signal) => signal.data.length > 0);
        const resolvedOverlaySignals = assignOverlaySignalAxes(downsampledOverlaySignals);
        const {axes: secondaryAxes, extraAxesCount, nextAxisIndex: volumeYAxisIndex} = buildSecondaryYAxes(resolvedOverlaySignals, dark, 0, true, secondaryAxisScales);

        const series: any[] = [];

        // Candlestick series
        series.push({
            type: 'candlestick',
            name: currency || 'Price',
            data: candleData,
            xAxisIndex: 0,
            yAxisIndex: 0,
            barWidth: '80%',
            itemStyle: {
                color: greenColor,
                color0: redColor,
                borderColor: greenColor,
                borderColor0: redColor,
            },
        });

        // Volume bars (on separate grid)
        if (actualShowVolume) {
            series.push({
                type: 'bar',
                name: 'Volume',
                data: volumeData,
                xAxisIndex: 1,
                yAxisIndex: volumeYAxisIndex,
                barMaxWidth: 12,
            });
        }

        // Overlay signals — uses shared helper
        series.push(...buildOverlaySignalSeries(resolvedOverlaySignals, dates, dark, 0));

        // ── Grid configuration ──
        // Price grid: leaves room for volume below (if active) and extra yAxes to the right
        const rightMargin = computeRightMargin(extraAxesCount);
        const priceGridBottom = actualShowVolume ? '27%' : '10%';

        const grids: any[] = [
            {
                top: 20,
                right: rightMargin,
                bottom: priceGridBottom,
                left: 10,
                containLabel: true,
            },
        ];

        if (actualShowVolume) {
            grids.push({
                top: '76%',
                right: rightMargin,
                bottom: 20,
                left: 10,
                containLabel: true,
            });
        }

        let savedZoom: {start: number; end: number} | null = null;
        if (chartOptionSet && chartInstance) {
            const currentOption = chartInstance.getOption() as {
                dataZoom?: Array<{start?: unknown; end?: unknown}>;
            };
            const currentZoom = currentOption.dataZoom?.[0];
            if (typeof currentZoom?.start === 'number' && typeof currentZoom.end === 'number') {
                savedZoom = {
                    start: currentZoom.start,
                    end: currentZoom.end,
                };
            }
        }

        // ── X-axes ──
        // The zoom about to be restored is read first, so the labels are spaced on that window (47-1).
        const restoredZoomCount = savedZoom ? visiblePointCountFromZoom(savedZoom, dates.length) : null;
        const xAxisPolicy = buildResponsiveXAxisPolicy({
            width: rect.width,
            values: dates,
            locale: uiLocale(),
            axisType: 'category',
            visibleCount: restoredZoomCount ?? undefined,
        });
        responsiveXAxisCompact = xAxisPolicy.compact;
        const xAxisBase = {
            type: 'category' as const,
            data: dates,
            boundaryGap: true,
            axisLine: {lineStyle: {color: axisColor}},
            axisLabel: {
                color: labelColor,
                fontSize: 14,
                formatter: xAxisPolicy.formatter,
                ...(xAxisPolicy.axisLabel ?? {}),
            },
            splitLine: {show: false},
        };

        const xAxes: any[] = [{...xAxisBase, gridIndex: 0}];

        if (actualShowVolume) {
            xAxes.push({
                ...xAxisBase,
                gridIndex: 1,
                show: false, // hide x-axis labels on volume grid
            });
        }

        // ── Y-axes ──
        const colors = getChartColors(dark, chartContainer);
        const priceYAxis = buildPriceYAxis({mode: yAxisMode, min: yAxisMin, max: yAxisMax, isPercentage}, colors, {gridIndex: 0, showGridLines});
        const yAxes: any[] = [priceYAxis, ...secondaryAxes];

        if (actualShowVolume) {
            // yAxis[3] — volume (grid[1], hidden)
            yAxes.push({
                type: 'value',
                gridIndex: 1,
                show: false,
                scale: false,
                splitLine: {show: false},
            });
        }

        // ── Tooltip ──
        const fmtPrice = (v: number) => formatCandlePrice(v, isPercentage);

        // Build header label (asset name + icon + currency)
        const tooltipHeaderHtml = (() => {
            const label = truncateName(mainSeriesLabel || currency || 'Price');
            let suffix = '';
            if (displayCurrencyProp && mainCurrencyProp && displayCurrencyProp !== mainCurrencyProp) {
                suffix = ` <span style="font-size:10px">(${escapeHtml(displayCurrencyFlag || '')} ${escapeHtml(displayCurrencyProp)})</span>`;
            } else if (mainCurrencyProp) {
                suffix = ` <span style="font-size:10px">(${escapeHtml(mainCurrencyFlagProp || '')} ${escapeHtml(mainCurrencyProp)})</span>`;
            }
            return signalLabelToHtml({label, iconUrl: mainIconUrl, assetType: mainAssetType, isCrown: true}) + suffix;
        })();

        const tooltipFormatter = (params: any) => {
            const arr = Array.isArray(params) ? params : [params];
            if (!arr.length) return '';

            const date = String(arr[0].axisValue ?? arr[0].name ?? '');
            let html = buildTooltipHeader(date, bucketInfoByDate.get(date));
            html += `<div style="font-size:11px;margin-bottom:3px">${tooltipHeaderHtml}</div>`;

            const staleLookup = new Map<string, number>();
            const fxStaleLookup = new Map<string, number>();
            for (const point of data) {
                if (point.staleDays && point.staleDays > 0) staleLookup.set(point.date, point.staleDays);
                if (point.fxStaleDays && point.fxStaleDays > 0) fxStaleLookup.set(point.date, point.fxStaleDays);
            }

            for (const p of arr) {
                if (p.seriesName === 'Volume') {
                    const vol: number = p.value ?? 0;
                    const volFmt = formatVolume(vol);
                    html += `<div style="color:${neutrals.tooltip.candlestickBox.muted};font-size:11px;margin-top:3px">Vol: ${volFmt}</div>`;
                    continue;
                }

                if (p.seriesType === 'candlestick' && Array.isArray(p.value)) {
                    // ECharts prepends the category-axis ordinal index as value[0] for whisker/candlestick
                    // series when the x-axis is a category axis with no explicit x-encode (see echarts
                    // whiskerBoxCommon.js addOrdinal/unshift) — value is [index, open, close, low, high]
                    // (5 items), not [open, close, low, high] (4 items). Always take the last 4 so this
                    // works regardless of whether the index got prepended.
                    const {open, close, low, high, bullish} = parseCandleTooltipValue(p.value as number[]);
                    const clr = bullish ? greenColor : redColor;
                    const dimClr = neutrals.tooltip.candlestickBox.muted;
                    html += `<div style="display:grid;grid-template-columns:auto 1fr;gap:0 6px;font-size:11px;margin-top:2px">`;
                    html += `<span style="color:${dimClr}">O</span><span style="color:${clr}">${fmtPrice(open)}</span>`;
                    html += `<span style="color:${dimClr}">H</span><span style="color:${clr}">${fmtPrice(high)}</span>`;
                    html += `<span style="color:${dimClr}">L</span><span style="color:${clr}">${fmtPrice(low)}</span>`;
                    html += `<span style="color:${dimClr}">C</span><span style="color:${clr};font-weight:600">${fmtPrice(close)}</span>`;
                    html += `</div>`;
                    continue;
                }

                // Overlay signal line
                if (p.value !== null && p.value !== undefined) {
                    html += `<div style="font-size:11px"><span style="color:${p.color ?? CHART_TOOLTIP_COLORS.candlestickBox.seriesFallback}">${escapeHtml(truncateName(String(p.seriesName ?? '')))}: ${typeof p.value === 'number' ? formatFixed(p.value, 4) : p.value}</span></div>`;
                }
            }

            const staleDays = staleLookup.get(date);
            if (staleDays !== undefined) {
                html += `<div style="color:${neutrals.tooltip.staleWarning};font-size:11px;margin-top:3px">⚠ ${$t('chart.tooltip.stale', {values: {days: staleDays}})}</div>`;
                const fxStaleDays = fxStaleLookup.get(date);
                if (fxStaleDays !== undefined && fxStaleDays > 0) {
                    html += `<div style="color:${neutrals.tooltip.staleWarning};font-size:11px">⚠ ${$t('chart.tooltip.fxStale', {values: {days: fxStaleDays}})}</div>`;
                }
            }

            return html;
        };

        const option: echarts.EChartsOption = {
            animation: false,
            grid: grids,
            dataZoom: buildDataZoom(actualShowVolume ? [0, 1] : [0]),
            xAxis: xAxes,
            yAxis: yAxes,
            tooltip: {
                trigger: 'axis' as const,
                axisPointer: {type: 'cross' as const, crossStyle: {color: neutrals.tooltip.candlestickBox.crosshair}},
                appendToBody: true,
                confine: true,
                position: tooltipPositionSide,
                backgroundColor: neutrals.tooltip.box.background,
                borderColor: neutrals.tooltip.candlestickBox.border,
                textStyle: {color: neutrals.tooltip.candlestickBox.text, fontSize: 12},
                formatter: tooltipFormatter,
            },
            series,
        };

        // Resolution switch: same ECharts tooltip-crash risk as PriceChartFull's line view
        // (full rebuild via setOption(option,true) while an axis-trigger tooltip + mousewheel
        // dataZoom are active) — hide the tooltip first when resolution actually changed.
        if (lastRenderedResolution !== null && lastRenderedResolution !== resolution) {
            chartInstance.dispatchAction({type: 'hideTip'});
        }

        chartInstance.setOption(option, true);
        noteArrowMarkers(chartInstance, option);
        chartOptionSet = true;
        lastRenderedResolution = resolution;
        if (savedZoom) {
            chartInstance.dispatchAction({
                type: 'dataZoom',
                start: savedZoom.start,
                end: savedZoom.end,
            });
        }
        updateArrowRotations(chartInstance);
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer, updateArrowRotations);
        }
    }
</script>

<div bind:this={chartContainer} class="w-full" class:cursor-crosshair={measureMode} data-testid="candlestick-chart" data-measure-hover={measureHover ?? undefined} style="height: {height};"></div>
