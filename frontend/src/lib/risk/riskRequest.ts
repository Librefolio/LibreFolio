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
    process: z.infer<typeof schemas.RiskSimulationProcess>;
    regime: z.infer<typeof schemas.RiskSimulationRegime>;
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

export function canonicalizeScope(scope: RiskScope): RiskScope {
    if (scope.kind === 'asset_set') {
        return {...scope, asset_ids: sortedNumbers(scope.asset_ids)};
    }
    if (scope.kind !== 'portfolio') return scope;

    // A portfolio scope narrows by brokers, by assets, or by both, and the two
    // narrowings are independent: a slice carrying only `asset_ids` must be ordered
    // exactly like one carrying only `broker_ids`.
    // `asset_ids` is read structurally because the generated client does not declare
    // it yet; once K4 lands and `api sync` runs, this becomes a typed read and the
    // cast below disappears.
    const assetIds: unknown = (scope as {asset_ids?: unknown}).asset_ids;
    if (!isNumberArray(scope.broker_ids) && !isNumberArray(assetIds)) return scope;

    const normalized = {...scope};
    if (isNumberArray(scope.broker_ids)) normalized.broker_ids = sortedNumbers(scope.broker_ids);
    if (isNumberArray(assetIds)) (normalized as {asset_ids?: number[]}).asset_ids = sortedNumbers(assetIds);
    return normalized;
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

/**
 * Turn an editor state into simulation parameters the server can accept.
 *
 * The two engines take **disjoint** parameter sets, and the server enforces the
 * difference rather than tolerating it (`simulation.py:149-169`): the block
 * bootstrap requires `bootstrap_seed`, forbids `random_seed` and
 * `sobol_start_index`, and only resamples under pseudo-random sampling; the
 * parametric engine requires exactly one of the two parametric seeds, forbids
 * `bootstrap_seed`, and admits no prescribed regime.
 *
 * So this is a branch, not a spread with a couple of optional keys. And the
 * parametric branch states `regime: 'none'` literally instead of forwarding
 * `state.regime`: the pairing is guaranteed at the point of emission, so an
 * editor state that somehow carried a regime alongside GBM still cannot put
 * that combination on the wire.
 */
export function buildSimulationParameters(state: SimulationEditorState): RiskAnalyticParameters {
    const shared = {
        horizon_days: state.horizonDays,
        path_count: state.pathCount,
    };

    if (state.process === 'block_bootstrap') {
        return {
            ...shared,
            process: 'block_bootstrap',
            regime: state.regime,
            // Resampling draws blocks with a pseudo-random generator, so there is
            // no low-discrepancy sequence to walk: `qmc` is refused rather than
            // ignored, and sending the reader's parametric choice here would turn
            // a meaningless option into an unavailable result.
            sampling_method: 'mc',
            bootstrap_seed: state.randomSeed,
        };
    }

    return {
        ...shared,
        process: 'gbm',
        regime: 'none',
        sampling_method: state.samplingMethod,
        ...(state.samplingMethod === 'mc' ? {random_seed: state.randomSeed} : {sobol_start_index: state.sobolStartIndex}),
    };
}
