/**
 * Asset labeling helpers for the AI export — enforces "name first" everywhere.
 *
 * Rule: assets are always referred to by their display `name` (never by ticker,
 * ISIN, or any other identifier) in prose, table headers, event references, or
 * as dictionary/lookup keys. Identifiers are exported only as an auxiliary
 * `identifiers` block so the receiving AI can perform accurate web research.
 */

import {buildIdentifiersList} from '$lib/utils/assetTypes';

/**
 * Builds the auxiliary identifiers block for an asset (ISIN/Ticker/CUSIP/SEDOL/
 * FIGI/... — whichever are non-empty), reusing the same generic, enum-driven
 * logic already used by the Asset Detail metadata panel. Accepts any asset-like
 * record with `identifier_*` fields (assetStore's AssetInfo, or the Zod-derived
 * AssetDetail — both use the same field names). Returns undefined when no
 * identifier is available so it's stripped from the export cleanly.
 */
export function buildAssetIdentifiers<T extends object>(assetInfo: T | undefined | null): Record<string, string> | undefined {
    if (!assetInfo) return undefined;
    const pairs = buildIdentifiersList(assetInfo as unknown as Record<string, unknown>);
    if (pairs.length === 0) return undefined;
    return Object.fromEntries(pairs);
}

/**
 * Appends a short, non-identifier disambiguator to an asset name — used only
 * when two *different* assets (different ids) happen to share the exact same
 * display name. Positions of the SAME asset across multiple brokers are NOT a
 * collision (identical name is correct there) and must not be disambiguated.
 *
 * Never falls back to ticker/ISIN: uses asset type/currency/broker instead.
 */
export function disambiguateAssetName(name: string, parts: {assetType?: string | null; currency?: string | null; broker?: string | null}): string {
    const extra = [parts.assetType, parts.currency, parts.broker].filter((v): v is string => !!v).join(' · ');
    return extra ? `${name} (${extra})` : name;
}

/**
 * Given all holdings about to be exported, returns the set of asset ids whose
 * display name collides with at least one other, different, asset id.
 */
export function findCollidingAssetIds(holdings: {asset_id: number; asset_name: string}[]): Set<number> {
    const nameToIds = new Map<string, Set<number>>();
    for (const h of holdings) {
        if (!nameToIds.has(h.asset_name)) nameToIds.set(h.asset_name, new Set());
        nameToIds.get(h.asset_name)!.add(h.asset_id);
    }

    const colliding = new Set<number>();
    for (const ids of nameToIds.values()) {
        if (ids.size > 1) {
            for (const id of ids) colliding.add(id);
        }
    }
    return colliding;
}
