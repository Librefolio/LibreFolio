/**
 * txCharges — the pure logic of the linked charges of a parent in the transaction form (project 66, F2a), no DOM, no network.
 *
 *   - `chargesFromRows`: the saved FEE / TAX rows of a parent as drafts (magnitude cash, id order, `original` kept for the diff).
 *   - `newCharge`, `chargeCashDirection`, `chargesTotal`, `chargeRowsMissingAmount`, `chargesKey`: the small helpers the section uses.
 *   - `buildChargesBatch`: creates / updates / deletes of the charges, with exact payloads. A new row is created linked to its
 *     parent (`parent_ref` of the same batch, or `parent_transaction_id` of a saved parent); a saved row is updated only for what
 *     changed, never re-linked; a removed row is unlinked (`parent_transaction_id: 0`) or deleted.
 *
 * Every expectation is a literal: the test never calculates its own answer.
 */
import {describe, expect, it} from 'vitest';
import type {TypeRule} from '../transactionTypeStore';
import type {TXReadItem} from '../types';
import * as txCharges from './txCharges';
import {buildChargesBatch, chargeCashDirection, chargeFromPicked, chargeRowsMissingAmount, chargesFromRows, chargesKey, chargesTotal, newCharge, type ChargeDraft, type ChargesParent} from './txCharges';

/** FEE and TAX as the backend declares them: cash out (negative), required; an asset is optional, no quantity; role «charge». */
const CHARGE_RULE: TypeRule = {
    assetField: 'optional',
    cashField: 'required',
    quantityMode: 'forbidden',
    quantityRule: 'zero',
    cashSign: 'negative',
    eventLinkable: false,
    requiresPair: false,
    pairFormLayout: null,
    costBasisMode: 'forbidden',
    costBasisPair: null,
    costBasisAuto: true,
    chargeRole: 'charge',
};
const RULES = {FEE: CHARGE_RULE, TAX: CHARGE_RULE};

const PARENT: ChargesParent = {broker_id: 1, asset_id: 7, date: '2026-03-01'};

function row(fields: Partial<TXReadItem> & {id: number; type: string}): TXReadItem {
    return {broker_id: 1, asset_id: 7, date: '2026-03-01', quantity: '0', ...fields};
}

/** A saved draft whose current values equal its original unless `over` changes them. */
function saved(id: number, over: Partial<ChargeDraft> = {}): ChargeDraft {
    const base = {type: 'FEE' as const, cash: {amount: '5', code: 'EUR'}, description: ''};
    return {key: `saved-${id}`, id, ...base, state: 'linked', original: {...base}, ...over};
}

function added(seq: number, over: Partial<ChargeDraft> = {}): ChargeDraft {
    return {key: `new-${seq}`, id: null, type: 'FEE', cash: {amount: '5', code: 'EUR'}, description: '', state: 'linked', original: null, ...over};
}

describe('chargesFromRows', () => {
    it('keeps only FEE and TAX rows, sorted by id, with the cash as a magnitude', () => {
        const drafts = chargesFromRows([
            row({id: 30, type: 'TAX', cash: {code: 'EUR', amount: '-2.50'}, description: 'stamp'}),
            row({id: 10, type: 'BUY', cash: {code: 'EUR', amount: '-100'}}),
            row({id: 20, type: 'FEE', cash: {code: 'EUR', amount: '-5.00'}}),
            row({id: 5, type: 'DIVIDEND', cash: {code: 'EUR', amount: '3'}}),
        ]);
        expect(drafts).toEqual([
            {key: 'saved-20', id: 20, state: 'linked', type: 'FEE', cash: {amount: '5', code: 'EUR'}, description: '', original: {type: 'FEE', cash: {amount: '5', code: 'EUR'}, description: ''}},
            {key: 'saved-30', id: 30, state: 'linked', type: 'TAX', cash: {amount: '2.5', code: 'EUR'}, description: 'stamp', original: {type: 'TAX', cash: {amount: '2.5', code: 'EUR'}, description: 'stamp'}},
        ]);
    });

    it('gives a null cash and an empty description to a row without them', () => {
        expect(chargesFromRows([row({id: 1, type: 'FEE', cash: null, description: null})])).toEqual([{key: 'saved-1', id: 1, state: 'linked', type: 'FEE', cash: null, description: '', original: {type: 'FEE', cash: null, description: ''}}]);
    });

    it('answers an empty list for no rows or no charges', () => {
        expect(chargesFromRows([])).toEqual([]);
        expect(chargesFromRows([row({id: 1, type: 'BUY'})])).toEqual([]);
    });
});

describe('newCharge', () => {
    it('is an empty draft keyed by its sequence, with no cash even when a default code is given', () => {
        expect(newCharge('FEE', 'EUR', 3)).toEqual({key: 'new-3', id: null, state: 'linked', type: 'FEE', cash: null, description: '', original: null});
    });

    it('accepts a null default code and a TAX', () => {
        expect(newCharge('TAX', null, 1)).toEqual({key: 'new-1', id: null, state: 'linked', type: 'TAX', cash: null, description: '', original: null});
    });
});

describe('chargeCashDirection', () => {
    it('maps negative to out and positive to in', () => {
        expect(chargeCashDirection('negative')).toBe('out');
        expect(chargeCashDirection('positive')).toBe('in');
    });

    it('is null for every other sign rule', () => {
        for (const sign of ['free', 'zero', 'nonzero', 'any', '']) expect(chargeCashDirection(sign), sign).toBeNull();
    });
});

describe('chargesTotal', () => {
    const eur100 = {amount: '100', code: 'EUR'};
    const fee5 = added(1, {cash: {amount: '5', code: 'EUR'}});
    const tax2 = added(2, {type: 'TAX', cash: {amount: '2', code: 'EUR'}});

    it('BUY 100 + FEE 5 + TAX 2 in EUR is 107 out', () => {
        expect(chargesTotal('out', eur100, [fee5, tax2])).toEqual([{currency: 'EUR', amount: '107'}]);
    });

    it('SELL 100 with FEE 5 and TAX 2 nets 93 in', () => {
        expect(chargesTotal('in', eur100, [fee5, tax2])).toEqual([{currency: 'EUR', amount: '93'}]);
    });

    it('keeps one entry per currency: the trade first, then the charges', () => {
        const usd = added(3, {cash: {amount: '1.5', code: 'USD'}});
        expect(chargesTotal('out', eur100, [usd, fee5])).toEqual([
            {currency: 'EUR', amount: '105'},
            {currency: 'USD', amount: '1.5'},
        ]);
    });

    it('skips a charge without cash and a charge with a blank amount', () => {
        const noCash = added(4, {cash: null});
        const blank = added(5, {cash: {amount: '  ', code: 'EUR'}});
        expect(chargesTotal('out', eur100, [fee5, noCash, blank])).toEqual([{currency: 'EUR', amount: '105'}]);
    });

    it('counts only the linked rows: an unlinked or deleted charge is out', () => {
        const unlinked = saved(8, {state: 'unlink'});
        const deleted = saved(9, {state: 'delete'});
        expect(chargesTotal('out', eur100, [fee5, unlinked, deleted])).toEqual([{currency: 'EUR', amount: '105'}]);
        expect(chargesTotal('out', eur100, [unlinked, deleted])).toBeNull();
    });

    it('is null without a direction, without the parent cash, or without charges', () => {
        expect(chargesTotal(null, eur100, [fee5])).toBeNull();
        expect(chargesTotal('out', null, [fee5])).toBeNull();
        expect(chargesTotal('out', eur100, [])).toBeNull();
    });
});

describe('chargeRowsMissingAmount', () => {
    it('lists the keys of rows with a null cash or a blank amount', () => {
        const rows = [added(1, {cash: null}), added(2, {cash: {amount: '', code: 'EUR'}}), added(3, {cash: {amount: '   ', code: 'EUR'}}), added(4), saved(9)];
        expect(chargeRowsMissingAmount(rows)).toEqual(['new-1', 'new-2', 'new-3']);
    });

    it('ignores an unlinked or deleted row without amount', () => {
        expect(chargeRowsMissingAmount([saved(1, {cash: null, state: 'unlink'}), saved(2, {cash: null, state: 'delete'})])).toEqual([]);
    });

    it('is empty when every row has an amount, and for no rows', () => {
        expect(chargeRowsMissingAmount([added(1), saved(2)])).toEqual([]);
        expect(chargeRowsMissingAmount([])).toEqual([]);
    });
});

describe('chargesKey', () => {
    const rows = (): ChargeDraft[] => [saved(1), added(2, {description: 'note'})];

    it('is the same string for equal inputs built apart', () => {
        expect(chargesKey(rows())).toBe(chargesKey(rows()));
    });

    it('changes when a row type, amount, currency or note changes', () => {
        const base = chargesKey(rows());
        const changed = [(r: ChargeDraft[]) => (r[0].type = 'TAX'), (r: ChargeDraft[]) => (r[0].cash = {amount: '6', code: 'EUR'}), (r: ChargeDraft[]) => (r[0].cash = {amount: '5', code: 'USD'}), (r: ChargeDraft[]) => (r[1].description = 'other')];
        for (const mutate of changed) {
            const r = rows();
            mutate(r);
            expect(chargesKey(r)).not.toBe(base);
        }
    });

    it('changes when a row is added or its state changes', () => {
        const base = chargesKey(rows());
        expect(chargesKey([...rows(), added(3)])).not.toBe(base);
        const unlink = rows();
        unlink[0].state = 'unlink';
        const del = rows();
        del[0].state = 'delete';
        expect(chargesKey(unlink)).not.toBe(base);
        expect(chargesKey(del)).not.toBe(base);
        expect(chargesKey(unlink)).not.toBe(chargesKey(del));
    });
});

describe('buildChargesBatch — creates', () => {
    it('creates a new row linked by parent_ref, with the cash signed by the rule', () => {
        const batch = buildChargesBatch([added(1)], PARENT, {parent_ref: 'p'}, RULES);
        expect(batch).toEqual({
            creates: [{broker_id: 1, asset_id: 7, type: 'FEE', date: '2026-03-01', cash: {code: 'EUR', amount: '-5'}, parent_ref: 'p'}],
            updates: [],
            deletes: [],
        });
    });

    it('links a new row to a saved parent with parent_transaction_id', () => {
        const batch = buildChargesBatch([added(1, {type: 'TAX', cash: {amount: '2.5', code: 'USD'}})], PARENT, {parent_transaction_id: 42}, RULES);
        expect(batch.creates).toEqual([{broker_id: 1, asset_id: 7, type: 'TAX', date: '2026-03-01', cash: {code: 'USD', amount: '-2.5'}, parent_transaction_id: 42}]);
    });

    it('sends the description only when it is not blank', () => {
        const batch = buildChargesBatch([added(1, {description: 'broker fee'}), added(2, {description: '   '}), added(3, {description: ''})], PARENT, {parent_ref: 'p'}, RULES);
        expect(batch.creates[0]).toHaveProperty('description', 'broker fee');
        expect(batch.creates[1]).not.toHaveProperty('description');
        expect(batch.creates[2]).not.toHaveProperty('description');
    });

    it('keeps asset_id null for a parent without an asset', () => {
        const batch = buildChargesBatch([added(1)], {broker_id: 2, asset_id: null, date: '2026-04-02'}, {parent_ref: 'p'}, RULES);
        expect(batch.creates).toEqual([{broker_id: 2, asset_id: null, type: 'FEE', date: '2026-04-02', cash: {code: 'EUR', amount: '-5'}, parent_ref: 'p'}]);
    });

    it('creates in row order', () => {
        const batch = buildChargesBatch([added(2, {cash: {amount: '2', code: 'EUR'}}), added(1, {cash: {amount: '1', code: 'EUR'}})], PARENT, {parent_ref: 'p'}, RULES);
        expect(batch.creates.map((c) => (c.cash as {amount: string}).amount)).toEqual(['-2', '-1']);
    });
});

describe('buildChargesBatch — updates of saved rows', () => {
    const link = {parent_transaction_id: 42};

    it('sends no update when nothing changed, 5 vs 5.00 included', () => {
        const unchanged = saved(10);
        const sameNumber = saved(11, {cash: {amount: '5.00', code: 'EUR'}});
        expect(buildChargesBatch([unchanged, sameNumber], PARENT, link, RULES)).toEqual({creates: [], updates: [], deletes: []});
    });

    it('sends only the changed amount, signed', () => {
        expect(buildChargesBatch([saved(10, {cash: {amount: '7', code: 'EUR'}})], PARENT, link, RULES).updates).toEqual([{id: 10, cash: {code: 'EUR', amount: '-7'}}]);
    });

    it('sends the cash when only the currency changed', () => {
        expect(buildChargesBatch([saved(10, {cash: {amount: '5', code: 'USD'}})], PARENT, link, RULES).updates).toEqual([{id: 10, cash: {code: 'USD', amount: '-5'}}]);
    });

    it('sends only the type for a FEE turned into a TAX', () => {
        expect(buildChargesBatch([saved(10, {type: 'TAX'})], PARENT, link, RULES).updates).toEqual([{id: 10, type: 'TAX'}]);
    });

    it('sends the new note, and an empty one when the note was cleared', () => {
        const edited = saved(10, {description: 'new'});
        const cleared = saved(11, {description: '', original: {type: 'FEE', cash: {amount: '5', code: 'EUR'}, description: 'old'}});
        expect(buildChargesBatch([edited, cleared], PARENT, link, RULES).updates).toEqual([
            {id: 10, description: 'new'},
            {id: 11, description: ''},
        ]);
    });

    it('sends several changed fields together, never the link fields', () => {
        const batch = buildChargesBatch([saved(10, {type: 'TAX', cash: {amount: '9', code: 'EUR'}, description: 'x'})], PARENT, link, RULES);
        expect(batch.updates).toEqual([{id: 10, type: 'TAX', cash: {code: 'EUR', amount: '-9'}, description: 'x'}]);
        expect(batch.updates[0]).not.toHaveProperty('parent_transaction_id');
        expect(batch.updates[0]).not.toHaveProperty('parent_ref');
    });

    it('does not count a padded note as a change', () => {
        const row = saved(10, {description: ' a ', original: {type: 'FEE', cash: {amount: '5', code: 'EUR'}, description: 'a'}});
        expect(buildChargesBatch([row], PARENT, link, RULES).updates).toEqual([]);
    });
});

describe('buildChargesBatch — unlinked, deleted rows and order', () => {
    const link = {parent_ref: 'p'};

    it('unlinks a saved row with one update carrying parent_transaction_id 0', () => {
        expect(buildChargesBatch([saved(11, {state: 'unlink'})], PARENT, link, RULES)).toEqual({creates: [], updates: [{id: 11, parent_transaction_id: 0}], deletes: []});
    });

    it('keeps the edits of an unlinked row in the same update', () => {
        const row = saved(11, {state: 'unlink', type: 'TAX', cash: {amount: '9', code: 'EUR'}, description: 'x'});
        expect(buildChargesBatch([row], PARENT, link, RULES).updates).toEqual([{id: 11, type: 'TAX', cash: {code: 'EUR', amount: '-9'}, description: 'x', parent_transaction_id: 0}]);
    });

    it('deletes a saved row by id and drops its edits', () => {
        const row = saved(12, {state: 'delete', cash: {amount: '99', code: 'EUR'}, description: 'x'});
        expect(buildChargesBatch([row], PARENT, link, RULES)).toEqual({creates: [], updates: [], deletes: [12]});
    });

    it('orders creates, updates (linked and unlinks interleaved) and deletes by row order', () => {
        const rows = [saved(21, {state: 'delete'}), saved(10, {type: 'TAX'}), saved(22, {state: 'unlink'}), added(1), saved(23, {state: 'delete'}), saved(11, {cash: {amount: '8', code: 'EUR'}}), saved(24, {state: 'unlink'})];
        const batch = buildChargesBatch(rows, PARENT, link, RULES);
        expect(batch.creates).toHaveLength(1);
        expect(batch.updates.map((u) => u.id)).toEqual([10, 22, 11, 24]);
        expect(batch.deletes).toEqual([21, 23]);
    });

    it('is empty for nothing to do', () => {
        expect(buildChargesBatch([], PARENT, link, RULES)).toEqual({creates: [], updates: [], deletes: []});
    });
});

// ---------------------------------------------------------------------------------------------------------------
//  F4 — a saved charge picked into a parent's section (`linkNew`). RED FIRST: `chargeFromPicked` and `linkNew` do not
//  exist yet.
// ---------------------------------------------------------------------------------------------------------------

describe('chargeFromPicked', () => {
    it('turns a saved FEE into a linked draft flagged linkNew, with the magnitude and the original', () => {
        const draft = chargeFromPicked(row({id: 20, type: 'FEE', cash: {code: 'EUR', amount: '-5.00'}, description: 'bank'}));
        expect(draft).toEqual({key: 'saved-20', id: 20, state: 'linked', linkNew: true, type: 'FEE', cash: {amount: '5', code: 'EUR'}, description: 'bank', original: {type: 'FEE', cash: {amount: '5', code: 'EUR'}, description: 'bank'}});
    });

    it('does the same for a TAX', () => {
        expect(chargeFromPicked(row({id: 31, type: 'TAX', cash: {code: 'USD', amount: '-2.50'}}))).toEqual({
            key: 'saved-31',
            id: 31,
            state: 'linked',
            linkNew: true,
            type: 'TAX',
            cash: {amount: '2.5', code: 'USD'},
            description: '',
            original: {type: 'TAX', cash: {amount: '2.5', code: 'USD'}, description: ''},
        });
    });

    it('answers null for a row that is not a charge', () => {
        expect(chargeFromPicked(row({id: 1, type: 'BUY', cash: {code: 'EUR', amount: '-100'}}))).toBeNull();
    });

    it('is never set by chargesFromRows or newCharge', () => {
        expect(chargesFromRows([row({id: 1, type: 'FEE', cash: {code: 'EUR', amount: '-1'}})])[0]).not.toHaveProperty('linkNew');
        expect(newCharge('FEE', 'EUR', 1)).not.toHaveProperty('linkNew');
    });
});

describe('chargesKey — linkNew', () => {
    it('changes when linkNew is set on a row', () => {
        expect(chargesKey([saved(1, {linkNew: true})])).not.toBe(chargesKey([saved(1)]));
    });
});

describe('buildChargesBatch — linkNew rows', () => {
    it('links an untouched picked row to a parent of the same batch: {id, parent_ref}', () => {
        expect(buildChargesBatch([saved(10, {linkNew: true})], PARENT, {parent_ref: 'p'}, RULES)).toEqual({creates: [], updates: [{id: 10, parent_ref: 'p'}], deletes: []});
    });

    it('links an untouched picked row to a saved parent: {id, parent_transaction_id}', () => {
        expect(buildChargesBatch([saved(10, {linkNew: true})], PARENT, {parent_transaction_id: 42}, RULES).updates).toEqual([{id: 10, parent_transaction_id: 42}]);
    });

    it('sends the changed cash together with the link', () => {
        const batch = buildChargesBatch([saved(10, {linkNew: true, cash: {amount: '7', code: 'EUR'}})], PARENT, {parent_transaction_id: 42}, RULES);
        expect(batch.updates).toEqual([{id: 10, cash: {code: 'EUR', amount: '-7'}, parent_transaction_id: 42}]);
    });

    it('a deleted picked row goes to the deletes, with no update', () => {
        expect(buildChargesBatch([saved(10, {linkNew: true, state: 'delete'})], PARENT, {parent_ref: 'p'}, RULES)).toEqual({creates: [], updates: [], deletes: [10]});
    });

    it('an unlinked picked row sends nothing: it was never linked', () => {
        expect(buildChargesBatch([saved(10, {linkNew: true, state: 'unlink'})], PARENT, {parent_ref: 'p'}, RULES)).toEqual({creates: [], updates: [], deletes: []});
    });

    it('rows without linkNew are unchanged beside a linkNew one', () => {
        const batch = buildChargesBatch([saved(10), saved(11, {linkNew: true}), saved(12, {state: 'unlink'})], PARENT, {parent_transaction_id: 42}, RULES);
        expect(batch.updates).toEqual([
            {id: 11, parent_transaction_id: 42},
            {id: 12, parent_transaction_id: 0},
        ]);
    });
});

// ---------------------------------------------------------------------------------------------------------------
//  TL-2 — a row the picker took from the Bulk. A new row of the Bulk is a mirror with a synthetic negative id and its
//  key (`_bulkKey: 'op-<tempId>'`): the draft is that row's own (`chargeDraftsFor` keys a new charge the same way), so
//  `applyChargeDrafts` links the create itself and never makes a copy. RED until `chargeFromPicked` reads `_bulkKey`.
// ---------------------------------------------------------------------------------------------------------------

/** A mirror of a Bulk row as the Bulk hands it to the picker (`panelItem`: signed as the ledger, no parent). */
function bulkMirror(fields: Partial<TXReadItem> & {id: number; type: string}, bulk: {_bulkKey?: string; _rowRef?: string}): TXReadItem {
    return {...row({parent_transaction_id: null, ...fields}), ...bulk} as TXReadItem;
}

describe('chargeFromPicked — a new row of the Bulk (TL-2)', () => {
    it('a row carrying _bulkKey gives that row’s draft: its key, no id, no original, linked, and no linkNew', () => {
        const draft = chargeFromPicked(bulkMirror({id: -3, type: 'FEE', cash: {code: 'EUR', amount: '-2.50'}, description: 'bulk fee'}, {_bulkKey: 'op-n-fee', _rowRef: 'row 4'}));
        expect(draft).toEqual({key: 'op-n-fee', id: null, state: 'linked', type: 'FEE', cash: {amount: '2.5', code: 'EUR'}, description: 'bulk fee', original: null});
        expect(draft).not.toHaveProperty('linkNew');
    });

    it('a new TAX with no amount yet: cash null, no description → empty', () => {
        const draft = chargeFromPicked(bulkMirror({id: -9, type: 'TAX', cash: null, description: null}, {_bulkKey: 'op-n-tax'}));
        expect(draft).toEqual({key: 'op-n-tax', id: null, state: 'linked', type: 'TAX', cash: null, description: '', original: null});
        expect(draft).not.toHaveProperty('linkNew');
    });

    it('a row with _bulkKey that is no charge answers null', () => {
        expect(chargeFromPicked(bulkMirror({id: -4, type: 'BUY', cash: {code: 'EUR', amount: '-100'}}, {_bulkKey: 'op-n-buy'}))).toBeNull();
    });

    it('guard: a saved row of the Bulk (its txId, no _bulkKey) is today’s picked saved charge, linkNew', () => {
        expect(chargeFromPicked(bulkMirror({id: 20, type: 'FEE', cash: {code: 'EUR', amount: '-5.00'}, description: 'bank'}, {_rowRef: '#20'}))).toEqual({
            key: 'saved-20',
            id: 20,
            state: 'linked',
            linkNew: true,
            type: 'FEE',
            cash: {amount: '5', code: 'EUR'},
            description: 'bank',
            original: {type: 'FEE', cash: {amount: '5', code: 'EUR'}, description: 'bank'},
        });
    });
});

// ---------------------------------------------------------------------------------------------------------------
//  TL-12 — the unsaved links to a SAVED transaction that a new broker or asset breaks: the saved charges linked here
//  (`linkNew`) and the saved parent shown. The form asks before it undoes them. RED until `brokenSavedLinks` exists.
// ---------------------------------------------------------------------------------------------------------------

type LinkSide = {broker_id: number; asset_id: number | null};
type BrokenSavedLinks = <T>(current: LinkSide, next: LinkSide, charges: readonly ChargeDraft[], parent: T | null) => {charges: ChargeDraft[]; parent: T | null};

/** The helper, read at call time: a missing export fails these cases only. */
function brokenSavedLinks<T>(current: LinkSide, next: LinkSide, charges: readonly ChargeDraft[], parent: T | null): {charges: ChargeDraft[]; parent: T | null} {
    const helper = (txCharges as unknown as {brokenSavedLinks?: BrokenSavedLinks}).brokenSavedLinks;
    expect(helper, '66 TL-12: txCharges exports no brokenSavedLinks').toBeTypeOf('function');
    return helper!(current, next, charges, parent);
}

describe('brokenSavedLinks (TL-12)', () => {
    const HERE: LinkSide = {broker_id: 1, asset_id: 7};
    const OTHER_ASSET: LinkSide = {broker_id: 1, asset_id: 8};
    const OTHER_BROKER: LinkSide = {broker_id: 2, asset_id: 7};
    const NONE = {charges: [], parent: null};
    const linkedHere = (id: number, over: Partial<ChargeDraft> = {}) => saved(id, {linkNew: true, ...over});

    it('cell 1: new charges only (op-, new-) break nothing, whatever changes', () => {
        const charges = [added(1), added(2, {key: 'op-n-fee'})];
        expect(brokenSavedLinks(HERE, OTHER_ASSET, charges, null)).toEqual(NONE);
        expect(brokenSavedLinks(HERE, OTHER_BROKER, charges, null)).toEqual(NONE);
    });

    it('cell 2: the saved charges linked here are named, in their order, on a new asset and on a new broker', () => {
        const charges = [linkedHere(30), linkedHere(20, {type: 'TAX'})];
        expect(brokenSavedLinks(HERE, OTHER_ASSET, charges, null)).toEqual({charges, parent: null});
        expect(brokenSavedLinks(HERE, OTHER_BROKER, charges, null)).toEqual({charges, parent: null});
    });

    it('cell 2, mixed: only the saved ones among new charges', () => {
        const savedOne = linkedHere(20);
        expect(brokenSavedLinks(HERE, OTHER_ASSET, [added(1), savedOne, added(2, {key: 'op-n-fee'})], null)).toEqual({charges: [savedOne], parent: null});
    });

    it('cell 3: the saved parent shown is named, as it was given', () => {
        const parent = {id: 10, note: 'a parent'};
        expect(brokenSavedLinks(HERE, OTHER_ASSET, [], parent)).toEqual({charges: [], parent});
        expect(brokenSavedLinks(HERE, OTHER_BROKER, [], parent).parent, 'the very value it was given').toBe(parent);
    });

    it('nothing when neither the broker nor the asset changes, no asset on both sides included', () => {
        const nowhere: LinkSide = {broker_id: 1, asset_id: null};
        expect(brokenSavedLinks(HERE, {...HERE}, [linkedHere(20)], {id: 10})).toEqual(NONE);
        expect(brokenSavedLinks(nowhere, {...nowhere}, [linkedHere(20)], {id: 10})).toEqual(NONE);
    });

    it('no asset → an asset, and an asset → no asset, are both a change', () => {
        const charges = [linkedHere(20)];
        const nowhere: LinkSide = {broker_id: 1, asset_id: null};
        expect(brokenSavedLinks(nowhere, HERE, charges, null)).toEqual({charges, parent: null});
        expect(brokenSavedLinks(HERE, nowhere, charges, null)).toEqual({charges, parent: null});
        expect(brokenSavedLinks(HERE, nowhere, [], {id: 10})).toEqual({charges: [], parent: {id: 10}});
    });

    it('a saved charge linked here but taken out of the section (unlink, delete) is not named', () => {
        expect(brokenSavedLinks(HERE, OTHER_ASSET, [linkedHere(20, {state: 'unlink'}), linkedHere(21, {state: 'delete'})], null)).toEqual(NONE);
    });

    it('a saved charge without linkNew (really saved under this parent) is not named', () => {
        expect(brokenSavedLinks(HERE, OTHER_ASSET, [saved(20), saved(21, {linkNew: false})], null)).toEqual(NONE);
    });

    it('does not touch the drafts it is given', () => {
        const charges = [linkedHere(20), added(1)];
        const before = structuredClone(charges);
        brokenSavedLinks(HERE, OTHER_ASSET, charges, {id: 10});
        expect(charges).toEqual(before);
    });
});
