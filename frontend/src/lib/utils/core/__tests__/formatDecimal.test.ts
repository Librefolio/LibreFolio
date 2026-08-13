/**
 * formatDecimal.test.ts — display formatting of backend decimal strings.
 *
 * The idempotence block exists because of a real defect: the WAC field showed
 * `191.50591660` (truncation to 8 decimals had exposed a trailing zero), and
 * re-formatting that string produced `191.5059166`. `WacPreviewSection` compares
 * the two to decide whether the user edited the amount, so simply focusing the
 * field and clicking away silently switched the form to Manual mode.
 */
import {describe, expect, it} from 'vitest';
import {formatDecimalForDisplay} from '../formatDecimal';

describe('formatDecimalForDisplay', () => {
    it('returns empty for null, undefined and empty string', () => {
        expect(formatDecimalForDisplay(null)).toBe('');
        expect(formatDecimalForDisplay(undefined)).toBe('');
        expect(formatDecimalForDisplay('')).toBe('');
    });

    it('leaves non-numeric input untouched', () => {
        expect(formatDecimalForDisplay('abc')).toBe('abc');
        expect(formatDecimalForDisplay('1,5')).toBe('1,5');
    });

    it('drops insignificant trailing zeros', () => {
        expect(formatDecimalForDisplay('6.000000')).toBe('6');
        expect(formatDecimalForDisplay('6.500000')).toBe('6.5');
        expect(formatDecimalForDisplay('-0.250')).toBe('-0.25');
    });

    it('keeps significant fractional digits up to maxFrac', () => {
        expect(formatDecimalForDisplay('0.00000123')).toBe('0.00000123');
        expect(formatDecimalForDisplay('1.234567891234')).toBe('1.23456789');
    });

    it('pads to minFrac when asked', () => {
        expect(formatDecimalForDisplay('6', {minFrac: 2})).toBe('6.00');
        expect(formatDecimalForDisplay('6.5', {minFrac: 2})).toBe('6.50');
    });

    it('never leaves a trailing zero exposed by truncation', () => {
        // The 9th decimal onwards is cut; the 8th is a zero and must go too.
        expect(formatDecimalForDisplay('191.5059166043')).toBe('191.5059166');
        expect(formatDecimalForDisplay('1.2345678000009')).toBe('1.2345678');
    });

    it('is idempotent — a round trip through an input is not an edit', () => {
        const samples = ['191.5059166043', '170.3261122757978', '1.2345678000009', '6.000000', '0.00000123', '-0.250', '42.00', '1.234567891234'];
        for (const raw of samples) {
            const once = formatDecimalForDisplay(raw);
            expect(formatDecimalForDisplay(once), `not idempotent for ${raw}`).toBe(once);
        }
    });

    it('is idempotent with minFrac too', () => {
        for (const raw of ['6', '6.5', '191.5059166043']) {
            const once = formatDecimalForDisplay(raw, {minFrac: 2});
            expect(formatDecimalForDisplay(once, {minFrac: 2}), `not idempotent for ${raw}`).toBe(once);
        }
    });
});
