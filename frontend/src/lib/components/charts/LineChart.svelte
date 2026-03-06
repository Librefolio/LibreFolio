<!--
  LineChart — ECharts line chart with stale-data gradient, segment coloring, and zoom sync.

  Features:
  - Line series with configurable area fill
  - Per-point opacity based on staleDays (stale gradient)
  - Segment-based color by baseline: green above baseline, red below (both % and abs modes)
  - Y-axis always visible with values (also mini-axis mode for compact cards)
  - Tooltip with date, value, stale warning, and % note
  - Dark mode support with MutationObserver
  - ResizeObserver for responsive sizing
  - Mouse wheel zoom + drag-to-pan via ECharts inside dataZoom
  - Bidirectional zoom sync: emits onZoomChange when user zooms inside chart
  - Click event emission for parent components
  - onChartReady callback for coordinate mapping (used by MeasureOverlay)

  Used by: PriceChartCompact, PriceChartFull (line mode)
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import type {RenderedSignal} from '$lib/charts/signals';

    // =========================================================================
    // Types
    // =========================================================================

    export interface LineDataPoint {
        date: string;
        value: number;
        staleDays?: number;
    }

    export interface ChartApi {
        getGridBounds: () => {left: number; right: number; top: number; bottom: number; width: number; height: number};
        dataToPixel: (dataIndex: number, value: number) => {x: number; y: number} | null;
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
        /** External zoom range [startPercent, endPercent] (0-100) */
        zoomRange?: [number, number];
        /** Called when user zooms inside the chart (for DataZoomBar sync) */
        onZoomChange?: (start: number, end: number) => void;
        /** View mode (for tooltip formatting and segment colors) */
        viewMode?: 'absolute' | 'percentage';
        /** Called when chart instance is ready (for coordinate mapping) */
        onChartReady?: (api: ChartApi) => void;
        /** Overlay signals to render as additional line series */
        overlaySignals?: RenderedSignal[];
    }

    let {
        data = [],
        currency = '',
        areaFill = true,
        showGradient = true,
        colorByBaseline = true,
        showGridLines = true,
        height = '300px',
        compact = false,
        showMiniAxis = false,
        lineColor,
        darkLineColor,
        pendingColor = '#f59e0b',
        pendingData = [],
        onPointClick,
        zoomRange,
        onZoomChange,
        viewMode = 'absolute',
        onChartReady,
        overlaySignals = [],
    }: Props = $props();

    // Default colors
    const DEFAULT_LINE_LIGHT = '#1a4031';
    const DEFAULT_LINE_DARK = '#4ade80';
    const GREEN_LIGHT = '#16a34a';
    const GREEN_DARK = '#4ade80';
    const RED_LIGHT = '#ef4444';
    const RED_DARK = '#f87171';

    // =========================================================================
    // State
    // =========================================================================

    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let suppressZoomEvent = false;

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
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
            // Touch overlaySignals to register dependency
            void overlaySignals;
            tick().then(renderChart);
        }
    });

    $effect(() => {
        if (chartInstance && zoomRange) {
            suppressZoomEvent = true;
            chartInstance.dispatchAction({
                type: 'dataZoom',
                start: zoomRange[0],
                end: zoomRange[1],
            });
            setTimeout(() => { suppressZoomEvent = false; }, 50);
        }
    });

    function cleanup() {
        resizeObserver?.disconnect();
        resizeObserver = null;
        chartInstance?.dispose();
        chartInstance = null;
    }

    // =========================================================================
    // Helpers
    // =========================================================================

    function getOpacity(staleDays?: number): number {
        if (!staleDays || staleDays === 0) return 1.0;
        return Math.max(0.3, 1.0 - staleDays * 0.15);
    }

    function hexToRgba(hex: string, alpha: number): string {
        const h = hex.replace('#', '');
        const r = parseInt(h.substring(0, 2), 16);
        const g = parseInt(h.substring(2, 4), 16);
        const b = parseInt(h.substring(4, 6), 16);
        return `rgba(${r},${g},${b},${alpha})`;
    }

    // =========================================================================
    // ChartApi for external coordinate mapping
    // =========================================================================

    function emitChartReady() {
        if (!chartInstance || !onChartReady) return;
        onChartReady({
            getGridBounds: () => {
                try {
                    const gridModel = (chartInstance as any).getModel().getComponent('grid', 0);
                    if (gridModel && gridModel.coordinateSystem) {
                        const rect = gridModel.coordinateSystem.getRect();
                        return {
                            left: rect.x,
                            right: rect.x + rect.width,
                            top: rect.y,
                            bottom: rect.y + rect.height,
                            width: rect.width,
                            height: rect.height,
                        };
                    }
                } catch (_) { /* fallback below */ }
                // Fallback estimate
                return {left: 60, right: 15, top: 35, bottom: 35, width: 0, height: 0};
            },
            dataToPixel: (dataIndex: number, value: number) => {
                if (!chartInstance) return null;
                try {
                    const pixel = (chartInstance as any).convertToPixel('grid', [dataIndex, value]);
                    if (pixel) return {x: pixel[0], y: pixel[1]};
                } catch (_) { /* return null */ }
                return null;
            },
        });
    }

    // =========================================================================
    // Chart Rendering
    // =========================================================================

    function renderChart() {
        if (!chartContainer || data.length === 0) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});

            if (onPointClick) {
                chartInstance.on('click', 'series.line', (params: any) => {
                    if (params.dataIndex !== undefined && data[params.dataIndex]) {
                        const point = data[params.dataIndex];
                        onPointClick!(point.date, point.value);
                    }
                });
            }

            // Bidirectional zoom: emit event for DataZoomBar sync
            chartInstance.on('datazoom', (params: any) => {
                if (suppressZoomEvent) return;
                const batch = params.batch;
                if (batch && batch.length > 0) {
                    const {start, end} = batch[0];
                    if (typeof start === 'number' && typeof end === 'number') {
                        onZoomChange?.(start, end);
                    }
                }
            });

            if (!resizeObserver) {
                resizeObserver = new ResizeObserver(() => chartInstance?.resize());
                resizeObserver.observe(chartContainer);
            }
        }

        const isDark = document.documentElement.classList.contains('dark');
        const isPercentage = viewMode === 'percentage';

        const baseColor = isDark
            ? (darkLineColor || DEFAULT_LINE_DARK)
            : (lineColor || DEFAULT_LINE_LIGHT);

        const greenColor = isDark ? GREEN_DARK : GREEN_LIGHT;
        const redColor = isDark ? RED_DARK : RED_LIGHT;

        // Build series data
        const dates = data.map(d => d.date);

        // Determine if we need visualMap (baseline coloring)
        const useBaselineColoring = colorByBaseline && !compact;
        const baselineValue = isPercentage ? 0 : (data[0]?.value ?? 0);
        // When baseline coloring is active, data MUST be tuples [index, value] for visualMap dimension:1 to work
        const useTupleFormat = useBaselineColoring;

        // Build per-point data with optional stale gradient opacity
        const hasStaleData = showGradient && !useBaselineColoring && data.some(d => (d.staleDays ?? 0) > 0);

        const seriesData: any[] = data.map((d, i) => {
            const val = useTupleFormat ? [i, d.value] : d.value;
            const opacity = getOpacity(d.staleDays);

            // When stale gradient is active (and baseline coloring is NOT), apply per-point opacity
            if (hasStaleData && opacity < 1.0) {
                return {
                    value: val,
                    itemStyle: {
                        color: hexToRgba(baseColor, opacity),
                        borderColor: hexToRgba(baseColor, opacity),
                    },
                    lineStyle: {
                        color: hexToRgba(baseColor, opacity),
                    },
                };
            }
            return val;
        });

        // Main line series
        const mainSeries: any = {
            type: 'line',
            name: currency || 'Value',
            data: seriesData,
            smooth: !!compact,
            symbol: compact && !showMiniAxis ? 'none' : (compact ? 'none' : 'circle'),
            symbolSize: compact ? 0 : 4,
            showSymbol: !compact,
            lineStyle: {
                width: compact ? 1.5 : 2,
            },
            itemStyle: {},
            emphasis: {
                focus: compact ? 'none' : 'series',
            },
        };

        // Set line/item color when NOT using baseline coloring
        if (!useBaselineColoring) {
            mainSeries.lineStyle.color = baseColor;
            mainSeries.itemStyle.color = baseColor;
        }

        // Area fill
        if (areaFill) {
            if (useBaselineColoring) {
                // Area colored by visualMap (green/red segments)
                mainSeries.areaStyle = {
                    opacity: isDark ? 0.25 : 0.15,
                };
            } else {
                // Fixed color gradient area
                const areaTopColor = hexToRgba(baseColor, isDark ? 0.35 : 0.2);
                const areaBottomColor = hexToRgba(baseColor, isDark ? 0.05 : 0.02);
                mainSeries.areaStyle = {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {offset: 0, color: areaTopColor},
                        {offset: 1, color: areaBottomColor},
                    ]),
                };
            }
        }

        const series: any[] = [mainSeries];

        // Pending edits overlay
        if (pendingData && pendingData.length > 0) {
            series.push({
                type: 'scatter',
                name: 'Pending',
                data: pendingData.map(d => {
                    const idx = dates.indexOf(d.date);
                    return idx >= 0 ? [idx, d.value] : null;
                }).filter(Boolean),
                symbol: 'diamond',
                symbolSize: 10,
                itemStyle: {
                    color: pendingColor,
                    borderColor: isDark ? '#1e293b' : '#ffffff',
                    borderWidth: 2,
                },
                z: 10,
            });
        }

        // Overlay signals — rendered as additional line series (generic: chart doesn't
        // know or care about signal types, it just renders whatever it receives)
        if (overlaySignals && overlaySignals.length > 0) {
            for (const signal of overlaySignals) {
                if (!signal.data.length) continue;

                // Build date→value lookup, then align to main chart's date axis
                const signalLookup = new Map(signal.data.map(d => [d.date, d.value]));
                const signalSeriesData: any[] = dates.map((date, i) => {
                    const val = signalLookup.get(date);
                    if (val === undefined) return useTupleFormat ? [i, null] : null;
                    return useTupleFormat ? [i, val] : val;
                });

                const overlaySeries: any = {
                    type: 'line',
                    name: signal.label,
                    data: signalSeriesData,
                    connectNulls: true,
                    smooth: false,
                    symbol: 'none',
                    lineStyle: {
                        color: signal.color,
                        width: signal.lineWidth,
                        type: signal.lineType,
                    },
                    itemStyle: {
                        color: signal.color,
                    },
                    emphasis: {
                        focus: 'none',
                    },
                    z: 1, // below main series
                };

                // Endpoint markers at start/end of signal data
                if (signal.markerStart || signal.markerEnd) {
                    const markData: any[] = [];
                    // Find first non-null index for markerStart
                    if (signal.markerStart) {
                        for (let i = 0; i < signalSeriesData.length; i++) {
                            const v = useTupleFormat ? signalSeriesData[i]?.[1] : signalSeriesData[i];
                            if (v !== null && v !== undefined) {
                                markData.push({
                                    coord: [i, v],
                                    symbol: signal.markerStart,
                                    symbolSize: 8,
                                    symbolRotate: signal.markerStart === 'arrow' ? 180 : 0,
                                    itemStyle: {color: signal.color},
                                });
                                break;
                            }
                        }
                    }
                    // Find last non-null index for markerEnd
                    if (signal.markerEnd) {
                        for (let i = signalSeriesData.length - 1; i >= 0; i--) {
                            const v = useTupleFormat ? signalSeriesData[i]?.[1] : signalSeriesData[i];
                            if (v !== null && v !== undefined) {
                                markData.push({
                                    coord: [i, v],
                                    symbol: signal.markerEnd,
                                    symbolSize: 8,
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
                        };
                    }
                }

                series.push(overlaySeries);
            }
        }

        // Mark line at baseline
        if (useBaselineColoring) {
            mainSeries.markLine = {
                silent: true,
                symbol: 'none',
                lineStyle: {
                    color: isDark ? '#64748b' : '#9ca3af',
                    type: 'dashed',
                    width: 1,
                },
                data: [{yAxis: baselineValue}],
                label: {show: false},
            };
        }

        // Grid configuration
        const showYAxis = !compact || showMiniAxis;
        const gridConfig = compact
            ? {
                top: 5,
                right: showMiniAxis ? 45 : 5,
                bottom: 5,
                left: 5,
                containLabel: false,
            }
            : {
                top: 35,
                right: 15,
                bottom: 35,
                left: 15,
                containLabel: true,
            };

        const option: echarts.EChartsOption = {
            animation: !compact,
            grid: gridConfig,
            dataZoom: compact ? [] : [
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
                axisLine: {lineStyle: {color: isDark ? '#475569' : '#d1d5db'}},
                axisLabel: {color: isDark ? '#94a3b8' : '#6b7280', fontSize: 11},
                splitLine: {show: false},
            },
            yAxis: {
                type: 'value',
                show: showYAxis,
                position: compact && showMiniAxis ? 'right' : 'left',
                axisLine: {show: !compact, lineStyle: {color: isDark ? '#475569' : '#d1d5db'}},
                axisTick: {show: !compact},
                splitNumber: compact && showMiniAxis ? 2 : undefined,
                axisLabel: {
                    show: showYAxis,
                    color: isDark ? '#94a3b8' : '#6b7280',
                    fontSize: compact && showMiniAxis ? 9 : 11,
                    formatter: isPercentage
                        ? (v: number) => `${v.toFixed(1)}%`
                        : (v: number) => {
                            if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}k`;
                            if (Math.abs(v) >= 1) return v.toFixed(2);
                            return v.toFixed(4).replace(/\.?0+$/, '');
                        },
                },
                splitLine: {
                    show: showGridLines && showYAxis,
                    lineStyle: {
                        color: isDark ? '#334155' : '#e5e7eb',
                        type: 'dashed',
                        opacity: compact && showMiniAxis ? 0.5 : 1,
                    },
                },
                scale: true,
            },
            tooltip: compact ? undefined : {
                trigger: 'axis',
                backgroundColor: isDark ? '#1e293b' : '#ffffff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    if (!items.length) return '';
                    const date = items[0].axisValue || items[0].name;
                    let html = `<strong>${date}</strong>`;

                    for (const p of items) {
                        // Skip pending scatter series
                        if (p.seriesName === 'Pending') continue;
                        // Extract value (may be tuple [index, value] or plain number)
                        const rawVal = p.value;
                        const value = Array.isArray(rawVal) ? rawVal[1]
                            : (typeof rawVal === 'object' && rawVal?.value !== undefined
                                ? (Array.isArray(rawVal.value) ? rawVal.value[1] : rawVal.value)
                                : rawVal);
                        if (value === null || value === undefined) continue;

                        const suffix = isPercentage ? '%' : '';
                        const colorDot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px;"></span>`;
                        html += `<br/>${colorDot}${p.seriesName}: ${Number(value).toFixed(4)}${suffix}`;
                    }

                    // Stale warning for main series
                    const dataPoint = data.find(d => d.date === date);
                    if (dataPoint?.staleDays && dataPoint.staleDays > 0) {
                        html += `<br/><span style="color:#f59e0b;font-size:11px">⚠ Stale: ${dataPoint.staleDays} day(s) old</span>`;
                    }
                    if (isPercentage) {
                        html += `<br/><span style="color:#94a3b8;font-size:10px">% relative to range start date</span>`;
                    }
                    return html;
                },
            },
            series,
        };

        // Visual map for baseline coloring: piecewise segment coloring by y-value
        if (useBaselineColoring) {
            (option as any).visualMap = {
                show: false,
                seriesIndex: 0,
                type: 'piecewise',
                dimension: 1,  // y-axis value — works because data is [index, value] tuples
                pieces: [
                    {lt: baselineValue, color: redColor},
                    {gte: baselineValue, color: greenColor},
                ],
                outOfRange: {color: greenColor},
            };
        }

        chartInstance.setOption(option, true);

        // Emit chart ready API for MeasureOverlay coordinate mapping
        emitChartReady();
    }
</script>

<div
    bind:this={chartContainer}
    class="w-full"
    style="height: {height};"
></div>

