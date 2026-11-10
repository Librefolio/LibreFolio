/**
 * formatAxisDate.test.ts — short locale-aware date for chart axes/tooltips.
 *
 * Locale output is ICU/timezone dependent, so the assertions avoid pinning an
 * exact string: they check the invariant contract instead — the year appears iff
 * `withYear`, and an unparseable input is echoed rather than shown as "Invalid
 * Date". A local-constructed timestamp keeps the mid-year date stable across the
 * runner's timezone.
 */
import {describe, expect, it} from 'vitest';
import {formatAxisDate, formatDayRange, parseDisplayDate} from '../formatAxisDate';

// 15 June 2024, noon local — a mid-year day so no timezone can shift it across a
// year (or even month) boundary and disturb the year-presence assertions.
const ts = new Date(2024, 5, 15, 12).getTime();

describe('formatAxisDate', () => {
    it('omits the year by default', () => {
        const out = formatAxisDate('en', ts);
        expect(out).not.toContain('2024');
        expect(out.length).toBeGreaterThan(0);
    });

    it('includes the year when withYear is set', () => {
        expect(formatAxisDate('en', ts, true)).toContain('2024');
    });

    it('accepts a string date as well as a timestamp', () => {
        expect(formatAxisDate('en', '2024-06-15T12:00:00', true)).toContain('2024');
    });

    it('echoes an unparseable string instead of rendering Invalid Date', () => {
        expect(formatAxisDate('en', 'not-a-date')).toBe('not-a-date');
    });

    it('echoes a NaN timestamp via String()', () => {
        expect(formatAxisDate('en', NaN)).toBe('NaN');
    });

    it('falls back to the environment locale when locale is empty', () => {
        const out = formatAxisDate('', ts, true);
        expect(out).toContain('2024');
    });
});

describe('a bare calendar day is not an instant', () => {
    it('renders the day it was given, not the day before it', () => {
        // `new Date('2024-03-15')` is midnight UTC by spec, so rendering it shows
        // 14 March to everyone west of Greenwich. Measured before the fix:
        // "Mar 14, 2024" in New York against "15 mar 2024" in Rome, from the same
        // string. Every opening, closing and lot boundary the API sends is a bare
        // YYYY-MM-DD — a calendar day with no instant attached — so the only
        // reading that means anything is the local one.
        //
        // This assertion is timezone-independent by construction: it does not name
        // an expected string, it states that the rendered day matches the day that
        // was asked for. It therefore fails in New York on the old code and passes
        // everywhere on the new, instead of passing in Rome either way.
        expect(formatAxisDate('en-US', '2024-03-15', true)).toContain('15');
        expect(formatAxisDate('en-US', '2024-01-01', true)).toContain('2024');
        expect(formatAxisDate('en-US', '2024-12-31', true)).toContain('31');
    });

    it('still treats a value with a time as the instant it is', () => {
        // The counterpart: an ISO timestamp *is* a point in time and must keep
        // converting into the reader's zone. Only the bare-day form is special.
        const noon = new Date(2024, 2, 15, 12, 0, 0).toISOString();
        expect(formatAxisDate('en-US', noon, true)).toContain('15');
    });

    it('leaves numeric timestamps alone', () => {
        const ts = new Date(2024, 5, 5, 12, 0, 0).getTime();
        expect(formatAxisDate('en-US', ts)).toContain('5');
    });

    it('still echoes something that is not a date at all', () => {
        expect(formatAxisDate('en-US', 'not-a-date')).toBe('not-a-date');
        // A day-shaped string that is not a real day falls through to the normal
        // parse, which rejects it — the regex matches the shape, not the calendar.
        expect(formatAxisDate('en-US', '2024-13-45')).toBe('2024-13-45');
    });
});

describe('parseDisplayDate — the parse, exported so every formatter shares it', () => {
    it('reads a bare day on the local calendar', () => {
        const d = parseDisplayDate('2024-03-15');
        expect(d).not.toBeNull();
        // Asserted through the components, not a rendered string, so the case is
        // meaningful in every timezone rather than only in the one it was written in.
        expect([d!.getFullYear(), d!.getMonth(), d!.getDate()]).toEqual([2024, 2, 15]);
    });

    it('reads a timestamped value as the instant it is', () => {
        const iso = new Date(2024, 2, 15, 12, 30).toISOString();
        expect(parseDisplayDate(iso)!.getDate()).toBe(15);
    });

    it('accepts a numeric timestamp', () => {
        expect(parseDisplayDate(new Date(2024, 5, 5).getTime())!.getMonth()).toBe(5);
    });

    it('returns null rather than a wrong date for an impossible day', () => {
        // Shape-valid, calendar-invalid: the constructor would roll it over into
        // February of the next year instead of refusing.
        expect(parseDisplayDate('2024-13-45')).toBeNull();
        expect(parseDisplayDate('2024-02-30')).toBeNull();
    });

    it('returns null for something that is not a date', () => {
        expect(parseDisplayDate('not-a-date')).toBeNull();
        expect(parseDisplayDate('')).toBeNull();
    });
});

// F8 (06/11/2026): the loss cards write the stretch of days a figure is about as one range, in the language of the interface.
describe('formatDayRange', () => {
    it('writes one year once when both days fall in it', () => {
        const out = formatDayRange('2026-10-07', '2026-11-05', 'en');

        expect(out.match(/2026/g)).toHaveLength(1);
        expect(out).toContain('Oct');
        expect(out).toContain('Nov');
        expect(out).toMatch(/[–-]/);
    });

    it('writes both years when the days are in different ones', () => {
        const out = formatDayRange('2025-12-05', '2026-01-09', 'en');

        expect(out).toContain('2025');
        expect(out).toContain('2026');
    });

    it('writes a single day when the two are one', () => {
        expect(formatDayRange('2026-11-05', '2026-11-05', 'en')).toBe(formatAxisDate('en', '2026-11-05', true));
    });

    it('follows the language: the same stretch in Italian names the months in Italian', () => {
        const out = formatDayRange('2026-10-07', '2026-11-05', 'it');

        expect(out).toMatch(/ott/i);
        expect(out).toMatch(/nov/i);
    });

    it('reads a calendar day as a local day, never through UTC', () => {
        // 1 January: a UTC reading shows 31 December west of Greenwich.
        expect(formatDayRange('2026-01-01', '2026-01-01', 'en')).toContain('1');
        expect(formatDayRange('2026-01-01', '2026-01-01', 'en')).toContain('Jan');
    });

    it('gives back what it cannot read, joined by an en dash, instead of «Invalid Date»', () => {
        expect(formatDayRange('x', '2026-11-05', 'en')).toBe('x \u2013 2026-11-05');
        expect(formatDayRange('2026-02-30', '2026-03-01', 'en')).toBe('2026-02-30 \u2013 2026-03-01');
    });
});
