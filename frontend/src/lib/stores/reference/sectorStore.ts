/**
 * Sector Store — Session-level cache for financial sector names from GET /utilities/sectors.
 *
 * Loads once per session, then provides getSectorKeys() and getSectorEmoji() for any component.
 * Eliminates hardcoded sector arrays — single source of truth from the backend.
 *
 * Used by: DistributionEditor (sector options), assetTypes.ts (SECTOR_KEYS),
 *          AllocationHistoryChart (emoji icons).
 *
 * @module stores/sectorStore
 */
import {zodiosApi} from '$lib/api';

// ============================================================================
// INTERNAL STATE
// ============================================================================

let sectorKeys: string[] = [];
let sectorEmojiMap: Record<string, string> = {};
let loaded = false;
let loading = false;
let loadPromise: Promise<void> | null = null;

// ============================================================================
// PUBLIC API
// ============================================================================

/**
 * Ensure sectors are loaded (idempotent — safe to call from any component).
 * First call triggers the API request; subsequent calls return the same promise
 * or resolve immediately if already loaded.
 */
export async function ensureSectorsLoaded(): Promise<void> {
    if (loaded) return;
    if (loadPromise) return loadPromise;

    loadPromise = (async () => {
        loading = true;
        try {
            const response = await (zodiosApi as any).list_sectors_api_v1_utilities_sectors_get({
                queries: {include_other: true},
            });
            const items = response.items ?? [];
            // Handle both old format (string[]) and new format ({key, emoji}[])
            if (items.length > 0 && typeof items[0] === 'object') {
                sectorKeys = items.map((i: any) => i.key);
                sectorEmojiMap = Object.fromEntries(items.map((i: any) => [i.key, i.emoji ?? '📊']));
            } else {
                sectorKeys = items;
                sectorEmojiMap = {};
            }
            loaded = true;
        } catch (e) {
            console.error('Failed to load sectors:', e);
        } finally {
            loading = false;
            loadPromise = null;
        }
    })();

    return loadPromise;
}

/**
 * Get all sector keys (empty array if not loaded yet).
 * Call ensureSectorsLoaded() first if you need guaranteed data.
 */
export function getSectorKeys(): string[] {
    return sectorKeys;
}

/**
 * Get the emoji for a sector key. Returns from backend data if available,
 * otherwise uses built-in fallback map.
 */
export function getSectorEmoji(key: string): string {
    if (sectorEmojiMap[key]) return sectorEmojiMap[key];
    // Fallback: hardcoded map (used until API sync regenerates client)
    const FALLBACK: Record<string, string> = {
        Industrials: '🏭',
        Technology: '💻',
        Financials: '🏦',
        'Consumer Discretionary': '🛍️',
        'Health Care': '🏥',
        'Real Estate': '🏠',
        'Basic Materials': '⛏️',
        Energy: '⚡',
        'Consumer Staples': '🛒',
        Telecommunication: '📡',
        Utilities: '💡',
        Other: '📦',
        Liquidity: '💰',
        Unknown: '❓',
    };
    return FALLBACK[key] ?? '📊';
}

/** Check if sectors have been loaded. */
export function isSectorsLoaded(): boolean {
    return loaded;
}
