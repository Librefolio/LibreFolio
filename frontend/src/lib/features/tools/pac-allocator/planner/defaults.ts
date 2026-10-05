/**
 * Scenario defaults applied by the PAC planner draft (C0 delta §8.2).
 *
 * Every value here is a starting point the user can edit; none is a
 * recommendation, and none is sent without appearing in the draft first.
 */

/** Lower is preferred (N13); negative priorities are rejected by the backend. */
export const DEFAULT_ROUTE_PRIORITY = '0';
export const DEFAULT_FUNDING_PRIORITY = '0';

export const DEFAULT_EXECUTION_MARGIN_PERCENT = '0';
export const DEFAULT_FX_SPREAD_PERCENT = '0';

export const DEFAULT_QUANTITY_STEP = '1';

export const DEFAULT_FEE = {
    fixed: '0',
    ratePercent: '0',
    floor: '0',
    cap: '',
} as const;

/** Today in the local calendar, clamped to the UTC date: `as_of` may not pass the snapshot date (N26). */
export function defaultAsOf(now: Date = new Date()): string {
    const local = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
    const utc = now.toISOString().slice(0, 10);
    return local < utc ? local : utc;
}

export const PLANNER_TOOL_CODE = 'pac_allocator';
export const PLANNER_CONTRACT_VERSION = '1.0.0';

/** The only value the 1.0.0 wire accepts for `operation`. */
export const PLANNER_OPERATION = 'plan';
