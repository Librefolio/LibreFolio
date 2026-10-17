/**
 * currencyChangeErrors.ts — The refusals of the wipes that delete an asset's events, as one sentence in the interface
 * language: the currency change's market-data wipe (X-R48) and a parametric provider's change (X-R49, the asset modal).
 *
 * X-R48: `POST /assets/{id}/market-data/wipe` deletes every event of the asset, so it refuses while a SPLIT of the asset
 * has linked incoming adjustments without a purchase cost: with the split gone, those units would count as bought at an
 * unknown price. The answer is a 409 `MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST`, whose `params.splits` lists each such
 * split by date with the adjustments the user can see (`transaction_ids`) and the others (`hidden_transactions_count`).
 * Every other refusal of the wipe keeps the modal's generic sentence.
 *
 * X-R49: `POST /assets/provider` refuses the same way, `PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST`, when a parametric
 * provider's new parameters (or leaving it) would delete such a split it generated; the values are the same.
 */

type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

/** The refusals this module says, by code: their sentence's key. Own keys only: a prototype name is no code. */
const SENTENCE_KEYS: Readonly<Record<string, string>> = {
    MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST: 'assetDetail.currencyChange.splitAdjustmentsWithoutCost',
    PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST: 'assets.modal.planSplitAdjustmentsWithoutCost',
};

function asRecord(value: unknown): Record<string, unknown> | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function count(value: unknown): number {
    const n = Number(value);
    return Number.isInteger(n) && n > 0 ? n : 0;
}

/** The sentence for a refused wipe this module knows, or `null` for any other error (the caller keeps its generic one). */
export function wipeRefusalMessage(err: unknown, t: Translate, dateLabel: (iso: string) => string = (iso) => iso): string | null {
    const refusal = asRecord(asRecord(asRecord(asRecord(err)?.response)?.data)?.detail);
    const code = refusal?.error_code;
    if (refusal === null || typeof code !== 'string' || !Object.prototype.hasOwnProperty.call(SENTENCE_KEYS, code)) return null;
    const listed = asRecord(refusal.params)?.splits;
    const splits = Array.isArray(listed) ? listed : [];
    const first = asRecord(splits[0]) ?? {};
    const visible = Array.isArray(first.transaction_ids) ? first.transaction_ids.length : 0;
    const hidden = count(first.hidden_transactions_count);
    const date = typeof first.date === 'string' ? first.date : '';
    return t(SENTENCE_KEYS[code], {
        values: {date: date ? dateLabel(date) : '', n: visible + hidden, hidden, more: Math.max(splits.length - 1, 0)},
    });
}
