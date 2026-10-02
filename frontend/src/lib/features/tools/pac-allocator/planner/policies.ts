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

/** The L2 tip (`strategy.l2Formula`): in Strategy, behind the «?», and on the L2 badge of the Result (R11.4). */
export const L2_FORMULA_FALLBACK =
    'Distance from the targets:\n$D = \\min \\sum_i (V_i - p_i R)^2$\n• $V_i$: value of the Asset after the plan\n• $p_i$: its target\n• $R$: already invested plus usable cash\nThe plan with the lowest sum wins: the square makes big gaps weigh more. At the quote price, without fees or margin.';

export const OBJECTIVE_FALLBACKS: Readonly<Record<string, string>> = {
    fixed_l2: 'Closeness to the targets (L2 distance)',
    shortfall: 'Uninvested money',
    turnover: 'Turnover',
    explicit_cost: 'Explicit costs (fees, spread, margin)',
    incremental_cost: 'Incremental costs',
    split_asset_count: 'Assets split across Brokers',
    active_order_rows: 'Number of orders',
    incremental_order_rows: 'Additional orders',
    route_priority: 'Broker and source priority',
};

/** The one-line explanation of each objective (`objectiveHelp.<code>`), in Strategy. */
export const OBJECTIVE_HELP_FALLBACKS: Readonly<Record<string, string>> = {
    fixed_l2: 'Each Asset as close as possible to its share of the money.',
    shortfall: 'Less money left uninvested.',
    route_priority: 'First the Brokers and the cash sources with the lowest priority number.',
    explicit_cost: 'Less spent on fees, conversion spread and price margin.',
    active_order_rows: 'Fewer orders to place.',
};

export interface ObjectiveTip {
    key: string;
    fallback: string;
    /** The tip holds inline LaTeX; `spoken` says the same in words for the accessible name. */
    math?: boolean;
    spoken?: {key: string; fallback: string};
}

/** The longer explanation behind a «?», only where the short line cannot say it all: in Strategy and on the objective cards of the Proof (R11.10). */
export const OBJECTIVE_TIPS: Readonly<Record<string, ObjectiveTip>> = {
    fixed_l2: {
        key: 'tools.pacAllocator.planner.strategy.l2Formula',
        fallback: L2_FORMULA_FALLBACK,
        math: true,
        spoken: {
            key: 'tools.pacAllocator.planner.strategy.l2Help',
            fallback:
                'Distance from the targets: for each Asset, the difference between its value after the plan and its target share of R, squared, then summed over the Assets. R is what is already invested in these Assets plus the cash you can use. The plan with the lowest sum wins; squaring makes big gaps weigh more. Values at the quote price, without fees or margin.',
        },
    },
    route_priority: {
        key: 'tools.pacAllocator.planner.strategy.priorityHelp',
        fallback: 'You choose the numbers in the Routing step, for the Assets that more than one Broker can buy, and in the Brokers step, for the cash sources: the lowest wins. All at 0 = no preference.',
    },
};
