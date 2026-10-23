/**
 * Unit tests for TimeSeriesStore — Generic client-side cache for time-series data.
 *
 * Tests 16–24: the stale state a price catch-up puts every store in (`markStale()`, Z-14).
 *
 * Tests 25–32: the generation of a store (N64) — the one number that says which state of the store an answer was drawn
 * over. A client cache of the backend's signal answers keeps an answer together with the generations of the stores it
 * depends on, and takes it back only while they are the same; so the generation must move whenever what the store
 * stands for may have changed (`invalidateAll()`, `invalidateRange()`, `markStale()`) and stay put when it did not
 * (`merge()`, `markFetched()`, any read).
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

// =============================================================================
//  generation — which state of the store an answer was drawn over (N64)
//
//  A signal answer comes from the backend over the prices of one or two stores.
//  The cache that keeps it files it with the stores' generations and takes it
//  back only when every one is what it was: a store that was emptied, had a
//  range invalidated or was marked stale by a price catch-up has moved on, and
//  the answer drawn over its old state must be asked again. A merge or a
//  `markFetched` only adds what the server already held, and a read changes
//  nothing, so neither may move it.
//
//  The counter is global to the app, not per store: a number is never given
//  twice, to two stores or to the same store after a change, so a store that was
//  removed and made again can never be mistaken for the one it replaced.
//
//  Red first: `generation` is read by name, so that its absence fails each case
//  with the contract in the message, and the type check does not wait for it.
//  Every "does not change" case asserts that the number exists before comparing,
//  or `undefined === undefined` would pass it for the wrong reason.
// =============================================================================

/** `store.generation`, read by name (see above). */
function generationOf(store: TimeSeriesStore<TestPoint>): number {
    const generation = (store as unknown as {generation?: unknown}).generation;
    expect(typeof generation, 'TimeSeriesStore has no numeric generation: a cache of signal answers cannot tell whether the prices an answer was drawn over have changed (N64)').toBe('number');
    return generation as number;
}

/**
 * Runs `change` and asserts the store moved to a generation nobody had: not its own before, not one of the other
 * stores', not one it had earlier. `seen` is every generation observed so far, and gains the new one.
 */
function expectFreshGeneration(store: TimeSeriesStore<TestPoint>, seen: Set<number>, what: string, change: () => void): void {
    seen.add(generationOf(store));
    change();
    const after = generationOf(store);
    expect(seen.has(after), `${what} left the store with a generation it, or another store, already had: an answer drawn over the old state would still be taken for current (N64)`).toBe(false);
    seen.add(after);
}

/** Asserts `read` leaves the generation of `store` alone. */
function expectSameGeneration(store: TimeSeriesStore<TestPoint>, what: string, read: () => unknown): void {
    const before = generationOf(store);
    read();
    expect(generationOf(store), `${what} moved the generation: the cached answers drawn over this store would be asked again for nothing (N64)`).toBe(before);
}

describe('TimeSeriesStore.generation (N64)', () => {
    // =========================================================================
    // Test 25: every store has one, from construction, and none shares it
    // =========================================================================
    it('gives every store a numeric generation from construction, and never the same one to two stores', () => {
        const stores = Array.from({length: 25}, () => new TimeSeriesStore<TestPoint>());

        const generations = stores.map(generationOf);

        expect(new Set(generations).size, 'two stores share a generation: an answer drawn over one would be taken for current over the other (N64)').toBe(generations.length);
    });

    // =========================================================================
    // Test 26: a number is never given twice
    // =========================================================================
    it('never gives a number twice: a store made after others changed or were left behind gets one nobody had', () => {
        const first = new TimeSeriesStore<TestPoint>();
        const seen = new Set<number>([generationOf(first)]);
        expectFreshGeneration(first, seen, 'invalidateAll()', () => first.invalidateAll());
        expectFreshGeneration(first, seen, 'markStale()', () => first.markStale());
        expectFreshGeneration(first, seen, 'invalidateRange()', () => first.invalidateRange('2026-01-01', '2026-01-02'));
        expect(seen.size, 'the store gave the same number twice').toBe(4);

        // `first` is not read again: the numbers it held are gone with it, and still taken.
        const later = new TimeSeriesStore<TestPoint>();

        expect(seen.has(generationOf(later)), 'a store made later got a number an earlier store already had: removing a store and making it again would hand the new one the old answers (N64)').toBe(false);
    });

    // =========================================================================
    // Test 27: invalidateAll moves it, empty or not
    // =========================================================================
    it('moves to a fresh generation on invalidateAll(), whether the store holds points or not', () => {
        const other = new TimeSeriesStore<TestPoint>();
        const otherGeneration = generationOf(other);
        const seen = new Set<number>([otherGeneration]);

        const empty = new TimeSeriesStore<TestPoint>();
        expectFreshGeneration(empty, seen, 'invalidateAll() on an empty store', () => empty.invalidateAll());

        const filled = new TimeSeriesStore<TestPoint>();
        filled.merge(everyDay('2026-01-01', '2026-01-10'));
        filled.markFetched('2026-01-01', '2026-01-10');
        expectFreshGeneration(filled, seen, 'invalidateAll() on a loaded store', () => filled.invalidateAll());
        expectFreshGeneration(filled, seen, 'a second invalidateAll()', () => filled.invalidateAll());

        expect(generationOf(other), 'the other store did not take part: its generation stays').toBe(otherGeneration);
    });

    // =========================================================================
    // Test 28: invalidateRange moves it even when the range held nothing
    // =========================================================================
    it('moves to a fresh generation on invalidateRange(), even for a range that held no point and on an empty store', () => {
        const seen = new Set<number>();
        const store = new TimeSeriesStore<TestPoint>();
        store.merge(everyDay('2026-01-01', '2026-01-10'));
        store.markFetched('2026-01-01', '2026-01-10');

        expectFreshGeneration(store, seen, 'invalidateRange() over points', () => store.invalidateRange('2026-01-04', '2026-01-06'));
        expect(store.size, 'premise: the range held points and they went').toBe(7);
        expectFreshGeneration(store, seen, 'invalidateRange() over a range that held no point (a fetched mark may be all it drops)', () => store.invalidateRange('2025-06-01', '2025-06-30'));
        expect(store.size, 'premise: nothing was there to delete').toBe(7);

        const empty = new TimeSeriesStore<TestPoint>();
        expectFreshGeneration(empty, seen, 'invalidateRange() on an empty store', () => empty.invalidateRange('2026-01-01', '2026-01-31'));
    });

    // =========================================================================
    // Test 29: markStale moves it, every time
    // =========================================================================
    it('moves to a fresh generation on markStale(), and again on a second markStale()', () => {
        const seen = new Set<number>();
        const store = new TimeSeriesStore<TestPoint>();
        store.merge(everyDay('2026-01-01', '2026-01-05'));
        store.markFetched('2026-01-01', '2026-01-05');

        expectFreshGeneration(store, seen, 'markStale()', () => store.markStale());
        expectFreshGeneration(store, seen, 'a second markStale(): what was fetched after the first is stale in turn', () => {
            store.markFetched('2026-01-01', '2026-01-05');
            store.markStale();
        });

        const empty = new TimeSeriesStore<TestPoint>();
        expectFreshGeneration(empty, seen, 'markStale() on an empty store', () => empty.markStale());
    });

    // =========================================================================
    // Test 30: merge and markFetched leave it
    // =========================================================================
    it('keeps its generation on merge() and markFetched(): they add what the server already held', () => {
        const store = new TimeSeriesStore<TestPoint>();
        const points = [pt('2026-01-01', 1), pt('2026-01-02', 1.1), pt('2026-01-03', 1.2)];

        expectSameGeneration(store, 'merge() into an empty store', () => store.merge(points));
        expectSameGeneration(store, 'merge() of the same points again', () => store.merge(points));
        expectSameGeneration(store, 'merge() that replaces a point with another value', () => store.merge([pt('2026-01-02', 9.9)]));
        expectSameGeneration(store, 'merge() of nothing', () => store.merge([]));
        expectSameGeneration(store, 'markFetched()', () => store.markFetched('2026-01-01', '2026-01-03'));
        expectSameGeneration(store, 'markFetched() of the same range again', () => store.markFetched('2026-01-01', '2026-01-03'));

        // The same two, in the stale state a catch-up leaves: a fetch that follows the mark is not a change either.
        store.markStale();
        expectSameGeneration(store, 'merge() after markStale()', () => store.merge([pt('2026-01-04', 2)]));
        expectSameGeneration(store, 'markFetched() after markStale()', () => store.markFetched('2026-01-01', '2026-01-04'));
    });

    // =========================================================================
    // Test 31: no read moves it
    // =========================================================================
    it('keeps its generation on every read: get, has, getRange, getMissingIntervals, getAllSorted and size, fresh or stale', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge(everyDay('2026-01-01', '2026-01-05'));
        store.markFetched('2026-01-01', '2026-01-03');

        const reads: Array<[string, () => unknown]> = [
            ['get()', () => store.get('2026-01-02')],
            ['has()', () => store.has('2026-01-09')],
            ['getRange()', () => store.getRange('2026-01-01', '2026-01-09')],
            ['getMissingIntervals()', () => store.getMissingIntervals('2026-01-01', '2026-01-09')],
            ['getAllSorted()', () => store.getAllSorted()],
            ['size', () => store.size],
        ];
        for (const [what, read] of reads) expectSameGeneration(store, what, read);

        // In the stale state getMissingIntervals walks every day by coverage: still a read.
        store.markStale();
        for (const [what, read] of reads) expectSameGeneration(store, `${what} on a stale store`, read);
    });

    // =========================================================================
    // Test 32: a change belongs to its store
    // =========================================================================
    it('moves only the generation of the store that changed', () => {
        const changed = new TimeSeriesStore<TestPoint>();
        const neighbour = new TimeSeriesStore<TestPoint>();
        const before = generationOf(neighbour);

        changed.invalidateAll();
        changed.markStale();
        changed.invalidateRange('2026-01-01', '2026-01-02');

        expect(generationOf(neighbour), 'a change of one store moved the generation of another: the answers drawn over it would be asked again for nothing (N64)').toBe(before);
    });
});

// =============================================================================
//  isStale — whether a catch-up marked the store (Y5-1, plan «Z-14b + Z-15»)
// =============================================================================
//
//  A page that finds its range missing from a stale store, and holds points for it, shows those points at once and asks the
//  server in background, with no loading state: the store tells which of the two it is. Read-only: only `markStale()` sets it,
//  only `invalidateAll()` ends it (the points are then forgotten too), and a fetch covering the range clears the *gaps*, not
//  the mark — a later catch-up marks it again anyway.
//
//  Red first: `isStale` does not exist.

describe('TimeSeriesStore.isStale (Y5-1)', () => {
    it('is false for a store nobody marked, whatever it holds', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1)]);
        store.markFetched('2024-01-01', '2024-01-01');

        expect(store.isStale).toBe(false);
    });

    it('is true once markStale() ran, and the points are still readable', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1), pt('2024-01-02', 2)]);
        store.markFetched('2024-01-01', '2024-01-02');

        store.markStale();

        expect(store.isStale).toBe(true);
        expect(store.getRange('2024-01-01', '2024-01-02').data).toHaveLength(2);
        expect(store.getMissingIntervals('2024-01-01', '2024-01-02'), 'the whole range counts as missing').toEqual([{start: '2024-01-01', end: '2024-01-02'}]);
    });

    it('is false again after invalidateAll()', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1)]);
        store.markStale();

        store.invalidateAll();

        expect(store.isStale).toBe(false);
    });

    it('stays true when a fetch covers the range: the mark is the store’s, the gaps are the range’s', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1)]);
        store.markStale();

        store.markFetched('2024-01-01', '2024-01-01');

        expect(store.isStale).toBe(true);
        expect(store.getMissingIntervals('2024-01-01', '2024-01-01')).toEqual([]);
    });
});
