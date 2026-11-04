/**
 * MeasureSignal — Measurement overlay signal.
 *
 * Renders as a 2-point line between startDate and endDate with pin/arrow markers.
 * NOT registered in the global signal registry (not in dropdown menus).
 * Managed exclusively by MeasurePanel.
 *
 * @financial-math-exception The chart measuring tool: Δ, Δ% and the annualized change between the two
 * points the user pins on the chart, recomputed as the pins move. It measures the series drawn on screen,
 * not a figure of the portfolio, so it stays in the browser (developer docs, financial_math.md, rule 6).
 *
 * @module charts/signals/MeasureSignal
 */

import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {ChartSignal, type SignalParamDescriptor, type SignalStyle} from './ChartSignal';
import {SIGNAL_COLORS} from '$lib/theme/chartTheme';

/**
 * The shortest span the ruler annualises, in days: the floor of the backend home (`_MIN_ANNUALIZATION_DAYS` in
 * backend/app/services/financial_math/returns.py, held to it by a parity test). Shorter spans show «—» for Δ%/yr.
 */
export const MIN_ANNUALIZATION_DAYS = 30;

/** Computed measurement values between two points */
export interface MeasurementResult {
    startDate: string;
    endDate: string;
    startValue: number;
    endValue: number;
    deltaAbs: number;
    /** null when the span opens at zero: the move is unknown, not 0 % */
    deltaPct: number | null;
    days: number;
    /** null under MIN_ANNUALIZATION_DAYS, without a Δ%, for a line that changes sign, or when not finite */
    annualizedPct: number | null;
}

/**
 * The change in %, or null when the start is zero: the move is then unknown, not 0 % (night decision N65). The one Δ%
 * rule of the charts: the ruler and the main tooltip's delta (`priceChartHelpers.ts::buildDeltaHtml`, J-44) read it.
 */
export function changePct(startValue: number, endValue: number): number | null {
    return startValue !== 0 ? ((endValue - startValue) / startValue) * 100 : null;
}

/**
 * The change compounded to a year, (1 + Δ%/100)^(365/days) − 1, in %. null under the floor, without a Δ%, for a line
 * that changes sign (a negative growth factor has no compounded rate) and when the result is not finite. A fall to
 * exactly zero keeps its −100 %/yr.
 */
function annualizedChangePct(deltaPct: number | null, days: number): number | null {
    if (deltaPct === null || days < MIN_ANNUALIZATION_DAYS) return null;
    const growth = 1 + deltaPct / 100;
    if (growth < 0) return null;
    const annualized = (Math.pow(growth, 365 / days) - 1) * 100;
    return Number.isFinite(annualized) ? annualized : null;
}

export class MeasureSignal extends ChartSignal {
    static signalType = 'measure';
    static displayName = 'Measure';
    static icon = '📏';
    static category = 'measure' as const;
    static yAxisIndex = 0;
    static paramDescriptors: SignalParamDescriptor[] = [
        {key: 'startDate', label: 'Start', type: 'string', default: ''},
        {key: 'endDate', label: 'End', type: 'string', default: ''},
    ];

    constructor(id: string, style: SignalStyle, params: Record<string, unknown>) {
        super(id, style, params);
    }

    /** Default style for measure lines */
    static getDefaultStyle(): SignalStyle {
        return {
            color: SIGNAL_COLORS.measure, // orange
            lineWidth: 1,
            lineType: 'dotted',
            markerStart: 'pin',
            markerEnd: 'arrow',
        };
    }

    computePoints(baseData: LineDataPoint[]): LineDataPoint[] {
        const startDate = String(this.params.startDate || '');
        const endDate = String(this.params.endDate || '');
        if (!startDate || !endDate) return [];

        const start = baseData.find((d) => d.date === startDate);
        const end = baseData.find((d) => d.date === endDate);
        if (!start || !end || start.missing || end.missing) return [];

        // Interpolate all dates between start and end so the line segment
        // remains visible when zoomed in (ECharts hides lines with both
        // endpoints outside the visible range if only 2 non-null points exist)
        //
        // No guard on the indices: `find` above has already returned when either
        // endpoint is absent, and `findIndex` runs the same predicate over the
        // same array, so it cannot then answer -1.
        const startIdx = baseData.findIndex((d) => d.date === startDate);
        const endIdx = baseData.findIndex((d) => d.date === endDate);

        const points: LineDataPoint[] = [];
        const totalSteps = endIdx - startIdx;
        for (let i = startIdx; i <= endIdx; i++) {
            const t = totalSteps > 0 ? (i - startIdx) / totalSteps : 0;
            points.push({
                date: baseData[i].date,
                value: start.value + t * (end.value - start.value),
            });
        }
        return points;
    }

    getLabel(): string {
        const startDate = String(this.params.startDate || '???');
        const endDate = String(this.params.endDate || '???');
        return `📏 ${startDate} → ${endDate}`;
    }

    /** Compute measurement values from base data */
    getMeasurement(baseData: LineDataPoint[]): MeasurementResult | null {
        const startDate = String(this.params.startDate || '');
        const endDate = String(this.params.endDate || '');
        if (!startDate || !endDate) return null;

        const start = baseData.find((d) => d.date === startDate);
        const end = baseData.find((d) => d.date === endDate);
        if (!start || !end || start.missing || end.missing) return null;

        const deltaAbs = end.value - start.value;
        const deltaPct = changePct(start.value, end.value);
        const days = ChartSignal.daysBetween(startDate, endDate);
        const annualizedPct = annualizedChangePct(deltaPct, days);

        return {
            startDate,
            endDate,
            startValue: start.value,
            endValue: end.value,
            deltaAbs,
            deltaPct,
            days: Math.abs(days),
            annualizedPct,
        };
    }

    /**
     * Get measurement for a specific signal's data at the measure's date range.
     * Used by MeasurePanel's summary table to show values for all visible signals.
     */
    getMeasurementForSignal(signalData: LineDataPoint[]): {startValue: number; endValue: number; deltaAbs: number; deltaPct: number | null; annualizedPct: number | null} | null {
        const startDate = String(this.params.startDate || '');
        const endDate = String(this.params.endDate || '');
        if (!startDate || !endDate) return null;

        const start = signalData.find((d) => d.date === startDate);
        const end = signalData.find((d) => d.date === endDate);
        if (!start || !end || start.missing || end.missing) return null;

        const deltaAbs = end.value - start.value;
        const deltaPct = changePct(start.value, end.value);
        const annualizedPct = annualizedChangePct(deltaPct, ChartSignal.daysBetween(startDate, endDate));
        return {startValue: start.value, endValue: end.value, deltaAbs, deltaPct, annualizedPct};
    }
}
