/**
 * The «Allocazione» answer read as things to draw (lane 80, F3): the pie's entries, the map's data, the colour ranks of the
 * assets, and the rows of the table (slices, the assets that make a slice up, and what is excluded).
 *
 * It computes nothing financial: every amount and share is the backend's string, read as a number only to be drawn
 * (a share in percent becomes the 0–1 weight the map takes, the same change of unit the Dashboard's allocation panel makes).
 * What the backend did not send is not drawn: an excluded row has no share, and a base at or below zero has no percentages.
 *
 * Pure: no store, no network, no component.
 *
 * @module features/allocation/allocationView
 */
import {assetColorRanks} from '$lib/features/dashboard/positionsSeries';
import type {AllocationDimension, AllocationResponse} from './allocationQuery';

/** Buckets that hold no country on the map. */
const NOT_A_COUNTRY: ReadonlySet<string> = new Set(['Unknown', 'Other', 'Liquidity']);

const num = (value: string | null | undefined): number => {
    const parsed = value == null ? NaN : parseFloat(value);
    return Number.isFinite(parsed) ? parsed : 0;
};

/** The name of an asset by its id, from the assets the answer lists. */
export function assetNamesOf(view: AllocationResponse): Map<number, string> {
    return new Map(view.assets.map((asset) => [asset.asset_id, asset.name]));
}

/** An entry of `AllocationPieChart` (its `AllocationEntry`): the name as the backend keys it, the share in percent, the amount. */
export interface PieEntry {
    name: string;
    value: number;
    amount: number;
    id?: number | null;
    iconUrl?: string | null;
    assetType?: string | null;
}

/** The pie's entries: the slices of the base, `value` the share of the selection (0 when there is none), `amount` the amount. */
export function pieEntries(view: AllocationResponse): PieEntry[] {
    const assets = new Map(view.assets.map((asset) => [asset.asset_id, asset]));
    return view.slices.map((slice) => {
        const asset = slice.asset_id === null ? undefined : assets.get(slice.asset_id);
        return {
            name: view.dimension === 'asset' && asset ? asset.name : slice.key,
            value: num(slice.share_of_selection),
            amount: num(slice.amount),
            id: slice.asset_id,
            iconUrl: asset?.icon_url ?? null,
            assetType: asset?.asset_type ?? null,
        };
    });
}

/** The map's data: ISO3 → weight (0–1) of the selection, and ISO3 → amount. Buckets that are no country are not drawn. */
export function geoData(view: AllocationResponse): {data: Record<string, number>; amounts: Record<string, number>} {
    const data: Record<string, number> = {};
    const amounts: Record<string, number> = {};
    for (const slice of view.slices) {
        if (NOT_A_COUNTRY.has(slice.key)) continue;
        data[slice.key] = num(slice.share_of_selection) / 100;
        if (num(slice.amount) > 0) amounts[slice.key] = num(slice.amount);
    }
    return {data, amounts};
}

/** One colour rank per asset, shared by the pie and the history: the heaviest first, then the ones that left. */
export function colorRanksOf(view: AllocationResponse): Map<number, number> {
    return assetColorRanks(
        view.slices.map((slice) => ({id: slice.asset_id, amount: slice.amount})),
        (view.history ?? []).map((step) => ({date: step.date, through: step.through, components: step.components.map((component) => ({id: component.id, amount: component.amount}))})),
    );
}

export type AllocationRowKind = 'slice' | 'detail' | 'excluded';

export interface AllocationRow {
    /** Unique in the table. */
    id: string;
    kind: AllocationRowKind;
    /** The slice's bucket (a detail row: the slice it belongs to); for an excluded row, its bucket, its asset id or its reason. */
    key: string;
    /** An excluded row says what it is. */
    excluded?: 'bucket' | 'asset' | 'unattributable';
    /** A detail row: the asset. */
    assetId?: number | null;
    amount: number;
    shareOfSelection: string | null;
    shareOfPortfolio: string | null;
    /** A detail row's share of its slice. */
    shareOfSlice?: string | null;
    /** The assets the slice holds; `null` where the dimension lists none (the asset dimension, the cash). */
    assetCount: number | null;
    /** The slice can be opened to show its assets. */
    expandable?: boolean;
    expanded?: boolean;
}

/**
 * The rows of the table, in the order the backend gave the slices (largest first); a slice that is open is followed by the assets
 * that make it up; what is excluded stays at the bottom, with no share (nothing the backend sent is a share of it).
 */
export function tableRows(view: AllocationResponse, expanded: ReadonlySet<string>): AllocationRow[] {
    const rows: AllocationRow[] = [];
    for (const slice of view.slices) {
        const canOpen = slice.assets.length > 0;
        const open = canOpen && expanded.has(slice.key);
        rows.push({
            id: `slice:${slice.key}`,
            kind: 'slice',
            key: slice.key,
            assetId: slice.asset_id,
            amount: num(slice.amount),
            shareOfSelection: slice.share_of_selection,
            shareOfPortfolio: slice.share_of_portfolio,
            assetCount: view.dimension === 'asset' || slice.key === 'Liquidity' ? null : slice.assets.length,
            expandable: canOpen,
            expanded: open,
        });
        if (!open) continue;
        for (const asset of slice.assets) {
            rows.push({id: `detail:${slice.key}:${asset.asset_id}`, kind: 'detail', key: slice.key, assetId: asset.asset_id, amount: num(asset.amount), shareOfSelection: null, shareOfPortfolio: null, shareOfSlice: asset.share_of_slice, assetCount: null});
        }
    }
    for (const bucket of view.excluded.by_bucket) {
        rows.push({id: `excluded:bucket:${bucket.key}`, kind: 'excluded', excluded: 'bucket', key: bucket.key, amount: num(bucket.amount), shareOfSelection: null, shareOfPortfolio: null, assetCount: null});
    }
    for (const asset of view.excluded.by_asset) {
        rows.push({id: `excluded:asset:${asset.asset_id}`, kind: 'excluded', excluded: 'asset', key: String(asset.asset_id), assetId: asset.asset_id, amount: num(asset.amount), shareOfSelection: null, shareOfPortfolio: null, assetCount: null});
    }
    for (const fixed of view.excluded.unattributable) {
        if (num(fixed.amount) === 0) continue;
        rows.push({id: `excluded:fixed:${fixed.reason}`, kind: 'excluded', excluded: 'unattributable', key: fixed.reason, amount: num(fixed.amount), shareOfSelection: null, shareOfPortfolio: null, assetCount: null});
    }
    return rows;
}

/** The dimensions the selector offers, in its order. */
export const ALLOCATION_DIMENSIONS: readonly AllocationDimension[] = ['sector', 'geography', 'type', 'asset'];

// ---------------------------------------------------------------------------
// The matrix
// ---------------------------------------------------------------------------

export interface MatrixCellModel {
    assetClass: string;
    key: string;
    amount: number;
    /** The backend's share of the portfolio; `null` when it sent none (NAV at or below zero). */
    shareOfPortfolio: string | null;
    /** The cell holds something. */
    present: boolean;
    /** 0–1: how heavy the cell is next to the heaviest, only to tint it. */
    intensity: number;
    /** In the selection: the class is on and the column is not taken out of the 100 %. */
    selected: boolean;
}

export interface MatrixModel {
    rows: string[];
    columns: string[];
    /** `cells[row][column]`, in the order of `rows` and `columns`. */
    cells: MatrixCellModel[][];
    unattributed: Array<{reason: 'in_transit' | 'no_country'; amount: number}>;
}

/**
 * The matrix as a grid, with what the filters keep marked. The tint is a drawing of the cell's share next to the heaviest cell
 * (a ratio for the colour, never shown); the shares themselves are the backend's. A cell the backend did not list is empty.
 */
export function matrixModel(view: AllocationResponse, isClassOn: (assetClass: string) => boolean, excludedBuckets: ReadonlySet<string>): MatrixModel | null {
    // Only the exclusions the dimension has count (the backend applies a bucket only where the dimension lists it): a saved «Other» does nothing in Area.
    const matrix = view.matrix;
    if (!matrix) return null;
    const applicable = new Set<string>(view.applicable_buckets);
    const bySlot = new Map(matrix.cells.map((cell) => [`${cell.asset_class}\u0000${cell.key}`, cell]));
    // One unit for the whole tint: the shares when the backend sent any (a tiny cell rounds to «0.00» and must stay the lightest), else the amounts.
    const byShare = matrix.cells.some((cell) => cell.share_of_portfolio != null);
    const weightOf = (cell: {amount: string; share_of_portfolio: string | null}): number => Math.abs(num(byShare ? cell.share_of_portfolio : cell.amount));
    const heaviest = Math.max(0, ...matrix.cells.map(weightOf));
    const cells = matrix.rows.map((assetClass) =>
        matrix.columns.map((key): MatrixCellModel => {
            const cell = bySlot.get(`${assetClass}\u0000${key}`);
            const weight = cell ? weightOf(cell) : 0;
            return {
                assetClass,
                key,
                amount: cell ? num(cell.amount) : 0,
                shareOfPortfolio: cell?.share_of_portfolio ?? null,
                present: !!cell && num(cell.amount) !== 0,
                intensity: heaviest > 0 ? weight / heaviest : 0,
                selected: isClassOn(assetClass) && !(applicable.has(key) && excludedBuckets.has(key)),
            };
        }),
    );
    return {rows: [...matrix.rows], columns: [...matrix.columns], cells, unattributed: matrix.unattributed.map((row) => ({reason: row.reason, amount: num(row.amount)}))};
}
