import {describe, expect, it} from 'vitest';

import {schemas} from '$lib/api';
import {SIMULATION_MODES} from '$lib/components/risk/levels/l4/simulationModes';

import {buildSimulationParameters, type SimulationEditorState} from './riskRequest';

/**
 * The two engines take **disjoint** parameter sets, and the difference is
 * enforced rather than tolerated.
 *
 * `SimulationParams` is `extra="forbid"`, and on top of that
 * `validate_engine_contract` (`backend/app/services/risk_plugins/simulation.py:141-169`)
 * rules:
 *
 *   |                     | block_bootstrap | gbm                       |
 *   |---------------------|-----------------|---------------------------|
 *   | `sampling_method`   | must be `mc`    | `mc` or `qmc`             |
 *   | `regime`            | free            | must be `none`            |
 *   | `bootstrap_seed`    | required        | forbidden                 |
 *   | `block_length_days` | optional        | forbidden                 |
 *   | `random_seed`       | forbidden       | required when `mc`        |
 *   | `sobol_start_index` | forbidden       | required when `qmc`       |
 *
 * None of that is visible to TypeScript. `RiskAnalyticRequest.parameters` is
 * `z.record(JsonValue)` where `JsonValue` is `z.unknown()`, so the generated
 * client checks **nothing** about the keys of an analytic's parameters: the
 * only contract the frontend has here is this test. That is why the assertions
 * below are key-by-key rather than a single schema parse — and why they use
 * `not.toHaveProperty` rather than `toBeUndefined`.
 *
 * The distinction matters. `toEqual` ignores keys whose value is `undefined`,
 * and so does `toBeUndefined` by definition; but `JSON.stringify` drops such a
 * key while an explicit `null` survives, and `extra="forbid"` judges what
 * actually arrives. A key that must not be sent has to be *absent*, and only
 * `not.toHaveProperty` asks that question.
 *
 * The failure mode is worth stating once: an invalid combination does not come
 * back as a 422. `service.py:141-150` catches the per-analytic `ValidationError`
 * and continues, so the response is a 200 with the analytic `unavailable` and
 * the simulation rung silently missing. There is no error for a test to catch
 * downstream — the emission is the only place it can be caught.
 */

const BASE_STATE: SimulationEditorState = {
    process: 'block_bootstrap',
    regime: 'none',
    samplingMethod: 'mc',
    horizonDays: 365,
    pathCount: 8192,
    randomSeed: 123456,
    sobolStartIndex: 0,
};

function state(overrides: Partial<SimulationEditorState> = {}): SimulationEditorState {
    return {...BASE_STATE, ...overrides};
}

/** Every regime that is a *hypothesis*, i.e. everything except the absence of one. */
const PRESCRIBED_REGIMES = schemas.RiskSimulationRegime.options.filter((regime) => regime !== 'none');

describe('buildSimulationParameters — the block bootstrap branch', () => {
    it('emits the resampler set and nothing from the other engine', () => {
        const params = buildSimulationParameters(state({regime: 'prolonged_crisis'}));
        expect(params).toEqual({
            process: 'block_bootstrap',
            regime: 'prolonged_crisis',
            sampling_method: 'mc',
            horizon_days: 365,
            path_count: 8192,
            bootstrap_seed: 123456,
        });
    });

    it('leaves out the two parametric seeds entirely, not merely undefined', () => {
        const params = buildSimulationParameters(state());
        expect(params).not.toHaveProperty('random_seed');
        expect(params).not.toHaveProperty('sobol_start_index');
        // Serialisation is where a present-but-undefined key would betray itself,
        // so the check is repeated against what actually goes on the wire.
        expect(Object.keys(JSON.parse(JSON.stringify(params)))).not.toContain('random_seed');
    });

    it('does not invent a block length the reader never chose', () => {
        // `block_length_days` is optional for this engine and the panel offers no
        // control for it, so the server picks. Sending a client-side default
        // would silently override a choice the engine is better placed to make.
        expect(buildSimulationParameters(state())).not.toHaveProperty('block_length_days');
    });

    it('forces pseudo-random sampling instead of forwarding a quasi-random choice', () => {
        // Resampling draws block starts from a generator; there is no
        // low-discrepancy sequence to walk. The server does not ignore `qmc`
        // here, it refuses the whole run — so forwarding the reader's parametric
        // choice would turn a meaningless option into a missing answer.
        expect(buildSimulationParameters(state({samplingMethod: 'qmc'})).sampling_method).toBe('mc');
    });

    it('carries the seed the reader typed, under the name this engine uses', () => {
        const params = buildSimulationParameters(state({randomSeed: 424242}));
        expect(params.bootstrap_seed).toBe(424242);
    });
});

describe('buildSimulationParameters — the parametric branch', () => {
    it('emits the Monte Carlo set and nothing from the resampler', () => {
        const params = buildSimulationParameters(state({process: 'gbm'}));
        expect(params).toEqual({
            process: 'gbm',
            regime: 'none',
            sampling_method: 'mc',
            horizon_days: 365,
            path_count: 8192,
            random_seed: 123456,
        });
        expect(params).not.toHaveProperty('bootstrap_seed');
        expect(params).not.toHaveProperty('block_length_days');
        expect(params).not.toHaveProperty('sobol_start_index');
    });

    it('swaps the seed for a sequence entry point under quasi-random sampling', () => {
        const params = buildSimulationParameters(state({process: 'gbm', samplingMethod: 'qmc', sobolStartIndex: 11}));
        expect(params.sobol_start_index).toBe(11);
        expect(params).not.toHaveProperty('random_seed');
        expect(params).not.toHaveProperty('bootstrap_seed');
    });

    it('states `regime: none` literally, even handed a state that says otherwise', () => {
        // The deliberate defence, and it deserves its own test because it looks
        // like a bug: the branch does **not** forward `state.regime`. The pairing
        // is guaranteed at the point of emission instead of being checked before
        // it, so an editor state that somehow carried a regime alongside GBM
        // still cannot put that combination on the wire — no matter how it got
        // into that state, or which future control sets it.
        for (const regime of PRESCRIBED_REGIMES) {
            const params = buildSimulationParameters(state({process: 'gbm', regime}));
            expect(params.regime, `a gbm state carrying "${regime}"`).toBe('none');
        }
    });

    it('keeps `regime: none` present rather than omitting it', () => {
        // Absent would also be accepted by the server, which defaults it. Present
        // is better: `_default_process` (`simulation.py:134-138`) infers the
        // engine from whichever fields it finds, so the more the request states
        // outright, the less is inferred on its behalf.
        expect(buildSimulationParameters(state({process: 'gbm'}))).toHaveProperty('regime', 'none');
    });
});

describe('buildSimulationParameters — every mode the panel can offer', () => {
    // Driven from the mode table rather than from five hand-written cases: the
    // rules below are the server's, so they must hold for any row the table ever
    // contains, including ones added after this file was written.
    const samplings = schemas.RiskSamplingStrategy.options;

    for (const mode of SIMULATION_MODES) {
        for (const samplingMethod of samplings) {
            it(`obeys the engine contract for "${mode.id}" under ${samplingMethod}`, () => {
                const params = buildSimulationParameters(state({process: mode.process, regime: mode.regime, samplingMethod}));

                expect(schemas.RiskSimulationProcess.safeParse(params.process).success).toBe(true);
                expect(schemas.RiskSimulationRegime.safeParse(params.regime).success).toBe(true);
                expect(schemas.RiskSamplingStrategy.safeParse(params.sampling_method).success).toBe(true);

                if (params.process === 'block_bootstrap') {
                    expect(params.sampling_method).toBe('mc');
                    expect(params).toHaveProperty('bootstrap_seed');
                    expect(params).not.toHaveProperty('random_seed');
                    expect(params).not.toHaveProperty('sobol_start_index');
                    return;
                }

                expect(params.regime).toBe('none');
                expect(params).not.toHaveProperty('bootstrap_seed');
                expect(params).not.toHaveProperty('block_length_days');
                if (params.sampling_method === 'mc') {
                    expect(params).toHaveProperty('random_seed');
                    expect(params).not.toHaveProperty('sobol_start_index');
                } else {
                    expect(params).toHaveProperty('sobol_start_index');
                    expect(params).not.toHaveProperty('random_seed');
                }
            });
        }
    }

    it('never emits the pair the server would answer with a missing rung', () => {
        for (const mode of SIMULATION_MODES) {
            for (const samplingMethod of samplings) {
                const params = buildSimulationParameters(state({process: mode.process, regime: mode.regime, samplingMethod}));
                expect(params.process === 'gbm' && params.regime !== 'none', `"${mode.id}" under ${samplingMethod}`).toBe(false);
            }
        }
    });

    it('produces a request the generated client will send', () => {
        // Worth stating what this does *not* prove: `parameters` is a
        // `z.record(z.unknown())`, so this parse accepts any keys at all. It
        // checks the envelope — instance id pattern, analytic code — and is the
        // only contract-level check available on the request side. The engine
        // rules above are the real ones, and they exist only here.
        for (const mode of SIMULATION_MODES) {
            const request = schemas.RiskAnalyticRequest.parse({
                instance_id: 'base-simulation',
                analytic_code: 'simulation',
                parameters: buildSimulationParameters(state({process: mode.process, regime: mode.regime})),
            });
            expect(request.parameters).toMatchObject({process: mode.process});
        }
    });
});
