import {describe, it, expect} from 'vitest';
import {FAKE_ASSET_ID_BASE} from '$lib/features/transactions/import/isFakeAssetId';
import type {TransactionCreateItem} from '$lib/types';
import type {AssetResolution, DedupKey, MergedTx} from './importTypes';
// W-B81: the module as a whole, for an export the cure adds (`sameDedupQuantity`, read through an accessor below).
import * as dedup from './importDedup';
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
        // W-B81: the amount is its exact text, never a Number.
        expect(getDedupCurrency([{code: ' eur ', amount: '12.5'}])).toEqual({code: 'EUR', amount: '12.5'});
        expect(getDedupCurrency({code: 'eur', amount: '12.50'}), 'W-B81: the exact text, trailing zeros removed').toEqual({code: 'EUR', amount: '12.5'});
    });
    it('rejects a leg with no code or an amount that is no plain decimal', () => {
        expect(getDedupCurrency({code: '', amount: '1'})).toBeNull();
        expect(getDedupCurrency({code: 'EUR', amount: 'abc'})).toBeNull();
        expect(getDedupCurrency(null)).toBeNull();
    });
    it('rejects a leg whose code field is entirely absent', () => {
        expect(getDedupCurrency({amount: '5'})).toBeNull();
    });
    it('defaults a wholly-absent amount to zero', () => {
        // A cash leg carrying only a code is a legitimate zero movement, not a reject.
        expect(getDedupCurrency({code: 'eur'})).toEqual({code: 'EUR', amount: '0'});
    });
    it("W-B81: reads a blank amount as '0', as a missing one", () => {
        for (const amount of ['', '   ']) expect.soft(getDedupCurrency({code: 'EUR', amount}), `W-B81: the blank amount ${JSON.stringify(amount)} is 0`).toEqual({code: 'EUR', amount: '0'});
    });
    it('reads the cash leg off a transaction', () => {
        // The amount is a string on the wire (Currency_Output), so the input is one too.
        expect(getDedupCash(tx({cash: {code: 'usd', amount: '-3'}}))).toEqual({code: 'USD', amount: '-3'});
        expect(getDedupCash(tx({}))).toBeNull();
    });
    it('W-B81: rejects an amount text in exponent notation, even a finite one', () => {
        expect(getDedupCurrency({code: 'EUR', amount: '1e3'}), 'W-B81: the parsing reads plain decimals only; through Number 1e3 is 1000').toBeNull();
    });
    it('W-B81: reads a finite number as the decimal JavaScript writes for it, its exponent expanded; the same value as a text in exponent notation stays unreadable', () => {
        // The type says text, but a number reaches the reader too: the code's own `?? 0`, a value set at run time.
        expect.soft(getDedupCurrency({code: 'EUR', amount: 12.5}), 'W-B81: the number 12.5 is 12.5').toEqual({code: 'EUR', amount: '12.5'});
        expect.soft(getDedupCurrency({code: 'EUR', amount: 1.5e-7}), 'W-B81: the number 1.5e-7 is 0.00000015, its exponent expanded').toEqual({code: 'EUR', amount: '0.00000015'});
        expect.soft(getDedupCurrency({code: 'EUR', amount: '1.5e-7'}), 'W-B81: the text 1.5e-7 stays unreadable, texts keep the strict rule').toBeNull();
    });
    it('W-B81: reads no number that is not finite', () => {
        expect(getDedupCurrency({code: 'EUR', amount: Infinity}), 'W-B81: Infinity is no amount').toBeNull();
        expect(getDedupCurrency({code: 'EUR', amount: NaN}), 'W-B81: NaN is no amount').toBeNull();
    });
});

describe('buildDedupKey', () => {
    it('returns null when the quantity is not finite', () => {
        expect(buildDedupKey(tx({quantity: 'not-a-number'}), new Map())).toBeNull();
    });

    it('captures the identity fields, trimming the date to its day', () => {
        // W-B81: quantity, cash amount and cost override travel as decimal texts, never through Number.
        const key = buildDedupKey(tx({broker_id: 3, type: 'BUY', date: '2024-01-02T10:11:12', quantity: '10', cash: {code: 'eur', amount: '-100'}, cost_basis_override: {code: 'EUR', amount: '5.5'}, asset_id: 7}), new Map());
        expect(key).toEqual({
            broker: '3',
            type: 'BUY',
            date: '2024-01-02',
            quantity: '10',
            cashCode: 'EUR',
            cashAmount: '-100',
            costOverride: '5.5',
            assetIdentity: 'asset:7',
        });
    });

    it('leaves cashAmount and costOverride null when absent', () => {
        const key = buildDedupKey(tx({broker_id: 1, type: 'ADJUSTMENT', date: '2024-03-03', quantity: '1', asset_id: 9}), new Map());
        expect(key?.cashAmount).toBeNull();
        expect(key?.costOverride).toBeNull();
    });

    it('defaults broker, type and date to empty strings and quantity to zero on a bare row', () => {
        // A row missing broker/type/date/quantity still forms a (degenerate) key rather than
        // throwing: an absent quantity reads as '0', the payload's own default (TXCreateItem).
        const key = buildDedupKey(tx({}), new Map());
        expect(key).toEqual({broker: '', type: '', date: '', quantity: '0', cashCode: null, cashAmount: null, costOverride: null, assetIdentity: 'asset:null'});
    });
});

describe('dedupKeysMatch', () => {
    const base: DedupKey = {broker: '1', type: 'BUY', date: '2024-01-02', quantity: '10', cashCode: 'EUR', cashAmount: '-100', costOverride: null, assetIdentity: 'asset:5'};
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
        expect(dedupKeysMatch(base, withKey({quantity: '10.00005'}))).toBe(true);
        expect(dedupKeysMatch(base, withKey({quantity: '10.5'}))).toBe(false);
    });

    it('accepts an amount within tolerance and rejects one beyond it', () => {
        expect(dedupKeysMatch(base, withKey({cashAmount: '-100.005'}))).toBe(true);
        expect(dedupKeysMatch(base, withKey({cashAmount: '-101'}))).toBe(false);
    });

    it('treats a null cashAmount on only one side as a mismatch, both-null as a match', () => {
        expect(dedupKeysMatch(withKey({cashAmount: null}), base)).toBe(false);
        expect(dedupKeysMatch(withKey({cashAmount: null}), withKey({cashAmount: null}))).toBe(true);
    });

    it('separates two adjustment legs by a per-unit cost override', () => {
        // Same cashless movement, different book price → not the same lot.
        expect(dedupKeysMatch(withKey({cashAmount: null, costOverride: '5'}), withKey({cashAmount: null, costOverride: '9'}))).toBe(false);
        expect(dedupKeysMatch(withKey({cashAmount: null, costOverride: '5'}), withKey({cashAmount: null, costOverride: '5.00005'}))).toBe(true);
        // Override present on one side only is a mismatch.
        expect(dedupKeysMatch(withKey({cashAmount: null, costOverride: '5'}), withKey({cashAmount: null, costOverride: null}))).toBe(false);
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
    it('renders a stable pipe-joined identity with the exact text of each number', () => {
        // W-B81: no fixed precision any more — toFixed(4) gave 0.00015123 and 0.00015098 one identity.
        const key: DedupKey = {broker: '1', type: 'BUY', date: '2024-01-02', quantity: '10', cashCode: 'EUR', cashAmount: '-100', costOverride: null, assetIdentity: 'asset:5'};
        expect(describeDedupKey(key)).toBe('1|BUY|2024-01-02|10|EUR|-100||asset:5');
    });

    it('emits empty slots for a null cashCode and cashAmount', () => {
        const key: DedupKey = {broker: '1', type: 'DEPOSIT', date: '2024-01-02', quantity: '0', cashCode: null, cashAmount: null, costOverride: null, assetIdentity: 'asset:null'};
        expect(describeDedupKey(key)).toBe('1|DEPOSIT|2024-01-02|0||||asset:null');
    });
});

describe('buildDuplicateGroups', () => {
    const buyKey = {broker_id: 1, type: 'BUY', date: '2024-01-02', quantity: '10', cash: {code: 'EUR', amount: '-100'}, asset_id: 5};

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
            const secondary = mt(1, 'fB', {}, {duplicateStatus: 'pending_duplicate', dupGroupKey: 'k', dupTier: 'sure', isDupKeeper: false});
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
    const markers = ['pendingMatchStatus', 'dupPendingMatch', 'dupGroupKey', 'dupTier', 'isDupKeeper'] as const;
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

// ---------------------------------------------------------------------------
// W-B81: the quantity of a duplicate, by the backend's rule (W-B51, decision D-W51-1)
// ---------------------------------------------------------------------------

/*
 * The wizard keeps its own copy of the backend's duplicate rule: `dedupKeysMatch` clusters the rows
 * of two source files into a group (`buildDuplicateGroups`) and matches a parsed row with an unsaved
 * row of the bulk editor. Until W-B81 that copy compared quantities as floats within 0.0001, so two
 * recurring buys of 10 EUR of BTC on one day, 0.00015123 and 0.00015098, were one movement — a group
 * keeps one copy by default and resolves the other away from step 4 — and `toFixed(4)` addressed
 * both by the same `0.0002` (`ImportWizardModal` finds a row's group by that key, `dupGroupKey`).
 *
 * D-W51-1: two quantities match when, rounded half-up to the scale of the less precise of the two
 * (trailing zeros are no precision), they are equal, AND |a − b| ≤ 0.0001 — on the exact decimal
 * text, never through `Number`. The per-unit cost override follows the same rule; the cash amount
 * keeps «within 0.01, same currency», computed exactly too.
 *
 * Parsing (coordinator, 17/10): plain decimals only, as `exactDecimalParts` reads them — a sign,
 * digits, a point (`+5`, `.5`, `5.` and blanks around them accepted), no exponent notation at all.
 * A blank quantity or cash amount is no number for the comparison; `buildDedupKey` (the quantity)
 * and `getDedupCurrency` (the amount) read it as `'0'`, as a missing one. A finite number — the
 * code's own `?? 0`, a value set at run time — is read as the decimal JavaScript writes for it, its
 * exponent expanded (`1.5e-7` is `0.00000015`); a text in exponent notation stays unreadable.
 */

/** The rule on two decimal texts or finite numbers, read through the module: until the cure exports it, each case using it fails alone. */
function sameDedupQuantity(a: string | number, b: string | number): boolean {
    const rule = (dedup as unknown as {sameDedupQuantity?: (a: string | number, b: string | number) => boolean}).sameDedupQuantity;
    if (typeof rule !== 'function') throw new Error('W-B81: sameDedupQuantity does not exist yet');
    return rule(a, b);
}

/** Two quantity texts, and what D-W51-1 makes of them. */
interface QuantityPair {
    /** In the shared table, the pytest id of the backend's twin case. */
    id: string;
    a: string;
    b: string;
    /** Whether `a` and `b` are one and the same quantity. */
    match: boolean;
    /** What `describeDedupKey` writes for `a` and for `b`: the exact value, trailing zeros removed. */
    identity: [string, string];
    why: string;
}

/** A text the rule cannot read: no plain decimal (a sign, digits, a point, blanks around them; no exponent). */
interface UnreadableQuantity {
    id: string;
    quantity: string;
    /** The plain decimal `Number` reads it as, when there is one: the float rule took the two for one quantity. */
    twin?: string;
    /** A blank text: no number for the rule, yet `buildDedupKey` reads it as the payload's default, `'0'`. */
    blank?: true;
    why: string;
}

/**
 * THE SHARED TABLE. Its backend twin is `TestWB51QuantityOfADuplicate` in
 * `backend/test_scripts/test_db/test_brim_db.py`: the same ids for the same pairs (there a `saved`
 * quantity, read back through the column, against an `incoming` one). A pair that changes on one
 * side changes on the other. The shared `unreadable` case is `WB51_UNREADABLE`, just below.
 */
const WB51_SHARED: QuantityPair[] = [
    {id: 'apart-at-5-decimals', a: '0.00015', b: '0.00008', match: false, identity: ['0.00015', '0.00008'], why: 'both have 5 decimals, and 0.00015 ≠ 0.00008 (|a − b| = 0.00007, inside the old float tolerance)'},
    {id: 'recurring-buys-at-8-decimals', a: '0.00015123', b: '0.00015098', match: false, identity: ['0.00015123', '0.00015098'], why: 'two recurring buys of the same 10 EUR: both have 8 decimals, and 0.00015123 ≠ 0.00015098 (|a − b| = 0.00000025)'},
    {id: 'report-rounded', a: '0.000153', b: '0.00015', match: true, identity: ['0.000153', '0.00015'], why: 'a report rounding to 5 decimals: 0.000153 rounded half-up to 5 decimals is 0.00015, and |a − b| = 0.000003'},
    {id: 'integers-10', a: '10', b: '10', match: true, identity: ['10', '10'], why: 'the same whole quantity'},
    {id: 'integers-10-and-10.4', a: '10', b: '10.4', match: false, identity: ['10', '10.4'], why: 'rounded half-up to 0 decimals, the scale of 10, both are 10, but |a − b| = 0.4 > 0.0001'},
    {id: 'identical-reimport', a: '0.1234567891', b: '0.1234567891', match: true, identity: ['0.1234567891', '0.1234567891'], why: 'the same file imported again: all 10 decimals agree'},
    {id: 'saved-read-back-padded', a: '0.000150', b: '0.000153', match: true, identity: ['0.00015', '0.000153'], why: '0.000150 states 5 decimals, not 6 (a trailing zero is no precision): 0.000153 rounded half-up to 5 decimals is 0.00015'},
    {id: 'incoming-padded', a: '0.000153', b: '0.000150', match: true, identity: ['0.000153', '0.00015'], why: 'a report writing 0.000150 means 0.00015, scale 5: 0.000153 rounded half-up to 5 decimals is 0.00015'},
    {id: 'half-up-tie', a: '0.000145', b: '0.00015', match: true, identity: ['0.000145', '0.00015'], why: 'a tie: 0.000145 rounded half-up to 5 decimals is 0.00015 (half-even would make it 0.00014)'},
];

/** The shared table's `unreadable` case, in the backend's two variants (`[text]`, `[inf]`): each against `0.5`. */
const WB51_UNREADABLE: UnreadableQuantity[] = [
    {id: 'unreadable[text]', quantity: 'n/a', why: 'a text, not a number (on the backend: a text planted in the column)'},
    {id: 'unreadable[inf]', quantity: 'Infinity', why: 'an infinity (on the backend: a REAL +inf planted in the column)'},
];

/**
 * Beyond the shared table: pairs the backend's twin does not hold, each pinning a part of the rule a
 * cure on this side could miss. The backend's `_same_quantity` answers each of them the same way.
 */
const WB81_FRONTEND_ONLY: QuantityPair[] = [
    {id: 'integers-10-read-back', a: '10.000000', b: '10', match: true, identity: ['10', '10'], why: "the pair the backend's integers-10 compares once the column reads 10 back as 10.000000; a parse report writes it too (it keeps a Decimal's zeros): padding is no precision"},
    {id: 'bound-inclusive', a: '100', b: '100.0001', match: true, identity: ['100', '100.0001'], why: 'rounded half-up to 0 decimals both are 100, and |a − b| = 0.0001 exactly, on the bound (as floats the difference is 0.00010000000000331966, outside it)'},
    {id: 'wei-apart', a: '0.123456789012345678', b: '0.123456789012345679', match: false, identity: ['0.123456789012345678', '0.123456789012345679'], why: 'ETH to the wei, 18 decimals, one wei apart: different at their common scale, yet one and the same double through Number'},
    {id: 'negative-half-up-tie', a: '-0.000145', b: '-0.00015', match: true, identity: ['-0.000145', '-0.00015'], why: "a SELL's quantity is negative, and half-up rounds a tie away from zero, as the backend's ROUND_HALF_UP: -0.000145 is -0.00015 at 5 decimals (toward +∞ it would be -0.00014)"},
];

/** The contract's other texts that are no plain decimal, beyond the shared `unreadable` case. */
const WB81_NOT_PLAIN: UnreadableQuantity[] = [
    {id: 'not-plain[exponent]', quantity: '1e400', why: 'exponent notation, which a parse report never writes (SafeDecimal); through Number it is Infinity'},
    {id: 'not-plain[exponent-finite]', quantity: '1.5e-7', twin: '0.00000015', why: 'exponent notation, even of a finite value: the rule reads plain decimals only'},
    {id: 'not-plain[empty]', quantity: '', twin: '0', blank: true, why: 'no digits at all: reading a blank quantity as 0 is the business of buildDedupKey, not of the comparison'},
    {id: 'not-plain[spaces]', quantity: '   ', twin: '0', blank: true, why: 'blanks only, no digits: reading a blank quantity as 0 is the business of buildDedupKey, not of the comparison'},
];

/** The plain forms the rule reads besides the canonical one (as `exactDecimalParts`), each with its canonical text. */
const WB81_ACCEPTED_FORMS: Array<[form: string, canonical: string]> = [
    ['+0.5', '0.5'],
    ['.5', '0.5'],
    ['5.', '5'],
    [' 0.5 ', '0.5'],
    ['-.5', '-0.5'],
];

describe('W-B81: the quantity of a duplicate, by the rule of W-B51 (D-W51-1)', () => {
    type PairTable = [title: string, pairs: QuantityPair[]];
    const SHARED: PairTable = ['the shared table (backend twin: TestWB51QuantityOfADuplicate)', WB51_SHARED];
    const FRONTEND_ONLY: PairTable = ['beyond the shared table', WB81_FRONTEND_ONLY];
    const NOT_PLAIN_DECIMALS = [...WB51_UNREADABLE, ...WB81_NOT_PLAIN];

    /** One case per pair, grouped under the table the pair comes from. */
    const eachPair = (tables: PairTable[], title: (pair: QuantityPair) => string, body: (pair: QuantityPair) => void): void => {
        for (const [table, pairs] of tables) {
            describe(table, () => {
                for (const pair of pairs) it(title(pair), () => body(pair));
            });
        }
    };
    const verdict = (match: boolean): string => (match ? 'the same' : 'apart');
    const show = (text: string): string => JSON.stringify(text);

    /** A recurring buy of `quantity` units, everything else fixed: two of them differ in quantity alone. */
    const recurringBuy = (quantity: string): Record<string, unknown> => ({broker_id: 1, type: 'BUY', date: '2024-01-02', quantity, cash: {code: 'EUR', amount: '-10'}, asset_id: 5, description: 'Recurring buy BTC'});
    /** The key of such a buy, by hand: each case varies one field of it. */
    const recurringKey: DedupKey = {broker: '1', type: 'BUY', date: '2024-01-02', quantity: '0.5', cashCode: 'EUR', cashAmount: '-10', costOverride: null, assetIdentity: 'asset:5'};
    const keyWith = (o: Partial<DedupKey>): DedupKey => ({...recurringKey, ...o});
    /** A cashless adjustment leg booked at `costOverride` per unit: the override is what tells two such legs apart. */
    const legWith = (costOverride: string): DedupKey => keyWith({type: 'ADJUSTMENT', cashCode: null, cashAmount: null, costOverride});
    /** The identity `buildDuplicateGroups` gives a group whose first row is a recurring buy of `quantity`. */
    const identityOf = (quantity: string): string => {
        const key = buildDedupKey(tx(recurringBuy(quantity)), new Map());
        expect(key, `W-B81: ${show(quantity)} is a plain decimal, so a buy of it forms a key`).not.toBeNull();
        return describeDedupKey(key as DedupKey);
    };
    /** That identity, written out: only the quantity varies. */
    const identityText = (quantity: string): string => `1|BUY|2024-01-02|${quantity}|EUR|-10||asset:5`;

    describe('sameDedupQuantity', () => {
        eachPair(
            [SHARED, FRONTEND_ONLY],
            ({id, a, b, match}) => `${id}: ${a} and ${b} are ${verdict(match)}`,
            ({id, a, b, match, why}) => {
                expect(sameDedupQuantity(a, b), `W-B81 ${id}: ${why}`).toBe(match);
                expect(sameDedupQuantity(b, a), `W-B81 ${id}, the other way round: ${why}`).toBe(match);
            },
        );

        for (const {id, quantity, twin, why} of NOT_PLAIN_DECIMALS) {
            it(`${id}: ${show(quantity)} is no plain finite decimal, so it matches nothing`, () => {
                // Presence barrier: 0.5 matches itself, so a false below speaks of the text, not of a rule that never says yes.
                expect(sameDedupQuantity('0.5', '0.5'), 'control: 0.5 and 0.5').toBe(true);
                expect(sameDedupQuantity(quantity, '0.5'), `W-B81 ${id}: ${why}`).toBe(false);
                expect(sameDedupQuantity('0.5', quantity), `W-B81 ${id}, the other way round: ${why}`).toBe(false);
                expect(sameDedupQuantity(quantity, quantity), `W-B81 ${id}: not even against itself, ${why}`).toBe(false);
                if (twin) expect(sameDedupQuantity(quantity, twin), `W-B81 ${id}: not even against ${twin}, what Number reads it as: ${why}`).toBe(false);
            });
        }

        it('reads every plain form as its canonical value: a sign, a bare point on either side, blanks around', () => {
            for (const [form, canonical] of WB81_ACCEPTED_FORMS) {
                expect.soft(sameDedupQuantity(form, canonical), `W-B81: ${show(form)} is ${canonical}`).toBe(true);
                expect.soft(sameDedupQuantity(canonical, form), `W-B81: ${canonical} is ${show(form)}`).toBe(true);
            }
        });

        it('reads a finite number as the decimal JavaScript writes for it, its exponent expanded; a text in exponent notation stays unreadable', () => {
            expect(sameDedupQuantity(1e-7, '0.0000001'), 'W-B81: the number 1e-7 is 0.0000001').toBe(true);
            expect(sameDedupQuantity('0.0000001', 1e-7), 'W-B81: the number 1e-7 is 0.0000001, the other way round').toBe(true);
            expect(sameDedupQuantity('1e-7', '0.0000001'), 'W-B81: the text 1e-7 stays unreadable, texts keep the strict rule').toBe(false);
        });

        it('reads no number that is not finite, not even against itself', () => {
            // Presence barrier: a finite number is read, so a false below speaks of Infinity and NaN, not of numbers.
            expect(sameDedupQuantity(0.5, 0.5), 'control: the number 0.5 and the number 0.5').toBe(true);
            expect(sameDedupQuantity(Infinity, Infinity), 'W-B81: Infinity is no quantity').toBe(false);
            expect(sameDedupQuantity(NaN, NaN), 'W-B81: NaN is no quantity').toBe(false);
        });
    });

    describe('dedupKeysMatch: two keys that differ only in quantity', () => {
        eachPair(
            [SHARED, FRONTEND_ONLY],
            ({id, a, b, match}) => `${id}: ${a} and ${b} are ${verdict(match)}`,
            ({id, a, b, match, why}) => {
                expect(dedupKeysMatch(keyWith({quantity: a}), keyWith({quantity: b})), `W-B81 ${id}: ${why}`).toBe(match);
                expect(dedupKeysMatch(keyWith({quantity: b}), keyWith({quantity: a})), `W-B81 ${id}, the other way round: ${why}`).toBe(match);
            },
        );

        for (const {id, quantity, twin, why} of NOT_PLAIN_DECIMALS) {
            it(`${id}: a key whose quantity is ${show(quantity)} matches no key, not even one of the same text`, () => {
                expect(dedupKeysMatch(keyWith({quantity: '0.5'}), keyWith({quantity: '0.5'})), 'control: two keys of 0.5').toBe(true);
                expect(dedupKeysMatch(keyWith({quantity}), keyWith({quantity: '0.5'})), `W-B81 ${id}: ${why}`).toBe(false);
                expect(dedupKeysMatch(keyWith({quantity: '0.5'}), keyWith({quantity})), `W-B81 ${id}, the other way round: ${why}`).toBe(false);
                expect(dedupKeysMatch(keyWith({quantity}), keyWith({quantity})), `W-B81 ${id}: not even a key of the same text, ${why}`).toBe(false);
                if (twin) expect(dedupKeysMatch(keyWith({quantity}), keyWith({quantity: twin})), `W-B81 ${id}: not even a key of ${twin}, what Number reads it as: ${why}`).toBe(false);
            });
        }

        it('a row written in any plain form meets its twin written canonically (a bulk-editor SELL typed .5 goes out as -.5)', () => {
            for (const [form, canonical] of WB81_ACCEPTED_FORMS) {
                const [typed, written] = [buildDedupKey(tx(recurringBuy(form)), new Map()), buildDedupKey(tx(recurringBuy(canonical)), new Map())];
                expect(typed, `W-B81: ${show(form)} is a plain decimal, so it forms a key`).not.toBeNull();
                expect(written, `control: ${canonical} forms a key`).not.toBeNull();
                expect(dedupKeysMatch(typed as DedupKey, written as DedupKey), `W-B81: ${show(form)} meets ${canonical}`).toBe(true);
            }
        });
    });

    describe('dedupKeysMatch: two adjustment legs that differ only in their per-unit cost override', () => {
        // The shared table again, on the cost override: the same rule, not a second one.
        eachPair(
            [SHARED],
            ({id, a, b, match}) => `${id}: book prices ${a} and ${b} are ${verdict(match)}`,
            ({id, a, b, match, why}) => {
                expect(dedupKeysMatch(legWith(a), legWith(b)), `W-B81 ${id}, on the cost override: ${why}`).toBe(match);
                expect(dedupKeysMatch(legWith(b), legWith(a)), `W-B81 ${id}, on the cost override, the other way round: ${why}`).toBe(match);
            },
        );
    });

    describe('dedupKeysMatch: the cash amount, within 0.01, computed exactly', () => {
        it('keeps two amounts 0.01 apart together, on the bound, and two amounts 0.011 apart apart', () => {
            // As floats, -100 and -100.01 are 0.010000000000005116 apart: outside the very bound they sit on.
            expect(dedupKeysMatch(keyWith({cashAmount: '-100'}), keyWith({cashAmount: '-100.01'})), 'W-B81: |-100 − (-100.01)| = 0.01, within 0.01').toBe(true);
            expect(dedupKeysMatch(keyWith({cashAmount: '-100'}), keyWith({cashAmount: '-100.011'})), 'W-B81: |-100 − (-100.011)| = 0.011, beyond 0.01').toBe(false);
        });

        it("reads a blank amount on a key as nothing: '0' is the reading of getDedupCurrency, not of the comparison", () => {
            expect(dedupKeysMatch(keyWith({cashAmount: '0'}), keyWith({cashAmount: '0'})), 'control: two keys of 0 EUR').toBe(true);
            for (const blank of ['', '   ']) {
                expect(dedupKeysMatch(keyWith({cashAmount: blank}), keyWith({cashAmount: '0'})), `W-B81: a cash amount of ${show(blank)} on a key is no 0`).toBe(false);
                expect(dedupKeysMatch(keyWith({cashAmount: blank}), keyWith({cashAmount: blank})), `W-B81: not even a key of the same blank ${show(blank)}`).toBe(false);
            }
        });
    });

    describe('describeDedupKey: the identity of a group, the exact text of its numbers', () => {
        eachPair(
            [SHARED, FRONTEND_ONLY],
            ({id, a, b, identity}) => `${id}: ${a} → ${identity[0]}, ${b} → ${identity[1]}`,
            ({id, a, b, match, identity}) => {
                const [first, second] = [identityOf(a), identityOf(b)];
                // Two quantities the rule keeps apart are two groups: one identity for both would conflate them.
                if (!match) expect(first, `W-B81 ${id}: ${a} and ${b} are two movements, so two groups, yet they share one identity`).not.toBe(second);
                expect(first, `W-B81 ${id}: the identity of ${a}`).toBe(identityText(identity[0]));
                expect(second, `W-B81 ${id}: the identity of ${b}`).toBe(identityText(identity[1]));
            },
        );

        it('writes every text of one value as one identity, in plain notation, without padding zeros', () => {
            for (const written of ['10', '10.0', '10.000000']) expect.soft(identityOf(written), `W-B81: ${written} is 10`).toBe(identityText('10'));
            expect.soft(identityOf('0.000000150'), 'W-B81: 0.000000150 is 0.00000015, never 1.5e-7').toBe(identityText('0.00000015'));
            expect.soft(identityOf('0.00'), 'W-B81: 0.00 is 0').toBe(identityText('0'));
            for (const [form, canonical] of WB81_ACCEPTED_FORMS) expect.soft(identityOf(form), `W-B81: ${show(form)} is ${canonical}`).toBe(identityText(canonical));
        });

        it('writes the cash amount and the per-unit cost override the same way, from the key alone', () => {
            const key: DedupKey = {broker: '1', type: 'BUY', date: '2024-01-02', quantity: '10.000000', cashCode: 'EUR', cashAmount: '-100.50', costOverride: '5.50', assetIdentity: 'asset:5'};
            expect(describeDedupKey(key), 'W-B81: whatever text the key carries, the identity is its exact value').toBe('1|BUY|2024-01-02|10|EUR|-100.5|5.5|asset:5');
        });
    });

    describe('buildDedupKey: a quantity that is no plain finite decimal forms no key; a blank quantity or cash amount reads as 0', () => {
        /** A deposit as a parse report writes it (quantity 0), or as the bulk editor sends it once a field was cleared. */
        const deposit = (quantity: string, amount = '100'): Record<string, unknown> => ({broker_id: 1, type: 'DEPOSIT', date: '2024-01-02', quantity, cash: {code: 'EUR', amount}, description: 'Deposit'});

        it("a blank cash amount reads as '0' too: a deposit whose cash amount was cleared meets the same deposit written '0'", () => {
            const written = buildDedupKey(tx(deposit('0', '0')), new Map());
            expect(written, 'control: a deposit of 0 EUR forms a key').not.toBeNull();
            for (const amount of ['', '   ']) {
                const cleared = buildDedupKey(tx(deposit('0', amount)), new Map());
                expect(cleared, `W-B81: a deposit whose cash amount is ${show(amount)} forms a key`).not.toBeNull();
                expect(dedupKeysMatch(cleared as DedupKey, written as DedupKey), `W-B81: the deposit whose cash amount is ${show(amount)} meets the same deposit written '0'`).toBe(true);
                expect(cleared?.cashAmount, `W-B81: the key carries the text '0' for a cash amount of ${show(amount)}`).toBe('0');
            }
        });

        for (const {id, quantity, blank, why} of NOT_PLAIN_DECIMALS) {
            if (blank) {
                it(`${id}: ${show(quantity)} reads as '0', the payload's default: a cash row whose quantity was cleared still meets its twin`, () => {
                    const [cleared, parsed] = [buildDedupKey(tx(deposit(quantity)), new Map()), buildDedupKey(tx(deposit('0')), new Map())];
                    expect(parsed, 'control: a deposit of quantity 0 forms a key').not.toBeNull();
                    expect(cleared, `W-B81 ${id}: a blank quantity still forms a key`).not.toBeNull();
                    expect(dedupKeysMatch(cleared as DedupKey, parsed as DedupKey), `W-B81 ${id}: the cleared deposit meets its twin of quantity 0`).toBe(true);
                    expect(cleared?.quantity, `W-B81 ${id}: the key carries the text '0'`).toBe('0');
                });
                continue;
            }
            it(`${id}: ${show(quantity)} forms no key`, () => {
                expect(buildDedupKey(tx(recurringBuy('0.5')), new Map()), 'control: a buy of 0.5 forms a key').not.toBeNull();
                expect(buildDedupKey(tx(recurringBuy(quantity)), new Map()), `W-B81 ${id}: ${why}, so it cannot be compared`).toBeNull();
            });
        }
    });

    describe('buildDuplicateGroups', () => {
        it('recurring-buys-at-8-decimals: two recurring buys, in two files, are no group', () => {
            const rows = [mt(0, 'fileA', recurringBuy('0.00015123')), mt(1, 'fileB', recurringBuy('0.00015098'))];
            expect(buildDuplicateGroups(rows, new Map()), 'W-B81: 0.00015123 (fileA) and 0.00015098 (fileB) are two buys of the same 10 EUR; grouped, the second is resolved away from step 4 by default').toEqual([]);
        });

        it('report-rounded: a rounded report and the precise one, in two files, are still one group', () => {
            const rows = [mt(0, 'fileA', recurringBuy('0.000153')), mt(1, 'fileB', recurringBuy('0.00015'))];
            const groups = buildDuplicateGroups(rows, new Map());
            expect(
                groups.map((g) => ({members: g.memberIndices, tier: g.tier})),
                'W-B81: 0.000153 rounded half-up to 5 decimals is 0.00015, the same buy in two files',
            ).toEqual([{members: [0, 1], tier: 'sure'}]);
        });

        it('two overlapping exports of the same two recurring buys: one group per buy, each under its own key', () => {
            const rows = [mt(0, 'fileA', recurringBuy('0.00015123')), mt(1, 'fileA', recurringBuy('0.00015098')), mt(2, 'fileB', recurringBuy('0.00015123')), mt(3, 'fileB', recurringBuy('0.00015098'))];
            const groups = buildDuplicateGroups(rows, new Map());
            expect(groups.map((g) => g.memberIndices.join('+')).sort(), 'W-B81: each buy pairs with its own copy in the other file, and with nothing else').toEqual(['0+2', '1+3']);
            expect(new Set(groups.map((g) => g.key)).size, "W-B81: the wizard finds a row's group by its key (dupGroupKey): two groups, two keys").toBe(groups.length);
        });
    });
});
