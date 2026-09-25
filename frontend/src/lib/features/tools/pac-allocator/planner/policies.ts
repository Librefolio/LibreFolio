/**
 * Strategies offered by Step 8 (Q-C0-4): read from the compiled contract,
 * never a hand-written list. The objective order of each strategy is the
 * backend cascade (objectives.py `build_objective_cascade`), shown before the
 * calculation; the result publishes the stages that were actually used.
 */
import type {z} from 'zod';
import {toolContractMap} from '$lib/api/tool-contract-map.generated';
import {PLANNER_CONTRACT_VERSION, PLANNER_TOOL_CODE} from './defaults';

export function contractPolicies(): string[] {
    const field = toolContractMap[PLANNER_TOOL_CODE][PLANNER_CONTRACT_VERSION].input.shape.policy as z.ZodTypeAny;
    const def = field._def as {typeName?: string; value?: unknown; values?: unknown};
    if (def.typeName === 'ZodLiteral' && typeof def.value === 'string') return [def.value];
    if (def.typeName === 'ZodEnum' && Array.isArray(def.values)) return def.values.filter((value): value is string => typeof value === 'string');
    return [];
}

export function defaultPolicy(): string {
    const policies = contractPolicies();
    return policies.length === 1 ? policies[0] : '';
}

/** W12: `proportional` = fixed_l2 → shortfall → route_priority → explicit_cost → active_order_rows. */
export const POLICY_OBJECTIVES: Readonly<Record<string, readonly string[]>> = {
    proportional: ['fixed_l2', 'shortfall', 'route_priority', 'explicit_cost', 'active_order_rows'],
};

export const OBJECTIVE_FALLBACKS: Readonly<Record<string, string>> = {
    fixed_l2: 'L2 distance from the fixed targets',
    shortfall: 'Uninvested liquidity (U)',
    turnover: 'Turnover',
    explicit_cost: 'Explicit costs (fees, spread, margin)',
    incremental_cost: 'Incremental costs',
    split_asset_count: 'Assets split across Brokers',
    active_order_rows: 'Number of orders',
    incremental_order_rows: 'Additional orders',
    route_priority: 'Route priority',
};
