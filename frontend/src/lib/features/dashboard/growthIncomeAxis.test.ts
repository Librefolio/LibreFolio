/**
 * growthIncomeAxis — the lower edge of the Income chart's y axis (G4, B9).
 *
 * With costs of 80 € ECharts put the edge at −2k, a whole tick under the bar. The edge is now just below the largest cost, at a small round
 * number, and 0 when nothing hangs below zero.
 */
import {describe, expect, it} from 'vitest';
import {incomeAxisMin} from './growthIncomeAxis';

describe('incomeAxisMin', () => {
    it.each([undefined, 0, 12, 20_000])('no costs (lowest value %s): the edge is 0', (min) => {
        expect(incomeAxisMin(min === undefined ? Number.NaN : min, 1_000)).toBe(0);
    });

    it('a non-finite edge is 0, never NaN or −Infinity', () => {
        expect(incomeAxisMin(Number.NEGATIVE_INFINITY)).toBe(0);
        expect(incomeAxisMin(Number.NaN, 10)).toBe(0);
    });

    it('costs of 80 € under bars of 1 000 €: the edge is −90, not −2k', () => {
        expect(incomeAxisMin(-80, 1_000)).toBe(-90);
    });

    it.each([
        [-80, 1_000, -90],
        [-25, 400, -30],
        [-1_234, 5_000, -1_500],
        [-1_900, 9_000, -2_500],
        [-4_000, 9_000, -4_500],
        [-12, 200, -15],
    ])('the lowest value %s: a round number just below it (%s → %s)', (min, max, edge) => {
        expect(incomeAxisMin(min, max)).toBe(edge);
    });

    it('is always at or below the lowest value, and never more than 30% lower', () => {
        for (const cost of [3, 7.5, 18, 80, 99, 101, 640, 1_000, 2_345, 87_654, 1_250_000]) {
            const edge = incomeAxisMin(-cost, cost * 3);
            expect(edge, `cost ${cost}`).toBeLessThan(-cost);
            expect(edge, `cost ${cost}`).toBeGreaterThanOrEqual(-cost * 1.3);
        }
    });

    it("keeps the label clear of the zero's: a tiny cost under tall bars goes down by a twentieth of the span at least", () => {
        const edge = incomeAxisMin(-20, 20_000);
        expect(edge).toBeLessThanOrEqual(-(20_020 * 0.05));
        expect(edge).toBe(-1_200);
    });

    it('prints no floating-point dust: 1.2 × 1000 is exactly 1200', () => {
        expect(incomeAxisMin(-1_000, 4_000)).toBe(-1_200);
        expect(String(incomeAxisMin(-0.011, 1))).not.toMatch(/0000|9999/);
    });

    it('is a number the axis can take: negative, finite', () => {
        const edge = incomeAxisMin(-0.4, 3);
        expect(Number.isFinite(edge)).toBe(true);
        expect(edge).toBeLessThan(0);
    });
});
