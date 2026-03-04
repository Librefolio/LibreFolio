/**
 * Currency Store — Session-level cache for currency data from GET /currencies.
 *
 * Loads once per session, then provides getCurrencyInfo(code) for any component.
 * Eliminates duplicate API calls from multiple CurrencySearchSelect instances.
 *
 * Used by: CurrencySearchSelect, FxCard, FxPairAddModal, SettingCurrency, etc.
 *
 * @module stores/currencyStore
 */
import {zodiosApi} from '$lib/api';

// ============================================================================
// TYPES
// ============================================================================

export interface CurrencyInfo {
    code: string;
    name: string;
    symbol: string;
    flag_emoji: string;
    country_codes: string[];
}

// ============================================================================
// INTERNAL STATE
// ============================================================================

let allCurrencies: CurrencyInfo[] = [];
let currencyMap: Map<string, CurrencyInfo> = new Map();
let loaded = false;
let loading = false;
let loadPromise: Promise<void> | null = null;

// ============================================================================
// PUBLIC API
// ============================================================================

/**
 * Ensure currencies are loaded (idempotent — safe to call from any component).
 * First call triggers the API request; subsequent calls return the same promise
 * or resolve immediately if already loaded.
 */
export async function ensureCurrenciesLoaded(): Promise<void> {
    if (loaded) return;
    if (loadPromise) return loadPromise;

    loadPromise = (async () => {
        loading = true;
        try {
            const response = await zodiosApi.list_currencies_api_v1_utilities_currencies_get();
            allCurrencies = (response.items ?? []).map((c: any) => ({
                code: c.code,
                name: c.name,
                symbol: c.symbol,
                flag_emoji: c.flag_emoji ?? '🏳️',
                country_codes: c.country_codes ?? [],
            }));
            currencyMap = new Map(allCurrencies.map(c => [c.code, c]));
            loaded = true;
        } catch (e) {
            console.error('Failed to load currencies:', e);
        } finally {
            loading = false;
            loadPromise = null;
        }
    })();

    return loadPromise;
}

/**
 * Get all currencies (empty array if not loaded yet).
 * Call ensureCurrenciesLoaded() first if you need guaranteed data.
 */
export function getAllCurrencies(): CurrencyInfo[] {
    return allCurrencies;
}

/**
 * Get info for a specific currency code.
 * Returns a sensible fallback if not found or not yet loaded.
 */
export function getCurrencyInfo(code: string): CurrencyInfo {
    return currencyMap.get(code) ?? {
        code,
        name: code,
        symbol: code,
        flag_emoji: '🏳️',
        country_codes: [],
    };
}

/** Check if currencies have been loaded. */
export function isCurrenciesLoaded(): boolean {
    return loaded;
}

/** Check if currencies are currently being loaded. */
export function isCurrenciesLoading(): boolean {
    return loading;
}

