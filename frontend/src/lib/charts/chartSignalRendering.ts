/**
 * The one renderer of a chart's saved signals (lot Y-39a).
 *
 * A chart draws its saved local signals by rebuilding each one from its config, giving the signals that read another
 * series their data, and rendering it on the chart's own data; then it draws the backend results of its backend signals.
 * The asset and FX cards and the Chart Settings preview do it here, with the same data sources: what a card shows and
 * what its preview shows are the same signals by construction.
 *
 * Pure: no Svelte state, no store read. The caller passes where the data comes from (`SignalDataSources`), so a detail
 * page can adopt the same functions (backlog Y-42).
 *
 * @module charts/chartSignalRendering
 */

import {signalFromConfig, type RenderedSignal, type SignalConfig, type SignalDefinition} from '$lib/charts/signals';
import {renderBackendSignalResult} from '$lib/charts/signals/backendRenderer';
import type {SignalInstanceResult} from '$lib/charts/signals/resultMapper';
import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
import {displayFxRate} from '$lib/stores/fxStoreRegistry';
import {extractDaysBack} from '$lib/utils/assetPriceDerived';

type ViewMode = 'absolute' | 'percentage';

/** An FX store point (`FxDataPoint`), as far as the chart reads it. */
export interface FxRatePoint {
    date: string;
    rate: number | null;
    backwardFillInfo?: {actualRateDate?: string; daysBack?: number} | null;
}

/** The other asset a comparison signal draws. */
export interface ComparisonTarget {
    /** Its series, absolute. */
    data: LineDataPoint[];
    /** Absent: the signal's own catalogue fallback names it. */
    displayName?: string | null;
    iconUrl?: string | null;
    assetType?: string | null;
    /** Its point on the day the comparison starts: the percentage base (lot Z-29d-0). */
    basePoint?: LineDataPoint | null;
}

/** Where a chart's local signals get the series they read. */
export interface SignalDataSources {
    /** A pair's rates, straight: the signal's own `_inverted` turns them. Null or empty: the pair is not drawn. */
    fxPairData: (pairSlug: string) => LineDataPoint[] | null;
    /** A comparison's target. Null: this chart cannot draw it. */
    comparisonTarget: (assetId: number) => ComparisonTarget | null;
    /** The asset the chart draws: a comparison with it is never drawn. */
    selfAssetId?: number | null;
}

/** No series to read: FX pair and comparison signals are not drawn, the others are. */
export const NO_SIGNAL_SOURCES: SignalDataSources = {fxPairData: () => null, comparisonTarget: () => null};

/** An FX store point as a chart point: the rate the way the chart shows the pair, a gap without one, its staleness. */
export function fxPointToLineDataPoint(point: FxRatePoint, inverted: boolean): LineDataPoint {
    const rate = displayFxRate(point.rate, inverted);
    return {
        date: point.date,
        value: rate ?? 0,
        missing: rate === null,
        staleDays: extractDaysBack(point),
    };
}

/**
 * One saved local signal, drawn on `baseData`: nothing when its type is unknown, or when the series it reads is missing.
 * The signal is rebuilt from `config` and given its data; `config` itself is never written into.
 */
export function renderLocalSignal(config: SignalConfig, baseData: LineDataPoint[], viewMode: ViewMode, sources: SignalDataSources): RenderedSignal[] {
    const instance = signalFromConfig(config);
    if (!instance) return [];

    if (config.signalType === 'fx-pair') {
        const pairSlug = String(config.params.pairSlug || '');
        if (!pairSlug) return [];
        const data = sources.fxPairData(pairSlug);
        if (!data?.length) return [];
        instance.params._resolvedData = data;
    }

    if (config.signalType === 'asset-comparison') {
        const assetId = Number(config.params.assetId);
        if (!assetId || assetId === sources.selfAssetId) return [];
        const target = sources.comparisonTarget(assetId);
        if (!target?.data.length) return [];
        instance.params._resolvedData = target.data;
        // Only what the target gives: a name, an icon or a type the saved config carries stays otherwise.
        if (target.displayName != null) instance.params._assetDisplayName = target.displayName;
        if (target.iconUrl != null) instance.params._assetIconUrl = target.iconUrl;
        if (target.assetType != null) instance.params._assetType = target.assetType;
        if (target.basePoint != null) instance.params._basePoint = target.basePoint;
    }

    return instance.renderMulti(baseData, viewMode).filter((result) => result.data.length > 0);
}

/** A chart's saved local signals, in their order. Backend-owned and unknown definitions are left to the backend results. */
export function renderLocalSignals(configs: readonly SignalConfig[], definitionsByType: ReadonlyMap<string, SignalDefinition>, baseData: LineDataPoint[], viewMode: ViewMode, sources: SignalDataSources): RenderedSignal[] {
    const rendered: RenderedSignal[] = [];
    for (const config of configs) {
        const definition = definitionsByType.get(config.signalType);
        if (!definition || definition.source === 'backend') continue;
        rendered.push(...renderLocalSignal(config, baseData, viewMode, sources));
    }
    return rendered;
}

/**
 * A chart's backend results, in their order, each drawn with the current config of its id (a style changed since the
 * request applies at once), else with the config it was requested with.
 */
export function renderBackendResults(configs: readonly SignalConfig[], results: readonly SignalInstanceResult[], definitionsByType: ReadonlyMap<string, SignalDefinition>, baseData: LineDataPoint[], viewMode: ViewMode, translate?: (key: string) => string): RenderedSignal[] {
    const rendered: RenderedSignal[] = [];
    for (const item of results) {
        if (item.source !== 'backend' || !item.result) continue;
        const config = configs.find((candidate) => candidate.id === item.config.id) ?? item.config;
        const definition = definitionsByType.get(config.signalType);
        if (!definition || definition.source !== 'backend') {
            console.error(`Missing backend signal definition for '${config.signalType}'`);
            continue;
        }
        rendered.push(...renderBackendSignalResult(item.result, config, {baseData, viewMode, definition, translate}).signals);
    }
    return rendered;
}

/** A target's rolling return, as far as the chart reads it (`CalendarReturnView` of `priceChartHelpers.ts`). */
export interface CalendarReturnSeries {
    state: string;
    points: LineDataPoint[];
}

/**
 * The comparisons of a chart in the rolling-return view (lot Y-40): each saved comparison drawn with its target's rolling
 * return (`views`, by asset), as the asset detail page draws them. A return not ready nor partial, the chart's own asset and
 * an unset target draw nothing. `target` names the target (its icon and type too); `fallbackName` when it does not.
 */
export function renderCalendarComparisons(
    configs: readonly SignalConfig[],
    views: ReadonlyMap<number, CalendarReturnSeries>,
    target: (assetId: number) => Pick<ComparisonTarget, 'displayName' | 'iconUrl' | 'assetType'> | null,
    fallbackName: (assetId: number) => string,
    selfAssetId?: number | null,
): RenderedSignal[] {
    const rendered: RenderedSignal[] = [];
    for (const config of configs) {
        if (config.signalType !== 'asset-comparison') continue;
        const assetId = Number(config.params.assetId);
        if (!Number.isInteger(assetId) || assetId <= 0 || assetId === selfAssetId) continue;
        const view = views.get(assetId);
        if (!view || (view.state !== 'ready' && view.state !== 'partial')) continue;
        const names = target(assetId);
        rendered.push({
            id: `${config.id}:calendar-return`,
            label: names?.displayName ?? fallbackName(assetId),
            data: view.points,
            color: config.style.color,
            lineWidth: config.style.lineWidth,
            lineType: config.style.lineType,
            markerStart: config.style.markerStart,
            markerEnd: config.style.markerEnd,
            yAxisIndex: 0,
            axisRole: 'price',
            unit: 'percentage',
            connectNulls: false,
            aggregationProfile: 'last_with_range',
            iconUrl: names?.iconUrl ?? null,
            assetType: names?.assetType ?? null,
        });
    }
    return rendered;
}
