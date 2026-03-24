/**
 * lineChartHelpers — Extracted helper functions for LineChart rendering.
 *
 * Keeps the main LineChart component focused on lifecycle and wiring,
 * while reusable chart-building logic lives here.
 *
 * @module components/charts/lineChartHelpers
 */

import * as echarts from 'echarts';
import type {RenderedSignal} from '$lib/charts/signals';

// ═══════════════════════════════════════════════════════════════════════════════
// Color utilities
// ═══════════════════════════════════════════════════════════════════════════════

/** Convert hex color to rgba string with given alpha */
export function hexToRgba(hex: string, alpha: number): string {
    const h = hex.replace('#', '');
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b = parseInt(h.substring(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}

/**
 * Staleness opacity: fully opaque for fresh data, linearly fading to 0.15
 * as staleDays increases. The fade is uniform — no buckets or thresholds.
 *
 * @param staleDays   Number of days since last fresh data (0 = fresh)
 * @param maxDays     Number of stale days at which opacity reaches minimum (default 14)
 * @returns           Opacity in [0.15, 1.0]
 */
export function getStaleOpacity(staleDays?: number, maxDays = 14): number {
    if (!staleDays || staleDays <= 0) return 1.0;
    // Linear interpolation: 0 days → 1.0, maxDays+ days → 0.15
    const t = Math.min(staleDays / maxDays, 1.0);
    return 1.0 - t * 0.85; // range [1.0 … 0.15]
}

// ═══════════════════════════════════════════════════════════════════════════════
// Theme constants
// ═══════════════════════════════════════════════════════════════════════════════

export const COLORS = {
    lineLight: '#1a4031',
    lineDark: '#4ade80',
    greenLight: '#16a34a',
    greenDark: '#4ade80',
    redLight: '#ef4444',
    redDark: '#f87171',
} as const;

// ═══════════════════════════════════════════════════════════════════════════════
// Unified main series builder
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Build the main chart series, handling BOTH baseline coloring (green/red)
 * AND stale-data gradient (opacity fade) in a single unified function.
 *
 * Modes:
 *   1. baseline + stale  → 2 series (green/red) each with horizontal opacity gradient
 *   2. baseline only     → 2 series (green/red) with solid colors
 *   3. stale only        → 1 series with horizontal opacity gradient
 *   4. neither           → 1 simple solid-color series
 *
 * By unifying these effects we avoid the old problem where activating baseline
 * coloring disabled stale gradient and vice versa. The series always share the
 * same `seriesName` so the tooltip deduplicates them into a single entry.
 *
 * @param values       Array of Y values aligned to the date axis
 * @param staleDays    Array of staleDays per point (0 = fresh)
 * @param baseColor    Hex color for the line (used when baseline coloring is off)
 * @param greenColor   Hex color for above-baseline segments
 * @param redColor     Hex color for below-baseline segments
 * @param isDark       Whether dark mode is active
 * @param areaFill     Whether to add gradient area fill
 * @param lineWidth    Line width in pixels
 * @param seriesName   Shared series name (for tooltip grouping / dedup)
 * @param useBaseline  Whether to split into green/red by baseline
 * @param baseline     The threshold value (0 for %, p0 for abs)
 * @param useStale     Whether to apply stale-data opacity gradient
 * @returns Array of ECharts series configs (1 or 2 depending on baseline flag)
 */
/**
 * Segment descriptor: a contiguous run of points sharing the same visual
 * properties (baseline color + stale opacity bucket).
 */
interface Segment {
    /** Index of the first point in this segment */
    start: number;
    /** Index of the last point (inclusive) */
    end: number;
    /** Which color to use (base / green / red) */
    color: string;
    /** Opacity multiplier (1.0 = fresh, 0.5 = stale sentinel) */
    opacity: number;
    /** True if this is a stale segment that needs a horizontal gradient */
    isStale: boolean;
    /** staleDays at start of segment (for gradient computation) */
    staleStart: number;
    /** staleDays at end of segment (for gradient computation) */
    staleEnd: number;
}

/**
 * Round opacity for segment grouping — fresh (1.0) vs stale (anything < 1.0).
 * We keep ALL fresh points as one group and ALL stale points as another,
 * then use a horizontal gradient within the stale segment for smooth fading.
 * This avoids N micro-segments that cause visible stepping.
 */
function roundOpacity(op: number): number {
    // Binary: 1.0 if fresh, 0.5 as sentinel for "stale" (actual opacity applied via gradient)
    return op >= 1.0 ? 1.0 : 0.5;
}

export function buildMainSeries(
    values: number[],
    staleDays: number[],
    baseColor: string,
    greenColor: string,
    redColor: string,
    isDark: boolean,
    areaFill: boolean,
    lineWidth: number,
    seriesName: string,
    useBaseline: boolean,
    baseline: number,
    useStale: boolean,
): any[] {
    if (values.length === 0) return [];

    const n = values.length;

    // ── Single-point: render as circle marker (no line segment possible) ──
    if (n === 1) {
        const color = useBaseline
            ? (values[0] >= baseline ? greenColor : redColor)
            : baseColor;
        return [{
            name: seriesName,
            type: 'line',
            data: [values[0]],
            showSymbol: true,
            symbol: 'circle',
            symbolSize: 8,
            itemStyle: { color },
            lineStyle: { width: 0 },
            areaStyle: undefined,
        }];
    }

    const hasStale = useStale && staleDays.some(d => d > 0);

    // ── Step 1: Assign per-point color and opacity ──
    // Each point gets a "color key" (which color) and an "opacity bucket".
    // We then merge consecutive points with the same (color, opacity) into segments.
    const pointColors: string[] = new Array(n);
    const pointOpacities: number[] = new Array(n);

    for (let i = 0; i < n; i++) {
        // Determine color
        if (useBaseline) {
            pointColors[i] = values[i] >= baseline ? greenColor : redColor;
        } else {
            pointColors[i] = baseColor;
        }
        // Determine opacity — linear fade, rounded for segment grouping
        pointOpacities[i] = hasStale ? roundOpacity(getStaleOpacity(staleDays[i])) : 1.0;
    }

    // ── Step 2: Build contiguous segments ──
    const segments: Segment[] = [];
    let segStart = 0;
    for (let i = 1; i <= n; i++) {
        const sameGroup = i < n
            && pointColors[i] === pointColors[segStart]
            && pointOpacities[i] === pointOpacities[segStart];
        if (!sameGroup) {
            const isStale = pointOpacities[segStart] < 1.0;
            segments.push({
                start: segStart,
                end: i - 1,
                color: pointColors[segStart],
                opacity: pointOpacities[segStart],
                isStale,
                staleStart: staleDays[segStart] ?? 0,
                staleEnd: staleDays[i - 1] ?? 0,
            });
            segStart = i;
        }
    }

    // ── Step 3: Create one ECharts series per segment ──
    // Each segment's data array has null everywhere except in its range.
    // Adjacent segments share a 1-point overlap so the line is visually continuous.
    //
    // Bridge strategy (direction depends on transition type):
    //   COLOR transition → BACKWARD bridge: new segment extends 1 point back into
    //     the previous segment's territory. This ensures the line ARRIVING at a
    //     point carries that point's baseline color (destination-based coloring).
    //   OPACITY-ONLY transition (same color) → FORWARD bridge: old segment extends
    //     1 point forward into the next segment's territory. This prevents a
    //     visible "flash" when transitioning from fresh to stale data.
    const result: any[] = [];

    for (let sIdx = 0; sIdx < segments.length; sIdx++) {
        const seg = segments[sIdx];
        const segData: (number | null)[] = new Array(n).fill(null);

        const prevSeg = sIdx > 0 ? segments[sIdx - 1] : null;
        const nextSeg = sIdx < segments.length - 1 ? segments[sIdx + 1] : null;

        // Start: extend backward if previous segment had a DIFFERENT color
        // (so the line arriving at this segment's first point carries this color)
        const colorChangeAtStart = prevSeg != null && prevSeg.color !== seg.color;
        const drawStart = colorChangeAtStart
            ? Math.max(0, seg.start - 1)
            : seg.start;

        // End: extend forward ONLY if next segment has the SAME color
        // (opacity-only boundary → fresh segment paints the bridge at full opacity).
        // At color boundaries we do NOT extend forward — the next segment will
        // bridge backward instead.
        const colorChangeAtEnd = nextSeg != null && nextSeg.color !== seg.color;
        const drawEnd = (!colorChangeAtEnd && nextSeg)
            ? Math.min(n - 1, seg.end + 1)
            : seg.end;

        for (let i = drawStart; i <= drawEnd; i++) {
            segData[i] = values[i];
        }

        // For stale segments, compute a smooth horizontal gradient
        // from the opacity at the first stale point to the opacity at the last.
        // For fresh segments, use a solid color at full opacity.
        let lineColor: any;
        let itemColor: string;
        if (seg.isStale) {
            const opStart = getStaleOpacity(seg.staleStart);
            const opEnd = getStaleOpacity(seg.staleEnd);
            lineColor = new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                {offset: 0, color: hexToRgba(seg.color, opStart)},
                {offset: 1, color: hexToRgba(seg.color, opEnd)},
            ]);
            itemColor = hexToRgba(seg.color, (opStart + opEnd) / 2);
        } else {
            const solidColor = hexToRgba(seg.color, seg.opacity);
            lineColor = solidColor;
            itemColor = solidColor;
        }

        const s: any = {
            type: 'line',
            name: seriesName,
            data: segData,
            smooth: false,
            symbol: 'none',
            showSymbol: false,
            sampling: 'lttb',
            yAxisIndex: 0,
            lineStyle: {width: lineWidth, color: lineColor},
            itemStyle: {color: itemColor},
            // 'none' so hovering any segment doesn't dim the others —
            // all segments are the "same" signal visually.
            emphasis: {focus: 'none'},
            z: 2,
        };

        if (areaFill) {
            const avgOp = seg.isStale
                ? (getStaleOpacity(seg.staleStart) + getStaleOpacity(seg.staleEnd)) / 2
                : seg.opacity;
            const areaTopOp = (isDark ? 0.15 : 0.10) * avgOp;
            const areaBotOp = (isDark ? 0.03 : 0.02) * avgOp;
            if (seg.isStale) {
                // Horizontal gradient for stale area fill too
                const opStart = getStaleOpacity(seg.staleStart);
                const opEnd = getStaleOpacity(seg.staleEnd);
                s.areaStyle = {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        {offset: 0, color: hexToRgba(seg.color, (isDark ? 0.15 : 0.10) * opStart)},
                        {offset: 1, color: hexToRgba(seg.color, (isDark ? 0.03 : 0.02) * opEnd)},
                    ]),
                };
            } else {
                s.areaStyle = {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {offset: 0, color: hexToRgba(seg.color, areaTopOp)},
                        {offset: 1, color: hexToRgba(seg.color, areaBotOp)},
                    ]),
                };
            }
        }

        result.push(s);
    }

    return result;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Overlay signal series builders
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Build an ECharts band series (Bollinger-style confidence band) from a
 * RenderedSignal with bandData. Returns 3 series: lower (invisible stack base),
 * delta (shaded area), and middle (visible line).
 *
 * Uses explicit upper + lower lines instead of stacking to avoid ECharts
 * rendering artifacts when lower values go negative (common in % mode).
 */
export function buildBandSeries(
    signal: RenderedSignal,
    dates: string[],
    isDark: boolean,
): any[] {
    if (!signal.bandData) return [];
    const {upper, middle, lower} = signal.bandData;
    const bandColor = signal.color;
    const bandOpacity = isDark ? 0.18 : 0.12;

    const signalDateIdx = new Map(signal.data.map((d, idx) => [d.date, idx]));


    const lowerData: any[] = dates.map((date) => {
        const idx = signalDateIdx.get(date);
        return idx === undefined ? null : lower[idx];
    });

    const middleData: any[] = dates.map((date) => {
        const idx = signalDateIdx.get(date);
        return idx === undefined ? null : middle[idx];
    });

    // Delta for stack: upper - lower (always positive since upper > lower by construction)
    const deltaData: any[] = dates.map((date) => {
        const idx = signalDateIdx.get(date);
        if (idx === undefined) return null;
        const u = upper[idx];
        const l = lower[idx];
        return (u !== undefined && l !== undefined) ? u - l : null;
    });

    return [
        // Stack base: lower values (invisible line)
        {
            type: 'line',
            name: `${signal.label} Lower`,
            data: lowerData,
            lineStyle: {opacity: 0},
            itemStyle: {color: 'transparent'},
            stack: `bb-${signal.id}`,
            stackStrategy: 'all',
            symbol: 'none',
            yAxisIndex: signal.yAxisIndex ?? 0,
            silent: true,
            z: 0,
            tooltip: {show: false},
        },
        // Stacked delta: renders the shaded area from lower to upper
        {
            type: 'line',
            name: `${signal.label} Band`,
            data: deltaData,
            lineStyle: {opacity: 0},
            areaStyle: {color: hexToRgba(bandColor, bandOpacity)},
            stack: `bb-${signal.id}`,
            stackStrategy: 'all',
            symbol: 'none',
            yAxisIndex: signal.yAxisIndex ?? 0,
            silent: true,
            z: 0,
            tooltip: {show: false},
        },
        // Middle line (visible)
        {
            type: 'line',
            name: signal.label,
            data: middleData,
            connectNulls: true,
            smooth: false,
            symbol: 'none',
            yAxisIndex: signal.yAxisIndex ?? 0,
            lineStyle: {color: bandColor, width: signal.lineWidth, type: signal.lineType},
            itemStyle: {color: bandColor},
            emphasis: {focus: 'none'},
            z: 1,
        },
    ];
}

/**
 * Build an ECharts bar series (MACD histogram style) with red/green per-bar
 * coloring based on value sign.
 */
export function buildBarSeries(
    signal: RenderedSignal,
    signalSeriesData: any[],
    isDark: boolean,
): any {
    const barData: any[] = signalSeriesData.map((val) => {
        if (val === null || val === undefined) return val;
        return {
            value: val,
            itemStyle: {
                color: val >= 0
                    ? (isDark ? COLORS.greenDark : COLORS.greenLight)
                    : (isDark ? COLORS.redDark : COLORS.redLight),
            },
        };
    });

    return {
        type: 'bar',
        name: signal.label,
        data: barData,
        yAxisIndex: signal.yAxisIndex ?? 0,
        barWidth: '60%',
        itemStyle: {color: signal.color},
        emphasis: {focus: 'none'},
        z: 0,
    };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Arrow marker rotation
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * After `chart.setOption()`, scan all series for arrow markPoints
 * and recompute their `symbolRotate` using pixel-space coordinates.
 *
 * Each arrow marker is processed independently using its **local slope**:
 * scan backward for the nearest non-null neighbor, fall back to forward.
 * The arrow points AWAY from the neighbor (incoming for start, outgoing for end).
 *
 * Must be called:
 *  - After every `chart.setOption()`
 *  - On `dataZoom` events (zoom changes pixel aspect ratio)
 *  - On `resize` events
 */
export function updateArrowRotations(chart: echarts.ECharts): void {
    if (!chart || chart.isDisposed?.()) return;

    const option = chart.getOption() as any;
    if (!option?.series) return;

    const dates: string[] = Array.isArray(option.xAxis) ? option.xAxis[0]?.data ?? [] : [];
    let needsUpdate = false;

    for (const series of option.series) {
        if (!series.markPoint?.data?.length) continue;

        const seriesData: any[] = series.data || [];

        for (const marker of series.markPoint.data) {
            if (marker.symbol !== 'arrow' || !marker.coord) continue;

            // Resolve the marker's index in the category axis
            const markerIdx = typeof marker.coord[0] === 'number'
                ? marker.coord[0]
                : dates.indexOf(marker.coord[0]);
            if (markerIdx < 0) continue;

            // Find nearest non-null neighbor: backward first, forward fallback.
            // - END markers (last non-null): backward finds data → arrow points forward
            // - START markers (first non-null): backward finds nothing → forward → arrow points backward
            let neighborIdx = -1;
            for (let j = markerIdx - 1; j >= Math.max(0, markerIdx - 20); j--) {
                if (seriesData[j] !== null && seriesData[j] !== undefined) {
                    neighborIdx = j;
                    break;
                }
            }
            if (neighborIdx < 0) {
                for (let j = markerIdx + 1; j < Math.min(seriesData.length, markerIdx + 21); j++) {
                    if (seriesData[j] !== null && seriesData[j] !== undefined) {
                        neighborIdx = j;
                        break;
                    }
                }
            }
            if (neighborIdx < 0) continue;

            try {
                const neighborCoord = [dates[neighborIdx], seriesData[neighborIdx]];
                const pMarker = chart.convertToPixel({gridIndex: 0}, marker.coord) as unknown as number[];
                const pNeighbor = chart.convertToPixel({gridIndex: 0}, neighborCoord) as unknown as number[];
                if (!pMarker || !pNeighbor) continue;

                // forwardDeg = math angle from marker toward neighbor (0° = right, CCW)
                const dx = pNeighbor[0] - pMarker[0];
                const dy = pNeighbor[1] - pMarker[1];
                const towardNeighborDeg = (Math.atan2(-dy, dx) * 180) / Math.PI;

                // Arrow points AWAY from neighbor:
                //   math: towardNeighborDeg + 180°
                //   ECharts (0° = up, anti-clockwise): math_angle - 90°
                //   Combined: towardNeighborDeg + 180 - 90 = towardNeighborDeg + 90
                marker.symbolRotate = towardNeighborDeg + 90;
                needsUpdate = true;
            } catch (_) {
                // convertToPixel can fail if chart not fully laid out
            }
        }
    }

    if (needsUpdate) {
        chart.setOption({series: option.series}, false);
    }
}

