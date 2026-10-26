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
 * the rule can be pinned by a unit test instead of by a page. Every risk surface reads it
 * (`RiskPanelHeader`, `RiskAnalysisPanel`, `AssetSetRiskPanel`), so none keeps a copy that
 * can drift from the others (J-71).
 *
 * The banner rule below (`labQualityAction`) is the one every risk panel reads —
 * the lab, the levels of the Dashboard and of a broker, and the asset detail (TC-23).
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

/** What a data-quality banner action does in a risk panel. */
export type LabQualityAction = {kind: 'sync'} | {kind: 'navigate'; href: string} | {kind: 'add_pair'; pair: string};

/**
 * What a data-quality banner action does in a risk panel: a sync opens the panel's own sync, which
 * refreshes the answer's prices and rates (`buildSyncTargets`); `add_fx_pair` opens the panel's own
 * «add FX pair» dialog on the pair of the chip pressed, or empty when the action names no pair
 * (TC-23, the developer's decision Q-TC23-1 (a): the reader stays on the analysis, as on the
 * Dashboard); the rest navigate. `null` for an action the panel does not know, or a navigation
 * without a target.
 *
 * Any `sync_` action syncs, the two the backend sends today (`sync_asset_prices`,
 * `sync_fx_pair`) and a later one alike: the panel has one sync, and it covers both.
 */
export function labQualityAction(action: string, target: string | null): LabQualityAction | null {
    if (action.startsWith('sync_')) return {kind: 'sync'};
    if (action === 'navigate_asset') return target ? {kind: 'navigate', href: `/assets/${encodeURIComponent(target)}`} : null;
    if (action === 'navigate_fx') return target ? {kind: 'navigate', href: `/fx/${encodeURIComponent(target)}`} : null;
    if (action === 'add_fx_pair') return {kind: 'add_pair', pair: target ?? ''};
    return null;
}

/**
 * The sides the «add FX pair» dialog opens on, for the pair of an `add_pair` action: a slug of
 * exactly two non-empty parts (`EUR-USD`) gives both, kept as written; anything else opens the
 * dialog empty, for the reader to choose.
 */
export function addPairSides(pair: string): {base: string; quote: string} {
    const parts = pair.split('-');
    if (parts.length === 2 && parts[0] && parts[1]) return {base: parts[0], quote: parts[1]};
    return {base: '', quote: ''};
}
