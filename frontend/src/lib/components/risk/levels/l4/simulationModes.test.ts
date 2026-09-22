import {describe, expect, it} from 'vitest';

import {schemas} from '$lib/api';
import en from '$lib/i18n/en.json';

import {DEFAULT_SIMULATION_MODE, SIMULATION_MODES, simulationModeSpec, type SimulationMode} from './simulationModes';

/**
 * What this table is for, and therefore what these tests have to prove.
 *
 * The backend takes two fields, `process` and `regime`, and they are not
 * independent: `simulation.py:165` refuses any prescribed regime that is not
 * carried by the block bootstrap. It refuses it **quietly** — the params
 * `ValidationError` is caught per-analytic (`service.py:141-150`, which does
 * `continue` rather than raise), so the response is a 200 with the analytic
 * marked `unavailable` and the simulation rung simply never appears.
 *
 * A UI offering two dropdowns could therefore build a combination that makes
 * the panel vanish with no message. The table collapses the pair into one list
 * so that combination is not *validated* against — it is unrepresentable.
 *
 * Every test below is that sentence checked from one side:
 *   - no row can express the invalid pair, whatever rows are added later;
 *   - every value both enums define is still reachable from the list, which is
 *     the guarantee that failed before (the request builder hard-coded `gbm`,
 *     so the resampler existed on the server and nowhere in the UI);
 *   - the id, which doubles as the i18n key, resolves to a real label.
 */

/** The label namespace the id is used as a key into. */
const MODE_LABELS = en.risk.simulation.mode as Record<string, unknown>;

function labelsFor(id: SimulationMode): {label?: unknown; hypothesis?: unknown} {
    const entry = MODE_LABELS[id];
    return entry !== null && typeof entry === 'object' ? (entry as {label?: unknown; hypothesis?: unknown}) : {};
}

describe('SIMULATION_MODES', () => {
    it('cannot express a prescribed regime outside the block bootstrap', () => {
        // Written as a loop rather than five cases on purpose: the guarantee is
        // about the table, not about today's contents, so a sixth row added next
        // year is covered the moment it is written.
        for (const mode of SIMULATION_MODES) {
            if (mode.regime === 'none') continue;
            expect(mode.process, `mode "${mode.id}" prescribes "${mode.regime}" and so must use the block bootstrap`).toBe('block_bootstrap');
        }
    });

    it('states the same thing from the other side: no parametric row carries a regime', () => {
        const parametricWithRegime = SIMULATION_MODES.filter((mode) => mode.process === 'gbm' && mode.regime !== 'none');
        expect(parametricWithRegime).toEqual([]);
    });

    it('uses only values the wire contract defines', () => {
        // The two axes are enums on the server. A typo here would not fail to
        // compile — `RiskSimulationProcess` is a union of string literals, and a
        // future widening of it would let a wrong-but-typed value through — so
        // the generated schema is asked instead.
        for (const mode of SIMULATION_MODES) {
            expect(schemas.RiskSimulationProcess.safeParse(mode.process).success, `process of "${mode.id}"`).toBe(true);
            expect(schemas.RiskSimulationRegime.safeParse(mode.regime).success, `regime of "${mode.id}"`).toBe(true);
        }
    });

    it('leaves no engine or regime unreachable from the UI', () => {
        // This is the regression the workstream exists for. The request builder
        // used to hard-code `process: 'gbm'`, so the block bootstrap was
        // implemented, tested server-side, and impossible to select — a whole
        // engine reachable only by hand-writing a request. An enum value absent
        // from this list is that same defect, in advance.
        expect(new Set(SIMULATION_MODES.map((mode) => mode.process))).toEqual(new Set(schemas.RiskSimulationProcess.options));
        expect(new Set(SIMULATION_MODES.map((mode) => mode.regime))).toEqual(new Set(schemas.RiskSimulationRegime.options));
    });

    it('gives every mode an id of its own', () => {
        // The id is the `{#each}` key, the label key and the argument to
        // `simulationModeSpec`. A duplicate would make two rows the same row in
        // all three roles, and `find` would silently resolve to the first.
        const ids = SIMULATION_MODES.map((mode) => mode.id);
        expect(new Set(ids).size).toBe(ids.length);
    });

    it('recommends exactly one mode', () => {
        const recommended = SIMULATION_MODES.filter((mode) => mode.badge === 'recommended');
        expect(recommended.map((mode) => mode.id)).toEqual(['block_bootstrap']);
    });
});

describe('DEFAULT_SIMULATION_MODE', () => {
    it('opens on the resampler, not on the parametric model', () => {
        // The headline behaviour change. Before this workstream every user
        // simulation was GBM because the request builder said so; if the default
        // quietly returns to `gbm`, the product regresses to the state this test
        // was written to end — and nothing else on screen would say so, because
        // both engines render an identical-looking cone.
        const spec = simulationModeSpec(DEFAULT_SIMULATION_MODE);
        expect(spec.process).toBe('block_bootstrap');
        expect(spec.process).not.toBe('gbm');
    });

    it('opens on a run that adds no hypothesis of its own', () => {
        // Defaulting to a *prescribed* regime would be a different bug with the
        // same shape: the reader would be shown a transformed history without
        // having asked for one.
        expect(simulationModeSpec(DEFAULT_SIMULATION_MODE).regime).toBe('none');
    });

    it('names a mode that is actually in the table', () => {
        expect(SIMULATION_MODES.map((mode) => mode.id)).toContain(DEFAULT_SIMULATION_MODE);
    });
});

describe('simulationModeSpec', () => {
    it('returns each mode under its own id', () => {
        for (const mode of SIMULATION_MODES) {
            expect(simulationModeSpec(mode.id)).toBe(mode);
        }
    });

    it('falls back to the first mode rather than to nothing', () => {
        // The signature forbids it, but the value arrives from component state
        // that may one day be restored from a URL or a saved preference. A
        // fallback keeps the panel rendering; returning undefined would take the
        // whole rung down on a stale bookmark.
        expect(simulationModeSpec('gbm_legacy' as SimulationMode)).toBe(SIMULATION_MODES[0]);
    });
});

describe('the ids are the i18n keys', () => {
    it('resolves a label and a hypothesis for every mode', () => {
        // The module makes the id the label key deliberately: a second id→key
        // table is a second thing that can drift. The cost of that choice is
        // that a missing entry renders the raw key *in the place where the
        // hypothesis belongs* — the one line the design treats as part of the
        // contract rather than decoration.
        for (const mode of SIMULATION_MODES) {
            const labels = labelsFor(mode.id);
            expect(typeof labels.label, `risk.simulation.mode.${mode.id}.label`).toBe('string');
            expect(typeof labels.hypothesis, `risk.simulation.mode.${mode.id}.hypothesis`).toBe('string');
        }
    });

    it('resolves every badge it can show', () => {
        for (const badge of new Set(SIMULATION_MODES.map((mode) => mode.badge))) {
            if (badge === null) continue;
            expect(typeof MODE_LABELS[badge], `risk.simulation.mode.${badge}`).toBe('string');
        }
    });
});
