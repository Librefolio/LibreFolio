/**
 * moveFigures — the positive twins of one scope, read once for the lab's table and the levels' block (RN-18, Vitest).
 *
 * The lab's reading (`buildAssetSetMoveRows`) is pinned in `assetSetLevels.test.ts` and goes through the same
 * `readMoveFigures`; this file pins the one-scope builder the levels' block «How does it move?» reads: the historical
 * KPI, the best window of the 30-day VaR and the drawdown summary, with the payloads as the contract validates them.
 */
import {describe, expect, it} from 'vitest';

import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';
import {buildMoveFigures, moveLead, semiDeviationPerimeterDiffers} from './moveFigures';

type Payload = Record<string, unknown>;

function ok(code: string, output: Payload, warnings: Payload[] = []): RiskAnalyticResult {
    return {instance_id: `base-historical-${code}`, analytic_code: code, status: 'ok', output, warnings} as unknown as RiskAnalyticResult;
}

/** The KPI with every positive figure RN-14 publishes. */
const SHAPE = {
    best_realization: 0.034,
    best_realization_date: '2026-04-09',
    positive_observation_share: 0.54,
    mean_positive_return: 0.007,
    mean_negative_return: -0.006,
    longest_positive_run_observations: 9,
    longest_positive_run_start_date: '2026-06-03',
    longest_positive_run_end_date: '2026-06-13',
    omega_ratio: 1.25,
    downside_deviation: 0.098,
    extreme_day_ratio: 2.4,
};

function kpi(fields: Payload = SHAPE, warnings: Payload[] = []): RiskAnalyticResult {
    return ok('historical_kpi', {kind: 'kpi', volatility: 0.139, max_drawdown: -0.16, max_drawdown_duration_days: 63, ...fields}, warnings);
}

function monthlyVar(best: Payload | null): RiskAnalyticResult {
    return ok('historical_var', {kind: 'var_cvar', confidence_level: 0.95, horizon_days: 30, horizon_observations: 21, observations: 231, value_at_risk: 0.12, conditional_value_at_risk: 0.146, best_horizon: best});
}

function drawdown(fields: Payload): RiskAnalyticResult {
    return ok('drawdown_summary', {
        kind: 'drawdown',
        current_drawdown: -0.127,
        current_peak_date: '2026-11-06',
        current_drawdown_duration_days: 11,
        maximum_drawdown: -0.16,
        maximum_drawdown_recovery_status: 'recovered',
        maximum_drawdown_duration_days: 63,
        remaining_to_peak_ratio: 0.145,
        available_start: '2025-11-17',
        available_end: '2026-11-17',
        n_observations: 251,
        coverage: 1,
        calculation_basis: 'price_only_close',
        return_basis: 'price_only',
        ...fields,
    });
}

const RALLY = {largest_rally: 0.246, largest_rally_start_date: '2026-04-21', largest_rally_end_date: '2026-11-04', largest_rally_duration_days: 197, average_drawdown: -0.021};

describe('buildMoveFigures — one scope', () => {
    it('reads each figure from the answer that measures it, with its dates', () => {
        const figures = buildMoveFigures(kpi(), monthlyVar({compounded_return: 0.116, start_date: '2026-04-22', end_date: '2026-05-21'}), drawdown(RALLY));

        expect(figures).toEqual({
            volatility: 0.139,
            riskFreeRate: null,
            bestDay: 0.034,
            bestDayDate: '2026-04-09',
            bestMonth: {gain: 0.116, from: '2026-04-22', to: '2026-05-21'},
            rally: {gain: 0.246, from: '2026-04-21', to: '2026-11-04', days: 197},
            omega: 1.25,
            positiveShare: 0.54,
            downsideDeviation: 0.098,
            meanUp: 0.007,
            meanDown: -0.006,
            streak: {days: 9, from: '2026-06-03', to: '2026-06-13'},
            averageDrawdown: -0.021,
            extremeDays: 2.4,
            reasons: {},
        });
    });

    it('keeps a best 30 days that lost, and a rally of zero as a measured zero with no dates', () => {
        const figures = buildMoveFigures(kpi(), monthlyVar({compounded_return: -0.021, start_date: '2026-04-22', end_date: '2026-05-21'}), drawdown({...RALLY, largest_rally: 0, largest_rally_duration_days: 0}));

        expect(figures?.bestMonth).toEqual({gain: -0.021, from: '2026-04-22', to: '2026-05-21'});
        expect(figures?.rally).toEqual({gain: 0, from: null, to: null, days: 0});
    });

    it('says why a figure is blank: the warning of one scope names no asset', () => {
        const blank = {...SHAPE, best_realization: null, best_realization_date: null, mean_positive_return: null, omega_ratio: null, longest_positive_run_observations: null};
        const figures = buildMoveFigures(
            kpi(blank, [
                {code: 'best_realization_undefined', message: 'no gain'},
                {code: 'omega_undefined', message: 'no loss'},
            ]),
            null,
            null,
        );

        expect(figures?.bestDay).toBeNull();
        expect(figures?.omega).toBeNull();
        expect(figures?.reasons).toEqual({
            bestDay: 'risk.warnings.best_realization_undefined',
            meanUp: 'risk.warnings.best_realization_undefined',
            streak: 'risk.warnings.best_realization_undefined',
            omega: 'risk.warnings.omega_undefined',
        });
    });

    it('fills what answered on a short history: the drawdown without the KPI', () => {
        const figures = buildMoveFigures(null, null, drawdown(RALLY));

        expect(figures?.rally).toEqual({gain: 0.246, from: '2026-04-21', to: '2026-11-04', days: 197});
        expect(figures?.averageDrawdown).toBe(-0.021);
        expect(figures?.bestDay).toBeNull();
        expect(figures?.bestMonth).toBeNull();
    });

    it('reads the risk-free rate the KPI was charged (RN-21), never one beside it', () => {
        const charged = {...kpi(), metadata: {risk_free: {annual_rate: 0.025, source: 'analytic_param', currency: 'EUR'}}} as unknown as RiskAnalyticResult;
        expect(buildMoveFigures(charged, null, null)?.riskFreeRate).toBe(0.025);
        expect(buildMoveFigures(kpi(), null, null)?.riskFreeRate, 'an answer that names no rate').toBeNull();
    });

    it('is null when none of the three answered', () => {
        expect(buildMoveFigures(null, null, null)).toBeNull();
        expect(buildMoveFigures({instance_id: 'x', analytic_code: 'historical_kpi', status: 'unavailable', output: null} as unknown as RiskAnalyticResult, null, null)).toBeNull();
    });
});

describe('moveLead — the block’s headline (RN-18)', () => {
    /** A translator that shows the key and its values, so the case reads what was asked, not a language. */
    const t = (key: string, options?: {values?: Record<string, unknown>}) => `${key}${options?.values ? ` ${JSON.stringify(options.values)}` : ''}`;
    const base = {bestDay: null, bestDayDate: null, bestMonth: null, positiveShare: null, downsideDeviation: null, meanUp: null, meanDown: null, streak: null, averageDrawdown: null, extremeDays: null, reasons: {}};

    it('says gains against losses and how long the largest rally lasted', () => {
        expect(moveLead({...base, omega: 1.25, rally: {gain: 0.246, from: '2026-04-21', to: '2026-11-04', days: 197}}, t)).toBe(`risk.levels.move.lead.both ${JSON.stringify({omega: '1.25', days: 'risk.levels.l1.daysCount {"days":197}'})}`);
    });

    it('says gains against losses alone when the rally has no length', () => {
        expect(moveLead({...base, omega: 1.9, rally: {gain: 0, from: null, to: null, days: 0}}, t)).toBe(`risk.levels.move.lead.omega ${JSON.stringify({omega: '1.90'})}`);
        expect(moveLead({...base, omega: 1.9, rally: null}, t)).toBe(`risk.levels.move.lead.omega ${JSON.stringify({omega: '1.90'})}`);
    });

    // RN-21 (the consultant, 17/11/2026): with a rate the headline counts from it and names it, as the answer used it.
    it('counts from the risk-free rate the answer was charged, and names it a year', () => {
        expect(moveLead({...base, omega: 1.25, rally: {gain: 0.246, from: '2026-04-21', to: '2026-11-04', days: 197}, riskFreeRate: 0.025}, t)).toBe(`risk.levels.move.lead.bothWithRate ${JSON.stringify({omega: '1.25', days: 'risk.levels.l1.daysCount {"days":197}', rate: '2.5%'})}`);
        expect(moveLead({...base, omega: 1.9, rally: null, riskFreeRate: 0.025}, t)).toBe(`risk.levels.move.lead.omegaWithRate ${JSON.stringify({omega: '1.90', rate: '2.5%'})}`);
    });

    it('names the rate with every decimal the field keeps, never rounded', () => {
        expect(moveLead({...base, omega: 1.9, rally: null, riskFreeRate: 0.00125}, t)).toBe(`risk.levels.move.lead.omegaWithRate ${JSON.stringify({omega: '1.90', rate: '0.125%'})}`);
    });

    it('keeps today’s headline at a rate of 0', () => {
        expect(moveLead({...base, omega: 1.9, rally: null, riskFreeRate: 0}, t)).toBe(`risk.levels.move.lead.omega ${JSON.stringify({omega: '1.90'})}`);
    });

    it('says nothing without gains against losses: an invented headline is worse than none', () => {
        expect(moveLead({...base, omega: null, rally: {gain: 0.2, from: '2026-01-01', to: '2026-02-01', days: 31}}, t)).toBe('');
        expect(moveLead(null, t)).toBe('');
    });
});

// RN-18b: the semi-deviation's tooltip says its swing can differ from L3's volatility only when the two really read two
// series — the portfolio as lived (L1's historical KPI) against today's holdings (L3's current-composition KPI).
describe('semiDeviationPerimeterDiffers', () => {
    it('is true on a portfolio whose history is its own and whose L3 is on today’s holdings', () => {
        expect(semiDeviationPerimeterDiffers({oneAsset: false, backtest: false, l3Perimeter: 'current_composition'})).toBe(true);
    });

    it('is false on one asset, on a backtest (the history is today’s holdings replayed), and when L3 fell back to the history', () => {
        expect(semiDeviationPerimeterDiffers({oneAsset: true, backtest: false, l3Perimeter: 'current_composition'})).toBe(false);
        expect(semiDeviationPerimeterDiffers({oneAsset: false, backtest: true, l3Perimeter: 'current_composition'})).toBe(false);
        expect(semiDeviationPerimeterDiffers({oneAsset: false, backtest: false, l3Perimeter: 'historical'})).toBe(false);
        expect(semiDeviationPerimeterDiffers({oneAsset: false, backtest: false, l3Perimeter: null})).toBe(false);
    });
});
