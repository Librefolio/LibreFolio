/**
 * chartCoreHelpers.ts — Shared logic for both LineChart (PriceChartFull) and CandlestickChart.
 *
 * Extracted to avoid duplication and ensure fixes apply uniformly.
 * Contains: overlay signal series builder, yAxis config builders, color palette,
 * and dataZoom config.
 */

import type {RenderedSignal} from '$lib/charts/signals';
import type {ECharts} from 'echarts';
import {buildBandSeries, buildBarSeries, buildSignalReferencePrimitives, COLORS, hexToRgba} from './lineChartHelpers';

// =============================================================================
// Types
// =============================================================================

export interface ChartColors {
    green: string;
    red: string;
    axis: string;
    label: string;
    gridLine: string;
}

export interface YAxisConfig {
    mode: 'auto' | 'include0' | 'custom';
    min?: number;
    max?: number;
    isPercentage?: boolean;
}

// =============================================================================
// Color palette for dark/light mode
// =============================================================================

export function getChartColors(dark: boolean): ChartColors {
    return {
        green: dark ? COLORS.greenDark : COLORS.greenLight,
        red: dark ? COLORS.redDark : COLORS.redLight,
        axis: dark ? '#475569' : '#d1d5db',
        label: dark ? '#94a3b8' : '#6b7280',
        gridLine: dark ? '#4b5563' : '#d1d5db',
    };
}

// =============================================================================
// Y-axis builders
// =============================================================================

/**
 * Build the primary price Y-axis config.
 */
export function buildPriceYAxis(config: YAxisConfig, colors: ChartColors, opts: {gridIndex?: number; showGridLines?: boolean} = {}): any {
    const {mode, min, max, isPercentage} = config;
    const {gridIndex = 0, showGridLines = true} = opts;

    const isCustom = mode === 'custom';
    const isInclude0 = mode === 'include0';
    let effectiveMin = isCustom && min !== undefined ? min : undefined;
    let effectiveMax = isCustom && max !== undefined ? max : undefined;
    if (effectiveMin !== undefined && effectiveMax !== undefined && effectiveMin > effectiveMax) {
        [effectiveMin, effectiveMax] = [effectiveMax, effectiveMin];
    }

    return {
        type: 'value',
        gridIndex,
        position: 'left',
        min: effectiveMin,
        max: effectiveMax,
        scale: !isInclude0,
        axisLine: {show: true, lineStyle: {color: colors.axis}},
        axisTick: {show: true},
        axisLabel: {
            color: colors.label,
            fontSize: 14,
            formatter: isPercentage
                ? (v: number) => `${v.toFixed(1)}%`
                : (v: number) => {
                      if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}k`;
                      if (Math.abs(v) >= 1) return v.toFixed(2);
                      return v.toFixed(4).replace(/\.?0+$/, '');
                  },
        },
        splitLine: {
            show: showGridLines,
            lineStyle: {color: colors.gridLine, type: 'dashed' as const},
        },
    };
}

/** Assign stable ECharts indexes to canonical independent axes. */
export function assignOverlaySignalAxes(overlaySignals: RenderedSignal[]): RenderedSignal[] {
    const axisIndexes = new Map<string, number>();
    const usedIndexes = new Set<number>([0]);

    for (const signal of overlaySignals) {
        if (!signal.axisKey && (signal.yAxisIndex ?? 0) > 0) {
            const index = signal.yAxisIndex!;
            axisIndexes.set(`legacy:${index}`, index);
            usedIndexes.add(index);
        }
    }

    function nextIndex(): number {
        let index = 1;
        while (usedIndexes.has(index)) index++;
        usedIndexes.add(index);
        return index;
    }

    return overlaySignals.map((signal) => {
        if (signal.axisRole === 'price') return {...signal, yAxisIndex: 0};

        if (signal.axisKey && (signal.axisRole === 'independent' || signal.axisRole === 'volume')) {
            const key = `${signal.axisRole}:${signal.axisKey}`;
            let index = axisIndexes.get(key);
            if (index === undefined) {
                index = nextIndex();
                axisIndexes.set(key, index);
            }
            return {...signal, yAxisIndex: index};
        }

        return signal;
    });
}

/** Build all active non-price Y-axes from canonical axis metadata. */
export function buildSecondaryYAxes(overlaySignals: RenderedSignal[], dark: boolean, gridIndex: number = 0, showAxes: boolean = true): {axes: any[]; hasSecondary: boolean; hasTertiary: boolean; extraAxesCount: number; nextAxisIndex: number} {
    const signalByIndex = new Map<number, RenderedSignal>();
    for (const signal of overlaySignals) {
        const index = signal.yAxisIndex ?? 0;
        if (index > 0 && signal.data.length > 0 && !signalByIndex.has(index)) {
            signalByIndex.set(index, signal);
        }
    }

    const activeIndexes = [...signalByIndex.keys()].sort((left, right) => left - right);
    const maxIndex = activeIndexes.at(-1) ?? 0;
    const axes: any[] = [];

    for (let index = 1; index <= maxIndex; index++) {
        const signal = signalByIndex.get(index);
        const active = signal !== undefined;
        const color = signal?.color ?? (dark ? '#64748b' : '#9ca3af');
        const label = signal?.axisLabel ?? (index === 1 ? 'RSI' : index === 2 ? 'MACD' : `AXIS ${index}`);

        axes.push({
            type: 'value',
            gridIndex,
            name: active && showAxes ? label : '',
            nameLocation: 'start' as const,
            nameGap: 5,
            nameTextStyle: {
                color,
                fontSize: 9,
                fontWeight: 'bold',
                align: 'center',
            },
            show: active && showAxes,
            position: 'right' as const,
            offset: (index - 1) * 55,
            min: active ? signal.axisMinimum : 0,
            max: active ? signal.axisMaximum : 1,
            axisLine: {
                show: active && showAxes,
                lineStyle: {color},
            },
            axisTick: {show: active && showAxes},
            axisLabel: {
                show: active && showAxes,
                color,
                fontSize: 10,
                formatter: (value: number) => {
                    if (Math.abs(value) >= 100) return value.toFixed(0);
                    if (Math.abs(value) >= 1) return value.toFixed(2);
                    return value.toFixed(4).replace(/\.?0+$/, '');
                },
            },
            splitLine: {show: false},
            scale: signal?.axisMinimum === undefined && signal?.axisMaximum === undefined,
        });
    }

    return {
        axes,
        hasSecondary: signalByIndex.has(1),
        hasTertiary: signalByIndex.has(2),
        extraAxesCount: activeIndexes.length,
        nextAxisIndex: axes.length + 1,
    };
}

// =============================================================================
// Overlay signal series builder
// =============================================================================

/**
 * Build ECharts series for all overlay signals.
 * Returns an array of series configs ready to push into the main series array.
 *
 * @param overlaySignals - Array of rendered signals
 * @param dates - Array of date strings (x-axis categories)
 * @param dark - Whether dark mode is active
 * @param xAxisIndex - Which x-axis to bindto (default: 0)
 */
export function buildOverlaySignalSeries(overlaySignals: RenderedSignal[], dates: string[], dark: boolean, xAxisIndex: number = 0): any[] {
    const series: any[] = [];

    if (!overlaySignals || overlaySignals.length === 0) return series;

    for (const signal of overlaySignals) {
        if (!signal.data.length) continue;

        const sType = signal.seriesType ?? 'line';
        const signalLookup = new Map(signal.data.map((d) => [d.date, d.value]));
        const signalSeriesData: any[] = dates.map((date) => signalLookup.get(date) ?? null);

        if (sType === 'band' && signal.bandData) {
            const bandSeries = buildBandSeries(signal, dates, dark);
            for (const bs of bandSeries) {
                bs.xAxisIndex = xAxisIndex;
            }
            series.push(...bandSeries);
            continue;
        }

        if (sType === 'bar') {
            const barS = buildBarSeries(signal, signalSeriesData, dark);
            barS.xAxisIndex = xAxisIndex;
            series.push(barS);
            continue;
        }

        // LINE series
        const overlaySeries: any = {
            type: 'line',
            name: signal.label,
            data: signalSeriesData,
            connectNulls: true,
            smooth: false,
            symbol: 'none',
            showSymbol: false,
            sampling: 'lttb',
            xAxisIndex,
            yAxisIndex: signal.yAxisIndex ?? 0,
            lineStyle: {color: signal.color, width: signal.lineWidth, type: signal.lineType, opacity: signal.opacity ?? 1},
            itemStyle: {color: signal.color, opacity: signal.opacity ?? 1},
            emphasis: {focus: 'none'},
            z: signal.opacity != null && signal.opacity < 1 ? 0 : 1,
            ...buildSignalReferencePrimitives(signal, dark),
        };

        // Marker points (start/end arrows)
        if ((signal.markerStart || signal.markerEnd) && signalSeriesData.length > 0) {
            const markData: any[] = [];

            if (signal.markerStart) {
                for (let i = 0; i < signalSeriesData.length; i++) {
                    if (signalSeriesData[i] !== null && signalSeriesData[i] !== undefined) {
                        markData.push({
                            coord: [dates[i], signalSeriesData[i]],
                            symbol: signal.markerStart,
                            symbolSize: Math.max(signal.lineWidth * 3, 8),
                            symbolRotate: 0,
                            itemStyle: {color: signal.color},
                        });
                        break;
                    }
                }
            }
            if (signal.markerEnd) {
                for (let i = signalSeriesData.length - 1; i >= 0; i--) {
                    if (signalSeriesData[i] !== null && signalSeriesData[i] !== undefined) {
                        markData.push({
                            coord: [dates[i], signalSeriesData[i]],
                            symbol: signal.markerEnd,
                            symbolSize: Math.max(signal.lineWidth * 3, 8),
                            symbolRotate: 0,
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

    return series;
}

// =============================================================================
// DataZoom config
// =============================================================================

/**
 * Build inside-type dataZoom config for synchronised zoom across multiple x-axes.
 *
 * moveOnMouseMove drives DESKTOP mouse-drag pan only — this is safe unconditionally
 * (genuine mouse pointer events never compete with native page scroll, since desktop
 * page-scroll uses the wheel, handled independently via zoomOnMouseWheel above).
 *
 * Touch-drag pan is intentionally NOT enabled here (moveOnMouseMove also nominally
 * covers touch, but per zrender's HandlerProxy.js, touch-sourced pointer movement is
 * unreliable for RoamController-driven pan on modern mobile browsers — verified while
 * building the treemap's zoom guard, see echartsTreemapZoomGuard.ts's doc comment).
 * Mobile pan is instead provided by attachDataZoomTouchPan()'s manual two-finger
 * bridge (one finger is ALWAYS reserved for native page scroll, never intercepted —
 * same "two fingers, not one" rationale as the treemap's touch-pan bridge).
 */
export const INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG = {
    zoomOnMouseWheel: true,
    moveOnMouseMove: true,
    moveOnMouseWheel: false,
    preventDefaultMouseMove: false,
};

export function buildDataZoom(xAxisIndices: number[]): any[] {
    return [
        {
            type: 'inside',
            xAxisIndex: xAxisIndices,
            filterMode: 'filter',
            ...INSIDE_DATA_ZOOM_SCROLL_SAFE_CONFIG,
        },
    ];
}

/**
 * Read the current dataZoom window (start/end percentages, 0-100) from a chart's
 * first dataZoom component. Returns null if the chart has no dataZoom configured yet
 * (e.g. called before the first `setOption`).
 *
 * Shared by echartsDataZoomTouchPan.ts (touch-drag pan) and any cross-chart dataZoom
 * sync bridge (e.g. linked time-series chart ↔ timeline chart zoom/pan sync) so both
 * read/compare the SAME percentage-based window representation.
 */
export function getChartZoomWindow(chart: ECharts): {start: number; end: number} | null {
    const opt = chart.getOption() as {dataZoom?: Array<{start?: number; end?: number}>};
    const dz = opt?.dataZoom?.[0];
    if (!dz) return null;
    return {start: dz.start ?? 0, end: dz.end ?? 100};
}

// =============================================================================
// Grid right margin helper
// =============================================================================

/**
 * Compute right margin based on how many extra y-axes are visible.
 */
export function computeRightMargin(extraAxesCount: number): number {
    return extraAxesCount > 0 ? 60 + (extraAxesCount - 1) * 55 : 12;
}
