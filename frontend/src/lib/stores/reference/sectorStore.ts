/**
 * Sector Store — session cache of GET /utilities/sectors: the sector keys, and the emoji of every sector and of the two
 * allocation buckets (the cash, the unclassified), from the backend's one map (`backend/app/utils/asset/sector.py`).
 *
 * No emoji is written here (developer, 15/10/2026: «se la andasse a prendere dal backend per essere centralizzati»).
 * Until the list arrives a key has none, and every reader inside a reactive context — a `$derived`, an `$effect`, a
 * template — runs again when it does (`createSubscriber`). A key the backend lists nowhere gets the backend's own
 * fallback (`fallback_emoji`).
 *
 * Used by: DistributionEditor and SectorSearchSelect (sector options), assetTypes.ts (`getSectorKeysList`), the
 * allocation pie and history, the correlation heatmap, the risk panels, the PAC categories.
 *
 * @module stores/sectorStore
 */
import {createSubscriber} from 'svelte/reactivity';
import {zodiosApi} from '$lib/api';

// ============================================================================
// INTERNAL STATE
// ============================================================================

let sectorKeys: string[] = [];
let emojiByKey = new Map<string, string>();
let fallbackEmoji = '';
let loaded = false;
let version = 0;
let loadPromise: Promise<void> | null = null;
let announce: (() => void) | null = null;

/** Registers the reader in a reactive context; `announce()` then runs it again. */
const track = createSubscriber((update) => {
    announce = update;
    return () => {
        announce = null;
    };
});

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
        try {
            const response = await zodiosApi.list_sectors_api_v1_utilities_sectors_get({
                queries: {include_other: true},
            });
            const items = response.items ?? [];
            const buckets = response.buckets ?? [];
            sectorKeys = items.map((item) => item.key);
            // A Map, not an object: `constructor` or `__proto__` must not answer with what Object.prototype holds.
            emojiByKey = new Map([...items, ...buckets].map((entry): [string, string] => [entry.key, entry.emoji]));
            fallbackEmoji = response.fallback_emoji ?? '';
            loaded = true;
            version += 1;
            announce?.();
        } catch (e) {
            console.error('Failed to load sectors:', e);
        } finally {
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
    track();
    return sectorKeys;
}

/**
 * The emoji of a sector or an allocation bucket (`Liquidity`, `Unknown`), as the backend lists it: `''` until the
 * list arrives, the backend's fallback for a key it does not list.
 */
export function getSectorEmoji(key: string): string {
    track();
    return emojiByKey.get(key) ?? (loaded ? fallbackEmoji : '');
}

/**
 * A number that changes when the list arrives. Read it in the reactive context of a view that writes the emoji
 * somewhere a reactive read cannot follow — a chart option built later, in a callback — to rebuild that view then.
 */
export function sectorEmojiVersion(): number {
    track();
    return version;
}
