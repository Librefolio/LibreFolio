/**
 * Promote helpers — pure utility functions for CASH_TRANSFER promote suggestions.
 *
 * Extracted from TransactionBulkModal.svelte so these can be unit-tested
 * without a Svelte component context.
 */

import {signedCashAmount, type CashValue} from './txPayloadHelpers';
import type {TypeRule} from '$lib/stores/transactions/transactionTypeStore';

/** Minimal shape required by cashAmountsCancel (subset of PendingOp).
 *  `type` is mandatory: without it the sign of a DB-sourced amount cannot be recovered. */
export interface CashCancelable {
    fields: {type: string; cash: CashValue | null};
}

/** Resolve a transaction type to its rule. Injected rather than imported so these helpers
 *  stay pure — the real resolver reads type rules the backend provides at runtime. */
export type TypeRuleResolver = (type: string) => TypeRule;

/**
 * Return true only when the two ops have cash amounts that are exactly
 * opposite (sum = 0). Required for CASH_TRANSFER promote suggestions —
 * prevents false positives between unrelated transactions that only share
 * type and date proximity but have different amounts.
 *
 * Both sides are canonicalised through `signedCashAmount` first, so the answer is the same
 * whether a row came from the import pool (already signed) or from the database (normalised
 * to a magnitude by the edit form). Comparing the stored strings instead made a DEPOSIT of
 * +11 and a WITHDRAWAL of -11 read as +11 and +11: the pairing worked during an import and
 * never worked between two saved transactions.
 *
 * `resolveRule` is a required parameter on purpose: a caller that does not have the type
 * cannot ask this question correctly, and should not be able to ask it at all.
 *
 * Uses floating-point epsilon relative to the larger absolute value to
 * handle decimal strings that lose precision when parsed as Number.
 */
export function cashAmountsCancel(a: CashCancelable, b: CashCancelable, resolveRule: TypeRuleResolver): boolean {
    const numA = signedCashAmount(a.fields.cash, resolveRule(a.fields.type));
    const numB = signedCashAmount(b.fields.cash, resolveRule(b.fields.type));
    if (numA === null || numB === null) return false;
    const maxAbs = Math.max(Math.abs(numA), Math.abs(numB));
    if (maxAbs === 0) return false;
    // Exact cancellation: sum must be 0 within floating-point epsilon
    return Math.abs(numA + numB) / maxAbs < 1e-9;
}
