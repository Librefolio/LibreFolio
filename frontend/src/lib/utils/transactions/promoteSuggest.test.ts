/**
 * promoteSuggest — the pure half of the bulk editor's promote suggestions for a NEW row whose other
 * side is SAVED (plan step 11): Scalable Capital's overnight account imported a month after the broker
 * account, its transfers' other legs already in the database.
 *
 * - `newRowSuggestId`: the id a new row is asked under in `POST /transactions/promote-suggest`. Negative,
 *   because the backend leaves the input ids out of the candidates only when they are positive — real
 *   transactions — and because a negative id can never be mistaken for one.
 * - `mixedPromotePairs`: every (new, saved) pair of the editor that promotes inside the date window, for
 *   the green banner: new rows outer, saved rows inner, the window checked before the match.
 * - `importableSuggestions`: the search's answer reduced to what the 💡 offers to add — per asked row still
 *   in the editor, the candidates the editor does not hold yet; nothing for a row with nothing missing.
 * - `assetQuantitiesCancel`: the banner's test for an asset TRANSFER pair — one asset, exactly opposite
 *   quantities once each type's sign rule has signed them — so that neither the banner nor «Merge all»
 *   offers a pair the backend's promote rule refuses (a saved −3 with a new +5, two assets).
 *
 * The browser side is `e2e/transactions/tx-import-scalable-transfers.spec.ts` and, for the asset
 * pairs, `e2e/transactions/tx-bulk-promote-cost-basis.spec.ts` (PC4).
 */

import {describe, expect, it, vi} from 'vitest';
import type {TypeRule} from '$lib/stores/transactions/transactionTypeStore';
import {assetQuantitiesCancel, importableSuggestions, mixedPromotePairs, newRowSuggestId, type MixedPairingRules, type QuantityCancelable, type SuggestCandidate} from './promoteSuggest';

describe('newRowSuggestId', () => {
    it('is minus the creation sequence plus one: the first new row is asked as -1', () => {
        expect([0, 1, 2, 41].map(newRowSuggestId)).toEqual([-1, -2, -3, -42]);
    });

    it('is negative for every sequence, zero included — never a transaction id, never 0', () => {
        for (const seq of [0, 1, 7, 1000, Number.MAX_SAFE_INTEGER - 1]) expect(newRowSuggestId(seq)).toBeLessThan(0);
    });

    it('gives distinct rows distinct ids', () => {
        const ids = Array.from({length: 50}, (_, seq) => newRowSuggestId(seq));
        expect(new Set(ids).size).toBe(ids.length);
    });
});

/** A row of the editor as far as pairing goes: its id, its day, and what it would promote with. */
interface Row {
    key: string;
    day: number;
    /** The target type it promotes to with any row, or null: the rules' `match` is driven per test. */
    kind: string | null;
}

const row = (key: string, day: number, kind: string | null = 'CASH_TRANSFER'): Row => ({key, day, kind});

/** Rules over `Row`: whole days are |Δday|; a pair promotes to the new row's kind. Spies, so the calls can be read. */
function rules(maxDeltaDays: number, match?: (newRow: Row, savedRow: Row) => string | null) {
    return {
        keyOf: vi.fn((r: Row) => r.key),
        daysBetween: vi.fn((a: Row, b: Row) => Math.abs(a.day - b.day)),
        maxDeltaDays,
        match: vi.fn(match ?? ((newRow: Row) => newRow.kind)),
    } satisfies MixedPairingRules<Row>;
}

describe('mixedPromotePairs', () => {
    it('pairs nothing when either side is empty, and asks the rules nothing', () => {
        const r = rules(3);
        expect(mixedPromotePairs([], [row('s1', 0)], r)).toEqual([]);
        expect(mixedPromotePairs([row('n1', 0)], [], r)).toEqual([]);
        expect(r.daysBetween).not.toHaveBeenCalled();
        expect(r.match).not.toHaveBeenCalled();
    });

    it('lists every promoting pair in the order of the new rows, then of the saved rows', () => {
        const pairs = mixedPromotePairs([row('n1', 0), row('n2', 1)], [row('s1', 0), row('s2', 2)], rules(3));
        expect(pairs).toEqual([
            {newTempId: 'n1', savedTempId: 's1', targetType: 'CASH_TRANSFER'},
            {newTempId: 'n1', savedTempId: 's2', targetType: 'CASH_TRANSFER'},
            {newTempId: 'n2', savedTempId: 's1', targetType: 'CASH_TRANSFER'},
            {newTempId: 'n2', savedTempId: 's2', targetType: 'CASH_TRANSFER'},
        ]);
    });

    it('keeps the new row as newTempId and the saved one as savedTempId, and asks the rules new row first', () => {
        const r = rules(3);
        const newRow = row('new-row', 10);
        const savedRow = row('saved-row', 11);
        expect(mixedPromotePairs([newRow], [savedRow], r)).toEqual([{newTempId: 'new-row', savedTempId: 'saved-row', targetType: 'CASH_TRANSFER'}]);
        expect(r.daysBetween).toHaveBeenCalledWith(newRow, savedRow);
        expect(r.match).toHaveBeenCalledWith(newRow, savedRow);
    });

    it('takes the target type from the match, pair by pair', () => {
        const pairs = mixedPromotePairs([row('n1', 0, 'FX_CONVERSION'), row('n2', 0, 'CASH_TRANSFER')], [row('s1', 0)], rules(3));
        expect(pairs.map((pair) => [pair.newTempId, pair.targetType])).toEqual([
            ['n1', 'FX_CONVERSION'],
            ['n2', 'CASH_TRANSFER'],
        ]);
    });

    it('includes a gap equal to the window and skips a wider one — without asking the match about it', () => {
        const r = rules(3);
        const saved = row('s1', 0);
        const pairs = mixedPromotePairs([row('in-window', 3), row('outside', 4), row('before', -4)], [saved], r);
        expect(pairs.map((pair) => pair.newTempId)).toEqual(['in-window']);
        expect(r.match.mock.calls.map(([newRow]) => newRow.key)).toEqual(['in-window']);
    });

    it('with a window of zero days pairs same-day rows only', () => {
        const pairs = mixedPromotePairs([row('same', 5), row('next', 6)], [row('s1', 5)], rules(0));
        expect(pairs.map((pair) => pair.newTempId)).toEqual(['same']);
    });

    it.each([
        ['null', null],
        ['an empty type', ''],
    ])('skips a pair whose match is %s', (_label, verdict) => {
        const pairs = mixedPromotePairs([row('n1', 0, verdict), row('n2', 0)], [row('s1', 0)], rules(3));
        expect(pairs).toEqual([{newTempId: 'n2', savedTempId: 's1', targetType: 'CASH_TRANSFER'}]);
    });

    it('decides each pair on its own: one new row may pair with several saved rows, and one saved row with several new ones', () => {
        // The rules decide what promotes; the function lists, it does not deduplicate.
        const onlyEven = (newRow: Row, savedRow: Row) => ((newRow.day + savedRow.day) % 2 === 0 ? 'CASH_TRANSFER' : null);
        const pairs = mixedPromotePairs([row('n0', 0), row('n1', 1), row('n2', 2)], [row('s0', 0), row('s2', 2)], rules(5, onlyEven));
        expect(pairs.map((pair) => `${pair.newTempId}+${pair.savedTempId}`)).toEqual(['n0+s0', 'n0+s2', 'n2+s0', 'n2+s2']);
    });

    it('leaves its inputs alone', () => {
        const newRows = Object.freeze([Object.freeze(row('n1', 0))]);
        const savedRows = Object.freeze([Object.freeze(row('s1', 1))]);
        expect(() => mixedPromotePairs(newRows, savedRows, rules(3))).not.toThrow();
        expect(newRows).toEqual([row('n1', 0)]);
        expect(savedRows).toEqual([row('s1', 1)]);
    });
});

const candidate = (id: number, brokerId = 1, date = '2026-06-01', type = 'DEPOSIT'): SuggestCandidate => ({id, broker_id: brokerId, date, type});

/** The editor's map from asked id to row: saved rows by transaction id, new rows by `newRowSuggestId`. */
function tempIds(entries: Record<number, string>): (key: number) => string | undefined {
    return (key) => entries[key];
}

describe('importableSuggestions', () => {
    it('offers, per asked row, the candidates the editor does not hold yet — new rows (negative ids) like saved ones', () => {
        const results = new Map<number, SuggestCandidate[]>([
            [-1, [candidate(101)]],
            [55, [candidate(102, 2, '2026-04-02', 'WITHDRAWAL')]],
        ]);
        expect(importableSuggestions(results, tempIds({[-1]: 'new-row', 55: 'saved-row'}), new Set())).toEqual([
            {key: -1, tempId: 'new-row', candidates: [candidate(101)]},
            {key: 55, tempId: 'saved-row', candidates: [candidate(102, 2, '2026-04-02', 'WITHDRAWAL')]},
        ]);
    });

    it('drops the candidates already in the editor, keeping the others in their order', () => {
        const results = new Map([[-3, [candidate(201), candidate(202), candidate(203)]]]);
        expect(importableSuggestions(results, tempIds({[-3]: 'row'}), new Set([202]))).toEqual([{key: -3, tempId: 'row', candidates: [candidate(201), candidate(203)]}]);
    });

    it('drops a row whose candidates are all in the editor already, or that has none', () => {
        const results = new Map<number, SuggestCandidate[]>([
            [-1, [candidate(301), candidate(302)]],
            [-2, []],
            [-4, [candidate(303)]],
        ]);
        expect(importableSuggestions(results, tempIds({[-1]: 'all-held', [-2]: 'no-candidate', [-4]: 'one-missing'}), new Set([301, 302]))).toEqual([{key: -4, tempId: 'one-missing', candidates: [candidate(303)]}]);
    });

    it('drops an asked row that is no longer in the editor', () => {
        const results = new Map([
            [-1, [candidate(401)]],
            [-2, [candidate(402)]],
        ]);
        expect(importableSuggestions(results, tempIds({[-2]: 'still-here'}), new Set())).toEqual([{key: -2, tempId: 'still-here', candidates: [candidate(402)]}]);
    });

    it('keeps the order of the answer', () => {
        const results = new Map([
            [9, [candidate(503)]],
            [-7, [candidate(501)]],
            [3, [candidate(502)]],
        ]);
        expect(importableSuggestions(results, tempIds({9: 'a', [-7]: 'b', 3: 'c'}), new Set()).map((entry) => entry.key)).toEqual([9, -7, 3]);
    });

    it('answers nothing for an empty answer', () => {
        expect(importableSuggestions(new Map(), tempIds({}), new Set([1]))).toEqual([]);
    });

    it('returns its own lists and leaves the answer alone — whether some candidates are held or none', () => {
        const partlyHeld = [candidate(601), candidate(602)];
        const noneHeld = [candidate(603)];
        const results = new Map([
            [-1, partlyHeld],
            [-2, noneHeld],
        ]);
        const entries = importableSuggestions(results, tempIds({[-1]: 'row', [-2]: 'other'}), new Set([602]));
        expect(entries.map((entry) => entry.candidates)).toEqual([[candidate(601)], [candidate(603)]]);
        expect(entries[0].candidates).not.toBe(partlyHeld);
        expect(entries[1].candidates).not.toBe(noneHeld);
        expect(partlyHeld).toEqual([candidate(601), candidate(602)]);
        expect(results.get(-1)).toBe(partlyHeld);
        expect(results.get(-2)).toBe(noneHeld);
    });
});

/**
 * The sign rules the backend sends for a quantity (`SignType`: positive, negative, zero, nonzero, free).
 * ADJUSTMENT and TRANSFER — the rows the banner pairs into a TRANSFER — are `nonzero`: the typed sign is
 * the sign. QTY_OUT and QTY_IN stand for a type that carries the sign, whose quantity the editor shows
 * as a magnitude (SELL is `negative`, BUY `positive`). Anything else gets the rule of an unknown type,
 * `free`. Only `quantityRule` is read by the helper.
 */
const SIGN_RULES: Record<string, string> = {ADJUSTMENT: 'nonzero', TRANSFER: 'nonzero', QTY_OUT: 'negative', QTY_IN: 'positive'};
const resolveRule = (type: string): TypeRule => ({quantityRule: SIGN_RULES[type] ?? 'free'}) as unknown as TypeRule;

/** An editor row as far as the helper goes: type (ADJUSTMENT unless given), quantity, asset (7 unless given, even as null/undefined). */
function assetRow(quantity: string | number | null | undefined, options: {asset?: number | null; type?: string} = {}): QuantityCancelable {
    return {fields: {type: options.type ?? 'ADJUSTMENT', quantity, asset_id: 'asset' in options ? options.asset : 7}};
}

describe('assetQuantitiesCancel', () => {
    it('is true for one asset moved by exactly opposite quantities, in either order', () => {
        expect(assetQuantitiesCancel(assetRow('-5'), assetRow('5'), resolveRule)).toBe(true);
        expect(assetQuantitiesCancel(assetRow('5'), assetRow('-5'), resolveRule)).toBe(true);
    });

    it.each([
        ['a saved −3 with a new +5', '-3', '5'],
        ['a new +5 with a saved −3', '5', '-3'],
        ['the same sign twice', '5', '5'],
        ['a 6th-decimal difference on a small quantity', '-5', '5.000001'],
    ])('is false when the quantities do not cancel: %s', (_label, a, b) => {
        expect(assetQuantitiesCancel(assetRow(a), assetRow(b), resolveRule)).toBe(false);
    });

    it('is false for two assets, even when the quantities cancel', () => {
        expect(assetQuantitiesCancel(assetRow('-5', {asset: 7}), assetRow('5', {asset: 8}), resolveRule)).toBe(false);
    });

    it.each([
        ['the first row', null, 7],
        ['the second row', 7, null],
        ['either row — two unknown assets are not one asset', null, null],
        ['either row, left undefined', undefined, undefined],
    ])('is false when %s has no asset', (_label, first, second) => {
        expect(assetQuantitiesCancel(assetRow('-5', {asset: first}), assetRow('5', {asset: second}), resolveRule)).toBe(false);
    });

    it.each([
        ['0', '0'],
        ['0', '-0'],
        ['0.000000', '-0.000000'],
        ['0', '5'],
        ['-5', '0'],
    ])('is false when a quantity is zero: %s with %s', (a, b) => {
        expect(assetQuantitiesCancel(assetRow(a), assetRow(b), resolveRule)).toBe(false);
    });

    it.each([
        ['empty', ''],
        ['null', null],
        ['missing', undefined],
        ['not a number', 'abc'],
    ])('is false when a quantity is %s, on either side', (_label, quantity) => {
        expect(assetQuantitiesCancel(assetRow(quantity), assetRow('5'), resolveRule)).toBe(false);
        expect(assetQuantitiesCancel(assetRow('-5'), assetRow(quantity), resolveRule)).toBe(false);
    });
});

describe('assetQuantitiesCancel — a magnitude takes the sign its type carries', () => {
    // Where the type carries the sign the editor shows a magnitude (fieldsFromTx), so the rule decides
    // the sign, never the stored string.

    it('cancels two magnitudes of opposite signed types', () => {
        expect(assetQuantitiesCancel(assetRow('5', {type: 'QTY_OUT'}), assetRow('5', {type: 'QTY_IN'}), resolveRule)).toBe(true);
    });

    it('gives the same answer whatever sign the strings carry', () => {
        for (const out of ['5', '-5']) {
            for (const into of ['5', '-5']) {
                expect(assetQuantitiesCancel(assetRow(out, {type: 'QTY_OUT'}), assetRow(into, {type: 'QTY_IN'}), resolveRule), `${out} out, ${into} in`).toBe(true);
            }
        }
    });

    it('never cancels two rows of one signed type', () => {
        expect(assetQuantitiesCancel(assetRow('5', {type: 'QTY_OUT'}), assetRow('-5', {type: 'QTY_OUT'}), resolveRule)).toBe(false);
        expect(assetQuantitiesCancel(assetRow('5', {type: 'QTY_IN'}), assetRow('-5', {type: 'QTY_IN'}), resolveRule)).toBe(false);
    });

    it('cancels a magnitude against a free-sign row typed with the opposite sign', () => {
        expect(assetQuantitiesCancel(assetRow('5', {type: 'QTY_OUT'}), assetRow('5'), resolveRule)).toBe(true);
        expect(assetQuantitiesCancel(assetRow('5', {type: 'QTY_IN'}), assetRow('-5'), resolveRule)).toBe(true);
    });

    it('still needs the magnitudes to match once signed', () => {
        expect(assetQuantitiesCancel(assetRow('3', {type: 'QTY_OUT'}), assetRow('5', {type: 'QTY_IN'}), resolveRule)).toBe(false);
    });
});

describe('assetQuantitiesCancel — a free-sign type keeps the typed sign', () => {
    it.each([
        ['nonzero: ADJUSTMENT, the rows the banner pairs', 'ADJUSTMENT'],
        ['nonzero: TRANSFER', 'TRANSFER'],
        ['free: the rule of an unknown type', 'SOMETHING_ELSE'],
    ])('%s', (_label, type) => {
        expect(assetQuantitiesCancel(assetRow('-5', {type}), assetRow('5', {type}), resolveRule)).toBe(true);
        expect(assetQuantitiesCancel(assetRow('5', {type}), assetRow('5', {type}), resolveRule)).toBe(false);
        expect(assetQuantitiesCancel(assetRow('-5', {type}), assetRow('-5', {type}), resolveRule)).toBe(false);
    });
});

describe('assetQuantitiesCancel — values, not representations', () => {
    it.each([
        ['5.000000', '-5'],
        ['-5.000000', '5'],
        ['0005.50', '-5.500000'],
        ['-0.000001', '0.000001'],
    ])('%s cancels %s', (a, b) => {
        expect(assetQuantitiesCancel(assetRow(a), assetRow(b), resolveRule)).toBe(true);
    });

    it('takes a number as readily as a string', () => {
        expect(assetQuantitiesCancel(assetRow(5), assetRow('-5.0'), resolveRule)).toBe(true);
        expect(assetQuantitiesCancel(assetRow(-2.5), assetRow(2.5), resolveRule)).toBe(true);
    });
});

describe('assetQuantitiesCancel — exactly, as the backend compares', () => {
    // The backend's promote rule compares Decimals: `tx_a.quantity != -tx_b.quantity` refuses any
    // difference. A relative tolerance is not that: 1e-9 of 1 500 units is 1.5e-6, coarser than the 6th
    // decimal the editor keeps, and past ~15 significant digits a Number cannot tell two quantities apart
    // at all. Two legs an import rounded differently would be offered by the banner and refused on Save.
    it.each([
        ['an import rounding the 6th decimal of 1 500 units', '1500.123457', '-1500.123456'],
        ['the widest quantity the form takes, 12 + 6 digits', '999999999999.123456', '-999999999999.123457'],
    ])('is false for quantities one unit of the 6th decimal apart: %s', (_label, a, b) => {
        expect(assetQuantitiesCancel(assetRow(a), assetRow(b), resolveRule)).toBe(false);
    });
});
