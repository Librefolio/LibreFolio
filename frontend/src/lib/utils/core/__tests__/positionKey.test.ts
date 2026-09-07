/**
 * positionKey.test.ts — the composite holding key shared by dashboard tables.
 *
 * The contract is stability: the two dashboard tables build a map with this key
 * on one side and look it up on the other, so the exact string — including how a
 * null broker collapses — is what must not drift.
 */
import {describe, expect, it} from 'vitest';
import {makePositionKey} from '../positionKey';

describe('makePositionKey', () => {
    it('joins asset and broker id', () => {
        expect(makePositionKey(12, 3)).toBe('12-3');
    });

    it('collapses a null broker to 0', () => {
        expect(makePositionKey(12, null)).toBe('12-0');
    });

    it('keeps an explicit broker id of 0 (indistinguishable from null by design)', () => {
        expect(makePositionKey(12, 0)).toBe('12-0');
    });

    it('is a pure string builder, stable across calls', () => {
        expect(makePositionKey(7, 9)).toBe(makePositionKey(7, 9));
    });
});
