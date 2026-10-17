/**
 * Signal helpers shared by the chart detail pages (asset and FX).
 *
 * Both pages ask the backend for signal results together with their prices, and decide
 * from the signal configs when a change needs new data. These are the parts of that work
 * which read no page state:
 * - the backend signal results, validated;
 * - the fingerprint of what the signal data depends on;
 * - the peer assets of the comparison signals.
 *
 * The FX detail page still has its own copies of all three; they come here with FE4.
 *
 * @module charts/chartPageSignals
 */

import {backendSignalSchemas, type BackendSignalResult} from '$lib/charts/signals/backendTypes';
import type {SignalConfig} from '$lib/charts/signals/ChartSignal';
import {COMPARISON_ASSET_RUNTIME_PARAM_KEYS} from '$lib/charts/loadComparisonData';

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
