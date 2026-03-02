<!--
  LineChart — ECharts line chart with stale-data gradient opacity.

  Features:
  - Line series with configurable area fill
  - Gradient opacity based on staleDays: max(0.3, 1.0 - staleDays * 0.15)
  - Dynamic color: changes to red for negative percentage values
  - Tooltip with date and value
  - Dark mode support with MutationObserver
  - ResizeObserver for responsive sizing
  - Mouse wheel zoom + drag-to-pan via ECharts inside dataZoom
  - Click event emission for parent components
  - External zoom range synchronization with DataZoomBar

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
        /** View mode (for tooltip formatting) */
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
        viewMode = 'absolute',
    }: Props = $props();

    // Default colors
    const DEFAULT_LINE_LIGHT = '#1a4031';
    const DEFAULT_LINE_DARK = '#4ade80';

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
        // Watch for dark mode changes to re-render chart with correct colors
        const observer = new MutationObserver(() => {
            if (chartContainer && data.length > 0) {
                renderChart();
            }
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
            tick().then(renderChart);
        }
    });

    $effect(() => {
        // Update zoom range from external source (DataZoomBar) without full re-render
        if (chartInstance && zoomRange) {
            suppressZoomEvent = true;
            chartInstance.dispatchAction({
                type: 'dataZoom',
                start: zoomRange[0],
                end: zoomRange[1],
            });
            // Reset flag after a short delay
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
    // Gradient Opacity
    // =========================================================================

    function getOpacity(staleDays?: number): number {
        if (!staleDays || staleDays === 0) return 1.0;
        return Math.max(0.3, 1.0 - staleDays * 0.15);
    }

    // =========================================================================
    // Chart Rendering
    // =========================================================================

    function renderChart() {
        if (!chartContainer || data.length === 0) return;

        if (!chartInstance) {
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});

            // Click handler
            if (onPointClick) {
                chartInstance.on('click', 'series.line', (params: any) => {
                    if (params.dataIndex !== undefined && data[params.dataIndex]) {
                        const point = data[params.dataIndex];
                        onPointClick!(point.date, point.value);
                    }
                });
            }

            // Bi-directional zoom: when user zooms inside the main chart, emit event
            // so DataZoomBar can sync. But suppress when the zoom came FROM the DataZoomBar.
            chartInstance.on('datazoom', (params: any) => {
                if (!suppressZoomEvent && params.batch && params.batch.length > 0) {
                    const {start, end} = params.batch[0];
                    if (typeof start === 'number' && typeof end === 'number') {
                        // Dispatch a custom event on the container element
                        chartContainer?.dispatchEvent(new CustomEvent('chartZoom', {
                            detail: {start, end},
                            bubbles: true,
                        }));
                    }
                }
            });

            // Setup resize observer
            if (!resizeObserver) {
                resizeObserver = new ResizeObserver(() => chartInstance?.resize());
                resizeObserver.observe(chartContainer);
            }
        }

        const isDark = document.documentElement.classList.contains('dark');
        const effectiveLineColor = isDark
            ? (darkLineColor || DEFAULT_LINE_DARK)
            : (lineColor || DEFAULT_LINE_LIGHT);

        // Area fill colors derived from line color
        const areaTopColor = isDark
            ? hexToRgba(darkLineColor || DEFAULT_LINE_DARK, 0.35)
            : hexToRgba(lineColor || DEFAULT_LINE_LIGHT, 0.2);
        const areaBottomColor = isDark
            ? hexToRgba(darkLineColor || DEFAULT_LINE_DARK, 0.05)
            : hexToRgba(lineColor || DEFAULT_LINE_LIGHT, 0.02);

        // Build visual map pieces for gradient opacity
        const pieces: any[] = [];
        if (showGradient && !compact) {
            for (let i = 0; i < data.length - 1; i++) {
                const opacity = getOpacity(data[i].staleDays);
                pieces.push({
                    gt: i,
                    lte: i + 1,
                    color: effectiveLineColor,
                    opacity: opacity,
                });
            }
        }

        // Main line series
        const mainSeries: any = {
            type: 'line',
            name: currency || 'Value',
            data: data.map(d => [d.date, d.value]),
            smooth: compact ? true : false,
            symbol: compact ? 'none' : 'circle',
            symbolSize: compact ? 0 : 4,
            showSymbol: !compact,
            lineStyle: {
                width: compact ? 1.5 : 2,
                color: effectiveLineColor,
            },
            itemStyle: {
                color: effectiveLineColor,
            },
            emphasis: {
                focus: compact ? 'none' : 'series',
            },
        };

        // Area fill
        if (areaFill) {
            mainSeries.areaStyle = {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    {offset: 0, color: areaTopColor},
                    {offset: 1, color: areaBottomColor},
                ]),
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
        if (viewMode === 'percentage') {
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
                    formatter: viewMode === 'percentage' ? '{value}%' : undefined,
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
                    const suffix = viewMode === 'percentage' ? '%' : '';
                    let html = `<strong>${date}</strong><br/>${currency} ${Number(value).toFixed(4)}${suffix}`;
                    if (dataPoint?.staleDays && dataPoint.staleDays > 0) {
                        html += `<br/><span style="color:#f59e0b;font-size:11px">⚠ Stale: ${dataPoint.staleDays} day(s) old</span>`;
                    }
                    return html;
                },
            },
            series,
        };

        // Visual map for gradient (only for non-compact with gradient enabled)
        if (showGradient && !compact && pieces.length > 0) {
            (option as any).visualMap = {
                show: false,
                dimension: 0,
                pieces: pieces,
            };
        }

        chartInstance.setOption(option, true);
    }

    // =========================================================================
    // Helpers
    // =========================================================================

    /** Convert hex color (#rrggbb) to rgba string */
    function hexToRgba(hex: string, alpha: number): string {
        const h = hex.replace('#', '');
        const r = parseInt(h.substring(0, 2), 16);
        const g = parseInt(h.substring(2, 4), 16);
        const b = parseInt(h.substring(4, 6), 16);
        return `rgba(${r},${g},${b},${alpha})`;
    }
</script>

<div
    bind:this={chartContainer}
    class="w-full"
    style="height: {height};"
></div>

