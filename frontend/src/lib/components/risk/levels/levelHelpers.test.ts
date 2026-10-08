import {beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';

import {setupI18n} from '$test/component';
import {CODE_EQUAL_ICU_WARNING_KEYS, icuWarningKeys, plausibleParams, type WarningParams} from '$test/riskWarningCatalogue';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {DAILY_VAR_INSTANCE, MONTHLY_VAR_INSTANCE} from '../riskAnalysisHelpers';
import * as levelHelpers from './levelHelpers';
import {
    BACKTEST_RETURN_BASIS,
    backtestDeclared,
    buildConcentration,
    buildCurrentDrawdown,
    buildDivergenceRows,
    buildHurtRows,
    buildRiskAdjusted,
    comparedAssetId,
    degradedResults,
    resultErrorCodes,
    resultReasons,
    type ResultReason,
    translateErrorCode,
    leadDivergence,
    lossMagnitude,
    requiredRecovery,
    uncoveredWeight,
    warningSentence,
} from './levelHelpers';

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
    /**
     * A `risk_contribution` answer as L2 receives it; `partial` is what an exclusion makes it.
     *
     * `cash_weight` is the zero-return residual — true cash, value in transit, and every
     * holding left without a price series — and `excluded_weight` is that last part alone.
     * The card splits the one into the other, so the reader can tell an allocation from a
     * modelling gap. Every weight here is invented.
     */
    function contribution(output: Record<string, unknown>, status: 'ok' | 'partial' | 'unavailable' | 'failed' = 'ok'): RiskAnalyticResult {
        return {analytic_code: 'risk_contribution', instance_id: 'base-current_composition-risk_contribution', status, output: {kind: 'contribution', ...output}} as unknown as RiskAnalyticResult;
    }

    /** The same two fields as `asset_risk_return` publishes them: L3 reads its residual through this helper too. */
    function riskReturn(output: Record<string, unknown>, status: 'ok' | 'partial' = 'ok'): RiskAnalyticResult {
        return {analytic_code: 'asset_risk_return', instance_id: 'base-current_composition-asset_risk_return', status, output: {kind: 'risk_return', ...output}} as unknown as RiskAnalyticResult;
    }

    it('splits the uncovered share into the holdings left without a price and the cash that remains', () => {
        expect(uncoveredWeight(contribution({cash_weight: 0.25, excluded_weight: 0.1})), 'the residual was not split: the holdings the model could not price still read as cash').toStrictEqual({total: 0.25, unpriced: 0.1, cash: expect.closeTo(0.15, 12)});
        // A residual made only of unpriced holdings — a slice carries no cash — is none of it cash.
        expect(uncoveredWeight(contribution({cash_weight: 0.1, excluded_weight: 0.1})), 'the whole residual is unpriced, yet part of it was called cash').toStrictEqual({total: 0.1, unpriced: 0.1, cash: 0});
    });

    it("states the total as the backend's residual itself, never as the sum of its parts", () => {
        // In binary floating point 0.1 + (0.45 − 0.1) is 0.44999999999999996: a total rebuilt
        // from its parts would contradict the residual the backend published, by one bit.
        expect(0.1 + (0.45 - 0.1), 'guard: these weights add back exactly, so the pin below could not tell the residual from a sum').not.toBe(0.45);
        expect(uncoveredWeight(contribution({cash_weight: 0.45, excluded_weight: 0.1}))).toStrictEqual({total: 0.45, unpriced: 0.1, cash: expect.closeTo(0.35, 12)});
    });

    it('reads a partial contribution — what an exclusion makes it — exactly like an ok one', () => {
        // Refusing `partial` would blank the card in the one case it exists for.
        expect(uncoveredWeight(contribution({cash_weight: 0.25, excluded_weight: 0.1}, 'partial'))).toStrictEqual({total: 0.25, unpriced: 0.1, cash: expect.closeTo(0.15, 12)});
    });

    it('takes a zero excluded weight as a known zero: all of the uncovered share is cash', () => {
        // Zero is a measurement here, not a missing value — and the only case the card may caption "all cash".
        expect(uncoveredWeight(contribution({cash_weight: 0.25, excluded_weight: 0}))).toStrictEqual({total: 0.25, unpriced: 0, cash: 0.25});
        expect(uncoveredWeight(contribution({cash_weight: 0, excluded_weight: 0}))).toStrictEqual({total: 0, unpriced: 0, cash: 0});
    });

    it('never states a negative cash when the excluded weight overshoots the residual by float noise', () => {
        // Σ excluded weights and 1 − Σ usable weights are summed apart, so they can disagree
        // in the last bit. A negative cash would render as "−0%", or worse.
        const overshoot = 0.1 + 0.2;
        expect(overshoot, 'guard: the excluded weight does not overshoot the residual, so the clamp below is not exercised').toBeGreaterThan(0.3);
        expect(uncoveredWeight(contribution({cash_weight: 0.3, excluded_weight: overshoot}))).toStrictEqual({total: 0.3, unpriced: expect.closeTo(0.3, 12), cash: 0});
    });

    /*
     * The derived cash is cleaned at the risk service's own weight tolerance, 1e-9
     * (`services/risk/service.py:515` and `:524`): a difference thinner than that is
     * float noise, and a card stating it would caption a sliver of cash nobody holds.
     * Only the derived figure is cleaned — `total` and `unpriced` are published
     * numbers and stay exactly as the payload states them.
     */
    it('reads what the excluded holdings leave of the residual, thinner than the tolerance, as no cash at all', () => {
        // 1 − Σ usable weights and Σ excluded weights, summed apart, disagree by 5.55e-17.
        expect(uncoveredWeight(contribution({cash_weight: 0.30000000000000004, excluded_weight: 0.3}))).toStrictEqual({total: 0.30000000000000004, unpriced: 0.3, cash: 0});
    });

    it('reads the float residue of a fully invested portfolio as no cash, and still states the total exactly', () => {
        // 1 − 0.9999999999999999 is 2⁻⁵³: weights that sum to one leave this behind.
        expect(uncoveredWeight(contribution({cash_weight: 1.1102230246251565e-16, excluded_weight: 0}))).toStrictEqual({total: 1.1102230246251565e-16, unpriced: 0, cash: 0});
    });

    it('draws the line at the tolerance itself: just above 1e-9 is cash, just under it is noise', () => {
        expect(uncoveredWeight(contribution({cash_weight: 1.1e-9, excluded_weight: 0})), 'just above the tolerance').toStrictEqual({total: 1.1e-9, unpriced: 0, cash: 1.1e-9});
        expect(uncoveredWeight(contribution({cash_weight: 9e-10, excluded_weight: 0})), 'just under the tolerance').toStrictEqual({total: 9e-10, unpriced: 0, cash: 0});
    });

    it("keeps a residual of exactly 1e-9 as cash: the line is strict, as in the service's in-transit check", () => {
        // `service.py` reads `abs(...) < 1e-9` as noise, so exactly 1e-9 is not.
        expect(uncoveredWeight(contribution({cash_weight: 1e-9, excluded_weight: 0}))).toStrictEqual({total: 1e-9, unpriced: 0, cash: 1e-9});
    });

    it('keeps real cash above the tolerance: the cleaning must not eat an allocation', () => {
        expect(uncoveredWeight(contribution({cash_weight: 0.001, excluded_weight: 0}))).toStrictEqual({total: 0.001, unpriced: 0, cash: 0.001});
    });

    it('states both published weights as published — the excluded one uncapped, even above the residual — and cleans only the derived cash', () => {
        // Negative true cash, which the service refuses upstream: the two weights are then not
        // nested, and capping the excluded one at the residual would rewrite a published number.
        const split = uncoveredWeight(contribution({cash_weight: 0.2, excluded_weight: 0.25}));
        expect(split?.total, 'total').toBe(0.2);
        expect(split?.unpriced, 'unpriced, as published').toBe(0.25);
        expect(split?.cash, 'cash').toBe(0);
    });

    it('states a dust holding without a price as published, however thin: the card must not deny the asset the notice badges', () => {
        // Both published weights sit under the tolerance and stay exactly as published;
        // only the cash derived from them is cleaned.
        expect(uncoveredWeight(contribution({cash_weight: 5e-10, excluded_weight: 5e-10}))).toStrictEqual({total: 5e-10, unpriced: 5e-10, cash: 0});
    });

    // L3 reads the same residual off `asset_risk_return` (developer's decision of 29/09,
    // 23:35: one helper, the twins deleted). A check on `kind` would blank that card.
    it('reads an asset_risk_return output exactly like a risk_contribution one, total and split included', () => {
        expect(uncoveredWeight(riskReturn({portfolio_volatility: 0.13, portfolio_expected_annual_return: 0.07, cash_weight: 0.25, excluded_weight: 0.1, items: []})), 'the risk/return residual was not read').toStrictEqual({
            total: 0.25,
            unpriced: 0.1,
            cash: expect.closeTo(0.15, 12),
        });
        const outputs: Array<[string, Record<string, unknown>]> = [
            ['a known split', {cash_weight: 0.25, excluded_weight: 0.1}],
            ['an unknown split', {cash_weight: 0.25}],
            ['a residual of excluded holdings only', {cash_weight: 0.1, excluded_weight: 0.1}],
        ];
        for (const [label, output] of outputs) {
            expect(uncoveredWeight(riskReturn(output)), label).toStrictEqual(uncoveredWeight(contribution(output)));
            expect(uncoveredWeight(riskReturn(output, 'partial')), `${label}, partial`).toStrictEqual(uncoveredWeight(contribution(output, 'partial')));
        }
    });

    it('keeps the total but will not split it when the excluded weight is missing or unusable', () => {
        // An unknown split is not "all cash": captioned so, it would hide exactly the
        // holdings the split exists to name.
        const unusable: Array<[string, Record<string, unknown>]> = [
            ['missing', {}],
            ['null', {excluded_weight: null}],
            ['text', {excluded_weight: '0.1'}],
            ['NaN', {excluded_weight: Number.NaN}],
            ['infinite', {excluded_weight: Number.POSITIVE_INFINITY}],
            ['negative', {excluded_weight: -0.05}],
        ];
        for (const [label, extra] of unusable) {
            expect(uncoveredWeight(contribution({cash_weight: 0.25, ...extra})), `excluded_weight ${label}`).toStrictEqual({total: 0.25, unpriced: null, cash: null});
        }
    });

    it('is still null when the residual itself is unusable or the answer is not one, however usable the excluded weight', () => {
        // The barrier first: every null below would also hold for a helper that never answers.
        expect(uncoveredWeight(contribution({cash_weight: 0.25, excluded_weight: 0.1})), 'presence barrier: a usable pair was not split, so the nulls below would prove nothing').toStrictEqual({total: 0.25, unpriced: 0.1, cash: expect.closeTo(0.15, 12)});
        const refused: Array<[string, RiskAnalyticResult | null]> = [
            ['no result', null],
            ['cash_weight missing', contribution({excluded_weight: 0.1})],
            ['cash_weight null', contribution({cash_weight: null, excluded_weight: 0.1})],
            ['cash_weight text', contribution({cash_weight: '0.25', excluded_weight: 0.1})],
            ['cash_weight NaN', contribution({cash_weight: Number.NaN, excluded_weight: 0.1})],
            ['cash_weight infinite', contribution({cash_weight: Number.POSITIVE_INFINITY, excluded_weight: 0.1})],
            ['cash_weight negative', contribution({cash_weight: -0.05, excluded_weight: 0.1})],
            ['a stale output on an unavailable result', contribution({cash_weight: 0.25, excluded_weight: 0.1}, 'unavailable')],
            ['a stale output on a failed result', contribution({cash_weight: 0.25, excluded_weight: 0.1}, 'failed')],
        ];
        for (const [label, result] of refused) {
            expect(uncoveredWeight(result), label).toBeNull();
        }
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

    // The invariant this file's docstring records: `message` is backend prose,
    // shown verbatim. If an error sentence ever leaks into `reasons`, a caller
    // can no longer tell which entries it may translate — so the error travels
    // in `resultErrorCodes` instead, and this asserts the separation holds.
    it('leaves an outright failure out of the verbatim list', () => {
        const failed = {analytic_code: 'correlation', instance_id: 'a', status: 'failed', error: {code: 'incompatible_scope', message: 'Not supported.'}} as unknown as RiskAnalyticResult;
        expect(resultReasons([failed])).toEqual([]);
    });

    /**
     * The notice above the levels draws one badge per excluded asset, in a tone set by
     * the cause: informative for a permanent one (`no_price_source`), amber otherwise.
     * Both come from the warning's `details` — `reason`, and the ids the backend names
     * the assets from (`asset_ids`, or a lone `asset_id`) — and the grouping by
     * sentence must not lose them. A field the helper cannot state for certain is
     * **absent**, never `undefined`, so an entry without one keeps the exact shape the
     * one-argument callers pin today.
     *
     * Every absence below comes with a presence barrier in the same call: "absent" also
     * holds for a helper that never reads `details` at all.
     */
    describe('the cause and the assets behind each sentence', () => {
        /** The backend's one English sentence for every `assets_excluded` warning, whatever its cause. */
        const EXCLUDED_SENTENCE = 'One or more scope assets were excluded from risk calculations.';
        /** The backend's one English sentence for every asset a hypothetical shock treated as "Other". */
        const FALLBACK_SENTENCE = 'Sector or geography metadata was unavailable; the asset was treated as Other at 100%.';

        function excluded(details: unknown, message = EXCLUDED_SENTENCE): unknown {
            return {code: 'assets_excluded', message, details};
        }

        /** The entry of one sentence, found by its sentence rather than by its position. */
        function entryOf(reasons: ResultReason[], message: string): ResultReason | undefined {
            return reasons.find((reason) => reason.message === message);
        }

        /** The one entry that warnings sharing a sentence collapse into, each carried by its own result. */
        function mergedEntry(detailsList: unknown[]): ResultReason | undefined {
            const reasons = resultReasons(detailsList.map((details, index) => warned(`r${index}`, [excluded(details)])));
            expect(reasons, 'guard: the warnings did not share one sentence, so nothing was merged').toHaveLength(1);
            return reasons[0];
        }

        it('carries the cause and the assets of a warning beside its sentence, the ids in the order they came', () => {
            const reasons = resultReasons([warned('a', [excluded({asset_ids: [12, 11], reason: 'no_price_source'})])]);
            expect(reasons, 'the cause (which picks the tone) or the ids (one badge each) were lost to the grouping').toStrictEqual([{key: `assets_excluded:${EXCLUDED_SENTENCE}`, message: EXCLUDED_SENTENCE, occurrences: 1, reason: 'no_price_source', assetIds: [12, 11]}]);
        });

        it('reads the one asset a warning names under asset_id, and prefers the list when a warning carries both', () => {
            // The backend's own rule for the names in the sentence (`_warning_asset_ids`).
            const single = 'Synthetic: one asset, named alone.';
            const both = 'Synthetic: a list and a single id at once.';
            const reasons = resultReasons([warned('a', [excluded({asset_id: 7}, single), excluded({asset_ids: [11, 12], asset_id: 7}, both)])]);
            expect(reasons).toStrictEqual([
                {key: `assets_excluded:${single}`, message: single, occurrences: 1, assetIds: [7]},
                {key: `assets_excluded:${both}`, message: both, occurrences: 1, assetIds: [11, 12]},
            ]);
        });

        it('states no cause it cannot read: missing, empty, blank or not text, the reason is left out — not set to undefined', () => {
            const readable = 'Synthetic: a readable reason.';
            const unreadable: Array<[string, unknown]> = [
                ['no reason at all', {}],
                ['an empty reason', {reason: ''}],
                ['a blank reason', {reason: '   '}],
                ['a numeric reason', {reason: 3}],
                ['a null reason', {reason: null}],
                ['a boolean reason', {reason: true}],
                ['a reason in a list', {reason: ['no_price_source']}],
                ['details that are not an object', null],
            ];
            const reasons = resultReasons([warned('a', [excluded({reason: 'no_price_source'}, readable), ...unreadable.map(([label, details]) => excluded(details, `Synthetic: ${label}.`))])]);

            expect(entryOf(reasons, readable), 'presence barrier: a readable reason was not carried, so the absences below would prove nothing').toStrictEqual({key: `assets_excluded:${readable}`, message: readable, occurrences: 1, reason: 'no_price_source'});
            for (const [label] of unreadable) {
                const message = `Synthetic: ${label}.`;
                expect(entryOf(reasons, message), label).toStrictEqual({key: `assets_excluded:${message}`, message, occurrences: 1});
            }
        });

        it('stores the cause trimmed, so padding neither misses the tone nor splits a merged sentence', () => {
            // The notice picks its tone by comparing the cause with `no_price_source`: a padded one would miss it.
            const padded = 'Synthetic: a padded reason.';
            const reasons = resultReasons([warned('a', [excluded({reason: '  no_price_source '}, padded)])]);
            expect(entryOf(reasons, padded)).toStrictEqual({key: `assets_excluded:${padded}`, message: padded, occurrences: 1, reason: 'no_price_source'});
            expect(mergedEntry([{reason: ' no_price_source'}, {reason: 'no_price_source  '}]), 'two paddings of one cause were read as two causes').toStrictEqual({key: `assets_excluded:${EXCLUDED_SENTENCE}`, message: EXCLUDED_SENTENCE, occurrences: 2, reason: 'no_price_source'});
        });

        it('draws no badge from ids it cannot trust: all or nothing, and no fallback past a list that is there but unusable', () => {
            const usable = 'Synthetic: a usable list.';
            const unusable: Array<[string, unknown]> = [
                ['no ids at all', {}],
                ['an empty list', {asset_ids: []}],
                ['a list with a fraction in it', {asset_ids: [11, 1.5]}],
                ['a list with an id sent as text', {asset_ids: [11, '3']}],
                ['a list with a boolean in it', {asset_ids: [11, true]}],
                ['a list with a null in it', {asset_ids: [11, null]}],
                ['a list that is not a list', {asset_ids: '11, 12'}],
                ['an unusable list beside a usable single id', {asset_ids: [11, 1.5], asset_id: 7}],
                ['an empty list beside a usable single id', {asset_ids: [], asset_id: 7}],
                ['a single id that is a fraction', {asset_id: 7.5}],
                ['a single id sent as text', {asset_id: '7'}],
                ['a single id that is null', {asset_id: null}],
                ['details that are not an object', null],
            ];
            const reasons = resultReasons([warned('a', [excluded({asset_ids: [11, 12]}, usable), ...unusable.map(([label, details]) => excluded(details, `Synthetic: ${label}.`))])]);

            expect(entryOf(reasons, usable), 'presence barrier: a usable list was not carried, so the absences below would prove nothing').toStrictEqual({key: `assets_excluded:${usable}`, message: usable, occurrences: 1, assetIds: [11, 12]});
            for (const [label] of unusable) {
                const message = `Synthetic: ${label}.`;
                // Filtering would badge 11 alone and hide the asset the list could not name.
                expect(entryOf(reasons, message), label).toStrictEqual({key: `assets_excluded:${message}`, message, occurrences: 1});
            }
        });

        it('reads a null list as no list at all, as the backend does, and falls back to the single id', () => {
            // `_warning_asset_ids`: `raw is None` → the single `asset_id`. A list that is there but
            // unusable, the empty one included, still stops the fallback (pinned just above).
            const nullList = 'Synthetic: a null list beside a single id.';
            const reasons = resultReasons([warned('a', [excluded({asset_ids: null, asset_id: 7}, nullList)])]);
            expect(entryOf(reasons, nullList)).toStrictEqual({key: `assets_excluded:${nullList}`, message: nullList, occurrences: 1, assetIds: [7]});
        });

        it('keeps the cause and the assets every warning of a merged sentence agrees on, the list as the first one gave it', () => {
            // The ordinary case: one exclusion, repeated on every result that inherited it.
            // Same set, told in another order after the first: the entry keeps the first as it came.
            const entry = mergedEntry([
                {asset_ids: [12, 11], reason: 'missing_price'},
                {asset_ids: [11, 12], reason: 'missing_price'},
                {asset_ids: [11, 12], reason: 'missing_price'},
            ]);
            expect(entry, 'a cause or a set of assets that every merged warning shares was dropped, or the list was not the first one as given').toStrictEqual({key: `assets_excluded:${EXCLUDED_SENTENCE}`, message: EXCLUDED_SENTENCE, occurrences: 3, reason: 'missing_price', assetIds: [12, 11]});
        });

        it('drops the cause of a merged sentence as soon as one warning states another or none, and never takes it back', () => {
            expect(mergedEntry([{reason: 'missing_price'}, {reason: 'missing_price'}]), 'presence barrier: a cause both warnings agree on was not kept, so the absences below would prove nothing').toStrictEqual({
                key: `assets_excluded:${EXCLUDED_SENTENCE}`,
                message: EXCLUDED_SENTENCE,
                occurrences: 2,
                reason: 'missing_price',
            });
            const disagreements: Array<[string, unknown[]]> = [
                ['another cause', [{reason: 'no_price_source'}, {reason: 'missing_price'}]],
                ['a later warning without one', [{reason: 'missing_price'}, {}]],
                ['a first warning without one', [{}, {reason: 'missing_price'}]],
                ['a later warning with a blank one', [{reason: 'missing_price'}, {reason: '   '}]],
                ['agreement again after a warning without one', [{reason: 'missing_price'}, {}, {reason: 'missing_price'}]],
                ['agreement again after another cause', [{reason: 'missing_price'}, {reason: 'no_price_source'}, {reason: 'missing_price'}]],
            ];
            for (const [label, detailsList] of disagreements) {
                expect(mergedEntry(detailsList), label).toStrictEqual({key: `assets_excluded:${EXCLUDED_SENTENCE}`, message: EXCLUDED_SENTENCE, occurrences: detailsList.length});
            }
        });

        it('drops the badges of a merged sentence as soon as one warning names other assets or none, and never takes them back', () => {
            expect(mergedEntry([{asset_ids: [11, 12]}, {asset_ids: [11, 12]}]), 'presence barrier: a set both warnings agree on was not kept, so the absences below would prove nothing').toStrictEqual({
                key: `assets_excluded:${EXCLUDED_SENTENCE}`,
                message: EXCLUDED_SENTENCE,
                occurrences: 2,
                assetIds: [11, 12],
            });
            const disagreements: Array<[string, unknown[]]> = [
                ['another set', [{asset_ids: [11, 12]}, {asset_ids: [11, 13]}]],
                ['a subset', [{asset_ids: [11, 12]}, {asset_ids: [11]}]],
                ['a superset', [{asset_ids: [11]}, {asset_ids: [11, 12]}]],
                ['a later warning without ids', [{asset_ids: [11, 12]}, {}]],
                ['a first warning without ids', [{}, {asset_ids: [11, 12]}]],
                ['a later warning with an unusable list', [{asset_ids: [11, 12]}, {asset_ids: [11, 1.5]}]],
                ['agreement again after a warning without ids', [{asset_ids: [11, 12]}, {}, {asset_ids: [11, 12]}]],
                ['agreement again after another set', [{asset_ids: [11, 12]}, {asset_ids: [13]}, {asset_ids: [11, 12]}]],
            ];
            for (const [label, detailsList] of disagreements) {
                expect(mergedEntry(detailsList), label).toStrictEqual({key: `assets_excluded:${EXCLUDED_SENTENCE}`, message: EXCLUDED_SENTENCE, occurrences: detailsList.length});
            }
        });

        it('compares the assets of a merged sentence as a set: a list naming one asset twice still agrees, and the first list is kept as given', () => {
            // All or nothing takes a list with a repeated id as it is: every element is an integer.
            expect(mergedEntry([{asset_ids: [11, 11, 12]}, {asset_ids: [12, 11]}]), 'the repeat first').toStrictEqual({key: `assets_excluded:${EXCLUDED_SENTENCE}`, message: EXCLUDED_SENTENCE, occurrences: 2, assetIds: [11, 11, 12]});
            expect(mergedEntry([{asset_ids: [12, 11]}, {asset_ids: [11, 11, 12]}]), 'the repeat second').toStrictEqual({key: `assets_excluded:${EXCLUDED_SENTENCE}`, message: EXCLUDED_SENTENCE, occurrences: 2, assetIds: [12, 11]});
        });

        it('decides the cause and the badges apart: verbatim, one fallback sentence per asset keeps its cause and loses its badges', () => {
            // `hypothetical_metadata_other_fallback` is emitted once per asset under one English
            // sentence: the cause is the same for all of them, the assets are not.
            const fallback = (assetId: number) => ({code: 'hypothetical_metadata_other_fallback', message: FALLBACK_SENTENCE, degrades_result: false, details: {asset_id: assetId, dimension: 'sector', reason: 'missing_classification_metadata'}});
            const reasons = resultReasons([warned('a', [fallback(31), fallback(32)], 'ok')]);
            expect(reasons).toStrictEqual([{key: `hypothetical_metadata_other_fallback:${FALLBACK_SENTENCE}`, message: FALLBACK_SENTENCE, occurrences: 2, reason: 'missing_classification_metadata'}]);
        });
    });
});

/* ------------------------------------------------- keyed warning sentences --- */

/**
 * A warning now travels in two forms: the backend's English `message`, and the
 * same sentence as a catalogue key (`message_i18n_key`) with the values it needs
 * (`message_params`: names, counts, days). `warningSentence` chooses between the
 * two, and `resultReasons` lists what it chose.
 *
 * **How a worded sentence is asserted without writing one down.** Every expected
 * sentence is resolved from the *shipped catalogue* through the same `$_`
 * formatter the components hand in, with the same values — the pattern of
 * `L4Replay.test.ts`. No English is pinned, so rewording `en.json` moves both
 * sides together. That makes each comparison only as honest as the lookup behind
 * it, so the first case guards the two ways it could go vacuous: a key missing
 * from the catalogue (svelte-i18n echoes the id back, and a helper echoing it too
 * would "agree"), and a sentence that never received its values (svelte-i18n then
 * returns the raw ICU source, braces included).
 *
 * The named cases below pin one sentence each; the block after them states the
 * same rule over *every* `risk.warnings` sentence that takes arguments, with the
 * list and plausible values read off `en.json` at test time by
 * `$test/riskWarningCatalogue` — the same list `RiskResultFrame.test.ts` renders.
 */
type Warning = NonNullable<RiskAnalyticResult['warnings']>[number];

interface KeyedCase {
    code: string;
    key: string;
    params: WarningParams;
    /** The backend's English sentence for this code, as `message` carries it. */
    message: string;
    /** What the worded sentence must visibly carry: the names, and any count, days or share. */
    carries: string[];
}

const HOLDING_A = 'Synthetic Holding A';
const HOLDING_B = 'Synthetic Holding B';
const HOLDING_C = 'Synthetic Holding C';

/** Emitted once per asset, with the same English sentence for every one of them. */
const FALLBACK_CASE: KeyedCase = {
    code: 'hypothetical_metadata_other_fallback',
    key: 'risk.warnings.hypothetical_metadata_other_fallback',
    params: {names: HOLDING_A, dimension: 'sector', count: 1},
    message: 'Sector or geography metadata was unavailable; the asset was treated as Other at 100%.',
    carries: [HOLDING_A],
};
const SLICE_CASE: KeyedCase = {
    code: 'slice_assets_not_held',
    key: 'risk.warnings.slice_assets_not_held',
    params: {count: 2, names: `${HOLDING_A}, ${HOLDING_B}`},
    message: 'Some requested assets are not held in the selected portfolio scope and were ignored.',
    carries: [`${HOLDING_A}, ${HOLDING_B}`, '2'],
};
/** The code says only `assets_excluded`: the reason lives in the key alone. */
const EXCLUDED_CASE: KeyedCase = {
    code: 'assets_excluded',
    key: 'risk.warnings.assets_excluded_missing_price',
    params: {count: 3, names: `${HOLDING_A}, ${HOLDING_B}, ${HOLDING_C}`},
    message: 'One or more scope assets were excluded from risk calculations.',
    carries: [`${HOLDING_A}, ${HOLDING_B}, ${HOLDING_C}`, '3'],
};
const STALE_CASE: KeyedCase = {
    code: 'historical_replay_assets_excluded',
    key: 'risk.warnings.historical_replay_excluded_stale_at_start',
    params: {names: HOLDING_C, treatment: 'omitted_from_replay', days: 37, count: 1},
    message: 'Historical replay excluded assets quoted before the replay window but with no price in the 37 days before it begins.',
    carries: [HOLDING_C, '37'],
};
/** The one argument formatted as a number (`{covered, number, percent}`), not interpolated as text. */
const MOSTLY_EXCLUDED_CASE: KeyedCase = {
    code: 'historical_replay_mostly_excluded',
    key: 'risk.warnings.historical_replay_mostly_excluded',
    params: {covered: 0.37},
    message: 'Historical replay describes only 37% of the portfolio: the rest is excluded.',
    carries: ['37'],
};
const KEYED_CASES: KeyedCase[] = [FALLBACK_CASE, SLICE_CASE, EXCLUDED_CASE, STALE_CASE, MOSTLY_EXCLUDED_CASE];

/** A key no catalogue ships: svelte-i18n answers it with the id itself. */
const ABSENT_KEY = 'risk.warnings.synthetic_key_added_after_this_build';
const UNKEYED_CODE = 'synthetic_unkeyed_notice';
const UNKEYED_MESSAGE = 'A synthetic notice the backend sent without a key.';

function warning(code: string, message: string, key?: string | null, params?: WarningParams, details?: Record<string, unknown>): Warning {
    return {code, message, ...(key === undefined ? {} : {message_i18n_key: key}), ...(params === undefined ? {} : {message_params: params}), ...(details === undefined ? {} : {details})};
}

function keyedWarning({code, message, key, params}: KeyedCase, overrides: WarningParams = {}, details?: Record<string, unknown>): Warning {
    return warning(code, message, key, {...params, ...overrides}, details);
}

/** A catalogue sentence formatted exactly as a component formats it: `$_` with the warning's values. */
function resolve(key: string, values: WarningParams): string {
    return get(_)(key, {values});
}

/** The catalogue leaf behind a dotted key, read from `en.json` on disk. */
function enLeaf(key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), en);
}

describe('warningSentence', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('is pinned against keys that exist, resolve, and leak ICU braces when formatted without values', () => {
        for (const {key, params} of KEYED_CASES) {
            expect(typeof enLeaf(key), `${key} is missing from en.json`).toBe('string');
            // On disk is not the same as loaded: a catalogue that never finished
            // loading echoes every id back, and so would the helper.
            expect(get(_)(key), `${key} does not resolve through svelte-i18n: the catalogue is not loaded`).not.toBe(key);
            // The defect's premise, and why these keys were chosen: called without
            // values, svelte-i18n hands back the raw ICU source.
            expect(get(_)(key), `${key} has no ICU argument: a raw sentence could not be told from a formatted one`).toContain('{');
            expect(resolve(key, params), `${key} still carries braces once formatted with its values`).not.toContain('{');
        }
        expect(get(_)(ABSENT_KEY), `${ABSENT_KEY} exists after all: the fallback cases below would not be exercised`).toBe(ABSENT_KEY);
    });

    // `%s` and not `$key`: an object attribute in the title is cut at 40 characters.
    it.each(KEYED_CASES.map((keyed) => [keyed.key, keyed] as const))('words %s with the names, counts and days the warning carries', (_key, keyed) => {
        const expected = resolve(keyed.key, keyed.params);
        for (const value of keyed.carries) {
            expect(expected, `the ${keyed.key} sentence does not show "${value}": its values never reached the formatter`).toContain(value);
        }
        expect(expected, `${keyed.key} formats to the backend sentence itself: nothing here could tell the two branches apart`).not.toBe(keyed.message);

        expect(warningSentence(keyedWarning(keyed), get(_))).toBe(expected);
    });

    it('falls back to the backend sentence for a key this build does not ship, never to the key', () => {
        const sentence = warningSentence(warning('synthetic_code_added_later', 'A synthetic sentence only the backend knows.', ABSENT_KEY, {names: HOLDING_A, count: 1}), get(_));
        expect(sentence).toBe('A synthetic sentence only the backend knows.');
        expect(sentence).not.toContain('risk.warnings.');
    });

    it('falls back to the backend sentence, not to raw ICU, when a value the sentence needs is missing', () => {
        const incomplete: WarningParams = {count: 2}; // `names` is missing
        // svelte-i18n logs the failed format: the log is the premise, not the subject.
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        try {
            // What the fallback rests on: a missing value does not throw, it hands
            // back the raw ICU source — which is what would reach the screen.
            expect(get(_)(EXCLUDED_CASE.key, {values: incomplete}), 'svelte-i18n no longer returns the raw source on a missing value: re-read the fallback rule').toContain('{');

            const sentence = warningSentence(warning(EXCLUDED_CASE.code, EXCLUDED_CASE.message, EXCLUDED_CASE.key, incomplete), get(_));
            expect(sentence).toBe(EXCLUDED_CASE.message);
            expect(sentence).not.toContain('{');
        } finally {
            warn.mockRestore();
        }
    });

    // The backend joins its own lists (`", ".join(...)`) before they reach the wire.
    // One it did not join must read exactly like one it did, not vanish into the
    // fallback because the formatter found no value.
    it('joins a list the backend did not join, exactly as the backend joins its own', () => {
        const listed: Warning = {code: EXCLUDED_CASE.code, message: EXCLUDED_CASE.message, message_i18n_key: EXCLUDED_CASE.key, message_params: {count: 2, names: [HOLDING_A, HOLDING_B]}};
        expect(warningSentence(listed, get(_))).toBe(resolve(EXCLUDED_CASE.key, {count: 2, names: `${HOLDING_A}, ${HOLDING_B}`}));
    });

    it('leaves out a value that is neither a scalar nor a list, so the sentence falls back instead of printing it', () => {
        const nested: Warning = {code: EXCLUDED_CASE.code, message: EXCLUDED_CASE.message, message_i18n_key: EXCLUDED_CASE.key, message_params: {count: 2, names: {first: HOLDING_A}}};
        // The value is left out, so svelte-i18n logs a failed format: the premise again.
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        try {
            const sentence = warningSentence(nested, get(_));
            expect(sentence).toBe(EXCLUDED_CASE.message);
            expect(sentence).not.toContain('[object');
        } finally {
            warn.mockRestore();
        }
    });

    it('shows the backend sentence, trimmed, for a warning that carries no key', () => {
        for (const key of [undefined, null, '']) {
            expect(warningSentence(warning(UNKEYED_CODE, `  ${UNKEYED_MESSAGE}  `, key), get(_)), `message_i18n_key: ${JSON.stringify(key)}`).toBe(UNKEYED_MESSAGE);
        }
    });

    it('keeps the backend sentence when no translator is handed in', () => {
        for (const keyed of KEYED_CASES) {
            expect(warningSentence(keyedWarning(keyed)), keyed.key).toBe(keyed.message);
        }
    });

    it('says nothing for a warning that is not there', () => {
        expect(warningSentence(null, get(_))).toBe('');
        expect(warningSentence(undefined, get(_))).toBe('');
        expect(warningSentence(null)).toBe('');
    });

    it('says nothing, rather than the key, when there is neither a translation nor a sentence', () => {
        expect(warningSentence(warning(UNKEYED_CODE, '   '), get(_))).toBe('');
        expect(warningSentence(warning(UNKEYED_CODE, '   '))).toBe('');
        expect(warningSentence(warning(UNKEYED_CODE, '   ', ABSENT_KEY), get(_))).toBe('');
    });
});

describe('warningSentence — every sentence with arguments in the catalogue', () => {
    /** Stands in for the English `message`; no catalogue sentence reads like it. */
    const BACKEND_SENTENCE = 'A synthetic backend sentence standing in for the English message.';

    beforeAll(async () => {
        await setupI18n();
    });

    // The case below is what stops the list from passing vacuously: `it.each([])`
    // collects no test at all, and a property over nothing is green by definition.
    it('reads its list off the catalogue: never empty, every sentence with braces, the code-equal keys', () => {
        const keys = icuWarningKeys();
        expect(keys.length, 'no risk.warnings sentence with arguments was found: the scan reads the wrong node').toBeGreaterThan(0);
        for (const key of [...CODE_EQUAL_ICU_WARNING_KEYS, ...KEYED_CASES.map((keyed) => keyed.key)]) {
            expect(keys, `${key} is missing from the scanned list`).toContain(key);
        }
        // Completeness: a sentence carrying a brace that the parse found no argument
        // in would otherwise drop out of the property in silence.
        for (const [leaf, text] of Object.entries(en.risk.warnings as Record<string, unknown>)) {
            if (typeof text === 'string' && text.includes('{')) {
                expect(keys, `risk.warnings.${leaf} has braces but the scan found no argument in it`).toContain(`risk.warnings.${leaf}`);
            }
        }
    });

    // Collected when the file loads, so the list is the catalogue's own on every run
    // and a key added tomorrow gets its own case without anyone writing one.
    it.each(icuWarningKeys())('%s is worded with its values, and falls back to the backend sentence without them — never a brace, never a key', (key) => {
        const params = plausibleParams(key);
        const expected = resolve(key, params);
        // The harness first: values that do not complete the sentence would send the
        // helper to its fallback, and the red would belong to this file, not to it.
        expect(expected, `the values built for ${key} do not complete its sentence: ${JSON.stringify(params)}`).not.toContain('{');
        expect(expected, `${key} does not resolve through svelte-i18n`).not.toBe(key);

        const worded = warningSentence(warning('synthetic_code', BACKEND_SENTENCE, key, params), get(_));
        expect(worded, 'with its values').toBe(expected);
        expect(worded, 'with its values').not.toContain('{');
        expect(worded, 'with its values').not.toContain('risk.warnings.');

        const missing: (WarningParams | undefined)[] = [{}, undefined];
        // svelte-i18n logs every failed format: the log is the premise, not the subject.
        const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
        try {
            for (const params of missing) {
                const label = `without values (message_params ${JSON.stringify(params)})`;
                const fallback = warningSentence(warning('synthetic_code', BACKEND_SENTENCE, key, params), get(_));
                expect(fallback, label).toBe(BACKEND_SENTENCE);
                expect(fallback, label).not.toContain('{');
                expect(fallback, label).not.toContain('risk.warnings.');
            }
        } finally {
            warn.mockRestore();
        }
    });
});

describe('resultReasons — keyed warnings', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    function stressResult(instanceId: string, warnings: Warning[]): RiskAnalyticResult {
        return {analytic_code: 'stress', instance_id: instanceId, status: 'partial', warnings, output: {kind: 'stress', method: 'hypothetical'}} as unknown as RiskAnalyticResult;
    }

    /** A result read off the scope's own series (correlation, contribution): the kind that inherits an exclusion. */
    function scopeResult(instanceId: string, analyticCode: string, warnings: Warning[]): RiskAnalyticResult {
        return {analytic_code: analyticCode, instance_id: instanceId, status: 'partial', warnings, output: {kind: 'synthetic'}} as unknown as RiskAnalyticResult;
    }

    it('words each keyed warning through the catalogue and keeps the backend sentence for the rest', () => {
        const fallback = resolve(FALLBACK_CASE.key, FALLBACK_CASE.params);
        const excluded = resolve(EXCLUDED_CASE.key, EXCLUDED_CASE.params);
        const reasons = resultReasons([stressResult('a', [keyedWarning(FALLBACK_CASE), warning(UNKEYED_CODE, UNKEYED_MESSAGE)]), stressResult('b', [keyedWarning(EXCLUDED_CASE)])], get(_));
        expect(reasons).toStrictEqual([
            {key: `${FALLBACK_CASE.code}:${fallback}`, message: fallback, occurrences: 1},
            {key: `${UNKEYED_CODE}:${UNKEYED_MESSAGE}`, message: UNKEYED_MESSAGE, occurrences: 1},
            {key: `${EXCLUDED_CASE.code}:${excluded}`, message: excluded, occurrences: 1},
        ]);
    });

    it('says one worded sentence once, and counts the results that carried it', () => {
        const slice = resolve(SLICE_CASE.key, SLICE_CASE.params);
        const reasons = resultReasons([stressResult('a', [keyedWarning(SLICE_CASE)]), stressResult('b', [keyedWarning(SLICE_CASE)])], get(_));
        expect(reasons).toStrictEqual([{key: `${SLICE_CASE.code}:${slice}`, message: slice, occurrences: 2}]);
    });

    // The backend emits one fallback warning per asset, each carrying the same
    // English sentence. Deduplicated verbatim they collapse into a single line and
    // the reader loses *which* assets were treated as "Other"; worded, the names
    // differ, so the lines must differ too.
    it('keeps two assets apart when one key names each of them under the same backend sentence', () => {
        const first = resolve(FALLBACK_CASE.key, {...FALLBACK_CASE.params, names: HOLDING_A});
        const second = resolve(FALLBACK_CASE.key, {...FALLBACK_CASE.params, names: HOLDING_B});
        expect(first, 'the two names format alike: the split asserted below would prove nothing').not.toBe(second);

        const reasons = resultReasons([stressResult('a', [keyedWarning(FALLBACK_CASE, {names: HOLDING_A}), keyedWarning(FALLBACK_CASE, {names: HOLDING_B})])], get(_));
        expect(reasons).toStrictEqual([
            {key: `${FALLBACK_CASE.code}:${first}`, message: first, occurrences: 1},
            {key: `${FALLBACK_CASE.code}:${second}`, message: second, occurrences: 1},
        ]);
    });

    // The Asset Global callers still pass one argument until a later integration.
    // The catalogue is loaded here on purpose — a helper that reached for the store
    // by itself would be caught — and their output must not move by a byte:
    // verbatim, trimmed, deduplicated by the English sentence, keyed `code:message`.
    it('without a translator, returns exactly the verbatim reasons the one-argument callers get today', () => {
        const reasons = resultReasons([stressResult('a', [keyedWarning(FALLBACK_CASE, {names: HOLDING_A}), keyedWarning(FALLBACK_CASE, {names: HOLDING_B}), warning(UNKEYED_CODE, `  ${UNKEYED_MESSAGE}  `)]), stressResult('b', [keyedWarning(EXCLUDED_CASE), keyedWarning(EXCLUDED_CASE)])]);
        expect(reasons).toStrictEqual([
            {key: `${FALLBACK_CASE.code}:${FALLBACK_CASE.message}`, message: FALLBACK_CASE.message, occurrences: 2},
            {key: `${UNKEYED_CODE}:${UNKEYED_MESSAGE}`, message: UNKEYED_MESSAGE, occurrences: 1},
            {key: `${EXCLUDED_CASE.code}:${EXCLUDED_CASE.message}`, message: EXCLUDED_CASE.message, occurrences: 2},
        ]);
    });

    // Without a translator every `assets_excluded` warning falls back to the backend's one
    // English sentence, whatever its cause: a permanent and an occasional exclusion merge
    // there, and the merged line can claim neither cause nor one set of badges. Worded,
    // the two causes are two sentences, and each keeps its own.
    it('words a permanent and an occasional exclusion apart, each with its own cause and badges — and verbatim merges them into one sentence that claims neither', () => {
        const noSourceKey = 'risk.warnings.assets_excluded_no_price_source';
        const noSourceParams = {count: 1, names: 'Synthetic Holding D'};
        const missing = resolve(EXCLUDED_CASE.key, EXCLUDED_CASE.params);
        const noSource = resolve(noSourceKey, noSourceParams);
        expect(noSource, `guard: ${noSourceKey} does not resolve through svelte-i18n`).not.toBe(noSourceKey);
        expect(noSource, `guard: ${noSourceKey} still carries braces once formatted with its values`).not.toContain('{');
        expect(noSource, 'guard: the two causes word alike, so the split asserted below would prove nothing').not.toBe(missing);

        // One warning per cause, in the backend's order (sorted by reason), on every result that inherited the exclusion.
        const exclusions = (): Warning[] => [keyedWarning(EXCLUDED_CASE, {}, {asset_ids: [22, 23, 24], reason: 'missing_price'}), warning(EXCLUDED_CASE.code, EXCLUDED_CASE.message, noSourceKey, noSourceParams, {asset_ids: [21], reason: 'no_price_source'})];
        const results = [scopeResult('base-historical-correlation', 'correlation', exclusions()), scopeResult('base-current_composition-risk_contribution', 'risk_contribution', exclusions())];

        expect(resultReasons(results, get(_)), 'worded: a cause or its assets were lost, so the notice could neither pick the tone nor draw the badges').toStrictEqual([
            {key: `${EXCLUDED_CASE.code}:${missing}`, message: missing, occurrences: 2, reason: 'missing_price', assetIds: [22, 23, 24]},
            {key: `${EXCLUDED_CASE.code}:${noSource}`, message: noSource, occurrences: 2, reason: 'no_price_source', assetIds: [21]},
        ]);
        expect(resultReasons(results), 'verbatim: one sentence standing for two causes claimed one of them, or badged one set of assets for both').toStrictEqual([{key: `${EXCLUDED_CASE.code}:${EXCLUDED_CASE.message}`, message: EXCLUDED_CASE.message, occurrences: 4}]);
    });

    // `stress.py` emits one fallback per asset, naming it under `details.asset_id` beside the
    // cause. Worded, the names split the sentence, so each asset's line keeps its own badge.
    it('carries the one asset and the cause of each hypothetical fallback, which names its asset under asset_id', () => {
        const first = resolve(FALLBACK_CASE.key, {...FALLBACK_CASE.params, names: HOLDING_A});
        const second = resolve(FALLBACK_CASE.key, {...FALLBACK_CASE.params, names: HOLDING_B});
        const fallback = (names: string, assetId: number): Warning => ({...keyedWarning(FALLBACK_CASE, {names}, {asset_id: assetId, dimension: 'sector', reason: 'missing_classification_metadata'}), degrades_result: false});

        expect(resultReasons([stressResult('a', [fallback(HOLDING_A, 31), fallback(HOLDING_B, 32)])], get(_))).toStrictEqual([
            {key: `${FALLBACK_CASE.code}:${first}`, message: first, occurrences: 1, reason: 'missing_classification_metadata', assetIds: [31]},
            {key: `${FALLBACK_CASE.code}:${second}`, message: second, occurrences: 1, reason: 'missing_classification_metadata', assetIds: [32]},
        ]);
    });
});

describe('resultErrorCodes', () => {
    function failed(instanceId: string, error: unknown): RiskAnalyticResult {
        return {analytic_code: 'correlation', instance_id: instanceId, status: 'failed', error} as unknown as RiskAnalyticResult;
    }

    it('gives back the code of a measurement that never ran', () => {
        expect(resultErrorCodes([failed('a', {code: 'incompatible_scope'})])).toEqual(['incompatible_scope']);
    });

    // `RiskResultFrame:23` reads the same field through `singleValue` because the
    // generated client types it as a value *or* a list. Reaching for
    // `result.error.code` works on today's payload and returns `undefined` the
    // day one arrives wrapped — an error that would then disclose nothing at all,
    // with nothing turning red.
    it('reads an error that arrives wrapped in a list', () => {
        expect(resultErrorCodes([failed('a', [{code: 'insufficient_history'}])])).toEqual(['insufficient_history']);
    });

    it('says one cause once, however many measurements share it', () => {
        expect(resultErrorCodes([failed('a', {code: 'incompatible_scope'}), failed('b', {code: 'incompatible_scope'})])).toEqual(['incompatible_scope']);
    });

    it('keeps two different causes apart, in the order they arrived', () => {
        expect(resultErrorCodes([failed('a', {code: 'insufficient_history'}), failed('b', {code: 'incompatible_scope'})])).toEqual(['insufficient_history', 'incompatible_scope']);
    });

    it('stays empty for results that answered, or did not arrive', () => {
        expect(resultErrorCodes([{analytic_code: 'x', instance_id: 'a', status: 'ok', output: {}} as unknown as RiskAnalyticResult])).toEqual([]);
        expect(resultErrorCodes([null, undefined])).toEqual([]);
        expect(resultErrorCodes([failed('a', null), failed('b', {}), failed('c', {code: '   '}), failed('d', {code: 7})])).toEqual([]);
    });
});

describe('translateErrorCode', () => {
    // Stands in for `svelte-i18n`, whose documented behaviour for a missing
    // message is to return the key itself. That behaviour is the entire reason
    // the guard exists, so the double has to reproduce it exactly.
    const catalogue: Record<string, string> = {
        'risk.errors.incompatible_scope': 'This analytic does not support the selected scope.',
        'risk.errors.unknown': 'This measurement did not return a result.',
    };
    const translate = (key: string): string => catalogue[key] ?? key;

    it('words a known code with its own sentence', () => {
        expect(translateErrorCode('incompatible_scope', translate, 'risk.errors.unknown')).toBe('This analytic does not support the selected scope.');
    });

    // The defect recorded at `RiskResultFrame:108`: without the `translated === key`
    // comparison, a code the backend gains tomorrow prints `risk.errors.<code>` on
    // screen. Nothing else in the stack catches it — a key is a string, and a
    // string renders.
    it('falls back rather than printing its own key for a code nobody has seen', () => {
        const rendered = translateErrorCode('a_code_added_next_month', translate, 'risk.errors.unknown');
        expect(rendered).toBe('This measurement did not return a result.');
        expect(rendered).not.toContain('risk.errors.');
    });

    it('falls back when there is no code at all', () => {
        expect(translateErrorCode(null, translate, 'risk.errors.unknown')).toBe('This measurement did not return a result.');
        expect(translateErrorCode('', translate, 'risk.errors.unknown')).toBe('This measurement did not return a result.');
    });

    // The translator is an argument, not an import, so that the call sits inside
    // the caller's reactive scope: reading the store here would word the sentence
    // once and keep it in the old language after a switch.
    it('re-words through whichever translator it is handed', () => {
        const italian = (key: string): string => (key === 'risk.errors.incompatible_scope' ? 'Questa analitica non supporta lo scope selezionato.' : key);
        expect(translateErrorCode('incompatible_scope', italian, 'risk.errors.unknown')).toBe('Questa analitica non supporta lo scope selezionato.');
    });
});

/**
 * ─── D379: a refusal for size, worded by the setting that cures it ───────────────────────────────
 *
 * The simulation refuses a run too large to carry with `resource_limit`, and its `details` now
 * say which limit was hit and which setting brings the run back within reach: `{metric, actual,
 * limit, remedy}`, the remedy one of four (`simulation.py::_REMEDY_BY_METRIC`). The four are not
 * interchangeable — fewer paths or a shorter horizon cure only the path budgets, a history too
 * long needs a shorter period, the Sobol dimension ignores the paths, and no setting shrinks the
 * number of positions — so one generic «too large to run» leaves the reader guessing which
 * setting to change, and over the 100-position ceiling no setting helps at all. A metric the
 * backend has no remedy for still answers `resource_limit`, without one.
 *
 * The contract pinned below, written red first against a module that exports neither new name:
 *
 *   - `RESOURCE_LIMIT_REMEDIES`: the four remedies, in the order of `REMEDIES`;
 *   - `errorDisplayCode(error)`: the code an error is worded by — `resource_limit_<remedy>` for a
 *     remedy this build knows, the code itself (trimmed) for anything else, `null` for no code;
 *   - `resultErrorCodes` hands the levels those display codes, deduplicated in arrival order;
 *   - `translateErrorCode` is unchanged: each display code is a key of its own, which every
 *     catalogue ships.
 *
 * The two new names are read through the module namespace, as `syncTargets.test.ts` reads
 * `labQualityAction`: until they exist, the cases calling them fail on an assertion naming what
 * is missing — those cases only, never the collection of this file.
 */

/** The four remedies a refusal can name, in the contract's order: this file's own copy, which the export is pinned to. */
const REMEDIES = ['paths_or_horizon', 'horizon_or_sampling', 'period', 'positions'] as const;
type Remedy = (typeof REMEDIES)[number];

/** `MAX_SIMULATION_ASSETS`, the ceiling the `positions` sentence cites: pinned on the backend by `test_the_ceilings_cited_to_the_user_are_pinned`. */
const POSITIONS_CEILING = 100;

const GENERIC_LIMIT_KEY = 'risk.errors.resource_limit';
const UNKNOWN_ERROR_KEY = 'risk.errors.unknown';

/** The display code of a refusal naming `remedy`, and the catalogue key that words it. */
const remedyCode = (remedy: Remedy): string => `resource_limit_${remedy}`;
const remedyKey = (remedy: Remedy): string => `risk.errors.${remedyCode(remedy)}`;

/** One refusal per remedy, its details as `simulation.py::_resource_limit` sends them for a metric that maps to it. */
const REFUSAL_DETAILS: Record<Remedy, Record<string, unknown>> = {
    paths_or_horizon: {metric: 'portfolio_cells', actual: 20_000_001, limit: 20_000_000, remedy: 'paths_or_horizon'},
    horizon_or_sampling: {metric: 'sobol_dimension', actual: 21_202, limit: 21_201, remedy: 'horizon_or_sampling'},
    period: {metric: 'observations', actual: 5001, limit: 5000, remedy: 'period'},
    positions: {metric: 'assets', actual: 101, limit: POSITIONS_CEILING, remedy: 'positions'},
};

/** What `errorDisplayCode` reads, as the contract types it: declared here, so the cases compile before the export exists. */
type DisplayedError = {code?: unknown; details?: unknown} | null | undefined;

/** The module's exports by name: a name it does not export reads `undefined` here, instead of failing the whole file. */
const levelHelperExports = levelHelpers as unknown as Record<string, unknown>;

/**
 * `errorDisplayCode`, called through the module. Until the export exists every case calling it
 * fails here, on the assertion that names what is missing, rather than on a `TypeError` thrown
 * before any assertion ran.
 */
function errorDisplayCode(error: DisplayedError): string | null {
    const helper = levelHelperExports.errorDisplayCode;
    expect(typeof helper, 'levelHelpers exports no errorDisplayCode(): a resource_limit refusal cannot be worded by the remedy it names').toBe('function');
    return (helper as (error: DisplayedError) => string | null)(error);
}

/** `RESOURCE_LIMIT_REMEDIES`, read the same way. */
function resourceLimitRemedies(): unknown {
    const remedies = levelHelperExports.RESOURCE_LIMIT_REMEDIES;
    expect(Array.isArray(remedies), 'levelHelpers exports no RESOURCE_LIMIT_REMEDIES list: nothing says which remedies this build words').toBe(true);
    return remedies;
}

/** A `resource_limit` refusal carrying `details` as given. */
const limitRefusal = (details: unknown): DisplayedError => ({code: 'resource_limit', details});

describe('RESOURCE_LIMIT_REMEDIES', () => {
    it('lists exactly the four remedies a refusal can name, in order', () => {
        expect(resourceLimitRemedies()).toStrictEqual([...REMEDIES]);
    });
});

describe('errorDisplayCode — the code an error is worded by', () => {
    it.each([...REMEDIES])('words a resource_limit refusal naming %s by that remedy', (remedy) => {
        expect(errorDisplayCode(limitRefusal(REFUSAL_DETAILS[remedy]))).toBe(remedyCode(remedy));
    });

    // The remedy alone decides: the rest of the details describes the limit, not the cure.
    it('needs nothing from the details but the remedy', () => {
        expect(errorDisplayCode(limitRefusal({remedy: 'period'}))).toBe('resource_limit_period');
    });

    it('reads the code trimmed, and refines it once trimmed', () => {
        expect(errorDisplayCode({code: '  incompatible_scope\t'})).toBe('incompatible_scope');
        expect(errorDisplayCode({code: ' resource_limit\n', details: REFUSAL_DETAILS.positions})).toBe('resource_limit_positions');
    });

    it.each<[string, DisplayedError]>([
        ['no error', null],
        ['an undefined error', undefined],
        ['an error without a code', {}],
        ['an undefined code', {code: undefined}],
        ['a null code', {code: null}],
        ['an empty code', {code: ''}],
        ['a blank code', {code: '   '}],
        ['a numeric code', {code: 7}],
        ['a code wrapped in a list', {code: ['resource_limit']}],
        ['a known remedy without a code', {details: REFUSAL_DETAILS.period}],
        ['a blank code beside a known remedy', {code: '  ', details: REFUSAL_DETAILS.period}],
    ])('has no code for %s', (_label, error) => {
        expect(errorDisplayCode(error)).toBeNull();
    });

    // Strict on purpose. A display code is a catalogue key: one built from a remedy this build has
    // no sentence for falls through `translateErrorCode` to `risk.errors.unknown`, which no longer
    // says the run was too large at all — the generic sentence is the honest answer there. The
    // prototype names catch a lookup through a plain object, where `constructor` is always found.
    it.each<[string, DisplayedError]>([
        ['no details', {code: 'resource_limit'}],
        ['null details', limitRefusal(null)],
        ['details naming no remedy, as for a metric the backend has none for', limitRefusal({metric: 'synthetic_cells', actual: 11, limit: 10})],
        ['a remedy added after this build', limitRefusal({...REFUSAL_DETAILS.period, remedy: 'future_remedy'})],
        ['an empty remedy', limitRefusal({remedy: ''})],
        ['a fragment of two real remedies', limitRefusal({remedy: 'horizon'})],
        ['a numeric remedy', limitRefusal({remedy: 7})],
        ['a null remedy', limitRefusal({remedy: null})],
        ['a remedy wrapped in a list', limitRefusal({remedy: ['period']})],
        ['details that are a list', limitRefusal([{remedy: 'period'}])],
        ['a list carrying a remedy of its own', limitRefusal(Object.assign(['period'], {remedy: 'period'}))],
        ['the remedy "constructor"', limitRefusal({remedy: 'constructor'})],
        ['the remedy "toString"', limitRefusal({remedy: 'toString'})],
        ['the remedy "__proto__"', limitRefusal({remedy: '__proto__'})],
    ])('keeps resource_limit generic for %s', (_label, error) => {
        expect(errorDisplayCode(error)).toBe('resource_limit');
    });

    // Only `resource_limit` is refined. The near misses catch a prefix, a suffix or a
    // case-insensitive match; an already refined code is not refined a second time.
    it.each(['invalid_parameters', 'insufficient_history', 'resource_limit_period', 'not_a_resource_limit', 'RESOURCE_LIMIT'])('returns %s unchanged, whatever remedy its details name', (code) => {
        for (const remedy of REMEDIES) {
            expect(errorDisplayCode({code, details: REFUSAL_DETAILS[remedy]}), `${code} beside the remedy ${remedy}`).toBe(code);
        }
    });
});

describe('resultErrorCodes — a refusal for size keeps the remedy it names', () => {
    const REFUSAL_MESSAGE = 'A synthetic backend refusal sentence.';

    /** A simulation the backend refused, as a level receives it. */
    function refusedResult(instanceId: string, error: unknown): RiskAnalyticResult {
        return {analytic_code: 'simulation', instance_id: instanceId, status: 'unavailable', error} as unknown as RiskAnalyticResult;
    }

    function refusal(remedy: Remedy): Record<string, unknown> {
        return {code: 'resource_limit', message: REFUSAL_MESSAGE, details: REFUSAL_DETAILS[remedy]};
    }

    it('gives back one code per remedy when two refusals name different ones', () => {
        expect(resultErrorCodes([refusedResult('a', refusal('period')), refusedResult('b', refusal('positions'))])).toEqual(['resource_limit_period', 'resource_limit_positions']);
    });

    it('says one remedy once, however many refusals name it', () => {
        expect(resultErrorCodes([refusedResult('a', refusal('paths_or_horizon')), refusedResult('b', refusal('paths_or_horizon'))])).toEqual(['resource_limit_paths_or_horizon']);
    });

    // A refusal naming no remedy and one naming a remedy this build does not know are the
    // same generic cause: said once, beside the refined one and never in its place.
    it('keeps a plain resource_limit beside a refined one, and says the generic cause once', () => {
        const plain = {code: 'resource_limit', message: REFUSAL_MESSAGE};
        const unknownRemedy = {code: 'resource_limit', message: REFUSAL_MESSAGE, details: {...REFUSAL_DETAILS.period, remedy: 'future_remedy'}};
        expect(resultErrorCodes([refusedResult('a', plain), refusedResult('b', refusal('horizon_or_sampling')), refusedResult('c', unknownRemedy)])).toEqual(['resource_limit', 'resource_limit_horizon_or_sampling']);
    });

    // Through `singleValue`, as the cases above pin it for the code alone: an error that
    // arrives wrapped must keep its remedy, not lose it to the generic sentence.
    it('reads the remedy of a refusal that arrives wrapped in a list', () => {
        expect(resultErrorCodes([refusedResult('a', [refusal('positions')])])).toEqual(['resource_limit_positions']);
    });

    it('keeps first-seen order across refined and other codes, and skips what carries no code', () => {
        const results = [
            null,
            refusedResult('a', refusal('positions')),
            refusedResult('b', {code: 'incompatible_scope', message: REFUSAL_MESSAGE, details: {remedy: 'period'}}),
            refusedResult('c', {code: '   '}),
            undefined,
            refusedResult('d', refusal('period')),
            refusedResult('e', refusal('positions')),
        ];
        expect(resultErrorCodes(results)).toEqual(['resource_limit_positions', 'incompatible_scope', 'resource_limit_period']);
    });
});

describe('translateErrorCode — each remedy has a sentence of its own in the shipped catalogue', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it.each([...REMEDIES])('words resource_limit_%s with its own en.json sentence — not its key, not the generic one, not risk.errors.unknown', (remedy) => {
        const code = remedyCode(remedy);
        const key = remedyKey(remedy);
        const generic = get(_)(GENERIC_LIMIT_KEY);
        const unknown = get(_)(UNKNOWN_ERROR_KEY);
        // The harness first: the two sentences this one must differ from are real, and differ from each other.
        expect(generic, `${GENERIC_LIMIT_KEY} does not resolve: the catalogue is not loaded`).not.toBe(GENERIC_LIMIT_KEY);
        expect(unknown, `${UNKNOWN_ERROR_KEY} does not resolve: the catalogue is not loaded`).not.toBe(UNKNOWN_ERROR_KEY);
        expect(generic, `${GENERIC_LIMIT_KEY} reads like ${UNKNOWN_ERROR_KEY}: which of the two answered could not be told`).not.toBe(unknown);

        const worded = translateErrorCode(code, get(_), UNKNOWN_ERROR_KEY);
        expect(worded, `${code} printed its own key`).not.toBe(key);
        expect(worded, `${code} fell back to ${UNKNOWN_ERROR_KEY}: the catalogue has no ${key}`).not.toBe(unknown);
        expect(worded, `${code} reads like ${GENERIC_LIMIT_KEY}: the refusal still does not say which setting to change`).not.toBe(generic);
        expect(worded, `${code} is not worded with its own en.json sentence`).toBe(enLeaf(key));
    });
});

describe('the catalogues word every remedy a refusal can name', () => {
    /** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
    const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

    /** The leaf behind a dotted key in one catalogue, read from the file on disk. */
    function leaf(catalogue: unknown, key: string): unknown {
        return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    }

    /** Whitespace is not wording: two sentences differing only by it read alike. */
    function normalize(text: string): string {
        return text.replace(/\s+/g, ' ').trim();
    }

    it.each([...SUPPORTED_LOCALES])('%s.json words each remedy with a sentence of its own, none of them the generic one, and the positions one cites the ceiling', (locale) => {
        const catalogue = CATALOGUES[locale];
        const generic = leaf(catalogue, GENERIC_LIMIT_KEY);
        // Positive control: the generic sentence lives beside the four, so a red below is a
        // missing sentence, not a guard reading the wrong place.
        expect(typeof generic, `${GENERIC_LIMIT_KEY} is not a sentence in ${locale}.json: this guard reads the wrong place`).toBe('string');

        const keys = REMEDIES.map(remedyKey);
        const missing = keys.filter((key) => {
            const sentence = leaf(catalogue, key);
            return typeof sentence !== 'string' || sentence.trim() === '';
        });
        expect(missing, `${locale}.json does not word these remedies`).toEqual([]);

        const sentences = keys.map((key) => normalize(String(leaf(catalogue, key))));
        sentences.forEach((sentence, index) => {
            expect(sentence, `${keys[index]} reads like ${GENERIC_LIMIT_KEY} in ${locale}.json: the reader is still not told which setting to change`).not.toBe(normalize(String(generic)));
            // A code is worded without values (`translateErrorCode`, the frame's own lookup): an ICU argument would reach the screen as its braces.
            expect(sentence, `${keys[index]} takes ICU arguments in ${locale}.json, but an error code is worded without values`).not.toMatch(/[{}]/);
        });
        expect(new Set(sentences).size, `two remedies read alike in ${locale}.json: ${JSON.stringify(sentences)}`).toBe(REMEDIES.length);
        // The ceiling as a number of its own: «1000» contains the digits and cites another one.
        expect(sentences[REMEDIES.indexOf('positions')], `${remedyKey('positions')} does not cite the ceiling of ${POSITIONS_CEILING} positions in ${locale}.json`).toMatch(new RegExp(`(?<!\\d)${POSITIONS_CEILING}(?!\\d)`));
    });
});
