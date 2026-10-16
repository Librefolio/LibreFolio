/**
 * What the asset detail page reads from the bulk price query (`POST /assets/prices/query`).
 *
 * The page asks in one query for its own prices, the calendar-return signal and the
 * comparison peers. These are the parts of reading that answer which use no page state:
 * - the answer parsed with **signal isolation**: an invalid signal result does not throw away
 *   the prices of its item;
 * - the FX conversion error an item reports, if any;
 * - for each comparison peer: its calendar-return problem, its FX failure, and its last
 *   factual view, kept while a refresh reports the peer unavailable.
 *
 * @module components/assets/detail/assetDetailPriceQuery
 */

import {schemas} from '$lib/api';
import {backendSignalSchemas} from '$lib/charts/signals/backendTypes';
import type {SignalConfig} from '$lib/charts/signals/ChartSignal';
import type {SignalInstanceResult} from '$lib/charts/signals/resultMapper';
import {getSignalProblem, type SignalProblem} from '$lib/charts/signals/signalProblem';
import {CALENDAR_RETURN_INSTANCE_ID, isCalendarReturnSignalResult, type CalendarReturnView} from '$lib/components/charts/priceChartHelpers';

/** What the calendar problems need to know about the page: the assets and the currency the chart shows. */
export interface CalendarComparisonContext {
    readonly assets: ReadonlyArray<{id: number; currency?: string | null}>;
    readonly displayCurrency: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function responseItemFor(responseItems: unknown[], assetId: number): Record<string, unknown> | undefined {
    return responseItems.find((candidate): candidate is Record<string, unknown> => isRecord(candidate) && candidate.asset_id === assetId);
}

/**
 * The answer of the bulk price query, item by item.
 *
 * - Each item is validated as `FAPriceQueryResult` with only its valid signal results.
 * - It is returned with its **raw** `signals`, so the caller can still report the invalid ones.
 * - A missing `items` is an empty answer.
 * - It throws when the answer, its `items`, an item or an item's signal collection is malformed.
 */
export function parseAssetPriceQueryWithSignalIsolation(data: unknown): {items: Record<string, unknown>[]} {
    if (!isRecord(data)) {
        throw new Error('Invalid Asset price query response');
    }
    if (data.items === undefined) return {items: []};
    if (!Array.isArray(data.items)) {
        throw new Error('Invalid Asset price query items');
    }

    return {
        items: data.items.map((rawItem, index) => {
            if (!isRecord(rawItem)) {
                throw new Error(`Invalid Asset price query item at index ${index}`);
            }
            const rawSignals = rawItem.signals;
            if (rawSignals !== undefined && !Array.isArray(rawSignals)) {
                throw new Error(`Invalid Asset signal collection at item index ${index}`);
            }
            const validSignals = (rawSignals ?? []).flatMap((signal) => {
                const parsed = backendSignalSchemas.result.safeParse(signal);
                return parsed.success ? [parsed.data] : [];
            });
            const parsedItem = schemas.FAPriceQueryResult.safeParse({
                ...rawItem,
                signals: validSignals,
            });
            if (!parsedItem.success) {
                throw new Error(`Invalid Asset price query item at index ${index}`);
            }
            return {
                ...parsedItem.data,
                signals: rawSignals ?? [],
            };
        }),
    };
}

/**
 * The FX conversion error of a price query item: its first error, if that one is about a
 * conversion and not about an event.
 */
export function priceConversionErrorFromItem(item: Record<string, unknown> | undefined): string | undefined {
    const errors = item && Array.isArray(item.errors) ? item.errors.filter((error): error is string => typeof error === 'string') : [];
    const firstError = errors[0];
    return firstError && !/\bfor event on\b/i.test(firstError) && /\b(?:fx|conversion|currenc)/i.test(firstError) ? firstError : undefined;
}

/**
 * The calendar-return problem of each comparison peer, keyed by asset id. Peers with no problem
 * are absent.
 *
 * - A peer with no comparison config is skipped.
 * - A result that is missing or invalid is a `missing` instance.
 * - So is a result that does not fail while the strict view says `error`.
 * - A `missing_input_fields` problem becomes `fx_conversion_unavailable`, with the item's
 *   conversion error as its message, when the peer's currency differs from the one shown.
 */
export function calendarComparisonProblemsFromResponse(responseItems: unknown[], configs: SignalConfig[], assetIds: number[], views: ReadonlyMap<number, CalendarReturnView>, context: CalendarComparisonContext): Map<number, SignalProblem> {
    const configByAssetId = new Map<number, SignalConfig>();
    for (const config of configs) {
        if (config.signalType !== 'asset-comparison') continue;
        const assetId = Number(config.params.assetId);
        if (Number.isSafeInteger(assetId) && assetId > 0) configByAssetId.set(assetId, config);
    }
    const problems = new Map<number, SignalProblem>();

    for (const assetId of assetIds) {
        const config = configByAssetId.get(assetId);
        if (!config) continue;
        const item = responseItemFor(responseItems, assetId);
        const rawResults: unknown[] = item && Array.isArray(item.signals) ? item.signals : [];
        const rawResult = rawResults.find((candidate) => isCalendarReturnSignalResult(candidate, CALENDAR_RETURN_INSTANCE_ID));
        let instance: SignalInstanceResult;

        if (!rawResult) {
            instance = {
                config,
                source: 'backend',
                status: 'missing',
                result: null,
                error: `Calendar Return result for asset ${assetId} is missing`,
            };
        } else {
            const parsed = backendSignalSchemas.result.safeParse(rawResult);
            if (!parsed.success) {
                instance = {
                    config,
                    source: 'backend',
                    status: 'missing',
                    result: null,
                    error: `Calendar Return result for asset ${assetId} is invalid`,
                };
            } else {
                const result = parsed.data;
                const strictView = views.get(assetId);
                if (strictView?.state === 'error' && result.status !== 'failed') {
                    instance = {
                        config,
                        source: 'backend',
                        status: 'missing',
                        result: null,
                        error: `Calendar Return result for asset ${assetId} is invalid`,
                    };
                } else {
                    const resultError = Array.isArray(result.error) ? result.error.find((error) => error !== null)?.message : result.error?.message;
                    instance = {
                        config,
                        source: 'backend',
                        status: result.status,
                        result,
                        error: resultError ?? null,
                    };
                }
            }
        }

        let problem = getSignalProblem(instance);
        const priceConversionError = priceConversionErrorFromItem(item);
        const targetAsset = context.assets.find((asset) => asset.id === assetId);
        if (problem?.code === 'missing_input_fields' && priceConversionError && targetAsset?.currency && context.displayCurrency && targetAsset.currency !== context.displayCurrency) {
            problem = {
                ...problem,
                code: 'fx_conversion_unavailable',
                message: priceConversionError,
            };
        }
        if (problem) problems.set(assetId, problem);
    }
    return problems;
}

/**
 * The comparison peers whose conversion failed in this answer.
 *
 * A peer absent from the answer keeps the outcome it had before (`previousFailures`).
 */
export function calendarComparisonFxFailuresFromResponse(responseItems: unknown[], assetIds: number[], previousFailures: ReadonlySet<number>): Set<number> {
    const failedAssetIds = new Set<number>();
    for (const assetId of assetIds) {
        const item = responseItemFor(responseItems, assetId);
        if (!item) {
            if (previousFailures.has(assetId)) failedAssetIds.add(assetId);
            continue;
        }
        if (priceConversionErrorFromItem(item)) failedAssetIds.add(assetId);
    }
    return failedAssetIds;
}

/**
 * The next calendar views of the peers, except that a peer the refresh reports `unavailable`
 * keeps its previous view. This happens only when that view was `ready` or `partial` with at
 * least one factual point, and the peer is in the answer.
 */
export function preserveFactualCalendarPeersForCurrentUnavailable(previousViews: ReadonlyMap<number, CalendarReturnView>, nextViews: ReadonlyMap<number, CalendarReturnView>, responseItems: unknown[], assetIds: number[]): Map<number, CalendarReturnView> {
    const merged = new Map(nextViews);
    for (const assetId of assetIds) {
        const itemPresent = responseItems.some((candidate) => isRecord(candidate) && candidate.asset_id === assetId);
        const next = nextViews.get(assetId);
        const previous = previousViews.get(assetId);
        const previousHasFacts = previous && ['ready', 'partial'].includes(previous.state) && previous.points.some((point) => !point.missing);
        if (itemPresent && next?.state === 'unavailable' && previousHasFacts) {
            merged.set(assetId, previous);
        }
    }
    return merged;
}
