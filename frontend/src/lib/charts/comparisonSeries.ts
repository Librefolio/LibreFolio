/**
 * Where a chart that holds no series of its own finds the ones its saved comparisons draw (lot Y-41).
 *
 * A saved comparison names an asset (`asset-comparison`, `params.assetId`) or an FX pair (`fx-pair`, `params.pairSlug`);
 * the settings store keeps only that name, never the series. The FX list asks no prices and draws daily rates, so a card
 * with an asset comparison reads the asset's daily series from the price cache (`assetPriceStoreRegistry`, shared with
 * the asset detail page: a visit there warms it), and every chart with a pair comparison reads the pair's rates from the
 * FX stores. This module loads what is missing and hands the renderers the shape they read (`SignalDataSources`).
 *
 * The series are in the asset's own currency, as the FX detail page draws them (decision Q-Y41-1 a): in the percentage
 * view the comparison starts at its own first value, and the absolute view puts it on the rates' axis as the detail does.
 *
 * @module charts/comparisonSeries
 */

import {zodiosApi} from '$lib/api';
import {bulkRangeDays, sendBulkBatches} from '$lib/api/bulkBatches';
import type {ComparisonTarget} from '$lib/charts/chartSignalRendering';
import type {SignalConfig} from '$lib/charts/signals';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {apiPricesToAssetPricePoints, getAssetPriceStore} from '$lib/stores/assetPriceStoreRegistry';
import {ensureFxRangeLoaded} from '$lib/stores/fxStoreRegistry';
import {todayIso} from '$lib/utils/dateOnly';

/** An asset a comparison draws, with the currency its series is cached in. */
export interface ComparisonAssetRef {
    id: number;
    currency: string;
}

/** What names an asset on a chart. */
export interface ComparisonAssetNames {
    display_name: string;
    icon_url?: string | null;
    asset_type?: string | null;
}

/**
 * The asset's cached daily series as a comparison target: its points, named, with icon and type. Null while the cache
 * holds none. A backward-filled day carries its staleness, as the cards' own series do.
 */
export function comparisonTargetFromStore(asset: ComparisonAssetRef & ComparisonAssetNames): ComparisonTarget | null {
    const points = getAssetPriceStore(asset.id, asset.currency).getAllSorted();
    if (points.length === 0) return null;
    const data = points.map((point): LineDataPoint => {
        const staleDays = point.backwardFillInfo?.daysBack ?? 0;
        return {date: point.date, value: point.close, ...(staleDays > 0 ? {staleDays} : {})};
    });
    return {data, displayName: asset.display_name, iconUrl: asset.icon_url ?? null, assetType: asset.asset_type ?? null};
}

/**
 * Ask the backend for the assets' daily prices that the cache does not cover over `range`, in one request for all of
 * them (in batches under the backend's caps), and file the answers in the cache. A failed request marks nothing fetched,
 * so a later call asks again; a 404 is final. Never throws.
 */
export async function ensureComparisonSeries(assets: readonly ComparisonAssetRef[], range: {start: string; end: string}): Promise<void> {
    const missing = new Map<number, ComparisonAssetRef>();
    for (const asset of assets) {
        if (missing.has(asset.id)) continue;
        if (getAssetPriceStore(asset.id, asset.currency).getMissingIntervals(range.start, range.end).length > 0) missing.set(asset.id, asset);
    }
    if (missing.size === 0) return;

    const today = todayIso();
    const days = bulkRangeDays(range.start, range.end, today);
    const refs = [...missing.values()];
    const outcome = await sendBulkBatches(
        refs,
        () => days,
        (batch) => zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post(batch.map((asset) => ({asset_id: asset.id, date_range: {start: range.start, end: range.end}, include_price: true, include_events: false}))),
    ).catch(() => null);
    if (!outcome) return;

    for (const {batch, answer} of outcome.answers) {
        const items: unknown[] = Array.isArray((answer as {items?: unknown})?.items) ? (answer as {items: unknown[]}).items : [];
        for (const asset of batch.items) {
            const item = items.find((candidate) => typeof candidate === 'object' && candidate !== null && (candidate as {asset_id?: number}).asset_id === asset.id) as {prices?: unknown[]} | undefined;
            const store = getAssetPriceStore(asset.id, asset.currency);
            const points = apiPricesToAssetPricePoints(Array.isArray(item?.prices) ? item.prices : []);
            if (points.length > 0) store.merge(points);
            // Even an empty answer is an answer: the range is not asked again.
            store.markFetched(range.start, range.end);
        }
    }
    // A request the backend refused as unknown is final for the assets it carried.
    if (outcome.failed && (outcome.error as {response?: {status?: number}})?.response?.status === 404) {
        for (const asset of outcome.failedBatch?.items ?? []) getAssetPriceStore(asset.id, asset.currency).markFetched(range.start, range.end);
    }
}

/**
 * The FX pairs the `fx-pair` signals of `configs` name, once each and in order, without the chart's own pair (`ownSlug`,
 * which the chart loads itself) and without an empty one.
 */
export function fxPairSlugsOf(configs: readonly Pick<SignalConfig, 'signalType' | 'params'>[], ownSlug?: string): string[] {
    const slugs: string[] = [];
    for (const config of configs) {
        if (config.signalType !== 'fx-pair') continue;
        const slug = String(config.params.pairSlug || '');
        if (!slug || slug === ownSlug || slugs.includes(slug)) continue;
        slugs.push(slug);
    }
    return slugs;
}

/**
 * Load into the FX stores the rates of the pairs the `fx-pair` signals name, over `range` (the stores' own gap detection).
 * One pair failing does not stop the others. Never throws. The caller redraws afterwards: the stores are not reactive.
 */
export async function ensureSignalFxPairs(configs: readonly Pick<SignalConfig, 'signalType' | 'params'>[], ownSlug: string | undefined, range: {start: string; end: string}): Promise<void> {
    await Promise.allSettled(fxPairSlugsOf(configs, ownSlug).map((slug) => ensureFxRangeLoaded(slug, range.start, range.end)));
}
