/**
 * lotChartShared — pure unit tests (node env, no jsdom).
 *
 * These four helpers are shared verbatim by the three lot charts. Formatting is
 * asserted with an explicit locale so the expected strings are deterministic
 * regardless of the machine's locale; the default — no locale — is the interface
 * language (M-18), pinned in its own describe under a switched UI.
 *
 * `isUnknownOrNonZero` and `addOrNull` carry the B3b rule for lot amounts that can
 * be unknown (`null`: no FX rate to the target currency). An unknown amount is
 * shown as «—», never hidden as if it were 0, and a sum with an unknown part is
 * unknown.
 *
 * `withAlpha` moved to `$lib/theme/colorAlpha` (colour workstream R, R-4), and
 * its tests moved with it, unchanged: `src/lib/theme/colorAlpha.test.ts`.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

// The interface locale is the UI language regionalised by `navigator.language` (M-18). Node's tag
// follows the host's ICU locale, so it is pinned to en-US — jsdom's own — before any import.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {addOrNull, clamp, formatAxisNumber, isUnknownOrNonZero, normalizeZero, resolveBrokerName} from './lotChartShared';

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

/**
 * M-18 CP2: without a locale, the interface language.
 *
 * The WAC and Comparison lot charts call `formatAxisNumber(value)` with no locale, which until now meant
 * the machine's: an Italian reader on an English Windows got `1.5K` and `3.14` on the axis, beside amounts
 * written `1.234,56`. Every figure is written in the interface language (the developer's decision M-18,
 * 2026-10-12), so the default locale is `uiLocale()` — the UI language regionalised by the browser — and an
 * explicit locale still wins.
 *
 * The oracle is the helper's own explicit-locale path, pinned above: without a locale it must write what it
 * writes when handed the interface locale. A control checks that the language under test really writes
 * the ticks differently from English, so the comparison is about something.
 */
describe('formatAxisNumber — without a locale, the interface language (M-18)', () => {
    /** Ticks of both branches — compact from 1,000, plain below, a sub-10 fraction, zero and negative zero. */
    const TICKS = [1500, -2000, 1_234_567, 3.14159, 12.5, 7, 999, 0, -0];

    /** What `format` writes for each tick, keyed by the tick as written, so one diff names every tick that moved. */
    function ticks(format: (value: number) => string): Record<string, string> {
        return Object.fromEntries(TICKS.map((value) => [Object.is(value, -0) ? '-0' : String(value), format(value)]));
    }

    /** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
    async function uiLanguage(lang: 'en' | 'it' | 'fr'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
    }

    /** `value` as JSON with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
    function spelled(value: unknown): string {
        return JSON.stringify(value).replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it.each(['fr', 'it'] as const)('%s UI on an en-US browser: the ticks in that language, not the machine’s', async (lang) => {
        await uiLanguage(lang);
        const expected = ticks((value) => formatAxisNumber(value, lang));
        // Control: this runtime carries the language's data, so its ticks are not the English ones.
        expect(expected['3.14159'], `${lang} writes 3.14159 differently from en-US`).not.toBe(formatAxisNumber(3.14159, 'en-US'));
        expect(expected['1500'], `${lang} writes 1500 differently from en-US`).not.toBe(formatAxisNumber(1500, 'en-US'));

        expect(
            ticks((value) => formatAxisNumber(value)),
            spelled(expected),
        ).toEqual(expected);
    });

    it('English UI on an en-US browser (guard): without a locale, today’s en-US text', async () => {
        await uiLanguage('en');

        expect(ticks((value) => formatAxisNumber(value))).toEqual(ticks((value) => formatAxisNumber(value, 'en-US')));
        expect([formatAxisNumber(1500), formatAxisNumber(3.14159)]).toEqual(['1.5K', '3.14']);
    });

    it('an explicit locale still wins over the interface language', async () => {
        await uiLanguage('fr');

        expect(formatAxisNumber(3.14, 'de-DE')).toBe('3,14');
        expect(formatAxisNumber(1500, 'en-US')).toBe('1.5K');
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
