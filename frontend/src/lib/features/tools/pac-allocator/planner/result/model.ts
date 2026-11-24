/**
 * Read-only projections of a backend result for the screens (C1–C14).
 *
 * Grouping, ordering by `sequence` and bar widths from published weights:
 * presentation only. No amount is added, subtracted or converted here.
 */
import {canonicalDecimal, compareDecimal, decimalSign} from '$lib/utils/core/exactDecimal';
import {exactDisplay, formatPlannerMoneyPlain, type CurrencyDigits} from '../format';
import type {
    PlannerConversion,
    PlannerExactNumber,
    PlannerExposureRow,
    PlannerFundingAction,
    PlannerLedgerRow,
    PlannerNumberAvailability,
    PlannerOrderRow,
    PlannerResult,
    PlannerReadyResult,
    PlannerResolvedAsset,
    PlannerResolvedFundingRoute,
    PlannerResolvedOrderRoute,
    PlannerResolvedRequest,
    RebalancerAssetRow,
    RebalancerCashRow,
    RebalancerTransfer,
    RebalancerUninvestedRow,
} from '../types';

export const UNCATEGORISED_CATEGORY_ID = 'allocation.uncategorised';

export type BadgeTone = 'success' | 'info' | 'warning' | 'danger' | 'neutral';

/** R11.4: the explanation a badge opens on hover or focus; `extra`, a line after it (lot MG: what the margin is). */
export interface BadgeHelp {
    key: string;
    fallback: string;
    values?: Record<string, string>;
    extra?: BadgeHelp;
}

export interface ResultBadge {
    id: string;
    key: string;
    fallback: string;
    tone: BadgeTone;
    help: BadgeHelp;
    /** The badge's own values (lot MG: the margin, formatted as personal money). */
    values?: Record<string, string>;
}

const NO_INCUMBENT_HELP: BadgeHelp = {key: 'tools.pacAllocator.planner.result.states.noIncumbent.body', fallback: 'The solver found no plan before the limit. This is not a proof that no plan exists.'};
/**
 * Lot SEEDS of project 67: a not-proven plan whose reason says why, before how the run ended. The Rebalancer plans three
 * times: a run that proved its plan by itself, with no second run confirming it; and a plan of the wide model (lot ZB),
 * found counting the rounding in its favour. Provisional EN texts, the developer's to word.
 */
const NOT_PROVEN_REASON_HELP: Record<string, BadgeHelp> = {
    'allocation.proof_not_confirmed': {
        key: 'tools.pacAllocator.planner.result.proof.notConfirmed',
        fallback: 'One search ended on this plan, but no second search confirmed it: it is the best plan found, not a proven one.',
    },
    'allocation.limits_leave_no_rounding_room': {
        key: 'tools.pacAllocator.planner.result.proof.limitsLeaveNoRoundingRoom',
        fallback: 'The limits leave no room for rounding, so the plan was found counting the rounding in its favour. It respects the limits once any top-up shown is added, but it is not proven to be the best.',
    },
};
/** The Rebalancer's proven optimum: its objective, the tie-breaks apart (F4a of project 67, step 7). */
const REBALANCER_OPTIMAL_PROVEN =
    "The solver proved that no plan has a better score (with «Target first»: a smaller distance from the targets, then less money lost), and the exact check of the plan matches its numbers. The tie-breaks after it may have stopped earlier: they only choose among plans just as good. The proof holds within the solver's small calculation margin, which grows with the amounts.";

/** Lot MG of project 67: what the margin of a «local optimum» is. «Should»: the bound is the solver's, not a proof. */
const MARGIN_HELP = "The best possible plan should be at most {margin} better than this one: the solver's own bounds say so, and they are not a proof.";

/** Lot ZB of project 67: a search that ended, with no limit, without a plan the exact check accepts. */
export const NO_PLAN_COMPLETED = 'The search ended without a plan that can be carried out within these limits. This is not a proof that no plan exists.';
const NO_INCUMBENT_COMPLETED_HELP: BadgeHelp = {key: 'tools.pacAllocator.planner.result.states.noIncumbent.completedBody', fallback: NO_PLAN_COMPLETED};
const STOP_HELP: Record<PlannerReadyResult['stop_reason'], BadgeHelp> = {
    completed: {key: 'tools.pacAllocator.planner.result.badges.help.completed', fallback: 'The solver ended its search by itself, without reaching a limit.'},
    time_limit: {key: 'tools.pacAllocator.planner.result.badges.help.timeLimit', fallback: 'The solver reached its time limit before ending the search.'},
    node_limit: {key: 'tools.pacAllocator.planner.result.badges.help.nodeLimit', fallback: 'The solver reached its node limit, the number of attempts it may make, before ending the search.'},
};

export function isReady(result: PlannerResult): result is PlannerReadyResult {
    return result.availability === 'ready';
}

/**
 * Four fields, four badges: availability, outcome, proof, stop reason (C1). "Completed" never means optimal. `text` is the
 * Tool's (F4a of project 67, step 7): the Rebalancer's proof names its objective, not the Strategy's order.
 */
export function resultBadges(result: PlannerReadyResult, text: 'pac' | 'rebalancer' = 'pac', digits?: CurrencyDigits): ResultBadge[] {
    const badges: ResultBadge[] = [];
    const verified = 'primary_solution' in result && result.primary_solution.validation === 'decimal_verified';
    switch (result.outcome) {
        case 'incumbent_found':
            badges.push({
                id: 'availability',
                key: 'tools.pacAllocator.planner.result.badges.planAvailable',
                fallback: 'Plan available',
                tone: 'success',
                help: {key: 'tools.pacAllocator.planner.result.badges.help.planAvailable', fallback: 'A plan that respects every constraint: the sections below detail it.'},
            });
            break;
        case 'no_op':
            badges.push({
                id: 'availability',
                key: 'tools.pacAllocator.planner.result.badges.noOperation',
                fallback: 'No operation',
                tone: 'neutral',
                help: {key: 'tools.pacAllocator.planner.result.states.noOp.empty', fallback: 'No order, no FX, no funding.'},
            });
            break;
        case 'infeasible_proven':
            badges.push({
                id: 'availability',
                key: 'tools.pacAllocator.planner.result.badges.infeasible',
                fallback: 'Infeasible with these constraints',
                tone: 'danger',
                help: {key: 'tools.pacAllocator.planner.result.states.infeasible.body', fallback: 'Proven: no combination meets every hard constraint together.'},
            });
            break;
        case 'no_incumbent':
            badges.push({id: 'availability', key: 'tools.pacAllocator.planner.result.badges.noIncumbent', fallback: 'No plan within the limits', tone: 'warning', help: NO_INCUMBENT_HELP});
            break;
    }
    if (verified)
        badges.push({
            id: 'validation',
            key: 'tools.pacAllocator.planner.result.badges.decimalVerified',
            fallback: 'Verified in Decimal',
            tone: 'info',
            help: {
                key: 'tools.pacAllocator.planner.result.badges.help.decimalVerified',
                fallback: 'The backend checked the plan again in exact decimal arithmetic, apart from the solver: every constraint holds and the values of the objectives are exact.',
            },
        });
    switch (result.proof.kind) {
        case 'optimal_proven':
            badges.push({
                id: 'proof',
                key: 'tools.pacAllocator.planner.result.badges.optimalProven',
                fallback: 'Proven optimal',
                tone: 'success',
                help:
                    text === 'rebalancer'
                        ? {
                              key: 'tools.portfolioRebalancer.planner.result.badges.help.optimalProven',
                              fallback: REBALANCER_OPTIMAL_PROVEN,
                          }
                        : {
                              key: 'tools.pacAllocator.planner.result.badges.help.optimalProven',
                              fallback: "The solver proved that no better plan exists, objective by objective in the order chosen in Strategy, and the exact check of the plan matches its numbers. The proof holds within the solver's small calculation margin, which grows with the amounts.",
                          },
            });
            break;
        case 'not_proven': {
            // Lot MG: «local optimum», with the margin the backend published when two runs bound it; personal money.
            const published = result.outcome === 'no_incumbent' ? null : ((result.proof as {margin?: {amount: string; currency: string} | null}).margin ?? null);
            const margin = published ? {margin: formatPlannerMoneyPlain(published.amount, published.currency, {digits})} : undefined;
            badges.push({
                id: 'proof',
                // A result with no plan is not a «local optimum»: it keeps the plain «optimality not proven».
                key: result.outcome === 'no_incumbent' ? 'tools.pacAllocator.planner.result.badges.noPlanNotProven' : margin ? 'tools.pacAllocator.planner.result.badges.notProvenWithin' : 'tools.pacAllocator.planner.result.badges.notProven',
                fallback: result.outcome === 'no_incumbent' ? 'Optimality not proven' : margin ? 'Local optimum (within {margin})' : 'Local optimum',
                tone: 'warning',
                ...(margin ? {values: margin} : {}),
                // With no plan, «the best plan found» would be false: the badge says what the state says.
                // A completed search that is still not proven means the final exact check contradicted the solver's bounds.
                help:
                    result.outcome === 'no_incumbent'
                        ? result.stop_reason === 'completed'
                            ? NO_INCUMBENT_COMPLETED_HELP
                            : NO_INCUMBENT_HELP
                        : result.proof.reason_code in NOT_PROVEN_REASON_HELP
                          ? NOT_PROVEN_REASON_HELP[result.proof.reason_code]
                          : result.stop_reason === 'completed'
                            ? {
                                  key: 'tools.pacAllocator.planner.result.proof.floatingFinished',
                                  fallback: 'The solver finished its search, but its own numbers do not match the exact check of this plan, so the proof does not hold. The plan respects every constraint: it is the best plan found, but it is not proven to be the best.',
                              }
                            : {key: 'tools.pacAllocator.planner.result.proof.floatingUnfinished', fallback: 'The solver stopped before closing every stage: this is the best plan found, not a proven one.'},
            });
            if (margin) {
                const badge = badges[badges.length - 1];
                badge.help = {...badge.help, extra: {key: 'tools.pacAllocator.planner.result.badges.help.margin', fallback: MARGIN_HELP, values: margin}};
            }
            break;
        }
        case 'infeasibility_proven':
            badges.push({
                id: 'proof',
                key: 'tools.pacAllocator.planner.result.badges.infeasibilityProven',
                fallback: 'Infeasibility proven',
                tone: 'danger',
                help: {key: 'tools.pacAllocator.planner.result.proof.solverInfeasibleWitness', fallback: 'The solver closed the first stage as infeasible: no plan meets every hard constraint.'},
            });
            break;
    }
    badges.push({
        id: 'stop',
        key: `tools.pacAllocator.planner.result.stop.${result.stop_reason}`,
        fallback: result.stop_reason === 'completed' ? 'Completed' : result.stop_reason === 'time_limit' ? 'Time limit' : 'Node limit',
        tone: result.stop_reason === 'completed' ? 'neutral' : 'warning',
        help: STOP_HELP[result.stop_reason],
    });
    return badges;
}

/** A published weight as a float fraction, for drawing only (bars, maps). Never summed or compared. */
export function weightFraction(value: PlannerExactNumber | PlannerNumberAvailability | null | undefined): number | null {
    if (!value) return null;
    const exact = value.kind === 'available' ? value.value : value.kind === 'unavailable' ? null : value;
    if (!exact) return null;
    const fraction = Number(exactDisplay(exact).text);
    return Number.isFinite(fraction) ? fraction : null;
}

/** A published weight as a CSS width (0–100%), relative to `scale` (the widest bar of the chart). */
export function weightWidth(value: PlannerExactNumber | PlannerNumberAvailability | null | undefined, scale = 1): string {
    const fraction = weightFraction(value);
    if (fraction === null || !(scale > 0)) return '0%';
    return `${Math.min(100, Math.max(0, (fraction / scale) * 100)).toFixed(2)}%`;
}

/** The widest published weight, so that a chart fills its width. 1 when nothing is drawable. */
export function weightScale(values: readonly (PlannerExactNumber | PlannerNumberAvailability | null | undefined)[]): number {
    const widest = Math.max(0, ...values.map((value) => weightFraction(value) ?? 0));
    return widest > 0 ? widest : 1;
}

/** The sign of an exact backend number, read without rounding: to hide a line that would say 0. */
export function exactSign(value: PlannerExactNumber): -1 | 0 | 1 | null {
    if (value.kind === 'finite_decimal') return decimalSign(value.value);
    try {
        const sign = BigInt(value.numerator) * BigInt(value.denominator);
        return sign === 0n ? 0 : sign < 0n ? -1 : 1;
    } catch {
        return null;
    }
}

/** An exact backend number as an integer ratio with a positive denominator; null when unreadable. */
function exactRatio(value: PlannerExactNumber): {numerator: bigint; denominator: bigint} | null {
    try {
        if (value.kind === 'finite_decimal') {
            const canonical = canonicalDecimal(value.value);
            if (canonical === null) return null;
            const [integer, fraction = ''] = canonical.split('.');
            return {numerator: BigInt(integer + fraction), denominator: 10n ** BigInt(fraction.length)};
        }
        const numerator = BigInt(value.numerator);
        const denominator = BigInt(value.denominator);
        if (denominator === 0n) return null;
        return denominator < 0n ? {numerator: -numerator, denominator: -denominator} : {numerator, denominator};
    } catch {
        return null;
    }
}

/** Two exact backend numbers compared without rounding (the ▲/▼/= of an exposure): no subtraction. */
export function compareExact(left: PlannerExactNumber, right: PlannerExactNumber): -1 | 0 | 1 | null {
    if (left.kind === 'finite_decimal' && right.kind === 'finite_decimal') return compareDecimal(left.value, right.value);
    const a = exactRatio(left);
    const b = exactRatio(right);
    if (!a || !b) return null;
    const x = a.numerator * b.denominator;
    const y = b.numerator * a.denominator;
    return x === y ? 0 : x < y ? -1 : 1;
}

export function availableNumber(value: PlannerNumberAvailability): PlannerExactNumber | null {
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
    target: PlannerExactNumber;
    final: PlannerNumberAvailability;
}

/** A geography row for the maps: `code` is the country code the world map is keyed by (ISO alpha-3). */
export interface MapWeightRow extends WeightRow {
    code: string;
}

/** A published weight in percent units, for a chart only (colour, bar length). Never shown as a number. */
export function chartPercent(value: PlannerExactNumber | PlannerNumberAvailability | null | undefined): number | null {
    const fraction = weightFraction(value);
    return fraction === null ? null : fraction * 100;
}

// -- catalogue names ----------------------------------------------------------------

export interface ResultNames {
    asset: (id: string) => string;
    ticker: (id: string) => string | null;
    broker: (id: string) => string;
}

export function resultNames(result: PlannerReadyResult): ResultNames {
    const assets = new Map(result.catalogs.assets.map((row) => [row.asset_id, row]));
    const brokers = new Map(result.catalogs.brokers.map((row) => [row.broker_id, row]));
    return {
        asset: (id) => assets.get(id)?.name ?? id,
        ticker: (id) => assets.get(id)?.ticker ?? null,
        broker: (id) => brokers.get(id)?.name ?? id,
    };
}

// -- the request a result describes ------------------------------------------------

export type PlannerProvenanceRow = PlannerReadyResult['provenance'][number];

/** A funding source, resolved for display: a Broker's cash in one currency, or a new contribution. */
export type PlanSource = {kind: 'cash'; brokerId: string | null; currency: string | null; label: string} | {kind: 'contribution'; label: string; currency: string | null};

/** Lookups into the request that produced the result: the result may be older than the draft. */
export interface PlanLookup {
    sourceLabel: (source: PlannerFundingAction['source']) => string;
    source: (source: PlannerFundingAction['source']) => PlanSource;
    route: (routeId: string) => PlannerResolvedOrderRoute | null;
    fundingRoute: (fundingRouteId: string) => PlannerResolvedFundingRoute | null;
    /** How many funding routes of the request reach one Broker in one currency: a priority matters only above one. */
    fundingChoices: (brokerId: string, currency: string) => number;
    quote: (assetId: string) => NonNullable<PlannerResolvedAsset['quote']> | null;
    provenance: (id: string) => PlannerProvenanceRow | null;
}

export function planLookup(result: PlannerReadyResult, request: PlannerResolvedRequest, names: ResultNames): PlanLookup {
    const cash = new Map(request.existing_cash.map((row) => [row.cash_id, row]));
    const contributions = new Map(request.contributions.map((row) => [row.contribution_id, row]));
    const routes = new Map(request.order_routes.map((row) => [row.route_id, row]));
    // The Rebalancer's request carries no funding route (contract §5.4): it has deposits and transfers instead.
    const fundingRoutes = new Map((request.funding_routes ?? []).map((row) => [row.funding_route_id, row]));
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
        source: (source) => {
            if (source.kind === 'existing_cash') {
                const row = cash.get(source.cash_id);
                return row ? {kind: 'cash', brokerId: row.broker_id, currency: row.available.currency, label: names.broker(row.broker_id)} : {kind: 'cash', brokerId: null, currency: null, label: source.cash_id};
            }
            const row = contributions.get(source.contribution_id);
            return {kind: 'contribution', label: row?.label || source.contribution_id, currency: row?.amount.currency ?? null};
        },
        route: (routeId) => routes.get(routeId) ?? null,
        fundingRoute: (fundingRouteId) => fundingRoutes.get(fundingRouteId) ?? null,
        // Defensive: called only once a funding route is found, which the Rebalancer never has.
        fundingChoices: (brokerId, currency) => (request.funding_routes ?? []).filter((row) => row.broker_id === brokerId && row.currency === currency).length,
        quote: (assetId) => assets.get(assetId)?.quote ?? null,
        provenance: (id) => provenance.get(id) ?? null,
    };
}

// -- limits (F2 of project 67, M20) ------------------------------------------------------

type PlannerResolvedTargetEntry = PlannerResolvedRequest['target_weights'][number];
export type PlannerResolvedLimit = NonNullable<PlannerResolvedTargetEntry['minimum']>;

/** A target entry with at least one limit: an Asset (`id` = its id) or a Broker's cash in one currency (`id` = `broker:currency`). */
export interface LimitedEntry {
    kind: 'asset' | 'cash';
    id: string;
    brokerId: string | null;
    currency: string | null;
    minimum: PlannerResolvedLimit | null;
    maximum: PlannerResolvedLimit | null;
}

/** The entries of the request that carry a limit, in wire order: what the «no solution with these limits» banner lists. */
export function limitedEntries(request: PlannerResolvedRequest): LimitedEntry[] {
    return request.target_weights.flatMap((entry): LimitedEntry[] => {
        const minimum = entry.minimum ?? null;
        const maximum = entry.maximum ?? null;
        if (minimum === null && maximum === null) return [];
        return entry.kind === 'asset' ? [{kind: 'asset', id: entry.asset_id, brokerId: null, currency: null, minimum, maximum}] : [{kind: 'cash', id: `${entry.broker_id}:${entry.currency}`, brokerId: entry.broker_id, currency: entry.currency, minimum, maximum}];
    });
}

/**
 * The result's notes to list beside the state notice. With `ready_infeasible` and a limit in the request the banner lists every
 * limited entry, so the backend's per-entry `allocation.bounds_unsatisfiable` notes would say it twice: they are left out.
 */
export function notesBesideLimitsBanner(result: PlannerReadyResult, limits: readonly LimitedEntry[]): PlannerReadyResult['issues'] {
    if (result.result_state !== 'ready_infeasible' || limits.length === 0) return result.issues;
    return result.issues.filter((issue) => issue.code !== 'allocation.bounds_unsatisfiable');
}

// -- operational plan (C10–C12) -------------------------------------------------------

export type PlanStep = {kind: 'funding'; sequence: number; action: PlannerFundingAction} | {kind: 'conversion'; sequence: number; action: PlannerConversion} | {kind: 'transfer'; sequence: number; action: RebalancerTransfer};

/**
 * R4.9: funding, the conversions the user makes and (the Rebalancer, F4a of project 67) the transfers between Brokers, in
 * the backend's counter (contract §6.3): the steps follow `sequence` and nothing else, the frontend has no rule about
 * which kind goes first. Orders are listed per Broker.
 */
export function planSteps(funding: readonly PlannerFundingAction[], conversions: readonly PlannerConversion[], transfers: readonly RebalancerTransfer[] = []): PlanStep[] {
    const manual = conversions.flatMap((action) => (action.mode === 'manual' && action.sequence !== null ? [{kind: 'conversion' as const, sequence: action.sequence, action}] : []));
    const steps: PlanStep[] = [...funding.map((action) => ({kind: 'funding' as const, sequence: action.sequence, action})), ...manual, ...transfers.map((action) => ({kind: 'transfer' as const, sequence: action.sequence, action}))];
    return steps.sort((a, b) => a.sequence - b.sequence);
}

/** The lists a plan is made of; `transfers` only in the Rebalancer's. */
export interface PlanLists {
    funding_actions: readonly unknown[];
    conversions: readonly unknown[];
    order_rows: readonly unknown[];
    transfers?: readonly unknown[];
}

/** Whether a solution has anything to do: a plan of transfers only, or of conversions only, is still a plan (contract §6.3). */
export function hasPlanSteps(solution: PlanLists): boolean {
    return solution.order_rows.length + solution.funding_actions.length + solution.conversions.length + (solution.transfers?.length ?? 0) > 0;
}

/** The transfers of a solution: the Rebalancer's, none in the PAC's. */
export function planTransfers(solution: object): readonly RebalancerTransfer[] {
    return 'transfers' in solution ? (solution.transfers as readonly RebalancerTransfer[]) : [];
}

/** R4.9: the conversions a Broker makes by itself when the orders are placed; they carry no step number. */
export function automaticConversions(conversions: readonly PlannerConversion[], brokerId: string): PlannerConversion[] {
    return conversions.filter((action) => action.mode === 'automatic' && action.broker_id === brokerId);
}

/** R4.9: the conversions crediting the cash an order pays from; several source currencies can credit the same one. */
export function conversionsFor(conversions: readonly PlannerConversion[], order: PlannerOrderRow): PlannerConversion[] {
    return conversions.filter((action) => action.broker_id === order.broker_id && action.destination_credit.currency === order.cash_debit.currency);
}

export function ordersByBroker(orders: readonly PlannerOrderRow[]): {brokerId: string; orders: PlannerOrderRow[]}[] {
    const groups = new Map<string, PlannerOrderRow[]>();
    for (const order of [...orders].sort((a, b) => a.sequence - b.sequence)) {
        if (!groups.has(order.broker_id)) groups.set(order.broker_id, []);
        groups.get(order.broker_id)!.push(order);
    }
    return [...groups].map(([brokerId, rows]) => ({brokerId, orders: rows}));
}

// -- allocation: before, target and after (F4a of project 67, contract §6.2) ----------------

/** One of the two parts of the uninvested row (TL-5 of project 67): before and after, value and weight, no target. */
export type RebalancerUninvestedPart = RebalancerUninvestedRow['untargeted_cash'];

/** The two parts of the uninvested row, in the order the table shows them: the cash with no target, then the costs. */
export const UNINVESTED_PARTS = ['untargeted_cash', 'costs'] as const;
export type UninvestedPartKind = (typeof UNINVESTED_PARTS)[number];

/** One row of the allocation: an Asset, a cash entry with a target (the Rebalancer's), or a part of the uninvested row. */
export type AllocationRow<A extends {asset_id: string} = RebalancerAssetRow> = {kind: 'asset'; id: string; row: A} | {kind: 'cash'; id: string; row: RebalancerCashRow} | {kind: UninvestedPartKind; id: UninvestedPartKind; row: RebalancerUninvestedPart};

/** Whether a row is a part of the uninvested row: no target, no gap, no limits. */
export function isUninvestedPart(entry: AllocationRow<{asset_id: string}>): entry is Extract<AllocationRow<{asset_id: string}>, {kind: UninvestedPartKind}> {
    return (UNINVESTED_PARTS as readonly string[]).includes(entry.kind);
}

/**
 * The allocation's rows, as published: every Asset, then every cash entry, then the two parts of the uninvested row
 * (contract §6.2; TL-5 of project 67, the developer's answer of 24/11: «Cassa senza obiettivo» and «Costi e commissioni»,
 * the same words as everywhere). The PAC's solution has its Assets only. Nothing is computed: each row is the backend's.
 */
export function allocationRows<A extends {asset_id: string}>(solution: {asset_rows: readonly A[]; cash_rows?: readonly RebalancerCashRow[]; uninvested_row?: RebalancerUninvestedRow}): AllocationRow<A>[] {
    const uninvested = solution.uninvested_row;
    return [
        ...solution.asset_rows.map((row): AllocationRow<A> => ({kind: 'asset', id: row.asset_id, row})),
        ...(solution.cash_rows ?? []).map((row): AllocationRow<A> => ({kind: 'cash', id: `cash:${row.broker_id}:${row.currency}`, row})),
        ...(uninvested ? UNINVESTED_PARTS.map((kind): AllocationRow<A> => ({kind, id: kind, row: uninvested[kind]})) : []),
    ];
}

// -- ledger, transposed (one column per Broker × currency) ----------------------------

/** The PAC's balance columns, in the order of the ledger identity (`schemas/pac_allocator/rows.py`, `PlannerLedgerRow`). */
export const LEDGER_FIELDS = ['initial_selected', 'funding_in', 'funding_out', 'fx_debit', 'fx_credit', 'gross_sell_credit', 'buy_debit', 'buy_fees', 'sell_fees', 'broker_withheld_tax', 'self_reserved_tax', 'rounding_delta', 'final_spendable', 'final_physical'] as const;

/**
 * The Rebalancer's: the PAC's and its transfers between Brokers, after the funding (F4a of project 67, step 5; contract
 * §6.5). A PAC never posts a transfer, so its table keeps its fourteen columns.
 */
export const REBALANCER_LEDGER_FIELDS = [
    'initial_selected',
    'funding_in',
    'funding_out',
    'transfer_in',
    'transfer_out',
    'fx_debit',
    'fx_credit',
    'gross_sell_credit',
    'buy_debit',
    'buy_fees',
    'sell_fees',
    'broker_withheld_tax',
    'self_reserved_tax',
    'rounding_delta',
    'final_spendable',
    'final_physical',
] as const;

export type LedgerField = (typeof REBALANCER_LEDGER_FIELDS)[number];

/** The balance columns of a Tool's table. */
export function ledgerFieldList(text: 'pac' | 'rebalancer'): readonly LedgerField[] {
    return text === 'rebalancer' ? REBALANCER_LEDGER_FIELDS : LEDGER_FIELDS;
}

/** Always 0 in a PAC, which only buys and sets no tax aside. */
export const LEDGER_PAC_ZERO_FIELDS: ReadonlySet<LedgerField> = new Set(['gross_sell_credit', 'sell_fees', 'broker_withheld_tax', 'self_reserved_tax']);

const LEDGER_KEY = 'tools.pacAllocator.planner.result.ledger';
const REBALANCER_LEDGER_KEY = 'tools.portfolioRebalancer.planner.result.ledger';

/** The column's name: the transfers are the Rebalancer's own, every other name is shared. */
export function ledgerLabelKey(field: LedgerField): string {
    return field === 'transfer_in' || field === 'transfer_out' ? `${REBALANCER_LEDGER_KEY}.fields.${field}` : `${LEDGER_KEY}.fields.${field}`;
}

/**
 * The column's help. The PAC's sale and tax columns are «always 0 in a PAC». The Rebalancer's funding is its deposits (it
 * declares no funding route, so nothing goes out as funding: money moves between Brokers as transfers), and with «Invest
 * only», the one strategy until C1, its sale and tax columns are 0 too. Every other help is shared.
 */
export function ledgerHelpKey(field: LedgerField, text: 'pac' | 'rebalancer'): string {
    if (text === 'pac') return LEDGER_PAC_ZERO_FIELDS.has(field) ? `${LEDGER_KEY}.help.alwaysZero` : `${LEDGER_KEY}.help.${field}`;
    if (LEDGER_PAC_ZERO_FIELDS.has(field)) return `${REBALANCER_LEDGER_KEY}.help.alwaysZeroInvestOnly`;
    if (field === 'funding_in' || field === 'funding_out' || field === 'transfer_in' || field === 'transfer_out') return `${REBALANCER_LEDGER_KEY}.help.${field}`;
    return `${LEDGER_KEY}.help.${field}`;
}

/** Always shown: where each cash starts and where it ends. */
const LEDGER_ANCHORS: ReadonlySet<LedgerField> = new Set(['initial_selected', 'final_spendable']);

/** A column says something when it is not 0 on some row; the physical balance, when it differs from the spendable one. */
function ledgerFieldSpeaks(rows: readonly PlannerLedgerRow[], field: LedgerField): boolean {
    if (field === 'final_physical') return rows.some((row) => compareDecimal(row.final_physical, row.final_spendable) !== 0);
    if (field === 'rounding_delta') return rows.some((row) => exactSign(row.rounding_delta) !== 0);
    return rows.some((row) => decimalSign(row[field]) !== 0);
}

/**
 * The help on the «Status» of the solver's stages. The Rebalancer's names one more reason a stage is unfinished: a
 * tie-break whose plan was set aside because it was no better, in exact arithmetic, on the objectives above (D4 of
 * project 67). The PAC's cascade has no such stage.
 */
export function proofStatusHelpKey(text: 'pac' | 'rebalancer'): string {
    return text === 'rebalancer' ? 'tools.portfolioRebalancer.planner.result.proof.help.status' : 'tools.pacAllocator.planner.result.proof.help.status';
}

/** R9.8: the balance columns to show, of a Tool's `fields` (the PAC's by default); `all` brings back the silent ones. */
export function ledgerFields(rows: readonly PlannerLedgerRow[], all: boolean, fields: readonly LedgerField[] = LEDGER_FIELDS): LedgerField[] {
    return fields.filter((field) => all || LEDGER_ANCHORS.has(field) || ledgerFieldSpeaks(rows, field));
}

export function ledgerColumns(rows: readonly PlannerLedgerRow[]): PlannerLedgerRow[] {
    return [...rows].sort((a, b) => (a.broker_id === b.broker_id ? a.currency.localeCompare(b.currency) : a.broker_id.localeCompare(b.broker_id)));
}

// -- exposures (C4) ------------------------------------------------------------------------

export const RESULT_DIMENSIONS = ['asset_type', 'geography', 'sector'] as const;

export interface ExposureGroup {
    dimension: (typeof RESULT_DIMENSIONS)[number];
    rows: PlannerExposureRow[];
    /** Nothing declared: a single uncategorised row at 100%, folded into one line. */
    onlyUncategorised: boolean;
}

export function exposureGroups(rows: readonly PlannerExposureRow[]): ExposureGroup[] {
    return RESULT_DIMENSIONS.map((dimension) => {
        const group = rows.filter((row) => row.dimension === dimension);
        return {dimension, rows: group, onlyUncategorised: group.length > 0 && group.every((row) => row.category_id === UNCATEGORISED_CATEGORY_ID)};
    });
}

export function objectiveStage<T extends {objective_code: string}>(stages: readonly T[], code: string): T | null {
    return stages.find((stage) => stage.objective_code === code) ?? null;
}
