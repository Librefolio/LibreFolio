/**
 * Unit tests for TimeSeriesStore — Generic client-side cache for time-series data.
 */
import {describe, expect, it} from 'vitest';
import type {TimeSeriesPoint} from '../TimeSeriesStore';
import {TimeSeriesStore} from '../TimeSeriesStore';

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
        store.merge([
            pt('2024-01-01', 1.0),
            pt('2024-01-02', 1.1),
            pt('2024-01-03', 1.2),
        ]);
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
    // Test 5: getMissingIntervals is wrapper for getRange().gaps
    // =========================================================================
    it('getMissingIntervals equals getRange().gaps', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([pt('2024-01-01', 1.0), pt('2024-01-03', 1.2)]);
        const gaps = store.getMissingIntervals('2024-01-01', '2024-01-03');
        const rangeGaps = store.getRange('2024-01-01', '2024-01-03').gaps;
        expect(gaps).toEqual(rangeGaps);
    });

    // =========================================================================
    // Test 6: invalidateRange removes only the specified range
    // =========================================================================
    it('invalidateRange removes only the specified range', () => {
        const store = new TimeSeriesStore<TestPoint>();
        store.merge([
            pt('2024-01-01', 1.0),
            pt('2024-01-02', 1.1),
            pt('2024-01-03', 1.2),
            pt('2024-01-04', 1.3),
        ]);
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
        store.merge([
            pt('2024-01-03', 1.2),
            pt('2024-01-01', 1.0),
            pt('2024-01-02', 1.1),
        ]);
        const sorted = store.getAllSorted();
        expect(sorted.map(d => d.date)).toEqual(['2024-01-01', '2024-01-02', '2024-01-03']);
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
        store.merge([
            pt('2024-01-01', 1.0),
            pt('2024-01-05', 1.4),
            pt('2024-01-10', 1.9),
        ]);
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

