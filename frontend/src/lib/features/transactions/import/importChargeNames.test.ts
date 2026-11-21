/**
 * Linked charges at the import hand-over (project 66, lot P1b; contract `66-P1b-contract.md` §1.1, corrected by §4) —
 * the pure half, written red before `importChargeNames.ts` exists: its two exports' signatures are the contract's, their
 * behaviour comes after these tests.
 *
 * completeChargeNames(rows, newName)
 *   Takes the rows CHOSEN for one hand-over (after `completePairsOnly`: a row the user unticked, a duplicate, a row
 *   before the broker's opening is simply not among them) and returns them with their names renewed, under the key of
 *   the pairs: file + name.
 *     - A row with `ref` gets a new name, one per key and per hand-over; the charges of the same file that name it get
 *       the same new name in `parent_ref`.
 *     - A charge whose parent is not among the chosen rows loses `parent_ref`, and stands alone (D10).
 *     - A parent that no chosen charge names loses `ref`: nothing needs it.
 *     - Rows without names are left as they are; no name of the parse survives; the length and the order are kept; the
 *       input is not mutated; the result depends on `newName` only.
 *   A cleared name is read as `?? null`: absent, null and undefined are the same «no name» to the batch.
 *
 * splitLegRows(row, legs)
 *   The legs of the wizard's split, lifted out of `applyFixToRow` (ImportWizardModal.svelte) with today's result for
 *   every field (pinned field by field below, the same shape `ImportWizardModal.test.ts` pins through the wizard), and
 *   in addition: no leg copies the parent's `ref` or `link_uuid`; every leg names the parent in `parent_ref`; a parent
 *   without a name gets the wizard's, `split:<index>`. `row` is the parent as the patch left it (its cash already the
 *   trade's share); `legs` the patch's `split.legs`. It returns `{parent, legs}`: the parent comes back named. No name
 *   maker: the wizard's name is `split:<index>` (coordinator, 20/11).
 *
 * The rows are plain objects of the `MergedTx` shape. Names and descriptions are this file's own.
 */
import {describe, expect, it} from 'vitest';
import type {TransactionCreateItem} from '$lib/types';
import type {MergedTx} from './importTypes';
import {completeChargeNames, splitLegRows} from './importChargeNames';

// ---------------------------------------------------------------------------
// Rows
// ---------------------------------------------------------------------------

const FILE_A = 'file-statement-a';
const FILE_B = 'file-statement-b';

type Names = {ref?: string | null; parent_ref?: string | null; link_uuid?: string | null};

/** A merged row of `type` in `file`, with the names given (a name not given is absent from the transaction). */
function row(index: number, file: string, type: string, names: Names = {}, over: Partial<MergedTx> = {}): MergedTx {
    const charge = type === 'FEE' || type === 'TAX';
    const tx: Record<string, unknown> = {
        broker_id: 7,
        asset_id: 101,
        type,
        date: '2025-03-14',
        quantity: charge ? '0' : '10',
        cash: {code: 'EUR', amount: charge ? '-2.50' : '-1000.00'},
        description: `${type} ${file} #${index}`,
        tags: ['imported'],
        ...names,
    };
    return {index, sourceFileId: file, tx: tx as unknown as TransactionCreateItem, selected: true, duplicateStatus: 'unique', dupMatches: [], todos: [], ...over};
}

/** A fresh name maker: `n1`, `n2`, … — and the names it handed out. */
function names(prefix = 'n'): {newName: () => string; made: string[]} {
    const made: string[] = [];
    return {
        made,
        newName: () => {
            const name = `${prefix}${made.length + 1}`;
            made.push(name);
            return name;
        },
    };
}

function refOf(r: MergedTx): string | null {
    return ((r.tx as Names).ref ?? null) || null;
}

function parentRefOf(r: MergedTx): string | null {
    return ((r.tx as Names).parent_ref ?? null) || null;
}

function at(rows: readonly MergedTx[], index: number): MergedTx {
    const found = rows.find((candidate) => candidate.index === index);
    if (!found) throw new Error(`no row ${index} in the result`);
    return found;
}

function snapshot<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
}

/** Every name a set of rows carries, `ref` and `parent_ref` alike. */
function allNames(rows: readonly MergedTx[]): string[] {
    return rows.flatMap((r) => [refOf(r), parentRefOf(r)]).filter((name): name is string => name !== null);
}

// ---------------------------------------------------------------------------
// completeChargeNames
// ---------------------------------------------------------------------------

describe('completeChargeNames — the names of one hand-over', () => {
    it('gives every parent a fresh name, one per key, and its charges of the same file the same name', () => {
        const input = [row(0, FILE_A, 'BUY', {ref: 'r1'}), row(1, FILE_A, 'FEE', {parent_ref: 'r1'}), row(2, FILE_A, 'TAX', {parent_ref: 'r1'}), row(3, FILE_A, 'SELL', {ref: 'r2'}), row(4, FILE_A, 'FEE', {parent_ref: 'r2'})];
        const maker = names();
        const out = completeChargeNames(input, maker.newName);

        const buy = refOf(at(out, 0));
        const sell = refOf(at(out, 3));
        expect(buy, 'the BUY has a name').not.toBeNull();
        expect(sell, 'the SELL has a name').not.toBeNull();
        expect(buy, 'two parents, two names').not.toBe(sell);
        expect(maker.made, 'every name comes from newName').toEqual(expect.arrayContaining([buy, sell]));
        expect(parentRefOf(at(out, 1)), 'the FEE names the BUY by its new name').toBe(buy);
        expect(parentRefOf(at(out, 2)), 'the TAX names the BUY by its new name').toBe(buy);
        expect(parentRefOf(at(out, 4)), 'the FEE of the SELL names the SELL').toBe(sell);
        for (const charge of [1, 2, 4]) expect(refOf(at(out, charge)), `charge #${charge}: no name of its own (nothing names it)`).toBeNull();
        for (const parent of [0, 3]) expect(parentRefOf(at(out, parent)), `parent #${parent}: no parent`).toBeNull();
    });

    it('two files reusing r1 stay apart: each charge names the parent of its own file', () => {
        const input = [row(0, FILE_A, 'BUY', {ref: 'r1'}), row(1, FILE_A, 'FEE', {parent_ref: 'r1'}), row(2, FILE_B, 'BUY', {ref: 'r1'}), row(3, FILE_B, 'FEE', {parent_ref: 'r1'})];
        const out = completeChargeNames(input, names().newName);

        const buyA = refOf(at(out, 0));
        const buyB = refOf(at(out, 2));
        expect(buyA).not.toBeNull();
        expect(buyB).not.toBeNull();
        expect(buyA, 'one name per file + ref: the two BUYs are two keys').not.toBe(buyB);
        expect(parentRefOf(at(out, 1)), 'the FEE of file A names the BUY of file A').toBe(buyA);
        expect(parentRefOf(at(out, 3)), 'the FEE of file B names the BUY of file B').toBe(buyB);
    });

    it('a charge whose parent is not chosen loses parent_ref and stands alone', () => {
        // The BUY was unticked, or held back before the broker's opening: it is not in the hand-over.
        const out = completeChargeNames([row(1, FILE_A, 'FEE', {parent_ref: 'r1'})], names().newName);

        expect(parentRefOf(at(out, 1)), 'no parent to name').toBeNull();
        expect(refOf(at(out, 1)), 'and no name of its own').toBeNull();
    });

    it('a parent unticked as a database duplicate, its charge new: the charge arrives free', () => {
        const review = [row(0, FILE_A, 'BUY', {ref: 'r1'}, {selected: false, duplicateStatus: 'likely', dbDuplicateStatus: 'likely'}), row(1, FILE_A, 'FEE', {parent_ref: 'r1'})];
        const chosen = review.filter((r) => r.selected);
        expect(
            chosen.map((r) => r.index),
            'premise: only the FEE is chosen',
        ).toEqual([1]);

        const out = completeChargeNames(chosen, names().newName);

        expect(out).toHaveLength(1);
        expect(parentRefOf(at(out, 1)), 'the FEE never names a parent the batch does not hold (CHARGE_PARENT_REF_NOT_FOUND)').toBeNull();
    });

    it('a charge unticked as a database duplicate, its parent new: the parent loses its ref', () => {
        const review = [row(0, FILE_A, 'BUY', {ref: 'r1'}), row(1, FILE_A, 'FEE', {parent_ref: 'r1'}, {selected: false, duplicateStatus: 'likely', dbDuplicateStatus: 'likely'})];
        const out = completeChargeNames(
            review.filter((r) => r.selected),
            names().newName,
        );

        expect(out.map((r: MergedTx) => r.index)).toEqual([0]);
        expect(refOf(at(out, 0)), 'no chosen charge names the BUY: its name is not needed').toBeNull();
    });

    it('a parent with no charge at all among the chosen rows has no ref', () => {
        const out = completeChargeNames([row(0, FILE_A, 'BUY', {ref: 'r1'}), row(1, FILE_A, 'DEPOSIT')], names().newName);
        expect(refOf(at(out, 0))).toBeNull();
    });

    it('no name of the parse survives, whatever the mix', () => {
        const parseNames = ['r1', 'r2', 'r3', 'orphan'];
        const input = [row(0, FILE_A, 'BUY', {ref: 'r1'}), row(1, FILE_A, 'FEE', {parent_ref: 'r1'}), row(2, FILE_A, 'BUY', {ref: 'r2'}), row(3, FILE_B, 'FEE', {parent_ref: 'orphan'}), row(4, FILE_B, 'SELL', {ref: 'r3'}), row(5, FILE_B, 'TAX', {parent_ref: 'r3'})];
        const out = completeChargeNames(input, names('fresh-').newName);

        const carried = allNames(out);
        expect(carried.length, 'premise: the two linked parents and their charges carry names').toBeGreaterThan(0);
        expect(
            carried.filter((name) => parseNames.includes(name)),
            'a name of the parse never reaches the batch',
        ).toEqual([]);
    });

    it('rows without names are left as they are', () => {
        const plain = [row(0, FILE_A, 'DEPOSIT'), row(1, FILE_A, 'BUY'), row(2, FILE_A, 'FEE')];
        const named = [row(3, FILE_A, 'BUY', {ref: 'r1'}), row(4, FILE_A, 'FEE', {parent_ref: 'r1'})];
        const before = snapshot(plain);

        const out = completeChargeNames([...plain, ...named], names().newName);

        for (const original of before) expect(at(out, original.index), `row #${original.index} is untouched`).toEqual(original);
    });

    it('keeps the length and the order, and never mutates its input', () => {
        const input = [row(4, FILE_A, 'FEE', {parent_ref: 'r1'}), row(0, FILE_A, 'BUY', {ref: 'r1'}), row(9, FILE_B, 'DEPOSIT'), row(2, FILE_B, 'FEE', {parent_ref: 'gone'})];
        const before = snapshot(input);

        const out = completeChargeNames(input, names().newName);

        expect(
            out.map((r: MergedTx) => r.index),
            'same rows, same order',
        ).toEqual([4, 0, 9, 2]);
        expect(input, 'the input is untouched').toEqual(before);
    });

    it('a row with both a ref and a parent_ref: each name follows its own rule', () => {
        // The FEE names the BUY (renewed) and carries a ref no row names (dropped).
        const out = completeChargeNames([row(0, FILE_A, 'BUY', {ref: 'p'}), row(1, FILE_A, 'FEE', {ref: 'f', parent_ref: 'p'})], names().newName);

        const buy = refOf(at(out, 0));
        expect(buy).not.toBeNull();
        expect(parentRefOf(at(out, 1)), 'its parent_ref follows the parent').toBe(buy);
        expect(refOf(at(out, 1)), 'its own ref is named by nobody: dropped').toBeNull();

        // Its parent missing and its own name used by another row: the parent_ref goes, the ref is renewed and followed.
        const other = completeChargeNames([row(0, FILE_A, 'BUY', {ref: 'x', parent_ref: 'absent'}), row(1, FILE_A, 'FEE', {parent_ref: 'x'})], names().newName);
        const renewed = refOf(at(other, 0));
        expect(parentRefOf(at(other, 0)), 'the parent it named is not chosen').toBeNull();
        expect(renewed, 'named by the FEE: it keeps a name, a new one').not.toBeNull();
        expect(renewed).not.toBe('x');
        expect(parentRefOf(at(other, 1))).toBe(renewed);
    });

    it('is deterministic with respect to newName', () => {
        const input = [row(0, FILE_A, 'BUY', {ref: 'r1'}), row(1, FILE_A, 'FEE', {parent_ref: 'r1'}), row(2, FILE_B, 'BUY', {ref: 'r1'}), row(3, FILE_B, 'TAX', {parent_ref: 'r1'}), row(4, FILE_B, 'FEE', {parent_ref: 'r9'})];

        const first = completeChargeNames(input, names().newName);
        const second = completeChargeNames(input, names().newName);

        expect(second, 'the same input and the same name maker give the same result').toEqual(first);
    });

    it('cross-file keepers: the BUY kept from file 1, the FEE kept from file 2 — the FEE stays free, the BUY needs no name', () => {
        // The same statement loaded twice: a manual choice per duplicate group kept the BUY of file 1 and the FEE of
        // file 2 (contract §4.2). The FEE's parent in its own file is not chosen.
        const review = [row(0, FILE_A, 'BUY', {ref: 'r1'}), row(1, FILE_A, 'FEE', {parent_ref: 'r1'}, {selected: false, duplicateStatus: 'likely'}), row(2, FILE_B, 'BUY', {ref: 'r1'}, {selected: false, duplicateStatus: 'likely'}), row(3, FILE_B, 'FEE', {parent_ref: 'r1'})];
        const out = completeChargeNames(
            review.filter((r) => r.selected),
            names().newName,
        );

        expect(
            out.map((r: MergedTx) => r.index),
            'premise: the two keepers',
        ).toEqual([0, 3]);
        expect(parentRefOf(at(out, 3)), 'the FEE of file 2 never names the BUY of file 1').toBeNull();
        expect(refOf(at(out, 0)), 'no charge of file 1 is chosen: the BUY needs no name').toBeNull();
    });
});

// ---------------------------------------------------------------------------
// splitLegRows
// ---------------------------------------------------------------------------

/** The wizard's split legs: one per charge, at most this many (`MAX_SPLIT_LEGS`). */
const MAX_SPLIT_LEGS = 6;
/** The legs' index namespace (`SPLIT_LEG_INDEX_BASE`): leg k of row i is `BASE * (k + 1) + i`. */
const SPLIT_LEG_INDEX_BASE = 1_000_000;

/**
 * A BUY as `applyFixToRow` hands it to the legs: its cash already the trade's share (−1000.00 of the −1012.50 moved), a
 * duplicate verdict, a match and the split todo of its own, which no leg may inherit. `tx` overrides fields of its
 * transaction.
 */
function splitParent(named: Names = {}, tx: Record<string, unknown> = {}): MergedTx {
    const base = row(12, FILE_A, 'BUY', named, {
        duplicateStatus: 'possible',
        dupMatches: [{existing_tx_id: 5, similarity: 0.9} as never],
        todos: [{tx_index: 12, field: 'cash', severity: 'warning', reason_code: 'probe_trade_charges', message: 'probe', context: {split_hint: 'trade_charges'}} as never],
    });
    return {...base, tx: {...(base.tx as unknown as Record<string, unknown>), ...tx} as unknown as TransactionCreateItem};
}

const FEE_AND_TAX = [
    {type: 'FEE' as const, amount: '10.00', description: 'Split probe — fee'},
    {type: 'TAX' as const, amount: '2.50', description: 'Split probe — tax'},
];

describe('splitLegRows — today’s legs, field by field', () => {
    it('a FEE leg and a TAX leg: type, quantity 0, cash out in the row’s currency, description, tags, no cost, no todos, unique, the index scheme', () => {
        const parent = splitParent();
        const {legs} = splitLegRows(parent, FEE_AND_TAX);

        expect(legs, 'one leg per charge').toHaveLength(2);
        const [fee, tax] = legs;
        expect(fee.index, 'leg 0 of row 12').toBe(SPLIT_LEG_INDEX_BASE * 1 + 12);
        expect(tax.index, 'leg 1 of row 12').toBe(SPLIT_LEG_INDEX_BASE * 2 + 12);
        for (const [leg, spec] of [
            [fee, FEE_AND_TAX[0]],
            [tax, FEE_AND_TAX[1]],
        ] as const) {
            const tx = leg.tx as unknown as Record<string, unknown>;
            expect(tx.type, `${spec.type}: its type`).toBe(spec.type);
            expect(tx.quantity, `${spec.type}: quantity 0`).toBe('0');
            expect(tx.cash, `${spec.type}: money leaving, in the row's currency`).toEqual({code: 'EUR', amount: `-${spec.amount}`});
            expect(tx.description, `${spec.type}: the description given`).toBe(spec.description);
            expect(tx.tags, `${spec.type}: the row's tags plus split_leg`).toEqual(['imported', 'split_leg']);
            expect(tx.cost_basis_override, `${spec.type}: no cost`).toBeNull();
            expect(tx.broker_id, `${spec.type}: the row's broker`).toBe(7);
            expect(tx.asset_id, `${spec.type}: the row's asset`).toBe(101);
            expect(tx.date, `${spec.type}: the row's date`).toBe('2025-03-14');
            expect(leg.todos, `${spec.type}: no todo`).toEqual([]);
            expect(leg.duplicateStatus, `${spec.type}: unique`).toBe('unique');
            expect(leg.dupMatches, `${spec.type}: no match`).toEqual([]);
            expect(leg.sourceFileId, `${spec.type}: the row's file`).toBe(FILE_A);
            expect(leg.selected, `${spec.type}: selected as the row`).toBe(true);
        }
    });

    it('a row in another currency: the legs take it; a row without cash: EUR', () => {
        const usd = splitParent({}, {cash: {code: 'USD', amount: '-1000.00'}});
        expect(splitLegRows(usd, FEE_AND_TAX).legs.map((leg: MergedTx) => (leg.tx.cash as {code: string}).code)).toEqual(['USD', 'USD']);
        const none = splitParent({}, {cash: null});
        expect(splitLegRows(none, FEE_AND_TAX).legs.map((leg: MergedTx) => (leg.tx.cash as {code: string}).code)).toEqual(['EUR', 'EUR']);
    });

    it(`at most ${MAX_SPLIT_LEGS} legs, in the order given`, () => {
        const many = Array.from({length: MAX_SPLIT_LEGS + 2}, (_, k) => ({type: 'FEE' as const, amount: `${k + 1}.00`, description: `leg ${k}`}));
        const {legs} = splitLegRows(splitParent(), many);
        expect(legs.map((leg: MergedTx) => leg.index)).toEqual(Array.from({length: MAX_SPLIT_LEGS}, (_, k) => SPLIT_LEG_INDEX_BASE * (k + 1) + 12));
        expect(legs.map((leg: MergedTx) => leg.tx.description)).toEqual(many.slice(0, MAX_SPLIT_LEGS).map((leg) => leg.description));
    });

    it('never mutates the row', () => {
        const parent = splitParent({ref: 'r1', link_uuid: 'L-1'});
        const before = snapshot(parent);
        splitLegRows(parent, FEE_AND_TAX);
        expect(parent).toEqual(before);
    });
});

describe('splitLegRows — the legs are born linked to the trade (D10)', () => {
    it('no leg copies the parent’s ref or link_uuid; every leg names the parent by its ref', () => {
        const {parent, legs} = splitLegRows(splitParent({ref: 'r1', link_uuid: 'L-1'}), FEE_AND_TAX);

        expect(refOf(parent), 'a parent that has a name keeps it').toBe('r1');
        for (const leg of legs) {
            const tx = leg.tx as Names;
            expect(tx.ref ?? null, `${leg.tx.type}: no ref of the parent`).toBeNull();
            expect(tx.link_uuid ?? null, `${leg.tx.type}: no link_uuid of the parent`).toBeNull();
            expect(parentRefOf(leg), `${leg.tx.type}: names the parent`).toBe('r1');
        }
    });

    it('a parent without a name gets the wizard’s, split:<index>, and the legs name it', () => {
        const {parent, legs} = splitLegRows(splitParent(), FEE_AND_TAX);

        expect(refOf(parent)).toBe('split:12');
        expect(legs.map(parentRefOf)).toEqual(['split:12', 'split:12']);
    });

    it('the parent keeps every other field as it came', () => {
        const input = splitParent();
        const {parent} = splitLegRows(input, FEE_AND_TAX);
        const {ref: _ref, ...rest} = parent.tx as unknown as Record<string, unknown>;
        const {ref: _inputRef, ...inputRest} = input.tx as unknown as Record<string, unknown>;
        expect(rest).toEqual(inputRest);
        expect({...parent, tx: null}).toEqual({...input, tx: null});
    });

    it('then the hand-over renews the name: completeChargeNames over the parent and its legs links them under a fresh one', () => {
        const {parent, legs} = splitLegRows(splitParent(), FEE_AND_TAX);
        const out = completeChargeNames([parent, ...legs], names('handover-').newName);

        const name = refOf(at(out, 12));
        expect(name, 'the wizard’s split name never reaches the batch').not.toBe('split:12');
        expect(name).not.toBeNull();
        expect(out.filter((r: MergedTx) => r.index !== 12).map(parentRefOf)).toEqual([name, name]);
    });

    it('a leg ticked with its parent unticked stands alone at the hand-over', () => {
        const {legs} = splitLegRows(splitParent(), FEE_AND_TAX);
        const out = completeChargeNames(legs, names().newName);
        expect(out.map(parentRefOf)).toEqual([null, null]);
    });
});
