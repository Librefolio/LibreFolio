/**
 * bulkCharges.ts — the linked charges of the Bulk editor, as operations (project 66, F7-b, model H).
 *
 * A charge (a FEE or a TAX) brought into the Bulk is a `PendingOp` of its own, owned by its parent through `chargeOf`
 * (the parent's `tempId`), never through `pairedWith`: the pairs' code is not touched. The link that changes lives on
 * the charge: `parentUnlink` («scollega»: `parent_transaction_id: 0`), `parentLinkId` (a saved parent absent from the
 * Bulk), and a create born in its parent's form carries `followsParent`. This module is the pure half of the model
 * (contract 66-F7 §10, corrected by §11); `TransactionBulkModal` wires it.
 *
 * The values of a charge are held as the editor holds every amount (`fieldsFromTx`, W-B65): a magnitude, the type
 * carries the sign. `ChargeDraft` (`../form/txCharges.ts`) holds magnitudes too, so they pass through unchanged.
 */
import type {TXReadItem} from '../types';
import type {PendingOp} from './txBulkTypes';
import {chargesFromRows, type ChargeDraft, type ChargeType} from '../form/txCharges';
import {exactDecimalEqual} from '../txPayloadHelpers';

type StoreGet = (id: number) => TXReadItem | undefined;
type ChargeFlag = 'chargeOf' | 'parentUnlink' | 'parentLinkId' | 'followsParent';

/** What the payload of a charge carries to name its parent: a create of the batch by its `ref`, or a saved id (0 =
 *  unlink). Never both (`chargeParentTwice`). */
export type ChargeParentFields = {parent_ref: string} | {parent_transaction_id: number};

/** What `applyChargeDrafts` takes from the editor. Both may hand back operations without `chargeOf`/`followsParent`:
 *  setting them is this module's job. */
export interface ChargeDraftDeps {
    /** The edit operation of a saved row, read from the store; `null` when the store does not hold it. */
    editOpFromTx: (id: number) => PendingOp | null;
    /** A create for a new charge typed in the parent's form. */
    newChargeOp: (draft: ChargeDraft, parent: PendingOp) => PendingOp;
}

function isChargeType(type: string): type is ChargeType {
    return type === 'FEE' || type === 'TAX';
}

/** The saved parent of a saved row (`parent_transaction_id`), `null` for none or for a create. */
function savedParentId(op: PendingOp, get: StoreGet): number | null {
    if (op.op !== 'edit') return null;
    const id = get(op.txId)?.parent_transaction_id ?? null;
    return id != null && id > 0 ? id : null;
}

/** A copy of `op` without these keys: a flag that is off is absent, never `false`, so a round trip changes nothing. */
function without(op: PendingOp, ...keys: ChargeFlag[]): PendingOp {
    const next = {...op} as PendingOp & Record<string, unknown>;
    for (const key of keys) delete next[key];
    return next;
}

/** The parent operation `op` names, if present. */
function ownerOf(op: PendingOp, ops: readonly PendingOp[]): PendingOp | undefined {
    if (op.chargeOf === undefined) return undefined;
    return ops.find((other) => other.tempId === op.chargeOf && other !== op);
}

/**
 * A present parent adopts its saved charges: a row whose saved `parent_transaction_id` is P, with no `chargeOf`,
 * `parentUnlink` nor `parentLinkId`, takes as `chargeOf` the edit operation of P, if the Bulk holds it. A `parentLinkId`
 * whose parent arrived becomes `chargeOf`. A `chargeOf` already set is kept. Pairs untouched; idempotent; a new array.
 */
export function adoptCharges(ops: readonly PendingOp[], get: StoreGet): PendingOp[] {
    const byTxId = new Map<number, string>();
    for (const op of ops) if (op.op === 'edit' && !op.inaccessible && !byTxId.has(op.txId)) byTxId.set(op.txId, op.tempId);
    return ops.map((op) => {
        if (op.chargeOf !== undefined) return op;
        if (op.parentLinkId !== undefined) {
            const owner = byTxId.get(op.parentLinkId);
            if (owner === undefined || owner === op.tempId) return op;
            return {...without(op, 'parentLinkId'), chargeOf: owner};
        }
        if (op.parentUnlink) return op;
        const parentId = savedParentId(op, get);
        if (parentId === null) return op;
        const owner = byTxId.get(parentId);
        if (owner === undefined || owner === op.tempId) return op;
        return {...op, chargeOf: owner};
    });
}

/** A reset regenerated a parent's `tempId`: every charge naming the old one names the new one (§11.2). */
export function remapChargeOf(ops: readonly PendingOp[], fromTempId: string, toTempId: string): PendingOp[] {
    return ops.map((op) => (op.chargeOf === fromTempId ? {...op, chargeOf: toTempId} : op));
}

/** The one predicate of «sits under its parent» (§11.7): owned by a present parent and linked to it, or unlinked from a
 *  parent marked for deletion (the state it keeps under it). */
export function isUnderParent(op: PendingOp, ops: readonly PendingOp[]): boolean {
    const owner = ownerOf(op, ops);
    if (!owner) return false;
    if (!op.parentUnlink) return true;
    return owner.op === 'edit' && owner.markedDelete;
}

/**
 * The parent's charges as the form's drafts: its `chargeOf` operations of a charge type. A saved one is keyed
 * `saved-<id>`, has the store's values as `original` (as `chargesFromRows` reads them), its state from the operation
 * (`delete` / `unlink` / `linked`), and `linkNew` when its saved parent is not this one (a link made in this Bulk).
 * A new one is keyed `op-<tempId>`. The current values are the operation's.
 */
export function chargeDraftsFor(parent: PendingOp, ops: readonly PendingOp[], get: StoreGet): ChargeDraft[] {
    const parentTxId = parent.op === 'edit' ? parent.txId : null;
    const drafts: ChargeDraft[] = [];
    for (const op of ops) {
        if (op === parent || op.chargeOf !== parent.tempId || !isChargeType(op.fields.type)) continue;
        const type = op.fields.type;
        const cash = op.fields.cash ? {amount: op.fields.cash.amount, code: op.fields.cash.code} : null;
        const description = op.fields.description ?? '';
        if (op.op === 'create') {
            drafts.push({key: `op-${op.tempId}`, id: null, type, cash, description, original: null, state: 'linked'});
            continue;
        }
        const saved = get(op.txId);
        const original = saved ? (chargesFromRows([saved])[0]?.original ?? null) : null;
        const state = op.markedDelete ? 'delete' : op.parentUnlink ? 'unlink' : 'linked';
        const draft: ChargeDraft = {key: `saved-${op.txId}`, id: op.txId, type, cash, description, original, state};
        if (parentTxId === null || savedParentId(op, get) !== parentTxId) draft.linkNew = true;
        drafts.push(draft);
    }
    return drafts;
}

/** `op` with the draft's type, cash and note, written only where they differ: an unchanged draft changes nothing. */
function withDraftValues(op: PendingOp, draft: ChargeDraft): PendingOp {
    const fields = op.fields;
    const cash = draft.cash ? {code: draft.cash.code, amount: draft.cash.amount} : null;
    const sameCash = fields.cash == null || cash === null ? (fields.cash ?? null) === cash : fields.cash.code === cash.code && exactDecimalEqual(fields.cash.amount, cash.amount);
    if (fields.type === draft.type && sameCash && (fields.description ?? '') === draft.description) return {...op};
    return {...op, fields: {...fields, type: draft.type, cash: sameCash ? fields.cash : cash, description: draft.description}};
}

/**
 * The form's answer (`_charges`) back onto the operations, one way: nothing typed is lost.
 *   - type, cash and note go to the charge's operation;
 *   - a saved one: `delete` → `markedDelete`, `unlink` → `parentUnlink` (`chargeOf` kept), `linked` clears both;
 *   - a `linkNew` (a link made here, never saved) unlinked, or left out by the form, only undoes that link;
 *   - a new draft → a create from `newChargeOp`, owned by the parent and following it (`followsParent`);
 *   - a create of the parent (`op-<tempId>`) deleted, or left out by the form (trashed there), leaves the Bulk;
 *   - a `linkNew` absent from the Bulk is added from the store (`editOpFromTx`).
 * Every other operation comes out as it went in; the input is not mutated.
 */
export function applyChargeDrafts(parent: PendingOp, ops: readonly PendingOp[], drafts: readonly ChargeDraft[], deps: ChargeDraftDeps): PendingOp[] {
    const out: PendingOp[] = [...ops];
    const handled = new Set<string>();
    for (const draft of drafts) {
        if (draft.id === null) {
            const tempId = draft.key.startsWith('op-') ? draft.key.slice(3) : null;
            const at = tempId === null ? -1 : out.findIndex((op) => op.op === 'create' && op.tempId === tempId);
            if (at < 0) {
                if (draft.state !== 'linked') continue;
                const made = deps.newChargeOp(draft, parent);
                handled.add(made.tempId);
                out.push({...made, chargeOf: parent.tempId, followsParent: true});
                continue;
            }
            handled.add(out[at].tempId);
            if (draft.state === 'delete') {
                out.splice(at, 1);
                continue;
            }
            const valued = withDraftValues(out[at], draft);
            if (draft.state === 'unlink') {
                // A new charge taken out of its parent: a create of its own, with the values it followed.
                const {broker_id, asset_id, date} = parent.fields;
                const standalone = without(valued, 'chargeOf', 'followsParent');
                out[at] = valued.followsParent ? {...standalone, fields: {...standalone.fields, broker_id, asset_id, date}} : standalone;
                continue;
            }
            out[at] = {...valued, chargeOf: parent.tempId};
            continue;
        }

        let at = out.findIndex((op) => op.op === 'edit' && op.txId === draft.id);
        if (draft.linkNew && draft.state === 'unlink') {
            // Never linked to this parent: unlinking it undoes the link made here, nothing more.
            if (at >= 0) {
                handled.add(out[at].tempId);
                if (out[at].chargeOf === parent.tempId) out[at] = without(out[at], 'chargeOf');
            }
            continue;
        }
        if (at < 0) {
            const fresh = deps.editOpFromTx(draft.id);
            if (!fresh) continue;
            out.push(fresh);
            at = out.length - 1;
        }
        handled.add(out[at].tempId);
        const valued = withDraftValues(out[at], draft);
        if (valued.op !== 'edit') continue;
        if (draft.state === 'delete') {
            out[at] = {...without(valued, 'parentUnlink', 'parentLinkId'), chargeOf: parent.tempId, markedDelete: true} as PendingOp;
        } else if (draft.state === 'unlink') {
            out[at] = {...without(valued, 'parentLinkId'), chargeOf: parent.tempId, markedDelete: false, parentUnlink: true} as PendingOp;
        } else {
            out[at] = {...without(valued, 'parentUnlink', 'parentLinkId'), chargeOf: parent.tempId, markedDelete: false} as PendingOp;
        }
    }
    // What the form left out: a create it trashed leaves; a saved charge it dropped was a link made here (the form
    // drops only those, `TxFormChargesSection`), so that link is undone.
    return out.flatMap((op) => {
        if (op.chargeOf !== parent.tempId || handled.has(op.tempId) || op === parent) return [op];
        if (op.op === 'create') return [];
        if (!isChargeType(op.fields.type)) return [op];
        return [without(op, 'chargeOf')];
    });
}

/**
 * How the payload of `op` names its parent; `null` when it sends nothing about it.
 *   - a row marked for deletion: nothing (it is a delete);
 *   - `parentUnlink` on a saved row with a saved parent: `parent_transaction_id: 0`;
 *   - `chargeOf` a create: `parent_ref` = that create's `tempId` (its `ref`, `parentNeedsRef`);
 *   - `chargeOf` a saved parent: its id, unless it is already the saved parent of this row;
 *   - `parentLinkId`: that id, unless already saved.
 */
export function chargeParentFields(op: PendingOp, ops: readonly PendingOp[], get: StoreGet): ChargeParentFields | null {
    if (op.chargeOf === undefined && !op.parentUnlink && op.parentLinkId === undefined) return null;
    if (op.op === 'edit' && op.markedDelete) return null;
    const saved = savedParentId(op, get);
    if (op.parentUnlink) return saved !== null ? {parent_transaction_id: 0} : null;
    const owner = ownerOf(op, ops);
    if (owner) {
        if (owner.op === 'create') return {parent_ref: owner.tempId};
        return saved === owner.txId ? null : {parent_transaction_id: owner.txId};
    }
    if (op.parentLinkId !== undefined) return saved === op.parentLinkId ? null : {parent_transaction_id: op.parentLinkId};
    return null;
}

/** A create carries a `ref` when an operation of the Bulk names it as its parent (`chargeOf`). An unused `ref` is
 *  harmless, so every named one gets it, whatever the state of the charges naming it. */
export function parentNeedsRef(op: PendingOp, ops: readonly PendingOp[]): boolean {
    if (op.op !== 'create') return false;
    return ops.some((other) => other !== op && other.chargeOf === op.tempId);
}

/** The charges «scollega» under a parent «del»: they feed the F6 banner until F7-c. */
export function chargeUnlinkList(ops: readonly PendingOp[]): PendingOp[] {
    return ops.filter((op) => op.parentUnlink === true && !(op.op === 'edit' && op.markedDelete) && isUnderParent(op, ops));
}
