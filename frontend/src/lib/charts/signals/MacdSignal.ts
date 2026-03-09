/**
 * MacdSignal — Moving Average Convergence Divergence (Composite).
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
 * This is a COMPOSITE signal: a single card/config generates 3 RenderedSignals:
 *   1. MACD Line (solid, primary color)
 *   2. Signal Line (dashed, secondary color)
 *   3. Histogram bars (bar chart, green/red)
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
    ];

    /**
     * Compute all three MACD components in one pass.
     * Returns { macdLine, signalLine, histogram } aligned to baseData dates.
     */
    private _computeAll(baseData: LineDataPoint[]): {
        macdLine: LineDataPoint[];
        signalLine: LineDataPoint[];
        histogram: LineDataPoint[];
    } {
        if (baseData.length < 2) {
            return {macdLine: [], signalLine: [], histogram: []};
        }

        const fastN = Math.max(2, Math.round(Number(this.params.fastPeriod ?? 12)));
        const slowN = Math.max(2, Math.round(Number(this.params.slowPeriod ?? 26)));
        const sigN = Math.max(2, Math.round(Number(this.params.signalPeriod ?? 9)));

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

        // Build output arrays
        const macdLine: LineDataPoint[] = [];
        const signalLine: LineDataPoint[] = [];
        const histogram: LineDataPoint[] = [];

        for (let i = 0; i < baseData.length; i++) {
            const date = baseData[i].date;
            macdLine.push({date, value: macdValues[i]});
            signalLine.push({date, value: signalValues[i]});
            histogram.push({date, value: macdValues[i] - signalValues[i]});
        }

        return {macdLine, signalLine, histogram};
    }

    /** computePoints returns MACD line for compatibility with base class */
    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        return this._computeAll(baseData).macdLine;
    }

    getLabel(): string {
        const fast = this.params.fastPeriod ?? 12;
        const slow = this.params.slowPeriod ?? 26;
        const sig = this.params.signalPeriod ?? 9;
        return `MACD(${fast},${slow},${sig})`;
    }

    /**
     * Override renderMulti() to produce 3 RenderedSignals from a single config:
     *  1. MACD Line (solid, uses the card's style color)
     *  2. Signal Line (dashed, dimmed variant of card color)
     *  3. Histogram (bar chart, red/green determined by LineChart)
     *
     * No % conversion for secondary-axis signals (they're dimensionless).
     */
    override renderMulti(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal[] {
        const {macdLine, signalLine, histogram} = this._computeAll(baseData);
        if (macdLine.length === 0) return [];

        const label = this.getLabel();
        // Derive Signal Line color: use a complementary hue
        const signalColor = this.params._signalColor as string || '#f59e0b';
        const histColor = this.params._histColor as string || '#94a3b8';

        return [
            // 1. MACD Line
            {
                id: `${this.id}-macd`,
                label: `${label}`,
                data: macdLine,
                color: this.style.color,
                lineWidth: this.style.lineWidth,
                lineType: 'solid',
                markerStart: this.style.markerStart,
                markerEnd: this.style.markerEnd,
                yAxisIndex: 1,
            },
            // 2. Signal Line
            {
                id: `${this.id}-signal`,
                label: `${label} Signal`,
                data: signalLine,
                color: signalColor,
                lineWidth: Math.max(1, this.style.lineWidth - 1),
                lineType: 'dashed',
                markerStart: null,
                markerEnd: null,
                yAxisIndex: 1,
            },
            // 3. Histogram (bar chart — red/green coloring handled by LineChart)
            {
                id: `${this.id}-hist`,
                label: `${label} Hist`,
                data: histogram,
                color: histColor,
                lineWidth: 1,
                lineType: 'solid',
                markerStart: null,
                markerEnd: null,
                yAxisIndex: 1,
                seriesType: 'bar',
            },
        ];
    }
}

