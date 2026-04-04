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

import {ChartSignal, type RenderedSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {getCurrencyInfo} from '$lib/stores/currencyStore';

export class FxPairSignal extends ChartSignal {
    static override signalType = 'fx-pair';
    static override displayName = 'FX Pair';                   // i18n: 'signals.fxPair'
    static override icon = '💱';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'comparison';

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'pairSlug',
            label: 'Currency Pair',                    // i18n: 'chartSettings.params.currencyPair'
            type: 'select',
            default: '',
            dynamicOptionsKey: 'configuredFxPairs',    // resolved at runtime by the modal
            tooltip: 'chartSettings.tooltips.fxPair',
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

    /**
     * Override render() for FxPairSignal: in percentage mode, normalize to the
     * signal's OWN first value (not the base chart's p0).
     *
     * Rationale: FxPair comparison data has a completely different scale
     * (e.g. EUR/USD ~1.10 vs GBP/JPY ~190). Normalizing both curves to their
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
        const slug = String(this.params.pairSlug || '');
        const isInverted = Boolean(this.params._inverted);
        if (!slug) return 'FX Pair';
        const [a, b] = slug.split('-');
        const base = isInverted ? b : a;
        const quote = isInverted ? a : b;
        const baseFlag = getCurrencyInfo(base).flag_emoji;
        const quoteFlag = getCurrencyInfo(quote).flag_emoji;
        return `${baseFlag} ${base} → ${quoteFlag} ${quote}`;
    }
}
