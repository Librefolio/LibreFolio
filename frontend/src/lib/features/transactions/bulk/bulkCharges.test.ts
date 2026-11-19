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
 *   - `chargeUnlinkList`  the charges «scollega» under a parent «del»: they feed the F6 banner until F7-c.
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
import {adoptCharges, applyChargeDrafts, chargeDraftsFor, chargeParentFields, chargeUnlinkList, isUnderParent, parentNeedsRef, remapChargeOf} from './bulkCharges';

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

/** The two dependencies `applyChargeDrafts` takes from the editor, as spies. Both return operations WITHOUT `chargeOf`
 *  and `followsParent`: setting them is the module's job, whatever the editor hands back. */
function makeDeps() {
    const editOpFromTx = vi.fn((id: number): PendingOp | null => {
        const r = get(id);
        return r ? editOp(r, {tempId: `fresh-${id}`}) : null;
    });
    const newChargeOp = vi.fn((draft: ChargeDraft, parent: PendingOp): PendingOp => createOp(`made-${draft.key}`, {...parent.fields, type: draft.type, cash: draft.cash ? {...draft.cash} : null, description: draft.description, quantity: '0', tags: []}));
    return {editOpFromTx, newChargeOp};
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
// chargeParentFields / parentNeedsRef / chargeUnlinkList
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

describe('chargeUnlinkList — the charges «scollega» under a parent «del» (the F6 banner until F7-c)', () => {
    it('lists exactly those: not a deleted charge, not a linked one, not one unlinked from a parent that stays', () => {
        const ops = [editOp(BUY_A, {markedDelete: true}), editOp(FEE_A, {chargeOf: 't-501', parentUnlink: true}), editOp(TAX_A, {chargeOf: 't-501', markedDelete: true}), editOp(BUY_B), editOp(FEE_B, {chargeOf: 't-511', parentUnlink: true}), editOp(FEE_FREE, {chargeOf: 't-501'})];

        expect(chargeUnlinkList(ops).map((op) => op.tempId)).toEqual([`t-${FEE_A.id}`]);
    });

    it('nothing when no parent is deleted', () => {
        expect(chargeUnlinkList(adoptCharges([editOp(BUY_A), editOp(FEE_A), editOp(TAX_A)], get))).toEqual([]);
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
