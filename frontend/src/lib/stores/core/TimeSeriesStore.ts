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
 * - Staleness: after a price catch-up on the server, markStale() keeps the points and makes the next read of any
 *   range ask again (Z-14)
 * - Generation: a number, unique in the whole app, renewed by every invalidation and by markStale(): what was computed
 *   from the store's data (the signal results of `signalResultCache`, N64) holds only while it is the same
 *
 * Design principle: the chart component asks "what do I need for this range?",
 * the store responds with existing data + gaps. The controller fetches only the gaps
 * from the backend, then merges the results. This minimizes API calls.
 *
 * @module stores/TimeSeriesStore
 */

import {utcMs} from '../../utils/dateOnly';

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
    return new Date(utcMs(y, m - 1, d)); // not Date.UTC: it reads the year 24 as 1924
}

/** Format Date to ISO YYYY-MM-DD string */
function formatDate(date: Date): string {
    const y = date.getUTCFullYear();
    const m = String(date.getUTCMonth() + 1).padStart(2, '0');
    const d = String(date.getUTCDate()).padStart(2, '0');
    return `${String(y).padStart(4, '0')}-${m}-${d}`;
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

/** The last generation handed out, by any store: a generation is never given twice, not even to a store made anew. */
let lastGeneration = 0;
const nextGeneration = (): number => ++lastGeneration;

export class TimeSeriesStore<T extends TimeSeriesPoint> {
    private data: Map<string, T> = new Map();
    /** Intervals already fetched from the API (may have returned no data). */
    private fetchedRanges: Array<{start: Date; end: Date}> = [];
    /**
     * Set by markStale(): the server may hold newer points than the store. Until a fetch covers it again, a date
     * counts as missing whether or not the store has a point; the points stay readable. Ended by invalidateAll().
     */
    private stale = false;
    /** Renewed by invalidateAll(), invalidateRange() and markStale(); kept by merge(), markFetched() and every read. */
    private currentGeneration = nextGeneration();

    /**
     * The generation of the store's data, unique in the app (N64). It changes when the data may have changed under what
     * was computed from it — an invalidation, a catch-up marking it stale — and never when points are only added.
     */
    get generation(): number {
        return this.currentGeneration;
    }

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
     * Once the store is stale (markStale), the dates no fetch since the mark covers are missing, points or not.
     */
    getMissingIntervals(start: string, end: string): DateGap[] {
        if (this.stale) return this.unfetchedIntervals(start, end);
        return this.getRange(start, end).gaps.filter((gap) => !this.isRangeFetched(gap.start, gap.end));
    }

    /**
     * The server may hold newer points than the store — a price catch-up filled or corrected days (Z-14): forget
     * the fetched marks, so the next read of any range asks the server again even where the store has points.
     * The points stay readable until the answer replaces them.
     */
    markStale(): void {
        this.fetchedRanges = [];
        this.stale = true;
        this.currentGeneration = nextGeneration();
    }

    /**
     * Whether a price catch-up marked the store (`markStale()`) and nothing forgot its points since (`invalidateAll()`). A
     * page whose range is missing from a stale store that still holds points for it shows them at once and asks in background
     * (Y5-1). Read-only: a fetch covering the range clears the gaps, not this.
     */
    get isStale(): boolean {
        return this.stale;
    }

    /** The parts of [start, end] that no fetch since the last markStale() covers, in date order. */
    private unfetchedIntervals(start: string, end: string): DateGap[] {
        const endDate = parseDate(end);
        const gaps: DateGap[] = [];
        let gapStart: Date | null = null;
        let current = parseDate(start);

        while (current <= endDate) {
            const covered = this.isDateFetched(current);
            if (!covered && gapStart === null) {
                gapStart = new Date(current.getTime());
            } else if (covered && gapStart !== null) {
                gaps.push({start: formatDate(gapStart), end: formatDate(addDays(current, -1))});
                gapStart = null;
            }
            current = addDays(current, 1);
        }

        if (gapStart !== null) {
            gaps.push({start: formatDate(gapStart), end: end});
        }
        return gaps;
    }

    private isDateFetched(date: Date): boolean {
        return this.fetchedRanges.some((r) => r.start <= date && r.end >= date);
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
        this.currentGeneration = nextGeneration();
    }

    /**
     * Clear the entire store. Used for full refresh or component teardown. Ends the stale state too.
     */
    invalidateAll(): void {
        this.data.clear();
        this.fetchedRanges = [];
        this.stale = false;
        this.currentGeneration = nextGeneration();
    }

    /**
     * Get all data points sorted by date.
     */
    getAllSorted(): T[] {
        return Array.from(this.data.values()).sort((a, b) => a.date.localeCompare(b.date));
    }
}
