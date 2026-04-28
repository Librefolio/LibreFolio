/**
 * Transaction Type Rules — UI gating tables for per-type field visibility/sign hints.
 *
 * **NOT** a duplicate of backend validation. The authoritative validator is
 * `POST /transactions/validate` (see `backend/app/schemas/transactions.py
 * → TXCreateItem.validate_transaction_rules`). This module only powers the
 * frontend UI: which fields to show/hide, which sign hint to display, whether
 * a type requires the pair-wizard instead of the bulk modal.
 *
 * Source-of-truth mapping is derived from the 9 backend rules:
 *  Rule 1: TRANSFER + FX_CONVERSION require link_uuid           → requiresPair
 *  Rule 2: TRANSFER  → asset_id required, qty != 0, no cash
 *  Rule 3: FX_CONVERSION → no asset, qty = 0, cash != 0
 *  Rule 4: DEPOSIT/WITHDRAWAL → no asset
 *  Rule 5: BUY/SELL/DIVIDEND/TRANSFER/ADJUSTMENT → asset required
 *  Rule 6: INTEREST/FEE/TAX → asset optional
 *  Rule 7: cash required for everything except TRANSFER + ADJUSTMENT
 *  Rule 8: ADJUSTMENT → no cash
 *  Rule 9: asset_event_id only for DIVIDEND/INTEREST/ADJUSTMENT (eventLinkable)
 *
 * @module utils/transactionTypeRules
 */

import {TX_TYPES, type TransactionTypeCode} from './transactionTypes';

export type FieldGating = 'required' | 'optional' | 'forbidden';
export type QuantityRule = 'positive' | 'negative' | 'zero' | 'nonzero' | 'any';
export type CashSign = 'positive' | 'negative' | 'either' | 'none';

export interface TypeRule {
    /** Whether the asset_id field must/may/cannot be set. */
    assetField: FieldGating;
    /** Whether the cash field must/may/cannot be set. */
    cashField: FieldGating;
    /** Constraint on quantity sign (UI hint only). */
    quantityRule: QuantityRule;
    /** Suggested sign for the cash amount (UI hint only). */
    cashSign: CashSign;
    /** True for DIVIDEND/INTEREST/ADJUSTMENT — only these may link an asset_event_id. */
    eventLinkable: boolean;
    /** True for TRANSFER/FX_CONVERSION — must be created via the promote wizard, not the bulk modal. */
    requiresPair: boolean;
}

/**
 * Per-type UI rules. Keep in sync with backend `validate_transaction_rules`
 * whenever rules change there. Tested via `transactionTypeRules.test.ts` for
 * completeness against `TX_TYPES`.
 */
export const TX_TYPE_RULES: Record<TransactionTypeCode, TypeRule> = {
    BUY: {assetField: 'required', cashField: 'required', quantityRule: 'positive', cashSign: 'negative', eventLinkable: false, requiresPair: false},
    SELL: {assetField: 'required', cashField: 'required', quantityRule: 'negative', cashSign: 'positive', eventLinkable: false, requiresPair: false},
    DIVIDEND: {assetField: 'required', cashField: 'required', quantityRule: 'zero', cashSign: 'positive', eventLinkable: true, requiresPair: false},
    INTEREST: {assetField: 'optional', cashField: 'required', quantityRule: 'zero', cashSign: 'positive', eventLinkable: true, requiresPair: false},
    DEPOSIT: {assetField: 'forbidden', cashField: 'required', quantityRule: 'zero', cashSign: 'positive', eventLinkable: false, requiresPair: false},
    WITHDRAWAL: {assetField: 'forbidden', cashField: 'required', quantityRule: 'zero', cashSign: 'negative', eventLinkable: false, requiresPair: false},
    FEE: {assetField: 'optional', cashField: 'required', quantityRule: 'zero', cashSign: 'negative', eventLinkable: false, requiresPair: false},
    TAX: {assetField: 'optional', cashField: 'required', quantityRule: 'zero', cashSign: 'negative', eventLinkable: false, requiresPair: false},
    TRANSFER: {assetField: 'required', cashField: 'forbidden', quantityRule: 'nonzero', cashSign: 'none', eventLinkable: false, requiresPair: true},
    FX_CONVERSION: {assetField: 'forbidden', cashField: 'required', quantityRule: 'zero', cashSign: 'either', eventLinkable: false, requiresPair: true},
    ADJUSTMENT: {assetField: 'required', cashField: 'forbidden', quantityRule: 'nonzero', cashSign: 'none', eventLinkable: true, requiresPair: false},
};

/** Safe lookup with a permissive fallback for unknown / null types. */
export function getTypeRule(type: string | null | undefined): TypeRule {
    const rule = TX_TYPE_RULES[(type ?? '') as TransactionTypeCode];
    return rule ?? FALLBACK_RULE;
}

const FALLBACK_RULE: TypeRule = {
    assetField: 'optional',
    cashField: 'optional',
    quantityRule: 'any',
    cashSign: 'either',
    eventLinkable: false,
    requiresPair: false,
};

/** Types that are NOT pair-only — i.e. selectable in the bulk modal type dropdown. */
export const STANDALONE_TX_TYPES: TransactionTypeCode[] = TX_TYPES.filter((t) => !TX_TYPE_RULES[t].requiresPair);

/** Pair-only types — created exclusively through the promote wizard. */
export const PAIR_TX_TYPES: TransactionTypeCode[] = TX_TYPES.filter((t) => TX_TYPE_RULES[t].requiresPair);

/** Types that may link to an AssetEvent. */
export const EVENT_LINKABLE_TYPES: TransactionTypeCode[] = TX_TYPES.filter((t) => TX_TYPE_RULES[t].eventLinkable);

// =============================================================================
// READINESS CHECK — gate auto-validation in modals (Bugfix-2 §C5)
// =============================================================================

/**
 * Minimal shape consumed by `isDraftReadyForValidation`. Both
 * `TransactionFormModal.FormDraft` and `TransactionBulkModal.DraftRow` satisfy
 * this contract.
 */
export interface ValidatableDraft {
    type: string;
    broker_id: number;
    asset_id?: number | null;
    quantity?: string | null;
    cash?: {code: string; amount: string} | null;
}

/**
 * True when the required fields for the draft's type are populated. Used to
 * gate the **auto** triggers (`change` debounce + `idle` 60s) of
 * `useValidateScheduler`, so the user doesn't see "BUY requires asset_id" right
 * after `+ Add` on an empty row. The **manual** Validate button always fires.
 *
 * Rules (mirror UI gating, not backend semantics):
 *   - `broker_id` must be > 0 (a real broker, not the "0 = unset" sentinel).
 *   - If `assetField === 'required'` → `asset_id != null`.
 *   - If `cashField === 'required'`  → `cash.amount` is a non-empty string.
 *   - If `quantityRule === 'positive'|'negative'|'nonzero'` → `quantity != 0/empty`.
 *
 * Optional fields (`assetField === 'optional'`, etc.) are NOT required to be
 * populated — they're, well, optional.
 */
export function isDraftReadyForValidation(d: ValidatableDraft): boolean {
    if (!d.broker_id || d.broker_id <= 0) return false;
    const r = getTypeRule(d.type);
    if (r.assetField === 'required' && d.asset_id == null) return false;
    if (r.cashField === 'required' && (!d.cash || !d.cash.amount || d.cash.amount.trim() === '' || d.cash.amount === '0')) return false;
    if (r.quantityRule !== 'zero' && r.quantityRule !== 'any') {
        const q = (d.quantity ?? '').trim();
        if (q === '' || Number(q) === 0) return false;
    }
    return true;
}

