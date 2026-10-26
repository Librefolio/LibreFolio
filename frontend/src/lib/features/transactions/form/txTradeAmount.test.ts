/**
 * txTradeAmount — the pure half of «Total amount / Unit price» in the transaction form (#47).
 *
 * Two functions, no DOM, no network:
 *   - `driverAfterEdit(current, edit)`: the driver is the value written LAST. Typing an amount gives it to `amount`, typing in
 *     the unit-price field gives it to `unit_price`; a new quantity or asset is not a write of either, so it keeps
 *     whoever drives and the other value is recalculated from it.
 *   - `planTradeAmountRequest(input)`: when to ask the backend, and what. The driver's value is what is sent, with the
 *     mode that calculates the OTHER one: driver `unit_price` → `price_to_amount`, driver `amount` → `amount_to_price`.
 *     `null` for every state with nothing to ask: no asset, a quantity or a driving value that is blank, zero,
 *     negative, not a number, or past the limits the backend keeps (quantity 10 decimals, amount 6, unit price 12,
 *     15 significant digits).
 *
 * The inputs arrive canonical (dot decimal, the comma already normalised by the field): turning `83,40` into `83.40` is
 * the input's job, not this function's, and nothing here exercises it. The form does no arithmetic: no test calculates.
 * The value that does NOT drive is never looked at: a refusal in it is red in its own field and asks nothing of this plan.
 */
import {describe, expect, it} from 'vitest';
import {driverAfterEdit, planTradeAmountRequest, type TradeAmountDriver, type TradeAmountEdit, type TradeAmountInput, type TradeAmountRequest} from './txTradeAmount';

const DRIVERS: TradeAmountDriver[] = ['amount', 'unit_price'];

describe('driverAfterEdit — the driver is the value written last', () => {
    // Every current × edit combination, written out: the table is the contract.
    const TABLE: Array<[TradeAmountDriver, TradeAmountEdit, TradeAmountDriver]> = [
        ['amount', 'amount', 'amount'],
        ['amount', 'unit_price', 'unit_price'],
        ['amount', 'quantity', 'amount'],
        ['amount', 'asset', 'amount'],
        ['unit_price', 'amount', 'amount'],
        ['unit_price', 'unit_price', 'unit_price'],
        ['unit_price', 'quantity', 'unit_price'],
        ['unit_price', 'asset', 'unit_price'],
    ];

    it.each(TABLE)('current %s, the user edits the %s → the driver is %s', (current, edit, expected) => {
        expect(driverAfterEdit(current, edit)).toBe(expected);
    });

    it('the table above covers every combination of the two drivers and the four edits', () => {
        const edits: TradeAmountEdit[] = ['amount', 'unit_price', 'quantity', 'asset'];
        const covered = new Set(TABLE.map(([current, edit]) => `${current}/${edit}`));
        for (const current of DRIVERS) for (const edit of edits) expect(covered, `${current}/${edit} is in the table`).toContain(`${current}/${edit}`);
        expect(covered.size).toBe(DRIVERS.length * edits.length);
    });

    it('typing an amount always hands the driver to amount; typing a unit price always hands it to unit_price', () => {
        for (const current of DRIVERS) {
            expect(driverAfterEdit(current, 'amount'), `from ${current}`).toBe('amount');
            expect(driverAfterEdit(current, 'unit_price'), `from ${current}`).toBe('unit_price');
        }
    });

    it('a quantity or asset edit never changes the driver', () => {
        for (const current of DRIVERS) {
            expect(driverAfterEdit(current, 'quantity'), `quantity from ${current}`).toBe(current);
            expect(driverAfterEdit(current, 'asset'), `asset from ${current}`).toBe(current);
        }
    });
});

describe('planTradeAmountRequest', () => {
    /** A state with both values filled, so a test names only what it changes. */
    function input(overrides: Partial<TradeAmountInput> = {}): TradeAmountInput {
        return {driver: 'amount', assetId: 7, quantity: '12', amount: '1000.8', unitPrice: '83.4', ...overrides};
    }

    describe('what is asked', () => {
        it('driver amount → the unit price is calculated: mode amount_to_price, value = the amount', () => {
            const expected: TradeAmountRequest = {asset_id: 7, quantity: '12', mode: 'amount_to_price', value: '1000.8'};
            expect(planTradeAmountRequest(input({driver: 'amount'}))).toEqual(expected);
        });

        it('driver unit_price → the amount is calculated: mode price_to_amount, value = the unit price', () => {
            const expected: TradeAmountRequest = {asset_id: 7, quantity: '12', mode: 'price_to_amount', value: '83.4'};
            expect(planTradeAmountRequest(input({driver: 'unit_price'}))).toEqual(expected);
        });

        it('the request is exactly {asset_id, quantity, mode, value}: nothing else of the form travels', () => {
            for (const driver of DRIVERS) {
                const request = planTradeAmountRequest(input({driver}));
                expect(request, `driver ${driver}`).not.toBeNull();
                expect(Object.keys(request as TradeAmountRequest).sort()).toEqual(['asset_id', 'mode', 'quantity', 'value']);
            }
        });

        it('the asset id and the quantity are the ones of the input', () => {
            expect(planTradeAmountRequest(input({driver: 'amount', assetId: 91, quantity: '0.5', amount: '20'}))).toEqual({asset_id: 91, quantity: '0.5', mode: 'amount_to_price', value: '20'});
            expect(planTradeAmountRequest(input({driver: 'unit_price', assetId: 91, quantity: '0.5', unitPrice: '40'}))).toEqual({asset_id: 91, quantity: '0.5', mode: 'price_to_amount', value: '40'});
        });

        it('the value that does not drive is ignored, blank or garbage: driver amount does not read the unit price', () => {
            for (const unitPrice of ['', 'abc', '0', '-3', '0.1234567890123456789']) {
                expect(planTradeAmountRequest(input({driver: 'amount', unitPrice})), `unit price «${unitPrice}»`).toEqual({asset_id: 7, quantity: '12', mode: 'amount_to_price', value: '1000.8'});
            }
        });

        it('the value that does not drive is ignored, blank or garbage: driver unit_price does not read the amount', () => {
            for (const amount of ['', 'abc', '0', '-3', '0.1234567']) {
                expect(planTradeAmountRequest(input({driver: 'unit_price', amount})), `amount «${amount}»`).toEqual({asset_id: 7, quantity: '12', mode: 'price_to_amount', value: '83.4'});
            }
        });
    });

    describe('nothing to ask → null', () => {
        it.each(DRIVERS)('no asset (driver %s)', (driver) => {
            expect(planTradeAmountRequest(input({driver, assetId: null}))).toBeNull();
        });

        it.each(['', ' ', '0', '0.0', '0.0000000000', '-1', '-0.5', 'abc', '12abc', '1.2.3', '.'])('a quantity of «%s» (driver amount)', (quantity) => {
            expect(planTradeAmountRequest(input({driver: 'amount', quantity}))).toBeNull();
        });

        it.each(['', '0', '-1', 'abc'])('a quantity of «%s» (driver unit_price)', (quantity) => {
            expect(planTradeAmountRequest(input({driver: 'unit_price', quantity}))).toBeNull();
        });

        it.each(['', ' ', '0', '0.0', '0.000000', '-1', '-0.5', 'abc', '12abc', '1.2.3', '.'])('an amount of «%s» drives nothing', (amount) => {
            expect(planTradeAmountRequest(input({driver: 'amount', amount}))).toBeNull();
        });

        it.each(['', ' ', '0', '0.0', '0.000000000000', '-1', '-0.5', 'abc', '83.4x', '1.2.3', '.'])('a unit price of «%s» drives nothing', (unitPrice) => {
            expect(planTradeAmountRequest(input({driver: 'unit_price', unitPrice}))).toBeNull();
        });
    });

    describe('past the limits the backend keeps → null; at the limit → asked', () => {
        it('an amount of 7 decimals is past the 6 it keeps; 6 decimals are asked', () => {
            expect(planTradeAmountRequest(input({driver: 'amount', amount: '0.1234567'}))).toBeNull();
            expect(planTradeAmountRequest(input({driver: 'amount', amount: '0.123456'}))).toEqual({asset_id: 7, quantity: '12', mode: 'amount_to_price', value: '0.123456'});
        });

        it('a unit price of 13 decimals is past the 12 it keeps; 12 decimals are asked', () => {
            expect(planTradeAmountRequest(input({driver: 'unit_price', unitPrice: '0.1234567890123'}))).toBeNull();
            expect(planTradeAmountRequest(input({driver: 'unit_price', unitPrice: '0.123456789012'}))).toEqual({asset_id: 7, quantity: '12', mode: 'price_to_amount', value: '0.123456789012'});
        });

        it('a quantity of 11 decimals is past the 10 it keeps, whoever drives; 10 decimals are asked', () => {
            for (const driver of DRIVERS) {
                expect(planTradeAmountRequest(input({driver, quantity: '1.01234567891'})), `driver ${driver}: 11 decimals`).toBeNull();
                expect(planTradeAmountRequest(input({driver, quantity: '1.0123456789'})), `driver ${driver}: 10 decimals`).not.toBeNull();
            }
        });

        it('16 significant digits are past the 15 it keeps: in the amount, in the unit price and in the quantity', () => {
            expect(planTradeAmountRequest(input({driver: 'amount', amount: '12345678901234.56'})), 'amount').toBeNull();
            expect(planTradeAmountRequest(input({driver: 'unit_price', unitPrice: '1234.123456789012'})), 'unit price').toBeNull();
            expect(planTradeAmountRequest(input({driver: 'amount', quantity: '999999999999999.5'})), 'quantity, driver amount').toBeNull();
            expect(planTradeAmountRequest(input({driver: 'unit_price', quantity: '999999999999999.5'})), 'quantity, driver unit price').toBeNull();
        });

        it('15 significant digits are asked: in the amount, in the unit price and in the quantity', () => {
            expect(planTradeAmountRequest(input({driver: 'amount', amount: '1234567890123.45'})), 'amount').toEqual({asset_id: 7, quantity: '12', mode: 'amount_to_price', value: '1234567890123.45'});
            expect(planTradeAmountRequest(input({driver: 'unit_price', unitPrice: '123.123456789012'})), 'unit price').toEqual({asset_id: 7, quantity: '12', mode: 'price_to_amount', value: '123.123456789012'});
            expect(planTradeAmountRequest(input({driver: 'amount', quantity: '99999999999999.5'})), 'quantity').toEqual({asset_id: 7, quantity: '99999999999999.5', mode: 'amount_to_price', value: '1000.8'});
        });

        it('the limits apply to the driving value only: a non-driving amount of 7 decimals does not stop a unit-price request', () => {
            expect(planTradeAmountRequest(input({driver: 'unit_price', amount: '0.1234567'}))).toEqual({asset_id: 7, quantity: '12', mode: 'price_to_amount', value: '83.4'});
        });
    });
});
