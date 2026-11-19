/**
 * currencyRoutes.worker.ts — Web Worker script that finds the conversion routes of one currency pair, off the main
 * thread (lane 75, L20b, developer decision Q6 of 19/11/2026: the search runs in a worker in every case).
 *
 * Each task receives the providers as plain data (code, bases, targets, `configured`) and the currency codes, builds the
 * full graph and the graph of the configured providers, and answers `findRoutePaths`: the depth rule of Q6, then every
 * chain up to that depth. The graphs are rebuilt for every task (about 1 ms): the providers' readiness changes without a
 * new graph («Configure», plan 76 N3c), and a worker that keeps no state never answers with a stale one.
 *
 * Imports only `currencyGraph.ts` (graphology): never the store or `$lib/api`, which pull SvelteKit runtime modules a
 * worker's bundle cannot load (see `priceProcessing.worker.ts`).
 *
 * @module workers/currencyRoutes.worker
 */

import {buildConfiguredCurrencyGraph, buildCurrencyGraph, type ChainStep, findRoutePaths, type ProviderInfo, ROUTE_DEPTH_CAP} from '$lib/utils/currency/currencyGraph';
import type {WorkerRequestMessage, WorkerResponseMessage} from './workerPool';

export interface CurrencyRoutesRequest {
    /** The FX providers as `GET /fx/providers` lists them; only the codes, currencies and `configured` are read. */
    providers: ProviderInfo[];
    /** Every currency code of the app: the graph's nodes. */
    currencyCodes: string[];
    source: string;
    target: string;
    /** The longest chain searched (default `ROUTE_DEPTH_CAP`). */
    cap?: number;
}

/** The routes of the pair: `findRoutePaths` on graphs built from the request's plain data. */
export function computeRoutePaths(request: CurrencyRoutesRequest): ChainStep[][] {
    const fullGraph = buildCurrencyGraph(request.providers, request.currencyCodes);
    const configuredGraph = buildConfiguredCurrencyGraph(request.providers, request.currencyCodes);
    return findRoutePaths(fullGraph, configuredGraph, request.source, request.target, request.cap ?? ROUTE_DEPTH_CAP);
}

if (typeof self !== 'undefined' && typeof (self as {postMessage?: unknown}).postMessage === 'function' && typeof window === 'undefined') {
    self.onmessage = (event: MessageEvent<WorkerRequestMessage<CurrencyRoutesRequest>>) => {
        const {id, payload} = event.data;
        let response: WorkerResponseMessage<ChainStep[][]>;
        try {
            response = {id, result: computeRoutePaths(payload)};
        } catch (error) {
            response = {id, error: error instanceof Error ? error.message : 'Unknown error while finding conversion routes.'};
        }
        (self as unknown as Worker).postMessage(response);
    };
}
