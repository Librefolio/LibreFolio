import {describe, it, expect} from 'vitest';
import {FAKE_ASSET_ID_BASE} from '$lib/utils/brim/isFakeAssetId';
import type {AssetResolution, MergedTx} from './importTypes';
import type {TransactionCreateItem} from '$lib/types';
import {brokerIdForTx, beforeOpeningInfo, isBeforeOpening, isRowAssetResolved, type RowBrokerSource, type BrokerOpening} from './importRowState';

const FAKE = FAKE_ASSET_ID_BASE;

/** A MergedTx with only the fields these predicates read. */
const mt = (over: {sourceFileId?: string; date?: unknown; asset_id?: unknown; index?: number} = {}): MergedTx =>
    ({
        index: over.index ?? 0,
        sourceFileId: over.sourceFileId ?? 'fileA',
        tx: {date: over.date, asset_id: over.asset_id} as unknown as TransactionCreateItem,
        selected: false,
        duplicateStatus: 'unique',
        dupMatches: [],
        todos: [],
    }) as MergedTx;

const pr = (fileId: string, brokerId: number): RowBrokerSource => ({fileId, brokerId});
const brk = (id: number, opened_at?: string | null): BrokerOpening => ({id, opened_at});
const resolution = (fakeAssetId: number, resolvedAssetId: number | null): AssetResolution => ({fakeAssetId, resolvedAssetId}) as unknown as AssetResolution;

describe('brokerIdForTx', () => {
    it('returns the broker of the row source file', () => {
        expect(brokerIdForTx(mt({sourceFileId: 'f1'}), [pr('f1', 7), pr('f2', 9)])).toBe(7);
    });
    it('returns null when the source file is unknown', () => {
        expect(brokerIdForTx(mt({sourceFileId: 'missing'}), [pr('f1', 7)])).toBeNull();
    });
});

describe('beforeOpeningInfo', () => {
    it('returns null when the row has no known broker', () => {
        expect(beforeOpeningInfo(mt({sourceFileId: 'x'}), [], [brk(1, '2024-01-01')])).toBeNull();
    });
    it('returns null when the broker carries no opening date', () => {
        expect(beforeOpeningInfo(mt({sourceFileId: 'f1'}), [pr('f1', 1)], [brk(1, null)])).toBeNull();
    });
    it('returns null when the broker is absent from the list', () => {
        expect(beforeOpeningInfo(mt({sourceFileId: 'f1'}), [pr('f1', 1)], [brk(2, '2024-01-01')])).toBeNull();
    });
    it('returns broker id and opening date when both are known', () => {
        expect(beforeOpeningInfo(mt({sourceFileId: 'f1'}), [pr('f1', 1)], [brk(1, '2024-01-01')])).toEqual({brokerId: 1, openedAt: '2024-01-01'});
    });
});

describe('isBeforeOpening', () => {
    const results = [pr('f1', 1)];
    const brokers = [brk(1, '2024-06-01')];

    it('is false when there is no opening info', () => {
        expect(isBeforeOpening(mt({sourceFileId: 'x', date: '2020-01-01'}), results, brokers)).toBe(false);
    });
    it('is false for a row with no date', () => {
        expect(isBeforeOpening(mt({sourceFileId: 'f1', date: undefined}), results, brokers)).toBe(false);
    });
    it('is false on the opening day itself (strict comparison)', () => {
        expect(isBeforeOpening(mt({sourceFileId: 'f1', date: '2024-06-01'}), results, brokers)).toBe(false);
    });
    it('is false after the opening day', () => {
        expect(isBeforeOpening(mt({sourceFileId: 'f1', date: '2024-06-02'}), results, brokers)).toBe(false);
    });
    it('is true strictly before the opening day', () => {
        expect(isBeforeOpening(mt({sourceFileId: 'f1', date: '2024-05-31'}), results, brokers)).toBe(true);
    });
});

describe('isRowAssetResolved', () => {
    it('is true for a row with no asset id', () => {
        expect(isRowAssetResolved(mt({asset_id: undefined}), [])).toBe(true);
    });
    it('is true for a row bound to a real (non-fake) asset', () => {
        expect(isRowAssetResolved(mt({asset_id: 42}), [])).toBe(true);
    });
    it('is true for a fake asset that has been resolved to a real one', () => {
        expect(isRowAssetResolved(mt({asset_id: FAKE}), [resolution(FAKE, 100)])).toBe(true);
    });
    it('is false for a fake asset still awaiting resolution', () => {
        expect(isRowAssetResolved(mt({asset_id: FAKE}), [resolution(FAKE, null)])).toBe(false);
    });
    it('is false for a fake asset with no resolution entry at all', () => {
        expect(isRowAssetResolved(mt({asset_id: FAKE}), [])).toBe(false);
    });
});
