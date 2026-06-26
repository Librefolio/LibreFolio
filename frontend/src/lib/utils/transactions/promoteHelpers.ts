/**
 * Promote helpers — pure utility functions for CASH_TRANSFER promote suggestions.
 *
 * Extracted from TransactionBulkModal.svelte so these can be unit-tested
 * without a Svelte component context.
 */

/** Minimal shape required by cashAmountsCancel (subset of PendingOp). */
export interface CashCancelable {
    fields: {cash: {amount: string} | null};
}

/**
 * Return true only when the two ops have cash amounts that are exactly
 * opposite (sum = 0). Required for CASH_TRANSFER promote suggestions —
 * prevents false positives between unrelated transactions that only share
 * type and date proximity but have different amounts.
 *
 * Uses floating-point epsilon relative to the larger absolute value to
 * handle decimal strings that lose precision when parsed as Number.
 */
export function cashAmountsCancel(a: CashCancelable, b: CashCancelable): boolean {
    if (!a.fields.cash || !b.fields.cash) return false;
    const numA = Number(a.fields.cash.amount);
    const numB = Number(b.fields.cash.amount);
    const maxAbs = Math.max(Math.abs(numA), Math.abs(numB));
    if (maxAbs === 0) return false;
    // Exact cancellation: sum must be 0 within floating-point epsilon
    return Math.abs(numA + numB) / maxAbs < 1e-9;
}
