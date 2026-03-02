<!--
  LineChart — ECharts line chart with stale-data gradient, segment coloring, and zoom sync.

  Features:
  - Line series with configurable area fill
  - Gradient opacity based on staleDays
  - Segment-based color in % mode: green above 0%, red below 0% (with matching area fill)
  - Y-axis always visible with values
  - Tooltip with date, value, and stale warning
  - Dark mode support with MutationObserver
  - ResizeObserver for responsive sizing
  - Mouse wheel zoom + drag-to-pan via ECharts inside dataZoom
  - Bidirectional zoom sync: emits onZoomChange when user zooms inside chart
  - Click event emission for parent components

  Used by: PriceChartCompact, PriceChartFull (line mode)
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';

    // =========================================================================
    // Types
    // =========================================================================

    export interface LineDataPoint {
        date: string;
        value: number;
        staleDays?: number;
    }

    interface Props {
        data: LineDataPoint[];
        /** Y-axis label / currency code */
        currency?: string;
        /** Show area fill under the line */
        areaFill?: boolean;
        /** Show stale-data gradient */
        showGradient?: boolean;
        /** CSS height */
        height?: string;
        /** Compact mode (no axis labels, no tooltip, thinner line) */
        compact?: boolean;
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
    }

    let {
        data = [],
        currency = '',
        areaFill = true,
        showGradient = true,
        height = '300px',
        compact = false,
        lineColor,
        darkLineColor,
        pendingColor = '#f59e0b',
        pendingData = [],
        onPointClick,
        zoomRange,
        onZoomChange,
        viewMode = 'absolute',
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
        if (chartContainer && data) tick().then(renderChart);
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

        // In percentage mode, use segment coloring (green > 0, red < 0)
        // In absolute mode, use single color
        const baseColor = isDark
            ? (darkLineColor || DEFAULT_LINE_DARK)
            : (lineColor || DEFAULT_LINE_LIGHT);

        const greenColor = isDark ? GREEN_DARK : GREEN_LIGHT;
        const redColor = isDark ? RED_DARK : RED_LIGHT;

        // Build series data
        const seriesData = data.map(d => [d.date, d.value]);

        // Main line series
        const mainSeries: any = {
            type: 'line',
            name: currency || 'Value',
            data: seriesData,
            smooth: compact ? true : false,
            symbol: compact ? 'none' : 'circle',
            symbolSize: compact ? 0 : 4,
            showSymbol: !compact,
            lineStyle: {
                width: compact ? 1.5 : 2,
                color: isPercentage ? undefined : baseColor,  // undefined = let visualMap decide
            },
            itemStyle: {
                color: isPercentage ? undefined : baseColor,
            },
            emphasis: {
                focus: compact ? 'none' : 'series',
            },
        };

        // Area fill
        if (areaFill && !isPercentage) {
            const areaTopColor = hexToRgba(baseColor, isDark ? 0.35 : 0.2);
            const areaBottomColor = hexToRgba(baseColor, isDark ? 0.05 : 0.02);
            mainSeries.areaStyle = {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    {offset: 0, color: areaTopColor},
                    {offset: 1, color: areaBottomColor},
                ]),
            };
        }

        // In percentage mode, use piecewise visualMap for segment coloring
        if (areaFill && isPercentage) {
            mainSeries.areaStyle = {
                // Will be overridden by visualMap colors
                opacity: isDark ? 0.2 : 0.12,
            };
        }

        const series: any[] = [mainSeries];

        // Pending edits overlay
        if (pendingData && pendingData.length > 0) {
            series.push({
                type: 'scatter',
                name: 'Pending',
                data: pendingData.map(d => [d.date, d.value]),
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

        // Mark line at y=0 when in percentage mode
        if (isPercentage) {
            mainSeries.markLine = {
                silent: true,
                symbol: 'none',
                lineStyle: {
                    color: isDark ? '#64748b' : '#9ca3af',
                    type: 'dashed',
                    width: 1,
                },
                data: [{yAxis: 0}],
                label: {show: false},
            };
        }

        const option: echarts.EChartsOption = {
            animation: !compact,
            grid: {
                top: compact ? 5 : 30,
                right: compact ? 5 : 20,
                bottom: compact ? 5 : 30,
                left: compact ? 5 : 60,
                containLabel: !compact,
            },
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
                data: data.map(d => d.date),
                show: !compact,
                axisLine: {lineStyle: {color: isDark ? '#475569' : '#d1d5db'}},
                axisLabel: {color: isDark ? '#94a3b8' : '#6b7280', fontSize: 11},
                splitLine: {show: false},
            },
            yAxis: {
                type: 'value',
                show: !compact,
                axisLine: {show: false},
                axisLabel: {
                    color: isDark ? '#94a3b8' : '#6b7280',
                    fontSize: 11,
                    formatter: isPercentage ? '{value}%' : undefined,
                },
                splitLine: {lineStyle: {color: isDark ? '#334155' : '#f3f4f6'}},
                scale: true,
            },
            tooltip: compact ? undefined : {
                trigger: 'axis',
                backgroundColor: isDark ? '#1e293b' : '#ffffff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: any) => {
                    const p = Array.isArray(params) ? params[0] : params;
                    const date = p.axisValue || p.name;
                    const value = typeof p.value === 'object' ? p.value[1] : p.value;
                    const dataPoint = data.find(d => d.date === date);
                    const suffix = isPercentage ? '%' : '';
                    let html = `<strong>${date}</strong><br/>${currency} ${Number(value).toFixed(4)}${suffix}`;
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

        // Visual map for percentage mode: segment coloring
        if (isPercentage && !compact) {
            (option as any).visualMap = {
                show: false,
                seriesIndex: 0,
                dimension: 1,  // y-axis value
                pieces: [
                    {lt: 0, color: redColor},
                    {gte: 0, color: greenColor},
                ],
            };
        } else if (showGradient && !compact) {
            // Stale data gradient (absolute mode)
            const pieces: any[] = [];
            for (let i = 0; i < data.length - 1; i++) {
                const opacity = getOpacity(data[i].staleDays);
                pieces.push({
                    gt: i, lte: i + 1,
                    color: baseColor,
                    opacity: opacity,
                });
            }
            if (pieces.length > 0) {
                (option as any).visualMap = {
                    show: false,
                    dimension: 0,
                    pieces: pieces,
                };
            }
        }

        chartInstance.setOption(option, true);
    }
</script>

<div
    bind:this={chartContainer}
    class="w-full"
    style="height: {height};"
></div>

