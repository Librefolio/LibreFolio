/**
 * MeasureSignal — Measurement overlay signal.
 *
 * Renders as a 2-point line between startDate and endDate with pin/arrow markers.
 * NOT registered in the global signal registry (not in dropdown menus).
 * Managed exclusively by MeasurePanel.
 *
 * @module charts/signals/MeasureSignal
 */

import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {ChartSignal, type SignalParamDescriptor, type SignalStyle} from './ChartSignal';

/** Computed measurement values between two points */
export interface MeasurementResult {
    startDate: string;
    endDate: string;
    startValue: number;
    endValue: number;
    deltaAbs: number;
    deltaPct: number;
    days: number;
    annualizedPct: number;
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
            color: '#f97316', // orange
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
        if (!start || !end) return [];

        // Interpolate all dates between start and end so the line segment
        // remains visible when zoomed in (ECharts hides lines with both
        // endpoints outside the visible range if only 2 non-null points exist)
        const startIdx = baseData.findIndex((d) => d.date === startDate);
        const endIdx = baseData.findIndex((d) => d.date === endDate);
        if (startIdx < 0 || endIdx < 0) return [];

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
        if (!start || !end) return null;

        const deltaAbs = end.value - start.value;
        const deltaPct = start.value !== 0 ? (deltaAbs / start.value) * 100 : 0;
        const days = ChartSignal.daysBetween(startDate, endDate);
        // Annualized: (1 + deltaPct/100)^(365/days) - 1, as %
        const annualizedPct = days > 0 ? (Math.pow(1 + deltaPct / 100, 365 / days) - 1) * 100 : 0;

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
    getMeasurementForSignal(signalData: LineDataPoint[]): {startValue: number; endValue: number; deltaAbs: number; deltaPct: number; annualizedPct: number} | null {
        const startDate = String(this.params.startDate || '');
        const endDate = String(this.params.endDate || '');
        if (!startDate || !endDate) return null;

        const start = signalData.find((d) => d.date === startDate);
        const end = signalData.find((d) => d.date === endDate);
        if (!start || !end) return null;

        const deltaAbs = end.value - start.value;
        const deltaPct = start.value !== 0 ? (deltaAbs / start.value) * 100 : 0;
        const days = ChartSignal.daysBetween(startDate, endDate);
        const annualizedPct = days > 0 ? (Math.pow(1 + deltaPct / 100, 365 / days) - 1) * 100 : 0;
        return {startValue: start.value, endValue: end.value, deltaAbs, deltaPct, annualizedPct};
    }
}
