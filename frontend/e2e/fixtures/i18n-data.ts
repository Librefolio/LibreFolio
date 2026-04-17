/**
 * i18n Test Data - Auto-discovered from frontend i18n files
 *
 * This file provides language data for E2E tests.
 * Tests that need to verify language-specific UI should iterate over SUPPORTED_LANGUAGES.
 */
import * as fs from 'fs';
import * as path from 'path';
import {fileURLToPath} from 'url';

// ES module compatibility
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to i18n directory
const I18N_DIR = path.resolve(__dirname, '../../src/lib/i18n');

/**
 * Dynamically discover available languages from i18n directory
 */
function discoverLanguages(): string[] {
    const files = fs.readdirSync(I18N_DIR);
    return files
        .filter((f) => f.endsWith('.json'))
        .map((f) => f.replace('.json', ''))
        .sort();
}

/**
 * Load translations for a specific language
 */
function loadTranslations(lang: string): Record<string, any> {
    const filePath = path.join(I18N_DIR, `${lang}.json`);
    const content = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(content);
}

/**
 * Get a nested translation value by dot-notation key
 * Example: getTranslation(translations, 'auth.login') => 'Login'
 */
export function getTranslation(translations: Record<string, any>, key: string): string {
    const parts = key.split('.');
    let value: any = translations;
    for (const part of parts) {
        if (value && typeof value === 'object' && part in value) {
            value = value[part];
        } else {
            return key; // Return key if not found
        }
    }
    return typeof value === 'string' ? value : key;
}

// Discover languages at module load time
export const SUPPORTED_LANGUAGES = discoverLanguages();

// Language display info (matches frontend/src/lib/i18n/index.ts)
export const LANGUAGE_INFO: Record<string, {name: string; flag: string}> = {
    en: {name: 'English', flag: '🇬🇧'},
    it: {name: 'Italiano', flag: '🇮🇹'},
    fr: {name: 'Français', flag: '🇫🇷'},
    es: {name: 'Español', flag: '🇪🇸'},
    // Add more as needed - tests will still work with any language file present
};

// Pre-load all translations
export const TRANSLATIONS: Record<string, Record<string, any>> = {};
for (const lang of SUPPORTED_LANGUAGES) {
    TRANSLATIONS[lang] = loadTranslations(lang);
}

/**
 * Helper to get translation for a key in a specific language
 */
export function t(lang: string, key: string): string {
    const translations = TRANSLATIONS[lang];
    if (!translations) return key;
    return getTranslation(translations, key);
}

/**
 * Generate test data for all languages
 * Useful for parameterized tests
 */
export function forAllLanguages<T>(fn: (lang: string, translations: Record<string, any>) => T): T[] {
    return SUPPORTED_LANGUAGES.map((lang) => fn(lang, TRANSLATIONS[lang]));
}

// Export default language
export const DEFAULT_LANGUAGE = 'en';
