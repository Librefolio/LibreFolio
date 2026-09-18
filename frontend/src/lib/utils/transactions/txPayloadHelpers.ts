/**
 * txPayloadHelpers.ts — Shared helpers for building transaction create/update
 * payloads. Used by both TransactionFormModal and TransactionBulkModal to
 * guarantee identical diffing and sign-flip logic.
 *
 * @module utils/txPayloadHelpers
 */

import {type TypeRule, getCostBasisRule} from '$lib/stores/transactions/transactionTypeStore';
import type {BrimEvidence} from '$lib/types/files';

// =============================================================================
//  Types
// =============================================================================

/** A field todo emitted by a BRIM plugin for an accepted transaction.
 *  Severity 'blocker' prevents the row from being committed until resolved. */
export interface ImportTodo {
    field: string;
    severity: 'blocker' | 'warning';
    reasonCode: string;
    message: string;
    /** Source-data tables backing this todo (raw file rows + plugin comment). */
    evidence?: BrimEvidence[];
    /** Machine-readable numbers behind the todo (e.g. the nominal a purchase was compared to). */
    context?: Record<string, unknown>;
}

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
    cost_basis_override: {code: string; amount: string} | null;
    /** WAC mode: 'auto' = backend calculates, 'manual' = user-provided, null = not applicable */
    cost_basis_mode?: 'auto' | 'manual' | null;
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
    cost_basis_override?: {code: string; amount: string} | null;
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

interface ExactDecimalParts {
    /** -1 for negative, 0 for every representation of zero, 1 for positive. */
    sign: -1 | 0 | 1;
    /** Input magnitude with its exact decimal digits preserved. */
    unsigned: string;
    /** Representation-normalized magnitude used only for exact equality. */
    canonicalMagnitude: string;
}

/**
 * Parse the plain-decimal strings accepted by transaction payloads without ever
 * routing their digits through JavaScript's floating-point number type.
 */
function exactDecimalParts(value: unknown): ExactDecimalParts | null {
    if (typeof value !== 'string') return null;
    const trimmed = value.trim();
    const match = /^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))$/.exec(trimmed);
    if (!match) return null;

    const integer = match[2] ?? '';
    const fraction = match[3] ?? match[4] ?? '';
    const unsigned = trimmed.replace(/^[+-]/, '');
    const zero = !/[1-9]/.test(`${integer}${fraction}`);
    const canonicalInteger = (integer || '0').replace(/^0+(?=\d)/, '');
    const canonicalFraction = fraction.replace(/0+$/, '');
    const canonicalMagnitude = canonicalFraction ? `${canonicalInteger}.${canonicalFraction}` : canonicalInteger;
    return {
        sign: zero ? 0 : match[1] === '-' ? -1 : 1,
        unsigned,
        canonicalMagnitude,
    };
}

/** Exact sign classification for a transaction decimal string. */
export function exactDecimalSign(value: unknown): -1 | 0 | 1 | null {
    return exactDecimalParts(value)?.sign ?? null;
}

/** Exact numeric equality for plain-decimal strings, ignoring representation-only zeros. */
export function exactDecimalEqual(a: unknown, b: unknown): boolean {
    const left = exactDecimalParts(a);
    const right = exactDecimalParts(b);
    if (!left || !right) return a === b;
    if (left.sign !== right.sign) return false;
    return left.sign === 0 || left.canonicalMagnitude === right.canonicalMagnitude;
}

/** Apply sign-flip rules based on the TypeRule. Pure function, no side effects.
 *
 * Both directions are enforced, not just the negative one: a rule that says "positive"
 * is as binding as one that says "negative", and the backend rejects either violation
 * the same way. Any other rule (`free`, `any`, `nonzero`) carries real information in
 * the sign — an ADJUSTMENT or a TRANSFER leg means the opposite thing when flipped —
 * so those values are passed through untouched.
 */
export function applySignRules(qty: string, cash: CashValue | null | undefined, rule: TypeRule): {signedQty: string; signedCash: CashValue | null} {
    return {signedQty: applySign(qty, rule.quantityRule), signedCash: buildSignedCash(cash, rule.cashSign)};
}

/** Coerce a numeric string to the sign a rule demands, leaving free-sign rules alone. */
export function applySign(value: string, rule: string): string {
    // Preserve the established payload fallback for an absent signed field
    // without using Number('') as the coercion mechanism.
    if (value.trim() === '' && (rule === 'negative' || rule === 'positive')) return '0';
    const parsed = exactDecimalParts(value);
    if (!parsed) return value;
    if (rule === 'negative') return parsed.sign === 0 ? parsed.unsigned : `-${parsed.unsigned}`;
    if (rule === 'positive') return parsed.unsigned;
    return value;
}

/** Build a cash value with the sign its rule demands. Accepts a rule or a legacy boolean. */
export function buildSignedCash(cash: CashValue | null | undefined, rule: string | boolean): CashValue | null {
    if (!cash) return null;
    const resolved = typeof rule === 'boolean' ? (rule ? 'negative' : 'free') : rule;
    return {code: cash.code, amount: applySign(cash.amount, resolved)};
}

/** Canonical signed cash amount for a transaction, whatever representation it arrives in.
 *
 * Two representations of the same money coexist in the app, and this is what reconciles them:
 *   - **import pool rows** carry the amount already signed, as parsed from the broker file;
 *   - **rows read from the DB** are normalised to a magnitude by the edit form (see
 *     `fieldsFromTx`), because the form shows a magnitude and the *type* carries the sign.
 *
 * Applying the type's sign rule is safe on both, because `applySign` is idempotent: `'negative'`
 * adds exactly one leading minus to a non-zero decimal magnitude. Free-sign
 * rules (`free`/`any`/`nonzero` — ADJUSTMENT, TRANSFER legs) pass through untouched, which is
 * required rather than incidental: there the sign *is* information.
 *
 * Anything that compares, sums or pairs cash amounts must go through here. Reading
 * `fields.cash.amount` directly silently works for one representation and fails for the other.
 *
 * @returns the signed amount, or `null` when there is no cash or it is not a finite number.
 */
export function signedCashAmount(cash: CashValue | null | undefined, rule: TypeRule): number | null {
    const signed = buildSignedCash(cash, rule.cashSign);
    if (!signed) return null;
    const n = Number(signed.amount);
    return Number.isFinite(n) ? n : null;
}

// =============================================================================
//  Field-level equality — type-aware normalization
// =============================================================================

/** Compare two field values with type-aware normalization.
 *  Prevents spurious diffs from format differences ("0.1" vs "0.100000"). */
export function fieldEq(key: string, a: unknown, b: unknown): boolean {
    // Decimal fields: compare exact digits while ignoring representation-only zeros.
    if (key === 'quantity') {
        return exactDecimalEqual(a, b);
    }
    // Cash: compare code strictly and amount as an exact decimal string.
    if (key === 'cash') {
        const ca = a as CashValue | null | undefined;
        const cb = b as CashValue | null | undefined;
        if (!ca && !cb) return true;
        if (!ca || !cb) return false;
        return ca.code === cb.code && exactDecimalEqual(ca.amount, cb.amount);
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
    // WAC: send cost_basis_mode only if the backend rule allows it for this type+side.
    // The rule comes from the server transaction type metadata (getCostBasisRule).
    const qtySign = exactDecimalSign(fields.quantity) ?? 0;
    const side: 'from' | 'to' | 'self' = qtySign < 0 ? 'from' : qtySign > 0 ? 'to' : 'self';
    const cbRule = getCostBasisRule(fields.type, side);
    const cbAllowed = cbRule !== 'forbidden' && !(cbRule === 'required_qty_pos' && qtySign <= 0);

    if (cbAllowed) {
        if (fields.cost_basis_mode === 'auto') {
            out.cost_basis_mode = 'auto';
            out.cost_basis_override = fields.cost_basis_override ?? null;
        } else if (fields.cost_basis_mode === 'manual' && fields.cost_basis_override) {
            out.cost_basis_override = fields.cost_basis_override;
        }
    }
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
    const qtySign = exactDecimalSign(current.quantity) ?? 0;
    const side: 'from' | 'to' | 'self' = qtySign < 0 ? 'from' : qtySign > 0 ? 'to' : 'self';
    const cbRule = getCostBasisRule(current.type, side);
    const cbAllowed = cbRule !== 'forbidden' && !(cbRule === 'required_qty_pos' && qtySign <= 0);

    // Field definitions: [key, currentValue, originalValue]
    const fieldPairs: Array<[string, unknown, unknown]> = [
        ['type', current.type, original.type],
        ['date', current.date, original.date],
        ['quantity', signedQty, origSignedQty],
        ['cash', signedCash, origSignedCash],
        ['tags', current.tags, original.tags ?? []],
        ['description', current.description || null, original.description ?? null],
        ['asset_event_id', current.asset_event_id, original.asset_event_id ?? null],
    ];
    if (cbAllowed && current.cost_basis_mode === 'manual') {
        fieldPairs.push(['cost_basis_override', current.cost_basis_override || null, original.cost_basis_override ?? null]);
    }

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
    // Auto mode is meaningful only on a metadata-approved type/side. Explicit
    // manual overrides were included in fieldPairs above under the same gate.
    if (current.cost_basis_mode === 'auto' && cbAllowed) {
        changes.cost_basis_mode = 'auto';
        changes.cost_basis_override = current.cost_basis_override ?? null;
    }
    return changes;
}

/** Build update diff for a dual-form item (from collectDualCreates output).
 *  Compares the full CREATE payload against original, filtering to PATCHABLE_FIELDS.
 *  Used by FormModal's collectDualUpdates(). */
export function diffDualItem(item: Record<string, unknown>, orig: TxOriginal, costBasisMode?: TxFields['cost_basis_mode']): Record<string, unknown> {
    const out: Record<string, unknown> = {id: orig.id};
    for (const key of PATCHABLE_FIELDS) {
        // Cost basis is handled atomically below with its explicit mode and
        // metadata gate. Never let the generic field loop detach the override.
        if (key === 'cost_basis_override') continue;
        if (!(key in item)) continue;
        const origVal = (orig as unknown as Record<string, unknown>)[key];
        if (!fieldEq(key, item[key], origVal)) {
            out[key] = item[key];
        }
    }

    const itemType = typeof item.type === 'string' ? item.type : orig.type;
    const itemQuantity = item.quantity ?? orig.quantity;
    const itemQuantitySign = exactDecimalSign(itemQuantity) ?? 0;
    const itemSide: 'from' | 'to' | 'self' = itemQuantitySign < 0 ? 'from' : itemQuantitySign > 0 ? 'to' : 'self';
    const itemCostBasisRule = getCostBasisRule(itemType, itemSide);
    const cbAllowed = itemCostBasisRule !== 'forbidden' && !(itemCostBasisRule === 'required_qty_pos' && itemQuantitySign <= 0);
    const explicitMode = costBasisMode !== undefined ? costBasisMode : item.cost_basis_mode === 'auto' || item.cost_basis_mode === 'manual' ? item.cost_basis_mode : null;

    if (!cbAllowed || explicitMode == null) return out;
    if (explicitMode === 'auto') {
        out.cost_basis_mode = 'auto';
        out.cost_basis_override = item.cost_basis_override ?? null;
    } else if ('cost_basis_override' in item) {
        const originalOverride = orig.cost_basis_override ?? null;
        if (!fieldEq('cost_basis_override', item.cost_basis_override, originalOverride)) {
            // Manual is an internal discriminator; its wire shape is override-only.
            out.cost_basis_override = item.cost_basis_override;
        }
    }
    return out;
}

// =============================================================================
//  Dual-form payload builder — centralizes paired CREATE logic
// =============================================================================

/** Minimal fields for the "to" side of a dual-form transaction. */
export interface TxDualSide {
    broker_id: number;
    date?: string;
    cash?: CashValue | null;
    quantity?: string;
    cost_basis_override?: CashValue | null;
}

export type PairFormLayout = 'fx' | 'transfer_asset' | 'transfer_cash';

/**
 * Build 2 TXCreateItem payloads for a paired (dual-form) transaction.
 * Returns [fromItem, toItem] with shared link_uuid and correct signs per layout.
 *
 * Layout semantics:
 * - 'fx': FX_CONVERSION — qty=0 both sides, cash with opposite signs, different currencies
 * - 'transfer_asset': TRANSFER — qty with opposite signs, no cash, shared asset
 * - 'transfer_cash': CASH_TRANSFER — qty=0, cash with opposite signs, same currency
 */
export function buildDualCreatePayloads(layout: PairFormLayout, from: TxFields, to: TxDualSide, linkUuid: string): [Record<string, unknown>, Record<string, unknown>] {
    const sharedTags = from.tags && from.tags.length > 0 ? from.tags : undefined;
    const sharedDesc = (from.description ?? '').trim() || undefined;

    if (layout === 'fx') {
        const fromCashAmt = from.cash?.amount ? applySign(from.cash.amount, 'negative') : '0';
        const toCashAmt = to.cash?.amount ? applySign(to.cash.amount, 'positive') : '0';
        const fromItem: Record<string, unknown> = {
            broker_id: from.broker_id,
            type: 'FX_CONVERSION',
            date: from.date,
            quantity: '0',
            cash: {code: from.cash?.code ?? '', amount: fromCashAmt},
            link_uuid: linkUuid,
        };
        const toItem: Record<string, unknown> = {
            broker_id: from.broker_id,
            type: 'FX_CONVERSION',
            date: to.date || from.date,
            quantity: '0',
            cash: {code: to.cash?.code ?? '', amount: toCashAmt},
            link_uuid: linkUuid,
        };
        if (sharedTags) {
            fromItem.tags = sharedTags;
            toItem.tags = sharedTags;
        }
        if (sharedDesc) {
            fromItem.description = sharedDesc;
            toItem.description = sharedDesc;
        }
        return [fromItem, toItem];
    }

    if (layout === 'transfer_asset') {
        const absQty = applySign(from.quantity, 'positive');
        const fromItem: Record<string, unknown> = {
            broker_id: from.broker_id,
            type: 'TRANSFER',
            date: from.date,
            quantity: applySign(from.quantity, 'negative'),
            link_uuid: linkUuid,
        };
        const toItem: Record<string, unknown> = {
            broker_id: to.broker_id,
            type: 'TRANSFER',
            date: to.date || from.date,
            quantity: absQty,
            link_uuid: linkUuid,
        };
        if (from.asset_id != null) {
            fromItem.asset_id = from.asset_id;
            toItem.asset_id = from.asset_id;
        }
        // WAC: for auto mode, send mode + currency hint override (or null for backend-decides)
        if (from.cost_basis_mode === 'auto') {
            toItem.cost_basis_mode = 'auto';
            // Pass through the currency hint sentinel ({code, amount:"0"}) if present
            toItem.cost_basis_override = from.cost_basis_override ?? null;
        } else if (from.cost_basis_override && (from.cost_basis_override as CashValue).amount?.trim()) {
            toItem.cost_basis_override = from.cost_basis_override;
        } else if (to.cost_basis_override && to.cost_basis_override.amount?.trim()) {
            toItem.cost_basis_override = to.cost_basis_override;
        }
        if (sharedTags) {
            fromItem.tags = sharedTags;
            toItem.tags = sharedTags;
        }
        if (sharedDesc) {
            fromItem.description = sharedDesc;
            toItem.description = sharedDesc;
        }
        return [fromItem, toItem];
    }

    // layout === 'transfer_cash'
    const absAmount = from.cash?.amount ? applySign(from.cash.amount, 'positive') : '0';
    const cashCode = from.cash?.code ?? '';
    const fromItem: Record<string, unknown> = {
        broker_id: from.broker_id,
        type: 'CASH_TRANSFER',
        date: from.date,
        quantity: '0',
        cash: {code: cashCode, amount: applySign(absAmount, 'negative')},
        link_uuid: linkUuid,
    };
    const toItem: Record<string, unknown> = {
        broker_id: to.broker_id,
        type: 'CASH_TRANSFER',
        date: to.date || from.date,
        quantity: '0',
        cash: {code: cashCode, amount: absAmount},
        link_uuid: linkUuid,
    };
    if (sharedTags) {
        fromItem.tags = sharedTags;
        toItem.tags = sharedTags;
    }
    if (sharedDesc) {
        fromItem.description = sharedDesc;
        toItem.description = sharedDesc;
    }
    return [fromItem, toItem];
}

// =============================================================================
//  Batch payload assembly — pure aggregation of resolved ops
// =============================================================================

/** A single resolved CUD operation — result of iterating PendingOps and diffing. */
export interface ResolvedOp {
    intent: 'create' | 'update' | 'delete';
    /** CREATE or UPDATE payload (Record with fields to send). */
    payload?: Record<string, unknown>;
    /** For delete: the transaction ID to delete. */
    deleteId?: number;
    /** Partner CREATE/UPDATE payload (for paired dual-form edits/creates). */
    partnerPayload?: Record<string, unknown> | null;
    /** Partner ID to delete (for paired deletes). */
    partnerDeleteId?: number | null;
}

/**
 * Assemble the final batch API payload from resolved CUD ops + atomic commands.
 *
 * Splits/promotes are first-class inputs because they affect how edits are resolved
 * (split-queued rows have type stripped, promote-queued rows are skipped).
 * The resolveOps() caller has already applied these rules — this function just assembles.
 *
 * Omits empty arrays from the output (e.g. no `creates` key if none exist).
 */
export function buildBatchPayload(input: {ops: ResolvedOp[]; splits?: {id_a: number; id_b: number}[]; promotes?: Record<string, unknown>[]}): Record<string, unknown> {
    const creates: Record<string, unknown>[] = [];
    const updates: Record<string, unknown>[] = [];
    const deletes: number[] = [];

    for (const op of input.ops) {
        if (op.intent === 'create') {
            if (op.payload) creates.push(op.payload);
            if (op.partnerPayload) creates.push(op.partnerPayload);
        } else if (op.intent === 'update') {
            if (op.payload) updates.push(op.payload);
            if (op.partnerPayload) updates.push(op.partnerPayload);
        } else if (op.intent === 'delete') {
            if (op.deleteId != null) deletes.push(op.deleteId);
            if (op.partnerDeleteId != null) deletes.push(op.partnerDeleteId);
        }
    }

    const out: Record<string, unknown> = {};
    if (creates.length > 0) out.creates = creates;
    if (updates.length > 0) out.updates = updates;
    if (deletes.length > 0) out.deletes = deletes;
    if (input.splits && input.splits.length > 0) out.splits = input.splits;
    if (input.promotes && input.promotes.length > 0) out.promotes = input.promotes;
    return out;
}

/**
 * Post-process a batch payload for validate: upgrade cost_basis_mode 'auto' → 'auto-detail'
 * so the backend includes qualifying_txs + asset_price in the response.
 * Mutates the payload in-place (safe — the object is local to the validate call).
 * Must NOT be called on commit payloads (commit doesn't need details).
 */
export function upgradeAutoToDetail(payload: Record<string, unknown>): void {
    const arrays = ['creates', 'updates'] as const;
    for (const key of arrays) {
        const items = payload[key] as Record<string, unknown>[] | undefined;
        if (!items) continue;
        for (const item of items) {
            if (item.cost_basis_mode === 'auto') {
                item.cost_basis_mode = 'auto-detail';
            }
        }
    }
}
