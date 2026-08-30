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
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {attachChartReady} from '$lib/utils/chartReady';
    import {_ as t} from '$lib/i18n';
    import type {RenderedSignal} from '$lib/charts/signals';
    import type {LineDataPoint} from './LineChart.svelte';
    import {COLORS, hexToRgba, updateArrowRotations} from './lineChartHelpers';
    import {signalLabelToHtml} from '$lib/charts/signalLabel';
    import {assignOverlaySignalAxes, buildPriceYAxis, buildSecondaryYAxes, buildOverlaySignalSeries, buildDataZoom, computeRightMargin, getChartColors} from './chartCoreHelpers';
    import {scheduleFirstRenderStabilityFix, tooltipPositionSide} from './echartsTooltipHelpers';
    import {attachDataZoomTouchPan, type DataZoomTouchPanHandle} from './echartsDataZoomTouchPan';
    import {downsampleRenderedSignal, type ChartResolution} from './timeSeriesAggregation';
    import {formatMonthLabel, getBucketInfo} from './priceChartHelpers';
    import {buildCandleSeriesData, computePercentageBase, formatCandlePrice, formatVolume, hasRenderableVolume, isBullishBar, parseCandleTooltipValue} from './candlestickChartHelpers';
    import {truncateName} from '$lib/utils/text';

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
        /** Called on mousemove in measure mode (date, close value) */
        onMeasureHover?: (date: string, value: number) => void;
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
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement;
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let dataZoomTouchPanHandle: DataZoomTouchPanHandle | null = null;
    let chartOptionSet = false;
    let needsInitialLayoutStabilityPass = false;
    let lastRenderedResolution: ChartResolution | null = null;

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        // Watch for dark-mode class changes on <html>
        const observer = new MutationObserver(() => {
            if (chartContainer && data.length > 0) renderChart();
        });
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['class'],
        });
        return () => {
            observer.disconnect();
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
            tick().then(renderChart);
        }
    });

    function cleanup() {
        resizeObserver?.disconnect();
        resizeObserver = null;
        chartOptionSet = false;
        lastRenderedResolution = null;
        dataZoomTouchPanHandle?.dispose();
        dataZoomTouchPanHandle = null;
        chartInstance?.dispose();
        chartInstance = null;
    }

    function buildTooltipHeader(date: string, bucketInfo?: {bucketStart: string; bucketEnd: string}): string {
        if (resolution === 'daily') {
            return `<div style="font-size:12px;font-weight:600;margin-bottom:2px;color:${(isDarkProp ?? document.documentElement.classList.contains('dark')) ? '#e2e8f0' : '#1f2937'}">${date}</div>`;
        }

        const dark = isDarkProp ?? document.documentElement.classList.contains('dark');
        const info = bucketInfo ?? {bucketStart: date, bucketEnd: date};

        if (resolution === 'weekly') {
            return `<div style="font-size:12px;font-weight:600;margin-bottom:2px;color:${dark ? '#e2e8f0' : '#1f2937'}">${$t('chart.tooltip.weekRange', {values: {start: info.bucketStart, end: info.bucketEnd}})}</div>`;
        }

        return `<div style="font-size:12px;font-weight:600;margin-bottom:2px;color:${dark ? '#e2e8f0' : '#1f2937'}">${$t('chart.tooltip.monthLabel', {values: {month: formatMonthLabel(info.bucketEnd)}})}</div><div style="font-size:11px;margin-bottom:3px;opacity:0.8">${$t('chart.tooltip.valueAt', {values: {date: info.bucketEnd}})}</div>`;
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
                        if (chartInstance) updateArrowRotations(chartInstance);
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
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});
            attachChartReady(chartInstance, chartContainer, 'candlestick');
            needsInitialLayoutStabilityPass = true;
            dataZoomTouchPanHandle = attachDataZoomTouchPan(chartInstance, chartContainer);
            chartInstance.on('dataZoom', () => {
                if (chartInstance) updateArrowRotations(chartInstance);
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
                if (!measureMode || !onMeasureHover || !chartInstance || hoverRaf) return;
                hoverRaf = true;
                requestAnimationFrame(() => {
                    hoverRaf = false;
                    if (!chartInstance) return;
                    const pointInPixel = [params.offsetX, params.offsetY];
                    if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                        const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                        if (pointInGrid) {
                            const dateIdx = Math.round(pointInGrid[0]);
                            if (dateIdx >= 0 && dateIdx < data.length) {
                                const d = data[dateIdx];
                                const closeVal = d.close ?? d.value;
                                onMeasureHover!(d.date, closeVal);
                            }
                        }
                    }
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

        const dark = isDarkProp ?? document.documentElement.classList.contains('dark');

        const greenColor = dark ? COLORS.greenDark : COLORS.greenLight;
        const redColor = dark ? COLORS.redDark : COLORS.redLight;
        const axisColor = dark ? '#475569' : '#d1d5db';
        const labelColor = dark ? '#94a3b8' : '#6b7280';

        const dates = data.map((d) => d.date);
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
                color: isBullishBar(d) ? hexToRgba(greenColor, 0.55) : hexToRgba(redColor, 0.55),
            },
        }));

        // ── Overlay signals ──
        const downsampledOverlaySignals = resolution === 'daily' ? overlaySignals : overlaySignals.map((signal) => downsampleRenderedSignal(signal, resolution, data)).filter((signal) => signal.data.length > 0);
        const resolvedOverlaySignals = assignOverlaySignalAxes(downsampledOverlaySignals);
        const {axes: secondaryAxes, extraAxesCount, nextAxisIndex: volumeYAxisIndex} = buildSecondaryYAxes(resolvedOverlaySignals, dark, 0);

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

        // ── X-axes ──
        const xAxisBase = {
            type: 'category' as const,
            data: dates,
            boundaryGap: true,
            axisLine: {lineStyle: {color: axisColor}},
            axisLabel: {color: labelColor, fontSize: 14},
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
        const colors = getChartColors(dark);
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
                suffix = ` <span style="font-size:10px">(${displayCurrencyFlag || ''} ${displayCurrencyProp})</span>`;
            } else if (mainCurrencyProp) {
                suffix = ` <span style="font-size:10px">(${mainCurrencyFlagProp || ''} ${mainCurrencyProp})</span>`;
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
                    html += `<div style="color:${dark ? '#94a3b8' : '#6b7280'};font-size:11px;margin-top:3px">Vol: ${volFmt}</div>`;
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
                    const dimClr = dark ? '#94a3b8' : '#6b7280';
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
                    html += `<div style="font-size:11px"><span style="color:${p.color ?? '#888'}">${truncateName(String(p.seriesName ?? ''))}: ${typeof p.value === 'number' ? p.value.toFixed(4) : p.value}</span></div>`;
                }
            }

            const staleDays = staleLookup.get(date);
            if (staleDays !== undefined) {
                html += `<div style="color:#f59e0b;font-size:11px;margin-top:3px">⚠ ${$t('chart.tooltip.stale', {values: {days: staleDays}})}</div>`;
                const fxStaleDays = fxStaleLookup.get(date);
                if (fxStaleDays !== undefined && fxStaleDays > 0) {
                    html += `<div style="color:#f59e0b;font-size:11px">⚠ ${$t('chart.tooltip.fxStale', {values: {days: fxStaleDays}})}</div>`;
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
                axisPointer: {type: 'cross' as const, crossStyle: {color: dark ? '#475569' : '#9ca3af'}},
                appendToBody: true,
                confine: true,
                position: tooltipPositionSide,
                backgroundColor: dark ? '#1e293b' : '#ffffff',
                borderColor: dark ? '#334155' : '#e5e7eb',
                textStyle: {color: dark ? '#e2e8f0' : '#111827', fontSize: 12},
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
        chartOptionSet = true;
        lastRenderedResolution = resolution;
        updateArrowRotations(chartInstance);
        if (needsInitialLayoutStabilityPass) {
            needsInitialLayoutStabilityPass = false;
            scheduleFirstRenderStabilityFix(chartInstance, chartContainer, updateArrowRotations);
        }
    }
</script>

<div bind:this={chartContainer} class="w-full" class:cursor-crosshair={measureMode} data-testid="candlestick-chart" style="height: {height};"></div>
