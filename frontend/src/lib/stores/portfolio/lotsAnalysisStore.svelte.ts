/**
 * lotsAnalysisStore — session cache for `POST /portfolio/lots/analysis` (page cache, phase 1, E5).
 *
 * One entry per question: the user, the asset, the brokers, the currency, the analyses and the
 * selected lots — the three lists in any order. A fresh answer is served without asking, identical
 * questions in flight share one request, and `force` («Aggiorna») asks again.
 *
 * A portfolio mutation, or «Aggiorna» (`requestPortfolioRefresh`), marks every answer stale and
 * keeps it: `peekLotsAnalysis` still returns it, so the panel shows it while `fetchLotsAnalysis`
 * asks again. A failure rejects and leaves the previous answer where it was; a session change
 * forgets everything.
 *
 * @module stores/portfolio/lotsAnalysisStore
 */

import {zodiosApi} from '$lib/api';
import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, registerClientSessionReset} from '$lib/stores/app/clientSession';
import {registerPortfolioMutationListener} from './portfolioMutation';

type LotsAnalysisEndpoint = typeof zodiosApi.get_lots_analysis_api_v1_portfolio_lots_analysis_post;
export type LotsAnalysisRequest = Parameters<LotsAnalysisEndpoint>[0];
export type LotsAnalysisResponse = Awaited<ReturnType<LotsAnalysisEndpoint>>;

interface Entry {
    response: LotsAnalysisResponse;
    /** The mark the question was asked under: asked before the last mark = stale. */
    seq: number;
}

interface Flight {
    promise: Promise<LotsAnalysisResponse | null>;
    seq: number;
}

// Not reactive: the panel reads an answer when it asks, it does not render the cache.
const cache = new Map<string, Entry>();
const inflight = new Map<string, Flight>();
/** Bumped by a session change: an answer asked before it is discarded. */
let generation = 0;
/** Bumped by a portfolio mutation or «Aggiorna»: answers asked before it are stale, and kept. */
let markSeq = 0;

const UNORDERED_LISTS = ['broker_ids', 'requested_analyses', 'selected_lot_ids'] as const;

function canonical(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(canonical);
    if (value !== null && typeof value === 'object') {
        return Object.fromEntries(
            Object.entries(value as Record<string, unknown>)
                .filter(([, entry]) => entry !== undefined)
                .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0))
                .map(([name, entry]) => [name, canonical(entry)]),
        );
    }
    return value;
}

/** The user, then the question with its object keys sorted and its three unordered lists sorted. */
function lotsKey(body: LotsAnalysisRequest): string {
    const question: Record<string, unknown> = {...(body as Record<string, unknown>)};
    for (const name of UNORDERED_LISTS) {
        const list = question[name];
        if (Array.isArray(list)) question[name] = [...list].sort((left, right) => String(left).localeCompare(String(right), undefined, {numeric: true}));
    }
    return `${getClientSessionUserId() ?? 'anonymous'}|${JSON.stringify(canonical(question))}`;
}

/** What the cache holds for this question, read synchronously: `{response, stale}`, or null. */
export function peekLotsAnalysis(body: LotsAnalysisRequest): {response: LotsAnalysisResponse; stale: boolean} | null {
    const entry = cache.get(lotsKey(body));
    return entry ? {response: entry.response, stale: entry.seq < markSeq} : null;
}

/**
 * The analysis of this question: from the cache when fresh, else asked once per question.
 *
 * Resolves the answer; resolves `null` when a session change discarded it; rejects when the request
 * fails, leaving any previous answer cached (stale) and remembering nothing, so the next call asks again.
 */
export function fetchLotsAnalysis(body: LotsAnalysisRequest, force = false): Promise<LotsAnalysisResponse | null> {
    const key = lotsKey(body);
    const entry = cache.get(key);
    if (!force && entry && entry.seq >= markSeq) return Promise.resolve(entry.response);
    const existing = inflight.get(key);
    if (existing && existing.seq >= markSeq) return existing.promise;

    const requestGeneration = generation;
    const requestSessionGeneration = getClientSessionGeneration();
    const discarded = () => requestGeneration !== generation || !isClientSessionCurrent(requestSessionGeneration);
    const flight = {seq: markSeq} as Flight;
    inflight.set(key, flight);
    flight.promise = (async () => {
        try {
            const response = await zodiosApi.get_lots_analysis_api_v1_portfolio_lots_analysis_post(body);
            if (discarded()) return null;
            const stored = cache.get(key);
            if (!stored || stored.seq <= flight.seq) cache.set(key, {response, seq: flight.seq});
            return response;
        } catch (error) {
            if (discarded()) return null;
            throw error;
        } finally {
            if (inflight.get(key) === flight) inflight.delete(key);
        }
    })();
    return flight.promise;
}

/** Forget every answer and discard every request in flight. */
export function resetLotsAnalysisCache(): void {
    generation += 1;
    cache.clear();
    inflight.clear();
}

registerClientSessionReset('lotsAnalysisStore', resetLotsAnalysisCache);
registerPortfolioMutationListener('lotsAnalysisStore', () => {
    markSeq += 1;
});
