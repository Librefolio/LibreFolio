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

/**
 * W5-11: JavaScript's Date.UTC reads a year 0..99 as 1900..1999. A date typed with a short year (`0024-03-01` for
 * `2024-03-01`, the typo D-P4 wants to catch) must be read as the year 24, in the proleptic Gregorian calendar, so the
 * forms can warn about it. Valid range of a stored date: 0001-01-01 … 9999-12-31; year 0 is not a date.
 */
describe('parseTypedDate — years below 100 (W5-11)', () => {
    it.each(['0024-03-01', '0001-01-01', '0099-12-31', '0100-01-01', '0004-02-29', '9999-12-31'])('accepts canonical ISO %s as it is', (iso) => {
        expect(parseTypedDate(iso)).toBe(iso);
    });

    it('reads a day-first date with a four-digit short year, any separator', () => {
        expect(parseTypedDate('1/3/0024')).toBe('0024-03-01');
        expect(parseTypedDate('01.03.0024')).toBe('0024-03-01');
        expect(parseTypedDate('01-03-0024')).toBe('0024-03-01');
        expect(parseTypedDate('1/1/0001')).toBe('0001-01-01');
    });

    it('reads an ISO-order date written without padding, with the year padded to four digits', () => {
        expect(parseTypedDate('0024/3/1')).toBe('0024-03-01');
        expect(parseTypedDate('0001.1.1')).toBe('0001-01-01');
    });

    it('year 4 is a leap year in the proleptic calendar, year 100 is not', () => {
        expect(parseTypedDate('0004-02-29')).toBe('0004-02-29');
        expect(parseTypedDate('0024-02-29')).toBe('0024-02-29');
        expect(parseTypedDate('0100-02-29')).toBeNull();
        expect(parseTypedDate('0100-02-28')).toBe('0100-02-28');
        expect(parseTypedDate('0001-02-29')).toBeNull();
    });

    it('refuses year 0, and dates that do not exist, as before', () => {
        expect(parseTypedDate('0000-01-01')).toBeNull();
        expect(parseTypedDate('1/1/0000')).toBeNull();
        expect(parseTypedDate('2024-02-30')).toBeNull();
        expect(parseTypedDate('0024-02-30')).toBeNull();
        expect(parseTypedDate('0024-04-31')).toBeNull();
    });

    it('still refuses a two-digit year (unchanged)', () => {
        expect(parseTypedDate('1/3/24')).toBeNull();
        expect(parseTypedDate('24-03-01')).toBeNull();
    });

    it('always writes a four-digit padded year', () => {
        for (const typed of ['0024-03-01', '1/3/0024', '0001-01-01', '0099-12-31', '2024-03-01']) {
            expect(parseTypedDate(typed)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        }
    });
});
