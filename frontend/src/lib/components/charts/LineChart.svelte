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
    import {onMount, tick} from 'svelte';
    import * as echarts from 'echarts';
    import {t} from '$lib/i18n';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {
        COLORS,
        buildMainSeries,
        buildBandSeries,
        buildBarSeries,
        updateArrowRotations,
    } from './lineChartHelpers';

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
        viewMode = 'absolute',
        yAxisMode = 'auto',
        yAxisMin,
        yAxisMax,
        overlaySignals = [],
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
            // Touch all visual props to register reactive dependencies
            void overlaySignals;
            void areaFill;
            void colorByBaseline;
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
            tick().then(renderChart);
        }
    });


    function cleanup() {
        resizeObserver?.disconnect();
        resizeObserver = null;
        chartOptionSet = false;
        chartInstance?.dispose();
        chartInstance = null;
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
                    try {
                        chartInstance?.resize();
                        if (chartInstance) updateArrowRotations(chartInstance);
                    } catch (_) { /* ignore coord errors during resize */ }
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
            chartInstance = echarts.init(chartContainer, undefined, {renderer: 'canvas'});

            if (onPointClick) {
                chartInstance.on('click', 'series.line', (params: any) => {
                    if (params.dataIndex !== undefined && data[params.dataIndex]) {
                        const point = data[params.dataIndex];
                        onPointClick!(point.date, point.value);
                    }
                });
            }

            // Recompute arrow rotations when zoom changes (aspect ratio shifts)
            chartInstance.on('dataZoom', () => {
                if (chartInstance) updateArrowRotations(chartInstance);
            });
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

        // Determine if we need baseline coloring (green above baseline, red below)
        const useBaselineColoring = colorByBaseline && !compact;
        const baselineValue = isPercentage ? 0 : (data[0]?.value ?? 0);

        // Build per-point stale data array
        const staleDaysArr = data.map(d => d.staleDays ?? 0);

        const series: any[] = [];
        // Tooltip needs a stable series name for the main data — we use this name
        // for both single-series mode and the segmented baseline-color mode.
        const mainSeriesName = currency || 'Value';

        // ── Unified main series: handles baseline coloring + stale gradient together ──
        {
            const values = data.map(d => d.value);
            const lineW = compact ? 1.5 : 2;
            const mainSeriesList = buildMainSeries(
                values,
                staleDaysArr,
                baseColor,
                greenColor,
                redColor,
                isDark,
                areaFill,
                lineW,
                mainSeriesName,
                useBaselineColoring,
                baselineValue,
                showGradient,
            );
            series.push(...mainSeriesList);
        }

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

        // Overlay signals — rendered as additional series.
        // Supports three seriesType modes:
        //   'line' (default) — standard overlay line
        //   'bar'            — vertical bars (e.g. MACD histogram) on secondary axis
        //   'band'           — confidence band (e.g. Bollinger): stacked area lower→upper + middle line
        if (overlaySignals && overlaySignals.length > 0) {
            for (const signal of overlaySignals) {
                if (!signal.data.length) continue;

                const sType = signal.seriesType ?? 'line';

                // Build date→value lookup, then align to main chart's date axis
                const signalLookup = new Map(signal.data.map(d => [d.date, d.value]));
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
                    connectNulls: true,
                    smooth: false,
                    symbol: 'none',
                    showSymbol: false,
                    sampling: 'lttb',
                    yAxisIndex: signal.yAxisIndex ?? 0,
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
            const baselineData = data.map(() => baselineValue);
            series.push({
                type: 'line',
                name: '__baseline__',
                data: baselineData,
                symbol: 'none',
                showSymbol: false,
                sampling: 'lttb',
                lineStyle: {
                    color: isDark ? '#64748b' : '#9ca3af',
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
        // Check which overlay axes are active (have at least one signal with data).
        // In compact mode the axes are hidden but still auto-scaled so overlay
        // lines render at the correct proportions — no fixed min/max fallback.
        const hasSecondaryAxis = overlaySignals.some(s => (s.yAxisIndex ?? 0) === 1 && s.data.length > 0);
        const hasTertiaryAxis = overlaySignals.some(s => (s.yAxisIndex ?? 0) === 2 && s.data.length > 0);

        // Count how many extra axes need right-side space (only visible in non-compact)
        const extraAxesCount = (hasSecondaryAxis ? 1 : 0) + (hasTertiaryAxis ? 1 : 0);

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
                right: extraAxesCount > 1 ? 115 : extraAxesCount === 1 ? 60 : 12,
                bottom: 25,
                left: 10,
                containLabel: true,
            };

        // Pre-compute stale lookup map for O(1) tooltip access (instead of O(n) data.find per hover)
        const staleLookup = new Map<string, number>();
        for (const d of data) {
            if (d.staleDays && d.staleDays > 0) staleLookup.set(d.date, d.staleDays);
        }

        const option: echarts.EChartsOption = {
            animation: false,
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
                        position: compact && showMiniAxis ? 'right' as const : 'left' as const,
                        min: effectiveMin,
                        max: effectiveMax,
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
                                color: isDark ? '#4b5563' : '#d1d5db',
                                type: 'dashed' as const,
                                opacity: compact && showMiniAxis ? 0.5 : 1,
                            },
                        },
                        scale: !isInclude0,
                    };
                })(),
                // Axis 1 — Secondary (right side, independent scale for RSI 0-100)
                // Always declared to prevent ECharts coord resolution crashes when
                // axis count changes between renders. When no series use it, it's
                // hidden with fixed bounds so coord resolution never fails.
                // In compact mode: hidden but auto-scaled so overlay lines render correctly.
                {
                    type: 'value',
                    name: hasSecondaryAxis && !compact ? 'RSI' : '',
                    nameLocation: 'start',
                    nameGap: 5,
                    nameTextStyle: {
                        color: isDark ? '#94a3b8' : '#9ca3af',
                        fontSize: 9,
                        fontWeight: 'bold',
                        align: 'center',
                    },
                    show: hasSecondaryAxis && !compact,
                    position: 'right',
                    // Always auto-scale when signals are present (no fixed min/max)
                    min: hasSecondaryAxis ? undefined : 0,
                    max: hasSecondaryAxis ? undefined : 100,
                    axisLine: {show: hasSecondaryAxis && !compact, lineStyle: {color: isDark ? '#64748b' : '#9ca3af'}},
                    axisTick: {show: hasSecondaryAxis && !compact},
                    axisLabel: {
                        show: hasSecondaryAxis && !compact,
                        color: isDark ? '#94a3b8' : '#9ca3af',
                        fontSize: 10,
                        formatter: (v: number) => v.toFixed(0),
                    },
                    splitLine: {show: false},
                    scale: hasSecondaryAxis,
                },
                // Axis 2 — Tertiary (right side with offset, independent scale for MACD)
                // Always declared so ECharts never crashes on yAxisIndex=2 references.
                // In compact mode: hidden but auto-scaled so overlay lines render correctly.
                {
                    type: 'value',
                    name: hasTertiaryAxis && !compact ? 'MACD' : '',
                    nameLocation: 'start',
                    nameGap: 5,
                    nameTextStyle: {
                        color: isDark ? '#a78bfa' : '#7c3aed',
                        fontSize: 9,
                        fontWeight: 'bold',
                        align: 'center',
                    },
                    show: hasTertiaryAxis && !compact,
                    position: 'right',
                    offset: hasSecondaryAxis && hasTertiaryAxis ? 55 : 0,
                    min: hasTertiaryAxis ? undefined : 0,
                    max: hasTertiaryAxis ? undefined : 1,
                    axisLine: {show: hasTertiaryAxis && !compact, lineStyle: {color: isDark ? '#8b5cf6' : '#7c3aed'}},
                    axisTick: {show: hasTertiaryAxis && !compact},
                    axisLabel: {
                        show: hasTertiaryAxis && !compact,
                        color: isDark ? '#a78bfa' : '#7c3aed',
                        fontSize: 10,
                        formatter: (v: number) => {
                            if (Math.abs(v) >= 1) return v.toFixed(2);
                            return v.toFixed(4).replace(/\.?0+$/, '');
                        },
                    },
                    splitLine: {show: false},
                    scale: hasTertiaryAxis,
                },
            ],
            tooltip: compact ? undefined : {
                trigger: 'axis',
                appendToBody: true,
                backgroundColor: isDark ? '#1e293b' : '#ffffff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    if (!items.length) return '';
                    const date = items[0].axisValue || items[0].name;
                    let html = `<strong>${date}</strong>`;

                    // Build a set of band helper series names to skip in tooltip
                    const bandHelperNames = new Set<string>();
                    for (const sig of overlaySignals) {
                        if ((sig.seriesType ?? 'line') === 'band') {
                            bandHelperNames.add(`${sig.label} Lower`);
                            bandHelperNames.add(`${sig.label} Band`);
                        }
                    }

                    // Build yAxisIndex lookup for overlay signals by name
                    const signalAxisMap = new Map<string, number>();
                    for (const sig of overlaySignals) {
                        signalAxisMap.set(sig.label, sig.yAxisIndex ?? 0);
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
                        const value = (typeof rawVal === 'object' && rawVal?.value !== undefined)
                            ? rawVal.value
                            : rawVal;
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
                        const axisNote = axisIdx === 1
                            ? ` <span style="font-size:10px;color:#94a3b8">[RSI]</span>`
                            : axisIdx === 2
                                ? ` <span style="font-size:10px;color:#a78bfa">[MACD]</span>`
                                : '';
                        html += `<br/>${colorDot}${p.seriesName}: ${Number(value).toFixed(4)}${valueSuffix}${axisNote}`;

                        // For band signals, also show upper/lower in the tooltip
                        const bandSignal = overlaySignals.find(
                            s => s.label === p.seriesName && (s.seriesType ?? 'line') === 'band' && s.bandData
                        );
                        if (bandSignal?.bandData) {
                            const dataIdx = bandSignal.data.findIndex(d => d.date === date);
                            if (dataIdx >= 0) {
                                html += `<br/><span style="padding-left:12px;font-size:11px;color:#94a3b8">${$t('chart.tooltip.upper')}: ${bandSignal.bandData.upper[dataIdx].toFixed(4)}${suffix} · ${$t('chart.tooltip.lower')}: ${bandSignal.bandData.lower[dataIdx].toFixed(4)}${suffix}</span>`;
                            }
                        }
                    }

                    // Stale warning for main series
                    const staleDays = staleLookup.get(date);
                    if (staleDays !== undefined) {
                        html += `<br/><span style="color:#f59e0b;font-size:11px">⚠ ${$t('chart.tooltip.stale', {values: {days: staleDays}})}</span>`;
                    }
                    if (isPercentage) {
                        html += `<br/><span style="color:#94a3b8;font-size:10px">${$t('chart.tooltip.percentNote')}</span>`;
                    }
                    return html;
                },
            },
            series,
        };

        // Single pass: render everything at once — no visualMap needed
        // (baseline coloring is handled by segmented series above)

        // Preserve user zoom state across re-renders (adding signals, toggling options).
        // Without this, setOption({...}, true) replaces dataZoom and resets scroll position.
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
            } catch (_) { /* ignore */ }
        }

        chartInstance.setOption(option, true);
        chartOptionSet = true;

        // Compute pixel-accurate arrow rotations after layout is established
        updateArrowRotations(chartInstance);

        // Restore zoom position if the user had zoomed/panned
        if (savedZoom && !compact) {
            chartInstance.dispatchAction({
                type: 'dataZoom',
                start: savedZoom.start,
                end: savedZoom.end,
            });
        }
    }
</script>

<div
    bind:this={chartContainer}
    class="w-full"
    style="height: {height};"
></div>

