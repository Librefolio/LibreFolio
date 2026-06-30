/**
 * Broker Store — Session-level cache for broker info.
 *
 * Mirrors the [`assetStore`](./assetStore.ts) pattern: a unified, reactive
 * cache for broker entries (`{id, name, icon_url, portal_url,
 * default_import_plugin, ...}`) so any component (TransactionsTable cell,
 * BrokerSelect, header summary, etc.) can resolve a broker by id without
 * firing its own `GET /brokers` request.
 *
 * Loaded once via `GET /brokers` (the basic list, NOT the per-broker summary
 * which carries cash_balances/holdings — that stays page-specific).
 *
 * **Implementation**: built on top of [`createEntityStore`](./entityStore.ts).
 * Same invariants as `assetStore`: `invalidateBroker(id)` resets `loaded` so
 * the next `ensureBrokersLoaded()` re-fetches, and `mergeBrokers` accepts
 * partial PATCH payloads.
 *
 * @module stores/brokerStore
 */

import {zodiosApi} from '$lib/api';
import {createEntityStore} from '../core/entityStore';
import {derived} from 'svelte/store';
import {canEditWithRole, getRoleRank, type PairedAccessLevel} from '$lib/utils/broker/brokerRoleHelpers';
import {ensurePluginIconsLoaded, normalizeBrokerIconField} from '$lib/utils/broker/brokerHelpers';

// ============================================================================
// TYPES
// ============================================================================

/**
 * Subset of `BRReadItem` cached for cross-component lookup.
 * Optional fields may be missing or null on partial sources.
 */
export interface BrokerInfo {
    id: number;
    name: string;
    description?: string | null;
    icon_url?: string | null;
    portal_url?: string | null;
    default_import_plugin?: string | null;
    allow_cash_overdraft?: boolean;
    allow_asset_shorting?: boolean;
    is_active?: boolean;
    opened_at?: string | null;
    user_role?: string | null;
    /** Carried for compatibility with the wider `Broker` type (BRReadItem). */
    created_at?: string;
    /** Carried for compatibility with the wider `Broker` type (BRReadItem). */
    updated_at?: string;
}

// ============================================================================
// NORMALIZATION
// ============================================================================

/**
 * Coerce a raw API item into a clean BrokerInfo.
 * Defensive: when called via `mergeBrokers` with a partial PATCH payload, only
 * fields actually present on `raw` are emitted (others stay `undefined` so the
 * factory's merge step can preserve the existing cached value).
 */
function normalize(raw: Record<string, unknown>): BrokerInfo {
    const out: Record<string, unknown> = {id: raw.id as number};
    const copy = (key: string, fallback: unknown = null): void => {
        if (key in raw) out[key] = (raw[key] ?? fallback) as unknown;
    };
    copy('name', '');
    copy('description');
    copy('icon_url');
    copy('portal_url');
    copy('default_import_plugin');
    copy('allow_cash_overdraft');
    copy('allow_asset_shorting');
    copy('is_active');
    copy('opened_at');
    copy('user_role');
    copy('created_at');
    copy('updated_at');
    return out as unknown as BrokerInfo;
}

// ============================================================================
// STORE INSTANCE
// ============================================================================

const store = createEntityStore<BrokerInfo, number>({
    loader: async () => (await zodiosApi.list_brokers_api_v1_brokers_get()) as Array<Record<string, unknown>>,
    getId: (b) => b.id,
    normalize,
    requiredFields: ['name'],
});

const iconFieldLoaders = new Map<number, Promise<void>>();

function hasBrokerIconFields(info: BrokerInfo | null | undefined): boolean {
    if (!info) return false;
    return Boolean(
        normalizeBrokerIconField(info.icon_url) ||
        normalizeBrokerIconField(info.portal_url) ||
        normalizeBrokerIconField(info.default_import_plugin),
    );
}

// ============================================================================
// PUBLIC API
// ============================================================================

/** Reactive version counter — bumped on every cache mutation. */
export const brokerStoreVersion = derived(store.version, (v) => v);

/**
 * Ensure the full broker list is loaded once.
 * Concurrent calls share the same in-flight promise. After `invalidateBroker()`
 * removes entries, `loaded` is reset and the next call re-fetches.
 *
 * Also kicks off plugin icon cache loading (fire-and-forget) so that
 * `getBrokerIconUrl()` can resolve plugin-based icons without requiring
 * explicit `ensurePluginIconsLoaded()` calls in every consumer page.
 */
export const ensureBrokersLoaded = async (): Promise<void> => {
    await store.ensureLoaded();
    ensurePluginIconsLoaded(); // fire-and-forget — populates _pluginIconCache for getBrokerIconUrl
};

/** Force reload — discards the cache and re-fetches.
 *  Also kicks off plugin icon cache loading (fire-and-forget). */
export const refreshAllBrokers = async (): Promise<void> => {
    await store.refreshAll();
    ensurePluginIconsLoaded(); // fire-and-forget — keeps plugin icon cache fresh
};

/** Sync lookup. Returns null if id is null/undefined or not cached. */
export const getBrokerInfo = store.get;

/** All cached brokers, in insertion order. */
export const getAllBrokers = store.getAll;

/** Whether the store has been populated at least once. */
export const isBrokersLoaded = store.isLoaded;

/**
 * Hydrate icon-relevant fields for a broker when a consumer only has a partial
 * `{id, name}` shape. Shared de-duplication prevents N identical requests.
 */
export async function ensureBrokerIconFieldsLoaded(brokerId: number | null | undefined): Promise<void> {
    if (brokerId == null) return;
    if (hasBrokerIconFields(store.get(brokerId))) return;
    const inFlight = iconFieldLoaders.get(brokerId);
    if (inFlight) return inFlight;

    const loader = (async () => {
        try {
            const broker = (await zodiosApi.get_broker_api_v1_brokers__broker_id__get({
                params: {broker_id: brokerId},
            } as never)) as Record<string, unknown>;
            store.merge([broker]);
        } catch (e) {
            // eslint-disable-next-line no-console
            console.error('[brokerStore] Failed to hydrate broker icon fields:', e);
        } finally {
            iconFieldLoaders.delete(brokerId);
        }
    })();

    iconFieldLoaders.set(brokerId, loader);
    return loader;
}

/**
 * Opportunistic ingress: upsert fresh broker data into the cache.
 * Accepts both full payloads (GET responses) and partial PATCH payloads.
 */
export const mergeBrokers = store.merge;

/**
 * Centralized eviction utility.
 * Call this from EVERY broker mutation callsite (BrokerModal save / delete).
 * Removes the entry **and resets `loaded=false`** so the next
 * `ensureBrokersLoaded()` re-fetches.
 */
export const invalidateBroker = store.invalidate;

// ============================================================================
// ROLE / ACCESS HELPERS
// ============================================================================

/** Get the user's role on a specific broker. Returns null if not cached. */
export function getBrokerRole(brokerId: number): string | null {
    const info = store.get(brokerId);
    return info?.user_role ?? null;
}

/** True if the user has OWNER or EDITOR role on the broker. */
export function canEditBroker(brokerId: number): boolean {
    return canEditWithRole(getBrokerRole(brokerId));
}

/** True if the user has EDITOR+ on BOTH brokers of a paired transaction. */
export function canEditPaired(brokerIdA: number, brokerIdB: number): boolean {
    return canEditBroker(brokerIdA) && canEditBroker(brokerIdB);
}

/** All brokers the user has some access to (user_role != null). */
export function getAccessibleBrokers(): BrokerInfo[] {
    return store.getAll().filter((b) => b.user_role != null);
}

/** Only brokers where user is OWNER or EDITOR. */
export function getEditableBrokers(): BrokerInfo[] {
    return store.getAll().filter((b) => canEditWithRole(b.user_role));
}

/**
 * Paired access level: min(roleA, roleB).
 * - `full`: both EDITOR+ → edit/delete/clone allowed
 * - `viewer`: at least one is VIEWER → view only
 * - `none`: partner broker not accessible → view only (locked)
 */
export function getPairedAccessLevel(brokerIdA: number, partnerBrokerId: number | null | undefined): PairedAccessLevel {
    const rankA = getRoleRank(getBrokerRole(brokerIdA));
    if (partnerBrokerId == null) {
        // Standalone
        return rankA >= 2 ? 'full' : rankA >= 1 ? 'viewer' : 'none';
    }
    const rankB = getRoleRank(getBrokerRole(partnerBrokerId));
    const minRank = Math.min(rankA, rankB);
    if (minRank >= 2) return 'full';
    if (minRank >= 1) return 'viewer';
    return 'none';
}
