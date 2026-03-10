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
 *   2. Signal Line (dashed, secondary color — customizable via card)
 *   3. Histogram bars (bar chart, green/red, scaled by histogramScale)
 *
 * Y-axis: primary (yAxisIndex = 0) — all 3 components share the price axis.
 * The raw MACD values are very small for FX pairs (~0.001–0.01), so the histogram
 * uses a configurable scale multiplier to make bars visible on the chart.
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
    static yAxisIndex = 0; // primary axis — values are small but on the same scale as price

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
            key: 'histogramScale',
            label: 'Histogram Scale',                  // i18n: 'signals.params.histogramScale'
            type: 'number',
            default: 1000,
            min: 1,
            max: 100000,
            step: 100,
            suffix: '×',
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
     *  1. MACD Line (solid, uses the card's primary style) — secondary axis
     *  2. Signal Line (customizable style) — secondary axis
     *  3. Histogram (bar chart, values × histogramScale for visibility) — primary axis
     *
     * MACD Line/Signal on yAxisIndex=1 (secondary, auto-scaled to their small values).
     * Histogram on yAxisIndex=0 (primary, scaled by histogramScale for visibility).
     */
    override renderMulti(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal[] {
        const {macdLine, signalLine, histogram} = this._computeAll(baseData);
        if (macdLine.length === 0) return [];

        const label = this.getLabel();
        const signalColor = this.params._signalColor as string || '#f59e0b';
        const signalLineWidth = Number(this.params._signalLineWidth ?? Math.max(1, this.style.lineWidth - 1));
        const signalLineType = (this.params._signalLineType as 'solid' | 'dashed' | 'dotted') || 'dashed';
        const histScale = Math.max(1, Number(this.params.histogramScale ?? 1000));

        // Scale histogram values for visibility on the price axis
        const scaledHistogram: LineDataPoint[] = histogram.map(d => ({
            ...d,
            value: d.value * histScale,
        }));

        // MACD Line/Signal are on secondary axis (yAxisIndex=1) — they use their own scale,
        // so no % conversion needed. They are differential values, not price levels.
        // Only the histogram (primary axis) gets % conversion if active.
        const p0 = baseData.length > 0 ? baseData[0].value : 1;
        const applyPct = viewMode === 'percentage' && p0 !== 0;


        // For histogram in %, we convert the already-scaled values
        const convertHistPct = (data: LineDataPoint[]): LineDataPoint[] => {
            if (!applyPct) return data;
            // Histogram is a differential value, not a price level.
            // In % mode, express as % of p0.
            return data.map(d => ({...d, value: (d.value / p0) * 100}));
        };

        return [
            // 1. MACD Line — secondary axis for visibility (raw MACD values are tiny vs price)
            {
                id: `${this.id}-macd`,
                label: `${label}`,
                data: macdLine, // Raw values, no % conversion (secondary axis has own scale)
                color: this.style.color,
                lineWidth: this.style.lineWidth,
                lineType: 'solid',
                markerStart: this.style.markerStart,
                markerEnd: this.style.markerEnd,
                yAxisIndex: 1,
            },
            // 2. Signal Line — secondary axis, same scale as MACD Line
            {
                id: `${this.id}-signal`,
                label: `${label} Signal`,
                data: signalLine, // Raw values, no % conversion (secondary axis)
                color: signalColor,
                lineWidth: signalLineWidth,
                lineType: signalLineType,
                markerStart: null,
                markerEnd: null,
                yAxisIndex: 1,
            },
            // 3. Histogram (bar chart — red/green coloring handled by LineChart)
            //    On primary axis with scale multiplier for visibility
            {
                id: `${this.id}-hist`,
                label: `${label} Hist`,
                data: convertHistPct(scaledHistogram),
                color: '#94a3b8',
                lineWidth: 1,
                lineType: 'solid',
                markerStart: null,
                markerEnd: null,
                yAxisIndex: 0,
                seriesType: 'bar',
            },
        ];
    }
}

