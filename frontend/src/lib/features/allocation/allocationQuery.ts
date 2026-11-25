/**
 * The question of the «Allocazione» tab, in one place (lane 80, F2).
 *
 * The body of `POST /portfolio/allocation` is built from the SAME `PortfolioScope` the page hands to the report
 * (`portfolioDataScope.ts`: its brokers, `historyStart`, `end`, currency and `fullShare`), so the backend reads the report's
 * engine run and a change of a filter replays nothing. A field that differed would make it run the engine again at every
 * click. The scope key (`scopeKey`) is the report's; the filters and the dimension only add to it.
 *
 * Pure: no store, no network.
 *
 * @module features/allocation/allocationQuery
 */
import type {z} from 'zod';
import type {schemas} from '$lib/api';
import {scopeKey, type PortfolioScope} from '$lib/features/portfolio-view/portfolioDataScope';
import {serializeFilters, type AllocationFilters} from './allocationFilters';

export type AllocationQuery = z.infer<typeof schemas.PortfolioAllocationQuery>;
/** The answer as the generated client types it: every field with a default is optional there, and the optional ones are widened. */
export type RawAllocationResponse = z.infer<typeof schemas.PortfolioAllocationResponse>;
export type AllocationDimension = NonNullable<AllocationQuery['dimension']>;

export type AllocationBucket = 'Unknown' | 'Other';

export interface AllocationSlice {
    /** The bucket: a sector, an ISO3 country, an asset type, «Liquidity»; in the asset dimension the asset id as text. */
    key: string;
    asset_id: number | null;
    amount: string;
    share_of_selection: string | null;
    share_of_portfolio: string | null;
    assets: Array<{asset_id: number; amount: string; share_of_slice: string | null}>;
}

export interface AllocationScopeAsset {
    asset_id: number;
    asset_class: string;
    amount: string;
    name: string;
    ticker: string | null;
    asset_type: string | null;
    icon_url: string | null;
}

/**
 * What the tab reads: `POST /portfolio/allocation`'s answer with every list present and every optional scalar a `string | null`,
 * exactly as the backend serialises it (its defaults are always sent). Amounts and shares stay the strings the backend wrote.
 * The matrix and the history join in the lots that draw them (F4, F3).
 */
export interface AllocationResponse {
    currency: string;
    date_from: string | null;
    as_of: string | null;
    dimension: AllocationDimension;
    applicable_buckets: AllocationBucket[];
    portfolio_total: string;
    base: string;
    base_share_of_portfolio: string | null;
    slices: AllocationSlice[];
    outside: {amount: string; by_class: Array<{asset_class: string; amount: string}>};
    excluded: {
        amount: string;
        by_bucket: Array<{key: string; amount: string}>;
        by_asset: Array<{asset_id: number; amount: string}>;
        unattributable: Array<{reason: 'in_transit' | 'no_country'; amount: string}>;
    };
    /** The classes the scope holds, largest first, each with the asset types that make it up (none for the cash). */
    classes: Array<{asset_class: string; amount: string; types: Array<{asset_type: string; amount: string}>}>;
    assets: AllocationScopeAsset[];
    /** The selection's history in steps, when it was asked (`include_history`); `null` otherwise. */
    history: AllocationHistoryStep[] | null;
    /** Class × dimension of the WHOLE portfolio, whatever the filters; `null` in the type and asset dimensions. */
    matrix: AllocationMatrixView | null;
}

export interface AllocationMatrixView {
    /** The classes, largest first. */
    rows: string[];
    /** The buckets of the dimension, largest first. */
    columns: string[];
    cells: Array<{asset_class: string; key: string; amount: string; share_of_portfolio: string | null}>;
    /** What has no column (the cash in the geography, the securities in transit): with the cells, the net worth. */
    unattributed: Array<{reason: 'in_transit' | 'no_country'; amount: string}>;
}

/** A step of the selection's history: the slices hold from `date` to `through` (inclusive); `base` is their sum. */
export interface AllocationHistoryStep {
    date: string;
    through: string;
    base: string;
    /** The slices of the step, as the history chart reads them (`name`, the share in percent or `null`, the amount, the asset id). */
    components: Array<{name: string; value: string | null; amount: string; emoji: string | null; id: number | null}>;
}

/** An optional scalar of the generated type, as the `string | null` it is. */
function text(value: string | null | undefined | Array<string | null>): string | null {
    return typeof value === 'string' ? value : null;
}

type RawHistoryStep = {
    date: string;
    through?: string | null;
    base: string;
    components?: Array<{name: string; value?: string | null | Array<string | null>; amount: string; emoji?: string | null | Array<string | null>; id?: number | null | Array<number | null>}>;
};

function normalizeHistory(steps: RawHistoryStep[]): AllocationHistoryStep[] {
    return steps.map((step) => ({
        date: step.date,
        through: step.through ?? step.date,
        base: step.base,
        components: (step.components ?? []).map((component) => ({name: component.name, value: text(component.value), amount: component.amount, emoji: text(component.emoji), id: typeof component.id === 'number' ? component.id : null})),
    }));
}

type RawMatrix = {rows?: string[]; columns?: string[]; cells?: Array<{asset_class: string; key: string; amount: string; share_of_portfolio?: string | null | Array<string | null>}>; unattributed?: Array<{reason: 'in_transit' | 'no_country'; amount: string}>};

function normalizeMatrix(raw: unknown): AllocationMatrixView | null {
    if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) return null;
    const matrix = raw as RawMatrix;
    return {
        rows: matrix.rows ?? [],
        columns: matrix.columns ?? [],
        cells: (matrix.cells ?? []).map((cell) => ({asset_class: cell.asset_class, key: cell.key, amount: cell.amount, share_of_portfolio: text(cell.share_of_portfolio)})),
        unattributed: matrix.unattributed ?? [],
    };
}

/** Reads the generated answer into the strict one, at the one place the client's widened types are met. */
export function normalizeAllocation(raw: RawAllocationResponse): AllocationResponse {
    return {
        currency: raw.currency,
        date_from: text(raw.date_from),
        as_of: text(raw.as_of),
        dimension: raw.dimension,
        applicable_buckets: raw.applicable_buckets ?? [],
        portfolio_total: raw.portfolio_total,
        base: raw.base,
        base_share_of_portfolio: text(raw.base_share_of_portfolio),
        slices: (raw.slices ?? []).map((slice) => ({
            key: slice.key,
            asset_id: typeof slice.asset_id === 'number' ? slice.asset_id : null,
            amount: slice.amount,
            share_of_selection: text(slice.share_of_selection),
            share_of_portfolio: text(slice.share_of_portfolio),
            assets: (slice.assets ?? []).map((asset) => ({asset_id: asset.asset_id, amount: asset.amount, share_of_slice: text(asset.share_of_slice)})),
        })),
        outside: {amount: raw.outside.amount, by_class: raw.outside.by_class ?? []},
        excluded: {
            amount: raw.excluded.amount,
            by_bucket: raw.excluded.by_bucket ?? [],
            by_asset: raw.excluded.by_asset ?? [],
            unattributable: raw.excluded.unattributable ?? [],
        },
        classes: (raw.classes ?? []).map((row) => ({asset_class: row.asset_class, amount: row.amount, types: row.types ?? []})),
        assets: (raw.assets ?? []).map((asset) => ({asset_id: asset.asset_id, asset_class: asset.asset_class, amount: asset.amount, name: asset.name, ticker: text(asset.ticker), asset_type: text(asset.asset_type), icon_url: text(asset.icon_url)})),
        matrix: normalizeMatrix(raw.matrix),
        history: Array.isArray(raw.history) && raw.history.every((step) => typeof step === 'object' && step !== null && !Array.isArray(step) && 'date' in step) ? normalizeHistory(raw.history as unknown as RawHistoryStep[]) : null,
    };
}

export const DEFAULT_ALLOCATION_DIMENSION: AllocationDimension = 'sector';

export interface AllocationAsk {
    scope: PortfolioScope;
    dimension: AllocationDimension;
    filters: AllocationFilters;
    /** The selection's history in steps (the Storico view); off for the table and the chart of «Ora». */
    includeHistory?: boolean;
}

/**
 * The body. The report's conventions: `broker_ids` only when there are some (a page that must not widen its scope never
 * asks without them: the caller does not ask before the owned brokers are known), the dates only when set, the currency
 * only when known, and `apply_ownership_share: false` only on a page that counts its broker whole.
 */
export function buildAllocationQuery({scope, dimension, filters, includeHistory = false}: AllocationAsk): AllocationQuery {
    const body: AllocationQuery = {dimension};
    if (scope.brokerIds && scope.brokerIds.length > 0) body.broker_ids = [...scope.brokerIds];
    if (scope.start || scope.end) body.date_range = {...(scope.start ? {start: scope.start} : {}), ...(scope.end ? {end: scope.end} : {})};
    if (scope.currency) body.target_currency = scope.currency;
    if (scope.fullShare) body.apply_ownership_share = false;
    if (filters.classes !== null) {
        body.classes = [...filters.classes];
        if (filters.types.length > 0) body.types = [...filters.types];
    }
    if (filters.excludeBuckets.length > 0) body.exclude_buckets = [...filters.excludeBuckets];
    if (filters.excludeAssetIds.length > 0) body.exclude_asset_ids = [...filters.excludeAssetIds];
    if (includeHistory) body.include_history = true;
    return body;
}

/** Two asks are the same question when this is equal: the report's scope key, then what the tab adds. */
export function allocationAskKey(ask: AllocationAsk): string {
    return [scopeKey(ask.scope), ask.dimension, serializeFilters(ask.filters), ask.includeHistory ? 'history' : 'now'].join('|');
}
