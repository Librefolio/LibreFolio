/**
 * Read-only projections of a backend result for the screens (C1–C14).
 *
 * Grouping, ordering by `sequence` and bar widths from published weights:
 * presentation only. No amount is added, subtracted or converted here.
 */
import {canonicalDecimal, compareDecimal, decimalSign} from '../decimal';
import {exactDisplay} from '../format';
import type {PacConversion, PacExactNumber, PacExposureRow, PacFundingAction, PacLedgerRow, PacNumberAvailability, PacOrderRow, PacPlannerRequest, PacPlannerResult, PacReadyResult, PacRequestAsset, PacRequestFundingRoute, PacRequestOrderRoute} from '../types';

export const UNCATEGORISED_CATEGORY_ID = 'allocation.uncategorised';

export type BadgeTone = 'success' | 'info' | 'warning' | 'danger' | 'neutral';

/** R11.4: the explanation a badge opens on hover or focus. */
export interface BadgeHelp {
    key: string;
    fallback: string;
}

export interface ResultBadge {
    id: string;
    key: string;
    fallback: string;
    tone: BadgeTone;
    help: BadgeHelp;
}

const NO_INCUMBENT_HELP: BadgeHelp = {key: 'tools.pacAllocator.planner.result.states.noIncumbent.body', fallback: 'The solver found no plan before the limit. This is not a proof that no plan exists.'};
const STOP_HELP: Record<PacReadyResult['stop_reason'], BadgeHelp> = {
    completed: {key: 'tools.pacAllocator.planner.result.badges.help.completed', fallback: 'The solver ended its search by itself, without reaching a limit.'},
    time_limit: {key: 'tools.pacAllocator.planner.result.badges.help.timeLimit', fallback: 'The solver reached its time limit before ending the search.'},
    node_limit: {key: 'tools.pacAllocator.planner.result.badges.help.nodeLimit', fallback: 'The solver reached its node limit, the number of attempts it may make, before ending the search.'},
};

export function isReady(result: PacPlannerResult): result is PacReadyResult {
    return result.availability === 'ready';
}

/** Four fields, four badges: availability, outcome, proof, stop reason (C1). "Completed" never means optimal. */
export function resultBadges(result: PacReadyResult): ResultBadge[] {
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
                help: {key: 'tools.pacAllocator.planner.result.badges.help.optimalProven', fallback: 'The solver proved that no better plan exists, objective by objective, in the order chosen in Strategy.'},
            });
            break;
        case 'not_proven':
            badges.push({
                id: 'proof',
                key: 'tools.pacAllocator.planner.result.badges.notProven',
                fallback: 'Optimality not proven',
                tone: 'warning',
                // With no plan, «the best plan found» would be false: the badge says what the state says.
                help:
                    result.outcome === 'no_incumbent'
                        ? NO_INCUMBENT_HELP
                        : {key: 'tools.pacAllocator.planner.result.proof.floatingUnfinished', fallback: 'The solver stopped before closing every stage: this is the best plan found, not a proven one.'},
            });
            break;
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
export function weightFraction(value: PacExactNumber | PacNumberAvailability | null | undefined): number | null {
    if (!value) return null;
    const exact = value.kind === 'available' ? value.value : value.kind === 'unavailable' ? null : value;
    if (!exact) return null;
    const fraction = Number(exactDisplay(exact).text);
    return Number.isFinite(fraction) ? fraction : null;
}

/** A published weight as a CSS width (0–100%), relative to `scale` (the widest bar of the chart). */
export function weightWidth(value: PacExactNumber | PacNumberAvailability | null | undefined, scale = 1): string {
    const fraction = weightFraction(value);
    if (fraction === null || !(scale > 0)) return '0%';
    return `${Math.min(100, Math.max(0, (fraction / scale) * 100)).toFixed(2)}%`;
}

/** The widest published weight, so that a chart fills its width. 1 when nothing is drawable. */
export function weightScale(values: readonly (PacExactNumber | PacNumberAvailability | null | undefined)[]): number {
    const widest = Math.max(0, ...values.map((value) => weightFraction(value) ?? 0));
    return widest > 0 ? widest : 1;
}

/** The sign of an exact backend number, read without rounding: to hide a line that would say 0. */
export function exactSign(value: PacExactNumber): -1 | 0 | 1 | null {
    if (value.kind === 'finite_decimal') return decimalSign(value.value);
    try {
        const sign = BigInt(value.numerator) * BigInt(value.denominator);
        return sign === 0n ? 0 : sign < 0n ? -1 : 1;
    } catch {
        return null;
    }
}

/** An exact backend number as an integer ratio with a positive denominator; null when unreadable. */
function exactRatio(value: PacExactNumber): {numerator: bigint; denominator: bigint} | null {
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
export function compareExact(left: PacExactNumber, right: PacExactNumber): -1 | 0 | 1 | null {
    if (left.kind === 'finite_decimal' && right.kind === 'finite_decimal') return compareDecimal(left.value, right.value);
    const a = exactRatio(left);
    const b = exactRatio(right);
    if (!a || !b) return null;
    const x = a.numerator * b.denominator;
    const y = b.numerator * a.denominator;
    return x === y ? 0 : x < y ? -1 : 1;
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

/** A geography row for the maps: `code` is the country code the world map is keyed by (ISO alpha-3). */
export interface MapWeightRow extends WeightRow {
    code: string;
}

/** A published weight in percent units, for a chart only (colour, bar length). Never shown as a number. */
export function chartPercent(value: PacExactNumber | PacNumberAvailability | null | undefined): number | null {
    const fraction = weightFraction(value);
    return fraction === null ? null : fraction * 100;
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

/** A funding source, resolved for display: a Broker's cash in one currency, or a new contribution. */
export type PlanSource = {kind: 'cash'; brokerId: string | null; currency: string | null; label: string} | {kind: 'contribution'; label: string; currency: string | null};

/** Lookups into the request that produced the result: the result may be older than the draft. */
export interface PlanLookup {
    sourceLabel: (source: PacFundingAction['source']) => string;
    source: (source: PacFundingAction['source']) => PlanSource;
    route: (routeId: string) => PacRequestOrderRoute | null;
    fundingRoute: (fundingRouteId: string) => PacRequestFundingRoute | null;
    /** How many funding routes of the request reach one Broker in one currency: a priority matters only above one. */
    fundingChoices: (brokerId: string, currency: string) => number;
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
        fundingChoices: (brokerId, currency) => request.funding_routes.filter((row) => row.broker_id === brokerId && row.currency === currency).length,
        quote: (assetId) => assets.get(assetId)?.quote ?? null,
        provenance: (id) => provenance.get(id) ?? null,
    };
}

/** Hard minimums of the request, listed next to a proven infeasibility (D12): the backend names no culprit. */
export function requiredMinimumRoutes(request: PacPlannerRequest): PacRequestOrderRoute[] {
    return request.order_routes.filter((route) => route.required_minimum.kind !== 'none');
}

// -- operational plan (C10–C12) -------------------------------------------------------

export type PlanStep = {kind: 'funding'; sequence: number; action: PacFundingAction} | {kind: 'conversion'; sequence: number; action: PacConversion};

/** R4.9: funding and the conversions the user makes, in the backend's sequence; orders are listed per Broker. */
export function planSteps(funding: readonly PacFundingAction[], conversions: readonly PacConversion[]): PlanStep[] {
    const manual = conversions.flatMap((action) => (action.mode === 'manual' && action.sequence !== null ? [{kind: 'conversion' as const, sequence: action.sequence, action}] : []));
    const steps: PlanStep[] = [...funding.map((action) => ({kind: 'funding' as const, sequence: action.sequence, action})), ...manual];
    return steps.sort((a, b) => a.sequence - b.sequence);
}

/** R4.9: the conversions a Broker makes by itself when the orders are placed; they carry no step number. */
export function automaticConversions(conversions: readonly PacConversion[], brokerId: string): PacConversion[] {
    return conversions.filter((action) => action.mode === 'automatic' && action.broker_id === brokerId);
}

/** R4.9: the conversions crediting the cash an order pays from; several source currencies can credit the same one. */
export function conversionsFor(conversions: readonly PacConversion[], order: PacOrderRow): PacConversion[] {
    return conversions.filter((action) => action.broker_id === order.broker_id && action.destination_credit.currency === order.cash_debit.currency);
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

/** Every balance column, in the order of the ledger identity (`schemas/pac_allocator.py`, `PlannerLedgerRow`). */
export const LEDGER_FIELDS = ['initial_selected', 'funding_in', 'funding_out', 'fx_debit', 'fx_credit', 'gross_sell_credit', 'buy_debit', 'buy_fees', 'sell_fees', 'broker_withheld_tax', 'self_reserved_tax', 'rounding_delta', 'final_spendable', 'final_physical'] as const;

export type LedgerField = (typeof LEDGER_FIELDS)[number];

/** Always 0 in a PAC, which only buys and sets no tax aside. */
export const LEDGER_PAC_ZERO_FIELDS: ReadonlySet<LedgerField> = new Set(['gross_sell_credit', 'sell_fees', 'broker_withheld_tax', 'self_reserved_tax']);

/** Always shown: where each cash starts and where it ends. */
const LEDGER_ANCHORS: ReadonlySet<LedgerField> = new Set(['initial_selected', 'final_spendable']);

/** A column says something when it is not 0 on some row; the physical balance, when it differs from the spendable one. */
function ledgerFieldSpeaks(rows: readonly PacLedgerRow[], field: LedgerField): boolean {
    if (field === 'final_physical') return rows.some((row) => compareDecimal(row.final_physical, row.final_spendable) !== 0);
    return rows.some((row) => decimalSign(row[field]) !== 0);
}

/** R9.8: the balance columns to show; `all` brings back the silent ones. */
export function ledgerFields(rows: readonly PacLedgerRow[], all: boolean): LedgerField[] {
    return LEDGER_FIELDS.filter((field) => all || LEDGER_ANCHORS.has(field) || ledgerFieldSpeaks(rows, field));
}

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
