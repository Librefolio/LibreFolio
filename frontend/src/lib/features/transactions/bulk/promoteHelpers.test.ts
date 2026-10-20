/**
 * Unit tests for cashAmountsCancel — pure promote helper.
 *
 * This function guards CASH_TRANSFER promote suggestions:
 * only pairs where amounts are exactly opposite (sum = 0)
 * should be promoted, preventing false positives from unrelated
 * transactions with the same type/date but different amounts.
 *
 * The suite is split in two halves on purpose. The first half feeds SIGNED amounts, the
 * representation an import-pool row carries. The second half feeds NORMALISED amounts, the
 * representation `fieldsFromTx` produces for a row read from the database — where a
 * WITHDRAWAL of -11 is stored as "11" because the form shows a magnitude and the type
 * carries the sign. Both halves must give the same answers: that equivalence is the whole
 * point of routing the comparison through `signedCashAmount`, and it is what was broken
 * (edit+edit pairs could never be promoted, because +11 + +11 is never 0).
 */
import {describe, expect, it} from 'vitest';
import {cashAmountsCancel, mergeStrings, mergeTagSets, promotePairOrder, type CashCancelable, type PromotePairOrder} from './promoteHelpers';
import * as promoteHelpers from './promoteHelpers';
import type {TypeRule} from '$lib/features/transactions/transactionTypeStore';

/** Rule stub — only `cashSign` is read by the helper under test. */
function rule(cashSign: string): TypeRule {
    return {cashSign} as unknown as TypeRule;
}

/** Type-rule resolver mirroring the real one for the three types used here. */
const resolve = (type: string): TypeRule => {
    if (type === 'CASH_OUT') return rule('negative');
    if (type === 'CASH_IN') return rule('positive');
    return rule('free'); // ADJUSTMENT / TRANSFER legs: the stored sign is meaningful
};

function op(amount: string | null, type = 'FREE'): CashCancelable {
    return {fields: {type, cash: amount !== null ? {code: 'EUR', amount} : null}};
}

describe('cashAmountsCancel', () => {
    // --- true cases: exact cancellation ---------------------------------

    it('returns true for exact opposite integer amounts', () => {
        expect(cashAmountsCancel(op('-100'), op('100'), resolve)).toBe(true);
    });

    it('returns true for exact opposite decimal amounts', () => {
        expect(cashAmountsCancel(op('-360.87'), op('360.87'), resolve)).toBe(true);
    });

    it('returns true regardless of argument order', () => {
        expect(cashAmountsCancel(op('360.87'), op('-360.87'), resolve)).toBe(true);
    });

    it('handles very small amounts that cancel exactly', () => {
        expect(cashAmountsCancel(op('-0.01'), op('0.01'), resolve)).toBe(true);
    });

    // --- false cases: different amounts ---------------------------------

    it('returns false when amounts are clearly different', () => {
        // The real bug: CASH_OUT -360.87 matched with CASH_IN +1445.00
        expect(cashAmountsCancel(op('-360.87'), op('1445.00'), resolve)).toBe(false);
    });

    it('returns false for same sign (no cancellation)', () => {
        expect(cashAmountsCancel(op('100'), op('100'), resolve)).toBe(false);
    });

    it('returns false when amounts differ by 1 cent', () => {
        expect(cashAmountsCancel(op('-100.00'), op('100.01'), resolve)).toBe(false);
    });

    // --- false cases: missing cash field --------------------------------

    it('returns false when first op has cash=null', () => {
        expect(cashAmountsCancel(op(null), op('100'), resolve)).toBe(false);
    });

    it('returns false when second op has cash=null', () => {
        expect(cashAmountsCancel(op('-100'), op(null), resolve)).toBe(false);
    });

    it('returns false when both ops have cash=null', () => {
        expect(cashAmountsCancel(op(null), op(null), resolve)).toBe(false);
    });

    // --- edge: zero amounts ---------------------------------------------

    it('returns false when both amounts are zero (maxAbs=0 guard)', () => {
        expect(cashAmountsCancel(op('0'), op('0'), resolve)).toBe(false);
    });

    it('returns false when one amount is zero (non-cancelling)', () => {
        expect(cashAmountsCancel(op('0'), op('100'), resolve)).toBe(false);
    });
});

describe('cashAmountsCancel — representation independence', () => {
    // A row read from the DB is normalised to a magnitude by fieldsFromTx: a WITHDRAWAL of
    // -11 becomes "11". Every case below is the same money as the signed cases above.

    it('cancels a normalised (DB) pair — the edit+edit case that never worked', () => {
        const withdrawal = op('11', 'CASH_OUT'); // stored as a magnitude
        const deposit = op('11', 'CASH_IN');
        expect(cashAmountsCancel(withdrawal, deposit, resolve)).toBe(true);
    });

    it('cancels a mixed pair — one row from the pool, one from the DB', () => {
        const fromPool = op('-11', 'CASH_OUT'); // already signed
        const fromDb = op('11', 'CASH_IN'); // normalised
        expect(cashAmountsCancel(fromPool, fromDb, resolve)).toBe(true);
    });

    it('is idempotent: the stored sign never changes the answer for a signed type', () => {
        // Same money, four ways of writing it. A rule that flipped instead of coercing
        // ("multiply by -1" rather than "-Math.abs") would give different answers here.
        const expected = true;
        expect(cashAmountsCancel(op('-11', 'CASH_OUT'), op('11', 'CASH_IN'), resolve)).toBe(expected);
        expect(cashAmountsCancel(op('11', 'CASH_OUT'), op('11', 'CASH_IN'), resolve)).toBe(expected);
        expect(cashAmountsCancel(op('-11', 'CASH_OUT'), op('-11', 'CASH_IN'), resolve)).toBe(expected);
        expect(cashAmountsCancel(op('11', 'CASH_OUT'), op('-11', 'CASH_IN'), resolve)).toBe(expected);
    });

    it('still rejects a normalised pair with different amounts', () => {
        expect(cashAmountsCancel(op('11', 'CASH_OUT'), op('12', 'CASH_IN'), resolve)).toBe(false);
    });

    it('leaves free-sign types untouched, where the stored sign is the information', () => {
        // Two ADJUSTMENTs of +50 do not cancel; +50 and -50 do. Coercing either one would
        // destroy the only thing distinguishing them.
        expect(cashAmountsCancel(op('50'), op('50'), resolve)).toBe(false);
        expect(cashAmountsCancel(op('50'), op('-50'), resolve)).toBe(true);
    });

    it('returns false when an amount is not a number', () => {
        expect(cashAmountsCancel(op('abc'), op('100'), resolve)).toBe(false);
    });
});

describe('cashAmountsCancel — exact at large magnitudes', () => {
    // The backend promotes two cash rows to a CASH_TRANSFER only when their amounts are exactly
    // opposite: it compares decimals, and refuses anything else with `noPromoteRule`. A float
    // comparison with a relative tolerance of 1e-9 stops seeing a cent at about 10 million
    // (0.01 / 10 000 000 = 1e-9), so the editor would propose a pair the save then refuses.
    // A cent is a cent at any magnitude: the answer must be exact, as in `assetQuantitiesCancel`.
    // The true cases are the other half of the contract: exactness must not lose a pair that
    // differs only in how it is written.

    // --- true cases: exactly opposite -----------------------------------

    it('returns true for -10000000.00 vs 10000000.00 (exact at 10 million)', () => {
        expect(cashAmountsCancel(op('-10000000.00'), op('10000000.00'), resolve)).toBe(true);
    });

    it('returns true for -10000000 vs 10000000.000 (representation-only zeros)', () => {
        expect(cashAmountsCancel(op('-10000000'), op('10000000.000'), resolve)).toBe(true);
    });

    it('returns true for -1234567890123.45 vs 1234567890123.45 (exact at 1.2 trillion)', () => {
        expect(cashAmountsCancel(op('-1234567890123.45'), op('1234567890123.45'), resolve)).toBe(true);
    });

    it('returns true for a normalised (DB) CASH_OUT 10000000.00 and CASH_IN 10000000.00 (exact at 10 million)', () => {
        const withdrawal = op('10000000.00', 'CASH_OUT'); // stored as a magnitude
        const deposit = op('10000000.00', 'CASH_IN');
        expect(cashAmountsCancel(withdrawal, deposit, resolve)).toBe(true);
    });

    // --- false cases: one cent apart ------------------------------------

    it('returns false for -10000000.00 vs 10000000.01 (one cent at 10 million)', () => {
        expect(cashAmountsCancel(op('-10000000.00'), op('10000000.01'), resolve)).toBe(false);
    });

    it('returns false for -123456789.12 vs 123456789.13 (one cent at 123 million)', () => {
        expect(cashAmountsCancel(op('-123456789.12'), op('123456789.13'), resolve)).toBe(false);
    });

    it('returns false for -1234567890123.45 vs 1234567890123.46 (one cent at 1.2 trillion)', () => {
        // Here a double steps by 2^-12 (about 0.00024): as Numbers the gap reads 0.010009765625,
        // not 0.01. Only a decimal comparison sees the cent as it was written.
        expect(cashAmountsCancel(op('-1234567890123.45'), op('1234567890123.46'), resolve)).toBe(false);
    });

    it('returns false for a normalised (DB) CASH_OUT 10000000.00 and CASH_IN 10000000.01 (one cent at 10 million)', () => {
        const withdrawal = op('10000000.00', 'CASH_OUT'); // stored as a magnitude
        const deposit = op('10000000.01', 'CASH_IN');
        expect(cashAmountsCancel(withdrawal, deposit, resolve)).toBe(false);
    });
});

/**
 * promotePairOrder (J-66) — which row of a suggested pair pays. One rule, five readers: the banner lists that row first,
 * an exchange reads its implied rate and asks the market rate from it to the other row, «Merge all → left» names it,
 * and the merge dialog of a single «Merge» lists it first.
 *
 * The bulk editor holds the cash of a type whose rule demands a negative value as its magnitude: a WITHDRAWAL, whether
 * saved (`fieldsFromTx`), imported (`txCreateItemToPendingOp`) or applied from the form (W-B65, `magnitudeForRule`),
 * holds 1000, not -1000, while the legs of a split pair keep their signed cash (`handleSplitRow`). Read as stored, a
 * withdrawal of 1000 EUR beside a deposit of 1100 USD has no paying row and, depending on the order, the banner listed
 * the deposit first (Scenario A2) or its rate read USD → EUR @ 0.9091 instead of 1.1000 (tx-fx-implied-rate.spec.ts,
 * Scenario A). So each row's cash first takes its type's sign (`buildSignedCash`, as `cashAmountsCancel` does), and the
 * sign is read from the digits: a row without cash, or whose amount is no plain decimal, never pays.
 *
 * Reds today: a withdrawal held as its magnitude, a deposit carrying a minus, an amount in exponent notation. Guards,
 * green before and after the cure: signed rows (a split pair's legs), free-sign pair legs, a row without cash,
 * two deposits.
 */
describe('promotePairOrder — the paying row first, signed by its type (J-66)', () => {
    /** The cash sign of each real type used here, as the backend declares it (`schemas/transactions/type_metadata.py`).
     *  `nonzero`, the rule of the pair legs, is a free-sign rule: their stored sign is the information. */
    const CASH_SIGN: Record<string, string> = {WITHDRAWAL: 'negative', DEPOSIT: 'positive', FX_CONVERSION: 'nonzero', CASH_TRANSFER: 'nonzero'};

    /** Type-rule resolver for those types. A code it does not know is a slip in this test, never a free-sign type. */
    const ruleOf = (type: string): TypeRule => {
        const cashSign = CASH_SIGN[type];
        if (cashSign === undefined) throw new Error(`no cash sign stubbed for type ${type}`);
        return rule(cashSign);
    };

    /** A row of the bulk editor, its amount as the editor holds it; `null` for a row without cash. */
    const txRow = (type: string, amount: string | null, code = 'EUR'): CashCancelable => ({fields: {type, cash: amount !== null ? {code, amount} : null}});

    /** The whole answer — `swapped`, and `from` and `to` as the very rows passed in — under a label naming the call. */
    const expectOrder = (order: PromotePairOrder<CashCancelable>, expected: PromotePairOrder<CashCancelable>, label = 'promotePairOrder(a, b)') => {
        expect(order.swapped, `${label} — swapped: the banner lists b first`).toBe(expected.swapped);
        expect(order.from, `${label} — from: the row the money leaves`).toBe(expected.from);
        expect(order.to, `${label} — to: the other row`).toBe(expected.to);
    };

    // --- reds: a WITHDRAWAL held as its magnitude (W-B65) ---------------

    it('a WITHDRAWAL held as its magnitude still pays: from the withdrawal to the DEPOSIT, and nothing swaps', () => {
        const withdrawal = txRow('WITHDRAWAL', '1000', 'EUR'); // -1000 EUR, held as its magnitude
        const deposit = txRow('DEPOSIT', '1100', 'USD');

        expectOrder(promotePairOrder(withdrawal, deposit, ruleOf), {swapped: false, from: withdrawal, to: deposit});
    });

    it('given second, a WITHDRAWAL held as its magnitude still pays: the banner swaps it first', () => {
        const withdrawal = txRow('WITHDRAWAL', '1000', 'EUR'); // -1000 EUR, held as its magnitude
        const deposit = txRow('DEPOSIT', '1100', 'USD');

        expectOrder(promotePairOrder(deposit, withdrawal, ruleOf), {swapped: true, from: withdrawal, to: deposit});
    });

    it('a WITHDRAWAL of one satoshi held as its magnitude, 0.00000001, still pays: the smallest amount takes its type’s sign too', () => {
        const withdrawal = txRow('WITHDRAWAL', '0.00000001', 'EUR');
        const deposit = txRow('DEPOSIT', '1100', 'USD');

        expectOrder(promotePairOrder(withdrawal, deposit, ruleOf), {swapped: false, from: withdrawal, to: deposit});
    });

    it('a WITHDRAWAL held as its magnitude pays beside a row without cash, which never does', () => {
        const withdrawal = txRow('WITHDRAWAL', '1000', 'EUR');
        const noCash = txRow('DEPOSIT', null); // its amount not entered yet

        expectOrder(promotePairOrder(withdrawal, noCash, ruleOf), {swapped: false, from: withdrawal, to: noCash});
    });

    // --- guards: green today, and after the cure ------------------------

    it('rows already signed, as a split pair’s legs keep them, give the same answers in both orders: the representation never changes the order', () => {
        const withdrawal = txRow('WITHDRAWAL', '-1000', 'EUR'); // signed, as a split pair's leg keeps it
        const deposit = txRow('DEPOSIT', '1100', 'USD');

        expectOrder(promotePairOrder(withdrawal, deposit, ruleOf), {swapped: false, from: withdrawal, to: deposit}, 'the withdrawal first');
        expectOrder(promotePairOrder(deposit, withdrawal, ruleOf), {swapped: true, from: withdrawal, to: deposit}, 'the deposit first');
    });

    it('a free-sign pair leg keeps its stored sign: the negative leg pays, and the pair swaps only when that leg comes second', () => {
        const legs: Array<[CashCancelable, CashCancelable]> = [
            [txRow('FX_CONVERSION', '-1000', 'EUR'), txRow('FX_CONVERSION', '1100', 'USD')],
            [txRow('CASH_TRANSFER', '-1000', 'EUR'), txRow('CASH_TRANSFER', '1000', 'EUR')],
        ];
        for (const [out, into] of legs) {
            expectOrder(promotePairOrder(out, into, ruleOf), {swapped: false, from: out, to: into}, `${out.fields.type}, the negative leg first`);
            expectOrder(promotePairOrder(into, out, ruleOf), {swapped: true, from: out, to: into}, `${out.fields.type}, the negative leg second`);
        }
    });

    it('a row without cash never pays, whatever its type: given first beside a WITHDRAWAL held as its magnitude, the withdrawal pays and nothing swaps', () => {
        const withdrawal = txRow('WITHDRAWAL', '1000', 'EUR');
        for (const type of ['DEPOSIT', 'WITHDRAWAL']) {
            const noCash = txRow(type, null); // a WITHDRAWAL too: its rule alone pays nothing
            expectOrder(promotePairOrder(noCash, withdrawal, ruleOf), {swapped: false, from: withdrawal, to: noCash}, `a ${type} without cash, first`);
        }
    });

    it('when neither row pays, as two DEPOSITs, from is b and nothing swaps: the documented fallback', () => {
        const first = txRow('DEPOSIT', '1000', 'EUR');
        const second = txRow('DEPOSIT', '1100', 'USD');

        expectOrder(promotePairOrder(first, second, ruleOf), {swapped: false, from: second, to: first});
    });

    // --- reds: the positive rule binds, the sign read from the digits ---

    it('a DEPOSIT whose amount carries a minus still receives, as the save will send it: its positive rule decides, so the WITHDRAWAL pays and the pair swaps', () => {
        const deposit = txRow('DEPOSIT', '-1100', 'USD'); // saved as 1100: `buildCreatePayload` applies the positive rule
        const withdrawal = txRow('WITHDRAWAL', '1000', 'EUR');

        expectOrder(promotePairOrder(deposit, withdrawal, ruleOf), {swapped: true, from: withdrawal, to: deposit});
    });

    it('an amount that is no plain decimal never pays nor swaps: -1e3 is not read through a double as -1000, and the pair reads as one where nothing pays', () => {
        const exponent = txRow('FX_CONVERSION', '-1e3', 'EUR');
        const into = txRow('FX_CONVERSION', '1100', 'USD');

        // Nothing pays, so `from` is b both ways (the fallback), and no swap.
        expectOrder(promotePairOrder(exponent, into, ruleOf), {swapped: false, from: into, to: exponent}, 'the exponent leg first');
        expectOrder(promotePairOrder(into, exponent, ruleOf), {swapped: false, from: exponent, to: into}, 'the exponent leg second');
    });
});

/**
 * mergeStrings / mergeTagSets — pure field-merge helpers used by PromoteMergeModal to pre-fill
 * the resolved description and tags when two rows are merged into a promoted pair.
 */
describe('mergeStrings', () => {
    it('returns the other side when one is empty', () => {
        expect(mergeStrings('', 'B')).toBe('B');
        expect(mergeStrings('A', '')).toBe('A');
    });

    it('returns both empty as empty (first-branch short-circuit)', () => {
        expect(mergeStrings('', '')).toBe('');
    });

    it('collapses identical sides to a single copy', () => {
        expect(mergeStrings('same', 'same')).toBe('same');
    });

    it('stacks two distinct values on separate lines', () => {
        expect(mergeStrings('first', 'second')).toBe('first\nsecond');
    });
});

describe('mergeTagSets', () => {
    it('unions two lists and de-duplicates, preserving first-seen order', () => {
        expect(mergeTagSets(['a', 'b'], ['b', 'c'])).toEqual(['a', 'b', 'c']);
    });

    it('treats a nullish first list as empty', () => {
        expect(mergeTagSets(null as unknown as string[], ['x'])).toEqual(['x']);
    });

    it('treats a nullish second list as empty', () => {
        expect(mergeTagSets(['x'], undefined as unknown as string[])).toEqual(['x']);
    });

    it('returns [] when both are nullish', () => {
        expect(mergeTagSets(null as unknown as string[], null as unknown as string[])).toEqual([]);
    });
});

/**
 * W-B70 (decision D-W70-4 a of the coordinator, 17/10) — «Merge all» never writes notes past the limit.
 *
 * A transaction's notes hold 500 characters (`max_length=500` on the backend, counted by Python's `len()`, in code
 * points). «Merge all» (`mergeAllSuggestions` in TransactionBulkModal.svelte) settles every suggested pair with one
 * strategy, inline: nothing to resolve when the two rows have the same notes and the same tags; else the left row's
 * notes and tags, the right row's, or by default both combined — `mergeStrings` of the notes, `mergeTagSets` of the
 * tags. Combined, two notes of 250 characters become 501, written into both rows; the save is then refused on the
 * promote (`string_too_long`) and nothing is saved. The decision: such a pair is left unmerged, and the editor says so;
 * no text is ever cut.
 *
 * The contract lifts the inline logic into this module, where it can be tested:
 *   - `TX_DESCRIPTION_MAX_LENGTH = 500`, the backend's `max_length` of a transaction's notes;
 *   - `textLength(text)`, the length in code points, as Python's `len()` counts it: an emoji outside the BMP is one, a
 *     precomposed é one, a decomposed é (e and a combining accent) two;
 *   - `resolvePromoteAllFields(strategy, left, right)`: `{}` when both sides have the same notes and the same tags (in
 *     order, `JSON.stringify` of the arrays, nullish tags read as none, as today); `'left'` and `'right'`: that side's
 *     notes and a copy of its tags; `'merge'`: both combined — or `null` when the combined notes would pass the limit.
 *     Exactly 500 is allowed, and the length is the combined text's: two identical notes collapse to one first.
 *
 * The first describe is today's behaviour of the inline code, lifted as it is (guards); the second is the limit
 * (reds). All of them are red today on their own missing export: the names are read through the module's namespace,
 * so the file still collects and the cases above keep running.
 */
type PromoteSide = {description?: string | null; tags?: string[] | null};
type PromoteAllStrategy = 'left' | 'merge' | 'right';
type ResolvePromoteAllFields = (strategy: PromoteAllStrategy, left: PromoteSide, right: PromoteSide) => Record<string, unknown> | null;

const PROMOTE_ALL_STRATEGIES: readonly PromoteAllStrategy[] = ['left', 'merge', 'right'];

/** An export W-B70 adds to promoteHelpers, or a failure naming it while it does not exist. */
function wb70Export<T>(name: string): T {
    const value = (promoteHelpers as unknown as Record<string, unknown>)[name];
    if (value === undefined) throw new Error(`W-B70: promoteHelpers.${name} does not exist yet`);
    return value as T;
}

const descriptionMaxLength = (): number => wb70Export<number>('TX_DESCRIPTION_MAX_LENGTH');
const textLength = (text: string): number => wb70Export<(text: string) => number>('textLength')(text);
const resolvePromoteAllFields: ResolvePromoteAllFields = (strategy, left, right) => wb70Export<ResolvePromoteAllFields>('resolvePromoteAllFields')(strategy, left, right);

describe('TX_DESCRIPTION_MAX_LENGTH (W-B70)', () => {
    it('is 500, the backend max_length of a transaction’s notes', () => {
        expect(descriptionMaxLength()).toBe(500);
    });
});

describe('textLength — code points, as Python’s len() counts them (W-B70)', () => {
    it('counts 500 ASCII letters as 500, the newline that joins two notes as 1, and the empty string as 0', () => {
        expect(textLength('a'.repeat(500))).toBe(500);
        expect(textLength('\n')).toBe(1);
        expect(textLength('')).toBe(0);
    });

    it('counts an emoji outside the BMP as 1, not its 2 UTF-16 units', () => {
        expect('😀'.length, 'control: two UTF-16 units').toBe(2);
        expect(textLength('😀')).toBe(1);
        expect(textLength('😀'.repeat(300))).toBe(300);
    });

    it('counts a precomposed é as 1', () => {
        expect('\u00e9'.length, 'control: one code point, one UTF-16 unit').toBe(1);
        expect(textLength('\u00e9')).toBe(1);
    });

    it('counts a decomposed é as 2: e and its combining accent are two code points for the backend, not one grapheme', () => {
        const decomposed = 'e\u0301';
        expect(decomposed.normalize('NFC'), 'control: the same letter as the precomposed é').toBe('\u00e9');
        expect(textLength(decomposed)).toBe(2);
    });
});

describe('resolvePromoteAllFields — today’s «Merge all», lifted (W-B70 guards)', () => {
    const OUT = {description: 'Savings out', tags: ['savings', 'monthly']};
    const IN = {description: 'Savings in', tags: ['monthly', 'transfer']};

    it('resolves nothing, {}, for every strategy when both sides have the same notes and the same tags — even notes of 500 characters', () => {
        for (const description of ['Same notes', 'S'.repeat(500)]) {
            for (const strategy of PROMOTE_ALL_STRATEGIES) {
                expect(resolvePromoteAllFields(strategy, {description, tags: ['a', 'b']}, {description, tags: ['a', 'b']}), `${strategy}, notes of ${description.length}`).toEqual({});
            }
        }
    });

    it('reads nullish tags as no tags, as today: null, undefined and [] agree', () => {
        for (const strategy of PROMOTE_ALL_STRATEGIES) {
            expect(resolvePromoteAllFields(strategy, {description: 'Same', tags: null}, {description: 'Same', tags: []}), `${strategy}: null and []`).toEqual({});
            expect(resolvePromoteAllFields(strategy, {description: 'Same'}, {description: 'Same', tags: null}), `${strategy}: undefined and null`).toEqual({});
        }
    });

    it('compares the tags in order, as today: the same tags in another order differ', () => {
        const left = {description: 'Same', tags: ['a', 'b']};
        const right = {description: 'Same', tags: ['b', 'a']};
        expect(resolvePromoteAllFields('left', left, right)).toEqual({description: 'Same', tags: ['a', 'b']});
        expect(resolvePromoteAllFields('right', left, right)).toEqual({description: 'Same', tags: ['b', 'a']});
        expect(resolvePromoteAllFields('merge', left, right), 'identical notes collapse to one copy; the union keeps the left order').toEqual({description: 'Same', tags: ['a', 'b']});
    });

    it("'left': the left row's notes and a copy of its tags", () => {
        const resolved = resolvePromoteAllFields('left', OUT, IN);
        expect(resolved).toEqual({description: 'Savings out', tags: ['savings', 'monthly']});
        expect(resolved?.tags, 'a copy, not the row’s own array').not.toBe(OUT.tags);
    });

    it("'right': the right row's notes and a copy of its tags", () => {
        const resolved = resolvePromoteAllFields('right', OUT, IN);
        expect(resolved).toEqual({description: 'Savings in', tags: ['monthly', 'transfer']});
        expect(resolved?.tags, 'a copy, not the row’s own array').not.toBe(IN.tags);
    });

    it("'merge': both notes, one per line, and the union of the tags", () => {
        expect(resolvePromoteAllFields('merge', OUT, IN)).toEqual({description: 'Savings out\nSavings in', tags: ['savings', 'monthly', 'transfer']});
    });

    it("'merge': notes on one side only are that side's notes, whether the other is null or empty", () => {
        expect(resolvePromoteAllFields('merge', {description: null, tags: ['a']}, {description: 'Savings in', tags: ['a']})).toEqual({description: 'Savings in', tags: ['a']});
        expect(resolvePromoteAllFields('merge', {description: 'Savings out', tags: ['a']}, {description: '', tags: ['a']})).toEqual({description: 'Savings out', tags: ['a']});
    });
});

describe('resolvePromoteAllFields — never past the notes’ limit (W-B70 reds, D-W70-4 a)', () => {
    it("'merge' returns null when the combined notes would be 501 characters: the pair is left for a manual merge", () => {
        const left = {description: 'L'.repeat(250), tags: []};
        const right = {description: 'R'.repeat(250), tags: []};
        expect(mergeStrings(left.description, right.description), 'control: combined, 501 characters').toHaveLength(501);

        expect(resolvePromoteAllFields('merge', left, right)).toBeNull();
    });

    it("'merge' allows exactly 500", () => {
        const left = {description: 'L'.repeat(250), tags: []};
        const right = {description: 'R'.repeat(249), tags: []};
        const combined = `${left.description}\n${right.description}`;
        expect(combined, 'control: combined, 500 characters').toHaveLength(500);

        expect(resolvePromoteAllFields('merge', left, right)).toEqual({description: combined, tags: []});
    });

    it('counts code points: 250 and 249 emoji combine into 500 code points (999 UTF-16 units), allowed', () => {
        const left = {description: '😀'.repeat(250), tags: []};
        const right = {description: '😃'.repeat(249), tags: []};
        const combined = `${left.description}\n${right.description}`;
        expect(combined.length, 'control: 999 UTF-16 units').toBe(999);

        expect(resolvePromoteAllFields('merge', left, right)).toEqual({description: combined, tags: []});
    });

    it('and 250 and 250 emoji, 501 code points, are not', () => {
        expect(resolvePromoteAllFields('merge', {description: '😀'.repeat(250), tags: []}, {description: '😃'.repeat(250), tags: []})).toBeNull();
    });

    it('counts the notes as combined: identical notes of 400 collapse to one copy, allowed, while the tags still merge', () => {
        const notes = 'N'.repeat(400);

        expect(resolvePromoteAllFields('merge', {description: notes, tags: ['a']}, {description: notes, tags: ['b']})).toEqual({description: notes, tags: ['a', 'b']});
    });

    it('counts the notes as combined: an empty side beside 500 characters leaves the 500, allowed', () => {
        const notes = 'R'.repeat(500);

        expect(resolvePromoteAllFields('merge', {description: '', tags: ['x']}, {description: notes, tags: []})).toEqual({description: notes, tags: ['x']});
    });

    it("'left' and 'right' never return null: each side alone fits, only the combination does not", () => {
        const left = {description: 'L'.repeat(500), tags: []};
        const right = {description: 'R'.repeat(500), tags: []};

        expect(resolvePromoteAllFields('left', left, right)).toEqual({description: left.description, tags: []});
        expect(resolvePromoteAllFields('right', left, right)).toEqual({description: right.description, tags: []});
        expect(resolvePromoteAllFields('merge', left, right)).toBeNull();
    });
});
