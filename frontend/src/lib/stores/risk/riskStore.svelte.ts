/**
 * Session-scoped cache for the Risk catalog and bulk queries.
 *
 * Query keys preserve array order but sort object keys recursively, so equivalent
 * request objects share one cache entry regardless of construction order.
 */

import {zodiosApi} from '$lib/api';
import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, registerClientSessionReset} from '$lib/stores/app/clientSession';
import {registerPortfolioMutationListener} from '$lib/stores/portfolio/portfolioMutation';

export type RiskCatalogResponse = Awaited<ReturnType<typeof zodiosApi.get_risk_catalog_api_v1_risk_catalog_get>>;
export type RiskCatalogDefinition = NonNullable<RiskCatalogResponse['items']>[number];
export type RiskQueryRequest = Parameters<typeof zodiosApi.query_risk_api_v1_risk_query_post>[0];
export type RiskQueryResponse = Awaited<ReturnType<typeof zodiosApi.query_risk_api_v1_risk_query_post>>;
export type RiskAnalyticResult = NonNullable<RiskQueryResponse['items']>[number];
export type RiskScope = RiskQueryRequest['scope'];
export type RiskScopeKind = RiskScope['kind'];
export type RiskMode = RiskQueryRequest['mode'];

type CacheKey = string;

let catalogCache = $state<RiskCatalogResponse | null>(null);
let queryCache = $state(new Map<CacheKey, RiskQueryResponse>());

let catalogInflight: Promise<RiskCatalogResponse | null> | null = null;
const queryInflight = new Map<CacheKey, Promise<RiskQueryResponse | null>>();
let cacheGeneration = 0;

function canonicalize(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(canonicalize);
    if (value === null || typeof value !== 'object') return value;

    const record = value as Record<string, unknown>;
    const normalized: Record<string, unknown> = {};
    for (const key of Object.keys(record).sort()) {
        if (record[key] !== undefined) normalized[key] = canonicalize(record[key]);
    }
    return normalized;
}

export function makeRiskRequestKey(request: RiskQueryRequest): CacheKey {
    return `${getClientSessionUserId() ?? 'anonymous'}|${JSON.stringify(canonicalize(request))}`;
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

export async function queryRisk(request: RiskQueryRequest, force = false): Promise<RiskQueryResponse | null> {
    const key = makeRiskRequestKey(request);
    if (!force) {
        const cached = queryCache.get(key);
        if (cached) return cached;
    }

    const existing = queryInflight.get(key);
    if (existing) return existing;

    const requestSessionGeneration = getClientSessionGeneration();
    const requestCacheGeneration = cacheGeneration;
    const promise = (async () => {
        try {
            const response = await zodiosApi.query_risk_api_v1_risk_query_post(request);
            if (!isClientSessionCurrent(requestSessionGeneration) || requestCacheGeneration !== cacheGeneration) return null;
            queryCache = new Map(queryCache).set(key, response);
            return response;
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
    queryCache = new Map();
    catalogInflight = null;
    queryInflight.clear();
}

registerClientSessionReset('riskStore', invalidateRisk);
registerPortfolioMutationListener('riskStore', invalidateRisk);
