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

import {getClientSessionUserId} from '$lib/stores/app/clientSession';

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

const STORAGE_BASE_KEY = 'assetGlobal.riskSelection.v1';

/**
 * Where the selection lived before it was scoped to the user. It is only ever
 * removed, never read back: adopting it would hand one account's selection to
 * whichever account opened the page first on that browser — the leak the
 * scoping exists to close. Losing a remembered selection once is the price.
 */
const LEGACY_STORAGE_KEY = STORAGE_BASE_KEY;

/** Storage as this module uses it. `removeItem` is optional so minimal stand-ins still fit. */
type SelectionStorage = Pick<Storage, 'getItem' | 'setItem'> & Partial<Pick<Storage, 'removeItem'>>;

/**
 * The key for one account's selection, or `null` when there is no account.
 *
 * Per user, because the selection is the user's *work* — which assets they are
 * studying — not a property of the screen. (`privacyStore` keeps its key bare
 * for the opposite reason: privacy describes the screen being watched.) Same
 * `lf_<id>_` shape as `riskBenchmarkStore`, which sits on this page too.
 *
 * No identity means no memory. An `anon` bucket would be shared by every session
 * that has not identified itself yet: the same leak, in a smaller room.
 */
function storageKey(userId: string | null | undefined): string | null {
    return userId ? `lf_${userId}_${STORAGE_BASE_KEY}` : null;
}

/** Assets the user actually owns — what "my assets" means on this page. */
export function ownedAssetIds(assets: readonly SelectableAsset[]): number[] {
    return assets.filter((asset) => (asset.tx_count_own ?? 0) > 0).map((asset) => asset.id);
}

/**
 * Read the last selection this user made.
 *
 * Storage is best-effort on purpose: a browser with storage disabled, a quota
 * error or a value left over from an older shape must degrade to "no memory",
 * never to a broken page. The pre-scoping key is removed on the way, unread.
 */
export function readPersistedSelection(storage: SelectionStorage | null | undefined = safeStorage(), userId: string | null | undefined = getClientSessionUserId()): number[] | null {
    if (!storage) return null;
    try {
        storage.removeItem?.(LEGACY_STORAGE_KEY);
        const key = storageKey(userId);
        if (!key) return null;
        const raw = storage.getItem(key);
        if (!raw) return null;
        const parsed: unknown = JSON.parse(raw);
        if (!Array.isArray(parsed)) return null;
        const ids = parsed.filter((entry): entry is number => Number.isInteger(entry));
        return ids.length > 0 ? ids : null;
    } catch {
        return null;
    }
}

/** Persist this user's current selection. Failure is silent: it is a convenience, not a contract. */
export function writePersistedSelection(assetIds: readonly number[], storage: SelectionStorage | null | undefined = safeStorage(), userId: string | null | undefined = getClientSessionUserId()): void {
    if (!storage) return;
    const key = storageKey(userId);
    if (!key) return;
    try {
        storage.setItem(key, JSON.stringify([...assetIds]));
    } catch {
        /* storage full or disabled — the page works without memory */
    }
}

function safeStorage(): SelectionStorage | null {
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
export function applyFilters<T extends SelectableAsset>(assets: readonly T[], filters: SelectionFilters): T[] {
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

/**
 * A text as the "+" picker's search compares it: lower case, accents removed.
 * "societe" finds "Société", which a plain `includes` would miss.
 */
export function foldForSearch(text: string): string {
    return text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

/**
 * The rows of the "+" picker: the candidates not selected yet whose search text
 * holds **every** word of the query, in the order the caller passed them.
 *
 * Words rather than the whole query, so "etf usd" finds an ETF quoted in dollars
 * whichever way its name is written. An empty query lists every candidate.
 */
export function pickerRows<T extends {id: number}>(candidates: readonly T[], selected: readonly number[], query: string, searchText: (asset: T) => string): T[] {
    const taken = new Set(selected);
    const words = foldForSearch(query).split(/\s+/).filter(Boolean);
    return candidates.filter((asset) => {
        if (taken.has(asset.id)) return false;
        if (words.length === 0) return true;
        const haystack = foldForSearch(searchText(asset));
        return words.every((word) => haystack.includes(word));
    });
}

/**
 * The picker's "select visible" switch.
 *
 * It **unchecks** the visible rows when there is nothing left it could check:
 * every visible row is checked already, or the selection has no room left. Otherwise
 * it checks the visible rows in order, up to `room`, the number of assets the
 * selection can still take. Rows checked under an earlier query stay checked
 * either way: a search narrows what is shown, not what was chosen.
 */
export function toggleVisibleRows(checked: readonly number[], visible: readonly number[], room: number): number[] {
    const current = new Set(checked);
    const unchecked = visible.filter((id) => !current.has(id));
    const free = Math.max(0, room - current.size);
    if (unchecked.length === 0 || free === 0) {
        const shown = new Set(visible);
        return checked.filter((id) => !shown.has(id));
    }
    return [...checked, ...unchecked.slice(0, free)];
}

/** Whether the switch above would uncheck, which is what its label must say. */
export function visibleRowsAllChecked(checked: readonly number[], visible: readonly number[], room: number): boolean {
    const current = new Set(checked);
    return visible.length > 0 && (visible.every((id) => current.has(id)) || current.size >= room);
}
