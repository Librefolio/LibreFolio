/**
 * EmaSignal — Exponential Moving Average (First-Order IIR Low-Pass Filter).
 *
 * Financial meaning:
 *   Tracks the trend by smoothing noise, giving more weight to recent prices.
 *   A shorter period = faster reaction (higher cutoff frequency).
 *   A longer period = smoother but more lagged (lower cutoff frequency).
 *
 * Signal processing equivalent:
 *   First-order IIR Low-Pass Filter: y[n] = α·x[n] + (1−α)·y[n−1]
 *   where α = 2/(N+1) maps the trader-intuitive period N to the filter coefficient.
 *   This mapping is derived by equating the "center of mass" (average data age)
 *   of an EMA with that of an SMA of the same period.
 *
 * Computed iteratively in O(N) — one multiplication per data point.
 *
 * Y-axis: primary (same scale as price data) → yAxisIndex = 0
 *
 * For detailed mathematical theory and signal processing equivalents, see:
 * docs/financial-theory/technical-analysis/indicators/ema.en.md
 */

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class EmaSignal extends ChartSignal {
    static override signalType = 'ema';
    static override displayName = 'EMA'; // i18n: 'signals.ema'
    static override icon = '📉';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'indicator';
    static docsPath = 'financial-theory/technical-analysis/indicators/ema/';
    // yAxisIndex = 0 (default, same scale as price)

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'period',
            label: 'Period', // i18n: 'chartSettings.params.period'
            type: 'number',
            default: 14,
            min: 2,
            max: 500,
            step: 1,
            suffix: 'days',
            tooltip: 'chartSettings.tooltips.emaPeriod',
        },
        {
            key: 'offset',
            label: 'Offset', // i18n: 'chartSettings.params.offset'
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

        const period = Math.max(2, Math.round(Number(this.params.period ?? 14)));
        const offset = Number(this.params.offset ?? 0) / 100;
        // IIR filter coefficient: α = 2/(N+1)
        const alpha = 2 / (period + 1);

        const result: LineDataPoint[] = [];
        let ema = baseData[0].value; // Initialize with first price

        for (let i = 0; i < baseData.length; i++) {
            const d = baseData[i];
            if (i === 0) {
                ema = d.value;
            } else {
                // IIR Low-Pass: y[n] = α·x[n] + (1−α)·y[n−1]
                ema = alpha * d.value + (1 - alpha) * ema;
            }

            result.push({
                date: d.date,
                value: ema * (1 + offset),
            });
        }

        return result;
    }

    getLabel(): string {
        const period = this.params.period ?? 14;
        const offset = Number(this.params.offset ?? 0);
        const offsetStr = offset !== 0 ? ` +${offset}%` : '';
        return `EMA(${period})${offsetStr}`;
    }
}
