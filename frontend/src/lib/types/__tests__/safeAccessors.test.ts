import {describe, expect, it} from 'vitest';
import {safeDecimal, safeNumber, safeScalar, safeString} from '../common';

/**
 * These four exist because `openapi-zod-client` widens some nullable fields to
 * `T | (T | null)[]`, and every chart in the app has to unwrap that before it
 * can read a value. They used to be copy-pasted into nine components under five
 * different names; the cases below pin the behaviour the copies shared, so a
 * future edit to the shared version cannot quietly change what the callers get.
 */
describe('safeScalar', () => {
    it('unwraps a single-element array', () => {
        expect(safeScalar(['a'])).toBe('a');
        expect(safeScalar([7])).toBe(7);
    });

    it('takes the first element, not the first non-null one', () => {
        // Worth pinning: `UnifiedLotsTable` has a local variant that skips nulls,
        // and the two disagree on exactly this input.
        expect(safeScalar([null, 'b'])).toBeNull();
    });

    it('passes a plain scalar through', () => {
        expect(safeScalar('a')).toBe('a');
        expect(safeScalar(0)).toBe(0);
    });

    it('maps every empty shape to null', () => {
        expect(safeScalar(null)).toBeNull();
        expect(safeScalar(undefined)).toBeNull();
        expect(safeScalar([])).toBeNull();
        expect(safeScalar([null])).toBeNull();
    });
});

describe('safeString', () => {
    it('accepts a string, bare or wrapped', () => {
        expect(safeString('EUR')).toBe('EUR');
        expect(safeString(['EUR'])).toBe('EUR');
    });

    it('preserves the empty string instead of collapsing it to null', () => {
        expect(safeString('')).toBe('');
        expect(safeString([''])).toBe('');
    });

    it('rejects anything that is not a string', () => {
        expect(safeString(12)).toBeNull();
        expect(safeString([12])).toBeNull();
        expect(safeString({})).toBeNull();
    });

    it('maps every empty shape to null', () => {
        expect(safeString(null)).toBeNull();
        expect(safeString(undefined)).toBeNull();
        expect(safeString([])).toBeNull();
        expect(safeString([null])).toBeNull();
    });
});

describe('safeNumber', () => {
    it('accepts a number, bare or wrapped', () => {
        expect(safeNumber(42)).toBe(42);
        expect(safeNumber([42])).toBe(42);
    });

    it('preserves zero instead of treating it as absent', () => {
        expect(safeNumber(0)).toBe(0);
        expect(safeNumber([0])).toBe(0);
    });

    it('does not parse strings — that is what safeDecimal is for', () => {
        // The whole reason `safeDecimal` exists. Nine components used to carry a
        // local `safeNum` that parsed; swapping it for this one would have turned
        // every monetary amount into null, because amounts arrive as strings.
        expect(safeNumber('12.34')).toBeNull();
        expect(safeNumber(['12.34'])).toBeNull();
    });

    it('maps every empty shape to null', () => {
        expect(safeNumber(null)).toBeNull();
        expect(safeNumber(undefined)).toBeNull();
        expect(safeNumber([])).toBeNull();
        expect(safeNumber([null])).toBeNull();
    });
});

describe('safeDecimal', () => {
    it('parses the decimal strings the API sends for money and quantities', () => {
        expect(safeDecimal('12.34')).toBe(12.34);
        expect(safeDecimal(['12.34'])).toBe(12.34);
        expect(safeDecimal('-0.5')).toBe(-0.5);
    });

    it('preserves a parsed zero', () => {
        // `0` is falsy, so a `||` in the caller would drop it; the function must
        // not do the same. A position worth exactly zero is not a missing one.
        expect(safeDecimal('0')).toBe(0);
        expect(safeDecimal(0)).toBe(0);
    });

    it('accepts a number that is already a number', () => {
        expect(safeDecimal(12.5)).toBe(12.5);
    });

    it('returns null for text that is not a number', () => {
        expect(safeDecimal('abc')).toBeNull();
        expect(safeDecimal('')).toBeNull();
    });

    it('keeps the numeric prefix of a partly numeric string', () => {
        // `parseFloat` semantics, inherited from the copies this replaced rather
        // than chosen. Pinned so that swapping in `Number()` — which returns NaN
        // here — is a visible change and not a silent one.
        expect(safeDecimal('12abc')).toBe(12);
    });

    it('maps every empty shape to null', () => {
        expect(safeDecimal(null)).toBeNull();
        expect(safeDecimal(undefined)).toBeNull();
        expect(safeDecimal([])).toBeNull();
        expect(safeDecimal([null])).toBeNull();
    });
});
