/**
 * formatDateTime — a locale-aware "date **and** time" label, e.g. "Jun 5, 2024,
 * 04:30 PM".
 *
 * `FileGrid` and the files route each carried this verbatim: a file listing
 * shows *when* each file was uploaded, down to the minute. That minute is the
 * whole point, which is what sets this family apart from its neighbours —
 * `formatAxisDate` is date-only (for chart labels), and the profile/broker
 * display formatters are date-only too. Reading the bodies rather than the
 * names, these two were the only genuine "date+time" copies, and they were
 * byte-identical, so they collapse into one function.
 *
 * Two deliberate fidelity choices, so the output stays exactly what the copies
 * produced:
 *
 * - The locale defaults to the environment's, matching the original
 *   `toLocaleDateString(undefined, …)` calls (not the `$currentLanguage` store
 *   the chart formatters thread through).
 * - The original used `toLocaleDateString` *with* time options rather than
 *   `toLocaleString`. `toLocaleDateString` does honour `hour`/`minute` in
 *   practice, so the two render identically — but this keeps the exact call to
 *   avoid any engine-specific difference.
 *
 * There is intentionally **no** "Invalid Date" guard: neither copy had one, and
 * adding it here would change what a malformed timestamp renders as. The lot
 * formatters, which echo the raw string on a bad parse, are a separate family
 * with a separate contract.
 */
export function formatDateTime(value: Date | string, locale?: string): string {
    return new Date(value).toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}
