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
import type {RiskBenchmarkState} from '$lib/stores/risk/riskBenchmarkStore.svelte';

/** The fields of an asset this module reads. */
export interface SelectableAsset {
    id: number;
    active?: boolean;
    asset_type?: string | null;
    currency: string;
    /** Transactions across every broker the user can see. */
    tx_count?: number;
}

/** The API's ceiling on an asset-set scope. A limit, not a default. */
export const MAX_SELECTED_ASSETS = 100;

/** Which rung of the D19 ladder produced the opening selection. */
export type SelectionSource = 'persisted' | 'mine' | 'fallback';

/** How many assets to fall back to when the user holds none. */
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
 * D19 — the initial selection, in order of preference, and the rung it stopped on:
 *
 *  1. the user's last selection, intersected with what still exists;
 *  2. what they hold on the last day of the period (`held`, from the portfolio
 *     report — the caller fetches it, because it is asynchronous);
 *  3. a small readable handful.
 *
 * Step 1 intersects rather than trusting the stored list: an asset can be
 * deleted or merged between two visits, and asking the API for an id that no
 * longer resolves turns a stale preference into an error the user cannot
 * explain. Step 2 intersects too, for the same reason: a holding outside the
 * page's list would reach the analysis with no chip to remove it by.
 *
 * Step 2 used to read `tx_count_own > 0` — any transaction ever made in the
 * user's brokers — which also brought back positions sold years ago. Since the
 * developer's decision of 24/09, "mine" means held: quantity above the dust
 * threshold on the period's last day, the report's own holdings.
 *
 * The rung is reported because the selection alone cannot distinguish a
 * deliberate choice from a coincidence: a test that only counts the opening
 * selection would pass just as happily under the old "first hundred from the
 * array" behaviour, which never consulted ownership at all.
 *
 * Every branch is capped, so no path can reproduce the hundred-asset opening.
 */
export function resolveInitialSelectionWithSource(assets: readonly SelectableAsset[], persisted: readonly number[] | null = readPersistedSelection(), held: readonly number[] = []): {ids: number[]; source: SelectionSource} {
    const available = new Set(assets.map((asset) => asset.id));

    if (persisted) {
        // Deduped: the asset-set scope rejects a repeated id, and a duplicate that reached storage would
        // otherwise be read back and written again on every visit.
        const surviving = dedupe(persisted.filter((id) => available.has(id)));
        if (surviving.length > 0) return {ids: surviving.slice(0, MAX_SELECTED_ASSETS), source: 'persisted'};
    }

    const mine = dedupe(held.filter((id) => available.has(id)));
    if (mine.length > 0) return {ids: mine.slice(0, MAX_SELECTED_ASSETS), source: 'mine'};

    return {ids: fallbackSelection(assets), source: 'fallback'};
}

/**
 * The last resort: a user who holds nothing and has no history here.
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

/** Which mass action was pressed. */
export type BulkAction = 'all' | 'none' | 'invert';

/**
 * Resolve a mass action.
 *
 * `candidates` are the assets the action may bring in: the page's catalogue
 * without the ones Risk's engine rules out for the period. The filters no
 * longer narrow them — they moved into the "+", where they narrow a list, not
 * a button — so "all" really means all, and nothing can be selected past a
 * filter the user forgot was on.
 *
 * - `all` adds every candidate;
 * - `none` empties the selection, the ruled-out assets parked in it included:
 *   "deselect all" leaving chips behind would be a button that lies;
 * - `invert` swaps the candidates in and out, and leaves the parked ones where
 *   they are, since they were never candidates.
 *
 * "Mine" left this row: holdings are a period-dependent report, so they are a
 * command of their own (the panel's holdings menu), not a pure function.
 *
 * Everything is capped at the API limit, and `all` on a catalogue larger than
 * the cap truncates rather than failing: this is the one place where the
 * hundred is legitimate, because the user asked for it explicitly.
 */
export function applyBulkAction(action: BulkAction, selected: readonly number[], candidates: readonly SelectableAsset[]): number[] {
    const visible = candidates.map((asset) => asset.id);
    const current = new Set(selected);

    switch (action) {
        case 'all':
            return dedupe([...selected, ...visible]).slice(0, MAX_SELECTED_ASSETS);
        case 'none':
            return [];
        case 'invert': {
            const kept = selected.filter((id) => !visible.includes(id));
            const added = visible.filter((id) => !current.has(id));
            return dedupe([...kept, ...added]).slice(0, MAX_SELECTED_ASSETS);
        }
    }
}

function dedupe(ids: readonly number[]): number[] {
    return [...new Set(ids)];
}

/**
 * The benchmark the lab's comparison levels measure against, or `null`.
 *
 * Read from the shared picker (`BenchmarkSelect`): only a choice it has confirmed against the
 * asset list (`set`) is used — a stored id still being confirmed, or one no asset matches,
 * never reaches a request. A choice that is also one of the selected assets is used too
 * (D371): the backend keeps it in the selection, measures it like the others, and leaves it
 * out of the comparison's items, so it is the yardstick of the others and never of itself.
 */
export function labBenchmarkId(state: RiskBenchmarkState, value: number | null): number | null {
    return state === 'set' ? value : null;
}

/**
 * Whether L3° must wait before it asks (D378, the developer's decision of 06/10/2026: a
 * benchmark that cannot be measured over the period is not tried).
 *
 * It waits while the picker is still confirming a stored choice (`pending`), and — whenever a
 * benchmark is chosen, `set` or `blocked` — until the lab's eligibility verdicts for the current
 * list, period and currency have come back (or failed). The picker reads those verdicts as the
 * lab hands them over and does not wait for them: with the map still empty it says `set`, and
 * only when the verdict lands does it say `blocked`; on a new period it keeps the old verdict
 * until the new one lands. Asked in between, L3° would ask by a verdict that no longer decides
 * — trying a benchmark it must not, or leaving out one it may use — and then ask again. With no
 * benchmark (`none`, `unknown`) there is nothing to wait for.
 */
export function labL3Waits(state: RiskBenchmarkState, eligibilitySettled: boolean): boolean {
    return state === 'pending' || ((state === 'set' || state === 'blocked') && !eligibilitySettled);
}
