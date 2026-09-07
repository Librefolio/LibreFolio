import {describe, it, expect} from 'vitest';
import {groupPartitions, defaultKeeperIndices, resolverSelectionFor, outlierIndexSet} from './importDuplicateResolver';
import type {DuplicateGroup, MergedTx} from './importTypes';

/**
 * Minimal MergedTx factory. Only the fields the resolver reads matter: index, sourceFileId,
 * and tx.description (via normalizeDedupDescription). Everything else is filler.
 */
function mt(index: number, sourceFileId: string, description: string): MergedTx {
    return {
        index,
        sourceFileId,
        tx: {description} as MergedTx['tx'],
        selected: true,
        duplicateStatus: 'unique',
        dupMatches: [],
        todos: [],
    };
}

function group(key: string, memberIndices: number[]): DuplicateGroup {
    return {key, memberIndices, tier: 'sure'};
}

describe('groupPartitions', () => {
    it('returns [] when no member index resolves to a row', () => {
        const g = group('k', [10, 11]);
        expect(groupPartitions(g, [mt(1, 'f1', 'x')], ['f1'])).toEqual([]);
    });

    it('folds same-description cross-file twins into ONE partition; primary is highest-priority file', () => {
        const tx = [mt(0, 'fB', 'Acme Corp'), mt(1, 'fA', 'Acme Corp')];
        const g = group('k', [0, 1]);
        // priority order: fA before fB → fA (index 1) is primary
        const parts = groupPartitions(g, tx, ['fA', 'fB']);
        expect(parts).toHaveLength(1);
        expect(parts[0].primaryIndex).toBe(1);
        expect(parts[0].memberIndices.sort()).toEqual([0, 1]);
        expect(parts[0].crossFile).toBe(true);
    });

    it('keeps genuinely-distinct rows (different descriptions) as separate single-member partitions', () => {
        const tx = [mt(0, 'fA', 'Apple'), mt(1, 'fA', 'Banana')];
        const parts = groupPartitions(group('k', [0, 1]), tx, ['fA']);
        expect(parts).toHaveLength(2);
        expect(parts.every((p) => p.crossFile === false)).toBe(true);
    });

    it('normalizes whitespace/case when partitioning descriptions', () => {
        const tx = [mt(0, 'fA', 'ACME  corp'), mt(1, 'fB', 'acme corp')];
        const parts = groupPartitions(group('k', [0, 1]), tx, ['fA', 'fB']);
        expect(parts).toHaveLength(1);
    });

    it('crossFile is false when the partition is confined to one file', () => {
        const tx = [mt(0, 'fA', 'Dup'), mt(1, 'fA', 'Dup')];
        const parts = groupPartitions(group('k', [0, 1]), tx, ['fA']);
        expect(parts).toHaveLength(1);
        expect(parts[0].crossFile).toBe(false);
    });

    it('ranks a member from an unknown (not-in-priority) file as lowest priority', () => {
        // fUnknown is absent from priorityIds → rank MAX_SAFE_INTEGER; fA wins primary.
        const tx = [mt(0, 'fUnknown', 'Same'), mt(1, 'fA', 'Same')];
        const parts = groupPartitions(group('k', [0, 1]), tx, ['fA']);
        expect(parts[0].primaryIndex).toBe(1);
    });

    it('when ALL members are from unknown files the reduce still returns a stable primary', () => {
        const tx = [mt(7, 'fX', 'Same'), mt(3, 'fY', 'Same')];
        const parts = groupPartitions(group('k', [7, 3]), tx, []);
        expect(parts).toHaveLength(1);
        // both rank MAX → reduce keeps the seed (first member, index 7)
        expect(parts[0].primaryIndex).toBe(7);
        expect(parts[0].crossFile).toBe(true);
    });
});

describe('defaultKeeperIndices', () => {
    it('keeps exactly one primary per description-partition', () => {
        const tx = [mt(0, 'fB', 'Twin'), mt(1, 'fA', 'Twin'), mt(2, 'fA', 'Other')];
        const keepers = defaultKeeperIndices(group('k', [0, 1, 2]), tx, ['fA', 'fB']);
        // Twin partition keeps fA(1); Other partition keeps 2. Row 0 is the dropped twin.
        expect(keepers.has(1)).toBe(true);
        expect(keepers.has(2)).toBe(true);
        expect(keepers.has(0)).toBe(false);
    });

    it('is empty when the group resolves to no rows', () => {
        expect(defaultKeeperIndices(group('k', [99]), [mt(0, 'fA', 'x')], ['fA']).size).toBe(0);
    });
});

describe('resolverSelectionFor', () => {
    const tx = [mt(0, 'fB', 'Twin'), mt(1, 'fA', 'Twin')];
    const g = group('k', [0, 1]);

    it('uses the manual selection map when manualChoice is true', () => {
        // Manual overrides the default: keep the dropped twin (row 0), drop the primary (row 1).
        const selections = {0: true, 1: false};
        expect(resolverSelectionFor(g, 0, tx, ['fA', 'fB'], true, selections)).toBe(true);
        expect(resolverSelectionFor(g, 1, tx, ['fA', 'fB'], true, selections)).toBe(false);
    });

    it('a manual choice for a row not present in the selection map defaults to false', () => {
        expect(resolverSelectionFor(g, 0, tx, ['fA', 'fB'], true, {})).toBe(false);
    });

    it('falls back to the default keeper set when manualChoice is false', () => {
        // Default: fA(1) is the primary → kept; row 0 dropped. selections map is ignored.
        expect(resolverSelectionFor(g, 1, tx, ['fA', 'fB'], false, {0: true})).toBe(true);
        expect(resolverSelectionFor(g, 0, tx, ['fA', 'fB'], false, {0: true})).toBe(false);
    });
});

describe('outlierIndexSet', () => {
    const keyOf = (m: MergedTx) => String(m.tx.description ?? '');

    it('returns an empty set when all members share the same key', () => {
        const members = [mt(0, 'f', 'A'), mt(1, 'f', 'A'), mt(2, 'f', 'A')];
        expect(outlierIndexSet(members, keyOf).size).toBe(0);
    });

    it('returns an empty set for a single member (counts.size <= 1)', () => {
        expect(outlierIndexSet([mt(0, 'f', 'A')], keyOf).size).toBe(0);
    });

    it('returns an empty set for no members', () => {
        expect(outlierIndexSet([], keyOf).size).toBe(0);
    });

    it('flags the minority members as outliers', () => {
        // A×3, B×1 → majority A, outlier is the B row (index 3)
        const members = [mt(0, 'f', 'A'), mt(1, 'f', 'A'), mt(2, 'f', 'A'), mt(3, 'f', 'B')];
        const out = outlierIndexSet(members, keyOf);
        expect([...out]).toEqual([3]);
    });

    it('on a tie keeps the first-seen key as majority and flags the rest', () => {
        // A×1 then B×1: best starts at -1, A becomes majority (1 > -1), B not (1 !> 1) → B is outlier.
        const members = [mt(0, 'f', 'A'), mt(1, 'f', 'B')];
        expect([...outlierIndexSet(members, keyOf)]).toEqual([1]);
    });

    it('supports a compound key function (e.g. cash amount|code)', () => {
        const cashKey = (m: MergedTx) => {
            const cash = m.tx.cash as {code: string; amount: string} | undefined;
            return cash ? `${Number(cash.amount).toFixed(2)}|${cash.code}` : '';
        };
        const withCash = (index: number, amount: string, code: string): MergedTx => {
            const row = mt(index, 'f', 'x');
            row.tx = {cash: {amount, code}} as MergedTx['tx'];
            return row;
        };
        const members = [withCash(0, '100', 'EUR'), withCash(1, '100', 'EUR'), withCash(2, '250', 'EUR')];
        expect([...outlierIndexSet(members, cashKey)]).toEqual([2]);
    });
});
