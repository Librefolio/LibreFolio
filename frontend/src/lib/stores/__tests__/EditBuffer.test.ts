/**
 * Unit tests for EditBuffer — Bidirectional edit buffer for pending chart modifications.
 */
import {describe, expect, it, vi} from 'vitest';
import {EditBuffer} from '../core/EditBuffer';
import type {TimeSeriesPoint} from '../core/TimeSeriesStore';

interface TestPoint extends TimeSeriesPoint {
    date: string;
    value: number;
}

function pt(date: string, value: number): TestPoint {
    return {date, value};
}

describe('EditBuffer', () => {
    // =========================================================================
    // Test 1: add new entry
    // =========================================================================
    it('add inserts a new entry', () => {
        const buf = new EditBuffer<TestPoint>();
        const edit = buf.add(pt('2024-01-01', 1.0), 'click');
        expect(buf.size).toBe(1);
        expect(buf.hasChanges).toBe(true);
        expect(edit.point.date).toBe('2024-01-01');
        expect(edit.source).toBe('click');
        expect(edit.isNew).toBe(true);
    });

    // =========================================================================
    // Test 2: add same date → upsert (replaces, preserves csvLineNumber)
    // =========================================================================
    it('add same date replaces existing entry, preserving csvLineNumber', () => {
        const buf = new EditBuffer<TestPoint>();
        const first = buf.add(pt('2024-01-01', 1.0), 'click');
        const lineNum = first.csvLineNumber;
        const second = buf.add(pt('2024-01-01', 2.0), 'form');
        expect(buf.size).toBe(1);
        expect(second.point.value).toBe(2.0);
        expect(second.csvLineNumber).toBe(lineNum);
    });

    // =========================================================================
    // Test 3: update existing entry
    // =========================================================================
    it('update modifies an existing entry', () => {
        const buf = new EditBuffer<TestPoint>();
        const edit = buf.add(pt('2024-01-01', 1.0), 'click');
        const updated = buf.update(edit.id, pt('2024-01-01', 5.0));
        expect(updated).toBe(true);
        expect(buf.getById(edit.id)?.point.value).toBe(5.0);
    });

    // =========================================================================
    // Test 4: remove by ID
    // =========================================================================
    it('remove by ID decrements size and cleans dateIndex', () => {
        const buf = new EditBuffer<TestPoint>();
        const e1 = buf.add(pt('2024-01-01', 1.0), 'click');
        buf.add(pt('2024-01-02', 2.0), 'click');
        expect(buf.size).toBe(2);
        const removed = buf.remove(e1.id);
        expect(removed).toBe(true);
        expect(buf.size).toBe(1);
        expect(buf.getByDate('2024-01-01')).toBeUndefined();
    });

    // =========================================================================
    // Test 5: getByDate
    // =========================================================================
    it('getByDate returns correct entry', () => {
        const buf = new EditBuffer<TestPoint>();
        buf.add(pt('2024-01-01', 1.0), 'click');
        buf.add(pt('2024-01-02', 2.0), 'form');
        const entry = buf.getByDate('2024-01-02');
        expect(entry).toBeDefined();
        expect(entry!.point.value).toBe(2.0);
        expect(entry!.source).toBe('form');
    });

    // =========================================================================
    // Test 6: getAll returns sorted by csvLineNumber
    // =========================================================================
    it('getAll returns entries sorted by csvLineNumber', () => {
        const buf = new EditBuffer<TestPoint>();
        buf.add(pt('2024-01-03', 3.0), 'click');
        buf.add(pt('2024-01-01', 1.0), 'click');
        buf.add(pt('2024-01-02', 2.0), 'click');
        const all = buf.getAll();
        expect(all).toHaveLength(3);
        // CSV line numbers are assigned in order of add() calls
        expect(all[0].point.date).toBe('2024-01-03');
        expect(all[1].point.date).toBe('2024-01-01');
        expect(all[2].point.date).toBe('2024-01-02');
    });

    // =========================================================================
    // Test 7: clear resets everything
    // =========================================================================
    it('clear resets size and hasChanges', () => {
        const buf = new EditBuffer<TestPoint>();
        buf.add(pt('2024-01-01', 1.0), 'click');
        buf.add(pt('2024-01-02', 2.0), 'click');
        expect(buf.hasChanges).toBe(true);
        buf.clear();
        expect(buf.size).toBe(0);
        expect(buf.hasChanges).toBe(false);
    });

    // =========================================================================
    // Test 8: onChange callback is invoked on add/update/remove
    // =========================================================================
    it('onChange callback is invoked on add, update, remove', () => {
        const buf = new EditBuffer<TestPoint>();
        const cb = vi.fn();
        buf.onChange(cb);

        const edit = buf.add(pt('2024-01-01', 1.0), 'click');
        expect(cb).toHaveBeenCalledTimes(1);

        buf.update(edit.id, pt('2024-01-01', 2.0));
        expect(cb).toHaveBeenCalledTimes(2);

        buf.remove(edit.id);
        expect(cb).toHaveBeenCalledTimes(3);
    });

    // =========================================================================
    // Test 9: onChange unsubscribe stops notifications
    // =========================================================================
    it('onChange unsubscribe stops notifications', () => {
        const buf = new EditBuffer<TestPoint>();
        const cb = vi.fn();
        const unsub = buf.onChange(cb);

        buf.add(pt('2024-01-01', 1.0), 'click');
        expect(cb).toHaveBeenCalledTimes(1);

        unsub();
        buf.add(pt('2024-01-02', 2.0), 'click');
        expect(cb).toHaveBeenCalledTimes(1); // Not called again
    });

    // =========================================================================
    // Test 10: getByDate returns undefined for missing date
    // =========================================================================
    it('getByDate returns undefined for missing date', () => {
        const buf = new EditBuffer<TestPoint>();
        buf.add(pt('2024-01-01', 1.0), 'click');
        expect(buf.getByDate('2024-01-02')).toBeUndefined();
    });

    // =========================================================================
    // Test 11: Multiple sources (click/csv/form) tracked correctly
    // =========================================================================
    it('multiple sources are tracked correctly', () => {
        const buf = new EditBuffer<TestPoint>();
        buf.add(pt('2024-01-01', 1.0), 'click');
        buf.add(pt('2024-01-02', 2.0), 'csv');
        buf.add(pt('2024-01-03', 3.0), 'form');
        const all = buf.getAll();
        expect(all[0].source).toBe('click');
        expect(all[1].source).toBe('csv');
        expect(all[2].source).toBe('form');
    });

    // =========================================================================
    // Test 12: replaceFromCsv replaces CSV edits but preserves click/form edits
    // =========================================================================
    it('replaceFromCsv replaces CSV edits but preserves click/form edits', () => {
        const buf = new EditBuffer<TestPoint>();
        buf.add(pt('2024-01-01', 1.0), 'click');
        buf.add(pt('2024-01-02', 2.0), 'csv');
        buf.add(pt('2024-01-03', 3.0), 'csv');
        expect(buf.size).toBe(3);

        // Replace CSV edits with new ones
        buf.replaceFromCsv([pt('2024-01-04', 4.0), pt('2024-01-05', 5.0)]);

        // Click edit should still be there
        expect(buf.getByDate('2024-01-01')).toBeDefined();
        // Old CSV edits removed
        expect(buf.getByDate('2024-01-02')).toBeUndefined();
        expect(buf.getByDate('2024-01-03')).toBeUndefined();
        // New CSV edits present
        expect(buf.getByDate('2024-01-04')).toBeDefined();
        expect(buf.getByDate('2024-01-05')).toBeDefined();
        expect(buf.size).toBe(3); // 1 click + 2 new csv
    });
});
