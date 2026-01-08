/**
 * i18n Configuration for LibreFolio
 *
 * Supported languages: English, Italian, French, Spanish
 * Uses svelte-i18n for internationalization
 */
import { browser } from '$app/environment';
import { init, register, getLocaleFromNavigator } from 'svelte-i18n';

// Register language files
register('en', () => import('./en.json'));
register('it', () => import('./it.json'));
register('fr', () => import('./fr.json'));
register('es', () => import('./es.json'));

// Supported locales
export const SUPPORTED_LOCALES = ['en', 'it', 'fr', 'es'] as const;
export type SupportedLocale = typeof SUPPORTED_LOCALES[number];

// Default locale
export const DEFAULT_LOCALE: SupportedLocale = 'en';

// Locale display names (in their own language)
export const LOCALE_NAMES: Record<SupportedLocale, string> = {
	en: 'English',
	it: 'Italiano',
	fr: 'Français',
	es: 'Español'
};

// Locale flags (emoji)
export const LOCALE_FLAGS: Record<SupportedLocale, string> = {
	en: '🇬🇧',
	it: '🇮🇹',
	fr: '🇫🇷',
	es: '🇪🇸'
};

/**
 * Get the initial locale from browser or localStorage
 */
function getInitialLocale(): SupportedLocale {
	if (!browser) return DEFAULT_LOCALE;

	// Try localStorage first
	const stored = localStorage.getItem('librefolio-locale');
	if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
		return stored as SupportedLocale;
	}

	// Try browser locale
	const browserLocale = getLocaleFromNavigator();
	if (browserLocale) {
		// Extract language code (e.g., 'en-US' -> 'en')
		const lang = browserLocale.split('-')[0];
		if (SUPPORTED_LOCALES.includes(lang as SupportedLocale)) {
			return lang as SupportedLocale;
		}
	}

	return DEFAULT_LOCALE;
}

/**
 * Initialize i18n
 * Call this in your root layout
 */
export function initI18n() {
	init({
		fallbackLocale: DEFAULT_LOCALE,
		initialLocale: getInitialLocale(),
	});
}

/**
 * Save locale preference to localStorage
 */
export function saveLocalePreference(locale: SupportedLocale) {
	if (browser) {
		localStorage.setItem('librefolio-locale', locale);
	}
}

// Re-export commonly used functions from svelte-i18n
export {
	locale,
	t,
	_,
	date,
	time,
	number,
	isLoading as i18nLoading
} from 'svelte-i18n';
