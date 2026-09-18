/**
 * What the simulation actually assumed — read from the payload, never asserted.
 *
 * The third rung of L4 is the only one that is a *model*, so it is the only one
 * whose result cannot be checked against anything the reader can see. That makes
 * its assumptions part of the answer rather than a footnote to it.
 *
 * Today the panel prints `risk.simulation.assumptions`, which reads:
 *
 *   "{paths} paths over {days} days; current buy-and-hold composition, without
 *    costs, cash flows, inflation or rebalancing."
 *
 * The two numbers are interpolated. Everything after the semicolon is **hard-coded
 * in four translation catalogues**. It is true of today's backend, and nothing
 * keeps it true: the day a run sets `rebalanced` or `costs_included`, the sentence
 * goes on denying it, in every language, with no test to notice. A hard-coded
 * assumption is not a declaration — it is a guess that happens to be right.
 *
 * So this module reads each flag and reports both directions. An effect that is
 * *stated* as included is listed as included; one stated as excluded is listed as
 * excluded; one the payload does not mention is listed **nowhere**, because a
 * cone that never said whether it charges costs has not said that it doesn't.
 */
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

import {finite, okOutput} from './levelHelpers';

/** One provenance line: a label key plus whichever kind of value it carries. */
export interface ProvenanceEntry {
    /** Suffix for the label, resolved by the caller against its own namespace. */
    key: string;
    /** An enum value, rendered through a value catalogue. */
    value: string | null;
    /** A count, rendered as a plain number. */
    number: number | null;
}

/** An effect the model applies, or declines to apply, stated either way. */
export type SimulationEffect = 'costs' | 'cashFlows' | 'inflation' | 'rebalancing';

export interface SimulationProvenance {
    entries: ProvenanceEntry[];
    /** Effects the payload states are **not** in the cone. */
    exclusions: SimulationEffect[];
    /** Effects the payload states **are** in the cone. */
    inclusions: SimulationEffect[];
    /**
     * Set only when the regime was applied for a different span than declared.
     *
     * A regime asked for over 250 days and applied over 60 is not the regime the
     * reader asked for, and the cone is not wrong — it is answering a different
     * question. The note exists so that difference is on screen rather than in a
     * log.
     */
    truncation: {declaredDays: number; appliedDays: number} | null;
}

/** The four effect flags, paired with the field that states each one. */
const EFFECT_FIELDS: ReadonlyArray<readonly [SimulationEffect, string]> = [
    ['costs', 'costs_included'],
    ['cashFlows', 'cash_flows_included'],
    ['inflation', 'inflation_included'],
    ['rebalancing', 'rebalanced'],
];

/** An enum value, or null for anything that is not a non-empty string. */
function enumValue(value: unknown): string | null {
    return typeof value === 'string' && value.length > 0 ? value : null;
}

/** A positive whole number of days, or null. */
function dayCount(value: unknown): number | null {
    const raw = finite(value);
    if (raw === null || !Number.isInteger(raw) || raw <= 0) return null;
    return raw;
}

/**
 * Describe a simulation from its own output.
 *
 * Returns null when there is no successful simulation to describe — the caller
 * then shows nothing, rather than an empty provenance block that would read as
 * "no assumptions".
 */
export function buildSimulationProvenance(simulationResult: RiskAnalyticResult | null): SimulationProvenance | null {
    const output = okOutput(simulationResult);
    if (!output) return null;

    const entries: ProvenanceEntry[] = [];
    const pushEnum = (key: string, field: string) => {
        const value = enumValue(output[field]);
        if (value !== null) entries.push({key, value, number: null});
    };
    const pushDays = (key: string, field: string) => {
        const number = dayCount(output[field]);
        if (number !== null) entries.push({key, value: null, number});
    };

    pushEnum('process', 'process');
    pushEnum('sampling', 'sampling_method');
    pushEnum('driftEstimator', 'drift_estimator');
    pushEnum('covarianceEstimator', 'covariance_estimator');
    pushEnum('aggregation', 'aggregation_policy');

    // K6. A regime without a declared span is impossible server-side, so the
    // declared span is read as part of the regime rather than as an optional
    // extra: reporting the name alone would restore exactly the ambiguity the
    // server-side validator exists to prevent.
    const regime = enumValue(output.regime);
    const declaredDays = dayCount(output.regime_declared_days);
    if (regime !== null && declaredDays !== null) {
        entries.push({key: 'regime', value: regime, number: declaredDays});
    }
    pushDays('blockLength', 'block_length_days');

    const seed = finite(output.bootstrap_seed);
    if (seed !== null && Number.isInteger(seed)) entries.push({key: 'seed', value: null, number: seed});

    const exclusions: SimulationEffect[] = [];
    const inclusions: SimulationEffect[] = [];
    for (const [effect, field] of EFFECT_FIELDS) {
        const stated = output[field];
        if (stated === true) inclusions.push(effect);
        else if (stated === false) exclusions.push(effect);
    }

    const appliedDays = dayCount(output.regime_applied_days);
    const truncation = regime !== null && declaredDays !== null && appliedDays !== null && declaredDays !== appliedDays ? {declaredDays, appliedDays} : null;

    return {entries, exclusions, inclusions, truncation};
}
