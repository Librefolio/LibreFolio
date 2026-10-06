/**
 * Browsing assets from the detail page: which order the ‹ prev / next › buttons follow.
 *
 * The developer's decision (K step 16, 06/10): the buttons follow the list the user left — its
 * filters, its view (grid or table) and, in the table, its column sort. With no list to follow
 * (direct link, another page, a reload, an asset that list does not hold) they follow every asset
 * in the list's default order.
 *
 * The asset list publishes its order here while it is open: the panels it shows (`AssetBrowseOrder`)
 * and, in the table view, the row order of each panel's table (`AssetTable` → `DataTable`'s
 * `onRowOrderChange`). Memory only: what matters is where the detail page was entered from, which
 * a reload loses anyway. A new client session (logout, another user) empties it.
 */
import {registerClientSessionReset} from '$lib/stores/app/clientSession';
import {matchesAssetLifecycle, orderAssetsByLifecycle} from './assetLifecycle';

export type AssetPanelId = 'own' | 'others' | 'analysis';

/** The list's usage panels, top to bottom. */
export const ASSET_BROWSE_PANEL_ORDER: readonly AssetPanelId[] = ['own', 'others', 'analysis'];

export interface AssetBrowsePosition {
    /** 0-based index of the current asset. */
    index: number;
    total: number;
    previous: number | null;
    next: number | null;
}

interface PublishedList {
    view: 'grid' | 'list';
    panels: Array<{id: AssetPanelId; ids: number[]}>;
}

let published: PublishedList | null = null;
const tableOrders = new Map<AssetPanelId, number[]>();

/** The asset list's panels as shown now, in order, and its view. */
export function publishAssetListOrder(view: 'grid' | 'list', panels: ReadonlyArray<{id: AssetPanelId; ids: readonly number[]}>): void {
    published = {view, panels: panels.map((panel) => ({id: panel.id, ids: [...panel.ids]}))};
}

/** The row order of one panel's table: its column filters and its sort, every page. */
export function publishAssetTableOrder(panel: AssetPanelId, ids: readonly number[]): void {
    tableOrders.set(panel, [...ids]);
}

/** A panel's table is gone: its last order must not outlive it. */
export function clearAssetTableOrder(panel: AssetPanelId): void {
    tableOrders.delete(panel);
}

/** The order the user left the list in, or null if the list never published one. */
export function getAssetListOrder(): number[] | null {
    if (!published) return null;
    const order: number[] = [];
    for (const panel of published.panels) {
        if (panel.ids.length === 0) continue;
        const tableOrder = published.view === 'list' ? tableOrders.get(panel.id) : undefined;
        if (tableOrder) {
            // A column filter can hide rows: what the table does not list is not added back.
            const inPanel = new Set(panel.ids);
            order.push(...tableOrder.filter((id) => inPanel.has(id)));
        } else {
            order.push(...panel.ids);
        }
    }
    return order;
}

export function resetAssetBrowse(): void {
    published = null;
    tableOrders.clear();
}

registerClientSessionReset('assetBrowse', resetAssetBrowse);

// The list page's usage panels, copied: a +page.svelte cannot be imported. `assetBrowse.test.ts`
// keeps this function identical to `assetScope` in `routes/(app)/assets/+page.svelte`. The panels read
// what is held now (`held_by_me`, `held_by_others` from the asset list), not who ever traded.
type AssetScope = 'own' | 'others' | 'analysis';

function assetScope(a: {held_by_me?: boolean; held_by_others?: boolean}): AssetScope {
    if (a.held_by_me) return 'own';
    if (a.held_by_others) return 'others';
    return 'analysis';
}

type BrowseAsset = Parameters<typeof assetScope>[0] & {id: number; active: boolean};

/**
 * Every asset in the order the list shows with no filter: active ones — and inactive ones too when
 * the current asset is inactive, as with the list's "inactive" switch on — panel by panel.
 */
export function defaultAssetBrowseOrder(assets: ReadonlyArray<BrowseAsset>, currentId: number): number[] {
    const current = assets.find((asset) => asset.id === currentId);
    const showInactive = current ? !current.active : false;
    const shown = orderAssetsByLifecycle(assets.filter((asset) => matchesAssetLifecycle(asset.active, true, showInactive)));
    return ASSET_BROWSE_PANEL_ORDER.flatMap((panel) => shown.filter((asset) => assetScope(asset) === panel).map((asset) => asset.id));
}

/** Where `currentId` sits in `order`, or null if it is not there. */
export function browseNeighbours(order: readonly number[], currentId: number): AssetBrowsePosition | null {
    const index = order.indexOf(currentId);
    if (index < 0) return null;
    return {
        index,
        total: order.length,
        previous: index > 0 ? order[index - 1] : null,
        next: index < order.length - 1 ? order[index + 1] : null,
    };
}
