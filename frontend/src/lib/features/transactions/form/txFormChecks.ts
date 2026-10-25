/**
 * txFormChecks.ts — the pre-check behind «⚡ Validate now» (V-37b).
 *
 * Pure: a snapshot of the form in, the list of cells that are wrong out. No server, no component state.
 * Phase 1 looks for what is missing (the required fields); phase 2 looks at the format of what is there.
 * A cell has at most one entry — a missing value wins over a format complaint about the same cell.
 * The order of the list is by phase; «the first cell» on screen is a question for the DOM (`[data-cell-invalid]`).
 */
import type {PairFormLayout, TypeRule} from '$lib/features/transactions/transactionTypeStore';
import {computeSignHint} from '$lib/features/transactions/form/signHintColor';
import {decimalDigitCounts, exceedsSignificantDigits, normalizeDecimalInput, REAL_SIGNIFICANT_DIGITS} from '$lib/utils/core/parseDecimalInput';

export type TxFormCell = 'date' | 'dateTo' | 'quantity' | 'cash' | 'cashTo' | 'asset' | 'broker' | 'brokerTo';
export type TxFormCheckKind = 'required' | 'format';
export type TxFormCheckReason = 'missing' | 'zero' | 'invalid_date' | 'invalid_quantity' | 'wrong_sign' | 'too_many_digits' | 'same_currency' | 'same_broker';

export interface TxFormCheck {
    cell: TxFormCell;
    kind: TxFormCheckKind;
    reason: TxFormCheckReason;
}

export interface TxFormCheckInput {
    pairLayout: PairFormLayout | null;
    rule: Pick<TypeRule, 'assetField' | 'cashField' | 'quantityMode' | 'cashSign'>;
    draft: {
        date: string;
        broker_id: number;
        asset_id: number | null;
        quantity: string;
        cash: {code: string; amount: string} | null;
    };
    /** The «To» side of a pair (`effectiveDualTo`); `null` for a single transaction. */
    dualTo: {broker_id: number; date: string; cash: {code: string; amount: string} | null} | null;
    /** What the inputs themselves report: a typed date the picker refused, a quantity its input refuses. */
    dateValid: boolean;
    dateToValid: boolean;
    quantityValid: boolean;
}

type Cash = {code: string; amount: string} | null | undefined;

/** A zero in any form (`0`, `0.00`, `-0`), read exactly — the same reading as `isDraftReadyForValidation` (B-47). */
function isZeroText(amount: string): boolean {
    return decimalDigitCounts(normalizeDecimalInput(amount))?.stripped === '0';
}

/** What is wrong with a required cash amount, or `null` when it is there and not zero. */
function cashRequiredReason(cash: Cash): 'missing' | 'zero' | null {
    if (!cash?.amount || cash.amount.trim() === '') return 'missing';
    return isZeroText(cash.amount) ? 'zero' : null;
}

/** The FX legs need a currency and an amount that is a finite number other than zero. */
function fxLegReason(cash: Cash): 'missing' | 'zero' | null {
    if (!cash?.code.trim() || !cash.amount.trim()) return 'missing';
    const amount = Number(cash.amount);
    if (!Number.isFinite(amount)) return 'missing';
    return amount === 0 ? 'zero' : null;
}

/** The cells to mark, required first, then format. Empty when the form can go to the server. */
export function computeTxFormChecks(input: TxFormCheckInput): TxFormCheck[] {
    const {pairLayout, rule, draft, dualTo, dateValid, dateToValid, quantityValid} = input;
    const required: TxFormCheck[] = [];
    const format: TxFormCheck[] = [];
    const flagged = new Set<TxFormCell>();
    const add = (list: TxFormCheck[], cell: TxFormCell, kind: TxFormCheckKind, reason: TxFormCheckReason) => {
        // One entry per cell: the first phase to complain keeps the cell.
        if (flagged.has(cell)) return;
        flagged.add(cell);
        list.push({cell, kind, reason});
    };

    // Phase 1 — required.
    if (!draft.date) add(required, 'date', 'required', 'missing');
    if (!draft.broker_id || draft.broker_id <= 0) add(required, 'broker', 'required', 'missing');
    if (rule.assetField === 'required' && draft.asset_id == null) add(required, 'asset', 'required', 'missing');
    if (rule.cashField === 'required') {
        const reason = cashRequiredReason(draft.cash);
        if (reason) add(required, 'cash', 'required', reason);
    }
    if (rule.quantityMode !== 'forbidden') {
        const q = (draft.quantity ?? '').trim();
        if (q === '') add(required, 'quantity', 'required', 'missing');
        else if (Number(q) === 0) add(required, 'quantity', 'required', 'zero');
    }
    if (pairLayout != null && dualTo) {
        if (!dualTo.date) add(required, 'dateTo', 'required', 'missing');
        if (pairLayout !== 'fx' && (!dualTo.broker_id || dualTo.broker_id <= 0)) add(required, 'brokerTo', 'required', 'missing');
        if (pairLayout === 'fx') {
            const from = fxLegReason(draft.cash);
            if (from) add(required, 'cash', 'required', from);
            const to = fxLegReason(dualTo.cash);
            if (to) add(required, 'cashTo', 'required', to);
        }
    }

    // Phase 2 — format.
    if (!dateValid) add(format, 'date', 'format', 'invalid_date');
    if (pairLayout != null && !dateToValid) add(format, 'dateTo', 'format', 'invalid_date');
    if (rule.quantityMode !== 'forbidden' && !quantityValid) add(format, 'quantity', 'format', 'invalid_quantity');
    // Pairs take positive amounts (the flip negates the From side); a single transaction follows its type's sign rule.
    const cashRule = pairLayout != null ? 'positive' : rule.cashSign;
    if (computeSignHint(parseFloat(draft.cash?.amount ?? '0'), cashRule).bad) add(format, 'cash', 'format', 'wrong_sign');
    if (exceedsSignificantDigits(draft.cash?.amount, REAL_SIGNIFICANT_DIGITS)) add(format, 'cash', 'format', 'too_many_digits');
    if (pairLayout === 'fx' && dualTo) {
        if (computeSignHint(parseFloat(dualTo.cash?.amount ?? '0'), 'positive').bad) add(format, 'cashTo', 'format', 'wrong_sign');
        if (exceedsSignificantDigits(dualTo.cash?.amount, REAL_SIGNIFICANT_DIGITS)) add(format, 'cashTo', 'format', 'too_many_digits');
        const fromCode = draft.cash?.code ?? '';
        const toCode = dualTo.cash?.code ?? '';
        if (fromCode && toCode && fromCode === toCode) add(format, 'cashTo', 'format', 'same_currency');
    } else if (pairLayout != null && dualTo && draft.broker_id && dualTo.broker_id && draft.broker_id === dualTo.broker_id) {
        add(format, 'brokerTo', 'format', 'same_broker');
    }

    return [...required, ...format];
}
