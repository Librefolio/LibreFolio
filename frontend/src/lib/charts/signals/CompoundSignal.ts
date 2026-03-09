/**
 * CompoundSignal — Synthetic signal: compound growth (exponential / interesse composto).
 *
 * Mathematical formula (for reference):
 *   absolute:   y(t) = y0 × (1 + offset/100) × (1 + rate)^t
 *   percentage: pct(t) = ((y(t) / y0) − 1) × 100
 *   where t = daysSinceStart / 365, rate = annualRate / 100
 *
 * For performance, since we need ALL data points in sequence, we compute iteratively:
 * each point multiplies the previous value by the daily growth factor, avoiding N
 * expensive Math.pow() calls. This is computationally equivalent but O(N) multiplications
 * instead of O(N) full power operations.
 *
 * Unlimited instances per chart.
 *
 * For detailed mathematical theory, see:
 * docs/financial-theory/synthetic-benchmarks.md#compound-growth
 */

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class CompoundSignal extends ChartSignal {
    static override signalType = 'compound';
    static override displayName = 'Compound Growth';           // i18n: 'signals.compound'
    static override icon = '📊';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'benchmark';

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'annualRate',
            label: 'Annual Rate',
            type: 'number',
            default: 8,
            min: -100,
            max: 1000,
            step: 0.5,
            suffix: '%/yr',
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
        },
    ];

    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        if (!baseData.length) return [];

        const rate = Number(this.params.annualRate ?? 8) / 100;
        const offset = Number(this.params.offset ?? 0) / 100;
        const y0 = baseData[0].value;

        // Starting value with offset applied
        const startValue = y0 * (1 + offset);

        // Daily growth factor: (1 + rate)^(1/365)
        // We compute this once and multiply iteratively, which is much cheaper
        // than calling Math.pow() for every single data point.
        const dailyFactor = Math.pow(1 + rate, 1 / 365);

        const result: LineDataPoint[] = [];
        let currentValue = startValue;
        let prevDate = baseData[0].date;

        for (let i = 0; i < baseData.length; i++) {
            const d = baseData[i];
            if (i === 0) {
                result.push({date: d.date, value: startValue});
            } else {
                const daysDelta = ChartSignal.daysBetween(prevDate, d.date);
                currentValue *= Math.pow(dailyFactor, daysDelta);
                prevDate = d.date;
                result.push({date: d.date, value: currentValue});
            }
        }

        return result;
    }

    getLabel(): string {
        const rate = this.params.annualRate ?? 8;
        const offset = Number(this.params.offset ?? 0);
        const offsetStr = offset !== 0 ? ` +${offset}%` : '';
        return `Compound ${rate}%/yr${offsetStr}`;
    }
}

