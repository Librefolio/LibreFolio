/**
 * BollingerSignal — Bollinger Bands (confidence band rendering).
 *
 * Financial meaning:
 *   Adaptive volatility envelope. When bands squeeze, expect a breakout.
 *   Price touching the upper band → statistically high, lower → statistically low.
 *
 * Signal processing equivalent:
 *   Adaptive confidence interval tracker. The middle band is a moving average
 *   (expected value estimator), and the upper/lower bands are at ±k standard
 *   deviations (σ). With k=2 and Gaussian assumption, 95.4% of values fall
 *   within the bands.
 *
 * Computed iteratively in O(N) using a sliding window for the SMA and σ.
 * Rendered as a confidence band (shaded area between upper and lower) with
 * the middle SMA line visible.
 *
 * Y-axis: primary (same scale as price) → yAxisIndex = 0
 *
 * See: docs/financial-theory/technical-indicators.md#bollinger-bands
 */

import {ChartSignal, type SignalParamDescriptor, type RenderedSignal} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

export class BollingerSignal extends ChartSignal {
    static override signalType = 'bollinger';
    static override displayName = 'Bollinger Bands';
    static override icon = '📏';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'indicator';
    static docsPath = 'financial-theory/technical-indicators/#bollinger-bands';
    // yAxisIndex = 0 (default, same scale as price)

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'period',
            label: 'Period',
            type: 'number',
            default: 20,
            min: 2,
            max: 200,
            step: 1,
            suffix: 'days',
            tooltip: 'chartSettings.tooltips.period',
        },
        {
            key: 'multiplier',
            label: 'Multiplier',
            type: 'number',
            default: 2,
            min: 0.5,
            max: 5,
            step: 0.1,
            suffix: 'σ',
            tooltip: 'chartSettings.tooltips.multiplier',
        },
    ];

    /**
     * Compute the middle (SMA) line as the primary data series.
     * All three bands are computed in _computeAllBands.
     */
    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        if (baseData.length < 2) return [];
        const {middle} = this._computeAllBands(baseData);
        return middle;
    }

    /** Compute upper, middle, lower arrays in one O(N) pass (absolute values) */
    private _computeAllBands(
        baseData: LineDataPoint[],
    ): {upper: number[]; middle: LineDataPoint[]; lower: number[]} {
        const period = Math.max(2, Math.round(Number(this.params.period ?? 20)));
        const k = Number(this.params.multiplier ?? 2);

        const upperArr: number[] = [];
        const middleArr: LineDataPoint[] = [];
        const lowerArr: number[] = [];

        const window: number[] = [];
        let windowSum = 0;

        for (let i = 0; i < baseData.length; i++) {
            const price = baseData[i].value;
            window.push(price);
            windowSum += price;

            if (window.length > period) {
                windowSum -= window.shift()!;
            }

            const n = window.length;
            const sma = windowSum / n;

            let variance = 0;
            for (let j = 0; j < n; j++) {
                const diff = window[j] - sma;
                variance += diff * diff;
            }
            const sigma = Math.sqrt(variance / n);

            upperArr.push(sma + k * sigma);
            middleArr.push({date: baseData[i].date, value: sma});
            lowerArr.push(sma - k * sigma);
        }

        return {upper: upperArr, middle: middleArr, lower: lowerArr};
    }

    /**
     * Override render() to produce a confidence-band signal.
     * The LineChart reads seriesType='band' + bandData to generate the
     * stacked area series (Lower invisible + Upper-Lower shaded) + Middle line.
     */
    override render(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal {
        const rendered = super.render(baseData, viewMode);
        if (baseData.length < 2) return rendered;

        const {upper, middle, lower} = this._computeAllBands(baseData);
        rendered.seriesType = 'band';

        // Apply the same centralized % conversion to band data
        if (viewMode === 'percentage' && baseData.length > 0) {
            const p0 = baseData[0].value;
            if (p0 !== 0) {
                rendered.bandData = {
                    upper: upper.map(v => ((v - p0) / p0) * 100),
                    middle: middle.map(p => ((p.value - p0) / p0) * 100),
                    lower: lower.map(v => ((v - p0) / p0) * 100),
                };
                return rendered;
            }
        }

        rendered.bandData = {
            upper,
            middle: middle.map(p => p.value),
            lower,
        };
        return rendered;
    }

    getLabel(): string {
        const period = this.params.period ?? 20;
        const mult = this.params.multiplier ?? 2;
        return `BB(${period},${mult}σ)`;
    }
}
