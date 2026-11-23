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
