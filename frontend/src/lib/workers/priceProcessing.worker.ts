/**
 * priceProcessing.worker.ts — Web Worker script that validates + transforms a CHUNK of
 * the bulk asset-prices-query response, off the main thread.
 *
 * Run by instances spawned from a shared `WorkerPool` (see `workerPool.ts`). Each task
 * receives a subset of the `items` array from `POST /api/v1/assets/prices/query`'s raw
 * (not-yet-validated) response, validates every item with the SAME Zod schema the
 * generated Zodios client would otherwise use automatically, then computes the SAME
 * derived UI state (last price, per-period deltas, chart-ready points) the Assets list
 * page already computed on the main thread — identical schema, identical algorithm,
 * only WHERE it runs changes.
 *
 * Why this exists: the single bulk request itself is intentional (backend runs one SQL
 * query for all requested assets) and must not be split into many smaller requests.
 * What WAS blocking the main thread (and, transitively, delaying click/navigation
 * handling — same-thread, single-threaded JS) was validating + transforming the
 * response for every asset in one synchronous block. Splitting that CPU-bound work
 * across a worker pool moves it off the main thread entirely, and distributing it
 * across multiple worker instances lets it run on separate CPU cores in parallel.
 *
 * @module workers/priceProcessing.worker
 */

import {z} from 'zod';
// Import the Zod schema DIRECTLY from the generated module (not the `$lib/api` barrel,
// which also re-exports the Zodios HTTP client — pulling that into the worker's
// dependency graph fails to bundle, since it transitively imports SvelteKit runtime
// modules like `$app/environment` that only exist in the main app's build context, not
// a Worker's). `generated.ts` itself has zero SvelteKit dependencies (only zod +
// @zodios/core), so importing it directly is safe here.
import {schemas} from '$lib/api/generated';
import {apiPricesToAssetPricePoints, computeDerivedPriceState, type AssetPricePoint, type DerivedPriceState} from '$lib/utils/assetPriceDerived';
import type {WorkerRequestMessage, WorkerResponseMessage} from './workerPool';

/** One raw (unvalidated) bulk-query result item, as received over the wire. */
export type RawPriceQueryResultItem = unknown;

export interface PriceProcessingRequest {
    /** Raw (unvalidated) `items` entries from the bulk prices query response. */
    items: RawPriceQueryResultItem[];
}

export interface ProcessedAssetResult {
    assetId: number;
    mappedPoints: AssetPricePoint[];
    derived: DerivedPriceState;
}

export interface PriceProcessingResponse {
    results: ProcessedAssetResult[];
    /** Items that failed Zod validation — surfaced so the caller can log/report them
     *  instead of silently dropping malformed entries. */
    invalidItemErrors: string[];
}

/** Reuse the exact schema the generated Zodios client would validate each item with. */
// z.infer derives the exact validated shape from the schema itself (rather than
// re-declaring/importing the generated TS type, which the openapi-zod-client codegen
// does not export) — stays in sync automatically if the schema is regenerated.
type FAPriceQueryResult = z.infer<typeof schemas.FAPriceQueryResult>;
const FAPriceQueryResultSchema: z.ZodType<FAPriceQueryResult> = schemas.FAPriceQueryResult;

function processRequest(request: PriceProcessingRequest): PriceProcessingResponse {
    const results: ProcessedAssetResult[] = [];
    const invalidItemErrors: string[] = [];

    for (const rawItem of request.items) {
        const parsed = FAPriceQueryResultSchema.safeParse(rawItem);
        if (!parsed.success) {
            invalidItemErrors.push(parsed.error.message);
            continue;
        }

        const item = parsed.data;
        const prices = item.prices ?? [];
        results.push({
            assetId: item.asset_id,
            mappedPoints: apiPricesToAssetPricePoints(prices),
            derived: computeDerivedPriceState(prices),
        });
    }

    return {results, invalidItemErrors};
}

self.onmessage = (event: MessageEvent<WorkerRequestMessage<PriceProcessingRequest>>) => {
    const {id, payload} = event.data;

    try {
        const result = processRequest(payload);
        const response: WorkerResponseMessage<PriceProcessingResponse> = {id, result};
        (self as unknown as Worker).postMessage(response);
    } catch (error) {
        const response: WorkerResponseMessage<PriceProcessingResponse> = {
            id,
            error: error instanceof Error ? error.message : 'Unknown error while processing price chunk.',
        };
        (self as unknown as Worker).postMessage(response);
    }
};
