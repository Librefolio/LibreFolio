/**
 * LinearSignal — Synthetic signal: straight line with constant annual slope.
 *
 * Formula (absolute): y = y0 × (1 + offset/100 + rate × t)
 * Formula (percentage): pct = (offset + rate × t) × 100
 *
 * where: t = daysSinceStart / 365, rate = annualRate / 100, offset = offset / 100
 * Unlimited instances per chart.
 *
 * For detailed mathematical theory, see:
 * docs/financial-theory/technical-analysis/synthetic-benchmarks/linear.en.md
 *
 * @financial-math-exception A what-if curve: a straight line with the constant annual slope and the offset
 * the user enters, to compare with the series on screen. It is a hypothetical path, not a figure of the
 * user's holdings, so it stays in the browser (developer docs, financial_math.md, rule 6).
 */

import {ChartSignal, type SignalParamDescriptor} from './ChartSignal';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {formatPercent} from '$lib/utils/core/formatPercent';

export class LinearSignal extends ChartSignal {
    static override signalType = 'linear';
    static override displayName = 'Linear Growth'; // i18n: 'signals.linear'
    static override icon = '📈';
    static category: 'indicator' | 'comparison' | 'benchmark' = 'benchmark';
    static docsPath = 'financial-theory/technical-analysis/synthetic-benchmarks/linear/';

    static override paramDescriptors: SignalParamDescriptor[] = [
        {
            key: 'annualRate',
            label: 'Annual Rate',
            type: 'number',
            default: 2,
            min: -100,
            max: 1000,
            step: 0.5,
            suffix: 'percentPerYear',
            tooltip: 'chartSettings.tooltips.annualRate',
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
            tooltip: 'chartSettings.tooltips.offset',
        },
    ];

    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        if (!baseData.length) return [];

        const rate = Number(this.params.annualRate ?? 2) / 100;
        const offset = Number(this.params.offset ?? 0) / 100;
        const baseValue = baseData[0].value;
        const startDate = baseData[0].date;

        return baseData.map((d) => {
            const days = ChartSignal.daysBetween(startDate, d.date);
            const t = days / 365;
            return {
                date: d.date,
                value: baseValue * (1 + offset + rate * t),
            };
        });
    }

    getLabel(): string {
        const rate = Number(this.params.annualRate ?? 2);
        const offset = Number(this.params.offset ?? 0);
        const label = ChartSignal.text('chartSettings.signals.linearLabel', {rate: formatPercent(rate, {signed: false, trim: true})});
        // The sign travels with the number: a hard-coded `+` in front of a
        // negative offset reads as `+-5%`, which users reported. The
        // descriptor allows `min: -100`, so a benchmark below the start is a
        // legitimate thing to draw.
        return offset !== 0 ? `${label} ${formatPercent(offset, {trim: true})}` : label;
    }
}
