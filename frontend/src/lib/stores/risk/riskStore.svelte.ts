/**
 * Session-scoped cache for the Risk catalog and bulk queries.
 *
 * Query keys sort object keys and canonicalize unordered scope identifiers, so
 * semantically equivalent requests share one cache entry.
 *
 * Two ways to let go of an answer (page cache, phase 1):
 * - `markRiskStale()` — a portfolio mutation, «Aggiorna»: query and eligibility answers are marked
 *   stale and kept, so a panel shows them while it asks again; the catalogs describe the engine,
 *   not the portfolio, and are left alone (E6). Nothing in flight is discarded.
 * - `invalidateRisk()` — a session change, or a host that wants everything asked again: forget
 *   everything, catalogs included, and discard every answer still in flight.
 */

import {zodiosApi} from '$lib/api';
import {canonicalizeRiskRequest, serializeCanonicalRiskRequest} from '$lib/risk/riskRequest';
import type {RiskMode, RiskQueryRequest, RiskQueryResponse, RiskScopeKind} from '$lib/risk/riskRequest';
import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, registerClientSessionReset} from '$lib/stores/app/clientSession';
import {registerPortfolioMutationListener} from '$lib/stores/portfolio/portfolioMutation';
import {EMPTY_VERDICTS, eligibilityBatches, mergeEligibilityAnswers, type EligibilityVerdicts} from '$lib/components/risk/eligibility';

export type RiskCatalogResponse = Awaited<ReturnType<typeof zodiosApi.get_risk_catalog_api_v1_risk_catalog_get>>;
export type RiskCatalogDefinition = NonNullable<RiskCatalogResponse['items']>[number];
export type RiskScenarioCatalogResponse = Awaited<ReturnType<typeof zodiosApi.get_scenario_catalog_api_v1_risk_scenario_catalog_get>>;
export type RiskAnalyticResult = NonNullable<RiskQueryResponse['items']>[number];
export type {RiskMode, RiskQueryRequest, RiskQueryResponse, RiskScope, RiskScopeKind} from '$lib/risk/riskRequest';

type CacheKey = string;

/** An answer, and the mark its question was asked under: asked before the last `markRiskStale()` = stale. */
interface Marked<T> {
    value: T;
    seq: number;
}

interface MarkedFlight<T> {
    promise: Promise<T | null>;
    seq: number;
}

let catalogCache = $state<RiskCatalogResponse | null>(null);
let scenarioCatalogCache = $state<RiskScenarioCatalogResponse | null>(null);
let queryCache = $state(new Map<CacheKey, Marked<RiskQueryResponse>>());
let queryErrorCache = $state(new Map<CacheKey, unknown>());

let catalogInflight: Promise<RiskCatalogResponse | null> | null = null;
let scenarioCatalogInflight: Promise<RiskScenarioCatalogResponse | null> | null = null;
const queryInflight = new Map<CacheKey, MarkedFlight<RiskQueryResponse>>();
// Not reactive: nothing renders the cache, the callers await its answers.
let eligibilityCache = new Map<CacheKey, Marked<EligibilityVerdicts>>();
const eligibilityInflight = new Map<CacheKey, MarkedFlight<EligibilityVerdicts>>();
/** Bumped by `invalidateRisk()` only: an answer asked before it is discarded. */
let cacheGeneration = 0;
/** Bumped by `markRiskStale()`: answers asked before it are stale, and kept. */
let markSeq = 0;

export type RiskQueryCacheStatus = 'idle' | 'loading' | 'success' | 'error';

export interface RiskQueryCacheSnapshot {
    key: CacheKey;
    status: RiskQueryCacheStatus;
    response: RiskQueryResponse | null;
    error: unknown | null;
    /** The cached response was asked before the last `markRiskStale()`: show it, and ask again. */
    stale: boolean;
}

export function makeRiskRequestKey(request: RiskQueryRequest): CacheKey {
    return `${getClientSessionUserId() ?? 'anonymous'}|${serializeCanonicalRiskRequest(request)}`;
}

/**
 * Free an in-flight slot once its request settles, whatever the outcome.
 *
 * Discarding a *response* that arrived after the session or the cache moved on
 * is correct. Keeping its promise parked in the in-flight slot is not: every
 * later caller short-circuits on that slot and gets the same already-resolved
 * `null`, so the data can never load again for the life of the page. The
 * identity check makes sure a newer request's slot is never cleared, and
 * settling through `then(fn, fn)` keeps a rejected request from surfacing as an
 * unhandled rejection while still rejecting for its real callers.
 */
function releaseWhenSettled(promise: Promise<unknown>, release: () => void): void {
    promise.then(release, release);
}

/**
 * How many times in all a risk question is asked while its answer keeps being discarded: the
 * first request plus two re-asks (D374, «come il catalogo»). One constant for the two catalog
 * fetches below and for the controller's base wave and on-demand runs, so the bound cannot
 * drift apart between them. Three, not two: on Asset Global a slow request used to cross more
 * than one 30 s live-price poll, each moving the cache generation. Since the page cache a poll
 * only marks the answers stale; the generation moves with a session change or `invalidateRisk()`.
 */
export const RISK_DISCARD_ATTEMPTS = 3;

export function getRiskQuerySnapshot(request: RiskQueryRequest): RiskQueryCacheSnapshot {
    const key = makeRiskRequestKey(request);
    const entry = queryCache.get(key);
    const response = entry?.value ?? null;
    const error = queryErrorCache.get(key) ?? null;
    let status: RiskQueryCacheStatus = 'idle';
    if (queryInflight.has(key)) status = 'loading';
    else if (queryErrorCache.has(key)) status = 'error';
    else if (response) status = 'success';
    return {key, status, response, error, stale: entry !== undefined && entry.seq < markSeq};
}

export async function fetchRiskCatalog(force = false): Promise<RiskCatalogResponse | null> {
    if (!force && catalogCache) return catalogCache;
    if (catalogInflight) return catalogInflight;

    const promise = (async () => {
        // A response is discarded when the session or the cache generation moved while
        // it was in flight: a session change, or a host's `invalidateRisk()`. A portfolio
        // mutation no longer does — the catalog describes the engine, not the portfolio
        // (E6). A discard is not a failure: it means the answer describes a world that no
        // longer exists, so the right reaction is to ask again rather than hand the caller
        // a null it can only report as an error. Bounded, so a generation that keeps
        // moving cannot spin.
        for (let attempt = 0; attempt < RISK_DISCARD_ATTEMPTS; attempt += 1) {
            const requestSessionGeneration = getClientSessionGeneration();
            const requestCacheGeneration = cacheGeneration;
            const response = await zodiosApi.get_risk_catalog_api_v1_risk_catalog_get();
            if (isClientSessionCurrent(requestSessionGeneration) && requestCacheGeneration === cacheGeneration) {
                catalogCache = response;
                return response;
            }
        }
        return null;
    })();

    catalogInflight = promise;
    releaseWhenSettled(promise, () => {
        if (catalogInflight === promise) catalogInflight = null;
    });
    return promise;
}

export async function fetchRiskScenarioCatalog(force = false): Promise<RiskScenarioCatalogResponse | null> {
    if (!force && scenarioCatalogCache) return scenarioCatalogCache;
    if (scenarioCatalogInflight) return scenarioCatalogInflight;

    const promise = (async () => {
        // Same discard-is-not-failure reasoning as fetchRiskCatalog above.
        for (let attempt = 0; attempt < RISK_DISCARD_ATTEMPTS; attempt += 1) {
            const requestSessionGeneration = getClientSessionGeneration();
            const requestCacheGeneration = cacheGeneration;
            const response = await zodiosApi.get_scenario_catalog_api_v1_risk_scenario_catalog_get();
            if (isClientSessionCurrent(requestSessionGeneration) && requestCacheGeneration === cacheGeneration) {
                scenarioCatalogCache = response;
                return response;
            }
        }
        return null;
    })();

    scenarioCatalogInflight = promise;
    releaseWhenSettled(promise, () => {
        if (scenarioCatalogInflight === promise) scenarioCatalogInflight = null;
    });
    return promise;
}

/**
 * Ask a bulk risk question, or answer it from the cache.
 *
 * A fresh answer is served as it is. A stale one (`markRiskStale`) is asked again, once however
 * many callers, and the promise resolves the fresh answer; `getRiskQuerySnapshot` still hands the
 * stale one to whoever shows it meanwhile. A mark never discards a request in flight: its answer
 * is cached, still stale. Resolves `null` only when the session or `invalidateRisk()` discarded it.
 *
 * A failure rejects. It is remembered (and thrown again without asking) only when there is no
 * answer to fall back on: a failed refresh leaves the stale answer cached, and the next question
 * asks again.
 */
export async function queryRisk(request: RiskQueryRequest, force = false): Promise<RiskQueryResponse | null> {
    const canonicalRequest = canonicalizeRiskRequest(request);
    const key = makeRiskRequestKey(canonicalRequest);
    const cached = queryCache.get(key);
    if (!force) {
        if (cached && cached.seq >= markSeq) return cached.value;
        if (!cached && queryErrorCache.has(key)) throw queryErrorCache.get(key);
    }

    const existing = queryInflight.get(key);
    if (existing && existing.seq >= markSeq) return existing.promise;

    if (force && queryErrorCache.has(key)) {
        queryErrorCache = new Map(queryErrorCache);
        queryErrorCache.delete(key);
    }

    const requestSessionGeneration = getClientSessionGeneration();
    const requestCacheGeneration = cacheGeneration;
    const requestSeq = markSeq;
    const discarded = () => !isClientSessionCurrent(requestSessionGeneration) || requestCacheGeneration !== cacheGeneration;
    const promise = (async () => {
        try {
            const response = await zodiosApi.query_risk_api_v1_risk_query_post(canonicalRequest);
            if (discarded()) return null;
            const stored = queryCache.get(key);
            if (!stored || stored.seq <= requestSeq) queryCache = new Map(queryCache).set(key, {value: response, seq: requestSeq});
            if (queryErrorCache.has(key)) {
                queryErrorCache = new Map(queryErrorCache);
                queryErrorCache.delete(key);
            }
            return response;
        } catch (error) {
            if (discarded()) return null;
            if (!queryCache.has(key)) queryErrorCache = new Map(queryErrorCache).set(key, error);
            throw error;
        }
    })();

    const flight = {promise, seq: requestSeq};
    queryInflight.set(key, flight);
    releaseWhenSettled(promise, () => {
        if (queryInflight.get(key) === flight) queryInflight.delete(key);
    });
    return promise;
}

/**
 * The engine's eligibility verdicts on a set of assets over a period, in a currency (D378).
 *
 * The same question is asked once per session: the key is the user, the period, the currency and the ids
 * sorted, so two pickers — or one remounted when its section reopens — share the answer and its request.
 * A portfolio mutation or a sync marks the verdicts stale (`markRiskStale`): they follow the prices, and
 * a sync is how prices change, so the same question then asks again — and its answer is awaited. A
 * session change forgets them (`invalidateRisk`). The engine takes at most 500 ids a request, so the
 * question is split and the answers merged, as the lab does.
 *
 * Resolves `null` when the session or `invalidateRisk()` moved on while it was asked, like `queryRisk`
 * (a mark does not discard it); a failure rejects and is not kept, so the next question asks again.
 */
export function queryEligibility(assetIds: readonly number[], period: {start: string; end: string}, currency: string): Promise<EligibilityVerdicts | null> {
    const ids = [...new Set(assetIds)].sort((left, right) => left - right);
    if (ids.length === 0) return Promise.resolve(EMPTY_VERDICTS);
    const key = `${getClientSessionUserId() ?? 'anonymous'}|${period.start}|${period.end}|${currency}|${ids.join(',')}`;
    const cached = eligibilityCache.get(key);
    if (cached && cached.seq >= markSeq) return Promise.resolve(cached.value);
    const existing = eligibilityInflight.get(key);
    if (existing && existing.seq >= markSeq) return existing.promise;

    const requestSessionGeneration = getClientSessionGeneration();
    const requestCacheGeneration = cacheGeneration;
    const requestSeq = markSeq;
    const discarded = () => !isClientSessionCurrent(requestSessionGeneration) || requestCacheGeneration !== cacheGeneration;
    const promise = (async () => {
        try {
            const answers = await Promise.all(eligibilityBatches(ids).map((batch) => zodiosApi.asset_eligibility_api_v1_risk_eligibility_post({asset_ids: batch, date_range: {start: period.start, end: period.end || null}, target_currency: currency})));
            if (discarded()) return null;
            const verdicts = mergeEligibilityAnswers(answers);
            const stored = eligibilityCache.get(key);
            if (!stored || stored.seq <= requestSeq) eligibilityCache.set(key, {value: verdicts, seq: requestSeq});
            return verdicts;
        } catch (error) {
            if (discarded()) return null;
            throw error;
        }
    })();

    const flight = {promise, seq: requestSeq};
    eligibilityInflight.set(key, flight);
    releaseWhenSettled(promise, () => {
        if (eligibilityInflight.get(key) === flight) eligibilityInflight.delete(key);
    });
    return promise;
}

export function getRiskDefinition(catalog: RiskCatalogResponse | null | undefined, analyticCode: string): RiskCatalogDefinition | undefined {
    return catalog?.items?.find((definition) => definition.analytic_code === analyticCode);
}

export function hasRiskCapability(catalog: RiskCatalogResponse | null | undefined, analyticCode: string, scope: RiskScopeKind, mode: RiskMode): boolean {
    const definition = getRiskDefinition(catalog, analyticCode);
    return Boolean(definition?.supported_scopes.includes(scope) && definition.supported_modes.includes(mode));
}

/**
 * Mark every query and eligibility answer stale, and keep it (page cache, phase 1): the next question
 * asks again, `getRiskQuerySnapshot` still hands the old answer to the panel that shows it, and an
 * answer in flight still lands. The catalogs are not touched (E6). A remembered failure is dropped,
 * so the next question asks again instead of throwing it.
 */
export function markRiskStale(): void {
    markSeq += 1;
    if (queryErrorCache.size > 0) queryErrorCache = new Map();
}

/** Forget everything, catalogs included, and discard every answer still in flight: a session change. */
export function invalidateRisk(): void {
    cacheGeneration += 1;
    catalogCache = null;
    scenarioCatalogCache = null;
    queryCache = new Map();
    queryErrorCache = new Map();
    catalogInflight = null;
    scenarioCatalogInflight = null;
    queryInflight.clear();
    eligibilityCache = new Map();
    eligibilityInflight.clear();
}

registerClientSessionReset('riskStore', invalidateRisk);
registerPortfolioMutationListener('riskStore', markRiskStale);
