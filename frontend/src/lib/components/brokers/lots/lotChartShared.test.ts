/**
 * lotChartShared — pure unit tests (node env, no jsdom).
 *
 * These four helpers are shared verbatim by the three lot charts. Formatting is
 * asserted with an explicit locale so the expected strings are deterministic
 * regardless of the machine's locale.
 *
 * `isUnknownOrNonZero` and `addOrNull` carry the B3b rule for lot amounts that can
 * be unknown (`null`: no FX rate to the target currency). An unknown amount is
 * shown as «—», never hidden as if it were 0, and a sum with an unknown part is
 * unknown.
 */
import {describe, expect, it} from 'vitest';

import {addOrNull, clamp, formatAxisNumber, isUnknownOrNonZero, normalizeZero, resolveBrokerName, withAlpha} from './lotChartShared';

describe('normalizeZero', () => {
    it('collapses negative zero to a plain zero', () => {
        expect(Object.is(normalizeZero(-0), 0)).toBe(true);
        expect(Object.is(normalizeZero(-0), -0)).toBe(false);
    });

    it('passes every other value through untouched', () => {
        expect(normalizeZero(0)).toBe(0);
        expect(normalizeZero(3.14)).toBe(3.14);
        expect(normalizeZero(-5)).toBe(-5);
        expect(Number.isNaN(normalizeZero(Number.NaN))).toBe(true);
    });
});

describe('clamp', () => {
    it('returns the value when already inside the range', () => {
        expect(clamp(5, 0, 10)).toBe(5);
    });

    it('clamps to the bounds on either side', () => {
        expect(clamp(-3, 0, 10)).toBe(0);
        expect(clamp(42, 0, 10)).toBe(10);
    });

    it('honours the bounds at the exact edges', () => {
        expect(clamp(0, 0, 10)).toBe(0);
        expect(clamp(10, 0, 10)).toBe(10);
    });
});

describe('withAlpha', () => {
    it('rewrites an hsl() color into hsla() with the alpha inserted literally', () => {
        expect(withAlpha('hsl(210 68% 44%)', 0.5)).toBe('hsla(210 68% 44%, 0.5)');
    });

    it('appends a clamped alpha byte to a #rrggbb color', () => {
        expect(withAlpha('#00ff00', 1)).toBe('#00ff00ff');
        expect(withAlpha('#00ff00', 0)).toBe('#00ff0000');
        // 0.5 * 255 = 127.5 → rounds to 128 → 0x80
        expect(withAlpha('#112233', 0.5)).toBe('#11223380');
    });

    it('clamps an out-of-range alpha before scaling the hex byte', () => {
        expect(withAlpha('#112233', 2)).toBe('#112233ff');
        expect(withAlpha('#112233', -1)).toBe('#11223300');
    });

    it('pads a small alpha byte to two hex digits', () => {
        // 0.02 * 255 = 5.1 → 5 → "05", not "5"
        expect(withAlpha('#112233', 0.02)).toBe('#11223305');
    });

    it('returns unrecognised color shapes unchanged', () => {
        expect(withAlpha('red', 0.5)).toBe('red');
        expect(withAlpha('#abc', 0.5)).toBe('#abc');
        expect(withAlpha('rgba(1,2,3,0.4)', 0.5)).toBe('rgba(1,2,3,0.4)');
    });
});

describe('formatAxisNumber', () => {
    it('uses compact notation at or above 1000', () => {
        expect(formatAxisNumber(1500, 'en-US')).toBe('1.5K');
        expect(formatAxisNumber(-2000, 'en-US')).toBe('-2K');
        expect(formatAxisNumber(1000, 'en-US')).toBe('1K');
    });

    it('adds a second decimal only for sub-10 fractional magnitudes', () => {
        expect(formatAxisNumber(3.14159, 'en-US')).toBe('3.14');
        // >= 10 → the sub-10 branch is off, so at most the default 2 max digits
        expect(formatAxisNumber(12.5, 'en-US')).toBe('12.5');
    });

    it('prints whole numbers below 1000 with no forced decimals', () => {
        expect(formatAxisNumber(7, 'en-US')).toBe('7');
        expect(formatAxisNumber(999, 'en-US')).toBe('999');
    });

    it('renders a zero tick as "0", never "-0"', () => {
        expect(formatAxisNumber(-0, 'en-US')).toBe('0');
        expect(formatAxisNumber(0, 'en-US')).toBe('0');
    });

    it('honours the locale argument', () => {
        // de-DE uses a comma decimal separator, proving the locale is routed through.
        expect(formatAxisNumber(3.14, 'de-DE')).toBe('3,14');
    });
});

describe('resolveBrokerName', () => {
    const brokers = [
        {id: 1, name: 'Fineco'},
        {id: 2, name: 'Degiro'},
        {id: 3}, // present by id, no name
    ];

    it('returns the matching broker name', () => {
        expect(resolveBrokerName(1, brokers)).toBe('Fineco');
        expect(resolveBrokerName(2, brokers)).toBe('Degiro');
    });

    it('uses the "missing" fallback for a null id', () => {
        expect(resolveBrokerName(null, brokers)).toBe('—');
        expect(resolveBrokerName(null, brokers, {missing: 'Combined'})).toBe('Combined');
    });

    it('uses the default #id fallback for an unknown or nameless broker', () => {
        expect(resolveBrokerName(99, brokers)).toBe('#99'); // not in list
        expect(resolveBrokerName(3, brokers)).toBe('#3'); // in list but no name
    });

    it('routes a custom unknown-fallback (the WAC chart shape)', () => {
        expect(resolveBrokerName(99, brokers, {unknown: (id) => `Broker ${id}`})).toBe('Broker 99');
    });
});

describe('isUnknownOrNonZero', () => {
    // Decides whether an amount row is shown. A row hidden because its amount is zero
    // must not also swallow an amount that is unknown: that would read as a zero.

    it('shows an unknown amount (null or undefined), which renders as «—»', () => {
        expect(isUnknownOrNonZero(null)).toBe(true);
        expect(isUnknownOrNonZero(undefined)).toBe(true);
    });

    it('shows any non-zero amount, positive or negative', () => {
        expect(isUnknownOrNonZero(12.5)).toBe(true);
        expect(isUnknownOrNonZero(-3)).toBe(true);
        expect(isUnknownOrNonZero(0.01)).toBe(true);
    });

    it('hides a known zero, negative zero included', () => {
        expect(isUnknownOrNonZero(0)).toBe(false);
        expect(isUnknownOrNonZero(-0)).toBe(false);
    });
});

describe('addOrNull', () => {
    it('adds two known amounts', () => {
        expect(addOrNull(2.5, 4)).toBe(6.5);
        expect(addOrNull(-10, 4)).toBe(-6);
    });

    it('treats zero as a known amount, not as a missing one', () => {
        expect(addOrNull(0, 5)).toBe(5);
        expect(addOrNull(5, 0)).toBe(5);
        expect(addOrNull(0, 0)).toBe(0);
        expect(addOrNull(5, -0)).toBe(5);
    });

    it('is unknown when either side is unknown', () => {
        // Control: the same amounts, both known, do add up.
        expect(addOrNull(5, 5)).toBe(10);

        expect(addOrNull(null, 5)).toBeNull();
        expect(addOrNull(5, null)).toBeNull();
        expect(addOrNull(null, null)).toBeNull();
    });

    it('does not let a known zero stand in for the unknown side', () => {
        expect(addOrNull(0, null)).toBeNull();
        expect(addOrNull(null, 0)).toBeNull();
    });
});
