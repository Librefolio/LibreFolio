/**
 * chartCoreHelpers.ts — Shared logic for both LineChart (PriceChartFull) and CandlestickChart.
 *
 * Extracted to avoid duplication and ensure fixes apply uniformly.
 * Contains: overlay signal series builder, yAxis config builders, color palette,
 * and dataZoom config.
 */

import type {RenderedSignal} from '$lib/charts/signals';
import {buildBandSeries, buildBarSeries, COLORS, hexToRgba} from './lineChartHelpers';

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
            fontSize: 11,
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

/**
 * Build secondary (RSI) and tertiary (MACD) Y-axes for overlay signals.
 * Always returns 2 axes (indices 1 and 2 relative to yAxes array).
 */
export function buildSecondaryYAxes(overlaySignals: RenderedSignal[], dark: boolean, gridIndex: number = 0): {axes: any[]; hasSecondary: boolean; hasTertiary: boolean; extraAxesCount: number} {
    const hasSecondary = overlaySignals.some((s) => (s.yAxisIndex ?? 0) === 1 && s.data.length > 0);
    const hasTertiary = overlaySignals.some((s) => (s.yAxisIndex ?? 0) === 2 && s.data.length > 0);
    const extraAxesCount = (hasSecondary ? 1 : 0) + (hasTertiary ? 1 : 0);

    const axes: any[] = [
        // yAxis[1] — secondary / RSI
        {
            type: 'value',
            gridIndex,
            name: hasSecondary ? 'RSI' : '',
            nameLocation: 'start' as const,
            nameGap: 5,
            nameTextStyle: {color: dark ? '#94a3b8' : '#9ca3af', fontSize: 9, fontWeight: 'bold', align: 'center'},
            show: hasSecondary,
            position: 'right' as const,
            min: hasSecondary ? undefined : 0,
            max: hasSecondary ? undefined : 100,
            axisLine: {show: hasSecondary, lineStyle: {color: dark ? '#64748b' : '#9ca3af'}},
            axisTick: {show: hasSecondary},
            axisLabel: {
                show: hasSecondary,
                color: dark ? '#94a3b8' : '#9ca3af',
                fontSize: 10,
                formatter: (v: number) => v.toFixed(0),
            },
            splitLine: {show: false},
            scale: hasSecondary,
        },
        // yAxis[2] — tertiary / MACD
        {
            type: 'value',
            gridIndex,
            name: hasTertiary ? 'MACD' : '',
            nameLocation: 'start' as const,
            nameGap: 5,
            nameTextStyle: {color: dark ? '#a78bfa' : '#7c3aed', fontSize: 9, fontWeight: 'bold', align: 'center'},
            show: hasTertiary,
            position: 'right' as const,
            offset: hasSecondary && hasTertiary ? 55 : 0,
            min: hasTertiary ? undefined : 0,
            max: hasTertiary ? undefined : 1,
            axisLine: {show: hasTertiary, lineStyle: {color: dark ? '#8b5cf6' : '#7c3aed'}},
            axisTick: {show: hasTertiary},
            axisLabel: {
                show: hasTertiary,
                color: dark ? '#a78bfa' : '#7c3aed',
                fontSize: 10,
                formatter: (v: number) => (Math.abs(v) < 0.01 ? v.toExponential(1) : v.toFixed(3)),
            },
            splitLine: {show: false},
            scale: hasTertiary,
        },
    ];

    return {axes, hasSecondary, hasTertiary, extraAxesCount};
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
 */
export function buildDataZoom(xAxisIndices: number[]): any[] {
    return [
        {
            type: 'inside',
            xAxisIndex: xAxisIndices,
            filterMode: 'filter',
            zoomOnMouseWheel: true,
            moveOnMouseMove: true,
        },
    ];
}

// =============================================================================
// Grid right margin helper
// =============================================================================

/**
 * Compute right margin based on how many extra y-axes are visible.
 */
export function computeRightMargin(extraAxesCount: number): number {
    return extraAxesCount > 1 ? 115 : extraAxesCount === 1 ? 60 : 12;
}
