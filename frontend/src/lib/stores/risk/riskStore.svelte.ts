/**
 * Session-scoped cache for the Risk catalog and bulk queries.
 *
 * Query keys sort object keys and canonicalize unordered scope identifiers, so
 * semantically equivalent requests share one cache entry.
 */

import {zodiosApi} from '$lib/api';
import {canonicalizeRiskRequest, serializeCanonicalRiskRequest} from '$lib/risk/riskRequest';
import type {RiskMode, RiskQueryRequest, RiskQueryResponse, RiskScopeKind} from '$lib/risk/riskRequest';
import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, registerClientSessionReset} from '$lib/stores/app/clientSession';
import {registerPortfolioMutationListener} from '$lib/stores/portfolio/portfolioMutation';

export type RiskCatalogResponse = Awaited<ReturnType<typeof zodiosApi.get_risk_catalog_api_v1_risk_catalog_get>>;
export type RiskCatalogDefinition = NonNullable<RiskCatalogResponse['items']>[number];
export type RiskScenarioCatalogResponse = Awaited<ReturnType<typeof zodiosApi.get_scenario_catalog_api_v1_risk_scenario_catalog_get>>;
export type RiskAnalyticResult = NonNullable<RiskQueryResponse['items']>[number];
export type {RiskMode, RiskQueryRequest, RiskQueryResponse, RiskScope, RiskScopeKind} from '$lib/risk/riskRequest';

type CacheKey = string;

let catalogCache = $state<RiskCatalogResponse | null>(null);
let scenarioCatalogCache = $state<RiskScenarioCatalogResponse | null>(null);
let queryCache = $state(new Map<CacheKey, RiskQueryResponse>());
let queryErrorCache = $state(new Map<CacheKey, unknown>());

let catalogInflight: Promise<RiskCatalogResponse | null> | null = null;
let scenarioCatalogInflight: Promise<RiskScenarioCatalogResponse | null> | null = null;
const queryInflight = new Map<CacheKey, Promise<RiskQueryResponse | null>>();
let cacheGeneration = 0;

export type RiskQueryCacheStatus = 'idle' | 'loading' | 'success' | 'error';

export interface RiskQueryCacheSnapshot {
    key: CacheKey;
    status: RiskQueryCacheStatus;
    response: RiskQueryResponse | null;
    error: unknown | null;
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

/** How many times a catalog fetch may be re-issued after its answer is discarded. */
const CATALOG_DISCARD_RETRIES = 3;

export function getRiskQuerySnapshot(request: RiskQueryRequest): RiskQueryCacheSnapshot {
    const key = makeRiskRequestKey(request);
    const response = queryCache.get(key) ?? null;
    const error = queryErrorCache.get(key) ?? null;
    let status: RiskQueryCacheStatus = 'idle';
    if (queryInflight.has(key)) status = 'loading';
    else if (queryErrorCache.has(key)) status = 'error';
    else if (response) status = 'success';
    return {key, status, response, error};
}

export async function fetchRiskCatalog(force = false): Promise<RiskCatalogResponse | null> {
    if (!force && catalogCache) return catalogCache;
    if (catalogInflight) return catalogInflight;

    const promise = (async () => {
        // A response is discarded when the session or the cache generation moved while
        // it was in flight — and on an asset page that happens for a mundane reason:
        // opening the page persists today's price, which notifies the portfolio
        // mutation listeners, which invalidate risk. A discard is not a failure: it
        // means the answer describes a world that no longer exists, so the right
        // reaction is to ask again rather than hand the caller a null it can only
        // report as an error. Bounded, so a generation that keeps moving cannot spin.
        for (let attempt = 0; attempt < CATALOG_DISCARD_RETRIES; attempt += 1) {
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
        for (let attempt = 0; attempt < CATALOG_DISCARD_RETRIES; attempt += 1) {
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

export async function queryRisk(request: RiskQueryRequest, force = false): Promise<RiskQueryResponse | null> {
    const canonicalRequest = canonicalizeRiskRequest(request);
    const key = makeRiskRequestKey(canonicalRequest);
    if (!force) {
        const cached = queryCache.get(key);
        if (cached) return cached;
        if (queryErrorCache.has(key)) throw queryErrorCache.get(key);
    }

    const existing = queryInflight.get(key);
    if (existing) return existing;

    if (force && queryErrorCache.has(key)) {
        queryErrorCache = new Map(queryErrorCache);
        queryErrorCache.delete(key);
    }

    const requestSessionGeneration = getClientSessionGeneration();
    const requestCacheGeneration = cacheGeneration;
    const promise = (async () => {
        try {
            const response = await zodiosApi.query_risk_api_v1_risk_query_post(canonicalRequest);
            if (!isClientSessionCurrent(requestSessionGeneration) || requestCacheGeneration !== cacheGeneration) return null;
            queryCache = new Map(queryCache).set(key, response);
            if (queryErrorCache.has(key)) {
                queryErrorCache = new Map(queryErrorCache);
                queryErrorCache.delete(key);
            }
            return response;
        } catch (error) {
            if (!isClientSessionCurrent(requestSessionGeneration) || requestCacheGeneration !== cacheGeneration) return null;
            queryErrorCache = new Map(queryErrorCache).set(key, error);
            throw error;
        }
    })();

    queryInflight.set(key, promise);
    releaseWhenSettled(promise, () => {
        if (queryInflight.get(key) === promise) queryInflight.delete(key);
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

export function invalidateRisk(): void {
    cacheGeneration += 1;
    catalogCache = null;
    scenarioCatalogCache = null;
    queryCache = new Map();
    queryErrorCache = new Map();
    catalogInflight = null;
    scenarioCatalogInflight = null;
    queryInflight.clear();
}

registerClientSessionReset('riskStore', invalidateRisk);
registerPortfolioMutationListener('riskStore', invalidateRisk);
