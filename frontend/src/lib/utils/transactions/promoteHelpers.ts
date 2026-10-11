/**
 * Promote helpers — pure utility functions for CASH_TRANSFER promote suggestions.
 *
 * Extracted from TransactionBulkModal.svelte so these can be unit-tested
 * without a Svelte component context.
 */

import {applySign, buildSignedCash, exactDecimalEqual, exactDecimalSign, type CashValue} from './txPayloadHelpers';
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
 * Both sides first take the sign their type implies (`buildSignedCash`, the canonicalisation
 * `signedCashAmount` applies too), so the answer is the same whether a row came from the import
 * pool (already signed) or from the database (normalised to a magnitude by the edit form).
 * Comparing the stored strings instead made a DEPOSIT of +11 and a WITHDRAWAL of -11 read as
 * +11 and +11: the pairing worked during an import and never worked between two saved
 * transactions.
 *
 * `resolveRule` is a required parameter on purpose: a caller that does not have the type
 * cannot ask this question correctly, and should not be able to ask it at all.
 *
 * The comparison is exact decimal arithmetic on the strings, as the backend's is and as
 * `assetQuantitiesCancel` does for quantities. The former floating-point tolerance (relative,
 * 1e-9) let a one-cent difference through above about 10 million: the editor proposed a pair
 * the backend then refused.
 */
export function cashAmountsCancel(a: CashCancelable, b: CashCancelable, resolveRule: TypeRuleResolver): boolean {
    const signedAmount = (row: CashCancelable) => buildSignedCash(row.fields.cash, resolveRule(row.fields.type).cashSign)?.amount ?? null;
    const amountA = signedAmount(a);
    const amountB = signedAmount(b);
    if (amountA === null || amountB === null) return false;
    const signA = exactDecimalSign(amountA);
    const signB = exactDecimalSign(amountB);
    if (signA === null || signB === null || signA === 0 || signA !== -signB) return false;
    return exactDecimalEqual(applySign(amountA, 'positive'), applySign(amountB, 'positive'));
}

/**
 * Merge two free-text field values (e.g. descriptions) for the promote-merge modal.
 * An empty side yields the other; identical sides collapse to one; otherwise the two are
 * stacked on separate lines so nothing the user wrote is silently dropped.
 */
export function mergeStrings(a: string, b: string): string {
    if (!a) return b;
    if (!b) return a;
    if (a === b) return a;
    return `${a}\n${b}`;
}

/** Union of two tag lists, de-duplicated and order-preserving; nullish lists are treated as empty. */
export function mergeTagSets(a: string[], b: string[]): string[] {
    return [...new Set([...(a ?? []), ...(b ?? [])])];
}
