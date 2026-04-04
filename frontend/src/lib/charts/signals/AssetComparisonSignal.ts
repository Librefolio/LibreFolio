/**
 * AssetComparisonSignal — Overlay signal sourced from another asset's price data.
 *
 * The parent component pre-fetches data and injects it via `params._resolvedData`
 * before calling `computePoints()`. The '_' prefix ensures `_resolvedData` and
 * `_assetDisplayName` are excluded from `toConfig()` serialization.
 *
 * Complementary to FxPairSignal: allows overlaying asset prices on any chart
 * (FX or Asset), enabling cross-asset comparison.
 *
 * No maxInstances limit — user can overlay multiple assets on the same chart.
 */

import {ChartSignal, type RenderedSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class AssetComparisonSignal extends ChartSignal {
    static override signalType = 'asset-comparison';
    static override displayName = 'Asset';
    static override icon = '📊';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'comparison';

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'assetId',
            label: 'Asset',
            type: 'select',
            default: '',
            dynamicOptionsKey: 'configuredAssets',
            tooltip: 'chartSettings.tooltips.assetComparison',
        },
    ];

    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        // _resolvedData is injected by the parent before calling computePoints
        const resolvedData = this.params._resolvedData as LineDataPoint[] | undefined;
        if (!resolvedData?.length || !baseData.length) return [];

        // Build date→value lookup, then align to base chart's date axis
        const lookup = new Map(resolvedData.map(d => [d.date, d.value]));
        const points: LineDataPoint[] = [];
        for (const bd of baseData) {
            const val = lookup.get(bd.date);
            if (val !== undefined && val !== 0) {
                points.push({date: bd.date, value: val});
            }
        }

        return points;
    }

    /**
     * Override render() for AssetComparisonSignal: in percentage mode, normalize to the
     * signal's OWN first value (not the base chart's p0).
     *
     * Rationale: Asset comparison data has a completely different scale
     * (e.g. AAPL ~180 vs GOOGL ~140). Normalizing both curves to their
     * own starting point makes them start at 0% and shows relative movement,
     * which is the only meaningful comparison in percentage mode.
     */
    override render(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal {
        const absData = this.computePoints(baseData);

        let data = absData;
        if (viewMode === 'percentage' && absData.length > 0) {
            const p0 = absData[0].value;   // OWN first value, not base chart's
            if (p0 !== 0) {
                data = absData.map(d => ({
                    ...d,
                    value: ((d.value - p0) / p0) * 100,
                }));
            }
        }

        return {
            id: this.id,
            label: this.getLabel(),
            data,
            color: this.style.color,
            lineWidth: this.style.lineWidth,
            lineType: this.style.lineType,
            markerStart: this.style.markerStart,
            markerEnd: this.style.markerEnd,
            yAxisIndex: 0,
        };
    }

    getLabel(): string {
        const displayName = this.params._assetDisplayName as string | undefined;
        if (displayName) return `📊 ${displayName}`;
        const assetId = this.params.assetId;
        if (assetId) return `📊 Asset #${assetId}`;
        return '📊 Asset';
    }
}

