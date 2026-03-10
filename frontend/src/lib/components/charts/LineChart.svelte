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

    let chartContainer: HTMLDivElement;
    let chartInstance: echarts.ECharts | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let suppressZoomEvent = false;
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
            void viewMode;
            void compact;
            void showMiniAxis;
            void lineColor;
            void darkLineColor;
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
        chartOptionSet = false;
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

        // Ensure ResizeObserver is set up even before first render,
        // so it can trigger renderChart when container becomes visible.
        if (!resizeObserver) {
            resizeObserver = new ResizeObserver(() => {
                if (chartOptionSet) {
                    try { chartInstance?.resize(); } catch (_) { /* ignore coord errors during resize */ }
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

        // Build per-point data with optional stale gradient opacity
        const hasStaleData = showGradient && !useBaselineColoring && data.some(d => (d.staleDays ?? 0) > 0);

        const seriesData: any[] = data.map((d) => {
            const opacity = getOpacity(d.staleDays);
            if (hasStaleData && opacity < 1.0) {
                return {
                    value: d.value,
                    itemStyle: {
                        color: hexToRgba(baseColor, opacity),
                        borderColor: hexToRgba(baseColor, opacity),
                    },
                    lineStyle: {
                        color: hexToRgba(baseColor, opacity),
                    },
                };
            }
            return d.value;
        });

        const series: any[] = [];
        // Tooltip needs a stable series name for the main data — we use this name
        // for both single-series mode and the segmented baseline-color mode.
        const mainSeriesName = currency || 'Value';

        if (useBaselineColoring) {
            // ── Segment-based baseline coloring ──────────────────────────────
            // Instead of using visualMap (which crashes with secondary axes),
            // split the main series data into contiguous green/red segments.
            // Each segment is a separate ECharts series with the same name so
            // the tooltip groups them as one. Null values create gaps so only
            // the relevant part of each series is drawn.
            //
            // We iterate through points and detect zero-crossings relative to
            // baselineValue. At crossings we interpolate the exact crossing point
            // to avoid visual gaps.

            const values = data.map(d => d.value);
            const lineW = compact ? 2 : 2.5;

            // Helper: create one segment series
            const makeSegSeries = (segData: (number | null)[], color: string): any => {
                const s: any = {
                    type: 'line',
                    name: mainSeriesName,
                    data: segData,
                    smooth: false,
                    symbol: 'none',
                    showSymbol: false,
                    yAxisIndex: 0,
                    lineStyle: {width: lineW, color},
                    itemStyle: {color},
                    emphasis: {focus: compact ? 'none' : 'series'},
                    z: 2,
                    // ECharts: only first series with this name shows in legend
                };
                if (areaFill) {
                    const areaTop = hexToRgba(color, isDark ? 0.15 : 0.10);
                    const areaBot = hexToRgba(color, isDark ? 0.03 : 0.02);
                    s.areaStyle = {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {offset: 0, color: areaTop},
                            {offset: 1, color: areaBot},
                        ]),
                    };
                }
                return s;
            };

            // Build green (above baseline) and red (below baseline) data arrays
            const greenData: (number | null)[] = new Array(values.length).fill(null);
            const redData: (number | null)[] = new Array(values.length).fill(null);

            for (let i = 0; i < values.length; i++) {
                const v = values[i];
                if (v >= baselineValue) {
                    greenData[i] = v;
                } else {
                    redData[i] = v;
                }

                // At segment boundaries, duplicate the crossing point in both series
                // so lines connect without gaps
                if (i > 0) {
                    const prev = values[i - 1];
                    const curr = v;
                    const crossedUp = prev < baselineValue && curr >= baselineValue;
                    const crossedDown = prev >= baselineValue && curr < baselineValue;
                    if (crossedUp || crossedDown) {
                        // Both sides need the crossing value for continuity
                        greenData[i - 1] = greenData[i - 1] ?? prev;
                        redData[i - 1] = redData[i - 1] ?? prev;
                        greenData[i] = greenData[i] ?? curr;
                        redData[i] = redData[i] ?? curr;
                    }
                }
            }

            series.push(makeSegSeries(greenData, greenColor));
            series.push(makeSegSeries(redData, redColor));
        } else {
            // ── Single-color main series ─────────────────────────────────────
            const mainSeries: any = {
                type: 'line',
                name: mainSeriesName,
                data: seriesData,
                smooth: !!compact,
                symbol: 'none',
                symbolSize: compact ? 0 : 4,
                showSymbol: false,
                yAxisIndex: 0,
                lineStyle: {
                    width: compact ? 1.5 : 2,
                    color: baseColor,
                },
                itemStyle: {color: baseColor},
                emphasis: {
                    focus: compact ? 'none' : 'series',
                },
            };

            if (areaFill) {
                const areaTopColor = hexToRgba(baseColor, isDark ? 0.35 : 0.2);
                const areaBottomColor = hexToRgba(baseColor, isDark ? 0.05 : 0.02);
                mainSeries.areaStyle = {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {offset: 0, color: areaTopColor},
                        {offset: 1, color: areaBottomColor},
                    ]),
                };
            }
            series.push(mainSeries);
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
                    const {upper, middle, lower} = signal.bandData;
                    const bandColor = signal.color;
                    const bandOpacity = isDark ? 0.18 : 0.12;

                    // Build date→index lookup from signal data for O(1) access
                    const signalDateIdx = new Map(signal.data.map((d, idx) => [d.date, idx]));

                    // Series 1: Lower bound (invisible line, base of the stack)
                    const lowerData: any[] = dates.map((date) => {
                        const idx = signalDateIdx.get(date);
                        if (idx === undefined) return null;
                        return lower[idx];
                    });
                    series.push({
                        type: 'line',
                        name: `${signal.label} Lower`,
                        data: lowerData,
                        lineStyle: {opacity: 0},
                        itemStyle: {color: bandColor},
                        stack: `bb-${signal.id}`,
                        symbol: 'none',
                        yAxisIndex: signal.yAxisIndex ?? 0,
                        silent: true,
                        z: 0,
                    });

                    // Series 2: Upper - Lower delta (shaded area stacked on lower)
                    const deltaData: any[] = dates.map((date) => {
                        const idx = signalDateIdx.get(date);
                        if (idx === undefined) return null;
                        return upper[idx] - lower[idx];
                    });
                    series.push({
                        type: 'line',
                        name: `${signal.label} Band`,
                        data: deltaData,
                        lineStyle: {opacity: 0},
                        areaStyle: {
                            color: hexToRgba(bandColor, bandOpacity),
                        },
                        stack: `bb-${signal.id}`,
                        symbol: 'none',
                        yAxisIndex: signal.yAxisIndex ?? 0,
                        silent: true,
                        z: 0,
                    });

                    // Series 3: Middle line (SMA) — visible, styled
                    const middleData: any[] = dates.map((date) => {
                        const idx = signalDateIdx.get(date);
                        if (idx === undefined) return null;
                        return middle[idx];
                    });
                    series.push({
                        type: 'line',
                        name: signal.label,
                        data: middleData,
                        connectNulls: true,
                        smooth: false,
                        symbol: 'none',
                        yAxisIndex: signal.yAxisIndex ?? 0,
                        lineStyle: {
                            color: bandColor,
                            width: signal.lineWidth,
                            type: signal.lineType,
                        },
                        itemStyle: {color: bandColor},
                        emphasis: {focus: 'none'},
                        z: 1,
                    });
                    continue;
                }

                // ─── BAR (MACD Histogram) ───────────────────────────────────
                if (sType === 'bar') {
                    // Bar data with red/green coloring: positive = green, negative = red
                    const barData: any[] = signalSeriesData.map((val) => {
                        if (val === null || val === undefined) return val;
                        return {
                            value: val,
                            itemStyle: {
                                color: val >= 0
                                    ? (isDark ? GREEN_DARK : GREEN_LIGHT)
                                    : (isDark ? RED_DARK : RED_LIGHT),
                            },
                        };
                    });

                    series.push({
                        type: 'bar',
                        name: signal.label,
                        data: barData,
                        yAxisIndex: signal.yAxisIndex ?? 0,
                        barWidth: '60%',
                        itemStyle: {
                            color: signal.color,
                        },
                        emphasis: {focus: 'none'},
                        z: 0, // behind lines
                    });
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
                // Arrow markers are rotated to follow the line direction at that point.
                if ((signal.markerStart || signal.markerEnd) && signalSeriesData.length > 0) {
                    const markData: any[] = [];

                    // Helper: compute rotation angle (degrees) for an arrow marker
                    // based on the slope of the line at a given point index.
                    // For 'start' the arrow points backwards (entering), for 'end' it points forward.
                    const computeArrowRotation = (idx: number, isStart: boolean): number => {
                        // Find a neighboring valid point to compute slope
                        let neighborIdx = -1;
                        if (isStart) {
                            // Look right for next valid point
                            for (let j = idx + 1; j < signalSeriesData.length; j++) {
                                if (signalSeriesData[j] !== null && signalSeriesData[j] !== undefined) {
                                    neighborIdx = j; break;
                                }
                            }
                        } else {
                            // Look left for previous valid point
                            for (let j = idx - 1; j >= 0; j--) {
                                if (signalSeriesData[j] !== null && signalSeriesData[j] !== undefined) {
                                    neighborIdx = j; break;
                                }
                            }
                        }
                        if (neighborIdx < 0) return isStart ? 180 : 0;

                        const v1 = signalSeriesData[idx] as number;
                        const v2 = signalSeriesData[neighborIdx] as number;
                        // Normalize: slope in "chart space" — x is index, y is value
                        // Arrow points in the direction of travel; for start, we reverse.
                        const dx = neighborIdx - idx;
                        const dy = v2 - v1;
                        // atan2 gives angle in radians, but ECharts arrow default points right (0°)
                        // We want: positive slope → arrow tilts upward, etc.
                        // ECharts symbolRotate is clockwise from "pointing up" for arrow symbol
                        // arrow symbol default points up (90° in math coords)
                        const angleRad = Math.atan2(-dy, dx); // negative dy because y-axis is inverted in screen
                        let angleDeg = (angleRad * 180) / Math.PI;
                        // For start marker: arrow should point in the opposite direction (incoming)
                        if (isStart) angleDeg += 180;
                        // ECharts 'arrow' points up by default, so rotate from "up" reference
                        return angleDeg + 90;
                    };

                    if (signal.markerStart) {
                        for (let i = 0; i < signalSeriesData.length; i++) {
                            const v = signalSeriesData[i];
                            if (v !== null && v !== undefined) {
                                const rotate = signal.markerStart === 'arrow' ? computeArrowRotation(i, true) : 0;
                                markData.push({
                                    coord: [dates[i], v],
                                    symbol: signal.markerStart,
                                    symbolSize: Math.max(signal.lineWidth * 3, 8),
                                    symbolRotate: rotate,
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
                                const rotate = signal.markerEnd === 'arrow' ? computeArrowRotation(i, false) : 0;
                                markData.push({
                                    coord: [dates[i], v],
                                    symbol: signal.markerEnd,
                                    symbolSize: Math.max(signal.lineWidth * 3, 8),
                                    symbolRotate: rotate,
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
        // Check if any overlay signal needs the secondary Y axis (yAxisIndex = 1)
        const hasSecondaryAxis = !compact && overlaySignals.some(s => (s.yAxisIndex ?? 0) === 1 && s.data.length > 0);

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
                right: hasSecondaryAxis ? 55 : 15,
                bottom: 35,
                left: 15,
                containLabel: true,
            };

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
                {
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
                            color: isDark ? '#4b5563' : '#d1d5db',
                            type: 'dashed',
                            opacity: compact && showMiniAxis ? 0.5 : 1,
                        },
                    },
                    scale: true,
                },
                // Axis 1 — Secondary (right side, independent scale for RSI/MACD)
                // Always declared to prevent ECharts coord resolution crashes when
                // axis count changes between renders. When no series use it, it's
                // hidden with fixed bounds (min/max) so coord resolution never fails.
                {
                    type: 'value',
                    show: hasSecondaryAxis,
                    position: 'right',
                    min: hasSecondaryAxis ? undefined : 0,
                    max: hasSecondaryAxis ? undefined : 100,
                    axisLine: {show: hasSecondaryAxis, lineStyle: {color: isDark ? '#64748b' : '#9ca3af'}},
                    axisTick: {show: hasSecondaryAxis},
                    axisLabel: {
                        show: hasSecondaryAxis,
                        color: isDark ? '#94a3b8' : '#9ca3af',
                        fontSize: 10,
                        formatter: (v: number) => v.toFixed(0),
                    },
                    splitLine: {show: false},
                    scale: hasSecondaryAxis,
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
                        const axisNote = axisIdx === 1 ? ' <span style="font-size:10px;color:#94a3b8">[2nd]</span>' : '';
                        html += `<br/>${colorDot}${p.seriesName}: ${Number(value).toFixed(4)}${suffix}${axisNote}`;

                        // For band signals, also show upper/lower in the tooltip
                        const bandSignal = overlaySignals.find(
                            s => s.label === p.seriesName && (s.seriesType ?? 'line') === 'band' && s.bandData
                        );
                        if (bandSignal?.bandData) {
                            const dataIdx = bandSignal.data.findIndex(d => d.date === date);
                            if (dataIdx >= 0) {
                                html += `<br/><span style="padding-left:12px;font-size:11px;color:#94a3b8">Upper: ${bandSignal.bandData.upper[dataIdx].toFixed(4)}${suffix} · Lower: ${bandSignal.bandData.lower[dataIdx].toFixed(4)}${suffix}</span>`;
                            }
                        }
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

        // Single pass: render everything at once — no visualMap needed
        // (baseline coloring is handled by segmented series above)
        chartInstance.setOption(option, true);
        chartOptionSet = true;



        // Emit chart ready API for MeasureOverlay coordinate mapping
        emitChartReady();
    }
</script>

<div
    bind:this={chartContainer}
    class="w-full"
    style="height: {height};"
></div>

