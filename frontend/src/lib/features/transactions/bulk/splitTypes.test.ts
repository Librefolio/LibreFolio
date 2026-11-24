/**
 * 66 C22d (FEE consultant, 21/11): the ONE computation of the type a split gives each half of a saved pair, shared by
 * the Bulk's Type cell, the half's Form (`postSplitTypeForForm`) and the mirror rows of «Link» (`bulkLinkSelection`).
 *
 *   - `SPLIT_TYPE_MAP` mirrors the backend's (`apply_splits`): [sender's type, receiver's type].
 *   - `splitHalfType(originalType, fields)`: the sender (index 0) when the sign is ≤ 0 — the quantity for TRANSFER, the
 *     cash amount for the others — the receiver (index 1) when > 0; `null` for a type the map does not split.
 *   - `postSplitType(op, splits)`: `op.fields.type` when the op is no edit in a queued split, or when the user picked a
 *     type by hand (`fields.type !== originalType`); otherwise `splitHalfType(originalType, op.fields) ?? op.fields.type`.
 *
 * Red until `splitTypes.ts` exists: the import below does not resolve.
 */
import {describe, expect, it} from 'vitest';
import {SPLIT_TYPE_MAP, postSplitType, splitHalfType} from './splitTypes';
import * as splitTypes from './splitTypes';
import type {PendingOp} from './txBulkTypes';
import type {TransactionTypeCode} from '$lib/features/transactions/transactionTypeStore';

type Split = {id_a: number; id_b: number; originalType: string};

/** A pending operation with only the fields these rules read; `txId` null makes it a create. */
function op(txId: number | null, type: string, cash: string | null, quantity = '0'): PendingOp {
    const fields = {
        broker_id: 77,
        asset_id: null,
        type: type as TransactionTypeCode,
        date: '2026-10-05',
        quantity,
        cash: cash === null ? null : {code: 'EUR', amount: cash},
        tags: [],
        description: '',
        asset_event_id: null,
        cost_basis_override: null,
        cost_basis_mode: null,
    };
    return (txId === null ? {op: 'create', tempId: 'new-1', createdSeq: 1, fields} : {op: 'edit', txId, markedDelete: false, tempId: `saved-${txId}`, createdSeq: 0, fields}) as PendingOp;
}

describe('66 C22d: SPLIT_TYPE_MAP', () => {
    it('mirrors the backend: TRANSFER → two ADJUSTMENT, CASH_TRANSFER and FX_CONVERSION → WITHDRAWAL then DEPOSIT, nothing else', () => {
        expect(SPLIT_TYPE_MAP).toEqual({
            TRANSFER: ['ADJUSTMENT', 'ADJUSTMENT'],
            CASH_TRANSFER: ['WITHDRAWAL', 'DEPOSIT'],
            FX_CONVERSION: ['WITHDRAWAL', 'DEPOSIT'],
        });
    });
});

describe('66 C22d: splitHalfType', () => {
    it.each([
        ['CASH_TRANSFER, cash −50 (the sender)', 'CASH_TRANSFER', {cash: {amount: '-50.000000'}}, 'WITHDRAWAL'],
        ['CASH_TRANSFER, cash +50 (the receiver)', 'CASH_TRANSFER', {cash: {amount: '50.000000'}}, 'DEPOSIT'],
        ['CASH_TRANSFER, cash 0 (≤ 0: the sender)', 'CASH_TRANSFER', {cash: {amount: '0'}}, 'WITHDRAWAL'],
        ['FX_CONVERSION, cash −10', 'FX_CONVERSION', {cash: {amount: '-10.000000'}}, 'WITHDRAWAL'],
        ['FX_CONVERSION, cash +10', 'FX_CONVERSION', {cash: {amount: '10.000000'}}, 'DEPOSIT'],
        ['CASH_TRANSFER, quantity −5 but cash +50 (the cash decides)', 'CASH_TRANSFER', {quantity: '-5.000000', cash: {amount: '50.000000'}}, 'DEPOSIT'],
        ['CASH_TRANSFER, quantity +5 but cash −50 (the cash decides)', 'CASH_TRANSFER', {quantity: '5.000000', cash: {amount: '-50.000000'}}, 'WITHDRAWAL'],
        ['TRANSFER, quantity −5', 'TRANSFER', {quantity: '-5.000000', cash: null}, 'ADJUSTMENT'],
        ['TRANSFER, quantity +5', 'TRANSFER', {quantity: '5.000000', cash: null}, 'ADJUSTMENT'],
    ] as const)('%s → %s', (_label, original, fields, expected) => {
        expect(splitHalfType(original, fields)).toBe(expected);
    });

    it.each(['DEPOSIT', 'WITHDRAWAL', 'BUY', 'FEE', 'ADJUSTMENT', ''])('a type the map does not split (%j) → null', (type) => {
        expect(splitHalfType(type, {quantity: '-5.000000', cash: {amount: '-50.000000'}})).toBeNull();
    });
});

describe('66 C22d: postSplitType', () => {
    const PAIR: Split = {id_a: 92_522, id_b: 92_521, originalType: 'CASH_TRANSFER'};
    const TRANSFER_PAIR: Split = {id_a: 92_551, id_b: 92_552, originalType: 'TRANSFER'};

    it('a create keeps its own type, whatever the splits', () => {
        expect(postSplitType(op(null, 'CASH_TRANSFER', '-50.000000'), [PAIR])).toBe('CASH_TRANSFER');
    });

    it('an edit in no queued split keeps its own type', () => {
        expect(postSplitType(op(91_000, 'CASH_TRANSFER', '-50.000000'), [PAIR])).toBe('CASH_TRANSFER');
        expect(postSplitType(op(PAIR.id_a, 'CASH_TRANSFER', '-50.000000'), [])).toBe('CASH_TRANSFER');
    });

    it('an untouched half named as id_a (the sender, cash −50) → WITHDRAWAL', () => {
        expect(postSplitType(op(PAIR.id_a, 'CASH_TRANSFER', '-50.000000'), [PAIR])).toBe('WITHDRAWAL');
    });

    it('an untouched half named as id_b (the receiver, cash +50) → DEPOSIT', () => {
        expect(postSplitType(op(PAIR.id_b, 'CASH_TRANSFER', '50.000000'), [PAIR])).toBe('DEPOSIT');
    });

    it('the side is the cash sign, not the place in the split: the receiver named as id_a → DEPOSIT', () => {
        expect(postSplitType(op(PAIR.id_a, 'CASH_TRANSFER', '50.000000'), [PAIR])).toBe('DEPOSIT');
    });

    it('an untouched half of a split TRANSFER → ADJUSTMENT', () => {
        expect(postSplitType(op(TRANSFER_PAIR.id_a, 'TRANSFER', null, '-5.000000'), [TRANSFER_PAIR])).toBe('ADJUSTMENT');
        expect(postSplitType(op(TRANSFER_PAIR.id_b, 'TRANSFER', null, '5.000000'), [TRANSFER_PAIR])).toBe('ADJUSTMENT');
    });

    it('the half found among several queued splits', () => {
        expect(postSplitType(op(PAIR.id_b, 'CASH_TRANSFER', '50.000000'), [TRANSFER_PAIR, PAIR])).toBe('DEPOSIT');
    });

    // The user's choice wins over the sign: the receiver (cash +50) the user turned WITHDRAWAL by hand stays WITHDRAWAL,
    // where the sign alone would say DEPOSIT. This is the Bulk's own state after the Form turns the DEPOSIT half into a
    // WITHDRAWAL: the Form pushes −50, the editor holds a negative-rule cash as its magnitude, +50 (W-B65,
    // `applyFormPayload`). TransactionBulkModal.test.ts «C22d: the DEPOSIT half turned WITHDRAWAL» drives it end to end.
    it('a half whose type the user picked by hand keeps it, against the sign: receiver (+50) turned WITHDRAWAL → WITHDRAWAL', () => {
        expect(postSplitType(op(PAIR.id_b, 'WITHDRAWAL', '50.000000'), [PAIR])).toBe('WITHDRAWAL');
    });

    it('a half whose type the user picked by hand keeps it: sender (−50) turned DEPOSIT → DEPOSIT', () => {
        expect(postSplitType(op(PAIR.id_a, 'DEPOSIT', '-50.000000'), [PAIR])).toBe('DEPOSIT');
    });

    it('a split whose original type the map does not split falls back on the op’s own type', () => {
        expect(postSplitType(op(PAIR.id_a, 'DEPOSIT', '-50.000000'), [{...PAIR, originalType: 'DEPOSIT'}])).toBe('DEPOSIT');
    });
});

/**
 * 66 C22e (FEE consultant + coordinator, 21/11): the type an update of a split half carries. `resolveOps` strips `type`
 * from the update of a split-queued row, because the backend's split assigns it (`apply_splits`, read on the SAVED side,
 * `pair_sides`). That is right while the Bulk shows the type the split gives, and wrong the moment the user picks the
 * other one in the half's Form: the DEPOSIT half turned WITHDRAWAL is sent `{id, cash: −50}` with no type, the split
 * makes it a DEPOSIT, rule 11 refuses −50 on a DEPOSIT and the whole batch fails.
 *
 *   `splitTypeToSend(op, splits, saved)`:
 *     - `null` when `op` is no edit, `saved` is null, or `op` is in no queued split;
 *     - otherwise `serverType = splitHalfType(split.originalType, saved)` — the SAVED side, as the backend reads it —
 *       and `finalType = postSplitType(op, splits)`; `finalType` when they differ, else `null`.
 *
 * The draft holds a negative-rule cash as its MAGNITUDE (W-B65): a WITHDRAWAL half holds +50 where the server holds −50.
 * The rows where the draft's sign and the saved sign disagree are the ones that tell «reads the saved side» from
 * «reads the draft».
 *
 * Red until `splitTypeToSend` is exported: every call below throws «not a function».
 */
describe('66 C22e: splitTypeToSend', () => {
    // The C22d pair: 92 522 the sender (saved −50, on 88), 92 521 the receiver (saved +50, on 77).
    const PAIR: Split = {id_a: 92_522, id_b: 92_521, originalType: 'CASH_TRANSFER'};
    const SENDER = {quantity: '0.000000', cash: {amount: '-50.000000'}};
    const RECEIVER = {quantity: '0.000000', cash: {amount: '50.000000'}};
    const TRANSFER_PAIR: Split = {id_a: 92_551, id_b: 92_552, originalType: 'TRANSFER'};
    const FX_PAIR: Split = {id_a: 92_561, id_b: 92_562, originalType: 'FX_CONVERSION'};
    /** The half's saved side, as the store holds it (signed). */
    type SavedSide = {quantity?: string | null; cash?: {amount: string} | null};

    /** The export, read at call time: until it exists each call fails with «not a function», never at import. */
    function send(...args: unknown[]): string | null {
        const fn = (splitTypes as unknown as Record<string, unknown>).splitTypeToSend as ((...a: unknown[]) => string | null) | undefined;
        if (typeof fn !== 'function') throw new TypeError('splitTypeToSend is not exported by splitTypes.ts');
        return fn(...args);
    }

    const CASES: ReadonlyArray<readonly [string, PendingOp, readonly Split[], SavedSide | null, string | null]> = [
        // -- nothing to send: not a split half, or nothing saved to read --
        ['a create (no saved row)', op(null, 'WITHDRAWAL', '50.000000'), [PAIR], RECEIVER, null],
        ['an edit with no saved row', op(PAIR.id_b, 'WITHDRAWAL', '50.000000'), [PAIR], null, null],
        ['an edit in no queued split', op(91_000, 'WITHDRAWAL', '50.000000'), [PAIR], RECEIVER, null],
        ['a half, but no split queued', op(PAIR.id_b, 'WITHDRAWAL', '50.000000'), [], RECEIVER, null],
        // -- untouched halves: `fields.type` still the pair's; the Bulk shows what the split gives --
        ['the untouched receiver (CASH_TRANSFER +50, saved +50)', op(PAIR.id_b, 'CASH_TRANSFER', '50.000000'), [PAIR], RECEIVER, null],
        ['the untouched sender (CASH_TRANSFER −50, saved −50)', op(PAIR.id_a, 'CASH_TRANSFER', '-50.000000'), [PAIR], SENDER, null],
        // -- a hand type equal to the server's: nothing to send, even with the draft holding the magnitude --
        // Discriminating: the draft's +50 alone would say DEPOSIT; the saved −50 says WITHDRAWAL, the same as the user's.
        ['the sender handed WITHDRAWAL (draft +50 magnitude, saved −50) — C22d’s note edit', op(PAIR.id_a, 'WITHDRAWAL', '50.000000'), [PAIR], SENDER, null],
        ['the receiver handed DEPOSIT (draft +50, saved +50)', op(PAIR.id_b, 'DEPOSIT', '50.000000'), [PAIR], RECEIVER, null],
        // -- a hand type opposite to the server's: send it --
        ['the receiver swapped to WITHDRAWAL (draft +50 magnitude, saved +50) — the defect', op(PAIR.id_b, 'WITHDRAWAL', '50.000000'), [PAIR], RECEIVER, 'WITHDRAWAL'],
        // Discriminating: a draft −50 alone would say WITHDRAWAL, equal to the user's; the saved +50 says DEPOSIT.
        ['the receiver swapped to WITHDRAWAL, the draft holding −50 (saved +50 decides)', op(PAIR.id_b, 'WITHDRAWAL', '-50.000000'), [PAIR], RECEIVER, 'WITHDRAWAL'],
        // Discriminating: the draft's +50 alone would say DEPOSIT, equal to the user's; the saved −50 says WITHDRAWAL.
        ['the sender swapped to DEPOSIT (draft +50, saved −50)', op(PAIR.id_a, 'DEPOSIT', '50.000000'), [PAIR], SENDER, 'DEPOSIT'],
        // -- a half whose type is still the pair's but whose draft sign is flipped (not reachable in the Bulk today:
        //    its grid has no inline cell); the Bulk would show the flipped side, the server would give the saved one --
        ['the receiver still CASH_TRANSFER, its draft at −50 (saved +50)', op(PAIR.id_b, 'CASH_TRANSFER', '-50.000000'), [PAIR], RECEIVER, 'WITHDRAWAL'],
        // -- the half found among several splits, as id_b --
        ['the receiver swapped, found among two queued splits', op(PAIR.id_b, 'WITHDRAWAL', '50.000000'), [TRANSFER_PAIR, PAIR], RECEIVER, 'WITHDRAWAL'],
        // -- a split TRANSFER: both halves ADJUSTMENT, whatever the side --
        ['a TRANSFER sender, untouched (quantity −5, saved −5)', op(TRANSFER_PAIR.id_a, 'TRANSFER', null, '-5.000000'), [TRANSFER_PAIR], {quantity: '-5.000000', cash: null}, null],
        ['a TRANSFER receiver, untouched (quantity +5, saved +5)', op(TRANSFER_PAIR.id_b, 'TRANSFER', null, '5.000000'), [TRANSFER_PAIR], {quantity: '5.000000', cash: null}, null],
        ['a TRANSFER sender handed ADJUSTMENT (quantity −5, saved −5)', op(TRANSFER_PAIR.id_a, 'ADJUSTMENT', null, '-5.000000'), [TRANSFER_PAIR], {quantity: '-5.000000', cash: null}, null],
        // -- FX_CONVERSION: the same sides as a CASH_TRANSFER --
        ['an FX_CONVERSION sender, untouched (−10, saved −10)', op(FX_PAIR.id_a, 'FX_CONVERSION', '-10.000000'), [FX_PAIR], {cash: {amount: '-10.000000'}}, null],
        ['an FX_CONVERSION receiver, untouched (+10, saved +10)', op(FX_PAIR.id_b, 'FX_CONVERSION', '10.000000'), [FX_PAIR], {cash: {amount: '10.000000'}}, null],
        ['an FX_CONVERSION sender swapped to DEPOSIT (draft +10, saved −10)', op(FX_PAIR.id_a, 'DEPOSIT', '10.000000'), [FX_PAIR], {cash: {amount: '-10.000000'}}, 'DEPOSIT'],
        ['an FX_CONVERSION receiver swapped to WITHDRAWAL (draft +10 magnitude, saved +10)', op(FX_PAIR.id_b, 'WITHDRAWAL', '10.000000'), [FX_PAIR], {cash: {amount: '10.000000'}}, 'WITHDRAWAL'],
    ];

    it.each(CASES.map(([label, pending, splits, saved, expected]) => [`${label} → ${expected}`, pending, splits, saved, expected] as const))('%s', (_title, pending, splits, saved, expected) => {
        expect(send(pending, splits, saved)).toBe(expected);
    });

    it('both halves swapped: each sends its own type', () => {
        const splits = [PAIR];
        expect(send(op(PAIR.id_a, 'DEPOSIT', '50.000000'), splits, SENDER), 'the sender swapped to DEPOSIT').toBe('DEPOSIT');
        expect(send(op(PAIR.id_b, 'WITHDRAWAL', '50.000000'), splits, RECEIVER), 'the receiver swapped to WITHDRAWAL').toBe('WITHDRAWAL');
    });

    it('does not mutate its arguments', () => {
        const pending = op(PAIR.id_b, 'WITHDRAWAL', '50.000000');
        const splits = [{...PAIR}, {...TRANSFER_PAIR}];
        const saved = {quantity: '0.000000', cash: {amount: '50.000000'}};
        const before = structuredClone({pending, splits, saved});

        expect(send(pending, splits, saved), 'premise: the swapped receiver sends WITHDRAWAL').toBe('WITHDRAWAL');

        expect({pending, splits, saved}).toEqual(before);
    });
});
