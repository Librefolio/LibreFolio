/**
 * The rule of the bulk actions (plan 77, SEL-A; the developer's Q-SEL-1, Q-SEL-9, Q-SEL-12, Q-SEL-17 of 19/11/2026):
 * an action is **hidden** when no selected row can take it, or when on those rows it makes no sense here; **off with its
 * reason** when it could but is blocked; **on** otherwise. It always carries the number of rows it acts on, and acts on
 * those rows only.
 */
import {describe, expect, it, vi} from 'vitest';

import type {BulkAction} from './types';
import {resolveSelectionAction, resolveSelectionActions} from './selectionActions';

interface Row {
    id: number;
    kind: 'unique' | 'none' | 'several';
}

const rows: Row[] = [
    {id: 1, kind: 'unique'},
    {id: 2, kind: 'none'},
    {id: 3, kind: 'unique'},
    {id: 4, kind: 'several'},
];

const icon = {} as never;

function action(over: Partial<BulkAction<Row>> = {}): BulkAction<Row> {
    return {id: 'link', icon, label: 'Link', onClick: vi.fn(), ...over};
}

describe('resolveSelectionAction', () => {
    it('without a row test, an action takes every selected row and says how many', () => {
        const resolved = resolveSelectionAction(action(), rows);
        expect(resolved.state).toBe('on');
        expect(resolved.state === 'on' && resolved.count).toBe(4);
        expect(resolved.state === 'on' && resolved.rows.map((row) => row.id)).toEqual([1, 2, 3, 4]);
    });

    it('acts on the selected rows it can take only, and the number is theirs', () => {
        const resolved = resolveSelectionAction(action({appliesTo: (row) => row.kind === 'unique'}), rows);
        expect(resolved.state).toBe('on');
        if (resolved.state !== 'on') return;
        expect(resolved.count).toBe(2);
        expect(resolved.rows.map((row) => row.id)).toEqual([1, 3]);
    });

    it('the number is there even when the action takes every selected row (Q-SEL-1)', () => {
        const resolved = resolveSelectionAction(action({appliesTo: (row) => row.kind === 'unique'}), [rows[0], rows[2]]);
        expect(resolved.state === 'on' && resolved.count).toBe(2);
    });

    it('is hidden when no selected row can take it', () => {
        expect(resolveSelectionAction(action({appliesTo: (row) => row.kind === 'unique'}), [rows[1], rows[3]]).state).toBe('hidden');
    });

    it('is hidden with no selection', () => {
        expect(resolveSelectionAction(action(), []).state).toBe('hidden');
    });

    it('is hidden when, on the rows it would take, it makes no sense here (Q-SEL-17: Balance at 100 %)', () => {
        const pointless = vi.fn(() => true);
        const resolved = resolveSelectionAction(action({appliesTo: (row) => row.kind === 'unique', pointless}), rows);
        expect(resolved.state).toBe('hidden');
        expect(pointless).toHaveBeenCalledWith([rows[0], rows[2]]);
    });

    it('is off with its reason when it could act but is blocked, still saying how many rows it would take', () => {
        const blocked = vi.fn(() => ({hint: () => 'Only adjacent periods merge', reason: 'not_adjacent'}));
        const resolved = resolveSelectionAction(action({appliesTo: (row) => row.kind === 'unique', blocked}), rows);
        expect(resolved.state).toBe('off');
        if (resolved.state !== 'off') return;
        expect(resolved.count).toBe(2);
        expect(resolved.hint).toBe('Only adjacent periods merge');
        expect(resolved.reason).toBe('not_adjacent');
        expect(blocked).toHaveBeenCalledWith([rows[0], rows[2]]);
    });

    it('a block that answers null leaves the action on', () => {
        expect(resolveSelectionAction(action({blocked: () => null}), rows).state).toBe('on');
    });

    it('hidden wins over blocked: a pointless action is never shown off', () => {
        const blocked = vi.fn(() => ({hint: 'x', reason: 'y'}));
        expect(resolveSelectionAction(action({pointless: () => true, blocked}), rows).state).toBe('hidden');
        expect(blocked).not.toHaveBeenCalled();
    });

    it('a minimum selection under which the action has nothing to do hides it', () => {
        expect(resolveSelectionAction(action({minSelection: 2, appliesTo: (row) => row.kind === 'unique'}), [rows[0], rows[1]]).state).toBe('hidden');
        expect(resolveSelectionAction(action({minSelection: 2, appliesTo: (row) => row.kind === 'unique'}), rows).state).toBe('on');
    });
});

describe('resolveSelectionActions', () => {
    it('keeps the order of the actions and leaves the hidden ones out', () => {
        const link = action({id: 'link', appliesTo: (row) => row.kind === 'unique'});
        const create = action({id: 'create', appliesTo: (row) => row.kind === 'none'});
        const remove = action({id: 'delete', variant: 'danger'});
        expect(resolveSelectionActions([link, create, remove], [rows[0], rows[2]]).map((item) => item.action.id)).toEqual(['link', 'delete']);
        expect(resolveSelectionActions([link, create, remove], [rows[1]]).map((item) => item.action.id)).toEqual(['create', 'delete']);
        expect(resolveSelectionActions([link, create], [rows[3]])).toEqual([]);
    });
});
