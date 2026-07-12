/**
 * RsiSignal — Relative Strength Index.
 *
 * Financial meaning:
 *   Measures overbought/oversold conditions. RSI oscillates 0-100:
 *     RSI > 70 → overbought, RSI < 30 → oversold.
 *
 * Signal processing equivalent:
 *   Duty-cycle / saturation indicator using Wilder's SMMA (α = 1/N).
 *   RSI = 100 − 100/(1 + RS) where RS = avgGain / avgLoss.
 *
 * Computed iteratively in O(N).
 * Y-axis: secondary (left, independent scale 0-100) → yAxisIndex = 1
 *
 * See: docs/financial-theory/technical-analysis/indicators/rsi.en.md
 */

import {ChartSignal, type RenderedSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class RsiSignal extends ChartSignal {
    static override signalType = 'rsi';
    static override displayName = 'RSI';
    static override icon = '📊';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'indicator';
    static yAxisIndex = 1;
    static docsPath = 'financial-theory/technical-analysis/indicators/rsi/';

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'period',
            label: 'Period',
            type: 'number',
            default: 14,
            min: 2,
            max: 200,
            step: 1,
            suffix: 'days',
            tooltip: 'chartSettings.tooltips.period',
        },
        {
            key: 'overbought',
            label: 'Overbought',
            type: 'number',
            default: 70,
            min: 50,
            max: 100,
            step: 1,
            suffix: '',
            tooltip: 'chartSettings.tooltips.overbought',
        },
        {
            key: 'oversold',
            label: 'Oversold',
            type: 'number',
            default: 30,
            min: 0,
            max: 50,
            step: 1,
            suffix: '',
            tooltip: 'chartSettings.tooltips.oversold',
        },
    ];

    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        if (baseData.length < 2) return [];

        const period = Math.max(2, Math.round(Number(this.params.period ?? 14)));
        const alpha = 1 / period;

        const result: LineDataPoint[] = [];
        let avgGain = 0;
        let avgLoss = 0;

        for (let i = 0; i < baseData.length; i++) {
            if (i === 0) {
                result.push({date: baseData[i].date, value: 50});
                continue;
            }

            const delta = baseData[i].value - baseData[i - 1].value;
            const gain = delta > 0 ? delta : 0;
            const loss = delta < 0 ? -delta : 0;

            if (i <= period) {
                avgGain += gain / period;
                avgLoss += loss / period;
                if (i < period) {
                    result.push({date: baseData[i].date, value: 50});
                    continue;
                }
            } else {
                avgGain = alpha * gain + (1 - alpha) * avgGain;
                avgLoss = alpha * loss + (1 - alpha) * avgLoss;
            }

            const rsi = avgLoss === 0 ? 100 : avgGain === 0 ? 0 : (100 * avgGain) / (avgGain + avgLoss);
            result.push({date: baseData[i].date, value: rsi});
        }

        return result;
    }

    getLabel(): string {
        return `RSI(${this.params.period ?? 14})`;
    }

    override renderMulti(baseData: LineDataPoint[], _viewMode: 'absolute' | 'percentage'): RenderedSignal[] {
        const allPoints = this.computePoints(baseData);
        if (allPoints.length === 0) return [];

        const overbought = Number(this.params.overbought ?? 70);
        const oversold = Number(this.params.oversold ?? 30);

        type Zone = 'oversold' | 'neutral' | 'overbought';
        const getZone = (v: number): Zone => {
            if (v < oversold) return 'oversold';
            if (v > overbought) return 'overbought';
            return 'neutral';
        };

        function zoneStyle(zone: Zone, baseWidth: number): {lineType: 'solid' | 'dashed'; lineWidth: number} {
            if (zone === 'neutral') return {lineType: 'dashed', lineWidth: baseWidth};
            return {lineType: 'solid', lineWidth: baseWidth + 1};
        }

        interface Segment {
            zone: Zone;
            startIdx: number;
            endIdx: number;
        }

        const segments: Segment[] = [];
        let currentZone = getZone(allPoints[0].value);
        let segStart = 0;

        for (let i = 1; i <= allPoints.length; i++) {
            const z: Zone | null = i < allPoints.length ? getZone(allPoints[i].value) : null;
            if (z !== currentZone) {
                segments.push({zone: currentZone, startIdx: segStart, endIdx: i - 1});
                if (z !== null) {
                    currentZone = z;
                    segStart = i - 1; // overlap: include junction point in next segment
                }
            }
        }

        // Merge micro-segments to bound the series count (same rationale as the price
        // line's baseline-color segmentation, see buildMainSeries): a sufficiently
        // volatile+long series can cross the overbought/oversold thresholds hundreds of
        // times, and buildOverlaySignalSeries() turns EACH segment into its own
        // full-length ECharts series — a series count in the hundreds/thousands can make
        // a single setOption() call take seconds. Segments shorter than a few points are
        // visually meaningless anyway, so merge them into a neighbor — recomputing the
        // merged zone as a point-weighted majority vote (not just "first segment wins")
        // so a long run of one zone can't be silently mis-colored by a handful of brief
        // crossings merged into it.
        const MAX_RSI_SEGMENTS = 100;
        const mergeShortZoneSegments = (minPoints: number): Segment[] => {
            if (minPoints <= 1) return segments;
            const merged: Segment[] = [];
            let zoneVotes: Map<Zone, number> | null = null;

            for (const seg of segments) {
                const segLength = seg.endIdx - seg.startIdx + 1;
                const last = merged[merged.length - 1];
                if (last && segLength < minPoints) {
                    if (!zoneVotes) {
                        zoneVotes = new Map([[last.zone, last.endIdx - last.startIdx + 1]]);
                    }
                    zoneVotes.set(seg.zone, (zoneVotes.get(seg.zone) ?? 0) + segLength);

                    let bestZone = last.zone;
                    let bestCount = -1;
                    for (const [zone, count] of zoneVotes) {
                        if (count > bestCount) {
                            bestCount = count;
                            bestZone = zone;
                        }
                    }

                    last.endIdx = seg.endIdx;
                    last.zone = bestZone;
                } else {
                    merged.push({...seg});
                    zoneVotes = null;
                }
            }
            return merged;
        };

        let effectiveSegments = segments;
        for (let minPoints = 2; effectiveSegments.length > MAX_RSI_SEGMENTS && minPoints <= allPoints.length; minPoints++) {
            effectiveSegments = mergeShortZoneSegments(minPoints);
        }

        const baseWidth = this.style.lineWidth;
        const color = this.style.color;
        const yAxis = (this.constructor as typeof ChartSignal).yAxisIndex;

        return effectiveSegments
            .map((seg): RenderedSignal | null => {
                const segData = allPoints.slice(seg.startIdx, seg.endIdx + 1);
                if (segData.length === 0) return null;
                const s = zoneStyle(seg.zone, baseWidth);
                return {
                    id: `${this.id}-${seg.zone}-${seg.startIdx}`,
                    label: seg.startIdx === 0 ? this.getLabel() : '',
                    data: segData,
                    color,
                    lineWidth: s.lineWidth,
                    lineType: s.lineType,
                    markerStart: seg.startIdx === 0 ? this.style.markerStart : null,
                    markerEnd: seg.endIdx === allPoints.length - 1 ? this.style.markerEnd : null,
                    yAxisIndex: yAxis,
                } satisfies RenderedSignal;
            })
            .filter((s): s is RenderedSignal => s !== null);
    }
}
