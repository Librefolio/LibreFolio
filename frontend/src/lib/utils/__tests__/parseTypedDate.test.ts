import {describe, expect, it} from 'vitest';
import {parseTypedDate} from '$lib/utils/core/parseTypedDate';

describe('parseTypedDate', () => {
    it('accepts canonical ISO', () => {
        expect(parseTypedDate('2026-08-07')).toBe('2026-08-07');
        expect(parseTypedDate('  2026-08-07 ')).toBe('2026-08-07');
    });

    it('accepts ISO order with any separator and no padding', () => {
        expect(parseTypedDate('2026/8/7')).toBe('2026-08-07');
        expect(parseTypedDate('2026.8.7')).toBe('2026-08-07');
        expect(parseTypedDate('2026-8-7')).toBe('2026-08-07');
    });

    it('accepts day-first order', () => {
        expect(parseTypedDate('7/8/2026')).toBe('2026-08-07');
        expect(parseTypedDate('07.08.2026')).toBe('2026-08-07');
        expect(parseTypedDate('31-12-2024')).toBe('2024-12-31');
    });

    it('refuses a missing or short year', () => {
        expect(parseTypedDate('7/8/26')).toBeNull();
        expect(parseTypedDate('08-07')).toBeNull();
    });

    it('refuses dates that do not exist', () => {
        expect(parseTypedDate('2026-02-30')).toBeNull();
        expect(parseTypedDate('31/2/2026')).toBeNull();
        expect(parseTypedDate('2026-13-01')).toBeNull();
    });

    it('refuses junk', () => {
        expect(parseTypedDate('')).toBeNull();
        expect(parseTypedDate('domani')).toBeNull();
        expect(parseTypedDate('2026')).toBeNull();
    });
});
