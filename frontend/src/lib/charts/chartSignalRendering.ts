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
    backwardFillInfo?: {daysBack?: number} | null;
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
