import {describe, expect, it} from 'vitest';

import {splitRowCharges, type ChargeDraft} from './splitRowCharges';

const fee = (amount: string): ChargeDraft => ({kind: 'fee', amount});

describe('splitRowCharges', () => {
    it('returns null for a row that carries no usable amount', () => {
        expect(splitRowCharges('', 'out', [fee('10')])).toBeNull();
        expect(splitRowCharges('0', 'out', [fee('10')])).toBeNull();
        expect(splitRowCharges('abc', 'out', [fee('10')])).toBeNull();
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
});
