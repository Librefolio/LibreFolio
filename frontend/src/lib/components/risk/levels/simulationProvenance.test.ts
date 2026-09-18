import {describe, expect, it} from 'vitest';

import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {buildSimulationProvenance} from './simulationProvenance';

/** A simulation output shaped like today's backend, before K6's fields land. */
function simulation(overrides: Record<string, unknown> = {}): RiskAnalyticResult {
    return {
        analytic_code: 'simulation',
        instance_id: 'base-simulation',
        status: 'ok',
        output: {
            kind: 'simulation',
            process: 'gbm',
            sampling_method: 'mc',
            horizon_days: 252,
            path_count: 2000,
            drift_estimator: 'historical_log_mle',
            covariance_estimator: 'sample_log_returns',
            aggregation_policy: 'current_buy_and_hold',
            costs_included: false,
            cash_flows_included: false,
            inflation_included: false,
            rebalanced: false,
            ...overrides,
        },
    } as unknown as RiskAnalyticResult;
}

function entryFor(result: RiskAnalyticResult, key: string) {
    return buildSimulationProvenance(result)?.entries.find((entry) => entry.key === key) ?? null;
}

describe('buildSimulationProvenance', () => {
    it('has nothing to describe when the simulation never succeeded', () => {
        expect(buildSimulationProvenance(null)).toBeNull();
        expect(buildSimulationProvenance({analytic_code: 'simulation', instance_id: 'base-simulation', status: 'unavailable', output: null} as unknown as RiskAnalyticResult)).toBeNull();
    });

    it('reports the estimators the reader did not choose and could not guess', () => {
        // `horizon_days` and `path_count` are the two the user typed in. Printing
        // those back as "assumptions" tells the reader only what they already knew.
        expect(entryFor(simulation(), 'driftEstimator')).toEqual({key: 'driftEstimator', value: 'historical_log_mle', number: null});
        expect(entryFor(simulation(), 'covarianceEstimator')).toEqual({key: 'covarianceEstimator', value: 'sample_log_returns', number: null});
        expect(entryFor(simulation(), 'process')?.value).toBe('gbm');
        expect(entryFor(simulation(), 'sampling')?.value).toBe('mc');
        expect(entryFor(simulation(), 'aggregation')?.value).toBe('current_buy_and_hold');
    });

    it('reads the four effects from the payload in both directions', () => {
        const stated = buildSimulationProvenance(simulation());
        expect(stated?.exclusions).toEqual(['costs', 'cashFlows', 'inflation', 'rebalancing']);
        expect(stated?.inclusions).toEqual([]);

        // The hard-coded sentence cannot do this: it says "without rebalancing"
        // in four languages whatever the payload states.
        const rebalanced = buildSimulationProvenance(simulation({rebalanced: true, costs_included: true}));
        expect(rebalanced?.inclusions).toEqual(['costs', 'rebalancing']);
        expect(rebalanced?.exclusions).toEqual(['cashFlows', 'inflation']);
    });

    it('stays silent about an effect the payload never mentions', () => {
        // Absent is not false. A cone that never said whether it charges costs
        // has not said that it doesn't, and claiming otherwise would put a
        // sentence on screen that no field backs.
        const silent = buildSimulationProvenance(simulation({costs_included: undefined, rebalanced: undefined}));
        expect(silent?.exclusions).toEqual(['cashFlows', 'inflation']);
        expect(silent?.inclusions).toEqual([]);
    });

    it('refuses a truthy flag that is not a boolean', () => {
        // `'false'` is a string and every string is truthy: read loosely it would
        // flip the statement to its exact opposite.
        const loose = buildSimulationProvenance(simulation({costs_included: 'false', rebalanced: 1}));
        expect(loose?.inclusions).toEqual([]);
        expect(loose?.exclusions).toEqual(['cashFlows', 'inflation']);
    });

    describe('K6 — the fields that are not in this baseline yet', () => {
        it('adds nothing when they are absent, so today\u2019s payload renders unchanged', () => {
            const provenance = buildSimulationProvenance(simulation());
            expect(provenance?.entries.map((entry) => entry.key)).toEqual(['process', 'sampling', 'driftEstimator', 'covarianceEstimator', 'aggregation']);
            expect(provenance?.truncation).toBeNull();
        });

        it('carries a regime together with the span it was declared over', () => {
            const entry = entryFor(simulation({regime: 'crisis', regime_declared_days: 60}), 'regime');
            expect(entry).toEqual({key: 'regime', value: 'crisis', number: 60});
        });

        it('drops a regime that arrives without its declared span', () => {
            // The server makes this impossible; a fixture is validated by nobody.
            // A regime name with no span is the ambiguity the validator exists to
            // forbid, so it is not rendered as though it were complete.
            expect(entryFor(simulation({regime: 'crisis'}), 'regime')).toBeNull();
            expect(entryFor(simulation({regime_declared_days: 60}), 'regime')).toBeNull();
        });

        it('notes the truncation when the regime was applied over a different span', () => {
            const provenance = buildSimulationProvenance(simulation({regime: 'crisis', regime_declared_days: 250, regime_applied_days: 60}));
            expect(provenance?.truncation).toEqual({declaredDays: 250, appliedDays: 60});
        });

        it('says nothing when declared and applied agree', () => {
            const provenance = buildSimulationProvenance(simulation({regime: 'crisis', regime_declared_days: 60, regime_applied_days: 60}));
            expect(provenance?.truncation).toBeNull();
        });

        it('reports the block length and the seed that make a run reproducible', () => {
            const provenance = buildSimulationProvenance(simulation({block_length_days: 20, bootstrap_seed: 424242}));
            expect(provenance?.entries).toContainEqual({key: 'blockLength', value: null, number: 20});
            expect(provenance?.entries).toContainEqual({key: 'seed', value: null, number: 424242});
        });

        it('rejects day counts that are not whole positive days', () => {
            for (const bad of [0, -5, 12.5, Number.NaN, Number.POSITIVE_INFINITY, '20']) {
                expect(entryFor(simulation({block_length_days: bad}), 'blockLength')).toBeNull();
            }
        });
    });
});
