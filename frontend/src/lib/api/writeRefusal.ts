/**
 * writeRefusal.ts — A save the backend refused, whole or in part, as one sentence in the interface language (X-R46).
 *
 * The data editors save prices (`POST /assets/prices`) and rates (`POST /fx/currencies/rate`). The server refuses a
 * whole save with a coded `detail`: 422 `date_out_of_range` (X-R65), 422 `price_currency_mismatch` (X-R71), 422
 * `bulk_too_many_items` (MF-SEC9a: a save's own sentence, not X-R58's reading one), 400 `fx_rates_refused`. Or it writes the save and leaves single dates out, naming
 * them in `rejected` (`{date, reason}`). This module turns both into a sentence that names the dates; any other error
 * falls back to what the server said (`extractErrorMessage`), never to Axios's «Request failed with status code …».
 * Dates stay ISO, as in `eventSaveErrorMessage`, unless the caller passes `dateLabel`.
 */
import {bulkRefusalMessage} from './bulkRefusal';
import {extractErrorMessage} from '$lib/utils/trySave';

type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;
type DateLabel = (iso: string) => string;

/** The reasons the backend gives for a date left out: `FAPriceRejection.reason` and `FXRateRejection.reason`. */
export const REJECTION_REASONS = ['ohlc_inconsistent', 'date_out_of_range', 'value_not_storable', 'rate_not_storable', 'same_currency', 'invalid_rate', 'internal_error'] as const;

/** A date left out of a save, and why. */
export interface Rejection {
    date: string;
    reason: string;
}

/** How many dates a sentence names before «and N more». */
const SHOWN = 5;

const iso: DateLabel = (value) => value;

function asRecord(value: unknown): Record<string, unknown> | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function finite(value: unknown): value is number {
    return typeof value === 'number' && Number.isFinite(value);
}

function texts(value: unknown): string[] {
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function records(value: unknown): Record<string, unknown>[] {
    return Array.isArray(value) ? value.map(asRecord).filter((item): item is Record<string, unknown> => item !== null) : [];
}

/** At most SHOWN labels, then «and N more» for the rest of `total`. */
function listed(labels: string[], total: number, t: Translate): string {
    const shown = labels.slice(0, SHOWN);
    const hidden = Math.max(total - shown.length, 0);
    return hidden > 0 ? `${shown.join(', ')} ${t('common.writeRefusal.more', {values: {n: hidden}})}` : shown.join(', ');
}

function reasonText(reason: string, t: Translate): string {
    return (REJECTION_REASONS as readonly string[]).includes(reason) ? t(`common.writeRefusal.reason.${reason}`) : t('common.writeRefusal.reason.other');
}

function rejectionsOf(value: unknown): Rejection[] {
    return records(value).flatMap(({date, reason}) => (typeof date === 'string' && typeof reason === 'string' ? [{date, reason}] : []));
}

/** The dates of a `date_out_of_range` refusal: a price item lists its `dates`, a rate item has one `date`. */
function outOfRangeDates(items: unknown): string[] {
    return records(items).flatMap((item) => (typeof item.date === 'string' ? [item.date] : texts(item.dates)));
}

/** The sentence for the dates a save left out, or `null` when there are none. */
export function rejectedMessage(rejected: readonly Rejection[], t: Translate, dateLabel: DateLabel = iso): string | null {
    if (rejected.length === 0) return null;
    const items = rejected.map(({date, reason}) => `${dateLabel(date)} (${reasonText(reason, t)})`);
    return t('common.writeRefusal.notSaved', {values: {count: rejected.length, items: listed(items, rejected.length, t)}});
}

/** The sentence for a save the backend refused with a coded `detail`, or `null` for any other error. */
export function writeRefusalMessage(error: unknown, t: Translate, dateLabel: DateLabel = iso): string | null {
    const response = asRecord(asRecord(error)?.response);
    const detail = asRecord(asRecord(response?.data)?.detail);
    if (response === null || detail === null) return null;
    const {code, count} = detail;
    if (response.status === 422 && code === 'bulk_too_many_items') {
        const {max_items: maxItems, items} = detail;
        return finite(maxItems) && maxItems > 0 && finite(items) ? t('common.writeRefusal.tooManyItems', {values: {max: maxItems, count: items}}) : null;
    }
    if (response.status === 422 && code === 'bulk_too_many_days') return bulkRefusalMessage(error, t);
    if (response.status === 422 && code === 'date_out_of_range') {
        const params = asRecord(detail.params);
        const dates = outOfRangeDates(detail.items);
        if (!finite(count) || typeof params?.min !== 'string' || typeof params?.max !== 'string' || dates.length === 0) return null;
        return t('common.writeRefusal.dateOutOfRange', {values: {count, min: dateLabel(params.min), max: dateLabel(params.max), dates: listed(dates.map(dateLabel), count, t)}});
    }
    if (response.status === 422 && code === 'price_currency_mismatch') {
        const items = records(detail.items);
        const expected = items[0]?.expected;
        const found = [...new Set(items.flatMap((item) => texts(item.found)))];
        const dates = items.flatMap((item) => texts(item.dates));
        if (!finite(count) || typeof expected !== 'string' || dates.length === 0) return null;
        return t('common.writeRefusal.currencyMismatch', {values: {count, expected, found: found.join(', '), dates: listed(dates.map(dateLabel), count, t)}});
    }
    if (response.status === 400 && code === 'fx_rates_refused') return rejectedMessage(rejectionsOf(detail.rejected), t, dateLabel);
    return null;
}

/** What to tell the user about a failed save: the refusal's sentence, else what the server said, never Axios's text. */
export function saveErrorText(error: unknown, t: Translate, dateLabel: DateLabel = iso): string {
    return writeRefusalMessage(error, t, dateLabel) ?? extractErrorMessage(error, t('common.unknownError'));
}
