/**
 * The date range a targeted sync asks a provider for.
 *
 * One rule, shared by asset prices and FX rates: a week before the first date that
 * matters and a week after the last one, never past today. A week either side turns
 * a weekend or a bank holiday at an edge into a covered day, because conversions and
 * valuations backfill from the last value on or before the date they need.
 *
 * @module utils/sync/syncRange
 */

import {addDays, todayIso} from '$lib/utils/dateOnly';

/** Calendar days added on each side of a targeted sync. */
export const SYNC_MARGIN_DAYS = 7;

/** A sync range: `start` may be the `'min'` sentinel (everything the provider publishes). */
export interface SyncRange {
    start: string;
    end: string;
}

/** `start` moved back by `days`, or `'min'` when it already is, or when the calendar runs out. */
export function subtractCalendarDaysOrMin(start: string, days: number): string {
    if (start === 'min') return start;
    try {
        return addDays(start, -days);
    } catch (error) {
        if (error instanceof RangeError) return 'min';
        throw error;
    }
}

/**
 * Widen `range` by `days` on each side (default {@link SYNC_MARGIN_DAYS}).
 *
 * The end never passes `today` (an `end` of `'max'`, today or later means today), and
 * the start never passes the end. A `'min'` start is kept as is.
 */
export function padSyncRange(range: {start: string; end: string}, options: {days?: number; today?: string} = {}): SyncRange {
    const days = options.days ?? SYNC_MARGIN_DAYS;
    if (!Number.isSafeInteger(days) || days < 0) {
        throw new RangeError('days must be a non-negative safe integer');
    }
    const today = options.today ?? todayIso();
    const start = subtractCalendarDaysOrMin(range.start, days);
    const end = range.end === 'max' || range.end >= today ? today : addDays(range.end, days);
    const cappedEnd = end > today ? today : end;
    return {
        start: start !== 'min' && start > cappedEnd ? cappedEnd : start,
        end: cappedEnd,
    };
}

/** The part of a MISSING_FX_RATES data-quality issue a sync request is built from. */
export interface MissingFxRatesIssueLike {
    affected_fx_pairs?: readonly string[] | null;
    cta_target?: string | null;
    message_params?: Record<string, unknown> | null;
}

/** `EUR/usd`, `usd-EUR` → `EUR-USD`; null when it does not name two different currencies. */
function pairSlug(pair: unknown): string | null {
    if (typeof pair !== 'string') return null;
    const codes = pair
        .split(/[-/]/)
        .map((code) => code.trim().toUpperCase())
        .filter(Boolean);
    if (codes.length !== 2 || codes[0] === codes[1]) return null;
    return codes.sort().join('-');
}

function isCalendarDate(value: unknown): value is string {
    if (typeof value !== 'string') return false;
    try {
        return addDays(value, 0) === value;
    } catch {
        return false;
    }
}

/**
 * The body of `POST /fx/currencies/sync` that fills the dates a MISSING_FX_RATES issue reports.
 *
 * The issue carries the span of its missing dates (`date_from`/`date_to`, over every
 * affected pair). A date is missing only when no rate exists on or before it, so these
 * dates precede the pair's first stored rate, and syncing the period on screen never
 * reaches them: the request targets the span instead, padded by {@link padSyncRange}.
 * Without usable dates it asks for the whole history. Null when there is no pair.
 */
export function buildMissingFxRatesSyncRequest(issue: MissingFxRatesIssueLike, options: {today?: string} = {}): {pairs: string[]; start: string; end: string} | null {
    const candidates = issue.affected_fx_pairs?.length ? issue.affected_fx_pairs : [issue.cta_target];
    const pairs = [...new Set(candidates.map(pairSlug).filter((slug): slug is string => slug !== null))];
    if (pairs.length === 0) return null;

    const today = options.today ?? todayIso();
    const from = issue.message_params?.date_from;
    const to = issue.message_params?.date_to;
    if (!isCalendarDate(from) || !isCalendarDate(to)) {
        return {pairs, start: 'min', end: today};
    }
    const range = padSyncRange({start: from <= to ? from : to, end: from <= to ? to : from}, {today});
    return {pairs, ...range};
}
