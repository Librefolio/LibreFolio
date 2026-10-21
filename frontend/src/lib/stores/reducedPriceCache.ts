/**
 * Reduced Price Cache — the series a card of the Assets grid draws, sampled by the backend for the card's plot (lot Z-29b).
 *
 * Beside the daily cache (`assetPriceStoreRegistry`), which it does not touch: that one holds every day and serves the
 * pages that draw every day; this one holds what a compact chart takes, one point per day, week or month, with the step
 * the backend chose (`resolution`) and the point on the fill's first day (`derived.base`, from `sample_bounds.first`).
 *
 * An entry answers a width when the step that width asks (`stepForMaxPoints`, from the counts of days and weeks of the
 * fill the entry holds) is the entry's own. A resize that keeps the step reads the same entry; one that changes it reads
 * nothing, and the page asks the backend again: a weekly sample is never re-aggregated into months, nor turned back into
 * days (MF n2).
 *
 * A comparison target is sampled like its card (`sample_like`), so it is kept by the card it was read for, valid for the
 * step the card had.
 *
 * After a price catch-up on the server (`{kind: 'prices'}` on the portfolio bus) every entry is marked stale: still
 * readable, to be read again. An asset's sync or refresh drops what it touched (`invalidateAsset`).
 *
 * @module stores/reducedPriceCache
 */

import type {ChartResolution} from '$lib/components/charts/timeSeriesAggregation';
import {fillCounts, stepForMaxPoints} from '$lib/components/charts/timeSeriesAggregation';
import type {DerivedPriceState} from '$lib/utils/assetPriceDerived';

import {registerPortfolioMutationListener} from './portfolio/portfolioMutation';

/** A series as the page reads it from an answer. */
export interface ReducedSeries {
    resolution: ChartResolution;
    derived: DerivedPriceState;
}

export interface ReducedEntry extends ReducedSeries {
    /** The days and ISO weeks of the fill the series holds, from its base to its last point. */
    counts: {days: number; weeks: number};
    /** Marked by a price catch-up: readable, but to be read again. */
    stale: boolean;
}

interface TargetEntry extends ReducedEntry {
    /** The step of the card the target was sampled like. */
    likeResolution: ChartResolution;
}

function countsOf(derived: DerivedPriceState): {days: number; weeks: number} {
    const last = derived.chartData[derived.chartData.length - 1];
    if (!derived.base || !last) return {days: 0, weeks: 0};
    const {days, weeks} = fillCounts(derived.base.date, last.date);
    return {days, weeks};
}

export class ReducedPriceCache {
    private cards = new Map<string, ReducedEntry>();
    private targets = new Map<string, TargetEntry>();

    private static cardKey(assetId: number, start: string, end: string): string {
        return `${assetId}|${start}|${end}`;
    }

    private static targetKey(targetId: number, cardId: number, start: string, end: string): string {
        return `${targetId}|${cardId}|${start}|${end}`;
    }

    /** The card's series for this range if it is the step a plot taking `maxPoints` asks; null otherwise. */
    getCard(assetId: number, start: string, end: string, maxPoints: number): ReducedEntry | null {
        const entry = this.cards.get(ReducedPriceCache.cardKey(assetId, start, end));
        if (!entry || stepForMaxPoints(entry.counts, maxPoints) !== entry.resolution) return null;
        return entry;
    }

    putCard(assetId: number, start: string, end: string, series: ReducedSeries): ReducedEntry {
        const entry: ReducedEntry = {...series, counts: countsOf(series.derived), stale: false};
        this.cards.set(ReducedPriceCache.cardKey(assetId, start, end), entry);
        return entry;
    }

    /** The target's series sampled like the card, if the card has the step it was read for; null otherwise. */
    getTarget(targetId: number, cardId: number, start: string, end: string, cardResolution: ChartResolution): ReducedEntry | null {
        const entry = this.targets.get(ReducedPriceCache.targetKey(targetId, cardId, start, end));
        return entry && entry.likeResolution === cardResolution ? entry : null;
    }

    putTarget(targetId: number, cardId: number, start: string, end: string, series: ReducedSeries): ReducedEntry {
        const entry: TargetEntry = {...series, counts: countsOf(series.derived), stale: false, likeResolution: series.resolution};
        this.targets.set(ReducedPriceCache.targetKey(targetId, cardId, start, end), entry);
        return entry;
    }

    /** A price catch-up: every entry stays readable and is read again. */
    markStale(): void {
        for (const entry of this.cards.values()) entry.stale = true;
        for (const entry of this.targets.values()) entry.stale = true;
    }

    /** What an asset's sync or refresh touched: its own series, and the samples of it other cards hold, and its card's targets. */
    invalidateAsset(assetId: number): void {
        const prefix = `${assetId}|`;
        for (const key of [...this.cards.keys()]) if (key.startsWith(prefix)) this.cards.delete(key);
        for (const key of [...this.targets.keys()]) {
            const [targetId, cardId] = key.split('|');
            if (Number(targetId) === assetId || Number(cardId) === assetId) this.targets.delete(key);
        }
    }

    clear(): void {
        this.cards.clear();
        this.targets.clear();
    }
}

/** The one cache of the app. */
export const reducedPrices = new ReducedPriceCache();

registerPortfolioMutationListener('reducedPriceCache', (signal) => {
    if (signal.kind === 'prices') reducedPrices.markStale();
});
