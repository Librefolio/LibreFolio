import {describe, expect, it} from 'vitest';

import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {MeasureSignal} from '../MeasureSignal';

/**
 * MeasureSignal — the ruler dropped on a chart by two clicks.
 *
 * It never reaches the registry and has no config UI: MeasurePanel builds it,
 * reads its numbers into the summary table, and throws it away. So the whole of
 * its behaviour lives in these four methods, and none of it was pinned before.
 */

const style = MeasureSignal.getDefaultStyle();

/** A chart that dips in the middle, so interpolation is visibly not the data. */
const chart: LineDataPoint[] = [
    {date: '2026-04-01', value: 100},
    {date: '2026-04-02', value: 60},
    {date: '2026-04-03', value: 300},
    {date: '2026-04-04', value: 130},
];

function measure(startDate: unknown, endDate: unknown): MeasureSignal {
    return new MeasureSignal('m1', style, {startDate, endDate});
}

function values(points: LineDataPoint[]): number[] {
    return points.map((point) => point.value);
}

describe('MeasureSignal — default style', () => {
    it('ships a dotted orange line pinned at the start and arrowed at the end', () => {
        expect(MeasureSignal.getDefaultStyle()).toEqual({
            color: '#f97316',
            lineWidth: 1,
            lineType: 'dotted',
            markerStart: 'pin',
            markerEnd: 'arrow',
        });
    });

    it('hands out a fresh style object each time, so one measure cannot recolour another', () => {
        const first = MeasureSignal.getDefaultStyle();
        first.color = '#000000';

        expect(MeasureSignal.getDefaultStyle().color).toBe('#f97316');
    });
});

describe('MeasureSignal — the drawn segment', () => {
    it('draws a straight line between the endpoints, ignoring the data in between', () => {
        // 100 → 130 across three steps. The 60 and 300 the chart actually did are
        // deliberately not on the ruler.
        expect(values(measure('2026-04-01', '2026-04-04').computePoints(chart))).toEqual([100, 110, 120, 130]);
    });

    it('emits a point for every chart date it spans', () => {
        // ECharts drops a two-point line as soon as both ends leave the zoom
        // window, so the segment is filled in rather than left as endpoints.
        const points = measure('2026-04-01', '2026-04-04').computePoints(chart);
        expect(points.map((point) => point.date)).toEqual(['2026-04-01', '2026-04-02', '2026-04-03', '2026-04-04']);
    });

    it('covers only the requested span, not the whole chart', () => {
        const points = measure('2026-04-02', '2026-04-03').computePoints(chart);

        expect(points.map((point) => point.date)).toEqual(['2026-04-02', '2026-04-03']);
        expect(values(points)).toEqual([60, 300]);
    });

    it('collapses to a single point when both ends are the same day', () => {
        expect(measure('2026-04-02', '2026-04-02').computePoints(chart)).toEqual([{date: '2026-04-02', value: 60}]);
    });

    it('draws nothing when an endpoint is not on the chart', () => {
        expect(measure('2026-03-30', '2026-04-04').computePoints(chart)).toEqual([]);
        expect(measure('2026-04-01', '2026-04-09').computePoints(chart)).toEqual([]);
        expect(measure('2026-04-01', '2026-04-04').computePoints([])).toEqual([]);
    });

    it('draws nothing before both dates have been picked', () => {
        expect(measure('', '2026-04-04').computePoints(chart)).toEqual([]);
        expect(measure('2026-04-01', '').computePoints(chart)).toEqual([]);
        expect(measure(undefined, undefined).computePoints(chart)).toEqual([]);
    });
});

describe('MeasureSignal — the measurement', () => {
    it('reports the absolute and relative move between the two points', () => {
        expect(measure('2026-04-02', '2026-04-03').getMeasurement(chart)).toMatchObject({
            startDate: '2026-04-02',
            endDate: '2026-04-03',
            startValue: 60,
            endValue: 300,
            deltaAbs: 240,
            deltaPct: 400,
            days: 1,
        });
    });

    it('reports a loss as a negative move', () => {
        expect(measure('2026-04-03', '2026-04-04').getMeasurement(chart)).toMatchObject({
            deltaAbs: -170,
            days: 1,
        });
        expect(measure('2026-04-03', '2026-04-04').getMeasurement(chart)!.deltaPct).toBeCloseTo(-56.6667, 4);
    });

    it('annualises a partial year by compounding, not by scaling', () => {
        // +10% held for 73 days — a fifth of a year — is 1.1^5 − 1 = 61.05%/yr,
        // not 5 × 10%.
        const yearly: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-03-15', value: 110}, // 73 days later
        ];

        const result = measure('2026-01-01', '2026-03-15').getMeasurement(yearly)!;
        expect(result.days).toBe(73);
        expect(result.deltaPct).toBeCloseTo(10, 10);
        expect(result.annualizedPct).toBeCloseTo(61.051, 3);
    });

    it('leaves a one-year move unchanged by annualisation', () => {
        const yearly: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2027-01-01', value: 110},
        ];

        expect(measure('2026-01-01', '2027-01-01').getMeasurement(yearly)!.annualizedPct).toBeCloseTo(10, 10);
    });

    it('reports no annual rate for a zero-length span', () => {
        // 365/0 is infinite; there is no rate to report from a single instant.
        expect(measure('2026-04-02', '2026-04-02').getMeasurement(chart)).toMatchObject({
            deltaAbs: 0,
            deltaPct: 0,
            days: 0,
            annualizedPct: 0,
        });
    });

    it('reports no percentage when the span opens at zero', () => {
        // Any move away from zero is an infinite gain; the absolute delta is the
        // only honest number left.
        const fromZero: LineDataPoint[] = [
            {date: '2026-04-01', value: 0},
            {date: '2026-04-02', value: 50},
        ];

        expect(measure('2026-04-01', '2026-04-02').getMeasurement(fromZero)).toMatchObject({
            deltaAbs: 50,
            deltaPct: 0,
            annualizedPct: 0,
        });
    });

    it('has nothing to report until both endpoints exist on the chart', () => {
        expect(measure('', '2026-04-04').getMeasurement(chart)).toBeNull();
        expect(measure('2026-04-01', '').getMeasurement(chart)).toBeNull();
        expect(measure('2026-03-30', '2026-04-04').getMeasurement(chart)).toBeNull();
        expect(measure('2026-04-01', '2026-04-09').getMeasurement(chart)).toBeNull();
    });

    it('counts elapsed days across a month boundary', () => {
        const spanning: LineDataPoint[] = [
            {date: '2026-01-31', value: 100},
            {date: '2026-03-01', value: 100},
        ];

        expect(measure('2026-01-31', '2026-03-01').getMeasurement(spanning)!.days).toBe(29);
    });

    it('measures a span the panel never builds without drawing it', () => {
        // Both entry points in MeasurePanel sort the two clicks before
        // constructing the signal, so end-before-start is unreachable today. The
        // asymmetry is pinned here so it stays visible if that ever changes: the
        // summary would report nine days while the chart drew no line at all.
        const reversed = measure('2026-04-04', '2026-04-01');

        expect(reversed.getMeasurement(chart)).toMatchObject({days: 3, deltaAbs: -30, annualizedPct: 0});
        expect(reversed.computePoints(chart)).toEqual([]);
    });
});

describe('MeasureSignal — measuring another signal', () => {
    const overlay: LineDataPoint[] = [
        {date: '2026-04-01', value: 20},
        {date: '2026-04-04', value: 25},
    ];

    it('reads the same span off an overlay\u2019s own series', () => {
        expect(measure('2026-04-01', '2026-04-04').getMeasurementForSignal(overlay)).toMatchObject({
            startValue: 20,
            endValue: 25,
            deltaAbs: 5,
            deltaPct: 25,
        });
    });

    it('annualises the overlay the same way as the chart', () => {
        const result = measure('2026-04-01', '2026-04-04').getMeasurementForSignal(overlay)!;
        // +25% held for 3 days, compounded to a year.
        expect(result.annualizedPct).toBeCloseTo((Math.pow(1.25, 365 / 3) - 1) * 100, 0);
    });

    it('returns nothing for an overlay that has no point on those dates', () => {
        // A benchmark that starts later than the measure is simply not comparable.
        expect(measure('2026-04-01', '2026-04-04').getMeasurementForSignal([{date: '2026-04-02', value: 20}])).toBeNull();
        expect(measure('2026-04-01', '2026-04-04').getMeasurementForSignal([])).toBeNull();
    });

    it('has nothing to report before both dates have been picked', () => {
        expect(measure('', '').getMeasurementForSignal(overlay)).toBeNull();
        expect(measure('2026-04-01', undefined).getMeasurementForSignal(overlay)).toBeNull();
    });

    it('reports no percentage when the overlay opens at zero', () => {
        expect(
            measure('2026-04-01', '2026-04-04').getMeasurementForSignal([
                {date: '2026-04-01', value: 0},
                {date: '2026-04-04', value: 8},
            ]),
        ).toMatchObject({deltaAbs: 8, deltaPct: 0, annualizedPct: 0});
    });

    it('reports no annual rate for a zero-length span on the overlay either', () => {
        expect(measure('2026-04-01', '2026-04-01').getMeasurementForSignal(overlay)).toMatchObject({deltaAbs: 0, annualizedPct: 0});
    });
});

describe('MeasureSignal — legend label', () => {
    it('shows the ruler and both dates', () => {
        expect(measure('2026-04-01', '2026-04-04').getLabel()).toBe('📏 2026-04-01 → 2026-04-04');
    });

    it('marks a date that has not been picked yet', () => {
        expect(measure('2026-04-01', '').getLabel()).toBe('📏 2026-04-01 → ???');
        expect(measure(undefined, undefined).getLabel()).toBe('📏 ??? → ???');
    });
});
