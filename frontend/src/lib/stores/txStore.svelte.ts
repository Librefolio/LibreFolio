/**
 * txStore — Single source of truth for loaded transactions.
 *
 * Replaces the `mainRows` / `partnerRows` pattern scattered across +page,
 * BulkModal, and PickerModal. All DB-fetched transactions live here;
 * modals read from the store instead of receiving them via props.
 *
 * Architecture: Plan C — Phase 07 Part 4 Round 6.
 */

import {canEditBroker, canEditPaired} from '$lib/stores/brokerStore';

// ─── Types ───────────────────────────────────────────────────────────────────

// Re-export from canonical source
export type {TXReadItem} from '$lib/components/transactions/types';
import type {TXReadItem} from '$lib/components/transactions/types';

// ─── Store State (Svelte 5 runes) ───────────────────────────────────────────

/** Internal reactive map: id → TXReadItem */
let _map = $state<Map<number, TXReadItem>>(new Map());

/** Reactive version counter — bumped on every setAll/invalidate so consumers
 *  using `$derived` or `$effect` that reference `txStoreVersion` will re-run. */
let _version = $state(0);

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Replace all transactions in the store (called once from +page reload).
 * Both mainRows and partnerRows are merged into a single flat Map.
 */
export function txStoreSetAll(main: TXReadItem[], partners: TXReadItem[]): void {
    const map = new Map<number, TXReadItem>();
    for (const r of main) map.set(r.id, r);
    for (const r of partners) map.set(r.id, r);
    _map = map;
    _version++;
}

/** Get a single transaction by ID. */
export function txStoreGet(id: number): TXReadItem | undefined {
    return _map.get(id);
}

/** Get the linked partner of a transaction (via related_transaction_id). */
export function txStoreGetPartner(id: number): TXReadItem | undefined {
    const tx = _map.get(id);
    if (!tx?.related_transaction_id) return undefined;
    return _map.get(tx.related_transaction_id);
}

/** Get all transactions as an array. */
export function txStoreGetAll(): TXReadItem[] {
    return [..._map.values()];
}

/** Get all "main" rows (those not exclusively partner-only).
 *  In practice this returns everything since main+partners are merged. */
export function txStoreGetMain(): TXReadItem[] {
    return [..._map.values()];
}

/** Get filtered subset. */
export function txStoreGetFiltered(filterFn: (tx: TXReadItem) => boolean): TXReadItem[] {
    return [..._map.values()].filter(filterFn);
}

/**
 * Check if a transaction can be edited by the current user.
 * - Standalone: user must be OWNER/EDITOR on the broker.
 * - Paired: user must be OWNER/EDITOR on BOTH brokers.
 */
export function txStoreCanEdit(id: number): boolean {
    const tx = _map.get(id);
    if (!tx) return false;
    if (tx.related_transaction_id == null) {
        return canEditBroker(tx.broker_id);
    }
    // Paired — need both brokers
    const partner = _map.get(tx.related_transaction_id);
    const partnerBrokerId = partner?.broker_id ?? tx.partner_broker_id ?? tx.broker_id;
    return canEditPaired(tx.broker_id, partnerBrokerId);
}

/** Invalidate (clear) the store — signals that a reload is needed. */
export function txStoreInvalidate(): void {
    _map = new Map();
    _version++;
}

/** Reactive version number — use in `$derived`/`$effect` to track changes. */
export function txStoreGetVersion(): number {
    return _version;
}

/** Total count of transactions in store. */
export function txStoreCount(): number {
    return _map.size;
}

