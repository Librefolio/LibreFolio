/**
 * Pure helpers extracted from LotsAnalysisPanel.svelte.
 *
 * The panel is an orchestrator: it fetches once, then fans the result out to five
 * child components. The parts that are pure functions of their input — unwrapping
 * the generated client's redundant `Optional[List[X]]` union, deciding whether a
 * lot counts as "open-ish", applying the open/closed visibility filter, clamping
 * the quote-base quantity, and gathering every lot touched by a double-clicked
 * event — are lifted here so they can be unit tested without a fetch or a DOM.
 *
 * The async loaders, the rAF/geometry settling and the i18n/labelling stay in the
 * component; none of them is a pure function of its arguments.
 *
 * @module brokers/lots/lotsAnalysisHelpers
 */

/**
 * Unwrap the redundant union the Zodios client emits for every `Optional[List[X]]`
 * response field: `(X[] | null) | (X[] | null)[]` (openapi-zod-client artifact —
 * the API never returns the doubled-array branch). Non-arrays and falsy values
 * become `[]`; a genuine array of arrays is flattened (null inner arrays → `[]`).
 * `T` is always supplied explicitly at the call site.
 */
export function asArray<T>(value: unknown): T[] {
    if (!value || !Array.isArray(value)) return [];
    if (value.length > 0 && Array.isArray(value[0])) {
        return (value as unknown[][]).flatMap((item) => (item ?? []) as T[]);
    }
    return value as T[];
}

/** Same generator artifact as {@link asArray}, for single-object `Optional[X]` fields. */
export function asObject<T>(value: unknown): T | null {
    if (!value) return null;
    return Array.isArray(value) ? ((value[0] ?? null) as T | null) : (value as T);
}

/** The subset of a lot summary needed to decide open-ness. */
export interface LotOpenish {
    open_quantity: string;
    states?: readonly string[] | null;
}

/**
 * Whether a lot is "open-ish": it still holds quantity, or it carries the OPEN
 * state tag (which includes partially-closed lots). Mirrors FifoEngineResult.
 */
export function lotIsOpenish(lot: LotOpenish): boolean {
    return Number.parseFloat(lot.open_quantity) > 0 || (lot.states ?? []).includes('OPEN');
}

/** The open/closed bucket toggle: both true (or both false) means "all lots". */
export interface LotVisibilityFilter {
    open: boolean;
    closed: boolean;
}

/**
 * Filter lots to the visible set per the open/closed toggle. When both buckets
 * agree (both on or both off) every lot is visible; a single bucket narrows to
 * just the open-ish lots or just the closed ones.
 */
export function filterVisibleLots<T extends LotOpenish>(lots: readonly T[], filter: LotVisibilityFilter): T[] {
    const bothSame = filter.open === filter.closed;
    const showOpen = bothSame || filter.open;
    const showClosed = bothSame || filter.closed;
    return lots.filter((lot) => (lotIsOpenish(lot) ? showOpen : showClosed));
}

/**
 * Clamp a raw quote-base quantity to a safe positive multiplier: any non-finite
 * or non-positive input (including a non-numeric string) collapses to `1`, so the
 * price chart never divides by zero or a NaN.
 */
export function normalizeQuoteBaseQuantity(raw: unknown): number {
    const value = Number(raw);
    return Number.isFinite(value) && value > 0 ? value : 1;
}

/** The subset of a timeline event needed to gather everything a double-click touches. */
export interface InvolvedEventRow {
    transaction_id: number;
    // Widened to absorb the generated client's redundant scalar-or-array union; unwrapped to a scalar below.
    related_transaction_id?: number | (number | null)[] | null;
    lot_id: number;
}

/** Reduce the redundant scalar-or-array id union to a single number, or null. */
function toScalarId(value: number | (number | null)[] | null | undefined): number | null {
    const scalar = Array.isArray(value) ? (value[0] ?? null) : value;
    return scalar ?? null;
}

/**
 * Every lot id touched by a double-clicked event: the clicked lot itself, plus
 * every row sharing the same transaction, the clicked event's paired transaction,
 * or a row whose own paired transaction is the clicked one. De-duplicated, with
 * the clicked lot first. (The array arm of the paired-id union never occurs at
 * runtime, but is unwrapped here rather than compared, which is equivalent for
 * the scalar data the API returns.)
 */
export function collectInvolvedLotIds(events: readonly InvolvedEventRow[], clicked: InvolvedEventRow): number[] {
    const txId = clicked.transaction_id;
    const relatedId = toScalarId(clicked.related_transaction_id);
    const involved = events.filter((row) => {
        const rowRelated = toScalarId(row.related_transaction_id);
        return row.transaction_id === txId || (relatedId != null && row.transaction_id === relatedId) || (rowRelated != null && rowRelated === txId);
    });
    return Array.from(new Set<number>([clicked.lot_id, ...involved.map((row) => row.lot_id)]));
}
