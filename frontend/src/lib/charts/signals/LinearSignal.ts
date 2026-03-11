/**
 * LinearSignal — Synthetic signal: straight line with constant annual slope.
 *
 * Formula (absolute): y = y0 × (1 + offset/100 + rate × t)
 * Formula (percentage): pct = (offset + rate × t) × 100
 *
 * where: t = daysSinceStart / 365, rate = annualRate / 100, offset = offset / 100
 * Unlimited instances per chart.
 *
 * For detailed mathematical theory, see:
 * docs/financial-theory/synthetic-benchmarks.md#linear-growth
 */

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class LinearSignal extends ChartSignal {
    static override signalType = 'linear';
    static override displayName = 'Linear Growth';             // i18n: 'signals.linear'
    static override icon = '📈';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'benchmark';
    static docsPath = 'financial-theory/synthetic-benchmarks/#linear-growth';

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'annualRate',
            label: 'Annual Rate',
            type: 'number',
            default: 2,
            min: -100,
            max: 1000,
            step: 0.5,
            suffix: '%/yr',
            tooltip: 'chartSettings.tooltips.annualRate',
        },
        {
            key: 'offset',
            label: 'Offset',
            type: 'number',
            default: 0,
            min: -100,
            max: 100,
            step: 0.5,
            suffix: '%',
            tooltip: 'chartSettings.tooltips.offset',
        },
    ];

    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        if (!baseData.length) return [];

        const rate = Number(this.params.annualRate ?? 2) / 100;
        const offset = Number(this.params.offset ?? 0) / 100;
        const baseValue = baseData[0].value;
        const startDate = baseData[0].date;

        return baseData.map(d => {
            const days = ChartSignal.daysBetween(startDate, d.date);
            const t = days / 365;
            return {
                date: d.date,
                value: baseValue * (1 + offset + rate * t),
            };
        });
    }

    getLabel(): string {
        const rate = this.params.annualRate ?? 2;
        const offset = Number(this.params.offset ?? 0);
        const offsetStr = offset !== 0 ? ` +${offset}%` : '';
        return `Linear ${rate}%/yr${offsetStr}`;
    }
}

