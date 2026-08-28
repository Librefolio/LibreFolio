/**
 * Calendar-day arithmetic for `YYYY-MM-DD` strings.
 *
 * ## Why this exists
 *
 * A date-only value has **no time zone**. `2024-12-31` is a day on a calendar, not
 * an instant, and the moment it is treated as one the answer starts depending on
 * where the user is sitting.
 *
 * That is exactly what went wrong in `ScheduledInvestmentEditor`, which did:
 *
 * ```ts
 * const d = new Date(iso + 'T00:00:00');   // midnight LOCAL
 * d.setDate(d.getDate() + days);
 * return d.toISOString().slice(0, 10);     // ...re-projected into UTC
 * ```
 *
 * East of Greenwich, local midnight is the *previous* day in UTC, so the final
 * `slice` hands back a day that is one behind. Measured under `TZ=Europe/Rome`:
 *
 * | call | returned | expected |
 * |---|---|---|
 * | `addDays('2024-12-31', +1)` | `2024-12-31` | `2025-01-01` |
 * | `addDays('2024-03-15', -1)` | `2024-03-13` | `2024-03-14` |
 *
 * The second row is the nastier one: a single step backwards moved **two** days,
 * because the DST-free offset and the projection stack. Under `TZ=UTC` — which is
 * what a CI container usually runs — every one of these is correct, so the bug is
 * invisible to a test suite that never leaves Greenwich.
 *
 * ## The rule
 *
 * Stay inside the calendar-day domain from beginning to end. These helpers do the
 * arithmetic in UTC, where a "day" is exactly 24 hours and no offset is ever
 * applied, and never mix in a local-time reading.
 *
 * The one function that *must* read local time is {@link todayIso}: "today" is a
 * question about the user's calendar, not Greenwich's. `new Date().toISOString()`
 * gets that wrong too — at 00:30 in Rome it answers *yesterday*.
 */

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Parse `YYYY-MM-DD` into a UTC-midnight Date. Throws on anything else. */
function parseUtc(isoDate: string): Date {
    if (!ISO_DATE.test(isoDate)) {
        throw new RangeError(`expected a YYYY-MM-DD date, got ${JSON.stringify(isoDate)}`);
    }
    const d = new Date(`${isoDate}T00:00:00Z`);
    if (Number.isNaN(d.getTime())) {
        throw new RangeError(`not a real calendar date: ${isoDate}`);
    }
    // `Date` silently normalises a day that does not exist — 2023-02-30 becomes
    // 2 March — which would turn a typo into a plausible-looking wrong answer
    // instead of an error. The round trip is the only way to tell them apart.
    if (formatUtc(d) !== isoDate) {
        throw new RangeError(`not a real calendar date: ${isoDate}`);
    }
    return d;
}

/** Format a UTC Date back to `YYYY-MM-DD`. */
function formatUtc(d: Date): string {
    return d.toISOString().slice(0, 10);
}

/** Today, on the *user's* calendar. */
export function todayIso(): string {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

/** `isoDate` shifted by `days`, which may be negative. */
export function addDays(isoDate: string, days: number): string {
    const d = parseUtc(isoDate);
    d.setUTCDate(d.getUTCDate() + days);
    return formatUtc(d);
}

/**
 * `isoDate` shifted by `months`, which may be negative.
 *
 * Overflow follows the platform's own rule and is left deliberately unsmoothed:
 * 31 January plus one month is 2 or 3 March, not 28/29 February. Callers that
 * need clamping should say so at the call site, where the intent is visible —
 * silently clamping here would make "add a month twice" and "add two months"
 * disagree.
 */
export function addMonths(isoDate: string, months: number): string {
    const d = parseUtc(isoDate);
    d.setUTCMonth(d.getUTCMonth() + months);
    return formatUtc(d);
}

/** Whole days from `start` to `end`; negative when `end` precedes `start`. */
export function daysBetween(start: string, end: string): number {
    const ms = parseUtc(end).getTime() - parseUtc(start).getTime();
    return Math.round(ms / 86_400_000);
}

/** The day halfway between the two, rounded down towards `start`. */
export function midpointDate(start: string, end: string): string {
    return addDays(start, Math.floor(daysBetween(start, end) / 2));
}
