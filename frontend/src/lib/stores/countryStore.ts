/**
 * Country Store — Session-level cache for country data from GET /utilities/countries.
 *
 * Loads once per session per language, then provides getCountryInfo(iso3) for any component.
 * Eliminates duplicate API calls from multiple country selectors.
 * Automatically invalidates and reloads when the app language changes.
 *
 * Used by: DistributionEditor (geographic), future geographic selectors.
 *
 * NOTE: The language codes passed here MUST match Babel locale codes (ISO 639-1:
 * 'en', 'it', 'fr', 'es', etc.) to ensure backend returns correctly localized data.
 *
 * @module stores/countryStore
 */
import {zodiosApi} from '$lib/api';

// ============================================================================
// TYPES
// ============================================================================

export interface CountryInfo {
    iso3: string;
    iso2: string;
    name: string;
    flag_emoji: string;
}

// ============================================================================
// INTERNAL STATE
// ============================================================================

let allCountries: CountryInfo[] = [];
let countryMap: Map<string, CountryInfo> = new Map();
let loaded = false;
let loading = false;
let loadPromise: Promise<void> | null = null;
/** Language used for the last successful load — used to detect language changes. */
let lastLoadedLanguage: string = '';

// ============================================================================
// PUBLIC API
// ============================================================================

/**
 * Ensure countries are loaded (idempotent — safe to call from any component).
 * First call triggers the API request; subsequent calls return the same promise
 * or resolve immediately if already loaded.
 *
 * If `language` differs from the last loaded language, the cache is invalidated
 * and data is reloaded in the new language.
 *
 * @param language - ISO 639-1 language code (must match Babel locale codes: 'en', 'it', 'fr', 'es', etc.)
 */
export async function ensureCountriesLoaded(language: string = 'en'): Promise<void> {
    // If language changed, invalidate cache
    if (loaded && language !== lastLoadedLanguage) {
        loaded = false;
        loadPromise = null;
    }

    if (loaded) return;
    if (loadPromise) return loadPromise;

    loadPromise = (async () => {
        loading = true;
        try {
            const response = await (zodiosApi as any).list_countries_api_v1_utilities_countries_get({
                queries: {language},
            });
            allCountries = (response.items ?? []).map((c: any) => ({
                iso3: c.iso3 ?? c.code ?? '',
                iso2: c.iso2 ?? '',
                name: c.name ?? c.iso3 ?? '',
                flag_emoji: c.flag_emoji ?? '🏳️',
            }));
            countryMap = new Map(allCountries.map(c => [c.iso3, c]));
            loaded = true;
            lastLoadedLanguage = language;
        } catch (e) {
            console.error('Failed to load countries:', e);
        } finally {
            loading = false;
            loadPromise = null;
        }
    })();

    return loadPromise;
}

/**
 * Get all countries (empty array if not loaded yet).
 * Call ensureCountriesLoaded() first if you need guaranteed data.
 */
export function getAllCountries(): CountryInfo[] {
    return allCountries;
}

/**
 * Get info for a specific country by ISO-3166-A3 code.
 * Returns a sensible fallback if not found or not yet loaded.
 */
export function getCountryInfo(iso3: string): CountryInfo {
    return countryMap.get(iso3) ?? {
        iso3,
        iso2: '',
        name: iso3,
        flag_emoji: '🏳️',
    };
}

/** Check if countries have been loaded. */
export function isCountriesLoaded(): boolean {
    return loaded;
}

/** Check if countries are currently being loaded. */
export function isCountriesLoading(): boolean {
    return loading;
}

