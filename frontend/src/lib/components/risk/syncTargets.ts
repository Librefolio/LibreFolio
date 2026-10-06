/**
 * syncTargets — what a risk answer's "sync" button has to refresh.
 *
 * An answer about a set of assets rests on two kinds of data: each asset's
 * prices, and — for every asset quoted in a currency other than the one the
 * answer is expressed in — the exchange rate that converts it. Syncing only the
 * prices leaves a converted series standing on stale rates, which is exactly the
 * loss R2-128 recorded when the legacy panel left Asset Global: the page kept a
 * prices-only sync and lost the only entry point that refreshed both.
 *
 * Pure on purpose: the lookup and the set of configured pairs are passed in, so
 * the rule can be pinned by a unit test instead of by a page. It is the same rule
 * `RiskPanelHeader` applies inline, lifted so a second surface does not become a
 * second copy that can drift from the first.
 */

/** The asset fields the sync modal and the pair rule read. */
export interface SyncAssetInfo {
    id: number;
    display_name: string;
    currency: string;
    icon_url?: string | null;
    asset_type?: string | null;
    provider_code?: string | null;
}

export interface SyncTargets {
    /** Known assets, deduplicated, in ascending id order. */
    assets: SyncAssetInfo[];
    /** Configured pair slugs (`EUR-USD`), deduplicated and sorted. */
    fxPairs: string[];
}

/**
 * The assets and exchange-rate pairs behind an answer about `assetIds`.
 *
 * - An id the lookup does not know is skipped: it has nothing to sync.
 * - A pair is proposed only when it is **configured** (`configuredPairs`): an
 *   unconfigured pair has no route to fetch, so offering it would promise a sync
 *   that cannot happen.
 * - An asset already quoted in `targetCurrency` needs no conversion, so no pair.
 */
export function buildSyncTargets(assetIds: readonly number[], targetCurrency: string, lookup: (assetId: number) => SyncAssetInfo | null | undefined, configuredPairs: ReadonlySet<string>): SyncTargets {
    const assets = [...new Set(assetIds)]
        .sort((left, right) => left - right)
        .map((assetId) => lookup(assetId))
        .filter((asset): asset is SyncAssetInfo => Boolean(asset))
        .map((asset) => ({
            id: asset.id,
            display_name: asset.display_name,
            currency: asset.currency,
            icon_url: asset.icon_url,
            asset_type: asset.asset_type,
            provider_code: asset.provider_code,
        }));

    const pairs = new Set<string>();
    for (const asset of assets) {
        if (asset.currency === targetCurrency) continue;
        const slug = [asset.currency, targetCurrency].sort().join('-');
        if (configuredPairs.has(slug)) pairs.add(slug);
    }

    return {assets, fxPairs: [...pairs].sort()};
}

/** What a data-quality banner action does in the lab. */
export type LabQualityAction = {kind: 'sync'} | {kind: 'navigate'; href: string};

/**
 * What a data-quality banner action does in the lab: a sync opens the lab's own sync, which
 * refreshes the selection's prices and rates (`buildSyncTargets`); the rest navigate, as on the
 * Dashboard. `null` for an action the lab does not know, or a navigation without a target.
 *
 * Any `sync_` action syncs, the two the backend sends today (`sync_asset_prices`,
 * `sync_fx_pair`) and a later one alike: the lab has one sync, and it covers both.
 */
export function labQualityAction(action: string, target: string | null): LabQualityAction | null {
    if (action.startsWith('sync_')) return {kind: 'sync'};
    if (action === 'navigate_asset') return target ? {kind: 'navigate', href: `/assets/${encodeURIComponent(target)}`} : null;
    if (action === 'navigate_fx') return target ? {kind: 'navigate', href: `/fx/${encodeURIComponent(target)}`} : null;
    if (action === 'add_fx_pair') return {kind: 'navigate', href: '/fx'};
    return null;
}
