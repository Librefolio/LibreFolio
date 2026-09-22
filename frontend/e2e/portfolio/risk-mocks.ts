/**
 * Shared scaffolding for the risk E2E specs.
 *
 * Extracted verbatim from `risk-analysis.spec.ts` when that 817-line file was
 * split into one helper module and three specs with three different owners.
 * Nothing here changed shape in the move: the bodies are the originals.
 *
 * ⚠️ `resultFor` encodes the SHAPE OF THE RISK PAYLOAD. When the backend
 * changes that shape — the underwater series and histogram bins (K1), the
 * acquired KPIs (K8) — this mock has to change with it. Otherwise the specs
 * keep passing while serving a payload the backend no longer produces, and a
 * stale mock does not fail: it reassures.
 *
 * ⚠️ This module is ADDITIVE for its owner. `risk-asset-detail.spec.ts` is the
 * net that proves Asset Detail was left untouched (D8, D47, D82): whatever it
 * imports may be extended, never removed and never renamed.
 */
import {expect, type Page} from '../fixtures/playwright';

import {navigateTo} from '../fixtures/auth-helpers';

export type RiskScope = {kind: 'asset'; asset_id: number} | {kind: 'asset_set'; asset_ids: number[]} | {kind: 'portfolio'; broker_ids?: number[] | null};

export interface RiskAnalyticRequest {
    instance_id: string;
    analytic_code: string;
    parameters?: Record<string, unknown>;
}

export interface RiskRequest {
    scope: RiskScope;
    date_range: {start: string; end?: string | null};
    target_currency: string;
    mode: 'historical' | 'current_composition';
    composition_policy?: 'current_buy_and_hold' | null;
    analytics: RiskAnalyticRequest[];
}

export interface RiskMockOptions {
    unavailableVar?: boolean;
}

const CATALOG = {
    items: [
        // `current_composition` is advertised so the E2E exercises L3's *primary*
        // branch. The card falls back to the historical KPI when the backend does not
        // offer this mode, and a catalogue that withheld it here would have pinned the
        // fallback forever: green, and measuring the road users do not take.
        definition('historical_kpi', 'kpi', ['asset', 'portfolio'], ['historical', 'current_composition'], 'historicalKpi', 20),
        definition('correlation', 'matrix', ['asset_set', 'portfolio'], ['historical', 'current_composition'], 'correlation', 2),
        definition('risk_contribution', 'contribution', ['portfolio'], ['current_composition'], 'riskContribution', 20),
        definition('stress', 'stress', ['asset', 'asset_set', 'portfolio'], ['current_composition'], 'stress', 1),
        definition('comparison', 'comparison', ['asset', 'portfolio'], ['historical', 'current_composition'], 'comparison', 20),
        definition('historical_var', 'var_cvar', ['asset', 'portfolio'], ['historical', 'current_composition'], 'historicalVar', 20),
        definition('simulation', 'simulation', ['asset', 'portfolio'], ['current_composition'], 'simulation', 30),
    ],
};

const SCENARIO_CATALOG = {
    items: [
        {
            source: 'built_in',
            source_file: 'historical/custom_period.yml',
            scenario: {
                schema_version: 1,
                id: 'custom_period',
                kind: 'historical_replay',
                tags: ['custom'],
                name: {
                    en: 'Custom period',
                    it: 'Periodo personalizzato',
                    fr: 'Période personnalisée',
                    es: 'Período personalizado',
                },
                description: {
                    en: 'Choose the historical dates to replay.',
                    it: 'Scegli le date storiche da riprodurre.',
                    fr: 'Choisissez les dates historiques à rejouer.',
                    es: 'Elige las fechas históricas que se reproducirán.',
                },
                defaults: {
                    start: null,
                    end: null,
                    missing_history_policy: 'manual_proxy_or_exclude',
                    composition_policy: 'current_buy_and_hold',
                },
                editable: {
                    dates: true,
                    missing_history_policy: true,
                    proxies: true,
                    exclusions: true,
                },
                limits: {
                    minimum_calendar_days: 1,
                    maximum_calendar_days: null,
                },
            },
        },
        {
            source: 'built_in',
            source_file: 'hypothetical/global_risk_off.yml',
            scenario: {
                schema_version: 1,
                id: 'global_risk_off',
                kind: 'hypothetical_shock',
                tags: ['global', 'risk_off'],
                name: {
                    en: 'Global risk-off',
                    it: 'Avversione globale al rischio',
                    fr: 'Aversion mondiale au risque',
                    es: 'Aversión global al riesgo',
                },
                description: {
                    en: 'Editable asset-class shocks.',
                    it: 'Shock modificabili per classe di asset.',
                    fr: "Chocs modifiables par classe d'actifs.",
                    es: 'Choques editables por clase de activo.',
                },
                allowed_dimensions: ['asset_class'],
                defaults: {
                    dimension: 'asset_class',
                    bucket_shocks: {
                        STOCK: -0.2,
                        ETF: -0.15,
                        FUND: -0.15,
                        BOND: -0.05,
                        CRYPTO: -0.3,
                        CROWDFUND: -0.1,
                        HOLD: -0.05,
                        INDEX: -0.2,
                        OTHER: 0,
                    },
                },
                editable: {
                    dimension: false,
                    bucket_shocks: true,
                    manual_overrides: true,
                },
                limits: {
                    minimum_shock: -1,
                    maximum_shock: 1,
                    maximum_buckets: 100,
                },
            },
        },
    ],
    geography_groups: [],
    status: {
        schema_version: 1,
        loaded_at: '2026-01-31T12:00:00Z',
        built_in_count: 2,
        host_count: 0,
        warning_count: 0,
    },
    warnings: [],
};

function definition(analyticCode: string, outputKind: string, supportedScopes: string[], supportedModes: string[], translationKey: string, minObservations: number) {
    return {
        analytic_code: analyticCode,
        name_i18n_key: `risk.analytics.${translationKey}.name`,
        description_i18n_key: `risk.analytics.${translationKey}.description`,
        output_kind: outputKind,
        supported_scopes: supportedScopes,
        supported_modes: supportedModes,
        parameters_schema: {},
        min_observations: minObservations,
        algorithm_version: 'e2e-mock-v1',
    };
}

function metadata(request: RiskRequest, analytic: RiskAnalyticRequest) {
    const observations = 60;
    const calendarDays = 87;
    const brokerIds = request.scope.kind === 'portfolio' ? (request.scope.broker_ids ?? null) : null;
    return {
        analyzed_range: {
            start: request.date_range.start,
            end: request.date_range.end ?? request.date_range.start,
        },
        frequency: 'daily',
        n_observations: observations,
        calendar_days: calendarDays,
        annualization_factor: (observations * 365) / calendarDays,
        coverage: 0.92,
        currency: request.target_currency,
        scope: request.scope.kind,
        scope_reference: request.scope.kind === 'portfolio' ? (brokerIds ? `portfolio:${brokerIds.join(',')}` : 'portfolio:all') : request.scope.kind,
        ...(brokerIds ? {broker_ids: brokerIds} : {}),
        ...(request.scope.kind === 'portfolio' ? {composition_as_of: request.date_range.end ?? request.date_range.start} : {}),
        method: analytic.analytic_code,
        params: analytic.parameters ?? {},
        mode: request.mode,
        ...(request.composition_policy ? {composition_policy: request.composition_policy} : {}),
        return_basis: analytic.analytic_code === 'historical_kpi' && request.scope.kind === 'portfolio' ? 'twrr' : 'price_only',
        excluded_assets: [],
        algorithm_version: 'e2e-mock-v1',
        computed_at: '2026-01-31T12:00:00Z',
    };
}

function dataQuality() {
    return {
        issues: [
            {
                domain: 'asset',
                code: 'STALE_PRICE',
                severity: 'warning',
                message_i18n_key: 'dataQuality.stalePrice',
                message_params: {count: 1},
                count: 1,
                affected_asset_ids: [1],
            },
        ],
        carried_forward_price_points: 3,
        carried_forward_fx_points: 1,
        carried_forward_price_asset_ids: [1],
        carried_forward_fx_pairs: ['EUR-USD'],
        data_quality_status: 'carried_forward',
    };
}

function matrixAssetIds(request: RiskRequest): number[] {
    if (request.scope.kind === 'asset_set') return request.scope.asset_ids.slice(0, 8);
    return [1, 2];
}

function resultFor(request: RiskRequest, analytic: RiskAnalyticRequest, options: RiskMockOptions): Record<string, unknown> {
    const base = {
        instance_id: analytic.instance_id,
        analytic_code: analytic.analytic_code,
        metadata: metadata(request, analytic),
        data_quality: dataQuality(),
        warnings: [],
    };

    if (analytic.analytic_code === 'historical_var' && options.unavailableVar) {
        return {
            ...base,
            status: 'unavailable',
            output: null,
            error: {
                code: 'insufficient_history',
                message: 'E2E unavailable fixture',
            },
        };
    }

    switch (analytic.analytic_code) {
        case 'historical_kpi':
            return {
                ...base,
                status: 'ok',
                output: {
                    kind: 'kpi',
                    volatility: 0.142,
                    max_drawdown: -0.087,
                    max_drawdown_duration_days: 19,
                    sharpe: 1.21,
                    sortino: 1.68,
                },
            };
        case 'correlation': {
            const assetIds = matrixAssetIds(request);
            return {
                ...base,
                status: 'partial',
                warnings: [{code: 'low_pair_coverage', message: 'E2E partial fixture'}],
                output: {
                    kind: 'matrix',
                    asset_ids: assetIds,
                    cells: assetIds.flatMap((rowAssetId) =>
                        assetIds.map((columnAssetId) => ({
                            row_asset_id: rowAssetId,
                            column_asset_id: columnAssetId,
                            value: rowAssetId === columnAssetId ? 1 : 0.35,
                            observations: 60,
                            coverage: rowAssetId === columnAssetId ? 1 : 0.82,
                            status: 'ok',
                        })),
                    ),
                },
            };
        }
        case 'risk_contribution':
            return {
                ...base,
                status: 'ok',
                output: {
                    kind: 'contribution',
                    portfolio_volatility: 0.13,
                    cash_weight: 0.05,
                    items: [
                        {asset_id: 1, weight: 0.6, marginal_contribution: 0.11, component_contribution: 0.08, percentage_contribution: 0.65},
                        {asset_id: 2, weight: 0.35, marginal_contribution: 0.13, component_contribution: 0.05, percentage_contribution: 0.35},
                    ],
                },
            };
        case 'historical_var':
            return {
                ...base,
                status: 'ok',
                output: {
                    kind: 'var_cvar',
                    confidence_level: 0.95,
                    horizon_days: 1,
                    observations: 60,
                    value_at_risk: 0.021,
                    conditional_value_at_risk: 0.031,
                },
            };
        case 'comparison': {
            const comparisonAssetId = Number(analytic.parameters?.comparison_asset_id ?? 2);
            return {
                ...base,
                status: 'ok',
                output: {
                    kind: 'comparison',
                    comparison_asset_id: comparisonAssetId,
                    active_return: 0.034,
                    tracking_error: 0.071,
                    information_ratio: 0.48,
                    correlation: 0.62,
                    beta: 0.91,
                    observations: 60,
                    series: [
                        {date: '2025-01-01', primary_cumulative_return: 0, comparison_cumulative_return: 0, primary_drawdown: 0, comparison_drawdown: 0},
                        {date: '2025-02-01', primary_cumulative_return: 0.04, comparison_cumulative_return: 0.02, primary_drawdown: -0.01, comparison_drawdown: -0.015},
                        {date: '2025-03-01', primary_cumulative_return: 0.08, comparison_cumulative_return: 0.045, primary_drawdown: 0, comparison_drawdown: -0.005},
                    ],
                },
            };
        }
        case 'stress': {
            const method = String(analytic.parameters?.method ?? 'hypothetical');
            const assetId = request.scope.kind === 'asset' ? request.scope.asset_id : matrixAssetIds(request)[0];
            if (method === 'historical_replay') {
                const proxyAssets = (analytic.parameters?.proxy_assets ?? []) as Array<{asset_id: number; proxy_asset_id: number}>;
                const excludedAssetIds = (analytic.parameters?.excluded_assets ?? []) as number[];
                const proxy = proxyAssets.find((mapping) => mapping.asset_id === assetId);
                const excluded = excludedAssetIds.includes(assetId);
                const replayRange = (analytic.parameters?.replay_range ?? request.date_range) as {start: string; end: string};
                const replayReturn = excluded ? 0 : -0.12;
                return {
                    ...base,
                    status: proxy || excluded ? 'partial' : 'ok',
                    metadata: {
                        ...base.metadata,
                        analyzed_range: replayRange,
                        historical_replay_audit: {
                            proxy_count: proxyAssets.length,
                            proxy_assets: proxyAssets,
                            excluded_count: excludedAssetIds.length,
                            excluded_assets: excludedAssetIds.map((excludedAssetId) => ({
                                asset_id: excludedAssetId,
                                reason: 'manual_exclusion',
                                weight: request.scope.kind === 'asset' ? 1 : 0.5,
                                treatment: request.scope.kind === 'portfolio' ? 'zero_return_residual' : 'omitted_from_replay',
                            })),
                            excluded_weight_total: excludedAssetIds.length > 0 ? (request.scope.kind === 'asset' ? 1 : 0.5 * excludedAssetIds.length) : 0,
                            missing_history_policy: String(analytic.parameters?.missing_history_policy ?? 'manual_proxy_or_exclude'),
                            composition_policy: 'current_buy_and_hold',
                            proxy_series_usage: 'returns_only',
                        },
                    },
                    output: {
                        kind: 'stress',
                        method: 'historical_replay',
                        portfolio_return: replayReturn,
                        impact_amount: String(replayReturn * 10000),
                        replay_range: replayRange,
                        impacts: excluded
                            ? []
                            : [
                                  {
                                      asset_id: assetId,
                                      ...(proxy ? {return_source_asset_id: proxy.proxy_asset_id} : {}),
                                      weight: 1,
                                      shock_return: replayReturn,
                                      contribution_return: replayReturn,
                                      impact_amount: String(replayReturn * 10000),
                                      metadata_fallback: false,
                                      bucket_audit: [],
                                  },
                              ],
                        configured_buckets: [],
                    },
                };
            }

            const dimension = String(analytic.parameters?.dimension ?? 'asset_class');
            const bucketShocks = (analytic.parameters?.bucket_shocks ?? {OTHER: 0}) as Record<string, number>;
            const configuredBucketIds = Object.keys(bucketShocks).sort((left, right) => left.localeCompare(right));
            const appliedBucketId = configuredBucketIds.find((bucketId) => bucketShocks[bucketId] !== 0) ?? configuredBucketIds[0] ?? 'OTHER';
            const shock = bucketShocks[appliedBucketId] ?? 0;
            return {
                ...base,
                status: 'ok',
                output: {
                    kind: 'stress',
                    method: 'hypothetical',
                    dimension,
                    portfolio_return: shock,
                    impact_amount: String(shock * 10000),
                    classification_coverage: 1,
                    impacts: [
                        {
                            asset_id: assetId,
                            weight: 1,
                            shock_return: shock,
                            contribution_return: shock,
                            impact_amount: String(shock * 10000),
                            dimension,
                            metadata_fallback: false,
                            bucket_audit: [
                                {
                                    exposure_bucket_id: appliedBucketId,
                                    exposure: 1,
                                    candidate_bucket_ids: [appliedBucketId],
                                    applied_bucket_id: appliedBucketId,
                                    bucket_shock: shock,
                                    shock_contribution: shock,
                                    rule: 'direct',
                                },
                            ],
                        },
                    ],
                    configured_buckets: configuredBucketIds.map((bucketId) => ({
                        bucket_id: bucketId,
                        shock: bucketShocks[bucketId],
                        applied_asset_count: bucketId === appliedBucketId ? 1 : 0,
                        asset_exposure_total: bucketId === appliedBucketId ? 1 : 0,
                        contribution_return: bucketId === appliedBucketId ? shock : 0,
                    })),
                },
            };
        }
        case 'simulation': {
            const horizonDays = Number(analytic.parameters?.horizon_days ?? 365);
            const pathCount = Number(analytic.parameters?.path_count ?? 8192);
            const samplingMethod = String(analytic.parameters?.sampling_method ?? 'mc');
            return {
                ...base,
                status: 'ok',
                output: {
                    kind: 'simulation',
                    process: 'gbm',
                    sampling_method: samplingMethod,
                    horizon_days: horizonDays,
                    path_count: pathCount,
                    drift_estimator: 'historical_log_mle',
                    covariance_estimator: 'sample_log_returns',
                    aggregation_policy: 'current_buy_and_hold',
                    costs_included: false,
                    cash_flows_included: false,
                    inflation_included: false,
                    rebalanced: false,
                    percentile_bands: [
                        {day: 0, p05: 0, p50: 0, p95: 0},
                        {day: Math.max(1, Math.floor(horizonDays / 2)), p05: -0.08, p50: 0.04, p95: 0.18},
                        {day: horizonDays, p05: -0.13, p50: 0.09, p95: 0.31},
                    ],
                    terminal_mean_return: 0.095,
                    terminal_volatility: 0.14,
                    probability_of_loss: 0.27,
                },
            };
        }
        default:
            return {
                ...base,
                status: 'failed',
                output: null,
                error: {
                    code: 'analytic_not_found',
                    message: `Unexpected E2E analytic ${analytic.analytic_code}`,
                },
            };
    }
}

export async function installRiskMocks(page: Page, options: RiskMockOptions = {}): Promise<RiskRequest[]> {
    const requests: RiskRequest[] = [];

    await page.route('**/api/v1/risk/catalog', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(CATALOG),
        });
    });

    await page.route('**/api/v1/risk/scenario-catalog', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(SCENARIO_CATALOG),
        });
    });

    await page.route('**/api/v1/risk/query', async (route) => {
        const request = route.request().postDataJSON() as RiskRequest;
        requests.push(request);
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                items: request.analytics.map((analytic) => resultFor(request, analytic, options)),
            }),
        });
    });

    return requests;
}

/**
 * Every section of the risk panel is gated on the capability catalog, so an
 * absent section means "unsupported" *or* "not loaded yet". The panel publishes
 * which one via `data-catalog`; wait for it before asserting on any section, or
 * the assertion is really a bet on fetch latency.
 */
export async function waitForRiskCatalog(page: Page): Promise<void> {
    await expect(page.getByTestId('risk-analysis-panel').first()).toHaveAttribute('data-catalog', 'ready', {timeout: 20_000});
}

export async function openDashboardRisk(page: Page): Promise<void> {
    await navigateTo(page, '/dashboard');
    await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
    await page.getByTestId('dashboard-tab-risk').click();
    await expect(page.getByTestId('dashboard-risk-tab')).toBeVisible({timeout: 8_000});
    await waitForRiskCatalog(page);
}

export async function openFirstBrokerRisk(page: Page): Promise<number> {
    await navigateTo(page, '/brokers');
    const firstBroker = page.getByTestId(/^broker-card-\d+$/).first();
    await expect(firstBroker).toBeVisible({timeout: 8_000});
    await firstBroker.click();
    await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 10_000});
    const match = page.url().match(/\/brokers\/(\d+)/);
    if (!match) throw new Error('Broker detail URL must contain a numeric broker ID.');
    await page.getByTestId('broker-tab-risk').click();
    await expect(page.getByTestId('broker-risk-tab')).toBeVisible({timeout: 8_000});
    await waitForRiskCatalog(page);
    return Number(match[1]);
}
export async function brokerWithHoldings(page: Page): Promise<{brokerId: number; assetIds: number[]}> {
    const brokersResponse = await page.request.get('/api/v1/brokers');
    expect(brokersResponse.ok()).toBe(true);
    const brokersPayload = (await brokersResponse.json()) as {items?: Array<{id: number}>};

    for (const broker of brokersPayload.items ?? []) {
        const reportResponse = await page.request.post('/api/v1/portfolio/report', {
            data: {
                broker_ids: [broker.id],
                include_summary: true,
                include_history: false,
                include_allocation_history: false,
                include_breakdown: false,
                include_positions_contribution: false,
            },
        });
        if (!reportResponse.ok()) continue;
        const report = (await reportResponse.json()) as {summary?: {holdings?: Array<{asset_id: number}>} | null};
        const assetIds = [...new Set((report.summary?.holdings ?? []).map((holding) => holding.asset_id))].sort((left, right) => left - right);
        if (assetIds.length > 0) return {brokerId: broker.id, assetIds};
    }

    throw new Error('No seeded broker has holdings. Check populate_mock_data.py.');
}

/** The asset IDs the panel currently shows as selected, sorted and capped like the request payload. */
export async function selectedAssetIds(page: Page): Promise<number[]> {
    const ids = await page.getByTestId(/^risk-selected-asset-\d+$/).evaluateAll((nodes) => nodes.map((node) => Number(node.getAttribute('data-testid')?.replace('risk-selected-asset-', ''))));
    return ids
        .filter(Number.isInteger)
        .sort((left, right) => left - right)
        .slice(0, 100);
}
