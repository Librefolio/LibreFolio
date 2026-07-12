/**
 * assetPriceDerived.test.ts — Unit tests for the pure price-derived-state computation
 * extracted from the Assets list page (see assetPriceDerived.ts header for rationale).
 *
 * @module utils/__tests__/assetPriceDerived.test
 */
import {describe, expect, it} from 'vitest';

import {computeDerivedPriceState, computePeriodDelta, DELTA_PERIODS} from '../assetPriceDerived';

describe('computePeriodDelta', () => {
    it('computes a simple positive delta over a period', () => {
        const chartData = [
            {date: '2026-01-01', value: 100},
            {date: '2026-01-08', value: 110},
        ];
        expect(computePeriodDelta(chartData, 7)).toBeCloseTo(10, 5);
    });

    it('returns null for an empty series', () => {
        expect(computePeriodDelta([], 7)).toBeNull();
    });

    it('returns null when the last value is 0', () => {
        expect(computePeriodDelta([{date: '2026-01-01', value: 0}], 7)).toBeNull();
    });

    it('backward-fills to the closest point at or before the target date', () => {
        const chartData = [
            {date: '2026-01-01', value: 100},
            {date: '2026-01-03', value: 105}, // no data for 01-02 (e.g. weekend)
            {date: '2026-01-08', value: 110},
        ];
        // Target for a 5-day lookback from 01-08 is 01-03 -> should hit the 01-03 point.
        expect(computePeriodDelta(chartData, 5)).toBeCloseTo(((110 - 105) / 105) * 100, 5);
    });

    it('matches results for very long histories regardless of scan direction (regression: forward vs backward scan)', () => {
        // Build ~10 years of daily data and confirm the backward-scan implementation
        // used here gives the same answer a naive forward scan would.
        const chartData: Array<{date: string; value: number}> = [];
        const start = new Date('2016-01-01T00:00:00Z');
        for (let i = 0; i < 3650; i++) {
            const d = new Date(start.getTime() + i * 86400000);
            chartData.push({date: d.toISOString().slice(0, 10), value: 100 + i * 0.01});
        }

        function forwardScan(data: typeof chartData, periodDays: number): number | null {
            const pn = data[data.length - 1];
            const targetDate = new Date(pn.date);
            targetDate.setDate(targetDate.getDate() - periodDays);
            const targetStr = targetDate.toISOString().slice(0, 10);
            let startPoint: {date: string; value: number} | null = null;
            for (const point of data) {
                if (point.date <= targetStr) startPoint = point;
                else break;
            }
            if (!startPoint) return null;
            return ((pn.value - startPoint.value) / startPoint.value) * 100;
        }

        for (const days of [7, 30, 365, 1825]) {
            expect(computePeriodDelta(chartData, days)).toBeCloseTo(forwardScan(chartData, days) ?? NaN, 9);
        }
    });
});

describe('computeDerivedPriceState', () => {
    it('returns empty/null state for an empty price array', () => {
        const result = computeDerivedPriceState([]);
        expect(result).toEqual({lastPrice: null, deltaAbs: null, deltaPercent: null, chartData: [], deltas: {}});
    });

    it('computes lastPrice, deltaAbs, deltaPercent, chartData, and all DELTA_PERIODS deltas', () => {
        const prices = [
            {date: '2026-01-01', close: '100'},
            {date: '2026-01-08', close: '110'},
        ];
        const result = computeDerivedPriceState(prices);
        expect(result.lastPrice).toBe(110);
        expect(result.deltaAbs).toBeCloseTo(10, 5);
        expect(result.deltaPercent).toBeCloseTo(10, 5);
        expect(result.chartData).toEqual([
            {date: '2026-01-01', value: 100, staleDays: 0},
            {date: '2026-01-08', value: 110, staleDays: 0},
        ]);
        expect(Object.keys(result.deltas)).toEqual(DELTA_PERIODS.map((p) => p.key));
    });

    it('reads staleDays from backward_fill_info.days_back when present', () => {
        const prices = [{date: '2026-01-01', close: '100', backward_fill_info: {days_back: 3}}];
        const result = computeDerivedPriceState(prices);
        expect(result.chartData[0].staleDays).toBe(3);
    });

    it('falls back to legacy camelCase backwardFillInfo.daysBack when snake_case is absent', () => {
        const prices = [{date: '2026-01-01', close: '100', backwardFillInfo: {daysBack: 5}}];
        const result = computeDerivedPriceState(prices);
        expect(result.chartData[0].staleDays).toBe(5);
    });

    it('defaults staleDays to 0 for a malformed/unexpected backward_fill_info shape', () => {
        const prices = [{date: '2026-01-01', close: '100', backward_fill_info: []}];
        const result = computeDerivedPriceState(prices);
        expect(result.chartData[0].staleDays).toBe(0);
    });

    it('treats a zero first price as "no delta" (avoids division by zero)', () => {
        const prices = [
            {date: '2026-01-01', close: '0'},
            {date: '2026-01-08', close: '10'},
        ];
        const result = computeDerivedPriceState(prices);
        expect(result.deltaAbs).toBeNull();
        expect(result.deltaPercent).toBeNull();
    });
});
