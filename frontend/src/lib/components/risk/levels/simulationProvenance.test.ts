import {describe, expect, it} from 'vitest';

import {schemas} from '$lib/api';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {buildSimulationProvenance} from './simulationProvenance';

/**
 * Why this file parses its fixtures instead of asserting them.
 *
 * The previous version of these tests built the payload by hand and cast it
 * with `as unknown as RiskAnalyticResult`. That cast is not a convenience — it
 * is the mechanism by which every defect in this module stayed green. A
 * hand-built fixture agrees with whatever the production code assumes, so it
 * can confirm an address but never falsify one: the seed was read from
 * `output`, the fixture put it in `output`, and the pair agreed with each other
 * while disagreeing with the server. Likewise `regime: 'crisis'`, a value the
 * enum has never contained, travelled through five assertions unchallenged.
 *
 * So the fixtures below are parsed through the **generated Zod schemas**
 * (`src/lib/api/generated.ts`, produced from the backend's own OpenAPI). That
 * makes the contract the arbiter of the fixture rather than the other way
 * round, and it does so in the two directions that matter:
 *
 *   - a field at the wrong address is **stripped** (`z.object` strips unknown
 *     keys), so a seed written into `output` simply is not there afterwards;
 *   - a value outside an enum **throws**, so `'crisis'` cannot be written down
 *     at all.
 *
 * The one thing the schemas cannot check is the backend's cross-field rules,
 * which live in Python validators and are not expressed in OpenAPI. Where a
 * fixture is shaped by those, its provenance is named in a comment.
 */

/**
 * A real block-bootstrap run's output, field by field from its producer.
 *
 * Traced from `backend/app/services/risk_plugins/simulation.py:274-289`: the
 * resampler reports `empirical_resampled` / `not_estimated_joint_resampling`
 * (it estimates neither drift nor covariance — it reorders the reader's own
 * returns), `sampling_method` is forced to `mc`, and `block_length_days` comes
 * back from the engine. This is the panel's default mode, so it is the right
 * baseline.
 */
const BOOTSTRAP_OUTPUT = {
    kind: 'simulation',
    process: 'block_bootstrap',
    regime: 'none',
    sampling_method: 'mc',
    horizon_days: 365,
    path_count: 8192,
    block_length_days: 20,
    drift_estimator: 'empirical_resampled',
    covariance_estimator: 'not_estimated_joint_resampling',
    aggregation_policy: 'current_buy_and_hold',
    costs_included: false,
    cash_flows_included: false,
    inflation_included: false,
    rebalanced: false,
    percentile_bands: [
        {day: 0, p05: 0, p50: 0, p95: 0},
        {day: 365, p05: -0.28, p50: 0.05, p95: 0.41},
    ],
    terminal_mean_return: 0.05,
    terminal_volatility: 0.19,
    probability_of_loss: 0.37,
};

/** The same run under the parametric engine (`simulation.py:283-287`, else branch). */
const PARAMETRIC_OUTPUT = {
    ...BOOTSTRAP_OUTPUT,
    process: 'gbm',
    drift_estimator: 'historical_log_mle',
    covariance_estimator: 'sample_log_returns',
    block_length_days: undefined,
};

/**
 * Metadata with no run disclosure at all.
 *
 * `annualization_factor` is not free: `RiskResultMetadata.validate_context`
 * (`backend/app/schemas/risk.py:543-547`) requires it to equal
 * `n_observations * 365 / calendar_days` to within 1e-12, so 505 · 365 / 730 =
 * 252.5 exactly. `composition_policy` is required because the mode is
 * `current_composition` (same validator), and the simulation analytic supports
 * no other mode.
 *
 * The four simulation disclosure fields are absent here and added per test,
 * because the seed is what several of these tests are about and a baseline
 * that already carried one could not show its absence.
 */
const METADATA_WITHOUT_RUN_DISCLOSURE = {
    analyzed_range: {start: '2024-01-02', end: '2025-12-31'},
    frequency: 'daily',
    n_observations: 505,
    calendar_days: 730,
    annualization_factor: 252.5,
    coverage: 1,
    currency: 'EUR',
    scope: 'portfolio',
    scope_reference: 'portfolio:all',
    composition_as_of: '2025-12-31',
    method: 'block_bootstrap_simulation',
    mode: 'current_composition',
    composition_policy: 'current_buy_and_hold',
    return_basis: 'price_only',
    excluded_assets: [],
    algorithm_version: '3.0.0-bootstrap-quantlib-1.43',
    computed_at: '2026-01-31T12:00:00Z',
};

/**
 * What a bootstrap run discloses about how it was computed.
 *
 * `simulation.py:293-297` hands `sampling_method`, `path_count` and
 * `bootstrap_seed` to `RiskComputation`, and `service.py:855-859` copies them
 * verbatim into the metadata. `random_seed` and `sobol_start_index` are None
 * there because the params validator forbids them for this engine
 * (`simulation.py:152-157`).
 */
const BOOTSTRAP_RUN_DISCLOSURE = {
    sampling_method: 'mc',
    path_count: 8192,
    bootstrap_seed: 424242,
};

/** The parametric Monte Carlo equivalent: same two fields, the other seed. */
const PARAMETRIC_MC_RUN_DISCLOSURE = {
    sampling_method: 'mc',
    path_count: 8192,
    random_seed: 123456,
};

/** Quasi-random: an entry point into a Sobol sequence, and no seed at all. */
const PARAMETRIC_QMC_RUN_DISCLOSURE = {
    sampling_method: 'qmc',
    path_count: 8192,
    sobol_start_index: 0,
};

/**
 * A result assembled and then **validated against the wire contract**.
 *
 * No cast: `schemas.RiskAnalyticResult.parse` returns the generated type, so a
 * fixture that stops matching the API has to fail here rather than three
 * assertions later, or — worse — quietly agree with the code under test.
 */
function contractSimulation(overrides: {output?: Record<string, unknown>; metadata?: Record<string, unknown>} = {}): RiskAnalyticResult {
    return schemas.RiskAnalyticResult.parse({
        instance_id: 'base-simulation',
        analytic_code: 'simulation',
        status: 'ok',
        output: {...BOOTSTRAP_OUTPUT, ...overrides.output},
        metadata: {...METADATA_WITHOUT_RUN_DISCLOSURE, ...BOOTSTRAP_RUN_DISCLOSURE, ...overrides.metadata},
    });
}

/**
 * A payload the contract cannot express, for the branches that guard against one.
 *
 * Reserved for exactly that: `costs_included: 'false'`, a NaN day count, a
 * missing boolean. Those shapes cannot come off this wire — the schema rejects
 * the first two and defaults the third — so a schema-parsed fixture cannot
 * produce them, and the defensive code would otherwise go untested. Every test
 * using this helper is testing robustness against a **non-contract** input, and
 * says so.
 */
function looseSimulation(outputOverrides: Record<string, unknown> = {}): RiskAnalyticResult {
    return {
        analytic_code: 'simulation',
        instance_id: 'base-simulation',
        status: 'ok',
        output: {...BOOTSTRAP_OUTPUT, ...outputOverrides},
        metadata: {...METADATA_WITHOUT_RUN_DISCLOSURE, ...BOOTSTRAP_RUN_DISCLOSURE},
    } as unknown as RiskAnalyticResult;
}

function entryFor(result: RiskAnalyticResult, key: string) {
    return buildSimulationProvenance(result)?.entries.find((entry) => entry.key === key) ?? null;
}

describe('buildSimulationProvenance', () => {
    it('has nothing to describe when the simulation never succeeded', () => {
        expect(buildSimulationProvenance(null)).toBeNull();
        const unavailable = schemas.RiskAnalyticResult.parse({
            instance_id: 'base-simulation',
            analytic_code: 'simulation',
            status: 'unavailable',
            output: null,
            metadata: {...METADATA_WITHOUT_RUN_DISCLOSURE, ...BOOTSTRAP_RUN_DISCLOSURE},
        });
        expect(buildSimulationProvenance(unavailable)).toBeNull();
    });

    it('reports the estimators the reader did not choose and could not guess', () => {
        // `horizon_days` and `path_count` are the two the user typed in. Printing
        // those back as "assumptions" tells the reader only what they already knew.
        expect(entryFor(contractSimulation(), 'driftEstimator')).toEqual({key: 'driftEstimator', value: 'empirical_resampled', number: null});
        expect(entryFor(contractSimulation(), 'covarianceEstimator')).toEqual({key: 'covarianceEstimator', value: 'not_estimated_joint_resampling', number: null});
        expect(entryFor(contractSimulation(), 'process')?.value).toBe('block_bootstrap');
        expect(entryFor(contractSimulation(), 'sampling')?.value).toBe('mc');
        expect(entryFor(contractSimulation(), 'aggregation')?.value).toBe('current_buy_and_hold');
    });

    it('follows the engine when the estimators change with it', () => {
        // The two engines disclose different estimators for the same run, and the
        // pairing is the plugin's (`simulation.py:283-284`), not this module's: a
        // resampler that reported `historical_log_mle` would be claiming an
        // estimate it never made.
        const parametric = contractSimulation({output: PARAMETRIC_OUTPUT});
        expect(entryFor(parametric, 'process')?.value).toBe('gbm');
        expect(entryFor(parametric, 'driftEstimator')?.value).toBe('historical_log_mle');
        expect(entryFor(parametric, 'covarianceEstimator')?.value).toBe('sample_log_returns');
    });

    it('reads the four effects from the payload in both directions', () => {
        const stated = buildSimulationProvenance(contractSimulation());
        expect(stated?.exclusions).toEqual(['costs', 'cashFlows', 'inflation', 'rebalancing']);
        expect(stated?.inclusions).toEqual([]);

        // The hard-coded sentence cannot do this: it says "without rebalancing"
        // in four languages whatever the payload states.
        const rebalanced = buildSimulationProvenance(contractSimulation({output: {rebalanced: true, costs_included: true}}));
        expect(rebalanced?.inclusions).toEqual(['costs', 'rebalancing']);
        expect(rebalanced?.exclusions).toEqual(['cashFlows', 'inflation']);
    });

    it('stays silent about an effect no field mentions, even though the wire always states one', () => {
        // Absent is not false. A cone that never said whether it charges costs
        // has not said that it doesn't, and claiming otherwise would put a
        // sentence on screen that no field backs.
        //
        // Off-contract by construction: `costs_included` and `rebalanced` carry
        // `.default(false)` in the generated schema, so a parsed payload always
        // states them and this branch is unreachable from the server as it
        // stands today. It is kept because "absent" is one schema revision away
        // — the field only has to become optional-without-default — and the
        // failure mode is a confident sentence about an effect nobody declared.
        const silent = buildSimulationProvenance(looseSimulation({costs_included: undefined, rebalanced: undefined}));
        expect(silent?.exclusions).toEqual(['cashFlows', 'inflation']);
        expect(silent?.inclusions).toEqual([]);
    });

    it('refuses a truthy flag that is not a boolean', () => {
        // `'false'` is a string and every string is truthy: read loosely it would
        // flip the statement to its exact opposite.
        //
        // Off-contract by construction: the schema types these as booleans, so
        // this is defence against a payload that is not the one documented.
        const loose = buildSimulationProvenance(looseSimulation({costs_included: 'false', rebalanced: 1}));
        expect(loose?.inclusions).toEqual([]);
        expect(loose?.exclusions).toEqual(['cashFlows', 'inflation']);
    });

    describe('what a resampled run adds to the line', () => {
        it('lists a whole bootstrap run in the order the panel prints it', () => {
            const provenance = buildSimulationProvenance(contractSimulation());
            expect(provenance?.entries.map((entry) => entry.key)).toEqual(['process', 'sampling', 'driftEstimator', 'covarianceEstimator', 'aggregation', 'blockLength', 'seed']);
            expect(provenance?.truncation).toBeNull();
        });

        it('adds nothing for a run that declares no regime, block or seed', () => {
            const bare = contractSimulation({output: PARAMETRIC_OUTPUT, metadata: {...PARAMETRIC_QMC_RUN_DISCLOSURE, bootstrap_seed: undefined}});
            expect(buildSimulationProvenance(bare)?.entries.map((entry) => entry.key)).toEqual(['process', 'sampling', 'driftEstimator', 'covarianceEstimator', 'aggregation']);
        });

        it('carries a regime together with the span it was declared over', () => {
            const entry = entryFor(contractSimulation({output: {regime: 'prolonged_crisis', regime_declared_days: 60}}), 'regime');
            expect(entry).toEqual({key: 'regime', value: 'prolonged_crisis', number: 60});
        });

        it('drops a regime that arrives without its declared span', () => {
            // The server makes this impossible; a fixture is validated by nobody.
            // A regime name with no span is the ambiguity the validator exists to
            // forbid, so it is not rendered as though it were complete.
            expect(entryFor(contractSimulation({output: {regime: 'prolonged_crisis'}}), 'regime')).toBeNull();
            expect(entryFor(contractSimulation({output: {regime: undefined, regime_declared_days: 60}}), 'regime')).toBeNull();
        });

        it('says nothing about a regime an ordinary run never prescribed', () => {
            // `none` is the value every unprescribed run carries, and the plain
            // bootstrap above is one. Its span is null, so no line appears — the
            // reader is not told about a hypothesis nobody made.
            expect(entryFor(contractSimulation(), 'regime')).toBeNull();
        });

        it('notes the truncation when the regime was applied over a different span', () => {
            const provenance = buildSimulationProvenance(contractSimulation({output: {regime: 'prolonged_crisis', regime_declared_days: 250, regime_applied_days: 60}}));
            expect(provenance?.truncation).toEqual({declaredDays: 250, appliedDays: 60});
        });

        it('says nothing when declared and applied agree', () => {
            const provenance = buildSimulationProvenance(contractSimulation({output: {regime: 'prolonged_crisis', regime_declared_days: 60, regime_applied_days: 60}}));
            expect(provenance?.truncation).toBeNull();
        });

        it('reports the block length and the seed that make a run reproducible', () => {
            const provenance = buildSimulationProvenance(contractSimulation({output: {block_length_days: 20}, metadata: {bootstrap_seed: 424242}}));
            expect(provenance?.entries).toContainEqual({key: 'blockLength', value: null, number: 20});
            expect(provenance?.entries).toContainEqual({key: 'seed', value: null, number: 424242});
        });

        it('rejects day counts the contract permits but a reader cannot use', () => {
            // `block_length_days` is a bare `number | null` on the wire: nothing
            // in the schema says whole, nothing says positive, and `Infinity` is
            // a number as far as Zod is concerned. So each of these survives the
            // parse and has to be refused here instead.
            for (const bad of [0, -5, 12.5, Number.POSITIVE_INFINITY]) {
                expect(entryFor(contractSimulation({output: {block_length_days: bad}}), 'blockLength')).toBeNull();
            }
        });

        it('rejects day counts that are not numbers at all', () => {
            // Off-contract by construction: `'20'` and NaN cannot survive
            // `schemas.RiskSimulationOutput`, so they are fed past it.
            for (const bad of ['20', Number.NaN]) {
                expect(entryFor(looseSimulation({block_length_days: bad}), 'blockLength')).toBeNull();
            }
        });
    });

    /**
     * The address of the seed — the defect this file exists to have caught.
     *
     * `simulationSeed` used to read `output.bootstrap_seed`. The field is not
     * there and never was: `RiskResultMetadata` carries it
     * (`backend/app/schemas/risk.py:502`), `RiskSimulationOutput` does not. The
     * bug was invisible because a missing field yields no line rather than a
     * wrong line — nothing rendered, nothing threw, and every "does it render?"
     * assertion stayed green while the seed was silently never shown.
     *
     * These tests ask the contract where the field lives instead of asking the
     * production code, which is the only way a test can answer that question.
     */
    describe('the address of the seed', () => {
        it('cannot be written into the output, whatever a hand-built fixture claims', () => {
            const parsed = schemas.RiskSimulationOutput.parse({...BOOTSTRAP_OUTPUT, bootstrap_seed: 424242, random_seed: 123456});
            expect(parsed).not.toHaveProperty('bootstrap_seed');
            expect(parsed).not.toHaveProperty('random_seed');
        });

        it('yields no seed line when the seed is put at that wrong address', () => {
            const misplaced = contractSimulation({output: {bootstrap_seed: 424242}, metadata: {bootstrap_seed: undefined}});
            expect(entryFor(misplaced, 'seed')).toBeNull();
        });

        it('lives in the metadata, which keeps it', () => {
            const metadata = schemas.RiskResultMetadata.parse({...METADATA_WITHOUT_RUN_DISCLOSURE, ...BOOTSTRAP_RUN_DISCLOSURE});
            expect(metadata.bootstrap_seed).toBe(424242);
            expect(entryFor(contractSimulation(), 'seed')).toEqual({key: 'seed', value: null, number: 424242});
        });

        it('falls back to the parametric seed, because both engines are reproducible', () => {
            // A "Seed" line that appeared for one engine and not the other would
            // suggest the other is not repeatable. It is.
            const parametric = contractSimulation({output: PARAMETRIC_OUTPUT, metadata: {...PARAMETRIC_MC_RUN_DISCLOSURE, bootstrap_seed: undefined}});
            expect(entryFor(parametric, 'seed')).toEqual({key: 'seed', value: null, number: 123456});
        });

        it('does not call a Sobol entry point a seed', () => {
            // `sobol_start_index: 0` is falsy *and* a valid index, so a reader
            // that treated it as a seed would print "Seed: 0" — a quant's knob
            // under a word that means something else.
            const qmc = contractSimulation({output: PARAMETRIC_OUTPUT, metadata: {...PARAMETRIC_QMC_RUN_DISCLOSURE, bootstrap_seed: undefined}});
            expect(schemas.RiskResultMetadata.parse({...METADATA_WITHOUT_RUN_DISCLOSURE, ...PARAMETRIC_QMC_RUN_DISCLOSURE}).sobol_start_index).toBe(0);
            expect(entryFor(qmc, 'seed')).toBeNull();
        });

        it('refuses the regime name the previous fixture invented', () => {
            // `crisis` appeared five times in this file and matched nothing on
            // either side of the wire. The enum is the arbiter, so the fixture
            // that used it cannot even be built now.
            expect(schemas.RiskSimulationRegime.safeParse('crisis').success).toBe(false);
            expect(schemas.RiskSimulationRegime.safeParse('prolonged_crisis').success).toBe(true);
            expect(() => contractSimulation({output: {regime: 'crisis'}})).toThrow();
        });
    });
});
