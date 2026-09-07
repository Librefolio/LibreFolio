/**
 * resolveFormItems — unit tests
 *
 * This module decides *which rows a transaction form is opened on*: one row for
 * a plain transaction, two for a paired one (transfer_asset / transfer_cash /
 * fx), or one plus a sentinel when the other half lives in a broker the user
 * cannot see. Getting that wrong is not cosmetic — the form writes back what it
 * was handed, so a mis-ordered pair swaps sender and receiver, and an
 * unvalidated pair edits two transactions that were never linked.
 *
 * Everything here is pure: two lookups and an adapter are injected, so the
 * whole decision table is reachable without a broker, a store or a DOM. The
 * fakes below record what they were asked for, which is how the tests can
 * assert that a lookup was *not* consulted — a claim the return value alone
 * cannot make.
 *
 * Note on `resolveFormItemsFromOps`: it is the BulkModal edit-path resolver.
 * Its adapter boundary matters: callers can project in-flight draft state
 * before the pair guardrail runs.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

import {isInaccessible, resolveFormItemsForView, resolveFormItemsFromOps, type InaccessiblePartner, type MinimalPendingOp} from './resolveFormItems';
import type {TXReadItem} from '../types';

// =============================================================================
//  Fixtures
// =============================================================================

/** A transaction row. Only the fields this module reads are given defaults. */
function tx(over: Partial<TXReadItem> & {id: number}): TXReadItem {
    return {
        broker_id: 1,
        type: 'TRANSFER_ASSET',
        date: '2024-03-01',
        quantity: '0',
        cash: null,
        related_transaction_id: null,
        partner_broker_id: null,
        ...over,
    };
}

/** A store lookup that answers from a fixed table and records every id asked. */
function storeOf(...rows: TXReadItem[]) {
    const asked: number[] = [];
    const byId = new Map(rows.map((r) => [r.id, r]));
    const get = (id: number): TXReadItem | undefined => {
        asked.push(id);
        return byId.get(id);
    };
    return {get, asked};
}

interface Op extends MinimalPendingOp {
    row: TXReadItem;
}

/** The PendingOp → TXReadItem adapter the callers inject. */
const adapt = (o: Op): TXReadItem => o.row;

/** Silences the module's dev-time console.error and reports whether it fired. */
function captureRefusal() {
    return vi.spyOn(console, 'error').mockImplementation(() => {});
}

beforeEach(() => {
    vi.restoreAllMocks();
});

// =============================================================================
//  isInaccessible
// =============================================================================

describe('isInaccessible', () => {
    it('is true only for the sentinel', () => {
        const sentinel: InaccessiblePartner = {_inaccessible: true, broker_id: 9};
        expect(isInaccessible(sentinel)).toBe(true);
    });

    it('is false for a real row, which has no such field', () => {
        expect(isInaccessible(tx({id: 1}))).toBe(false);
    });

    it('is false for an object that carries the field turned off', () => {
        // The guard is `in` *and* truthy: a row that grew a `_inaccessible:
        // false` field must still be treated as a real transaction, or the form
        // would lock a side the user can perfectly well edit.
        const notReally = {...tx({id: 1}), _inaccessible: false} as unknown as TXReadItem;
        expect(isInaccessible(notReally)).toBe(false);
    });
});

// =============================================================================
//  resolveFormItemsForView — the resolver the three pages actually call
// =============================================================================

describe('resolveFormItemsForView', () => {
    const noRole = () => null;
    const anyRole = () => 'viewer';

    describe('rows that are not paired at all', () => {
        it.each([
            ['a null link', null],
            ['an undefined link', undefined],
            ['a zero link', 0],
            ['a negative link', -1],
        ])('returns the row alone and never touches the store for %s', (_label, relId) => {
            const store = storeOf(tx({id: 77}));
            const row = tx({id: 5, related_transaction_id: relId});

            expect(resolveFormItemsForView(row, store.get, noRole)).toEqual([row]);
            expect(store.asked).toEqual([]);
        });
    });

    describe('the partner is in the store', () => {
        it('returns both halves', () => {
            const from = tx({id: 5, quantity: '-10', related_transaction_id: 6});
            const to = tx({id: 6, quantity: '10', related_transaction_id: 5});
            const store = storeOf(to);

            const items = resolveFormItemsForView(from, store.get, noRole);

            expect(items).toHaveLength(2);
            expect(items.map((i) => (i as TXReadItem).id)).toEqual([5, 6]);
            expect(store.asked).toEqual([6]);
        });

        it('refuses a pair whose halves are of different types', () => {
            const refusal = captureRefusal();
            const row = tx({id: 5, type: 'TRANSFER_ASSET', related_transaction_id: 6});
            const partner = tx({id: 6, type: 'BUY', related_transaction_id: 5});

            expect(resolveFormItemsForView(row, storeOf(partner).get, noRole)).toEqual([row]);
            expect(refusal).toHaveBeenCalled();
        });

        it('accepts a partner that does not link back', () => {
            // On this path the forward link holds by construction — the partner
            // was fetched *by* `row.related_transaction_id`, so it is that id.
            // The guardrail therefore only ever fires on the type check here;
            // the missing back-reference is exercised from `…FromOps` below,
            // where the partner arrives by `pairedWith` instead of by id.
            const refusal = captureRefusal();
            const row = tx({id: 5, quantity: '-10', related_transaction_id: 6});
            const partner = tx({id: 6, quantity: '10', related_transaction_id: null});

            expect(resolveFormItemsForView(row, storeOf(partner).get, noRole)).toHaveLength(2);
            expect(refusal).not.toHaveBeenCalled();
        });

        it('skips the cross-reference check when a half is an unsaved draft', () => {
            const refusal = captureRefusal();
            const draft = tx({id: 0, quantity: '-10', related_transaction_id: 6});
            const partner = tx({id: 6, quantity: '10', related_transaction_id: 999});

            expect(resolveFormItemsForView(draft, storeOf(partner).get, noRole)).toHaveLength(2);
            expect(refusal).not.toHaveBeenCalled();
        });
    });

    describe('orientation — the sender must come first', () => {
        /** Returns the ids in the order the resolver put them. */
        function order(row: TXReadItem, partner: TXReadItem): number[] {
            const items = resolveFormItemsForView(row, storeOf(partner).get, noRole);
            return items.map((i) => (i as TXReadItem).id);
        }

        it('keeps the row first when the row sends the asset', () => {
            expect(order(tx({id: 5, quantity: '-10', related_transaction_id: 6}), tx({id: 6, quantity: '10', related_transaction_id: 5}))).toEqual([5, 6]);
        });

        it('puts the partner first when the partner sends the asset', () => {
            expect(order(tx({id: 5, quantity: '10', related_transaction_id: 6}), tx({id: 6, quantity: '-10', related_transaction_id: 5}))).toEqual([6, 5]);
        });

        it('keeps the row first when the row sends the cash', () => {
            const row = tx({id: 5, type: 'TRANSFER_CASH', quantity: '0', cash: {code: 'EUR', amount: '-100'}, related_transaction_id: 6});
            const partner = tx({id: 6, type: 'TRANSFER_CASH', quantity: '0', cash: {code: 'EUR', amount: '100'}, related_transaction_id: 5});
            expect(order(row, partner)).toEqual([5, 6]);
        });

        it('puts the partner first when the partner sends the cash', () => {
            const row = tx({id: 5, type: 'TRANSFER_CASH', quantity: '0', cash: {code: 'EUR', amount: '100'}, related_transaction_id: 6});
            const partner = tx({id: 6, type: 'TRANSFER_CASH', quantity: '0', cash: {code: 'EUR', amount: '-100'}, related_transaction_id: 5});
            expect(order(row, partner)).toEqual([6, 5]);
        });

        it('lets the quantity decide before the cash', () => {
            // A row can be negative on both axes. Quantity is checked first, so
            // the asset leg names the sender even when the cash disagrees.
            const row = tx({id: 5, quantity: '10', cash: {code: 'EUR', amount: '-100'}, related_transaction_id: 6});
            const partner = tx({id: 6, quantity: '-10', cash: {code: 'EUR', amount: '100'}, related_transaction_id: 5});
            expect(order(row, partner)).toEqual([6, 5]);
        });

        it('keeps the given order when neither half is negative', () => {
            expect(order(tx({id: 5, quantity: '10', related_transaction_id: 6}), tx({id: 6, quantity: '10', related_transaction_id: 5}))).toEqual([5, 6]);
        });

        it('reads a missing quantity or cash as zero rather than NaN', () => {
            // `NaN < 0` is false, so a half-hydrated row would silently fall
            // through to the next test instead of throwing. Both guards are
            // pinned here: without them the cash leg below would never be read.
            const row = {...tx({id: 5, related_transaction_id: 6}), quantity: undefined, cash: null} as unknown as TXReadItem;
            const partner = {...tx({id: 6, related_transaction_id: 5}), quantity: undefined, cash: {code: 'EUR', amount: '-100'}} as unknown as TXReadItem;
            expect(order(row, partner)).toEqual([6, 5]);
        });
    });

    describe('the partner is not in the store', () => {
        it('returns the inaccessible sentinel when the user has no role on the partner broker', () => {
            const row = tx({id: 5, related_transaction_id: 6, partner_broker_id: 42});

            const items = resolveFormItemsForView(row, storeOf().get, noRole);

            expect(items).toEqual([row, {_inaccessible: true, broker_id: 42}]);
        });

        it('asks the role lookup for the partner broker, not for the row broker', () => {
            const asked: number[] = [];
            const row = tx({id: 5, broker_id: 1, related_transaction_id: 6, partner_broker_id: 42});

            resolveFormItemsForView(row, storeOf().get, (id) => {
                asked.push(id);
                return null;
            });

            expect(asked).toEqual([42]);
        });

        it('returns the row alone when the partner broker is unknown', () => {
            const row = tx({id: 5, related_transaction_id: 6, partner_broker_id: null});
            expect(resolveFormItemsForView(row, storeOf().get, noRole)).toEqual([row]);
        });

        it('returns the row alone when the user does have a role but the partner simply is not loaded', () => {
            // Accessible-but-absent is a loading state, not a permission one:
            // marking it inaccessible would lock a side the user may edit.
            const row = tx({id: 5, related_transaction_id: 6, partner_broker_id: 42});
            expect(resolveFormItemsForView(row, storeOf().get, anyRole)).toEqual([row]);
        });
    });
});

// =============================================================================
//  resolveFormItemsFromOps
// =============================================================================

/** Runtime caller: `TransactionBulkModal.openEditRowForm`. */
describe('resolveFormItemsFromOps', () => {
    const main: Op = {tempId: 'main', op: 'create', row: tx({id: 0, quantity: '10'})};

    it('pairs with the op that points at the main op', () => {
        const partner: Op = {tempId: 'p', op: 'create', pairedWith: 'main', row: tx({id: 0, quantity: '-10'})};
        const items = resolveFormItemsFromOps(main, [main, partner], adapt, storeOf().get);

        expect(items).toHaveLength(2);
        // The partner is the sender here, so orientation moves it to the front.
        expect(items[0]).toBe(partner.row);
        expect(items[1]).toBe(main.row);
    });

    it('ignores an op that points at somebody else', () => {
        const other: Op = {tempId: 'p', op: 'create', pairedWith: 'someone-else', row: tx({id: 0, quantity: '-10'})};
        expect(resolveFormItemsFromOps(main, [main, other], adapt, storeOf().get)).toEqual([main.row]);
    });

    it('falls back to the main op alone when the local partner fails the guardrail', () => {
        const refusal = captureRefusal();
        const partner: Op = {tempId: 'p', op: 'create', pairedWith: 'main', row: tx({id: 0, type: 'BUY'})};

        expect(resolveFormItemsFromOps(main, [main, partner], adapt, storeOf().get)).toEqual([main.row]);
        expect(refusal).toHaveBeenCalled();
    });

    describe('the cross-reference guardrail, on two saved rows paired locally', () => {
        // This is the only path on which the check can fail: the partner comes
        // from `pairedWith`, so nothing guarantees the two ids match up. Two
        // rows the user dragged together by mistake must not be edited as one.
        const mainEdit: Op = {tempId: 'main', op: 'edit', txId: 5, row: tx({id: 5, quantity: '-10', related_transaction_id: 6})};

        function pairedWithRow(row: TXReadItem): Op {
            return {tempId: 'p', op: 'edit', txId: row.id, pairedWith: 'main', row};
        }

        it('accepts a pair linked from the main side', () => {
            const refusal = captureRefusal();
            const partner = pairedWithRow(tx({id: 6, quantity: '10', related_transaction_id: null}));

            expect(resolveFormItemsFromOps(mainEdit, [mainEdit, partner], adapt, storeOf().get)).toHaveLength(2);
            expect(refusal).not.toHaveBeenCalled();
        });

        it('accepts a pair linked from the partner side only', () => {
            // Half-written links exist: one row references the other and the
            // back-reference was never filled in. Either direction is enough.
            const refusal = captureRefusal();
            const unlinkedMain: Op = {tempId: 'main', op: 'edit', txId: 5, row: tx({id: 5, quantity: '-10', related_transaction_id: null})};
            const partner = pairedWithRow(tx({id: 6, quantity: '10', related_transaction_id: 5}));

            expect(resolveFormItemsFromOps(unlinkedMain, [unlinkedMain, partner], adapt, storeOf().get)).toHaveLength(2);
            expect(refusal).not.toHaveBeenCalled();
        });

        it('refuses two saved rows that reference neither each other', () => {
            const refusal = captureRefusal();
            const stranger = pairedWithRow(tx({id: 7, quantity: '10', related_transaction_id: 99}));

            expect(resolveFormItemsFromOps(mainEdit, [mainEdit, stranger], adapt, storeOf().get)).toEqual([mainEdit.row]);
            expect(refusal).toHaveBeenCalled();
        });
    });

    describe('the database fallback, for edits with no local partner', () => {
        it('follows the stored link to the partner row', () => {
            const editMain: Op = {tempId: 'main', op: 'edit', txId: 5, row: tx({id: 5, quantity: '-10', related_transaction_id: 6})};
            const store = storeOf(tx({id: 5, quantity: '-10', related_transaction_id: 6}), tx({id: 6, quantity: '10', related_transaction_id: 5}));

            const items = resolveFormItemsFromOps(editMain, [editMain], adapt, store.get);

            expect(items).toHaveLength(2);
            expect((items[1] as TXReadItem).id).toBe(6);
            // The stored main row is read for its link, then the partner.
            expect(store.asked).toEqual([5, 6]);
        });

        it('orients the pair it found in the database', () => {
            const editMain: Op = {tempId: 'main', op: 'edit', txId: 5, row: tx({id: 5, quantity: '10', related_transaction_id: 6})};
            const store = storeOf(tx({id: 5, quantity: '10', related_transaction_id: 6}), tx({id: 6, quantity: '-10', related_transaction_id: 5}));

            const items = resolveFormItemsFromOps(editMain, [editMain], adapt, store.get);

            expect(items.map((i) => (i as TXReadItem).id)).toEqual([6, 5]);
        });

        it('refuses a database pair that fails the guardrail', () => {
            const refusal = captureRefusal();
            const editMain: Op = {tempId: 'main', op: 'edit', txId: 5, row: tx({id: 5, type: 'TRANSFER_ASSET', related_transaction_id: 6})};
            const store = storeOf(tx({id: 5, related_transaction_id: 6}), tx({id: 6, type: 'BUY', related_transaction_id: 5}));

            expect(resolveFormItemsFromOps(editMain, [editMain], adapt, store.get)).toEqual([editMain.row]);
            expect(refusal).toHaveBeenCalled();
        });

        it('does not re-pair a split-queued edit tail after the caller projects the post-split type', () => {
            const refusal = captureRefusal();
            const splitTail: Op = {
                tempId: 'tail',
                op: 'edit',
                txId: 6,
                row: tx({
                    id: 6,
                    type: 'DEPOSIT',
                    quantity: '0',
                    cash: {code: 'EUR', amount: '100'},
                    related_transaction_id: 5,
                }),
            };
            const store = storeOf(
                tx({
                    id: 6,
                    type: 'CASH_TRANSFER',
                    quantity: '0',
                    cash: {code: 'EUR', amount: '100'},
                    related_transaction_id: 5,
                }),
                tx({
                    id: 5,
                    type: 'CASH_TRANSFER',
                    quantity: '0',
                    cash: {code: 'EUR', amount: '-100'},
                    related_transaction_id: 6,
                }),
            );

            expect(resolveFormItemsFromOps(splitTail, [splitTail], adapt, store.get)).toEqual([splitTail.row]);
            expect(refusal).toHaveBeenCalled();
            expect(store.asked).toEqual([6, 5]);
        });

        it.each([
            ['the stored row is not there', 5, [] as TXReadItem[]],
            ['the stored row has no link', 5, [tx({id: 5, related_transaction_id: null})]],
            ['the link is zero', 5, [tx({id: 5, related_transaction_id: 0})]],
            ['the linked row is not there', 5, [tx({id: 5, related_transaction_id: 6})]],
        ])('returns the main op alone when %s', (_label, txId, rows) => {
            const editMain: Op = {tempId: 'main', op: 'edit', txId, row: tx({id: txId})};
            expect(resolveFormItemsFromOps(editMain, [editMain], adapt, storeOf(...rows).get)).toEqual([editMain.row]);
        });

        it.each([
            ['a create op carrying a stale txId', {tempId: 'main', op: 'create' as const, txId: 5}],
            ['an edit op with no txId', {tempId: 'main', op: 'edit' as const}],
        ])('never consults the store for %s', (_label, opFields) => {
            const op: Op = {...opFields, row: tx({id: 5})};
            const store = storeOf(tx({id: 5, related_transaction_id: 6}), tx({id: 6, related_transaction_id: 5}));

            expect(resolveFormItemsFromOps(op, [op], adapt, store.get)).toEqual([op.row]);
            expect(store.asked).toEqual([]);
        });
    });

    it('prefers the local partner over the database one', () => {
        const editMain: Op = {tempId: 'main', op: 'edit', txId: 5, row: tx({id: 5, quantity: '-10', related_transaction_id: 6})};
        const localPartner: Op = {tempId: 'p', op: 'create', pairedWith: 'main', row: tx({id: 0, quantity: '10'})};
        const store = storeOf(tx({id: 5, quantity: '-10', related_transaction_id: 6}), tx({id: 6, quantity: '10', related_transaction_id: 5}));

        const items = resolveFormItemsFromOps(editMain, [editMain, localPartner], adapt, store.get);

        // The unsaved draft wins, so the store is never asked.
        expect(items[1]).toBe(localPartner.row);
        expect(store.asked).toEqual([]);
    });
});
