/**
 * currencyRoutesPool.ts — the Web Worker that searches conversion routes (lane 75, L20b, decision Q6), behind the
 * shared `WorkerPool`.
 *
 * One worker is enough: the route picker asks one pair at a time, and a search costs a few ms with the depth rule. The
 * pool is created lazily, on the first search, never at import time, so this module is safe to import during SvelteKit
 * SSR. Where no `Worker` exists (SSR, the node test environment) the same pure function runs in the current thread; in
 * a browser the search always goes to the worker.
 *
 * @module workers/currencyRoutesPool
 */

import type {ChainStep} from '$lib/utils/currency/currencyGraph';
import {computeRoutePaths, type CurrencyRoutesRequest} from './currencyRoutes.worker';
import {WorkerPool} from './workerPool';

let pool: WorkerPool | null = null;

function getCurrencyRoutesPool(): WorkerPool {
    if (!pool) {
        pool = new WorkerPool(() => new Worker(new URL('./currencyRoutes.worker.ts', import.meta.url), {type: 'module'}), 1);
    }
    return pool;
}

/** The routes of a pair, found in the worker (in the current thread where no `Worker` exists). */
export async function findRoutePathsOffThread(request: CurrencyRoutesRequest): Promise<ChainStep[][]> {
    if (typeof globalThis.Worker === 'undefined') return computeRoutePaths(request);
    return getCurrencyRoutesPool().run<CurrencyRoutesRequest, ChainStep[][]>(request);
}

/** Terminate the worker (tests, explicit cleanup). Safe when it was never created. */
export function destroyCurrencyRoutesPool(): void {
    pool?.destroy();
    pool = null;
}
