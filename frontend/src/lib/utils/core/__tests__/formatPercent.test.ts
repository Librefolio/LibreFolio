import {afterEach, describe, expect, it, vi} from 'vitest';

// The default locale is the UI language regionalised by `navigator.language` (M-18, last block). Node's tag
// follows the host's ICU locale (`LANG=it_CH.UTF-8` gives `it-CH`), so it is pinned to en-US — jsdom's own —
// before any import.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {formatPercent, type FormatPercentOptions} from '../formatPercent';

/**
 * These pin the five behaviours that used to live in five private copies, because
 * the copies disagreed and the disagreement was invisible: each one was correct
 * where it stood, and wrong anywhere else.
 *
 * The one that matters is `scale`. `formatPercent(2.5)` and
 * `formatPercent(0.025, {scale: 100})` must both print "2.50%" — get that
 * backwards and every figure on the affected screen is off by a hundred, with
 * nothing failing to say so.
 */
describe('formatPercent', () => {
    describe('scale', () => {
        it('treats the value as already a percentage by default', () => {
            expect(formatPercent(2.5)).toBe('+2.50%');
            expect(formatPercent(-2.5)).toBe('-2.50%');
        });

        it('multiplies a fraction when told the value is one', () => {
            expect(formatPercent(0.025, {scale: 100})).toBe('+2.50%');
            expect(formatPercent(-0.025, {scale: 100})).toBe('-2.50%');
        });

        it('agrees with itself across the two scales', () => {
            // The property the five copies violated: the same quantity, expressed
            // either way, must print identically.
            expect(formatPercent(7.25)).toBe(formatPercent(0.0725, {scale: 100}));
        });
    });

    describe('sign', () => {
        it('marks positives with a plus by default', () => {
            expect(formatPercent(1)).toBe('+1.00%');
        });

        it('omits the plus when the caller does not want a comparison', () => {
            expect(formatPercent(1, {signed: false})).toBe('1.00%');
            // A negative keeps its sign either way — that one is arithmetic, not decoration.
            expect(formatPercent(-1, {signed: false})).toBe('-1.00%');
        });

        it('never marks zero as positive', () => {
            expect(formatPercent(0)).toBe('0.00%');
        });
    });

    describe('negative zero', () => {
        it('prints a plain zero', () => {
            // `-0` survives multiplication and toFixed renders it "-0.00%", which
            // reads as a small loss. Two of the five copies guarded against this
            // and three did not, so the same value rendered differently depending
            // on which chart you were looking at.
            expect(formatPercent(-0)).toBe('0.00%');
            expect(formatPercent(-0.0000001, {scale: 100})).toBe('-0.00%');
        });

        it('handles a negative zero arriving through the scale', () => {
            expect(formatPercent(-0, {scale: 100})).toBe('0.00%');
        });
    });

    describe('missing values', () => {
        it('prints an em dash for null and undefined', () => {
            expect(formatPercent(null)).toBe('—');
            expect(formatPercent(undefined)).toBe('—');
        });

        it('prints an em dash for values that are not finite', () => {
            // A ratio whose denominator was zero reaches here as Infinity, and
            // "∞%" is not a fact about the portfolio.
            expect(formatPercent(Infinity)).toBe('—');
            expect(formatPercent(-Infinity)).toBe('—');
            expect(formatPercent(NaN)).toBe('—');
        });

        it('lets the caller choose the placeholder', () => {
            expect(formatPercent(null, {empty: 'n/a'})).toBe('n/a');
            expect(formatPercent(null, {empty: ''})).toBe('');
        });
    });

    describe('digits', () => {
        it('uses two decimals by default', () => {
            expect(formatPercent(1.5)).toBe('+1.50%');
            expect(formatPercent(1.239)).toBe('+1.24%');
        });

        it('honours a different precision', () => {
            expect(formatPercent(1.2345, {digits: 0})).toBe('+1%');
            expect(formatPercent(1.6, {digits: 0})).toBe('+2%');
            expect(formatPercent(1.2349, {digits: 3})).toBe('+1.235%');
        });

        it('rounds the way toFixed does, which is not the way school does', () => {
            // `(1.005).toFixed(2)` is "1.00", not "1.01": 1.005 has no exact binary
            // representation and the stored value sits just below the midpoint, so
            // it rounds down. Pinned because it looks like a bug in the formatter
            // when it is a property of the language, and because anyone tempted to
            // "fix" it by adding an epsilon should see this test first.
            expect(formatPercent(1.005)).toBe('+1.00%');
            expect(formatPercent(1.2345, {digits: 3})).toBe('+1.234%');
        });
    });

    describe('suffix', () => {
        it('writes a percent sign unless told otherwise', () => {
            // The default is the whole safety of this option: every caller that
            // existed before it keeps printing exactly what it printed.
            expect(formatPercent(1.5)).toBe('+1.50%');
            expect(formatPercent(0.015, {scale: 100})).toBe('+1.50%');
        });

        it('writes percentage points when the value is a difference of percentages', () => {
            // A holding weighing 20% and producing 80% of the risk differs by 60
            // POINTS, not by 60 percent. The two units read alike and are not.
            //
            // The numbers are round and invented deliberately: a measured pair
            // would integrate over the window that produced it, and a fixture
            // copied from a measurement gets read later as a reference value.
            expect(formatPercent(0.6, {scale: 100, digits: 1, suffix: 'pp'})).toBe('+60.0pp');
            expect(formatPercent(-0.3, {scale: 100, digits: 1, suffix: 'pp'})).toBe('-30.0pp');
        });

        it('drops the unit entirely when asked', () => {
            expect(formatPercent(7.25, {signed: false, suffix: ''})).toBe('7.25');
        });

        it('leaves the placeholder alone', () => {
            // The unit belongs to a number. Appending it to "—" would produce
            // "—pp", which claims a missing measurement has a unit.
            expect(formatPercent(null, {suffix: 'pp'})).toBe('—');
            expect(formatPercent(NaN, {suffix: 'pp', empty: 'n/a'})).toBe('n/a');
        });

        it('keeps the sign and the negative-zero guard', () => {
            // The guard lives before the suffix, so switching units cannot
            // resurrect the "-0.00" that this function exists to prevent.
            expect(formatPercent(-0, {suffix: 'pp'})).toBe('0.00pp');
            expect(formatPercent(0, {suffix: 'pp'})).toBe('0.00pp');
        });
    });

    /**
     * `locale` is the option DistributionEditor needs: its total badge prints
     * `toFixed(2)` and a `%`, so a French screen reads "100.00%" where French writes
     * the number with a decimal comma and a no-break space before the sign.
     *
     * What these cases pin:
     * - `locale` with the default `%` suffix: `Intl.NumberFormat(locale, {style:
     *   'percent'})` with `digits` fraction digits, applied to `value * scale / 100`;
     * - `locale` with another suffix: `toLocaleString(locale)` with the same digits,
     *   then the suffix as written;
     * - `signed`, `empty` and the `-0` guard keep their meaning;
     * - no `locale`: the interface locale, `uiLocale()` (M-18). With the English UI and
     *   the en-US browser pinned at the top of the file, that is today's text below a
     *   thousand; the last block of the file pins the other languages.
     *
     * Every expected string comes from `Intl` at run time, never typed here. The
     * separators are ICU data — which no-break space precedes a French `%` has
     * changed between releases — so a typed copy would pin one ICU, not the rule.
     */
    describe('locale', () => {
        /** `locale` typed in, so this block type-checks before FormatPercentOptions declares it. */
        const localised = (value: number | null | undefined, options: FormatPercentOptions & {locale?: string}) => formatPercent(value, options);
        const intlPercent = (locale: string, fraction: number) => new Intl.NumberFormat(locale, {style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2}).format(fraction);
        const intlNumber = (locale: string, value: number) => value.toLocaleString(locale, {minimumFractionDigits: 2, maximumFractionDigits: 2});

        it.each(['fr', 'it', 'es'])('writes a share the way %s does, decimal comma included', (locale) => {
            const written = localised(12.5, {signed: false, locale});
            expect(written).toBe(intlPercent(locale, 0.125));
            // Also proves this runtime carries the locale's ICU data: without it Intl
            // falls back to English and both sides would agree on "12.50%".
            expect(written).toContain(',');
        });

        it('puts the plus of a signed positive in front of the localised text', () => {
            const written = localised(12.5, {signed: true, locale: 'fr'});
            expect(written.startsWith('+')).toBe(true);
            expect(written).toBe(`+${intlPercent('fr', 0.125)}`);
        });

        it('agrees with itself across the two scales', () => {
            const fromFraction = localised(0.125, {scale: 100, signed: false, locale: 'fr'});
            expect(fromFraction).toBe(intlPercent('fr', 0.125));
            expect(fromFraction).toBe(localised(12.5, {signed: false, locale: 'fr'}));
        });

        it('localises the number and leaves a percentage-point suffix as written', () => {
            const written = localised(12.5, {signed: false, suffix: 'pp', locale: 'fr'});
            expect(written).toBe(`${intlNumber('fr', 12.5)}pp`);
            expect(written).toContain(',');
        });

        // ---- controls: green before `locale` exists, and must stay green after ----

        it('writes English the way Intl does, which is also what it printed before', () => {
            expect(localised(12.5, {signed: false, locale: 'en'})).toBe(intlPercent('en', 0.125));
        });

        it('without a locale, writes the interface locale: today’s text for an English UI on an en-US browser', () => {
            expect(formatPercent(2.5)).toBe('+2.50%');
            expect(formatPercent(0.6, {scale: 100, digits: 1, suffix: 'pp'})).toBe('+60.0pp');
        });

        it('prints the placeholder for a missing value, whatever the locale', () => {
            expect(localised(null, {locale: 'fr'})).toBe('—');
            expect(localised(undefined, {locale: 'fr', empty: 'n/a'})).toBe('n/a');
            expect(localised(NaN, {locale: 'fr', suffix: 'pp'})).toBe('—');
        });

        it('never prints a negative zero in French either', () => {
            // Intl prints a minus on -0 ("-0,00 %"), so the guard has to run before
            // the number reaches it, on every route through the formatter.
            for (const written of [localised(-0, {locale: 'fr'}), localised(-0, {scale: 100, locale: 'fr'}), localised(-0, {suffix: 'pp', locale: 'fr'})]) {
                expect(written).toMatch(/^0\D00/);
                expect(written).not.toMatch(/[-\u2212]/);
            }
        });
    });
});

/**
 * M-18 CP1 — without `locale`, the UI language.
 *
 * Numbers follow the UI language (the developer's rule of 2026-10-12), so `locale` now defaults to
 * `uiLocale()`: the UI language, regionalised by the browser when the two agree. The fixed `12.50%`
 * shape is gone. A French UI reads `+12,50 %` out of `formatPercent(12.5)` with nothing passed by the
 * caller, which is what lets the calls without `locale` follow the language untouched. What stays: `%`
 * through `Intl.NumberFormat(locale, {style: 'percent'})`, any other unit after the localized number,
 * an explicit `locale` winning over the default, the placeholder and the `-0` guard.
 *
 * English. The UI starts in English and the browser here is en-US (pinned at the top of the file), so
 * English output is today's text but for one thing: thousands are grouped.
 *
 * Expectations come from Intl in this runtime and are never typed, as in the `locale` block above;
 * English is typed where it is today's exact text.
 *
 * Language. `currentLanguage.set`, as LanguageSelector does; module-level state, put back to English
 * after every test.
 */
describe('formatPercent — without a locale, the UI language (M-18)', () => {
    type UiLanguage = 'en' | 'it' | 'fr' | 'es';

    const intlPercent = (locale: string, fraction: number, digits = 2) => new Intl.NumberFormat(locale, {style: 'percent', minimumFractionDigits: digits, maximumFractionDigits: digits}).format(fraction);
    const intlNumber = (locale: string, value: number, digits = 2) => new Intl.NumberFormat(locale, {minimumFractionDigits: digits, maximumFractionDigits: digits}).format(value);

    /** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
    async function uiLanguage(lang: UiLanguage): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
    }

    afterEach(async () => {
        await uiLanguage('en');
    });

    it.each(['fr', 'it', 'es'] as const)('%s UI: a share in that language’s notation, with its sign, from a call that passes no locale', async (lang) => {
        await uiLanguage(lang);
        // Control: the notation really differs from English in this runtime.
        expect(intlPercent(lang, 0.125)).not.toBe(intlPercent('en', 0.125));

        expect(formatPercent(12.5)).toBe(`+${intlPercent(lang, 0.125)}`);
        expect(formatPercent(0.125, {scale: 100, signed: false})).toBe(intlPercent(lang, 0.125));
        expect(formatPercent(-3.21, {digits: 1})).toBe(intlPercent(lang, -0.0321, 1));
    });

    it('Italian UI, another unit: the number in Italian notation, the unit as written', async () => {
        await uiLanguage('it');

        expect(formatPercent(0.6, {scale: 100, digits: 1, suffix: 'pp'})).toBe(`+${intlNumber('it', 60, 1)}pp`);
        expect(formatPercent(7.25, {signed: false, suffix: ''})).toBe(intlNumber('it', 7.25));
    });

    it('English UI on an en-US browser: today’s text, except that thousands are grouped', async () => {
        await uiLanguage('en');

        expect(formatPercent(2.5), 'control: below a thousand, today’s text').toBe('+2.50%');
        expect(formatPercent(1234.5, {signed: false})).toBe(intlPercent('en-US', 12.345));
        expect(formatPercent(1234.5, {signed: false})).toBe('1,234.50%');
        expect(formatPercent(1234.5, {signed: false, suffix: 'pp'})).toBe('1,234.50pp');
    });

    it('follows the UI language from one call to the next: fr → it → en', async () => {
        const written: Record<string, string> = {};
        for (const lang of ['fr', 'it', 'en'] as const) {
            await uiLanguage(lang);
            written[lang] = formatPercent(12.5, {signed: false});
        }

        expect(written).toEqual({fr: intlPercent('fr', 0.125), it: intlPercent('it', 0.125), en: '12.50%'});
    });

    it('an explicit locale still wins over the UI language (control: green before the default exists)', async () => {
        await uiLanguage('fr');

        expect(formatPercent(12.5, {signed: false, locale: 'it'})).toBe(intlPercent('it', 0.125));
        expect(formatPercent(12.5, {signed: false, locale: 'en'})).toBe('12.50%');
    });

    it('French UI: -0 is a plain zero on every route, and a missing value keeps its placeholder', async () => {
        await uiLanguage('fr');

        expect(formatPercent(-0)).toBe(intlPercent('fr', 0));
        expect(formatPercent(-0, {scale: 100})).toBe(intlPercent('fr', 0));
        expect(formatPercent(-0, {suffix: 'pp'})).toBe(`${intlNumber('fr', 0)}pp`);
        expect(formatPercent(null)).toBe('—');
        expect(formatPercent(NaN, {suffix: 'pp', empty: 'n/a'})).toBe('n/a');
    });
});
