/**
 * Signal Result Cache — the backend signal results the detail pages already received, kept like their prices (lot N64).
 *
 * The asset and FX detail pages keep their prices and rates in `TimeSeriesStore`s; their backend signals (SMA, RSI…,
 * the calendar rolling returns) were asked again at every change of mode, window, period or currency, even when nothing
 * had changed. Here an answer is kept under the exact request it answered — the canonical text of the request body
 * (`canonicalCacheKey`) — and given back only while the data it was computed from is the same: the caller passes the
 * generations of the stores it read (`TimeSeriesStore.generation`), read when the request started, and a later read with
 * any other generation misses and drops the entry. Every invalidation of those stores — Refresh, a sync, an editor save,
 * a currency change, a price catch-up marking them stale (`{kind: 'prices'}` on the portfolio bus) — thus invalidates
 * what was computed from them, without a call of its own anywhere.
 *
 * No merge by intervals as for prices: a signal on [start, end] depends on its warm-up before `start`, so only the
 * exact request matches. The pages write only answers they applied and found valid, never a failed or invalid one.
 *
 * Bounded: the least recently used entry goes past `maxEntries`. Values are deep copies both ways, so no caller can
 * change what another one reads later. Emptied when the signed-in account changes.
 *
 * @module stores/signalResultCache
 */

import type {BackendSignalResult} from '$lib/charts/signals/backendTypes';
import {registerClientSessionReset} from '$lib/stores/app/clientSession';

/** The answer of the asset detail page's price query, without the prices (the price store holds them). */
export interface AssetChartAnswer {
    items: Record<string, unknown>[];
}

/** A value with its object keys sorted at every depth, so that the same request gives the same text. */
function sortedKeys(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(sortedKeys);
    if (value === null || typeof value !== 'object') return value;
    const record = value as Record<string, unknown>;
    return Object.fromEntries(
        Object.keys(record)
            .sort()
            .map((key) => [key, sortedKeys(record[key])]),
    );
}

/**
 * The JSON text of a value with the keys of every object sorted: two requests that differ only in the order of their
 * properties are one key. Arrays keep their order; an undefined property is left out, as `JSON.stringify` does.
 */
export function canonicalCacheKey(value: unknown): string {
    return JSON.stringify(sortedKeys(value));
}

interface CacheEntry<T> {
    generations: readonly number[];
    value: T;
}

const sameGenerations = (left: readonly number[], right: readonly number[]): boolean => left.length === right.length && left.every((generation, index) => generation === right[index]);

export class SignalResultCache<T> {
    /** In use order: the first key is the least recently used (a `Map` keeps insertion order). */
    private entries = new Map<string, CacheEntry<T>>();

    constructor(private readonly maxEntries = 32) {}

    /**
     * The answer kept under `key`, if it was drawn over these very generations (same stores, same order); null
     * otherwise. A mismatch drops the entry: its data has changed. A hit becomes the most recently used.
     */
    get(key: string, generations: readonly number[]): T | null {
        const entry = this.entries.get(key);
        if (!entry) return null;
        this.entries.delete(key);
        if (!sameGenerations(entry.generations, generations)) return null;
        this.entries.set(key, entry);
        return structuredClone(entry.value);
    }

    /** Keeps `value` under `key`, drawn over `generations`, as the most recently used; past `maxEntries` the oldest goes. */
    set(key: string, generations: readonly number[], value: T): void {
        this.entries.delete(key);
        this.entries.set(key, {generations: [...generations], value: structuredClone(value)});
        while (this.entries.size > this.maxEntries) {
            const oldest = this.entries.keys().next().value;
            if (oldest === undefined) break;
            this.entries.delete(oldest);
        }
    }

    clear(): void {
        this.entries.clear();
    }

    get size(): number {
        return this.entries.size;
    }
}

/** The asset detail page's answers: events, backend signals and calendar returns, its comparisons' included. */
export const assetChartAnswers = new SignalResultCache<AssetChartAnswer>();

/** The FX detail page's backend signal results, validated. */
export const fxSignalAnswers = new SignalResultCache<BackendSignalResult[]>();

// An answer is the signed-in account's data: another account starts empty.
registerClientSessionReset('signalResultCache', () => {
    assetChartAnswers.clear();
    fxSignalAnswers.clear();
});
