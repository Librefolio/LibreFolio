/**
 * Language Store
 *
 * Manages the current language preference and syncs with i18n
 */
import {derived, writable} from 'svelte/store';
import {locale} from 'svelte-i18n';
import {browser} from '$app/environment';
import {DEFAULT_LOCALE, LOCALE_FLAGS, LOCALE_NAMES, saveLocalePreference, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';

/**
 * Get initial locale from localStorage (browser only)
 */
function getStoredLocale(): SupportedLocale {
    if (!browser) return DEFAULT_LOCALE;
    const stored = localStorage.getItem('librefolio-locale');
    if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
        return stored as SupportedLocale;
    }
    return DEFAULT_LOCALE;
}

/**
 * Current language store
 * Synced with svelte-i18n locale
 * Initialized from localStorage immediately
 */
function createLanguageStore() {
    // Initialize with stored value immediately
    const initialLocale = getStoredLocale();
    const {subscribe, set, update} = writable<SupportedLocale>(initialLocale);

    // Also set the svelte-i18n locale immediately to stay in sync
    if (browser) {
        locale.set(initialLocale);
    }

    // With no stored preference the store follows the language svelte-i18n has in force, until one is picked here.
    let stopFollowing: (() => void) | null = null;
    function unfollow(): void {
        stopFollowing?.();
        stopFollowing = null;
    }

    return {
        subscribe,

        /**
         * Set the current language
         * Updates both the store and svelte-i18n locale
         */
        set: (lang: SupportedLocale) => {
            unfollow();
            if (!SUPPORTED_LOCALES.includes(lang)) {
                console.warn(`Unsupported locale: ${lang}, falling back to ${DEFAULT_LOCALE}`);
                lang = DEFAULT_LOCALE;
            }

            set(lang);
            locale.set(lang);
            saveLocalePreference(lang);
        },

        /**
         * Cycle through available languages
         * Useful for language picker buttons
         */
        cycle: () => {
            unfollow();
            update((current) => {
                const currentIndex = SUPPORTED_LOCALES.indexOf(current);
                const nextIndex = (currentIndex + 1) % SUPPORTED_LOCALES.length;
                const nextLang = SUPPORTED_LOCALES[nextIndex];

                locale.set(nextLang);
                saveLocalePreference(nextLang);

                return nextLang;
            });
        },

        /**
         * Initialize from browser/localStorage and sync with svelte-i18n
         * Called after mount to ensure sync
         */
        init: () => {
            if (!browser) return;

            // Get from localStorage
            const stored = localStorage.getItem('librefolio-locale');
            if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
                const lang = stored as SupportedLocale;
                unfollow();
                set(lang);
                locale.set(lang);
            } else if (!stopFollowing) {
                // No stored value: follow svelte-i18n's locale. It moves to the browser's language only once that
                // dictionary has loaded, so the value read at mount can still be the default (TC-6: the page in
                // Italian, the selector on English). Following stops when a language is picked through this store.
                stopFollowing = locale.subscribe((currentLocale) => {
                    if (currentLocale && SUPPORTED_LOCALES.includes(currentLocale as SupportedLocale)) {
                        set(currentLocale as SupportedLocale);
                    }
                });
            }
        },
    };
}

export const currentLanguage = createLanguageStore();

/**
 * Derived store for current language display name
 */
export const currentLanguageName = derived(currentLanguage, ($lang) => LOCALE_NAMES[$lang]);

/**
 * Derived store for current language flag emoji
 */
export const currentLanguageFlag = derived(currentLanguage, ($lang) => LOCALE_FLAGS[$lang]);

/**
 * List of all available languages for UI selectors
 * Re-exported from i18n for convenience
 */
export {LANGUAGE_OPTIONS as availableLanguages} from '$lib/i18n';
