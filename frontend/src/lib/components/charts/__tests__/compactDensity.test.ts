/**
 * Z-29b (MF n1): the rule that sizes a card's price series, tied to the case table the backend reads
 * (`compactDensityCases.json`, `test_price_query_sampling.py`): the `max_points` a card sends, the step the browser's rule
 * and the backend's `choose_resolution()` give for it, and the counts of days and weeks of a fill.
 */
import {readFileSync} from 'node:fs';

import {describe, expect, it} from 'vitest';

import {COMPACT_DENSITY_THRESHOLD, COMPACT_GRID_LEFT_PX, COMPACT_GRID_RIGHT_PX, COMPACT_GRID_RIGHT_WITH_AXIS_PX, DEFAULT_COMPACT_PLOT_WIDTH_PX, chooseCompactResolution, compactMaxPoints, compactPlotWidth, fillCounts, stepForMaxPoints, type ChartResolution} from '../timeSeriesAggregation';

interface DensityCase {
    note: string;
    first: string;
    end: string;
    plot_width_px: number;
    days: number;
    weeks: number;
    max_points: number;
    resolution: ChartResolution;
}

const table = JSON.parse(readFileSync(new URL('./compactDensityCases.json', import.meta.url), 'utf8')) as {threshold: number; cases: DensityCase[]};

describe('compact density rule (Z-29b)', () => {
    it('keeps the threshold of the table: 1.3 points per pixel', () => {
        expect(table.threshold).toBe(COMPACT_DENSITY_THRESHOLD);
        expect(COMPACT_DENSITY_THRESHOLD).toBe(1.3);
    });

    it.each(table.cases.map((c) => [c.note, c] as const))('sends the max_points of the table for %s', (_note, c) => {
        expect(compactMaxPoints(c.plot_width_px)).toBe(c.max_points);
    });

    it.each(table.cases.map((c) => [c.note, c] as const))('counts the days and weeks of the fill of %s', (_note, c) => {
        const counts = fillCounts(c.first, c.end);
        expect([counts.days, counts.weeks]).toEqual([c.days, c.weeks]);
    });

    it.each(table.cases.map((c) => [c.note, c] as const))("gives the step of the table for %s, from the plot's width and from the max_points it sends", (_note, c) => {
        expect(chooseCompactResolution({dailyCount: c.days, weeklyCount: c.weeks}, c.plot_width_px)).toBe(c.resolution);
        expect(stepForMaxPoints({days: c.days, weeks: c.weeks}, compactMaxPoints(c.plot_width_px))).toBe(c.resolution);
    });

    it('counts the weeks and months a fill touches, Monday to Sunday and by calendar month', () => {
        // Sunday 11 Jan to Monday 12 Jan 2026: two days, two ISO weeks, one month.
        expect(fillCounts('2026-01-11', '2026-01-12')).toEqual({days: 2, weeks: 2, months: 1});
        expect(fillCounts('2026-01-12', '2026-01-18')).toEqual({days: 7, weeks: 1, months: 1});
        expect(fillCounts('2025-12-31', '2026-01-01')).toEqual({days: 2, weeks: 1, months: 2});
        expect(fillCounts('2026-03-05', '2026-03-05')).toEqual({days: 1, weeks: 1, months: 1});
    });

    it('bounds max_points by the backend: at least 1, at most 10000, whatever the width', () => {
        expect(compactMaxPoints(0)).toBe(1);
        expect(compactMaxPoints(-30)).toBe(1);
        expect(compactMaxPoints(Number.NaN)).toBe(1);
        expect(compactMaxPoints(100000)).toBe(10000);
    });

    it("takes the plot's width out of the card's chart: the grid's left and right paddings, the mini axis's room", () => {
        expect(COMPACT_GRID_LEFT_PX + COMPACT_GRID_RIGHT_WITH_AXIS_PX).toBe(50);
        expect(compactPlotWidth(340)).toBe(290);
        expect(compactPlotWidth(340, false)).toBe(340 - COMPACT_GRID_LEFT_PX - COMPACT_GRID_RIGHT_PX);
        expect(compactPlotWidth(20)).toBe(0);
        expect(compactMaxPoints(DEFAULT_COMPACT_PLOT_WIDTH_PX)).toBeGreaterThan(100);
    });

    it('goes monthly when not even the weeks fit, and never below weekly or daily when they do', () => {
        expect(stepForMaxPoints({days: 100, weeks: 15}, 100)).toBe('daily');
        expect(stepForMaxPoints({days: 101, weeks: 15}, 100)).toBe('weekly');
        expect(stepForMaxPoints({days: 5000, weeks: 700}, 100)).toBe('monthly');
    });
});
