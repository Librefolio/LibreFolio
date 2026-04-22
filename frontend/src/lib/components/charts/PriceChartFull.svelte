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
    import type {ChartType, ViewMode} from './ChartToolbar.svelte';
    import ChartToolbar from './ChartToolbar.svelte';
    import type {LineDataPoint} from './LineChart.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {buildBandSeries, buildBarSeries, buildMainSeries, COLORS, updateArrowRotations} from './lineChartHelpers';
    import {signalLabelToHtml, type SignalLabelInfo} from '$lib/charts/signalLabel';

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
    }

    const EVENT_SYMBOLS: Record<string, string> = {
        INTEREST: 'diamond',
        DIVIDEND: 'triangle',
        PRICE_ADJUSTMENT: 'rect',
        MATURITY_SETTLEMENT: 'roundRect',
        SPLIT: 'arrow',
    };

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

    $effect(() => {
        chartType = initialChartType;
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
            void displayData;
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
                    try {
                        chartInstance?.resize();
                        if (chartInstance) updateArrowRotations(chartInstance);
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

            // Global dblclick handler for edit mode — scrolls editor to clicked date
            chartInstance.getZr().on('dblclick', (params: any) => {
                if (!chartInstance) return;
                const pointInPixel = [params.offsetX, params.offsetY];
                if (chartInstance.containPixel({gridIndex: 0}, pointInPixel)) {
                    const pointInGrid = chartInstance.convertFromPixel({gridIndex: 0}, pointInPixel);
                    if (pointInGrid) {
                        const dateIdx = Math.round(pointInGrid[0]);
                        if (dateIdx >= 0 && dateIdx < displayData.length) {
                            const point = displayData[dateIdx];
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
                        if (dateIdx >= 0 && dateIdx < displayData.length) {
                            const point = displayData[dateIdx];
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
                            if (dateIdx >= 0 && dateIdx < displayData.length) {
                                const point = displayData[dateIdx];
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

            // Recompute arrow rotations when zoom changes (aspect ratio shifts)
            chartInstance.on('dataZoom', () => {
                if (chartInstance) updateArrowRotations(chartInstance);
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
                            if (dateIdx >= 0 && dateIdx < displayData.length) {
                                const point = displayData[dateIdx];
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
                                if (dateIdx >= 0 && dateIdx < displayData.length) {
                                    const point = displayData[dateIdx];
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

        const dates = displayData.map((d) => d.date);
        const useBaselineColoring = colorByBaseline;
        const baselineValue = isPercentage ? 0 : (displayData[0]?.value ?? 0);
        const staleDaysArr = displayData.map((d) => d.staleDays ?? 0);
        const mainSeriesName = mainSeriesLabel || currency || 'Value';

        const series: any[] = [];
        const values = displayData.map((d) => d.value);
        const mainSeriesList = buildMainSeries(values, staleDaysArr, baseColor, greenColor, redColor, isDark, areaFill, 2, mainSeriesName, useBaselineColoring, baselineValue, showGradient);
        series.push(...mainSeriesList);

        // Ghost series — original (unconverted) values — inserted right after main, before overlays
        const hasOriginalValues = data.some((d) => d.originalValue !== undefined);
        let ghostSeriesData: (number | null)[] = [];
        let ghostLabel = '';

        if (hasOriginalValues) {
            const origCur = data.find((d) => d.originalCurrency)?.originalCurrency ?? '';
            const origFlag = data.find((d) => d.originalCurrencyFlag)?.originalCurrencyFlag ?? '';
            ghostLabel = mainSeriesLabel ? `💱 ${mainSeriesLabel} (${origFlag} ${origCur})`.trim() : `💱 ${origCur}`;

            if (isPercentage) {
                // % mode: normalize original values to their own p0
                const firstOrigIdx = data.findIndex((d) => d.originalValue !== undefined);
                const origP0 = firstOrigIdx >= 0 ? data[firstOrigIdx].originalValue! : 1;
                ghostSeriesData = data.map((d) => {
                    if (d.originalValue === undefined) return null;
                    return origP0 !== 0 ? ((d.originalValue - origP0) / origP0) * 100 : 0;
                });
            } else {
                // Abs mode: use raw original values on shared yAxis[0]
                ghostSeriesData = data.map((d) => d.originalValue ?? null);
            }

            series.push({
                type: 'line',
                name: ghostLabel,
                data: ghostSeriesData,
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

        // Overlay signals
        if (overlaySignals && overlaySignals.length > 0) {
            for (const signal of overlaySignals) {
                if (!signal.data.length) continue;
                const sType = signal.seriesType ?? 'line';
                const signalLookup = new Map(signal.data.map((d) => [d.date, d.value]));
                const signalSeriesData: any[] = dates.map((date) => signalLookup.get(date) ?? null);

                if (sType === 'band' && signal.bandData) {
                    const bandSeries = buildBandSeries(signal, dates, isDark);
                    for (const bs of bandSeries) {
                        bs.xAxisIndex = 0;
                        series.push(bs);
                    }
                    continue;
                }
                if (sType === 'bar') {
                    const barS = buildBarSeries(signal, signalSeriesData, isDark);
                    barS.xAxisIndex = 0;
                    series.push(barS);
                    continue;
                }

                const overlaySeries: any = {
                    type: 'line',
                    name: signal.label,
                    data: signalSeriesData,
                    connectNulls: true,
                    smooth: false,
                    symbol: 'none',
                    showSymbol: false,
                    sampling: 'lttb',
                    xAxisIndex: 0,
                    yAxisIndex: signal.yAxisIndex ?? 0,
                    lineStyle: {color: signal.color, width: signal.lineWidth, type: signal.lineType, opacity: signal.opacity ?? 1},
                    itemStyle: {color: signal.color, opacity: signal.opacity ?? 1},
                    emphasis: {focus: 'none'},
                    z: signal.opacity != null && signal.opacity < 1 ? 0 : 1,
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
                                    symbolRotate: 0, // real rotation set by updateArrowRotations()
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
                                    symbolRotate: 0, // real rotation set by updateArrowRotations()
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
                type: 'line',
                name: '__baseline__',
                data: displayData.map(() => baselineValue),
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

        // Event markers — scatter series grouped by event type and asset
        if (eventMarkers && eventMarkers.length > 0) {
            const dateIndexMap = new Map(dates.map((d, i) => [d, i]));

            // Build overlay data lookup: label → (date → value) for comparison event Y positioning
            const overlayDataByLabel = new Map<string, Map<string, number>>();
            if (overlaySignals) {
                for (const signal of overlaySignals) {
                    if (!signal.data.length) continue;
                    const dateLookup = new Map(signal.data.map((d) => [d.date, d.value]));
                    overlayDataByLabel.set(signal.label, dateLookup);
                }
            }

            // Group by composite key: main asset uses type, comparison uses "label::type"
            const grouped = new Map<string, {markers: EventMarker[]; color: string; label: string}>();
            for (const m of eventMarkers) {
                const isComparison = !!m.assetLabel;
                const groupKey = isComparison ? `${m.assetLabel}::${m.type}` : m.type;
                // Main events use the chart line color; comparison events use their signal color
                const color = isComparison ? (m.signalColor ?? '#6b7280') : baseColor;
                const seriesLabel = isComparison ? `${m.assetLabel} ${m.type}` : m.type;
                if (!grouped.has(groupKey)) {
                    grouped.set(groupKey, {markers: [], color, label: seriesLabel});
                }
                grouped.get(groupKey)!.markers.push(m);
            }

            for (const [, group] of grouped) {
                const {markers, color: eventColor, label: seriesLabel} = group;
                const eventType = markers[0].type;
                const scatterData: any[] = [];
                for (const m of markers) {
                    const idx = dateIndexMap.get(m.date);
                    if (idx === undefined) continue;
                    // For comparison events, use Y from overlay data; for main events, use displayData
                    let yValue: number;
                    if (m.assetLabel) {
                        const overlayLookup = overlayDataByLabel.get(m.assetLabel);
                        yValue = overlayLookup?.get(m.date) ?? displayData[idx]?.value ?? 0;
                    } else {
                        yValue = displayData[idx]?.value ?? 0;
                    }
                    scatterData.push({
                        value: [m.date, yValue],
                        marker: m,
                    });
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
                            const m = params.data?.marker as EventMarker | undefined;
                            if (!m) return '';
                            const dot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${eventColor};margin-right:4px;"></span>`;
                            let html = `<strong>${m.date}</strong>`;
                            html += `<br/>${dot}${m.type}`;
                            if (m.value !== undefined) {
                                html += `<br/>💰 ${m.value.toFixed(4)} ${m.currency ?? ''}`;
                            }
                            if (m.notes) {
                                html += `<br/>📝 ${m.notes}`;
                            }
                            if (m.assetLabel) {
                                const sigDot = m.signalColor ? `<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${m.signalColor};margin-right:3px;"></span>` : '';
                                html += `<br/>🔗 ${sigDot}${m.assetLabel}`;
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

        // Check which overlay axes are active
        const hasSecondaryAxis = overlaySignals.some((s) => (s.yAxisIndex ?? 0) === 1 && s.data.length > 0);
        const hasTertiaryAxis = overlaySignals.some((s) => (s.yAxisIndex ?? 0) === 2 && s.data.length > 0);
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

        // Pre-compute stale lookup map for O(1) tooltip access (instead of O(n) data.find per hover)
        const staleLookup = new Map<string, number>();
        const fxStaleLookup = new Map<string, number>();
        const originalCurrencyLookup = new Map<string, string>();
        const originalValueLookup = new Map<string, number>();
        for (const d of data) {
            if (d.staleDays && d.staleDays > 0) staleLookup.set(d.date, d.staleDays);
            if (d.fxStaleDays && d.fxStaleDays > 0) fxStaleLookup.set(d.date, d.fxStaleDays);
            if (d.originalCurrency) originalCurrencyLookup.set(d.date, d.originalCurrency);
            if (d.originalValue !== undefined) originalValueLookup.set(d.date, d.originalValue);
        }

        const option: echarts.EChartsOption = {
            animation: false,
            grid: [{top: 20, right: extraAxesCount > 1 ? 115 : extraAxesCount === 1 ? 60 : 12, bottom: 20, left: 10, containLabel: true}],
            xAxis: [
                {
                    type: 'category',
                    data: dates,
                    gridIndex: 0,
                    axisLine: {lineStyle: {color: isDark ? '#475569' : '#d1d5db'}},
                    axisLabel: {color: isDark ? '#94a3b8' : '#6b7280', fontSize: 11},
                    splitLine: {show: false},
                },
            ],
            yAxis: [
                {
                    type: 'value',
                    gridIndex: 0,
                    position: 'left',
                    min: effectiveMin,
                    max: effectiveMax,
                    axisLine: {show: true, lineStyle: {color: isDark ? '#475569' : '#d1d5db'}},
                    axisTick: {show: true},
                    axisLabel: {
                        color: isDark ? '#94a3b8' : '#6b7280',
                        fontSize: 11,
                        formatter: isPercentage
                            ? (v: number) => `${v.toFixed(1)}%`
                            : (v: number) => {
                                  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}k`;
                                  if (Math.abs(v) >= 1) return v.toFixed(2);
                                  return v.toFixed(4).replace(/\.?0+$/, '');
                              },
                    },
                    splitLine: {show: showGridLines, lineStyle: {color: isDark ? '#4b5563' : '#d1d5db', type: 'dashed'}},
                    scale: !isInclude0,
                },
                {
                    type: 'value',
                    gridIndex: 0,
                    position: 'right',
                    name: hasSecondaryAxis ? 'RSI' : '',
                    nameLocation: 'start',
                    nameGap: 5,
                    nameTextStyle: {color: isDark ? '#94a3b8' : '#9ca3af', fontSize: 9, fontWeight: 'bold', align: 'center'},
                    show: hasSecondaryAxis,
                    min: hasSecondaryAxis ? undefined : 0,
                    max: hasSecondaryAxis ? undefined : 100,
                    axisLine: {show: hasSecondaryAxis, lineStyle: {color: isDark ? '#64748b' : '#9ca3af'}},
                    axisTick: {show: hasSecondaryAxis},
                    axisLabel: {show: hasSecondaryAxis, color: isDark ? '#94a3b8' : '#9ca3af', fontSize: 10, formatter: (v: number) => v.toFixed(0)},
                    splitLine: {show: false},
                    scale: hasSecondaryAxis,
                },
                {
                    type: 'value',
                    gridIndex: 0,
                    position: 'right',
                    name: hasTertiaryAxis ? 'MACD' : '',
                    nameLocation: 'start',
                    nameGap: 5,
                    nameTextStyle: {color: isDark ? '#a78bfa' : '#7c3aed', fontSize: 9, fontWeight: 'bold', align: 'center'},
                    show: hasTertiaryAxis,
                    offset: hasSecondaryAxis && hasTertiaryAxis ? 55 : 0,
                    min: hasTertiaryAxis ? undefined : 0,
                    max: hasTertiaryAxis ? undefined : 1,
                    axisLine: {show: hasTertiaryAxis, lineStyle: {color: isDark ? '#8b5cf6' : '#7c3aed'}},
                    axisTick: {show: hasTertiaryAxis},
                    axisLabel: {
                        show: hasTertiaryAxis,
                        color: isDark ? '#a78bfa' : '#7c3aed',
                        fontSize: 10,
                        formatter: (v: number) => (Math.abs(v) >= 1 ? v.toFixed(2) : v.toFixed(4).replace(/\.?0+$/, '')),
                    },
                    splitLine: {show: false},
                    scale: hasTertiaryAxis,
                },
            ],
            dataZoom: [{type: 'inside', xAxisIndex: [0], start: savedZoom?.start ?? 0, end: savedZoom?.end ?? 100, zoomOnMouseWheel: true, moveOnMouseMove: true}],
            tooltip: {
                trigger: 'axis',
                backgroundColor: isDark ? '#1e293b' : '#ffffff',
                borderColor: isDark ? '#334155' : '#e2e8f0',
                textStyle: {color: isDark ? '#e2e8f0' : '#1e293b', fontSize: 12},
                confine: true,
                position: (point: any, _params: any, _dom: any, _rect: any, size: any) => {
                    // Center tooltip horizontally on cursor, vertically pinned above finger
                    const tooltipW = size.contentSize[0];
                    const tooltipH = size.contentSize[1];
                    const viewW = size.viewSize[0];
                    let x = point[0] - tooltipW / 2;
                    // On touch devices, position well above the finger to avoid occlusion
                    // On desktop, position above cursor with adaptive gap
                    const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
                    let y: number;
                    if (isTouch) {
                        // Position above finger with large gap (80px) so it's not covered
                        const gap = 80;
                        y = point[1] - tooltipH - gap;
                        if (y < 0) y = 0;
                    } else {
                        const gap = 30;
                        y = point[1] - tooltipH - gap;
                        if (y < 0) y = 0;
                    }
                    // Clamp horizontal to chart bounds
                    if (x < 8) x = 8;
                    if (x + tooltipW > viewW - 8) x = viewW - tooltipW - 8;
                    return [x, y];
                },
                formatter: (params: any) => {
                    const items = Array.isArray(params) ? params : [params];
                    if (!items.length) return '';
                    const date = items[0].axisValue || items[0].name;
                    let html = `<strong>${date}</strong>`;
                    const bandHelperNames = new Set<string>();
                    for (const sig of overlaySignals) {
                        if ((sig.seriesType ?? 'line') === 'band') {
                            bandHelperNames.add(`${sig.label} Lower`);
                            bandHelperNames.add(`${sig.label} Band`);
                        }
                    }
                    const signalAxisMap = new Map<string, number>();
                    for (const sig of overlaySignals) {
                        signalAxisMap.set(sig.label, sig.yAxisIndex ?? 0);
                    }
                    const shownNames = new Set<string>();
                    const firstValue = displayData.length > 0 ? displayData[0].value : null;
                    // Determine if FX conversion is active (for main label suffix)
                    const conversionActive = hasOriginalValues && displayCurrencyProp && displayCurrencyFlag;
                    for (const p of items) {
                        if (p.seriesName === 'Pending' || p.seriesName === '__baseline__' || p.seriesName === '__overview__') continue;
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
                        // Show separate price stale and FX stale when applicable
                        const fxStale = fxStaleLookup.get(date);
                        if (fxStale !== undefined && fxStale > 0) {
                            // Price staleness is the staleDays minus FX contribution
                            // (staleDays = max(price_days_back, fx_days_back), but we show both separately)
                            const priceDaysBack = dataPoint; // already the combined max
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

        chartInstance.setOption(option, true);
        chartOptionSet = true;

        // Compute pixel-accurate arrow rotations after layout is established
        updateArrowRotations(chartInstance);
    }
</script>

<div class="space-y-2">
    <!-- Toolbar (hidden when parent provides external controls) -->
    {#if !hideToolbar}
        <ChartToolbar {chartType} {viewMode} onChartTypeChange={handleChartTypeChange} onViewModeChange={handleViewModeChange} disableCandlestick={true} />
    {/if}

    <!-- Unified Chart -->
    <div class="relative">
        {#if chartType === 'line'}
            <div bind:this={chartContainer} class="w-full" style="height: {chartHeight};" class:cursor-crosshair={measureMode}></div>
        {:else}
            <!-- Candlestick stub — TODO Phase 6 (Assets) -->
            <div class="flex items-center justify-center bg-gray-50 dark:bg-slate-800 rounded-lg border border-dashed border-gray-300 dark:border-slate-600" style="height: {chartHeight};">
                <p class="text-gray-400 dark:text-slate-500 text-sm">Candlestick chart — Coming soon</p>
            </div>
        {/if}
    </div>
</div>
