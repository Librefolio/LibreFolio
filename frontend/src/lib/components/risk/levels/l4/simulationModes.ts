/**
 * The five simulation modes, and the two contract axes each one stands for.
 *
 * The backend takes two independent-looking fields, `process` and `regime`, but
 * they are **not** free: `simulation.py:158` refuses any prescribed regime that
 * is not carried by the block bootstrap. A UI offering the two as separate
 * dropdowns would let the reader build "GBM + prolonged crisis", a combination
 * the server rejects — and it does not reject it loudly. A params
 * `ValidationError` is caught per-analytic (`service.py:141-150`) and returned
 * as a **200 with the analytic unavailable**, so the invalid choice would show
 * up as the simulation rung silently failing to appear, with no visible cause.
 *
 * So the pair is collapsed into one list. The invalid combination is not
 * validated against here: it is **unrepresentable**, because no entry in the
 * table below produces it.
 *
 * The id doubles as the i18n key under `risk.simulation.mode`. That is
 * deliberate rather than convenient: a separate id→key mapping is a second
 * table that can drift from the first, and a label lookup that misses renders
 * the raw key *in the place where the hypothesis should be* — which is the one
 * line the design says is part of the contract rather than decoration.
 */
import {schemas} from '$lib/api';
import type {z} from 'zod';

export type RiskSimulationProcess = z.infer<typeof schemas.RiskSimulationProcess>;
export type RiskSimulationRegime = z.infer<typeof schemas.RiskSimulationRegime>;

/** A mode id, which is also its label/hypothesis key under `risk.simulation.mode`. */
export type SimulationMode = 'block_bootstrap' | 'calm' | 'prolonged_crisis' | 'shock_recovery' | 'gbm';

export interface SimulationModeSpec {
    id: SimulationMode;
    process: RiskSimulationProcess;
    regime: RiskSimulationRegime;
    /** Suffix under `risk.simulation.mode` for the badge, when the mode carries one. */
    badge: 'recommended' | 'advanced' | null;
}

/**
 * Presentation order, which is also a statement about what to pick.
 *
 * The resampler leads because it is the honest default: it reorders the
 * reader's own returns and adds no assumption. The three prescribed regimes
 * follow, each declaring its transformation. GBM comes last and is marked
 * advanced — it is kept because it is the classic model, not because it is the
 * better one: it assumes regular swings and so understates the tails.
 */
export const SIMULATION_MODES: readonly SimulationModeSpec[] = [
    {id: 'block_bootstrap', process: 'block_bootstrap', regime: 'none', badge: 'recommended'},
    {id: 'calm', process: 'block_bootstrap', regime: 'calm', badge: null},
    {id: 'prolonged_crisis', process: 'block_bootstrap', regime: 'prolonged_crisis', badge: null},
    {id: 'shock_recovery', process: 'block_bootstrap', regime: 'shock_recovery', badge: null},
    {id: 'gbm', process: 'gbm', regime: 'none', badge: 'advanced'},
];

/** The mode the panel opens on: resampled history, no added hypothesis. */
export const DEFAULT_SIMULATION_MODE: SimulationMode = 'block_bootstrap';

export function simulationModeSpec(id: SimulationMode): SimulationModeSpec {
    return SIMULATION_MODES.find((mode) => mode.id === id) ?? SIMULATION_MODES[0];
}
