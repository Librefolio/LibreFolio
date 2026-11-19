/**
 * The rules behind «link the charges» from the table's selection bar and «delete a parent that has charges» (project 66,
 * lot F6), as pure functions.
 *
 * The backend checks the same rules on the batch (`backend/app/services/transactions/charges.py`, rules 1–8): here
 * they only decide whether the selection bar offers «Link», and why it is off. A charge is a FEE or a TAX, a parent one
 * of the parent types (`chargeRole` of the type table).
 */
import type {TXReadItem} from './types';

export type LinkRole = 'charge' | 'parent' | null;

/** Why «Link» is off, in the order the rules are checked. */
export type LinkReason = 'twoParents' | 'paired' | 'linked' | 'otherBroker' | 'otherAsset' | 'noAsset';

export type LinkSelection = {kind: 'hidden'} | {kind: 'disabled'; reason: LinkReason; params: {id: number; type: string; date: string}} | {kind: 'ok'; parent: TXReadItem; charges: TXReadItem[]};

export interface LinkOptions {
    /** The type's `chargeRole`. */
    roleOf: (type: string) => LinkRole;
    /** Whether the user edits rows of this broker. */
    canEdit: (brokerId: number) => boolean;
}

/** One parent and the charges of a delete that leaves some of them out of the selection. */
export interface DeletePlanEntry {
    parent: TXReadItem;
    charges: TXReadItem[];
}

const assetOf = (row: TXReadItem): number | null => row.asset_id ?? null;
const parentOf = (row: TXReadItem): number | null => {
    const id = row.parent_transaction_id ?? 0;
    return id > 0 ? id : null;
};

/**
 * What «Link» does with this selection.
 *  - `hidden`: the selection is not «one or more parents and charges» a user can edit; the button is not there.
 *  - `disabled`: a rule is broken; `reason` is the earliest broken rule, `params` names the first row that breaks it.
 *  - `ok`: one parent and the charges to link to it (those already linked to it are left out, in selection order).
 */
export function linkSelection(rows: TXReadItem[], {roleOf, canEdit}: LinkOptions): LinkSelection {
    if (rows.length < 2) return {kind: 'hidden'};
    const parents: TXReadItem[] = [];
    const charges: TXReadItem[] = [];
    for (const row of rows) {
        const role = roleOf(row.type);
        if (role === null || !canEdit(row.broker_id)) return {kind: 'hidden'};
        (role === 'parent' ? parents : charges).push(row);
    }
    if (parents.length === 0 || charges.length === 0) return {kind: 'hidden'};
    const parent = parents[0];
    const toLink = parents.length === 1 ? charges.filter((c) => parentOf(c) !== parent.id) : charges;
    if (parents.length === 1 && toLink.length === 0) return {kind: 'hidden'};

    const off = (reason: LinkReason, row: TXReadItem): LinkSelection => ({kind: 'disabled', reason, params: {id: row.id, type: row.type, date: row.date}});
    if (parents.length > 1) return off('twoParents', parents[1]);
    const paired = [parent, ...toLink].sort((a, b) => rows.indexOf(a) - rows.indexOf(b)).find((r) => r.related_transaction_id != null);
    if (paired) return off('paired', paired);
    const checks: [LinkReason, (c: TXReadItem) => boolean][] = [
        ['linked', (c) => parentOf(c) !== null],
        ['otherBroker', (c) => c.broker_id !== parent.broker_id],
        ['otherAsset', (c) => assetOf(c) !== null && assetOf(c) !== assetOf(parent)],
        ['noAsset', (c) => assetOf(c) === null && assetOf(parent) !== null],
    ];
    for (const [reason, breaks] of checks) {
        const row = toLink.find(breaks);
        if (row) return off(reason, row);
    }
    return {kind: 'ok', parent, charges: toLink};
}

/** The batch that links the charges to the parent: one update per charge, all pass or none. */
export function linkCommit(parent: TXReadItem, charges: TXReadItem[]): {updates: {id: number; parent_transaction_id: number}[]} {
    return {updates: charges.map((c) => ({id: c.id, parent_transaction_id: parent.id}))};
}

/**
 * The parents of a delete whose charges are not all selected, each with all its charges: the panel asks what to do
 * with them. Empty: nothing to ask, the delete goes to the Bulk as it is.
 */
export function deletePlan(selected: TXReadItem[], chargesByParent: Map<number, TXReadItem[]>): DeletePlanEntry[] {
    const ids = new Set(selected.map((r) => r.id));
    const plan: DeletePlanEntry[] = [];
    for (const row of selected) {
        if ((row.charges_count ?? 0) <= 0) continue;
        const charges = chargesByParent.get(row.id) ?? [];
        if (charges.length === 0 || charges.every((c) => ids.has(c.id))) continue;
        plan.push({parent: row, charges});
    }
    return plan;
}

/**
 * What the Bulk receives after the panel: `all` deletes the selection and every charge of the plan; `keep` deletes the
 * selection and unlinks the plan's charges that are not selected (a selected charge is deleted, as asked).
 */
export function deleteIntent(selectedIds: number[], plan: DeletePlanEntry[], choice: 'all' | 'keep'): {txIds: number[]; unlinkIds: number[]} {
    const txIds = [...new Set(selectedIds)];
    const chosen = new Set(txIds);
    const rest: number[] = [];
    for (const entry of plan) {
        for (const c of entry.charges) {
            if (!chosen.has(c.id) && !rest.includes(c.id)) rest.push(c.id);
        }
    }
    return choice === 'all' ? {txIds: [...txIds, ...rest], unlinkIds: []} : {txIds, unlinkIds: rest};
}
