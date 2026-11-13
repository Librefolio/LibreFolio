/**
 * The planner's profile (F1 of project 67): what differs between the Tools that share this planner.
 *
 * The PAC and the Rebalancer run the same wizard and the same result views. What changes between them is data, read
 * from here instead of being written as a literal: the Tool's code and contract version, the prefix of the test ids
 * (also of the tables' `storageKey`, saved in the user's browser, and of the DOM ids), the prefix of a run's
 * correlation id, the names of the run's events, the wizard's steps, and which variant of a text that differs between
 * the two Tools is shown (`text`).
 *
 * **The PAC is the default profile.** A component reads the profile once, at birth, from the Svelte context its Tool's
 * wrapper sets (`setPlannerProfile`); with no wrapper — a component mounted alone in a Vitest, a function called
 * outside any component — it gets the PAC. So the PAC stays identical, in the DOM and on screen, wherever the profile
 * is not given.
 *
 * The i18n keys do not live here: the texts both Tools share stay under `tools.pacAllocator.planner` (plan §3 n. 1(a)),
 * and a text that differs is chosen in its own file between two whole literal keys, on `profile.text` (§3 n. 2(a)).
 */
import {getContext, setContext} from 'svelte';
import {PLANNER_CONTRACT_VERSION, PLANNER_TOOL_CODE} from './defaults';
import {PLANNER_STEPS, type PlannerContractVersion, type PlannerStep, type PlannerToolCode} from './types';

export type {PlannerToolCode} from './types';

export interface PlannerProfile {
    readonly toolCode: PlannerToolCode;
    readonly contractVersion: PlannerContractVersion;
    /** The head of every test id, table `storageKey` and DOM id of the planner: `pac-planner` for the PAC. */
    readonly testIdPrefix: string;
    /** The head of a run's correlation id: `pac-rev` for the PAC (`pac-rev-<revision>-<sequence>`). */
    readonly correlationPrefix: string;
    /** The names of the events a run publishes: states and counts only, never an amount. */
    readonly events: {readonly completed: string; readonly failed: string};
    /** The wizard's steps, in screen order. */
    readonly steps: readonly PlannerStep[];
    /** Which variant of a text that differs between the Tools a file shows. */
    readonly text: 'pac' | 'rebalancer';
}

export const PAC_PLANNER_PROFILE: PlannerProfile = Object.freeze({
    toolCode: PLANNER_TOOL_CODE,
    contractVersion: PLANNER_CONTRACT_VERSION,
    testIdPrefix: 'pac-planner',
    correlationPrefix: 'pac-rev',
    events: Object.freeze({completed: 'tool.pac-plan.completed', failed: 'tool.pac-plan.failed'}),
    steps: Object.freeze([...PLANNER_STEPS]),
    text: 'pac',
});

const PROFILE_KEY = Symbol('planner-profile');

/** Called by a Tool's wrapper, while it is being created: every planner component below it reads this profile. */
export function setPlannerProfile(profile: PlannerProfile): void {
    setContext(PROFILE_KEY, profile);
}

/**
 * The profile of the Tool this component belongs to, read once while the component is being created; the PAC profile
 * when no wrapper set one, or when called outside a component (where Svelte has no context to read).
 */
export function getPlannerProfile(): PlannerProfile {
    try {
        return getContext<PlannerProfile | undefined>(PROFILE_KEY) ?? PAC_PLANNER_PROFILE;
    } catch {
        return PAC_PLANNER_PROFILE;
    }
}

function prefixed(suffix: string, profile: PlannerProfile): string {
    return `${profile.testIdPrefix}-${suffix}`;
}

/** A test id of the planner: `testId('continue')` is `pac-planner-continue` for the PAC. */
export function testId(suffix: string, profile: PlannerProfile = PAC_PLANNER_PROFILE): string {
    return prefixed(suffix, profile);
}

/** A table's `storageKey`: the user's saved column choices, kept apart per Tool. */
export function storageKey(suffix: string, profile: PlannerProfile = PAC_PLANNER_PROFILE): string {
    return prefixed(suffix, profile);
}

/** A DOM id the planner points at (`aria-labelledby`, focus). */
export function domId(suffix: string, profile: PlannerProfile = PAC_PLANNER_PROFILE): string {
    return prefixed(suffix, profile);
}

/**
 * The phases an operation of the Tool reports, in order, as its served descriptor declares them (V3 of project 67): the
 * waiting panel shows the current one by its position in this list. Empty for an operation that reports none.
 */
export function declaredPhases(descriptor: {readonly operations: readonly {readonly operation: string; readonly progress_phases?: readonly string[]}[]}, operation: string): readonly string[] {
    return descriptor.operations.find((policy) => policy.operation === operation)?.progress_phases ?? [];
}
