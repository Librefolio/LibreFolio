/**
 * The pure half of `AssetPickerPanel`: the picker of **portfolio assets** (not of image files, which
 * `ui/media/AssetPickerModal.svelte` picks).
 *
 * The filter, search and "select visible" rules came here from the Asset Global lab
 * (`risk/assetSetSelection.ts`) with the panel, unchanged. The search and order rules of
 * `AssetSelect` live here too, so that a select and a panel listing the same assets cannot disagree
 * on what a query finds or on what comes first. Nothing here imports from `components/risk/`: a
 * verdict is described by its shape, which the risk engine's worded verdicts already have.
 */

/** An asset as the panel reads it. Everything but the identity is optional, so the store's `AssetInfo` and a page's own rows both fit. */
export interface PickerAsset {
    id: number;
    display_name: string;
    currency: string;
    icon_url?: string | null;
    asset_type?: string | null;
    active?: boolean;
    is_benchmark?: boolean;
    identifier_isin?: string | null;
    identifier_ticker?: string | null;
    identifier_other?: readonly string[] | null;
}

/** Whether an asset may be chosen, and why not: the risk engine's worded verdict, by shape. */
export interface PickerVerdict {
    level: 'eligible' | 'warning' | 'ineligible';
    codes: readonly string[];
    texts: readonly string[];
}

/** A titled group of the list. An asset joins the first section whose `match` accepts it. */
export interface PickerSection {
    key: string;
    label: string;
    match: (asset: PickerAsset) => boolean;
}

/** The criteria the filter menus narrow the list by. */
export interface SelectionFilters {
    /** Empty means "every type": an empty filter is not an empty result. */
    types: readonly string[];
    currencies: readonly string[];
}

/**
 * Apply the filter menus.
 *
 * An empty criterion means *unconstrained*, not *matches nothing*: a list that opens with no filter
 * on must show everything, or it opens blank and the user has to guess why.
 */
export function applyFilters<T extends {asset_type?: string | null; currency: string}>(assets: readonly T[], filters: SelectionFilters): T[] {
    return assets.filter((asset) => {
        // `||`, not `??`: an empty-string type is as unclassified as a null one, and under `??` it
        // would match no criterion at all — an asset that disappears the moment any filter is on.
        if (filters.types.length > 0 && !filters.types.includes(asset.asset_type || 'OTHER')) return false;
        if (filters.currencies.length > 0 && !filters.currencies.includes(asset.currency)) return false;
        return true;
    });
}

/** A text as the multi-choice search compares it: lower case, accents removed. "societe" finds "Société". */
export function foldForSearch(text: string): string {
    return text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

/**
 * The rows of the multi-choice list: the candidates not selected yet whose search text holds
 * **every** word of the query, in the order the caller passed them.
 *
 * Words rather than the whole query, so "etf usd" finds an ETF quoted in dollars whichever way its
 * name is written. An empty query lists every candidate.
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
 * The "select visible" switch.
 *
 * It **unchecks** the visible rows when there is nothing left it could check: every visible row is
 * checked already, or the selection has no room left. Otherwise it checks the visible rows in order,
 * up to `room`. Rows checked under an earlier query stay checked either way: a search narrows what is
 * shown, not what was chosen.
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

/**
 * What a query may find an asset by, besides its name: its codes (P3/A6).
 *
 * `identifier_other` holds alternate codes, such as the non-tradeable "CUM" ISIN of an Italian BTP.
 * Currency and type are deliberately left out: shared by hundreds of rows, any query that is a
 * prefix of one (`eur`, `bon`, `etf`) matched the whole list, and the search looked as if it only
 * began working from the fourth letter. An identifier names an instrument; a currency describes it.
 */
export function assetSearchText(asset: Pick<PickerAsset, 'identifier_isin' | 'identifier_ticker' | 'identifier_other'>): string {
    return [asset.identifier_isin, asset.identifier_ticker, ...(asset.identifier_other ?? [])].filter(Boolean).join(' ');
}

/** `AssetSelect`'s order: active assets first, then by name, with the runtime's own collation. A new array. */
export function assetSelectOrder<T extends {active?: boolean; display_name: string}>(assets: readonly T[]): T[] {
    return [...assets].sort((a, b) => {
        if (a.active !== b.active) return a.active ? -1 : 1;
        return a.display_name.localeCompare(b.display_name);
    });
}

/** Where a dropdown goes, in viewport pixels. */
export interface DropdownPlacement {
    side: 'top' | 'bottom';
    left: number;
    width: number;
    maxHeight: number;
}

/** Room a panel with a search, two filters and a handful of rows is comfortable in: below the trigger whenever this much is left. */
const ENOUGH_ROOM = 420;
/** Kept between the dropdown and the trigger, and between the dropdown and the viewport's edges. */
const GAP = 8;

/**
 * Where to open a dropdown under (or over) its trigger, inside the viewport.
 *
 * - `auto` opens below when the room there is enough, or at least as large as above; above otherwise.
 * - As wide as the trigger, never narrower than `minWidth`, never wider than the viewport less 16 px.
 * - Starts at the trigger's left edge, slid back so it keeps 8 px from both edges: on a phone a narrow
 *   trigger near the right edge still opens a full-width-enough list.
 */
export function dropdownPlacement(trigger: {top: number; bottom: number; left: number; width: number}, viewport: {width: number; height: number}, options: {position: 'top' | 'bottom' | 'auto'; minWidth: number}): DropdownPlacement {
    const below = viewport.height - trigger.bottom - GAP;
    const above = trigger.top - GAP;
    const side = options.position !== 'auto' ? options.position : below >= ENOUGH_ROOM || below >= above ? 'bottom' : 'top';
    const width = Math.min(Math.max(trigger.width, options.minWidth), viewport.width - 2 * GAP);
    const left = Math.max(GAP, Math.min(trigger.left, viewport.width - width - GAP));
    const room = side === 'bottom' ? below : above;
    return {side, left, width, maxHeight: Math.max(room - GAP, 2 * GAP)};
}
