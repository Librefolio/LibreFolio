/**
 * Contract tests for the incremental merge of new price points into the asset detail chart
 * (FE5c, piece 2: moved out of the page verbatim).
 *
 * The page merges a sync answer's `changed_points` and a polled live point into its chart data.
 * The merge must keep the fields only the chart load knows (`original_close`), keep the timeline
 * in date order, and never touch the arrays or the points it is given.
 */
import {describe, expect, it} from 'vitest';
import {mergeChartPointsIncremental} from './assetDetailChartPoints';

interface ChartPoint {
    date: string;
    close?: number;
    open?: number;
    volume?: number;
    original_close?: number;
}

function point(date: string, close: number, extra: Omit<ChartPoint, 'date' | 'close'> = {}): ChartPoint {
    return {date, close, ...extra};
}

describe('mergeChartPointsIncremental: the existing points with the delta merged in by date, sorted by date, the inputs untouched', () => {
    it('appends a point for a new date', () => {
        const existing = [point('2026-02-02', 12)];

        expect(mergeChartPointsIncremental(existing, [point('2026-02-03', 13)])).toEqual([point('2026-02-02', 12), point('2026-02-03', 13)]);
    });

    it('merges a known date shallowly: the delta fields win, the fields only the existing point has stay', () => {
        const existing = [point('2026-02-02', 12, {open: 11, original_close: 14})];

        expect(mergeChartPointsIncremental(existing, [point('2026-02-02', 12.5, {volume: 300})])).toEqual([{date: '2026-02-02', open: 11, close: 12.5, volume: 300, original_close: 14}]);
    });

    it('sorts the result by date, whatever the order of either input', () => {
        const existing = [point('2026-01-05', 15), point('2025-12-31', 11)];
        const delta = [point('2026-01-02', 13), point('2025-12-30', 9)];

        expect(mergeChartPointsIncremental(existing, delta).map((merged) => merged.date)).toEqual(['2025-12-30', '2025-12-31', '2026-01-02', '2026-01-05']);
    });

    it('merges repeated dates of the delta in order: the later one wins, on top of the earlier one', () => {
        const existing = [point('2026-02-02', 12, {original_close: 14})];
        const delta = [point('2026-02-02', 12.5, {volume: 300}), point('2026-02-02', 12.8), point('2026-02-04', 14, {volume: 50}), point('2026-02-04', 14.2)];

        expect(mergeChartPointsIncremental(existing, delta)).toEqual([point('2026-02-02', 12.8, {original_close: 14, volume: 300}), point('2026-02-04', 14.2, {volume: 50})]);
    });

    it('leaves both inputs and their points untouched', () => {
        const existing = [point('2026-02-03', 13, {original_close: 15}), point('2026-02-01', 11)];
        const delta = [point('2026-02-03', 13.5), point('2026-02-02', 12)];
        const existingPoints = [...existing];
        const existingBefore = structuredClone(existing);
        const deltaBefore = structuredClone(delta);

        const merged = mergeChartPointsIncremental(existing, delta);

        expect(merged.map((mergedPoint) => mergedPoint.date)).toEqual(['2026-02-01', '2026-02-02', '2026-02-03']);
        expect(existing).toEqual(existingBefore);
        expect(existing.every((existingPoint, index) => existingPoint === existingPoints[index])).toBe(true);
        expect(delta).toEqual(deltaBefore);
        // The merged point of a known date is a new object, not the existing one updated in place.
        expect(merged.find((mergedPoint) => mergedPoint.date === '2026-02-03')).not.toBe(existingPoints.find((existingPoint) => existingPoint.date === '2026-02-03'));
    });

    it('returns a new array, also for an empty delta', () => {
        const existing = [point('2026-02-01', 11), point('2026-02-02', 12)];

        const merged = mergeChartPointsIncremental(existing, []);

        expect(merged).not.toBe(existing);
        expect(merged).toEqual(existing);
    });

    it('takes the sorted delta as the result when there are no existing points', () => {
        expect(mergeChartPointsIncremental([], [point('2026-02-02', 12), point('2026-02-01', 11)])).toEqual([point('2026-02-01', 11), point('2026-02-02', 12)]);
        expect(mergeChartPointsIncremental<ChartPoint>([], [])).toEqual([]);
    });
});
