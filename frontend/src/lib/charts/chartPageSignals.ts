/**
 * Signal helpers shared by the chart detail pages (asset and FX).
 *
 * Both pages ask the backend for signal results together with their prices, and decide
 * from the signal configs when a change needs new data. These are the parts of that work
 * which read no page state:
 * - the backend signal results, validated;
 * - the fingerprint of what the signal data depends on;
 * - the peer assets of the comparison signals;
 * - the data sources both pages hand the one renderer of saved signals, `chartSignalRendering.ts` (lot Y-42).
 *
 * The FX detail page still has its own copies of the first three; they come here with FE4.
 *
 * @module charts/chartPageSignals
 */

import {fxPointToLineDataPoint, type FxRatePoint, type SignalDataSources} from '$lib/charts/chartSignalRendering';
import {backendSignalSchemas, type BackendSignalResult} from '$lib/charts/signals/backendTypes';
import type {SignalConfig} from '$lib/charts/signals/ChartSignal';
import {COMPARISON_ASSET_RUNTIME_PARAM_KEYS} from '$lib/charts/loadComparisonData';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

const comparisonRuntimeParamKeys = new Set<string>(COMPARISON_ASSET_RUNTIME_PARAM_KEYS);

/**
 * The backend signal results, each validated against the signal result schema.
 *
 * - A value that is not an array gives no results.
 * - An invalid result throws: the caller treats the whole answer as failed.
 */
export function parseBackendSignalResults(value: unknown): BackendSignalResult[] {
    if (!Array.isArray(value)) return [];
    return value.map((item) => backendSignalSchemas.result.parse(item));
}

/**
 * What the signal data depends on: each config's id, type and params.
 *
 * - It leaves out the runtime params that a comparison load writes back into its config
 *   (`COMPARISON_ASSET_RUNTIME_PARAM_KEYS`), so applying a load does not look like a change.
 * - It is independent of the order of the configs and of their params.
 */
export function signalDataContextFingerprint(configs: SignalConfig[]): string {
    return JSON.stringify(
        configs
            .map((config) => ({
                id: config.id,
                signalType: config.signalType,
                params: Object.fromEntries(
                    Object.entries(config.params)
                        .filter(([key]) => !comparisonRuntimeParamKeys.has(key))
                        .sort(([left], [right]) => left.localeCompare(right)),
                ),
            }))
            .sort((left, right) => left.id.localeCompare(right.id)),
    );
}

/**
 * The distinct peer asset ids of the comparison signals, in ascending order.
 *
 * - Only positive safe integers count.
 * - `excludeAssetId`, the asset the page is showing, is left out.
 */
export function comparisonAssetIds(configs: SignalConfig[], excludeAssetId?: number): number[] {
    return [
        ...new Set(
            configs
                .filter((config) => config.signalType === 'asset-comparison')
                .map((config) => Number(config.params.assetId))
                .filter((assetId) => Number.isSafeInteger(assetId) && assetId > 0 && assetId !== excludeAssetId),
        ),
    ].sort((left, right) => left - right);
}

/** An asset a detail page knows: what names a comparison. */
export interface DetailPageAsset {
    id: number;
    display_name: string;
    icon_url?: string | null;
    asset_type?: string | null;
}

/** What a detail page knows about the series its saved signals read. */
export interface DetailPageSignalSourcesInput {
    /** The page's signal configs: a comparison load writes its target's series into them (`params._resolvedData`). */
    configs: readonly SignalConfig[];
    /** The assets the page knows: a comparison's name, icon and type. */
    assets: readonly DetailPageAsset[];
    /** A pair's points as the FX store holds them, straight. */
    fxPairPoints: (pairSlug: string) => readonly FxRatePoint[];
    /** The asset the page draws (the asset detail page); none on the FX detail page. */
    selfAssetId?: number | null;
}

/**
 * The data sources of a detail page's saved signals, for `renderLocalSignals` (lot Y-42).
 *
 * - An FX pair: the store's points, straight (`fxPointToLineDataPoint(point, false)`); the signal's own `_inverted`
 *   turns them. The store is asked only for the pair a signal names, when it is drawn.
 * - A comparison: the series a comparison load wrote into the first config of that asset that has one, named, with
 *   icon and type, by the assets the page knows; an asset the page does not know gets nulls, so the signal's own
 *   catalogue fallback names it. No base point: a detail page draws daily data.
 *
 * Pure: it reads the configs, the assets and the points it is given, and writes into none of them.
 */
export function detailPageSignalSources(input: DetailPageSignalSourcesInput): SignalDataSources {
    return {
        fxPairData: (pairSlug) => input.fxPairPoints(pairSlug).map((point) => fxPointToLineDataPoint(point, false)),
        comparisonTarget: (assetId) => {
            const loaded = input.configs.find((config) => config.signalType === 'asset-comparison' && Number(config.params.assetId) === assetId && Array.isArray(config.params._resolvedData) && config.params._resolvedData.length > 0);
            if (!loaded) return null;
            const asset = input.assets.find((candidate) => candidate.id === assetId);
            return {
                data: loaded.params._resolvedData as LineDataPoint[],
                displayName: asset?.display_name ?? null,
                iconUrl: asset?.icon_url ?? null,
                assetType: asset?.asset_type ?? null,
            };
        },
        selfAssetId: input.selfAssetId ?? null,
    };
}
