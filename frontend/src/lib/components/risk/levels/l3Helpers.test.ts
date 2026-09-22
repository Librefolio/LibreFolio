import {describe, expect, it} from 'vitest';

import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {buildRiskReturnPoints, cashWeight, selectKpiWave} from './l3Helpers';

/**
 * Every figure below is invented here, on purpose.
 *
 * The mock dataset these levels are exercised against moves — its window is
 * relative to today and its seeding has been re-tuned more than once — so a spec
 * that asserted a number read from a live payload would be measuring the fixture
 * generator rather than this file. What is pinned here is behaviour: which wave
 * gets chosen, what the chosen perimeter is read from, and which points end up
 * on the chart.
 */
function kpiResult(mode: string | undefined, status: 'ok' | 'unavailable' = 'ok'): RiskAnalyticResult {
    return {
        analytic_code: 'historical_kpi',
        instance_id: `base-${mode ?? 'none'}-historical_kpi`,
        status,
        output: status === 'ok' ? {kind: 'kpi', sortino: 2, sharpe: 1, volatility: 0.1} : null,
        metadata: mode === undefined ? {} : {mode},
    } as unknown as RiskAnalyticResult;
}

function riskReturnResult(output: Record<string, unknown>): RiskAnalyticResult {
    return {
        analytic_code: 'asset_risk_return',
        instance_id: 'base-current_composition-asset_risk_return',
        status: 'ok',
        output: {kind: 'risk_return', ...output},
    } as unknown as RiskAnalyticResult;
}

function comparisonResult(output: Record<string, unknown>): RiskAnalyticResult {
    return {
        analytic_code: 'comparison',
        instance_id: 'single-comparison',
        status: 'ok',
        output: {kind: 'comparison', comparison_asset_id: 11, ...output},
    } as unknown as RiskAnalyticResult;
}

describe('selectKpiWave', () => {
    it('prefers the current composition, because that is the question L3 asks', () => {
        const wave = selectKpiWave([kpiResult('current_composition')], [kpiResult('historical')]);
        expect(wave.perimeter).toBe('current_composition');
        expect(wave.results[0].instance_id).toBe('base-current_composition-historical_kpi');
    });

    it('falls back to the historical wave when the backend does not offer the mode', () => {
        // An older install, or any scope where current composition does not apply:
        // the request is never even sent, so the current wave simply has no KPI.
        const wave = selectKpiWave([], [kpiResult('historical')]);
        expect(wave.perimeter).toBe('historical');
        expect(wave.results).toHaveLength(1);
    });

    it('falls back when the current-composition KPI came back without an output', () => {
        const wave = selectKpiWave([kpiResult('current_composition', 'unavailable')], [kpiResult('historical')]);
        expect(wave.perimeter).toBe('historical');
    });

    it('reads the perimeter from the payload, not from which array it came out of', () => {
        // Deliberately contradictory: a result sitting in the current wave that
        // declares itself historical. The payload wins, because the payload is the
        // one that knows what it measured.
        const wave = selectKpiWave([kpiResult('historical')], []);
        expect(wave.perimeter).toBe('historical');
    });

    it('declares nothing rather than guessing when the metadata carries no mode', () => {
        expect(selectKpiWave([kpiResult(undefined)], []).perimeter).toBeNull();
    });

    it('has nothing to declare when neither wave measured anything', () => {
        const historical: RiskAnalyticResult[] = [];
        const wave = selectKpiWave([], historical);
        expect(wave.perimeter).toBeNull();
        expect(wave.results).toBe(historical);
    });
});

describe('buildRiskReturnPoints', () => {
    const base = {
        assetNames: {1: 'Apple', 2: 'Bitcoin'},
        benchmarkName: 'MSCI World',
        portfolioLabel: 'Portfolio',
    };

    it('draws the portfolio, every asset and the benchmark, and nothing else', () => {
        const points = buildRiskReturnPoints({
            ...base,
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                cash_weight: 0.5,
                items: [
                    {asset_id: 1, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15},
                    {asset_id: 2, weight: 0.2, volatility: 0.8, expected_annual_return: -0.1},
                ],
            }),
            comparisonResult: comparisonResult({comparison_volatility: 0.17, comparison_expected_annual_return: 0.12}),
        });

        expect(points.map((point) => point.role)).toEqual(['portfolio', 'asset', 'asset', 'benchmark']);
        expect(points.map((point) => point.name)).toEqual(['Portfolio', 'Apple', 'Bitcoin', 'MSCI World']);
    });

    it('sizes the portfolio as the whole of itself and the assets by their real weight', () => {
        const points = buildRiskReturnPoints({
            ...base,
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                cash_weight: 0.5,
                items: [{asset_id: 1, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15}],
            }),
            comparisonResult: null,
        });

        expect(points[0].weight).toBe(1);
        // Not renormalised to the invested part: the asset bubbles are meant to fall
        // short of the whole, and the shortfall is the cash.
        expect(points[1].weight).toBe(0.3);
    });

    it('never places cash, even though the model says it returns exactly zero', () => {
        const result = riskReturnResult({
            portfolio_volatility: 0.06,
            portfolio_expected_annual_return: 0.09,
            cash_weight: 0.49,
            items: [{asset_id: 1, weight: 0.51, volatility: 0.2, expected_annual_return: 0.15}],
        });
        const points = buildRiskReturnPoints({...base, riskReturnResult: result, comparisonResult: null});

        expect(points.every((point) => point.volatility !== 0 || point.annualReturn !== 0)).toBe(true);
        // The share is still published, so the caller can say it in words.
        expect(cashWeight(result)).toBe(0.49);
    });

    it('drops a point it cannot place instead of pinning it to an axis', () => {
        const points = buildRiskReturnPoints({
            ...base,
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                items: [
                    {asset_id: 1, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15},
                    {asset_id: 2, weight: 0.2, volatility: null, expected_annual_return: -0.1},
                ],
            }),
            comparisonResult: null,
        });

        expect(points.map((point) => point.id)).toEqual(['portfolio', 'asset-1']);
    });

    it('waits for the comparison answer before drawing a benchmark', () => {
        const points = buildRiskReturnPoints({
            ...base,
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                items: [{asset_id: 1, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15}],
            }),
            // A comparison that ran against an older backend carries beta but not the
            // reference's own risk and reward.
            comparisonResult: comparisonResult({beta: 0.2}),
        });

        expect(points.some((point) => point.role === 'benchmark')).toBe(false);
    });

    it('names an asset it has no name for rather than dropping it', () => {
        const points = buildRiskReturnPoints({
            ...base,
            assetNames: {},
            riskReturnResult: riskReturnResult({
                portfolio_volatility: 0.06,
                portfolio_expected_annual_return: 0.09,
                items: [{asset_id: 7, weight: 0.3, volatility: 0.2, expected_annual_return: 0.15}],
            }),
            comparisonResult: null,
        });

        expect(points[1].name).toBe('#7');
    });

    it('draws nothing at all when the analytic did not run', () => {
        expect(buildRiskReturnPoints({...base, riskReturnResult: null, comparisonResult: null})).toEqual([]);
        expect(cashWeight(null)).toBeNull();
    });
});
