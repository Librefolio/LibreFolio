/**
 * formatDateTime.test.ts — locale-aware date+time label for file listings.
 *
 * Like formatAxisDate, the exact string is ICU/timezone dependent, so the
 * assertions pin the *contract* rather than a literal: the date parts are
 * present AND a wall-clock time is present (the trait that distinguishes this
 * family from the date-only formatters). A local-constructed timestamp keeps the
 * rendered time stable across the runner's timezone.
 *
 * M-18 CP2 (the developer's rule of 2026-10-12: every figure in the interface
 * language). Without a locale the label is written in the interface locale —
 * `uiLocale()`, the UI language regionalised by the browser — and no longer in
 * the browser's own (`toLocaleDateString(undefined, …)`): an Italian UI reads the
 * Italian label whatever the machine. An explicit locale still wins. The
 * localized expectations come from Intl in this runtime with the formatter's own
 * options, never typed. Node's `navigator.language` follows the host's ICU
 * locale, so it is pinned to en-US before any import, as jsdom's always is: the
 * English UI then writes en-US, today's text.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {formatDateTime} from '../formatDateTime';

// 5 June 2024, 14:30 local — local components so no timezone shifts the wall
// clock, and mid-year so no boundary disturbs the date parts.
const d = new Date(2024, 5, 5, 14, 30);

/** What formatDateTime asks Intl for: a short date and the wall-clock time. */
const DATE_TIME: Intl.DateTimeFormatOptions = {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'};

/** The label of `value` in `locale`, as Intl writes it in this runtime. */
const labelIn = (locale: string, value: Date | string = d): string => new Date(value).toLocaleDateString(locale, DATE_TIME);

/** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
async function uiLanguage(lang: 'en' | 'it' | 'fr'): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
}

afterEach(async () => {
    // The language is module-level state shared by every test of the file.
    await uiLanguage('en');
});

describe('formatDateTime', () => {
    it('includes the date parts (short month, day, year)', () => {
        const out = formatDateTime(d, 'en-US');
        expect(out).toContain('Jun');
        expect(out).toContain('2024');
        expect(out).toMatch(/\b5\b/);
    });

    it('includes a wall-clock time — the trait that separates it from date-only formatters', () => {
        const out = formatDateTime(d, 'en-US');
        expect(out).toMatch(/\d{1,2}:\d{2}/);
        expect(out).toContain('30'); // the minute
    });

    it('accepts an ISO string as well as a Date', () => {
        // No trailing Z → parsed as local, so the wall clock is timezone-stable.
        const out = formatDateTime('2024-06-05T14:30:00', 'en-US');
        expect(out).toContain('2024');
        expect(out).toMatch(/\d{1,2}:\d{2}/);
    });

    it('without a locale, the interface locale: the English UI on an en-US browser writes en-US, today’s text', async () => {
        // Was "falls back to the environment locale": the machine's locale is no longer the default (M-18 CP2).
        await uiLanguage('en');

        expect(formatDateTime(d)).toBe(labelIn('en-US'));
        expect(formatDateTime('2024-06-05T14:30:00')).toBe(labelIn('en-US'));
    });
});

describe('formatDateTime — without a locale, the UI language (M-18 CP2)', () => {
    it('Italian UI: the Italian label, without passing a locale', async () => {
        await uiLanguage('it');
        const expected = labelIn('it');
        expect(expected, 'control: the Italian label differs from the English one').not.toBe(labelIn('en-US'));

        expect(formatDateTime(d)).toBe(expected);
        expect(formatDateTime('2024-06-05T14:30:00'), 'an ISO string, too').toBe(expected);
    });

    it('follows the UI language from one call to the next: it → fr → en', async () => {
        const written: Record<string, string> = {};
        for (const lang of ['it', 'fr', 'en'] as const) {
            await uiLanguage(lang);
            written[lang] = formatDateTime(d);
        }

        expect(written).toEqual({it: labelIn('it'), fr: labelIn('fr'), en: labelIn('en-US')});
    });

    it('an explicit locale still wins over the UI language', async () => {
        await uiLanguage('it');

        expect(formatDateTime(d, 'en-US')).toBe(labelIn('en-US'));
        expect(formatDateTime(d, 'fr')).toBe(labelIn('fr'));
    });
});
