/**
 * Asset Store — Session-level cache for asset info.
 *
 * Provides a unified, reactive cache for `{id, display_name, currency, asset_type,
 * icon_url, provider_code, active, identifier_*}` so any component can resolve an
 * asset by id without firing its own request.
 *
 * Loads the FULL set of accessible assets via `GET /assets/query` (no filter),
 * matching the existing pattern used by `/assets/+page.svelte` and `LiveTicker`.
 * The endpoint does not currently accept an `ids` filter, so by-ids batch fetch
 * is not possible — full-load is the established convention. If the per-user
 * asset count grows enough that this is too heavy, switch to lazy by-ids after
 * a backend extension.
 *
 * Cross-client edits are NOT proactively synced (no WS/SSE). Mitigations:
 * - `merge(items)`: opportunistic ingress called wherever fresh asset data
 *   naturally flows through the FE (e.g. AssetModal save response,
 *   `/assets` page reload). This keeps the cache consistent without polling.
 * - `invalidateAfterMutation(ids)`: centralized eviction called from every
 *   mutation callsite (AssetModal save/delete/wipe). Forces re-fetch on
 *   next access.
 * - `refreshAll()`: manual reload (↻ button).
 * - Modal-open: callers (e.g. TransactionStagingModal) call `ensureLoaded()`
 *   to guarantee fresh data before showing an editable form.
 *
 * See plan: `LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4.prompt.md`.
 *
 * @module stores/assetStore
 */

import {writable} from 'svelte/store';
import {zodiosApi} from '$lib/api';

// ============================================================================
// TYPES
// ============================================================================

/**
 * Subset of `FAinfoResponse` used across the app.
 * Optional fields may be missing or null on partial sources.
 */
export interface AssetInfo {
    id: number;
    display_name: string;
    currency: string;
    asset_type?: string | null;
    icon_url?: string | null;
    provider_code?: string | null;
    active: boolean;
    user_url?: string | null;
    has_metadata?: boolean;
    identifier_isin?: string | null;
    identifier_ticker?: string | null;
    identifier_cusip?: string | null;
    identifier_sedol?: string | null;
    identifier_figi?: string | null;
    identifier_uuid?: string | null;
    identifier_other?: string | null;
}

// ============================================================================
// INTERNAL STATE
// ============================================================================

const assetMap: Map<number, AssetInfo> = new Map();
let loaded = false;
let loadPromise: Promise<void> | null = null;

/**
 * Reactive version counter — incremented after every cache mutation.
 * Subscribe in components (`void $assetStoreVersion`) to retrigger derived
 * computations when the cache changes.
 */
export const assetStoreVersion = writable(0);

function bump(): void {
    assetStoreVersion.update((v) => v + 1);
}

/**
 * Coerce a raw API item (which may use union-with-null types from generated.ts)
 * into a clean AssetInfo. Strips array-wrapped null variants if present.
 */
function normalize(raw: Record<string, unknown>): AssetInfo {
    const flat = (v: unknown): unknown => (Array.isArray(v) ? v[0] : v);
    return {
        id: raw.id as number,
        display_name: (raw.display_name as string) ?? '',
        currency: (raw.currency as string) ?? '',
        asset_type: (flat(raw.asset_type) as string | null | undefined) ?? null,
        icon_url: (flat(raw.icon_url) as string | null | undefined) ?? null,
        provider_code: (flat(raw.provider_code) as string | null | undefined) ?? null,
        active: (raw.active as boolean) ?? true,
        user_url: (flat(raw.user_url) as string | null | undefined) ?? null,
        has_metadata: (raw.has_metadata as boolean) ?? false,
        identifier_isin: (flat(raw.identifier_isin) as string | null | undefined) ?? null,
        identifier_ticker: (flat(raw.identifier_ticker) as string | null | undefined) ?? null,
        identifier_cusip: (flat(raw.identifier_cusip) as string | null | undefined) ?? null,
        identifier_sedol: (flat(raw.identifier_sedol) as string | null | undefined) ?? null,
        identifier_figi: (flat(raw.identifier_figi) as string | null | undefined) ?? null,
        identifier_uuid: (flat(raw.identifier_uuid) as string | null | undefined) ?? null,
        identifier_other: (flat(raw.identifier_other) as string | null | undefined) ?? null,
    };
}

// ============================================================================
// PUBLIC API
// ============================================================================

/**
 * Ensure the full asset list is loaded once.
 * Concurrent calls share the same in-flight promise. Subsequent calls after
 * a successful load resolve immediately.
 *
 * The endpoint returns only assets the current user can access (server-side
 * filter), so the cache is per-user safe.
 */
export async function ensureAssetsLoaded(): Promise<void> {
    if (loaded) return;
    if (loadPromise) return loadPromise;
    loadPromise = (async () => {
        try {
            const items = (await zodiosApi.list_assets_api_v1_assets_query_get()) as Array<Record<string, unknown>>;
            assetMap.clear();
            for (const it of items) {
                const info = normalize(it);
                assetMap.set(info.id, info);
            }
            loaded = true;
            bump();
        } catch {
            // Fail silently — getAssetInfo() returns null for unknown ids
        } finally {
            loadPromise = null;
        }
    })();
    return loadPromise;
}

/** Force reload — discards the cache and re-fetches. Use behind a manual ↻ button. */
export async function refreshAllAssets(): Promise<void> {
    loaded = false;
    loadPromise = null;
    assetMap.clear();
    bump();
    return ensureAssetsLoaded();
}

/**
 * Sync lookup. Returns null if the cache hasn't loaded the id yet.
 * Components that need to react to load completion should subscribe to
 * `assetStoreVersion` (or call `ensureAssetsLoaded()` before render).
 */
export function getAssetInfo(id: number | null | undefined): AssetInfo | null {
    if (id == null) return null;
    return assetMap.get(id) ?? null;
}

/** All cached assets, in insertion order. Re-derives on every call. */
export function getAllAssets(): AssetInfo[] {
    return Array.from(assetMap.values());
}

/** Whether the store has been populated at least once. */
export function isAssetsLoaded(): boolean {
    return loaded;
}

/**
 * Opportunistic ingress: upsert fresh asset data into the cache.
 *
 * Call this from any callsite that already holds fresh asset payloads
 * (e.g. `AssetModal.save` response, `/assets` page reload, search-select
 * pick of an existing DB asset). Cheap, idempotent, and centralizes the
 * "verify backend has the same data" intent.
 *
 * Items missing required fields (`id`, `display_name`, `currency`) are skipped.
 */
export function mergeAssets(items: ReadonlyArray<Record<string, unknown> | AssetInfo>): void {
    let changed = false;
    for (const raw of items) {
        if (raw == null || (raw as AssetInfo).id == null) continue;
        const info = normalize(raw as Record<string, unknown>);
        if (!info.display_name || !info.currency) continue;
        assetMap.set(info.id, info);
        changed = true;
    }
    if (changed) bump();
}

/**
 * Centralized eviction utility.
 * Call this from EVERY asset mutation callsite (AssetModal save / delete / wipe).
 * Removes the entry from the cache so the next `ensureAssetsLoaded()` (after
 * a `refreshAllAssets()` or `mergeAssets()` follow-up) re-fetches fresh data.
 *
 * Note: this does NOT trigger a network call by itself — it only invalidates.
 * Pair with `mergeAssets([response])` when the mutation response carries the
 * fresh payload to avoid an extra round-trip.
 */
export function invalidateAfterMutation(idOrIds: number | ReadonlyArray<number>): void {
    const ids = typeof idOrIds === 'number' ? [idOrIds] : idOrIds;
    let changed = false;
    for (const id of ids) {
        if (assetMap.delete(id)) changed = true;
    }
    if (changed) bump();
}
