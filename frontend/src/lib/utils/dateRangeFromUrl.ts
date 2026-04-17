/**
 * Utility to initialize date range from URL search params.
 *
 * Used by both asset detail and FX detail pages to read start/end
 * query params from the URL, falling back to a default 3-month range.
 *
 * @module utils/dateRangeFromUrl
 */

/**
 * Parse date range from URL search params.
 *
 * @param searchParams - URLSearchParams from the current page
 * @param defaultMonths - Number of months back for the default start date (default: 3)
 * @returns { start, end, hasCustomRange } — start/end dates and whether custom params were found
 */
export function parseDateRangeFromUrl(searchParams: URLSearchParams, defaultMonths = 3): {start: string; end: string; hasCustomRange: boolean} {
    const qEnd = searchParams.get('end');
    const qStart = searchParams.get('start');

    const end = qEnd || new Date().toISOString().slice(0, 10);

    let start: string;
    if (qStart) {
        start = qStart;
    } else {
        const d = new Date();
        d.setMonth(d.getMonth() - defaultMonths);
        start = d.toISOString().slice(0, 10);
    }

    return {start, end, hasCustomRange: !!qStart};
}
