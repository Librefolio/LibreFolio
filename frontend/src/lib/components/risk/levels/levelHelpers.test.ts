import {describe, expect, it} from 'vitest';

import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {DAILY_VAR_INSTANCE, MONTHLY_VAR_INSTANCE} from '../riskAnalysisHelpers';
import {BACKTEST_RETURN_BASIS, backtestDeclared, buildConcentration, buildCurrentDrawdown, buildDivergenceRows, buildHurtRows, buildRiskAdjusted, comparedAssetId, degradedResults, resultReasons, leadDivergence, lossMagnitude, requiredRecovery, uncoveredWeight} from './levelHelpers';

/** A successful result carrying `output`, shaped like the API's. */
function ok(analyticCode: string, output: Record<string, unknown>, instanceId = `base-historical-${analyticCode}`): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'ok', output} as unknown as RiskAnalyticResult;
}

/** A result the backend could not compute. */
function unavailable(analyticCode: string, instanceId = `base-historical-${analyticCode}`): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'unavailable', output: null} as unknown as RiskAnalyticResult;
}

function varResult(instanceId: string, valueAtRisk: number, cvar: number): RiskAnalyticResult {
    return ok('historical_var', {kind: 'var_cvar', value_at_risk: valueAtRisk, conditional_value_at_risk: cvar}, instanceId);
}

describe('requiredRecovery', () => {
    it('states the asymmetry that makes a drawdown expensive', () => {
        expect(requiredRecovery(0.1)).toBeCloseTo(0.1111, 4);
        expect(requiredRecovery(0.5)).toBeCloseTo(1, 10);
        expect(requiredRecovery(0.8)).toBeCloseTo(4, 10);
    });

    it('has no answer for a total loss, and says so instead of returning Infinity', () => {
        expect(requiredRecovery(1)).toBeNull();
        expect(requiredRecovery(1.2)).toBeNull();
    });

    it('returns null rather than zero when there was no loss', () => {
        expect(requiredRecovery(0)).toBeNull();
        expect(requiredRecovery(-0.1)).toBeNull();
        expect(requiredRecovery(Number.NaN)).toBeNull();
    });
});

describe('buildHurtRows', () => {
    it('orders the scale day → month → worst, so the change of scale is legible', () => {
        const rows = buildHurtRows([varResult(DAILY_VAR_INSTANCE, 0.018, 0.024), varResult(MONTHLY_VAR_INSTANCE, 0.072, 0.09), ok('drawdown_summary', {maximum_drawdown: -0.384, maximum_drawdown_duration_days: 570})]);
        expect(rows.map((row) => row.id)).toEqual(['day', 'month', 'worst']);
    });

    it('leads with the CVaR and keeps the VaR as the secondary figure', () => {
        const [row] = buildHurtRows([varResult(DAILY_VAR_INSTANCE, 0.018, 0.024)]);
        expect(row.loss).toBe(0.024);
        expect(row.secondaryLoss).toBe(0.018);
    });

    it('never mixes the daily and monthly VaR up, even though they share an analytic code', () => {
        const rows = buildHurtRows([varResult(DAILY_VAR_INSTANCE, 0.018, 0.024), varResult(MONTHLY_VAR_INSTANCE, 0.072, 0.09)]);
        expect(rows.find((row) => row.id === 'day')?.loss).toBe(0.024);
        expect(rows.find((row) => row.id === 'month')?.loss).toBe(0.09);
    });

    it('omits a rung the backend could not compute, rather than showing a zero loss', () => {
        const rows = buildHurtRows([unavailable('historical_var', DAILY_VAR_INSTANCE), ok('drawdown_summary', {maximum_drawdown: -0.2})]);
        expect(rows.map((row) => row.id)).toEqual(['worst']);
    });

    it('turns the negative drawdown into a positive magnitude and derives the recovery', () => {
        const rows = buildHurtRows([ok('drawdown_summary', {maximum_drawdown: -0.5, maximum_drawdown_duration_days: 19})]);
        expect(rows[0]).toMatchObject({id: 'worst', loss: 0.5, durationDays: 19});
        expect(rows[0].requiredRecovery).toBeCloseTo(1, 10);
    });

    it('falls back to the KPI drawdown when the summary was not requested', () => {
        const rows = buildHurtRows([ok('historical_kpi', {max_drawdown: -0.087, max_drawdown_duration_days: 19})]);
        expect(rows[0]).toMatchObject({id: 'worst', loss: 0.087, durationDays: 19});
    });

    it('prefers the drawdown summary over the KPI when both are present', () => {
        const rows = buildHurtRows([ok('historical_kpi', {max_drawdown: -0.087, max_drawdown_duration_days: 19}), ok('drawdown_summary', {maximum_drawdown: -0.384, maximum_drawdown_duration_days: 570})]);
        expect(rows[0]).toMatchObject({loss: 0.384, durationDays: 570});
    });

    it('drops the secondary figure when VaR and CVaR coincide, instead of printing it twice', () => {
        const [row] = buildHurtRows([varResult(DAILY_VAR_INSTANCE, 0.02, 0.02)]);
        expect(row.secondaryLoss).toBeNull();
    });

    it('returns nothing at all when the wave is empty', () => {
        expect(buildHurtRows([])).toEqual([]);
    });
});

describe('buildCurrentDrawdown', () => {
    it('reads the live fall, its peak date and the gain needed to undo it', () => {
        const current = buildCurrentDrawdown([ok('drawdown_summary', {current_drawdown: -0.2, current_peak_date: '2024-02-05', current_drawdown_duration_days: 41})]);
        expect(current).toMatchObject({loss: 0.2, peakDate: '2024-02-05', durationDays: 41});
        expect(current?.requiredRecovery).toBeCloseTo(0.25, 10);
    });

    it('keeps the peak date, which a numeric-only view of the output would discard', () => {
        expect(buildCurrentDrawdown([ok('drawdown_summary', {current_drawdown: -0.1, current_peak_date: '2023-11-14'})])?.peakDate).toBe('2023-11-14');
    });

    it('says nothing when the portfolio sits at its peak', () => {
        expect(buildCurrentDrawdown([ok('drawdown_summary', {current_drawdown: 0, current_peak_date: '2024-03-17'})])).toBeNull();
    });

    it('says nothing when the summary never ran', () => {
        expect(buildCurrentDrawdown([ok('historical_kpi', {max_drawdown: -0.3})])).toBeNull();
    });
});

describe('buildDivergenceRows', () => {
    /**
     * Weight and contribution both as fractions — the API's single scale.
     *
     * `percentage_contribution` is named for the question it answers, not for
     * its scale: the backend divides a component contribution by the portfolio
     * volatility, and `test_risk_api.py` asserts the items sum to 1,0. A fixture
     * stated in 0-100 would agree with a helper that divided by a hundred, and
     * the pair would stay green while the screen showed every holding as a risk
     * reducer.
     */
    function item(assetId: number, weight: number, contribution: number | null) {
        return {asset_id: assetId, weight, percentage_contribution: contribution};
    }

    it('puts what risks more than it weighs at the top', () => {
        const rows = buildDivergenceRows(ok('risk_contribution', {items: [item(1, 0.5, 0.4), item(2, 0.08, 0.23), item(3, 0.42, 0.37)]}));
        expect(rows.map((row) => row.assetId)).toEqual([2, 3, 1]);
        expect(rows[0].divergence).toBeCloseTo(0.15, 10);
    });

    it('reads the contribution on the scale the payload states it in', () => {
        const [row] = buildDivergenceRows(ok('risk_contribution', {items: [item(1, 0.08, 0.23)]}));
        expect(row.weight).toBe(0.08);
        expect(row.contribution).toBeCloseTo(0.23, 10);
    });

    it('keeps a risk-reducing asset, with a negative contribution, at the bottom', () => {
        const rows = buildDivergenceRows(ok('risk_contribution', {items: [item(1, 0.3, -0.05), item(2, 0.7, 1.05)]}));
        expect(rows.map((row) => row.assetId)).toEqual([2, 1]);
        expect(rows[1].contribution).toBeCloseTo(-0.05, 10);
    });

    it('drops an asset whose contribution is unknown rather than calling it zero risk', () => {
        const rows = buildDivergenceRows(ok('risk_contribution', {items: [item(1, 0.5, null), item(2, 0.5, 1)]}));
        expect(rows.map((row) => row.assetId)).toEqual([2]);
    });

    it('breaks ties by asset id, so the order never wobbles between renders', () => {
        const rows = buildDivergenceRows(ok('risk_contribution', {items: [item(9, 0.5, 0.5), item(3, 0.5, 0.5), item(6, 0.5, 0.5)]}));
        expect(rows.map((row) => row.assetId)).toEqual([3, 6, 9]);
    });

    it('yields nothing for a missing or failed result', () => {
        expect(buildDivergenceRows(null)).toEqual([]);
        expect(buildDivergenceRows(unavailable('risk_contribution'))).toEqual([]);
    });
});

describe('leadDivergence', () => {
    const rows = [
        {assetId: 2, weight: 0.08, contribution: 0.23, divergence: 0.15},
        {assetId: 1, weight: 0.5, contribution: 0.4, divergence: -0.1},
    ];

    it('offers the headline when one holding genuinely stands out', () => {
        expect(leadDivergence(rows)?.assetId).toBe(2);
    });

    it('stays quiet rather than making a headline out of noise', () => {
        expect(leadDivergence([{assetId: 1, weight: 0.5, contribution: 0.52, divergence: 0.02}])).toBeNull();
        expect(leadDivergence([])).toBeNull();
    });

    it('honours a caller-supplied threshold', () => {
        expect(leadDivergence(rows, 0.2)).toBeNull();
    });
});

describe('buildRiskAdjusted', () => {
    it('collects the KPI figures and the beta from the comparison', () => {
        const figures = buildRiskAdjusted([ok('historical_kpi', {sortino: 1.4, sharpe: 1.1, volatility: 0.142})], ok('comparison', {beta: 0.93}));
        expect(figures).toEqual({sortino: 1.4, sharpe: 1.1, volatility: 0.142, beta: 0.93});
    });

    it('reports a missing figure as null, never as zero', () => {
        const figures = buildRiskAdjusted([ok('historical_kpi', {sortino: null, sharpe: 1.1, volatility: 0.142})], null);
        expect(figures.sortino).toBeNull();
        expect(figures.beta).toBeNull();
    });

    it('survives a wave with no KPI at all', () => {
        expect(buildRiskAdjusted([], null)).toEqual({sortino: null, sharpe: null, volatility: null, beta: null});
    });
});

describe('lossMagnitude', () => {
    it('reads both of the backend conventions as one magnitude', () => {
        // `max_drawdown` is `le=0`, `value_at_risk` is `ge=0`. Same loss, opposite signs.
        expect(lossMagnitude(-0.0385, 'negative')).toBeCloseTo(0.0385, 10);
        expect(lossMagnitude(0.0312, 'positive')).toBeCloseTo(0.0312, 10);
        expect(lossMagnitude(0, 'negative')).toBe(0);
        expect(lossMagnitude(0, 'positive')).toBe(0);
    });

    it('treats a value that contradicts its own contract as absent, not as a loss', () => {
        // The server cannot emit these — Pydantic enforces the bound. A fixture can,
        // and this is the only place that would notice. `Math.abs` would have turned
        // both into perfectly plausible numbers.
        expect(lossMagnitude(0.0385, 'negative')).toBeNull();
        expect(lossMagnitude(-0.0312, 'positive')).toBeNull();
    });

    it('rejects everything that is not a finite number', () => {
        expect(lossMagnitude(null, 'negative')).toBeNull();
        expect(lossMagnitude(undefined, 'positive')).toBeNull();
        expect(lossMagnitude(Number.NaN, 'negative')).toBeNull();
        expect(lossMagnitude(Number.POSITIVE_INFINITY, 'positive')).toBeNull();
        expect(lossMagnitude('0.03', 'positive')).toBeNull();
    });
});

describe('buildHurtRows sign conventions', () => {
    it('omits a VaR rung whose fixture states the loss with the wrong sign', () => {
        const rows = buildHurtRows([varResult(DAILY_VAR_INSTANCE, -0.02, -0.031)]);
        expect(rows.map((row) => row.id)).not.toContain('day');
    });

    it('omits the worst rung when the drawdown arrives positive', () => {
        const rows = buildHurtRows([ok('historical_kpi', {kind: 'kpi', max_drawdown: 0.184, max_drawdown_duration_days: 90})]);
        expect(rows.map((row) => row.id)).not.toContain('worst');
    });
});

describe('buildConcentration', () => {
    const contribution = (output: Record<string, unknown>) => ok('contribution', {kind: 'contribution', ...output});

    it('returns the correlation-blind count only alongside the number that sees correlation', () => {
        const both = buildConcentration(contribution({effective_number_of_assets: 10, diversification_ratio: 1.02}));
        expect(both).toEqual({effectiveNumberOfAssets: 10, diversificationRatio: 1.02});
    });

    it('refuses to hand back the effective number of assets on its own', () => {
        // Ten equally weighted holdings score 10,00 whether correlation is 0 or 0,95.
        // Alone, that number congratulates one bet wearing ten names.
        expect(buildConcentration(contribution({effective_number_of_assets: 10}))).toBeNull();
        expect(buildConcentration(contribution({diversification_ratio: 1.02}))).toBeNull();
    });

    it('reads a non-positive value as a fault rather than as zero independent bets', () => {
        expect(buildConcentration(contribution({effective_number_of_assets: 0, diversification_ratio: 1.2}))).toBeNull();
        expect(buildConcentration(contribution({effective_number_of_assets: 4, diversification_ratio: 0}))).toBeNull();
    });

    it('is absent, not zero, when the analytic never ran', () => {
        expect(buildConcentration(null)).toBeNull();
        expect(buildConcentration(unavailable('contribution'))).toBeNull();
    });
});

describe('uncoveredWeight', () => {
    it('reads the residual that absorbs cash and every unpriceable holding', () => {
        expect(uncoveredWeight(ok('contribution', {kind: 'contribution', cash_weight: 0.17}))).toBeCloseTo(0.17, 10);
    });

    it('is absent, not zero, when the analytic never ran', () => {
        expect(uncoveredWeight(null)).toBeNull();
        expect(uncoveredWeight(unavailable('contribution'))).toBeNull();
    });
});

describe('okOutput and degradedResults', () => {
    /** A result the server could compute, but not cleanly. */
    function partial(analyticCode: string, output: Record<string, unknown>): RiskAnalyticResult {
        return {analytic_code: analyticCode, instance_id: `base-historical-${analyticCode}`, status: 'partial', output} as unknown as RiskAnalyticResult;
    }

    it('reads a partial answer instead of discarding it', () => {
        // `partial` is the ordinary state of a portfolio with one unpriceable
        // holding, not an exotic one: refusing it blanks every level for a reader
        // whose answer is merely incomplete.
        const rows = buildHurtRows([partial('historical_kpi', {kind: 'kpi', max_drawdown: -0.31})]);
        expect(rows.length).toBeGreaterThan(0);
    });

    it('still refuses a status that produced no answer at all', () => {
        expect(buildHurtRows([unavailable('historical_kpi')])).toEqual([]);
        expect(buildConcentration({analytic_code: 'risk_contribution', instance_id: 'i', status: 'failed', output: {effective_number_of_assets: 4, diversification_ratio: 2}} as unknown as RiskAnalyticResult)).toBeNull();
    });

    it('names every measurement that did not come back whole', () => {
        // Omission is not disclosure: a level that silently drops the rung it
        // could not compute is indistinguishable from a portfolio with less to
        // say, and only one of those is worth retrying.
        const health = degradedResults([ok('risk_kpi', {kind: 'kpi'}), partial('risk_contribution', {kind: 'contribution'}), unavailable('historical_var'), null]);
        expect(health).toEqual([
            {instanceId: 'base-historical-risk_contribution', code: 'risk_contribution', status: 'partial'},
            {instanceId: 'base-historical-historical_var', code: 'historical_var', status: 'unavailable'},
        ]);
    });

    it('keeps two instances of one analytic apart', () => {
        // L1 asks for `historical_var` twice, at one day and at one month. The
        // analytic code is therefore *not* an identity, and a list keyed by it
        // collides exactly when both horizons fail — the case the disclosure
        // exists for. A day and a month are not interchangeable answers.
        const health = degradedResults([unavailable('historical_var', DAILY_VAR_INSTANCE), unavailable('historical_var', MONTHLY_VAR_INSTANCE)]);
        expect(health.map((entry) => entry.instanceId)).toEqual([DAILY_VAR_INSTANCE, MONTHLY_VAR_INSTANCE]);
        expect(new Set(health.map((entry) => entry.instanceId)).size).toBe(2);
    });

    it('carries the caller’s label when the analytic name would be ambiguous', () => {
        const health = degradedResults([unavailable('historical_var', MONTHLY_VAR_INSTANCE)], {[MONTHLY_VAR_INSTANCE]: 'risk.levels.l1.rows.month'});
        expect(health[0].label).toBe('risk.levels.l1.rows.month');
        // An unlabelled instance stays unlabelled rather than borrowing another's.
        expect(degradedResults([unavailable('drawdown_summary')], {[MONTHLY_VAR_INSTANCE]: 'risk.levels.l1.rows.month'})[0].label).toBeUndefined();
    });

    it('says nothing about a wave that came back whole', () => {
        expect(degradedResults([ok('risk_kpi', {kind: 'kpi'}), ok('risk_contribution', {kind: 'contribution'})])).toEqual([]);
    });
});

describe('backtestDeclared', () => {
    /** A result carrying only the metadata the declaration reads. */
    function withBasis(basis: string | undefined, analyticCode = 'historical_kpi'): RiskAnalyticResult {
        return {analytic_code: analyticCode, instance_id: `base-historical-${analyticCode}`, status: 'ok', output: {kind: 'kpi'}, metadata: basis === undefined ? {} : {return_basis: basis}} as unknown as RiskAnalyticResult;
    }

    it('says nothing while the backend still reports what happened', () => {
        expect(backtestDeclared([withBasis('twrr'), withBasis('price_only', 'historical_var')])).toBe(false);
    });

    it('declares the backtest as soon as any analytic in the wave was rebuilt', () => {
        expect(backtestDeclared([withBasis('twrr'), withBasis(BACKTEST_RETURN_BASIS, 'historical_var')])).toBe(true);
    });

    // The value is compared as a literal because C's enum member does not exist
    // in this tree. A near-miss must therefore stay silent rather than trigger:
    // a declaration that fires on the wrong string would accuse a TWRR series of
    // being a backtest, which is the same lie in the opposite direction.
    it('does not fire on a value that merely looks like it', () => {
        expect(backtestDeclared([withBasis('composition_backtest')])).toBe(false);
        expect(backtestDeclared([withBasis('current_composition')])).toBe(false);
        expect(backtestDeclared([withBasis(BACKTEST_RETURN_BASIS.toUpperCase())])).toBe(false);
    });

    it('survives a wave with holes in it, since a missing result declares nothing', () => {
        expect(backtestDeclared([null, undefined, withBasis(undefined)])).toBe(false);
        expect(backtestDeclared([])).toBe(false);
    });

    // Guards the exact string against a well-meaning rename: it is the one value
    // shared with the two backend ternaries, and a fourth name for the same thing
    // was the outcome the contract exists to prevent.
    it('pins the wire value the whole system agreed on', () => {
        expect(BACKTEST_RETURN_BASIS).toBe('current_composition_backtest');
    });
});

describe('comparedAssetId', () => {
    // `output` is kept **populated** on every status on purpose. A fixture that
    // blanked it for the failing ones would let a reader of `result.output` that
    // ignores `status` pass identically, and that is precisely the defect these
    // cases exist to catch: a superseded or failed result can still carry the
    // output of the question it was answering.
    function comparison(status: string, comparisonAssetId: unknown): RiskAnalyticResult {
        return {analytic_code: 'comparison', instance_id: 'base-historical-comparison', status, output: {kind: 'comparison', comparison_asset_id: comparisonAssetId, beta: 0.91}} as unknown as RiskAnalyticResult;
    }

    it('names the reference the figures were computed against', () => {
        expect(comparedAssetId(comparison('ok', 7))).toBe(7);
    });

    // The label must vanish the moment the answer does. A benchmark name left
    // standing over a beta that is no longer there would let the reader attribute
    // a stale number to a reference that never produced it.
    it('has no name while there is no answer', () => {
        expect(comparedAssetId(null)).toBeNull();
        expect(comparedAssetId(undefined)).toBeNull();
        expect(comparedAssetId({analytic_code: 'comparison', instance_id: 'x', status: 'ok', output: null} as unknown as RiskAnalyticResult)).toBeNull();
    });

    // The load-bearing case: a failed result that still carries its old output.
    it('refuses a stale output attached to a result that did not succeed', () => {
        expect(comparedAssetId(comparison('unavailable', 7))).toBeNull();
        expect(comparedAssetId(comparison('failed', 7))).toBeNull();
    });

    it('accepts a partial answer, which is the ordinary state, not a fault', () => {
        expect(comparedAssetId(comparison('partial', 7))).toBe(7);
    });

    it('refuses an id that is not a usable number rather than rendering "#NaN"', () => {
        expect(comparedAssetId(comparison('ok', null))).toBeNull();
        expect(comparedAssetId(comparison('ok', 'seven'))).toBeNull();
        expect(comparedAssetId(comparison('ok', Number.NaN))).toBeNull();
    });
});

describe('resultReasons', () => {
    function warned(instanceId: string, warnings: unknown[], status = 'partial'): RiskAnalyticResult {
        return {analytic_code: 'historical_var', instance_id: instanceId, status, warnings, output: {kind: 'var_cvar', value_at_risk: 0.03}} as unknown as RiskAnalyticResult;
    }

    it('gives the reason behind a degraded measurement, verbatim', () => {
        const reasons = resultReasons([warned('a', [{code: 'short_history', message: 'Only 40 observations were available.'}])]);
        expect(reasons.map((reason) => reason.message)).toEqual(['Only 40 observations were available.']);
    });

    // `degrades_result: false` decides the *status*, which is already on screen.
    // The one real instance of it reports that an asset was treated as "Other"
    // at 100% because its sector metadata was missing — the number is fine, the
    // meaning of the shock is not. Dropping it would withhold the sentence that
    // explains the shape the reader is looking at.
    it('keeps a warning that declares it did not degrade the number', () => {
        const reasons = resultReasons([warned('a', [{code: 'hypothetical_metadata_other_fallback', message: 'Treated as Other at 100%.', degrades_result: false}], 'ok')]);
        expect(reasons.map((reason) => reason.message)).toEqual(['Treated as Other at 100%.']);
    });

    it('says the same sentence once, and says how many results carried it', () => {
        const reasons = resultReasons([warned('a', [{code: 'gap', message: 'A price gap was interpolated.'}]), warned('b', [{code: 'gap', message: 'A price gap was interpolated.'}])]);
        expect(reasons).toHaveLength(1);
        expect(reasons[0].occurrences).toBe(2);
    });

    it('keeps two different sentences apart even under one code', () => {
        const reasons = resultReasons([
            warned('a', [
                {code: 'gap', message: 'Asset 1 was interpolated.'},
                {code: 'gap', message: 'Asset 2 was interpolated.'},
            ]),
        ]);
        expect(reasons).toHaveLength(2);
    });

    // A partial wave with no warnings at all is ordinary: `service.py:736` also
    // turns a wave partial for exclusions and data quality, each disclosed by its
    // own surface. Inventing a reason here would be worse than showing none.
    it('stays empty rather than inventing a cause', () => {
        expect(resultReasons([warned('a', [])])).toEqual([]);
        expect(resultReasons([{analytic_code: 'x', instance_id: 'a', status: 'partial'} as unknown as RiskAnalyticResult])).toEqual([]);
        expect(resultReasons([null, undefined])).toEqual([]);
    });

    it('ignores a warning carrying no readable sentence', () => {
        expect(resultReasons([warned('a', [{code: 'x', message: '   '}, {code: 'y'}, null])])).toEqual([]);
    });
});
