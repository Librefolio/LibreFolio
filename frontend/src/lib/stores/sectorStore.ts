/**
 * Sector Store — Session-level cache for financial sector names from GET /utilities/sectors.
 *
 * Loads once per session, then provides getSectorKeys() for any component.
 * Eliminates hardcoded sector arrays — single source of truth from the backend.
 *
 * Used by: DistributionEditor (sector options), assetTypes.ts (SECTOR_KEYS).
 *
 * @module stores/sectorStore
 */
import {zodiosApi} from '$lib/api';

// ============================================================================
// INTERNAL STATE
// ============================================================================

let sectorKeys: string[] = [];
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
            sectorKeys = response.items ?? [];
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

/** Check if sectors have been loaded. */
export function isSectorsLoaded(): boolean {
    return loaded;
}

