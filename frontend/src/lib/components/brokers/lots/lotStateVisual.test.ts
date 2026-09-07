/**
 * Unit tests for lotStateVisual — the shared open/partial/closed encoding used by
 * both the WAC bubbles and the Gantt filter buttons. Pure functions, every branch
 * and every switch arm exercised.
 *
 * @vitest-environment node
 */

import {describe, it, expect} from 'vitest';
import {lotDisplayState, lotStateColor, lotStateSymbol, lotIsOpenBucket, type LotDisplayState} from './lotStateVisual';

describe('lotDisplayState', () => {
    it('is CLOSED when nothing is open', () => {
        expect(lotDisplayState(0, 10)).toBe('CLOSED');
        expect(lotDisplayState(-5, 10)).toBe('CLOSED');
    });

    it('is PARTIAL when some but not all is open', () => {
        expect(lotDisplayState(5, 10)).toBe('PARTIAL');
    });

    it('is OPEN when the full original quantity is still open', () => {
        expect(lotDisplayState(10, 10)).toBe('OPEN');
    });

    it('is OPEN when the original quantity is unknown (non-positive)', () => {
        // originalQuantity > 0 is false → cannot be partial → OPEN.
        expect(lotDisplayState(5, 0)).toBe('OPEN');
    });

    it('is OPEN when the open quantity exceeds the original', () => {
        // openQuantity < originalQuantity is false → OPEN.
        expect(lotDisplayState(5, 3)).toBe('OPEN');
    });
});

describe('lotStateColor', () => {
    const cases: Array<[LotDisplayState, boolean, string]> = [
        ['OPEN', true, '#38bdf8'],
        ['OPEN', false, '#0284c7'],
        ['PARTIAL', true, '#fbbf24'],
        ['PARTIAL', false, '#d97706'],
        ['CLOSED', true, '#94a3b8'],
        ['CLOSED', false, '#64748b'],
    ];
    it.each(cases)('colours %s (dark=%s)', (state, dark, hex) => {
        expect(lotStateColor(state, dark)).toBe(hex);
    });
});

describe('lotStateSymbol', () => {
    it('encodes each state as a distinct shape', () => {
        expect(lotStateSymbol('OPEN')).toBe('circle');
        expect(lotStateSymbol('PARTIAL')).toBe('diamond');
        expect(lotStateSymbol('CLOSED')).toBe('rect');
    });
});

describe('lotIsOpenBucket', () => {
    it('groups everything that is not fully closed into the open bucket', () => {
        expect(lotIsOpenBucket('OPEN')).toBe(true);
        expect(lotIsOpenBucket('PARTIAL')).toBe(true);
        expect(lotIsOpenBucket('CLOSED')).toBe(false);
    });
});
