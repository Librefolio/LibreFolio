/**
 * txFormChecks — the pure pre-check behind «⚡ Validate now» (V-37b).
 *
 * `computeTxFormChecks(input)` takes a snapshot of the form and answers which cells are wrong, in two phases:
 *   1. required — what is missing (date, broker, asset, cash, quantity, and the To side of a pair);
 *   2. format   — what is there but refused (a date the picker refused, a quantity the input refuses, a cash sign,
 *                 too many significant digits, the same currency on both legs of an FX, the same broker on both
 *                 sides of a transfer).
 * A cell has at most one entry (required wins over format), the list is required first then format, and a form
 * the server can be asked about answers [].
 *
 * The EQUIVALENCE block pins the helper to what the form already knew before V-37b: «no required entry» must
 * agree with `isDraftReadyForValidation` (plus the date and the partner side of a pair), so the old
 * «Validate now is disabled» gate and the new «Validate now marks the cells» can never disagree about
 * completeness.
 *
 * Node env, no DOM. `$lib/api` is mocked and the type rules are the real ones, loaded through the store from a
 * response in the shape of the backend's TX_TYPE_METADATA; nothing asserts on a translated string.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {schemas} from '$lib/api/generated';
import {ensureTypesLoaded, getTypeRule, isDraftReadyForValidation, isTypesLoaded, type TypeRule} from '$lib/features/transactions/transactionTypeStore';
import {computeTxFormChecks, type TxFormCheck, type TxFormCheckInput} from './txFormChecks';

const {getTransactionTypes} = vi.hoisted(() => ({getTransactionTypes: vi.fn()}));

vi.mock('$lib/api', () => ({
    zodiosApi: {get_transaction_types_api_v1_transactions_types_get: getTransactionTypes},
}));

function metadata(code: string, fields: Record<string, unknown>): Record<string, unknown> {
    return {code, name: code, description: code, icon_slug: code.toLowerCase(), doc_slug: code.toLowerCase(), requires_link: false, event_compatible: false, ...fields};
}

const TYPES_RESPONSE = schemas.TXTypesResponse.parse({
    transaction_types: [
        metadata('DEPOSIT', {asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'positive'}),
        metadata('WITHDRAWAL', {asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'negative'}),
        metadata('BUY', {asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'positive', cash_sign: 'negative'}),
        metadata('SELL', {asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'negative', cash_sign: 'positive'}),
        metadata('ADJUSTMENT', {asset_mode: 'required', cash_mode: 'forbidden', quantity_mode: 'required', quantity_sign: 'nonzero', cash_sign: 'zero', event_compatible: true, cost_basis_mode: 'required_qty_pos'}),
        metadata('TRANSFER', {
            asset_mode: 'required',
            cash_mode: 'forbidden',
            quantity_mode: 'required',
            requires_link: true,
            quantity_sign: 'nonzero',
            cash_sign: 'zero',
            pair_form_layout: 'transfer_asset',
            cost_basis_mode: 'forbidden',
            cost_basis_pair: ['forbidden', 'required_qty_pos'],
        }),
        metadata('FX_CONVERSION', {asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', requires_link: true, quantity_sign: 'zero', cash_sign: 'nonzero', pair_form_layout: 'fx'}),
        metadata('CASH_TRANSFER', {asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', requires_link: true, quantity_sign: 'zero', cash_sign: 'nonzero', pair_form_layout: 'transfer_cash'}),
    ],
    event_types: [],
});

beforeAll(async () => {
    getTransactionTypes.mockResolvedValue(TYPES_RESPONSE);
    await ensureTypesLoaded();
    expect(isTypesLoaded(), 'premise: the type cache is loaded').toBe(true);
    expect(getTypeRule('FX_CONVERSION').pairFormLayout, 'premise: the FX rule comes from the fixture').toBe('fx');
});

// ---------------------------------------------------------------------------------------------------------------------
// Builders
// ---------------------------------------------------------------------------------------------------------------------

type Draft = TxFormCheckInput['draft'];
type DualTo = NonNullable<TxFormCheckInput['dualTo']>;
type Cash = {code: string; amount: string};

interface Overrides {
    draft?: Partial<Draft>;
    dualTo?: Partial<DualTo>;
    dateValid?: boolean;
    dateToValid?: boolean;
    quantityValid?: boolean;
    /** Replace the type's rule fields (an `optional` asset, for one). */
    rule?: Partial<TxFormCheckInput['rule']>;
}

const DATE = '2024-03-10';
const DATE_TO = '2024-03-11';
const EUR: Cash = {code: 'EUR', amount: '100'};
const USD: Cash = {code: 'USD', amount: '110'};

/** A complete form of `type`: every field the type's rule asks for is there, and valid. */
function build(type: string, over: Overrides = {}): TxFormCheckInput {
    const typeRule: TypeRule = getTypeRule(type);
    const pairLayout = typeRule.pairFormLayout;
    const draft: Draft = {
        date: DATE,
        broker_id: 17,
        asset_id: typeRule.assetField === 'forbidden' ? null : 42,
        quantity: typeRule.quantityMode === 'forbidden' ? '' : '1',
        cash: typeRule.cashField === 'forbidden' ? null : {...EUR},
        ...over.draft,
    };
    let dualTo: TxFormCheckInput['dualTo'] = null;
    if (pairLayout === 'fx') dualTo = {broker_id: draft.broker_id, date: DATE_TO, cash: {...USD}, ...over.dualTo};
    else if (pairLayout != null) dualTo = {broker_id: 23, date: DATE_TO, cash: null, ...over.dualTo};
    return {
        pairLayout,
        rule: {assetField: typeRule.assetField, cashField: typeRule.cashField, quantityMode: typeRule.quantityMode, cashSign: typeRule.cashSign, ...over.rule},
        draft,
        dualTo,
        dateValid: over.dateValid ?? true,
        dateToValid: over.dateToValid ?? true,
        quantityValid: over.quantityValid ?? true,
    };
}

const required = (cell: TxFormCheck['cell'], reason: TxFormCheck['reason'] = 'missing'): TxFormCheck => ({cell, kind: 'required', reason});
const format = (cell: TxFormCheck['cell'], reason: TxFormCheck['reason']): TxFormCheck => ({cell, kind: 'format', reason});

// ---------------------------------------------------------------------------------------------------------------------
// A complete form is clean
// ---------------------------------------------------------------------------------------------------------------------

describe('computeTxFormChecks — a form the server can be asked about answers []', () => {
    it.each(['BUY', 'SELL', 'ADJUSTMENT', 'DEPOSIT', 'WITHDRAWAL'])('single %s, every required field present and valid', (type) => {
        expect(computeTxFormChecks(build(type))).toEqual([]);
    });

    it.each(['FX_CONVERSION', 'TRANSFER', 'CASH_TRANSFER'])('pair %s, both sides present and valid', (type) => {
        expect(computeTxFormChecks(build(type))).toEqual([]);
    });

    it('an optional asset, a forbidden quantity and a forbidden cash are never asked for', () => {
        // DEPOSIT-like: asset forbidden, quantity forbidden. Whatever text sits in the forbidden quantity is not a problem.
        expect(computeTxFormChecks(build('DEPOSIT', {draft: {asset_id: null, quantity: '0'}, quantityValid: false}))).toEqual([]);
        // an optional asset and an optional cash may be empty
        expect(computeTxFormChecks(build('BUY', {draft: {asset_id: null, cash: null}, rule: {assetField: 'optional', cashField: 'optional'}}))).toEqual([]);
        // a forbidden cash is not asked for, whatever it holds
        expect(computeTxFormChecks(build('ADJUSTMENT', {draft: {cash: null}}))).toEqual([]);
    });
});

// ---------------------------------------------------------------------------------------------------------------------
// Phase 1 — required
// ---------------------------------------------------------------------------------------------------------------------

describe('computeTxFormChecks — phase 1: what is missing', () => {
    it('an empty date is missing', () => {
        expect(computeTxFormChecks(build('BUY', {draft: {date: ''}}))).toEqual([required('date')]);
    });

    it.each([0, -1])('a broker of %i (the unset sentinel) is missing', (broker_id) => {
        expect(computeTxFormChecks(build('BUY', {draft: {broker_id}}))).toEqual([required('broker')]);
    });

    it('a null asset is missing when the rule requires it, and fine when the rule does not', () => {
        expect(computeTxFormChecks(build('BUY', {draft: {asset_id: null}}))).toEqual([required('asset')]);
        expect(computeTxFormChecks(build('BUY', {draft: {asset_id: null}, rule: {assetField: 'optional'}}))).toEqual([]);
        expect(computeTxFormChecks(build('BUY', {draft: {asset_id: null}, rule: {assetField: 'forbidden'}}))).toEqual([]);
    });

    it('a transfer of an asset needs its asset too', () => {
        expect(computeTxFormChecks(build('TRANSFER', {draft: {asset_id: null}}))).toEqual([required('asset')]);
    });

    describe('the cash of a type that requires it', () => {
        it('no cash at all is missing', () => {
            expect(computeTxFormChecks(build('BUY', {draft: {cash: null}}))).toEqual([required('cash')]);
        });

        it.each(['', '   '])('a blank amount (%j) is missing', (amount) => {
            expect(computeTxFormChecks(build('BUY', {draft: {cash: {code: 'EUR', amount}}}))).toEqual([required('cash', 'missing')]);
        });

        it.each(['0', '0.00', '0.000000', '-0'])('a zero in any form (%s) is a cash that is not there: reason zero', (amount) => {
            expect(computeTxFormChecks(build('BUY', {draft: {cash: {code: 'EUR', amount}}}))).toEqual([required('cash', 'zero')]);
        });

        it('an optional cash may be empty, a forbidden one is not looked at', () => {
            expect(computeTxFormChecks(build('BUY', {draft: {cash: null}, rule: {cashField: 'optional'}}))).toEqual([]);
            expect(computeTxFormChecks(build('BUY', {draft: {cash: {code: 'EUR', amount: '0'}}, rule: {cashField: 'forbidden'}}))).toEqual([]);
        });
    });

    describe('the quantity of a type that takes one', () => {
        it.each(['', '   '])('a blank quantity (%j) is missing', (quantity) => {
            expect(computeTxFormChecks(build('BUY', {draft: {quantity}}))).toEqual([required('quantity', 'missing')]);
        });

        it.each(['0', '0.000', '-0'])('a zero quantity (%s) is required, not a format problem', (quantity) => {
            expect(computeTxFormChecks(build('BUY', {draft: {quantity}}))).toEqual([expect.objectContaining({cell: 'quantity', kind: 'required'})]);
        });

        it('a transfer of an asset needs a quantity', () => {
            expect(computeTxFormChecks(build('TRANSFER', {draft: {quantity: ''}}))).toEqual([required('quantity')]);
        });

        it('a forbidden quantity is not looked at', () => {
            expect(computeTxFormChecks(build('DEPOSIT', {draft: {quantity: ''}}))).toEqual([]);
            expect(computeTxFormChecks(build('FX_CONVERSION', {draft: {quantity: '0'}}))).toEqual([]);
        });
    });

    describe('the To side of a pair', () => {
        it('an empty date of the To side is the cell dateTo', () => {
            expect(computeTxFormChecks(build('TRANSFER', {dualTo: {date: ''}}))).toEqual([required('dateTo')]);
            expect(computeTxFormChecks(build('FX_CONVERSION', {dualTo: {date: ''}}))).toEqual([required('dateTo')]);
        });

        it.each(['TRANSFER', 'CASH_TRANSFER'])('%s: a To broker that is not picked is brokerTo', (type) => {
            expect(computeTxFormChecks(build(type, {dualTo: {broker_id: 0}}))).toEqual([required('brokerTo')]);
        });

        it('an FX shares one broker: the To broker is never a cell of its own', () => {
            expect(computeTxFormChecks(build('FX_CONVERSION', {dualTo: {broker_id: 0}}))).toEqual([]);
            // and the shared broker, missing, is the cell broker
            expect(computeTxFormChecks(build('FX_CONVERSION', {draft: {broker_id: 0}, dualTo: {broker_id: 0}}))).toEqual([required('broker')]);
        });
    });

    describe('an FX needs both legs: a code, an amount, and an amount that is not zero', () => {
        it.each([
            ['no cash', null],
            ['a blank code', {code: '  ', amount: '5'}],
            ['a blank amount', {code: 'EUR', amount: ' '}],
        ])('the From leg with %s is missing', (_label, cash) => {
            expect(computeTxFormChecks(build('FX_CONVERSION', {draft: {cash}}))).toEqual([required('cash', 'missing')]);
        });

        it.each([
            ['no cash', null],
            ['a blank code', {code: '', amount: '5'}],
            ['a blank amount', {code: 'USD', amount: ''}],
        ])('the To leg with %s is missing', (_label, cash) => {
            expect(computeTxFormChecks(build('FX_CONVERSION', {dualTo: {cash}}))).toEqual([required('cashTo', 'missing')]);
        });

        it.each(['0', '0.00', '-0'])('a zero amount (%s) on either leg is required: zero', (amount) => {
            expect(computeTxFormChecks(build('FX_CONVERSION', {draft: {cash: {code: 'EUR', amount}}}))).toEqual([required('cash', 'zero')]);
            expect(computeTxFormChecks(build('FX_CONVERSION', {dualTo: {cash: {code: 'USD', amount}}}))).toEqual([required('cashTo', 'zero')]);
        });

        it('both legs empty are two cells, cash and cashTo', () => {
            const checks = computeTxFormChecks(build('FX_CONVERSION', {draft: {cash: null}, dualTo: {cash: null}}));
            expect(checks).toHaveLength(2);
            expect(checks).toEqual(expect.arrayContaining([required('cash'), required('cashTo')]));
        });
    });
});

// ---------------------------------------------------------------------------------------------------------------------
// Phase 2 — format
// ---------------------------------------------------------------------------------------------------------------------

describe('computeTxFormChecks — phase 2: what is there but refused', () => {
    it('a date the picker refused is invalid_date on date, and on dateTo for the To side', () => {
        expect(computeTxFormChecks(build('BUY', {dateValid: false}))).toEqual([format('date', 'invalid_date')]);
        expect(computeTxFormChecks(build('TRANSFER', {dateToValid: false}))).toEqual([format('dateTo', 'invalid_date')]);
        expect(computeTxFormChecks(build('FX_CONVERSION', {dateValid: false, dateToValid: false}))).toEqual(expect.arrayContaining([format('date', 'invalid_date'), format('dateTo', 'invalid_date')]));
    });

    it('a quantity the input refuses is invalid_quantity, unless the type forbids a quantity', () => {
        expect(computeTxFormChecks(build('BUY', {quantityValid: false}))).toEqual([format('quantity', 'invalid_quantity')]);
        expect(computeTxFormChecks(build('DEPOSIT', {quantityValid: false}))).toEqual([]);
        expect(computeTxFormChecks(build('TRANSFER', {quantityValid: false}))).toEqual([format('quantity', 'invalid_quantity')]);
    });

    describe('the sign of the cash', () => {
        it('BUY (the user enters a positive, the system negates): a negative is the wrong sign', () => {
            expect(computeTxFormChecks(build('BUY', {draft: {cash: {code: 'EUR', amount: '-5'}}}))).toEqual([format('cash', 'wrong_sign')]);
        });

        it('DEPOSIT (positive): a negative is the wrong sign, a positive is fine', () => {
            expect(computeTxFormChecks(build('DEPOSIT', {draft: {cash: {code: 'EUR', amount: '-5'}}}))).toEqual([format('cash', 'wrong_sign')]);
            expect(computeTxFormChecks(build('DEPOSIT', {draft: {cash: {code: 'EUR', amount: '5'}}}))).toEqual([]);
        });

        it('a pair reads its cash as positive whatever the type says: CASH_TRANSFER (rule nonzero) refuses a negative', () => {
            expect(getTypeRule('CASH_TRANSFER').cashSign, 'premise: the type itself would accept a negative').toBe('nonzero');
            expect(computeTxFormChecks(build('CASH_TRANSFER', {draft: {cash: {code: 'EUR', amount: '-5'}}}))).toEqual([format('cash', 'wrong_sign')]);
        });

        it('FX: a negative From leg is cash, a negative To leg is cashTo', () => {
            expect(computeTxFormChecks(build('FX_CONVERSION', {draft: {cash: {code: 'EUR', amount: '-5'}}}))).toEqual([format('cash', 'wrong_sign')]);
            expect(computeTxFormChecks(build('FX_CONVERSION', {dualTo: {cash: {code: 'USD', amount: '-5'}}}))).toEqual([format('cashTo', 'wrong_sign')]);
        });
    });

    describe('more significant digits than the backend keeps', () => {
        it('sixteen are too many on the cash, fifteen are not', () => {
            expect(computeTxFormChecks(build('BUY', {draft: {cash: {code: 'EUR', amount: '1234567890123.456'}}}))).toEqual([format('cash', 'too_many_digits')]);
            expect(computeTxFormChecks(build('BUY', {draft: {cash: {code: 'EUR', amount: '123456789012.345'}}}))).toEqual([]);
        });

        it('FX: the same on each leg', () => {
            expect(computeTxFormChecks(build('FX_CONVERSION', {draft: {cash: {code: 'EUR', amount: '1234567890123.456'}}}))).toEqual([format('cash', 'too_many_digits')]);
            expect(computeTxFormChecks(build('FX_CONVERSION', {dualTo: {cash: {code: 'USD', amount: '1234567890123.456'}}}))).toEqual([format('cashTo', 'too_many_digits')]);
        });
    });

    it('FX: the same currency on both legs marks cashTo', () => {
        expect(computeTxFormChecks(build('FX_CONVERSION', {dualTo: {cash: {code: 'EUR', amount: '110'}}}))).toEqual([format('cashTo', 'same_currency')]);
    });

    it.each(['TRANSFER', 'CASH_TRANSFER'])('%s: the same broker on both sides marks brokerTo', (type) => {
        expect(computeTxFormChecks(build(type, {dualTo: {broker_id: 17}}))).toEqual([format('brokerTo', 'same_broker')]);
    });

    it('FX: sharing the one broker is what an FX is, not a problem', () => {
        const input = build('FX_CONVERSION');
        expect(input.dualTo?.broker_id, 'premise: both sides carry the same broker').toBe(input.draft.broker_id);
        expect(computeTxFormChecks(input)).toEqual([]);
    });
});

// ---------------------------------------------------------------------------------------------------------------------
// One entry per cell, and the order of the list
// ---------------------------------------------------------------------------------------------------------------------

describe('computeTxFormChecks — one entry per cell, required wins over format', () => {
    it('an empty date the picker also refuses is required, once', () => {
        expect(computeTxFormChecks(build('BUY', {draft: {date: ''}, dateValid: false}))).toEqual([required('date')]);
    });

    it('an empty quantity the input also refuses is required, once', () => {
        expect(computeTxFormChecks(build('BUY', {draft: {quantity: ''}, quantityValid: false}))).toEqual([required('quantity', 'missing')]);
    });

    it('a zero cash is required: zero, not also a wrong sign', () => {
        expect(computeTxFormChecks(build('BUY', {draft: {cash: {code: 'EUR', amount: '-0'}}}))).toEqual([required('cash', 'zero')]);
    });

    it('the To date missing and refused is dateTo required, once', () => {
        expect(computeTxFormChecks(build('TRANSFER', {dualTo: {date: ''}, dateToValid: false}))).toEqual([required('dateTo')]);
    });

    it('no broker on either side of a transfer is brokerTo required, not also «same broker»', () => {
        const checks = computeTxFormChecks(build('TRANSFER', {draft: {broker_id: 0}, dualTo: {broker_id: 0}}));
        expect(checks).toHaveLength(2);
        expect(checks).toEqual(expect.arrayContaining([required('broker'), required('brokerTo')]));
    });

    it('an FX whose To leg is zero in the same currency is cashTo required, not also «same currency»', () => {
        expect(computeTxFormChecks(build('FX_CONVERSION', {dualTo: {cash: {code: 'EUR', amount: '0'}}}))).toEqual([required('cashTo', 'zero')]);
    });

    it('however many things are wrong, a cell appears once', () => {
        const checks = computeTxFormChecks(
            build('FX_CONVERSION', {
                draft: {date: '', cash: {code: 'EUR', amount: '-1234567890123.456'}},
                dualTo: {date: '', cash: {code: 'EUR', amount: '-1234567890123.456'}},
                dateValid: false,
                dateToValid: false,
            }),
        );
        const cells = checks.map((check) => check.cell);
        expect(new Set(cells).size, `cells ${cells.join(',')}`).toBe(cells.length);
        expect(cells.length, 'premise: the form has several problems').toBeGreaterThan(2);
    });
});

describe('computeTxFormChecks — the list is every required entry first, then every format entry', () => {
    it('two required and two format come out required, required, format, format', () => {
        const checks = computeTxFormChecks(build('BUY', {draft: {date: '', broker_id: 0, cash: {code: 'EUR', amount: '-5'}}, quantityValid: false}));
        expect(checks.map((check) => check.kind)).toEqual(['required', 'required', 'format', 'format']);
        expect(checks.filter((check) => check.kind === 'required')).toEqual(expect.arrayContaining([required('date'), required('broker')]));
        expect(checks.filter((check) => check.kind === 'format')).toEqual(expect.arrayContaining([format('cash', 'wrong_sign'), format('quantity', 'invalid_quantity')]));
    });

    it('a format problem found early on the form still comes after a required one found late', () => {
        // The date is refused (format) and the broker is missing (required): required first, whatever the screen order.
        const checks = computeTxFormChecks(build('BUY', {draft: {broker_id: 0}, dateValid: false}));
        expect(checks).toEqual([required('broker'), format('date', 'invalid_date')]);
    });
});

// ---------------------------------------------------------------------------------------------------------------------
// Equivalence with isDraftReadyForValidation
// ---------------------------------------------------------------------------------------------------------------------

describe('computeTxFormChecks — «no required entry» agrees with isDraftReadyForValidation', () => {
    const DATES = ['', DATE];
    const BROKERS = [0, 17];
    const ASSETS: Array<number | null> = [null, 42];
    const QUANTITIES = ['', '   ', '0', '0.0', '-0', '1', '-1', '0.5'];
    const AMOUNTS = ['', '  ', '0', '0.00', '-0', '5', '-5', '0.25'];
    const SINGLE_TYPES = ['BUY', 'SELL', 'ADJUSTMENT', 'DEPOSIT', 'WITHDRAWAL'];
    const PAIR_TYPES = ['TRANSFER', 'CASH_TRANSFER', 'FX_CONVERSION'];

    /** What the form's own completeness gates said before V-37b: the date, the draft, and the partner side of a pair. */
    function expectedComplete(type: string, input: TxFormCheckInput): boolean {
        const {draft, dualTo, pairLayout} = input;
        if (!draft.date) return false;
        if (!isDraftReadyForValidation({type, broker_id: draft.broker_id, asset_id: draft.asset_id, quantity: draft.quantity, cash: draft.cash})) return false;
        if (pairLayout != null) {
            if (!dualTo || !dualTo.date) return false;
            if (pairLayout === 'fx') {
                const legs = [draft.cash, dualTo.cash];
                return legs.every((cash) => {
                    if (!cash?.code.trim() || !cash.amount.trim()) return false;
                    const amount = Number(cash.amount);
                    return Number.isFinite(amount) && amount !== 0;
                });
            }
            return dualTo.broker_id > 0;
        }
        return true;
    }

    function disagreements(type: string, inputs: Iterable<TxFormCheckInput>): string[] {
        const bad: string[] = [];
        for (const input of inputs) {
            const hasRequired = computeTxFormChecks(input).some((check) => check.kind === 'required');
            const complete = expectedComplete(type, input);
            if (hasRequired === complete) bad.push(`${type} ${JSON.stringify({draft: input.draft, dualTo: input.dualTo})} → helper says ${hasRequired ? 'a required cell is missing' : 'nothing is missing'}, the form's gates say ${complete ? 'complete' : 'incomplete'}`);
        }
        return bad;
    }

    function* singleGrid(type: string): Generator<TxFormCheckInput> {
        for (const date of DATES)
            for (const broker_id of BROKERS)
                for (const asset_id of ASSETS)
                    for (const quantity of QUANTITIES)
                        for (const amount of AMOUNTS) {
                            for (const cash of [null, {code: 'EUR', amount}]) yield build(type, {draft: {date, broker_id, asset_id, quantity, cash}});
                        }
    }

    function* pairGrid(type: string): Generator<TxFormCheckInput> {
        const layout = getTypeRule(type).pairFormLayout;
        const fromCashes: Array<Cash | null> =
            layout === 'fx' ? [null, {code: 'EUR', amount: ''}, {code: '', amount: '5'}, {code: 'EUR', amount: '0'}, {code: 'EUR', amount: '-0'}, {code: 'EUR', amount: '5'}] : [null, {code: 'EUR', amount: ''}, {code: 'EUR', amount: '0.00'}, {code: 'EUR', amount: '5'}];
        const toCashes: Array<Cash | null> = layout === 'fx' ? [null, {code: 'USD', amount: ' '}, {code: '', amount: '7'}, {code: 'USD', amount: '0'}, {code: 'USD', amount: '7'}] : [null];
        for (const date of DATES)
            for (const broker_id of BROKERS)
                for (const asset_id of ASSETS)
                    for (const quantity of ['', '0', '1'])
                        for (const cash of fromCashes)
                            for (const dateTo of DATES)
                                for (const brokerTo of layout === 'fx' ? [0] : BROKERS)
                                    for (const cashTo of toCashes) {
                                        // An FX shares its broker: the component hands the helper `effectiveDualTo`, broker included.
                                        yield build(type, {draft: {date, broker_id, asset_id, quantity, cash}, dualTo: {date: dateTo, broker_id: layout === 'fx' ? broker_id : brokerTo, cash: cashTo}});
                                    }
    }

    it.each(SINGLE_TYPES)('single %s: the helper and the form agree on every draft of the grid', (type) => {
        const bad = disagreements(type, singleGrid(type));
        expect(bad.slice(0, 8), `${bad.length} disagreements`).toEqual([]);
    });

    it.each(PAIR_TYPES)('pair %s: the helper and the form agree on every draft of the grid, partner side included', (type) => {
        const bad = disagreements(type, pairGrid(type));
        expect(bad.slice(0, 8), `${bad.length} disagreements`).toEqual([]);
    });

    it('control: a complete BUY and an empty BUY land on opposite sides, so the grid is not vacuous', () => {
        expect(computeTxFormChecks(build('BUY')).some((check) => check.kind === 'required')).toBe(false);
        expect(computeTxFormChecks(build('BUY', {draft: {quantity: '', asset_id: null, broker_id: 0, cash: null, date: ''}})).filter((check) => check.kind === 'required')).toHaveLength(5);
    });
});
