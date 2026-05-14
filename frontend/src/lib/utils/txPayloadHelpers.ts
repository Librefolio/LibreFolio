/**
 * txPayloadHelpers.ts — Shared helpers for building transaction create/update
 * payloads. Used by both TransactionFormModal and TransactionBulkModal to
 * guarantee identical diffing and sign-flip logic.
 *
 * @module utils/txPayloadHelpers
 */

import type {TypeRule} from '$lib/stores/transactionTypeStore';

// =============================================================================
//  Types
// =============================================================================

/** Minimal cash shape used throughout transaction payloads. */
export interface CashValue {
    code: string;
    amount: string;
}

/** Minimal transaction fields needed for diffing and payload building.
 *  Works for both DraftRow (BulkModal) and form draft (FormModal). */
export interface TxFields {
    type: string;
    broker_id: number;
    date: string;
    quantity: string;
    asset_id?: number | null;
    cash?: CashValue | null;
    tags: string[];
    description: string;
    cost_basis_override: string;
    asset_event_id?: number | null;
    link_uuid?: string | null;
}

/** Original DB transaction shape for diffing (read-side). */
export interface TxOriginal {
    id: number;
    type: string;
    broker_id: number;
    date: string;
    quantity: string;
    asset_id?: number | null;
    cash?: CashValue | null;
    tags?: string[] | null;
    description?: string | null;
    cost_basis_override?: string | null;
    asset_event_id?: number | null;
    link_uuid?: string | null;
}

// =============================================================================
//  PATCHABLE_FIELDS — single source of truth
// =============================================================================

/** Fields accepted by the TXUpdateItem backend schema.
 *  Everything else (broker_id, asset_id, link_uuid, related_transaction_id,
 *  created_at, updated_at) is immutable and MUST NOT be sent. */
export const PATCHABLE_FIELDS = new Set(['type', 'date', 'quantity', 'cash', 'tags', 'description', 'cost_basis_override', 'asset_event_id']);

// =============================================================================
//  Sign-flip helpers
// =============================================================================

/** Apply sign-flip rules based on the TypeRule. Pure function, no side effects. */
export function applySignRules(qty: string, cash: CashValue | null | undefined, rule: TypeRule): {signedQty: string; signedCash: CashValue | null} {
    const negQty = rule.quantityRule === 'negative';
    const negCash = rule.cashSign === 'negative';
    const signedQty = negQty ? String(-Math.abs(Number(qty))) : qty;
    const signedCash = buildSignedCash(cash, negCash);
    return {signedQty, signedCash};
}

/** Build a cash value with sign applied. */
export function buildSignedCash(cash: CashValue | null | undefined, negate: boolean): CashValue | null {
    if (!cash) return null;
    if (negate) return {code: cash.code, amount: String(-Math.abs(Number(cash.amount)))};
    return {code: cash.code, amount: cash.amount};
}

// =============================================================================
//  Field-level equality — type-aware normalization
// =============================================================================

/** Compare two field values with type-aware normalization.
 *  Prevents spurious diffs from format differences ("0.1" vs "0.100000"). */
export function fieldEq(key: string, a: unknown, b: unknown): boolean {
    // Numeric fields: compare as numbers to ignore string format diffs
    if (key === 'quantity') {
        return Number(a) === Number(b);
    }
    // Cash: compare code strict + numeric amount
    if (key === 'cash') {
        const ca = a as CashValue | null | undefined;
        const cb = b as CashValue | null | undefined;
        if (!ca && !cb) return true;
        if (!ca || !cb) return false;
        return ca.code === cb.code && Number(ca.amount) === Number(cb.amount);
    }
    // String fields: normalize empty/null/undefined → ""
    if (key === 'description' || key === 'cost_basis_override') {
        return (a || '') === (b || '');
    }
    // Tags: compare sorted arrays
    if (key === 'tags') {
        const ta = Array.isArray(a) ? [...a].sort() : [];
        const tb = Array.isArray(b) ? [...b].sort() : [];
        return JSON.stringify(ta) === JSON.stringify(tb);
    }
    // asset_event_id: normalize null/undefined to 0
    if (key === 'asset_event_id') {
        return ((a as number | null) ?? 0) === ((b as number | null) ?? 0);
    }
    // Default: strict equality
    return a === b;
}

// =============================================================================
//  buildCreatePayload — single source of truth for CREATE items
// =============================================================================

/** Build a TXCreateItem payload from transaction fields + type rule. */
export function buildCreatePayload(fields: TxFields, rule: TypeRule): Record<string, unknown> {
    const {signedQty, signedCash} = applySignRules(fields.quantity, fields.cash, rule);
    const out: Record<string, unknown> = {
        broker_id: fields.broker_id,
        type: fields.type,
        date: fields.date,
        quantity: signedQty,
    };
    if (fields.asset_id != null && rule.assetField !== 'forbidden') out.asset_id = fields.asset_id;
    if (signedCash && rule.cashField !== 'forbidden') out.cash = signedCash;
    const tags = fields.tags ?? [];
    if (tags.length > 0) out.tags = tags;
    const desc = (fields.description ?? '').trim();
    if (desc) out.description = desc;
    if (fields.asset_event_id != null && rule.eventLinkable) out.asset_event_id = fields.asset_event_id;
    const cbo = (fields.cost_basis_override ?? '').trim();
    if (cbo) out.cost_basis_override = cbo;
    if (fields.link_uuid && rule.requiresPair) out.link_uuid = fields.link_uuid;
    return out;
}

// =============================================================================
//  buildUpdateDiff — single source of truth for UPDATE diffing
// =============================================================================

/** Build a TXUpdateItem payload by diffing current fields against the original.
 *  Uses the original type's sign rules for correct comparison when type changed.
 *  Only includes changed fields from PATCHABLE_FIELDS. */
export function buildUpdateDiff(current: TxFields, original: TxOriginal, currentRule: TypeRule, originalRule: TypeRule): Record<string, unknown> {
    const {signedQty, signedCash} = applySignRules(current.quantity, current.cash, currentRule);
    const {signedQty: origSignedQty, signedCash: origSignedCash} = applySignRules(original.quantity, original.cash, originalRule);

    // Field definitions: [key, currentValue, originalValue]
    const fieldPairs: Array<[string, unknown, unknown]> = [
        ['type', current.type, original.type],
        ['date', current.date, original.date],
        ['quantity', signedQty, origSignedQty],
        ['cash', signedCash, origSignedCash],
        ['tags', current.tags, original.tags ?? []],
        ['description', current.description || null, original.description ?? null],
        ['cost_basis_override', current.cost_basis_override || null, original.cost_basis_override ?? null],
        ['asset_event_id', current.asset_event_id, original.asset_event_id ?? null],
    ];

    const changes: Record<string, unknown> = {id: original.id};
    for (const [key, cur, orig] of fieldPairs) {
        if (!PATCHABLE_FIELDS.has(key)) continue;
        if (!fieldEq(key, cur, orig)) {
            // Special: asset_event_id sentinel 0 = unlink
            if (key === 'asset_event_id') {
                changes[key] = (cur as number | null) ?? 0;
            } else {
                changes[key] = cur;
            }
        }
    }
    return changes;
}

/** Build update diff for a dual-form item (from collectDualCreates output).
 *  Compares the full CREATE payload against original, filtering to PATCHABLE_FIELDS.
 *  Used by FormModal's collectDualUpdates(). */
export function diffDualItem(item: Record<string, unknown>, orig: TxOriginal): Record<string, unknown> {
    const out: Record<string, unknown> = {id: orig.id};
    for (const key of PATCHABLE_FIELDS) {
        if (!(key in item)) continue;
        const origVal = (orig as unknown as Record<string, unknown>)[key];
        if (!fieldEq(key, item[key], origVal)) {
            out[key] = item[key];
        }
    }
    return out;
}
