/**
 * The rule of the interface locale (M-18), alone: the interface language, plus the browser's region only when the
 * browser speaks that language. `uiLocale.ts` builds the app's locale with it and re-exports it.
 *
 * It imports nothing, on purpose: the E2E specs import it by path to write a day as the app does, and Playwright
 * resolves neither `$app` nor `$lib` (`uiLocale.test.ts` checks it).
 *
 * @module stores/app/uiLocaleRule
 */

/** The locale of an interface language when the browser cannot supply a region for it. */
const LANGUAGE_DEFAULTS: Readonly<Record<string, string>> = {en: 'en-GB'};

function canonicalTag(tag: string): string | undefined {
    try {
        return Intl.getCanonicalLocales(tag)[0];
    } catch {
        return undefined;
    }
}

/** The locale for an interface language, given the browser's primary language tag. */
export function resolveUiLocale(uiLanguage: string, browserTag: string | null | undefined): string {
    const language = uiLanguage.trim().toLowerCase();
    const tag = browserTag ? canonicalTag(browserTag.trim()) : undefined;
    if (tag) {
        // The browser contributes its region and nothing else: a bare `en` (or `en-Latn`) names none,
        // and kept as it is Intl would write it American (10/12/2026, 2:05 PM).
        const browser = new Intl.Locale(tag);
        if (browser.language === language && browser.region) return tag;
    }
    return LANGUAGE_DEFAULTS[language] ?? language;
}
