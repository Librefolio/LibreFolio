import {existsSync, readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {MeasureSignal, MIN_ANNUALIZATION_DAYS} from '../MeasureSignal';

/**
 * MeasureSignal — the ruler dropped on a chart by two clicks.
 *
 * It never reaches the registry and has no config UI: MeasurePanel builds it,
 * reads its numbers into the summary table, and throws it away. So the whole of
 * its behaviour lives in these four methods, and none of it was pinned before.
 *
 * The annual rate follows the backend home (T-D9, decision D-9; lot CP-14b of
 * workstream J): `cumulative_to_annualized` in
 * backend/app/services/financial_math/returns.py annualises no window shorter
 * than `_MIN_ANNUALIZATION_DAYS` (30) days, and the panel shows «—». The ruler
 * takes the same floor, `MIN_ANNUALIZATION_DAYS`, one constant exported by
 * MeasureSignal.ts and held to the backend's by the parity test at the end of
 * this file. The contract of both copies, `getMeasurement` and
 * `getMeasurementForSignal`:
 *   - `deltaPct` is null when the span opens at zero (night decision N65): the
 *     move is unknown, not 0 %;
 *   - `annualizedPct` is null when the span is shorter than 30 days (30
 *     included is the first span with a rate); when `deltaPct` is null; when
 *     the growth factor 1 + Δ%/100, that is end ÷ start, is negative: a line
 *     that changes sign (the ruler measures indicator lines too) has no
 *     compounded rate, whatever 365/days makes of it (NaN for most spans, a
 *     finite number when 365/days is whole, at 73 or 365 days); and when the
 *     compounded result is not finite (an overflow), where the home gives None
 *     too;
 *   - a fall to exactly zero, a growth factor of 0, keeps its −100 %/yr: the
 *     home's «≤ −100 %» rule is not adopted.
 *
 * Before: a rate from one day on, 0 for zero days and for a zero start, a
 * number for a line that changes sign (NaN, or −103.125 % and −150 % over 73
 * and 365 days), Infinity on an overflow, and no floor exported. The tests
 * whose comment says "Red" fail on that code.
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

function markMissing(data: LineDataPoint[], date: string): LineDataPoint[] {
    return data.map((point) => (point.date === date ? {...point, missing: true} : point));
}

describe('MeasureSignal — default style', () => {
    it('ships a dotted orange line pinned at the start and arrowed at the end', () => {
        expect(MeasureSignal.getDefaultStyle()).toEqual({
            color: '#b85e45',
            lineWidth: 1,
            lineType: 'dotted',
            markerStart: 'pin',
            markerEnd: 'arrow',
        });
    });

    it('hands out a fresh style object each time, so one measure cannot recolour another', () => {
        const first = MeasureSignal.getDefaultStyle();
        first.color = '#000000';

        expect(MeasureSignal.getDefaultStyle().color).toBe('#b85e45');
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

    it.each([
        ['start', '2026-04-01'],
        ['end', '2026-04-04'],
    ] as const)('draws nothing when the %s endpoint is marked missing', (_endpoint, date) => {
        expect(measure('2026-04-01', '2026-04-04').computePoints(markMissing(chart, date))).toEqual([]);
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
        // Red (T-D9): zero days are under the 30-day floor, so the rate is null,
        // which the panel shows as «—». Before: annualizedPct 0. The Δ% stays 0:
        // the span opens at 60, and nothing moved.
        expect(measure('2026-04-02', '2026-04-02').getMeasurement(chart)).toMatchObject({
            deltaAbs: 0,
            deltaPct: 0,
            days: 0,
            annualizedPct: null,
        });
    });

    it('reports no percentage when the span opens at zero', () => {
        // Any move away from zero is an infinite gain; the absolute delta is the
        // only honest number left.
        // Red (N65): the Δ% is null («—»), unknown rather than 0 %, and so is the
        // annual rate. Before: deltaPct 0 and annualizedPct 0.
        const fromZero: LineDataPoint[] = [
            {date: '2026-04-01', value: 0},
            {date: '2026-04-02', value: 50},
        ];

        expect(measure('2026-04-01', '2026-04-02').getMeasurement(fromZero)).toMatchObject({
            deltaAbs: 50,
            deltaPct: null,
            annualizedPct: null,
        });
    });

    it('reports no annual rate when a span past the floor opens at zero', () => {
        // Red (N65): 73 days clear the 30-day floor, so only the missing Δ%
        // leaves the rate null. Before: deltaPct 0, and (1 + 0)^(365/73) − 1 = 0.
        const fromZero: LineDataPoint[] = [
            {date: '2026-01-01', value: 0},
            {date: '2026-03-15', value: 50}, // 73 days later
        ];

        expect(measure('2026-01-01', '2026-03-15').getMeasurement(fromZero)).toMatchObject({
            deltaAbs: 50,
            days: 73,
            deltaPct: null,
            annualizedPct: null,
        });
    });

    it('reports no annual rate under 30 days', () => {
        // Red (T-D9): +10% over 29 days would compound to ~232%/yr. The backend
        // home annualises nothing under 30 days, and neither does the ruler.
        // Before: (1.1^(365/29) − 1) × 100. The Δ% is untouched.
        const month: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-01-30', value: 110}, // 29 days later
        ];

        const result = measure('2026-01-01', '2026-01-30').getMeasurement(month)!;
        expect(result.days).toBe(29);
        expect(result.deltaPct).toBeCloseTo(10, 10);
        expect(result.annualizedPct).toBeNull();
    });

    it('annualises from exactly 30 days, by compounding', () => {
        // Guard: the floor is inclusive, 30 days is the first span with a rate.
        const month: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-01-31', value: 110}, // 30 days later
        ];

        const result = measure('2026-01-01', '2026-01-31').getMeasurement(month)!;
        expect(result.days).toBe(30);
        expect(result.annualizedPct).toBeCloseTo((Math.pow(1.1, 365 / 30) - 1) * 100, 6);
    });

    it('reports no annual rate when compounding leaves the finite numbers', () => {
        // Red (T-D9): a rate that is not a finite number is null, as the home's
        // cumulative_to_annualized gives None on a non-finite result. 100 → −50
        // over 60 days is a Δ% of −150, a growth factor of −0.5, and a negative
        // base raised to 365/60 is NaN (the sign rule of the next test nulls it
        // as well); the Δ% stays −150. Before: annualizedPct NaN.
        const crossing: LineDataPoint[] = [
            {date: '2026-01-01', value: 100},
            {date: '2026-03-02', value: -50}, // 60 days later
        ];
        expect(measure('2026-01-01', '2026-03-02').getMeasurement(crossing)).toMatchObject({days: 60, deltaAbs: -150, deltaPct: -150, annualizedPct: null});

        // The other way out of the finite numbers is an overflow: 1 → 10^30 in 30
        // days compounds to about 10^365, past the largest double. Neither a check
        // for NaN nor the sign rule catches it. Before: annualizedPct Infinity.
        const overflow: LineDataPoint[] = [
            {date: '2026-01-01', value: 1},
            {date: '2026-01-31', value: 1e30}, // 30 days later
        ];
        expect(measure('2026-01-01', '2026-01-31').getMeasurement(overflow), 'an overflow to Infinity is not a finite rate either').toMatchObject({days: 30, annualizedPct: null});
    });

    it('reports no annual rate for a line that changes sign, even where compounding gives a number', () => {
        // Red (T-D9): a growth factor 1 + Δ%/100 (end ÷ start) below zero has no
        // compounded rate. 100 → −50 is a Δ% of −150, a factor of −0.5, and when
        // 365/days is a whole number its power is finite, so the non-finite check
        // alone would keep it. Before: over 73 days ((−0.5)^5 − 1) × 100 =
        // −103.125%/yr, over 365 days (−0.5 − 1) × 100 = −150%/yr. The Δ% stays
        // −150 in both.
        const changesSign = (endDate: string): LineDataPoint[] => [
            {date: '2026-01-01', value: 100},
            {date: endDate, value: -50},
        ];

        expect(measure('2026-01-01', '2026-03-15').getMeasurement(changesSign('2026-03-15'))).toMatchObject({days: 73, deltaAbs: -150, deltaPct: -150, annualizedPct: null});
        expect(measure('2026-01-01', '2027-01-01').getMeasurement(changesSign('2027-01-01'))).toMatchObject({days: 365, deltaAbs: -150, deltaPct: -150, annualizedPct: null});
    });

    it('keeps −100%/yr for a fall to exactly zero over 30 days or more', () => {
        // Guard: a fall to exactly zero is a growth factor of 0, not below it, and
        // (1 − 1)^(365/days) − 1 is −1, a finite rate, so it stays. The home gives
        // None for any return of −100% or less; the ruler drops only a negative
        // factor (coordinator, CP-14b).
        const wipedOut = (endDate: string): LineDataPoint[] => [
            {date: '2026-01-01', value: 100},
            {date: endDate, value: 0},
        ];

        expect(measure('2026-01-01', '2026-01-31').getMeasurement(wipedOut('2026-01-31'))).toMatchObject({days: 30, deltaPct: -100, annualizedPct: -100});
        expect(measure('2026-01-01', '2026-03-02').getMeasurement(wipedOut('2026-03-02'))).toMatchObject({days: 60, deltaPct: -100, annualizedPct: -100});
    });

    it('has nothing to report until both endpoints exist on the chart', () => {
        expect(measure('', '2026-04-04').getMeasurement(chart)).toBeNull();
        expect(measure('2026-04-01', '').getMeasurement(chart)).toBeNull();
        expect(measure('2026-03-30', '2026-04-04').getMeasurement(chart)).toBeNull();
        expect(measure('2026-04-01', '2026-04-09').getMeasurement(chart)).toBeNull();
    });

    it.each([
        ['start', '2026-04-01'],
        ['end', '2026-04-04'],
    ] as const)('has nothing to report when the %s endpoint is marked missing', (_endpoint, date) => {
        expect(measure('2026-04-01', '2026-04-04').getMeasurement(markMissing(chart, date))).toBeNull();
    });

    it('continues to measure Price endpoints explicitly marked available', () => {
        const available = chart.map((point) => ({...point, missing: false}));
        const ruler = measure('2026-04-01', '2026-04-04');

        expect(values(ruler.computePoints(available))).toEqual([100, 110, 120, 130]);
        expect(ruler.getMeasurement(available)).toMatchObject({
            startValue: 100,
            endValue: 130,
            deltaAbs: 30,
            deltaPct: 30,
            days: 3,
        });
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
        // Red (T-D9): three days are under the 30-day floor, so the rate is null.
        // Before: annualizedPct 0, from the old `days > 0` test on the signed
        // day count (−3).
        const reversed = measure('2026-04-04', '2026-04-01');

        expect(reversed.getMeasurement(chart)).toMatchObject({days: 3, deltaAbs: -30, annualizedPct: null});
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
        // +10% held for 73 days — a fifth of a year — compounds to 61.05%/yr on an
        // overlay as on the chart. This test used to annualise the 3-day `overlay`
        // above (+25%, about 6·10^13 %/yr): under the 30-day floor that span has
        // no rate any more (T-D9), pinned by the next test.
        const yearly: LineDataPoint[] = [
            {date: '2026-01-01', value: 20},
            {date: '2026-03-15', value: 22}, // 73 days later
        ];

        const result = measure('2026-01-01', '2026-03-15').getMeasurementForSignal(yearly)!;
        expect(result.deltaPct).toBeCloseTo(10, 10);
        expect(result.annualizedPct).toBeCloseTo(61.051, 3);
    });

    it('gives the overlay no annual rate under 30 days, like the chart', () => {
        // Red (T-D9). Before: the 3-day overlay compounded to (1.25^(365/3) − 1) × 100,
        // the 29-day one to (1.25^(365/29) − 1) × 100. The Δ% is untouched.
        expect(measure('2026-04-01', '2026-04-04').getMeasurementForSignal(overlay)).toMatchObject({deltaPct: 25, annualizedPct: null});
        expect(
            measure('2026-01-01', '2026-01-30').getMeasurementForSignal([
                {date: '2026-01-01', value: 20},
                {date: '2026-01-30', value: 25}, // 29 days later
            ]),
        ).toMatchObject({deltaPct: 25, annualizedPct: null});
    });

    it('annualises the overlay from exactly 30 days', () => {
        // Guard: the floor is inclusive on the overlay too.
        const result = measure('2026-01-01', '2026-01-31').getMeasurementForSignal([
            {date: '2026-01-01', value: 20},
            {date: '2026-01-31', value: 25}, // 30 days later
        ])!;
        expect(result.annualizedPct).toBeCloseTo((Math.pow(1.25, 365 / 30) - 1) * 100, 6);
    });

    it('gives the overlay no annual rate when compounding leaves the finite numbers', () => {
        // Red (T-D9), as on the chart. An overlay crossing zero, 20 → −10 over 60
        // days: Δ% −150, growth factor −0.5, NaN once compounded. Before:
        // annualizedPct NaN. Then an overflow, 2 → 2·10^30 in 30 days. Before:
        // annualizedPct Infinity.
        expect(
            measure('2026-01-01', '2026-03-02').getMeasurementForSignal([
                {date: '2026-01-01', value: 20},
                {date: '2026-03-02', value: -10}, // 60 days later
            ]),
        ).toMatchObject({deltaAbs: -30, deltaPct: -150, annualizedPct: null});
        expect(
            measure('2026-01-01', '2026-01-31').getMeasurementForSignal([
                {date: '2026-01-01', value: 2},
                {date: '2026-01-31', value: 2e30}, // 30 days later
            ]),
            'an overflow to Infinity is not a finite rate either',
        ).toMatchObject({annualizedPct: null});
    });

    it('gives the overlay no annual rate when it changes sign, even where compounding gives a number', () => {
        // Red (T-D9), as on the chart: 100 → −50, a growth factor of −0.5. Before:
        // −103.125%/yr over 73 days, −150%/yr over 365. The Δ% stays −150.
        const changesSign = (endDate: string): LineDataPoint[] => [
            {date: '2026-01-01', value: 100},
            {date: endDate, value: -50},
        ];

        expect(measure('2026-01-01', '2026-03-15').getMeasurementForSignal(changesSign('2026-03-15'))).toMatchObject({deltaAbs: -150, deltaPct: -150, annualizedPct: null});
        expect(measure('2026-01-01', '2027-01-01').getMeasurementForSignal(changesSign('2027-01-01'))).toMatchObject({deltaAbs: -150, deltaPct: -150, annualizedPct: null});
    });

    it('keeps −100%/yr for an overlay that falls to exactly zero over 30 days or more', () => {
        // Guard: a growth factor of 0 is not negative: the same finite −100% as on the chart.
        const wipedOut = (endDate: string): LineDataPoint[] => [
            {date: '2026-01-01', value: 20},
            {date: endDate, value: 0},
        ];

        expect(measure('2026-01-01', '2026-01-31').getMeasurementForSignal(wipedOut('2026-01-31'))).toMatchObject({deltaPct: -100, annualizedPct: -100});
        expect(measure('2026-01-01', '2026-03-02').getMeasurementForSignal(wipedOut('2026-03-02'))).toMatchObject({deltaPct: -100, annualizedPct: -100});
    });

    it('returns nothing for an overlay that has no point on those dates', () => {
        // A benchmark that starts later than the measure is simply not comparable.
        expect(measure('2026-04-01', '2026-04-04').getMeasurementForSignal([{date: '2026-04-02', value: 20}])).toBeNull();
        expect(measure('2026-04-01', '2026-04-04').getMeasurementForSignal([])).toBeNull();
    });

    it('returns nothing when either overlay endpoint is marked missing', () => {
        const ruler = measure('2026-04-01', '2026-04-04');

        expect(ruler.getMeasurementForSignal(markMissing(overlay, '2026-04-01'))).toBeNull();
        expect(ruler.getMeasurementForSignal(markMissing(overlay, '2026-04-04'))).toBeNull();
    });

    it('has nothing to report before both dates have been picked', () => {
        expect(measure('', '').getMeasurementForSignal(overlay)).toBeNull();
        expect(measure('2026-04-01', undefined).getMeasurementForSignal(overlay)).toBeNull();
    });

    it('reports no percentage when the overlay opens at zero', () => {
        // Red (N65): null, as on the chart, and no annual rate without a Δ%.
        // Before: deltaPct 0 and annualizedPct 0.
        expect(
            measure('2026-04-01', '2026-04-04').getMeasurementForSignal([
                {date: '2026-04-01', value: 0},
                {date: '2026-04-04', value: 8},
            ]),
        ).toMatchObject({deltaAbs: 8, deltaPct: null, annualizedPct: null});
        // 73 days clear the floor: only the missing Δ% leaves the rate null.
        expect(
            measure('2026-01-01', '2026-03-15').getMeasurementForSignal([
                {date: '2026-01-01', value: 0},
                {date: '2026-03-15', value: 8},
            ]),
        ).toMatchObject({deltaAbs: 8, deltaPct: null, annualizedPct: null});
    });

    it('reports no annual rate for a zero-length span on the overlay either', () => {
        // Red (T-D9). Before: annualizedPct 0. The Δ% stays 0: the overlay opens at 20.
        expect(measure('2026-04-01', '2026-04-01').getMeasurementForSignal(overlay)).toMatchObject({deltaAbs: 0, deltaPct: 0, annualizedPct: null});
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

/*
 * The backend's floor is read from its source, by regex, as assetTypeTables.test.ts
 * and allocationTypeEmoji.test.ts read backend/app/db/models.py: `node:fs` from the
 * repository root. `_MIN_ANNUALIZATION_DAYS` is private to returns.py and reaches
 * no API or generated client, so the source is the only copy that is not the
 * frontend's own.
 */
const HERE = path.dirname(fileURLToPath(import.meta.url));
/** `__tests__` → `signals` → `charts` → `lib` → `src` → `frontend` → the repository */
const REPO_DIR = path.resolve(HERE, '..', '..', '..', '..', '..', '..');
const RETURNS_PY = path.join(REPO_DIR, 'backend', 'app', 'services', 'financial_math', 'returns.py');

function backendMinAnnualizationDays(): number {
    expect(existsSync(RETURNS_PY), `${RETURNS_PY} does not exist: the parity test reads the backend floor there, so a move or a rename must stop it rather than compare nothing`).toBe(true);
    const assignments = [...readFileSync(RETURNS_PY, 'utf-8').matchAll(/^_MIN_ANNUALIZATION_DAYS[ \t]*(?::[ \t]*int[ \t]*)?=[ \t]*(\d+)[ \t]*(?:#.*)?$/gm)];
    expect(assignments.length, 'backend/app/services/financial_math/returns.py: expected exactly one module-level "_MIN_ANNUALIZATION_DAYS = <integer>"').toBe(1);
    return Number(assignments[0][1]);
}

describe('MeasureSignal — the annualisation floor', () => {
    it('is the floor of the backend home, one constant exported by MeasureSignal.ts', () => {
        // Red (T-D9). Before: MeasureSignal.ts exports no floor (undefined) and
        // annualises any span of at least one day.
        const backendFloor = backendMinAnnualizationDays();
        expect(backendFloor, 'the 29- and 30-day spans of this file sit on the backend floor: move them with it').toBe(30);
        expect(MIN_ANNUALIZATION_DAYS).toBe(backendFloor);
    });
});

/*
 * The Δ% rule of night decision N65 — a change measured from a start of 0 has
 * no percentage: the move is unknown, not 0 % — has a second copy outside the
 * ruler: `buildDeltaHtml` in components/charts/priceChartHelpers.ts, the
 * «(Δ …)» suffix of the price chart's tooltip, which still gives 0 % from a zero
 * start (backlog J-44). The ruler's `changePct` becomes the one copy, exported
 * for the tooltip to read. It is imported inside the test, not at the top of
 * the file, so that while the export is missing only this test fails and the
 * rest of the file still loads.
 */
describe('MeasureSignal — the Δ% rule, one copy exported (J-44)', () => {
    it('exports changePct: (end − start) ÷ start in %, null when the span opens at zero', async () => {
        // Red (J-44, N65). Before: `changePct` is private to MeasureSignal.ts, so
        // the import reads undefined; getMeasurement and getMeasurementForSignal
        // already give the values below.
        const {changePct} = await import('../MeasureSignal');
        expect(changePct, 'barrier: MeasureSignal.ts exports changePct').toBeTypeOf('function');

        expect(changePct(100, 110), 'a gain').toBeCloseTo(10, 10);
        expect(changePct(100, 0), 'a fall to exactly zero is a known move').toBe(-100);
        expect(changePct(0, 8), 'a span that opens at zero has no percentage (N65)').toBeNull();
        expect(changePct(0, 0), 'nor has one that stays at zero').toBeNull();
        // −50 → −25 reads −50 %: the plain formula over the signed start, not
        // +50 % over its absolute value.
        expect(changePct(-50, -25), 'a negative start keeps the plain formula, (end − start) ÷ start').toBeCloseTo(-50, 10);
    });
});
