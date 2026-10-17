// @vitest-environment node
/**
 * importWizard.assetsCount — one asset is not written as several, in any language (O-12, Vitest, node).
 *
 * Why. The import wizard's summary says how many unique assets the files hold and how many of them still
 * need resolving (`ImportWizardModal.svelte`, `{n: stats.uniqueAssets, m: stats.unresolvedCount}`). The four
 * sources (`importWizard/<lang>.json`) hold one fixed form for any number: «1 unique assets, 1 need
 * resolution» in English, and the plural of one asset in Italian, French and Spanish as well.
 *
 * Contract. `n` is an ICU plural in all four languages, and in English `m` is one too («1 needs
 * resolution», «2 need resolution»). English is pinned exactly. The other three only have to tell one asset
 * from two — the n = 1 rendering is not the n = 2 rendering with its 2 written as 1 —, so the wording stays
 * the translators'. The same check runs on English as well.
 *
 * How. The message is formatted as the app formats it: svelte-i18n with the catalogues the app registers
 * (`$lib/i18n`, the generated `<lang>.json` that Vitest's global setup builds from the sources), the
 * language switched in place as the language selector does (`currentLanguage.set`, then `waitLocale`).
 * svelte-i18n caches a formatter by its text alone (devpy-i18n, rule 5), so each language's text is
 * formatted only while that language is the current one: its first compile takes that language's plural
 * rules. `m` is 7 in the per-language check, so the only 2 in the n = 2 rendering is `n`'s — a control
 * proves both numbers are written.
 *
 * Expected. Red today in all five cases: English reads «1 unique assets, 1 need resolution», and no
 * language tells one asset from two. Green once the four sources carry the plurals; the component does not
 * change.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit`
 * (action `core-unit`), next to `catalogIcuLocale.test.ts`.
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';
import {init, waitLocale} from 'svelte-i18n';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from './index';
import {currentLanguage} from '$lib/stores/app/language';

const KEY = 'importWizard.assetsCount';

/** Change the UI language in place, as the language selector does; its catalogue is loaded before the next step. */
async function uiLanguage(lang: SupportedLocale): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
}

/** The wizard's summary line in the current language: `n` unique assets, `m` of them still to resolve. */
const assetsCount = (n: number, m: number): string => get(_)(KEY, {values: {n, m}});

beforeAll(async () => {
    init({fallbackLocale: 'en', initialLocale: 'en'});
    await waitLocale('en');
});

afterEach(async () => {
    // The language is module-level state shared by every test of the file.
    await uiLanguage('en');
});

describe('importWizard.assetsCount — the numbers agree with their words (O-12)', () => {
    it('English: «1 unique asset, 1 needs resolution» and «3 unique assets, 2 need resolution»', async () => {
        await uiLanguage('en');

        expect({one: assetsCount(1, 1), several: assetsCount(3, 2)}).toEqual({one: '1 unique asset, 1 needs resolution', several: '3 unique assets, 2 need resolution'});
    });

    it.each(SUPPORTED_LOCALES)('%s: the number of unique assets picks a plural form — one asset does not read as two assets with its 2 written as 1', async (lang) => {
        await uiLanguage(lang);
        const one = assetsCount(1, 7);
        const two = assetsCount(2, 7);
        expect(two, `control: the ${lang} catalogue has the message`).not.toBe(KEY);
        expect(two.match(/\d+/g), 'control: both numbers are written, n = 2 and m = 7').toEqual(expect.arrayContaining(['2', '7']));

        expect(one, `n = 1 must not be the n = 2 text «${two}» with its 2 written as 1`).not.toBe(two.replace(/(?<!\d)2(?!\d)/, '1'));
    });
});
