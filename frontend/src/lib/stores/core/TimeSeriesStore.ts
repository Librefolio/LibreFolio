/**
 * TimeSeriesStore — Generic client-side cache for time-series data.
 *
 * Parameterized on T (any type with a `date: string` field in ISO YYYY-MM-DD format).
 * Used by FX charts (FxDataPoint), Asset charts (AssetPricePoint), and Dashboard.
 *
 * Features:
 * - Efficient Map<string, T> storage keyed by ISO date
 * - Gap detection: returns missing date intervals for delta-fetching
 * - Merge: idempotent insert/update of data points
 * - Invalidation: per-range or full cache clear (for refresh)
 *
 * Design principle: the chart component asks "what do I need for this range?",
 * the store responds with existing data + gaps. The controller fetches only the gaps
 * from the backend, then merges the results. This minimizes API calls.
 *
 * @module stores/TimeSeriesStore
 */

// ============================================================================
// TYPES
// ============================================================================

/** Constraint for any time-series data point */
export interface TimeSeriesPoint {
    date: string; // ISO YYYY-MM-DD
}

/** A contiguous date interval where data is missing */
export interface DateGap {
    start: string; // ISO YYYY-MM-DD (inclusive)
    end: string; // ISO YYYY-MM-DD (inclusive)
}

/** Result of querying a date range from the store */
export interface RangeResult<T extends TimeSeriesPoint> {
    /** Data points present in the store for the requested range, sorted by date */
    data: T[];
    /** Contiguous intervals where no data exists in the store */
    gaps: DateGap[];
}

// ============================================================================
// HELPERS
// ============================================================================

/** Parse ISO date string to Date object (midnight UTC) */
function parseDate(iso: string): Date {
    const [y, m, d] = iso.split('-').map(Number);
    return new Date(Date.UTC(y, m - 1, d));
}

/** Format Date to ISO YYYY-MM-DD string */
function formatDate(date: Date): string {
    const y = date.getUTCFullYear();
    const m = String(date.getUTCMonth() + 1).padStart(2, '0');
    const d = String(date.getUTCDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

/** Advance a date by N days (returns new Date) */
function addDays(date: Date, days: number): Date {
    const result = new Date(date.getTime());
    result.setUTCDate(result.getUTCDate() + days);
    return result;
}

// ============================================================================
// STORE
// ============================================================================

export class TimeSeriesStore<T extends TimeSeriesPoint> {
    private data: Map<string, T> = new Map();
    /** Intervals already fetched from the API (may have returned no data). */
    private fetchedRanges: Array<{start: Date; end: Date}> = [];

    /** Number of data points currently in the store */
    get size(): number {
        return this.data.size;
    }

    /**
     * Get a single data point by date.
     */
    get(date: string): T | undefined {
        return this.data.get(date);
    }

    /**
     * Check if a data point exists for the given date.
     */
    has(date: string): boolean {
        return this.data.has(date);
    }

    /**
     * Query a date range. Returns existing data points (sorted) and a list
     * of contiguous gap intervals where the store has no data.
     *
     * The gaps can be used to fetch only the missing data from the backend.
     *
     * @param start - Start date (inclusive), ISO YYYY-MM-DD
     * @param end   - End date (inclusive), ISO YYYY-MM-DD
     */
    getRange(start: string, end: string): RangeResult<T> {
        const startDate = parseDate(start);
        const endDate = parseDate(end);

        const data: T[] = [];
        const gaps: DateGap[] = [];

        let gapStart: Date | null = null;
        let current = new Date(startDate.getTime());

        while (current <= endDate) {
            const key = formatDate(current);
            const point = this.data.get(key);

            if (point) {
                // Close any open gap
                if (gapStart !== null) {
                    gaps.push({
                        start: formatDate(gapStart),
                        end: formatDate(addDays(current, -1)),
                    });
                    gapStart = null;
                }
                data.push(point);
            } else {
                // Start a new gap if not already in one
                if (gapStart === null) {
                    gapStart = new Date(current.getTime());
                }
            }

            current = addDays(current, 1);
        }

        // Close trailing gap
        if (gapStart !== null) {
            gaps.push({
                start: formatDate(gapStart),
                end: end,
            });
        }

        return {data, gaps};
    }

    /**
     * Get only the missing intervals for a range (convenience wrapper).
     * Excludes intervals already marked as fetched (even if they returned no data),
     * preventing redundant API calls within the same session.
     */
    getMissingIntervals(start: string, end: string): DateGap[] {
        return this.getRange(start, end).gaps.filter((gap) => !this.isRangeFetched(gap.start, gap.end));
    }

    /**
     * Mark a date range as fetched from the API.
     * After this call, getMissingIntervals will not return gaps inside this range,
     * even if no data was stored (e.g. after a 404).
     * Cleared by invalidateAll() and invalidateRange().
     */
    markFetched(start: string, end: string): void {
        this.fetchedRanges.push({start: parseDate(start), end: parseDate(end)});
    }

    private isRangeFetched(start: string, end: string): boolean {
        const s = parseDate(start);
        const e = parseDate(end);
        return this.fetchedRanges.some((r) => r.start <= s && r.end >= e);
    }

    /**
     * Merge data points into the store. Existing points with the same date
     * are overwritten (upsert semantics). Idempotent.
     *
     * @param points - Array of data points to merge
     */
    merge(points: T[]): void {
        for (const point of points) {
            this.data.set(point.date, point);
        }
    }

    /**
     * Invalidate (remove) all data points in the given range.
     * Used by the refresh action to force re-fetching.
     *
     * @param start - Start date (inclusive)
     * @param end   - End date (inclusive)
     */
    invalidateRange(start: string, end: string): void {
        const startDate = parseDate(start);
        const endDate = parseDate(end);
        let current = new Date(startDate.getTime());

        while (current <= endDate) {
            this.data.delete(formatDate(current));
            current = addDays(current, 1);
        }

        // Clear fetched marks that overlap the invalidated range
        this.fetchedRanges = this.fetchedRanges.filter((r) => r.end < startDate || r.start > endDate);
    }

    /**
     * Clear the entire store. Used for full refresh or component teardown.
     */
    invalidateAll(): void {
        this.data.clear();
        this.fetchedRanges = [];
    }

    /**
     * Get all data points sorted by date.
     */
    getAllSorted(): T[] {
        return Array.from(this.data.values()).sort((a, b) => a.date.localeCompare(b.date));
    }
}
