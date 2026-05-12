/**
 * Transaction Type Store — Session-level cache for TX type metadata.
 *
 * Loads once per session from GET /transactions/types and provides:
 * - sync `getMetadata(type)` for any component
 * - reactive `txTypeStoreVersion` to retrigger derived computations on load
 *
 * Pattern mirrors `currencyStore.ts`. See [[concepts/svelte5-runes]] / wiki.
 *
 * The PNG icon mapping is kept separate in `utils/transactionTypes.ts` (single
 * source of truth for enum + filename); this store holds the *logical* metadata
 * only (display name, validation rules, allowed signs, event_compatible).
 *
 * @module stores/txTypeStore
 */

import {writable} from 'svelte/store';
import {zodiosApi} from '$lib/api';

// ============================================================================
// TYPES
// ============================================================================

export interface TXTypeMetadata {
    code: string;
    name: string;
    description: string;
    icon: string;
    asset_mode: 'REQUIRED' | 'OPTIONAL' | 'FORBIDDEN';
    requires_link: boolean;
    requires_cash: boolean;
    allowed_quantity_sign: '+' | '-' | '0' | '+/-';
    allowed_cash_sign: '+' | '-' | '0' | '+/-';
    event_compatible: boolean;
}

// ============================================================================
// INTERNAL STATE
// ============================================================================

const metadataMap: Map<string, TXTypeMetadata> = new Map();
let loaded = false;
let loadPromise: Promise<void> | null = null;

/** Reactive version counter — bumped after a successful load. */
export const txTypeStoreVersion = writable(0);

// ============================================================================
// PUBLIC API
// ============================================================================

/**
 * Ensure TX type metadata is loaded (idempotent).
 * Concurrent calls share the same in-flight promise.
 */
export async function ensureTxTypesLoaded(): Promise<void> {
    if (loaded) return;
    if (loadPromise) return loadPromise;
    loadPromise = (async () => {
        try {
            const resp = await zodiosApi.get_transaction_types_api_v1_transactions_types_get();
            const items = (resp as unknown as {transaction_types?: TXTypeMetadata[]})?.transaction_types ?? (resp as unknown as TXTypeMetadata[]);
            metadataMap.clear();
            for (const m of items) metadataMap.set(m.code, m);
            loaded = true;
            txTypeStoreVersion.update((v) => v + 1);
        } catch {
            // Fail silently — getMetadata() will return null
        } finally {
            loadPromise = null;
        }
    })();
    return loadPromise;
}

/** Sync lookup. Returns null when the store hasn't been loaded yet. */
export function getTxTypeMetadata(code: string | null | undefined): TXTypeMetadata | null {
    if (!code) return null;
    return metadataMap.get(code.toUpperCase()) ?? null;
}

/** Whether the store has been populated at least once. */
export function isTxTypesLoaded(): boolean {
    return loaded;
}
