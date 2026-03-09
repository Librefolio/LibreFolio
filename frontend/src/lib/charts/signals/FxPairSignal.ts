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

    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        // _resolvedData is injected by the parent before calling computePoints
        const resolvedData = this.params._resolvedData as LineDataPoint[] | undefined;
        if (!resolvedData?.length || !baseData.length) return [];

        const isInverted = Boolean(this.params._inverted);

        // Build date→value lookup, then align to base chart's date axis
        const lookup = new Map(resolvedData.map(d => [d.date, d.value]));
        const points: LineDataPoint[] = [];
        for (const bd of baseData) {
            const val = lookup.get(bd.date);
            if (val !== undefined && val !== 0) {
                points.push({date: bd.date, value: isInverted ? 1 / val : val});
            }
        }

        return points;
    }

    getLabel(): string {
        const slug = String(this.params.pairSlug || '');
        const isInverted = Boolean(this.params._inverted);
        if (!slug) return 'FX Pair';
        const [a, b] = slug.split('-');
        return isInverted ? `${b}/${a}` : `${a}/${b}`;
    }
}

