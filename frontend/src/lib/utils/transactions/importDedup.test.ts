import {describe, it, expect} from 'vitest';
import {FAKE_ASSET_ID_BASE} from '$lib/utils/brim/isFakeAssetId';
import type {TransactionCreateItem} from '$lib/types';
import type {AssetResolution, DedupKey, MergedTx} from './importTypes';
import {
    buildDedupKey,
    buildDuplicateGroups,
    compareTargetFor,
    dedupKeysMatch,
    describeDedupKey,
    duplicateStatusAllowsAutoSelect,
    duplicateStatusIsSelectedWarning,
    getDedupCash,
    getDedupCurrency,
    hasFirmOutsideCollision,
    isResolvedAwayDuplicate,
    normalizeAssetToken,
    normalizeDedupDescription,
    pendingDuplicateStatusFor,
    resolveDedupAssetIdentity,
    rowAfterRecheck,
} from './importDedup';

const FAKE = FAKE_ASSET_ID_BASE; // placeholder ids sit at/just below 2^31

/** Build a loose transaction; only the fields the dedup logic reads matter. */
const tx = (t: Record<string, unknown>): TransactionCreateItem => t as unknown as TransactionCreateItem;

/** Build a resolution with only the identity fields populated. */
const res = (r: Partial<AssetResolution>): AssetResolution => r as AssetResolution;

/** Build a merged row for group clustering. */
const mt = (index: number, sourceFileId: string, t: Record<string, unknown>, extra: Partial<MergedTx> = {}): MergedTx => ({index, sourceFileId, tx: tx(t), selected: false, duplicateStatus: 'unique', dupMatches: [], todos: [], ...extra}) as MergedTx;

describe('duplicate status predicates', () => {
    it('lets everything but the two firm-duplicate tiers auto-select', () => {
        expect(duplicateStatusAllowsAutoSelect('unique')).toBe(true);
        expect(duplicateStatusAllowsAutoSelect('possible')).toBe(true);
        expect(duplicateStatusAllowsAutoSelect('pending_possible_duplicate')).toBe(true);
        expect(duplicateStatusAllowsAutoSelect('likely')).toBe(false);
        expect(duplicateStatusAllowsAutoSelect('pending_duplicate')).toBe(false);
    });

    it('warns on a selected row that is likely or a pending duplicate of either strength', () => {
        expect(duplicateStatusIsSelectedWarning('likely')).toBe(true);
        expect(duplicateStatusIsSelectedWarning('pending_duplicate')).toBe(true);
        expect(duplicateStatusIsSelectedWarning('pending_possible_duplicate')).toBe(true);
        expect(duplicateStatusIsSelectedWarning('unique')).toBe(false);
        expect(duplicateStatusIsSelectedWarning('possible')).toBe(false);
    });
});

describe('normalizeAssetToken', () => {
    it('trims and lowercases a real token', () => {
        expect(normalizeAssetToken('  IT0001 ')).toBe('it0001');
    });
    it('returns null for anything empty', () => {
        expect(normalizeAssetToken('')).toBeNull();
        expect(normalizeAssetToken('   ')).toBeNull();
        expect(normalizeAssetToken(null)).toBeNull();
        expect(normalizeAssetToken(undefined)).toBeNull();
    });
});

describe('resolveDedupAssetIdentity', () => {
    const empty = new Map<number, AssetResolution>();

    it('reads a null asset as its own identity', () => {
        expect(resolveDedupAssetIdentity(tx({asset_id: null}), empty)).toBe('asset:null');
    });

    it('takes a real (non-fake) id verbatim, without consulting resolutions', () => {
        expect(resolveDedupAssetIdentity(tx({asset_id: 42}), empty)).toBe('asset:42');
    });

    it('prefers a resolved binding over every extracted code', () => {
        const map = new Map([[FAKE, res({fakeAssetId: FAKE, resolvedAssetId: 55, extractedIsin: 'IT0001'})]]);
        expect(resolveDedupAssetIdentity(tx({asset_id: FAKE}), map)).toBe('asset:55');
    });

    it('falls back ISIN → symbol → name for an unresolved fake', () => {
        const isin = new Map([[FAKE, res({fakeAssetId: FAKE, resolvedAssetId: null, extractedIsin: 'IT0001', extractedSymbol: 'ENI', extractedName: 'Eni SpA'})]]);
        expect(resolveDedupAssetIdentity(tx({asset_id: FAKE}), isin)).toBe('isin:it0001');

        const symbol = new Map([[FAKE, res({fakeAssetId: FAKE, resolvedAssetId: null, extractedIsin: null, extractedSymbol: 'ENI', extractedName: 'Eni SpA'})]]);
        expect(resolveDedupAssetIdentity(tx({asset_id: FAKE}), symbol)).toBe('symbol:eni');

        const name = new Map([[FAKE, res({fakeAssetId: FAKE, resolvedAssetId: null, extractedIsin: null, extractedSymbol: null, extractedName: 'Eni SpA'})]]);
        expect(resolveDedupAssetIdentity(tx({asset_id: FAKE}), name)).toBe('name:eni spa');
    });

    it('keeps an unresolved fake with no codes distinct by its fake id', () => {
        expect(resolveDedupAssetIdentity(tx({asset_id: FAKE}), empty)).toBe(`fake:${FAKE}`);
        const blank = new Map([[FAKE, res({fakeAssetId: FAKE, resolvedAssetId: null, extractedIsin: '  ', extractedSymbol: '', extractedName: null})]]);
        expect(resolveDedupAssetIdentity(tx({asset_id: FAKE}), blank)).toBe(`fake:${FAKE}`);
    });
});

describe('getDedupCurrency / getDedupCash', () => {
    it('unwraps an array-wrapped leg and normalises code + amount', () => {
        expect(getDedupCurrency([{code: ' eur ', amount: '12.5'}])).toEqual({code: 'EUR', amount: 12.5});
    });
    it('rejects a leg with no code or a non-finite amount', () => {
        expect(getDedupCurrency({code: '', amount: '1'})).toBeNull();
        expect(getDedupCurrency({code: 'EUR', amount: 'abc'})).toBeNull();
        expect(getDedupCurrency(null)).toBeNull();
    });
    it('rejects a leg whose code field is entirely absent', () => {
        expect(getDedupCurrency({amount: '5'})).toBeNull();
    });
    it('defaults a wholly-absent amount to zero', () => {
        // A cash leg carrying only a code is a legitimate zero movement, not a reject.
        expect(getDedupCurrency({code: 'eur'})).toEqual({code: 'EUR', amount: 0});
    });
    it('reads the cash leg off a transaction', () => {
        expect(getDedupCash(tx({cash: {code: 'usd', amount: -3}}))).toEqual({code: 'USD', amount: -3});
        expect(getDedupCash(tx({}))).toBeNull();
    });
});

describe('buildDedupKey', () => {
    it('returns null when the quantity is not finite', () => {
        expect(buildDedupKey(tx({quantity: 'not-a-number'}), new Map())).toBeNull();
    });

    it('captures the identity fields, trimming the date to its day', () => {
        const key = buildDedupKey(tx({broker_id: 3, type: 'BUY', date: '2024-01-02T10:11:12', quantity: 10, cash: {code: 'eur', amount: '-100'}, cost_basis_override: {code: 'EUR', amount: '5.5'}, asset_id: 7}), new Map());
        expect(key).toEqual({
            broker: '3',
            type: 'BUY',
            date: '2024-01-02',
            quantity: 10,
            cashCode: 'EUR',
            cashAmount: -100,
            costOverride: 5.5,
            assetIdentity: 'asset:7',
        });
    });

    it('leaves cashAmount and costOverride null when absent', () => {
        const key = buildDedupKey(tx({broker_id: 1, type: 'ADJUSTMENT', date: '2024-03-03', quantity: 1, asset_id: 9}), new Map());
        expect(key?.cashAmount).toBeNull();
        expect(key?.costOverride).toBeNull();
    });

    it('defaults broker, type and date to empty strings and quantity to zero on a bare row', () => {
        // A row missing broker/type/date/quantity still forms a (degenerate) key rather than
        // throwing — Number(undefined ?? 0) is a finite 0, so the guard on line 81 passes.
        const key = buildDedupKey(tx({}), new Map());
        expect(key).toEqual({broker: '', type: '', date: '', quantity: 0, cashCode: null, cashAmount: null, costOverride: null, assetIdentity: 'asset:null'});
    });
});

describe('dedupKeysMatch', () => {
    const base: DedupKey = {broker: '1', type: 'BUY', date: '2024-01-02', quantity: 10, cashCode: 'EUR', cashAmount: -100, costOverride: null, assetIdentity: 'asset:5'};
    const withKey = (o: Partial<DedupKey>): DedupKey => ({...base, ...o});

    it('matches two identical keys', () => {
        expect(dedupKeysMatch(base, withKey({}))).toBe(true);
    });

    it('rejects a difference in any of the exact-match fields', () => {
        expect(dedupKeysMatch(base, withKey({broker: '2'}))).toBe(false);
        expect(dedupKeysMatch(base, withKey({type: 'SELL'}))).toBe(false);
        expect(dedupKeysMatch(base, withKey({date: '2024-01-03'}))).toBe(false);
        expect(dedupKeysMatch(base, withKey({cashCode: 'USD'}))).toBe(false);
        expect(dedupKeysMatch(base, withKey({assetIdentity: 'asset:6'}))).toBe(false);
    });

    it('accepts a quantity within tolerance and rejects one beyond it', () => {
        expect(dedupKeysMatch(base, withKey({quantity: 10.00005}))).toBe(true);
        expect(dedupKeysMatch(base, withKey({quantity: 10.5}))).toBe(false);
    });

    it('accepts an amount within tolerance and rejects one beyond it', () => {
        expect(dedupKeysMatch(base, withKey({cashAmount: -100.005}))).toBe(true);
        expect(dedupKeysMatch(base, withKey({cashAmount: -101}))).toBe(false);
    });

    it('treats a null cashAmount on only one side as a mismatch, both-null as a match', () => {
        expect(dedupKeysMatch(withKey({cashAmount: null}), base)).toBe(false);
        expect(dedupKeysMatch(withKey({cashAmount: null}), withKey({cashAmount: null}))).toBe(true);
    });

    it('separates two adjustment legs by a per-unit cost override', () => {
        // Same cashless movement, different book price → not the same lot.
        expect(dedupKeysMatch(withKey({cashAmount: null, costOverride: 5}), withKey({cashAmount: null, costOverride: 9}))).toBe(false);
        expect(dedupKeysMatch(withKey({cashAmount: null, costOverride: 5}), withKey({cashAmount: null, costOverride: 5.00005}))).toBe(true);
        // Override present on one side only is a mismatch.
        expect(dedupKeysMatch(withKey({cashAmount: null, costOverride: 5}), withKey({cashAmount: null, costOverride: null}))).toBe(false);
    });
});

describe('normalizeDedupDescription / pendingDuplicateStatusFor', () => {
    it('collapses all whitespace so a re-wrapped description still twins', () => {
        expect(normalizeDedupDescription(tx({description: 'DT EMISS.'}))).toBe('dtemiss.');
        expect(normalizeDedupDescription(tx({description: 'DTEMISS.'}))).toBe('dtemiss.');
        expect(normalizeDedupDescription(tx({}))).toBe('');
    });

    it('is a firm pending duplicate only when the descriptions match', () => {
        expect(pendingDuplicateStatusFor(tx({description: 'DT EMISS.'}), tx({description: 'DTEMISS.'}))).toBe('pending_duplicate');
        expect(pendingDuplicateStatusFor(tx({description: 'BUY 10'}), tx({description: 'BUY 11'}))).toBe('pending_possible_duplicate');
    });
});

describe('describeDedupKey', () => {
    it('renders a stable pipe-joined identity with fixed precision', () => {
        const key: DedupKey = {broker: '1', type: 'BUY', date: '2024-01-02', quantity: 10, cashCode: 'EUR', cashAmount: -100, costOverride: null, assetIdentity: 'asset:5'};
        expect(describeDedupKey(key)).toBe('1|BUY|2024-01-02|10.0000|EUR|-100.00||asset:5');
    });

    it('emits empty slots for a null cashCode and cashAmount', () => {
        const key: DedupKey = {broker: '1', type: 'DEPOSIT', date: '2024-01-02', quantity: 0, cashCode: null, cashAmount: null, costOverride: null, assetIdentity: 'asset:null'};
        expect(describeDedupKey(key)).toBe('1|DEPOSIT|2024-01-02|0.0000||||asset:null');
    });
});

describe('buildDuplicateGroups', () => {
    const buyKey = {broker_id: 1, type: 'BUY', date: '2024-01-02', quantity: 10, cash: {code: 'EUR', amount: '-100'}, asset_id: 5};

    it('ignores a cluster confined to a single file', () => {
        const rows = [mt(0, 'fileA', {...buyKey, description: 'x'}), mt(1, 'fileA', {...buyKey, description: 'x'})];
        expect(buildDuplicateGroups(rows, new Map())).toEqual([]);
    });

    it('reports a cross-file cluster as a sure duplicate when descriptions align across files', () => {
        const rows = [mt(0, 'fileA', {...buyKey, description: 'DT EMISS.'}), mt(1, 'fileB', {...buyKey, description: 'DTEMISS.'})];
        const groups = buildDuplicateGroups(rows, new Map());
        expect(groups).toHaveLength(1);
        expect(groups[0].tier).toBe('sure');
        expect(groups[0].memberIndices).toEqual([0, 1]);
    });

    it('demotes to probable when a description partition lives in only one file', () => {
        // Three rows, same key, spanning two files, but one description sits alone in fileA.
        const rows = [mt(0, 'fileA', {...buyKey, description: 'twin'}), mt(1, 'fileB', {...buyKey, description: 'twin'}), mt(2, 'fileA', {...buyKey, description: 'lonely'})];
        const groups = buildDuplicateGroups(rows, new Map());
        expect(groups).toHaveLength(1);
        expect(groups[0].tier).toBe('probable');
        expect(groups[0].memberIndices).toEqual([0, 1, 2]);
    });

    it('skips rows whose quantity cannot form a key', () => {
        const rows = [mt(0, 'fileA', {...buyKey, quantity: 'NaN', description: 'x'}), mt(1, 'fileB', {...buyKey, quantity: 'NaN', description: 'x'})];
        expect(buildDuplicateGroups(rows, new Map())).toEqual([]);
    });
});

describe('isResolvedAwayDuplicate', () => {
    it('hides a non-keeper the user did not keep', () => {
        expect(isResolvedAwayDuplicate(mt(0, 'f', {}, {dupGroupKey: 'k', isDupKeeper: false, selected: false}))).toBe(true);
    });
    it('keeps the keeper, a deliberately kept secondary, and a non-grouped row', () => {
        expect(isResolvedAwayDuplicate(mt(0, 'f', {}, {dupGroupKey: 'k', isDupKeeper: true, selected: false}))).toBe(false);
        expect(isResolvedAwayDuplicate(mt(0, 'f', {}, {dupGroupKey: 'k', isDupKeeper: false, selected: true}))).toBe(false);
        expect(isResolvedAwayDuplicate(mt(0, 'f', {}, {isDupKeeper: false, selected: false}))).toBe(false);
    });
});

// ---------------------------------------------------------------------------
// U4: what a review badge compares with, and which copies collide outside the batch
// ---------------------------------------------------------------------------

describe('U4: compareTargetFor / hasFirmOutsideCollision', () => {
    /** A database match as the parse report carries it; the dispatch only counts them. */
    const dbMatch = (existingTxId: number): MergedTx['dupMatches'][number] => ({existing_tx_id: existingTxId}) as MergedTx['dupMatches'][number];
    /** The unsaved bulk-editor row a pending duplicate was matched against. */
    const editorRow = tx({type: 'BUY', description: 'shared buy'});

    describe('compareTargetFor — the comparison the badge claims', () => {
        it('opens nothing for a unique row, even one that belongs to a cross-file group', () => {
            expect(compareTargetFor(mt(0, 'fA', {}, {duplicateStatus: 'unique', dupGroupKey: 'k', isDupKeeper: true}))).toBeNull();
        });

        it('compares a likely or possible duplicate with its database row', () => {
            expect(compareTargetFor(mt(0, 'fA', {}, {duplicateStatus: 'likely', dbDuplicateStatus: 'likely', dupMatches: [dbMatch(500)]}))).toBe('db');
            expect(compareTargetFor(mt(0, 'fA', {}, {duplicateStatus: 'possible', dbDuplicateStatus: 'possible', dupMatches: [dbMatch(501)]}))).toBe('db');
        });

        it('opens nothing for a database verdict that carries no match to compare with', () => {
            // A backend `possible` entry may arrive without `tx_existing_matches`; there is no row to fetch.
            expect(compareTargetFor(mt(0, 'fA', {}, {duplicateStatus: 'likely', dbDuplicateStatus: 'likely', dupMatches: []}))).toBeNull();
            expect(compareTargetFor(mt(0, 'fA', {}, {duplicateStatus: 'possible', dbDuplicateStatus: 'possible', dupMatches: []}))).toBeNull();
        });

        it('compares a likely duplicate that is also a cross-file group member with the database, not with the lot', () => {
            // The fixed bug: the group keeper of two overlapping exports, already in the database,
            // shows "likely duplicate" — and its badge used to open the file-vs-file comparison.
            const keeper = mt(0, 'fA', {}, {duplicateStatus: 'likely', dbDuplicateStatus: 'likely', dupMatches: [dbMatch(500)], dupGroupKey: 'k', dupTier: 'sure', isDupKeeper: true});
            expect(compareTargetFor(keeper)).toBe('db');
        });

        it('compares a firm or weak bulk-editor duplicate with the editor row', () => {
            expect(compareTargetFor(mt(0, 'fA', {}, {duplicateStatus: 'pending_duplicate', pendingMatchStatus: 'pending_duplicate', dupPendingMatch: editorRow}))).toBe('pending');
            expect(compareTargetFor(mt(0, 'fA', {}, {duplicateStatus: 'pending_possible_duplicate', pendingMatchStatus: 'pending_possible_duplicate', dupPendingMatch: editorRow}))).toBe('pending');
        });

        it('compares an in-batch secondary, which matches no editor row, with its lot', () => {
            const secondary = mt(1, 'fB', {}, {duplicateStatus: 'pending_duplicate', dupGroupKey: 'k', dupTier: 'sure', isDupKeeper: false, dupKeeperIndex: 0});
            expect(compareTargetFor(secondary)).toBe('lot');
        });

        it('prefers the editor row over the lot for a copy that is both a group member and an editor duplicate', () => {
            const both = mt(1, 'fB', {}, {duplicateStatus: 'pending_duplicate', pendingMatchStatus: 'pending_duplicate', dupPendingMatch: editorRow, dupGroupKey: 'k', dupTier: 'sure', isDupKeeper: false});
            expect(compareTargetFor(both)).toBe('pending');
        });

        it('opens nothing for a pending verdict with neither an editor row nor a group behind it', () => {
            expect(compareTargetFor(mt(0, 'fA', {}, {duplicateStatus: 'pending_duplicate'}))).toBeNull();
        });
    });

    describe('hasFirmOutsideCollision — reads the two verdict fields only', () => {
        it('is true for a likely database twin and false for a possible one', () => {
            expect(hasFirmOutsideCollision(mt(0, 'fA', {}, {dbDuplicateStatus: 'likely'}))).toBe(true);
            expect(hasFirmOutsideCollision(mt(0, 'fA', {}, {dbDuplicateStatus: 'possible'}))).toBe(false);
        });

        it('is true for a firm bulk-editor duplicate and false for a weak one', () => {
            expect(hasFirmOutsideCollision(mt(0, 'fA', {}, {pendingMatchStatus: 'pending_duplicate'}))).toBe(true);
            expect(hasFirmOutsideCollision(mt(0, 'fA', {}, {pendingMatchStatus: 'pending_possible_duplicate'}))).toBe(false);
        });

        it('is false for a row with no verdict at all', () => {
            expect(hasFirmOutsideCollision(mt(0, 'fA', {}))).toBe(false);
        });

        it('ignores duplicateStatus, which the in-batch pass rewrites on every secondary', () => {
            // A secondary marked pending_duplicate by the in-batch pass collides with nothing outside.
            expect(hasFirmOutsideCollision(mt(1, 'fB', {}, {duplicateStatus: 'pending_duplicate', dupGroupKey: 'k', isDupKeeper: false}))).toBe(false);
            // A secondary whose database verdict was overwritten by that marker still collides.
            expect(hasFirmOutsideCollision(mt(1, 'fB', {}, {duplicateStatus: 'pending_duplicate', dbDuplicateStatus: 'likely', dupGroupKey: 'k', isDupKeeper: false}))).toBe(true);
        });
    });
});

// ---------------------------------------------------------------------------
// U7: the row a database recheck leaves behind, before the in-batch passes run again
// ---------------------------------------------------------------------------

describe('U7: rowAfterRecheck', () => {
    type Verdict = Parameters<typeof rowAfterRecheck>[1];
    /** A database match as the recheck report carries it; the rebuild only passes it through. */
    const dbMatch = (existingTxId: number): MergedTx['dupMatches'][number] => ({existing_tx_id: existingTxId}) as MergedTx['dupMatches'][number];
    /** Every answer the recheck can give a row: none, a weak twin, a firm twin. */
    const verdicts: Verdict[] = [undefined, {status: 'possible', matches: [dbMatch(501)]}, {status: 'likely', matches: [dbMatch(500)]}];
    const verdictLabel = (verdict: Verdict): string => verdict?.status ?? 'no verdict';
    /** Dated after the broker's opening, selection recomputed from scratch: the verdict alone decides. */
    const fresh = {beforeOpening: false, preserveSelection: false};
    /** The in-batch and editor markers, which the passes after the recheck rebuild from nothing. */
    const markers = ['pendingMatchStatus', 'dupPendingMatch', 'dupGroupKey', 'dupTier', 'dupKeeperIndex', 'dupKeeperFileName', 'isDupKeeper'] as const;
    /** A row carrying everything the earlier passes can leave on it: a database twin, a kept group secondary, an editor match. */
    const markedRow = (): MergedTx =>
        mt(
            3,
            'fileB',
            {type: 'BUY', date: '2024-05-01', quantity: 2, asset_id: 5, description: 'buy 2'},
            {
                selected: true,
                duplicateStatus: 'pending_duplicate',
                dbDuplicateStatus: 'likely',
                dupMatches: [dbMatch(500)],
                todos: [{field: 'quantity', severity: 'warning', reasonCode: 'A', message: 'm1'}],
                pendingMatchStatus: 'pending_duplicate',
                dupPendingMatch: tx({type: 'BUY', date: '2024-05-01', quantity: 2, description: 'buy 2'}),
                dupGroupKey: 'k',
                dupTier: 'sure',
                dupKeeperIndex: 0,
                dupKeeperFileName: 'fileA.csv',
                isDupKeeper: false,
            },
        );

    it('records a likely verdict as the database verdict and deselects the firm twin', () => {
        const m1 = dbMatch(500);
        const out = rowAfterRecheck(mt(0, 'fA', {}, {selected: true}), {status: 'likely', matches: [m1]}, fresh);
        expect(out.duplicateStatus).toBe('likely');
        expect(out.dbDuplicateStatus).toBe('likely');
        expect(out.dupMatches).toEqual([m1]);
        expect(out.selected).toBe(false);
    });

    it('records a possible verdict and re-selects the weak twin', () => {
        const out = rowAfterRecheck(mt(0, 'fA', {}, {selected: false}), {status: 'possible', matches: [dbMatch(501)]}, fresh);
        expect(out.duplicateStatus).toBe('possible');
        expect(out.dbDuplicateStatus).toBe('possible');
        expect(out.selected).toBe(true);
    });

    it('drops the stale database verdict from the parse when the recheck returns none', () => {
        // The regression the extraction pins: the parse said likely, a correction cleared the
        // twin, and a verdict carried over by the spread would keep the row out of the keepers.
        const parsed = mt(0, 'fA', {}, {duplicateStatus: 'likely', dbDuplicateStatus: 'likely', dupMatches: [dbMatch(500)]});
        const out = rowAfterRecheck(parsed, undefined, fresh);
        expect(out.duplicateStatus).toBe('unique');
        expect(out.dbDuplicateStatus).toBeUndefined();
        expect(out.dupMatches).toEqual([]);
    });

    it('clears every in-batch and editor marker, whatever the verdict', () => {
        for (const verdict of verdicts) {
            const row = markedRow();
            // Every marker is set on the way in, so an undefined on the way out is the rebuild's doing.
            for (const field of markers) expect(row[field], `input ${field}`).toBeDefined();
            const out = rowAfterRecheck(row, verdict, fresh);
            for (const field of markers) expect(out[field], `${field} after ${verdictLabel(verdict)}`).toBeUndefined();
        }
    });

    it('keeps a deselected unique row deselected only when the selection is preserved', () => {
        const deselected = mt(0, 'fA', {}, {selected: false});
        expect(rowAfterRecheck(deselected, undefined, {beforeOpening: false, preserveSelection: true}).selected).toBe(false);
        expect(rowAfterRecheck(deselected, undefined, {beforeOpening: false, preserveSelection: false}).selected).toBe(true);
        // Preserving is not deselecting: a row the user kept stays kept.
        expect(rowAfterRecheck(mt(0, 'fA', {}, {selected: true}), undefined, {beforeOpening: false, preserveSelection: true}).selected).toBe(true);
    });

    it("never selects a row predating the broker's opening, whatever the verdict or the previous selection", () => {
        for (const verdict of verdicts) {
            for (const selected of [true, false]) {
                for (const preserveSelection of [true, false]) {
                    const out = rowAfterRecheck(mt(0, 'fA', {}, {selected}), verdict, {beforeOpening: true, preserveSelection});
                    expect(out.selected, `${verdictLabel(verdict)}, selected=${selected}, preserveSelection=${preserveSelection}`).toBe(false);
                }
            }
        }
        // Control: the same selected unique row, dated after the opening, stays selected — the date is what deselects.
        expect(rowAfterRecheck(mt(0, 'fA', {}, {selected: true}), undefined, {beforeOpening: false, preserveSelection: true}).selected).toBe(true);
    });

    it('returns a new row: the input is untouched and the unrelated fields carry over', () => {
        const row = markedRow();
        const before = structuredClone(row);
        const out = rowAfterRecheck(row, undefined, fresh);
        expect(out).not.toBe(row);
        expect(row).toStrictEqual(before);
        expect(out.index).toBe(3);
        expect(out.sourceFileId).toBe('fileB');
        expect(out.tx).toBe(row.tx);
        expect(out.todos).toBe(row.todos);
    });
});
