import {describe, it, expect} from 'vitest';
import {FAKE_ASSET_ID_BASE} from '$lib/utils/brim/isFakeAssetId';
import type {AssetResolution, MergedTx} from './importTypes';
import type {TransactionCreateItem} from '$lib/types';
import {brokerIdForTx, beforeOpeningInfo, isBeforeOpening, isRowAssetResolved, shouldAutoSelectOnRecheck, type RowBrokerSource, type BrokerOpening} from './importRowState';

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

describe('shouldAutoSelectOnRecheck (W7)', () => {
    // The residual case from the beta: a row gated on before-opening whose asset
    // is ALSO unresolved. Fixing the broker opening first must NOT select it
    // (still unresolved); assigning the asset afterwards MUST — that second pass
    // is the one the pre-W7 `resolveAsset` never ran.
    const row = () => mt({sourceFileId: 'f1', date: '2020-03-01', asset_id: FAKE});
    const results = [pr('f1', 1)];
    const brokerClosed = [brk(1, '2024-06-01')]; // row (2020-03-01) is before-opening
    const brokerFixed = [brk(1, '2019-01-01')]; // opening moved before the row

    it('stays deselected while both gates are closed', () => {
        expect(shouldAutoSelectOnRecheck(row(), results, brokerClosed, [resolution(FAKE, null)])).toBe(false);
    });

    it('stays deselected when only the broker opening is fixed (asset still unresolved)', () => {
        expect(shouldAutoSelectOnRecheck(row(), results, brokerFixed, [resolution(FAKE, null)])).toBe(false);
    });

    it('stays deselected when only the asset is resolved (still before-opening)', () => {
        expect(shouldAutoSelectOnRecheck(row(), results, brokerClosed, [resolution(FAKE, 100)])).toBe(false);
    });

    it('selects once both gates are open — the order the user fixed them in does not matter', () => {
        expect(shouldAutoSelectOnRecheck(row(), results, brokerFixed, [resolution(FAKE, 100)])).toBe(true);
    });

    it('never re-selects a row the user already has selected', () => {
        const selected = {...row(), selected: true};
        expect(shouldAutoSelectOnRecheck(selected, results, brokerFixed, [resolution(FAKE, 100)])).toBe(false);
    });

    it('never selects a row whose duplicate verdict forbids it', () => {
        const dup = {...row(), duplicateStatus: 'likely' as const};
        expect(shouldAutoSelectOnRecheck(dup, results, brokerFixed, [resolution(FAKE, 100)])).toBe(false);
    });
});

// ---------------------------------------------------------------------------
// Report sets (phase C2): rows dated before the broker history H0
// ---------------------------------------------------------------------------
//
// The parse of a combined report-set file says where the broker history already in LibreFolio
// starts (`history_start`, H0). What precedes H0 is already represented — on a first import by
// the opening correction — so those rows are never imported: strictly before, because the rows
// of H0 itself are in the history and the duplicate check judges them.
//
// The two new predicates are loaded per test: while one is missing, its own tests fail and the
// rest of the file keeps running.

/** A parse result that also carries the response's H0. */
const prH0 = (fileId: string, brokerId: number, history_start: string | null | undefined): RowBrokerSource => ({fileId, brokerId, response: {history_start}}) as RowBrokerSource;

interface RowStateC2 {
    historyStartFor: (mt: MergedTx, parseResults: RowBrokerSource[]) => string | null;
    isBeforeHistory: (mt: MergedTx, parseResults: RowBrokerSource[]) => boolean;
}

async function rowStateC2<K extends keyof RowStateC2>(name: K): Promise<RowStateC2[K]> {
    const mod = (await import('./importRowState')) as unknown as Partial<RowStateC2>;
    const fn = mod[name];
    if (typeof fn !== 'function') throw new Error(`importRowState.${name} is not implemented yet (report sets, phase C2)`);
    return fn as RowStateC2[K];
}

describe('historyStartFor (C2)', () => {
    it('returns the H0 of the response the row comes from', async () => {
        const historyStartFor = await rowStateC2('historyStartFor');
        const results = [prH0('combined', 1, '2020-02-03'), prH0('other', 1, '2021-01-04')];
        expect(historyStartFor(mt({sourceFileId: 'combined'}), results)).toBe('2020-02-03');
        expect(historyStartFor(mt({sourceFileId: 'other'}), results)).toBe('2021-01-04');
    });

    it('is null when the source file is unknown', async () => {
        const historyStartFor = await rowStateC2('historyStartFor');
        expect(historyStartFor(mt({sourceFileId: 'missing'}), [prH0('combined', 1, '2020-02-03')])).toBeNull();
    });

    it('is null when the response carries no H0, or there is no response', async () => {
        const historyStartFor = await rowStateC2('historyStartFor');
        expect(historyStartFor(mt({sourceFileId: 'f1'}), [prH0('f1', 1, null)])).toBeNull();
        expect(historyStartFor(mt({sourceFileId: 'f1'}), [prH0('f1', 1, undefined)])).toBeNull();
        expect(historyStartFor(mt({sourceFileId: 'f1'}), [{fileId: 'f1', brokerId: 1, response: null} as RowBrokerSource])).toBeNull();
        expect(historyStartFor(mt({sourceFileId: 'f1'}), [pr('f1', 1)])).toBeNull();
    });
});

describe('isBeforeHistory (C2)', () => {
    const results = [prH0('combined', 1, '2020-02-03'), prH0('generic', 1, null)];

    it('is true strictly before H0', async () => {
        const isBeforeHistory = await rowStateC2('isBeforeHistory');
        expect(isBeforeHistory(mt({sourceFileId: 'combined', date: '2020-02-02'}), results)).toBe(true);
        expect(isBeforeHistory(mt({sourceFileId: 'combined', date: '2019-01-07'}), results)).toBe(true);
    });

    it('is false on H0 itself: those rows are in the history, and the duplicate check judges them', async () => {
        const isBeforeHistory = await rowStateC2('isBeforeHistory');
        expect(isBeforeHistory(mt({sourceFileId: 'combined', date: '2020-02-03'}), results)).toBe(false);
    });

    it('is false after H0', async () => {
        const isBeforeHistory = await rowStateC2('isBeforeHistory');
        expect(isBeforeHistory(mt({sourceFileId: 'combined', date: '2020-02-04'}), results)).toBe(false);
    });

    it('compares the day of a date-time', async () => {
        const isBeforeHistory = await rowStateC2('isBeforeHistory');
        expect(isBeforeHistory(mt({sourceFileId: 'combined', date: '2020-02-02T23:59:59Z'}), results)).toBe(true);
        expect(isBeforeHistory(mt({sourceFileId: 'combined', date: '2020-02-03T00:00:00'}), results)).toBe(false);
    });

    it('is false without an H0 for the row: none in the response, no response, or an unknown file', async () => {
        const isBeforeHistory = await rowStateC2('isBeforeHistory');
        expect(isBeforeHistory(mt({sourceFileId: 'generic', date: '2019-01-07'}), results)).toBe(false);
        expect(isBeforeHistory(mt({sourceFileId: 'plain', date: '2019-01-07'}), [pr('plain', 1)])).toBe(false);
        expect(isBeforeHistory(mt({sourceFileId: 'missing', date: '2019-01-07'}), results)).toBe(false);
    });

    it('is false for a row without a date', async () => {
        const isBeforeHistory = await rowStateC2('isBeforeHistory');
        expect(isBeforeHistory(mt({sourceFileId: 'combined', date: undefined}), results)).toBe(false);
    });
});

describe('shouldAutoSelectOnRecheck — rows before H0 (C2)', () => {
    // Every other gate open: no opening date, no fake asset, a unique row.
    const early = () => mt({sourceFileId: 'combined', date: '2019-11-04'});
    const brokers = [brk(1, null)];

    it('never re-selects a row dated before H0', () => {
        expect(shouldAutoSelectOnRecheck(early(), [prH0('combined', 1, '2020-02-03')], brokers, [])).toBe(false);
    });

    it('still re-selects the same row once H0 is earlier than it (unchanged behaviour)', () => {
        expect(shouldAutoSelectOnRecheck(early(), [prH0('combined', 1, '2019-01-01')], brokers, [])).toBe(true);
    });

    it('still re-selects a row on H0 itself (unchanged behaviour)', () => {
        expect(shouldAutoSelectOnRecheck(mt({sourceFileId: 'combined', date: '2020-02-03'}), [prH0('combined', 1, '2020-02-03')], brokers, [])).toBe(true);
    });
});
