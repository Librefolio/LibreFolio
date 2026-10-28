/**
 * `formatDayWithWeekday` — the date of a chart tooltip header, with the weekday in brackets (Y2 FB-1).
 *
 * «12 Oct 2026 (Mon)»: the same day text `formatDay` writes, plus the weekday of that calendar day in the locale asked for. The weekday is
 * read on the local calendar like the day itself (never through UTC), and what is not a bare day comes back unchanged.
 */
import {describe, expect, it} from 'vitest';
import {formatDay, formatDayWithWeekday} from '../formatAxisDate';

describe('formatDayWithWeekday', () => {
    it('adds the short weekday in brackets after the day, in English', () => {
        // 2026-10-12 is a Monday, 2026-10-16 a Friday
        expect(formatDayWithWeekday('2026-10-12', 'en')).toBe(`${formatDay('2026-10-12', 'en')} (Mon)`);
        expect(formatDayWithWeekday('2026-10-16', 'en')).toBe(`${formatDay('2026-10-16', 'en')} (Fri)`);
    });

    it('writes the weekday in the language of the interface', () => {
        expect(formatDayWithWeekday('2026-10-12', 'it')).toMatch(/\(lun\)$/);
        expect(formatDayWithWeekday('2026-10-12', 'es')).toMatch(/\(lun\)$/);
        expect(formatDayWithWeekday('2026-10-12', 'fr')).toMatch(/\(lun\.?\)$/);
    });

    it('reads the weekday of the calendar day, whatever the time zone', () => {
        // 1 January 2027 is a Friday: a UTC reading west of Greenwich would say Thursday.
        expect(formatDayWithWeekday('2027-01-01', 'en')).toMatch(/\(Fri\)$/);
    });

    it('gives back what is not a bare day as it is', () => {
        expect(formatDayWithWeekday('Q3', 'en')).toBe('Q3');
        expect(formatDayWithWeekday('2026-13-45', 'en')).toBe('2026-13-45');
        // `new Date('1')` and `new Date('2025')` are real dates: a count and a year must not become days.
        expect(formatDayWithWeekday('1', 'en')).toBe('1');
        expect(formatDayWithWeekday('2025', 'en')).toBe('2025');
    });

    it('reads a number as the instant in milliseconds it is', () => {
        expect(formatDayWithWeekday(new Date(2026, 9, 12).getTime(), 'en')).toMatch(/\(Mon\)$/);
    });
});
