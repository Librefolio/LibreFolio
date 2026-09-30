/**
 * lineChartHelpers.sessionGaps.test.ts — the confidence band on a calendar axis with session-only points.
 *
 * Indicators compute on quote days (developer's decision of 30/09/2026): a Bollinger or Donchian
 * signal has a point on each session only, while the chart's date axis keeps every calendar day.
 *
 * The fill is two stacked series, an invisible lower base and the delta above it. Where a stacked
 * series' base is null ECharts takes the axis origin as its bottom, and `connectNulls` only skips
 * the top points, so the fill's lower edge would fall to the axis on every weekend. The two fill
 * series therefore hold, on the days strictly between two points, the straight line between the
 * two neighbours by axis position; they stay null before the first point and after the last one,
 * and set no `connectNulls`. The middle line is the signal itself: null on the days without a
 * point, connected across them, never an invented value.
 *
 * @module components/charts/lineChartHelpers.sessionGaps.test
 */
import {describe, expect, it} from 'vitest';

import type {RenderedSignal} from '$lib/charts/signals';
import {buildBandSeries} from './lineChartHelpers';

// Saturday 3 to Sunday 18 January 2026: two weekend days before the first session, the weekend of
// 10-11 between the two weeks of sessions, and two weekend days after the last session.
const CALENDAR_AXIS = ['2026-01-03', '2026-01-04', '2026-01-05', '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09', '2026-01-10', '2026-01-11', '2026-01-12', '2026-01-13', '2026-01-14', '2026-01-15', '2026-01-16', '2026-01-17', '2026-01-18'];
const WEEKEND = new Set(['2026-01-03', '2026-01-04', '2026-01-10', '2026-01-11', '2026-01-17', '2026-01-18']);
const SESSIONS = CALENDAR_AXIS.filter((day) => !WEEKEND.has(day));
const HOLIDAY_MONDAY = '2026-01-12';

/**
 * A band signal as the backend renderer delivers it: one point per session. Session i has lower
 * 90 + i, middle 100 + i and upper 110 + 4·i, so the delta (20 + 3·i) climbs at a slope of its own
 * and its bridge is tested apart from the lower one.
 */
function sessionBand(label: string, sessions: string[] = SESSIONS): RenderedSignal {
    return {
        id: `${label.toLowerCase()}-1`,
        label,
        data: sessions.map((date, index) => ({date, value: 100 + index})),
        color: '#3355ff',
        lineWidth: 2,
        lineType: 'solid',
        markerStart: null,
        markerEnd: null,
        aggregationProfile: 'band_envelope',
        seriesType: 'band',
        bandData: {
            upper: sessions.map((_, index) => 110 + 4 * index),
            middle: sessions.map((_, index) => 100 + index),
            lower: sessions.map((_, index) => 90 + index),
        },
    };
}

/** Null where nothing is expected, `toBeCloseTo` everywhere else: interpolated values are fractions. */
function expectValues(actual: Array<number | null>, expected: Array<number | null>): void {
    expect(actual).toHaveLength(expected.length);
    expected.forEach((value, position) => {
        if (value === null) expect(actual[position], `${CALENDAR_AXIS[position]} should stay empty`).toBeNull();
        else expect(actual[position], CALENDAR_AXIS[position]).toBeCloseTo(value, 10);
    });
}

function valuePositions(values: Array<number | null>): number[] {
    return values.flatMap((value, position) => (value === null ? [] : [position]));
}

/** Axis positions strictly between the first and the last value that hold no value. */
function interiorNulls(values: Array<number | null>): number[] {
    const present = valuePositions(values);
    if (present.length === 0) return [];
    const [first, last] = [present[0], present[present.length - 1]];
    return values.flatMap((value, position) => (position > first && position < last && value === null ? [position] : []));
}

describe('buildBandSeries on sessions over a calendar axis', () => {
    describe.each(['Bollinger', 'Donchian'])('%s', (label) => {
        it('bridges the fill across the weekend between two sessions and leaves the days before and after empty', () => {
            // Premise: ten sessions on a sixteen-day axis.
            expect(SESSIONS).toHaveLength(10);

            const [lower, band] = buildBandSeries(sessionBand(label), CALENDAR_AXIS, false);

            // Friday 9 to Monday 12 is three axis steps: Saturday and Sunday hold 1/3 and 2/3 of the way.
            expectValues(lower.data, [null, null, 90, 91, 92, 93, 94, 94 + 1 / 3, 94 + 2 / 3, 95, 96, 97, 98, 99, null, null]);
            expectValues(band.data, [null, null, 20, 23, 26, 29, 32, 33, 34, 35, 38, 41, 44, 47, null, null]);
        });

        it('leaves no null inside the fill, the condition for ECharts to draw it', () => {
            const [lower, band] = buildBandSeries(sessionBand(label), CALENDAR_AXIS, false);

            // Premise: the fill runs from Monday 5 (position 2) to Friday 16 (position 13).
            const present = valuePositions(lower.data);
            expect([present[0], present[present.length - 1]]).toEqual([2, 13]);
            expect(interiorNulls(lower.data)).toEqual([]);
            expect(interiorNulls(band.data)).toEqual([]);
        });

        it('keeps the middle line on the sessions only', () => {
            const [, , middle] = buildBandSeries(sessionBand(label), CALENDAR_AXIS, false);

            expect(middle.data).toEqual([null, null, 100, 101, 102, 103, 104, null, null, 105, 106, 107, 108, 109, null, null]);
        });

        it('lets only the middle line connect the empty days', () => {
            const [lower, band, middle] = buildBandSeries(sessionBand(label), CALENDAR_AXIS, false);

            expect(lower).not.toHaveProperty('connectNulls');
            expect(band).not.toHaveProperty('connectNulls');
            expect(middle.connectNulls).toBe(true);
        });
    });

    it('bridges a longer gap, over a holiday Monday, by axis position', () => {
        const sessions = SESSIONS.filter((day) => day !== HOLIDAY_MONDAY);

        const [lower, band, middle] = buildBandSeries(sessionBand('Bollinger', sessions), CALENDAR_AXIS, false);

        // Friday 9 to Tuesday 13 is four axis steps: a quarter of the way per day.
        expectValues(lower.data, [null, null, 90, 91, 92, 93, 94, 94.25, 94.5, 94.75, 95, 96, 97, 98, null, null]);
        expectValues(band.data, [null, null, 20, 23, 26, 29, 32, 32.75, 33.5, 34.25, 35, 38, 41, 44, null, null]);
        expect(interiorNulls(lower.data)).toEqual([]);
        expect(interiorNulls(band.data)).toEqual([]);
        expect(middle.data).toEqual([null, null, 100, 101, 102, 103, 104, null, null, null, 105, 106, 107, 108, null, null]);
    });
});
