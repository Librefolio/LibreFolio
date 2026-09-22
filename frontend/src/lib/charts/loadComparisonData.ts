/**
 * Shared utility for loading comparison asset data (prices + events).
 *
 * Used by both asset detail and FX detail pages to avoid duplication.
 * Fetches price data and events for asset-comparison signals without mutating
 * caller-owned state. Callers apply the returned runtime data only after their
 * request-generation guard confirms the response is still current.
 *
 * @module charts/loadComparisonData
 */

import {zodiosApi} from '$lib/api';
import type {SignalConfig} from '$lib/charts/signals';
import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {addDays, todayIso} from '$lib/utils/dateOnly';

export interface ComparisonAssetMeta {
    id: number;
    display_name: string;
    icon_url?: string | null;
    asset_type?: string | null;
    currency?: string;
}

export interface ComparisonAssetLoadItem {
    readonly assetId: number;
    readonly runtimeParams: Readonly<Record<string, unknown>>;
    readonly events: readonly any[];
}

export interface ComparisonAssetsLoadResult {
    readonly items: readonly ComparisonAssetLoadItem[];
}

export interface ComparisonSyncRange {
    start: string;
    end: string;
}

const COMPARISON_SYNC_PADDING_DAYS = 7;

function subtractCalendarDaysOrMin(start: string, days: number): string {
    if (start === 'min') return start;
    try {
        return addDays(start, -days);
    } catch (error) {
        if (error instanceof RangeError) return 'min';
        throw error;
    }
}

export function buildComparisonSyncRange(
    selectedRange: ComparisonSyncRange,
    options: {
        calendarLookbackDays?: number;
        today?: string;
    } = {},
): ComparisonSyncRange {
    const calendarLookbackDays = options.calendarLookbackDays ?? 0;
    if (!Number.isSafeInteger(calendarLookbackDays) || calendarLookbackDays < 0) {
        throw new RangeError('calendarLookbackDays must be a non-negative safe integer');
    }

    const today = options.today ?? todayIso();
    const requiredStart = subtractCalendarDaysOrMin(selectedRange.start, calendarLookbackDays);
    const paddedStart = subtractCalendarDaysOrMin(requiredStart, COMPARISON_SYNC_PADDING_DAYS);
    const end = selectedRange.end === 'max' || selectedRange.end >= today ? today : addDays(selectedRange.end, COMPARISON_SYNC_PADDING_DAYS);
    const cappedEnd = end > today ? today : end;
    return {
        start: paddedStart !== 'min' && paddedStart > cappedEnd ? cappedEnd : paddedStart,
        end: cappedEnd,
    };
}

export const COMPARISON_ASSET_RUNTIME_PARAM_KEYS = ['_resolvedData', '_conversionFailed', '_conversionError', '_assetCurrency', '_targetCurrency', '_assetIconUrl', '_assetType', '_assetDisplayName'] as const;

export function clearComparisonAssetRuntimeParams(params: Record<string, unknown>): void {
    for (const key of COMPARISON_ASSET_RUNTIME_PARAM_KEYS) {
        delete params[key];
    }
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function moneyCurrency(value: unknown): string | null {
    if (!isRecord(value) || typeof value.code !== 'string') return null;
    const code = value.code.trim().toUpperCase();
    return code || null;
}

export interface ComparisonEventFxDependency {
    sourceCurrency: string;
    failed: boolean;
}

export function getComparisonEventFxDependency(event: unknown, targetCurrency: string): ComparisonEventFxDependency | null {
    if (!isRecord(event)) return null;
    const target = targetCurrency.trim().toUpperCase();
    if (!target) return null;
    const currentCurrency = moneyCurrency(event.value);
    const originalCurrency = moneyCurrency(event.original_value);
    const sourceCurrency = originalCurrency && originalCurrency !== target ? originalCurrency : currentCurrency && currentCurrency !== target ? currentCurrency : null;
    if (!sourceCurrency) return null;
    return {
        sourceCurrency,
        failed: currentCurrency !== target,
    };
}

export function collectConfiguredComparisonFxSlugs(assetCurrency: string | undefined, targetCurrency: string, events: readonly unknown[], configuredSlugs: readonly string[]): string[] {
    const target = targetCurrency.trim().toUpperCase();
    if (!target) return [];
    const configured = new Set(configuredSlugs);
    const required = new Set<string>();
    const addPair = (sourceCurrency: string | undefined) => {
        const source = sourceCurrency?.trim().toUpperCase();
        if (!source || source === target) return;
        const slug = [source, target].sort((left, right) => left.localeCompare(right)).join('-');
        if (configured.has(slug)) required.add(slug);
    };
    addPair(assetCurrency);
    for (const event of events) {
        addPair(getComparisonEventFxDependency(event, target)?.sourceCurrency);
    }
    return [...required].sort((left, right) => left.localeCompare(right));
}

/**
 * Load comparison asset data (prices + events) for the given signals.
 *
 * @param assetIds - Comparison asset IDs
 * @param dateRange - Start/end date range for the query
 * @param allAssets - Full asset list (for metadata lookup)
 * @param excludeAssetId - Asset ID to exclude from loading (the page's own asset)
 * @param targetCurrency - Target currency for FX conversion (when display currency differs from asset native)
 * @returns Immutable runtime data keyed by asset ID
 */
export async function loadComparisonAssetsData(assetIds: readonly number[], dateRange: {start: string; end: string}, allAssets: ComparisonAssetMeta[], excludeAssetId?: number, targetCurrency?: string): Promise<ComparisonAssetsLoadResult> {
    const idsToLoad = [...new Set(assetIds.filter((id) => Number.isSafeInteger(id) && id > 0 && id !== excludeAssetId))];
    if (idsToLoad.length === 0) return {items: []};

    const queries = idsToLoad.map((id) => ({
        asset_id: id,
        date_range: {start: dateRange.start, end: dateRange.end},
        include_events: true,
        target_currency: targetCurrency || undefined,
    }));
    const response = await zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post(queries);
    const responseItems = isRecord(response) && Array.isArray(response.items) ? response.items.filter(isRecord) : [];
    const resultByAssetId = new Map(responseItems.flatMap((item) => (typeof item.asset_id === 'number' ? [[item.asset_id, item] as const] : [])));

    const items = idsToLoad.map((assetId): ComparisonAssetLoadItem => {
        const result = resultByAssetId.get(assetId);
        const errors = result && Array.isArray(result.errors) ? result.errors.filter((error): error is string => typeof error === 'string') : [];
        const assetMeta = allAssets.find((a) => a.id === assetId);

        // Map backend price points to LineDataPoint format.
        // When targetCurrency was requested, exclude points where conversion
        // failed (p.currency !== targetCurrency) to avoid mixing currencies
        // on the chart (staircase effect).
        const rawPrices = result && Array.isArray(result.prices) ? result.prices.filter(isRecord) : [];
        const hasPriceConversionError = Boolean(targetCurrency && rawPrices.some((point) => point.currency !== targetCurrency));
        const prices = rawPrices
            .filter((point) => {
                if (!targetCurrency) return true; // no conversion requested — keep all
                // Keep point only if already in target currency
                // (either converted, or native = target)
                return point.currency === targetCurrency;
            })
            .map((point) => ({
                date: point.date,
                value: Number(point.close ?? 0),
                originalValue: point.original_close != null ? Number(point.original_close) : undefined,
                originalCurrency: point.original_currency ?? undefined,
                originalCurrencyFlag: typeof point.original_currency === 'string' ? getCurrencyInfo(point.original_currency).flag_emoji : undefined,
            }));

        return {
            assetId,
            runtimeParams: {
                _resolvedData: prices.length > 0 ? prices : undefined,
                _assetIconUrl: assetMeta?.icon_url ?? null,
                _assetType: assetMeta?.asset_type ?? null,
                _assetCurrency: assetMeta?.currency ?? undefined,
                _targetCurrency: targetCurrency ?? undefined,
                _conversionFailed: hasPriceConversionError,
                _conversionError: hasPriceConversionError ? errors[0] : undefined,
            },
            events: result && Array.isArray(result.events) ? [...result.events] : [],
        };
    });

    return {items};
}

export function applyComparisonAssetsData(compSignals: SignalConfig[], loaded: ComparisonAssetsLoadResult): Map<number, any[]> {
    const loadedByAssetId = new Map(loaded.items.map((item) => [item.assetId, item]));
    const events = new Map<number, any[]>();

    for (const config of compSignals) {
        const assetId = Number(config.params.assetId);
        const item = loadedByAssetId.get(assetId);
        if (!item) continue;
        clearComparisonAssetRuntimeParams(config.params);
        Object.assign(config.params, item.runtimeParams);
        events.set(assetId, [...item.events]);
    }

    return events;
}

export function clearComparisonAssetsData(compSignals: SignalConfig[]): Map<number, any[]> {
    for (const config of compSignals) {
        clearComparisonAssetRuntimeParams(config.params);
    }
    return new Map();
}
