/**
 * bulkRefusal.ts — A bulk request the backend refused as too large, as one sentence in the interface language (X-R58).
 *
 * `POST /assets/prices/query` and `POST /fx/currencies/convert` refuse more than `MAX_BULK_ITEMS` items, or more daily
 * values than `MAX_BULK_ITEM_DAYS`, with a 422 whose `detail` carries a code and its numbers (Z-25):
 * `bulk_too_many_items` (`max_items`, `items`) or `bulk_too_many_days` (`max_item_days`, `item_days`; for the
 * conversions a lower bound, so the sentence does not show it). The lists send those requests in batches under the caps
 * (`sendBulkBatches`, Z-27), so a refusal is rare; when one still comes back, the list says it instead of leaving its
 * cards without values. Any other error is not this module's: `null`.
 */

type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

function asRecord(value: unknown): Record<string, unknown> | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function finite(value: unknown): value is number {
    return typeof value === 'number' && Number.isFinite(value);
}

/** The sentence for a bulk request the backend refused as too large, or `null` for any other error. */
export function bulkRefusalMessage(error: unknown, t: Translate): string | null {
    const response = asRecord(asRecord(error)?.response);
    if (response?.status !== 422) return null;
    const detail = asRecord(asRecord(response.data)?.detail);
    if (detail === null) return null;
    const {code, max_items: maxItems, items, max_item_days: maxItemDays, item_days: itemDays} = detail;
    if (code === 'bulk_too_many_items' && finite(maxItems) && maxItems > 0 && finite(items)) {
        return t('common.bulkRefusal.tooManyItems', {values: {max: maxItems, count: items}});
    }
    if (code === 'bulk_too_many_days' && finite(maxItemDays) && maxItemDays > 0 && finite(itemDays)) {
        return t('common.bulkRefusal.tooManyDays', {values: {max: maxItemDays}});
    }
    return null;
}
