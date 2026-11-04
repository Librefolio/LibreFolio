import {describe, expect, it} from 'vitest';

import {splitRowCharges, type ChargeDraft} from './splitRowCharges';

const fee = (amount: string): ChargeDraft => ({kind: 'fee', amount});

describe('splitRowCharges', () => {
    it('returns null for a row that carries no usable amount', () => {
        expect(splitRowCharges('', 'out', [fee('10')])).toBeNull();
        expect(splitRowCharges('0', 'out', [fee('10')])).toBeNull();
        expect(splitRowCharges('abc', 'out', [fee('10')])).toBeNull();
    });

    it('returns null when the row amount is nullish (defensive against an absent value)', () => {
        expect(splitRowCharges(null as unknown as number, 'out', [fee('10')])).toBeNull();
        expect(splitRowCharges(undefined as unknown as number, 'out', [fee('10')])).toBeNull();
    });

    it('stays untouched, and silent, until the user types a charge', () => {
        const split = splitRowCharges('-46603.73', 'out', [fee('')]);
        expect(split).not.toBeNull();
        expect(split!.touched).toBe(false);
        expect(split!.valid).toBe(false);
        expect(split!.error).toBeNull();
        expect(split!.total).toBe('46603.73');
    });

    it('takes the charges out of a purchase, leaving the clean price', () => {
        const split = splitRowCharges('-46603.73', 'out', [
            {kind: 'fee', amount: '12,50'},
            {kind: 'tax', amount: '2.00'},
        ]);
        expect(split!.valid).toBe(true);
        expect(split!.chargesTotal).toBe('14.50');
        expect(split!.main).toBe('46589.23');
        expect(split!.charges.map((c) => c.kind)).toEqual(['fee', 'tax']);
    });

    it('adds the charges back onto a sale, since the credit was already net', () => {
        const split = splitRowCharges('20180.00', 'in', [fee('30')]);
        expect(split!.valid).toBe(true);
        expect(split!.main).toBe('20210.00');
    });

    it('keeps the legs adding back up to the row, where floats would not', () => {
        const split = splitRowCharges('-50683.13', 'out', [fee('50018.11')]);
        expect(split!.main).toBe('665.02'); // 665.0199999999968 in binary floating point
        expect(Number(split!.main) + Number(split!.chargesTotal)).toBeCloseTo(50683.13, 10);
    });

    it('rejects a charge that would swallow the whole purchase', () => {
        const split = splitRowCharges('-100.00', 'out', [fee('100.00')]);
        expect(split!.valid).toBe(false);
        expect(split!.error).toBe('exceeds');
    });

    it('rejects a leg of zero or less rather than ignoring it', () => {
        const split = splitRowCharges('-100.00', 'out', [fee('0')]);
        expect(split!.valid).toBe(false);
        expect(split!.error).toBe('nonpositive');
    });

    it('ignores blank lines so a half-filled form still previews', () => {
        const split = splitRowCharges('-100.00', 'out', [fee('10'), fee('  ')]);
        expect(split!.valid).toBe(true);
        expect(split!.charges).toHaveLength(1);
        expect(split!.main).toBe('90.00');
    });

    it('accepts a comma decimal separator in what the user types', () => {
        // The row amount itself is machine data and always canonical; only the input is loose.
        const split = splitRowCharges('-1000.00', 'out', [fee('1,50')]);
        expect(split!.main).toBe('998.50');
    });

    it('carves out five named charges at once, the trade leg still being the remainder', () => {
        // The UI allows up to six legs; the arithmetic must not degrade as they pile up.
        const split = splitRowCharges('-20129.44', 'out', [
            {kind: 'fee', amount: '40.00'},
            {kind: 'tax', amount: '12.00'},
            {kind: 'accrued', amount: '11.33'},
            {kind: 'fee', amount: '0.55'},
            {kind: 'tax', amount: '0.12'},
        ]);

        expect(split!.valid).toBe(true);
        expect(split!.charges).toHaveLength(5);
        expect(split!.chargesTotal).toBe('64.00');
        expect(split!.main).toBe('20065.44');
        // The invariant the whole module exists for, at five legs.
        expect(Number(split!.main) + Number(split!.chargesTotal)).toBeCloseTo(20129.44, 10);
    });

    it('keeps the sum exact when a charge has more decimals than the row', () => {
        // A four-decimal charge widens the working scale; the remainder must follow it
        // rather than round to the row's two, which would lose a hundredth of a cent.
        const split = splitRowCharges('-1000.00', 'out', [fee('3.1416')]);

        expect(split!.chargesTotal).toBe('3.1416');
        expect(split!.main).toBe('996.8584');
        expect(Number(split!.main) + Number(split!.chargesTotal)).toBeCloseTo(1000, 10);
    });

    it('lets a sale be split too, charges having been withheld from the proceeds', () => {
        const split = splitRowCharges('34248.34', 'in', [
            {kind: 'fee', amount: '18.00'},
            {kind: 'accrued', amount: '132.19'},
        ]);

        expect(split!.valid).toBe(true);
        expect(split!.main).toBe('34398.53');
        expect(Number(split!.main) - Number(split!.chargesTotal)).toBeCloseTo(34248.34, 10);
    });

    it('has no ceiling on a sale: the gross may be any multiple of the net', () => {
        const split = splitRowCharges('100.00', 'in', [fee('1000.00')]);

        expect(split!.valid).toBe(true);
        expect(split!.error).toBeNull();
        expect(split!.main).toBe('1100.00');
    });

    it('refuses a purchase left at exactly zero, not only one gone negative', () => {
        const split = splitRowCharges('-100.00', 'out', [fee('60'), fee('40')]);

        expect(split!.main).toBe('0.00');
        expect(split!.error).toBe('exceeds');
        expect(split!.valid).toBe(false);
    });

    it('reports the unusable leg first when a row is both malformed and over budget', () => {
        // 'nonpositive' names something the user can act on directly; 'exceeds' may well
        // be a consequence of it, so it must not mask the cause.
        const split = splitRowCharges('-100.00', 'out', [fee('-5'), fee('200')]);

        expect(split!.error).toBe('nonpositive');
    });

    it('is not valid when every typed leg was unusable, even though one was typed', () => {
        const split = splitRowCharges('-100.00', 'out', [fee('abc')]);

        expect(split!.touched).toBe(true);
        expect(split!.charges).toHaveLength(0);
        expect(split!.valid).toBe(false);
    });

    it('reads the row amount as a magnitude whichever sign it arrives with', () => {
        const asDebit = splitRowCharges('-500.00', 'out', [fee('10')]);
        const asNumber = splitRowCharges(-500, 'out', [fee('10')]);

        expect(asDebit!.total).toBe('500.00');
        expect(asNumber!.main).toBe('490.00');
    });
});
