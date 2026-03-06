/**
 * CompoundSignal — Synthetic signal: compound growth (exponential / interesse composto).
 *
 * Formula (absolute): y = y0 × (1 + rate)^t
 * Formula (percentage): pct = ((1 + rate)^t − 1) × 100
 *
 * where: t = daysSinceStart / 365, rate = annualRate / 100
 * Unlimited instances per chart.
 */

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class CompoundSignal extends ChartSignal {
    static override signalType = 'compound';
    static override displayName = 'Compound Growth';           // i18n: 'signals.compound'
    static override icon = '📊';
    // maxInstances = undefined → unlimited

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'annualRate',
            label: 'Annual Rate',                      // i18n: 'signals.params.annualRate'
            type: 'number',
            default: 8,
            min: -100,
            max: 1000,
            step: 0.5,
            suffix: '%/yr',
        },
    ];

    computePoints(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): LineDataPoint[] {
        if (!baseData.length) return [];

        const rate = Number(this.params.annualRate ?? 8) / 100;
        const baseValue = baseData[0].value;
        const startMs = new Date(baseData[0].date).getTime();
        const MS_PER_YEAR = 86_400_000 * 365;

        return baseData.map(d => {
            const t = (new Date(d.date).getTime() - startMs) / MS_PER_YEAR;
            return {
                date: d.date,
                value: viewMode === 'percentage'
                    ? (Math.pow(1 + rate, t) - 1) * 100
                    : baseValue * Math.pow(1 + rate, t),
            };
        });
    }

    getLabel(): string {
        return `Compound ${this.params.annualRate ?? 8}%/yr`;
    }
}

