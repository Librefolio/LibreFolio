/**
 * SineSignal — Synthetic signal: sinusoidal oscillation.
 *
 * Useful for previewing chart aesthetics (baseline coloring, area fill, etc.)
 * and as a general-purpose oscillation benchmark.
 *
 * Parameters:
 *   - amplitude: peak-to-peak size as % of baseline (default 15%)
 *   - period: oscillation period in days (default 45)
 *   - offset: vertical shift as % of baseline (default 0%)
 *
 * Formula:
 *   absolute:   y(t) = y0 × (1 + offset/100 + (amplitude/100) × sin(2π × days / period))
 *   percentage: pct(t) = offset + amplitude × sin(2π × days / period)
 *
 * Unlimited instances per chart.
 *
 * For detailed mathematical theory, see:
 * docs/financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.en.md
 *
 * @financial-math-exception A what-if curve: a sine oscillation with the amplitude, period and offset the
 * user enters, to preview the chart and to compare with the series on screen. It is a hypothetical path, not
 * a figure of the user's holdings, so it stays in the browser (developer docs, financial_math.md, rule 6).
 */

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {formatFixed} from '$lib/utils/core/formatFixed';
import {formatPercent} from '$lib/utils/core/formatPercent';

export class SineSignal extends ChartSignal {
    static override signalType = 'sine';
    static override displayName = 'Sine Wave'; // i18n: 'signals.sine'
    static override icon = '〰️';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'benchmark';
    static docsPath = 'financial-theory/technical-analysis/synthetic-benchmarks/sine-wave/';

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'amplitude',
            label: 'Amplitude', // i18n: 'signals.params.amplitude'
            type: 'number',
            default: 15,
            min: 0.1,
            max: 200,
            step: 1,
            suffix: '%',
            tooltip: 'chartSettings.tooltips.amplitude',
        },
        {
            key: 'period',
            label: 'Period', // i18n: 'signals.params.period'
            type: 'number',
            default: 45,
            min: 2,
            max: 3650,
            step: 1,
            suffix: 'days',
            tooltip: 'chartSettings.tooltips.period',
        },
        {
            key: 'offset',
            label: 'Offset', // i18n: 'signals.params.offset'
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

        const amplitude = Number(this.params.amplitude ?? 15) / 100;
        const period = Number(this.params.period ?? 45);
        const offset = Number(this.params.offset ?? 0) / 100;
        const y0 = baseData[0].value;
        const startDate = baseData[0].date;

        return baseData.map((d) => {
            const days = ChartSignal.daysBetween(startDate, d.date);
            const sine = amplitude * Math.sin((2 * Math.PI * days) / period);
            return {date: d.date, value: y0 * (1 + offset + sine)};
        });
    }

    getLabel(): string {
        const amplitude = formatPercent(Number(this.params.amplitude ?? 15), {signed: false, trim: true});
        const period = formatFixed(Number(this.params.period ?? 45), 2, {trim: true});
        return ChartSignal.text('chartSettings.signals.sineLabel', {amplitude, period});
    }
}
