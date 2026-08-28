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
import {formatAxisDate} from '../formatAxisDate';

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
