/**
 * translateOr.test.ts — the guarded i18n fallback shared by chart/table labels.
 *
 * The whole point of the helper is that a missing key never reaches the user, so
 * the cases that matter are the "missing" ones: svelte-i18n echoes the key back
 * on a miss, and a key mapped to "" is treated as a miss too.
 */
import {describe, expect, it} from 'vitest';
import {translateOr} from '../translateOr';

// A fake translator: known keys resolve, everything else echoes the key back
// exactly like svelte-i18n's `$_` does on a miss.
const dict: Record<string, string> = {
    'brokers.lots.value': 'Value',
    'brokers.lots.blank': '',
};
const translate = (key: string): string => (key in dict ? dict[key] : key);

describe('translateOr', () => {
    it('returns the translation when the key resolves', () => {
        expect(translateOr(translate, 'brokers.lots.value', 'Fallback')).toBe('Value');
    });

    it('returns the fallback when the key is missing (translator echoes the key)', () => {
        expect(translateOr(translate, 'brokers.lots.missing', 'Fallback')).toBe('Fallback');
    });

    it('returns the fallback when the key resolves to an empty string', () => {
        expect(translateOr(translate, 'brokers.lots.blank', 'Fallback')).toBe('Fallback');
    });

    it('never leaks a raw key to the caller', () => {
        const key = 'brokers.lots.someKey';
        expect(translateOr(translate, key, 'Human text')).not.toBe(key);
    });

    it('passes the key through to the injected translator', () => {
        const seen: string[] = [];
        const spy = (key: string): string => {
            seen.push(key);
            return 'X';
        };
        translateOr(spy, 'a.b.c', 'fb');
        expect(seen).toEqual(['a.b.c']);
    });
});
