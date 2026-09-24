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

// ---------------------------------------------------------------------------
// Keeper precedence against database / bulk-editor collisions
// ---------------------------------------------------------------------------

/**
 * The two verdicts a row carries *besides* its in-batch role: against the database
 * (`dbDuplicateStatus`) and against the bulk editor's unsaved rows (`pendingMatchStatus`).
 * The in-batch pass rewrites `duplicateStatus` to `pending_duplicate` on every secondary, so
 * that field cannot say whether a row really collides with something outside the batch;
 * these two are never rewritten by it. Declared here as well so the fixtures type-check
 * whether or not `MergedTx` already carries the same optional fields.
 */
type CollisionVerdicts = {
    dbDuplicateStatus?: 'likely' | 'possible';
    pendingMatchStatus?: 'pending_duplicate' | 'pending_possible_duplicate';
};

/** A database match as `/parse` or `/import/duplicates` reports it. The resolver never reads it. */
function dbMatch(existingTxId: number, description: string, verdict: 'likely' | 'possible'): MergedTx['dupMatches'][number] {
    return {
        existing_tx_id: existingTxId,
        tx_date: '2024-01-03',
        tx_type: 'BUY',
        tx_quantity: '3',
        tx_cash_amount: '-30',
        tx_cash_currency: 'EUR',
        tx_description: description,
        match_level: verdict === 'likely' ? 'likely_with_asset' : 'possible_with_asset',
    };
}

/**
 * A row as the wizard holds it once its collision verdicts are known: the status, the
 * evidence (DB match or matched editor row) and the auto-selection they imply. A firm verdict
 * (`likely`, `pending_duplicate`) arrives deselected; a weak one stays selected.
 */
function twin(index: number, sourceFileId: string, description: string, verdicts: CollisionVerdicts = {}): MergedTx {
    const row: MergedTx & CollisionVerdicts = {...mt(index, sourceFileId, description), ...verdicts};
    if (verdicts.dbDuplicateStatus) {
        row.duplicateStatus = verdicts.dbDuplicateStatus;
        row.dupMatches = [dbMatch(900 + index, description, verdicts.dbDuplicateStatus)];
    }
    if (verdicts.pendingMatchStatus) {
        row.duplicateStatus = verdicts.pendingMatchStatus;
        row.dupPendingMatch = {description} as MergedTx['tx'];
    }
    row.selected = verdicts.dbDuplicateStatus !== 'likely' && verdicts.pendingMatchStatus !== 'pending_duplicate';
    return row;
}

describe('keeper precedence: a twin that collides firmly (DB likely / editor pending_duplicate) is never the default keeper', () => {
    const priority = ['fA', 'fB'];
    const g = group('k', [0, 1]);

    describe('U1: only the higher-priority twin collides firmly with the database', () => {
        const a = twin(0, 'fA', 'Twin', {dbDuplicateStatus: 'likely'});
        const b = twin(1, 'fB', 'Twin');
        const tx = [a, b];

        it('groupPartitions elects the non-colliding lower-priority twin as partition primary', () => {
            const parts = groupPartitions(g, tx, priority);
            expect(parts).toHaveLength(1);
            expect(parts[0].primaryIndex).toBe(b.index);
        });

        it('defaultKeeperIndices keeps the non-colliding twin, not the colliding higher-priority one', () => {
            expect(defaultKeeperIndices(g, tx, priority)).toEqual(new Set([b.index]));
        });

        it('resolverSelectionFor without a manual choice deselects the colliding twin and selects its twin', () => {
            expect(resolverSelectionFor(g, a.index, tx, priority, false, {})).toBe(false);
            expect(resolverSelectionFor(g, b.index, tx, priority, false, {})).toBe(true);
        });

        it('re-applying after a priority reorder reads the verdict fields, not the in-batch pending_duplicate marker', () => {
            // State after a first pass over three copies with priority [fA, fB, fC]: A (in the DB)
            // lost the keeper role to B, and the pass rewrote `duplicateStatus` on both secondaries
            // (A and C) to its in-batch marker. A still collides; C collides with nothing.
            const a3: MergedTx = {...twin(0, 'fA', 'Twin', {dbDuplicateStatus: 'likely'}), duplicateStatus: 'pending_duplicate', isDupKeeper: false, dupKeeperIndex: 1};
            const b3: MergedTx = {...twin(1, 'fB', 'Twin'), isDupKeeper: true};
            const c3: MergedTx = {...twin(2, 'fC', 'Twin'), duplicateStatus: 'pending_duplicate', selected: false, isDupKeeper: false, dupKeeperIndex: 1};
            const g3 = group('k3', [0, 1, 2]);
            // The user then drags fC above fB.
            const reordered = ['fA', 'fC', 'fB'];
            expect(groupPartitions(g3, [a3, b3, c3], reordered)[0].primaryIndex).toBe(c3.index);
            expect(defaultKeeperIndices(g3, [a3, b3, c3], reordered)).toEqual(new Set([c3.index]));
        });
    });

    describe('U2: every twin collides firmly', () => {
        const variants: Array<{name: string; b: CollisionVerdicts}> = [
            {name: '(i) both twins are already in the database', b: {dbDuplicateStatus: 'likely'}},
            {name: '(ii) one twin is in the database, the other is pending in the bulk editor', b: {pendingMatchStatus: 'pending_duplicate'}},
        ];

        for (const variant of variants) {
            describe(variant.name, () => {
                const a = twin(0, 'fA', 'Twin', {dbDuplicateStatus: 'likely'});
                const b = twin(1, 'fB', 'Twin', variant.b);
                const tx = [a, b];

                it('defaultKeeperIndices keeps no copy at all', () => {
                    expect(defaultKeeperIndices(g, tx, priority)).toEqual(new Set());
                });

                it('resolverSelectionFor without a manual choice selects neither copy', () => {
                    expect(resolverSelectionFor(g, a.index, tx, priority, false, {})).toBe(false);
                    expect(resolverSelectionFor(g, b.index, tx, priority, false, {})).toBe(false);
                });

                it('the partition primary (display only) stays the highest-priority twin', () => {
                    expect(groupPartitions(g, tx, priority)[0].primaryIndex).toBe(a.index);
                });
            });
        }
    });

    describe('U3: controls — what must NOT move the keeper', () => {
        it('(a) with no collision at all the highest-priority twin is the keeper', () => {
            const tx = [twin(0, 'fA', 'Twin'), twin(1, 'fB', 'Twin')];
            expect(groupPartitions(g, tx, priority)[0].primaryIndex).toBe(0);
            expect(defaultKeeperIndices(g, tx, priority)).toEqual(new Set([0]));
            expect(resolverSelectionFor(g, 0, tx, priority, false, {})).toBe(true);
            expect(resolverSelectionFor(g, 1, tx, priority, false, {})).toBe(false);
        });

        it('(b) a weak database verdict ("possible") does not block the higher-priority twin', () => {
            const tx = [twin(0, 'fA', 'Twin', {dbDuplicateStatus: 'possible'}), twin(1, 'fB', 'Twin')];
            expect(groupPartitions(g, tx, priority)[0].primaryIndex).toBe(0);
            expect(defaultKeeperIndices(g, tx, priority)).toEqual(new Set([0]));
            expect(resolverSelectionFor(g, 0, tx, priority, false, {})).toBe(true);
            expect(resolverSelectionFor(g, 1, tx, priority, false, {})).toBe(false);
        });

        it('(c) a weak editor verdict ("pending_possible_duplicate") does not block the higher-priority twin', () => {
            const tx = [twin(0, 'fA', 'Twin', {pendingMatchStatus: 'pending_possible_duplicate'}), twin(1, 'fB', 'Twin')];
            expect(groupPartitions(g, tx, priority)[0].primaryIndex).toBe(0);
            expect(defaultKeeperIndices(g, tx, priority)).toEqual(new Set([0]));
            expect(resolverSelectionFor(g, 0, tx, priority, false, {})).toBe(true);
            expect(resolverSelectionFor(g, 1, tx, priority, false, {})).toBe(false);
        });

        it('(d) an explicit manual choice is respected even for a firmly colliding twin', () => {
            const tx = [twin(0, 'fA', 'Twin', {dbDuplicateStatus: 'likely'}), twin(1, 'fB', 'Twin')];
            const selections = {0: true, 1: false};
            expect(resolverSelectionFor(g, 0, tx, priority, true, selections)).toBe(true);
            expect(resolverSelectionFor(g, 1, tx, priority, true, selections)).toBe(false);
        });

        it("(e) a firm collision in one description-partition leaves the other partition's keeper alone", () => {
            // One key, two descriptions: the 'Twin' pair collides with the DB on its fA copy, the
            // 'Other' pair collides with nothing and keeps its highest-priority copy.
            const tx = [twin(0, 'fA', 'Twin', {dbDuplicateStatus: 'likely'}), twin(1, 'fB', 'Twin'), twin(2, 'fA', 'Other'), twin(3, 'fB', 'Other')];
            const g4 = group('k4', [0, 1, 2, 3]);
            const other = groupPartitions(g4, tx, priority).find((p) => p.memberIndices.includes(2));
            expect(other?.primaryIndex).toBe(2);
            const keepers = defaultKeeperIndices(g4, tx, priority);
            expect(keepers.has(2)).toBe(true);
            expect(keepers.has(3)).toBe(false);
            expect(resolverSelectionFor(g4, 2, tx, priority, false, {})).toBe(true);
            expect(resolverSelectionFor(g4, 3, tx, priority, false, {})).toBe(false);
        });
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
