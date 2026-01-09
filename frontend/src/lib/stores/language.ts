/**
 * Language Store
 *
 * Manages the current language preference and syncs with i18n
 */
import { writable, derived } from 'svelte/store';
import { locale } from 'svelte-i18n';
import { browser } from '$app/environment';
import {
	SUPPORTED_LOCALES,
	DEFAULT_LOCALE,
	LOCALE_NAMES,
	LOCALE_FLAGS,
	saveLocalePreference,
	type SupportedLocale
} from '$lib/i18n';

/**
 * Current language store
 * Synced with svelte-i18n locale
 */
function createLanguageStore() {
	const { subscribe, set, update } = writable<SupportedLocale>(DEFAULT_LOCALE);

	return {
		subscribe,

		/**
		 * Set the current language
		 * Updates both the store and svelte-i18n locale
		 */
		set: (lang: SupportedLocale) => {
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
			update(current => {
				const currentIndex = SUPPORTED_LOCALES.indexOf(current);
				const nextIndex = (currentIndex + 1) % SUPPORTED_LOCALES.length;
				const nextLang = SUPPORTED_LOCALES[nextIndex];

				locale.set(nextLang);
				saveLocalePreference(nextLang);

				return nextLang;
			});
		},

		/**
		 * Initialize from browser/localStorage
		 */
		init: () => {
			if (!browser) return;

			// Get from localStorage or browser
			const stored = localStorage.getItem('librefolio-locale');
			if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
				set(stored as SupportedLocale);
				locale.set(stored);
			}
		}
	};
}

export const currentLanguage = createLanguageStore();

/**
 * Derived store for current language display name
 */
export const currentLanguageName = derived(
	currentLanguage,
	$lang => LOCALE_NAMES[$lang]
);

/**
 * Derived store for current language flag emoji
 */
export const currentLanguageFlag = derived(
	currentLanguage,
	$lang => LOCALE_FLAGS[$lang]
);

/**
 * List of all available languages for UI selectors
 * Re-exported from i18n for convenience
 */
export { LANGUAGE_OPTIONS as availableLanguages } from '$lib/i18n';
