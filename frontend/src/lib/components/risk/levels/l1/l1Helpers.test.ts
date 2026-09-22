import {describe, expect, it} from 'vitest';

import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {DAILY_VAR_INSTANCE} from '../../riskAnalysisHelpers';
import {buildReturnHistogram, buildTailMeasures, buildUnderwater} from './l1Helpers';

/** A successful result carrying `output`, shaped like the API's. */
function ok(analyticCode: string, output: Record<string, unknown>, instanceId = `base-historical-${analyticCode}`): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'ok', output} as unknown as RiskAnalyticResult;
}

/** A result the backend could not compute. */
function unavailable(analyticCode: string, instanceId = `base-historical-${analyticCode}`): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'unavailable', output: null} as unknown as RiskAnalyticResult;
}

function bin(lower: number, upper: number, count: number): Record<string, unknown> {
    return {lower_bound: lower, upper_bound: upper, count};
}

function varResult(bins: Record<string, unknown>[], edge: number | null): RiskAnalyticResult {
    return ok('historical_var', {kind: 'var_cvar', return_bins: bins, var_bin_edge: edge}, DAILY_VAR_INSTANCE);
}

describe('buildUnderwater', () => {
    it('hands the chart percent units, because the chart converts nothing', () => {
        // `viewMode='percentage'` only relabels the axis; the series plots the
        // raw value. A decimal ratio here would draw the right shape against
        // numbers a hundred times too small.
        const points = buildUnderwater([ok('drawdown_summary', {underwater_series: [{date: '2024-01-02', drawdown: -0.123}]})]);
        expect(points).toEqual([{date: '2024-01-02', value: -12.3}]);
    });

    it('keeps each point on its own date rather than spreading them over the window', () => {
        const points = buildUnderwater([
            ok('drawdown_summary', {
                underwater_series: [
                    {date: '2024-01-02', drawdown: -0.01},
                    // A weekend gap: the series is shorter than the span it covers.
                    {date: '2024-01-08', drawdown: -0.04},
                ],
            }),
        ]);
        expect(points.map((point) => point.date)).toEqual(['2024-01-02', '2024-01-08']);
    });

    it('drops a point that contradicts its own le=0 convention instead of rescuing it', () => {
        const points = buildUnderwater([
            ok('drawdown_summary', {
                underwater_series: [
                    {date: '2024-01-02', drawdown: -0.05},
                    // Positive is impossible for a peak-relative drawdown. A
                    // `Math.abs` here would render it as a plausible −7%.
                    {date: '2024-01-03', drawdown: 0.07},
                ],
            }),
        ]);
        expect(points).toEqual([{date: '2024-01-02', value: -5}]);
    });

    it('prints a day at the peak as a plain zero, never as a negative one', () => {
        const [point] = buildUnderwater([ok('drawdown_summary', {underwater_series: [{date: '2024-01-02', drawdown: 0}]})]);
        // `toBe` compares with Object.is, so this fails on `-0` — which is the
        // whole point: `-0` reaches the axis formatter as "−0.0%".
        expect(point.value).toBe(0);
    });

    it('skips an entry with no usable date rather than inventing one', () => {
        const points = buildUnderwater([
            ok('drawdown_summary', {
                underwater_series: [{drawdown: -0.05}, {date: '2024-01-03', drawdown: -0.06}],
            }),
        ]);
        expect(points.map((point) => point.date)).toEqual(['2024-01-03']);
    });

    it('has nothing to draw when the analytic did not run', () => {
        expect(buildUnderwater([unavailable('drawdown_summary')])).toEqual([]);
        expect(buildUnderwater([])).toEqual([]);
        expect(buildUnderwater([ok('drawdown_summary', {})])).toEqual([]);
    });
});

describe('buildReturnHistogram', () => {
    it('locates the cut by inequality on a half-open interval, not by matching a float', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.03, -0.02, 4), bin(-0.02, -0.01, 9), bin(-0.01, 0, 20)], -0.015)]);
        expect(histogram?.bins.map((entry) => entry.holdsCut)).toEqual([false, true, false]);
    });

    it('gives the boundary to the bin that opens on it, and not to the one that closes there', () => {
        // `[lower, upper)`: an edge sitting exactly on a shared bound belongs to
        // the upper bin. Any equality-based search would claim both, or neither.
        const histogram = buildReturnHistogram([varResult([bin(-0.02, -0.01, 5), bin(-0.01, 0, 11)], -0.01)]);
        expect(histogram?.bins.map((entry) => entry.holdsCut)).toEqual([false, true]);
    });

    it('shades the run beyond the cut, and leaves the straddling bar out of it', () => {
        // The highlighted bar says where the number is; the shaded run says what
        // mass it is talking about. The bar holding the cut is in neither.
        const histogram = buildReturnHistogram([varResult([bin(-0.04, -0.03, 1), bin(-0.03, -0.02, 2), bin(-0.02, -0.01, 9), bin(-0.01, 0, 20)], -0.025)]);
        expect(histogram?.bins.map((entry) => entry.belowCut)).toEqual([true, false, false, false]);
        expect(histogram?.bins.map((entry) => entry.holdsCut)).toEqual([false, true, false, false]);
    });

    it('shades nothing when there is no cut to be beyond', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.02, -0.01, 5), bin(-0.01, 0, 20)], null)]);
        expect(histogram?.bins.every((entry) => !entry.belowCut)).toBe(true);
    });

    it('keeps a cut of exactly zero, which is a threshold at break-even and not a missing one', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.01, 0, 8), bin(0, 0.01, 12)], 0)]);
        expect(histogram?.cut).toBe(0);
        expect(histogram?.bins.map((entry) => entry.holdsCut)).toEqual([false, true]);
    });

    it('marks nothing when the backend published no cut at all', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.01, 0, 8), bin(0, 0.01, 12)], null)]);
        expect(histogram?.cut).toBeNull();
        expect(histogram?.bins.every((entry) => !entry.holdsCut)).toBe(true);
    });

    it('marks nothing when the cut falls outside every sampled bin, which is an answer', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.01, 0, 8), bin(0, 0.01, 12)], -0.5)]);
        expect(histogram?.cut).toBe(-50);
        expect(histogram?.bins.every((entry) => !entry.holdsCut)).toBe(true);
    });

    it('takes each bar width from its own bounds, so an uneven grid still draws true', () => {
        // The schema polices only that `lower_bound` ascends: contiguity and a
        // constant width are the producer's habit, not a guarantee.
        const histogram = buildReturnHistogram([varResult([bin(-0.08, -0.02, 3), bin(-0.02, -0.01, 7)], null)]);
        expect(histogram?.bins.map((entry) => entry.upperBound - entry.lowerBound)).toEqual([6, 1]);
    });

    it('sizes every bar against the tallest one', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.02, -0.01, 5), bin(-0.01, 0, 20)], null)]);
        expect(histogram?.bins.map((entry) => entry.share)).toEqual([0.25, 1]);
    });

    it('counts the observations it actually drew', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.02, -0.01, 5), bin(-0.01, 0, 20)], null)]);
        expect(histogram?.observations).toBe(25);
    });

    it('discards a bin with no width, which could hold neither an observation nor the cut', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.01, -0.01, 4), bin(-0.01, 0, 6)], -0.01)]);
        expect(histogram?.bins).toHaveLength(1);
        expect(histogram?.bins[0].holdsCut).toBe(true);
    });

    it('stays flat instead of dividing by zero when every bin is empty', () => {
        const histogram = buildReturnHistogram([varResult([bin(-0.01, 0, 0), bin(0, 0.01, 0)], null)]);
        expect(histogram?.bins.map((entry) => entry.share)).toEqual([0, 0]);
        expect(histogram?.observations).toBe(0);
    });

    it('has no histogram when the analytic did not run or carried no bins', () => {
        expect(buildReturnHistogram([unavailable('historical_var', DAILY_VAR_INSTANCE)])).toBeNull();
        expect(buildReturnHistogram([varResult([], null)])).toBeNull();
        expect(buildReturnHistogram([])).toBeNull();
    });
});

describe('buildTailMeasures', () => {
    it('leaves the worst day absent when the producer refused to publish one', () => {
        // Every day in the window gained. A zero here would claim a loss that
        // never happened — which is exactly why the backend sends null.
        const measures = buildTailMeasures([ok('historical_kpi', {worst_realization: null, ulcer_index: 0.04})]);
        expect(measures.worstRealization).toBeNull();
    });

    it('drops the date along with the value, so no day is named without a loss', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {worst_realization: null, worst_realization_date: '2024-03-11'})]);
        expect(measures.worstRealizationDate).toBeNull();
    });

    it('keeps the date when there is a loss to attach it to', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {worst_realization: -0.061, worst_realization_date: '2024-03-11'})]);
        expect(measures.worstRealization).toBeCloseTo(0.061, 10);
        expect(measures.worstRealizationDate).toBe('2024-03-11');
    });

    it('reads the confidence the backend used instead of assuming the default', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {drawdown_confidence_level: 0.99, drawdown_at_risk: -0.21})]);
        expect(measures.drawdownConfidence).toBe(0.99);
    });

    it('reports no confidence rather than a borrowed one when the field is absent', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {drawdown_at_risk: -0.21})]);
        expect(measures.drawdownConfidence).toBeNull();
    });

    it('reads the ulcer index as a dispersion, which is non-negative by contract', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {ulcer_index: 0.087})]);
        expect(measures.ulcerIndex).toBe(0.087);
    });

    it('turns the two drawdown tails into positive magnitudes, deepest last', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {drawdown_at_risk: -0.21, conditional_drawdown_at_risk: -0.34})]);
        expect(measures.drawdownAtRisk).toBeCloseTo(0.21, 10);
        expect(measures.conditionalDrawdownAtRisk).toBeCloseTo(0.34, 10);
    });

    it('refuses a drawdown that arrives on the wrong side of zero', () => {
        const measures = buildTailMeasures([ok('historical_kpi', {drawdown_at_risk: 0.21})]);
        expect(measures.drawdownAtRisk).toBeNull();
    });

    it('answers every field with null when the KPI analytic never ran', () => {
        const measures = buildTailMeasures([unavailable('historical_kpi')]);
        expect(measures).toEqual({
            worstRealization: null,
            worstRealizationDate: null,
            drawdownAtRisk: null,
            conditionalDrawdownAtRisk: null,
            drawdownConfidence: null,
            ulcerIndex: null,
        });
    });
});
