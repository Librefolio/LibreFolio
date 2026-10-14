// @vitest-environment jsdom
/**
 * Header toggles — PrivacyToggle and ThemeToggle label themselves through i18n (Vitest + jsdom).
 *
 * Subject. Both toggles take their `aria-label` and `title` from catalogue keys:
 *   - PrivacyToggle (runes): `header.privacy.hide` while amounts are shown, `header.privacy.show`
 *     while they are hidden — one string on both attributes — and `aria-pressed` carries the
 *     state itself;
 *   - ThemeToggle (legacy): `header.theme.switchToDark` (aria-label) and `header.theme.dark`
 *     (title) in the light theme, `header.theme.switchToLight` and `header.theme.light` in the
 *     dark one.
 * They used to be English literals in the components, so the header spoke English in every
 * locale, to screen readers and in every tooltip.
 *
 * Expectations are read from the catalogue JSON, per key and locale, and never written here: a
 * component test does not assert on translated text. The second locale is what gives the
 * assertions teeth — the English values equal the old literals, so a regression to literals is
 * caught only by the `it` steps — and a first test checks that the catalogues really differ
 * where the steps need them to (en vs it on every key, and the two states of each attribute
 * within a locale), or those steps would compare equal strings and prove nothing.
 *
 * Locale. Switched the way the app does (LanguageSelector, PreferencesTab):
 * `currentLanguage.set(lang)`, which drives svelte-i18n's `locale`. Both dictionaries are loaded
 * in `beforeAll`, so a switch is a pure state change: the test measures the components following
 * the locale, not the loader. Most switches happen in place, because the header stays mounted
 * while the user changes language — and ThemeToggle is legacy, the component kind whose template
 * may track less than it reads (R20, see BrokerCard.test.ts). Only an in-place step sees that.
 *
 * Privacy moves through the real store (`setPrivacyEnabled`) and through the button's own click
 * (`togglePrivacy`), both ways, each change flushed with `tick()`; it is reset after each test.
 * The shared `$app/environment` mock reports `browser: false`, so the privacy and language stores
 * stay in memory.
 *
 * Theme. The real themeStore runs. Its side effects are the stored preference — kept by a
 * `localStorage` stub this file owns and clears — and the `light`/`dark` class on `<html>`,
 * removed after each test. The harness's `matchMedia` stub matches nothing, so with nothing
 * stored the resolved theme is light: checked before every mount, not assumed.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {locale, waitLocale} from 'svelte-i18n';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import enCatalog from '$lib/i18n/en.json';
import itCatalog from '$lib/i18n/it.json';
import {currentLanguage} from '$lib/stores/app/language';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {getCurrentResolvedTheme, getStoredThemePreference, type ResolvedTheme} from '$lib/stores/app/themeStore';
import PrivacyToggle from './PrivacyToggle.svelte';
import ThemeToggle from './ThemeToggle.svelte';

// The theme preference is the only storage this graph writes. Stubbed so the file owns it: Node 26
// ships a global `localStorage` that is unavailable without --localstorage-file, and elsewhere a
// preference left by one test would decide the next test's starting theme. Nothing reads storage
// at import time, so installing the stub after the imports is early enough.
const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
    clear: () => storage.clear(),
});

const CATALOGS = {en: enCatalog, it: itCatalog} as const;
type Lang = keyof typeof CATALOGS;
const LOCALES: readonly Lang[] = ['en', 'it'];

const PRIVACY_KEYS = {shown: 'header.privacy.hide', hidden: 'header.privacy.show'} as const;
const THEME_KEYS = {
    light: {aria: 'header.theme.switchToDark', title: 'header.theme.dark'},
    dark: {aria: 'header.theme.switchToLight', title: 'header.theme.light'},
} as const;
/** Pairs of keys one attribute switches between: equal values would make a switch invisible. */
const STATE_PAIRS = [
    [PRIVACY_KEYS.shown, PRIVACY_KEYS.hidden],
    [THEME_KEYS.light.aria, THEME_KEYS.dark.aria],
    [THEME_KEYS.light.title, THEME_KEYS.dark.title],
] as const;
const ALL_KEYS = STATE_PAIRS.flat();

/** The catalogue value of `key` in `lang`, walked from the JSON. A missing key is a red, not a fallback. */
function fromCatalog(lang: Lang, key: string): string {
    const value = key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), CATALOGS[lang]);
    if (typeof value !== 'string' || value.trim() === '') throw new Error(`src/lib/i18n/${lang}.json has no string at ${key}`);
    return value;
}

const privacyToggle = () => screen.getByTestId('privacy-toggle');
const themeToggle = () => screen.getByTestId('theme-toggle');

/** Both labels of a toggle, as rendered right now. */
function labels(element: HTMLElement): {aria: string | null; title: string | null} {
    return {aria: element.getAttribute('aria-label'), title: element.getAttribute('title')};
}

/** Change language as the app does, then flush. The control names the layer if the locale did not move. */
async function switchLocale(lang: Lang): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
    flushSync();
    await tick();
    expect(get(locale), `control: the svelte-i18n locale is ${lang}`).toBe(lang);
}

/** Move the flag through the real store, then flush. */
async function setPrivacy(value: boolean): Promise<void> {
    setPrivacyEnabled(value);
    flushSync();
    await tick();
    expect(isPrivacyEnabled(), 'control: the privacy flag').toBe(value);
}

async function click(element: HTMLElement): Promise<void> {
    await fireEvent.click(element);
    flushSync();
    await tick();
}

function expectPrivacyToggle(lang: Lang, hidden: boolean, step: string): void {
    const key = hidden ? PRIVACY_KEYS.hidden : PRIVACY_KEYS.shown;
    const label = fromCatalog(lang, key);
    const toggle = privacyToggle();
    expect(toggle.getAttribute('aria-label'), `${step} — aria-label is ${lang}:${key}`).toBe(label);
    expect(toggle.getAttribute('title'), `${step} — title is ${lang}:${key}`).toBe(label);
    expect(toggle.getAttribute('aria-pressed'), `${step} — aria-pressed follows the flag`).toBe(String(hidden));
}

function expectThemeToggle(lang: Lang, theme: ResolvedTheme, step: string): void {
    const {aria, title} = THEME_KEYS[theme];
    const toggle = themeToggle();
    expect(toggle.getAttribute('aria-label'), `${step} — aria-label is ${lang}:${aria}`).toBe(fromCatalog(lang, aria));
    expect(toggle.getAttribute('title'), `${step} — title is ${lang}:${title}`).toBe(fromCatalog(lang, title));
}

async function mountPrivacyToggle(): Promise<void> {
    render(PrivacyToggle);
    flushSync();
    await tick();
}

async function mountThemeToggle(): Promise<void> {
    // Controls: nothing stored and no OS preference, so the component must start light.
    expect(getStoredThemePreference(), 'control: no stored theme preference').toBe('auto');
    expect(getCurrentResolvedTheme(), 'control: the resolved theme').toBe('light');
    render(ThemeToggle);
    flushSync();
    await tick();
    // Barrier: onMount ran — it resolved the theme and swapped the SSR placeholder for the icon.
    expect(themeToggle().querySelector('svg'), 'barrier: ThemeToggle mounted').not.toBeNull();
}

beforeAll(async () => {
    await setupI18n('en');
    // Both dictionaries up front: a later `currentLanguage.set('it')` is a pure state change.
    await waitLocale('it');
});

afterEach(async () => {
    // Module-level state shared by every test of the file: privacy flag, theme, locale.
    setPrivacyEnabled(false);
    storage.clear();
    document.documentElement.classList.remove('light', 'dark');
    await switchLocale('en');
});

describe('header toggles — catalogue preconditions', () => {
    it('en and it differ on every key, and each attribute has two distinct states per locale', () => {
        for (const key of ALL_KEYS) {
            expect(fromCatalog('it', key), `${key}: en and it must differ, or the it steps prove nothing`).not.toBe(fromCatalog('en', key));
        }
        for (const lang of LOCALES) {
            for (const [a, b] of STATE_PAIRS) {
                expect(fromCatalog(lang, a), `${lang}: ${a} and ${b} must differ, or a state switch is invisible`).not.toBe(fromCatalog(lang, b));
            }
        }
    });
});

describe('PrivacyToggle — labels from the catalogue', () => {
    it('follows the store both ways, then an in-place switch en → it; aria-pressed follows', async () => {
        await mountPrivacyToggle();
        expectPrivacyToggle('en', false, 'en, mount, shown');
        const enShown = labels(privacyToggle());

        await setPrivacy(true);
        expectPrivacyToggle('en', true, 'en, shown → hidden');
        const enHidden = labels(privacyToggle());

        await switchLocale('it');
        expectPrivacyToggle('it', true, 'en → it in place, hidden');
        expect(labels(privacyToggle()).aria, 'it, hidden — differs from en').not.toBe(enHidden.aria);

        await setPrivacy(false);
        expectPrivacyToggle('it', false, 'it, hidden → shown');
        expect(labels(privacyToggle()).aria, 'it, shown — differs from en').not.toBe(enShown.aria);

        await setPrivacy(true);
        expectPrivacyToggle('it', true, 'it, shown → hidden');
    });

    it.each(LOCALES)('a click toggles privacy both ways and the label follows (%s)', async (lang) => {
        await switchLocale(lang);
        await mountPrivacyToggle();
        expectPrivacyToggle(lang, false, `${lang}, mount`);

        await click(privacyToggle());
        expect(isPrivacyEnabled(), `${lang} — control: the click turned privacy on`).toBe(true);
        expectPrivacyToggle(lang, true, `${lang}, click → hidden`);

        await click(privacyToggle());
        expect(isPrivacyEnabled(), `${lang} — control: the click turned privacy off`).toBe(false);
        expectPrivacyToggle(lang, false, `${lang}, click → shown`);
    });
});

describe('ThemeToggle — labels from the catalogue', () => {
    it('follows an in-place switch en → it, and back, in both themes', async () => {
        await mountThemeToggle();
        expectThemeToggle('en', 'light', 'en, mount, light');
        const enLight = labels(themeToggle());

        await switchLocale('it');
        expectThemeToggle('it', 'light', 'en → it in place, light');
        const itLight = labels(themeToggle());
        expect(itLight.aria, 'it, light — aria-label differs from en').not.toBe(enLight.aria);
        expect(itLight.title, 'it, light — title differs from en').not.toBe(enLight.title);

        await click(themeToggle());
        expect(getCurrentResolvedTheme(), 'control: the click applied the dark theme').toBe('dark');
        expectThemeToggle('it', 'dark', 'it, light → dark');
        const itDark = labels(themeToggle());

        await switchLocale('en');
        expectThemeToggle('en', 'dark', 'it → en in place, dark');
        const enDark = labels(themeToggle());
        expect(enDark.aria, 'en, dark — aria-label differs from it').not.toBe(itDark.aria);
        expect(enDark.title, 'en, dark — title differs from it').not.toBe(itDark.title);
    });

    it.each(LOCALES)('a click switches between switchToDark and switchToLight, both ways (%s)', async (lang) => {
        await switchLocale(lang);
        await mountThemeToggle();
        expectThemeToggle(lang, 'light', `${lang}, mount, light`);

        await click(themeToggle());
        expect(getStoredThemePreference(), `${lang} — control: the click stored the dark theme`).toBe('dark');
        expectThemeToggle(lang, 'dark', `${lang}, click → dark`);

        await click(themeToggle());
        expect(getStoredThemePreference(), `${lang} — control: the click stored the light theme`).toBe('light');
        expectThemeToggle(lang, 'light', `${lang}, click → light`);
    });
});
