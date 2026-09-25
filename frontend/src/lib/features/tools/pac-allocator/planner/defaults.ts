/**
 * Scenario defaults applied by the PAC planner draft (C0 delta §8.2).
 *
 * Every value here is a starting point the user can edit; none is a
 * recommendation, and none is sent without appearing in the draft first.
 */

// TODO(pac-allocator): reduce this ceiling once the execution-time simulations with
// increasing thresholds have measured the supported domain (Q-C0-5, Step 3 point 13).
// A high cap does not widen the search: each order is bounded by min(cap, resources).
export const DEFAULT_ROUTE_CAP = '1000000000';

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

export const PLANNER_TOOL_CODE = 'pac_allocator';
export const PLANNER_CONTRACT_VERSION = '2.0.0';

/** The only value the 2.0.0 wire accepts for `operation`. */
export const PLANNER_OPERATION = 'plan';
