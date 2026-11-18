/**
 * enricherCalls — the two calls the «Arricchitori dell'asset» window makes itself (plan 68, E7b2): a search inside one
 * enricher and the test of a binding. «Riconosci» (a stream) belongs to the asset window (E8), which hands the window
 * what it found.
 *
 * `testOutcome` turns the answer, or the refusal, into the state a row shows: found, not found, conflict, error, not
 * configured (the coded 422 `NOT_CONFIGURED`), turned off on the instance (404), too many tests (429).
 *
 * @module features/assets/enrichers/enricherCalls
 */
import {zodiosApi} from '$lib/api';
import type {EnricherBinding, EnricherRecognition} from './enrichersEditState';

/** One result of a search inside an enricher. */
export interface EnricherSearchResult {
    name: string;
    binding: {identifier_type: string; identifier: string};
    asset_type?: string | null;
    page_url?: string | null;
}

export type SearchCall = (code: string, query: string) => Promise<EnricherSearchResult[]>;
export type TestCall = (code: string, binding: EnricherBinding) => Promise<EnricherRecognition>;

/** `GET /assets/enrichers/{code}/search`. */
export const searchEnricher: SearchCall = (code, query) => zodiosApi.search_enricher_api_v1_assets_enrichers__code__search_get({params: {code}, queries: {q: query}}) as Promise<EnricherSearchResult[]>;

/** `POST /assets/enrichers/{code}/test`. */
export const testEnricher: TestCall = (code, binding) => zodiosApi.test_enricher_api_v1_assets_enrichers__code__test_post({binding} as never, {params: {code}}) as Promise<EnricherRecognition>;

/** What a row shows after «Testa Configurazione». */
export type TestStatus = 'found' | 'not_found' | 'conflict' | 'error' | 'not_configured' | 'off' | 'rate_limited';

export interface TestOutcome {
    status: TestStatus;
    /** The name it found (`found`). */
    name: string | null;
}

/** The HTTP status and body of a refusal, whatever shape the client threw it in (`ApiError`, an Axios error). */
function refusal(error: unknown): {status: number; detail: Record<string, unknown> | null} {
    const raw = (error ?? {}) as {status?: number; data?: unknown; response?: {status?: number; data?: unknown}};
    const status = raw.status ?? raw.response?.status ?? 0;
    const data = (raw.data ?? raw.response?.data ?? null) as {detail?: unknown} | null;
    const detail = data && typeof data.detail === 'object' && data.detail !== null ? (data.detail as Record<string, unknown>) : null;
    return {status, detail};
}

/** The answer of a test as a row's state. */
export function testOutcome(answer: EnricherRecognition): TestOutcome {
    const status = answer.status === 'found' || answer.status === 'not_found' || answer.status === 'conflict' ? answer.status : 'error';
    return {status, name: status === 'found' ? (answer.name ?? null) : null};
}

/** A refused test (or search) as a row's state. */
export function refusalOutcome(error: unknown): TestOutcome {
    const {status, detail} = refusal(error);
    if (detail?.error_code === 'NOT_CONFIGURED') return {status: 'not_configured', name: null};
    if (status === 404) return {status: 'off', name: null};
    if (status === 429) return {status: 'rate_limited', name: null};
    return {status: 'error', name: null};
}
