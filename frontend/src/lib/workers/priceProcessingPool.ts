/**
 * priceProcessingPool.ts — Lazily-created singleton WorkerPool for the
 * priceProcessing.worker.ts script, plus the chunk-splitting logic that balances work
 * across pool workers by TOTAL PRICE-POINT COUNT (not naive item count — a 26-year
 * asset history vastly outweighs a 6-month one, so splitting evenly by item count would
 * leave some workers idle while one is overloaded).
 *
 * Lazy singleton: the pool (and its `new Worker(...)` calls) is only created on first
 * actual use, never at module import time — this file can be safely imported during
 * SvelteKit SSR (where `Worker`/`navigator` do not exist) as long as
 * `getPriceProcessingPool()` itself is never called outside the browser, which holds
 * today since the only caller (`fetchAllPriceData()` in the Assets list page) runs
 * exclusively from `onMount` (client-only).
 *
 * @module workers/priceProcessingPool
 */

import {WorkerPool} from './workerPool';
import type {PriceProcessingRequest, PriceProcessingResponse, ProcessedAssetResult, RawPriceQueryResultItem} from './priceProcessing.worker';

let pool: WorkerPool | null = null;

function getPriceProcessingPool(): WorkerPool {
    if (!pool) {
        pool = new WorkerPool(() => new Worker(new URL('./priceProcessing.worker.ts', import.meta.url), {type: 'module'}));
    }
    return pool;
}

/** Rough per-item weight for load-balancing: total price-point count if present, else 1. */
export function itemWeight(item: RawPriceQueryResultItem): number {
    const prices = (item as {prices?: unknown[]} | null | undefined)?.prices;
    return Array.isArray(prices) && prices.length > 0 ? prices.length : 1;
}

/**
 * Split `items` into `chunkCount` groups, balanced by total weight (price-point count)
 * per group rather than item count — a simple greedy bin-packing: sort items by weight
 * descending, then repeatedly add the next item to whichever group currently has the
 * LOWEST total weight. Good enough for a handful of groups and dozens of items; not
 * meant to be a perfectly optimal partition.
 */
export function splitBalanced(items: RawPriceQueryResultItem[], chunkCount: number): RawPriceQueryResultItem[][] {
    const groups: RawPriceQueryResultItem[][] = Array.from({length: chunkCount}, () => []);
    const groupWeights = new Array(chunkCount).fill(0);

    const sorted = [...items].sort((a, b) => itemWeight(b) - itemWeight(a));
    for (const item of sorted) {
        let lightestIndex = 0;
        for (let i = 1; i < chunkCount; i++) {
            if (groupWeights[i] < groupWeights[lightestIndex]) lightestIndex = i;
        }
        groups[lightestIndex].push(item);
        groupWeights[lightestIndex] += itemWeight(item);
    }

    return groups.filter((g) => g.length > 0);
}

/**
 * Validate + transform a bulk prices-query response's raw `items` array across the
 * shared worker pool, in parallel, without changing the single-request/single-SQL-query
 * shape of the underlying API call — only WHERE the CPU-bound post-processing runs
 * changes (across N worker threads instead of one synchronous block on the main thread).
 */
export async function processPriceItemsInParallel(items: RawPriceQueryResultItem[]): Promise<{results: ProcessedAssetResult[]; invalidItemErrors: string[]}> {
    if (items.length === 0) return {results: [], invalidItemErrors: []};

    const workerPool = getPriceProcessingPool();
    // Don't create more chunks than items — a single tiny fetch (e.g. 1 asset) should
    // just run as one chunk on one worker, not pointlessly spread across the whole pool.
    const chunkCount = Math.max(1, Math.min(items.length, getPoolSizeHint()));
    const chunks = splitBalanced(items, chunkCount);

    const chunkResponses = await Promise.all(chunks.map((chunk) => workerPool.run<PriceProcessingRequest, PriceProcessingResponse>({items: chunk})));

    const results: ProcessedAssetResult[] = [];
    const invalidItemErrors: string[] = [];
    for (const response of chunkResponses) {
        results.push(...response.results);
        invalidItemErrors.push(...response.invalidItemErrors);
    }
    return {results, invalidItemErrors};
}

/** Best-effort hint for how many chunks to split into — mirrors WorkerPool's own default
 *  sizing logic without needing to expose the pool's internal worker count. */
function getPoolSizeHint(): number {
    if (typeof navigator === 'undefined') return 4;
    const {hardwareConcurrency} = navigator;
    if (!Number.isFinite(hardwareConcurrency) || hardwareConcurrency < 1) return 4;
    return Math.min(8, Math.max(1, Math.floor(hardwareConcurrency)));
}

/** Terminate the pool (e.g. for tests, or explicit app-level cleanup). Safe to call even
 *  if the pool was never created. */
export function destroyPriceProcessingPool(): void {
    pool?.destroy();
    pool = null;
}
