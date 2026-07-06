/**
 * Maps frontend locale codes to full language names for AI prompt output.
 */

const LANGUAGE_MAP: Record<string, string> = {
    en: 'English',
    it: 'Italian',
    fr: 'French',
    es: 'Spanish',
};

/** Returns the full language name for a locale code, defaulting to English. */
export function getResponseLanguage(locale: string): string {
    const base = locale.split('-')[0].toLowerCase();
    return LANGUAGE_MAP[base] ?? 'English';
}
