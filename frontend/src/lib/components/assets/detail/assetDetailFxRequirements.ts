/**
 * The FX pairs the asset detail page needs, and the data-quality issues it shows.
 *
 * The page needs a pair for each currency it converts to the one shown:
 * - the asset's own currency;
 * - each comparison peer's currency;
 * - the currency of each event (dividends, cash events), the asset's own or a peer's.
 *
 * Each pair has a status. The issues of the page's data-quality banner are the pairs that are not
 * `ok`, an archived asset, and a range that starts before the first price.
 *
 * The page passes its state as an object of **getters**. These functions read it in the same order
 * and under the same conditions as the page's former `$derived` blocks, so a `$derived` over them
 * depends on exactly the same state: for example, on the chart data only while the main pair has
 * no converted date yet.
 *
 * @module components/assets/detail/assetDetailFxRequirements
 */

import {getComparisonEventFxDependency} from '$lib/charts/loadComparisonData';
import type {SignalConfig, SignalProblem} from '$lib/charts/signals';
import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';

/** A pair the page needs: its slug and label, the asset it serves, and its status. */
export interface RequiredFxPairInfo {
    slug: string;
    label: string;
    forAsset: string;
    forAssetIconUrl?: string | null;
    forAssetType?: string | null;
    status: 'ok' | 'missing' | 'no-data' | 'partial-gap';
    firstDate?: string;
}

interface FxRequirementAsset {
    display_name: string;
    icon_url?: string | null;
    asset_type?: string | null;
}

/** The page state the required pairs depend on. */
export interface RequiredFxPairsInput {
    readonly displayCurrency: string;
    /** The asset the page shows, once loaded. */
    readonly asset: (FxRequirementAsset & {currency: string}) | null;
    readonly pageAssetId: number;
    /** The slugs of the pairs configured on the instance. */
    readonly configuredFxSlugs: readonly string[];
    /** The first date the main pair converts, if any. */
    readonly fxFirstConvertedDate: string | null;
    readonly hasChartData: boolean;
    /** The main pair starts after the first price. */
    readonly hasFxDataGap: boolean;
    readonly signals: readonly SignalConfig[];
    /** Every asset the user has, for the comparison peers. */
    readonly assets: ReadonlyArray<FxRequirementAsset & {id: number; currency?: string}>;
    readonly primaryMode: string;
    readonly calendarSnapshotIsCurrent: boolean;
    readonly calendarComparisonFxFailures: ReadonlySet<number>;
    readonly calendarComparisonProblems: ReadonlyMap<number, SignalProblem>;
    readonly events: readonly unknown[];
    readonly comparisonEvents: ReadonlyMap<number, readonly unknown[]>;
    /** «for dividend/cash events», translated. */
    readonly eventsLabel: string;
    /** The name of a peer that is not among `assets`, translated. */
    assetFallbackLabel(assetId: number): string;
}

/** The page state the data-quality issues depend on. */
export interface AssetDetailIssuesInput {
    readonly asset: {active?: boolean | null} | null;
    readonly rangeStartsBeforeData: boolean;
    readonly loading: boolean;
    readonly error: string | null;
    readonly firstDataDate: string | null;
    readonly requiredFxPairs: readonly RequiredFxPairInfo[];
}

/**
 * The FX pairs the page needs, in this order: the asset's own pair, the comparison peers' pairs,
 * then the event currencies' pairs. A slug appears once.
 *
 * - **The asset's pair**: `missing` when it is not configured; `no-data` when nothing converts yet
 *   while there are prices; `partial-gap` when conversion starts after the first price; `ok`
 *   otherwise.
 * - **A peer's pair**: `missing` when it is not configured. In the calendar view (when its snapshot
 *   is current), `no-data` when the peer's conversion failed. In the price view, `no-data` when its
 *   conversion failed or it has no data. `ok` otherwise.
 * - **An event's pair** that is already listed can only get worse: `missing` if it is not
 *   configured, and `ok` becomes `no-data` when the event's conversion failed.
 */
export function buildRequiredFxPairs(input: RequiredFxPairsInput): RequiredFxPairInfo[] {
    if (!input.displayCurrency) return [];
    const pairs: RequiredFxPairInfo[] = [];
    const seenSlugs = new Set<string>();

    // Helper to compute canonical slug
    const toSlug = (a: string, b: string) => {
        const [lo, hi] = a < b ? [a, b] : [b, a];
        return `${lo}-${hi}`;
    };

    // Main asset FX pair
    const asset = input.asset;
    if (asset && input.displayCurrency !== asset.currency) {
        const slug = toSlug(asset.currency, input.displayCurrency);
        const missing = !input.configuredFxSlugs.includes(slug);
        let status: RequiredFxPairInfo['status'];
        if (missing) {
            status = 'missing';
        } else if (!input.fxFirstConvertedDate && input.hasChartData) {
            status = 'no-data';
        } else if (input.hasFxDataGap && input.fxFirstConvertedDate) {
            status = 'partial-gap';
        } else {
            status = 'ok';
        }
        pairs.push({
            slug,
            label: slug.replace('-', '/'),
            forAsset: asset.display_name,
            forAssetIconUrl: asset.icon_url,
            forAssetType: asset.asset_type,
            status,
            firstDate: input.fxFirstConvertedDate ?? undefined,
        });
        seenSlugs.add(slug);
    }

    // Comparison signal FX pairs
    for (const cfg of input.signals) {
        if (cfg.signalType !== 'asset-comparison') continue;
        const targetId = Number(cfg.params.assetId);
        if (!targetId || targetId === input.pageAssetId) continue;
        const targetAsset = input.assets.find((a) => a.id === targetId);
        if (!targetAsset?.currency || targetAsset.currency === input.displayCurrency) continue;
        const slug = toSlug(targetAsset.currency, input.displayCurrency);
        if (seenSlugs.has(slug)) continue;
        seenSlugs.add(slug);

        const missing = !input.configuredFxSlugs.includes(slug);
        let status: RequiredFxPairInfo['status'];
        if (missing) {
            status = 'missing';
        } else if (input.primaryMode === 'calendar-return' && input.calendarSnapshotIsCurrent) {
            status = input.calendarComparisonFxFailures.has(targetId) || input.calendarComparisonProblems.get(targetId)?.code === 'fx_conversion_unavailable' ? 'no-data' : 'ok';
        } else {
            const convFailed = Boolean(cfg.params._conversionFailed);
            const hasData = Boolean(cfg.params._resolvedData);
            status = convFailed || !hasData ? 'no-data' : 'ok';
        }
        pairs.push({
            slug,
            label: slug.replace('-', '/'),
            forAsset: targetAsset.display_name,
            forAssetIconUrl: targetAsset.icon_url,
            forAssetType: targetAsset.asset_type,
            status,
        });
    }

    // E.8 — Event currencies: if any event is in a currency ≠ displayCurrency,
    // add its pair to the required list. This surfaces the same banner + CTA
    // already used for prices (asset native + comparison signals), without
    // duplicating detection code. `forAsset` uses an i18n-aware "for events"
    // label so the user understands the context.
    if (input.displayCurrency) {
        const eventSources: Array<{
            values: readonly unknown[];
            forAsset: string;
            forAssetIconUrl?: string | null;
            forAssetType?: string | null;
        }> = [
            {
                values: input.events,
                forAsset: input.eventsLabel,
            },
            ...[...input.comparisonEvents].map(([assetId, values]) => {
                const peer = input.assets.find((candidate) => candidate.id === assetId);
                return {
                    values,
                    forAsset: peer?.display_name ?? input.assetFallbackLabel(assetId),
                    forAssetIconUrl: peer?.icon_url,
                    forAssetType: peer?.asset_type,
                };
            }),
        ];
        for (const source of eventSources) {
            for (const event of source.values) {
                const dependency = getComparisonEventFxDependency(event, input.displayCurrency);
                if (!dependency) continue;
                const slug = toSlug(dependency.sourceCurrency, input.displayCurrency);
                const missing = !input.configuredFxSlugs.includes(slug);
                const existing = pairs.find((pair) => pair.slug === slug);
                if (existing) {
                    if (missing) existing.status = 'missing';
                    else if (dependency.failed && existing.status === 'ok') existing.status = 'no-data';
                    continue;
                }
                seenSlugs.add(slug);
                pairs.push({
                    slug,
                    label: slug.replace('-', '/'),
                    forAsset: source.forAsset,
                    forAssetIconUrl: source.forAssetIconUrl,
                    forAssetType: source.forAssetType,
                    status: missing ? 'missing' : dependency.failed ? 'no-data' : 'ok',
                });
            }
        }
    }

    return pairs;
}

/**
 * The issues of the page's data-quality banner, in this order:
 * - the asset is archived;
 * - the range starts before the first price (once loaded, without errors);
 * - one issue per pair that is not `ok` (once loaded, without errors): a missing pair offers to add
 *   it, and a pair with no data or a gap links to the pair's page.
 */
export function buildAssetDetailIssues(input: AssetDetailIssuesInput): DataQualityIssue[] {
    const issues: DataQualityIssue[] = [];

    // Archived banner
    if (input.asset && input.asset.active === false) {
        issues.push({
            domain: 'asset',
            code: 'ASSET_ARCHIVED',
            severity: 'warning',
            message_i18n_key: 'dataQuality.archivedAsset',
        });
    }

    // Range starts before first data
    if (input.rangeStartsBeforeData && !input.loading && !input.error && input.asset) {
        issues.push({
            domain: 'asset',
            code: 'RANGE_BEFORE_FIRST_DATA',
            severity: 'info',
            message_i18n_key: 'dataQuality.rangeBeforeData',
            message_params: {date: input.firstDataDate ?? ''},
        });
    }

    // FX pair issues
    if (!input.loading && !input.error) {
        for (const pair of input.requiredFxPairs.filter((p) => p.status !== 'ok')) {
            if (pair.status === 'missing') {
                issues.push({
                    domain: 'forex',
                    code: 'FX_PAIR_MISSING',
                    severity: 'warning',
                    group_key: pair.slug,
                    message_i18n_key: 'dataQuality.fxPairMissing',
                    affected_fx_pairs: [pair.slug],
                    affected_asset_names: [pair.forAsset],
                    cta_action: 'add_fx_pair',
                    cta_target: pair.slug,
                });
            } else if (pair.status === 'no-data') {
                issues.push({
                    domain: 'forex',
                    code: 'FX_PAIR_NO_DATA',
                    severity: 'warning',
                    group_key: pair.slug,
                    message_i18n_key: 'dataQuality.fxPairNoData',
                    affected_fx_pairs: [pair.slug],
                    affected_asset_names: [pair.forAsset],
                    cta_action: 'navigate_fx',
                    cta_target: pair.slug,
                });
            } else if (pair.status === 'partial-gap') {
                issues.push({
                    domain: 'forex',
                    code: 'FX_PAIR_PARTIAL_GAP',
                    severity: 'info',
                    group_key: pair.slug,
                    message_i18n_key: 'dataQuality.fxPairPartialGap',
                    message_params: {date: pair.firstDate ?? ''},
                    affected_fx_pairs: [pair.slug],
                    affected_asset_names: [pair.forAsset],
                    cta_action: 'navigate_fx',
                    cta_target: pair.slug,
                });
            }
        }
    }

    return issues;
}
