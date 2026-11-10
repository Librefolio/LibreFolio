/**
 * formatTxQuantity — a transaction's quantity as the transactions table and the action modal show it (C-97c-1).
 * Vitest, node.
 *
 * D-C97c-1 (the coordinator, 17/10): a quantity on screen loses no digit the database keeps. `Transaction.quantity`
 * keeps ten decimals; `formatTxQuantity` writes the backend's decimal string at six (`parseFloat`, then
 * `toLocaleString` with `maximumFractionDigits: 6`), so 0.1234567891 reads +0.123457. The contract: up to ten
 * decimals, exact — the decimal string written as it is, never through a float — and everything else as today: a `+`
 * and 📈 above zero, 📉 below, `—` for nothing or zero, the interface language's notation.
 *
 * Reds today: 0.1234567891 cut at the sixth decimal; 123456789.1234567891 too, and it also holds more digits than a
 * float, so a cure through `Number` stays red on it. Guards, green today and after: a negative with one decimal, the
 * `—` of nothing and zero, and the Italian notation of a quantity within six decimals.
 *
 * Locale. The interface language through its store, as LanguageSelector sets it; the browser is pinned to en-US
 * below, so an English UI is written en-US and the English expectations are typed. The Italian one is Intl's output
 * for the decimal string, checked to differ from English.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action
 * `core-unit`).
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

// Node's `navigator.language` follows the host's ICU locale: pinned to en-US before any import, as jsdom's always is.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatTxQuantity} from './txDisplayHelpers';

type UiLanguage = 'en' | 'it';
/** The interface locale of each language on the en-US browser. */
const LOCALE_OF: Readonly<Record<UiLanguage, string>> = {en: 'en-US', it: 'it'};

/** Change the UI language as LanguageSelector does, and check the interface locale it gives. */
async function uiLanguage(lang: UiLanguage): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
    expect(uiLocale(), `control: a ${lang} UI on the en-US browser is written ${LOCALE_OF[lang]}`).toBe(LOCALE_OF[lang]);
}

/** What Intl writes for the plain decimal `text` in `locale`, with exactly its own fraction digits: the string, never a double. */
function intlExact(locale: string, text: string): string {
    const fractionDigits = text.split('.')[1]?.length ?? 0;
    return new Intl.NumberFormat(locale, {minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits}).format(text as Intl.StringNumericLiteral);
}

afterEach(async () => {
    // The language is module-level state shared by every test of the file.
    await uiLanguage('en');
});

describe('formatTxQuantity — every decimal the database keeps, up to ten, exact (C-97c-1)', () => {
    it('0.1234567891 reads +0.1234567891 📈 — the ten decimals of the column, not six', async () => {
        await uiLanguage('en');

        expect(formatTxQuantity('0.1234567891')).toBe('+0.1234567891 📈');
    });

    it('123456789.1234567891 reads +123,456,789.1234567891 📈 — the decimal string as it is, never through a float', async () => {
        await uiLanguage('en');
        expect(String(Number('123456789.1234567891')), 'control: a float does not hold every digit').not.toBe('123456789.1234567891');

        expect(formatTxQuantity('123456789.1234567891')).toBe('+123,456,789.1234567891 📈');
    });
});

describe('formatTxQuantity — the sign, the emoji and the notation, as today (guards)', () => {
    it('-2.5 reads -2.5 📉: its own minus, no +', async () => {
        await uiLanguage('en');

        expect(formatTxQuantity('-2.5')).toBe('-2.5 📉');
    });

    it.each([
        {qty: null, label: 'null'},
        {qty: undefined, label: 'undefined'},
        {qty: '', label: "''"},
        {qty: '0', label: "'0'"},
        {qty: '0.0000000000', label: "'0.0000000000'"},
    ])('$label reads — : nothing, or a zero quantity', async ({qty}) => {
        await uiLanguage('en');

        expect(formatTxQuantity(qty)).toBe('—');
    });

    it('Italian UI: -12345.5 in Italian notation, without passing a locale', async () => {
        await uiLanguage('it');
        const italian = intlExact('it', '-12345.5');
        expect(italian, 'control: Italian writes the quantity otherwise than English').not.toBe(intlExact('en-US', '-12345.5'));

        expect(formatTxQuantity('-12345.5')).toBe(`${italian} 📉`);
    });
});
