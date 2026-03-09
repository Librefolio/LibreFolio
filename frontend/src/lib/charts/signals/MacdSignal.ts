/**
 * MacdSignal — Moving Average Convergence Divergence.
 *
 * Financial meaning:
 *   Detects momentum shifts by comparing a fast EMA to a slow EMA.
 *   The MACD line oscillates around zero: positive = bullish momentum,
 *   negative = bearish momentum. The Signal line (smoothed MACD) produces
 *   crossover buy/sell signals.
 *
 * Signal processing equivalent:
 *   Band-pass filter (smoothed derivative). The subtraction of two low-pass
 *   filters (fast EMA − slow EMA) cancels the DC component (long-term trend)
 *   and attenuates high-frequency noise, isolating the intermediate momentum band.
 *   The Signal line is an additional low-pass filter applied to the band-pass output.
 *
 * Computed iteratively in O(N): three EMA passes, each a single multiplication per point.
 *
 * Components:
 *   - 'macd': MACD line (fast EMA − slow EMA)
 *   - 'signal': Signal line (EMA of MACD line)
 *   - 'histogram': MACD − Signal (divergence bars)
 *
 * Y-axis: secondary (left axis, independent scale) → yAxisIndex = 1
 *
 * For detailed mathematical theory and signal processing equivalents, see:
 * docs/financial-theory/technical-indicators.md#macd
 */

import {ChartSignal, type SignalParamDescriptor, type RenderedSignal} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class MacdSignal extends ChartSignal {
    static override signalType = 'macd';
    static override displayName = 'MACD';                      // i18n: 'signals.macd'
    static override icon = '📶';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'indicator';
    static yAxisIndex = 1; // independent scale on left axis

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'fastPeriod',
            label: 'Fast Period',                      // i18n: 'signals.params.fastPeriod'
            type: 'number',
            default: 12,
            min: 2,
            max: 200,
            step: 1,
            suffix: 'days',
        },
        {
            key: 'slowPeriod',
            label: 'Slow Period',                      // i18n: 'signals.params.slowPeriod'
            type: 'number',
            default: 26,
            min: 2,
            max: 500,
            step: 1,
            suffix: 'days',
        },
        {
            key: 'signalPeriod',
            label: 'Signal Period',                    // i18n: 'signals.params.signalPeriod'
            type: 'number',
            default: 9,
            min: 2,
            max: 100,
            step: 1,
            suffix: 'days',
        },
        {
            key: 'component',
            label: 'Component',                        // i18n: 'signals.params.component'
            type: 'select',
            default: 'macd',
            options: [
                {value: 'macd', label: 'MACD Line'},
                {value: 'signal', label: 'Signal Line'},
                {value: 'histogram', label: 'Histogram'},
            ],
        },
    ];

    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        if (baseData.length < 2) return [];

        const fastN = Math.max(2, Math.round(Number(this.params.fastPeriod ?? 12)));
        const slowN = Math.max(2, Math.round(Number(this.params.slowPeriod ?? 26)));
        const sigN = Math.max(2, Math.round(Number(this.params.signalPeriod ?? 9)));
        const component = String(this.params.component ?? 'macd');

        const alphaFast = 2 / (fastN + 1);
        const alphaSlow = 2 / (slowN + 1);
        const alphaSig = 2 / (sigN + 1);

        // Pass 1: compute fast EMA and slow EMA iteratively
        let emaFast = baseData[0].value;
        let emaSlow = baseData[0].value;
        const macdValues: number[] = [];

        for (let i = 0; i < baseData.length; i++) {
            const price = baseData[i].value;
            if (i === 0) {
                emaFast = price;
                emaSlow = price;
            } else {
                emaFast = alphaFast * price + (1 - alphaFast) * emaFast;
                emaSlow = alphaSlow * price + (1 - alphaSlow) * emaSlow;
            }
            macdValues.push(emaFast - emaSlow);
        }

        // Pass 2: compute signal line (EMA of MACD values) iteratively
        let emaSig = macdValues[0];
        const signalValues: number[] = [];

        for (let i = 0; i < macdValues.length; i++) {
            if (i === 0) {
                emaSig = macdValues[i];
            } else {
                emaSig = alphaSig * macdValues[i] + (1 - alphaSig) * emaSig;
            }
            signalValues.push(emaSig);
        }

        // Select component and build output
        return baseData.map((d, i) => {
            let value: number;
            switch (component) {
                case 'signal':
                    value = signalValues[i];
                    break;
                case 'histogram':
                    value = macdValues[i] - signalValues[i];
                    break;
                default: // 'macd'
                    value = macdValues[i];
                    break;
            }
            return {date: d.date, value};
        });
    }

    getLabel(): string {
        const fast = this.params.fastPeriod ?? 12;
        const slow = this.params.slowPeriod ?? 26;
        const sig = this.params.signalPeriod ?? 9;
        const comp = String(this.params.component ?? 'macd');
        const compLabel = comp === 'signal' ? 'Sig' : comp === 'histogram' ? 'Hist' : 'MACD';
        return `${compLabel}(${fast},${slow},${sig})`;
    }

    /** Override to set seriesType='bar' for histogram component */
    override render(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal {
        const base = super.render(baseData, viewMode);
        if (String(this.params.component ?? 'macd') === 'histogram') {
            base.seriesType = 'bar';
        }
        return base;
    }
}

