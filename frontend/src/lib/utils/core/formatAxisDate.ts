/**
 * formatAxisDate — a short, locale-aware date label for a chart axis or tooltip.
 *
 * "Jun 5", or "Jun 5, 2024" when `withYear` is set (used when a chart spans more
 * than one year and the day alone would be ambiguous). An unparseable input is
 * echoed back through `String(value)` rather than rendered as "Invalid Date".
 *
 * The locale is passed in; an empty one falls back to the interface locale
 * (`uiLocale()`, M-18), never to the browser's.
 *
 * The three lot charts each carried this verbatim — twice as `formatAxisDate`
 * and once, confusingly, as `formatShortDate`. Note it is NOT the same as
 * `LotComparisonChart`'s *other* `formatShortDate`, which renders a numeric
 * `dd/mm/yy`; that one is a genuinely different format and stays local.
 *
 * ## Why a date-only string is parsed by hand
 *
 * `new Date('2024-03-15')` is midnight **UTC** by specification, while
 * `new Date('2024-03-15T00:00')` is midnight local. Rendering the first one
 * therefore shows the *previous* day to everyone west of Greenwich: measured,
 * `2024-03-15` prints "Mar 14, 2024" in New York and "15 mar 2024" in Rome.
 *
 * Every date the API sends for an opening, a closing or a lot boundary is a bare
 * `YYYY-MM-DD` — a calendar day, with no instant attached and no timezone to
 * convert between. So it is read as a local calendar day, which is the only
 * reading that means anything. Timestamps and anything carrying a time of day
 * keep the normal parse: those *are* instants.
 *
 * `LotCustodyModal` was the one copy that already did this; the others rendered
 * the wrong day for half the planet.
 */

import {uiLocale} from '$lib/stores/app/uiLocale';

/** A bare calendar day: no time, no zone, nothing to convert. */
const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;

/**
 * Parse a value the way a *display* formatter should, and `null` if it cannot.
 *
 * The whole subtlety is in the first branch. `new Date('2024-03-15')` is midnight
 * UTC by specification, so formatting it shows the previous day to everyone west
 * of Greenwich — measured, "Mar 14, 2024" in New York against "15 mar 2024" in
 * Rome, from one string. Every opening, closing and lot boundary the API sends is
 * a bare `YYYY-MM-DD`: a calendar day, with no instant attached and no timezone
 * to convert between, so the only reading that means anything is the local one.
 *
 * Anything carrying a time of day, and any numeric timestamp, *is* an instant and
 * keeps the normal parse.
 *
 * Exported because the fix has to reach every display formatter, not just the
 * axis one: four call sites across the lot charts each had their own
 * `new Date(value)` and each showed the wrong day.
 */
export function parseDisplayDate(value: number | string): Date | null {
    const dayParts = typeof value === 'string' ? DATE_ONLY.exec(value) : null;
    if (dayParts) {
        const [, y, m, d] = dayParts.map(Number);
        const date = new Date(y, m - 1, d);
        // The regex matches the *shape*, not the calendar: `new Date(2024, 12, 45)`
        // does not fail, it rolls over into the next year. Round-tripping the
        // components is the only way to tell a real day from a well-formed
        // impossible one.
        if (date.getFullYear() !== y || date.getMonth() !== m - 1 || date.getDate() !== d) return null;
        return date;
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

/**
 * A calendar day, `YYYY-MM-DD`, as the interface writes a date in a tooltip or a detail line:
 * `12 ott 2026`, `12 Oct 2026`, `12 oct. 2026` (M-18). Anything else comes back unchanged — a
 * chart category that is not a day stays what it is, where `formatAxisDate` would read a bare
 * number as a year.
 */
export function formatDay(value: string, locale: string = uiLocale()): string {
    return DATE_ONLY.test(value) ? formatAxisDate(locale, value, true) : value;
}

export function formatAxisDate(locale: string | undefined, value: number | string, withYear = false): string {
    const date = parseDisplayDate(value);
    if (!date) return String(value);
    return date.toLocaleDateString(locale || uiLocale(), withYear ? {year: 'numeric', month: 'short', day: 'numeric'} : {month: 'short', day: 'numeric'});
}
