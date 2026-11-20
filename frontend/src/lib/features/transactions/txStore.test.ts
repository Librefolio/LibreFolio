/**
 * txStore — `txStoreAddExtras` (66 F6, §3 «the missing ids»).
 *
 * The Bulk resolves the ids of its intent from the store and silently drops what is not there. The charges read with
 * `GET /transactions?parent_ids=…` may be outside the page's list (filters, dates), so before opening the Bulk the page
 * adds them to the store, as it does with the partners. The contract:
 *   - a row not in the store is added, and `txStoreGet(id)` then finds it;
 *   - a row whose id is already in the store is NOT replaced: the page's own row wins;
 *   - the version (`txStoreGetVersion`) moves only when something was added — read as a delta, never as a value;
 *   - a later `txStoreSetAll` replaces the whole map, so the extras are gone.
 *
 * The store is module-level state: every case starts from `txStoreSetAll` with its own rows and ends with
 * `txStoreInvalidate`, so no case inherits its neighbour's rows. `txStoreAddExtras` is read off the module namespace,
 * so that while it does not exist each case fails on its own, saying so, instead of the whole file failing to import.
 */
import {afterEach, describe, expect, it} from 'vitest';
import * as txStore from './txStore.svelte';
import {txStoreGet, txStoreGetAll, txStoreGetVersion, txStoreInvalidate, txStoreSetAll} from './txStore.svelte';
import type {TXReadItem} from './types';

/** The function under test, or a failure naming it while it is missing. */
function addExtras(rows: TXReadItem[]): void {
    const fn = (txStore as unknown as Record<string, unknown>).txStoreAddExtras;
    if (typeof fn !== 'function') throw new Error('txStoreAddExtras is not exported by txStore.svelte.ts');
    (fn as (rows: TXReadItem[]) => void)(rows);
}

function tx(id: number, overrides: Partial<TXReadItem> = {}): TXReadItem {
    return {
        id,
        broker_id: 77,
        asset_id: 101,
        type: 'BUY',
        date: '2026-09-13',
        quantity: '1.000000',
        cash: {code: 'EUR', amount: '-10.000000'},
        related_transaction_id: null,
        partner_broker_id: null,
        tags: [],
        description: `row ${id}`,
        cost_basis_override: null,
        asset_event_id: null,
        ...overrides,
    };
}

const PARENT = tx(92_001, {charges_count: 2, description: 'page row: the parent'});
const FEE = tx(92_002, {type: 'FEE', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '-1.500000'}, parent_transaction_id: PARENT.id, description: 'extra: the fee'});
const TAX = tx(92_003, {type: 'TAX', asset_id: null, quantity: '0', cash: {code: 'EUR', amount: '-0.500000'}, parent_transaction_id: PARENT.id, description: 'extra: the tax'});

afterEach(() => {
    txStoreInvalidate();
});

describe('txStoreAddExtras (66 F6)', () => {
    it('adds the rows the store does not hold: txStoreGet finds them, and the page rows are still there', () => {
        txStoreSetAll([PARENT], []);

        addExtras([FEE, TAX]);

        expect(txStoreGet(FEE.id)).toEqual(FEE);
        expect(txStoreGet(TAX.id)).toEqual(TAX);
        expect(txStoreGet(PARENT.id), 'the page row is untouched').toEqual(PARENT);
        expect(new Set(txStoreGetAll().map((row) => row.id))).toEqual(new Set([PARENT.id, FEE.id, TAX.id]));
    });

    it('never replaces a row already in the store: the page row wins', () => {
        const pageFee = {...FEE, description: 'page row: the fee as the list shows it'};
        txStoreSetAll([PARENT, pageFee], []);

        addExtras([{...FEE, description: 'extra: a stale copy of the fee'}, TAX]);

        expect(txStoreGet(FEE.id)?.description, 'the page row is kept').toBe(pageFee.description);
        expect(txStoreGet(TAX.id), 'the new one is added all the same').toEqual(TAX);
    });

    it('moves the version when something is added', () => {
        txStoreSetAll([PARENT], []);
        const before = txStoreGetVersion();

        addExtras([FEE]);

        expect(txStoreGetVersion()).toBeGreaterThan(before);
    });

    it('does not move the version when nothing is added: every row already there, or none given', () => {
        txStoreSetAll([PARENT, FEE], []);
        const before = txStoreGetVersion();

        addExtras([{...FEE, description: 'extra: a copy'}]);
        expect(txStoreGetVersion(), 'only ids already in the store').toBe(before);

        addExtras([]);
        expect(txStoreGetVersion(), 'an empty list').toBe(before);
    });

    it('a later txStoreSetAll replaces the whole map: the extras are gone', () => {
        txStoreSetAll([PARENT], []);
        addExtras([FEE, TAX]);
        expect(txStoreGet(FEE.id), 'premise: the extra is in the store').toBeDefined();

        txStoreSetAll([PARENT], []);

        expect(txStoreGet(FEE.id)).toBeUndefined();
        expect(txStoreGet(TAX.id)).toBeUndefined();
        expect(txStoreGet(PARENT.id)).toEqual(PARENT);
    });
});
