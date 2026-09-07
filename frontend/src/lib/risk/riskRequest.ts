import {schemas, zodiosApi} from '$lib/api';
import type {z} from 'zod';

export type RiskQueryRequest = Parameters<typeof zodiosApi.query_risk_api_v1_risk_query_post>[0];
export type RiskQueryResponse = Awaited<ReturnType<typeof zodiosApi.query_risk_api_v1_risk_query_post>>;
export type RiskAnalyticRequest = RiskQueryRequest['analytics'][number];
export type RiskAnalyticParameters = Record<string, z.infer<typeof schemas.JsonValue>>;
export type RiskScope = RiskQueryRequest['scope'];
export type RiskScopeKind = RiskScope['kind'];
export type RiskMode = RiskQueryRequest['mode'];

export type RiskScenarioDimension = z.infer<typeof schemas.RiskScenarioDimension>;
export type RiskSamplingStrategy = z.infer<typeof schemas.RiskSamplingStrategy>;
export type RiskScenarioMissingHistoryPolicy = z.infer<typeof schemas.RiskScenarioMissingHistoryPolicy>;
export type RiskHistoricalReplayProxyAsset = z.infer<typeof schemas.RiskHistoricalReplayProxyAsset>;

export interface HistoricalReplayEditorState {
    start: string;
    end: string;
    missingHistoryPolicy: RiskScenarioMissingHistoryPolicy;
    proxyAssets: RiskHistoricalReplayProxyAsset[];
    excludedAssetIds: number[];
}

export interface HypotheticalShockEditorState {
    dimension: RiskScenarioDimension;
    bucketShocks: Record<string, number>;
}

export interface SimulationEditorState {
    samplingMethod: RiskSamplingStrategy;
    horizonDays: number;
    pathCount: number;
    randomSeed: number;
    sobolStartIndex: number;
}

export type SimulationView = 'evolution' | 'terminal_distribution';

interface BuildRiskQueryRequestInput {
    scope: RiskScope;
    dateStart: string;
    dateEnd: string;
    targetCurrency: string;
    mode: RiskMode;
    analytics: RiskQueryRequest['analytics'];
    compositionPolicy?: RiskQueryRequest['composition_policy'];
}

function sortedNumbers(values: readonly number[]): number[] {
    return [...values].sort((left, right) => left - right);
}

function isNumberArray(value: unknown): value is number[] {
    return Array.isArray(value) && value.every((item: unknown): item is number => typeof item === 'number');
}

function isProxyAsset(value: unknown): value is RiskHistoricalReplayProxyAsset {
    if (value === null || typeof value !== 'object') return false;
    const candidate = value as Record<string, unknown>;
    return typeof candidate.asset_id === 'number' && typeof candidate.proxy_asset_id === 'number';
}

function canonicalizeAnalyticParameters(parameters: RiskAnalyticParameters): RiskAnalyticParameters {
    const normalized = {...parameters};
    const excludedAssets = normalized.excluded_assets;
    const proxyAssets = normalized.proxy_assets;

    if (isNumberArray(excludedAssets)) {
        normalized.excluded_assets = sortedNumbers(excludedAssets);
    }
    if (Array.isArray(proxyAssets) && proxyAssets.every(isProxyAsset)) {
        normalized.proxy_assets = [...proxyAssets].sort((left, right) => left.asset_id - right.asset_id || left.proxy_asset_id - right.proxy_asset_id);
    }

    return normalized;
}

function canonicalizeScope(scope: RiskScope): RiskScope {
    if (scope.kind === 'asset_set') {
        return {...scope, asset_ids: sortedNumbers(scope.asset_ids)};
    }
    if (scope.kind === 'portfolio' && isNumberArray(scope.broker_ids)) {
        return {...scope, broker_ids: sortedNumbers(scope.broker_ids)};
    }
    return scope;
}

function stableValue(value: unknown): unknown {
    if (Array.isArray(value)) return value.map(stableValue);
    if (value === null || typeof value !== 'object') return value;

    const record = value as Record<string, unknown>;
    const normalized: Record<string, unknown> = {};
    for (const key of Object.keys(record).sort()) {
        if (record[key] !== undefined) normalized[key] = stableValue(record[key]);
    }
    return normalized;
}

export function canonicalizeRiskRequest(request: RiskQueryRequest): RiskQueryRequest {
    const normalized = {
        ...request,
        scope: canonicalizeScope(request.scope),
        target_currency: request.target_currency.trim().toUpperCase(),
        analytics: request.analytics.map((analytic) => ({
            ...analytic,
            parameters: canonicalizeAnalyticParameters(analytic.parameters ?? {}),
        })),
    };
    return schemas.RiskQueryRequest.parse(normalized);
}

export function serializeCanonicalRiskRequest(request: RiskQueryRequest): string {
    return JSON.stringify(stableValue(canonicalizeRiskRequest(request)));
}

export function buildRiskAnalyticRequest(instanceId: string, analyticCode: string, parameters: RiskAnalyticParameters = {}): RiskAnalyticRequest {
    return schemas.RiskAnalyticRequest.parse({
        instance_id: instanceId,
        analytic_code: analyticCode,
        parameters,
    });
}

export function buildRiskQueryRequest(input: BuildRiskQueryRequestInput): RiskQueryRequest {
    return canonicalizeRiskRequest({
        scope: input.scope,
        date_range: {start: input.dateStart, end: input.dateEnd},
        target_currency: input.targetCurrency,
        mode: input.mode,
        ...(input.compositionPolicy === undefined ? {} : {composition_policy: input.compositionPolicy}),
        analytics: input.analytics,
    });
}

export function buildHistoricalReplayParameters(state: HistoricalReplayEditorState): RiskAnalyticParameters {
    return canonicalizeAnalyticParameters({
        method: 'historical_replay',
        replay_range: {start: state.start, end: state.end},
        missing_history_policy: state.missingHistoryPolicy,
        proxy_assets: state.proxyAssets,
        excluded_assets: state.excludedAssetIds,
    });
}

export function buildHypotheticalShockParameters(state: HypotheticalShockEditorState): RiskAnalyticParameters {
    return {
        method: 'hypothetical',
        dimension: state.dimension,
        bucket_shocks: {...state.bucketShocks},
    };
}

export function buildSimulationParameters(state: SimulationEditorState): RiskAnalyticParameters {
    return {
        process: 'gbm',
        sampling_method: state.samplingMethod,
        horizon_days: state.horizonDays,
        path_count: state.pathCount,
        ...(state.samplingMethod === 'mc' ? {random_seed: state.randomSeed} : {sobol_start_index: state.sobolStartIndex}),
    };
}
