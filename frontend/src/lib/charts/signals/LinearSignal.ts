/**
 * LinearSignal — Synthetic signal: straight line with constant annual slope.
 *
 * Formula (absolute): y = y0 × (1 + rate × t)
 * Formula (percentage): pct = rate × t × 100
 *
 * where: t = daysSinceStart / 365, rate = annualRate / 100
 * Unlimited instances per chart.
 */

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class LinearSignal extends ChartSignal {
    static override signalType = 'linear';
    static override displayName = 'Linear Growth';             // i18n: 'signals.linear'
    static override icon = '📈';
    // maxInstances = undefined → unlimited

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'annualRate',
            label: 'Annual Rate',                      // i18n: 'signals.params.annualRate'
            type: 'number',
            default: 2,
            min: -100,
            max: 1000,
            step: 0.5,
            suffix: '%/yr',
        },
    ];

    computePoints(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): LineDataPoint[] {
        if (!baseData.length) return [];

        const rate = Number(this.params.annualRate ?? 2) / 100;
        const baseValue = baseData[0].value;
        const startDate = baseData[0].date;

        return baseData.map(d => {
            const days = ChartSignal.daysBetween(startDate, d.date);
            const t = days / 365;
            return {
                date: d.date,
                value: viewMode === 'percentage'
                    ? rate * t * 100
                    : baseValue * (1 + rate * t),
            };
        });
    }

    getLabel(): string {
        return `Linear ${this.params.annualRate ?? 2}%/yr`;
    }
}

