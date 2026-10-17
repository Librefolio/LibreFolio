/**
 * The refusals of `POST /assets/events` (decisions 20–23 of release 1.3).
 *
 * A refused save writes nothing, and the server says why and where: `detail = {error_code, message,
 * params}` (400, or 409 for `EVENT_EXISTS`), or a validation list (422) whose `loc` names the event.
 * This module reads them: `existingEvents()` for «+ New event», `eventSaveErrorMessage()` for one
 * sentence in the interface language that names the event at fault.
 */
import {formatExactDecimal} from '$lib/utils/core/formatFixed';

/** An event already on the date and type a create item wanted, as `EVENT_EXISTS` lists it. */
export interface ExistingEvent {
    id: number;
    date: string;
    type: string;
    value: {code: string; amount: string};
    notes: string | null;
    is_auto: boolean;
    linked_transactions: number;
}

/** A structured refusal: the code, the server's English sentence, and where it is. */
export interface EventRefusal {
    status: number;
    code: string;
    message: string;
    params: Record<string, unknown>;
}

/** The event of a request, by position: what a 422 names by index. */
export interface SentEvent {
    date: string;
    type: string;
}

type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

interface ErrorResponse {
    response?: {status?: number; data?: {detail?: unknown}};
    message?: string;
}

function responseOf(err: unknown): ErrorResponse['response'] {
    return (err as ErrorResponse | null)?.response;
}

/** The structured refusal an API error carries, or `null` when it is another error. */
export function eventRefusal(err: unknown): EventRefusal | null {
    const response = responseOf(err);
    const detail = response?.data?.detail;
    if (!detail || typeof detail !== 'object' || Array.isArray(detail)) return null;
    const {error_code: code, message, params} = detail as Record<string, unknown>;
    if (typeof code !== 'string') return null;
    return {
        status: response?.status ?? 0,
        code,
        message: typeof message === 'string' ? message : '',
        params: params && typeof params === 'object' && !Array.isArray(params) ? (params as Record<string, unknown>) : {},
    };
}

/** The events already on the date and type of a create item (`EVENT_EXISTS`), or `null` for any other error. */
export function existingEvents(err: unknown): ExistingEvent[] | null {
    const refusal = eventRefusal(err);
    if (refusal?.code !== 'EVENT_EXISTS') return null;
    const existing = refusal.params.existing;
    return Array.isArray(existing) && existing.length > 0 ? (existing as ExistingEvent[]) : null;
}

function text(value: unknown): string {
    return value === undefined || value === null ? '' : String(value);
}

/**
 * A stored event amount as the form and the panel show it: as written, with at least two decimals — a
 * per-share dividend can need more (`1.500000` → `1.50`, `0.123456` stays, `1` → `1.00`).
 */
export function existingAmountText(amount: string): string {
    const [whole, fraction = ''] = amount.split('.');
    return `${whole}.${fraction.replace(/0+$/, '').padEnd(2, '0')}`;
}

/**
 * One sentence for a refused events save, naming the event at fault. `sent` are the events posted, in
 * order, so that a 422 naming an index can name its date; `typeLabel` gives a type its translated name.
 */
export function eventSaveErrorMessage(err: unknown, t: Translate, sent: SentEvent[] = [], typeLabel: (type: string) => string = (type) => type, dateLabel: (iso: string) => string = (iso) => iso): string {
    const refusal = eventRefusal(err);
    if (refusal) {
        const p = refusal.params;
        switch (refusal.code) {
            case 'EVENT_CURRENCY_MISMATCH': {
                const events = Array.isArray(p.events) ? (p.events as Array<Record<string, unknown>>) : [];
                const first = events[0] ?? {};
                return t('events.saveError.currencyMismatch', {
                    values: {date: dateLabel(text(first.date)), type: typeLabel(text(first.type)), currency: text(first.currency), expected: text(p.expected), more: Math.max(events.length - 1, 0)},
                });
            }
            case 'EVENT_KEY_CONFLICT':
                return t('events.saveError.keyConflict', {values: {date: dateLabel(text(p.date)), type: typeLabel(text(p.type))}});
            case 'EVENT_NOT_EDITABLE':
                return t('events.saveError.notEditable');
            case 'EVENT_NOT_DELETABLE':
                return t('events.saveError.notDeletable');
            case 'EVENT_IN_USE': {
                const events = Array.isArray(p.events) ? (p.events as Array<Record<string, unknown>>) : [];
                const first = events[0] ?? {};
                return t('events.saveError.inUse', {
                    values: {date: dateLabel(text(first.date)), type: typeLabel(text(first.type)), n: Number(first.linked_transactions ?? 0), more: Math.max(events.length - 1, 0)},
                });
            }
            case 'EVENT_ASSET_NOT_FOUND':
                return t('events.saveError.assetNotFound');
            case 'EVENT_TOO_MANY_DIGITS': {
                // C-97a and W-B58: the value of an event keeps 6 decimal places, 15 significant digits and 12 digits before
                // the decimal point; past any of them the server refuses it and rounds nothing.
                const events = Array.isArray(p.events) ? (p.events as Array<Record<string, unknown>>) : [];
                const first = events[0] ?? {};
                return t('events.saveError.tooManyDigits', {
                    values: {
                        date: dateLabel(text(first.date)),
                        type: typeLabel(text(first.type)),
                        max: text(p.max_decimal_places),
                        significant: text(p.max_significant_digits),
                        integer: text(p.max_integer_digits),
                        more: Math.max(events.length - 1, 0),
                    },
                });
            }
            case 'EVENT_INVALID_SPLIT_RATIO': {
                // X-R47: a split's ratio is its value, a number above 0; the server refuses any other, naming each split.
                // The ratio comes as the request sent it, a decimal string: written the way the interface writes numbers.
                const events = Array.isArray(p.events) ? (p.events as Array<Record<string, unknown>>) : [];
                const first = events[0] ?? {};
                return t('events.saveError.invalidSplitRatio', {
                    values: {date: dateLabel(text(first.date)), type: typeLabel(text(first.type)), ratio: formatExactDecimal(text(first.ratio)), more: Math.max(events.length - 1, 0)},
                });
            }
            case 'EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST': {
                // P-10 (decision 27): a split is retyped while linked incoming adjustments have no purchase cost. The params
                // name the ones the caller can see and count the others (R13-SEC7, X-R47b): the sentence counts them all.
                const raw = p.hidden_transactions_count;
                const hidden = typeof raw === 'number' && Number.isInteger(raw) && raw >= 0 ? raw : 0;
                const visible = Array.isArray(p.transaction_ids) ? p.transaction_ids.length : 0;
                return t('events.saveError.splitAdjustmentsWithoutCost', {values: {date: dateLabel(text(p.date)), type: typeLabel('SPLIT'), n: visible + hidden, hidden}});
            }
        }
        return t('events.saveError.generic', {values: {message: refusal.message || refusal.code}});
    }
    const detail = responseOf(err)?.data?.detail;
    if (Array.isArray(detail)) {
        // A 422 on a type: loc = ['body', <item>, 'events', <index>, 'type'].
        const issue = detail.find((d) => Array.isArray(d?.loc) && d.loc[d.loc.length - 1] === 'type' && d.loc.includes('events')) as {loc: unknown[]; input?: unknown} | undefined;
        if (issue) {
            const row = sent[Number(issue.loc[issue.loc.indexOf('events') + 1])];
            return t('events.saveError.unknownType', {values: {value: text(issue.input ?? row?.type), date: row ? dateLabel(row.date) : '?'}});
        }
    }
    const fallback = typeof detail === 'string' ? detail : (err as ErrorResponse | null)?.message || 'unknown error';
    return t('events.saveError.generic', {values: {message: fallback}});
}
