/**
 * chargeLinkRules — the pure rules behind «link the charges» from the table and «delete a parent that has charges»
 * (project 66, lot F6). RED FIRST: `./chargeLinkRules` does not exist yet. Contract: `66-F6-contract.md` §1.
 *
 * The API this file pins (the implementer follows it):
 *
 *   type LinkRole = 'charge' | 'parent' | null;
 *   type LinkReason = 'twoParents' | 'paired' | 'linked' | 'otherBroker' | 'otherAsset' | 'noAsset';
 *   type LinkSelection =
 *       | {kind: 'hidden'}
 *       | {kind: 'disabled'; reason: LinkReason; params: {id: number; type: string; date: string}}
 *       | {kind: 'ok'; parent: TXReadItem; charges: TXReadItem[]};
 *
 *   linkSelection(rows: TXReadItem[], opts: {roleOf: (type: string) => LinkRole; canEdit: (brokerId: number) => boolean}): LinkSelection
 *   linkCommit(parent: TXReadItem, charges: TXReadItem[]): {updates: {id: number; parent_transaction_id: number}[]}
 *   isUnlinkable(row: TXReadItem, canEdit: (brokerId: number) => boolean): boolean                                   (66 TL-9)
 *   unlinkCommit(charges: TXReadItem[]): {updates: {id: number; parent_transaction_id: number}[]}                    (66 TL-9)
 *   deletePlan(selected: TXReadItem[], chargesByParent: Map<number, TXReadItem[]>): {parent: TXReadItem; charges: TXReadItem[]}[]
 *   deleteIntent(selectedIds: number[], plan: {parent: TXReadItem; charges: TXReadItem[]}[], choice: 'all' | 'keep'): {txIds: number[]; unlinkIds: number[]; chargeIds: number[]}
 *       66 F7-d (contract 66-F7 §20.2): `chargeIds` = the plan's charges that are not selected, with both choices — the
 *       Bulk marks them `byParentChoice`, so «Restore» on the parent takes them back.
 *
 * linkSelection, decided here where the contract leaves room:
 *   - every `hidden` condition wins over every `disabled` reason (the button is not there at all);
 *   - the reasons are checked reason by reason over the whole selection, in the contract's order (twoParents, paired,
 *     linked, otherBroker, otherAsset, noAsset), so the reason reported is the earliest that any row breaks;
 *   - `params` names the first row, in selection order, that breaks that reason; for `twoParents` it is the SECOND
 *     parent (the first is fine on its own: the second is the one that breaks «one parent»);
 *   - a charge already linked to the selected parent is dropped from `charges` (not an error); `charges` keeps the
 *     selection order.
 *
 * Fixtures: small factories, ids in the 910000s so they cannot be mistaken for a count or an index.
 */
import {describe, expect, it, vi} from 'vitest';
import {deleteIntent, deletePlan, isUnlinkable as rowIsUnlinkable, linkCommit, linkSelection, unlinkCommit} from './chargeLinkRules';
import type {TXReadItem} from './types';

// ─── fixtures ────────────────────────────────────────────────────────────────────────────────────────────────────

const BROKER = 11;
const OTHER_BROKER = 12;
const READ_ONLY_BROKER = 13;
const ASSET = 7;
const OTHER_ASSET = 8;

const ROLES: Record<string, 'charge' | 'parent' | null> = {
    BUY: 'parent',
    SELL: 'parent',
    DEPOSIT: 'parent',
    WITHDRAWAL: 'parent',
    FEE: 'charge',
    TAX: 'charge',
    ADJUSTMENT: null,
    TRANSFER: null,
};

const roleOf = (type: string): 'charge' | 'parent' | null => ROLES[type] ?? null;
const canEdit = (brokerId: number): boolean => brokerId !== READ_ONLY_BROKER;
const OPTS = {roleOf, canEdit};

let nextId = 910_001;

function tx(type: string, over: Partial<TXReadItem> = {}): TXReadItem {
    const id = nextId++;
    const isCharge = roleOf(type) === 'charge';
    return {
        id,
        broker_id: BROKER,
        asset_id: ASSET,
        type,
        date: '2026-05-10',
        quantity: isCharge ? '0' : '10',
        cash: {code: 'EUR', amount: isCharge ? '-2.00' : '-100.00'},
        related_transaction_id: null,
        parent_transaction_id: null,
        charges_count: 0,
        tags: [],
        description: null,
        ...over,
    };
}

const parent = (type = 'BUY', over: Partial<TXReadItem> = {}) => tx(type, over);
const charge = (type = 'FEE', over: Partial<TXReadItem> = {}) => tx(type, over);

const ids = (rows: TXReadItem[]) => rows.map((r) => r.id);
const sorted = (xs: number[]) => [...xs].sort((a, b) => a - b);

/** The offending row as `params` must name it. */
const named = (r: TXReadItem) => ({id: r.id, type: r.type, date: r.date});

// ─── linkSelection: hidden ───────────────────────────────────────────────────────────────────────────────────────

describe('linkSelection — hidden: the selection is not «a parent and its charges»', () => {
    it('is hidden with fewer than 2 rows', () => {
        expect(linkSelection([], OPTS)).toEqual({kind: 'hidden'});
        expect(linkSelection([parent()], OPTS)).toEqual({kind: 'hidden'});
        expect(linkSelection([charge()], OPTS)).toEqual({kind: 'hidden'});
    });

    it('is hidden with no charge in the selection', () => {
        expect(linkSelection([parent('BUY'), parent('SELL')], OPTS)).toEqual({kind: 'hidden'});
    });

    it('is hidden with no parent in the selection', () => {
        expect(linkSelection([charge('FEE'), charge('TAX')], OPTS)).toEqual({kind: 'hidden'});
    });

    it('is hidden when a row has no charge role (an ADJUSTMENT, a pair type)', () => {
        expect(linkSelection([parent(), charge(), tx('ADJUSTMENT')], OPTS)).toEqual({kind: 'hidden'});
        expect(linkSelection([parent(), charge(), tx('TRANSFER', {related_transaction_id: 1})], OPTS)).toEqual({kind: 'hidden'});
    });

    it('is hidden when a row sits on a broker the user cannot edit (like «promote», which disappears)', () => {
        expect(linkSelection([parent(), charge('FEE', {broker_id: READ_ONLY_BROKER})], OPTS)).toEqual({kind: 'hidden'});
        expect(linkSelection([parent('BUY', {broker_id: READ_ONLY_BROKER}), charge('FEE', {broker_id: READ_ONLY_BROKER})], OPTS)).toEqual({kind: 'hidden'});
    });

    it('is hidden when every charge is already linked to this same parent (nothing left to link)', () => {
        const buy = parent('BUY', {charges_count: 2});
        const fee = charge('FEE', {parent_transaction_id: buy.id});
        const taxCharge = charge('TAX', {parent_transaction_id: buy.id});
        expect(linkSelection([buy, fee, taxCharge], OPTS)).toEqual({kind: 'hidden'});
    });

    it('a hidden condition wins over a disabled reason', () => {
        // two parents (twoParents) + a row with no role → hidden
        expect(linkSelection([parent('BUY'), parent('SELL'), charge(), tx('ADJUSTMENT')], OPTS)).toEqual({kind: 'hidden'});
        // two parents + a row on a read-only broker → hidden
        expect(linkSelection([parent('BUY'), parent('SELL'), charge('FEE', {broker_id: READ_ONLY_BROKER})], OPTS)).toEqual({kind: 'hidden'});
        // a charge on another broker (otherBroker) that is also read-only → hidden
        expect(linkSelection([parent(), charge('FEE', {broker_id: READ_ONLY_BROKER, asset_id: OTHER_ASSET})], OPTS)).toEqual({kind: 'hidden'});
    });
});

// ─── linkSelection: disabled, one reason at a time ───────────────────────────────────────────────────────────────

describe('linkSelection — disabled: each reason, params name the first row that breaks it', () => {
    it('twoParents: more than one parent; params name the second parent', () => {
        const buy = parent('BUY');
        const fee = charge('FEE');
        const sell = parent('SELL', {date: '2026-05-11'});
        expect(linkSelection([buy, fee, sell], OPTS)).toEqual({kind: 'disabled', reason: 'twoParents', params: named(sell)});
    });

    it('paired: a row carries related_transaction_id (rule 8) — a parent', () => {
        const dep = parent('DEPOSIT', {asset_id: null, related_transaction_id: 1234});
        const fee = charge('FEE', {asset_id: null});
        expect(linkSelection([fee, dep], OPTS)).toEqual({kind: 'disabled', reason: 'paired', params: named(dep)});
    });

    it('paired: a row carries related_transaction_id (rule 8) — a charge', () => {
        const buy = parent('BUY');
        const fee = charge('FEE');
        const taxCharge = charge('TAX', {related_transaction_id: 1234});
        expect(linkSelection([buy, fee, taxCharge], OPTS)).toEqual({kind: 'disabled', reason: 'paired', params: named(taxCharge)});
    });

    it('linked: a charge already has ANOTHER parent (unlink it first)', () => {
        const buy = parent('BUY');
        const fee = charge('FEE');
        const taxCharge = charge('TAX', {parent_transaction_id: 999_999});
        expect(linkSelection([buy, fee, taxCharge], OPTS)).toEqual({kind: 'disabled', reason: 'linked', params: named(taxCharge)});
    });

    it('otherBroker: a charge on a different broker (rule 2)', () => {
        const buy = parent('BUY');
        const fee = charge('FEE', {broker_id: OTHER_BROKER});
        expect(linkSelection([buy, fee], OPTS)).toEqual({kind: 'disabled', reason: 'otherBroker', params: named(fee)});
    });

    it('otherAsset: a charge on a different asset (rule 3)', () => {
        const buy = parent('BUY');
        const fee = charge('FEE', {asset_id: OTHER_ASSET});
        expect(linkSelection([buy, fee], OPTS)).toEqual({kind: 'disabled', reason: 'otherAsset', params: named(fee)});
    });

    it('otherAsset: a charge with an asset, the parent without (rule 3)', () => {
        const dep = parent('DEPOSIT', {asset_id: null});
        const fee = charge('FEE', {asset_id: ASSET});
        expect(linkSelection([dep, fee], OPTS)).toEqual({kind: 'disabled', reason: 'otherAsset', params: named(fee)});
    });

    it('noAsset: a charge without an asset, the parent with one (D6b)', () => {
        const buy = parent('BUY');
        const fee = charge('FEE', {asset_id: null});
        expect(linkSelection([buy, fee], OPTS)).toEqual({kind: 'disabled', reason: 'noAsset', params: named(fee)});
    });

    it('params name the FIRST row, in selection order, that breaks the reason', () => {
        const buy = parent('BUY');
        const fee = charge('FEE', {broker_id: OTHER_BROKER, date: '2026-05-12'});
        const taxCharge = charge('TAX', {broker_id: OTHER_BROKER, date: '2026-05-13'});
        expect(linkSelection([taxCharge, buy, fee], OPTS)).toEqual({kind: 'disabled', reason: 'otherBroker', params: named(taxCharge)});
    });
});

// ─── linkSelection: precedence between reasons ───────────────────────────────────────────────────────────────────

describe('linkSelection — disabled: the earlier reason wins (twoParents › paired › linked › otherBroker › otherAsset › noAsset)', () => {
    it('twoParents beats paired', () => {
        const buy = parent('BUY');
        const fee = charge('FEE', {related_transaction_id: 1234});
        const sell = parent('SELL');
        expect(linkSelection([buy, fee, sell], OPTS)).toMatchObject({kind: 'disabled', reason: 'twoParents'});
    });

    it('paired beats linked', () => {
        const buy = parent('BUY');
        const fee = charge('FEE', {parent_transaction_id: 999_999});
        const taxCharge = charge('TAX', {related_transaction_id: 1234});
        expect(linkSelection([buy, fee, taxCharge], OPTS)).toEqual({kind: 'disabled', reason: 'paired', params: named(taxCharge)});
    });

    it('linked beats otherBroker', () => {
        const buy = parent('BUY');
        const fee = charge('FEE', {broker_id: OTHER_BROKER});
        const taxCharge = charge('TAX', {parent_transaction_id: 999_999});
        expect(linkSelection([buy, fee, taxCharge], OPTS)).toEqual({kind: 'disabled', reason: 'linked', params: named(taxCharge)});
    });

    it('otherBroker beats otherAsset', () => {
        const buy = parent('BUY');
        const fee = charge('FEE', {asset_id: OTHER_ASSET});
        const taxCharge = charge('TAX', {broker_id: OTHER_BROKER});
        expect(linkSelection([buy, fee, taxCharge], OPTS)).toEqual({kind: 'disabled', reason: 'otherBroker', params: named(taxCharge)});
    });

    it('otherAsset beats noAsset, even when the noAsset row comes first', () => {
        const buy = parent('BUY');
        const fee = charge('FEE', {asset_id: null});
        const taxCharge = charge('TAX', {asset_id: OTHER_ASSET});
        expect(linkSelection([buy, fee, taxCharge], OPTS)).toEqual({kind: 'disabled', reason: 'otherAsset', params: named(taxCharge)});
    });

    it('a charge already linked to THIS parent is not an error: the other charge still decides', () => {
        const buy = parent('BUY', {charges_count: 1});
        const fee = charge('FEE', {parent_transaction_id: buy.id});
        const taxCharge = charge('TAX', {broker_id: OTHER_BROKER});
        expect(linkSelection([buy, fee, taxCharge], OPTS)).toEqual({kind: 'disabled', reason: 'otherBroker', params: named(taxCharge)});
    });
});

// ─── linkSelection: ok ───────────────────────────────────────────────────────────────────────────────────────────

describe('linkSelection — ok', () => {
    it('1 BUY + FEE + TAX on the same broker and asset: the parent and both charges, in selection order', () => {
        const buy = parent('BUY');
        const fee = charge('FEE');
        const taxCharge = charge('TAX');
        const result = linkSelection([fee, buy, taxCharge], OPTS);
        expect(result.kind).toBe('ok');
        if (result.kind !== 'ok') return;
        expect(result.parent.id).toBe(buy.id);
        expect(ids(result.charges)).toEqual([fee.id, taxCharge.id]);
    });

    it('a charge already linked to this same parent is dropped from charges', () => {
        const buy = parent('BUY', {charges_count: 1});
        const fee = charge('FEE', {parent_transaction_id: buy.id});
        const taxCharge = charge('TAX');
        const result = linkSelection([buy, fee, taxCharge], OPTS);
        expect(result.kind).toBe('ok');
        if (result.kind !== 'ok') return;
        expect(result.parent.id).toBe(buy.id);
        expect(ids(result.charges)).toEqual([taxCharge.id]);
    });

    it('a charge without an asset and a parent without an asset is ok', () => {
        const dep = parent('DEPOSIT', {asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '1000.00'}});
        const fee = charge('FEE', {asset_id: null});
        const result = linkSelection([dep, fee], OPTS);
        expect(result.kind).toBe('ok');
        if (result.kind !== 'ok') return;
        expect(result.parent.id).toBe(dep.id);
        expect(ids(result.charges)).toEqual([fee.id]);
    });

    it('undefined and null asset_id count as the same «no asset»', () => {
        const dep = parent('DEPOSIT', {asset_id: undefined});
        const fee = charge('FEE', {asset_id: null});
        expect(linkSelection([dep, fee], OPTS).kind).toBe('ok');
    });
});

// ─── linkCommit ──────────────────────────────────────────────────────────────────────────────────────────────────

describe('linkCommit', () => {
    it('one update per charge, pointing at the parent, in charge order (one batch: all or none)', () => {
        const buy = parent('BUY');
        const taxCharge = charge('TAX');
        const fee = charge('FEE');
        expect(linkCommit(buy, [taxCharge, fee])).toEqual({
            updates: [
                {id: taxCharge.id, parent_transaction_id: buy.id},
                {id: fee.id, parent_transaction_id: buy.id},
            ],
        });
    });

    it('never puts the parent itself in the updates', () => {
        const buy = parent('BUY');
        const fee = charge('FEE');
        expect(linkCommit(buy, [fee]).updates.map((u) => u.id)).not.toContain(buy.id);
    });
});

// ─── isUnlinkable / unlinkCommit (66 TL-9) ────────────────────────────────────────────────────────────────────────

/**
 * «Unlink the charges» from the selection bar (TL-9). One predicate decides the number on the button, the panel and the
 * payload: the row has a saved parent (`parent_transaction_id > 0`) and the user edits its broker. The type is not asked:
 * the flow must not need the type rules (the broker page's cold path).
 */
describe('isUnlinkable (66 TL-9)', () => {
    const PARENT_ID = 919_901;
    const isUnlinkable = (row: TXReadItem, editable: (brokerId: number) => boolean = canEdit) => rowIsUnlinkable(row, editable);

    it('a FEE linked to a parent, on a broker the user edits: yes', () => {
        expect(isUnlinkable(charge('FEE', {parent_transaction_id: PARENT_ID}))).toBe(true);
    });

    it('a TAX linked to a parent, on a broker the user edits: yes', () => {
        expect(isUnlinkable(charge('TAX', {parent_transaction_id: PARENT_ID}))).toBe(true);
    });

    it('a charge with no parent (null, absent, 0): no', () => {
        const {parent_transaction_id: _left, ...absent} = charge('FEE');
        expect(isUnlinkable(charge('FEE', {parent_transaction_id: null})), 'null').toBe(false);
        expect(isUnlinkable(absent), 'absent').toBe(false);
        expect(isUnlinkable(charge('FEE', {parent_transaction_id: 0})), '0').toBe(false);
    });

    it('a parent BUY with charges: no (it has no parent of its own)', () => {
        expect(isUnlinkable(parent('BUY', {charges_count: 2}))).toBe(false);
    });

    it('a linked charge on a broker the user cannot edit: no', () => {
        expect(isUnlinkable(charge('FEE', {parent_transaction_id: PARENT_ID, broker_id: READ_ONLY_BROKER}))).toBe(false);
    });

    it('the broker asked about is the row’s own', () => {
        const editable = vi.fn<(brokerId: number) => boolean>(() => true);
        expect(isUnlinkable(charge('FEE', {parent_transaction_id: PARENT_ID, broker_id: OTHER_BROKER}), editable)).toBe(true);
        expect(editable).toHaveBeenCalledWith(OTHER_BROKER);
    });

    it('the type is not looked at: a row that is no charge type, with a parent, is unlinkable', () => {
        expect(isUnlinkable(tx('ADJUSTMENT', {parent_transaction_id: PARENT_ID}))).toBe(true);
    });
});

describe('unlinkCommit (66 TL-9)', () => {
    it('one update per charge with parent 0, in order, and nothing else (one batch: all or none)', () => {
        const taxCharge = charge('TAX', {parent_transaction_id: 919_901});
        const fee = charge('FEE', {parent_transaction_id: 919_902});
        expect(unlinkCommit([taxCharge, fee])).toEqual({
            updates: [
                {id: taxCharge.id, parent_transaction_id: 0},
                {id: fee.id, parent_transaction_id: 0},
            ],
        });
    });

    it('a single charge: one update', () => {
        const fee = charge('FEE', {parent_transaction_id: 919_901});
        expect(unlinkCommit([fee])).toEqual({updates: [{id: fee.id, parent_transaction_id: 0}]});
    });

    it('the rows handed in are left as they are', () => {
        const fee = charge('FEE', {parent_transaction_id: 919_901});
        const before = structuredClone(fee);
        unlinkCommit([fee]);
        expect(fee).toEqual(before);
    });
});

// ─── deletePlan ──────────────────────────────────────────────────────────────────────────────────────────────────

describe('deletePlan', () => {
    function family(type = 'BUY', nCharges = 2) {
        const p = parent(type, {charges_count: nCharges});
        const cs = Array.from({length: nCharges}, (_, i) => charge(i % 2 === 0 ? 'FEE' : 'TAX', {parent_transaction_id: p.id}));
        return {p, cs};
    }

    it('a parent selected alone: its charges are listed (all of them)', () => {
        const {p, cs} = family();
        const plan = deletePlan([p], new Map([[p.id, cs]]));
        expect(plan).toHaveLength(1);
        expect(plan[0].parent.id).toBe(p.id);
        expect(ids(plan[0].charges)).toEqual(ids(cs));
    });

    it('a parent with only some of its charges selected: still in the plan, with ALL its charges', () => {
        const {p, cs} = family('BUY', 3);
        const plan = deletePlan([p, cs[0]], new Map([[p.id, cs]]));
        expect(plan).toHaveLength(1);
        expect(plan[0].parent.id).toBe(p.id);
        expect(ids(plan[0].charges)).toEqual(ids(cs));
    });

    it('a parent with every charge selected: empty plan (the Bulk as today)', () => {
        const {p, cs} = family();
        expect(deletePlan([cs[1], p, cs[0]], new Map([[p.id, cs]]))).toEqual([]);
    });

    it('a selection of charges only: empty plan', () => {
        const {p, cs} = family();
        expect(deletePlan([...cs], new Map([[p.id, cs]]))).toEqual([]);
    });

    it('a parent without charges (charges_count 0) is never in the plan', () => {
        const lone = parent('SELL', {charges_count: 0});
        const {p, cs} = family();
        const plan = deletePlan([lone, p], new Map([[p.id, cs]]));
        expect(plan.map((e) => e.parent.id)).toEqual([p.id]);
    });

    it('several parents: one entry each, in selection order; a fully covered one is left out', () => {
        const a = family('BUY', 2);
        const b = family('SELL', 1);
        const c = family('DEPOSIT', 2);
        const map = new Map([
            [a.p.id, a.cs],
            [b.p.id, b.cs],
            [c.p.id, c.cs],
        ]);
        // c has every charge selected → out; b and a have charges outside the selection → in.
        const plan = deletePlan([b.p, c.p, ...c.cs, a.p, a.cs[1]], map);
        expect(plan.map((e) => e.parent.id)).toEqual([b.p.id, a.p.id]);
        expect(ids(plan[0].charges)).toEqual(ids(b.cs));
        expect(ids(plan[1].charges)).toEqual(ids(a.cs));
    });
});

// ─── deleteIntent ────────────────────────────────────────────────────────────────────────────────────────────────

describe('deleteIntent', () => {
    function planOf() {
        const buy = parent('BUY', {charges_count: 2});
        const fee = charge('FEE', {parent_transaction_id: buy.id});
        const taxCharge = charge('TAX', {parent_transaction_id: buy.id});
        const other = parent('SELL', {charges_count: 0});
        return {buy, fee, taxCharge, other, plan: [{parent: buy, charges: [fee, taxCharge]}]};
    }

    it("'all': the selection plus every charge of the plan, nothing to unlink", () => {
        const {buy, fee, taxCharge, other, plan} = planOf();
        const intent = deleteIntent([buy.id, other.id], plan, 'all');
        expect(sorted(intent.txIds)).toEqual(sorted([buy.id, other.id, fee.id, taxCharge.id]));
        expect(intent.unlinkIds).toEqual([]);
    });

    it("'all': a charge both selected and in the plan appears once", () => {
        const {buy, fee, taxCharge, plan} = planOf();
        const intent = deleteIntent([buy.id, fee.id], plan, 'all');
        expect(sorted(intent.txIds)).toEqual(sorted([buy.id, fee.id, taxCharge.id]));
        expect(new Set(intent.txIds).size).toBe(intent.txIds.length);
    });

    it("'keep': only the selection is deleted, the unselected charges of the plan are unlinked", () => {
        const {buy, fee, taxCharge, other, plan} = planOf();
        const intent = deleteIntent([buy.id, other.id], plan, 'keep');
        expect(sorted(intent.txIds)).toEqual(sorted([buy.id, other.id]));
        expect(sorted(intent.unlinkIds)).toEqual(sorted([fee.id, taxCharge.id]));
    });

    it("'keep': a selected charge is deleted, not unlinked", () => {
        const {buy, fee, taxCharge, plan} = planOf();
        const intent = deleteIntent([buy.id, fee.id], plan, 'keep');
        expect(sorted(intent.txIds)).toEqual(sorted([buy.id, fee.id]));
        expect(intent.unlinkIds).toEqual([taxCharge.id]);
    });

    it('several parents: both choices cover every entry of the plan, without duplicates', () => {
        const a = planOf();
        const b = planOf();
        const plan = [...a.plan, ...b.plan];
        const selected = [a.buy.id, b.buy.id, b.taxCharge.id];

        const all = deleteIntent(selected, plan, 'all');
        expect(sorted(all.txIds)).toEqual(sorted([a.buy.id, a.fee.id, a.taxCharge.id, b.buy.id, b.fee.id, b.taxCharge.id]));
        expect(new Set(all.txIds).size).toBe(all.txIds.length);
        expect(all.unlinkIds).toEqual([]);

        const keep = deleteIntent(selected, plan, 'keep');
        expect(sorted(keep.txIds)).toEqual(sorted(selected));
        expect(sorted(keep.unlinkIds)).toEqual(sorted([a.fee.id, a.taxCharge.id, b.fee.id]));
        expect(new Set(keep.unlinkIds).size).toBe(keep.unlinkIds.length);
    });

    // Re-targeted in F7-d (§20.2, §21.7): the intent carries `chargeIds` too, empty without a plan.
    it('an empty plan changes nothing', () => {
        const {buy, other} = planOf();
        expect(deleteIntent([buy.id, other.id], [], 'all')).toEqual({txIds: [buy.id, other.id], unlinkIds: [], chargeIds: []});
        expect(deleteIntent([buy.id, other.id], [], 'keep')).toEqual({txIds: [buy.id, other.id], unlinkIds: [], chargeIds: []});
    });

    // 66 F7-d (§20.2): the charges of the choice, whatever the choice — the Bulk marks them `byParentChoice`.
    it("'all': chargeIds are the plan's charges that are not selected", () => {
        const {buy, fee, taxCharge, other, plan} = planOf();
        const intent = deleteIntent([buy.id, other.id], plan, 'all') as ReturnType<typeof deleteIntent> & {chargeIds?: number[]};
        expect(intent.chargeIds, 'deleteIntent returns chargeIds').toBeDefined();
        expect(sorted(intent.chargeIds ?? [])).toEqual(sorted([fee.id, taxCharge.id]));
    });

    it("'keep': chargeIds are the plan's charges that are not selected, the same as unlinkIds", () => {
        const {buy, fee, taxCharge, other, plan} = planOf();
        const intent = deleteIntent([buy.id, other.id], plan, 'keep') as ReturnType<typeof deleteIntent> & {chargeIds?: number[]};
        expect(intent.chargeIds, 'deleteIntent returns chargeIds').toBeDefined();
        expect(sorted(intent.chargeIds ?? [])).toEqual(sorted([fee.id, taxCharge.id]));
        expect(sorted(intent.chargeIds ?? [])).toEqual(sorted(intent.unlinkIds));
    });

    it('a charge the user selected is not in chargeIds, with either choice: it was asked for, not chosen with the parent', () => {
        const {buy, fee, taxCharge, plan} = planOf();
        for (const choice of ['all', 'keep'] as const) {
            const intent = deleteIntent([buy.id, fee.id], plan, choice) as ReturnType<typeof deleteIntent> & {chargeIds?: number[]};
            expect(intent.chargeIds, `${choice}: only the TAX left out of the selection`).toEqual([taxCharge.id]);
        }
    });

    it('several parents: chargeIds cover every unselected charge of the plan once', () => {
        const a = planOf();
        const b = planOf();
        const plan = [...a.plan, ...b.plan];
        const intent = deleteIntent([a.buy.id, b.buy.id, b.taxCharge.id], plan, 'all') as ReturnType<typeof deleteIntent> & {chargeIds?: number[]};
        expect(sorted(intent.chargeIds ?? [])).toEqual(sorted([a.fee.id, a.taxCharge.id, b.fee.id]));
    });
});
