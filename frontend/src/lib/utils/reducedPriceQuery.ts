/**
 * What the Assets page asks `POST /assets/prices/query` for the cards of its grid (lot Z-29b).
 *
 * Each card sends its own item with a `key` (`asset:<id>`) and the `max_points` its measured plot takes
 * (`compactMaxPoints()`), and the backend answers the finest step whose points fit: the series the card draws as it is
 * (`resolution`, `sample_bounds`). Each comparison target of the card is an item `sample_like` that key, on the same range,
 * so the target comes on the card's own buckets. The items of one card go together, in one group: `bulkBatches.ts` never
 * cuts between a card and its targets.
 *
 * Only what is not cached is asked. A card whose own series is cached but whose targets are not is still sent, as an item
 * without prices (a step only, which counts nothing against the backend's day budget), because its targets name it.
 *
 * Pure: no Svelte, no store, no clock (`today` is an argument).
 *
 * @module utils/reducedPriceQuery
 */

import {BULK_SIGNAL_MARGIN_DAYS, bulkRangeDays} from '$lib/api/bulkBatches';
import type {SignalConfig} from '$lib/charts/signals';
import type {ComparisonTarget} from '$lib/charts/chartSignalRendering';
import {compactMaxPoints, type ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
import type {DerivedPriceState} from '$lib/utils/assetPriceDerived';

/** An item of the request, as the backend takes it (`FAPriceQueryItem`) for a card or a card's target. */
export interface ReducedQueryItem {
    asset_id: number;
    date_range: {start: string; end: string};
    include_price: boolean;
    signals: readonly unknown[];
    /** The name of a card's item, which its targets give in `sample_like`. */
    key?: string;
    /** On a card's item: the most points its plot takes. */
    max_points?: number;
    /** On a target's item: the key of the card it is sampled like. */
    sample_like?: string;
}

/** An item with what the page needs to put its answer back: whose it is. */
export interface ReducedQueryEntry {
    item: ReducedQueryItem;
    /** The card's key: the members of one card — its item, then its targets' — share it. */
    group: string;
    role: 'card' | 'target';
    /** The asset of the card the entry belongs to. */
    cardId: number;
    /** The asset a target entry reads; null on a card's own entry. */
    targetId: number | null;
}

/** What one card needs of the request. */
export interface CardQueryInput {
    assetId: number;
    /** The card's measured plot width, in pixels (`compactPlotWidth()`). */
    plotWidthPx: number;
    start: string;
    end: string;
    /** The card's own prices are not cached (or are stale, or for another step): they are asked. */
    needsPrice: boolean;
    /** The backend signals of the card (`SignalRequest`s). */
    signals: readonly unknown[];
    /** The assets its comparison signals draw, each with whether its sample is missing from the cache. */
    targets: ReadonlyArray<{assetId: number; needsRead: boolean}>;
}

/** The key a card's item is named by. */
export function cardKey(assetId: number): string {
    return `asset:${assetId}`;
}

/** The entries of the request for `cards`, a card's item and then its targets', in the cards' order. */
export function buildReducedQuery(cards: readonly CardQueryInput[]): ReducedQueryEntry[] {
    const entries: ReducedQueryEntry[] = [];
    for (const card of cards) {
        const targets: number[] = [];
        for (const target of card.targets) {
            if (target.needsRead && target.assetId !== card.assetId && !targets.includes(target.assetId)) targets.push(target.assetId);
        }
        if (!card.needsPrice && card.signals.length === 0 && targets.length === 0) continue;
        const key = cardKey(card.assetId);
        const dateRange = {start: card.start, end: card.end};
        entries.push({
            item: {asset_id: card.assetId, date_range: dateRange, include_price: card.needsPrice, signals: card.signals, key, max_points: compactMaxPoints(card.plotWidthPx)},
            group: key,
            role: 'card',
            cardId: card.assetId,
            targetId: null,
        });
        for (const targetId of targets) {
            entries.push({item: {asset_id: targetId, date_range: dateRange, include_price: true, signals: [], sample_like: key}, group: key, role: 'target', cardId: card.assetId, targetId});
        }
    }
    return entries;
}

/**
 * The item-days an entry is guessed to cost the backend's day budget: its range, plus the signals' margin; nothing for an
 * item without prices and signals (a step only).
 */
export function estimateEntryDays(entry: ReducedQueryEntry, today: string): number {
    const {item} = entry;
    if (!item.include_price && item.signals.length === 0) return 0;
    return bulkRangeDays(item.date_range.start, item.date_range.end, today) + (item.signals.length > 0 ? BULK_SIGNAL_MARGIN_DAYS : 0);
}

/** The assets the comparison signals of `configs` draw, once each and in order, without the card's own and the unset. */
export function comparisonTargetIds(configs: readonly Pick<SignalConfig, 'signalType' | 'params'>[], selfAssetId: number): number[] {
    const ids: number[] = [];
    for (const config of configs) {
        if (config.signalType !== 'asset-comparison') continue;
        const id = Number(config.params.assetId);
        if (!Number.isInteger(id) || id <= 0 || id === selfAssetId || ids.includes(id)) continue;
        ids.push(id);
    }
    return ids;
}

/**
 * A comparison target as the card's signal sources hand it to the renderer: its series, sampled like the card's, and, for a
 * sampled one, its point on the day the comparison starts as the percentage base (`basePoint`): the series draws the end of
 * the first bucket, and a daily chart measures from the first day (Z-29d-0). A daily target needs none. Null when it has no
 * point.
 */
export function comparisonTargetFrom(series: {resolution: ChartResolution; derived: DerivedPriceState}, names: {displayName?: string | null; iconUrl?: string | null; assetType?: string | null}): ComparisonTarget | null {
    const {chartData, base} = series.derived;
    if (chartData.length === 0) return null;
    return {data: chartData, ...names, basePoint: series.resolution === 'daily' || !base ? null : {date: base.date, value: base.value}};
}

/**
 * The cards whose measured width now asks another step than the series they hold (MF n2): each is read again from the
 * backend, never re-aggregated (a weekly sample into months) nor turned back into days. `read` says, for a card, whether it
 * has settled (not loading, a series on screen), its measured plot width, whether its cached series holds for a
 * `max_points`, and whether it was already read again for this width (a card is read again once for a width, however its
 * answer reads, so that a disagreement between this rule and the backend's cannot make it loop).
 */
export function cardsOfAnotherStep(candidates: readonly number[], read: (assetId: number) => {settled: boolean; plotWidthPx: number | undefined; holds: (maxPoints: number) => boolean; reloadedForWidth: boolean}): number[] {
    const changed: number[] = [];
    for (const assetId of candidates) {
        if (changed.includes(assetId)) continue;
        const card = read(assetId);
        if (!card.settled || card.plotWidthPx === undefined || card.reloadedForWidth) continue;
        if (!card.holds(compactMaxPoints(card.plotWidthPx))) changed.push(assetId);
    }
    return changed;
}

/**
 * The data a card hands its backend signals' renderer as the chart's: the renderer measures a `base_percentage` series from
 * the first point it is given (`backendRenderer.ts`, `baseData[0]`, and nothing else of it). A sampled card's first point is
 * the end of its first bucket, so it gets the point on the fill's first day instead (MF n3); a daily card's own data.
 */
export function signalBaseData<P extends {date: string; value: number}>(chartData: P[], base: {date: string; value: number} | null | undefined, resolution: ChartResolution | undefined): P[] | Array<{date: string; value: number}> {
    if (!base || resolution === undefined || resolution === 'daily') return chartData;
    return [{date: base.date, value: base.value}];
}
