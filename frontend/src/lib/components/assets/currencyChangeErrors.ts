/**
 * currencyChangeErrors.ts — The refusals of the changes that delete an asset's events, as one sentence in the interface
 * language: a change or removal of a provider (X-R49, X5-1, the asset modal).
 *
 * X-R49: `POST /assets/provider` refuses with a 409 `PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST` when a parametric
 * provider's new parameters (or leaving it) would delete a split it generated that has linked incoming adjustments without a
 * purchase cost: with the split gone, those units would count as bought at an unknown price. `params.splits` lists each such
 * split by date with the adjustments the user can see (`transaction_ids`) and the others (`hidden_transactions_count`).
 *
 * X5-1: `DELETE /assets/provider` («No provider» in the asset modal) refuses with that same code and the same `params.splits`
 * when the events it deletes include such a split; any other linked transaction is disconnected, after the dialog that
 * counts them (`providerImpact.ts`), so the old removal refusal (X-R62, `PROVIDER_REMOVAL_LINKED_TRANSACTIONS`) is gone.
 * `PROVIDER_REMOVAL_CONFLICT`, a link made meanwhile, has a sentence of its own that names nothing.
 *
 * N68: the currency change's market-data wipe (X-R48, `MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST`) no longer refuses: it keeps
 * the SPLIT events and the transactions linked to them, so its sentence is gone and the code is unknown here. Every other
 * refusal keeps the caller's generic sentence.
 */

type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

/** The refusals this module says, by code: their sentence's key. Own keys only: a prototype name is no code. */
const SENTENCE_KEYS: Readonly<Record<string, string>> = {
    PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST: 'assets.modal.planSplitAdjustmentsWithoutCost',
    PROVIDER_REMOVAL_CONFLICT: 'assets.modal.providerRemovalConflict',
};

/** X-R62: the refusal whose sentence names nothing. */
const CONFLICT_CODE = 'PROVIDER_REMOVAL_CONFLICT';

function asRecord(value: unknown): Record<string, unknown> | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function count(value: unknown): number {
    const n = Number(value);
    return Number.isInteger(n) && n > 0 ? n : 0;
}

/** The sentence for a refused provider change this module knows, or `null` for any other error (the caller keeps its generic one). */
export function wipeRefusalMessage(err: unknown, t: Translate, dateLabel: (iso: string) => string = (iso) => iso): string | null {
    const refusal = asRecord(asRecord(asRecord(asRecord(err)?.response)?.data)?.detail);
    const code = refusal?.error_code;
    if (refusal === null || typeof code !== 'string' || !Object.prototype.hasOwnProperty.call(SENTENCE_KEYS, code)) return null;
    if (code === CONFLICT_CODE) return t(SENTENCE_KEYS[code]);
    const listed = asRecord(refusal.params)?.splits;
    const items = Array.isArray(listed) ? listed : [];
    const first = asRecord(items[0]) ?? {};
    const visible = Array.isArray(first.transaction_ids) ? first.transaction_ids.length : 0;
    const hidden = count(first.hidden_transactions_count);
    const date = typeof first.date === 'string' ? first.date : '';
    const values: Record<string, string | number> = {date: date ? dateLabel(date) : '', n: visible + hidden, hidden, more: Math.max(items.length - 1, 0)};
    return t(SENTENCE_KEYS[code], {values});
}
