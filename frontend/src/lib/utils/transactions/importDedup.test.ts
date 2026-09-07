import {describe, it, expect} from 'vitest';
import {FAKE_ASSET_ID_BASE} from '$lib/utils/brim/isFakeAssetId';
import type {TransactionCreateItem} from '$lib/types';
import type {AssetResolution, DedupKey, MergedTx} from './importTypes';
import {
    buildDedupKey,
    buildDuplicateGroups,
    dedupKeysMatch,
    describeDedupKey,
    duplicateStatusAllowsAutoSelect,
    duplicateStatusIsSelectedWarning,
    getDedupCash,
    getDedupCurrency,
    isResolvedAwayDuplicate,
    normalizeAssetToken,
    normalizeDedupDescription,
    pendingDuplicateStatusFor,
    resolveDedupAssetIdentity,
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
