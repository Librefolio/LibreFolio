<!--
  PriceChartFull — Full-featured price chart with unified ECharts instance.

  Architecture: Single ECharts instance with 2 grids + shared dataZoom.
  - grid[0] (top): Main chart with line/signal series, overlay markers, pending edits
  - grid[1] (bottom): Overview mini-chart with dataZoom slider
  - dataZoom[0]: 'slider' type anchored to grid[1], controls both grids
  - dataZoom[1]: 'inside' type on grid[0] for mouse wheel zoom/pan

  No external DataZoomBar component needed — everything is native ECharts sync.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import ChartToolbar from './ChartToolbar.svelte';
    import type {LineDataPoint} from './LineChart.svelte';
    import type {ChartType, ViewMode} from './ChartToolbar.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {
        COLORS,
        buildMainSeries,
        buildBandSeries,
        buildBarSeries,
        computeArrowRotation as computeArrowRotationHelper,
    } from './lineChartHelpers';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        data: LineDataPoint[];
        pendingData?: LineDataPoint[];
        currency?: string;
        chartHeight?: string;
        overviewHeight?: string;
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
        /** Hide the built-in toolbar (chart type + view mode toggles) */
        hideToolbar?: boolean;
        /** Externally controlled view mode (when toolbar is hidden) */
        externalViewMode?: ViewMode;
    }

    let {
        data = [],
        pendingData = [],
        currency = '',
        chartHeight = '400px',
        overviewHeight = '60px',
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
        hideToolbar = false,
        externalViewMode,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartType: ChartType = $state('line');
    let viewMode: ViewMode = $state('absolute');
    let chartContainer: HTMLDivElement | undefined = $state(undefined);
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let chartOptionSet = false;

    $effect(() => { chartType = initialChartType; });
    $effect(() => { viewMode = externalViewMode ?? initialViewMode; });

    // =========================================================================
    // Derived data
    // =========================================================================

    let displayData = $derived.by(() => {
        if (viewMode === 'absolute' || data.length === 0) return data;
        const baseValue = data[0].value;
        if (baseValue === 0) return data;
        return data.map(d => ({...d, value: ((d.value - baseValue) / baseValue) * 100}));
    });

    let displayPending = $derived.by(() => {
        if (viewMode === 'absolute' || data.length === 0 || !pendingData || pendingData.length === 0) return pendingData;
        const baseValue = data[0].value;
        if (baseValue === 0) return pendingData;
        return pendingData.map(d => ({...d, value: ((d.value - baseValue) / baseValue) * 100}));
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
            resizeObserver?.disconnect();
            chartInstance?.dispose();
            chartInstance = null;
        };
    });

    $effect(() => {
        if (chartContainer && data) {
            void overlaySignals;
            void areaFill;
            void colorByBaseline;
            void showGridLines;
            void showGradient;
            void viewMode;
            void yAxisMode;
            void yAxisMin;
            void yAxisMax;
            void pendingData;
            tick().then(renderChart);
        }
    });

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleChartTypeChange(type: ChartType) {
        chartType = type;
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

    // =========================================================================
    // Chart Rendering — Unified 2-grid layout
    // =========================================================================

    function renderChart() {
        if (!chartContainer || displayData.length === 0) return;

        if (!resizeObserver) {
            resizeObserver = new ResizeObserver(() => {
                if (chartOptionSet) {
                    try { chartInstance?.resize(); } catch (_) {}
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

            // Series line click for edit mode
            chartInstance.on('click', 'series.line', (params: any) => {
                if (params.dataIndex !== undefined && displayData[params.dataIndex]) {
                    const point = displayData[params.dataIndex];
                    handlePointClick(point.date, point.value);
                }
            });

            // Global click handler for measure mode — catches clicks anywhere on the chart area
            chartInstance.getZr().on('click', (params: any) => {
                if (!measureMode || !onMeasureClick || !chartInstance) return;
                const pointInPixel = [params.offsetX, params.offsetY];
                if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                    const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                    if (pointInGrid) {
                        const dateIdx = Math.round(pointInGrid[0]);
                        if (dateIdx >= 0 && dateIdx < displayData.length) {
                            const point = displayData[dateIdx];
                            handlePointClick(point.date, point.value);
                        }
                    }
                }
            });
        }

        const isDark = document.documentElement.classList.contains('dark');
        const isPercentage = viewMode === 'percentage';

        const baseColor = isDark ? COLORS.lineDark : COLORS.lineLight;
        const greenColor = isDark ? COLORS.greenDark : COLORS.greenLight;
        const redColor = isDark ? COLORS.redDark : COLORS.redLight;

        const dates = displayData.map(d => d.date);
        const useBaselineColoring = colorByBaseline;
        const baselineValue = isPercentage ? 0 : (displayData[0]?.value ?? 0);
        const staleDaysArr = displayData.map(d => d.staleDays ?? 0);
        const mainSeriesName = currency || 'Value';

        const series: any[] = [];
        const values = displayData.map(d => d.value);
        const mainSeriesList = buildMainSeries(
            values, staleDaysArr, baseColor, greenColor, redColor, isDark,
            areaFill, 2, mainSeriesName, useBaselineColoring, baselineValue, showGradient,
        );
        series.push(...mainSeriesList);

        // Pending edits overlay
        if (displayPending && displayPending.length > 0) {
            series.push({
                type: 'scatter', name: 'Pending', xAxisIndex: 0, yAxisIndex: 0,
                data: displayPending.map(d => {
                    const idx = dates.indexOf(d.date);
                    return idx >= 0 ? [idx, d.value] : null;
                }).filter(Boolean),
                symbol: 'diamond', symbolSize: 10,
                itemStyle: {color: '#f59e0b', borderColor: isDark ? '#1e293b' : '#ffffff', borderWidth: 2},
                z: 10,
            });
        }

        // Overlay signals
        if (overlaySignals && overlaySignals.length > 0) {
            for (const signal of overlaySignals) {
                if (!signal.data.length) continue;
                const sType = signal.seriesType ?? 'line';
                const signalLookup = new Map(signal.data.map(d => [d.date, d.value]));
                const signalSeriesData: any[] = dates.map((date) => signalLookup.get(date) ?? null);

                if (sType === 'band' && signal.bandData) {
                    const bandSeries = buildBandSeries(signal, dates, isDark);
                    for (const bs of bandSeries) { bs.xAxisIndex = 0; series.push(bs); }
                    continue;
                }
                if (sType === 'bar') {
                    const barS = buildBarSeries(signal, signalSeriesData, isDark);
                    barS.xAxisIndex = 0;
                    series.push(barS);
                    continue;
                }

                const overlaySeries: any = {
                    type: 'line', name: signal.label, data: signalSeriesData,
                    connectNulls: true, smooth: false, symbol: 'none', showSymbol: false,
                    xAxisIndex: 0, yAxisIndex: signal.yAxisIndex ?? 0,
                    lineStyle: {color: signal.color, width: signal.lineWidth, type: signal.lineType},
                    itemStyle: {color: signal.color},
                    emphasis: {focus: 'none'}, z: 1,
                };

                if ((signal.markerStart || signal.markerEnd) && signalSeriesData.length > 0) {
                    const markData: any[] = [];
                    if (signal.markerStart) {
                        for (let i = 0; i < signalSeriesData.length; i++) {
                            if (signalSeriesData[i] !== null) {
                                markData.push({
                                    coord: [dates[i], signalSeriesData[i]],
                                    symbol: signal.markerStart,
                                    symbolSize: Math.max(signal.lineWidth * 3, 8),
                                    symbolRotate: signal.markerStart === 'arrow' ? computeArrowRotationHelper(signalSeriesData, i, true) : 0,
                                    itemStyle: {color: signal.color},
                                });
                                break;
                            }
                        }
                    }
                    if (signal.markerEnd) {
                        for (let i = signalSeriesData.length - 1; i >= 0; i--) {
                            if (signalSeriesData[i] !== null) {
                                markData.push({
                                    coord: [dates[i], signalSeriesData[i]],
                                    symbol: signal.markerEnd,
                                    symbolSize: Math.max(signal.lineWidth * 3, 8),
                                    symbolRotate: signal.markerEnd === 'arrow' ? computeArrowRotationHelper(signalSeriesData, i, false) : 0,
                                    itemStyle: {color: signal.color},
                                });
                                break;
                            }
                        }
                    }
                    if (markData.length > 0) {
                        overlaySeries.markPoint = {data: markData, label: {show: false}, animation: false};
                    }
                }
                series.push(overlaySeries);
            }
        }

        // Baseline reference line
        if (useBaselineColoring) {
            series.push({
                type: 'line', name: '__baseline__',
                data: displayData.map(() => baselineValue),
                xAxisIndex: 0, yAxisIndex: 0,
                symbol: 'none', showSymbol: false,
                lineStyle: {color: isDark ? '#64748b' : '#9ca3af', type: 'dashed', width: 1},
                itemStyle: {color: 'transparent'},
                emphasis: {disabled: true}, tooltip: {show: false}, silent: true, z: 0,
            });
        }

        // Overview series (grid[1]) — simplified line (always absolute)
        const overviewValues = data.map(d => d.value);
        series.push({
            type: 'line', name: '__overview__',
            data: overviewValues,
            xAxisIndex: 1, yAxisIndex: 3,
            smooth: true, symbol: 'none',
            lineStyle: {width: 1, color: baseColor, opacity: 0.5},
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    {offset: 0, color: isDark ? 'rgba(74,222,128,0.15)' : 'rgba(26,64,49,0.1)'},
                    {offset: 1, color: 'transparent'},
                ]),
            },
            tooltip: {show: false}, silent: true,
        });

        // Check which overlay axes are active
        const hasSecondaryAxis = overlaySignals.some(s => (s.yAxisIndex ?? 0) === 1 && s.data.length > 0);
        const hasTertiaryAxis = overlaySignals.some(s => (s.yAxisIndex ?? 0) === 2 && s.data.length > 0);
        const extraAxesCount = (hasSecondaryAxis ? 1 : 0) + (hasTertiaryAxis ? 1 : 0);

        // Y-axis configuration
        const isCustom = yAxisMode === 'custom';
        const isInclude0 = yAxisMode === 'include0';
        let effectiveMin = isCustom && yAxisMin !== undefined ? yAxisMin : undefined;
        let effectiveMax = isCustom && yAxisMax !== undefined ? yAxisMax : undefined;
        if (effectiveMin !== undefined && effectiveMax !== undefined && effectiveMin > effectiveMax) {
            [effectiveMin, effectiveMax] = [effectiveMax, effectiveMin];
        }

        // Preserve zoom state across re-renders
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
            } catch (_) {}
        }

        const option: echarts.EChartsOption = {
            animation: false,
            grid: [
                {top: 20, right: extraAxesCount > 1 ? 115 : extraAxesCount === 1 ? 60 : 12, bottom: 80, left: 10, containLabel: true},
                {left: 50, right: 50, bottom: 10, height: 40},
            ],
            xAxis: [
                {type: 'category', data: dates, gridIndex: 0, axisLine: {lineStyle: {color: isDark ? '#475569' : '#d1d5db'}}, axisLabel: {color: isDark ? '#94a3b8' : '#6b7280', fontSize: 11}, splitLine: {show: false}},
                {type: 'category', data: dates, gridIndex: 1, show: false},
            ],
            yAxis: [
                {type: 'value', gridIndex: 0, position: 'left', min: effectiveMin, max: effectiveMax,
                    axisLine: {show: true, lineStyle: {color: isDark ? '#475569' : '#d1d5db'}}, axisTick: {show: true},
                    axisLabel: {color: isDark ? '#94a3b8' : '#6b7280', fontSize: 11, formatter: isPercentage ? (v: number) => `${v.toFixed(1)}%` : (v: number) => { if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}k`; if (Math.abs(v) >= 1) return v.toFixed(2); return v.toFixed(4).replace(/\.?0+$/, ''); }},
                    splitLine: {show: showGridLines, lineStyle: {color: isDark ? '#4b5563' : '#d1d5db', type: 'dashed'}}, scale: !isInclude0},
                {type: 'value', gridIndex: 0, position: 'right', name: hasSecondaryAxis ? 'RSI' : '', nameLocation: 'start', nameGap: 5,
                    nameTextStyle: {color: isDark ? '#94a3b8' : '#9ca3af', fontSize: 9, fontWeight: 'bold', align: 'center'},
                    show: hasSecondaryAxis, min: hasSecondaryAxis ? undefined : 0, max: hasSecondaryAxis ? undefined : 100,
                    axisLine: {show: hasSecondaryAxis, lineStyle: {color: isDark ? '#64748b' : '#9ca3af'}}, axisTick: {show: hasSecondaryAxis},
                    axisLabel: {show: hasSecondaryAxis, color: isDark ? '#94a3b8' : '#9ca3af', fontSize: 10, formatter: (v: number) => v.toFixed(0)},
                    splitLine: {show: false}, scale: hasSecondaryAxis},
                {type: 'value', gridIndex: 0, position: 'right', name: hasTertiaryAxis ? 'MACD' : '', nameLocation: 'start', nameGap: 5,
                    nameTextStyle: {color: isDark ? '#a78bfa' : '#7c3aed', fontSize: 9, fontWeight: 'bold', align: 'center'},
                    show: hasTertiaryAxis, offset: hasSecondaryAxis && hasTertiaryAxis ? 55 : 0,
                    min: hasTertiaryAxis ? undefined : 0, max: hasTertiaryAxis ? undefined : 1,
                    axisLine: {show: hasTertiaryAxis, lineStyle: {color: isDark ? '#8b5cf6' : '#7c3aed'}}, axisTick: {show: hasTertiaryAxis},
                    axisLabel: {show: hasTertiaryAxis, color: isDark ? '#a78bfa' : '#7c3aed', fontSize: 10, formatter: (v: number) => Math.abs(v) >= 1 ? v.toFixed(2) : v.toFixed(4).replace(/\.?0+$/, '')},
                    splitLine: {show: false}, scale: hasTertiaryAxis},
                {type: 'value', gridIndex: 1, show: false, scale: true},
            ],
            dataZoom: [
                {type: 'slider', xAxisIndex: [0, 1], start: savedZoom?.start ?? 0, end: savedZoom?.end ?? 100, bottom: 10, height: 40,
                    borderColor: isDark ? '#475569' : '#d1d5db', backgroundColor: 'transparent',
                    fillerColor: isDark ? 'rgba(74,222,128,0.1)' : 'rgba(26,64,49,0.08)',
                    handleStyle: {color: isDark ? '#4ade80' : '#1a4031'},
                    textStyle: {color: isDark ? '#94a3b8' : '#6b7280', fontSize: 10}, brushSelect: false},
                {type: 'inside', xAxisIndex: [0, 1], zoomOnMouseWheel: true, moveOnMouseMove: true},
            ],
            tooltip: {
                trigger: 'axis', appendToBody: true,
                backgroundColor: isDark ? '#1e293b' : '#ffffff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    if (!items.length) return '';
                    const date = items[0].axisValue || items[0].name;
                    let html = `<strong>${date}</strong>`;
                    const bandHelperNames = new Set<string>();
                    for (const sig of overlaySignals) {
                        if ((sig.seriesType ?? 'line') === 'band') { bandHelperNames.add(`${sig.label} Lower`); bandHelperNames.add(`${sig.label} Band`); }
                    }
                    const signalAxisMap = new Map<string, number>();
                    for (const sig of overlaySignals) { signalAxisMap.set(sig.label, sig.yAxisIndex ?? 0); }
                    const shownNames = new Set<string>();
                    const firstValue = displayData.length > 0 ? displayData[0].value : null;
                    for (const p of items) {
                        if (p.seriesName === 'Pending' || p.seriesName === '__baseline__' || p.seriesName === '__overview__') continue;
                        if (bandHelperNames.has(p.seriesName)) continue;
                        const rawVal = p.value;
                        const value = (typeof rawVal === 'object' && rawVal?.value !== undefined) ? rawVal.value : rawVal;
                        if (value === null || value === undefined) continue;
                        if (shownNames.has(p.seriesName)) continue;
                        shownNames.add(p.seriesName);
                        const suffix = isPercentage ? '%' : '';
                        const colorDot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px;"></span>`;
                        const axisIdx = signalAxisMap.get(p.seriesName) ?? 0;
                        const valueSuffix = axisIdx === 0 ? suffix : '';
                        const axisNote = axisIdx === 1 ? ' <span style="font-size:10px;color:#94a3b8">[RSI]</span>' : axisIdx === 2 ? ' <span style="font-size:10px;color:#a78bfa">[MACD]</span>' : '';
                        html += `<br/>${colorDot}${p.seriesName}: ${Number(value).toFixed(4)}${valueSuffix}${axisNote}`;
                        // Show delta from first visible point for the main axis (yAxisIndex 0)
                        if (axisIdx === 0 && firstValue !== null) {
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
                    const dataPoint = data.find(d => d.date === date);
                    if (dataPoint?.staleDays && dataPoint.staleDays > 0) {
                        html += `<br/><span style="color:#f59e0b;font-size:11px">⚠ Stale: ${dataPoint.staleDays}d</span>`;
                    }
                    return html;
                },
            },
            series,
        };

        chartInstance.setOption(option, true);
        chartOptionSet = true;
    }
</script>

<div class="space-y-2">
    <!-- Toolbar (hidden when parent provides external controls) -->
    {#if !hideToolbar}
    <ChartToolbar
        {chartType}
        {viewMode}
        onChartTypeChange={handleChartTypeChange}
        onViewModeChange={handleViewModeChange}
        disableCandlestick={true}
    />
    {/if}

    <!-- Unified Chart -->
    <div class="relative">
        {#if chartType === 'line'}
            <div
                bind:this={chartContainer}
                class="w-full"
                style="height: calc({chartHeight} + {overviewHeight});"
                class:cursor-crosshair={measureMode}
            ></div>
        {:else}
            <!-- Candlestick stub — TODO Phase 6 (Assets) -->
            <div class="flex items-center justify-center bg-gray-50 dark:bg-slate-800 rounded-lg border border-dashed border-gray-300 dark:border-slate-600" style="height: {chartHeight};">
                <p class="text-gray-400 dark:text-slate-500 text-sm">Candlestick chart — Coming soon</p>
            </div>
        {/if}
    </div>
</div>
