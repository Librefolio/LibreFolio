/**
 * CompoundSignal — Synthetic signal: compound growth (exponential / interesse composto).
 *
 * Mathematical formula (for reference):
 *   absolute:   y(t) = y0 × (1 + rate)^t
 *   percentage: pct(t) = ((1 + rate)^t − 1) × 100
 *   where t = daysSinceStart / 365, rate = annualRate / 100
 *
 * For performance, since we need ALL data points in sequence, we compute iteratively:
 * each point multiplies the previous value by the daily growth factor, avoiding N
 * expensive Math.pow() calls. This is computationally equivalent but O(N) multiplications
 * instead of O(N) full power operations.
 *
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
        const y0 = baseData[0].value;

        // Daily growth factor: (1 + rate)^(1/365)
        // We compute this once and multiply iteratively, which is much cheaper
        // than calling Math.pow() for every single data point.
        const dailyFactor = Math.pow(1 + rate, 1 / 365);

        const result: LineDataPoint[] = [];
        let currentValue = y0;
        let prevDate = baseData[0].date;

        for (let i = 0; i < baseData.length; i++) {
            const d = baseData[i];
            if (i === 0) {
                result.push({
                    date: d.date,
                    value: viewMode === 'percentage' ? 0 : y0,
                });
            } else {
                const daysDelta = ChartSignal.daysBetween(prevDate, d.date);
                currentValue *= Math.pow(dailyFactor, daysDelta);
                prevDate = d.date;

                result.push({
                    date: d.date,
                    value: viewMode === 'percentage'
                        ? ((currentValue / y0) - 1) * 100
                        : currentValue,
                });
            }
        }

        return result;
    }

    getLabel(): string {
        return `Compound ${this.params.annualRate ?? 8}%/yr`;
    }
}

