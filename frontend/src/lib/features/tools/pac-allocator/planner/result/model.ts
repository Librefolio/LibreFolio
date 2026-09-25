/**
 * Read-only projections of a backend result for the screens (C1–C14).
 *
 * Grouping, ordering by `sequence` and bar widths from published weights:
 * presentation only. No amount is added, subtracted or converted here.
 */
import {exactDisplay} from '../format';
import type {PacExactNumber, PacExposureRow, PacFundingAction, PacFxAction, PacLedgerRow, PacNumberAvailability, PacOrderRow, PacPlannerRequest, PacPlannerResult, PacReadyResult, PacRequestAsset, PacRequestFundingRoute, PacRequestOrderRoute} from '../types';

export const UNCATEGORISED_CATEGORY_ID = 'allocation.uncategorised';

export type BadgeTone = 'success' | 'info' | 'warning' | 'danger' | 'neutral';

export interface ResultBadge {
    id: string;
    key: string;
    fallback: string;
    tone: BadgeTone;
}

export function isReady(result: PacPlannerResult): result is PacReadyResult {
    return result.availability === 'ready';
}

/** Four fields, four badges: availability, outcome, proof, stop reason (C1). "Completed" never means optimal. */
export function resultBadges(result: PacReadyResult): ResultBadge[] {
    const badges: ResultBadge[] = [];
    const verified = 'primary_solution' in result && result.primary_solution.validation === 'decimal_verified';
    switch (result.outcome) {
        case 'incumbent_found':
            badges.push({id: 'availability', key: 'tools.pacAllocator.planner.result.badges.planAvailable', fallback: 'Plan available', tone: 'success'});
            break;
        case 'no_op':
            badges.push({id: 'availability', key: 'tools.pacAllocator.planner.result.badges.noOperation', fallback: 'No operation', tone: 'neutral'});
            break;
        case 'infeasible_proven':
            badges.push({id: 'availability', key: 'tools.pacAllocator.planner.result.badges.infeasible', fallback: 'Infeasible with these constraints', tone: 'danger'});
            break;
        case 'no_incumbent':
            badges.push({id: 'availability', key: 'tools.pacAllocator.planner.result.badges.noIncumbent', fallback: 'No plan within the limits', tone: 'warning'});
            break;
    }
    if (verified) badges.push({id: 'validation', key: 'tools.pacAllocator.planner.result.badges.decimalVerified', fallback: 'Verified in Decimal', tone: 'info'});
    switch (result.proof.kind) {
        case 'optimal_proven':
            badges.push({id: 'proof', key: 'tools.pacAllocator.planner.result.badges.optimalProven', fallback: 'Proven optimal', tone: 'success'});
            break;
        case 'gap_bounded':
            badges.push({id: 'proof', key: 'tools.pacAllocator.planner.result.badges.gapBounded', fallback: 'Bounded gap', tone: 'info'});
            break;
        case 'not_proven':
            badges.push({id: 'proof', key: 'tools.pacAllocator.planner.result.badges.notProven', fallback: 'Optimality not proven', tone: 'warning'});
            break;
        case 'infeasibility_proven':
            badges.push({id: 'proof', key: 'tools.pacAllocator.planner.result.badges.infeasibilityProven', fallback: 'Infeasibility proven', tone: 'danger'});
            break;
    }
    badges.push({
        id: 'stop',
        key: `tools.pacAllocator.planner.result.stop.${result.stop_reason}`,
        fallback: result.stop_reason === 'completed' ? 'Completed' : result.stop_reason === 'time_limit' ? 'Time limit' : 'Node limit',
        tone: result.stop_reason === 'completed' ? 'neutral' : 'warning',
    });
    return badges;
}

/** A published weight as a CSS width (0–100%). Display projection of a backend number. */
export function weightWidth(value: PacExactNumber | PacNumberAvailability | null | undefined): string {
    if (!value) return '0%';
    const exact = value.kind === 'available' ? value.value : value.kind === 'unavailable' ? null : value;
    if (!exact) return '0%';
    const fraction = Number(exactDisplay(exact).text);
    if (!Number.isFinite(fraction)) return '0%';
    return `${Math.min(100, Math.max(0, fraction * 100)).toFixed(2)}%`;
}

export function availableNumber(value: PacNumberAvailability): PacExactNumber | null {
    return value.kind === 'available' ? value.value : null;
}

/** Why a published weight is unavailable (`UnavailableExactNumber.reason`). */
export const UNAVAILABLE_FALLBACKS = {
    zero_current_invested: 'not defined: nothing invested before',
    zero_final_invested: 'not defined: nothing invested after',
    not_applicable: 'not applicable',
    dependency_unavailable: 'not available',
} as const;

/** One pair of target/after bars (C2, C4). */
export interface WeightRow {
    id: string;
    label: string;
    target: PacExactNumber;
    final: PacNumberAvailability;
}

// -- catalogue names ----------------------------------------------------------------

export interface ResultNames {
    asset: (id: string) => string;
    ticker: (id: string) => string | null;
    broker: (id: string) => string;
}

export function resultNames(result: PacReadyResult): ResultNames {
    const assets = new Map(result.catalogs.assets.map((row) => [row.asset_id, row]));
    const brokers = new Map(result.catalogs.brokers.map((row) => [row.broker_id, row]));
    return {
        asset: (id) => assets.get(id)?.name ?? id,
        ticker: (id) => assets.get(id)?.ticker ?? null,
        broker: (id) => brokers.get(id)?.name ?? id,
    };
}

// -- the request a result describes ------------------------------------------------

export type PacProvenanceRow = PacReadyResult['provenance'][number];

/** Lookups into the request that produced the result: the result may be older than the draft. */
export interface PlanLookup {
    sourceLabel: (source: PacFundingAction['source']) => string;
    route: (routeId: string) => PacRequestOrderRoute | null;
    fundingRoute: (fundingRouteId: string) => PacRequestFundingRoute | null;
    quote: (assetId: string) => NonNullable<PacRequestAsset['quote']> | null;
    provenance: (id: string) => PacProvenanceRow | null;
}

export function planLookup(result: PacReadyResult, request: PacPlannerRequest, names: ResultNames): PlanLookup {
    const cash = new Map(request.existing_cash.map((row) => [row.cash_id, row]));
    const contributions = new Map(request.contributions.map((row) => [row.contribution_id, row]));
    const routes = new Map(request.order_routes.map((row) => [row.route_id, row]));
    const fundingRoutes = new Map(request.funding_routes.map((row) => [row.funding_route_id, row]));
    const assets = new Map(request.assets.map((row) => [row.asset_id, row]));
    const provenance = new Map(result.provenance.map((row) => [row.provenance_id, row]));
    return {
        sourceLabel: (source) => {
            if (source.kind === 'existing_cash') {
                const row = cash.get(source.cash_id);
                return row ? [names.broker(row.broker_id), row.available.currency].join(' · ') : source.cash_id;
            }
            const row = contributions.get(source.contribution_id);
            return row?.label || source.contribution_id;
        },
        route: (routeId) => routes.get(routeId) ?? null,
        fundingRoute: (fundingRouteId) => fundingRoutes.get(fundingRouteId) ?? null,
        quote: (assetId) => assets.get(assetId)?.quote ?? null,
        provenance: (id) => provenance.get(id) ?? null,
    };
}

/** Hard minimums of the request, listed next to a proven infeasibility (D12): the backend names no culprit. */
export function requiredMinimumRoutes(request: PacPlannerRequest): PacRequestOrderRoute[] {
    return request.order_routes.filter((route) => route.required_minimum.kind !== 'none');
}

// -- operational plan (C10–C12) -------------------------------------------------------

export type PlanStep = {kind: 'funding'; sequence: number; action: PacFundingAction} | {kind: 'fx'; sequence: number; action: PacFxAction};

/** Funding and FX actions in the backend's sequence; orders are listed per Broker. */
export function planSteps(funding: readonly PacFundingAction[], fx: readonly PacFxAction[]): PlanStep[] {
    const steps: PlanStep[] = [...funding.map((action) => ({kind: 'funding' as const, sequence: action.sequence, action})), ...fx.map((action) => ({kind: 'fx' as const, sequence: action.sequence, action}))];
    return steps.sort((a, b) => a.sequence - b.sequence);
}

export function ordersByBroker(orders: readonly PacOrderRow[]): {brokerId: string; orders: PacOrderRow[]}[] {
    const groups = new Map<string, PacOrderRow[]>();
    for (const order of [...orders].sort((a, b) => a.sequence - b.sequence)) {
        if (!groups.has(order.broker_id)) groups.set(order.broker_id, []);
        groups.get(order.broker_id)!.push(order);
    }
    return [...groups].map(([brokerId, rows]) => ({brokerId, orders: rows}));
}

// -- ledger, transposed (one column per Broker × currency) ----------------------------

export const LEDGER_FIELDS = ['initial_selected', 'funding_in', 'funding_out', 'fx_debit', 'fx_credit', 'buy_debit', 'buy_fees', 'rounding_delta', 'final_spendable', 'final_physical'] as const;

/** Always zero in PAC 2.0.0: shown on request only. */
export const LEDGER_ZERO_FIELDS = ['gross_sell_credit', 'sell_fees', 'broker_withheld_tax', 'self_reserved_tax'] as const;

export type LedgerField = (typeof LEDGER_FIELDS)[number] | (typeof LEDGER_ZERO_FIELDS)[number];

export function ledgerColumns(rows: readonly PacLedgerRow[]): PacLedgerRow[] {
    return [...rows].sort((a, b) => (a.broker_id === b.broker_id ? a.currency.localeCompare(b.currency) : a.broker_id.localeCompare(b.broker_id)));
}

// -- exposures (C4) ------------------------------------------------------------------------

export const RESULT_DIMENSIONS = ['asset_type', 'geography', 'sector'] as const;

export interface ExposureGroup {
    dimension: (typeof RESULT_DIMENSIONS)[number];
    rows: PacExposureRow[];
    /** Nothing declared: a single uncategorised row at 100%, folded into one line. */
    onlyUncategorised: boolean;
}

export function exposureGroups(rows: readonly PacExposureRow[]): ExposureGroup[] {
    return RESULT_DIMENSIONS.map((dimension) => {
        const group = rows.filter((row) => row.dimension === dimension);
        return {dimension, rows: group, onlyUncategorised: group.length > 0 && group.every((row) => row.category_id === UNCATEGORISED_CATEGORY_ID)};
    });
}

export function objectiveStage<T extends {objective_code: string}>(stages: readonly T[], code: string): T | null {
    return stages.find((stage) => stage.objective_code === code) ?? null;
}
