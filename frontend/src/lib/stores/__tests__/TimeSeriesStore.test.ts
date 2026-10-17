/**
 * Unit tests for TimeSeriesStore — Generic client-side cache for time-series data.
 *
 * Tests 16–24: the stale state a price catch-up puts every store in (`markStale()`, Z-14).
 */
import {describe, expect, it} from 'vitest';
import type {TimeSeriesPoint} from '../core/TimeSeriesStore';
import {TimeSeriesStore} from '../core/TimeSeriesStore';

interface TestPoint extends TimeSeriesPoint {
    date: string;
    value: number;
}

function pt(date: string, value: number): TestPoint {
    return {date, value};
}

describe('TimeSeriesStore', () => {
    // =========================================================================
    // Test 1: getRange on empty store → single gap for entire range
    // =========================================================================
    it('getRange on empty store returns single gap for entire range', () => {
        const store = new TimeSeriesStore<TestPoint>();
        const result = store.getRange('2024-01-01', '2024-01-05');
        expect(result.data).toEqual([]);
        expect(result.gaps).toEqual([{start: '2024-01-01', end: '2024-01-05'}]);
    });

    // =========================================================================
    // Test 2: merge + getRange → insert and retrieve
    // =========================================================================
    it('merge + getRange returns data and no gap for covered dates', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0), pt('2024-01-02', 1.1), pt('2024-01-03', 1.2)]);
        const result = store.getRange('2024-01-01', '2024-01-03');
        expect(result.data).toHaveLength(3);
        expect(result.gaps).toEqual([]);
        expect(result.data[0].value).toBe(1.0);
        expect(result.data[2].value).toBe(1.2);
    });

    // =========================================================================
    // Test 3: merge is idempotent (no duplicates)
    // =========================================================================
    it('merge is idempotent — re-merging does not increase size', () => {
        const store = new TimeSeriesStore<TestPoint>();
        const points = [pt('2024-01-01', 1.0), pt('2024-01-02', 1.1)];
        store.merge(points);
        expect(store.size).toBe(2);
        store.merge(points);
        expect(store.size).toBe(2);
    });

    // =========================================================================
    // Test 4: getRange with intermediate gaps
    // =========================================================================
    it('getRange with holes returns multiple gaps', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([
            pt('2024-01-01', 1.0),
            // 2024-01-02 missing
            pt('2024-01-03', 1.2),
            // 2024-01-04 missing
            pt('2024-01-05', 1.4),
        ]);
        const result = store.getRange('2024-01-01', '2024-01-05');
        expect(result.data).toHaveLength(3);
        expect(result.gaps).toHaveLength(2);
        expect(result.gaps[0]).toEqual({start: '2024-01-02', end: '2024-01-02'});
        expect(result.gaps[1]).toEqual({start: '2024-01-04', end: '2024-01-04'});
    });

    // =========================================================================
    // Test 5: getMissingIntervals excludes already-fetched intervals
    // =========================================================================
    it('getMissingIntervals excludes intervals already marked as fetched', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0), pt('2024-01-03', 1.2)]);
        // Gap: 2024-01-02. Without markFetched it should appear.
        expect(store.getMissingIntervals('2024-01-01', '2024-01-03')).toHaveLength(1);
        // After marking the gap as fetched, getMissingIntervals returns empty
        store.markFetched('2024-01-02', '2024-01-02');
        expect(store.getMissingIntervals('2024-01-01', '2024-01-03')).toHaveLength(0);
        // getRange().gaps is still the raw gaps (not filtered)
        expect(store.getRange('2024-01-01', '2024-01-03').gaps).toHaveLength(1);
    });

    // =========================================================================
    // Test 5b: invalidateRange clears overlapping fetchedRanges marks
    // =========================================================================
    it('invalidateRange clears fetched marks that overlap the invalidated range', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0), pt('2024-01-02', 1.1), pt('2024-01-03', 1.2)]);
        store.markFetched('2024-01-01', '2024-01-03');
        // Gap introduced inside the marked range
        store.invalidateRange('2024-01-02', '2024-01-02');
        // Mark should be cleared → gap is now visible again
        expect(store.getMissingIntervals('2024-01-01', '2024-01-03')).toHaveLength(1);
    });

    // =========================================================================
    // Test 5c: invalidateAll clears all fetchedRanges marks
    // =========================================================================
    it('invalidateAll clears all fetched marks so gaps become visible again', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.markFetched('2024-01-01', '2024-01-05');
        // Gap should be suppressed before invalidate
        expect(store.getMissingIntervals('2024-01-01', '2024-01-05')).toHaveLength(0);
        store.invalidateAll();
        // After invalidateAll, marks cleared → gaps reappear
        expect(store.getMissingIntervals('2024-01-01', '2024-01-05')).toHaveLength(1);
    });

    // =========================================================================
    // Test 6: invalidateRange removes only the specified range
    // =========================================================================
    it('invalidateRange removes only the specified range', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0), pt('2024-01-02', 1.1), pt('2024-01-03', 1.2), pt('2024-01-04', 1.3)]);
        store.invalidateRange('2024-01-02', '2024-01-03');
        expect(store.size).toBe(2);
        expect(store.has('2024-01-01')).toBe(true);
        expect(store.has('2024-01-02')).toBe(false);
        expect(store.has('2024-01-03')).toBe(false);
        expect(store.has('2024-01-04')).toBe(true);
    });

    // =========================================================================
    // Test 7: invalidateAll clears entire store
    // =========================================================================
    it('invalidateAll clears the entire store', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0), pt('2024-01-02', 1.1)]);
        expect(store.size).toBe(2);
        store.invalidateAll();
        expect(store.size).toBe(0);
    });

    // =========================================================================
    // Test 8: getAllSorted returns chronologically ordered array
    // =========================================================================
    it('getAllSorted returns chronologically ordered array', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-03', 1.2), pt('2024-01-01', 1.0), pt('2024-01-02', 1.1)]);
        const sorted = store.getAllSorted();
        expect(sorted.map((d) => d.date)).toEqual(['2024-01-01', '2024-01-02', '2024-01-03']);
    });

    // =========================================================================
    // Test 9: Edge — range with start > end → graceful
    // =========================================================================
    it('getRange with start > end returns empty data and no gaps', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0)]);
        const result = store.getRange('2024-01-05', '2024-01-01');
        expect(result.data).toEqual([]);
        expect(result.gaps).toEqual([]);
    });

    // =========================================================================
    // Test 10: Edge — range 1 day with point present
    // =========================================================================
    it('single-day range with point present returns 1 data point and no gap', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0)]);
        const result = store.getRange('2024-01-01', '2024-01-01');
        expect(result.data).toHaveLength(1);
        expect(result.gaps).toEqual([]);
    });

    // =========================================================================
    // Test 11: Edge — range 1 day without point
    // =========================================================================
    it('single-day range without point returns 1 gap', () => {
        const store = new TimeSeriesStore<TestPoint>();
        const result = store.getRange('2024-01-01', '2024-01-01');
        expect(result.data).toEqual([]);
        expect(result.gaps).toEqual([{start: '2024-01-01', end: '2024-01-01'}]);
    });

    // =========================================================================
    // Test 12: Merge with non-contiguous dates → sparse store
    // =========================================================================
    it('merge with non-contiguous dates → gaps calculated correctly', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0), pt('2024-01-05', 1.4), pt('2024-01-10', 1.9)]);
        const result = store.getRange('2024-01-01', '2024-01-10');
        expect(result.data).toHaveLength(3);
        expect(result.gaps).toHaveLength(2);
        expect(result.gaps[0]).toEqual({start: '2024-01-02', end: '2024-01-04'});
        expect(result.gaps[1]).toEqual({start: '2024-01-06', end: '2024-01-09'});
    });

    // =========================================================================
    // Test 13: get and has — direct lookup
    // =========================================================================
    it('get and has work for direct lookup', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0)]);
        expect(store.has('2024-01-01')).toBe(true);
        expect(store.has('2024-01-02')).toBe(false);
        expect(store.get('2024-01-01')?.value).toBe(1.0);
        expect(store.get('2024-01-02')).toBeUndefined();
    });

    // =========================================================================
    // Test 14: merge overwrites existing data (upsert)
    // =========================================================================
    it('merge overwrites existing data (upsert semantics)', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0)]);
        expect(store.get('2024-01-01')?.value).toBe(1.0);
        store.merge([pt('2024-01-01', 9.9)]);
        expect(store.get('2024-01-01')?.value).toBe(9.9);
        expect(store.size).toBe(1);
    });

    // =========================================================================
    // Test 15: Trailing gap (end of range is empty)
    // =========================================================================
    it('trailing gap at end of range is correctly detected', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0), pt('2024-01-02', 1.1)]);
        const result = store.getRange('2024-01-01', '2024-01-05');
        expect(result.data).toHaveLength(2);
        expect(result.gaps).toHaveLength(1);
        expect(result.gaps[0]).toEqual({start: '2024-01-03', end: '2024-01-05'});
    });
});

// =============================================================================
//  markStale — the server may have changed what the store holds (Z-14)
//
//  The price and FX answers fill backward the days without a value, so a store
//  that loaded a range holds a point for every day of it: the presence of a
//  point says nothing about whether the server changed it since. After a price
//  catch-up the registries call `markStale()` on every store. The points stay
//  readable — a page shows them until fresh ones land — and the fetched marks
//  are dropped: from then on `getMissingIntervals(start, end)` answers by
//  coverage, with the parts of [start, end] that no `markFetched` made after the
//  mark covers (their union), even where the store has points. `invalidateAll()`
//  ends that state. Without a mark nothing changes: presence-based gaps,
//  filtered by a single covering fetched range.
//
//  Red first: `markStale` is read by name, so that its absence fails each case
//  with the contract in the message, and the type check does not wait for it.
// =============================================================================

/** `store.markStale()`, read by name (see above). */
function markStale(store: TimeSeriesStore<TestPoint>): void {
    const method = (store as unknown as {markStale?: unknown}).markStale;
    expect(typeof method, 'TimeSeriesStore has no markStale(): after a price catch-up a store cannot be told that the server may have changed what it holds, so a range it loaded is never asked again (Z-14)').toBe('function');
    (method as () => void).call(store);
}

/** A point for every day of [start, end]: what a backward-filled answer leaves in the store. */
function everyDay(start: string, end: string, value = 1): TestPoint[] {
    const points: TestPoint[] = [];
    for (const day = new Date(`${start}T00:00:00Z`); day <= new Date(`${end}T00:00:00Z`); day.setUTCDate(day.getUTCDate() + 1)) {
        points.push(pt(day.toISOString().slice(0, 10), value));
    }
    return points;
}

describe('TimeSeriesStore.markStale (Z-14)', () => {
    // =========================================================================
    // Test 16: the points stay readable
    // =========================================================================
    it('keeps every point readable: get, has, size, getRange().data and getAllSorted() are what they were', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2026-01-03', 1.3), pt('2026-01-01', 1.1), pt('2026-01-02', 1.2)]);
        store.markFetched('2026-01-01', '2026-01-03');
        const before = {
            size: store.size,
            point: store.get('2026-01-02'),
            has: [store.has('2026-01-01'), store.has('2026-01-04')],
            data: store.getRange('2026-01-01', '2026-01-04').data,
            sorted: store.getAllSorted(),
        };

        markStale(store);

        expect(store.size).toBe(before.size);
        expect(store.get('2026-01-02'), 'a stale point is still the point to show until a fresh one replaces it').toEqual(before.point);
        expect([store.has('2026-01-01'), store.has('2026-01-04')]).toEqual(before.has);
        expect(store.getRange('2026-01-01', '2026-01-04').data, 'the mark emptied the range: a chart would blank out until the fresh answer lands').toEqual(before.data);
        expect(store.getAllSorted()).toEqual(before.sorted);
    });

    // =========================================================================
    // Test 17: a loaded range is missing whole after the mark
    // =========================================================================
    it('reports the whole range missing after the mark, though the store holds a point for every day of it', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge(everyDay('2026-01-01', '2026-01-20'));
        store.markFetched('2026-01-01', '2026-01-20');
        expect(store.getMissingIntervals('2026-01-01', '2026-01-20'), 'premise: a loaded range is not missing').toEqual([]);

        markStale(store);

        expect(store.getMissingIntervals('2026-01-01', '2026-01-20'), 'the range loaded before the catch-up is still served from the store: its backward-filled points hide what the server changed').toEqual([{start: '2026-01-01', end: '2026-01-20'}]);
        expect(store.getMissingIntervals('2026-01-05', '2026-01-07'), 'and so is any part of it').toEqual([{start: '2026-01-05', end: '2026-01-07'}]);
    });

    // =========================================================================
    // Test 18: only markFetched covers — a merge does not
    // =========================================================================
    it('does not count a point merged after the mark as fetched: only markFetched covers', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge(everyDay('2026-01-01', '2026-01-05'));
        markStale(store);

        store.merge([pt('2026-01-03', 9.9)]);

        expect(store.get('2026-01-03')?.value, 'the merge itself lands').toBe(9.9);
        expect(store.getMissingIntervals('2026-01-01', '2026-01-05'), 'a point is not a fetch: the range is still missing whole').toEqual([{start: '2026-01-01', end: '2026-01-05'}]);
    });

    // =========================================================================
    // Test 19: coverage is the union of the fetches made after the mark
    // =========================================================================
    it('takes the union of the fetches made after the mark: adjacent or overlapping fetches leave nothing missing', () => {
        const adjacent = new TimeSeriesStore<TestPoint>();
        adjacent.merge(everyDay('2026-01-01', '2026-01-20'));
        markStale(adjacent);
        adjacent.markFetched('2026-01-01', '2026-01-10');
        adjacent.markFetched('2026-01-11', '2026-01-20');
        expect(adjacent.getMissingIntervals('2026-01-01', '2026-01-20'), 'neither fetch covers the range alone; together they do').toEqual([]);

        const overlapping = new TimeSeriesStore<TestPoint>();
        overlapping.merge(everyDay('2026-01-01', '2026-01-20'));
        markStale(overlapping);
        overlapping.markFetched('2026-01-08', '2026-01-20');
        overlapping.markFetched('2026-01-01', '2026-01-12');
        expect(overlapping.getMissingIntervals('2026-01-01', '2026-01-20')).toEqual([]);
    });

    // =========================================================================
    // Test 20: a partial fetch leaves exactly the uncovered parts, in date order
    // =========================================================================
    it('leaves exactly the parts no fetch covers, as contiguous intervals in date order, points or not', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge(everyDay('2025-12-25', '2026-01-25'));
        markStale(store);

        store.markFetched('2026-01-08', '2026-01-12');
        expect(store.getMissingIntervals('2026-01-01', '2026-01-20'), 'before and after the one fetch').toEqual([
            {start: '2026-01-01', end: '2026-01-07'},
            {start: '2026-01-13', end: '2026-01-20'},
        ]);

        // Out of date order on purpose, one of them reaching before the range asked.
        store.markFetched('2026-01-15', '2026-01-16');
        store.markFetched('2025-12-28', '2026-01-02');
        expect(store.getMissingIntervals('2026-01-01', '2026-01-20')).toEqual([
            {start: '2026-01-03', end: '2026-01-07'},
            {start: '2026-01-13', end: '2026-01-14'},
            {start: '2026-01-17', end: '2026-01-20'},
        ]);
    });

    // =========================================================================
    // Test 21: fresh after a fetch of the whole range; a second mark
    // =========================================================================
    it('is fresh again once the whole range is fetched, and a second mark makes it stale again', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge(everyDay('2026-01-01', '2026-01-20'));
        markStale(store);
        store.markFetched('2026-01-01', '2026-01-20');
        expect(store.getMissingIntervals('2026-01-01', '2026-01-20'), 'the fetch made after the mark covers the range').toEqual([]);

        markStale(store);

        expect(store.getMissingIntervals('2026-01-01', '2026-01-20'), 'a second catch-up: what was fetched before it is stale in turn').toEqual([{start: '2026-01-01', end: '2026-01-20'}]);
    });

    // =========================================================================
    // Test 22: invalidateAll ends the stale state
    // =========================================================================
    it('ends the stale state on invalidateAll(): the store is empty, and a point merged then is not missing even without a fetch', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge(everyDay('2026-01-01', '2026-01-05'));
        markStale(store);

        store.invalidateAll();
        expect(store.size).toBe(0);
        store.merge([pt('2026-01-01', 1), pt('2026-01-02', 1), pt('2026-01-03', 1)]);

        expect(store.getMissingIntervals('2026-01-01', '2026-01-05'), 'after invalidateAll the store answers by presence again, as before any mark').toEqual([{start: '2026-01-04', end: '2026-01-05'}]);
    });

    // =========================================================================
    // Test 23: invalidateRange in the stale state
    // =========================================================================
    it('keeps invalidateRange working in the stale state: its points go, the fetch over them goes, and its days are missing', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge(everyDay('2026-01-01', '2026-01-10'));
        markStale(store);
        store.markFetched('2026-01-01', '2026-01-03');
        store.markFetched('2026-01-04', '2026-01-06');
        store.markFetched('2026-01-07', '2026-01-10');
        expect(store.getMissingIntervals('2026-01-01', '2026-01-10'), 'premise: the three fetches cover the range').toEqual([]);

        store.invalidateRange('2026-01-04', '2026-01-06');

        expect(
            ['2026-01-04', '2026-01-05', '2026-01-06'].map((date) => store.has(date)),
            'the points of the invalidated range are deleted',
        ).toEqual([false, false, false]);
        expect(store.size).toBe(7);
        expect(store.getMissingIntervals('2026-01-01', '2026-01-10'), 'only the invalidated days are missing: the fetch over them is cleared, the two beside it are not').toEqual([{start: '2026-01-04', end: '2026-01-06'}]);
    });

    // =========================================================================
    // Test 24: without a mark, exactly as before (green before and after Z-14)
    // =========================================================================
    it('without a mark answers as before: presence-based gaps, each dropped only when one fetched range covers it whole', () => {
        const loaded = new TimeSeriesStore<TestPoint>();
        loaded.merge(everyDay('2026-01-01', '2026-01-20'));
        expect(loaded.getMissingIntervals('2026-01-01', '2026-01-20'), 'a point is not missing, fetched or not').toEqual([]);

        const empty = new TimeSeriesStore<TestPoint>();
        empty.markFetched('2026-01-01', '2026-01-10');
        empty.markFetched('2026-01-11', '2026-01-20');
        expect(empty.getMissingIntervals('2026-01-01', '2026-01-10'), 'a gap inside one fetched range is not missing').toEqual([]);
        expect(empty.getMissingIntervals('2026-01-01', '2026-01-20'), 'a gap spanning two fetched ranges is still missing outside the stale state: one range has to cover it whole').toEqual([{start: '2026-01-01', end: '2026-01-20'}]);
    });
});
