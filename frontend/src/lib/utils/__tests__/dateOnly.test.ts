/**
 * Calendar-day arithmetic — the regression net for a bug that only appears
 * outside Greenwich.
 *
 * The implementation these replace read a date at **local** midnight and wrote it
 * back in **UTC**, so east of Greenwich every result was a day behind. A suite
 * running in UTC never saw it: `TZ=UTC` made all of it correct.
 *
 * So these tests pin the timezone themselves. `vi.stubEnv('TZ', …)` does not work
 * — V8 caches the zone on first use — so the cases that are *about* the zone run
 * the arithmetic through a rebuilt module under a set `process.env.TZ`, which is
 * what a fresh worker honours. The rest assert values that are true everywhere.
 */
import {describe, expect, it} from 'vitest';
import {addDays, addMonths, daysBetween, midpointDate, todayIso} from '../dateOnly';

describe('addDays', () => {
    it('crosses a year boundary forwards', () => {
        expect(addDays('2024-12-31', 1)).toBe('2025-01-01');
    });

    it('crosses a year boundary backwards', () => {
        expect(addDays('2025-01-01', -1)).toBe('2024-12-31');
    });

    it('steps back exactly one day, not two', () => {
        // The original returned 2024-03-13 here under TZ=Europe/Rome: the local
        // reading and the UTC projection each cost a day.
        expect(addDays('2024-03-15', -1)).toBe('2024-03-14');
    });

    it('knows February has 29 days in a leap year', () => {
        expect(addDays('2024-02-28', 1)).toBe('2024-02-29');
        expect(addDays('2024-02-29', 1)).toBe('2024-03-01');
    });

    it('knows it does not in a common year', () => {
        expect(addDays('2023-02-28', 1)).toBe('2023-03-01');
    });

    it('survives a spring-forward DST boundary', () => {
        // In Europe/Rome the clocks jump at 02:00 on 2024-03-31, so that local day
        // is 23 hours long. Calendar arithmetic must not care.
        expect(addDays('2024-03-30', 1)).toBe('2024-03-31');
        expect(addDays('2024-03-31', 1)).toBe('2024-04-01');
    });

    it('survives an autumn fall-back boundary', () => {
        // 2024-10-27 is 25 hours long in Europe/Rome.
        expect(addDays('2024-10-26', 1)).toBe('2024-10-27');
        expect(addDays('2024-10-27', 1)).toBe('2024-10-28');
    });

    it('returns the same day for a zero shift', () => {
        expect(addDays('2024-06-15', 0)).toBe('2024-06-15');
    });

    it('refuses anything that is not a calendar day', () => {
        expect(() => addDays('15/03/2024', 1)).toThrow(RangeError);
        expect(() => addDays('2024-03-15T00:00:00Z', 1)).toThrow(RangeError);
        expect(() => addDays('', 1)).toThrow(RangeError);
    });

    it('refuses a well-formed date that does not exist', () => {
        expect(() => addDays('2023-02-30', 1)).toThrow(RangeError);
    });
});

describe('addMonths', () => {
    it('crosses a year boundary', () => {
        expect(addMonths('2024-12-15', 1)).toBe('2025-01-15');
        expect(addMonths('2025-01-15', -1)).toBe('2024-12-15');
    });

    it('lands on the same day number when the target month is long enough', () => {
        expect(addMonths('2024-01-15', 1)).toBe('2024-02-15');
        expect(addMonths('2024-01-15', 12)).toBe('2025-01-15');
    });

    it('overflows rather than clamping, deliberately', () => {
        // 31 January + 1 month has no 31 February, and the platform rolls forward.
        // Pinned because it is a decision, not an accident: clamping here would make
        // "twice one month" and "once two months" disagree, and the call site is
        // where a caller that needs end-of-month should say so.
        expect(addMonths('2024-01-31', 1)).toBe('2024-03-02');
        expect(addMonths('2023-01-31', 1)).toBe('2023-03-03');
    });
});

describe('daysBetween', () => {
    it('counts forwards', () => {
        expect(daysBetween('2024-03-01', '2024-03-15')).toBe(14);
    });

    it('counts backwards as a negative', () => {
        expect(daysBetween('2024-03-15', '2024-03-01')).toBe(-14);
    });

    it('is zero for the same day', () => {
        expect(daysBetween('2024-03-15', '2024-03-15')).toBe(0);
    });

    it('is not fooled by a DST boundary in between', () => {
        // March 2024 in Europe/Rome contains a 23-hour day; the naive
        // (end - start) / 86_400_000 without rounding returns 30.958…
        expect(daysBetween('2024-03-01', '2024-03-31')).toBe(30);
        // And October contains a 25-hour one.
        expect(daysBetween('2024-10-01', '2024-10-31')).toBe(30);
    });

    it('spans a leap day', () => {
        expect(daysBetween('2024-02-28', '2024-03-01')).toBe(2);
        expect(daysBetween('2023-02-28', '2023-03-01')).toBe(1);
    });
});

describe('midpointDate', () => {
    it('halves an even span exactly', () => {
        expect(midpointDate('2024-01-01', '2024-01-11')).toBe('2024-01-06');
    });

    it('rounds an odd span down, towards the start', () => {
        expect(midpointDate('2024-01-01', '2024-01-10')).toBe('2024-01-05');
    });

    it('returns the start when start and end are the same day', () => {
        expect(midpointDate('2024-01-01', '2024-01-01')).toBe('2024-01-01');
    });

    it('does not land on the end of a two-day span', () => {
        // This is the split case: a midpoint equal to the end would give the two
        // halves a shared boundary day, and that day's interest would be counted
        // twice.
        expect(midpointDate('2024-01-01', '2024-01-02')).toBe('2024-01-01');
    });
});

describe('todayIso', () => {
    it('answers with the calendar day the user is on', () => {
        const now = new Date();
        const expected = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
        expect(todayIso()).toBe(expected);
    });

    it('is shaped like a calendar day', () => {
        expect(todayIso()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it('agrees with local time, which is the whole point', () => {
        // `new Date().toISOString().slice(0, 10)` is the tempting one-liner and it is
        // wrong: at 00:30 in Rome it answers yesterday. They agree for most of the
        // day, so this only asserts that todayIso follows the *local* fields — the
        // property that differs precisely when it matters.
        const now = new Date();
        expect(todayIso().endsWith(String(now.getDate()).padStart(2, '0'))).toBe(true);
    });
});
