/**
 * transactionTypeStore — findPromoteMatch: the paired type the editor offers to merge two
 * standalone rows into (the selection on the transactions page, the Bulk modal).
 *
 * An offer is a promise: the editor must not propose a pair the backend refuses.
 *
 *   - TRANSFER promotes from ADJUSTMENT + ADJUSTMENT with `quantity: opposite`, and the
 *     backend reads «opposite» as exactly opposite: -q on one broker, +q on the other,
 *     q non-zero. Opposite signs are not enough: -3 / +5 creates 2 units out of nothing
 *     (F1, F2).
 *   - A promote does not clear a row's asset event link, so an event-linked row may only
 *     become a type that accepts events (`event_compatible`). TRANSFER does not (rule 9,
 *     eventTypeIncompatible). PromoteContext carries each row's asset_event_id as
 *     eventA / eventB for this check (F3, F4).
 *
 * G1-G7 are the controls around those cases: what must keep matching, and what is already
 * refused. They also keep the F-cases from passing for the wrong reason, since null is what
 * findPromoteMatch answers on an empty cache too.
 *
 * Node env. `$lib/api` is mocked: GET /transactions/types answers six types copied from the
 * backend's TX_TYPE_METADATA (backend/app/schemas/transactions/type_metadata.py), in its order and through
 * the generated schema the real client applies. The store caches the response at module
 * level and never drops it, so it is loaded once, in beforeAll.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {schemas} from '$lib/api/generated';
import {ensureTypesLoaded, findPromoteMatch, getTypeRule, isTypesLoaded, type PromoteContext} from './transactionTypeStore';

const {getTransactionTypes} = vi.hoisted(() => ({getTransactionTypes: vi.fn()}));

vi.mock('$lib/api', () => ({
    zodiosApi: {get_transaction_types_api_v1_transactions_types_get: getTransactionTypes},
}));

// The pair constraints as TX_TYPE_METADATA declares them, once for promote_from and once for
// pair_field_constraints.
const TRANSFER_CONSTRAINTS = [
    {field: 'asset_id', relation: 'equal'},
    {field: 'broker_id', relation: 'different'},
    {field: 'quantity', relation: 'opposite'},
];
const FX_CONVERSION_CONSTRAINTS = [
    {field: 'cash_currency', relation: 'different'},
    {field: 'broker_id', relation: 'equal'},
];
const CASH_TRANSFER_CONSTRAINTS = [
    {field: 'cash_currency', relation: 'equal'},
    {field: 'broker_id', relation: 'different'},
    {field: 'cash_amount', relation: 'opposite'},
];

/** The backend's order matters: FX_CONVERSION's WITHDRAWAL + DEPOSIT rule is scanned before
 *  CASH_TRANSFER's, so G6 proves the constraints pick the target, not the position. */
const TYPES_RESPONSE = schemas.TXTypesResponse.parse({
    transaction_types: [
        {
            code: 'DEPOSIT',
            name: 'Deposit',
            description: 'Add cash to broker account',
            icon_slug: 'deposit',
            doc_slug: 'deposit-withdrawal',
            asset_mode: 'forbidden',
            cash_mode: 'required',
            quantity_mode: 'forbidden',
            requires_link: false,
            quantity_sign: 'zero',
            cash_sign: 'positive',
            event_compatible: false,
            swap_group: ['WITHDRAWAL'],
        },
        {
            code: 'WITHDRAWAL',
            name: 'Withdrawal',
            description: 'Remove cash from broker account',
            icon_slug: 'withdrawal',
            doc_slug: 'deposit-withdrawal',
            asset_mode: 'forbidden',
            cash_mode: 'required',
            quantity_mode: 'forbidden',
            requires_link: false,
            quantity_sign: 'zero',
            cash_sign: 'negative',
            event_compatible: false,
            swap_group: ['DEPOSIT'],
        },
        {
            code: 'TRANSFER',
            name: 'Asset Transfer',
            description: 'Asset transfer between brokers',
            icon_slug: 'transfer',
            doc_slug: 'transfer',
            asset_mode: 'required',
            cash_mode: 'forbidden',
            quantity_mode: 'required',
            requires_link: true,
            quantity_sign: 'nonzero',
            cash_sign: 'zero',
            event_compatible: false,
            pair_form_layout: 'transfer_asset',
            split_into: {from_type: 'ADJUSTMENT', to_type: 'ADJUSTMENT'},
            promote_from: [{type_a: 'ADJUSTMENT', type_b: 'ADJUSTMENT', field_constraints: TRANSFER_CONSTRAINTS}],
            pair_field_constraints: TRANSFER_CONSTRAINTS,
            swap_group: [],
            cost_basis_pair: ['forbidden', 'required_qty_pos'],
        },
        {
            code: 'FX_CONVERSION',
            name: 'FX Conversion',
            description: 'Currency exchange',
            icon_slug: 'fx-conversion',
            doc_slug: 'fx-conversion',
            asset_mode: 'forbidden',
            cash_mode: 'required',
            quantity_mode: 'forbidden',
            requires_link: true,
            quantity_sign: 'zero',
            cash_sign: 'nonzero',
            event_compatible: false,
            pair_form_layout: 'fx',
            split_into: {from_type: 'WITHDRAWAL', to_type: 'DEPOSIT'},
            promote_from: [{type_a: 'WITHDRAWAL', type_b: 'DEPOSIT', field_constraints: FX_CONVERSION_CONSTRAINTS}],
            pair_field_constraints: FX_CONVERSION_CONSTRAINTS,
            swap_group: [],
        },
        {
            code: 'ADJUSTMENT',
            name: 'Adjustment',
            description: 'Manual quantity correction (splits, gifts)',
            icon_slug: 'adjustment',
            doc_slug: 'adjustment',
            asset_mode: 'required',
            cash_mode: 'forbidden',
            quantity_mode: 'required',
            requires_link: false,
            quantity_sign: 'nonzero',
            cash_sign: 'zero',
            event_compatible: true,
            swap_group: [],
            cost_basis_mode: 'required_qty_pos',
        },
        {
            code: 'CASH_TRANSFER',
            name: 'Cash Transfer',
            description: 'Wire transfer / bonifico between brokers',
            icon_slug: 'cash-transfer',
            doc_slug: 'cash-transfer',
            asset_mode: 'forbidden',
            cash_mode: 'required',
            quantity_mode: 'forbidden',
            requires_link: true,
            quantity_sign: 'zero',
            cash_sign: 'nonzero',
            event_compatible: false,
            pair_form_layout: 'transfer_cash',
            split_into: {from_type: 'WITHDRAWAL', to_type: 'DEPOSIT'},
            promote_from: [{type_a: 'WITHDRAWAL', type_b: 'DEPOSIT', field_constraints: CASH_TRANSFER_CONSTRAINTS}],
            pair_field_constraints: CASH_TRANSFER_CONSTRAINTS,
            swap_group: [],
        },
    ],
    event_types: [],
});

/** Identity translator: the label is not the subject, the target type is. */
const t = (key: string) => key;

/** PromoteContext plus eventA / eventB, each row's asset_event_id. The intersection keeps this
 *  file compiling whether or not PromoteContext itself declares the two fields. */
type ContextWithEvents = PromoteContext & {eventA?: number | null; eventB?: number | null};

function ctx(fields: ContextWithEvents): PromoteContext {
    return fields as PromoteContext;
}

beforeAll(async () => {
    getTransactionTypes.mockResolvedValue(TYPES_RESPONSE);
    await ensureTypesLoaded();
    // Positive control: every case below must read this response, not an empty cache.
    expect(getTransactionTypes, 'the store fetched the fixture once').toHaveBeenCalledTimes(1);
    expect(isTypesLoaded(), 'the type cache is loaded').toBe(true);
    // The premise of F3 and F4, as the store itself reads it.
    expect(getTypeRule('ADJUSTMENT').eventLinkable, 'premise: an ADJUSTMENT may be linked to an asset event').toBe(true);
    expect(getTypeRule('TRANSFER').eventLinkable, 'premise: a TRANSFER may not be linked to an asset event').toBe(false);
});

describe('findPromoteMatch — never offers a pair the backend refuses', () => {
    it('F1: ADJUSTMENT -3 / +5 on one asset across two brokers is not a TRANSFER: the quantities do not cancel', () => {
        const match = findPromoteMatch('ADJUSTMENT', 'ADJUSTMENT', t, ctx({brokerA: 1, brokerB: 2, assetA: 7, assetB: 7, qtyA: -3, qtyB: 5}));
        expect(match, 'F1: -3 out and +5 in are not exactly opposite, so no TRANSFER').toBeNull();
    });

    it('F2: the same pair in the other order, +5 / -3, is not a TRANSFER either', () => {
        const match = findPromoteMatch('ADJUSTMENT', 'ADJUSTMENT', t, ctx({brokerA: 1, brokerB: 2, assetA: 7, assetB: 7, qtyA: 5, qtyB: -3}));
        expect(match, 'F2: +5 and -3 are not exactly opposite, so no TRANSFER').toBeNull();
    });

    it('F3: an exactly opposite -10 / +10 pair is not a TRANSFER when row A is linked to an asset event', () => {
        const match = findPromoteMatch('ADJUSTMENT', 'ADJUSTMENT', t, ctx({brokerA: 1, brokerB: 2, assetA: 7, assetB: 7, qtyA: -10, qtyB: 10, eventA: 13}));
        expect(match, 'F3: row A is linked to event 13 and TRANSFER is not event-compatible, so no TRANSFER').toBeNull();
    });

    it('F4: nor when the event-linked row is B', () => {
        const match = findPromoteMatch('ADJUSTMENT', 'ADJUSTMENT', t, ctx({brokerA: 1, brokerB: 2, assetA: 7, assetB: 7, qtyA: -10, qtyB: 10, eventB: 13}));
        expect(match, 'F4: row B is linked to event 13 and TRANSFER is not event-compatible, so no TRANSFER').toBeNull();
    });
});

describe('findPromoteMatch — controls', () => {
    it('G1: ADJUSTMENT -3 / +3 on one asset across two brokers, without events, is a TRANSFER', () => {
        const match = findPromoteMatch('ADJUSTMENT', 'ADJUSTMENT', t, ctx({brokerA: 1, brokerB: 2, assetA: 7, assetB: 7, qtyA: -3, qtyB: 3}));
        expect(match, 'G1: -3 / +3 cancel exactly, so TRANSFER').toMatchObject({targetType: 'TRANSFER'});
    });

    it('G2: so is the same pair in the other order, +3 / -3', () => {
        const match = findPromoteMatch('ADJUSTMENT', 'ADJUSTMENT', t, ctx({brokerA: 1, brokerB: 2, assetA: 7, assetB: 7, qtyA: 3, qtyB: -3}));
        expect(match, 'G2: +3 / -3 cancel exactly, so TRANSFER').toMatchObject({targetType: 'TRANSFER'});
    });

    it('G3: a null eventA and an undefined eventB both mean no event, so it is still a TRANSFER', () => {
        const match = findPromoteMatch('ADJUSTMENT', 'ADJUSTMENT', t, ctx({brokerA: 1, brokerB: 2, assetA: 7, assetB: 7, qtyA: -3, qtyB: 3, eventA: null, eventB: undefined}));
        expect(match, 'G3: neither row is linked to an event, so TRANSFER').toMatchObject({targetType: 'TRANSFER'});
    });

    it('G4: two different assets are not a TRANSFER', () => {
        const match = findPromoteMatch('ADJUSTMENT', 'ADJUSTMENT', t, ctx({brokerA: 1, brokerB: 2, assetA: 7, assetB: 8, qtyA: -3, qtyB: 3}));
        expect(match, 'G4: asset 7 out and asset 8 in, so no TRANSFER').toBeNull();
    });

    it('G5: the same broker on both sides is not a TRANSFER', () => {
        const match = findPromoteMatch('ADJUSTMENT', 'ADJUSTMENT', t, ctx({brokerA: 1, brokerB: 1, assetA: 7, assetB: 7, qtyA: -3, qtyB: 3}));
        expect(match, 'G5: broker 1 to broker 1, so no TRANSFER').toBeNull();
    });

    it('G6: WITHDRAWAL / DEPOSIT in EUR across two brokers, without events, is a CASH_TRANSFER', () => {
        // FX_CONVERSION is scanned first and refused (same currency); the event check must not
        // touch a cash pair whose rows carry no event.
        const match = findPromoteMatch('WITHDRAWAL', 'DEPOSIT', t, ctx({brokerA: 1, brokerB: 2, currencyA: 'EUR', currencyB: 'EUR', eventA: null, eventB: null}));
        expect(match, 'G6: same currency on two brokers, so CASH_TRANSFER').toMatchObject({targetType: 'CASH_TRANSFER'});
    });

    it('G7: without a context the match is by type only, as before: ADJUSTMENT / ADJUSTMENT is a TRANSFER', () => {
        const match = findPromoteMatch('ADJUSTMENT', 'ADJUSTMENT', t);
        expect(match, 'G7: no context, type-only match, so TRANSFER').toMatchObject({targetType: 'TRANSFER'});
    });
});
