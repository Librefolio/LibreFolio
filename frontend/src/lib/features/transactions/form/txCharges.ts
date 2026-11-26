/**
 * txCharges.ts — the linked charges of a parent in the transaction form (project 66, issue #25).
 *
 * A FEE or a TAX (a *charge*) can point at the transaction it belongs to, its *parent* (a BUY, SELL, DIVIDEND, INTEREST,
 * DEPOSIT or WITHDRAWAL: the type's `chargeRole`). The form of a parent lists its charges in a section of its own: the
 * rows already saved, the rows added in this form, and what the user unlinked or deleted. Every voice is only itself: the
 * parent's amount never holds its charges, and the charges are rows of their own in the batch (developer decisions of
 * 12/11/2026). This module is the section's model, pure: the rows from what the API returns, the rows the form adds, the
 * read-only total under them, and the creates, updates and deletes the batch sends.
 *
 * The form shows magnitudes and the type carries the sign (`buildSignedCash`), as for every other amount of the form.
 */
import type {TXReadItem} from '../types';
import {buildSignedCash, exactDecimalEqual, magnitudeForRule} from '$lib/features/transactions/txPayloadHelpers';
import type {TypeRule} from '$lib/features/transactions/transactionTypeStore';
import {tradeTotalWithCharges, type CashDirection, type CurrencyTotal} from './txTradeAmount';

export type ChargeType = 'FEE' | 'TAX';

/** An amount with its currency, as the form holds it: a magnitude. */
export interface ChargeCash {
    amount: string;
    code: string;
}

/** One row of the section: a saved charge, or one added in this form. */
export interface ChargeDraft {
    /** Stable UI key: `saved-<id>` for a saved row, `new-<n>` for a new one. */
    key: string;
    /** The saved id; `null` for a new row. */
    id: number | null;
    type: ChargeType;
    cash: ChargeCash | null;
    /** The charge's own note (its `description`): `''` when none. */
    description: string;
    /** The values saved, for the diff; `null` for a new row. */
    original: {type: ChargeType; cash: ChargeCash | null; description: string} | null;
    /** A saved charge the picker added to this parent's section (it belongs to no parent yet, lot F4): the batch links it. */
    linkNew?: boolean;
    /**
     * `linked`: in the section. A saved charge the user took out of it is kept with its state, so the batch and the Bulk
     * (F7) still see it: `unlink` (it stays, as a row of its own, with the changes the user typed) or `delete`. A new row
     * the user trashes simply leaves the list.
     */
    state: ChargeState;
}

export type ChargeState = 'linked' | 'unlink' | 'delete';

/** A charge's parent that is a new row of the Bulk (66 TL-11): its key (`op-<tempId>`), its name there («row 3»), its values. */
export interface HandedNewParent {
    key: string;
    ref: string;
    row: TXReadItem;
}

/** The Bulk's row behind a key `op-<tempId>`; `null` for a saved row or one typed in the form. */
export function bulkRowOf(key: string): string | null {
    return key.startsWith('op-') ? key.slice(3) : null;
}

/** What a new charge takes from its parent: the broker and the asset (rules 2 and 3), and the date it starts from. */
export interface ChargesParent {
    broker_id: number;
    asset_id: number | null;
    date: string;
}

/** How the batch names the parent: the `ref` of its create in the same batch, or its saved id. */
export type ChargesParentLink = {parent_ref: string} | {parent_transaction_id: number};

/** The operations of the charges, to join the parent's in one batch. */
export interface ChargesBatch {
    creates: Record<string, unknown>[];
    updates: Record<string, unknown>[];
    deletes: number[];
}

function isChargeType(type: string): type is ChargeType {
    return type === 'FEE' || type === 'TAX';
}

/** The rows of the section from the charges the API returns (`GET /transactions?parent_ids=…`), by id. */
export function chargesFromRows(rows: readonly TXReadItem[]): ChargeDraft[] {
    return rows
        .filter((row) => isChargeType(row.type))
        .slice()
        .sort((a, b) => a.id - b.id)
        .map((row) => {
            const cash = row.cash ? {amount: magnitudeForRule(String(row.cash.amount), 'negative'), code: row.cash.code} : null;
            const type = row.type as ChargeType;
            const description = row.description ?? '';
            return {key: `saved-${row.id}`, id: row.id, type, cash, description, original: {type, cash, description}, state: 'linked' as const};
        });
}

/** A saved charge picked to be linked to this parent (F4): its row, marked `linkNew`; `null` for a row that is no charge. */
export function chargeFromPicked(row: TXReadItem): ChargeDraft | null {
    const [draft] = chargesFromRows([row]);
    if (!draft) return null;
    // 66 TL-2: a new row of the Bulk (`_bulkKey` = `op-<tempId>`): the Bulk links that very row, never a copy of it.
    const bulkKey = (row as TXReadItem & {_bulkKey?: string})._bulkKey;
    if (bulkKey) return {key: bulkKey, id: null, type: draft.type, cash: draft.cash, description: draft.description, original: null, state: 'linked'};
    return {...draft, linkNew: true};
}

/** A new row of the given type, with no amount yet; `seq` keeps its key unique in the form. */
export function newCharge(type: ChargeType, _defaultCode: string | null, seq: number): ChargeDraft {
    return {key: `new-${seq}`, id: null, type, cash: null, description: '', original: null, state: 'linked'};
}

/** Which way the parent's cash goes, from its type's sign rule: out for a negative amount, in for a positive one. */
export function chargeCashDirection(cashSign: string): CashDirection | null {
    if (cashSign === 'negative') return 'out';
    if (cashSign === 'positive') return 'in';
    return null;
}

/** The rows the section shows and counts: the linked ones. */
export function linkedCharges(charges: readonly ChargeDraft[]): ChargeDraft[] {
    return charges.filter((charge) => charge.state === 'linked');
}

/** «Addebito totale» / «Netto incassato»: the parent's amount with its linked charges, per currency (`tradeTotalWithCharges`). */
export function chargesTotal(direction: CashDirection | null, parentCash: ChargeCash | null, charges: readonly ChargeDraft[]): CurrencyTotal[] | null {
    const linked = linkedCharges(charges);
    if (direction === null || parentCash === null || linked.length === 0) return null;
    return tradeTotalWithCharges(
        direction,
        {amount: parentCash.amount, currency: parentCash.code},
        linked.map((charge) => ({amount: charge.cash?.amount ?? '', currency: charge.cash?.code})),
    );
}

/** The linked rows that cannot be saved yet: no amount. The form marks them and does not save. */
export function chargeRowsMissingAmount(charges: readonly ChargeDraft[]): string[] {
    return linkedCharges(charges)
        .filter((charge) => !charge.cash || charge.cash.amount.trim() === '')
        .map((charge) => charge.key);
}

/** What a link needs equal on its two ends (rules 2 and 3). */
export interface LinkContext {
    broker_id: number;
    asset_id: number | null;
}

/**
 * The links made in this Bulk, not saved yet, that a change of broker or asset would break because their other end is
 * saved and cannot follow (66 TL-12): the saved charges linked under this new parent, or the saved parent of this new
 * charge. A new charge is not among them (an all-new group moves together, TL-3b), nor a charge saved under this parent.
 */
export function brokenSavedLinks<T>(current: LinkContext, next: LinkContext, charges: readonly ChargeDraft[], parent: T | null): {charges: ChargeDraft[]; parent: T | null} {
    if (current.broker_id === next.broker_id && current.asset_id === next.asset_id) return {charges: [], parent: null};
    return {charges: linkedCharges(charges).filter((charge) => charge.id !== null && charge.linkNew === true), parent};
}

/** The section's state as one string, for the form's unsaved-changes baseline and its anti-bounce. */
export function chargesKey(charges: readonly ChargeDraft[]): string {
    return JSON.stringify(charges.map((charge) => [charge.key, charge.state, charge.type, charge.cash?.amount ?? null, charge.cash?.code ?? null, charge.description, charge.linkNew === true]));
}

function sameCash(a: ChargeCash | null, b: ChargeCash | null): boolean {
    if (a === null || b === null) return a === b;
    return a.code === b.code && exactDecimalEqual(a.amount, b.amount);
}

/**
 * The creates, updates and deletes of the charges, for the batch of their parent. A linked new row is a create named to
 * its parent (`link`); a saved row sends only what changed; an unlinked one sends its changes with
 * `parent_transaction_id: 0` in one update (nothing the user typed is lost); a deleted one is a delete.
 */
export function buildChargesBatch(charges: readonly ChargeDraft[], parent: ChargesParent, link: ChargesParentLink, rules: Record<ChargeType, TypeRule>): ChargesBatch {
    const batch: ChargesBatch = {creates: [], updates: [], deletes: []};
    for (const charge of charges) {
        if (charge.state === 'delete') {
            if (charge.id !== null) batch.deletes.push(charge.id);
            continue;
        }
        const cash = buildSignedCash(charge.cash, rules[charge.type].cashSign);
        const description = charge.description.trim();
        if (charge.id === null) {
            const create: Record<string, unknown> = {broker_id: parent.broker_id, asset_id: parent.asset_id, type: charge.type, date: parent.date, cash, ...link};
            if (description !== '') create.description = description;
            batch.creates.push(create);
            continue;
        }
        const original = charge.original;
        const update: Record<string, unknown> = {id: charge.id};
        if (!original || original.type !== charge.type) update.type = charge.type;
        if (!original || !sameCash(original.cash, charge.cash)) update.cash = cash;
        if (!original || original.description.trim() !== description) update.description = description;
        if (charge.linkNew) {
            // Picked in this form: never linked, so an unlink sends nothing, a linked one always sends the link.
            if (charge.state === 'unlink') continue;
            batch.updates.push({...update, ...link});
            continue;
        }
        if (charge.state === 'unlink') update.parent_transaction_id = 0;
        if (Object.keys(update).length > 1) batch.updates.push(update);
    }
    return batch;
}
