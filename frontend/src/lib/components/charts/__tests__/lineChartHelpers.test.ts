/**
 * lineChartHelpers.test.ts — Unit tests for buildMainSeries() segment coloring/merging.
 *
 * @module components/charts/__tests__/lineChartHelpers.test
 */
import {describe, expect, it} from 'vitest';

import {buildMainSeries, hexToRgba} from '../lineChartHelpers';

const BASE_COLOR = '#1a4031';
const GREEN = '#16a34a';
const RED = '#ef4444';

describe('buildMainSeries', () => {
    it('colors a simple two-segment baseline crossing correctly (no merging needed)', () => {
        const values = [10, 10, 10, -5, -5, -5];
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);

        // 2 segments expected: green (above baseline) then red (below).
        expect(result.length).toBe(2);
        expect(result[0].itemStyle.color).toBe(hexToRgba(GREEN, 1));
        expect(result[1].itemStyle.color).toBe(hexToRgba(RED, 1));
    });

    it('keeps a single color as one series when there is no baseline crossing', () => {
        const values = new Array(50).fill(10);
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);
        expect(result.length).toBe(1);
        expect(result[0].itemStyle.color).toBe(hexToRgba(GREEN, 1));
    });

    it('caps series count for a pathologically choppy baseline-crossing series (perf guard)', () => {
        // Alternating short runs (2-3 points each) crossing the baseline hundreds of
        // times — simulates decades of volatile daily prices. Without the Step 2b
        // merge cap in buildMainSeries, this would produce hundreds of ECharts series
        // (each a full-length array), which is what made a real setOption() call take
        // multiple seconds (see impl_plan_chart_resolution bugfix history).
        const values: number[] = [];
        for (let i = 0; i < 1000; i++) {
            values.push(i % 4 < 2 ? 10 : -10);
        }
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);

        expect(result.length).toBeLessThanOrEqual(150);
    });

    it('recomputes the MAJORITY color when merging short segments — regression test for the "stays green below 0%" bug', () => {
        // Regression test for a real user-reported bug: a below-baseline (red) span
        // was rendered as green after the Step 2b micro-segment merge was introduced,
        // because the merge only extended `last.end` without recomputing `last.color`
        // — so a merged block always kept whichever color happened to be first,
        // regardless of how much of its ACTUAL range was the opposite sign.
        //
        // Pattern: a 1-point ABOVE-baseline "anchor" point, followed by a 4-point
        // BELOW-baseline run, repeated many times — every cycle is short enough to be
        // merged (forced by making the whole series highly fragmented), and in each
        // merged block the below-baseline (red) points substantially outnumber the
        // anchor (green) point. The correct rendered color for the whole thing must be
        // predominantly RED, matching the true majority — not GREEN (the old, buggy,
        // "first segment wins" behavior).
        const values: number[] = [];
        for (let i = 0; i < 150; i++) {
            values.push(5); // 1 point above baseline (would-be anchor)
            values.push(-5, -5, -5, -5); // 4 points below baseline
        }
        const staleDays = values.map(() => 0);
        const result = buildMainSeries(values, staleDays, BASE_COLOR, GREEN, RED, false, false, 2, 'Value', true, 0, false);

        // The whole series collapses under the merge cap (750 points, 300 original
        // segments) — the resulting color must reflect the true 4:1 red majority.
        const colors = result.map((s) => s.itemStyle.color);
        expect(colors).not.toContain(hexToRgba(GREEN, 1));
        expect(colors).toContain(hexToRgba(RED, 1));
    });
});
