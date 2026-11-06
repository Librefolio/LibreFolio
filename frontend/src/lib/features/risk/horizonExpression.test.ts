/**
 * horizonExpression — the simulation horizon as `2y3m5d` (F-8; Vitest).
 *
 * A fixed sum, by the developer's decision of 05/11/2026: a year is 365 days, a month 30, a day 1, and the parts add up, so no
 * test depends on a date and every expected number is a literal written here.
 *
 * Pinned:
 * - a plain number is days, as the field always was;
 * - the three units in the four interface languages (the letters are an argument; the catalogue is tested apart);
 * - the sum: `2a3m5g` is 730 + 90 + 5 = 825, and a value past its natural range is as good as any (`24m66g` = 786);
 * - the letters in any order and repeated, all of them counting (developer, 06/11/2026): `30g 1a 2m` = 455, `1a1a2m2m` = 850;
 * - a number with no letter beside letters (`1a 30`) is an error;
 * - the engine's bounds, and every malformed text, give an error and no number.
 */
import {describe, expect, it} from 'vitest';

import {DAYS_PER_MONTH, DAYS_PER_YEAR, HORIZON_MAX_DAYS, parseHorizon, type HorizonUnits} from './horizonExpression';

const IT: HorizonUnits = {year: 'a', month: 'm', day: 'g'};
const EN: HorizonUnits = {year: 'y', month: 'm', day: 'd'};
const FR: HorizonUnits = {year: 'a', month: 'm', day: 'j'};
const ES: HorizonUnits = {year: 'a', month: 'm', day: 'd'};

function days(text: string, units: HorizonUnits = IT): number | string {
    const parsed = parseHorizon(text, units);
    return parsed.ok ? parsed.days : parsed.error;
}

describe('parseHorizon — a plain number of days', () => {
    it('reads digits as days, with no parts', () => {
        expect(parseHorizon('365', IT)).toEqual({ok: true, days: 365, parts: null});
        expect(days('  30 ')).toBe(30);
    });

    it('refuses zero, and anything past the engine maximum', () => {
        expect(days('0')).toBe('tooShort');
        expect(days(String(HORIZON_MAX_DAYS))).toBe(HORIZON_MAX_DAYS);
        expect(days(String(HORIZON_MAX_DAYS + 1))).toBe('tooLong');
    });

    it('refuses an empty text, a decimal and a sign', () => {
        expect(days('')).toBe('empty');
        expect(days('   ')).toBe('empty');
        expect(days('1.5')).toBe('format');
        expect(days('-5')).toBe('format');
    });
});

describe('parseHorizon — years, months and days: a fixed sum', () => {
    it('counts a year as 365 days, a month as 30 and a day as 1', () => {
        expect([DAYS_PER_YEAR, DAYS_PER_MONTH]).toEqual([365, 30]);
        expect(days('1a')).toBe(365);
        expect(days('1m')).toBe(30);
        expect(days('1g')).toBe(1);
    });

    it('adds the parts: 2a3m5g is 730 + 90 + 5 = 825, in each language’s letters', () => {
        expect(days('2a3m5g', IT)).toBe(825);
        expect(days('2y3m5d', EN)).toBe(825);
        expect(days('2a3m5j', FR)).toBe(825);
        expect(days('2a3m5d', ES)).toBe(825);
    });

    it('takes a value past its natural range: 24m66g is 720 + 66 = 786', () => {
        expect(days('24m66g')).toBe(786);
        expect(days('15m')).toBe(450);
        expect(days('400g')).toBe(400);
        expect(days('1a400g')).toBe(765);
    });

    it('returns the parts it read', () => {
        expect(parseHorizon('2a3m5g', IT)).toMatchObject({ok: true, parts: {years: 2, months: 3, days: 5}});
        expect(parseHorizon('18m', IT)).toMatchObject({ok: true, parts: {years: 0, months: 18, days: 0}});
    });

    it("takes only the interface language's letters", () => {
        expect(days('2y3m5d', IT)).toBe('format');
        expect(days('2a3m5g', EN)).toBe('format');
        // French has no «g»: it is the day in Italian only.
        expect(days('5g', FR)).toBe('format');
    });

    it('is case-insensitive and allows spaces between parts', () => {
        expect(days('2A 3M 5G')).toBe(825);
        expect(days('1a 6m')).toBe(545);
    });

    it('takes the parts in any order and adds them up (developer, 06/11/2026)', () => {
        expect(days('30g 1a 2m')).toBe(455);
        expect(days('3m2a')).toBe(820);
        expect(days('5g1m')).toBe(35);
    });

    it('takes a unit as often as it is written, and every one counts', () => {
        expect(days('1a1a2m2m')).toBe(850);
        expect(days('1a1a')).toBe(730);
        expect(days('10g 10g 10g')).toBe(30);
    });

    it('does not forgive a number with no letter beside letters', () => {
        expect(days('1a 30')).toBe('format');
        expect(days('30 1a')).toBe('format');
        expect(days('1a30')).toBe('format');
        expect(days('1a 2m 3')).toBe('format');
    });

    it('still refuses a unit of another language when the order is free', () => {
        expect(days('1y 2m', IT)).toBe('format');
        expect(days('30g 1a', EN)).toBe('format');
    });

    it('refuses anything that is not a count and a unit', () => {
        expect(days('a')).toBe('format');
        expect(days('2a3')).toBe('format');
        expect(days('2a,3m')).toBe('format');
        expect(days('2.5a')).toBe('format');
        expect(days('due anni')).toBe('format');
    });

    it('refuses a total of zero days and one past the maximum', () => {
        expect(days('0g')).toBe('tooShort');
        expect(days('0a0m0g')).toBe('tooShort');
        // 3650 is ten years of 365 days, exactly: the bound is on the sum, not on a part.
        expect(days('10a')).toBe(3650);
        expect(days('10a1g')).toBe('tooLong');
        expect(days('122m')).toBe('tooLong');
        // The bound is on the sum, so repeated parts can cross it too.
        expect(days('5a5a1g')).toBe('tooLong');
        expect(days('99999999999a')).toBe('tooLong');
    });
});
