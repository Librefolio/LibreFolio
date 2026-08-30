/**
 * currencyBlocker — pure unit tests.
 *
 * Covers the marker guard and every default in the token parse: a full token, a
 * partial one (missing keys fall back), malformed chunks (no `=`, empty), and the
 * non-string / wrong-prefix inputs the guard must reject.
 */
import {describe, expect, it} from 'vitest';
import {CURRENCY_CHANGE_BLOCKED_PREFIX, isCurrencyChangeBlockedMessage, parseCurrencyChangeBlocker} from './currencyBlocker';

describe('isCurrencyChangeBlockedMessage', () => {
    it('accepts a string starting with the marker', () => {
        expect(isCurrencyChangeBlockedMessage(`${CURRENCY_CHANGE_BLOCKED_PREFIX}prices=1`)).toBe(true);
    });

    it('rejects a different message, an empty string and non-strings', () => {
        expect(isCurrencyChangeBlockedMessage('SOME_OTHER_ERROR')).toBe(false);
        expect(isCurrencyChangeBlockedMessage('')).toBe(false);
        expect(isCurrencyChangeBlockedMessage(null)).toBe(false);
        expect(isCurrencyChangeBlockedMessage(undefined)).toBe(false);
        expect(isCurrencyChangeBlockedMessage(42)).toBe(false);
    });
});

describe('parseCurrencyChangeBlocker', () => {
    it('parses a complete token into structured counts and ranges', () => {
        const msg = `${CURRENCY_CHANGE_BLOCKED_PREFIX}prices=12|events_manual=3|events_provider=4|` + 'linked_tx=5|oldest=2020-01-01|newest=2024-12-31|from=USD|to=EUR';
        expect(parseCurrencyChangeBlocker(msg)).toEqual({
            prices: 12,
            eventsManual: 3,
            eventsProvider: 4,
            linkedTx: 5,
            oldest: '2020-01-01',
            newest: '2024-12-31',
            from: 'USD',
            to: 'EUR',
        });
    });

    it('defaults missing numeric keys to 0 and missing string keys to empty', () => {
        expect(parseCurrencyChangeBlocker(`${CURRENCY_CHANGE_BLOCKED_PREFIX}prices=7`)).toEqual({
            prices: 7,
            eventsManual: 0,
            eventsProvider: 0,
            linkedTx: 0,
            oldest: '',
            newest: '',
            from: '',
            to: '',
        });
    });

    it('ignores malformed chunks (no "=" and empty segments)', () => {
        // `garbage` has no '='; the trailing '|' makes an empty chunk — both skipped.
        const msg = `${CURRENCY_CHANGE_BLOCKED_PREFIX}garbage|prices=2|`;
        const out = parseCurrencyChangeBlocker(msg);
        expect(out.prices).toBe(2);
        expect(out.linkedTx).toBe(0);
    });

    it('yields all-zero/empty when the token carries only the prefix', () => {
        expect(parseCurrencyChangeBlocker(CURRENCY_CHANGE_BLOCKED_PREFIX)).toEqual({
            prices: 0,
            eventsManual: 0,
            eventsProvider: 0,
            linkedTx: 0,
            oldest: '',
            newest: '',
            from: '',
            to: '',
        });
    });

    it('keeps a value that itself contains characters after the first "="', () => {
        // split('=') on `oldest=2020=weird` → ['oldest','2020','weird']; [k,v] takes v='2020'.
        const out = parseCurrencyChangeBlocker(`${CURRENCY_CHANGE_BLOCKED_PREFIX}oldest=2020=weird`);
        expect(out.oldest).toBe('2020');
    });
});
