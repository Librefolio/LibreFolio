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
 * See: docs/financial-theory/technical-indicators.md#rsi
 */

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class RsiSignal extends ChartSignal {
    static override signalType = 'rsi';
    static override displayName = 'RSI';
    static override icon = '📊';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'indicator';
    static yAxisIndex = 1;

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
        },
    ];

    computePoints(baseData: LineDataPoint[], _viewMode: 'absolute' | 'percentage'): LineDataPoint[] {
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

            const rsi = avgLoss === 0 ? 100 : avgGain === 0 ? 0 : 100 * avgGain / (avgGain + avgLoss);
            result.push({date: baseData[i].date, value: rsi});
        }

        return result;
    }

    getLabel(): string {
        return `RSI(${this.params.period ?? 14})`;
    }
}
