/**
 * text.test.ts — shared string helpers (utils/text.ts).
 *
 * Focused on humanizeKey, the last-resort label for machine keys: separators
 * become spaces and every word gets a capital, so a raw key never reaches the
 * user verbatim.
 */
import {describe, expect, it} from 'vitest';
import {humanizeKey} from '../text';

describe('humanizeKey', () => {
    it('turns snake_case into Title Case', () => {
        expect(humanizeKey('foo_bar')).toBe('Foo Bar');
    });

    it('turns kebab-case into Title Case', () => {
        expect(humanizeKey('foo-bar-baz')).toBe('Foo Bar Baz');
    });

    it('handles mixed separators', () => {
        expect(humanizeKey('rsi_over-bought')).toBe('Rsi Over Bought');
    });

    it('capitalises a single lowercase word', () => {
        expect(humanizeKey('signal')).toBe('Signal');
    });

    it('leaves an already-capitalised word unchanged', () => {
        expect(humanizeKey('Signal')).toBe('Signal');
    });

    it('returns empty for an empty string', () => {
        expect(humanizeKey('')).toBe('');
    });
});
