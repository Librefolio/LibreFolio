/**
 * assetSetSelection — how Asset Global decides which assets are on the table.
 *
 * The rule this module exists to enforce:
 *
 * > The page opens on something readable. It never opens on a hundred assets.
 *
 * The previous seed took `assets.filter(active).slice(0, 100)`, which produced a
 * 100×100 matrix — ten thousand cells, with the in-cell numbers already
 * suppressed past twelve — and offered no way to undo it: ninety-four clicks on
 * an X, or the broker filter, which means something else. The system was
 * choosing badly on the user's behalf and giving them no way back.
 *
 * The hundred stays as a **limit** (the API's), never as a starting point.
 */

/** The fields of an asset this module reads. */
export interface SelectableAsset {
    id: number;
    active?: boolean;
    asset_type?: string | null;
    currency: string;
    /** Transactions across every broker the user can see. */
    tx_count?: number;
    /** F15 usage counter: transactions in brokers the current user owns. */
    tx_count_own?: number;
}

/** The API's ceiling on an asset-set scope. A limit, not a default. */
export const MAX_SELECTED_ASSETS = 100;

/** Which rung of the D19 ladder produced the opening selection. */
export type SelectionSource = 'persisted' | 'mine' | 'fallback';

/** How many assets to fall back to when the user owns none. */
export const FALLBACK_SELECTION_SIZE = 6;

const STORAGE_KEY = 'assetGlobal.riskSelection.v1';

/** Assets the user actually owns — what "my assets" means on this page. */
export function ownedAssetIds(assets: readonly SelectableAsset[]): number[] {
    return assets.filter((asset) => (asset.tx_count_own ?? 0) > 0).map((asset) => asset.id);
}

/**
 * Read the last selection the user made.
 *
 * Storage is best-effort on purpose: a browser with storage disabled, a quota
 * error or a value left over from an older shape must degrade to "no memory",
 * never to a broken page.
 */
export function readPersistedSelection(storage: Pick<Storage, 'getItem' | 'setItem'> | null | undefined = safeStorage()): number[] | null {
    if (!storage) return null;
    try {
        const raw = storage.getItem(STORAGE_KEY);
        if (!raw) return null;
        const parsed: unknown = JSON.parse(raw);
        if (!Array.isArray(parsed)) return null;
        const ids = parsed.filter((entry): entry is number => Number.isInteger(entry));
        return ids.length > 0 ? ids : null;
    } catch {
        return null;
    }
}

/** Persist the current selection. Failure is silent: it is a convenience, not a contract. */
export function writePersistedSelection(assetIds: readonly number[], storage: Pick<Storage, 'getItem' | 'setItem'> | null | undefined = safeStorage()): void {
    if (!storage) return;
    try {
        storage.setItem(STORAGE_KEY, JSON.stringify([...assetIds]));
    } catch {
        /* storage full or disabled — the page works without memory */
    }
}

function safeStorage(): Pick<Storage, 'getItem' | 'setItem'> | null {
    try {
        return typeof localStorage === 'undefined' ? null : localStorage;
    } catch {
        return null;
    }
}

/**
 * D19 — the initial selection, in order of preference:
 *
 *  1. the user's last selection, intersected with what still exists;
 *  2. the assets they own;
 *  3. a small readable handful.
 *
 * Step 1 intersects rather than trusting the stored list: an asset can be
 * deleted or merged between two visits, and asking the API for an id that no
 * longer resolves turns a stale preference into an error the user cannot
 * explain.
 *
 * Every branch is capped, so no path can reproduce the hundred-asset opening.
 */
export function resolveInitialSelection(assets: readonly SelectableAsset[], persisted: readonly number[] | null = readPersistedSelection()): number[] {
    return resolveInitialSelectionWithSource(assets, persisted).ids;
}

/**
 * The same ladder, but it also says which rung it stopped on.
 *
 * The branch is worth reporting because the selection alone cannot distinguish
 * a deliberate choice from a coincidence: a test that only counts the opening
 * selection would pass just as happily under the old "first hundred from the
 * array" behaviour, which never consulted ownership at all. Surfacing the
 * branch is what lets that regression be caught rather than merely be unlikely.
 *
 * `resolveInitialSelection` stays the thin wrapper so there is exactly one
 * implementation of the ladder to keep correct.
 */
export function resolveInitialSelectionWithSource(assets: readonly SelectableAsset[], persisted: readonly number[] | null = readPersistedSelection()): {ids: number[]; source: SelectionSource} {
    const available = new Set(assets.map((asset) => asset.id));

    if (persisted) {
        const surviving = persisted.filter((id) => available.has(id));
        if (surviving.length > 0) return {ids: surviving.slice(0, MAX_SELECTED_ASSETS), source: 'persisted'};
    }

    const owned = ownedAssetIds(assets);
    if (owned.length > 0) return {ids: owned.slice(0, MAX_SELECTED_ASSETS), source: 'mine'};

    return {ids: fallbackSelection(assets), source: 'fallback'};
}

/**
 * The last resort: a user who owns nothing and has no history here.
 *
 * Ranked by how much the instrument has actually been transacted, not by where
 * it happens to sit in the API's array. D19's point is that the system should
 * not choose badly on the user's behalf — and choosing by array position is
 * still choosing, it just hides the arbitrariness behind an index.
 *
 * Transaction count is the only signal of relevance available on this page:
 * anything closer to "importance" would be a position size, and this page shows
 * no money. Id breaks the ties, so the set is stable across reloads.
 */
function fallbackSelection(assets: readonly SelectableAsset[]): number[] {
    return [...assets]
        .filter((asset) => asset.active !== false)
        .sort((left, right) => (right.tx_count ?? 0) - (left.tx_count ?? 0) || left.id - right.id)
        .slice(0, FALLBACK_SELECTION_SIZE)
        .map((asset) => asset.id);
}

/** The criteria the filter row can narrow the candidate set by. */
export interface SelectionFilters {
    /** Empty means "every type" — an empty filter is not an empty result. */
    types: readonly string[];
    currencies: readonly string[];
}

export const EMPTY_FILTERS: SelectionFilters = {types: [], currencies: []};

/**
 * Apply the filter row.
 *
 * An empty criterion means *unconstrained*, not *matches nothing*: a filter row
 * that starts empty must show everything, or the page opens blank and the user
 * has to guess why.
 */
export function applyFilters(assets: readonly SelectableAsset[], filters: SelectionFilters): SelectableAsset[] {
    return assets.filter((asset) => {
        // `||`, not `??`: an empty-string type is as unclassified as a null
        // one, and under `??` it would match no criterion at all — an asset
        // that disappears the moment any filter is switched on.
        if (filters.types.length > 0 && !filters.types.includes(asset.asset_type || 'OTHER')) return false;
        if (filters.currencies.length > 0 && !filters.currencies.includes(asset.currency)) return false;
        return true;
    });
}

/** Which mass action was pressed. */
export type BulkAction = 'all' | 'none' | 'invert' | 'mine';

/**
 * Resolve a mass action against the **currently filtered** candidates.
 *
 * "All" and "invert" deliberately act on what the user can see rather than on
 * the whole catalogue: a button that silently reaches past the active filter
 * would undo the filter without saying so. "Mine" is the exception — it is a
 * *reset* to the user's own holdings, so it ignores the filter by design.
 *
 * Everything is capped at the API limit, and `all` on a catalogue larger than
 * the cap truncates rather than failing: this is the one place where the
 * hundred is legitimate, because the user asked for it explicitly.
 */
export function applyBulkAction(action: BulkAction, selected: readonly number[], candidates: readonly SelectableAsset[], allAssets: readonly SelectableAsset[]): number[] {
    const visible = candidates.map((asset) => asset.id);
    const current = new Set(selected);

    switch (action) {
        case 'all':
            return dedupe([...selected, ...visible]).slice(0, MAX_SELECTED_ASSETS);
        case 'none':
            // Only what is visible is cleared, mirroring `all`.
            return selected.filter((id) => !visible.includes(id));
        case 'invert': {
            const kept = selected.filter((id) => !visible.includes(id));
            const added = visible.filter((id) => !current.has(id));
            return dedupe([...kept, ...added]).slice(0, MAX_SELECTED_ASSETS);
        }
        case 'mine':
            return ownedAssetIds(allAssets).slice(0, MAX_SELECTED_ASSETS);
    }
}

function dedupe(ids: readonly number[]): number[] {
    return [...new Set(ids)];
}
