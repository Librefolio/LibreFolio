/**
 * txTradeAmount — the logic of «Total amount / Unit price» in the transaction form (#47), no DOM, no network.
 *
 *   - `driverAfterEdit(current, edit)`: the driver is the value written LAST. Typing an amount gives it to `amount`, typing in
 *     the unit-price field gives it to `unit_price`; a new quantity or asset is not a write of either, so it keeps
 *     whoever drives and the other value is recalculated from it.
 *   - `amountFromUnitPrice` / `unitPriceFromAmount`: exact decimal arithmetic on BigInt, `amount = quantity /
 *     quote_base_quantity × price`, rounded half-even to the stored scales (amount 6 decimals, unit price 12).
 *   - `calculateTradeValue(input)`: which of the two to calculate, or `null` for every state with nothing to calculate:
 *     asset not known, a quantity or a driving value that is blank, zero, negative, not a number, or past the limits the
 *     backend keeps (quantity 10 decimals, amount 6, unit price 12, 15 significant digits).
 *
 * Parity corpus. The calculation used to live in the backend, as Python `Decimal` with `ROUND_HALF_EVEN`:
 * `amount = (quantity × price / base).quantize(1e-6)`, `price = (amount × base / quantity).quantize(1e-12)`. The two
 * tables `AMOUNT_PARITY` and `PRICE_PARITY` hold the answers that code gave (generated once at precision 80 and pasted
 * here as data: the test never calculates its own expectation), so the move to the browser is proved to change no digit.
 * The tables cover both bases (1, 100, and a few more), ties at the 7th decimal of an amount and at the 13th of a price
 * in both directions (down to an even digit, up to an even digit), and products a float already gets wrong.
 *
 * The inputs arrive canonical (dot decimal, the comma already normalised by the field).
 */
import {describe, expect, it} from 'vitest';
import {AMOUNT_DECIMALS, UNIT_PRICE_DECIMALS, amountFromUnitPrice, calculateTradeValue, driverAfterEdit, unitPriceFromAmount, type TradeAmountDriver, type TradeAmountEdit, type TradeAmountInput} from './txTradeAmount';

const DRIVERS: TradeAmountDriver[] = ['amount', 'unit_price'];

// [base, quantity, unit price, amount] — generated once by a throwaway script (Python Decimal, prec 80, ROUND_HALF_EVEN), pasted as data.
const AMOUNT_PARITY: Array<[number, string, string, string]> = [
    [1, '3', '0.1', '0.3'],
    [1, '12', '83.4', '1000.8'],
    [1, '0.1', '0.2', '0.02'],
    [1, '1', '0.0000005', '0'],
    [1, '1', '0.0000015', '0.000002'],
    [1, '1', '0.0000025', '0.000002'],
    [1, '1', '0.0000035', '0.000004'],
    [1, '1', '0.0000045', '0.000004'],
    [1, '1', '0.0000055', '0.000006'],
    [1, '2', '0.0000025', '0.000005'],
    [1, '0.5', '0.000001', '0'],
    [1, '0.5', '0.000003', '0.000002'],
    [1, '999999999999999', '1', '999999999999999'],
    [1, '0.000000001', '1', '0'],
    [1, '123456789.123456', '0.123456789', '15241578.765432'],
    [1, '1000', '0.001', '1'],
    [1, '7', '1.1', '7.7'],
    [1, '1234567.891', '0.0001', '123.456789'],
    [1, '0.0000000001', '1000000', '0.0001'],
    [1, '333.333333', '3', '999.999999'],
    [100, '1000', '98.5', '985'],
    [100, '10', '101.25', '10.125'],
    [100, '1', '0.00005', '0'],
    [100, '1', '0.00015', '0.000002'],
    [100, '1', '0.00025', '0.000002'],
    [100, '3', '0.0005', '0.000015'],
    [100, '7', '13.3', '0.931'],
    [100, '12345', '99.999999', '12344.999877'],
    [100, '0.5', '100', '0.5'],
    [100, '1', '0.00035', '0.000004'],
    [1000, '1', '0.5', '0.0005'],
    [1000, '1', '0.0005', '0'],
    [1000, '1', '0.0015', '0.000002'],
    [1000, '1', '0.0025', '0.000002'],
    [7, '1', '0.0000105', '0.000002'],
    [7, '100', '3.3333', '47.618571'],
    [1, '684', '826.811967', '565539.385428'],
    [1, '976', '742.908884', '725079.070784'],
    [1000, '23687.164402', '914.870753', '21670.693933'],
    [1000, '194045.1676', '838.898229', '162784.147446'],
    [1, '16', '155.496081', '2487.937296'],
    [1, '62116.8960', '556.1288', '34544994.832205'],
    [1, '93.28', '102.376629', '9549.691953'],
    [1000, '68', '689.646994', '46.895996'],
    [100, '39737', '594.345056', '236174.894903'],
    [10, '71', '464.909269', '3300.85581'],
    [100, '670901797.6', '268.82847', '1803575037.690577'],
    [1, '221421', '516.513011', '114366827.408631'],
];
// [base, quantity, amount, unit price] — same generator.
const PRICE_PARITY: Array<[number, string, string, string]> = [
    [1, '12', '1000.8', '83.4'],
    [1, '12', '1000.9', '83.408333333333'],
    [1, '3', '1', '0.333333333333'],
    [1, '7', '1', '0.142857142857'],
    [1, '1', '1', '1'],
    [1, '8192', '1', '0.000122070312'],
    [1, '8192', '3', '0.000366210938'],
    [1, '8192', '5', '0.000610351562'],
    [1, '8192', '7', '0.000854492188'],
    [1, '16384', '1', '0.000061035156'],
    [1, '16384', '3', '0.000183105469'],
    [1, '0.5', '1000.8', '2001.6'],
    [1, '0.0000000001', '1', '10000000000'],
    [1, '999999999999999', '1', '0'],
    [1, '1', '999999999.999999', '999999999.999999'],
    [1, '123456.789', '98765.4321', '0.80000000729'],
    [1, '333.333333', '1000', '3.000000003'],
    [1, '1', '0.000001', '0.000001'],
    [100, '1000', '985', '98.5'],
    [100, '10', '1012.5', '10125'],
    [100, '8192', '1', '0.01220703125'],
    [100, '8192', '3', '0.03662109375'],
    [100, '3', '7', '233.333333333333'],
    [100, '7', '1', '14.285714285714'],
    [100, '12345', '1234500', '10000'],
    [100, '1', '0.000001', '0.0001'],
    [100, '99999', '1', '0.00100001'],
    [1000, '8192', '1', '0.1220703125'],
    [1000, '8192', '3', '0.3662109375'],
    [7, '9', '1', '0.777777777778'],
    [7, '13', '5', '2.692307692308'],
    [1, '42179', '7943.639997', '0.188331634154'],
    [100, '5', '8432.580964', '168651.61928'],
    [1000, '803', '96132.304587', '119716.444068493151'],
    [10, '3572', '69378.178873', '194.227824392497'],
    [1, '88', '87504.258182', '994.36657025'],
    [10, '3762', '81164.965757', '215.749510252525'],
    [1, '56631', '11471.926038', '0.202573255602'],
    [10, '61250', '89710.302216', '14.646579953633'],
    [1, '99743', '12212.47088', '0.122439378001'],
    [10, '2323', '28995.875947', '124.820817679724'],
    [1, '766', '54539.380413', '71.20023552611'],
    [1000, '323', '7907.924034', '24482.736947368421'],
];

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

// ---------------------------------------------------------------------------------------------------------------------
// The arithmetic
// ---------------------------------------------------------------------------------------------------------------------

describe('the scales are the backend columns', () => {
    it('an amount keeps 6 decimals and a unit price 12', () => {
        expect(AMOUNT_DECIMALS).toBe(6);
        expect(UNIT_PRICE_DECIMALS).toBe(12);
    });
});

describe('amountFromUnitPrice — amount = quantity / base × price, half-even at 6 decimals', () => {
    // base, quantity, unit price, amount. Written by hand: each row is a sum a person can do on paper.
    const TABLE: Array<[number, string, string, string]> = [
        [1, '12', '83.4', '1000.8'], // the float says 1000.8000000000001
        [1, '3', '0.1', '0.3'], // the float says 0.30000000000000004
        [1, '0.1', '0.2', '0.02'],
        [1, '7', '1.1', '7.7'], // the float says 7.700000000000001
        [100, '1000', '98.5', '985'], // a bond quoted per 100 nominal
        [100, '10', '101.25', '10.125'],
        [100, '7', '13.3', '0.931'],
        [1000, '1', '0.5', '0.0005'],
        [1, '10', '5', '50'], // an integer has no point
        [1, '0.5', '2', '1'],
        [1, '2', '0.0000001', '0'], // zero is `0`, not `0.000000`
        [1, '999999999999999', '999999999999', '999999999998999000000000001'], // no exponent, ever
    ];

    it.each(TABLE)('base %s, quantity %s × price %s → %s', (base, quantity, price, expected) => {
        expect(amountFromUnitPrice(quantity, price, base)).toBe(expected);
    });

    it('a leading or trailing point is read as the decimal it is', () => {
        expect(amountFromUnitPrice('.5', '4', 1)).toBe('2');
        expect(amountFromUnitPrice('5.', '4', 1)).toBe('20');
        expect(amountFromUnitPrice('007', '2', 1)).toBe('14');
    });

    it('the result is plain text: no exponent, no trailing zero in the fraction, no point on an integer', () => {
        for (const [base, quantity, price] of AMOUNT_PARITY.map(([b, q, p]) => [b, q, p] as const)) {
            const amount = amountFromUnitPrice(quantity, price, base);
            expect(amount, `${quantity} × ${price} / ${base}`).toMatch(/^(0|[1-9]\d*)(\.\d*[1-9])?$/);
        }
    });

    describe('half-even at the 7th decimal', () => {
        // quantity 1, base 1: the amount is the price itself, rounded.
        it.each([
            ['0.0000005', '0'], // tie, 0 is even → down
            ['0.0000015', '0.000002'], // tie, 1 is odd → up
            ['0.0000025', '0.000002'], // tie, 2 is even → down
            ['0.0000035', '0.000004'], // tie, 3 is odd → up
            ['0.0000045', '0.000004'],
            ['0.0000055', '0.000006'],
            ['0.0000065', '0.000006'],
            ['0.0000075', '0.000008'],
            ['0.0000085', '0.000008'],
            ['0.0000095', '0.00001'], // tie, 9 is odd → up, and the carry drops the trailing zero
        ])('price %s → %s', (price, expected) => {
            expect(amountFromUnitPrice('1', price, 1)).toBe(expected);
        });

        it('one digit past a tie is no tie: above rounds up, below rounds down, whatever the parity', () => {
            expect(amountFromUnitPrice('1', '0.00000050000001', 1)).toBe('0.000001');
            expect(amountFromUnitPrice('1', '0.00000049999999', 1)).toBe('0');
            expect(amountFromUnitPrice('1', '0.00000250000001', 1)).toBe('0.000003');
            expect(amountFromUnitPrice('1', '0.00000149999999', 1)).toBe('0.000001');
        });

        it('a tie made by the quantity and by the base, not by the price alone', () => {
            expect(amountFromUnitPrice('0.5', '0.000003', 1)).toBe('0.000002'); // 0.0000015 → up to even 2
            expect(amountFromUnitPrice('0.5', '0.000001', 1)).toBe('0'); // 0.0000005 → down to even 0
            expect(amountFromUnitPrice('1', '0.00005', 100)).toBe('0'); // 0.0000005
            expect(amountFromUnitPrice('1', '0.00015', 100)).toBe('0.000002'); // 0.0000015
            expect(amountFromUnitPrice('1', '0.00025', 100)).toBe('0.000002'); // 0.0000025
            expect(amountFromUnitPrice('1', '0.00035', 100)).toBe('0.000004'); // 0.0000035
        });
    });
});

describe('unitPriceFromAmount — price = amount × base / quantity, half-even at 12 decimals', () => {
    const TABLE: Array<[number, string, string, string]> = [
        [1, '12', '1000.8', '83.4'],
        [1, '12', '1000.9', '83.408333333333'], // 12 decimals, the rest is dropped
        [1, '3', '1', '0.333333333333'],
        [1, '2', '1', '0.5'],
        [1, '0.5', '1000.8', '2001.6'],
        [1, '1', '1', '1'], // an integer has no point
        [1, '4', '2', '0.5'],
        [100, '1000', '985', '98.5'],
        [100, '10', '1012.5', '10125'],
        [100, '3', '7', '233.333333333333'],
        [1000, '8192', '1', '0.1220703125'],
        [1, '0.0000000001', '1', '10000000000'],
        [1, '999999999999999', '1', '0'], // below the last decimal: zero is `0`
    ];

    it.each(TABLE)('base %s, quantity %s, amount %s → %s', (base, quantity, amount, expected) => {
        expect(unitPriceFromAmount(quantity, amount, base)).toBe(expected);
    });

    it('a leading or trailing point is read as the decimal it is', () => {
        expect(unitPriceFromAmount('.5', '1', 1)).toBe('2');
        expect(unitPriceFromAmount('2.', '5.', 1)).toBe('2.5');
    });

    it('the result is plain text: no exponent, no trailing zero in the fraction, no point on an integer', () => {
        for (const [base, quantity, amount] of PRICE_PARITY.map(([b, q, a]) => [b, q, a] as const)) {
            const price = unitPriceFromAmount(quantity, amount, base);
            expect(price, `${amount} × ${base} / ${quantity}`).toMatch(/^(0|[1-9]\d*)(\.\d*[1-9])?$/);
        }
    });

    describe('half-even at the 13th decimal', () => {
        // 1/8192 = 0.0001220703125 and 3/8192 = 0.0003662109375 end exactly on a 5 at the 13th decimal: true ties.
        it.each([
            ['1', '0.000122070312'], // …312|5, 2 is even → down
            ['3', '0.000366210938'], // …937|5, 7 is odd → up
            ['5', '0.000610351562'], // …562|5 → down
            ['7', '0.000854492188'], // …187|5, 7 is odd → up
        ])('amount %s over quantity 8192 → %s', (amount, expected) => {
            expect(unitPriceFromAmount('8192', amount, 1)).toBe(expected);
        });

        it('quantity 16384: ties in both directions too', () => {
            expect(unitPriceFromAmount('16384', '1', 1)).toBe('0.000061035156'); // …156|25, below the tie
            expect(unitPriceFromAmount('16384', '3', 1)).toBe('0.000183105469'); // …468|75, above the tie
        });

        it('a base shifts the point, not the rounding rule', () => {
            expect(unitPriceFromAmount('8192', '1', 100)).toBe('0.01220703125');
            expect(unitPriceFromAmount('8192', '3', 100)).toBe('0.03662109375');
        });

        it('one digit past a tie is no tie: 1/81920 ends …031|25 (down), 3/81920 ends …093|75 (up)', () => {
            expect(unitPriceFromAmount('81920', '1', 1)).toBe('0.000012207031');
            expect(unitPriceFromAmount('81920', '3', 1)).toBe('0.000036621094');
        });
    });
});

describe('the round trip', () => {
    it('unit price → amount → unit price is the identity when the amount is exact', () => {
        const EXACT: Array<[number, string, string]> = [
            [1, '12', '83.4'],
            [1, '3', '0.1'],
            [100, '1000', '98.5'],
            [100, '10', '101.25'],
            [100, '7', '13.3'],
            [1000, '1', '0.5'],
            [1, '0.5', '2001.6'],
        ];
        for (const [base, quantity, price] of EXACT) {
            const amount = amountFromUnitPrice(quantity, price, base);
            expect(unitPriceFromAmount(quantity, amount, base), `${quantity} × ${price} / ${base} = ${amount}`).toBe(price);
        }
    });

    it('amount → unit price → amount gives the amount back when the quantity is small against the base (the 12-decimal price is finer than the 6-decimal amount)', () => {
        // quantity / base below 1e5 → the price's rounding error (5e-13) times it stays under half an amount step (5e-7).
        const rows = PRICE_PARITY.filter(([base, quantity]) => Number(quantity) / base < 1e5);
        expect(rows.length, 'the corpus has rows for this').toBeGreaterThan(20);
        for (const [base, quantity, amount] of rows) {
            const price = unitPriceFromAmount(quantity, amount, base);
            expect(amountFromUnitPrice(quantity, price, base), `${amount} over ${quantity} on base ${base} → ${price}`).toBe(amount);
        }
    });
});

describe('parity with the backend this replaces (Python Decimal, ROUND_HALF_EVEN)', () => {
    // [base, quantity, unit price, amount]: (quantity × price / base).quantize(1e-6), precision 80. Generated once, pasted as data.
    it.each(AMOUNT_PARITY)('base %s, quantity %s × price %s → %s', (base, quantity, price, expected) => {
        expect(amountFromUnitPrice(quantity, price, base)).toBe(expected);
    });
});

describe('parity with the backend this replaces: the unit price', () => {
    // [base, quantity, amount, unit price]: (amount × base / quantity).quantize(1e-12), precision 80. Generated once, pasted as data.
    it.each(PRICE_PARITY)('base %s, quantity %s, amount %s → %s', (base, quantity, amount, expected) => {
        expect(unitPriceFromAmount(quantity, amount, base)).toBe(expected);
    });
});

// ---------------------------------------------------------------------------------------------------------------------
// What to calculate, and when not to
// ---------------------------------------------------------------------------------------------------------------------

describe('calculateTradeValue', () => {
    /** A state with both values filled, so a test names only what it changes. */
    function input(overrides: Partial<TradeAmountInput> = {}): TradeAmountInput {
        return {driver: 'amount', quoteBaseQuantity: 1, quantity: '12', amount: '1000.8', unitPrice: '83.4', ...overrides};
    }

    describe('what is calculated', () => {
        it('driver amount → the unit price: mode amount_to_price', () => {
            expect(calculateTradeValue(input({driver: 'amount'}))).toEqual({mode: 'amount_to_price', result: '83.4'});
        });

        it('driver unit_price → the amount: mode price_to_amount', () => {
            expect(calculateTradeValue(input({driver: 'unit_price'}))).toEqual({mode: 'price_to_amount', result: '1000.8'});
        });

        it('base 100 (a bond): the price is per 100 units, the amount is the quantity over the base times the price', () => {
            expect(calculateTradeValue(input({driver: 'unit_price', quoteBaseQuantity: 100, quantity: '1000', unitPrice: '98.5'}))).toEqual({mode: 'price_to_amount', result: '985'});
            expect(calculateTradeValue(input({driver: 'amount', quoteBaseQuantity: 100, quantity: '1000', amount: '985'}))).toEqual({mode: 'amount_to_price', result: '98.5'});
        });

        it('the value that does not drive is never looked at, even when it is no number', () => {
            expect(calculateTradeValue(input({driver: 'amount', unitPrice: 'abc'}))?.result).toBe('83.4');
            expect(calculateTradeValue(input({driver: 'unit_price', amount: ''}))?.result).toBe('1000.8');
        });

        it('a result that rounds to nothing is the text `0`, not null: the sum was done', () => {
            expect(calculateTradeValue(input({driver: 'unit_price', quantity: '1', unitPrice: '0.0000001'}))).toEqual({mode: 'price_to_amount', result: '0'});
        });

        it('every parity row that is inside the limits gives the corpus answer through the full entry point', () => {
            let calculated = 0;
            for (const [base, quantity, price, amount] of AMOUNT_PARITY) {
                const value = calculateTradeValue(input({driver: 'unit_price', quoteBaseQuantity: base, quantity, unitPrice: price}));
                if (value === null) continue; // past a limit the form refuses (e.g. 16 significant digits)
                calculated++;
                expect(value, `${quantity} × ${price} / ${base}`).toEqual({mode: 'price_to_amount', result: amount});
            }
            for (const [base, quantity, amount, price] of PRICE_PARITY) {
                const value = calculateTradeValue(input({driver: 'amount', quoteBaseQuantity: base, quantity, amount}));
                if (value === null) continue;
                calculated++;
                expect(value, `${amount} over ${quantity} on base ${base}`).toEqual({mode: 'amount_to_price', result: price});
            }
            expect(calculated, 'most of the corpus is inside the limits').toBeGreaterThan((AMOUNT_PARITY.length + PRICE_PARITY.length) * 0.8);
        });
    });

    describe('the quote base', () => {
        it('an asset that is not known (null or undefined) calculates nothing, for either driver', () => {
            for (const driver of DRIVERS) {
                expect(calculateTradeValue(input({driver, quoteBaseQuantity: null})), `null, ${driver}`).toBeNull();
                expect(calculateTradeValue(input({driver, quoteBaseQuantity: undefined})), `undefined, ${driver}`).toBeNull();
            }
        });

        it.each([0, -1, -100, 2.5, Number.NaN, Number.POSITIVE_INFINITY])('a base of %s counts as 1, the way the backend reads it', (base) => {
            const withOne = calculateTradeValue(input({driver: 'unit_price', quoteBaseQuantity: 1}));
            expect(withOne?.result).toBe('1000.8');
            expect(calculateTradeValue(input({driver: 'unit_price', quoteBaseQuantity: base})), `unit price, base ${base}`).toEqual(withOne);
            expect(calculateTradeValue(input({driver: 'amount', quoteBaseQuantity: base})), `amount, base ${base}`).toEqual(calculateTradeValue(input({driver: 'amount', quoteBaseQuantity: 1})));
        });

        it('the base changes the answer: same quantity and price, base 1 against base 100', () => {
            const one = calculateTradeValue(input({driver: 'unit_price', quoteBaseQuantity: 1}));
            const hundred = calculateTradeValue(input({driver: 'unit_price', quoteBaseQuantity: 100}));
            expect(one?.result).toBe('1000.8');
            expect(hundred?.result).toBe('10.008');
        });
    });

    describe('nothing to calculate → null', () => {
        const NOT_A_POSITIVE_DECIMAL = ['', ' ', '0', '0.0', '0.000000', '-0', '-1', '-0.5', 'abc', '1e3', '1,5', '.', '-', '+5', '1.2.3', '١٢'];

        it.each(NOT_A_POSITIVE_DECIMAL)('quantity %j → null for either driver', (quantity) => {
            for (const driver of DRIVERS) expect(calculateTradeValue(input({driver, quantity})), driver).toBeNull();
        });

        it.each(NOT_A_POSITIVE_DECIMAL)('driving amount %j → null', (amount) => {
            expect(calculateTradeValue(input({driver: 'amount', amount}))).toBeNull();
        });

        it.each(NOT_A_POSITIVE_DECIMAL)('driving unit price %j → null', (unitPrice) => {
            expect(calculateTradeValue(input({driver: 'unit_price', unitPrice}))).toBeNull();
        });
    });

    describe('past the limits the backend keeps → null; at the limit → calculated', () => {
        it('quantity: 10 decimals pass, 11 do not', () => {
            for (const driver of DRIVERS) {
                expect(calculateTradeValue(input({driver, quantity: '0.0000000001'})), `10 decimals, ${driver}`).not.toBeNull();
                expect(calculateTradeValue(input({driver, quantity: '0.00000000001'})), `11 decimals, ${driver}`).toBeNull();
            }
        });

        it('amount: 6 decimals pass, 7 do not (trailing zeros past the 6th are not decimals)', () => {
            expect(calculateTradeValue(input({driver: 'amount', amount: '1000.123456'}))).not.toBeNull();
            expect(calculateTradeValue(input({driver: 'amount', amount: '1000.1234567'}))).toBeNull();
            expect(calculateTradeValue(input({driver: 'amount', amount: '1000.1234560'}))).not.toBeNull();
        });

        it('unit price: 12 decimals pass, 13 do not', () => {
            expect(calculateTradeValue(input({driver: 'unit_price', unitPrice: '0.123456789012'}))).not.toBeNull();
            expect(calculateTradeValue(input({driver: 'unit_price', unitPrice: '0.1234567890123'}))).toBeNull();
        });

        it('15 significant digits pass, 16 do not — for the quantity, the amount and the price', () => {
            expect(calculateTradeValue(input({driver: 'amount', quantity: '123456789012345'}))).not.toBeNull();
            expect(calculateTradeValue(input({driver: 'amount', quantity: '1234567890123456'}))).toBeNull();
            expect(calculateTradeValue(input({driver: 'amount', amount: '123456789.123456'}))).not.toBeNull();
            expect(calculateTradeValue(input({driver: 'amount', amount: '1234567890.123456'}))).toBeNull();
            expect(calculateTradeValue(input({driver: 'unit_price', unitPrice: '123456789012345'}))).not.toBeNull();
            expect(calculateTradeValue(input({driver: 'unit_price', unitPrice: '1234567890123456'}))).toBeNull();
        });

        it('the limit is on the value that drives: a long unit price is ignored while the amount drives', () => {
            expect(calculateTradeValue(input({driver: 'amount', unitPrice: '0.1234567890123456789'}))).not.toBeNull();
            expect(calculateTradeValue(input({driver: 'unit_price', amount: '1000.1234567'}))).not.toBeNull();
        });
    });
});
