/**
 * resolveFormItems.ts — Centralized helper for building FormModal input items.
 *
 * The FormModal receives an array of 1 or 2 TXReadItem objects:
 * - [single] → standard single-transaction form
 * - [from, to] → dual paired form (transfer_asset / transfer_cash / fx)
 * - [from, InaccessiblePartner] → dual form with locked partner side
 *
 * This module is the SINGLE source of truth for resolving those items from
 * any source (BulkModal ops[], txStore, standalone page).
 *
 * Plan: BugfixRound3 — Unified Partner Architecture
 */

import type {TXReadItem} from './types';

// =============================================================================
//  Types
// =============================================================================

/** Sentinel for a partner that exists but the user cannot access (no broker role). */
export interface InaccessiblePartner {
    _inaccessible: true;
    broker_id: number;
}

/** The normalized input for the FormModal: always an array of 1 or 2 items. */
export type FormModalItems = [TXReadItem] | [TXReadItem, TXReadItem] | [TXReadItem, InaccessiblePartner];

// =============================================================================
//  Type guards
// =============================================================================

export function isInaccessible(item: TXReadItem | InaccessiblePartner): item is InaccessiblePartner {
    return '_inaccessible' in item && !!(item as InaccessiblePartner)._inaccessible;
}

// =============================================================================
//  Orientation helper (From/To ordering)
// =============================================================================

/**
 * Ensure the "from" side is items[0] and "to" side is items[1].
 * Convention: "from" = the sender (qty < 0 for transfer_asset, cash < 0 for transfer_cash/fx).
 * If items are already oriented correctly, returns as-is.
 */
function orientPair(a: TXReadItem, b: TXReadItem): [TXReadItem, TXReadItem] {
    const qtyA = Number(a.quantity ?? 0);
    const cashA = Number(a.cash?.amount ?? 0);

    // transfer_asset: sender has qty < 0
    if (qtyA < 0) return [a, b];
    if (Number(b.quantity ?? 0) < 0) return [b, a];

    // transfer_cash / fx: sender has cash < 0
    if (cashA < 0) return [a, b];
    if (Number(b.cash?.amount ?? 0) < 0) return [b, a];

    // Fallback: keep as-is (first item = from)
    return [a, b];
}

// =============================================================================
//  Guardrail
// =============================================================================

function validatePair(a: TXReadItem, b: TXReadItem): boolean {
    if (a.type !== b.type) {
        console.error('[resolveFormItems] Paired items have mismatched types:', a.type, b.type);
        return false;
    }
    // If both have real IDs, check linking
    if (a.id > 0 && b.id > 0) {
        const aLinksB = a.related_transaction_id === b.id;
        const bLinksA = b.related_transaction_id === a.id;
        if (!aLinksB && !bLinksA) {
            console.error('[resolveFormItems] Paired items do not reference each other:', a.id, b.id);
            return false;
        }
    }
    return true;
}

// =============================================================================
//  Resolver: from BulkModal ops[]
// =============================================================================

/**
 * Minimal interface for PendingOp — avoids importing the full BulkModal type.
 * The BulkModal passes its internal types; we only need these fields.
 */
export interface MinimalPendingOp {
    tempId: string;
    op: 'create' | 'edit';
    pairedWith?: string;
    txId?: number; // only for op === 'edit'
}

/**
 * Resolve FormModal items from BulkModal's ops array.
 *
 * @param mainOp   The visible main PendingOp being edited
 * @param ops      The full ops[] array (includes hidden partners)
 * @param opToTxLike  Adapter: PendingOp → TXReadItem
 * @param txStoreGet  Lookup: DB id → TXReadItem (for fallback)
 */
export function resolveFormItemsFromOps<T extends MinimalPendingOp>(mainOp: T, ops: T[], opToTxLike: (op: T) => TXReadItem, txStoreGet: (id: number) => TXReadItem | undefined): FormModalItems {
    const item0 = opToTxLike(mainOp);

    // 1. Try to find partner op in the local ops array (pairedWith points to main)
    const partnerOp = ops.find((o) => o.pairedWith === mainOp.tempId);
    if (partnerOp) {
        const item1 = opToTxLike(partnerOp);
        if (!validatePair(item0, item1)) return [item0];
        return orientPair(item0, item1);
    }

    // 2. Fallback: for edit ops, check if DB has a linked partner
    if (mainOp.op === 'edit' && mainOp.txId != null) {
        const dbTx = txStoreGet(mainOp.txId);
        const relId = dbTx?.related_transaction_id;
        if (relId != null && relId > 0) {
            const partnerTx = txStoreGet(relId);
            if (partnerTx) {
                if (!validatePair(item0, partnerTx)) return [item0];
                return orientPair(item0, partnerTx);
            }
        }
    }

    // 3. Single item
    return [item0];
}

// =============================================================================
//  Resolver: for standalone page (view mode)
// =============================================================================

/**
 * Resolve FormModal items for the standalone transactions page (view/readonly).
 *
 * @param row           The main TXReadItem being viewed
 * @param txStoreGet    Lookup: DB id → TXReadItem
 * @param getBrokerRole Lookup: broker_id → role string | null (null = no access)
 */
export function resolveFormItemsForView(row: TXReadItem, txStoreGet: (id: number) => TXReadItem | undefined, getBrokerRole: (brokerId: number) => string | null): FormModalItems {
    const relId = row.related_transaction_id;
    if (relId == null || relId <= 0) return [row];

    const partner = txStoreGet(relId);
    if (partner) {
        // Partner accessible — orient and return pair
        if (!validatePair(row, partner)) return [row];
        return orientPair(row, partner);
    }

    // Partner not in store — check if we know the broker_id
    const pBid = row.partner_broker_id;
    if (pBid != null) {
        const role = getBrokerRole(pBid);
        if (role == null) {
            // Inaccessible partner
            return [row, {_inaccessible: true, broker_id: pBid}];
        }
    }

    // Partner exists but not loaded (edge case) — return single
    return [row];
}
