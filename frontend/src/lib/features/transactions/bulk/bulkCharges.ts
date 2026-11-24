/**
 * bulkCharges.ts — the linked charges of the Bulk editor, as operations (project 66, F7-b, model H).
 *
 * A charge (a FEE or a TAX) brought into the Bulk is a `PendingOp` of its own, owned by its parent through `chargeOf`
 * (the parent's `tempId`), never through `pairedWith`: the pairs' code is not touched. The link that changes lives on
 * the charge: `parentUnlink` («scollega»: `parent_transaction_id: 0`), `parentLinkId` (a saved parent absent from the
 * Bulk), and a create born in its parent's form carries `followsParent`. This module is the pure half of the model
 * (contract 66-F7 §10, corrected by §11); `TransactionBulkModal` wires it. F7-c1 (§13–§15) adds the grid's groups:
 * `foldBulkCharges` draws each open parent's charges right after it, `rowAnchor` names the row that stands for an
 * operation on screen.
 *
 * The values of a charge are held as the editor holds every amount (`fieldsFromTx`, W-B65): a magnitude, the type
 * carries the sign. `ChargeDraft` (`../form/txCharges.ts`) holds magnitudes too, so they pass through unchanged.
 */
import type {TXReadItem} from '../types';
import type {DraftFields, PendingOp} from './txBulkTypes';
import {chargesFromRows, type ChargeDraft, type ChargeType} from '../form/txCharges';
import {exactDecimalEqual} from '../txPayloadHelpers';
import {linkSelection, type LinkOptions, type LinkReason} from '../chargeLinkRules';

type StoreGet = (id: number) => TXReadItem | undefined;
type ChargeFlag = 'chargeOf' | 'parentUnlink' | 'parentLinkId' | 'followsParent' | 'byParentChoice' | 'clonedFields';

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
    /** 66 C22c: the store, for `unlinkCharge` (a link made here undone back to what it was before it). */
    get: StoreGet;
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

/** What «sits under its parent» reads of a row: the operations of the Bulk, and the rows `buildBulkRowLabels` labels. */
export interface ChargeLinkRow {
    tempId: string;
    op?: 'create' | 'edit';
    markedDelete?: boolean;
    chargeOf?: string;
    parentUnlink?: boolean;
    /** The visible half this hidden half of a pair names (the Bulk's pairs). */
    pairedWith?: string;
}

/** The parent operation `op` names, if present. */
function ownerOf<R extends ChargeLinkRow>(op: R, ops: readonly R[]): R | undefined {
    if (op.chargeOf === undefined) return undefined;
    return ops.find((other) => other.tempId === op.chargeOf && other !== op);
}

/**
 * 66 C22c: a charge's link undone — the one rule of every path that unlinks a charge (a reset or «Undo split» that makes
 * its parent a leg again, a restore under a parent still «del», «unlink» in its Form or in its parent's Form, «Keep» on
 * a parent's delete). Undoing a link brings the charge back to what it was before that link; `parentUnlink` («unlink»,
 * which sends `parent_transaction_id: 0`) cuts only a SAVED link:
 *   - its saved parent is its current owner (`chargeOf`, or `parentLinkId` naming it) → `parentUnlink`, the owner kept;
 *   - it has a saved parent, but another owner now (unlinked from the saved one, then linked here: «Link» refuses a
 *     charge that still has a parent) → `parentUnlink`, the link made here dropped: unlinked from its saved parent, as
 *     before that link — under that parent again when the Bulk holds it, as it was;
 *   - no saved parent (a link made only in this Bulk, or a new charge) → the link dropped and nothing else: the charge
 *     is back as saved, with no «unlink» badge and nothing to send about a parent (F7 §12.6, F7-d). A new charge that
 *     followed its parent keeps the parent's broker, asset and date as its own, as «Keep» on a parent's delete does.
 * Pure: returns a new operation.
 */
export function unlinkCharge(op: PendingOp, ops: readonly PendingOp[], get: StoreGet): PendingOp {
    const saved = savedParentId(op, get);
    const owner = ownerOf(op, ops);
    if (saved === null) {
        const own = without(op, 'chargeOf', 'parentLinkId', 'parentUnlink', 'followsParent', 'byParentChoice', 'clonedFields');
        if (op.op !== 'create' || !op.followsParent || !owner) return own;
        const {broker_id, asset_id, date} = owner.fields;
        return {...own, fields: {...own.fields, broker_id, asset_id, date}} as PendingOp;
    }
    const savedOwner = owner?.op === 'edit' && owner.txId === saved ? owner : ops.find((other) => other !== op && other.op === 'edit' && other.txId === saved);
    const unlinked = {...without(op, 'chargeOf', 'parentLinkId', 'followsParent', 'clonedFields'), parentUnlink: true} as PendingOp;
    return savedOwner ? ({...unlinked, chargeOf: savedOwner.tempId} as PendingOp) : unlinked;
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

/** 66 C22: the one predicate of «leg of a pair» (rule 8: a leg is neither a parent nor a charge). Every merge of the Bulk —
 *  a saved pair loaded, a merge queued for the save (`pendingPromotes`), two new rows merged — goes through
 *  `collapseIntoPaired`, which names the visible half on the hidden one (`pairedWith`); a saved pair split here loses it.
 *  A hidden half whose partner is missing (a W4b placeholder) is still a leg. */
export function isPairLeg<R extends {tempId: string; pairedWith?: string}>(op: R, ops: readonly R[]): boolean {
    return op.pairedWith !== undefined || ops.some((other) => other.pairedWith === op.tempId);
}

/** The one predicate of «sits under its parent» (§11.7): owned by a present parent and linked to it, or unlinked from a
 *  parent marked for deletion (the state it keeps under it). 66 C21: never under a leg of a pair (rule 8: a leg is no
 *  parent) — a charge «del» or unlinked of a row merged here is a row of its own, never hidden with the leg. */
export function isUnderParent<R extends ChargeLinkRow>(op: R, ops: readonly R[]): boolean {
    const owner = ownerOf(op, ops);
    if (!owner) return false;
    if (isPairLeg(owner, ops)) return false;
    if (!op.parentUnlink) return true;
    return owner.op === 'edit' && owner.markedDelete === true;
}

/**
 * The grid's rows (F7-c1, BK2): the top-level rows in their order, each open parent (`expanded`, by `tempId`) followed by
 * its charges (`isUnderParent`) in the order of the operations. A closed parent's charges are not drawn. A new array;
 * neither input is mutated.
 */
export function foldBulkCharges(top: readonly PendingOp[], ops: readonly PendingOp[], expanded: ReadonlySet<string>): PendingOp[] {
    const under = new Map<string, PendingOp[]>();
    for (const op of ops) {
        if (op.chargeOf === undefined || !expanded.has(op.chargeOf) || !isUnderParent(op, ops)) continue;
        under.set(op.chargeOf, [...(under.get(op.chargeOf) ?? []), op]);
    }
    const rows: PendingOp[] = [];
    for (const row of top) {
        rows.push(row);
        if (expanded.has(row.tempId)) rows.push(...(under.get(row.tempId) ?? []));
    }
    return rows;
}

/**
 * The row on screen that stands for an operation (F7-c1): a charge under its parent is its own row while the group is
 * open, the parent's row while it is closed; any other operation is its visible row (`pairedWith ?? tempId`). The
 * highlight of an issue and the jump to it read it.
 */
export function rowAnchor(op: PendingOp, ops: readonly PendingOp[], expanded: ReadonlySet<string>): string {
    if (op.chargeOf !== undefined && isUnderParent(op, ops)) return expanded.has(op.chargeOf) ? op.tempId : op.chargeOf;
    return op.pairedWith ?? op.tempId;
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
 *   - a saved one: `delete` → `markedDelete`, `unlink` → `parentUnlink` (`chargeOf` kept), `linked` clears them and the
 *     choices of another link (`byParentChoice`, `clonedFields`): the same operation as the bar's «Link» (66 TL-2);
 *   - a create of the Bulk picked in the form (66 TL-2, `op-<tempId>` not under this parent) joins as «Link» joins it;
 *     a `delete` never takes it out of the Bulk;
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
                // 66 TL-2: only a create of this parent leaves; a row picked from the Bulk was never its, and stays.
                if (out[at].chargeOf === parent.tempId) out.splice(at, 1);
                continue;
            }
            const valued = withDraftValues(out[at], draft);
            if (draft.state === 'unlink') {
                // A new charge taken out of its parent: a create of its own, with the values it followed.
                const {broker_id, asset_id, date} = parent.fields;
                const standalone = without(valued, 'chargeOf', 'followsParent', 'clonedFields');
                out[at] = valued.followsParent ? {...standalone, fields: {...standalone.fields, broker_id, asset_id, date}} : standalone;
                continue;
            }
            // 66 TL-2: a create picked from elsewhere in the Bulk joins as «Link» joins it (`linkInBulk`): its earlier link
            // choices go. One already under this parent keeps what it has (a «Clona» copy stays a copy).
            out[at] = out[at].chargeOf === parent.tempId ? {...valued, chargeOf: parent.tempId} : {...without(valued, 'parentUnlink', 'parentLinkId', 'byParentChoice', 'clonedFields'), chargeOf: parent.tempId};
            continue;
        }

        let at = out.findIndex((op) => op.op === 'edit' && op.txId === draft.id);
        if (draft.linkNew && draft.state === 'unlink') {
            // Never linked to this parent: unlinking it undoes the link made here, nothing more.
            if (at >= 0) {
                handled.add(out[at].tempId);
                if (out[at].chargeOf === parent.tempId) out[at] = unlinkCharge(out[at], out, deps.get);
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
            // Not a `linkNew`: this parent is the charge's saved one, so «unlink» cuts a saved link (`unlinkCharge`'s first case).
            out[at] = {...without(valued, 'parentLinkId'), chargeOf: parent.tempId, markedDelete: false, parentUnlink: true} as PendingOp;
        } else {
            // 66 TL-2: the same operation the bar's «Link» gives (`linkInBulk`): a choice set by another parent's delete goes too.
            out[at] = {...without(valued, 'parentUnlink', 'parentLinkId', 'byParentChoice', 'clonedFields'), chargeOf: parent.tempId, markedDelete: false} as PendingOp;
        }
    }
    // What the form left out: a create it trashed leaves; a saved charge it dropped was a link made here (the form
    // drops only those, `TxFormChargesSection`), so that link is undone.
    return out.flatMap((op) => {
        if (op.chargeOf !== parent.tempId || handled.has(op.tempId) || op === parent) return [op];
        if (op.op === 'create') return [];
        if (!isChargeType(op.fields.type)) return [op];
        return [unlinkCharge(op, out, deps.get)];
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

// ---------------------------------------------------------------------------
// F7-c2 — deleting a parent inside the Bulk: the panel V1 (contract 66-F7 §17, corrected by §18, §19)
// ---------------------------------------------------------------------------

/** Whether a charge's read is still pending (`loading`) or failed (`failed`) for this saved row; `null` when read. */
export type ChargesUnread = 'loading' | 'failed' | null;

/** One decision for «Delete» and «Delete selected», taken on the state before any of it (`planBulkDelete`). */
export interface BulkDeletePlan {
    /** Saved selected rows that flip: «del», or restored. */
    toggles: {tempId: string; deleted: boolean}[];
    /** New selected rows, which leave the Bulk. */
    removals: string[];
    /** Parents going «del» that have linked charges: they wait for the user's choice. */
    needsChoice: string[];
    /** Parents going «del» whose charges are being read. */
    waiting: string[];
    /** Parents going «del» whose charges could not be read. */
    skipped: string[];
    /** The panel's numbers: the charges «Keep» keeps, the rows «Delete all» deletes or removes. */
    counts: {keep: number; all: number};
}

/** The charges still linked to a parent (§17.1): under it, not «del», not unlinked; new ones included; in ops order. */
export function linkedChargesOf(parent: PendingOp, ops: readonly PendingOp[]): PendingOp[] {
    return ops.filter((op) => op !== parent && op.chargeOf === parent.tempId && !op.parentUnlink && !(op.op === 'edit' && op.markedDelete) && isUnderParent(op, ops));
}

/**
 * 66 C21: the rows (by `tempId`) that still hold linked charges, so no pair-promote may take them (rule 6): a charge
 * linked under them (`linkedChargesOf`), or a saved charge of theirs the Bulk does not hold yet — the saved count minus
 * the saved charges of that row held here, wherever they sit now (a charge moved to another parent with «Link» is held,
 * so the row it left is free). One pass over `ops`.
 */
export function rowsWithLinkedCharges(ops: readonly PendingOp[], get: StoreGet): Set<string> {
    const byTempId = new Map(ops.map((op) => [op.tempId, op]));
    const heldBySavedParent = new Map<number, number>();
    for (const op of ops) {
        const parentId = savedParentId(op, get);
        if (parentId !== null) heldBySavedParent.set(parentId, (heldBySavedParent.get(parentId) ?? 0) + 1);
    }
    const result = new Set<string>();
    for (const op of ops) {
        // `isUnderParent` holds here: the owner is present and the link not dropped.
        if (op.chargeOf !== undefined && !op.parentUnlink && !(op.op === 'edit' && op.markedDelete)) {
            const owner = byTempId.get(op.chargeOf);
            if (owner && owner !== op) result.add(owner.tempId);
        }
        if (op.op === 'edit' && !op.inaccessible && (get(op.txId)?.charges_count ?? 0) > (heldBySavedParent.get(op.txId) ?? 0)) result.add(op.tempId);
    }
    return result;
}

/**
 * The plan of a delete on these selected rows (a single «Delete» is a selection of one). A saved row flips; a new one
 * leaves; a saved row going «del» whose charges are not read (`unread`) waits or is skipped; a parent going «del» with
 * linked charges asks for a choice — its charges that are selected themselves toggle on their own instead (the choice on
 * the row wins over the cascade). The counts are the page's (66 F6): «Keep» = the linked charges of the parents asking;
 * «Delete all» = those parents, those charges and every other selected row going «del» or leaving.
 */
export function planBulkDelete(ops: readonly PendingOp[], selectedTempIds: readonly string[], unread: (op: PendingOp) => ChargesUnread): BulkDeletePlan {
    const selected = new Set(selectedTempIds);
    const plan: BulkDeletePlan = {toggles: [], removals: [], needsChoice: [], waiting: [], skipped: [], counts: {keep: 0, all: 0}};
    const seen = new Set<string>();
    for (const tempId of selectedTempIds) {
        if (seen.has(tempId)) continue;
        seen.add(tempId);
        const op = ops.find((o) => o.tempId === tempId);
        if (!op) continue;
        if (op.op === 'create') {
            plan.removals.push(tempId);
            continue;
        }
        const deleted = !op.markedDelete;
        if (deleted) {
            const state = unread(op);
            if (state === 'loading') {
                plan.waiting.push(tempId);
                continue;
            }
            if (state === 'failed') {
                plan.skipped.push(tempId);
                continue;
            }
            const linked = linkedChargesOf(op, ops).filter((c) => !selected.has(c.tempId));
            if (linked.length > 0) {
                plan.needsChoice.push(tempId);
                plan.counts.keep += linked.length;
                continue;
            }
        }
        plan.toggles.push({tempId, deleted});
    }
    plan.counts.all = plan.needsChoice.length + plan.counts.keep + plan.toggles.filter((t) => t.deleted).length + plan.removals.length;
    return plan;
}

/**
 * Rows leaving the Bulk: each with its pair's hidden half; a parent's new charges born in its form and never opened on
 * their own (`followsParent`) leave with it (§12.4, narrowed by 66 F7-d §21.3), and so do the copies «Clona» brought
 * with it while nobody changed them (66 TL-3, `isUntouchedClone`; the FEE consultant's 📌); every other charge stays — a new one
 * linked with «Link» or opened alone as a new row of its own, a saved one owned by nobody (§11.2). The one removal of
 * the Bulk (`removeRow`, and the plan's removals).
 */
export function withoutRows(ops: readonly PendingOp[], tempIds: Iterable<string>): PendingOp[] {
    const named = new Set(tempIds);
    const removed = new Set(ops.filter((op) => named.has(op.tempId) || (op.pairedWith !== undefined && named.has(op.pairedWith))).map((op) => op.tempId));
    const takenAlong = (op: PendingOp): boolean => op.op === 'create' && op.chargeOf !== undefined && removed.has(op.chargeOf) && (op.followsParent === true || isUntouchedClone(op));
    return ops.filter((op) => !removed.has(op.tempId) && !takenAlong(op)).map((op) => (op.chargeOf !== undefined && removed.has(op.chargeOf) ? without(op, 'chargeOf', 'followsParent', 'clonedFields') : op));
}

/**
 * The plan and the user's choice onto the operations; a new array, the input untouched. `choice` matters only when
 * the plan has parents asking for one.
 *   - «keep»: each such parent «del»; its saved linked charges unlinked (`parentUnlink` + `byParentChoice`); a `linkNew`
 *     one (linked here, never saved under it: `get`) only loses its local link; its new ones become rows of their own,
 *     with the broker, asset and date they followed;
 *   - «all»: each such parent «del»; its saved linked charges «del» (`byParentChoice`); its new ones leave;
 *   - a toggle flips its row: a restored parent takes back what a choice set on its charges (`byParentChoice`), a
 *     charge unlinked by hand stays; a charge restored under a parent still «del» is unlinked, never linked to it;
 *   - the removals leave (`withoutRows`).
 */
export function applyDeleteChoice(ops: readonly PendingOp[], plan: BulkDeletePlan, choice: 'keep' | 'all', get: StoreGet): PendingOp[] {
    const replaced = new Map<string, PendingOp | null>();
    const ownToggle = new Set([...plan.toggles.map((t) => t.tempId), ...plan.removals]);
    for (const parentId of plan.needsChoice) {
        const parent = ops.find((op) => op.tempId === parentId);
        if (!parent || parent.op !== 'edit') continue;
        replaced.set(parentId, {...parent, markedDelete: true});
        for (const charge of linkedChargesOf(parent, ops)) {
            if (ownToggle.has(charge.tempId)) continue;
            if (charge.op === 'create') {
                if (choice === 'all') {
                    replaced.set(charge.tempId, null);
                    continue;
                }
                const own = without(charge, 'chargeOf', 'followsParent');
                const {broker_id, asset_id, date} = parent.fields;
                replaced.set(charge.tempId, charge.followsParent ? {...own, fields: {...own.fields, broker_id, asset_id, date}} : own);
                continue;
            }
            if (choice === 'all') {
                replaced.set(charge.tempId, {...without(charge, 'parentUnlink'), markedDelete: true, byParentChoice: true} as PendingOp);
            } else if (savedParentId(charge, get) !== parent.txId) {
                replaced.set(charge.tempId, unlinkCharge(charge, ops, get));
            } else {
                replaced.set(charge.tempId, {...unlinkCharge(charge, ops, get), byParentChoice: true});
            }
        }
    }
    const restored = new Set(plan.toggles.filter((t) => !t.deleted).map((t) => t.tempId));
    for (const {tempId, deleted} of plan.toggles) {
        const op = ops.find((o) => o.tempId === tempId);
        if (!op || op.op !== 'edit') continue;
        if (deleted) {
            replaced.set(tempId, {...op, markedDelete: true});
            continue;
        }
        const owner = op.chargeOf !== undefined ? ops.find((o) => o.tempId === op.chargeOf) : undefined;
        const ownerStaysDeleted = owner?.op === 'edit' && owner.markedDelete && !restored.has(owner.tempId);
        replaced.set(tempId, ownerStaysDeleted ? unlinkCharge({...op, markedDelete: false} as PendingOp, ops, get) : {...op, markedDelete: false});
        for (const charge of ops) {
            if (charge.chargeOf !== tempId || !charge.byParentChoice || charge.op !== 'edit' || replaced.has(charge.tempId)) continue;
            replaced.set(charge.tempId, {...without(charge, 'parentUnlink', 'byParentChoice'), markedDelete: false} as PendingOp);
        }
    }
    const out = ops.flatMap((op) => {
        if (!replaced.has(op.tempId)) return [op];
        const next = replaced.get(op.tempId);
        return next ? [next] : [];
    });
    return plan.removals.length > 0 ? withoutRows(out, plan.removals) : out;
}

// ---------------------------------------------------------------------------
// F7-d — U3, «Link» on the Bulk's selection (contract 66-F7 §20.5, corrected by §21.2, §22.2, §23.4)
// ---------------------------------------------------------------------------

/** Why «Link» in the Bulk is off: the page's reasons, and a row marked for deletion in the selection. */
export type BulkLinkReason = LinkReason | 'deleted';

/** What «Link» does with the Bulk's selection; `params` names the first row that breaks the rule. */
export type BulkLinkSelection = {kind: 'hidden'} | {kind: 'disabled'; reason: BulkLinkReason; params: {op: PendingOp; type: string}} | {kind: 'ok'; parent: PendingOp; charges: PendingOp[]};

/**
 * «Link» on the selected rows of the Bulk, by the page's rules (`linkSelection`) read on mirror rows:
 *   - the values are the operation's (broker, asset, type, date); a create has a negative synthetic id;
 *   - the parent is the one in the Bulk (`chargeOf`), or `parentLinkId`, or the saved one — none after `parentUnlink`
 *     (an unlink already done here: «unlink first» is satisfied);
 *   - a pair is the Bulk's (`pairedWith`), as the payload sends it: a new pair counts, a saved pair split here does not
 *     (§23.4, corrected after the advisor's review).
 * Every `hidden` outcome of `linkSelection` wins; then a selected row marked for deletion turns «Link» off (`deleted`:
 * the backend refuses a deleted parent, and linking a deleted charge means nothing); then the page's reasons.
 */
export function bulkLinkSelection(rows: readonly PendingOp[], ops: readonly PendingOp[], get: StoreGet, opts: LinkOptions, typeOf: (op: PendingOp) => string = (op) => op.fields.type): BulkLinkSelection {
    const synthetic = new Map<string, number>();
    for (const op of [...ops, ...rows]) if (!synthetic.has(op.tempId)) synthetic.set(op.tempId, -(synthetic.size + 1));
    const mirrorId = (op: PendingOp): number => (op.op === 'edit' ? op.txId : synthetic.get(op.tempId)!);
    const parentIdOf = (op: PendingOp): number | null => {
        if (op.parentUnlink) return null;
        const owner = ownerOf(op, ops);
        if (owner) return mirrorId(owner);
        if (op.parentLinkId !== undefined) return op.parentLinkId;
        return savedParentId(op, get);
    };
    // Rule 8 (`charges.py`, `row_is_paired`): a leg of a pair is neither a parent nor a charge. The pair is the Bulk's,
    // as the payload sends it: a hidden half names its visible one (`pairedWith`). A new pair counts; a saved pair split
    // here does not (the batch splits it before it links the charges).
    const pairIdOf = (op: PendingOp): number | null => {
        const partner = op.pairedWith !== undefined ? ops.find((d) => d.tempId === op.pairedWith) : ops.find((d) => d.pairedWith === op.tempId);
        if (!partner) return op.pairedWith !== undefined ? -1 : null;
        return mirrorId(partner);
    };
    const byMirror = new Map<TXReadItem, PendingOp>();
    const mirrors = rows.map((op): TXReadItem => {
        const saved = op.op === 'edit' ? get(op.txId) : undefined;
        const mirror: TXReadItem = {
            ...(saved ?? {}),
            id: mirrorId(op),
            broker_id: op.fields.broker_id,
            asset_id: op.fields.asset_id ?? null,
            type: typeOf(op),
            date: op.fields.date,
            related_transaction_id: pairIdOf(op),
            parent_transaction_id: parentIdOf(op),
        } as TXReadItem;
        byMirror.set(mirror, op);
        return mirror;
    });
    const result = linkSelection(mirrors, opts);
    if (result.kind === 'hidden') return result;
    const deleted = rows.find((op) => op.op === 'edit' && op.markedDelete);
    if (deleted) return {kind: 'disabled', reason: 'deleted', params: {op: deleted, type: typeOf(deleted)}};
    if (result.kind === 'disabled') {
        const op = rows[mirrors.findIndex((m) => m.id === result.params.id)] ?? rows[0];
        return {kind: 'disabled', reason: result.reason, params: {op, type: typeOf(op)}};
    }
    return {kind: 'ok', parent: byMirror.get(result.parent)!, charges: result.charges.map((c) => byMirror.get(c)!)};
}

/**
 * The confirmation of «Link» in the Bulk: each charge is owned by the parent (`chargeOf`), its earlier link choices
 * dropped (`parentUnlink`, `parentLinkId`, `byParentChoice`, and a «Clona» copy's `clonedFields`: linked by hand, it no
 * longer leaves with a parent); `followsParent` is kept as it is. A new array.
 */
export function linkInBulk(ops: readonly PendingOp[], parent: PendingOp, charges: readonly PendingOp[]): PendingOp[] {
    const ids = new Set(charges.map((c) => c.tempId));
    return ops.map((op) => (ids.has(op.tempId) && op !== parent ? {...without(op, 'parentUnlink', 'parentLinkId', 'byParentChoice', 'clonedFields'), chargeOf: parent.tempId} : op));
}

// ---------------------------------------------------------------------------
// TL-3 — «Clona» carries the linked-charges structure (FEE consultant, lot TL-3)
// ---------------------------------------------------------------------------

/** Two sets of fields equal by value: decimals exactly (`'10' == '10.00'`), tags by value. */
export function sameDraftFields(a: DraftFields, b: DraftFields): boolean {
    const sameMoney = (x: {code: string; amount: string} | null, y: {code: string; amount: string} | null): boolean => (x === null || y === null ? x === y : x.code === y.code && exactDecimalEqual(x.amount, y.amount));
    return (
        a.broker_id === b.broker_id &&
        (a.asset_id ?? null) === (b.asset_id ?? null) &&
        a.type === b.type &&
        a.date === b.date &&
        exactDecimalEqual(a.quantity, b.quantity) &&
        sameMoney(a.cash ?? null, b.cash ?? null) &&
        sameMoney(a.cost_basis_override ?? null, b.cost_basis_override ?? null) &&
        (a.description ?? '') === (b.description ?? '') &&
        (a.asset_event_id ?? null) === (b.asset_event_id ?? null) &&
        (a.cost_basis_mode ?? null) === (b.cost_basis_mode ?? null) &&
        a.tags.length === b.tags.length &&
        a.tags.every((tag, i) => tag === b.tags[i])
    );
}

/** A charge copy brought by «Clona» that nobody changed: a create whose fields still equal the ones it was born with. */
export function isUntouchedClone(op: PendingOp): boolean {
    return op.op === 'create' && op.clonedFields !== undefined && sameDraftFields(op.fields, op.clonedFields);
}

/** Where the copy of a charge cloned alone is born: under an owner of the Bulk, linked to a saved parent absent from it,
 *  or free — with the reason the user is told (`null`: nothing to tell). */
export type CloneLink = {kind: 'owner'; chargeOf: string} | {kind: 'saved'; parentLinkId: number} | {kind: 'free'; reason: BulkLinkReason | 'hidden' | null};

/**
 * The link of the copy of charge `src` cloned alone inside the Bulk (66 TL-3, the developer: «già collegata»): the same
 * parent as its original. `copyFields` are the copy's own fields (a charge that followed its parent is copied with what
 * it showed).
 *   - the original already «scollega» → free, nothing to tell;
 *   - its owner is in the Bulk → the «Link» rule decides (`bulkLinkSelection` on the owner and a probe of the copy), so a
 *     copy is never born with a link «Link» would refuse: ok → under the owner; off → free, with that reason (a «del»
 *     owner `deleted`, a leg of a pair `paired`); hidden → free, `hidden`;
 *   - no owner here: `parentLinkId`, else the saved parent, is the copy's `parentLinkId`; none → free.
 * Pure: reads its inputs as given.
 */
export function cloneChargeLink(src: PendingOp, copyFields: DraftFields, ops: readonly PendingOp[], get: StoreGet, opts: LinkOptions, typeOf: (op: PendingOp) => string = (op) => op.fields.type): CloneLink {
    if (src.parentUnlink) return {kind: 'free', reason: null};
    const owner = ownerOf(src, ops);
    if (owner) {
        const probe: PendingOp = {op: 'create', tempId: `${src.tempId}~clone-probe`, createdSeq: src.createdSeq, fields: copyFields, link_uuid: null};
        const typeOfProbe = (op: PendingOp): string => (op === probe ? copyFields.type : typeOf(op));
        const verdict = bulkLinkSelection([owner, probe], [...ops, probe], get, opts, typeOfProbe);
        if (verdict.kind === 'ok') return {kind: 'owner', chargeOf: owner.tempId};
        return {kind: 'free', reason: verdict.kind === 'disabled' ? verdict.reason : 'hidden'};
    }
    if (src.parentLinkId !== undefined) return {kind: 'saved', parentLinkId: src.parentLinkId};
    const saved = savedParentId(src, get);
    return saved !== null ? {kind: 'saved', parentLinkId: saved} : {kind: 'free', reason: null};
}

/** The copies of the charges still linked under `parent` (`linkedChargesOf`: neither «del» nor «scollega», new ones
 *  included), in the order of the operations: each made by `makeCopy`, owned by the parent's copy and holding the values
 *  it was born with (`clonedFields`). */
export function cloneChargesUnder(parent: PendingOp, parentCopyTempId: string, ops: readonly PendingOp[], makeCopy: (charge: PendingOp) => PendingOp): PendingOp[] {
    return linkedChargesOf(parent, ops).map((charge) => {
        const copy = makeCopy(charge);
        return {...copy, chargeOf: parentCopyTempId, clonedFields: structuredClone(copy.fields)};
    });
}

/**
 * The page's clone intent (66 TL-3): `sources[i]` is the saved original of `clones[i]`.
 *   - a cloned charge whose saved parent is cloned too: under that parent's clone, part of the structure (`clonedFields`);
 *   - a cloned charge alone: linked to its saved parent (`parentLinkId`), as the developer decided («già collegata»);
 *   - the charges read (`readCharges`, by `parent_transaction_id`) of each cloned source, not cloned themselves: copies
 *     made by `makeCreate`, under the source's clone (`clonedFields`). `null` (the read failed): none.
 * `expanded`: the clones that got charges (their group starts open: the user brought them). The clones keep their
 * order; each parent's read copies follow the clones.
 */
export function wireClonedRows(sources: readonly TXReadItem[], clones: readonly PendingOp[], readCharges: readonly TXReadItem[] | null, makeCreate: (tx: TXReadItem) => PendingOp): {ops: PendingOp[]; expanded: string[]} {
    const cloneOf = new Map<number, string>();
    sources.forEach((source, at) => {
        if (clones[at] && !cloneOf.has(source.id)) cloneOf.set(source.id, clones[at].tempId);
    });
    const expanded: string[] = [];
    const open = (tempId: string) => {
        if (!expanded.includes(tempId)) expanded.push(tempId);
    };
    const out: PendingOp[] = clones.map((clone, at) => {
        const parentId = sources[at]?.parent_transaction_id ?? null;
        if (parentId === null || parentId <= 0) return clone;
        const parentClone = cloneOf.get(parentId);
        if (parentClone !== undefined && parentClone !== clone.tempId) {
            open(parentClone);
            return {...clone, chargeOf: parentClone, clonedFields: structuredClone(clone.fields)};
        }
        return {...clone, parentLinkId: parentId};
    });
    if (readCharges !== null) {
        const seen = new Set<number>(sources.map((source) => source.id));
        for (const charge of readCharges) {
            const parentId = charge.parent_transaction_id ?? null;
            const parentClone = parentId === null ? undefined : cloneOf.get(parentId);
            if (parentClone === undefined || seen.has(charge.id)) continue;
            seen.add(charge.id);
            const copy = makeCreate(charge);
            out.push({...copy, chargeOf: parentClone, clonedFields: structuredClone(copy.fields)});
            open(parentClone);
        }
    }
    return {ops: out, expanded};
}

// ---------------------------------------------------------------------------
// TL-2 — the charges picker of a parent's form sees the Bulk's rows (FEE consultant, lot TL-2)
// ---------------------------------------------------------------------------

/** What the form tells the Bulk about the parent it shows: its current broker, asset and type. */
export interface BulkChargeProbe {
    broker_id: number;
    asset_id: number | null;
    type: string;
}

/**
 * The Bulk's operations the charges picker of a parent's form may offer (66 TL-2), by the selection's «Link» rule.
 * `parent` is the parent's operation, or `null` while its form creates it (a probe create stands in); the probe carries the
 * form's current broker, asset and type. Every charge (by `typeOf`) other than the parent, not a hidden half of a pair:
 *   - already owned by this parent (`chargeOf`): in its section, neither offered nor excluded;
 *   - owned here by another operation and not unlinked: linked — a new parent of the Bulk has no id the bare rule could
 *     read, so this is said here; a saved one is excluded;
 *   - otherwise `bulkLinkSelection([probe, charge])`: ok → offered; off or hidden → a saved one is excluded (the form drops
 *     it from the database's rows: «del», linked to a parent outside the Bulk).
 * Pure.
 */
export function bulkChargeCandidates(parent: PendingOp | null, probe: BulkChargeProbe, ops: readonly PendingOp[], get: StoreGet, opts: LinkOptions, typeOf: (op: PendingOp) => string = (op) => op.fields.type): {candidates: PendingOp[]; excluded: number[]} {
    const base: DraftFields = parent ? parent.fields : {broker_id: probe.broker_id, asset_id: probe.asset_id, type: probe.type as DraftFields['type'], date: '', quantity: '0', cash: null, tags: [], description: '', asset_event_id: null, cost_basis_override: null, cost_basis_mode: null};
    const probeParent: PendingOp = parent ? ({...parent, fields: {...base, broker_id: probe.broker_id, asset_id: probe.asset_id, type: probe.type as DraftFields['type']}} as PendingOp) : {op: 'create', tempId: '~tl2-probe-parent', createdSeq: Number.MAX_SAFE_INTEGER, fields: base, link_uuid: null};
    const withProbe = parent ? ops.map((op) => (op === parent ? probeParent : op)) : [...ops, probeParent];
    const typeOfProbe = (op: PendingOp): string => (op === probeParent ? probe.type : typeOf(op));
    const candidates: PendingOp[] = [];
    const excluded: number[] = [];
    for (const op of ops) {
        if (op === parent || op.pairedWith !== undefined || !isChargeType(typeOf(op))) continue;
        if (parent && op.chargeOf === parent.tempId) continue;
        const exclude = () => {
            if (op.op === 'edit') excluded.push(op.txId);
        };
        const owner = ownerOf(op, ops);
        if (owner && !op.parentUnlink) {
            exclude();
            continue;
        }
        const verdict = bulkLinkSelection([probeParent, op], withProbe, get, opts, typeOfProbe);
        if (verdict.kind === 'ok') candidates.push(op);
        else exclude();
    }
    return {candidates, excluded};
}
