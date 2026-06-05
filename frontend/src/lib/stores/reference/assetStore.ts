/**
 * Asset Store — Session-level cache for asset info.
 *
 * Provides a unified, reactive cache for `{id, display_name, currency, asset_type,
 * icon_url, provider_code, active, identifier_*}` so any component can resolve an
 * asset by id without firing its own request.
 *
 * Loads the FULL set of accessible assets via `GET /assets/query` (no filter),
 * matching the existing pattern used by `/assets/+page.svelte` and `LiveTicker`.
 *
 * Cross-client edits are NOT proactively synced (no WS/SSE). Mitigations:
 * - `mergeAssets(items)`: opportunistic ingress called wherever fresh asset data
 *   naturally flows through the FE (e.g. AssetModal save response,
 *   `/assets` page reload). Partial PATCH payloads are also accepted — fields
 *   not present in the payload are preserved.
 * - `invalidateAfterMutation(ids)`: centralized eviction called from every
 *   mutation callsite (AssetModal save / delete / wipe). **Resets `loaded=false`**
 *   so the next access triggers a fresh fetch.
 * - `refreshAllAssets()`: manual reload (↻ button).
 * - Modal-open: callers (e.g. TransactionStagingModal) call `ensureAssetsLoaded()`
 *   to guarantee fresh data before showing an editable form.
 *
 * **Implementation**: built on top of [`createEntityStore`](./entityStore.ts) —
 * the generic factory that encodes the "list-bounded entity cache" pattern.
 *
 * @module stores/assetStore
 */

import {zodiosApi} from '$lib/api';
import {createEntityStore} from '../core/entityStore';
import {derived} from 'svelte/store';

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
// NORMALIZATION
// ============================================================================

/**
 * Coerce a raw API item (which may use union-with-null types from generated.ts)
 * into a clean AssetInfo. Strips array-wrapped null variants if present.
 *
 * Defensive: when called via `mergeAssets` with a partial PATCH payload, only
 * fields actually present on `raw` are emitted (others stay `undefined` so the
 * factory's merge step can preserve the existing cached value).
 */
function normalize(raw: Record<string, unknown>): AssetInfo {
    const flat = (v: unknown): unknown => (Array.isArray(v) ? v[0] : v);
    const out: Record<string, unknown> = {id: raw.id as number};
    const copyFlat = (key: string): void => {
        if (key in raw) out[key] = flat(raw[key]) ?? null;
    };
    const copyDirect = (key: string, fallback: unknown = null): void => {
        if (key in raw) out[key] = (raw[key] ?? fallback) as unknown;
    };
    copyDirect('display_name', '');
    copyDirect('currency', '');
    copyFlat('asset_type');
    copyFlat('icon_url');
    copyFlat('provider_code');
    copyDirect('active');
    copyFlat('user_url');
    copyDirect('has_metadata');
    copyFlat('identifier_isin');
    copyFlat('identifier_ticker');
    copyFlat('identifier_cusip');
    copyFlat('identifier_sedol');
    copyFlat('identifier_figi');
    copyFlat('identifier_uuid');
    copyFlat('identifier_other');
    return out as unknown as AssetInfo;
}

// ============================================================================
// STORE INSTANCE
// ============================================================================

const store = createEntityStore<AssetInfo, number>({
    loader: async () => (await zodiosApi.list_assets_api_v1_assets_query_get()) as Array<Record<string, unknown>>,
    getId: (a) => a.id,
    normalize,
    // New entries must carry these (PATCH payloads upsert into existing rows).
    requiredFields: ['display_name', 'currency'],
});

// ============================================================================
// PUBLIC API (preserved for backward compatibility)
// ============================================================================

/** Reactive version counter — bumped on every cache mutation. */
export const assetStoreVersion = derived(store.version, (v) => v);

/**
 * Ensure the full asset list is loaded once.
 * Concurrent calls share the same in-flight promise. Subsequent calls after
 * a successful load resolve immediately. After `invalidateAfterMutation()`
 * removes entries, `loaded` is reset and the next call re-fetches.
 */
export const ensureAssetsLoaded = store.ensureLoaded;

/** Force reload — discards the cache and re-fetches. Use behind a manual ↻ button. */
export const refreshAllAssets = store.refreshAll;

/**
 * Sync lookup. Returns null if the cache hasn't loaded the id yet.
 * Components that need to react to load completion should subscribe to
 * `assetStoreVersion` (or call `ensureAssetsLoaded()` before render).
 */
export const getAssetInfo = store.get;

/** All cached assets, in insertion order. Re-derives on every call. */
export const getAllAssets = store.getAll;

/** Whether the store has been populated at least once. */
export const isAssetsLoaded = store.isLoaded;

/**
 * Opportunistic ingress: upsert fresh asset data into the cache.
 *
 * Accepts FULL asset payloads (e.g. GET response items) AND partial PATCH
 * payloads — fields not present in the partial are preserved on the cached
 * entry. New entries (id not already cached) are skipped if `display_name`
 * or `currency` are missing.
 */
export const mergeAssets = store.merge;

/**
 * Centralized eviction utility.
 * Call this from EVERY asset mutation callsite (AssetModal save / delete / wipe).
 * Removes the entry from the cache **and resets `loaded=false`** so the next
 * `ensureAssetsLoaded()` re-fetches.
 *
 * Pair with `mergeAssets([{id, ...patchPayload}])` when the mutation FE knows
 * the new field values (avoids the round-trip).
 */
export const invalidateAfterMutation = store.invalidate;
