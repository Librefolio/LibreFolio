/**
 * formatDateTime.test.ts — locale-aware date+time label for file listings.
 *
 * Like formatAxisDate, the exact string is ICU/timezone dependent, so the
 * assertions pin the *contract* rather than a literal: the date parts are
 * present AND a wall-clock time is present (the trait that distinguishes this
 * family from the date-only formatters). A local-constructed timestamp keeps the
 * rendered time stable across the runner's timezone.
 */
import {describe, expect, it} from 'vitest';
import {formatDateTime} from '../formatDateTime';

// 5 June 2024, 14:30 local — local components so no timezone shifts the wall
// clock, and mid-year so no boundary disturbs the date parts.
const d = new Date(2024, 5, 5, 14, 30);

describe('formatDateTime', () => {
    it('includes the date parts (short month, day, year)', () => {
        const out = formatDateTime(d, 'en-US');
        expect(out).toContain('Jun');
        expect(out).toContain('2024');
        expect(out).toMatch(/\b5\b/);
    });

    it('includes a wall-clock time — the trait that separates it from date-only formatters', () => {
        const out = formatDateTime(d, 'en-US');
        expect(out).toMatch(/\d{1,2}:\d{2}/);
        expect(out).toContain('30'); // the minute
    });

    it('accepts an ISO string as well as a Date', () => {
        // No trailing Z → parsed as local, so the wall clock is timezone-stable.
        const out = formatDateTime('2024-06-05T14:30:00', 'en-US');
        expect(out).toContain('2024');
        expect(out).toMatch(/\d{1,2}:\d{2}/);
    });

    it('falls back to the environment locale when none is given', () => {
        expect(typeof formatDateTime(d)).toBe('string');
        expect(formatDateTime(d).length).toBeGreaterThan(0);
    });
});
