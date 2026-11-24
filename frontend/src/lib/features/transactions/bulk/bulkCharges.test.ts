/**
 * bulkCharges — the linked charges of the Bulk editor, as operations (project 66, F7-b, model H).
 *
 * A charge (a FEE or a TAX) brought into the Bulk is a `PendingOp` of its own, owned by its parent through `chargeOf` (the
 * parent's `tempId`), never through `pairedWith`. The link that changes lives on the charge: `parentUnlink` («scollega»:
 * the payload sends `parent_transaction_id: 0`), `parentLinkId` (a saved parent absent from the Bulk), and a create born
 * in its parent's form carries `followsParent`. This module is the pure half of that model (contract 66-F7 §10, corrected
 * by §11):
 *
 *   - `adoptCharges`      a present parent adopts its saved charges, recognised by their saved `parent_transaction_id`;
 *                         a `parentLinkId` turns into `chargeOf` once its parent arrives. Pairs untouched. Idempotent.
 *   - `remapChargeOf`     a reset regenerates the parent's `tempId`: its charges follow it (§11.2).
 *   - `isUnderParent`     the one predicate of «sits under its parent» (§11.7).
 *   - `chargeDraftsFor`   the parent's form gets its charges as `ChargeDraft[]` (`txCharges.ts`).
 *   - `applyChargeDrafts` the form's answer back onto the operations: one way, nothing typed is lost.
 *   - `chargeParentFields`/`parentNeedsRef` what the payload of a charge carries to name its parent, and which creates
 *                         need a `ref`.
 *   - `foldBulkCharges`   (F7-c1) the grid's rows: the top-level rows in order, each open parent followed by its
 *                         charges (`isUnderParent`), in the order of the operations.
 *   - `rowAnchor`         (F7-c1) the row on screen that stands for an operation: a charge under a closed parent → the
 *                         parent; open → itself; otherwise `pairedWith ?? tempId`.
 *   (`chargeUnlinkList`, the F6 banner's list, is gone in F7-c1: the indented «scollega» rows replace the banner.)
 *
 * And the five invariants of the payload (§3 + §11.2), checked on a payload built by applying `chargeParentFields` to
 * operations that the module itself produced: every id once across updates and deletes; a deleted parent leaves each of
 * its saved charges deleted or unlinked; every `parent_ref` names a `ref` of the same batch; no charge kept twice; every
 * `chargeOf` names an operation present. The checker is proved to bite, on one bad payload per invariant.
 *
 * RED until `bulkCharges.ts` exists and `PendingOp` gains `chargeOf`, `parentUnlink`, `parentLinkId`, `followsParent`.
 */
import {describe, expect, it, vi} from 'vitest';
import type {TXReadItem} from '../types';
import type {DraftFields, PendingOp} from './txBulkTypes';
import {chargeFromPicked, chargesFromRows, type ChargeDraft} from '../form/txCharges';
import {magnitudeForRule} from '../txPayloadHelpers';
import {adoptCharges, applyChargeDrafts, chargeDraftsFor, chargeParentFields, isUnderParent, parentNeedsRef, remapChargeOf} from './bulkCharges';
// F7-c1: the two functions it adds, read through the namespace so that while they do not exist only their own cases fail.
import * as bulkChargesModule from './bulkCharges';

// ---------------------------------------------------------------------------
// Fixtures: a store of saved rows, and operations built from them
// ---------------------------------------------------------------------------

function row(id: number, type: string, extra: Partial<TXReadItem> = {}): TXReadItem {
    return {
        id,
        broker_id: 77,
        asset_id: 101,
        type,
        date: '2026-10-01',
        quantity: type === 'BUY' ? '2.000000' : '0',
        cash: {code: 'EUR', amount: '-10.000000'},
        related_transaction_id: null,
        partner_broker_id: null,
        parent_transaction_id: null,
        charges_count: 0,
        tags: [],
        description: `saved ${type} ${id}`,
        cost_basis_override: null,
        asset_event_id: null,
        ...extra,
    };
}

/** A saved BUY with two charges, a FEE and a TAX. */
const BUY_A = row(501, 'BUY', {charges_count: 2});
const FEE_A = row(502, 'FEE', {parent_transaction_id: 501, cash: {code: 'EUR', amount: '-1.500000'}, description: 'fee A'});
const TAX_A = row(503, 'TAX', {parent_transaction_id: 501, cash: {code: 'EUR', amount: '-0.250000'}, description: 'tax A'});
/** Another saved BUY with one FEE. */
const BUY_B = row(511, 'BUY', {date: '2026-10-05', charges_count: 1});
const FEE_B = row(512, 'FEE', {parent_transaction_id: 511, date: '2026-10-05', cash: {code: 'EUR', amount: '-2.000000'}, description: 'fee B'});
/** A saved FEE that belongs to no parent. */
const FEE_FREE = row(520, 'FEE', {cash: {code: 'EUR', amount: '-3.000000'}, description: 'fee free'});
/** A saved TRANSFER pair: never touched by the charges. */
const PAIR_FROM = row(530, 'TRANSFER', {related_transaction_id: 531, cash: null, quantity: '-1.000000'});
const PAIR_TO = row(531, 'TRANSFER', {related_transaction_id: 530, cash: null, quantity: '1.000000', broker_id: 88});

const STORE = new Map<number, TXReadItem>([BUY_A, FEE_A, TAX_A, BUY_B, FEE_B, FEE_FREE, PAIR_FROM, PAIR_TO].map((r) => [r.id, r]));
const get = (id: number): TXReadItem | undefined => STORE.get(id);

/** The fields of a saved row as the editor holds them: amounts as magnitudes (`fieldsFromTx`). */
function fieldsOf(r: TXReadItem): DraftFields {
    return {
        broker_id: r.broker_id,
        asset_id: r.asset_id ?? null,
        type: r.type as DraftFields['type'],
        date: r.date,
        quantity: magnitudeForRule(r.quantity, 'free'),
        cash: r.cash ? {code: r.cash.code, amount: magnitudeForRule(r.cash.amount, 'negative')} : null,
        tags: [...(r.tags ?? [])],
        description: r.description ?? '',
        asset_event_id: null,
        cost_basis_override: null,
        cost_basis_mode: null,
    };
}

type OpExtra = {tempId?: string; markedDelete?: boolean; chargeOf?: string; parentUnlink?: boolean; parentLinkId?: number; followsParent?: boolean; pairedWith?: string; link_uuid?: string | null};

/** The edit operation of a saved row; its `tempId` is `t-<id>` unless given. */
function editOp(r: TXReadItem, extra: OpExtra = {}): PendingOp {
    return {op: 'edit', txId: r.id, markedDelete: false, tempId: `t-${r.id}`, createdSeq: r.id, fields: fieldsOf(r), ...extra};
}

/** A create operation. */
function createOp(tempId: string, fields: DraftFields, extra: Omit<OpExtra, 'markedDelete' | 'tempId'> = {}): PendingOp {
    return {op: 'create', tempId, createdSeq: 0, fields, ...extra};
}

/** A new BUY typed in the Bulk. */
function newBuyFields(): DraftFields {
    return {...fieldsOf(BUY_A), date: '2026-10-20', description: 'new buy'};
}

/** A new FEE draft as the form adds it (`newCharge`), with an amount and a note typed. */
function newDraft(key: string, type: 'FEE' | 'TAX', amount: string, description: string): ChargeDraft {
    return {key, id: null, type, cash: {amount, code: 'EUR'}, description, original: null, state: 'linked'};
}

function byTxId(ops: readonly PendingOp[], txId: number): PendingOp {
    const found = ops.filter((op) => op.op === 'edit' && op.txId === txId);
    if (found.length !== 1) throw new Error(`expected one operation for #${txId}, found ${found.length}`);
    return found[0];
}

function byTempId(ops: readonly PendingOp[], tempId: string): PendingOp {
    const found = ops.filter((op) => op.tempId === tempId);
    if (found.length !== 1) throw new Error(`expected one operation ${tempId}, found ${found.length}`);
    return found[0];
}

function draftByKey(drafts: readonly ChargeDraft[], key: string): ChargeDraft {
    const found = drafts.filter((draft) => draft.key === key);
    if (found.length !== 1) throw new Error(`expected one draft ${key}, found ${found.length}: ${drafts.map((d) => d.key).join(', ')}`);
    return found[0];
}

/** The dependencies `applyChargeDrafts` takes from the editor: two spies, which return operations WITHOUT `chargeOf` and
 *  `followsParent` (setting them is the module's job, whatever the editor hands back), and the store (`get`, required
 *  since 66 C22c: `unlinkCharge` reads the saved parent). */
function makeDeps() {
    const editOpFromTx = vi.fn((id: number): PendingOp | null => {
        const r = get(id);
        return r ? editOp(r, {tempId: `fresh-${id}`}) : null;
    });
    const newChargeOp = vi.fn((draft: ChargeDraft, parent: PendingOp): PendingOp => createOp(`made-${draft.key}`, {...parent.fields, type: draft.type, cash: draft.cash ? {...draft.cash} : null, description: draft.description, quantity: '0', tags: []}));
    return {editOpFromTx, newChargeOp, get};
}

/** A deep copy, to prove an input was not mutated. */
const snapshot = <T>(value: T): T => structuredClone(value);

// ---------------------------------------------------------------------------
// adoptCharges
// ---------------------------------------------------------------------------

describe('adoptCharges — a present parent adopts its saved charges', () => {
    it('a FEE and a TAX whose saved parent is an edit operation of the Bulk take that operation’s tempId as chargeOf', () => {
        const out = adoptCharges([editOp(BUY_A), editOp(FEE_A), editOp(TAX_A)], get);

        expect(byTxId(out, FEE_A.id).chargeOf).toBe('t-501');
        expect(byTxId(out, TAX_A.id).chargeOf).toBe('t-501');
        expect(byTxId(out, BUY_A.id).chargeOf, 'the parent itself belongs to nobody').toBeUndefined();
    });

    it('recognises the parent by its saved id, not by its position nor its tempId', () => {
        const out = adoptCharges([editOp(TAX_A), editOp(FEE_B), editOp(BUY_B, {tempId: 'other'}), editOp(BUY_A, {tempId: 'zzz'})], get);

        expect(byTxId(out, TAX_A.id).chargeOf).toBe('zzz');
        expect(byTxId(out, FEE_B.id).chargeOf).toBe('other');
    });

    it('a parent marked for deletion still adopts its charges', () => {
        const out = adoptCharges([editOp(BUY_A, {markedDelete: true}), editOp(FEE_A)], get);
        expect(byTxId(out, FEE_A.id).chargeOf).toBe('t-501');
    });

    it('a charge whose parent is not in the Bulk, and a charge with no parent, stay without chargeOf', () => {
        const out = adoptCharges([editOp(FEE_A), editOp(FEE_FREE), editOp(BUY_B)], get);

        expect(byTxId(out, FEE_A.id).chargeOf).toBeUndefined();
        expect(byTxId(out, FEE_FREE.id).chargeOf).toBeUndefined();
    });

    it('a chargeOf already set is kept, even when the saved parent is present too', () => {
        // Linked in this Bulk to the new BUY: the saved link to BUY_A must not take it back.
        const ops = [editOp(BUY_A), createOp('new-buy', newBuyFields()), editOp(FEE_A, {chargeOf: 'new-buy'})];
        const out = adoptCharges(ops, get);
        expect(byTxId(out, FEE_A.id).chargeOf).toBe('new-buy');
    });

    it('a parentLinkId becomes chargeOf when its parent arrives, and the parentLinkId goes', () => {
        const ops = [editOp(FEE_FREE, {parentLinkId: BUY_B.id}), editOp(BUY_B)];
        const out = adoptCharges(ops, get);

        const fee = byTxId(out, FEE_FREE.id);
        expect(fee.chargeOf).toBe('t-511');
        expect(fee.parentLinkId).toBeUndefined();
    });

    it('a parentLinkId whose parent is absent stays as it is', () => {
        const out = adoptCharges([editOp(FEE_FREE, {parentLinkId: BUY_B.id})], get);

        const fee = byTxId(out, FEE_FREE.id);
        expect(fee.parentLinkId).toBe(BUY_B.id);
        expect(fee.chargeOf).toBeUndefined();
    });

    it('never touches a pair: its two halves come out exactly as they went in', () => {
        const from = editOp(PAIR_FROM, {link_uuid: 'L-1'});
        const to = editOp(PAIR_TO, {pairedWith: from.tempId, link_uuid: 'L-1'});
        const out = adoptCharges([from, to, editOp(BUY_A), editOp(FEE_A)], get);

        expect(byTxId(out, PAIR_FROM.id)).toEqual(from);
        expect(byTxId(out, PAIR_TO.id)).toEqual(to);
    });

    it('returns a new array and leaves its input as it was', () => {
        const ops = [editOp(BUY_A), editOp(FEE_A), editOp(TAX_A), editOp(FEE_FREE, {parentLinkId: BUY_A.id})];
        const before = snapshot(ops);

        const out = adoptCharges(ops, get);

        expect(out).not.toBe(ops);
        expect(ops, 'the input operations are not mutated').toEqual(before);
    });

    it('is idempotent', () => {
        const ops = [editOp(BUY_A), editOp(FEE_A), editOp(TAX_A), editOp(BUY_B), editOp(FEE_B), editOp(FEE_FREE, {parentLinkId: BUY_B.id})];
        const once = adoptCharges(ops, get);
        expect(adoptCharges(once, get)).toEqual(once);
    });
});

// ---------------------------------------------------------------------------
// remapChargeOf
// ---------------------------------------------------------------------------

describe('remapChargeOf — the charges follow their parent’s new tempId', () => {
    it('every chargeOf naming the old tempId names the new one; the others are untouched', () => {
        const ops = [editOp(BUY_A), editOp(FEE_A, {chargeOf: 't-501'}), editOp(TAX_A, {chargeOf: 't-501', parentUnlink: true}), createOp('new-fee', fieldsOf(FEE_A), {chargeOf: 't-501', followsParent: true}), editOp(BUY_B), editOp(FEE_B, {chargeOf: 't-511'})];
        const before = snapshot(ops);

        const out = remapChargeOf(ops, 't-501', 'reset-501');

        expect(byTxId(out, FEE_A.id).chargeOf).toBe('reset-501');
        expect(byTxId(out, TAX_A.id)).toMatchObject({chargeOf: 'reset-501', parentUnlink: true});
        expect(byTempId(out, 'new-fee')).toMatchObject({chargeOf: 'reset-501', followsParent: true});
        expect(byTxId(out, FEE_B.id).chargeOf, 'another parent’s charge').toBe('t-511');
        expect(ops, 'the input is not mutated').toEqual(before);
    });

    it('with nothing to remap, the operations come out equal', () => {
        const ops = [editOp(BUY_A), editOp(FEE_B, {chargeOf: 't-511'})];
        expect(remapChargeOf(ops, 'nobody', 'x')).toEqual(ops);
    });
});

// ---------------------------------------------------------------------------
// isUnderParent — the one predicate (§11.7)
// ---------------------------------------------------------------------------

describe('isUnderParent — the one predicate of «sits under its parent»', () => {
    const parent = editOp(BUY_A);
    const deletedParent = editOp(BUY_A, {markedDelete: true});

    it.each([
        ['no chargeOf', [parent, editOp(FEE_A)], false],
        ['chargeOf naming an operation that is not there', [editOp(FEE_A, {chargeOf: 't-501'})], false],
        ['chargeOf, linked', [parent, editOp(FEE_A, {chargeOf: 't-501'})], true],
        ['chargeOf, itself marked for deletion', [parent, editOp(FEE_A, {chargeOf: 't-501', markedDelete: true})], true],
        ['chargeOf + parentUnlink, the parent stays', [parent, editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true})], false],
        ['chargeOf + parentUnlink, the parent marked for deletion', [deletedParent, editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true})], true],
        ['a new charge of a new parent', [createOp('new-buy', newBuyFields()), createOp('new-fee', fieldsOf(FEE_A), {chargeOf: 'new-buy'})], true],
    ] as const)('%s → %s', (_label, ops, expected) => {
        const charge = ops[ops.length - 1];
        expect(isUnderParent(charge, [...ops])).toBe(expected);
    });
});

// ---------------------------------------------------------------------------
// chargeDraftsFor
// ---------------------------------------------------------------------------

describe('chargeDraftsFor — the parent’s form gets its charges as drafts', () => {
    it('a saved charge: key saved-<id>, its id, the values of its operation, original from the store as chargesFromRows reads it, state linked', () => {
        const ops = adoptCharges([editOp(BUY_A), editOp(FEE_A), editOp(TAX_A)], get);

        const drafts = chargeDraftsFor(byTxId(ops, BUY_A.id), ops, get);

        expect(drafts).toHaveLength(2);
        const fee = draftByKey(drafts, `saved-${FEE_A.id}`);
        expect(fee).toMatchObject({id: FEE_A.id, type: 'FEE', cash: {amount: '1.5', code: 'EUR'}, description: 'fee A', state: 'linked'});
        expect(fee.original, 'original: the saved values, magnitudes, exactly as the form reads them').toEqual(chargesFromRows([FEE_A])[0].original);
        expect(fee.linkNew ?? false, 'a charge already linked to this parent is not a new link').toBe(false);
        expect(draftByKey(drafts, `saved-${TAX_A.id}`).original).toEqual(chargesFromRows([TAX_A])[0].original);
    });

    it('the current values come from the operation, the original from the store', () => {
        const ops = adoptCharges([editOp(BUY_A), editOp(FEE_A, {})], get).map((op) => (op.op === 'edit' && op.txId === FEE_A.id ? {...op, fields: {...op.fields, description: 'typed in the grid', cash: {code: 'EUR', amount: '9'}}} : op));

        const fee = draftByKey(chargeDraftsFor(byTxId(ops, BUY_A.id), ops, get), `saved-${FEE_A.id}`);

        expect(fee.description).toBe('typed in the grid');
        expect(fee.cash).toEqual({amount: '9', code: 'EUR'});
        expect(fee.original?.description).toBe('fee A');
    });

    it('state: delete for a charge marked for deletion, unlink for parentUnlink', () => {
        const ops = [editOp(BUY_A, {markedDelete: true}), editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true}), editOp(TAX_A, {chargeOf: 't-501', markedDelete: true})];

        const drafts = chargeDraftsFor(ops[0], ops, get);

        expect(draftByKey(drafts, `saved-${FEE_A.id}`).state).toBe('unlink');
        expect(draftByKey(drafts, `saved-${TAX_A.id}`).state).toBe('delete');
    });

    it('a new charge (a create): key op-<tempId>, no id, no original, its values', () => {
        const ops = [createOp('new-buy', newBuyFields()), createOp('n-fee', {...fieldsOf(FEE_A), description: 'brand new', cash: {code: 'EUR', amount: '4'}}, {chargeOf: 'new-buy', followsParent: true})];

        const drafts = chargeDraftsFor(ops[0], ops, get);

        expect(drafts).toEqual([{key: 'op-n-fee', id: null, type: 'FEE', cash: {amount: '4', code: 'EUR'}, description: 'brand new', original: null, state: 'linked'}]);
    });

    it('only this parent’s charges: not another parent’s, not a free FEE, not a FEE whose saved parent is this one but that was not adopted', () => {
        const ops = [editOp(BUY_A), editOp(FEE_A, {chargeOf: 't-501'}), editOp(TAX_A), editOp(BUY_B), editOp(FEE_B, {chargeOf: 't-511'}), editOp(FEE_FREE)];

        const drafts = chargeDraftsFor(ops[0], ops, get);

        expect(drafts.map((d) => d.key)).toEqual([`saved-${FEE_A.id}`]);
    });

    it('a parent with no charges gets an empty list', () => {
        expect(chargeDraftsFor(editOp(BUY_B), [editOp(BUY_B)], get)).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// applyChargeDrafts
// ---------------------------------------------------------------------------

describe('applyChargeDrafts — the form’s answer back onto the operations', () => {
    /** BUY_A with its two charges adopted, plus BUY_B with its FEE and the free FEE, untouched bystanders. */
    function start(): {ops: PendingOp[]; parent: PendingOp; drafts: ChargeDraft[]} {
        const ops = adoptCharges([editOp(BUY_A), editOp(FEE_A), editOp(TAX_A), editOp(BUY_B), editOp(FEE_B), editOp(FEE_FREE)], get);
        const parent = byTxId(ops, BUY_A.id);
        return {ops, parent, drafts: chargeDraftsFor(parent, ops, get)};
    }

    function edit(drafts: ChargeDraft[], key: string, patch: Partial<ChargeDraft>): ChargeDraft[] {
        return drafts.map((draft) => (draft.key === key ? {...draft, ...patch} : draft));
    }

    it('round trip: the drafts the form was given, handed back unchanged, change nothing', () => {
        const {ops, parent, drafts} = start();
        const deps = makeDeps();

        expect(applyChargeDrafts(parent, ops, drafts, deps)).toEqual(ops);
        expect(deps.newChargeOp).not.toHaveBeenCalled();
    });

    it('type, cash and note are applied to the charge’s operation', () => {
        const {ops, parent, drafts} = start();
        const next = edit(drafts, `saved-${TAX_A.id}`, {type: 'FEE', cash: {amount: '0.75', code: 'EUR'}, description: 'tax note changed'});

        const out = applyChargeDrafts(parent, ops, next, makeDeps());

        const tax = byTxId(out, TAX_A.id);
        expect(tax.fields).toMatchObject({type: 'FEE', cash: {amount: '0.75', code: 'EUR'}, description: 'tax note changed'});
        expect(tax).toMatchObject({chargeOf: parent.tempId, markedDelete: false});
        expect(tax.parentUnlink ?? false).toBe(false);
    });

    it('delete → the saved charge is marked for deletion', () => {
        const {ops, parent, drafts} = start();
        const out = applyChargeDrafts(parent, ops, edit(drafts, `saved-${FEE_A.id}`, {state: 'delete'}), makeDeps());
        expect(byTxId(out, FEE_A.id)).toMatchObject({markedDelete: true, chargeOf: parent.tempId});
    });

    it('unlink → parentUnlink, chargeOf kept, and what was typed with it is kept too', () => {
        const {ops, parent, drafts} = start();
        const out = applyChargeDrafts(parent, ops, edit(drafts, `saved-${FEE_A.id}`, {state: 'unlink', description: 'typed, then unlinked'}), makeDeps());

        const fee = byTxId(out, FEE_A.id);
        expect(fee).toMatchObject({parentUnlink: true, chargeOf: parent.tempId, markedDelete: false});
        expect(fee.fields.description, 'nothing typed is lost').toBe('typed, then unlinked');
    });

    it('linked → clears both a previous delete and a previous unlink', () => {
        const {ops: started, parent} = start();
        const ops = started.map((op) => {
            if (op.op === 'edit' && op.txId === FEE_A.id) return {...op, markedDelete: true};
            if (op.op === 'edit' && op.txId === TAX_A.id) return {...op, parentUnlink: true};
            return op;
        });
        const drafts = chargeDraftsFor(parent, ops, get).map((draft) => ({...draft, state: 'linked' as const}));

        const out = applyChargeDrafts(parent, ops, drafts, makeDeps());

        expect(byTxId(out, FEE_A.id)).toMatchObject({op: 'edit', markedDelete: false});
        expect(byTxId(out, TAX_A.id).parentUnlink ?? false).toBe(false);
        expect(byTxId(out, TAX_A.id).chargeOf).toBe(parent.tempId);
    });

    it('a new draft → newChargeOp, and the create it returns is owned by the parent and follows it', () => {
        const {ops, parent, drafts} = start();
        const deps = makeDeps();
        const added = newDraft('new-1', 'FEE', '2', 'fee typed in the form');

        const out = applyChargeDrafts(parent, ops, [...drafts, added], deps);

        expect(deps.newChargeOp).toHaveBeenCalledTimes(1);
        expect(deps.newChargeOp.mock.calls[0][0]).toMatchObject({key: 'new-1', type: 'FEE', description: 'fee typed in the form'});
        expect(deps.newChargeOp.mock.calls[0][1].tempId).toBe(parent.tempId);
        expect(out).toHaveLength(ops.length + 1);
        const created = out.filter((op) => op.op === 'create');
        expect(created).toHaveLength(1);
        expect(created[0]).toMatchObject({chargeOf: parent.tempId, followsParent: true});
        expect(created[0].fields).toMatchObject({type: 'FEE', cash: {amount: '2', code: 'EUR'}, description: 'fee typed in the form'});
    });

    it('a new charge already in the Bulk (key op-<tempId>): its values applied, no second create; delete → it leaves', () => {
        const {ops: started, parent} = start();
        const ops = [...started, createOp('n-fee', {...fieldsOf(FEE_A), description: 'first'}, {chargeOf: parent.tempId, followsParent: true})];
        const drafts = chargeDraftsFor(parent, ops, get);
        const deps = makeDeps();

        const changed = applyChargeDrafts(parent, ops, edit(drafts, 'op-n-fee', {description: 'second', cash: {amount: '7', code: 'EUR'}}), deps);
        expect(byTempId(changed, 'n-fee').fields).toMatchObject({description: 'second', cash: {amount: '7', code: 'EUR'}});
        expect(byTempId(changed, 'n-fee')).toMatchObject({chargeOf: parent.tempId, followsParent: true});
        expect(changed).toHaveLength(ops.length);

        const removed = applyChargeDrafts(parent, ops, edit(drafts, 'op-n-fee', {state: 'delete'}), deps);
        expect(
            removed.some((op) => op.tempId === 'n-fee'),
            'a create the user deleted leaves the Bulk',
        ).toBe(false);
        expect(removed).toHaveLength(ops.length - 1);
        expect(deps.newChargeOp).not.toHaveBeenCalled();
    });

    it('linkNew of a saved charge not in the Bulk: its operation is added from the store, owned by the parent', () => {
        const {ops, parent, drafts} = start();
        const ops2 = ops.filter((op) => !(op.op === 'edit' && op.txId === FEE_FREE.id));
        const deps = makeDeps();
        const picked = chargeFromPicked(FEE_FREE);
        if (!picked) throw new Error('premise: FEE_FREE is a charge');

        const out = applyChargeDrafts(parent, ops2, [...drafts, picked], deps);

        expect(deps.editOpFromTx).toHaveBeenCalledWith(FEE_FREE.id);
        expect(byTxId(out, FEE_FREE.id)).toMatchObject({chargeOf: parent.tempId, markedDelete: false});
        expect(out).toHaveLength(ops2.length + 1);
    });

    it('linkNew of a saved charge already in the Bulk: the same operation, re-owned, no second one', () => {
        const {ops, parent, drafts} = start();
        const deps = makeDeps();
        const picked = chargeFromPicked(FEE_B);
        if (!picked) throw new Error('premise: FEE_B is a charge');

        const out = applyChargeDrafts(parent, ops, [...drafts, {...picked, description: 'moved here'}], deps);

        expect(deps.editOpFromTx).not.toHaveBeenCalled();
        expect(byTxId(out, FEE_B.id)).toMatchObject({chargeOf: parent.tempId, tempId: `t-${FEE_B.id}`});
        expect(byTxId(out, FEE_B.id).fields.description).toBe('moved here');
        expect(out).toHaveLength(ops.length);
    });

    it('the other operations come out exactly as they went in, and the input is not mutated', () => {
        const {ops, parent, drafts} = start();
        const before = snapshot(ops);

        const out = applyChargeDrafts(parent, ops, edit(edit(drafts, `saved-${FEE_A.id}`, {state: 'unlink'}), `saved-${TAX_A.id}`, {state: 'delete'}), makeDeps());

        for (const id of [BUY_A.id, BUY_B.id, FEE_B.id, FEE_FREE.id]) expect(byTxId(out, id), `#${id}`).toEqual(byTxId(before, id));
        expect(ops).toEqual(before);
    });

    it('applied twice (the form opened again on the same parent), a new charge is still one create', () => {
        const {ops, parent, drafts} = start();
        const deps = makeDeps();
        const once = applyChargeDrafts(parent, ops, [...drafts, newDraft('new-1', 'TAX', '1', 'once')], deps);
        const parentAgain = byTempId(once, parent.tempId);

        const twice = applyChargeDrafts(parentAgain, once, chargeDraftsFor(parentAgain, once, get), deps);

        expect(twice.filter((op) => op.op === 'create')).toHaveLength(1);
        expect(twice).toEqual(once);
    });
});

// ---------------------------------------------------------------------------
// chargeParentFields / parentNeedsRef
// ---------------------------------------------------------------------------

describe('chargeParentFields — how a charge’s payload names its parent', () => {
    const newBuy = createOp('new-buy', newBuyFields());

    it('nothing for an operation that is no charge of the Bulk', () => {
        const ops = [editOp(BUY_A), editOp(FEE_FREE)];
        expect(chargeParentFields(ops[0], ops, get)).toBeNull();
        expect(chargeParentFields(ops[1], ops, get)).toBeNull();
    });

    it('parentUnlink → parent_transaction_id 0, whatever chargeOf says', () => {
        const ops = [editOp(BUY_A, {markedDelete: true}), editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true})];
        expect(chargeParentFields(ops[1], ops, get)).toEqual({parent_transaction_id: 0});
    });

    it('a create under a new parent → parent_ref = the parent’s tempId', () => {
        const ops = [newBuy, createOp('n-fee', fieldsOf(FEE_A), {chargeOf: 'new-buy', followsParent: true})];
        expect(chargeParentFields(ops[1], ops, get)).toEqual({parent_ref: 'new-buy'});
    });

    it('a saved charge linked to a new parent (linkNew) → parent_ref too (§11.5)', () => {
        const ops = [newBuy, editOp(FEE_FREE, {chargeOf: 'new-buy'})];
        expect(chargeParentFields(ops[1], ops, get)).toEqual({parent_ref: 'new-buy'});
    });

    it('a create under a saved parent → parent_transaction_id = the parent’s id', () => {
        const ops = [editOp(BUY_A), createOp('n-fee', fieldsOf(FEE_A), {chargeOf: 't-501', followsParent: true})];
        expect(chargeParentFields(ops[1], ops, get)).toEqual({parent_transaction_id: BUY_A.id});
    });

    it('a saved charge under its own saved parent → nothing: the link is already saved', () => {
        const ops = adoptCharges([editOp(BUY_A), editOp(FEE_A)], get);
        expect(chargeParentFields(byTxId(ops, FEE_A.id), ops, get)).toBeNull();
    });

    it('a saved charge moved under another saved parent, or a free one linked → parent_transaction_id = the new parent', () => {
        const ops = [editOp(BUY_A), editOp(FEE_B, {chargeOf: 't-501'}), editOp(FEE_FREE, {chargeOf: 't-501'})];
        expect(chargeParentFields(ops[1], ops, get)).toEqual({parent_transaction_id: BUY_A.id});
        expect(chargeParentFields(ops[2], ops, get)).toEqual({parent_transaction_id: BUY_A.id});
    });

    it('parentLinkId (a saved parent absent from the Bulk) → parent_transaction_id = that id', () => {
        const ops = [editOp(FEE_FREE, {parentLinkId: BUY_B.id})];
        expect(chargeParentFields(ops[0], ops, get)).toEqual({parent_transaction_id: BUY_B.id});
    });
});

describe('parentNeedsRef — which creates carry a ref', () => {
    it('a create named by a charge’s chargeOf needs one; a create nobody names, and a saved parent, do not', () => {
        const ops = [createOp('new-buy', newBuyFields()), createOp('n-fee', fieldsOf(FEE_A), {chargeOf: 'new-buy'}), createOp('lonely', newBuyFields()), editOp(BUY_A), editOp(FEE_A, {chargeOf: 't-501'})];

        expect(parentNeedsRef(ops[0], ops)).toBe(true);
        expect(parentNeedsRef(ops[2], ops)).toBe(false);
        expect(parentNeedsRef(ops[3], ops)).toBe(false);
        expect(parentNeedsRef(ops[1], ops), 'the charge itself is no parent').toBe(false);
    });

    it('a new parent named only by a saved charge linked to it (linkNew) needs one too', () => {
        const ops = [createOp('new-buy', newBuyFields()), editOp(FEE_FREE, {chargeOf: 'new-buy'})];
        expect(parentNeedsRef(ops[0], ops)).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// The invariants of the payload
// ---------------------------------------------------------------------------

type Item = Record<string, unknown>;
type Payload = {creates: Item[]; updates: Item[]; deletes: number[]};

/**
 * A payload of the operations, reduced to what the charges decide: a create per create op (`ref` when
 * `parentNeedsRef`, plus `chargeParentFields`), a delete per marked saved row, an update per saved row whose note
 * changed or whose parent fields are not null. `_op` names the operation an item came from, for the invariants.
 */
function payloadOf(ops: readonly PendingOp[]): Payload {
    const payload: Payload = {creates: [], updates: [], deletes: []};
    for (const op of ops) {
        const link = chargeParentFields(op, [...ops], get) ?? {};
        if (op.op === 'create') {
            payload.creates.push({_op: op.tempId, type: op.fields.type, ...(parentNeedsRef(op, [...ops]) ? {ref: op.tempId} : {}), ...link});
            continue;
        }
        if (op.markedDelete) {
            payload.deletes.push(op.txId);
            continue;
        }
        const saved = get(op.txId);
        const note = saved && (saved.description ?? '') !== op.fields.description ? {description: op.fields.description} : {};
        const update = {id: op.txId, ...note, ...link};
        if (Object.keys(update).length > 1) payload.updates.push(update);
    }
    return payload;
}

/** Every broken invariant of a payload, by name; `[]` when it holds them all. */
function invariantViolations(payload: Payload, ops: readonly PendingOp[]): string[] {
    const out: string[] = [];
    // 1. every id once across updates and deletes
    const ids = [...payload.updates.map((u) => u.id as number), ...payload.deletes];
    const dup = ids.filter((id, i) => ids.indexOf(id) !== i);
    if (dup.length > 0) out.push(`1 ids twice: ${[...new Set(dup)].join(', ')}`);
    // 2. a deleted parent: each of its saved charges in the Bulk is deleted or unlinked
    for (const deletedId of payload.deletes) {
        const parentOp = ops.find((op) => op.op === 'edit' && op.txId === deletedId);
        const charges = ops.filter((op) => op.op === 'edit' && (get(op.txId)?.parent_transaction_id === deletedId || (parentOp && op.chargeOf === parentOp.tempId)));
        for (const charge of charges) {
            if (charge.op !== 'edit') continue;
            const unlinked = payload.updates.some((u) => u.id === charge.txId && u.parent_transaction_id === 0);
            if (!payload.deletes.includes(charge.txId) && !unlinked) out.push(`2 charge #${charge.txId} of deleted #${deletedId} kept linked`);
        }
    }
    // 3. every parent_ref names a ref of the same batch
    const refs = new Set(payload.creates.map((c) => c.ref).filter((r): r is string => typeof r === 'string'));
    for (const item of [...payload.creates, ...payload.updates]) {
        if (item.parent_ref !== undefined && !refs.has(item.parent_ref as string)) out.push(`3 parent_ref ${String(item.parent_ref)} names no ref`);
        if (item.parent_ref !== undefined && item.parent_transaction_id !== undefined) out.push(`3 both parent_ref and parent_transaction_id on one item`);
    }
    // 4. no charge kept twice: one item per operation, one operation per saved row
    const sources = payload.creates.map((c) => c._op);
    if (new Set(sources).size !== sources.length) out.push('4 one create twice');
    const txIds = ops.filter((op) => op.op === 'edit').map((op) => (op.op === 'edit' ? op.txId : 0));
    if (new Set(txIds).size !== txIds.length) out.push('4 one saved row held by two operations');
    // 5. every chargeOf names an operation present
    for (const op of ops) if (op.chargeOf !== undefined && !ops.some((o) => o.tempId === op.chargeOf)) out.push(`5 dangling chargeOf ${op.chargeOf}`);
    return out;
}

describe('the five invariants of the payload, on operations the module produced', () => {
    const deps = () => makeDeps();
    function edit(drafts: ChargeDraft[], key: string, patch: Partial<ChargeDraft>): ChargeDraft[] {
        return drafts.map((draft) => (draft.key === key ? {...draft, ...patch} : draft));
    }

    /** S1 — delete a saved parent: its FEE kept (unlink), its TAX deleted. */
    function deleteParentKeepFee(): PendingOp[] {
        const ops = adoptCharges([editOp(BUY_A, {markedDelete: true}), editOp(FEE_A), editOp(TAX_A)], get);
        const parent = byTxId(ops, BUY_A.id);
        const drafts = edit(edit(chargeDraftsFor(parent, ops, get), `saved-${FEE_A.id}`, {state: 'unlink'}), `saved-${TAX_A.id}`, {state: 'delete'});
        return applyChargeDrafts(parent, ops, drafts, deps());
    }

    /** S2 — a new parent with a new FEE, and a free saved FEE linked to it. */
    function newParentNewFeeAndLinked(): PendingOp[] {
        const ops = [createOp('new-buy', newBuyFields())];
        const picked = chargeFromPicked(FEE_FREE);
        if (!picked) throw new Error('premise: FEE_FREE is a charge');
        return applyChargeDrafts(ops[0], ops, [newDraft('new-1', 'FEE', '2', 'new fee'), picked], deps());
    }

    /** S3 — a saved parent: a new FEE, the TAX’s note changed, the FEE unlinked, another parent’s FEE moved here. */
    function savedParentMixed(): PendingOp[] {
        const ops = adoptCharges([editOp(BUY_A), editOp(FEE_A), editOp(TAX_A), editOp(BUY_B), editOp(FEE_B), editOp(PAIR_FROM, {link_uuid: 'L'}), editOp(PAIR_TO, {pairedWith: 't-530', link_uuid: 'L'})], get);
        const parent = byTxId(ops, BUY_A.id);
        const picked = chargeFromPicked(FEE_B);
        if (!picked) throw new Error('premise: FEE_B is a charge');
        const drafts = [...edit(edit(chargeDraftsFor(parent, ops, get), `saved-${FEE_A.id}`, {state: 'unlink'}), `saved-${TAX_A.id}`, {description: 'tax note changed'}), newDraft('new-1', 'FEE', '1', 'new fee'), picked];
        return applyChargeDrafts(parent, ops, drafts, deps());
    }

    /** S4 — S3, then its parent form opened and applied again, then the parent reset (its tempId regenerated). */
    function savedParentAppliedTwiceThenReset(): PendingOp[] {
        const once = savedParentMixed();
        const parent = byTxId(once, BUY_A.id);
        const twice = applyChargeDrafts(parent, once, chargeDraftsFor(parent, once, get), deps());
        const reset = twice.map((op) => (op.tempId === parent.tempId ? {...editOp(BUY_A), tempId: 'reset-501'} : op));
        return remapChargeOf(reset, parent.tempId, 'reset-501');
    }

    it.each([
        ['S1 delete a parent, keep its FEE, delete its TAX', deleteParentKeepFee],
        ['S2 a new parent, a new FEE, a saved FEE linked to it', newParentNewFeeAndLinked],
        ['S3 a saved parent: new FEE, TAX note, FEE unlinked, a FEE moved in', savedParentMixed],
        ['S4 S3 applied twice and reset', savedParentAppliedTwiceThenReset],
    ] as const)('%s: the payload holds all five', (_label, build) => {
        const ops = build();
        expect(invariantViolations(payloadOf(ops), ops)).toEqual([]);
    });

    it('S1 payload: the parent and the TAX deleted, the FEE unlinked with parent_transaction_id 0, nothing else', () => {
        const payload = payloadOf(deleteParentKeepFee());
        expect(payload.creates).toEqual([]);
        expect([...payload.deletes].sort()).toEqual([BUY_A.id, TAX_A.id]);
        expect(payload.updates).toEqual([{id: FEE_A.id, parent_transaction_id: 0}]);
    });

    it('S2 payload: the new parent carries a ref, the new FEE and the linked saved FEE name it by parent_ref', () => {
        const payload = payloadOf(newParentNewFeeAndLinked());
        const parent = payload.creates.find((c) => c.type === 'BUY');
        const fee = payload.creates.find((c) => c.type === 'FEE');
        expect(typeof parent?.ref).toBe('string');
        expect(fee).toMatchObject({parent_ref: parent?.ref});
        expect(fee?.parent_transaction_id).toBeUndefined();
        expect(payload.updates).toEqual([{id: FEE_FREE.id, parent_ref: parent?.ref}]);
    });

    it('S3 payload: one create under the saved parent, the TAX note, the FEE unlinked, the moved FEE relinked', () => {
        const payload = payloadOf(savedParentMixed());
        expect(payload.creates).toEqual([expect.objectContaining({type: 'FEE', parent_transaction_id: BUY_A.id})]);
        expect(payload.updates).toEqual(
            expect.arrayContaining([
                {id: FEE_A.id, parent_transaction_id: 0},
                {id: TAX_A.id, description: 'tax note changed'},
                {id: FEE_B.id, parent_transaction_id: BUY_A.id},
            ]),
        );
        expect(payload.updates).toHaveLength(3);
        expect(payload.deletes).toEqual([]);
    });

    describe('the checker bites: one bad payload per invariant', () => {
        // Hand-built, so the checker's own proof does not depend on the module under test.
        const ops = [editOp(BUY_A, {markedDelete: true}), editOp(FEE_A, {chargeOf: 't-501'}), editOp(TAX_A, {chargeOf: 't-501'})];

        it.each([
            ['1 an id twice', {creates: [], updates: [{id: FEE_A.id, parent_transaction_id: 0}], deletes: [BUY_A.id, TAX_A.id, FEE_A.id]}, ops, '1 '],
            ['2 a charge of a deleted parent kept linked', {creates: [], updates: [], deletes: [BUY_A.id, TAX_A.id]}, ops, '2 '],
            ['3 a parent_ref naming no ref', {creates: [{_op: 'x', type: 'FEE', parent_ref: 'ghost'}], updates: [], deletes: []}, [], '3 '],
            [
                '3 parent_ref and parent_transaction_id together',
                {
                    creates: [
                        {_op: 'p', type: 'BUY', ref: 'p'},
                        {_op: 'x', type: 'FEE', parent_ref: 'p', parent_transaction_id: 501},
                    ],
                    updates: [],
                    deletes: [],
                },
                [],
                '3 ',
            ],
            [
                '4 one create twice',
                {
                    creates: [
                        {_op: 'x', type: 'FEE'},
                        {_op: 'x', type: 'FEE'},
                    ],
                    updates: [],
                    deletes: [],
                },
                [],
                '4 ',
            ],
            ['4 one saved row held twice', {creates: [], updates: [], deletes: []}, [editOp(FEE_A), editOp(FEE_A, {tempId: 'again'})], '4 '],
            ['5 a dangling chargeOf', {creates: [], updates: [], deletes: []}, [editOp(FEE_A, {chargeOf: 'gone'})], '5 '],
        ] as const)('%s', (_label, payload, opsOf, prefix) => {
            const violations = invariantViolations(payload as unknown as Payload, opsOf as readonly PendingOp[]);
            expect(
                violations.some((v) => v.startsWith(prefix)),
                violations.join(' | ') || 'no violation found',
            ).toBe(true);
        });
    });
});

// ---------------------------------------------------------------------------
// F7-c1 — foldBulkCharges and rowAnchor (contract 66-F7 §13 F7-c1, corrected by §14)
// ---------------------------------------------------------------------------

type FoldBulkCharges = (top: readonly PendingOp[], ops: readonly PendingOp[], expanded: ReadonlySet<string>) => PendingOp[];
type RowAnchor = (op: PendingOp, ops: readonly PendingOp[], expanded: ReadonlySet<string>) => string;

/** `foldBulkCharges`, or a failure naming it while `bulkCharges.ts` does not export it yet. */
function foldBulkCharges(top: readonly PendingOp[], ops: readonly PendingOp[], expanded: ReadonlySet<string>): PendingOp[] {
    const fn = (bulkChargesModule as unknown as {foldBulkCharges?: FoldBulkCharges}).foldBulkCharges;
    expect(fn, 'bulkCharges exports foldBulkCharges').toBeTypeOf('function');
    return fn!(top, ops, expanded);
}

/** `rowAnchor`, or a failure naming it while `bulkCharges.ts` does not export it yet. */
function rowAnchor(op: PendingOp, ops: readonly PendingOp[], expanded: ReadonlySet<string>): string {
    const fn = (bulkChargesModule as unknown as {rowAnchor?: RowAnchor}).rowAnchor;
    expect(fn, 'bulkCharges exports rowAnchor').toBeTypeOf('function');
    return fn!(op, ops, expanded);
}

const tempIds = (ops: readonly PendingOp[]): string[] => ops.map((op) => op.tempId);

describe('foldBulkCharges — the grid’s rows: top-level rows, each open parent followed by its charges', () => {
    // The ops in the order the Bulk holds them: the TAX before the FEE, so «in ops order» is not «in id order».
    const buyA = editOp(BUY_A);
    const taxA = editOp(TAX_A, {chargeOf: 't-501'});
    const feeA = editOp(FEE_A, {chargeOf: 't-501'});
    const buyB = editOp(BUY_B);
    const feeB = editOp(FEE_B, {chargeOf: 't-511'});
    const free = editOp(FEE_FREE);
    const ops = [taxA, buyA, free, feeB, buyB, feeA];
    /** The top-level rows as the Bulk sorts them (here BUY_B first, as a descending date sort would). */
    const top = [buyB, free, buyA];

    it('nothing open: the top-level rows, unchanged and in their order; no charge', () => {
        expect(tempIds(foldBulkCharges(top, ops, new Set()))).toEqual(['t-511', 't-520', 't-501']);
    });

    it('an open parent is followed by its charges, in the order of the operations, wherever the parent sits', () => {
        expect(tempIds(foldBulkCharges(top, ops, new Set(['t-501'])))).toEqual(['t-511', 't-520', 't-501', 't-503', 't-502']);
    });

    it('only the open parents unfold: BUY_B open, BUY_A closed', () => {
        expect(tempIds(foldBulkCharges(top, ops, new Set(['t-511'])))).toEqual(['t-511', 't-512', 't-520', 't-501']);
    });

    it('both open: each group right after its own parent', () => {
        expect(tempIds(foldBulkCharges(top, ops, new Set(['t-501', 't-511'])))).toEqual(['t-511', 't-512', 't-520', 't-501', 't-503', 't-502']);
    });

    it('a charge unlinked from a parent that stays is not under it: it is not inserted, even with the parent open (it is a top-level row of its own)', () => {
        const unlinked = editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true});
        const opsU = [buyA, taxA, unlinked];
        const topU = [buyA, unlinked];
        expect(tempIds(foldBulkCharges(topU, opsU, new Set(['t-501'])))).toEqual(['t-501', 't-503', 't-502']);
        expect(
            foldBulkCharges(topU, opsU, new Set(['t-501'])).filter((op) => op.tempId === 't-502'),
            'the unlinked FEE appears once, where the top-level rows put it',
        ).toHaveLength(1);
    });

    it('under a parent marked for deletion a «scollega» charge is still under it: inserted, as a «del» one is', () => {
        const deleted = editOp(BUY_A, {markedDelete: true});
        const opsD = [deleted, editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true}), editOp(TAX_A, {chargeOf: 't-501', markedDelete: true})];
        expect(tempIds(foldBulkCharges([deleted], opsD, new Set(['t-501'])))).toEqual(['t-501', 't-502', 't-503']);
    });

    it('a new charge of a new parent unfolds the same way', () => {
        const newBuy = createOp('new-buy', newBuyFields());
        const newFee = createOp('new-fee', fieldsOf(FEE_A), {chargeOf: 'new-buy', followsParent: true});
        expect(tempIds(foldBulkCharges([newBuy], [newBuy, newFee], new Set(['new-buy'])))).toEqual(['new-buy', 'new-fee']);
    });

    it('an open tempId that names no top-level row inserts nothing; a pair’s hidden half is never inserted', () => {
        const from = editOp(PAIR_FROM);
        const to = editOp(PAIR_TO, {pairedWith: 't-530', tempId: 't-531'});
        expect(tempIds(foldBulkCharges([from], [from, to], new Set(['t-530', 'nobody'])))).toEqual(['t-530']);
    });

    it('returns a new array and mutates neither input', () => {
        const topCopy = snapshot(top);
        const opsCopy = snapshot(ops);
        const out = foldBulkCharges(top, ops, new Set(['t-501']));
        expect(out).not.toBe(top);
        expect(top).toEqual(topCopy);
        expect(ops).toEqual(opsCopy);
    });
});

describe('rowAnchor — the row on screen that stands for an operation', () => {
    const buyA = editOp(BUY_A);
    const feeA = editOp(FEE_A, {chargeOf: 't-501'});
    const ops = [buyA, feeA];

    it('a charge under a closed parent → the parent’s row', () => {
        expect(rowAnchor(feeA, ops, new Set())).toBe('t-501');
    });

    it('a charge under an open parent → its own row', () => {
        expect(rowAnchor(feeA, ops, new Set(['t-501']))).toBe('t-502');
    });

    it('the parent itself → its own row, open or closed', () => {
        expect(rowAnchor(buyA, ops, new Set())).toBe('t-501');
        expect(rowAnchor(buyA, ops, new Set(['t-501']))).toBe('t-501');
    });

    it('a charge unlinked from a parent that stays is a top-level row: its own, whether the parent is open or not', () => {
        const unlinked = editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true});
        expect(rowAnchor(unlinked, [buyA, unlinked], new Set())).toBe('t-502');
        expect(rowAnchor(unlinked, [buyA, unlinked], new Set(['t-501']))).toBe('t-502');
    });

    it('a «scollega» charge under a parent marked for deletion is under it: the parent while closed, itself while open', () => {
        const deleted = editOp(BUY_A, {markedDelete: true});
        const kept = editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true});
        expect(rowAnchor(kept, [deleted, kept], new Set())).toBe('t-501');
        expect(rowAnchor(kept, [deleted, kept], new Set(['t-501']))).toBe('t-502');
    });

    it('a pair’s hidden half → its visible half (pairedWith), as before', () => {
        const from = editOp(PAIR_FROM);
        const to = editOp(PAIR_TO, {pairedWith: 't-530', tempId: 't-531'});
        expect(rowAnchor(to, [from, to], new Set())).toBe('t-530');
    });

    it('a row of its own → itself; a chargeOf naming nobody present → itself', () => {
        const free = editOp(FEE_FREE);
        const dangling = editOp(FEE_B, {chargeOf: 'gone'});
        expect(rowAnchor(free, [free], new Set())).toBe('t-520');
        expect(rowAnchor(dangling, [dangling], new Set())).toBe('t-512');
    });
});

// ---------------------------------------------------------------------------
// F7-c2 — linkedChargesOf, planBulkDelete, applyDeleteChoice (contract 66-F7 §17, corrected by §18)
// ---------------------------------------------------------------------------

/**
 * The shapes pinned here (the implementer follows them):
 *
 *   linkedChargesOf(parent, ops): PendingOp[]
 *       the operations with `chargeOf` = parent.tempId for which `isUnderParent` holds, not `markedDelete`, without
 *       `parentUnlink`; new ones included; in the order of `ops`.
 *
 *   planBulkDelete(ops, selectedTempIds, unread): BulkDeletePlan
 *       unread(op) → 'loading' | 'failed' | null, asked only of a saved row about to go «del»;
 *       BulkDeletePlan = {
 *           toggles: {tempId: string; deleted: boolean}[];  // saved selected rows that flip («del» ↔ restored)
 *           removals: string[];                              // new selected rows, which leave the Bulk
 *           needsChoice: string[];                           // parents going «del» that have linked charges
 *           waiting: string[];                               // parents going «del» whose read is in flight
 *           skipped: string[];                               // parents going «del» whose read failed
 *           counts: {keep: number; all: number};
 *       }
 *       Every decision is taken on the state before any of them. A waiting or skipped parent is in no toggle.
 *       counts, as the page's panel counts its intent (66 F6): `keep` = the linked charges of the parents in
 *       needsChoice (they survive «Keep»); `all` = every row «Delete all» deletes or removes: those parents, their
 *       linked charges, and the other selected rows going «del» or leaving. A restore counts in neither.
 *
 *   applyDeleteChoice(ops, plan, choice, get): PendingOp[]
 *       `get` is the store's read (`txStoreGet`): a saved charge linked here to a parent that is not its saved one
 *       (`linkNew`) is told apart by its saved `parent_transaction_id`. `choice` is ignored when needsChoice is empty.
 *       - toggles and removals applied;
 *       - «keep»: each parent «del»; its saved linked charges `parentUnlink` + `byParentChoice`; its new ones on their
 *         own (no `chargeOf`, no `followsParent`) with the broker, asset and date they followed; a `linkNew` one only
 *         loses `chargeOf` (it never had this parent saved: nothing to send);
 *       - «all»: each parent «del»; its saved linked charges `markedDelete` + `byParentChoice` (a `linkNew` too); its
 *         new ones leave the Bulk;
 *       - a parent restored: its charges marked `byParentChoice` get back as they were (no `markedDelete`, no
 *         `parentUnlink`, no `byParentChoice`); a charge unlinked by hand stays unlinked.
 *
 * RED until `bulkCharges.ts` exports them and `PendingOp` gains `byParentChoice?: true`.
 */
type Unread = 'loading' | 'failed' | null;
type BulkDeletePlan = {
    toggles: {tempId: string; deleted: boolean}[];
    removals: string[];
    needsChoice: string[];
    waiting: string[];
    skipped: string[];
    counts: {keep: number; all: number};
};
type LinkedChargesOf = (parent: PendingOp, ops: readonly PendingOp[]) => PendingOp[];
type PlanBulkDelete = (ops: readonly PendingOp[], selectedTempIds: readonly string[], unread: (op: PendingOp) => Unread) => BulkDeletePlan;
type ApplyDeleteChoice = (ops: readonly PendingOp[], plan: BulkDeletePlan, choice: 'keep' | 'all', get: (id: number) => TXReadItem | undefined) => PendingOp[];

function c2<T>(name: string): T {
    const fn = (bulkChargesModule as unknown as Record<string, unknown>)[name];
    expect(fn, `bulkCharges exports ${name}`).toBeTypeOf('function');
    return fn as T;
}
const linkedChargesOf: LinkedChargesOf = (parent, ops) => c2<LinkedChargesOf>('linkedChargesOf')(parent, ops);
const planBulkDelete: PlanBulkDelete = (ops, selected, unread) => c2<PlanBulkDelete>('planBulkDelete')(ops, selected, unread);
const applyDeleteChoice: ApplyDeleteChoice = (ops, plan, choice, g) => c2<ApplyDeleteChoice>('applyDeleteChoice')(ops, plan, choice, g);
const allRead = (): Unread => null;
type WithChoice = PendingOp & {byParentChoice?: true};

describe('linkedChargesOf — the charges still linked to a parent', () => {
    it('saved and new charges under the parent, in ops order; not «del», not unlinked, not another parent’s', () => {
        const ops = [
            editOp(BUY_A),
            editOp(TAX_A, {chargeOf: 't-501'}),
            editOp(FEE_A, {chargeOf: 't-501', markedDelete: true}),
            createOp('n-fee', fieldsOf(FEE_A), {chargeOf: 't-501', followsParent: true}),
            editOp(FEE_FREE, {chargeOf: 't-501', parentUnlink: true}),
            editOp(BUY_B),
            editOp(FEE_B, {chargeOf: 't-511'}),
        ];
        expect(tempIds(linkedChargesOf(ops[0], ops))).toEqual(['t-503', 'n-fee']);
        expect(tempIds(linkedChargesOf(ops[5], ops))).toEqual(['t-512']);
    });

    it('under a parent already «del» a «scollega» charge is under it but not linked: excluded', () => {
        const ops = [editOp(BUY_A, {markedDelete: true}), editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true}), editOp(TAX_A, {chargeOf: 't-501'})];
        expect(tempIds(linkedChargesOf(ops[0], ops))).toEqual(['t-503']);
    });

    it('a row with no charge: none', () => {
        const ops = [editOp(BUY_A), editOp(FEE_FREE)];
        expect(linkedChargesOf(ops[0], ops)).toEqual([]);
    });
});

describe('planBulkDelete — one plan for «Delete» and «Delete selected»', () => {
    const buyA = editOp(BUY_A);
    const feeA = editOp(FEE_A, {chargeOf: 't-501'});
    const taxA = editOp(TAX_A, {chargeOf: 't-501'});
    const free = editOp(FEE_FREE);

    it('a single parent with linked charges asks for a choice: keep = 2 charges, all = parent + 2', () => {
        const ops = [buyA, feeA, taxA, free];
        const plan = planBulkDelete(ops, ['t-501'], allRead);
        expect(plan.needsChoice).toEqual(['t-501']);
        expect(plan.waiting).toEqual([]);
        expect(plan.skipped).toEqual([]);
        expect(plan.counts).toEqual({keep: 2, all: 3});
    });

    it('a row with no linked charge needs no choice: it toggles', () => {
        const plan = planBulkDelete([buyA, free], ['t-520'], allRead);
        expect(plan.needsChoice).toEqual([]);
        expect(plan.toggles).toEqual([{tempId: 't-520', deleted: true}]);
    });

    it('a selected row already «del» toggles back without asking, and counts in nothing', () => {
        const ops = [editOp(BUY_A, {markedDelete: true}), editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true, byParentChoice: true} as never), free];
        const plan = planBulkDelete(ops, ['t-501'], allRead);
        expect(plan.needsChoice).toEqual([]);
        expect(plan.toggles).toEqual([{tempId: 't-501', deleted: false}]);
        expect(plan.counts).toEqual({keep: 0, all: 0});
    });

    it('a selection mixing a parent, an unrelated row and a new row: one choice; all counts every row that goes', () => {
        const fresh = createOp('n-dep', {...fieldsOf(FEE_FREE), type: 'DEPOSIT' as DraftFields['type']});
        const ops = [buyA, feeA, taxA, free, fresh];
        const plan = planBulkDelete(ops, ['t-501', 't-520', 'n-dep'], allRead);
        expect(plan.needsChoice).toEqual(['t-501']);
        expect(plan.toggles).toContainEqual({tempId: 't-520', deleted: true});
        expect(plan.removals).toEqual(['n-dep']);
        expect(plan.counts, 'keep: the 2 charges; all: BUY + 2 charges + the free FEE + the new row').toEqual({keep: 2, all: 5});
    });

    it('a parent whose read is in flight waits; one whose read failed is skipped; neither toggles', () => {
        const ops = [buyA, feeA, editOp(BUY_B), free];
        const unread = (op: PendingOp): Unread => (op.tempId === 't-501' ? 'loading' : op.tempId === 't-511' ? 'failed' : null);
        const plan = planBulkDelete(ops, ['t-501', 't-511', 't-520'], unread);
        expect(plan.waiting).toEqual(['t-501']);
        expect(plan.skipped).toEqual(['t-511']);
        expect(plan.needsChoice).toEqual([]);
        expect(plan.toggles).toEqual([{tempId: 't-520', deleted: true}]);
    });

    it('unread is asked only of rows going «del»: a parent being restored never waits', () => {
        const ops = [editOp(BUY_A, {markedDelete: true}), free];
        const plan = planBulkDelete(ops, ['t-501'], () => 'loading');
        expect(plan.waiting).toEqual([]);
        expect(plan.toggles).toEqual([{tempId: 't-501', deleted: false}]);
    });

    it('a top-level charge of the parent (unlinked by hand), selected with it: its own toggle, outside the parent’s choice', () => {
        const unlinked = editOp(TAX_A, {chargeOf: 't-501', parentUnlink: true});
        const ops = [buyA, feeA, unlinked];
        const plan = planBulkDelete(ops, ['t-501', 't-503'], allRead);
        expect(plan.needsChoice).toEqual(['t-501']);
        expect(plan.toggles).toContainEqual({tempId: 't-503', deleted: true});
        expect(plan.counts, 'keep: the FEE alone; all: BUY + FEE + the TAX deleted anyway').toEqual({keep: 1, all: 3});
    });
});

describe('applyDeleteChoice — the choice onto the operations', () => {
    const buyA = editOp(BUY_A);
    const feeA = editOp(FEE_A, {chargeOf: 't-501'});
    const taxA = editOp(TAX_A, {chargeOf: 't-501'});

    it('«keep»: parent «del»; saved charges unlinked, marked byParentChoice, still under the parent', () => {
        const ops = [buyA, feeA, taxA];
        const out = applyDeleteChoice(ops, planBulkDelete(ops, ['t-501'], allRead), 'keep', get) as WithChoice[];
        expect(byTempId(out, 't-501')).toMatchObject({markedDelete: true});
        for (const id of ['t-502', 't-503']) {
            expect(byTempId(out, id), id).toMatchObject({chargeOf: 't-501', parentUnlink: true, byParentChoice: true, markedDelete: false});
            expect(isUnderParent(byTempId(out, id), out), `${id} sits under the parent «del»`).toBe(true);
        }
    });

    it('«all»: parent «del»; saved charges «del», marked byParentChoice', () => {
        const ops = [buyA, feeA, taxA];
        const out = applyDeleteChoice(ops, planBulkDelete(ops, ['t-501'], allRead), 'all', get) as WithChoice[];
        expect(byTempId(out, 't-501')).toMatchObject({markedDelete: true});
        for (const id of ['t-502', 't-503']) expect(byTempId(out, id), id).toMatchObject({markedDelete: true, byParentChoice: true});
        expect(
            out.some((op) => op.tempId === 't-502' && op.parentUnlink),
            '«del» wins over «scollega»',
        ).toBe(false);
    });

    it('«keep» on a new charge: a row of its own, no chargeOf nor followsParent, with the broker, asset and date it followed', () => {
        const parent = editOp(BUY_A);
        const stale = createOp('n-fee', {...fieldsOf(FEE_A), date: '2025-01-01', broker_id: 1, asset_id: null}, {chargeOf: 't-501', followsParent: true});
        const ops = [parent, stale];
        const out = applyDeleteChoice(ops, planBulkDelete(ops, ['t-501'], allRead), 'keep', get);
        const kept = byTempId(out, 'n-fee');
        expect(kept.chargeOf, 'on its own').toBeUndefined();
        expect(kept.followsParent, 'no longer follows').toBeUndefined();
        expect({broker_id: kept.fields.broker_id, asset_id: kept.fields.asset_id, date: kept.fields.date}, 'the values it followed, frozen').toEqual({broker_id: parent.fields.broker_id, asset_id: parent.fields.asset_id, date: parent.fields.date});
    });

    it('«all» on a new charge: it leaves the Bulk', () => {
        const ops = [buyA, createOp('n-fee', fieldsOf(FEE_A), {chargeOf: 't-501', followsParent: true})];
        const out = applyDeleteChoice(ops, planBulkDelete(ops, ['t-501'], allRead), 'all', get);
        expect(out.some((op) => op.tempId === 'n-fee')).toBe(false);
    });

    it('a linkNew charge (linked here, saved under no parent): «keep» only drops the local link; «all» marks it «del»', () => {
        const linked = editOp(FEE_FREE, {chargeOf: 't-501'});
        const ops = [buyA, linked];
        const kept = byTempId(applyDeleteChoice(ops, planBulkDelete(ops, ['t-501'], allRead), 'keep', get), 't-520') as WithChoice;
        expect(kept.chargeOf, 'the local link is gone').toBeUndefined();
        expect(kept.parentUnlink, 'nothing to send: it never had this parent saved').toBeUndefined();
        expect(chargeParentFields(kept, [buyA, kept], get), 'the payload names no parent').toBeNull();
        const gone = byTempId(applyDeleteChoice(ops, planBulkDelete(ops, ['t-501'], allRead), 'all', get), 't-520') as WithChoice;
        expect(gone).toMatchObject({markedDelete: true, byParentChoice: true});
    });

    it('the toggles and removals of the plan are applied with the choice', () => {
        const free = editOp(FEE_FREE);
        const fresh = createOp('n-dep', fieldsOf(FEE_FREE));
        const ops = [buyA, feeA, free, fresh];
        const out = applyDeleteChoice(ops, planBulkDelete(ops, ['t-501', 't-520', 'n-dep'], allRead), 'keep', get);
        expect(byTempId(out, 't-520')).toMatchObject({markedDelete: true});
        expect(out.some((op) => op.tempId === 'n-dep')).toBe(false);
    });

    it('restoring the parent undoes only what the choice set: a charge unlinked by hand before stays unlinked', () => {
        const byHand = editOp(TAX_A, {chargeOf: 't-501', parentUnlink: true});
        const before = [buyA, feeA, byHand];
        const deleted = applyDeleteChoice(before, planBulkDelete(before, ['t-501'], allRead), 'keep', get);
        const restored = applyDeleteChoice(deleted, planBulkDelete(deleted, ['t-501'], allRead), 'keep', get) as WithChoice[];
        expect(byTempId(restored, 't-501')).toMatchObject({markedDelete: false});
        const fee = byTempId(restored, 't-502') as WithChoice;
        expect(fee.parentUnlink, 'the FEE the choice unlinked is linked again').toBeUndefined();
        expect(fee.byParentChoice, 'and no longer marked').toBeUndefined();
        expect(byTempId(restored, 't-503'), 'the TAX unlinked by hand stays unlinked').toMatchObject({parentUnlink: true});
    });

    it('restoring after «all»: the saved charges come back linked; a new one removed does not come back', () => {
        const before = [buyA, feeA, createOp('n-fee', fieldsOf(FEE_A), {chargeOf: 't-501', followsParent: true})];
        const deleted = applyDeleteChoice(before, planBulkDelete(before, ['t-501'], allRead), 'all', get);
        const restored = applyDeleteChoice(deleted, planBulkDelete(deleted, ['t-501'], allRead), 'all', get) as WithChoice[];
        expect(byTempId(restored, 't-502')).toMatchObject({markedDelete: false});
        expect((byTempId(restored, 't-502') as WithChoice).byParentChoice).toBeUndefined();
        expect(restored.some((op) => op.tempId === 'n-fee')).toBe(false);
    });

    it('does not mutate its input', () => {
        const ops = [buyA, feeA, taxA];
        const copy = snapshot(ops);
        applyDeleteChoice(ops, planBulkDelete(ops, ['t-501'], allRead), 'keep', get);
        expect(ops).toEqual(copy);
    });
});

// ---------------------------------------------------------------------------
// F7-d — U3 «Link» inside the Bulk, and the rows that leave (contract 66-F7 §20.5, corrected by §21.2, §21.3, §22.2, §22.3)
// ---------------------------------------------------------------------------

/**
 * The shape pinned here (the implementer follows it):
 *
 *   bulkLinkSelection(rows, ops, get, opts): BulkLinkSelection
 *       rows: the selected operations (top-level rows, in selection order); ops: every operation of the Bulk; get: the
 *       store's read; opts: `LinkOptions` of `chargeLinkRules.ts` ({roleOf, canEdit}).
 *       BulkLinkSelection =
 *           | {kind: 'hidden'}
 *           | {kind: 'disabled'; reason: LinkReason | 'deleted'; params: …}   // params: the implementer's (§20.6, §22.1)
 *           | {kind: 'ok'; parent: PendingOp; charges: PendingOp[]};
 *       It reuses `linkSelection` on mirror rows: a negative synthetic id for a create; a mirror's
 *       `parent_transaction_id` is its parent in the Bulk (`chargeOf`, unless `parentUnlink`), or `parentLinkId`, or its
 *       saved one unless `parentUnlink`. Order of the outcomes: every `hidden` of `linkSelection` first (§22.2); then
 *       `deleted` (a «del» row in the selection); then the reasons of `linkSelection`.
 *
 * RED until `bulkCharges.ts` exports `bulkLinkSelection`: read through the namespace, so only these cases fail.
 */
type BulkLinkSelection = {kind: 'hidden'} | {kind: 'disabled'; reason: string; params?: unknown} | {kind: 'ok'; parent: PendingOp; charges: PendingOp[]};
type LinkOpts = {roleOf: (type: string) => 'charge' | 'parent' | null; canEdit: (brokerId: number) => boolean};
type BulkLinkSelectionFn = (rows: readonly PendingOp[], ops: readonly PendingOp[], g: (id: number) => TXReadItem | undefined, opts: LinkOpts) => BulkLinkSelection;

const ROLES: Record<string, 'charge' | 'parent' | null> = {BUY: 'parent', SELL: 'parent', DEPOSIT: 'parent', WITHDRAWAL: 'parent', FEE: 'charge', TAX: 'charge', TRANSFER: null, ADJUSTMENT: null};
const LINK_OPTS: LinkOpts = {roleOf: (type) => ROLES[type] ?? null, canEdit: () => true};

const bulkLinkSelection: BulkLinkSelectionFn = (rows, ops, g, opts) => c2<BulkLinkSelectionFn>('bulkLinkSelection')(rows, ops, g, opts);

/** A new charge typed on its own in the Bulk (not born in a parent's form: no `followsParent`). */
function newFeeFields(extra: Partial<DraftFields> = {}): DraftFields {
    return {...fieldsOf(FEE_FREE), description: 'new fee', ...extra};
}

/** `ok`, with the parent and the charges named by tempId. */
function expectOk(result: BulkLinkSelection, parent: string, charges: string[]): void {
    expect(result.kind, JSON.stringify(result)).toBe('ok');
    if (result.kind !== 'ok') return;
    expect(result.parent.tempId).toBe(parent);
    expect(tempIds(result.charges)).toEqual(charges);
}

/** `disabled`, with this reason. */
function expectOff(result: BulkLinkSelection, reason: string): void {
    expect({kind: result.kind, reason: result.kind === 'disabled' ? result.reason : undefined}, JSON.stringify(result)).toEqual({kind: 'disabled', reason});
}

describe('bulkLinkSelection — «Link» on the Bulk’s selection (U3)', () => {
    it('saved parent + saved free charge: ok', () => {
        const buy = editOp(BUY_B, {});
        const fee = editOp(FEE_FREE);
        const ops = [buy, fee];
        expectOk(bulkLinkSelection([buy, fee], ops, get, LINK_OPTS), 't-511', ['t-520']);
    });

    it('new parent + new charge: ok, the operations themselves come back', () => {
        const buy = createOp('n-buy', newBuyFields());
        const fee = createOp('n-fee', newFeeFields({date: '2026-10-20'}));
        const ops = [buy, fee];
        expectOk(bulkLinkSelection([buy, fee], ops, get, LINK_OPTS), 'n-buy', ['n-fee']);
    });

    it('saved parent + new charge: ok', () => {
        const buy = editOp(BUY_B);
        const fee = createOp('n-fee', newFeeFields());
        expectOk(bulkLinkSelection([buy, fee], [buy, fee], get, LINK_OPTS), 't-511', ['n-fee']);
    });

    it('new parent + saved free charge: ok', () => {
        const buy = createOp('n-buy', newBuyFields());
        const fee = editOp(FEE_FREE);
        expectOk(bulkLinkSelection([buy, fee], [buy, fee], get, LINK_OPTS), 'n-buy', ['t-520']);
    });

    it('two new charges with a new parent: ok, both, in selection order', () => {
        const buy = createOp('n-buy', newBuyFields());
        const fee = createOp('n-fee', newFeeFields());
        const tax = createOp('n-tax', {...newFeeFields(), type: 'TAX' as DraftFields['type'], description: 'new tax'});
        expectOk(bulkLinkSelection([tax, buy, fee], [buy, fee, tax], get, LINK_OPTS), 'n-buy', ['n-tax', 'n-fee']);
    });

    // §22.2: the hidden outcomes of linkSelection still win.
    it('two charges and no parent stay hidden, even when one of them is «del»', () => {
        const fee = editOp(FEE_FREE, {markedDelete: true});
        const other = createOp('n-fee', newFeeFields());
        expect(bulkLinkSelection([fee, other], [fee, other], get, LINK_OPTS)).toEqual({kind: 'hidden'});
    });

    it('a single row is hidden', () => {
        const buy = editOp(BUY_B);
        expect(bulkLinkSelection([buy], [buy], get, LINK_OPTS)).toEqual({kind: 'hidden'});
    });

    it('a parent «del» in the selection: off, reason deleted', () => {
        const buy = editOp(BUY_B, {markedDelete: true});
        const fee = editOp(FEE_FREE);
        expectOff(bulkLinkSelection([buy, fee], [buy, fee], get, LINK_OPTS), 'deleted');
    });

    it('a charge «del» in the selection: off, reason deleted', () => {
        const buy = editOp(BUY_B);
        const fee = editOp(FEE_FREE, {markedDelete: true});
        expectOff(bulkLinkSelection([buy, fee], [buy, fee], get, LINK_OPTS), 'deleted');
    });

    it('deleted is checked before the other reasons: a «del» charge on another broker says deleted, not otherBroker', () => {
        const buy = editOp(BUY_B);
        const fee: PendingOp = {...editOp(FEE_FREE, {markedDelete: true}), fields: {...fieldsOf(FEE_FREE), broker_id: 99}};
        expectOff(bulkLinkSelection([buy, fee], [buy, fee], get, LINK_OPTS), 'deleted');
    });

    it('two parents: off, twoParents', () => {
        const a = editOp(BUY_B);
        const b = createOp('n-buy', newBuyFields());
        const fee = editOp(FEE_FREE);
        expectOff(bulkLinkSelection([a, b, fee], [a, b, fee], get, LINK_OPTS), 'twoParents');
    });

    it('a charge on another broker: off, otherBroker', () => {
        const buy = editOp(BUY_B);
        const fee = createOp('n-fee', newFeeFields({broker_id: 99}));
        expectOff(bulkLinkSelection([buy, fee], [buy, fee], get, LINK_OPTS), 'otherBroker');
    });

    it('a charge on another asset: off, otherAsset', () => {
        const buy = editOp(BUY_B);
        const fee = createOp('n-fee', newFeeFields({asset_id: 202}));
        expectOff(bulkLinkSelection([buy, fee], [buy, fee], get, LINK_OPTS), 'otherAsset');
    });

    it('a charge still linked to a saved parent absent from the Bulk (its saved parent): off, linked', () => {
        const buy = editOp(BUY_B);
        // FEE_A's saved parent is BUY_A (501), which is not in the Bulk.
        const fee = editOp(FEE_A);
        expectOff(bulkLinkSelection([buy, fee], [buy, fee], get, LINK_OPTS), 'linked');
    });

    it('a charge linked in this Bulk to a saved parent absent from it (parentLinkId): off, linked', () => {
        const buy = editOp(BUY_B);
        const fee = createOp('n-fee', newFeeFields(), {parentLinkId: 501});
        expectOff(bulkLinkSelection([buy, fee], [buy, fee], get, LINK_OPTS), 'linked');
    });

    // §21.2: unlinked here from A, then linked to B — «unlink first» is already done.
    it('a top-level charge unlinked here from its parent A (parentUnlink), selected with parent B: ok', () => {
        const a = editOp(BUY_A);
        const feeA = editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true});
        const b = editOp(BUY_B);
        const ops = [a, feeA, b];
        expectOk(bulkLinkSelection([b, feeA], ops, get, LINK_OPTS), 't-511', ['t-502']);
    });

    it('a saved charge whose saved parent is absent but unlinked here (parentUnlink, no chargeOf): ok', () => {
        const b = editOp(BUY_B);
        const feeA = editOp(FEE_A, {parentUnlink: true});
        expectOk(bulkLinkSelection([b, feeA], [b, feeA], get, LINK_OPTS), 't-511', ['t-502']);
    });

    it('a row the user cannot edit hides the button, as on the page', () => {
        const buy = editOp(BUY_B);
        const fee = editOp(FEE_FREE);
        expect(bulkLinkSelection([buy, fee], [buy, fee], get, {...LINK_OPTS, canEdit: (id) => id !== 77})).toEqual({kind: 'hidden'});
    });
});

/**
 * «paired» read from the Bulk's own state (66 F7-d, pair rule 8 of `charges.py`, `row_is_paired`): the backend refuses
 * a leg of a pair as parent or charge, and in one batch the pair links are applied before the charge links. So a
 * row is a leg of a pair when the Bulk holds it as one, as the payload does (`opToTxLike`): a visible row is paired
 * when another operation has `pairedWith === its tempId`; its hidden half carries `pairedWith`. The saved row's
 * `related_transaction_id` alone is not the answer: a new pair has none, and a saved pair split in this Bulk
 * (`handleSplitRow` Case A: the partner loses `pairedWith` and becomes visible) still has it.
 *
 * The pairs below use DEPOSIT / WITHDRAWAL, parent types of `ROLES`, so the other rules would say ok: a CASH_TRANSFER
 * or FX_CONVERSION leg has no charge role and would hide «Link» before «paired» is ever read.
 *
 * RED until `bulkLinkSelection` reads pairing from the operations: the new pair (no saved partner) and the split pair
 * (saved `related_transaction_id` still set) fail; the pair loaded as usual is a green guard.
 */
describe('bulkLinkSelection — «paired» from the Bulk’s own pairs (rule 8)', () => {
    /** A saved DEPOSIT / WITHDRAWAL pair on broker 77, asset 101 (the asset of FEE_FREE). */
    const DEP_P = row(540, 'DEPOSIT', {related_transaction_id: 541, cash: {code: 'EUR', amount: '100.000000'}, description: 'paired deposit'});
    const WD_P = row(541, 'WITHDRAWAL', {related_transaction_id: 540, cash: {code: 'EUR', amount: '-100.000000'}, description: 'paired withdrawal'});
    const PAIR_STORE = new Map<number, TXReadItem>([DEP_P, WD_P].map((r) => [r.id, r]));
    const pairGet = (id: number): TXReadItem | undefined => PAIR_STORE.get(id) ?? get(id);

    /** `disabled` for `paired`, naming this operation. */
    function expectPaired(result: BulkLinkSelection, tempId: string): void {
        expectOff(result, 'paired');
        const params = (result as {params?: {op?: PendingOp}}).params;
        expect(params?.op?.tempId, 'the row named is the leg of the pair').toBe(tempId);
    }

    it('a new pair in the Bulk (visible DEPOSIT + hidden WITHDRAWAL with pairedWith) with a new free FEE: off, paired, naming the DEPOSIT', () => {
        const dep = createOp('n-dep', {...fieldsOf(DEP_P), date: '2026-10-20', description: 'new paired deposit'}, {link_uuid: 'pair-uuid'});
        const wd = createOp('n-wd', {...fieldsOf(WD_P), date: '2026-10-20', description: 'new paired withdrawal'}, {pairedWith: 'n-dep', link_uuid: 'pair-uuid'});
        const fee = createOp('n-fee', newFeeFields({date: '2026-10-20'}));
        expectPaired(bulkLinkSelection([dep, fee], [dep, wd, fee], pairGet, LINK_OPTS), 'n-dep');
    });

    it('a saved pair split in this Bulk (both halves visible, no pairedWith either way) with a saved free FEE: ok', () => {
        // handleSplitRow Case A: the partner op stays in the Bulk, visible, and loses `pairedWith`; the store still
        // has `related_transaction_id` until the save, whose split runs before the charge links.
        const dep = editOp(DEP_P);
        const wd = editOp(WD_P);
        const fee = editOp(FEE_FREE);
        expectOk(bulkLinkSelection([dep, fee], [dep, wd, fee], pairGet, LINK_OPTS), 't-540', ['t-520']);
    });

    it('a saved pair loaded as usual (visible edit + hidden edit partner with pairedWith) with a saved free FEE: off, paired', () => {
        const dep = editOp(DEP_P, {link_uuid: 'saved-pair'});
        const wd = editOp(WD_P, {tempId: 'h-541', pairedWith: 't-540', link_uuid: 'saved-pair'});
        const fee = editOp(FEE_FREE);
        expectPaired(bulkLinkSelection([dep, fee], [dep, wd, fee], pairGet, LINK_OPTS), 't-540');
    });
});

/**
 * 66 C22d: `bulkLinkSelection` reads each row's type through `typeOf` (the Bulk passes `postSplitType`: a half of a
 * queued split reads the type the split gives it), for the mirror rows AND for the type the reason names
 * (`params.type`, which the toolbar's hint shows). Without `typeOf` it reads `fields.type`, as before.
 */
describe('bulkLinkSelection — the type of a row read through typeOf (66 C22d)', () => {
    type BulkLinkSelectionWithType = (rows: readonly PendingOp[], ops: readonly PendingOp[], g: (id: number) => TXReadItem | undefined, opts: LinkOpts, typeOf?: (op: PendingOp) => string) => BulkLinkSelection;
    const withType: BulkLinkSelectionWithType = (rows, ops, g, opts, typeOf) => c2<BulkLinkSelectionWithType>('bulkLinkSelection')(rows, ops, g, opts, typeOf);

    /** A saved CASH_TRANSFER pair split in this Bulk: the sender on 77 (−50), the receiver on 77 (+50); no `pairedWith`. */
    const CT_W = row(560, 'CASH_TRANSFER', {related_transaction_id: 561, cash: {code: 'EUR', amount: '-50.000000'}, description: 'split sender'});
    const CT_D = row(561, 'CASH_TRANSFER', {related_transaction_id: 560, cash: {code: 'EUR', amount: '50.000000'}, description: 'split receiver'});
    const CT_STORE = new Map<number, TXReadItem>([CT_W, CT_D].map((r) => [r.id, r]));
    const ctGet = (id: number): TXReadItem | undefined => CT_STORE.get(id) ?? get(id);
    /** The post-split types, as `postSplitType` gives them; any other row keeps its own. */
    const POST: Record<number, string> = {560: 'WITHDRAWAL', 561: 'DEPOSIT'};
    const typeOf = (op: PendingOp): string => (op.op === 'edit' && POST[op.txId]) || op.fields.type;

    it('without typeOf both halves read CASH_TRANSFER, no charge role: hidden', () => {
        const w = editOp(CT_W);
        const d = editOp(CT_D);
        const fee = editOp(FEE_FREE);
        expect(withType([w, d, fee], [w, d, fee], ctGet, LINK_OPTS)).toEqual({kind: 'hidden'});
    });

    it('with typeOf both halves are parents: off, twoParents, and params.type is the typeOf value of the second (DEPOSIT), not CASH_TRANSFER', () => {
        const w = editOp(CT_W);
        const d = editOp(CT_D);
        const fee = editOp(FEE_FREE);
        const result = withType([w, d, fee], [w, d, fee], ctGet, LINK_OPTS, typeOf);
        expectOff(result, 'twoParents');
        const params = (result as {params?: {op?: PendingOp; type?: string}}).params;
        expect({op: params?.op?.tempId, type: params?.type}, 'the second parent, named by its post-split type').toEqual({op: 't-561', type: 'DEPOSIT'});
    });

    it('the order of the selection picks the second parent: receiver first → params names the sender, WITHDRAWAL', () => {
        const w = editOp(CT_W);
        const d = editOp(CT_D);
        const fee = editOp(FEE_FREE);
        const result = withType([d, w, fee], [w, d, fee], ctGet, LINK_OPTS, typeOf);
        expectOff(result, 'twoParents');
        const params = (result as {params?: {op?: PendingOp; type?: string}}).params;
        expect({op: params?.op?.tempId, type: params?.type}).toEqual({op: 't-560', type: 'WITHDRAWAL'});
    });

    it('a half marked for deletion: off, deleted, and params.type is its typeOf value', () => {
        const d = editOp(CT_D, {markedDelete: true});
        const fee = editOp(FEE_FREE);
        const result = withType([d, fee], [editOp(CT_W), d, fee], ctGet, LINK_OPTS, typeOf);
        expectOff(result, 'deleted');
        expect((result as {params?: {type?: string}}).params?.type).toBe('DEPOSIT');
    });
});

describe('withoutRows — rows leaving the Bulk, and the new charges linked with «Link» (§21.3, §22.3)', () => {
    const withoutRows = (ops: readonly PendingOp[], ids: Iterable<string>): PendingOp[] => c2<(o: readonly PendingOp[], i: Iterable<string>) => PendingOp[]>('withoutRows')(ops, ids);

    it('a new charge born in its new parent’s form (followsParent) leaves with it', () => {
        const buy = createOp('n-buy', newBuyFields());
        const born = createOp('n-born', newFeeFields(), {chargeOf: 'n-buy', followsParent: true});
        const out = withoutRows([buy, born], ['n-buy']);
        expect(tempIds(out)).toEqual([]);
    });

    it('a new charge linked with «Link» (no followsParent) stays: a new top-level row, no chargeOf, its own values', () => {
        const buy = createOp('n-buy', newBuyFields());
        const linked = createOp('n-linked', newFeeFields({date: '2026-10-07', broker_id: 77, asset_id: 101}), {chargeOf: 'n-buy'});
        const out = withoutRows([buy, linked], ['n-buy']);
        expect(tempIds(out), 'only the parent leaves').toEqual(['n-linked']);
        const kept = byTempId(out, 'n-linked');
        expect(kept.chargeOf, 'no chargeOf left dangling').toBeUndefined();
        expect({broker_id: kept.fields.broker_id, asset_id: kept.fields.asset_id, date: kept.fields.date}).toEqual({broker_id: 77, asset_id: 101, date: '2026-10-07'});
    });

    it('both kinds under one new parent: the born one leaves, the linked one stays', () => {
        const buy = createOp('n-buy', newBuyFields());
        const born = createOp('n-born', newFeeFields(), {chargeOf: 'n-buy', followsParent: true});
        const linked = createOp('n-linked', newFeeFields(), {chargeOf: 'n-buy'});
        const saved = editOp(FEE_FREE, {chargeOf: 'n-buy'});
        const out = withoutRows([buy, born, linked, saved], ['n-buy']);
        expect(tempIds(out)).toEqual(['n-linked', 't-520']);
        for (const op of out) expect(op.chargeOf, op.tempId).toBeUndefined();
    });

    // §22.3: §12.5 unchanged — under a SAVED parent «Delete all» removes every new charge listed in the panel.
    it('«Delete all» on a saved parent still removes every new charge under it, followsParent or not', () => {
        const buy = editOp(BUY_B);
        const born = createOp('n-born', newFeeFields(), {chargeOf: 't-511', followsParent: true});
        const linked = createOp('n-linked', newFeeFields(), {chargeOf: 't-511'});
        const ops = [buy, born, linked];
        const out = applyDeleteChoice(ops, planBulkDelete(ops, ['t-511'], allRead), 'all', get);
        expect(tempIds(out)).toEqual(['t-511']);
        expect(byTempId(out, 't-511')).toMatchObject({markedDelete: true});
    });

    // §21.3: «Keep» on a create linked with «Link» keeps its own broker, asset and date (it never followed the parent).
    it('«Keep» on a saved parent with a new charge linked with «Link»: it stays with its own broker, asset and date', () => {
        const buy = editOp(BUY_B);
        const linked = createOp('n-linked', newFeeFields({date: '2026-10-07', broker_id: 77, asset_id: 101}), {chargeOf: 't-511'});
        const ops = [buy, linked];
        const out = applyDeleteChoice(ops, planBulkDelete(ops, ['t-511'], allRead), 'keep', get);
        const kept = byTempId(out, 'n-linked');
        expect(kept.chargeOf).toBeUndefined();
        expect({broker_id: kept.fields.broker_id, asset_id: kept.fields.asset_id, date: kept.fields.date}, 'its own, not BUY_B’s 2026-10-05').toEqual({broker_id: 77, asset_id: 101, date: '2026-10-07'});
    });
});

/**
 * 66 C22 (contract 66-C22 §1.1, §2.1, §5.4): one predicate of «leg of a pair», `isPairLeg(op, ops)`, exported by
 * `bulkCharges.ts`: `op.pairedWith !== undefined || ops.some((o) => o.pairedWith === op.tempId)`. A pair is the Bulk's,
 * as the payload sends it: a saved pair loaded as such, a merge queued in this Bulk (two saved rows, or a saved and a new
 * one: `collapseIntoPaired` hides one half with `pairedWith`), two new rows merged (`link_uuid`), the W4b placeholder of a
 * half the user cannot read, a hidden half whose partner is not there. A saved pair split in this Bulk is no pair (both
 * halves visible, no `pairedWith`), whatever the store's `related_transaction_id` still says.
 *
 * The same question is asked today in three places, which must agree with it on the same rows:
 *   - `pairIdOf` inside `bulkLinkSelection` (its `!= null` is the mirror row's `related_transaction_id`, read by the
 *     `paired` reason of `linkSelection`). The roles here make every non-charge type a parent, so no `hidden` outcome
 *     comes before the `paired` check (a CASH_TRANSFER leg would otherwise hide «Link» first);
 *   - `isUnderParent` (rule 8: a charge is never under a leg);
 *   - TBM:712 (`opToTxLike`, the form's `related_transaction_id` of the visible row): component level, in
 *     `TransactionBulkModal.test.ts`, describe «66 C22».
 *
 * RED until `bulkCharges.ts` exports `isPairLeg` (read through the namespace, `c2`): only the cases that call it fail.
 * The `pairIdOf` and `isUnderParent` cases are guards, green before and after.
 */
describe('isPairLeg — the one predicate of «leg of a pair» (66 C22)', () => {
    type IsPairLeg = (op: PendingOp, ops: readonly PendingOp[]) => boolean;
    const isPairLeg: IsPairLeg = (op, ops) => c2<IsPairLeg>('isPairLeg')(op, ops);

    /** Two saved rows, unpaired in the store: what a merge queued in this Bulk joins. */
    const DEP_Q = row(550, 'DEPOSIT', {asset_id: null, cash: {code: 'EUR', amount: '100.000000'}, description: 'queued deposit'});
    const WD_Q = row(551, 'WITHDRAWAL', {asset_id: null, broker_id: 88, cash: {code: 'EUR', amount: '-100.000000'}, description: 'queued withdrawal'});
    /** A saved charge of DEP_Q: what an adoption on load reads (path 7). */
    const FEE_Q = row(552, 'FEE', {asset_id: null, parent_transaction_id: 550, cash: {code: 'EUR', amount: '-1.000000'}, description: 'fee of the queued deposit'});
    /** A saved pair, linked in the store. */
    const DEP_S = row(560, 'DEPOSIT', {asset_id: null, related_transaction_id: 561, cash: {code: 'EUR', amount: '100.000000'}, description: 'saved paired deposit'});
    const WD_S = row(561, 'WITHDRAWAL', {asset_id: null, broker_id: 88, related_transaction_id: 560, cash: {code: 'EUR', amount: '-100.000000'}, description: 'saved paired withdrawal'});
    /** A free saved FEE on the legs' broker, no asset: the charge `bulkLinkSelection` is asked about. */
    const FEE_C = row(570, 'FEE', {asset_id: null, cash: {code: 'EUR', amount: '-2.000000'}, description: 'free fee'});
    const LEG_STORE = new Map<number, TXReadItem>([DEP_Q, WD_Q, FEE_Q, DEP_S, WD_S, FEE_C].map((r) => [r.id, r]));
    const legGet = (id: number): TXReadItem | undefined => LEG_STORE.get(id) ?? get(id);

    /** Every non-charge type a parent: no `hidden` of `linkSelection` comes before its `paired` reason. */
    const EQ_OPTS = {roleOf: (type: string): 'charge' | 'parent' | null => (type === 'FEE' || type === 'TAX' ? 'charge' : 'parent'), canEdit: () => true};

    const merged = (r: TXReadItem): DraftFields => ({...fieldsOf(r), type: 'CASH_TRANSFER' as DraftFields['type']});

    /** A case: the operations of the Bulk, the legs (true) and the rows that are no leg (false), by tempId. */
    type LegCase = {ops: PendingOp[]; legs: string[]; free: string[]};

    const CASES: Array<[string, () => LegCase]> = [
        ['a saved pair loaded as such (visible edit + hidden edit with pairedWith)', () => ({ops: [editOp(WD_S, {link_uuid: 's'}), editOp(DEP_S, {tempId: 'h-560', pairedWith: 't-561', link_uuid: 's'})], legs: ['t-561', 'h-560'], free: []})],
        [
            'a merge of two saved rows queued in this Bulk (the store still unpaired)',
            () => ({
                ops: [
                    {...editOp(WD_Q), fields: merged(WD_Q)},
                    {...editOp(DEP_Q, {pairedWith: 't-551'}), fields: merged(DEP_Q)},
                ],
                legs: ['t-551', 't-550'],
                free: [],
            }),
        ],
        ['a merge of a saved row and a new one queued in this Bulk', () => ({ops: [{...editOp(WD_Q), fields: merged(WD_Q)}, createOp('n-dep', merged(DEP_Q), {pairedWith: 't-551', link_uuid: 'mixed'})], legs: ['t-551', 'n-dep'], free: []})],
        ['two new rows merged (shared link_uuid, not queued)', () => ({ops: [createOp('n-wd', merged(WD_Q), {link_uuid: 'nn'}), createOp('n-dep', merged(DEP_Q), {pairedWith: 'n-wd', link_uuid: 'nn'})], legs: ['n-wd', 'n-dep'], free: []})],
        ['a saved pair split in this Bulk (both halves visible, no pairedWith; the store still linked)', () => ({ops: [editOp(WD_S), editOp(DEP_S)], legs: [], free: ['t-561', 't-560']})],
        [
            'W4b: a readable half and the placeholder of the half the user cannot read',
            () => ({
                ops: [editOp(WD_S, {link_uuid: 'w4b'}), {op: 'edit', txId: 9_560, markedDelete: false, tempId: 'ph-9560', createdSeq: 9_560, fields: {type: 'WITHDRAWAL', broker_id: 99, date: WD_S.date} as DraftFields, pairedWith: 't-561', link_uuid: 'w4b', inaccessible: true}],
                legs: ['t-561', 'ph-9560'],
                free: [],
            }),
        ],
        ['a hidden half whose partner is not in the Bulk (pairedWith naming no operation)', () => ({ops: [editOp(DEP_Q, {pairedWith: 'gone'})], legs: ['t-550'], free: []})],
        ['two lone rows, no pair', () => ({ops: [editOp(DEP_Q), editOp(WD_Q)], legs: [], free: ['t-550', 't-551']})],
    ];

    /** The case's operations with the free FEE beside them, and the FEE itself. */
    function withFee(c: LegCase): {ops: PendingOp[]; fee: PendingOp} {
        const fee = editOp(FEE_C);
        return {ops: [...c.ops, fee], fee};
    }

    /** Whether `bulkLinkSelection` reads `op` as a leg (`pairIdOf(op) != null` → its mirror's `related_transaction_id`). */
    function linkReadsPaired(op: PendingOp, ops: readonly PendingOp[], fee: PendingOp): boolean {
        const result = bulkLinkSelection([op, fee], ops, legGet, EQ_OPTS);
        return result.kind === 'disabled' && result.reason === 'paired';
    }

    it.each(CASES)('guard — pairIdOf != null (bulkLinkSelection «paired») on %s: exactly the legs', (_label, build) => {
        const c = build();
        const {ops, fee} = withFee(c);
        for (const id of c.legs) expect(linkReadsPaired(byTempId(ops, id), ops, fee), `${id} is a leg`).toBe(true);
        for (const id of c.free) expect(linkReadsPaired(byTempId(ops, id), ops, fee), `${id} is no leg`).toBe(false);
    });

    it.each(CASES)('isPairLeg on %s: true for the legs, false otherwise — and equal to pairIdOf != null on every row', (_label, build) => {
        const c = build();
        const {ops, fee} = withFee(c);
        for (const id of c.legs) expect(isPairLeg(byTempId(ops, id), ops), `${id} is a leg`).toBe(true);
        for (const id of c.free) expect(isPairLeg(byTempId(ops, id), ops), `${id} is no leg`).toBe(false);
        expect(isPairLeg(fee, ops), 'the free FEE is no leg').toBe(false);
        for (const op of ops) {
            if (op === fee) continue;
            expect(isPairLeg(op, ops), `${op.tempId}: isPairLeg and pairIdOf != null agree`).toBe(linkReadsPaired(op, ops, fee));
        }
    });

    it('isPairLeg reads the operations as given: no input mutated', () => {
        const c = CASES[1][1]();
        const before = snapshot(c.ops);
        for (const op of c.ops) isPairLeg(op, c.ops);
        expect(c.ops).toEqual(before);
    });

    // Rule 8, unchanged by C22 (C21 put it in `isUnderParent`): a charge owned by a leg is never under it; owned by a row
    // that is no leg, it is. The same rows as above.
    it.each(CASES)('guard — isUnderParent (rule 8) on %s: a FEE with chargeOf a leg is not under it; with chargeOf a row that is no leg it is', (_label, build) => {
        const c = build();
        for (const id of c.legs) {
            const fee = editOp(FEE_C, {chargeOf: id});
            expect(isUnderParent(fee, [...c.ops, fee]), `chargeOf the leg ${id}`).toBe(false);
        }
        for (const id of c.free) {
            const fee = editOp(FEE_C, {chargeOf: id});
            expect(isUnderParent(fee, [...c.ops, fee]), `chargeOf ${id}, no leg`).toBe(true);
        }
    });

    // Path 7 (§1.6): the adoption on load does not look at pairs, so a saved charge of a leg takes the leg as `chargeOf`;
    // it is never drawn under it (rule 8). In the Bulk the adoption cannot even reach a leg: a row with charges not read
    // is not offered for a merge (C21, `TransactionBulkModal.test.ts` «C21 §2.1: saved + saved, the DEPOSIT counts a
    // charge still being read / whose read failed»).
    it('guard, path 7 — a saved charge of a queued leg, adopted on load: chargeOf the leg, never under it', () => {
        const legs = [
            {...editOp(WD_Q), fields: merged(WD_Q)},
            {...editOp(DEP_Q, {pairedWith: 't-551'}), fields: merged(DEP_Q)},
        ];
        const out = adoptCharges([...legs, editOp(FEE_Q)], legGet);
        const fee = byTxId(out, FEE_Q.id);
        expect(fee.chargeOf, 'the adoption names the saved parent, a leg').toBe('t-550');
        expect(isUnderParent(fee, out), 'rule 8: never under a leg').toBe(false);
    });
});

// ---------------------------------------------------------------------------
// 66 C22c — unlinkCharge: «unlink» only from a SAVED parent; a pending link is dropped
// ---------------------------------------------------------------------------

/**
 * Consultant's decision (20/11, F7 contract §12.6 and F7-d): `parentUnlink` («scollega», `parent_transaction_id: 0`) is
 * only for a charge cut from its SAVED parent. A link that is only pending — `chargeOf` a Bulk row that is not its saved
 * parent, `parentLinkId`, or any link of a new charge (the `linkNew` test of `chargeDraftsFor`) — is undone by dropping it.
 * `unlinkCharge(op, ops, get)` returns the charge's operation unlinked (assumed: the one operation, not the array); a flag
 * that is off is absent (`without`), never `false`.
 *
 *   - saved parent == the current owner (`chargeOf` its edit row, or `parentLinkId` = it) → `parentUnlink: true`,
 *     `chargeOf` kept;
 *   - saved parent P present but another owner now → back to what it was BEFORE that link: unlinked from P
 *     (`parentUnlink: true`), sitting under P when the Bulk holds P's edit row (`chargeOf` = P's tempId: the «unlink»
 *     badge needs a `chargeOf`), with no `chargeOf` when P is not in the Bulk; `parentLinkId` and `followsParent`
 *     dropped either way, and the payload sends 0 (lane correction, 21/11);
 *   - no saved parent (a saved charge of nobody, or a create) → `chargeOf`, `parentLinkId`, `parentUnlink`,
 *     `followsParent` and `byParentChoice` dropped; a create that followed its owner (`followsParent`) keeps the owner's
 *     broker, asset and date it was following, as «Keep» does (`applyDeleteChoice`), every other field its own.
 * The cells a model cannot hold are left out: a create has no saved parent, and a create row is never a saved parent.
 *
 * RED until `bulkCharges.ts` exports `unlinkCharge` (read through the namespace, `c2`): only these cases fail.
 */
describe('unlinkCharge — «unlink» only from a saved parent; a pending link is dropped (66 C22c)', () => {
    type UnlinkCharge = (op: PendingOp, ops: readonly PendingOp[], get: (id: number) => TXReadItem | undefined) => PendingOp;
    const unlinkCharge: UnlinkCharge = (op, ops, g) => c2<UnlinkCharge>('unlinkCharge')(op, ops, g);

    type Expected = 'unlink-keep-owner' | 'unlink-under-saved' | 'unlink-saved-absent' | 'drop-all';
    /** `fields`: the fields expected out, when they are not the charge's own. */
    type Cell = {charge: PendingOp; ops: PendingOp[]; expected: Expected; fields?: DraftFields};

    const newBuy = (): PendingOp => createOp('n-buy', newBuyFields());
    /** A new FEE whose own broker, asset and date differ from every owner's, so that taking the owner's shows. */
    const NEW_FEE_FIELDS: DraftFields = {...newBuyFields(), broker_id: 99, asset_id: 202, date: '2026-11-11', type: 'FEE' as DraftFields['type'], quantity: '0', cash: {code: 'EUR', amount: '1.000000'}, description: 'new fee'};
    const newFee = (chargeOf: string, followsParent = true): PendingOp => createOp('n-fee', {...NEW_FEE_FIELDS}, followsParent ? {chargeOf, followsParent: true} : {chargeOf});
    /** The new FEE's fields with the broker, asset and date of the owner it followed. */
    const followed = (owner: DraftFields): DraftFields => ({...NEW_FEE_FIELDS, broker_id: owner.broker_id, asset_id: owner.asset_id, date: owner.date});

    /** The charge among the operations of its case: its owner (when any), another parent, a new BUY. */
    function cell(charge: PendingOp, others: PendingOp[], expected: Expected, fields?: DraftFields): Cell {
        return {charge, ops: [...others, charge], expected, fields};
    }

    const CELLS: Array<[string, () => Cell]> = [
        // Saved parent == the current owner.
        ['saved parent == owner, chargeOf its edit row', () => cell(editOp(FEE_A, {chargeOf: 't-501'}), [editOp(BUY_A), editOp(BUY_B)], 'unlink-keep-owner')],
        ['saved parent == owner, parentLinkId = it (the parent out of the Bulk)', () => cell(editOp(FEE_A, {parentLinkId: BUY_A.id}), [editOp(BUY_B)], 'unlink-keep-owner')],
        // Saved parent present, another owner now; the saved parent's edit row in the Bulk.
        ['saved parent present but another, chargeOf another edit row; the saved parent in the Bulk', () => cell(editOp(FEE_A, {chargeOf: 't-511'}), [editOp(BUY_A), editOp(BUY_B)], 'unlink-under-saved')],
        ['saved parent present but another, chargeOf a create row; the saved parent in the Bulk', () => cell(editOp(FEE_A, {chargeOf: 'n-buy'}), [editOp(BUY_A), newBuy()], 'unlink-under-saved')],
        ['saved parent present but another, parentLinkId another saved row; the saved parent in the Bulk', () => cell(editOp(FEE_A, {parentLinkId: BUY_B.id}), [editOp(BUY_A)], 'unlink-under-saved')],
        // The same, the saved parent not in the Bulk.
        ['saved parent present but another, chargeOf another edit row; the saved parent not in the Bulk', () => cell(editOp(FEE_A, {chargeOf: 't-511'}), [editOp(BUY_B)], 'unlink-saved-absent')],
        ['saved parent present but another, chargeOf a create row; the saved parent not in the Bulk', () => cell(editOp(FEE_A, {chargeOf: 'n-buy'}), [newBuy()], 'unlink-saved-absent')],
        ['saved parent present but another, parentLinkId another saved row; the saved parent not in the Bulk', () => cell(editOp(FEE_A, {parentLinkId: BUY_B.id}), [], 'unlink-saved-absent')],
        // No saved parent.
        ['no saved parent, chargeOf an edit row', () => cell(editOp(FEE_FREE, {chargeOf: 't-501'}), [editOp(BUY_A)], 'drop-all')],
        ['no saved parent, chargeOf a create row', () => cell(editOp(FEE_FREE, {chargeOf: 'n-buy'}), [newBuy()], 'drop-all')],
        ['no saved parent, parentLinkId a saved row', () => cell(editOp(FEE_FREE, {parentLinkId: BUY_B.id}), [editOp(BUY_A)], 'drop-all')],
        ['no saved parent, chargeOf an edit row, set by a delete choice (byParentChoice)', () => cell({...editOp(FEE_FREE, {chargeOf: 't-501'}), byParentChoice: true} as PendingOp, [editOp(BUY_A)], 'drop-all')],
        ['the charge is a create, chargeOf an edit row (followsParent): the owner’s broker, asset and date taken', () => cell(newFee('t-501'), [editOp(BUY_A)], 'drop-all', followed(fieldsOf(BUY_A)))],
        ['the charge is a create, chargeOf a create row (followsParent): the owner’s broker, asset and date taken', () => cell(newFee('n-buy'), [newBuy()], 'drop-all', followed(newBuyFields()))],
        ['the charge is a create, chargeOf an edit row, opened on its own (no followsParent): its own fields', () => cell(newFee('t-501', false), [editOp(BUY_A)], 'drop-all')],
    ];

    it.each(CELLS)('%s', (_label, build) => {
        const {charge, ops, expected, fields} = build();
        const out = unlinkCharge(charge, ops, get);
        const flags = {chargeOf: out.chargeOf, parentLinkId: out.parentLinkId, parentUnlink: out.parentUnlink, followsParent: out.followsParent};
        if (expected === 'unlink-keep-owner') {
            expect(out.parentUnlink, 'unlinked from its saved parent').toBe(true);
            expect(out.chargeOf, 'the owner kept').toBe(charge.chargeOf);
            expect(chargeParentFields(out, ops, get), 'the payload unlinks it').toEqual({parent_transaction_id: 0});
        } else if (expected === 'unlink-under-saved') {
            expect(flags, 'back under its saved parent, unlinked from it; the pending link dropped').toEqual({chargeOf: `t-${BUY_A.id}`, parentLinkId: undefined, parentUnlink: true, followsParent: undefined});
            expect(chargeParentFields(out, ops, get), 'the payload unlinks it from its saved parent').toEqual({parent_transaction_id: 0});
        } else if (expected === 'unlink-saved-absent') {
            expect(flags, 'unlinked from its saved parent, which the Bulk does not hold; the pending link dropped').toEqual({chargeOf: undefined, parentLinkId: undefined, parentUnlink: true, followsParent: undefined});
            expect(chargeParentFields(out, ops, get), 'the payload unlinks it from its saved parent').toEqual({parent_transaction_id: 0});
        } else {
            expect({...flags, byParentChoice: (out as WithChoice).byParentChoice}, 'the pending link dropped, nothing else set').toEqual({chargeOf: undefined, parentLinkId: undefined, parentUnlink: undefined, followsParent: undefined, byParentChoice: undefined});
            expect(chargeParentFields(out, ops, get), 'the payload says nothing about a parent').toBeNull();
        }
        expect({op: out.op, tempId: out.tempId, fields: out.fields}, 'the rest of the operation unchanged').toEqual({op: charge.op, tempId: charge.tempId, fields: fields ?? charge.fields});
    });

    // `applyChargeDrafts` with `deps.get`: FEE_A, saved under BUY_A, unlinked from it here and then linked to BUY_B (the
    // link «Link» makes: `chargeOf` BUY_B, no `parentUnlink`). In BUY_B's Form its chip is `linkNew`; set to «unlink»,
    // or left out by the Form (the «dropped» branch at the end), the link made here is undone back to what it was
    // before it: unlinked from BUY_A, under BUY_A when the Bulk holds it; the payload sends 0.
    it.each([
        ['its linkNew chip set to «unlink»', 'unlink', true],
        ['its linkNew chip left out by the Form', 'dropped', true],
        ['its linkNew chip set to «unlink», BUY_A not in the Bulk', 'unlink', false],
        ['its linkNew chip left out by the Form, BUY_A not in the Bulk', 'dropped', false],
    ] as const)('applyChargeDrafts — FEE_A unlinked from its saved BUY_A, linked to BUY_B, then in BUY_B’s Form %s: unlinked from BUY_A again, payload 0', (_label, how, withA) => {
        const ops = [...(withA ? [editOp(BUY_A)] : []), editOp(BUY_B), editOp(FEE_B, {chargeOf: 't-511'}), editOp(FEE_A, {chargeOf: 't-511'})];
        const parent = byTxId(ops, BUY_B.id);
        const drafts = chargeDraftsFor(parent, ops, get);
        expect(draftByKey(drafts, `saved-${FEE_A.id}`).linkNew, 'premise: FEE_A is a link made here').toBe(true);
        const answer = how === 'unlink' ? drafts.map((draft) => (draft.key === `saved-${FEE_A.id}` ? {...draft, state: 'unlink' as const} : draft)) : drafts.filter((draft) => draft.key !== `saved-${FEE_A.id}`);

        const out = applyChargeDrafts(parent, ops, answer, makeDeps());

        const fee = byTxId(out, FEE_A.id);
        expect({chargeOf: fee.chargeOf, parentLinkId: fee.parentLinkId, parentUnlink: fee.parentUnlink}, 'unlinked from BUY_A, as before the link').toEqual({chargeOf: withA ? `t-${BUY_A.id}` : undefined, parentLinkId: undefined, parentUnlink: true});
        expect(chargeParentFields(fee, out, get), 'the payload unlinks it from BUY_A').toEqual({parent_transaction_id: 0});
        expect(byTxId(out, FEE_B.id), 'FEE_B, saved under BUY_B, untouched').toEqual(byTxId(ops, FEE_B.id));
    });

    it('reads its inputs as given: neither the charge nor the operations mutated', () => {
        const {charge, ops} = CELLS[2][1]();
        const before = snapshot({charge, ops});
        unlinkCharge(charge, ops, get);
        expect({charge, ops}).toEqual(before);
    });
});

// ---------------------------------------------------------------------------
// TL-3 — «Clona» carries the linked-charges structure (project 66, lot TL-3)
// ---------------------------------------------------------------------------

/**
 * TL-3 (FEE consultant): cloning a parent that still has linked charges copies them too, linked to the parent's copy;
 * the copy of a charge is born linked to the same parent as its original. The pure half lives in `bulkCharges.ts`:
 *
 *   - `PendingOp.clonedFields`  a charge copy brought by «Clona» with or under its parent holds the values it was born
 *                               with; `isUntouchedClone` = a create whose fields still equal them (`sameDraftFields`:
 *                               decimals exactly, `'10' == '10.00'`; tags by value).
 *   - `cloneChargeLink`         the link of the copy of a charge cloned ALONE inside the Bulk: its owner (decided by the
 *                               «Link» rule on a probe create), a saved parent, or free with a reason.
 *   - `cloneChargesUnder`       the copies of the charges still linked under a parent, owned by the parent's copy.
 *   - `wireClonedRows`          the page's clone intent: cloned charges wired to their parent's clone (or to the saved
 *                               parent), the charges read added as copies under their parent's clone.
 *   - `withoutRows`             a parent's copy trashed takes its untouched charge copies with it; a touched one stays,
 *                               free.
 *   - `unlinkCharge`, `linkInBulk`, the «unlink» branch of `applyChargeDrafts`: `clonedFields` goes with the link.
 *
 * RED until `bulkCharges.ts` exports the new functions (read through the namespace, `c2`, so only their cases fail) and
 * the existing ones drop or honour `clonedFields`. `clonedFields` is read through a local cast (`WithClone`) until
 * `PendingOp` declares it.
 */
type WithClone = PendingOp & {clonedFields?: DraftFields};
type CloneLink = {kind: 'owner'; chargeOf: string} | {kind: 'saved'; parentLinkId: number} | {kind: 'free'; reason: string | null};
type SameDraftFields = (a: DraftFields, b: DraftFields) => boolean;
type IsUntouchedClone = (op: PendingOp) => boolean;
type CloneChargeLink = (src: PendingOp, copyFields: DraftFields, ops: readonly PendingOp[], g: (id: number) => TXReadItem | undefined, opts: LinkOpts, typeOf?: (op: PendingOp) => string) => CloneLink;
type CloneChargesUnder = (parent: PendingOp, parentCopyTempId: string, ops: readonly PendingOp[], makeCopy: (charge: PendingOp) => PendingOp) => PendingOp[];
type WireClonedRows = (sources: readonly TXReadItem[], clones: readonly PendingOp[], readCharges: readonly TXReadItem[] | null, makeCreate: (tx: TXReadItem) => PendingOp) => {ops: PendingOp[]; expanded: string[]};
type WithoutRowsFn = (ops: readonly PendingOp[], ids: Iterable<string>) => PendingOp[];
type UnlinkChargeFn = (op: PendingOp, ops: readonly PendingOp[], g: (id: number) => TXReadItem | undefined) => PendingOp;
type LinkInBulkFn = (ops: readonly PendingOp[], parent: PendingOp, charges: readonly PendingOp[]) => PendingOp[];

const sameDraftFields: SameDraftFields = (a, b) => c2<SameDraftFields>('sameDraftFields')(a, b);
const isUntouchedClone: IsUntouchedClone = (op) => c2<IsUntouchedClone>('isUntouchedClone')(op);
const cloneChargeLink: CloneChargeLink = (src, copyFields, ops, g, opts, typeOf) => c2<CloneChargeLink>('cloneChargeLink')(src, copyFields, ops, g, opts, typeOf);
const cloneChargesUnder: CloneChargesUnder = (parent, copyId, ops, makeCopy) => c2<CloneChargesUnder>('cloneChargesUnder')(parent, copyId, ops, makeCopy);
const wireClonedRows: WireClonedRows = (sources, clones, read, makeCreate) => c2<WireClonedRows>('wireClonedRows')(sources, clones, read, makeCreate);
const tl3WithoutRows: WithoutRowsFn = (ops, ids) => c2<WithoutRowsFn>('withoutRows')(ops, ids);
const tl3UnlinkCharge: UnlinkChargeFn = (op, ops, g) => c2<UnlinkChargeFn>('unlinkCharge')(op, ops, g);
const tl3LinkInBulk: LinkInBulkFn = (ops, parent, charges) => c2<LinkInBulkFn>('linkInBulk')(ops, parent, charges);

/** A saved BUY whose FEE and TAX sit on days of their own (rule 4: a charge's date is free), so «keeps its own date»
 *  cannot be told apart from «took the parent's». */
const BUY_D = row(601, 'BUY', {date: '2026-10-01', charges_count: 2, description: 'buy D'});
const FEE_D = row(602, 'FEE', {parent_transaction_id: 601, date: '2026-10-03', cash: {code: 'EUR', amount: '-1.500000'}, description: 'fee D'});
const TAX_D = row(603, 'TAX', {parent_transaction_id: 601, date: '2026-10-04', cash: {code: 'EUR', amount: '-0.250000'}, description: 'tax D'});

/** The copy of a saved row as the editor makes it: a create with the row's fields. */
function copyOf(tempId: string, r: TXReadItem, extra: Omit<OpExtra, 'markedDelete' | 'tempId'> & {clonedFields?: DraftFields} = {}): WithClone {
    return {...createOp(tempId, fieldsOf(r)), ...extra} as WithClone;
}

/** A charge copy brought by «Clona» under the parent copy `chargeOf`, born untouched. */
function broughtCopy(tempId: string, r: TXReadItem, chargeOf: string): WithClone {
    const fields = fieldsOf(r);
    return {...createOp(tempId, fields, {chargeOf}), clonedFields: structuredClone(fields)} as WithClone;
}

describe('TL-3 applyChargeDrafts — an unchanged draft of a cloned charge keeps the copy as it is', () => {
    it('the parent copy’s Form handed back unchanged: same tempId, the copy’s own date (not the parent’s), no followsParent, still untouched', () => {
        const parent = copyOf('c-buy', BUY_D);
        const fee = broughtCopy('c-fee', FEE_D, 'c-buy');
        expect(fee.fields.date, 'premise: the FEE copy has a date of its own').not.toBe(parent.fields.date);
        const ops = [parent, fee];
        const drafts = chargeDraftsFor(parent, ops, get);
        expect(
            drafts.map((d) => d.key),
            'premise: the Form sees the copy as a new charge of the parent',
        ).toEqual(['op-c-fee']);

        const out = applyChargeDrafts(parent, ops, drafts, makeDeps());

        const kept = byTempId(out, 'c-fee') as WithClone;
        expect(kept.fields.date, 'its own date, not the parent’s').toBe(FEE_D.date);
        expect(kept.chargeOf).toBe('c-buy');
        expect(kept.followsParent, 'a copy never follows its parent').toBeUndefined();
        expect(kept.clonedFields, 'the values it was born with are kept').toEqual(fieldsOf(FEE_D));
        expect(out).toHaveLength(2);
        expect(isUntouchedClone(kept), 'nothing was changed: still an untouched copy').toBe(true);
    });

    it('a changed draft: the copy stays under the parent copy, but it is no longer untouched', () => {
        const parent = copyOf('c-buy', BUY_D);
        const ops = [parent, broughtCopy('c-fee', FEE_D, 'c-buy')];
        const drafts = chargeDraftsFor(parent, ops, get).map((d) => ({...d, description: 'fee D, changed'}));

        const out = applyChargeDrafts(parent, ops, drafts, makeDeps());

        const changed = byTempId(out, 'c-fee');
        expect(changed.chargeOf).toBe('c-buy');
        expect(changed.fields.description).toBe('fee D, changed');
        expect(isUntouchedClone(changed)).toBe(false);
    });

    it('«unlink» on a copy in the parent copy’s Form: a row of its own, its own date, chargeOf and clonedFields gone', () => {
        const parent = copyOf('c-buy', BUY_D);
        const ops = [parent, broughtCopy('c-fee', FEE_D, 'c-buy')];
        const drafts = chargeDraftsFor(parent, ops, get).map((d) => ({...d, state: 'unlink' as const}));

        const out = applyChargeDrafts(parent, ops, drafts, makeDeps());

        const free = byTempId(out, 'c-fee') as WithClone;
        expect({chargeOf: free.chargeOf, followsParent: free.followsParent, clonedFields: free.clonedFields}).toEqual({chargeOf: undefined, followsParent: undefined, clonedFields: undefined});
        expect(free.fields.date, 'never followed the parent: its own date').toBe(FEE_D.date);
    });
});

describe('TL-3 sameDraftFields — two sets of fields equal by value', () => {
    const base = (): DraftFields => ({...fieldsOf(FEE_D), tags: ['a', 'b']});

    it('the same values in new objects: equal', () => {
        expect(sameDraftFields(base(), base())).toBe(true);
    });

    it('decimals compared exactly: 10 == 10.00 in cash and quantity', () => {
        const a = {...base(), quantity: '2', cash: {code: 'EUR', amount: '10'}};
        const b = {...base(), quantity: '2.000000', cash: {code: 'EUR', amount: '10.00'}};
        expect(sameDraftFields(a, b)).toBe(true);
    });

    it('a different amount, currency, date, note, type or tag: not equal', () => {
        const a = {...base(), cash: {code: 'EUR', amount: '10'}};
        expect(sameDraftFields(a, {...a, cash: {code: 'EUR', amount: '10.5'}}), 'amount').toBe(false);
        expect(sameDraftFields(a, {...a, cash: {code: 'USD', amount: '10'}}), 'currency').toBe(false);
        expect(sameDraftFields(a, {...a, cash: null}), 'cash removed').toBe(false);
        expect(sameDraftFields(a, {...a, date: '2026-10-09'}), 'date').toBe(false);
        expect(sameDraftFields(a, {...a, description: 'other'}), 'note').toBe(false);
        expect(sameDraftFields(a, {...a, type: 'TAX' as DraftFields['type']}), 'type').toBe(false);
        expect(sameDraftFields(a, {...a, tags: ['a']}), 'tags').toBe(false);
    });

    it('tags by value: equal arrays in different objects are equal', () => {
        expect(sameDraftFields({...base(), tags: ['x', 'y']}, {...base(), tags: ['x', 'y']})).toBe(true);
    });
});

describe('TL-3 isUntouchedClone — a copy brought by «Clona», as it was born', () => {
    it('a create with clonedFields equal to its fields: untouched', () => {
        expect(isUntouchedClone(broughtCopy('c-fee', FEE_D, 'c-buy'))).toBe(true);
    });

    it('equal by exact decimals (5 == 5.000000): untouched', () => {
        const op = broughtCopy('c-fee', FEE_D, 'c-buy');
        const reformatted = {...op, fields: {...op.fields, cash: {code: 'EUR', amount: `${op.fields.cash!.amount}000`}}} as WithClone;
        expect(isUntouchedClone(reformatted)).toBe(true);
    });

    it('a field changed since: touched', () => {
        const op = broughtCopy('c-fee', FEE_D, 'c-buy');
        expect(isUntouchedClone({...op, fields: {...op.fields, cash: {code: 'EUR', amount: '7'}}} as WithClone)).toBe(false);
    });

    it('a create without clonedFields (typed, or cloned alone), or a saved row: never an untouched clone', () => {
        expect(isUntouchedClone(createOp('n-fee', fieldsOf(FEE_D), {chargeOf: 'c-buy'}))).toBe(false);
        expect(isUntouchedClone({...editOp(FEE_A, {chargeOf: 't-501'}), clonedFields: fieldsOf(FEE_A)} as WithClone)).toBe(false);
    });
});

describe('TL-3 cloneChargeLink — the link of the copy of a charge cloned alone inside the Bulk', () => {
    const ownerOk = (): PendingOp[] => adoptCharges([editOp(BUY_A), editOp(FEE_A), editOp(TAX_A)], get);

    it('owner present and linkable: born under the same owner', () => {
        const ops = ownerOk();
        const src = byTxId(ops, FEE_A.id);
        expect(cloneChargeLink(src, {...src.fields}, ops, get, LINK_OPTS)).toEqual({kind: 'owner', chargeOf: 't-501'});
    });

    it('owner a new row of the Bulk (a parent copy): born under that create', () => {
        const parent = copyOf('c-buy', BUY_D);
        const src = broughtCopy('c-fee', FEE_D, 'c-buy');
        expect(cloneChargeLink(src, {...src.fields}, [parent, src], get, LINK_OPTS)).toEqual({kind: 'owner', chargeOf: 'c-buy'});
    });

    it('the original already «scollega»: free, no reason (no toast)', () => {
        const ops = ownerOk().map((op) => (op.op === 'edit' && op.txId === FEE_A.id ? ({...op, parentUnlink: true} as PendingOp) : op));
        const src = byTxId(ops, FEE_A.id);
        expect(cloneChargeLink(src, {...src.fields}, ops, get, LINK_OPTS)).toEqual({kind: 'free', reason: null});
    });

    it('owner marked «del» (its charges «del» with it): free, reason deleted', () => {
        const ops = ownerOk().map((op) => (op.op === 'edit' ? ({...op, markedDelete: true, ...(op.txId === BUY_A.id ? {} : {byParentChoice: true})} as PendingOp) : op));
        const src = byTxId(ops, FEE_A.id);
        expect(src.chargeOf, 'premise: the FEE is still owned by the BUY').toBe('t-501');
        expect(cloneChargeLink(src, {...src.fields}, ops, get, LINK_OPTS)).toEqual({kind: 'free', reason: 'deleted'});
    });

    it('owner a leg of a pair (a DEPOSIT with its hidden WITHDRAWAL): free, reason paired', () => {
        const dep = row(640, 'DEPOSIT', {related_transaction_id: 641, cash: {code: 'EUR', amount: '100.000000'}, description: 'paired deposit'});
        const wd = row(641, 'WITHDRAWAL', {related_transaction_id: 640, cash: {code: 'EUR', amount: '-100.000000'}, description: 'paired withdrawal'});
        const pairStore = new Map<number, TXReadItem>([dep, wd].map((r) => [r.id, r]));
        const pairGet = (id: number): TXReadItem | undefined => pairStore.get(id) ?? get(id);
        const src = createOp('n-fee', fieldsOf(FEE_FREE), {chargeOf: 't-640'});
        const ops = [editOp(dep), editOp(wd, {pairedWith: 't-640'}), src];
        expect(cloneChargeLink(src, {...src.fields}, ops, pairGet, LINK_OPTS)).toEqual({kind: 'free', reason: 'paired'});
    });

    it('the «Link» rule reads the copy’s fields, not the original’s: a copy on another asset is free, reason otherAsset', () => {
        const ops = ownerOk();
        const src = byTxId(ops, FEE_A.id);
        expect(cloneChargeLink(src, {...src.fields, asset_id: 202}, ops, get, LINK_OPTS)).toEqual({kind: 'free', reason: 'otherAsset'});
    });

    it('a «Link» that would be hidden (the user cannot edit the broker): free, reason hidden', () => {
        const ops = ownerOk();
        const src = byTxId(ops, FEE_A.id);
        expect(cloneChargeLink(src, {...src.fields}, ops, get, {...LINK_OPTS, canEdit: () => false})).toEqual({kind: 'free', reason: 'hidden'});
    });

    it('typeOf is forwarded to the «Link» rule: an owner read as a type with no charge role hides it', () => {
        const ops = ownerOk();
        const src = byTxId(ops, FEE_A.id);
        const typeOf = (op: PendingOp): string => (op.tempId === 't-501' ? 'TRANSFER' : op.fields.type);
        expect(cloneChargeLink(src, {...src.fields}, ops, get, LINK_OPTS, typeOf)).toEqual({kind: 'free', reason: 'hidden'});
    });

    it('no owner, parentLinkId: born linked to that saved parent', () => {
        const src = editOp(FEE_FREE, {parentLinkId: BUY_B.id});
        expect(cloneChargeLink(src, {...src.fields}, [src], get, LINK_OPTS)).toEqual({kind: 'saved', parentLinkId: BUY_B.id});
    });

    it('no owner, a saved parent absent from the Bulk: born linked to that saved parent', () => {
        const src = editOp(FEE_B);
        expect(cloneChargeLink(src, {...src.fields}, [src], get, LINK_OPTS)).toEqual({kind: 'saved', parentLinkId: BUY_B.id});
    });

    it('a chargeOf naming nobody present falls back to the saved parent', () => {
        const src = editOp(FEE_B, {chargeOf: 'ghost'});
        expect(cloneChargeLink(src, {...src.fields}, [src], get, LINK_OPTS)).toEqual({kind: 'saved', parentLinkId: BUY_B.id});
    });

    it('a free charge, saved or new: free, no reason', () => {
        const saved = editOp(FEE_FREE);
        const fresh = createOp('n-fee', fieldsOf(FEE_FREE));
        expect(cloneChargeLink(saved, {...saved.fields}, [saved], get, LINK_OPTS)).toEqual({kind: 'free', reason: null});
        expect(cloneChargeLink(fresh, {...fresh.fields}, [fresh], get, LINK_OPTS)).toEqual({kind: 'free', reason: null});
    });

    it('reads its inputs as given', () => {
        const ops = ownerOk();
        const before = snapshot(ops);
        cloneChargeLink(byTxId(ops, FEE_A.id), {...byTxId(ops, FEE_A.id).fields}, ops, get, LINK_OPTS);
        expect(ops).toEqual(before);
    });
});

describe('TL-3 cloneChargesUnder — the copies of the charges still linked under a parent', () => {
    const makeCopy = (charge: PendingOp): PendingOp => createOp(`copy-${charge.tempId}`, {...charge.fields});

    it('each linked charge copied once, owned by the parent copy, clonedFields = the copy’s fields, in ops order', () => {
        const ops = adoptCharges([editOp(BUY_A), editOp(FEE_A), editOp(TAX_A), editOp(BUY_B), editOp(FEE_B)], get);
        const spy = vi.fn(makeCopy);

        const copies = cloneChargesUnder(byTxId(ops, BUY_A.id), 'c-buy', ops, spy) as WithClone[];

        expect(tempIds(copies)).toEqual([`copy-t-${FEE_A.id}`, `copy-t-${TAX_A.id}`]);
        expect(spy).toHaveBeenCalledTimes(2);
        for (const copy of copies) {
            expect(copy.chargeOf).toBe('c-buy');
            expect(copy.clonedFields).toEqual(copy.fields);
            expect(isUntouchedClone(copy), copy.tempId).toBe(true);
        }
    });

    it('a charge «del» or «scollega» is not copied; a new charge under the parent is', () => {
        const ops = adoptCharges([editOp(BUY_A), editOp(FEE_A, {markedDelete: true}), editOp(TAX_A, {parentUnlink: true}), editOp(FEE_FREE, {chargeOf: 't-501'}), createOp('n-fee', fieldsOf(FEE_D), {chargeOf: 't-501'})], get);

        const copies = cloneChargesUnder(byTxId(ops, BUY_A.id), 'c-buy', ops, makeCopy);

        expect(tempIds(copies)).toEqual([`copy-t-${FEE_FREE.id}`, 'copy-n-fee']);
    });

    it('a parent with no linked charge: none; the operations are not mutated', () => {
        const ops = [editOp(BUY_B), editOp(FEE_FREE)];
        const before = snapshot(ops);
        expect(cloneChargesUnder(ops[0], 'c-buy', ops, makeCopy)).toEqual([]);
        expect(ops).toEqual(before);
    });
});

describe('TL-3 wireClonedRows — the page’s clone intent', () => {
    const makeCreate = (tx: TXReadItem): PendingOp => createOp(`r-${tx.id}`, fieldsOf(tx));

    it('a parent cloned alone: its charges read become copies under its clone, each on its own date; the group opens', () => {
        const spy = vi.fn(makeCreate);
        const cBuy = copyOf('c-buy', BUY_D);

        const {ops, expanded} = wireClonedRows([BUY_D], [cBuy], [FEE_D, TAX_D], spy);

        expect(ops).toHaveLength(3);
        expect(byTempId(ops, 'c-buy'), 'the parent clone comes out as it went in').toEqual(cBuy);
        for (const [id, date] of [
            [FEE_D.id, FEE_D.date],
            [TAX_D.id, TAX_D.date],
        ] as const) {
            const copy = byTempId(ops, `r-${id}`) as WithClone;
            expect(copy.chargeOf).toBe('c-buy');
            expect(copy.fields.date, 'its original’s date').toBe(date);
            expect(copy.clonedFields).toEqual(copy.fields);
        }
        expect(spy).toHaveBeenCalledTimes(2);
        expect(expanded).toEqual(['c-buy']);
    });

    it('a charge cloned alone: its clone is linked to the saved parent (parentLinkId), no clonedFields, nothing read added', () => {
        const cFee = copyOf('c-fee', FEE_D);

        const {ops, expanded} = wireClonedRows([FEE_D], [cFee], [], makeCreate);

        expect(ops).toHaveLength(1);
        const fee = ops[0] as WithClone;
        expect({tempId: fee.tempId, parentLinkId: fee.parentLinkId, chargeOf: fee.chargeOf, clonedFields: fee.clonedFields}).toEqual({tempId: 'c-fee', parentLinkId: BUY_D.id, chargeOf: undefined, clonedFields: undefined});
        expect(fee.fields.date).toBe(FEE_D.date);
        expect(expanded).toEqual([]);
    });

    it('a parent and one of its charges selected together: the charge copied once, under the parent’s clone; the other read', () => {
        const spy = vi.fn(makeCreate);

        const {ops, expanded} = wireClonedRows([BUY_D, FEE_D], [copyOf('c-buy', BUY_D), copyOf('c-fee', FEE_D)], [FEE_D, TAX_D], spy);

        expect(ops).toHaveLength(3);
        const fee = byTempId(ops, 'c-fee') as WithClone;
        expect(fee.chargeOf).toBe('c-buy');
        expect(fee.parentLinkId, 'linked to the parent’s copy, not to the saved parent').toBeUndefined();
        expect(fee.clonedFields).toEqual(fee.fields);
        expect(byTempId(ops, `r-${TAX_D.id}`).chargeOf).toBe('c-buy');
        expect(spy, 'only the TAX is made from the read').toHaveBeenCalledTimes(1);
        expect(spy.mock.calls[0][0].id).toBe(TAX_D.id);
        expect(expanded).toEqual(['c-buy']);
    });

    it('the read failed (null): no extra copies; a charge selected with its parent is still wired to its clone', () => {
        const spy = vi.fn(makeCreate);
        const alone = wireClonedRows([BUY_D], [copyOf('c-buy', BUY_D)], null, spy);
        expect(tempIds(alone.ops)).toEqual(['c-buy']);
        expect(alone.expanded).toEqual([]);

        const both = wireClonedRows([BUY_D, FEE_D], [copyOf('c-buy', BUY_D), copyOf('c-fee', FEE_D)], null, spy);
        expect(both.ops).toHaveLength(2);
        expect(byTempId(both.ops, 'c-fee').chargeOf).toBe('c-buy');
        expect(both.expanded).toEqual(['c-buy']);
        expect(spy).not.toHaveBeenCalled();
    });

    it('a read charge of a parent not among the sources is ignored; two parents each get their own', () => {
        const one = wireClonedRows([BUY_D], [copyOf('c-buy', BUY_D)], [FEE_D, FEE_B], makeCreate);
        expect(tempIds(one.ops).sort()).toEqual(['c-buy', `r-${FEE_D.id}`].sort());

        const two = wireClonedRows([BUY_D, BUY_B], [copyOf('c-buy', BUY_D), copyOf('c-buyb', BUY_B)], [FEE_D, TAX_D, FEE_B], makeCreate);
        expect(two.ops).toHaveLength(5);
        expect(byTempId(two.ops, `r-${FEE_B.id}`).chargeOf).toBe('c-buyb');
        expect(byTempId(two.ops, `r-${TAX_D.id}`).chargeOf).toBe('c-buy');
        expect([...two.expanded].sort()).toEqual(['c-buy', 'c-buyb']);
    });

    it('reads its inputs as given', () => {
        const clones = [copyOf('c-buy', BUY_D), copyOf('c-fee', FEE_D)];
        const read = [FEE_D, TAX_D];
        const before = snapshot({clones, read});
        wireClonedRows([BUY_D, FEE_D], clones, read, makeCreate);
        expect({clones, read}).toEqual(before);
    });
});

describe('TL-3 withoutRows — a parent copy trashed takes its untouched charge copies', () => {
    it('the untouched copies leave with the parent copy', () => {
        const out = tl3WithoutRows([copyOf('c-buy', BUY_D), broughtCopy('c-fee', FEE_D, 'c-buy'), broughtCopy('c-tax', TAX_D, 'c-buy')], ['c-buy']);
        expect(tempIds(out)).toEqual([]);
    });

    it('a touched copy stays, a row of its own (no chargeOf), with its values', () => {
        const touched = broughtCopy('c-fee', FEE_D, 'c-buy');
        touched.fields = {...touched.fields, cash: {code: 'EUR', amount: '7'}};
        const out = tl3WithoutRows([copyOf('c-buy', BUY_D), touched, broughtCopy('c-tax', TAX_D, 'c-buy')], ['c-buy']);
        expect(tempIds(out)).toEqual(['c-fee']);
        expect(out[0].chargeOf).toBeUndefined();
        expect(out[0].fields).toMatchObject({cash: {code: 'EUR', amount: '7'}, date: FEE_D.date});
    });

    it('the copies under a parent copy that stays are untouched by the removal of another row', () => {
        const ops = [copyOf('c-buy', BUY_D), broughtCopy('c-fee', FEE_D, 'c-buy'), editOp(FEE_FREE)];
        const out = tl3WithoutRows(ops, [`t-${FEE_FREE.id}`]);
        expect(out).toEqual(ops.slice(0, 2));
    });

    it('the touched copy left by applyChargeDrafts stays when its parent copy is trashed (the two halves together)', () => {
        const parent = copyOf('c-buy', BUY_D);
        const ops = [parent, broughtCopy('c-fee', FEE_D, 'c-buy'), broughtCopy('c-tax', TAX_D, 'c-buy')];
        const drafts = chargeDraftsFor(parent, ops, get).map((d) => (d.key === 'op-c-fee' ? {...d, cash: {code: 'EUR', amount: '7'}} : d));
        const edited = applyChargeDrafts(parent, ops, drafts, makeDeps());

        const out = tl3WithoutRows(edited, ['c-buy']);

        expect(tempIds(out), 'the changed FEE copy stays; the untouched TAX copy leaves').toEqual(['c-fee']);
    });
});

describe('TL-3 clonedFields goes with the link', () => {
    it('unlinkCharge: a copy under a parent copy loses chargeOf and clonedFields', () => {
        const ops = [copyOf('c-buy', BUY_D), broughtCopy('c-fee', FEE_D, 'c-buy')];
        const out = tl3UnlinkCharge(ops[1], ops, get) as WithClone;
        expect({chargeOf: out.chargeOf, clonedFields: out.clonedFields}).toEqual({chargeOf: undefined, clonedFields: undefined});
        expect(out.fields).toEqual(ops[1].fields);
    });

    it('linkInBulk: a copy linked to another parent loses clonedFields', () => {
        const other = createOp('n-buy', newBuyFields());
        const ops = [copyOf('c-buy', BUY_D), broughtCopy('c-fee', FEE_D, 'c-buy'), other];
        const out = tl3LinkInBulk(ops, other, [ops[1]]);
        const fee = byTempId(out, 'c-fee') as WithClone;
        expect(fee.chargeOf).toBe('n-buy');
        expect(fee.clonedFields).toBeUndefined();
    });
});

// ---------------------------------------------------------------------------
// TL-2 — the form's charges picker sees the Bulk's rows (FEE consultant, lot TL-2)
// ---------------------------------------------------------------------------

/**
 * TL-2: inside the Bulk, «Link an existing charge…» of a parent's form reads the candidates on the Bulk's current state,
 * not only on the database. The pure half:
 *
 *   bulkChargeCandidates(parent, probe, ops, get, opts, typeOf?): {candidates: PendingOp[]; excluded: number[]}
 *       parent: the parent's operation, or null when its form creates it (a synthetic probe create stands in).
 *       probe:  the form's current broker, asset and type (`BulkChargeProbe`): they decide, not the parent's fields.
 *       Every charge-type operation (FEE/TAX through `typeOf`) other than the parent and not already owned by it (in the
 *       section): the «Link» rule (`bulkLinkSelection` on the probe parent and that operation) ok → a candidate; otherwise
 *       a saved one's txId goes to `excluded` (the form drops it from the DB rows).
 *
 * And the pick is the selection's «Link»: a saved charge picked in a parent's form comes out of `applyChargeDrafts` as
 * `linkInBulk` makes it (`byParentChoice` and `clonedFields` dropped as well).
 *
 * RED until `bulkCharges.ts` exports `bulkChargeCandidates` (read through the namespace, `c2`, so only these cases fail)
 * and `applyChargeDrafts`' saved «linked» branch drops `byParentChoice`.
 */
type BulkChargeProbe = {broker_id: number; asset_id: number | null; type: string};
type BulkChargeCandidatesFn = (parent: PendingOp | null, probe: BulkChargeProbe, ops: readonly PendingOp[], g: (id: number) => TXReadItem | undefined, opts: LinkOpts, typeOf?: (op: PendingOp) => string) => {candidates: PendingOp[]; excluded: number[]};

const bulkChargeCandidates: BulkChargeCandidatesFn = (parent, probe, ops, g, opts, typeOf) => c2<BulkChargeCandidatesFn>('bulkChargeCandidates')(parent, probe, ops, g, opts, typeOf);

/** The probe of a parent's form left as the parent is: its broker, asset and type. */
const probeOf = (op: PendingOp): BulkChargeProbe => ({broker_id: op.fields.broker_id, asset_id: op.fields.asset_id ?? null, type: op.fields.type});
/** The probe of a BUY form on BUY_A / BUY_B's broker and asset. */
const PROBE_BUY: BulkChargeProbe = {broker_id: 77, asset_id: 101, type: 'BUY'};
const sortedIds = (ids: readonly number[]): number[] => [...ids].sort((a, b) => a - b);

/** BUY_A with its FEE and TAX adopted (`chargeOf: 't-501'`), plus BUY_B with none of its own in the Bulk. */
function twoParents(): PendingOp[] {
    return [...adoptCharges([editOp(BUY_A), editOp(FEE_A), editOp(TAX_A)], get), editOp(BUY_B)];
}

describe('TL-2 bulkChargeCandidates — what the charges picker of a parent’s form may offer from the Bulk', () => {
    it('a new free charge of the Bulk is a candidate; nothing excluded', () => {
        const parent = editOp(BUY_B);
        const ops = [parent, createOp('n-fee', newFeeFields())];
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(tempIds(result.candidates)).toEqual(['n-fee']);
        expect(result.excluded).toEqual([]);
    });

    it('a saved free charge of the Bulk, untouched, is a candidate (the form keeps one copy of it)', () => {
        const parent = editOp(BUY_B);
        const ops = [parent, editOp(FEE_FREE)];
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(tempIds(result.candidates)).toEqual(['t-520']);
        expect(result.excluded).toEqual([]);
    });

    it('a saved charge unlinked here («scollega» in its parent’s form) is a candidate; its linked sibling is excluded', () => {
        const ops = twoParents().map((op) => (op.op === 'edit' && op.txId === FEE_A.id ? ({...op, parentUnlink: true} as PendingOp) : op));
        expect({chargeOf: byTxId(ops, FEE_A.id).chargeOf, parentUnlink: byTxId(ops, FEE_A.id).parentUnlink}, 'premise: the FEE is unlinked under its saved parent').toEqual({chargeOf: 't-501', parentUnlink: true});
        const parent = byTxId(ops, BUY_B.id);
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(tempIds(result.candidates)).toEqual(['t-502']);
        expect(sortedIds(result.excluded), 'the TAX is still linked to BUY_A').toEqual([TAX_A.id]);
    });

    it('a saved charge kept with its parent «del» («Keep the charges») is a candidate', () => {
        const base = twoParents();
        const kept = applyDeleteChoice(base, planBulkDelete(base, ['t-501'], allRead), 'keep', get);
        const fee = byTxId(kept, FEE_A.id) as WithChoice;
        expect({parentUnlink: fee.parentUnlink, byParentChoice: fee.byParentChoice}, 'premise: kept by the parent’s choice').toEqual({parentUnlink: true, byParentChoice: true});
        const parent = byTxId(kept, BUY_B.id);
        const result = bulkChargeCandidates(parent, probeOf(parent), kept, get, LINK_OPTS);
        expect(tempIds(result.candidates)).toEqual(['t-502', 't-503']);
        expect(result.excluded).toEqual([]);
    });

    it('a saved charge marked «del» is excluded, never a candidate', () => {
        const parent = editOp(BUY_B);
        const ops = [parent, editOp(FEE_FREE, {markedDelete: true})];
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(result.candidates).toEqual([]);
        expect(result.excluded).toEqual([FEE_FREE.id]);
    });

    it('a saved charge linked here to another parent (adopted, or a free one linked with «Link») is excluded', () => {
        const ops = [...twoParents(), editOp(FEE_FREE, {chargeOf: 't-501'})];
        const parent = byTxId(ops, BUY_B.id);
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(result.candidates).toEqual([]);
        expect(sortedIds(result.excluded)).toEqual([FEE_A.id, TAX_A.id, FEE_FREE.id]);
    });

    it('a saved free charge linked here to a saved parent absent from the Bulk (parentLinkId) is excluded', () => {
        const parent = editOp(BUY_A);
        const ops = [parent, editOp(FEE_FREE, {parentLinkId: BUY_B.id})];
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(result.candidates).toEqual([]);
        expect(result.excluded).toEqual([FEE_FREE.id]);
    });

    it('a saved charge whose saved parent is absent from the Bulk is excluded', () => {
        const parent = editOp(BUY_A);
        const ops = [parent, editOp(FEE_B)];
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(result.candidates).toEqual([]);
        expect(result.excluded).toEqual([FEE_B.id]);
    });

    // Note for the implementer: `linkSelection` reads a parent id ≤ 0 as «no parent» (`parentOf`), and `bulkLinkSelection`
    // gives a create a negative mirror id, so a charge whose owner is a NEW row reads as free to the bare «Link» rule
    // (the selection bar never met it: an indented charge has no checkbox). These two cases ask for more than
    // «bulkLinkSelection ok»: a charge owned by another operation of the Bulk is linked, whatever that owner is.
    it('a new charge under another parent here is no candidate, and has no id to exclude (owner a new row)', () => {
        const parent = editOp(BUY_B);
        const ops = [createOp('n-buy', newBuyFields()), createOp('n-fee', newFeeFields(), {chargeOf: 'n-buy', followsParent: true}), parent];
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(result.candidates).toEqual([]);
        expect(result.excluded).toEqual([]);
    });

    it('a new charge under another SAVED parent here is no candidate', () => {
        const parent = editOp(BUY_B);
        const ops = [editOp(BUY_A), createOp('n-fee', newFeeFields(), {chargeOf: 't-501', followsParent: true}), parent];
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(result.candidates).toEqual([]);
        expect(result.excluded).toEqual([]);
    });

    it('a saved free charge linked here with «Link» to a NEW parent row is excluded (the DB still lists it as free)', () => {
        const parent = editOp(BUY_B);
        const ops = [createOp('n-buy', newBuyFields()), editOp(FEE_FREE, {chargeOf: 'n-buy'}), parent];
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(result.candidates).toEqual([]);
        expect(result.excluded).toEqual([FEE_FREE.id]);
    });

    it('a charge already under this parent (linked, «scollega» in this form, or new) is neither: it is in the section', () => {
        const ops = [...twoParents(), createOp('n-fee', newFeeFields(), {chargeOf: 't-501', followsParent: true})].map((op) => (op.op === 'edit' && op.txId === TAX_A.id ? ({...op, parentUnlink: true} as PendingOp) : op));
        const parent = byTxId(ops, BUY_A.id);
        const result = bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS);
        expect(result.candidates).toEqual([]);
        expect(result.excluded).toEqual([]);
    });

    it('the probe’s asset decides, not the parent’s saved fields', () => {
        const parent = editOp(BUY_B);
        const ops = [parent, createOp('f-101', newFeeFields()), createOp('f-202', newFeeFields({asset_id: 202}))];
        expect(tempIds(bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS).candidates), 'the form left on asset 101').toEqual(['f-101']);
        expect(tempIds(bulkChargeCandidates(parent, {...probeOf(parent), asset_id: 202}, ops, get, LINK_OPTS).candidates), 'the form moved to asset 202').toEqual(['f-202']);
    });

    it('the probe’s broker decides: a charge on another broker is no candidate', () => {
        const parent = editOp(BUY_B);
        const ops = [parent, createOp('f-77', newFeeFields()), createOp('f-88', newFeeFields({broker_id: 88}))];
        expect(tempIds(bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS).candidates), 'the form on broker 77').toEqual(['f-77']);
        expect(tempIds(bulkChargeCandidates(parent, {...probeOf(parent), broker_id: 88}, ops, get, LINK_OPTS).candidates), 'the form moved to broker 88').toEqual(['f-88']);
    });

    it('parent null (its form creates it): the probe stands in, and the probe is never a candidate nor added to the operations', () => {
        const ops = [createOp('n-fee', newFeeFields()), editOp(FEE_FREE), editOp(FEE_A)];
        const result = bulkChargeCandidates(null, PROBE_BUY, ops, get, LINK_OPTS);
        expect(tempIds(result.candidates)).toEqual(['n-fee', 't-520']);
        expect(result.excluded, 'FEE_A still has its saved parent').toEqual([FEE_A.id]);
        expect(ops).toHaveLength(3);
    });

    it('a probe whose type is no parent offers nothing', () => {
        const ops = [createOp('n-fee', newFeeFields()), editOp(FEE_FREE)];
        for (const type of ['FEE', 'TAX', 'TRANSFER']) {
            expect(bulkChargeCandidates(null, {...PROBE_BUY, type}, ops, get, LINK_OPTS).candidates, `probe ${type}`).toEqual([]);
        }
    });

    it('the type of a row is read through typeOf: a row read as a FEE is a candidate, a FEE read as a parent type is not', () => {
        const parent = editOp(BUY_B);
        const ops = [parent, createOp('as-fee', {...newFeeFields(), type: 'BUY' as DraftFields['type']}), createOp('as-buy', newFeeFields())];
        const typeOf = (op: PendingOp): string => (op.tempId === 'as-fee' ? 'FEE' : op.tempId === 'as-buy' ? 'BUY' : op.fields.type);
        expect(tempIds(bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS, typeOf).candidates)).toEqual(['as-fee']);
    });

    it('a user who cannot edit the broker is offered nothing from the Bulk', () => {
        const parent = editOp(BUY_B);
        const ops = [parent, createOp('n-fee', newFeeFields()), editOp(FEE_FREE)];
        expect(bulkChargeCandidates(parent, probeOf(parent), ops, get, {...LINK_OPTS, canEdit: () => false}).candidates).toEqual([]);
    });

    it('reads its inputs as given', () => {
        const ops = [...twoParents(), createOp('n-fee', newFeeFields()), editOp(FEE_FREE, {markedDelete: true})];
        const before = snapshot(ops);
        const parent = byTxId(ops, BUY_B.id);
        const probe = {...probeOf(parent), asset_id: 101};
        const probeBefore = snapshot(probe);
        bulkChargeCandidates(parent, probe, ops, get, LINK_OPTS);
        bulkChargeCandidates(null, probe, ops, get, LINK_OPTS);
        expect(ops).toEqual(before);
        expect(probe).toEqual(probeBefore);
    });
});

describe('TL-2 applyChargeDrafts — a Bulk row picked in a parent’s form is the selection’s «Link»', () => {
    it('a saved charge kept with its parent «del», picked in ANOTHER parent’s form: the same operation as linkInBulk', () => {
        const base = twoParents();
        const kept = applyDeleteChoice(base, planBulkDelete(base, ['t-501'], allRead), 'keep', get);
        const fee = byTxId(kept, FEE_A.id) as WithChoice;
        expect({chargeOf: fee.chargeOf, parentUnlink: fee.parentUnlink, byParentChoice: fee.byParentChoice}, 'premise: kept under its parent «del»').toEqual({chargeOf: 't-501', parentUnlink: true, byParentChoice: true});
        const other = byTxId(kept, BUY_B.id);
        // The form of BUY_B: its own charges (none in the Bulk) plus the FEE picked from the Bulk's mirror (no parent).
        const picked = chargeFromPicked({...FEE_A, parent_transaction_id: null});
        expect(picked, 'premise: the picked FEE is a saved draft linked here').toMatchObject({key: `saved-${FEE_A.id}`, id: FEE_A.id, linkNew: true, state: 'linked'});
        const drafts = [...chargeDraftsFor(other, kept, get), picked as ChargeDraft];

        const viaForm = byTxId(applyChargeDrafts(other, kept, drafts, makeDeps()), FEE_A.id) as WithChoice;
        const viaLink = byTxId(tl3LinkInBulk(kept, other, [byTxId(kept, FEE_A.id)]), FEE_A.id);

        expect({chargeOf: viaForm.chargeOf, parentUnlink: viaForm.parentUnlink, byParentChoice: viaForm.byParentChoice}, '«Restore» on the old parent must not take it back').toEqual({chargeOf: 't-511', parentUnlink: undefined, byParentChoice: undefined});
        expect(viaForm).toEqual(viaLink);
    });

    it('a new free charge picked (its op-<tempId> draft): the same create, under the parent, no copy, no followsParent', () => {
        const parent = editOp(BUY_B);
        const fee = createOp('n-fee', newFeeFields());
        const ops = [parent, fee];
        const draft: ChargeDraft = {key: 'op-n-fee', id: null, type: 'FEE', cash: fee.fields.cash ? {...fee.fields.cash} : null, description: fee.fields.description ?? '', original: null, state: 'linked'};
        const deps = makeDeps();

        const out = applyChargeDrafts(parent, ops, [draft], deps);

        expect(tempIds(out), 'still one FEE: the Bulk row itself').toEqual(['t-511', 'n-fee']);
        expect(deps.newChargeOp).not.toHaveBeenCalled();
        const linked = byTempId(out, 'n-fee');
        expect({chargeOf: linked.chargeOf, followsParent: linked.followsParent}).toEqual({chargeOf: 't-511', followsParent: undefined});
        expect(linked).toEqual(byTempId(tl3LinkInBulk(ops, parent, [fee]), 'n-fee'));
    });

    it('a free «Clona» copy picked (its op-<tempId> draft) loses clonedFields, as linkInBulk does', () => {
        const parent = editOp(BUY_B);
        const fields = newFeeFields();
        const fee = {...createOp('c-fee', fields), clonedFields: structuredClone(fields)} as WithClone;
        const ops = [parent, fee];
        const draft: ChargeDraft = {key: 'op-c-fee', id: null, type: 'FEE', cash: fields.cash ? {...fields.cash} : null, description: fields.description ?? '', original: null, state: 'linked'};

        const linked = byTempId(applyChargeDrafts(parent, ops, [draft], makeDeps()), 'c-fee') as WithClone;

        expect({chargeOf: linked.chargeOf, clonedFields: linked.clonedFields}, 'linked by hand: it no longer leaves with a parent').toEqual({chargeOf: 't-511', clonedFields: undefined});
        expect(linked).toEqual(byTempId(tl3LinkInBulk(ops, parent, [fee]), 'c-fee'));
    });
});

/**
 * TL-2, case 1 — a Bulk row picked in a parent's form, then taken back out of the section before «Apply». The section
 * drops an id-null draft on the trash (`TxFormChargesSection.remove`), so the form's answer leaves it out; a `delete` or
 * an `unlink` draft for it can only reach `applyChargeDrafts` some other way, and must not hurt it either. The row was
 * never this parent's: it stays in the Bulk, free, with its values, and the picker offers it again.
 */
describe('TL-2 applyChargeDrafts — a Bulk row picked, then taken back out of the section, stays in the Bulk', () => {
    /** BUY_A with its FEE and TAX adopted (the form's own charges), plus a new free FEE typed in the Bulk. */
    function parentAndFreeFee(): {parent: PendingOp; fee: PendingOp; ops: PendingOp[]} {
        const fee = createOp('n-fee', newFeeFields());
        const ops = [...adoptCharges([editOp(BUY_A), editOp(FEE_A), editOp(TAX_A)], get), fee];
        return {parent: byTxId(ops, BUY_A.id), fee, ops};
    }

    /** The draft of a Bulk create as the picker hands it (`op-<tempId>`, no id), in `state`. */
    function pickedDraft(op: PendingOp, state: ChargeDraft['state']): ChargeDraft {
        return {key: `op-${op.tempId}`, id: null, type: op.fields.type as ChargeDraft['type'], cash: op.fields.cash ? {...op.fields.cash} : null, description: op.fields.description ?? '', original: null, state};
    }

    /** The row stayed as it was — free, its values unchanged — and the picker of the same parent offers it again. */
    function expectStillFreeAndOffered(out: readonly PendingOp[], parent: PendingOp, fee: PendingOp): void {
        const after = byTempId(out, fee.tempId);
        expect(after.chargeOf, 'free: no parent').toBeUndefined();
        expect(after, 'the same row, with its values').toEqual(fee);
        const offered = bulkChargeCandidates(byTxId(out, BUY_A.id), probeOf(parent), out, get, LINK_OPTS).candidates;
        expect(tempIds(offered), 'the picker offers it again').toContain(fee.tempId);
    }

    it('premise: the new free FEE is offered in the parent’s form', () => {
        const {parent, fee, ops} = parentAndFreeFee();
        expect(tempIds(bulkChargeCandidates(parent, probeOf(parent), ops, get, LINK_OPTS).candidates)).toContain(fee.tempId);
    });

    it('(a) trashed in the section (the form leaves its draft out): the free create stays as it was', () => {
        const {parent, fee, ops} = parentAndFreeFee();
        const before = snapshot(ops);
        const drafts = chargeDraftsFor(parent, ops, get);
        expect(
            drafts.map((d) => d.key),
            'premise: the form answers with its own charges only',
        ).not.toContain(`op-${fee.tempId}`);

        const out = applyChargeDrafts(parent, ops, drafts, makeDeps());

        expect(tempIds(out), 'no row lost, none added').toEqual(tempIds(ops));
        expectStillFreeAndOffered(out, parent, fee);
        expect(byTxId(out, FEE_A.id).chargeOf, 'the parent’s own charges untouched').toBe('t-501');
        expect(ops).toEqual(before);
    });

    it('(b) a `delete` draft for a free create not under this parent: it stays, unchanged, still free', () => {
        const {parent, fee, ops} = parentAndFreeFee();
        const before = snapshot(ops);
        const deps = makeDeps();

        const out = applyChargeDrafts(parent, ops, [...chargeDraftsFor(parent, ops, get), pickedDraft(fee, 'delete')], deps);

        expect(tempIds(out), 'still in the Bulk').toEqual(tempIds(ops));
        expectStillFreeAndOffered(out, parent, fee);
        expect(deps.newChargeOp).not.toHaveBeenCalled();
        expect(ops).toEqual(before);
    });

    it('(b) a `delete` draft for a create under ANOTHER parent: it stays under that parent', () => {
        const parent = editOp(BUY_B);
        const other = createOp('n-buy', newBuyFields());
        const fee = createOp('n-fee', newFeeFields(), {chargeOf: 'n-buy', followsParent: true});
        const ops = [other, fee, parent];

        const out = applyChargeDrafts(parent, ops, [pickedDraft(fee, 'delete')], makeDeps());

        expect(tempIds(out)).toEqual(['n-buy', 'n-fee', 't-511']);
        expect(byTempId(out, 'n-fee')).toEqual(fee);
    });

    it('(c) guard: a `delete` draft for a create under THIS parent still removes it', () => {
        const parent = editOp(BUY_B);
        const fee = createOp('n-fee', newFeeFields(), {chargeOf: 't-511', followsParent: true});
        const ops = [parent, fee];

        const out = applyChargeDrafts(parent, ops, [pickedDraft(fee, 'delete')], makeDeps());

        expect(tempIds(out), 'the parent’s own new charge leaves the Bulk').toEqual(['t-511']);
    });

    it('(d) an `unlink` draft for a picked new row (never linked): it stays, free, with its values', () => {
        const {parent, fee, ops} = parentAndFreeFee();
        const before = snapshot(ops);

        const out = applyChargeDrafts(parent, ops, [...chargeDraftsFor(parent, ops, get), pickedDraft(fee, 'unlink')], makeDeps());

        expect(tempIds(out)).toEqual(tempIds(ops));
        expectStillFreeAndOffered(out, parent, fee);
        expect(ops).toEqual(before);
    });
});
