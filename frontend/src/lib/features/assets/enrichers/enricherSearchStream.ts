/**
 * enricherSearchStream — «Cerca online» as the backend streams it (ENR-3): `GET /api/v1/assets/enrichers/search`
 * answers Server-Sent Events, one `data: {json}` each — `enricher_results` (one enricher's answer, as it arrives) and
 * last `done` (the codes asked).
 *
 * Read with `fetch` and the parser of `recognizeStream.ts`. Outcomes: `done`, `refused` (429, the per-user limit of the
 * probes, with its wait), `aborted` (the caller stopped it: a newer text, the window closed). Any other failure throws.
 *
 * @module features/assets/enrichers/enricherSearchStream
 */
import type {z} from 'zod';
import type {schemas} from '$lib/api/generated';
import {createSseParser, isAbort, retryAfterOf} from './recognizeStream';

export const SEARCH_PATH = '/api/v1/assets/enrichers/search';

/** One result of an enricher's search: a binding ready to add. */
export type EnricherSearchHit = z.infer<typeof schemas.FAEnricherSearchResult>;

/** How one enricher answered a search. */
export type EnricherSearchStatus = 'ok' | 'identifier_only' | 'rate_limited' | 'not_configured' | 'off' | 'not_covering' | 'error';

export interface EnricherResultsEvent {
    event: 'enricher_results';
    code: string;
    status: EnricherSearchStatus;
    /** `search`, or `recognize` for an enricher without a search asked with an identifier of its type (R12). */
    via: 'search' | 'recognize' | null;
    results: EnricherSearchHit[];
    accepted_identifier_types: string[];
    retry_after: number | null;
    error_code: string | null;
}
export interface SearchDoneEvent {
    event: 'done';
    codes: string[];
}
export type EnricherSearchEvent = EnricherResultsEvent | SearchDoneEvent;

export interface EnricherSearchRequest {
    q: string;
    codes: string[];
    assetType?: string | null;
}

export type EnricherSearchOutcome = {kind: 'done'} | {kind: 'refused'; retryAfter: number | null} | {kind: 'aborted'};

/** The address of a search: the text, each code repeated, the asset's type. */
export function searchUrl(request: EnricherSearchRequest): string {
    const params = new URLSearchParams({q: request.q});
    for (const code of request.codes) params.append('codes', code);
    if (request.assetType) params.set('asset_type', request.assetType);
    return `${SEARCH_PATH}?${params.toString()}`;
}

/** «Cerca online»: every event handed over as it arrives; the outcome when the stream ends. */
export async function searchEnrichersOnline(request: EnricherSearchRequest, options: {onEvent: (event: EnricherSearchEvent) => void; signal?: AbortSignal; fetchImpl?: typeof fetch}): Promise<EnricherSearchOutcome> {
    const {onEvent, signal, fetchImpl = fetch} = options;
    try {
        const response = await fetchImpl(searchUrl(request), {method: 'GET', credentials: 'same-origin', headers: {Accept: 'text/event-stream'}, signal});
        if (response.status === 429) return {kind: 'refused', retryAfter: await retryAfterOf(response)};
        if (!response.ok || !response.body) throw new Error(`enricher search: HTTP ${response.status}`);
        const parser = createSseParser<EnricherSearchEvent>();
        const reader = response.body.getReader();
        for (;;) {
            const {value, done} = await reader.read();
            if (done) break;
            if (value) parser.push(value).forEach(onEvent);
        }
        parser.end().forEach(onEvent);
        return {kind: 'done'};
    } catch (error) {
        if (isAbort(error, signal)) return {kind: 'aborted'};
        throw error;
    }
}
