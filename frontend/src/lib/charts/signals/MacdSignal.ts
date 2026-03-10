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
 *   2. Signal Line (dashed, same color — customizable via card)
 *   3. Histogram bars (bar chart, green/red by value sign)
 *
 * Y-axis: dedicated (yAxisIndex = 2) — all 3 components share their own
 * independent MACD axis, auto-scaled by ECharts. No manual scaling needed.
 *
 * For detailed mathematical theory and signal processing equivalents, see:
 * docs/financial-theory/technical-indicators.md#macd
 */

import {ChartSignal, type SignalParamDescriptor, type RenderedSignal, type MarkerType} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class MacdSignal extends ChartSignal {
    static override signalType = 'macd';
    static override displayName = 'MACD';
    static override icon = '📶';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'indicator';
    static yAxisIndex = 2;

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'fastPeriod',
            label: 'Fast Period',
            type: 'number',
            default: 12,
            min: 2,
            max: 200,
            step: 1,
            suffix: 'days',
        },
        {
            key: 'slowPeriod',
            label: 'Slow Period',
            type: 'number',
            default: 26,
            min: 2,
            max: 500,
            step: 1,
            suffix: 'days',
        },
        {
            key: 'signalPeriod',
            label: 'Signal Period',
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
     *  1. MACD Line (solid by default, primary color — uses the card's primary style)
     *  2. Signal Line (dashed by default, same color — customizable via MACD card)
     *  3. Histogram bars (bar chart, green/red by value sign)
     *
     * All 3 components use yAxisIndex=2 (dedicated MACD axis, auto-scaled by ECharts).
     * No manual scaling is needed — the axis is independent from the price axis.
     *
     * MACD values are inherently relative (fast EMA - slow EMA) and don't use
     * the standard p0-based % conversion. They are passed through as-is regardless
     * of viewMode.
     */
    override renderMulti(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal[] {
        const {macdLine, signalLine, histogram} = this._computeAll(baseData);
        if (macdLine.length === 0) return [];

        const label = this.getLabel();
        const signalColor = this.params._signalColor as string || this.style.color;
        const signalLineWidth = Number(this.params._signalLineWidth ?? Math.max(1, this.style.lineWidth - 1));
        const signalLineType = (this.params._signalLineType as 'solid' | 'dashed' | 'dotted') || 'dashed';
        const signalMarkerStart = (this.params._signalMarkerStart as MarkerType) ?? null;
        const signalMarkerEnd = (this.params._signalMarkerEnd as MarkerType) ?? null;

        return [
            {
                id: `${this.id}-macd`,
                label: `${label}`,
                data: macdLine,
                color: this.style.color,
                lineWidth: this.style.lineWidth,
                lineType: this.style.lineType,
                markerStart: this.style.markerStart,
                markerEnd: this.style.markerEnd,
                yAxisIndex: 2,
            },
            {
                id: `${this.id}-signal`,
                label: `${label} Signal`,
                data: signalLine,
                color: signalColor,
                lineWidth: signalLineWidth,
                lineType: signalLineType,
                markerStart: signalMarkerStart,
                markerEnd: signalMarkerEnd,
                yAxisIndex: 2,
            },
            {
                id: `${this.id}-hist`,
                label: `${label} Hist`,
                data: histogram,
                color: '#94a3b8',
                lineWidth: 1,
                lineType: 'solid',
                markerStart: null,
                markerEnd: null,
                yAxisIndex: 2,
                seriesType: 'bar',
            },
        ];
    }
}
