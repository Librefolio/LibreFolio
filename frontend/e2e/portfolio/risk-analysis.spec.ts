import {expect, test, type Locator, type Page} from '../fixtures/playwright';

import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage} from '../assets/assets-helpers';

type RiskScope = {kind: 'asset'; asset_id: number} | {kind: 'asset_set'; asset_ids: number[]} | {kind: 'portfolio'; broker_ids?: number[] | null};

interface RiskAnalyticRequest {
    instance_id: string;
    analytic_code: string;
    parameters?: Record<string, unknown>;
}

interface RiskRequest {
    scope: RiskScope;
    date_range: {start: string; end?: string | null};
    target_currency: string;
    mode: 'historical' | 'current_composition';
    composition_policy?: 'current_buy_and_hold' | null;
    analytics: RiskAnalyticRequest[];
}

interface RiskMockOptions {
    unavailableVar?: boolean;
    /**
     * Makes the historical replay refuse to run until this holding is left out.
     *
     * `stress.py:451` stops at the **first** holding without usable history and
     * refuses the whole replay, naming it in `details`. That is not a dead end
     * but a question, and the only answer the reader can give is an exclusion —
     * which has to travel on the *next* request for anything to change.
     *
     * A stub that answered every replay with `ok` left that round trip
     * unexercised, so the accumulating-exclusion loop was reachable only in
     * production. Refusing until the id appears in `excluded_assets`, and
     * succeeding once it does, is the smallest model of the server that makes
     * the loop observable — and it is opt-in, so every other test is unmoved.
     */
    replayBlockedAssetId?: number;
    /**
     * Answers the simulation with `unavailable`, the way a busy worker, a
     * timeout or a series too short does.
     *
     * `schemas/risk.py:1056` forbids an `unavailable` result from carrying an
     * output, so this is not an unlikely corner: it is the **only** shape that
     * branch can take. Every step of L4 renders on `{#if output}`, so before
     * the level disclosed its health the reader got a blank panel with no cause
     * — and no fixture in this suite had ever produced the state that reveals
     * it. Opt-in, so every other test is unmoved.
     */
    unavailableSimulation?: boolean;
    /**
     * Warnings to hang on every result carrying one of these analytic codes.
     *
     * The wave already ships exactly one warning — `correlation` answers
     * `partial` with `E2E partial fixture` — and **no level renders
     * correlation**, so until this option existed nothing in the four-level
     * panel ever had a reason to display. The suite was green over a surface it
     * never reached.
     *
     * Keyed by code rather than by instance on purpose: `historical_var` is
     * asked twice in one wave, so one entry here puts the *same sentence* on two
     * results — which is the only way to exercise the deduplication, and the
     * reason `ResultReason` carries `occurrences` at all.
     *
     * Opt-in, like `replayBlockedAssetId` above: with it absent
     * `withInjectedWarnings` hands the result straight back, so every other
     * test's payload is unchanged down to the byte.
     */
    analyticWarnings?: Record<string, Array<{code: string; message: string}>>;
    /**
     * Turns every result carrying one of these analytic codes into an outright
     * failure, with the given code.
     *
     * The twin of `analyticWarnings`, and it exists for the same reason: the
     * fixture answers **every** code the panel asks for, so no level in this
     * suite has ever rendered a failure. A level that computed nothing looked
     * identical to one whose analytic does not support the scope, and said so
     * in a sentence that blamed the reader's data.
     *
     * The code travels rather than a sentence, because that is the real
     * asymmetry: a warning arrives as backend prose shown verbatim, an error
     * arrives as an identifier the UI has to word itself. Asserting on the
     * wording is therefore asserting on the i18n catalogue — which is the point
     * of the unknown-code case, where the only correct behaviour is to *not*
     * render `risk.errors.<code>`.
     *
     * Opt-in: absent, `withInjectedError` hands the result straight back.
     */
    analyticErrors?: Record<string, string>;
}

/**
 * The horizon the four-level panel asks its "bad month" VaR for.
 *
 * Mirrors `MONTHLY_VAR_HORIZON_DAYS` in `riskAnalysisHelpers`, on purpose rather
 * than imported: the dashboard test asserts that the panel really puts this
 * number on the wire, so a drift in the product shows up as a red here instead
 * of a constant that silently agrees with whatever was sent.
 */
const MONTHLY_VAR_HORIZON_DAYS = 21;

/**
 * A loss as the panel writes it: a real minus sign (U+2212), not a hyphen.
 *
 * Spelled with an escape because the two are indistinguishable in a diff, and a
 * test that fails on an invisible character costs an hour to read.
 */
function loss(percent: string): string {
    return `\u2212${percent}`;
}

const CATALOG = {
    items: [
        definition('historical_kpi', 'kpi', ['asset', 'portfolio'], ['historical'], 'historicalKpi', 20),
        definition('correlation', 'matrix', ['asset_set', 'portfolio'], ['historical', 'current_composition'], 'correlation', 2),
        definition('risk_contribution', 'contribution', ['portfolio'], ['current_composition'], 'riskContribution', 20),
        definition('stress', 'stress', ['asset', 'asset_set', 'portfolio'], ['current_composition'], 'stress', 1),
        definition('comparison', 'comparison', ['asset', 'portfolio'], ['historical', 'current_composition'], 'comparison', 20),
        definition('historical_var', 'var_cvar', ['asset', 'portfolio'], ['historical', 'current_composition'], 'historicalVar', 20),
        definition('drawdown_summary', 'drawdown', ['asset', 'portfolio'], ['historical'], 'drawdownSummary', 20),
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

    if (analytic.analytic_code === 'simulation' && options.unavailableSimulation) {
        return {
            ...base,
            status: 'unavailable',
            output: null,
            error: {
                code: 'insufficient_history',
                message: 'E2E unavailable simulation fixture',
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
                    // The four acquired measures. Signs follow the schema's own
                    // declared convention — drawdowns and returns negative,
                    // dispersions non-negative — so a fixture with a positive
                    // `worst_realization` would teach the panel a shape the
                    // backend forbids, and the validator enforces
                    // `max_drawdown <= CDaR <= DaR <= 0`: −0,087 ≤ −0,079 ≤ −0,071 ≤ 0.
                    //
                    // ⚠️ The confidence is deliberately 90% and NOT 95%. It is a
                    // parameter the backend publishes, not a constant, and the
                    // panel must read the field rather than assume the usual
                    // value. A fixture at 95% would let a hard-coded "95%" pass
                    // forever; at 90% that shortcut fails the moment it is taken.
                    worst_realization: -0.038,
                    worst_realization_date: '2023-11-21',
                    drawdown_at_risk: -0.071,
                    conditional_drawdown_at_risk: -0.079,
                    drawdown_confidence_level: 0.9,
                    ulcer_index: 0.041,
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
        case 'historical_var': {
            // Two VaRs travel in one historical wave — a 1-day and a ~1-month —
            // and only `instance_id` tells them apart. A fixture answering both
            // with the same figures would let `resultByInstance` be swapped for
            // `resultByCode` and still pass, which is exactly the mix-up that
            // helper was written to prevent. The horizon-1 branch keeps its
            // original numbers byte for byte, and no other scope in this file
            // ever asks for a longer horizon, so nothing existing moves.
            //
            // The month is deliberately *not* the day scaled by √21 (which would
            // be 14,2%): the backend compounds real overlapping windows, so the
            // two are independent observations, and a fixture that scaled one
            // from the other would teach the panel a model the server never ran.
            const longHorizon = Number(analytic.parameters?.horizon_days ?? 1) > 1;
            return {
                ...base,
                status: 'ok',
                output: {
                    kind: 'var_cvar',
                    confidence_level: 0.95,
                    horizon_days: longHorizon ? MONTHLY_VAR_HORIZON_DAYS : 1,
                    observations: 60,
                    value_at_risk: longHorizon ? 0.068 : 0.021,
                    conditional_value_at_risk: longHorizon ? 0.094 : 0.031,
                    // The distribution behind the number, and the cut located in it.
                    //
                    // ⚠️ The grid is deliberately NON-uniform — three bins are
                    // twice as wide as the others. `validate_return_bins` polices
                    // only that lower bounds ascend, not that widths match, so a
                    // uniform fixture would let the renderer divide the width by
                    // the bin count and still look right. Here that shortcut
                    // draws the wrong picture.
                    //
                    // The counts sum to 60, the declared `observations`: a
                    // histogram whose bars contradict its own total would be
                    // teaching a shape the backend never emits.
                    //
                    // Only the day carries bins. The month having none is what
                    // proves the histogram reads the *daily instance* and not
                    // merely the first `historical_var` result it finds.
                    return_bins: longHorizon
                        ? []
                        : [
                              {lower_bound: -0.06, upper_bound: -0.04, count: 1},
                              {lower_bound: -0.04, upper_bound: -0.03, count: 2},
                              {lower_bound: -0.03, upper_bound: -0.02, count: 5},
                              {lower_bound: -0.02, upper_bound: -0.01, count: 12},
                              {lower_bound: -0.01, upper_bound: 0.01, count: 28},
                              {lower_bound: 0.01, upper_bound: 0.02, count: 9},
                              {lower_bound: 0.02, upper_bound: 0.04, count: 3},
                          ],
                    // Falls inside bin 2 by the half-open rule −0,03 ≤ −0,021 < −0,02,
                    // and strictly beyond bins 0 and 1. Never on a boundary: a
                    // fixture sitting exactly on an edge would pass under both the
                    // half-open rule and the closed one it exists to distinguish.
                    var_bin_edge: longHorizon ? null : -0.021,
                },
            };
        }
        case 'drawdown_summary':
            // Kept numerically consistent with the `historical_kpi` fixture above:
            // a mock that contradicts itself would teach the panel a shape the
            // backend never emits, and still pass.
            return {
                ...base,
                status: 'ok',
                output: {
                    kind: 'drawdown',
                    current_drawdown: -0.032,
                    current_peak_date: '2024-02-05',
                    current_drawdown_duration_days: 41,
                    // Dated at the source, and deliberately at IRREGULAR intervals.
                    // Only trading days appear, so the series is shorter than the
                    // window it spans; a renderer that spread the points evenly
                    // would misplace every interior one, and an evenly-spaced
                    // fixture would never catch it doing so.
                    //
                    // Numerically consistent with the rest of this output: the
                    // deepest point is −0,087 on the max-drawdown trough date, the
                    // curve returns to 0 at the current peak date, and the last
                    // point is the −0,032 current drawdown.
                    underwater_series: [
                        {date: '2023-11-14', drawdown: 0},
                        {date: '2023-11-21', drawdown: -0.052},
                        {date: '2023-12-03', drawdown: -0.087},
                        {date: '2024-01-10', drawdown: -0.031},
                        {date: '2024-02-05', drawdown: 0},
                        {date: '2024-03-18', drawdown: -0.032},
                    ],
                    maximum_drawdown: -0.087,
                    maximum_drawdown_peak_date: '2023-11-14',
                    maximum_drawdown_trough_date: '2023-12-03',
                    maximum_drawdown_recovery_status: 'open',
                    maximum_drawdown_recovery_date: null,
                    maximum_drawdown_duration_days: 19,
                    maximum_drawdown_recovered_ratio: 0.63,
                    remaining_to_peak_ratio: 0.033,
                    available_start: '2023-09-01',
                    available_end: '2024-03-17',
                    n_observations: 60,
                    coverage: 0.98,
                    calculation_basis: 'daily_close',
                    return_basis: 'twrr',
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
                if (options.replayBlockedAssetId !== undefined && !excludedAssetIds.includes(options.replayBlockedAssetId)) {
                    // The server's own shape, down to the branch: `stress.py:458`
                    // sends `insufficient_history` with `return_source_asset_id`
                    // **equal to** `asset_id` when the holding itself has no
                    // history, and `invalid_parameters` with a different one when
                    // a stand-in is the thing at fault. Only the first has an
                    // answer the reader can give, and `replayBlocker` reads those
                    // two fields to decide whether to offer it — so a stub that
                    // set them carelessly would exercise the wrong branch while
                    // still producing a red-looking-green blocker panel.
                    return {
                        ...base,
                        status: 'unavailable',
                        output: null,
                        error: {
                            code: 'insufficient_history',
                            message: `Asset ${options.replayBlockedAssetId} requires a manual proxy or explicit exclusion`,
                            details: {
                                asset_id: options.replayBlockedAssetId,
                                return_source_asset_id: options.replayBlockedAssetId,
                                reason: 'insufficient_history',
                            },
                        },
                    };
                }
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

/**
 * Append the configured warnings to one result, leaving every other alone.
 *
 * Applied at the boundary rather than folded into `resultFor`, which builds
 * `warnings` in **two** places — once in `base`, and again in the `correlation`
 * branch which *replaces* the array wholesale. An injection written into `base`
 * would therefore be silently dropped for exactly one analytic, and a stub that
 * quietly discards what the test asked it to send is worse than one that never
 * offered the option: the test would fail describing the panel.
 *
 * Returns the very same object when nothing is configured for the code. That is
 * not an optimisation, it is the guarantee: the fixtures the pinned tests are
 * written against cannot move if no new object is ever built for them.
 */
function withInjectedWarnings(result: Record<string, unknown>, options: RiskMockOptions): Record<string, unknown> {
    const injected = options.analyticWarnings?.[String(result.analytic_code)];
    if (!injected || injected.length === 0) return result;
    return {...result, warnings: [...((result.warnings as unknown[] | undefined) ?? []), ...injected]};
}

/**
 * Replaces a result with the failure its analytic would have returned.
 *
 * `output: null` and `status: 'failed'` together, never one without the other:
 * `schemas/risk.py` forbids a failed result from carrying an output, so a stub
 * that kept the output while flipping the status would model a payload the
 * backend cannot emit — and the level would render its rows *and* its error.
 */
function withInjectedError(result: Record<string, unknown>, options: RiskMockOptions): Record<string, unknown> {
    const code = options.analyticErrors?.[String(result.analytic_code)];
    if (!code) return result;
    return {...result, status: 'failed', output: null, error: {code, message: `E2E injected ${code}`}};
}

async function installRiskMocks(page: Page, options: RiskMockOptions = {}): Promise<RiskRequest[]> {    const requests: RiskRequest[] = [];

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
                items: request.analytics.map((analytic) => withInjectedWarnings(withInjectedError(resultFor(request, analytic, options), options), options)),
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
async function waitForRiskCatalog(page: Page): Promise<void> {
    await expect(page.getByTestId('risk-analysis-panel').first()).toHaveAttribute('data-catalog', 'ready', {timeout: 20_000});
}

/**
 * The same gate, for the four-level panel that Dashboard and Broker Detail mount.
 *
 * A second helper rather than a widened first one, and deliberately so: Asset
 * Detail still mounts the legacy `risk-analysis-panel`, and a locator matching
 * either testid would report "ready" for whichever panel the page happened to
 * have — including the wrong one. One helper per component keeps the question
 * unambiguous, and leaves `waitForRiskCatalog` untouched for the asset specs.
 *
 * Waits for the capability catalogue, then for the base wave to land. The second
 * half is what makes every section assertion below a statement about the answer
 * instead of a bet on fetch latency.
 */
async function waitForRiskLevels(page: Page): Promise<Locator> {
    const panel = page.getByTestId('risk-levels-panel');
    await expect(panel).toHaveAttribute('data-catalog', 'ready', {timeout: 20_000});
    await expect(panel).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
    return panel;
}

async function openDashboardRisk(page: Page): Promise<Locator> {
    await navigateTo(page, '/dashboard');
    await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
    await page.getByTestId('dashboard-tab-risk').click();
    await expect(page.getByTestId('dashboard-risk-tab')).toBeVisible({timeout: 8_000});
    return waitForRiskLevels(page);
}

/**
 * Open L4 and leave it demonstrably open, whichever state it was in.
 *
 * Asks before clicking rather than toggling blind: L4 starts closed today, but a
 * helper that assumes so would *close* it the day the panel remembers the
 * reader's last drawer, and the caller would then be asserting on an absence it
 * caused itself.
 *
 * Ends on the rungs being on screen, not merely on the section's attribute:
 * `data-open` flips synchronously with the click, so it says the drawer was
 * asked to open, not that anything inside it mounted.
 */
async function openLevel4(panel: Locator): Promise<Locator> {
    const level4 = panel.getByTestId('risk-level-4');
    await expect(level4).toBeVisible({timeout: 10_000});
    if ((await level4.getAttribute('data-open')) !== 'true') await panel.getByTestId('risk-level-4-toggle').click();
    await expect(level4).toHaveAttribute('data-open', 'true');
    await expect(panel.getByTestId('risk-l4')).toBeVisible({timeout: 8_000});
    return level4;
}

async function openFirstBrokerRisk(page: Page): Promise<{brokerId: number; panel: Locator}> {
    await navigateTo(page, '/brokers');
    const firstBroker = page.getByTestId(/^broker-card-\d+$/).first();
    await expect(firstBroker).toBeVisible({timeout: 8_000});
    await firstBroker.click();
    await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 10_000});
    const match = page.url().match(/\/brokers\/(\d+)/);
    if (!match) throw new Error('Broker detail URL must contain a numeric broker ID.');
    await page.getByTestId('broker-tab-risk').click();
    await expect(page.getByTestId('broker-risk-tab')).toBeVisible({timeout: 8_000});
    return {brokerId: Number(match[1]), panel: await waitForRiskLevels(page)};
}

/**
 * Come back to the Broker Detail page the caller is already on, cold.
 *
 * A *document* load, not a route change, and the distinction is the whole reason
 * this helper exists. The capability catalogue is cached in a module
 * (`catalogCache` in `riskStore`), so a client-side navigation hands the next
 * panel a catalogue that is already present when it mounts, and every launcher
 * gated on that catalogue works by accident. Only a cold load puts a network
 * round trip between the panel mounting and the catalogue arriving, which is the
 * window a launcher can fall into.
 *
 * `reload` rather than a constructed URL: the tab lives in the query string
 * (`handleTabChange` → `buildTabUrl`), so coming back lands on Risk with the
 * panel mounted by the first render instead of by a later click — what a reader
 * who bookmarked or refreshed the Risk tab actually gets. The tab is then
 * checked rather than assumed: if it ever stopped being addressable the reload
 * would land on Overview, and a test waiting on a panel that never mounts would
 * be blaming the wrong thing.
 */
async function reloadBrokerRiskCold(page: Page): Promise<Locator> {
    await page.reload();
    await page.waitForSelector('html[data-i18n-ready="true"]', {timeout: 15_000});
    await expect(page.getByTestId('broker-risk-tab')).toBeVisible({timeout: 10_000});
    return waitForRiskLevels(page);
}

async function openFirstAssetDetail(page: Page): Promise<number> {
    await goToAssetsPage(page);
    const firstCard = page.getByTestId(/^asset-card-\d+$/).first();
    await expect(firstCard).toBeVisible({timeout: 8_000});
    const testId = await firstCard.getAttribute('data-testid');
    const assetId = Number(testId?.replace('asset-card-', ''));
    if (!Number.isInteger(assetId) || assetId <= 0) throw new Error('Seeded asset card must expose a numeric data-testid.');
    await firstCard.click();
    await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 12_000});
    await expect(page.getByTestId('asset-detail-tab-overview')).toBeVisible({timeout: 12_000});
    return assetId;
}

async function brokerWithHoldings(page: Page): Promise<{brokerId: number; assetIds: number[]}> {
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
async function selectedAssetIds(page: Page): Promise<number[]> {
    const ids = await page.getByTestId(/^risk-selected-asset-\d+$/).evaluateAll((nodes) => nodes.map((node) => Number(node.getAttribute('data-testid')?.replace('risk-selected-asset-', ''))));
    return ids
        .filter(Number.isInteger)
        .sort((left, right) => left - right)
        .slice(0, 100);
}

/** The analytic codes the mocked catalogue advertises for `portfolio` in one mode. */
function advertisedForPortfolio(mode: RiskRequest['mode']): Set<string> {
    return new Set(CATALOG.items.filter((item) => item.supported_scopes.includes('portfolio') && item.supported_modes.includes(mode)).map((item) => item.analytic_code));
}

/** Every analytic the panel asked for in one mode, across all portfolio requests. */
function portfolioAnalytics(requests: RiskRequest[], mode: RiskRequest['mode']): RiskAnalyticRequest[] {
    return requests.filter((request) => request.scope.kind === 'portfolio' && request.mode === mode).flatMap((request) => request.analytics);
}

/**
 * Pick the L3 benchmark from the picker on `panel`, and say which one was picked.
 *
 * The dropdown is driven through `role=combobox` rather than a `-trigger` testid
 * because `AssetSelect` does **not** forward its `testid` to the `SearchSelect`
 * it wraps: `risk-l3-benchmark-select` names the wrapper div only, so
 * `risk-l3-benchmark-select-trigger` does not exist in the DOM. (The neighbouring
 * `risk-comparison-asset-select-trigger` works because that one is a bare
 * `SearchSelect` given a `testId` directly.)
 *
 * The id is read off the option rather than hardcoded: which assets are offered
 * depends on the scope's own holdings, since `excludeAssetIds` drops everything
 * already in the portfolio so nothing is compared against itself.
 *
 * Ends on the choice being in force on the page that made it — the click having
 * landed is what the caller is owed, and it is a stronger statement than the
 * dropdown merely having closed.
 */
async function chooseBenchmark(page: Page, panel: Locator): Promise<number> {
    const select = panel.getByTestId('risk-l3-benchmark-select');
    await expect(select).toBeVisible({timeout: 10_000});
    await select.getByRole('combobox').click();

    // Retried, not slept on: `AssetSelect` fetches the asset cache on mount, so
    // an open dropdown legitimately shows "loading" before it shows options.
    const option = page.getByTestId(/^search-select-option-\d+$/).first();
    await expect(option).toBeVisible({timeout: 10_000});
    const optionTestId = await option.getAttribute('data-testid');
    const assetId = Number(optionTestId?.replace('search-select-option-', ''));
    if (!Number.isInteger(assetId) || assetId <= 0) throw new Error(`Benchmark option must expose a numeric asset id, got ${optionTestId}.`);

    await option.click();
    await expect(panel.getByTestId('risk-l3-benchmark')).toHaveAttribute('data-benchmark-id', String(assetId), {timeout: 8_000});
    return assetId;
}

/**
 * Put the shared benchmark back to "never chosen".
 *
 * Required rather than tidy: the choice is persisted, and `L3Benchmark` launches
 * a `comparison` run by itself whenever it finds one stored. A test that walked
 * away from its pick would hand every later mount an extra analytic nobody asked
 * for — an intermittent that shows up in full runs and evaporates on re-run alone.
 *
 * Matched by suffix because the key is user-scoped (`lf_<userId>_...`) and a test
 * has no business knowing the numeric id of the account it logged in as. The
 * blast radius is still exactly the key this spec writes, not "whatever is in
 * storage".
 *
 * Never throws: it runs in a `finally`, where the only thing worse than a failed
 * cleanup is a failed cleanup that hides the failure it was cleaning up after.
 */
async function clearRiskBenchmark(page: Page): Promise<void> {
    await page
        .evaluate(() => {
            for (const key of Object.keys(localStorage)) {
                if (key.endsWith('_risk_benchmark_asset')) localStorage.removeItem(key);
            }
        })
        .catch(() => undefined);
}

/** Every `comparison_asset_id` put on the wire by portfolio requests for one broker scope. */
function comparisonAssetIds(requests: RiskRequest[], brokerIds: number[]): number[] {
    const wanted = brokerIds.join(',');
    return requests
        .filter((request) => request.scope.kind === 'portfolio' && (request.scope.broker_ids ?? []).join(',') === wanted)
        .flatMap((request) => request.analytics)
        .filter((analytic) => analytic.analytic_code === 'comparison')
        .map((analytic) => Number(analytic.parameters?.comparison_asset_id));
}

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('Risk analysis functional integration', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('dashboard renders base analytics, quality, warnings, sync and capability gate', async ({page}) => {
        const requests = await installRiskMocks(page);

        // Armed before the first navigation: a request is an *edge*, and a
        // listener attached after the click would be unable to say whether the
        // closed level had already paid for its catalogue.
        const scenarioCatalogCalls: string[] = [];
        page.on('request', (request) => {
            if (request.url().includes('/api/v1/risk/scenario-catalog')) scenarioCatalogCalls.push(request.url());
        });

        const panel = await openDashboardRisk(page);

        await expect(page.getByTestId('risk-beta-banner')).toBeVisible();
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(1);

        // Dashboard's scope is the whole portfolio, so it must carry no subset
        // label. Broker Detail asserts the mirror image; the pair is what makes
        // the label mean something, since its text is translated and unassertable.
        await expect(panel.getByTestId('risk-scope-label')).toHaveCount(0);

        // --- L1: the scale of harm, every figure straight from the stub -------
        await expect(panel.getByTestId('risk-level-1')).toBeVisible();
        // A bad day and a bad month are separate observations carried by two
        // instances of one analytic: equal numbers here would pass even if the
        // panel read both rows off whichever result happened to arrive first.
        await expect(panel.getByTestId('risk-l1-card-day-value')).toHaveText(loss('3.1%'));
        await expect(panel.getByTestId('risk-l1-card-month-value')).toHaveText(loss('9.4%'));
        // The worst fall arrives as `-0.087` under the `le=0` convention and must
        // read as a positive magnitude of 8,7%, not as a dropped contradiction.
        await expect(panel.getByTestId('risk-l1-card-worst-value')).toHaveText(loss('8.7%'));
        await expect(panel.getByTestId('risk-l1-duration-worst')).toBeVisible();
        await expect(panel.getByTestId('risk-l1-recovery-worst')).toBeVisible();
        // Where the portfolio stands now is a different question from its worst
        // moment, and the drawdown summary is what answers it.
        await expect(panel.getByTestId('risk-l1-card-current-value')).toHaveText(loss('3.2%'));

        // --- L1: the acquired measures, as second rows and never as cards -----
        //
        // The count is the assertion. These four measures refine two figures that
        // are already on screen, so promoting any of them to a card of its own
        // would restate the change of scale this level exists to remove. Four
        // cards is the contract: three rungs plus the current drawdown.
        //
        // ⚠️ Scoped to the grid's DIRECT children on purpose. A plain
        // `[data-testid^="risk-l1-card-"]` counts 28, not 4: `RiskMetricCard`
        // derives its label, value, caption, technical name, docs link and accent
        // testids from the card's own, so the prefix that reads like "the cards"
        // matches every part of every card. Anchoring to the grid counts objects
        // instead of fragments, and still fails if a fifth card appears.
        await expect(panel.getByTestId('risk-l1-cards').locator('> div > [data-testid^="risk-l1-card-"]')).toHaveCount(4);
        await expect(panel.getByTestId('risk-l1-worst-realization')).toContainText(loss('3.8%'));
        await expect(panel.getByTestId('risk-l1-worst-realization-date')).toContainText('2023-11-21');
        // ⚠️ 90%, from the fixture's `drawdown_confidence_level`. The usual 95% is
        // a default the backend publishes, not a constant: this assertion turns red
        // the moment anyone writes the familiar number into the label.
        await expect(panel.getByTestId('risk-l1-drawdown-at-risk')).toContainText('90');
        await expect(panel.getByTestId('risk-l1-drawdown-at-risk')).toContainText(loss('7.1%'));
        await expect(panel.getByTestId('risk-l1-conditional-drawdown-at-risk')).toContainText(loss('7.9%'));

        // --- L1: the two representations that had no reader until now ---------
        //
        // Six points, and the count matters: the series is shorter than the
        // window it spans because only trading days appear. A chart fed by an
        // interpolation would have some other number here.
        await expect(panel.getByTestId('risk-l1-underwater-chart')).toHaveAttribute('data-point-count', '6');
        // The ulcer index is the caption of that curve, never a figure on its own:
        // alone it is a dimensionless number with no reading.
        await expect(panel.getByTestId('risk-l1-ulcer')).toBeVisible();

        await expect(panel.getByTestId('risk-l1-histogram-bars')).toHaveAttribute('data-bin-count', '7');
        await expect(panel.getByTestId('risk-l1-histogram-observations')).toContainText('60');
        // The cut lands in bin 2 by the half-open rule −0,03 ≤ −0,021 < −0,02, and
        // in exactly one bin. Asserting the neighbours is what separates "the
        // right bar" from "a bar": an off-by-one would still highlight something.
        await expect(panel.getByTestId('risk-l1-histogram-bin-2')).toHaveAttribute('data-holds-cut', 'true');
        await expect(panel.getByTestId('risk-l1-histogram-bars').locator('[data-holds-cut="true"]')).toHaveCount(1);
        // Two bars lie entirely beyond the cut. This is the shading that gives the
        // threshold a meaning: without it the marker points at nothing.
        await expect(panel.getByTestId('risk-l1-histogram-bars').locator('[data-below-cut="true"]')).toHaveCount(2);
        await expect(panel.getByTestId('risk-l1-histogram-bin-2')).toHaveAttribute('data-below-cut', 'false');

        // Nothing came back degraded, so nothing is disclosed. The mirror of the
        // two-entry assertion in the unavailable test: without this half, a
        // disclosure row that rendered unconditionally — or one wired to a
        // constant — would satisfy that half and never be noticed here.
        await expect(panel.getByTestId('risk-level-1-health')).toHaveCount(0);
        await expect(panel.getByTestId('risk-level-3-health')).toHaveCount(0);

        // --- L2: weight against risk contribution -----------------------------
        await expect(panel.getByTestId('risk-level-2')).toBeVisible();
        await expect(panel.getByTestId('risk-l2-weight-1')).toHaveText('60.0%');
        await expect(panel.getByTestId('risk-l2-contribution-1')).toHaveText('65.0%');
        await expect(panel.getByTestId('risk-l2-divergence-1')).toHaveText('+5.0pp');
        // The holding that produces more risk than it weighs leads: the ordering
        // is the argument, and an unordered list would answer a different question.
        // `.first()` is safe on a collection this test's own stub populated.
        await expect(panel.getByTestId('risk-l2-rows').locator('[data-testid^="risk-l2-row-"]').first()).toHaveAttribute('data-testid', 'risk-l2-row-1');
        // The rows are fractions of NAV, so they describe less than the whole
        // portfolio whenever something cannot be priced. The residual is read off
        // the attribute rather than the rendered line, because the label beside it
        // is translated and a text assertion would pass or fail by locale.
        await expect(panel.getByTestId('risk-l2-uncovered')).toHaveAttribute('data-uncovered', '0.05');

        // --- L3: is the risk being paid for -----------------------------------
        await expect(panel.getByTestId('risk-level-3')).toBeVisible();
        await expect(panel.getByTestId('risk-l3-sortino-value')).toHaveText('1.68');
        await expect(panel.getByTestId('risk-l3-sharpe-value')).toHaveText('1.21');
        await expect(panel.getByTestId('risk-l3-volatility-value')).toHaveText('14.2%');

        // --- Provenance: what the figures were computed over -------------------
        // `RiskResultFrame` publishes this and only the legacy panel uses it, so
        // the four levels rendered measurements with no window attached. The same
        // asset pair correlates 0.96 over one month and 0.67 over one year: a
        // number without its window is an assertion, not a measurement.
        const l1Metadata = panel.getByTestId('risk-level-1-metadata');
        await expect(l1Metadata).toBeVisible();

        // **Two rows, and the fixture did not have to be bent to produce them.**
        // `historical_kpi` reports `twrr` while `historical_var` and
        // `drawdown_summary` report `price_only`, so L1 aggregates figures
        // computed on two different bases — something no surface has ever said.
        // A design that picked one result as representative would print a single
        // basis over all three, which is the failure this split exists to avoid.
        await expect(l1Metadata).toHaveAttribute('data-rows', '2');

        // Open it the way a reader would. Asserting through a closed `<details>`
        // would pass on `textContent` alone and prove nothing about the
        // disclosure working.
        await l1Metadata.locator('summary').click();
        await expect(panel.getByTestId('risk-level-1-metadata-observations').first()).toBeVisible();
        await expect(panel.getByTestId('risk-level-1-metadata-observations').first()).toHaveText('60');

        const bases = panel.getByTestId('risk-level-1-metadata-basis');
        await expect(bases).toHaveCount(2);
        // Read off the attribute, which carries the backend token, rather than
        // off the rendered sentence, which is translated.
        await expect(panel.locator('[data-testid="risk-level-1-metadata-row"][data-codes="historical_var drawdown_summary"]')).toHaveCount(1);
        await expect(panel.locator('[data-testid="risk-level-1-metadata-row"][data-codes="historical_kpi"]')).toHaveCount(1);

        // The guard of `translateOrRaw` on the real catalogue: `RiskResultFrame:108`
        // builds this same key unguarded, and a basis it has not seen prints
        // `risk.returnBasis.<value>` on screen. Neither row may do that.
        for (const text of await bases.allTextContents()) {
            expect(text).not.toContain('risk.returnBasis.');
            expect(text.trim().length).toBeGreaterThan(0);
        }

        // --- Data quality -----------------------------------------------------
        // Scoped to the panel: the dashboard renders a banner of its own, and an
        // unscoped locator would be satisfied by the wrong one.
        const banner = panel.getByTestId('data-quality-banner');
        await expect(banner).toBeVisible();
        const bannerToggle = banner.getByTestId('data-quality-toggle');
        await expect(bannerToggle).toBeVisible();
        // Grouped mode starts folded, but asking beats assuming: a banner that
        // opened itself would otherwise be closed by an unconditional click.
        if ((await bannerToggle.getAttribute('aria-expanded')) !== 'true') await bannerToggle.click();
        await expect(bannerToggle).toHaveAttribute('aria-expanded', 'true');
        // The issue the risk payload carried, not merely "a banner exists".
        await expect(banner.getByTestId('data-quality-issue-STALE_PRICE')).toBeVisible();
        await expect(banner.getByTestId('data-quality-issue-STALE_PRICE')).toHaveAttribute('data-severity', 'warning');

        // --- The capability gate ----------------------------------------------
        // The old hidden `risk-frontier-capability` probe is gone with the legacy
        // panel. What it stood for is not: the catalogue decides what may be
        // asked, and the wire is where that decision is now observable.
        await expect.poll(() => portfolioAnalytics(requests, 'historical').map((analytic) => analytic.analytic_code), {timeout: 15_000}).toEqual(expect.arrayContaining(['historical_kpi', 'historical_var', 'drawdown_summary']));
        await expect.poll(() => portfolioAnalytics(requests, 'current_composition').length, {timeout: 15_000}).toBeGreaterThan(0);

        // Nothing the catalogue does not advertise for this scope *and* this
        // mode. Derived from CATALOG rather than restated, so the gate cannot go
        // vacuous when the fixture changes.
        const outsideCatalog = (mode: RiskRequest['mode']) => [...new Set(portfolioAnalytics(requests, mode).map((analytic) => analytic.analytic_code))].filter((code) => !advertisedForPortfolio(mode).has(code));
        expect(outsideCatalog('historical')).toEqual([]);
        expect(outsideCatalog('current_composition')).toEqual([]);

        // The two VaRs are one analytic asked twice, told apart by horizon. One
        // instance would collapse L1's day and month into the same rung.
        const varHorizons = portfolioAnalytics(requests, 'historical')
            .filter((analytic) => analytic.analytic_code === 'historical_var')
            .map((analytic) => Number(analytic.parameters?.horizon_days));
        expect([...new Set(varHorizons)].sort((left, right) => left - right)).toEqual([1, MONTHLY_VAR_HORIZON_DAYS]);

        // L4 is closed, and a closed level costs nothing: neither its analytics
        // (both advertised for this scope, so only the drawer can be keeping them
        // off the wire) nor its scenario catalogue.
        const onDemandCodes = ['stress', 'simulation'];
        expect(portfolioAnalytics(requests, 'current_composition').filter((analytic) => onDemandCodes.includes(analytic.analytic_code))).toEqual([]);
        expect(scenarioCatalogCalls).toEqual([]);
        await expect(panel.getByTestId('risk-level-4')).toHaveAttribute('data-open', 'false');

        await panel.getByTestId('risk-level-4-toggle').click();
        await expect(panel.getByTestId('risk-level-4')).toHaveAttribute('data-open', 'true');
        // …and opening it is what pays for the catalogue, once.
        await expect.poll(() => scenarioCatalogCalls.length, {timeout: 10_000}).toBe(1);

        // --- Sync -------------------------------------------------------------
        const syncButton = panel.getByTestId('risk-sync-button');
        await expect(syncButton).toBeEnabled();
        await syncButton.click();
        await expect(page.getByTestId('page-sync-modal')).toBeVisible({timeout: 5_000});
    });

    test('per-analytic unavailable state remains isolated', async ({page}) => {
        await installRiskMocks(page, {unavailableVar: true});
        const panel = await openDashboardRisk(page);

        // The barrier first. "No VaR row" is also true of a panel that never
        // rendered, so L1 has to be demonstrably present and fed by the same wave
        // that carried the unavailable result before its absence means anything.
        await expect(panel.getByTestId('risk-l1-cards')).toBeVisible({timeout: 8_000});
        await expect(panel.getByTestId('risk-l1-card-worst-value')).toHaveText(loss('8.7%'));

        // Both VaR instances came back `unavailable`. Their cards are omitted,
        // never zero-filled: an absent measurement and a measurement of zero are
        // different claims, and a 0,0% card would read as "it cannot hurt you".
        //
        // ⚠️ The count of 1 on the worst card is not decoration. Two absences
        // prove nothing on their own: a typo in the selector family would also
        // return zero, and would do it for every scenario, silently. Proving that
        // *this exact shape* resolves to 1 where the measurement exists is what
        // makes the two zeros beside it a measurement rather than a spelling.
        await expect(panel.getByTestId('risk-l1-card-worst')).toHaveCount(1);
        await expect(panel.getByTestId('risk-l1-card-day')).toHaveCount(0);
        await expect(panel.getByTestId('risk-l1-card-month')).toHaveCount(0);
        await expect(panel.getByTestId('risk-l1-empty')).toHaveCount(0);

        // …and the omission is *disclosed*, which is the other half of the same
        // claim: a level that quietly drops the rungs it could not compute shows
        // a shorter list, and a shorter list is indistinguishable from a
        // portfolio with less to say. Only one of the two is worth retrying.
        //
        // Two entries, not one, and the count is the whole assertion. L1 asks
        // `historical_var` **twice** — a day and a month — told apart solely by
        // `instance_id`, so a disclosure keyed or deduped by `analytic_code`
        // collapses to a single "Historical VaR: Unavailable". That reads as
        // perfectly plausible prose while hiding one of the two horizons, and it
        // is a bug this subsystem has already had once. Presence alone would
        // have passed straight through it.
        const health = panel.getByTestId('risk-level-1-health');
        await expect(health).toBeVisible();
        await expect(health).toHaveAttribute('data-count', '2');

        // The disclosure is scoped to what the level renders, never to the whole
        // wave: `correlation` travels in the same historical answer and comes
        // back `partial` from this very stub, but no level shows it, so blaming
        // L1 or L3 for it would be an accusation the reader cannot check.
        await expect(panel.getByTestId('risk-level-3-health')).toHaveCount(0);

        // The isolation itself: every level fed by a different analytic is intact,
        // and the failure did not escalate into a whole-panel error.
        await expect(panel.getByTestId('risk-l2-weight-1')).toHaveText('60.0%');
        await expect(panel.getByTestId('risk-l2-divergence-1')).toHaveText('+5.0pp');
        await expect(panel.getByTestId('risk-l3-sortino-value')).toHaveText('1.68');
        await expect(panel.getByTestId('risk-l1-card-current-value')).toHaveText(loss('3.2%'));
        await expect(panel.getByTestId('risk-load-error')).toHaveCount(0);
        await expect(panel).toHaveAttribute('data-catalog', 'ready');
    });

    test('asset global maps broker holdings and supports remove/add', async ({page}) => {
        const requests = await installRiskMocks(page);
        const brokerSelection = await brokerWithHoldings(page);

        await navigateTo(page, '/assets?tab=correlation');
        await expect(page.getByTestId('asset-global-risk-panel')).toBeVisible({timeout: 15_000});
        await expect(page.getByTestId('risk-beta-banner')).toBeVisible();
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(1);
        await expectChartCanvas(page, 'risk-correlation-heatmap', 8_000);

        const selectedAssets = page.getByTestId(/^risk-selected-asset-\d+$/);
        // The chips arrive with the correlation payload, not with the heatmap frame:
        // sampling count() once here reads whatever had rendered by that instant.
        await expect.poll(() => selectedAssets.count(), {timeout: 10_000}).toBeGreaterThanOrEqual(2); // needs two seeded active assets to remove one and add it back

        // Any chip works: the test removes one and puts it back, so it reads the ID
        // off whichever it picked rather than assuming a particular asset.
        const firstChip = selectedAssets.first();
        const firstChipTestId = await firstChip.getAttribute('data-testid');
        const removedAssetId = Number(firstChipTestId?.replace('risk-selected-asset-', ''));
        if (!Number.isInteger(removedAssetId)) throw new Error('Selected asset chip must expose its numeric asset ID.');

        await page.getByTestId(`risk-remove-asset-${removedAssetId}`).click();
        await expect(page.getByTestId(`risk-selected-asset-${removedAssetId}`)).toHaveCount(0);
        await page.getByTestId('risk-asset-add-select-trigger').click();
        await page.getByTestId(`search-select-option-${removedAssetId}`).click();
        await expect(page.getByTestId(`risk-selected-asset-${removedAssetId}`)).toBeVisible();

        await page.getByTestId('risk-broker-filter-button').click();
        await page.getByTestId(`risk-broker-option-${brokerSelection.brokerId}`).click();

        // The oracle is the panel's own selection, not the /portfolio/report snapshot
        // taken above. The panel freezes its holdings at page load, so a neighbouring
        // spec that touches this shared broker in between makes the two disagree
        // forever — no timeout can fix a comparison against data the page never saw.
        // Re-reading the chips on every iteration also absorbs the mid-update frame.
        await expect
            .poll(
                async () => {
                    const selected = await selectedAssetIds(page);
                    if (selected.length === 0) return false;
                    const wanted = selected.join(',');
                    return requests.some((request) => request.scope.kind === 'asset_set' && [...request.scope.asset_ids].sort((left, right) => left - right).join(',') === wanted);
                },
                {timeout: 15_000, intervals: [300, 500, 1_000]},
            )
            .toBe(true);

        // …and the filter really mapped to *that* broker. Exact equality with the
        // snapshot above is not assertable: the page reloaded the holdings after the
        // helper read them, so a neighbour writing to this shared broker shifts one
        // side only. A non-empty overlap survives drift in either direction and still
        // fails if the filter selected the wrong broker's assets.
        const afterFilter = await selectedAssetIds(page);
        expect(afterFilter.length).toBeGreaterThan(0);
        expect(afterFilter.some((id) => brokerSelection.assetIds.includes(id))).toBe(true);
    });

    test('broker tab sends a single-broker portfolio subset and labels it', async ({page}) => {
        const requests = await installRiskMocks(page);
        const {brokerId, panel} = await openFirstBrokerRisk(page);

        await expect(page.getByTestId('risk-beta-banner')).toBeVisible();
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(1);

        // The label is the user-visible half of the subset: this page runs the
        // whole portfolio's machinery over one broker's holdings, and a reader
        // who misses that reads these numbers as their portfolio's. Its text is
        // translated and therefore unassertable — what is assertable is that the
        // label is here and absent on the unfiltered dashboard, which the
        // dashboard test pins as the other half of the pair.
        await expect(panel.getByTestId('risk-scope-label')).toBeVisible();

        // One component, two scopes: Broker Detail is asserted with the very
        // testids the dashboard uses, because "the two pages cannot drift" is the
        // property the redesign exists to build. Two vocabularies here would let
        // them drift while both suites stayed green.
        await expect(panel.getByTestId('risk-level-1')).toBeVisible();
        await expect(panel.getByTestId('risk-l1-card-day-value')).toHaveText(loss('3.1%'));
        await expect(panel.getByTestId('risk-l1-card-month-value')).toHaveText(loss('9.4%'));
        await expect(panel.getByTestId('risk-l1-card-worst-value')).toHaveText(loss('8.7%'));
        await expect(panel.getByTestId('risk-l2-weight-1')).toHaveText('60.0%');
        await expect(panel.getByTestId('risk-l3-sortino-value')).toHaveText('1.68');

        await expect.poll(() => requests.some((request) => request.scope.kind === 'portfolio' && request.scope.broker_ids?.length === 1 && request.scope.broker_ids[0] === brokerId), {timeout: 15_000}).toBe(true);

        // And *only* that broker. A subset page that also asked the unfiltered
        // question would compute one portfolio and label another — which is
        // exactly the confusion the label above exists to prevent.
        const askedScopes = requests.filter((request) => request.scope.kind === 'portfolio').map((request) => (request.scope.kind === 'portfolio' ? (request.scope.broker_ids ?? []).join(',') : ''));
        expect([...new Set(askedScopes)]).toEqual([String(brokerId)]);
    });

    test('asset detail preserves Overview and exposes Risk through its dedicated tab', async ({page}) => {
        await installRiskMocks(page);
        await openFirstAssetDetail(page);

        await expect(page.getByTestId('asset-detail-signals-toggle')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(0);
        await expect(page.getByTestId('asset-detail-risk-panel')).toHaveCount(0);

        await page.getByTestId('asset-detail-tab-risk').click();
        await expect(page).toHaveURL(/[?&]tab=risk(?:&|$)/);
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 12_000});
        await expect(page.getByTestId('risk-beta-banner')).toBeVisible();
        await expect(page.getByTestId('risk-beta-banner')).toHaveCount(1);
        await expect(page.getByTestId('asset-detail-signals-toggle')).toHaveCount(0);

        await page.getByTestId('asset-risk-configure-signals').click();
        await expect(page.getByTestId('asset-detail-signals-toggle')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('asset-detail-signals-toggle')).toHaveAttribute('aria-expanded', 'true');
        await expect(page.getByTestId('asset-detail-risk-panel')).toHaveCount(0);
    });

    test('asset Risk runs typed scenarios, exposes replay audit and switches simulation view', async ({page}) => {
        const requests = await installRiskMocks(page);
        const assetId = await openFirstAssetDetail(page);
        await page.getByTestId('asset-detail-tab-risk').click();
        await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 12_000});

        // The comparison section renders only once the capability catalog has landed:
        // wait for the panel to say so, rather than for the section to appear — an
        // absent section is otherwise indistinguishable from an unsupported one.
        await waitForRiskCatalog(page);
        await expect(page.getByTestId('risk-comparison-controls')).toBeVisible({timeout: 12_000});
        await page.getByTestId('risk-comparison-asset-select-trigger').click();
        const comparisonOption = page.getByTestId(/^search-select-option-\d+$/).first();
        await expect(comparisonOption).toBeVisible({timeout: 5_000});
        await comparisonOption.click();
        await page.getByTestId('risk-comparison-run').click();
        await expectChartCanvas(page, 'risk-comparison-chart', 8_000);

        const stressBucketInputs = page.getByTestId(/^risk-stress-bucket-input-/);
        await expect(stressBucketInputs).toHaveCount(1, {timeout: 8_000});
        await page.getByTestId('risk-stress-show-all').check();
        await expect.poll(() => stressBucketInputs.count(), {timeout: 8_000}).toBeGreaterThan(1);
        const stressBucketInput = stressBucketInputs.first();
        await expect(stressBucketInput).toBeVisible({timeout: 8_000});
        const stressBucketTestId = await stressBucketInput.getAttribute('data-testid');
        const stressBucketId = stressBucketTestId?.replace('risk-stress-bucket-input-', '');
        if (!stressBucketId) throw new Error('Stress bucket input must expose its canonical bucket ID.');
        await stressBucketInput.fill('-25');
        await page.getByTestId('risk-stress-run').click();
        await expect(page.getByTestId('risk-stress-impacts')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('risk-stress-audit')).toBeVisible();
        await expect(page.getByTestId(`risk-stress-audit-asset-${assetId}`)).toBeVisible();

        await page.getByTestId('risk-replay-proxy-select-trigger').click();
        const proxyOption = page.getByTestId(/^search-select-option-\d+$/).first();
        await expect(proxyOption).toBeVisible({timeout: 5_000});
        const proxyOptionTestId = await proxyOption.getAttribute('data-testid');
        const proxyAssetId = Number(proxyOptionTestId?.replace('search-select-option-', ''));
        if (!Number.isInteger(proxyAssetId) || proxyAssetId <= 0) throw new Error('Replay proxy option must expose a numeric asset ID.');
        await proxyOption.click();
        await page.getByTestId('risk-replay-run').click();
        await expect(page.getByTestId('risk-replay-audit')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId(`risk-replay-audit-proxy-${assetId}`)).toBeVisible();
        await expect(page.getByTestId('risk-replay-audit-missing-history-policy')).toBeVisible();
        await expect(page.getByTestId('risk-replay-audit-composition-policy')).toBeVisible();
        await expect(page.getByTestId('risk-replay-audit-proxy-series-usage')).toBeVisible();

        const simulationQuery = page.waitForRequest(
            (request) => {
                if (request.method() !== 'POST' || !request.url().includes('/api/v1/risk/query')) return false;
                const body = request.postDataJSON() as RiskRequest;
                return body.analytics.some((analytic) => analytic.analytic_code === 'simulation');
            },
            {timeout: 10_000},
        );
        await expect(page.getByTestId('risk-simulation-run')).toBeEnabled();
        await page.getByTestId('risk-simulation-run').click();
        await simulationQuery;
        await expect(page.getByTestId('risk-simulation-chart')).toBeVisible({timeout: 12_000});
        await expect(page.getByTestId('risk-simulation-assumptions')).toBeVisible();
        await page.getByTestId('risk-simulation-view-terminal').click();
        await expect(page.getByTestId('risk-simulation-terminal-distribution')).toBeVisible({timeout: 5_000});

        await expect
            .poll(
                () => {
                    const assetRequests = requests.filter((request) => request.scope.kind === 'asset' && request.scope.asset_id === assetId);
                    return new Set(assetRequests.flatMap((request) => request.analytics.map((analytic) => analytic.analytic_code)));
                },
                {timeout: 15_000},
            )
            .toEqual(new Set(['comparison', 'historical_kpi', 'historical_var', 'simulation', 'stress']));

        const hypotheticalRequest = requests.flatMap((request) => request.analytics).find((analytic) => analytic.analytic_code === 'stress' && analytic.parameters?.method === 'hypothetical');
        expect(hypotheticalRequest?.parameters).toMatchObject({
            method: 'hypothetical',
            dimension: 'asset_class',
            bucket_shocks: {
                [stressBucketId]: -0.25,
            },
        });

        const replayRequest = requests.flatMap((request) => request.analytics).find((analytic) => analytic.analytic_code === 'stress' && analytic.parameters?.method === 'historical_replay');
        expect(replayRequest?.parameters).toMatchObject({
            method: 'historical_replay',
            missing_history_policy: 'manual_proxy_or_exclude',
            proxy_assets: [{asset_id: assetId, proxy_asset_id: proxyAssetId}],
            excluded_assets: [],
        });

        const simulationRequest = requests.flatMap((request) => request.analytics).find((analytic) => analytic.analytic_code === 'simulation');
        expect(simulationRequest?.parameters).toMatchObject({
            sampling_method: 'mc',
            path_count: 8192,
            random_seed: 123456,
        });
        expect(simulationRequest?.parameters).not.toHaveProperty('seed');
    });

    test('level 4 pays for its catalogue once, orders its three rungs and answers both scenarios', async ({page}) => {
        const requests = await installRiskMocks(page);

        // Armed before the first navigation, for the same reason test 1 arms it
        // there: a request is an *edge*, and a listener attached after the click
        // cannot say whether the closed drawer had already paid for its fetch.
        const scenarioCatalogCalls: string[] = [];
        page.on('request', (request) => {
            if (request.url().includes('/api/v1/risk/scenario-catalog')) scenarioCatalogCalls.push(request.url());
        });

        const panel = await openDashboardRisk(page);
        const level4 = await openLevel4(panel);
        await expect.poll(() => scenarioCatalogCalls.length, {timeout: 10_000}).toBe(1);

        // Closing and reopening is not a change of question, so it must not start
        // the work over. The barrier is the preset pill: it can only render from
        // a catalogue the controller still holds, so "the pill is back" and "the
        // counter is still one" together say the drawer *remembered* rather than
        // that the second fetch merely had not landed yet.
        await panel.getByTestId('risk-level-4-toggle').click();
        await expect(level4).toHaveAttribute('data-open', 'false');
        await expect(panel.getByTestId('risk-l4')).toHaveCount(0);
        await panel.getByTestId('risk-level-4-toggle').click();
        await expect(level4).toHaveAttribute('data-open', 'true');
        const shockPreset = panel.locator('[data-testid="risk-shock-preset"][data-preset-id="global_risk_off"]');
        await expect(shockPreset).toBeVisible({timeout: 8_000});
        expect(scenarioCatalogCalls).toHaveLength(1);

        // --- The three rungs, in order ----------------------------------------
        // L4 is the only level that is not homogeneous: it holds three answers at
        // increasing distance from observed data, and the order is the argument.
        // A replay is what happened; a shock is an assumption; a simulation is a
        // model. Shuffled, the reader has no way to tell which is which — so the
        // sequence is asserted, not merely the membership.
        const rungs = panel.getByTestId('risk-l4').locator('[data-distance]');
        await expect(rungs).toHaveCount(3);
        await expect.poll(() => rungs.evaluateAll((nodes) => nodes.map((node) => `${node.getAttribute('data-testid')}:${node.getAttribute('data-distance')}`)), {timeout: 5_000}).toEqual(['risk-l4-replay:observed', 'risk-l4-shock:assumed', 'risk-l4-simulation:modelled']);

        // Only the modelled rung carries the beta warning. On the section it
        // would tar the replay, which is simply what happened, and a warning that
        // is everywhere is read nowhere.
        await expect(panel.getByTestId('risk-l4-simulation').getByTestId('risk-l4-model-warning')).toBeVisible();
        await expect(panel.getByTestId('risk-l4-replay').getByTestId('risk-l4-model-warning')).toHaveCount(0);

        // Every editor really mounted, with the defaults the request will carry.
        await expect(panel.getByTestId('risk-replay')).toBeVisible();
        await expect(panel.getByTestId('risk-replay-preset')).toBeVisible();
        // Bound to the panel's own window rather than frozen at mount: the exact
        // dates belong to the dashboard, so the shape is what is assertable here.
        await expect(panel.getByTestId('risk-replay-start')).toHaveValue(/^\d{4}-\d{2}-\d{2}$/);
        await expect(panel.getByTestId('risk-replay-end')).toHaveValue(/^\d{4}-\d{2}-\d{2}$/);
        await expect(panel.getByTestId('risk-simulation-horizon')).toHaveValue('365');
        await expect(panel.getByTestId('risk-simulation-paths')).toHaveValue('8192');
        await expect(panel.getByTestId('risk-simulation-sampling')).toHaveValue('mc');

        // --- Rung 2: one click adopts the assumption *and* asks the question ---
        // The old panel made the reader fill in a shock per bucket before
        // anything would run, and a form nobody fills in produces no answers —
        // which reads exactly like a portfolio with nothing to worry about.
        await expect(panel.getByTestId('risk-shock-total')).toHaveCount(0);
        await shockPreset.click();
        await expect(shockPreset).toHaveAttribute('data-selected', 'true');
        const shockTotal = panel.getByTestId('risk-shock-total');
        await expect(shockTotal).toBeVisible({timeout: 10_000});
        // −5,00% is the stub's answer to *this* preset: BOND is the alphabetically
        // first non-zero bucket of `global_risk_off`, so the figure can only
        // appear if the scenario's own defaults reached the server. A pill that
        // ran an empty shock would render +0,00% and still look like a result.
        await expect(shockTotal).toContainText(loss('5.00%'));
        await expect(panel.getByTestId('risk-shock-tornado')).toBeVisible();

        // The detail is disclosure, not the price of admission: the buckets the
        // preset implied become visible only when someone asks to see them.
        await expect(panel.getByTestId('risk-shock-buckets')).toHaveCount(0);
        await panel.getByTestId('risk-shock-detail-toggle').click();
        await expect(panel.getByTestId('risk-shock-detail-toggle')).toHaveAttribute('aria-expanded', 'true');
        await expect(panel.locator('[data-testid="risk-shock-bucket"][data-bucket-id="STOCK"]')).toHaveValue('-20');

        // The barrier above (a rendered total) means the answer arrived, so the
        // request it answered is already in the array: a one-shot read, not a bet.
        const shockParameters = requests.flatMap((request) => request.analytics).find((analytic) => analytic.analytic_code === 'stress' && analytic.parameters?.method === 'hypothetical')?.parameters;
        expect(shockParameters).toMatchObject({
            method: 'hypothetical',
            dimension: 'asset_class',
            bucket_shocks: {STOCK: -0.2, CRYPTO: -0.3, BOND: -0.05, OTHER: 0},
        });

        // --- Rung 1: the replay, its total and the audit beside it -------------
        await expect(panel.getByTestId('risk-replay-total')).toHaveCount(0);
        await panel.getByTestId('risk-replay-run').click();
        const replayTotal = panel.getByTestId('risk-replay-total');
        await expect(replayTotal).toBeVisible({timeout: 10_000});
        await expect(replayTotal).toContainText(loss('12.00%'));
        await expect(panel.getByTestId('risk-replay-tornado')).toBeVisible();

        // The audit is not an appendix. A replay takes *today's* composition
        // through a past period, so a stand-in is an opinion and an exclusion
        // changes what the number means: both are stated where the number is
        // read. Here neither was used, and the row says so rather than vanishing.
        const replayAudit = panel.getByTestId('risk-replay-audit');
        await expect(replayAudit).toBeVisible();
        await expect(replayAudit).toHaveAttribute('data-proxy-count', '0');
        await expect(replayAudit).toHaveAttribute('data-excluded-count', '0');
    });

    test('a blocked replay names the holding and the exclusion travels on retry', async ({page}) => {
        // Not the holding the stub reports an impact for (`matrixAssetIds`[0] = 1):
        // excluding *that* one would empty the tornado and leave a 0,00% total,
        // which is indistinguishable from a replay that quietly did nothing. With
        // a second holding at fault, the retry has a real answer to produce.
        const blockedAssetId = 2;
        const requests = await installRiskMocks(page, {replayBlockedAssetId: blockedAssetId});
        const panel = await openDashboardRisk(page);
        await openLevel4(panel);

        /** `excluded_assets` of every replay the panel has put on the wire, in order. */
        const replayExclusions = () =>
            requests
                .flatMap((request) => request.analytics)
                .filter((analytic) => analytic.analytic_code === 'stress' && analytic.parameters?.method === 'historical_replay')
                .map((analytic) => analytic.parameters?.excluded_assets);

        await expect(panel.getByTestId('risk-replay-run')).toBeEnabled();
        await panel.getByTestId('risk-replay-run').click();

        // The refusal is turned into a question, addressed to the reader, about
        // the named holding. `data-asset-id` rather than the sentence: the
        // sentence ships in four languages, the id is the claim.
        const blocker = panel.getByTestId('risk-replay-blocker');
        await expect(blocker).toBeVisible({timeout: 10_000});
        await expect(blocker).toHaveAttribute('data-asset-id', String(blockedAssetId));
        // The holding itself has no history, not a stand-in chosen for it — so
        // there *is* an answer, and the button offering it is present. The other
        // branch would be a "fix it" button that fixes nothing.
        await expect(blocker).toHaveAttribute('data-proxy-at-fault', 'false');
        const excludeButton = panel.getByTestId('risk-replay-exclude');
        await expect(excludeButton).toBeVisible();

        // Barrier established (the blocker is on screen and fed by this very
        // answer), so the absences below are statements about the answer rather
        // than about how far the page had got.
        await expect(panel.getByTestId('risk-replay-total')).toHaveCount(0);
        await expect(panel.getByTestId('risk-replay-exclusions')).toHaveCount(0);

        await excludeButton.click();

        // The round trip itself, and the only place it is observable: the reader's
        // answer has to reach the server, or the loop never ends. Two requests —
        // the first asking with nothing excluded, the second carrying the choice.
        // A UI that remembered the exclusion locally and re-sent the old question
        // would show the chip, look entirely convincing, and fail exactly here.
        await expect.poll(replayExclusions, {timeout: 10_000}).toEqual([[], [blockedAssetId]]);

        // …and only then does the answer change.
        const replayTotal = panel.getByTestId('risk-replay-total');
        await expect(replayTotal).toBeVisible({timeout: 10_000});
        await expect(replayTotal).toContainText(loss('12.00%'));
        await expect(panel.getByTestId('risk-replay-audit')).toHaveAttribute('data-excluded-count', '1');
        await expect(blocker).toHaveCount(0);

        // An exclusion silently remembered is an assumption smuggled into the
        // number, so the choice stays visible — and reversible.
        const exclusionChip = panel.getByTestId('risk-replay-exclusion');
        await expect(exclusionChip).toBeVisible();
        await expect(exclusionChip).toHaveAttribute('data-asset-id', String(blockedAssetId));
        await exclusionChip.click();
        await expect(panel.getByTestId('risk-replay-exclusions')).toHaveCount(0);
        // Taking the choice back retires the answer it produced: leaving the
        // total on screen under an emptied form would make it a reply to a
        // question nobody is asking any more.
        await expect(replayTotal).toHaveCount(0);
        await expect(panel.getByTestId('risk-replay-audit')).toHaveCount(0);
    });

    test('an unavailable simulation names the step and its state instead of rendering nothing', async ({page}) => {
        await installRiskMocks(page, {unavailableSimulation: true});

        const panel = await openDashboardRisk(page);
        await openLevel4(panel);

        await expect(panel.getByTestId('risk-simulation-run')).toBeEnabled({timeout: 8_000});
        await panel.getByTestId('risk-simulation-run').click();

        // `schemas/risk.py:1056` forbids an `unavailable` result from carrying an
        // output, and every rung renders on `{#if output}`. So the absence below
        // is guaranteed by the contract, not by this fixture's choices — which is
        // exactly why the *presence* of the disclosure is the whole assertion.
        const health = panel.getByTestId('risk-level-4-health');
        await expect(health).toBeVisible({timeout: 8_000});
        await expect(health).toHaveAttribute('data-count', '1');

        // The state is read as text because that is what the reader is given, but
        // the step is identified by the rendered analytic name rather than by
        // position: L4 holds three rungs and any of them can degrade.
        await expect(health).toContainText('Simulation');
        await expect(health).toContainText('Unavailable for the selected data');

        // And the blank the disclosure replaces is still blank: naming the fault
        // must not conjure a figure. A rung that printed a number here would be
        // worse than the silence it fixed.
        await expect(panel.getByTestId('risk-simulation-terminal')).toHaveCount(0);

        // The other two rungs are untouched: an isolated failure, not a dead level.
        await expect(panel.getByTestId('risk-l4-replay')).toBeVisible();
        await expect(panel.getByTestId('risk-l4-shock')).toBeVisible();
    });

    test('a benchmark chosen on the Dashboard is the benchmark in force on Broker Detail', async ({page}) => {
        const requests = await installRiskMocks(page);

        try {
            const dashboard = await openDashboardRisk(page);
            const dashboardBenchmark = dashboard.getByTestId('risk-l3-benchmark');

            // The precondition, checked rather than assumed: without it, a page
            // that arrived already carrying the id would make the assertion at
            // the bottom true before this test had done anything at all.
            await expect(dashboardBenchmark).toBeVisible({timeout: 10_000});
            await expect(dashboardBenchmark).toHaveAttribute('data-benchmark-id', '');

            const benchmarkId = await chooseBenchmark(page, dashboard);

            // The choice is a real question put to the server, not a value parked
            // in a widget: the scope that made it asks its comparison against
            // exactly this id. Asserted here because this is where the pick
            // happens; the receiving page is asked the same question at the
            // bottom, where it is a harder one.
            await expect.poll(() => comparisonAssetIds(requests, []), {timeout: 15_000}).toContain(benchmarkId);

            // `openFirstBrokerRisk` navigates with `page.goto`, so this is a full
            // document load: the module that holds the choice is torn down and
            // re-evaluated, and the broker page can only know the benchmark by
            // reading it back out of storage. A per-component choice — or a
            // per-page one — cannot survive this line, which is precisely why
            // the assertion is worth making here and not after a client-side
            // route change.
            const {brokerId, panel} = await openFirstBrokerRisk(page);
            const brokerBenchmark = panel.getByTestId('risk-l3-benchmark');
            await expect(brokerBenchmark).toBeVisible({timeout: 10_000});
            await expect(brokerBenchmark).toHaveAttribute('data-benchmark-id', String(benchmarkId), {timeout: 10_000});

            // The attribute above is not the claim, and on its own it is not even
            // evidence: it was already correct while the feature was broken. The
            // picker showed the right benchmark over a comparison that was never
            // computed, because `L3Benchmark`'s hydration effect launched in the
            // same tick it read the store — `controller.catalog` still null — and
            // `runSingle`'s capability gate declines silently while `launched` has
            // already latched. So the display is pinned by the sample below, which
            // is the question actually put to the server.
            //
            // Sampled *before* the cold load rather than counted from zero: the
            // first visit legitimately sends its own comparison, so "has one ever
            // been sent" would go green on that one and never look at the reload
            // at all. Only the delta is about the load under test.
            //
            // The sample is an ordering barrier, and it is worth being precise
            // about its one weakness: a first-visit request handed to the recorder
            // after this line would land in the delta and be credited to the
            // reload. That degrades this assertion to the un-sliced one — which is
            // still a true statement about a cold catalogue, since the first visit
            // arrives through a `goto` that wipes the module cache too. It cannot
            // degrade to green over a scope that sent nothing, which is the failure
            // this exists to catch.
            const askedBeforeReload = comparisonAssetIds(requests, [brokerId]).length;

            // The cold load, and it is a *document* load of Broker Detail itself:
            // a fresh module cache by construction, so the panel is mounted by the
            // first render with the catalogue still a request away. That is the
            // order a reader gets when they open or refresh the Risk tab directly
            // with a benchmark already saved, and the order under which a launcher
            // that fires once, early and silently, leaves a page showing a
            // benchmark it never measured against.
            //
            // Structural rather than incidental, which is the reason for the extra
            // load: the walk-in above is cold only because `openFirstBrokerRisk`
            // happens to cross a `goto`, and it would quietly go warm the day the
            // brokers list prefetched the risk catalogue. A reload cannot.
            const coldPanel = await reloadBrokerRiskCold(page);
            await expect(coldPanel.getByTestId('risk-l3-benchmark')).toHaveAttribute('data-benchmark-id', String(benchmarkId), {timeout: 10_000});

            // Nothing was clicked after the reload. If the persisted choice is
            // worth persisting, that alone has to reach the backend as this
            // scope's comparison, carrying this id.
            await expect.poll(() => comparisonAssetIds(requests, [brokerId]).slice(askedBeforeReload), {timeout: 15_000}).toContain(benchmarkId);
        } finally {
            await clearRiskBenchmark(page);
        }
    });

    /**
     * Its own test rather than a tail on the one above, and the reason is what a
     * red would have to mean. That one is about *place*: the same benchmark on
     * two pages, which a per-page choice fails. This one is about *time*: the
     * same benchmark still measured after the question underneath it changed,
     * which a choice that asks itself once fails. Folding them together would
     * put a period change in the middle of a journey whose own assertion is a
     * sampled delta across a cold reload, so a failure could no longer name
     * which of the two properties broke — and the test's title would be a
     * statement about place over a body that also tested time.
     */
    test('a benchmark in force is re-measured when the period moves', async ({page}) => {
        const requests = await installRiskMocks(page);
        /** Portfolio-wide requests — the Dashboard's scope — that carry a comparison. */
        const dashboardComparisons = () => requests.filter((request) => request.scope.kind === 'portfolio' && (request.scope.broker_ids ?? []).length === 0 && request.analytics.some((analytic) => analytic.analytic_code === 'comparison'));

        try {
            // The Dashboard rather than Broker Detail, though both mount a period
            // control: its scope is `{kind: 'portfolio'}` with no broker ids, so
            // `comparisonAssetIds(requests, [])` names it exactly without the test
            // first having to resolve which broker it landed on, and one levels
            // panel is mounted on the page, so every locator below is unambiguous.
            const dashboard = await openDashboardRisk(page);

            // The precondition, checked rather than assumed: a page that arrived
            // already carrying a benchmark would make the rest of this true before
            // the test had chosen anything.
            const picker = dashboard.getByTestId('risk-l3-benchmark');
            await expect(picker).toBeVisible({timeout: 10_000});
            await expect(picker).toHaveAttribute('data-benchmark-id', '');

            const benchmarkId = await chooseBenchmark(page, dashboard);

            // The barrier the whole test turns on, and the reason it is this
            // locator and not the picker's attribute. `risk-l3-beta-benchmark` is
            // rendered from `comparedAssetId(controller.comparisonResult)` — the
            // *answer* — so it is on screen only once the comparison has come
            // back. The property below only exists for an analysis that has
            // already finished: `discardOnDemand` re-issues whatever was still in
            // flight, so a comparison still on the wire when the period moves is
            // relaunched by the controller itself and nothing is lost. Moving the
            // period before this line would exercise that other branch and go
            // green over a benchmark that never re-asks.
            const betaBenchmark = dashboard.getByTestId('risk-l3-beta-benchmark');
            await expect(betaBenchmark).toBeVisible({timeout: 15_000});

            // Sampled before the click, for the reason the test above samples
            // before its reload: choosing a benchmark legitimately sends its own
            // comparison, so "one was sent at some point" is already green before
            // the period has moved at all. Only the delta is about the change.
            const askedBeforePeriodChange = comparisonAssetIds(requests, []).length;
            const windowBefore = dashboardComparisons()[0]?.date_range.start;
            expect(windowBefore).toBeTruthy();

            // The period control the Dashboard actually gives the reader, driven
            // through the preset badges `DateRangePicker` publishes — the same
            // handle `gallery.spec.ts` uses. `1Y` because the ambient window is
            // the 3-month default, so this is one click that demonstrably moves
            // `dateStart`; `data-active` is asserted on both sides of it so the
            // test states which window it started in instead of assuming, and a
            // click that moved nothing fails here rather than three lines down.
            const oneYear = page.getByTestId('date-preset-1y');
            await expect(oneYear).toHaveAttribute('data-active', 'false');
            await oneYear.click();
            await expect(oneYear).toHaveAttribute('data-active', 'true');

            // The claim. Nothing was re-chosen and nothing was clicked in the
            // panel: a standing benchmark has to re-ask itself, because the answer
            // it had was discarded along with the question that produced it.
            await expect.poll(() => comparisonAssetIds(requests, []).slice(askedBeforePeriodChange), {timeout: 20_000}).toContain(benchmarkId);

            // …and it has to ask the *new* question. A re-ask that replayed the
            // old window would put the same id back on the wire and satisfy the
            // line above while showing the reader a beta measured over a period
            // they have left. Read once rather than polled because the poll is the
            // barrier: the request is already in the log by the time this runs,
            // and the index is into a collection filtered to comparisons only.
            const fresh = dashboardComparisons();
            expect(fresh[fresh.length - 1]?.date_range.start).not.toBe(windowBefore);

            // The reader's half of the same fact, and the state the defect leaves
            // behind: a benchmark named in the picker standing over an em dash,
            // because the label under beta is drawn from an answer nobody re-asked.
            await expect(betaBenchmark).toBeVisible({timeout: 15_000});
        } finally {
            await clearRiskBenchmark(page);
        }
    });

    /**
     * The third member of the disclosure trio, and the one that was missing.
     *
     * Test 1 proves nothing is disclosed when nothing fell short; test 2 proves
     * the *status* is disclosed when two horizons did. Neither ever put a
     * `warning` in front of a level that renders, because the only one this
     * stub ever sent rides on `correlation` — which no level shows. So the
     * reasons list had shipped, had unit tests, and had never once been
     * rendered by the suite.
     */
    test('a warning reaches the level that rendered the measurement, once per sentence', async ({page}) => {
        // Two sentences, three warnings. Written as full prose rather than as
        // codes because that is what the panel puts on screen: `resultReasons`
        // renders the backend's string verbatim, so the fixture sentence *is*
        // the contract under test. It is not translated, so asserting on it is
        // not the mistake the no-translated-text rule is about.
        const varReason = 'Only 41 of the 60 sessions had a usable close at this horizon';
        const drawdownReason = 'Peak-to-trough window truncated at the start of available history';

        await installRiskMocks(page, {
            analyticWarnings: {
                // Asked twice per wave — one day, one month — so this single
                // entry arrives on two results carrying identical text.
                historical_var: [{code: 'sparse_history', message: varReason}],
                // Asked once, and rendered by L1 only. Deliberately not
                // `historical_kpi`, which L1 and L3 both read: a sentence landing
                // under two levels could not say which slice put it there.
                drawdown_summary: [{code: 'truncated_window', message: drawdownReason}],
            },
        });

        const panel = await openDashboardRisk(page);

        // The barrier, and the precondition in one. Reasons live inside L1's
        // body, so "no reasons" is also true of a level that has not rendered —
        // and `data-occurrences="2"` only means something if two VaR results
        // really came back. Both rungs on screen with different figures is that
        // proof, taken from the product rather than from the request log.
        await expect(panel.getByTestId('risk-level-1')).toBeVisible();
        await expect(panel.getByTestId('risk-l1-card-day-value')).toHaveText(loss('3.1%'));
        await expect(panel.getByTestId('risk-l1-card-month-value')).toHaveText(loss('9.4%'));

        // Every result in this wave is `ok`: nothing is degraded, so the status
        // line is absent — and the reasons are still shown. That pair is the
        // claim. `degrades_result` decides the status and the status decides the
        // health row, but neither decides whether a sentence is worth reading; a
        // reasons list gated on `health` would render nothing here while looking
        // perfectly correct in the unavailable test above.
        await expect(panel.getByTestId('risk-level-1-health')).toHaveCount(0);

        const reasons = panel.getByTestId('risk-level-1-reasons');
        await expect(reasons).toBeVisible();
        // Three warnings in, two entries out. The count is the deduplication
        // stated as a number instead of inferred from the shape of the prose.
        await expect(reasons).toHaveAttribute('data-count', '2');
        await expect(panel.getByTestId('risk-level-1-reason')).toHaveCount(2);

        // The sentence both horizons carried: rendered once, counted twice. Two
        // `<li>` would read to the reader as a rendering fault rather than as two
        // affected measurements; one saying "1" would drop a horizon on the floor
        // and look entirely plausible doing it.
        const varEntry = panel.getByTestId('risk-level-1-reason').filter({hasText: varReason});
        await expect(varEntry).toHaveCount(1);
        await expect(varEntry).toHaveAttribute('data-occurrences', '2');
        await expect(varEntry).toHaveText(varReason);

        // …and the one that arrived alone still says "1", so the counter is read
        // off the data and not printed from a constant that happens to be right.
        const drawdownEntry = panel.getByTestId('risk-level-1-reason').filter({hasText: drawdownReason});
        await expect(drawdownEntry).toHaveCount(1);
        await expect(drawdownEntry).toHaveAttribute('data-occurrences', '1');
        await expect(drawdownEntry).toHaveText(drawdownReason);

        // Barriers before the absences: both other levels are demonstrably fed
        // by this same wave, so their empty reason lists are a statement about
        // scoping rather than about a panel that had not finished rendering.
        await expect(panel.getByTestId('risk-l2-weight-1')).toHaveText('60.0%');
        await expect(panel.getByTestId('risk-l3-sortino-value')).toHaveText('1.68');

        // The scoping itself. `correlation` rides in the very same historical
        // answer and this stub returns it `partial` with a warning of its own,
        // but no level renders correlation — so its sentence belongs under none
        // of them. A panel that fed every level the whole wave would show three
        // entries here, all of them plausible, one of them an accusation the
        // reader has no way to check.
        await expect(panel.getByTestId('risk-level-1-reason').filter({hasText: 'E2E partial fixture'})).toHaveCount(0);
        await expect(panel.getByTestId('risk-level-2-reasons')).toHaveCount(0);
        await expect(panel.getByTestId('risk-level-3-reasons')).toHaveCount(0);
    });

    /**
     * The twin of the test above, for the measurements that never ran.
     *
     * A level with no rows renders the same shape whether its analytic is out of
     * scope, short of history, or still in flight — and the one sentence it
     * showed, "unavailable for the selected data", blames the reader's portfolio
     * for a limit of the analytic. The legacy frame said which of the two it was;
     * the redesign lost that and nothing turned red, because the fixture answers
     * every code the panel asks for and so no level here had ever failed.
     *
     * ⚠️ **The codes are real enum members, not invented ones.** `RiskErrorCode`
     * is closed — thirteen values — and Zodios validates the response, so a stub
     * carrying a made-up code does not produce a failed *analytic*: it throws on
     * the whole wave, sets `loadError`, and renders **no levels at all**. The
     * first draft of this test did exactly that and failed on `risk-level-1` not
     * existing, an error whose obvious reading ("the level is broken") is the
     * wrong one.
     *
     * 📌 **The boundary that follows**: because the enum is closed at the client,
     * a code the UI has never seen cannot arrive through a validated response.
     * The fallback in `translateErrorCode` is therefore **unreachable from here
     * by construction**, and is covered by unit test instead. What this test can
     * prove — and what actually regressed — is that codes the catalogue *did* not
     * cover now speak: `worker_busy` and `execution_timeout` were two of five
     * enum values with no translation at all.
     *
     * ⚠️ **Not one assertion on the rendered wording.** The sentences are
     * translated, so pinning the English would fail the day the suite runs in
     * another locale. What is pinned is the *relation*: three codes, three
     * different sentences, none of them a key. Break the catalogue lookup so
     * everything falls back and the three collapse to one — red. Break the guard
     * so a key leaks — red on the `risk.errors.` check.
     */
    test('a measurement that never ran says which limit stopped it, and never says it in keys', async ({page}) => {
        // L1's three codes, so all three failures land in one list and the
        // comparison is between siblings rather than across levels. The last two
        // are the regression: until the catalogue gained them, both rendered the
        // same generic sentence as each other.
        await installRiskMocks(page, {
            analyticErrors: {
                historical_var: 'incompatible_scope',
                drawdown_summary: 'worker_busy',
                historical_kpi: 'execution_timeout',
            },
        });

        const panel = await openDashboardRisk(page);

        await expect(panel.getByTestId('risk-level-1')).toBeVisible();
        const errors = panel.getByTestId('risk-level-1-errors');
        await expect(errors).toBeVisible();
        await expect(errors).toHaveAttribute('data-count', '3');

        // Targeted by `data-code`, which carries the backend's identifier: the
        // one part of this row the UI does not word, and so the only safe handle
        // for saying *which* sentence is being read.
        const texts: string[] = [];
        for (const code of ['incompatible_scope', 'worker_busy', 'execution_timeout']) {
            const row = panel.locator(`[data-testid="risk-level-1-error"][data-code="${code}"]`);
            await expect(row).toHaveCount(1);
            texts.push(((await row.textContent()) ?? '').trim());
        }

        // The guard, against the real `svelte-i18n` rather than the double the
        // unit test hands `translateErrorCode`.
        for (const text of texts) {
            expect(text).not.toContain('risk.errors.');
            expect(text.length).toBeGreaterThan(0);
        }

        // Three causes, three sentences. Collapse the lookup and this is the
        // assertion that notices, because every code would fall back to one.
        expect(new Set(texts).size).toBe(3);

        // The failure is disclosed *and* the level is honest about having
        // nothing: with every L1 analytic failed there are no cards to draw, and
        // an error list next to a stale grid would be worse than either alone.
        // Same locator shape as the count assertion above, direct children only,
        // because `risk-l1-card-` also prefixes each card's own inner parts.
        await expect(panel.getByTestId('risk-l1-cards').locator('> div > [data-testid^="risk-l1-card-"]')).toHaveCount(0);

        // The generic sentence is still there, underneath. Not a contradiction
        // but the division the panel already uses for health and reasons: the
        // empty state says there is nothing to read, the error says what stopped
        // it. Pinned so a later attempt to suppress one of the two comes through
        // this test.
        await expect(panel.getByTestId('risk-l1-empty')).toBeVisible();

        // Confined to the level that asked. `risk_contribution` answered
        // normally, so L2 shows no error at all — a failure broadcast to every
        // level would read as a whole-panel outage.
        await expect(panel.getByTestId('risk-level-2-errors')).toHaveCount(0);
    });
});
