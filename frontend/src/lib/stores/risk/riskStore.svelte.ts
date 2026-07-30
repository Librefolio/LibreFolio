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

    const requestSessionGeneration = getClientSessionGeneration();
    const requestCacheGeneration = cacheGeneration;
    const promise = (async () => {
        try {
            const response = await zodiosApi.get_risk_catalog_api_v1_risk_catalog_get();
            if (!isClientSessionCurrent(requestSessionGeneration) || requestCacheGeneration !== cacheGeneration) return null;
            catalogCache = response;
            return response;
        } finally {
            if (isClientSessionCurrent(requestSessionGeneration) && requestCacheGeneration === cacheGeneration) {
                catalogInflight = null;
            }
        }
    })();

    catalogInflight = promise;
    return promise;
}

export async function fetchRiskScenarioCatalog(force = false): Promise<RiskScenarioCatalogResponse | null> {
    if (!force && scenarioCatalogCache) return scenarioCatalogCache;
    if (scenarioCatalogInflight) return scenarioCatalogInflight;

    const requestSessionGeneration = getClientSessionGeneration();
    const requestCacheGeneration = cacheGeneration;
    const promise = (async () => {
        try {
            const response = await zodiosApi.get_scenario_catalog_api_v1_risk_scenario_catalog_get();
            if (!isClientSessionCurrent(requestSessionGeneration) || requestCacheGeneration !== cacheGeneration) return null;
            scenarioCatalogCache = response;
            return response;
        } finally {
            if (isClientSessionCurrent(requestSessionGeneration) && requestCacheGeneration === cacheGeneration) {
                scenarioCatalogInflight = null;
            }
        }
    })();

    scenarioCatalogInflight = promise;
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
        } finally {
            if (isClientSessionCurrent(requestSessionGeneration) && requestCacheGeneration === cacheGeneration) {
                queryInflight.delete(key);
            }
        }
    })();

    queryInflight.set(key, promise);
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
