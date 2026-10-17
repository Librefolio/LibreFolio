/**
 * livePriceService.ts — Shared utility for fetching live current prices.
 *
 * Used by:
 * - routes/(app)/assets/+page.svelte (assets list, cards + table): `fetchCurrentPrices` and the poll's outcome;
 * - the asset detail page's live poll (`components/assets/detail/assetDetailLive.svelte.ts`): the helpers only, since
 *   it posts its one id itself.
 *
 * Always non-blocking: callers fire-and-forget via promises. `livePollOutcome` and `livePollFailure` turn an answer, or
 * a request that failed, into what the live poller needs to space the next one (`activePolling.ts`, Z7): the end of a
 * provider's pause, the server's `Retry-After`, or a failure that doubles the wait.
 */
import {axiosInstance} from '$lib/api';
import {sendBulkBatches} from '$lib/api/bulkBatches';
import type {PollOutcome} from '$lib/features/live-updates/activePolling';

export type LivePriceDirection = 'up' | 'down' | 'neutral';

/** The `error_code` of a price whose provider is paused after too many requests: the value is the last one saved. */
const RATE_LIMITED = 'RATE_LIMITED';

export interface LivePriceResult {
    assetId: number;
    value: number | null;
    currency: string;
    source: string | null;
    error: string | null;
    /** `RATE_LIMITED` while the asset's provider is paused; null, or another code, otherwise. */
    errorCode: string | null;
    /** With `RATE_LIMITED`: seconds until the provider's pause ends. */
    retryAfter: number | null;
}

/** One item of `POST /api/v1/assets/prices/current`, as the pages read it. */
export function toLivePriceResult(raw: any): LivePriceResult {
    const retryAfter = raw.retry_after != null ? Number(raw.retry_after) : NaN;
    return {
        assetId: raw.asset_id,
        value: raw.value != null ? parseFloat(raw.value) : null,
        currency: raw.currency ?? '',
        source: raw.source ?? null,
        error: raw.error ?? null,
        errorCode: raw.error_code ?? null,
        retryAfter: Number.isFinite(retryAfter) ? retryAfter : null,
    };
}

/**
 * Fetch current live prices for a list of asset IDs.
 * Wraps POST /api/v1/assets/prices/current, which answers at most 1,000 ids per request (R13-SEC9-1): a longer list goes
 * in batches (`sendBulkBatches`, lot Z-27), one after the other, the answers in order (X-R64). All or nothing: a failed
 * batch rejects with its own error, as axios raised it, so that `livePollFailure` still reads its `Retry-After`.
 */
export async function fetchCurrentPrices(ids: number[]): Promise<LivePriceResult[]> {
    if (ids.length === 0) return [];
    const outcome = await sendBulkBatches(
        ids,
        () => 0,
        (batch) => axiosInstance.post('/api/v1/assets/prices/current', batch),
    );
    if (outcome.failed) throw outcome.error;
    const results: any[] = outcome.answers.flatMap(({answer}) => answer.data?.results ?? []);
    return results.map(toLivePriceResult);
}

/**
 * What a live answer means for the next poll. Only when every asset asked about is paused does the next poll wait, for
 * the first pause to end: with one provider still answering the poll goes on, and costs little, since the backend does
 * not call the paused ones. A pause of unknown length counts as a failure: the poller doubles its wait.
 */
export function livePollOutcome(results: LivePriceResult[], now: number = Date.now()): PollOutcome {
    if (results.length === 0 || results.some((result) => result.errorCode !== RATE_LIMITED)) return {ok: true};
    const waits: number[] = [];
    for (const result of results) {
        if (result.retryAfter === null || !Number.isFinite(result.retryAfter) || result.retryAfter < 0) return {ok: false};
        waits.push(result.retryAfter);
    }
    return {ok: true, notBefore: now + Math.min(...waits) * 1000};
}

/**
 * A live request that failed: the next poll waits longer. A 429 or a 503 of the server with a usable `Retry-After`
 * also says when the next one may start.
 */
export function livePollFailure(error: unknown, now: number = Date.now()): PollOutcome {
    const response = error !== null && typeof error === 'object' ? (error as any).response : undefined;
    if (response?.status !== 429 && response?.status !== 503) return {ok: false};
    const notBefore = retryAfterAt(headerOf(response.headers, 'retry-after'), now);
    return notBefore === null ? {ok: false} : {ok: false, notBefore};
}

/** A response header from axios's `AxiosHeaders` (case-insensitive `get`) or a plain object (lower-case keys). */
function headerOf(headers: any, name: string): string | null {
    if (headers == null || typeof headers !== 'object') return null;
    const value = typeof headers.get === 'function' ? headers.get(name) : headers[name];
    return value == null ? null : String(value);
}

/** `Retry-After` — delta-seconds or an HTTP-date — as a `Date.now()` time; null when unusable or already past. */
function retryAfterAt(value: string | null, now: number): number | null {
    if (value === null) return null;
    const text = value.trim();
    if (/^\d+(\.\d+)?$/.test(text)) return now + parseFloat(text) * 1000;
    const at = Date.parse(text);
    return Number.isFinite(at) && at > now ? at : null;
}

/**
 * Compute price direction comparing current to previous value.
 */
export function computeDirection(current: number | null, prev: number | null): LivePriceDirection {
    if (current == null || prev == null || current === prev) return 'neutral';
    return current > prev ? 'up' : 'down';
}
