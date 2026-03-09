/**
 * FxPairSignal — Overlay signal sourced from a real FX pair (data from backend).
 *
 * The parent component pre-fetches data from the TimeSeriesStore and injects it
 * via `params._resolvedData` before calling `computePoints()`.
 * The '_' prefix ensures `_resolvedData` is excluded from `toConfig()` serialization.
 *
 * No maxInstances limit — user can overlay multiple FX pairs on the same chart.
 * If the same pair is added twice, points overlap harmlessly (not permanent).
 */

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class FxPairSignal extends ChartSignal {
    static override signalType = 'fx-pair';
    static override displayName = 'FX Pair';                   // i18n: 'signals.fxPair'
    static override icon = '💱';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'comparison';

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'pairSlug',
            label: 'Currency Pair',                    // i18n: 'signals.params.currencyPair'
            type: 'select',
            default: '',
            dynamicOptionsKey: 'configuredFxPairs',    // resolved at runtime by the modal
        },
    ];

    computePoints(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): LineDataPoint[] {
        // _resolvedData is injected by the parent before calling computePoints
        const resolvedData = this.params._resolvedData as LineDataPoint[] | undefined;
        if (!resolvedData?.length || !baseData.length) return [];

        // Build date→value lookup, then align to base chart's date axis
        const lookup = new Map(resolvedData.map(d => [d.date, d.value]));
        const points: LineDataPoint[] = [];
        for (const bd of baseData) {
            const val = lookup.get(bd.date);
            if (val !== undefined) points.push({date: bd.date, value: val});
        }

        if (viewMode === 'percentage' && points.length > 0) {
            const base = points[0].value;
            if (base !== 0) {
                return points.map(p => ({...p, value: ((p.value - base) / base) * 100}));
            }
        }
        return points;
    }

    getLabel(): string {
        const slug = String(this.params.pairSlug || '');
        return slug ? slug.replace('-', '/') : 'FX Pair';
    }
}

