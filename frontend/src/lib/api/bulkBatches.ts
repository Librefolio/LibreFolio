/**
 * Bulk requests split into batches under the backend's caps (lot Z-27, decisions D1–D4 of 17/10).
 *
 * `POST /assets/prices/query` and `POST /fx/currencies/convert` refuse more than 1,000 items and more than 1 million
 * item-days in one request (lot Z-25, the budget lowered by R13-SEC9-2: `MAX_BULK_ITEMS` and `MAX_BULK_ITEM_DAYS` in
 * `backend/app/utils/date_range_limits.py`, a 422 `bulk_too_many_items` or `bulk_too_many_days`). A list page sends one
 * item per asset or pair, so a large instance would be refused. `sendBulkBatches` plans the batches from an estimate of
 * each item's days, under the caps with a margin (D1), sends them one after the other (D2: production runs one backend
 * process), and splits again a batch the backend still refuses for its days. The caller applies the answers once every
 * batch has settled (D3). With every input under the caps there is a single batch: the single request of before.
 */
import {addDays, daysBetween} from '$lib/utils/dateOnly';

/** The backend's `MAX_BULK_ITEMS`: the most items one bulk request may hold. */
export const BULK_MAX_ITEMS = 1_000;
/** 80 % of the backend's `MAX_BULK_ITEM_DAYS` (1,000,000): the estimate is a guess, and the margin absorbs it (D1). */
export const BULK_ITEM_DAYS_BUDGET = 800_000;
/** The days a signal's warm-up is guessed to add to an item; only the backend knows the real figure. */
export const BULK_SIGNAL_MARGIN_DAYS = 400;
/** How many levels of splitting a batch refused for its days may go through. */
export const BULK_SPLIT_MAX_DEPTH = 4;
/** The backend's 100-year span (`RANGE_SPAN_LIMIT_DAYS`, lot X-R55): no range reaches further back from its end. */
export const BULK_RANGE_SPAN_DAYS = 36_525;

/** The days a range covers once the backend cuts it: at tomorrow, and 100 years back from its end; 0 when empty. */
export function bulkRangeDays(start: string, end: string | null | undefined, today: string): number {
    const ceiling = addDays(today, 1);
    const requestedEnd = end ?? start;
    const cutEnd = requestedEnd > ceiling ? ceiling : requestedEnd;
    const floor = addDays(cutEnd, -(BULK_RANGE_SPAN_DAYS - 1));
    const cutStart = start < floor ? floor : start;
    return Math.max(0, daysBetween(cutStart, cutEnd) + 1);
}

/** Consecutive items of one request; `offset` is the index of its first item in the original list. */
export interface BulkBatch<T> {
    readonly items: readonly T[];
    readonly offset: number;
}

/** The caps a plan stays under; the defaults are `BULK_MAX_ITEMS` and `BULK_ITEM_DAYS_BUDGET`. */
export interface BulkLimits {
    readonly maxItems?: number;
    readonly maxItemDays?: number;
}

/**
 * The batches of `items`, consecutive and in order: an item joins the current batch unless that would pass the item
 * cap or the day budget, and one whose estimate alone passes the budget gets a batch of its own. One batch when
 * everything fits.
 */
export function planBulkBatches<T>(items: readonly T[], estimateDays: (item: T) => number, limits: BulkLimits = {}): BulkBatch<T>[] {
    const maxItems = limits.maxItems ?? BULK_MAX_ITEMS;
    const maxItemDays = limits.maxItemDays ?? BULK_ITEM_DAYS_BUDGET;
    const batches: BulkBatch<T>[] = [];
    let current: T[] = [];
    let offset = 0;
    let days = 0;
    items.forEach((item, index) => {
        const estimate = estimateDays(item);
        const itemDays = Number.isFinite(estimate) ? Math.max(0, estimate) : 0;
        if (current.length > 0 && (current.length >= maxItems || days + itemDays > maxItemDays)) {
            batches.push({items: current, offset});
            current = [];
            offset = index;
            days = 0;
        }
        current.push(item);
        days += itemDays;
    });
    if (current.length > 0) batches.push({items: current, offset});
    return batches;
}

/** The numbers of a 422 `bulk_too_many_days` refusal (lot Z-25). */
export interface BulkDaysRefusal {
    readonly itemDays: number;
    readonly maxItemDays: number;
}

/** The numbers of a `bulk_too_many_days` 422 carried by an axios error, or null for any other error. */
export function bulkTooManyDaysOf(error: unknown): BulkDaysRefusal | null {
    const response = (error as {response?: {status?: unknown; data?: unknown}} | null | undefined)?.response;
    if (!response || response.status !== 422) return null;
    const detail = (response.data as {detail?: unknown} | null | undefined)?.detail;
    if (!detail || typeof detail !== 'object') return null;
    const {code, item_days: itemDays, max_item_days: maxItemDays} = detail as {code?: unknown; item_days?: unknown; max_item_days?: unknown};
    if (code !== 'bulk_too_many_days' || typeof itemDays !== 'number' || typeof maxItemDays !== 'number' || !(maxItemDays > 0)) return null;
    return {itemDays, maxItemDays};
}

/** One answered request, with the batch it answered: indexes in the answer (a `request_index`) are local to it. */
export interface BulkAnswer<T, R> {
    readonly batch: BulkBatch<T>;
    readonly answer: R;
}

/** Every answer in item order; on a failure, the error and the batch whose request failed (nothing sent after it). */
export interface BulkOutcome<T, R> {
    readonly answers: readonly BulkAnswer<T, R>[];
    readonly failed: boolean;
    readonly error?: unknown;
    readonly failedBatch?: BulkBatch<T>;
}

export interface BulkSendOptions extends BulkLimits {
    /** Levels of splitting after `bulk_too_many_days` refusals; `BULK_SPLIT_MAX_DEPTH` by default. */
    readonly maxDepth?: number;
}

function splitBatch<T>(batch: BulkBatch<T>, refusal: BulkDaysRefusal): BulkBatch<T>[] {
    const size = batch.items.length;
    const parts = Math.min(size, Math.max(2, Math.ceil(refusal.itemDays / refusal.maxItemDays) + 1));
    const split: BulkBatch<T>[] = [];
    for (let part = 0; part < parts; part++) {
        const from = Math.floor((part * size) / parts);
        const to = Math.floor(((part + 1) * size) / parts);
        split.push({items: batch.items.slice(from, to), offset: batch.offset + from});
    }
    return split;
}

/**
 * Send `items` in batches, one request at a time, and collect the answers in item order.
 *
 * A batch refused with `bulk_too_many_days` is split into `max(2, ceil(item_days / max_item_days) + 1)` consecutive
 * parts, sent in order, at most `maxDepth` levels deep; a refused batch of one item, or one at the last level, fails.
 * Any other error fails at once. A failure stops the sending: the batches answered before it keep their answers.
 */
export async function sendBulkBatches<T, R>(items: readonly T[], estimateDays: (item: T) => number, send: (items: T[]) => Promise<R>, options: BulkSendOptions = {}): Promise<BulkOutcome<T, R>> {
    const maxDepth = options.maxDepth ?? BULK_SPLIT_MAX_DEPTH;
    const answers: BulkAnswer<T, R>[] = [];
    const pending = planBulkBatches(items, estimateDays, options).map((batch) => ({batch, depth: 0}));
    while (pending.length > 0) {
        const {batch, depth} = pending.shift()!;
        try {
            answers.push({batch, answer: await send([...batch.items])});
        } catch (error) {
            const refusal = bulkTooManyDaysOf(error);
            if (refusal && batch.items.length > 1 && depth < maxDepth) {
                pending.unshift(...splitBatch(batch, refusal).map((part) => ({batch: part, depth: depth + 1})));
                continue;
            }
            return {answers, failed: true, error, failedBatch: batch};
        }
    }
    return {answers, failed: false};
}
