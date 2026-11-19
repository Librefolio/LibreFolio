/**
 * The rows of the transactions table and their pages (`txTableRows.ts`), as pure functions.
 *
 * Two parts:
 *
 *  1. CHARACTERIZATION of `paginateRows` as it was moved out of `TransactionsTable.svelte`: flat mode slices at a fixed
 *     size; grouped mode closes a page only before a row that does not follow the previous one, so the receiver half of
 *     a pair overflows a full page (N+1) and nothing is pushed to the next page. These are green before lot F5 and must
 *     stay green after it.
 *
 *  2. Lot F5 (project 66, linked charges — contract `66-F5-contract.md` §2): `foldCharges(rows, {folded, expandedIds,
 *     passes})` folds a parent's FEE/TAX (`parent_transaction_id`) under it, and `paginateRows` keeps an open group on
 *     one page as it keeps a pair.
 *
 * The module is imported as a namespace, so a function that does not exist yet fails its own tests and not the
 * characterization ones in the same file.
 */
import {describe, expect, it} from 'vitest';
import * as txRows from './txTableRows';
import type {DisplayRow} from './txTableRows';
import type {TXReadItem} from './types';

// ---------------------------------------------------------------------------
// Builders
// ---------------------------------------------------------------------------

const BROKER_ID = 7;

function tx(id: number, type: string, extra: Partial<TXReadItem> = {}): TXReadItem {
    return {
        id,
        broker_id: BROKER_ID,
        asset_id: null,
        type,
        date: '2026-05-01',
        quantity: '0',
        cash: {code: 'EUR', amount: '-1.00'},
        related_transaction_id: null,
        parent_transaction_id: null,
        asset_event_id: null,
        tags: [],
        description: null,
        ...extra,
    } as TXReadItem;
}

/** A display row with the F5 fields at their defaults (what the pair-building pass produces). */
function row(t: TXReadItem, extra: Partial<DisplayRow> = {}): DisplayRow {
    return {
        tx: t,
        isGhost: false,
        isReceiver: false,
        pairAnchorId: null,
        sortIndex: t.id,
        chargeCount: 0,
        chargeOfId: null,
        isChargeRow: false,
        followTx: null,
        ...extra,
    } as DisplayRow;
}

/** A standalone row of type `type`. */
function standalone(id: number, type = 'DEPOSIT'): DisplayRow {
    return row(tx(id, type));
}

/** A linked pair: giver then receiver, both anchored on the giver. */
function pair(giverId: number, receiverId: number): [DisplayRow, DisplayRow] {
    const g = tx(giverId, 'FX_CONVERSION', {related_transaction_id: receiverId, cash: {code: 'EUR', amount: '-100.00'}});
    const r = tx(receiverId, 'FX_CONVERSION', {related_transaction_id: giverId, cash: {code: 'USD', amount: '109.00'}});
    return [row(g, {pairAnchorId: giverId}), row(r, {isReceiver: true, pairAnchorId: giverId})];
}

/** A charge (FEE or TAX) linked to `parentId`. */
function charge(id: number, parentId: number, type: 'FEE' | 'TAX' = 'FEE'): DisplayRow {
    return row(tx(id, type, {parent_transaction_id: parentId, cash: {code: 'EUR', amount: '-2.00'}}));
}

function ids(rows: DisplayRow[]): number[] {
    return rows.map((d) => d.tx.id);
}

function pageIds(pages: DisplayRow[][]): number[][] {
    return pages.map(ids);
}

// ---------------------------------------------------------------------------
// 1. Characterization of paginateRows (green before F5)
// ---------------------------------------------------------------------------

describe('paginateRows — flat mode (characterization)', () => {
    const rows = [1, 2, 3, 4, 5].map((id) => standalone(id));

    it('slices at a fixed size, the last page holding the rest', () => {
        expect(pageIds(txRows.paginateRows(rows, 2, false))).toEqual([[1, 2], [3, 4], [5]]);
    });

    it('a pair is two independent rows: the receiver goes to the next page when the page is full', () => {
        const [g, r] = pair(11, 12);
        expect(pageIds(txRows.paginateRows([standalone(1), g, r, standalone(2)], 2, false))).toEqual([
            [1, 11],
            [12, 2],
        ]);
    });

    it('pageSize 0 or below is one page with every row', () => {
        expect(pageIds(txRows.paginateRows(rows, 0, false))).toEqual([[1, 2, 3, 4, 5]]);
        expect(pageIds(txRows.paginateRows(rows, -1, false))).toEqual([[1, 2, 3, 4, 5]]);
    });

    it('«all» (999999) is one page', () => {
        expect(pageIds(txRows.paginateRows(rows, 999999, false))).toEqual([[1, 2, 3, 4, 5]]);
    });

    it('no rows is one empty page', () => {
        expect(txRows.paginateRows([], 10, false)).toEqual([[]]);
        expect(txRows.paginateRows([], 0, false)).toEqual([[]]);
    });
});

describe('paginateRows — grouped mode (characterization)', () => {
    it('standalone rows slice at the page size', () => {
        const rows = [1, 2, 3, 4, 5].map((id) => standalone(id));
        expect(pageIds(txRows.paginateRows(rows, 2, true))).toEqual([[1, 2], [3, 4], [5]]);
    });

    it('a receiver arriving on a full page overflows it (N+1): nothing is pushed to the next page', () => {
        const [g, r] = pair(11, 12);
        // Page 1 is full after [1, 11]; the receiver 12 still joins it.
        expect(pageIds(txRows.paginateRows([standalone(1), g, r, standalone(2)], 2, true))).toEqual([[1, 11, 12], [2]]);
    });

    it('a giver arriving on a full page opens the next one, its receiver follows it there', () => {
        const [g, r] = pair(11, 12);
        expect(pageIds(txRows.paginateRows([standalone(1), standalone(2), g, r, standalone(3)], 2, true))).toEqual([[1, 2], [11, 12], [3]]);
    });

    it('a pair that fits stays where it is', () => {
        const [g, r] = pair(11, 12);
        expect(pageIds(txRows.paginateRows([g, r, standalone(1), standalone(2)], 2, true))).toEqual([
            [11, 12],
            [1, 2],
        ]);
    });

    it('«all» (999999) is one page', () => {
        const [g, r] = pair(11, 12);
        expect(pageIds(txRows.paginateRows([standalone(1), g, r, standalone(2)], 999999, true))).toEqual([[1, 11, 12, 2]]);
    });

    it('no rows is one empty page', () => {
        expect(txRows.paginateRows([], 10, true)).toEqual([[]]);
    });
});

// ---------------------------------------------------------------------------
// 2. Lot F5 — foldCharges
// ---------------------------------------------------------------------------

type FoldOptions = {folded: boolean; expandedIds: Set<number>; passes: (row: DisplayRow) => boolean};
type FoldCharges = (rows: DisplayRow[], options: FoldOptions) => DisplayRow[];

/** The function under test, or a clear failure naming it when it does not exist yet. */
function foldCharges(rows: DisplayRow[], options: FoldOptions): DisplayRow[] {
    const fn = (txRows as unknown as {foldCharges?: FoldCharges}).foldCharges;
    expect(fn, 'txTableRows exports foldCharges').toBeTypeOf('function');
    return fn!(rows, options);
}

const ALL = () => true;

/**
 * The fixture: a BUY (100) with a FEE (101) and a TAX (102), listed in the order the backend might give them — a charge
 * before its parent — around an unrelated DEPOSIT (200) and a pair (300/301).
 */
function fixture() {
    const buy = row(tx(100, 'BUY', {quantity: '10', cash: {code: 'EUR', amount: '-100.00'}}));
    const fee = charge(101, 100, 'FEE');
    const tax = charge(102, 100, 'TAX');
    const deposit = standalone(200);
    const [giver, receiver] = pair(300, 301);
    // Order: FEE, BUY, DEPOSIT, TAX, giver, receiver.
    const rows = [fee, buy, deposit, tax, giver, receiver];
    return {buy, fee, tax, deposit, giver, receiver, rows};
}

function byId(rows: DisplayRow[], id: number): DisplayRow {
    const found = rows.find((d) => d.tx.id === id);
    if (!found) throw new Error(`row ${id} not in [${ids(rows).join(', ')}]`);
    return found;
}

describe('foldCharges — folded, nothing open', () => {
    it('hides the charges and gives their parent the count', () => {
        const {rows} = fixture();

        const out = foldCharges(rows, {folded: true, expandedIds: new Set(), passes: ALL});

        expect(ids(out)).toEqual([100, 200, 300, 301]);
        expect(byId(out, 100)).toMatchObject({chargeCount: 2, chargeOfId: null, isChargeRow: false, followTx: null});
        expect(byId(out, 200)).toMatchObject({chargeCount: 0, chargeOfId: null, isChargeRow: false});
    });

    it('leaves a pair as it is', () => {
        const {rows} = fixture();

        const out = foldCharges(rows, {folded: true, expandedIds: new Set(), passes: ALL});

        expect(byId(out, 300)).toMatchObject({isReceiver: false, pairAnchorId: 300, isGhost: false, chargeCount: 0, isChargeRow: false, chargeOfId: null});
        expect(byId(out, 301)).toMatchObject({isReceiver: true, pairAnchorId: 300, isGhost: false, chargeCount: 0, isChargeRow: false, chargeOfId: null});
    });
});

describe('foldCharges — folded, the parent open', () => {
    it('emits the charges right after the parent, in list order, each pointing at it', () => {
        const {rows, buy} = fixture();

        const out = foldCharges(rows, {folded: true, expandedIds: new Set([100]), passes: ALL});

        expect(ids(out)).toEqual([100, 101, 102, 200, 300, 301]);
        expect(byId(out, 100)).toMatchObject({chargeCount: 2, chargeOfId: null, isChargeRow: false});
        for (const id of [101, 102]) {
            const d = byId(out, id);
            expect(d, `charge ${id}`).toMatchObject({chargeOfId: 100, isChargeRow: true, chargeCount: 0});
            expect(d.followTx, `charge ${id} follows its parent`).toBe(buy.tx);
        }
    });

    it('opening another id changes nothing', () => {
        const {rows} = fixture();

        const out = foldCharges(rows, {folded: true, expandedIds: new Set([200, 999]), passes: ALL});

        expect(ids(out)).toEqual([100, 200, 300, 301]);
    });
});

describe('foldCharges — folded, with a filter that is not on the type', () => {
    it('a parent that passes keeps its charges under it, even a charge that does not pass', () => {
        const {rows} = fixture();
        // The filter keeps the BUY and the TAX, not the FEE: the FEE follows its parent all the same.
        const passes = (d: DisplayRow) => d.tx.id !== 101;

        const closed = foldCharges(rows, {folded: true, expandedIds: new Set(), passes});
        expect(ids(closed)).toEqual([100, 200, 300, 301]);
        expect(byId(closed, 100).chargeCount).toBe(2);

        const open = foldCharges(rows, {folded: true, expandedIds: new Set([100]), passes});
        expect(ids(open)).toEqual([100, 101, 102, 200, 300, 301]);
        expect(byId(open, 101)).toMatchObject({chargeOfId: 100, isChargeRow: true});
    });

    it('a parent that does not pass hides itself; its charge that passes is a row of its own', () => {
        const {rows} = fixture();
        // The filter drops the BUY, keeps the FEE, drops the TAX.
        const passes = (d: DisplayRow) => d.tx.id !== 100 && d.tx.id !== 102;

        const out = foldCharges(rows, {folded: true, expandedIds: new Set([100]), passes});

        expect(ids(out)).toEqual([101, 200, 300, 301]);
        expect(byId(out, 101)).toMatchObject({chargeOfId: null, isChargeRow: true, followTx: null, chargeCount: 0});
    });

    it('rows that do not pass are not emitted', () => {
        const {rows} = fixture();
        const passes = (d: DisplayRow) => d.tx.id === 200;

        const out = foldCharges(rows, {folded: true, expandedIds: new Set([100]), passes});

        expect(ids(out)).toEqual([200]);
    });
});

describe('foldCharges — folded, a charge whose parent is not in the list', () => {
    it('is a row of its own', () => {
        const orphan = charge(401, 999, 'TAX');
        const deposit = standalone(200);

        const out = foldCharges([orphan, deposit], {folded: true, expandedIds: new Set([999]), passes: ALL});

        expect(ids(out)).toEqual([401, 200]);
        expect(byId(out, 401)).toMatchObject({chargeOfId: null, isChargeRow: true, followTx: null});
    });
});

describe('foldCharges — flat (not folded): annotate only', () => {
    it('keeps every row and the order, marks the charges and counts on the parent', () => {
        const {rows} = fixture();

        const out = foldCharges(rows, {folded: false, expandedIds: new Set(), passes: ALL});

        expect(ids(out)).toEqual([101, 100, 200, 102, 300, 301]);
        expect(byId(out, 100)).toMatchObject({chargeCount: 2, isChargeRow: false, chargeOfId: null});
        expect(byId(out, 101)).toMatchObject({isChargeRow: true, chargeOfId: null, followTx: null, chargeCount: 0});
        expect(byId(out, 102)).toMatchObject({isChargeRow: true, chargeOfId: null, followTx: null, chargeCount: 0});
        expect(byId(out, 200)).toMatchObject({isChargeRow: false, chargeCount: 0});
        expect(byId(out, 301)).toMatchObject({isReceiver: true, pairAnchorId: 300, isChargeRow: false});
    });

    it('an open parent changes nothing: no row moves, none is repeated', () => {
        const {rows} = fixture();

        const out = foldCharges(rows, {folded: false, expandedIds: new Set([100]), passes: ALL});

        expect(ids(out)).toEqual([101, 100, 200, 102, 300, 301]);
    });

    it("the predicate is not applied: filtering is DataTable's in flat mode", () => {
        const {rows} = fixture();

        const out = foldCharges(rows, {folded: false, expandedIds: new Set(), passes: () => false});

        expect(ids(out)).toEqual([101, 100, 200, 102, 300, 301]);
    });
});

// ---------------------------------------------------------------------------
// 2. Lot F5 — paginateRows with an open group
// ---------------------------------------------------------------------------

describe('paginateRows — grouped mode with an open parent', () => {
    it('a charge under its parent never starts a page: it overflows with its group', () => {
        const parent = row(tx(100, 'BUY'), {chargeCount: 2});
        const fee = charge(101, 100, 'FEE');
        const tax = charge(102, 100, 'TAX');
        const under = [row(fee.tx, {isChargeRow: true, chargeOfId: 100, followTx: parent.tx}), row(tax.tx, {isChargeRow: true, chargeOfId: 100, followTx: parent.tx})];

        const pages = txRows.paginateRows([standalone(1), parent, ...under, standalone(2)], 2, true);

        expect(pageIds(pages)).toEqual([[1, 100, 101, 102], [2]]);
    });

    it('a parent arriving on a full page takes its open charges to the next one', () => {
        const parent = row(tx(100, 'BUY'), {chargeCount: 1});
        const under = row(tx(101, 'FEE', {parent_transaction_id: 100}), {isChargeRow: true, chargeOfId: 100, followTx: parent.tx});

        const pages = txRows.paginateRows([standalone(1), standalone(2), parent, under, standalone(3)], 2, true);

        expect(pageIds(pages)).toEqual([[1, 2], [100, 101], [3]]);
    });

    it('a charge standing on its own (no parent shown) is an ordinary row: it starts a page like any other', () => {
        const lone = row(tx(101, 'FEE', {parent_transaction_id: 100}), {isChargeRow: true, chargeOfId: null});

        const pages = txRows.paginateRows([standalone(1), standalone(2), lone, standalone(3)], 2, true);

        expect(pageIds(pages)).toEqual([
            [1, 2],
            [101, 3],
        ]);
    });
});
