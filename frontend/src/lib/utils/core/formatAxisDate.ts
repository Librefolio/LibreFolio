/**
 * formatAxisDate — a short, locale-aware date label for a chart axis or tooltip.
 *
 * "Jun 5", or "Jun 5, 2024" when `withYear` is set (used when a chart spans more
 * than one year and the day alone would be ambiguous). An unparseable input is
 * echoed back through `String(value)` rather than rendered as "Invalid Date".
 *
 * The locale is passed in (the `$currentLanguage` store value) so this stays a
 * pure function; an empty locale falls back to the environment default, matching
 * the original `toLocaleDateString($currentLanguage || undefined, …)` call.
 *
 * The three lot charts each carried this verbatim — twice as `formatAxisDate`
 * and once, confusingly, as `formatShortDate`. Note it is NOT the same as
 * `LotComparisonChart`'s *other* `formatShortDate`, which renders a numeric
 * `dd/mm/yy`; that one is a genuinely different format and stays local.
 */
export function formatAxisDate(locale: string | undefined, value: number | string, withYear = false): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleDateString(locale || undefined, withYear ? {year: 'numeric', month: 'short', day: 'numeric'} : {month: 'short', day: 'numeric'});
}
