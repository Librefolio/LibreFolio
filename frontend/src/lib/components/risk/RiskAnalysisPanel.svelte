<script lang="ts">
    import {untrack} from 'svelte';
    import {goto} from '$app/navigation';
    import {Play, RefreshCw, RotateCw} from 'lucide-svelte';

    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import type {RenderedSignal} from '$lib/charts/signals';
    import SignalAssetParamControl from '$lib/components/charts/SignalAssetParamControl.svelte';
    import LineChart, {type LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import KpiCard from '$lib/components/dashboard/KpiCard.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import PageSyncModal from '$lib/components/ui/modals/PageSyncModal.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import {assetStoreVersion, ensureAssetsLoaded, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {ensureFxRoutesLoaded, fxRoutesVersion, getConfiguredPairSlugs} from '$lib/stores/reference/fxRoutesStore';
    import {fetchRiskCatalog, getRiskDefinition, hasRiskCapability, invalidateRisk, queryRisk, type RiskAnalyticResult, type RiskCatalogResponse, type RiskMode, type RiskQueryRequest, type RiskScope} from '$lib/stores/risk/riskStore.svelte';
    import {riskDataQuality, riskOutput, singleValue, type RiskDataQualityReport} from '$lib/risk/riskTypes';
    import CorrelationHeatmap from './CorrelationHeatmap.svelte';
    import RiskResultFrame from './RiskResultFrame.svelte';

    interface Props {
        scope: RiskScope;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        assetIds?: number[];
        title?: string;
        subtitle?: string;
        internalSubset?: boolean;
        onsynced?: () => void | Promise<void>;
    }

    let {scope, dateStart, dateEnd, targetCurrency, assetIds = [], title = '', subtitle = '', internalSubset = false, onsynced}: Props = $props();

    let catalog = $state<RiskCatalogResponse | null>(null);
    let historicalResults = $state<RiskAnalyticResult[]>([]);
    let currentResults = $state<RiskAnalyticResult[]>([]);
    let comparisonResult = $state<RiskAnalyticResult | null>(null);
    let stressResult = $state<RiskAnalyticResult | null>(null);
    let simulationResult = $state<RiskAnalyticResult | null>(null);
    let initialLoading = $state(true);
    let refreshing = $state(false);
    let loadError = $state(false);
    let requestGeneration = 0;
    let lastBaseSignature = '';

    let comparisonAssetId = $state<number | undefined>(undefined);
    let comparisonLoading = $state(false);
    let stressLoading = $state(false);
    let simulationLoading = $state(false);
    let stressClientError = $state(false);
    let stressPercent = $state(-10);
    let riskFreePercentInput = $state(0);
    let appliedRiskFreePercent = $state(0);
    let simulationSampling = $state<'mc' | 'qmc'>('mc');
    let simulationHorizonDays = $state(365);
    let simulationPaths = $state(8192);
    let simulationSeed = $state(123456);
    let syncOpen = $state(false);

    const samplingOptions = [
        {value: 'mc', label: 'MC'},
        {value: 'qmc', label: 'QMC'},
    ];
    const pathOptions = [1024, 2048, 4096, 8192, 16384].map((value) => ({value: String(value), label: value.toLocaleString()}));

    let supportsKpi = $derived(hasRiskCapability(catalog, 'portfolio_kpi', scope.kind, 'historical'));
    let supportsCorrelation = $derived(hasRiskCapability(catalog, 'correlation', scope.kind, 'historical'));
    let supportsContribution = $derived(hasRiskCapability(catalog, 'risk_contribution', scope.kind, 'current_composition'));
    let supportsVar = $derived(hasRiskCapability(catalog, 'historical_var', scope.kind, 'historical'));
    let supportsComparison = $derived(hasRiskCapability(catalog, 'comparison', scope.kind, 'historical'));
    let supportsStress = $derived(hasRiskCapability(catalog, 'stress', scope.kind, 'current_composition'));
    let supportsSimulation = $derived(hasRiskCapability(catalog, 'simulation', scope.kind, 'current_composition'));

    let kpiResult = $derived(resultByCode(historicalResults, 'portfolio_kpi'));
    let correlationResult = $derived(resultByCode(historicalResults, 'correlation'));
    let contributionResult = $derived(resultByCode(currentResults, 'risk_contribution'));
    let varResult = $derived(resultByCode(historicalResults, 'historical_var'));

    let kpiOutput = $derived(riskOutput(kpiResult, schemas.RiskKpiOutput));
    let correlationOutput = $derived(riskOutput(correlationResult, schemas.RiskCorrelationOutput));
    let contributionOutput = $derived(riskOutput(contributionResult, schemas.RiskContributionOutput));
    let varOutput = $derived(riskOutput(varResult, schemas.RiskVarCvarOutput));
    let comparisonOutput = $derived(riskOutput(comparisonResult, schemas.RiskComparisonOutput));
    let stressOutput = $derived(riskOutput(stressResult, schemas.RiskStressOutput));
    let simulationOutput = $derived(riskOutput(simulationResult, schemas.RiskSimulationOutput));

    let scopeAssetIds = $derived.by(() => {
        const ids = new Set<number>(assetIds);
        if (scope.kind === 'asset') ids.add(scope.asset_id);
        if (scope.kind === 'asset_set') scope.asset_ids.forEach((assetId) => ids.add(assetId));
        correlationOutput?.asset_ids.forEach((assetId) => ids.add(assetId));
        contributionOutput?.items?.forEach((item) => ids.add(item.asset_id));
        return [...ids].sort((left, right) => left - right);
    });

    let assetLabels = $derived.by(() => {
        void $assetStoreVersion;
        return new Map(scopeAssetIds.map((assetId) => [assetId, getAssetInfo(assetId)?.display_name ?? `#${assetId}`]));
    });

    let contributionRows = $derived.by(() => {
        const rows = (contributionOutput?.items ?? []).map((item) => ({
            ...item,
            name: assetLabels.get(item.asset_id) ?? `#${item.asset_id}`,
            percentage: singleValue(item.percentage_contribution),
        }));
        const maxAbs = Math.max(...rows.map((item) => Math.abs(item.percentage ?? 0)), 0);
        return rows.map((item) => ({...item, barWidth: maxAbs > 0 ? (Math.abs(item.percentage ?? 0) / maxAbs) * 50 : 0})).sort((left, right) => Math.abs(right.percentage ?? 0) - Math.abs(left.percentage ?? 0));
    });

    let comparisonPrimaryData = $derived.by<LineDataPoint[]>(() =>
        (comparisonOutput?.series ?? []).map((point) => ({
            date: point.date,
            value: point.primary_cumulative_return * 100,
        })),
    );
    let comparisonOverlay = $derived.by<RenderedSignal[]>(() => {
        if (!comparisonOutput) return [];
        return [
            {
                id: 'risk-comparison',
                label: $t('risk.comparison.comparisonAsset'),
                data: (comparisonOutput.series ?? []).map((point) => ({date: point.date, value: point.comparison_cumulative_return * 100})),
                color: '#f59e0b',
                lineWidth: 2,
                lineType: 'solid',
                markerStart: null,
                markerEnd: null,
                unit: 'percentage',
            },
        ];
    });

    let simulationData = $derived.by<LineDataPoint[]>(() =>
        (simulationOutput?.percentile_bands ?? []).map((point) => ({
            date: addDays(dateEnd, point.day),
            value: point.p50 * 100,
        })),
    );
    let simulationOverlay = $derived.by<RenderedSignal[]>(() => {
        if (!simulationOutput) return [];
        return [
            {
                id: 'risk-simulation-band',
                label: $t('risk.simulation.simulated'),
                data: simulationData,
                color: '#2563eb',
                lineWidth: 2,
                lineType: 'solid',
                markerStart: null,
                markerEnd: null,
                unit: 'percentage',
                seriesType: 'band',
                bandData: {
                    lower: simulationOutput.percentile_bands.map((point) => point.p05 * 100),
                    middle: simulationOutput.percentile_bands.map((point) => point.p50 * 100),
                    upper: simulationOutput.percentile_bands.map((point) => point.p95 * 100),
                },
            },
        ];
    });

    let allResults = $derived([kpiResult, correlationResult, contributionResult, varResult, comparisonResult, stressResult, simulationResult].filter((result): result is RiskAnalyticResult => result !== null && result !== undefined));
    let qualityReports = $derived(allResults.map(riskDataQuality).filter((report) => report !== null));
    let dataQualityIssues = $derived.by<DataQualityIssue[]>(() => {
        const deduped = new Map<string, DataQualityIssue>();
        for (const report of qualityReports) {
            for (const issue of report?.issues ?? []) {
                const normalized = normalizeQualityIssue(issue);
                const key = [normalized.code, normalized.affected_asset_ids?.join(','), normalized.affected_fx_pairs?.join(',')].join('|');
                deduped.set(key, normalized);
            }
        }
        return [...deduped.values()];
    });
    let qualityStatus = $derived.by(() => {
        const statuses = qualityReports.map((report) => report?.data_quality_status);
        if (statuses.includes('partial')) return 'partial';
        if (statuses.includes('carried_forward')) return 'carried_forward';
        return statuses.length > 0 ? 'ok' : null;
    });
    let carriedPricePoints = $derived(Math.max(0, ...qualityReports.map((report) => report?.carried_forward_price_points ?? 0)));
    let carriedFxPoints = $derived(Math.max(0, ...qualityReports.map((report) => report?.carried_forward_fx_points ?? 0)));

    let syncAssetIds = $derived([...new Set([...scopeAssetIds, ...(comparisonAssetId ? [comparisonAssetId] : [])])]);
    let syncAssets = $derived.by(() => {
        void $assetStoreVersion;
        return syncAssetIds
            .map((assetId) => getAssetInfo(assetId))
            .filter((asset) => Boolean(asset))
            .map((asset) => ({
                id: asset!.id,
                display_name: asset!.display_name,
                currency: asset!.currency,
                icon_url: asset!.icon_url,
                asset_type: asset!.asset_type,
                provider_code: asset!.provider_code,
            }));
    });
    let syncFxPairs = $derived.by(() => {
        void $fxRoutesVersion;
        const configured = getConfiguredPairSlugs();
        const pairs = new Set<string>();
        for (const asset of syncAssets) {
            if (!asset || asset.currency === targetCurrency) continue;
            const slug = [asset.currency, targetCurrency].sort().join('-');
            if (configured.has(slug)) pairs.add(slug);
        }
        return [...pairs].sort();
    });

    $effect(() => {
        const signature = JSON.stringify({
            scope,
            dateStart,
            dateEnd,
            targetCurrency,
            appliedRiskFreePercent,
        });
        if (signature === lastBaseSignature) return;
        lastBaseSignature = signature;
        comparisonResult = null;
        stressResult = null;
        simulationResult = null;
        untrack(() => void loadBase(false));
    });

    $effect(() => {
        untrack(() => {
            void Promise.all([ensureAssetsLoaded(), ensureFxRoutesLoaded()]);
        });
    });

    function resultByCode(results: RiskAnalyticResult[], analyticCode: string): RiskAnalyticResult | null {
        return results.find((result) => result.analytic_code === analyticCode) ?? null;
    }

    function normalizeQualityIssue(issue: NonNullable<RiskDataQualityReport['issues']>[number]): DataQualityIssue {
        return {
            domain: issue.domain,
            code: issue.code,
            severity: issue.severity,
            message_i18n_key: issue.message_i18n_key,
            message_params: issue.message_params as Record<string, string | number | boolean | null | undefined> | undefined,
            count: singleValue(issue.count),
            affected_asset_ids: issue.affected_asset_ids,
            affected_asset_names: issue.affected_asset_names,
            affected_fx_pairs: issue.affected_fx_pairs,
            cta_action: singleValue(issue.cta_action),
            cta_target: singleValue(issue.cta_target),
            group_key: singleValue(issue.group_key),
        };
    }

    function analyticTitle(code: string, fallbackKey: string): string {
        const definition = getRiskDefinition(catalog, code);
        return $t(definition?.name_i18n_key ?? fallbackKey);
    }

    function analyticDescription(code: string): string {
        const key = getRiskDefinition(catalog, code)?.description_i18n_key;
        return key ? $t(key) : '';
    }

    function buildBaseAnalytics(mode: RiskMode): RiskQueryRequest['analytics'] {
        const analytics: Array<RiskQueryRequest['analytics'][number]> = [];
        const add = (code: string, parameters: RiskQueryRequest['analytics'][number]['parameters'] = {}) => {
            if (hasRiskCapability(catalog, code, scope.kind, mode)) {
                analytics.push({instance_id: `base-${mode}-${code}`, analytic_code: code, parameters});
            }
        };
        if (mode === 'historical') {
            add('portfolio_kpi', {
                risk_free_annual_rate: appliedRiskFreePercent / 100,
                target_annual_return: 0,
            });
            add('correlation');
            add('historical_var', {confidence_level: 0.95, horizon_days: 1});
        } else {
            add('risk_contribution');
        }
        return analytics;
    }

    async function loadBase(force: boolean): Promise<void> {
        const generation = ++requestGeneration;
        const hadResults = historicalResults.length > 0 || currentResults.length > 0;
        initialLoading = !hadResults;
        refreshing = hadResults;
        loadError = false;

        try {
            catalog = await fetchRiskCatalog();
            if (generation !== requestGeneration || !catalog) return;

            const historicalAnalytics = buildBaseAnalytics('historical');
            const currentAnalytics = buildBaseAnalytics('current_composition');
            const [historical, current] = await Promise.all([
                historicalAnalytics.length > 0
                    ? queryRisk(
                          {
                              scope,
                              date_range: {start: dateStart, end: dateEnd},
                              target_currency: targetCurrency,
                              mode: 'historical',
                              analytics: historicalAnalytics,
                          },
                          force,
                      )
                    : null,
                currentAnalytics.length > 0
                    ? queryRisk(
                          {
                              scope,
                              date_range: {start: dateStart, end: dateEnd},
                              target_currency: targetCurrency,
                              mode: 'current_composition',
                              composition_policy: 'current_buy_and_hold',
                              analytics: currentAnalytics,
                          },
                          force,
                      )
                    : null,
            ]);

            if (generation !== requestGeneration) return;
            historicalResults = historical?.items ?? [];
            currentResults = current?.items ?? [];
        } catch (error) {
            console.error('[Risk] Failed to load base analytics:', error);
            if (generation === requestGeneration) loadError = true;
        } finally {
            if (generation === requestGeneration) {
                initialLoading = false;
                refreshing = false;
            }
        }
    }

    async function runSingle(code: string, mode: RiskMode, parameters: RiskQueryRequest['analytics'][number]['parameters']): Promise<RiskAnalyticResult | null> {
        if (!hasRiskCapability(catalog, code, scope.kind, mode)) return null;
        const response = await queryRisk({
            scope,
            date_range: {start: dateStart, end: dateEnd},
            target_currency: targetCurrency,
            mode,
            ...(mode === 'current_composition' ? {composition_policy: 'current_buy_and_hold' as const} : {}),
            analytics: [{instance_id: `${code}-${Date.now()}`, analytic_code: code, parameters}],
        });
        return response?.items?.[0] ?? null;
    }

    async function runComparison(): Promise<void> {
        if (!comparisonAssetId) return;
        comparisonLoading = true;
        try {
            comparisonResult = await runSingle('comparison', 'historical', {comparison_asset_id: comparisonAssetId});
        } catch (error) {
            console.error('[Risk] Comparison failed:', error);
            comparisonResult = null;
        } finally {
            comparisonLoading = false;
        }
    }

    async function runStress(): Promise<void> {
        stressClientError = scopeAssetIds.length === 0;
        if (stressClientError) return;
        stressLoading = true;
        try {
            stressResult = await runSingle('stress', 'current_composition', {
                method: 'hypothetical',
                shocks: Object.fromEntries(scopeAssetIds.map((assetId) => [String(assetId), stressPercent / 100])),
            });
        } catch (error) {
            console.error('[Risk] Stress failed:', error);
            stressResult = null;
        } finally {
            stressLoading = false;
        }
    }

    async function runSimulation(): Promise<void> {
        simulationLoading = true;
        try {
            simulationResult = await runSingle('simulation', 'current_composition', {
                process: 'gbm',
                sampling: simulationSampling,
                horizon_days: simulationHorizonDays,
                paths: simulationPaths,
                seed: simulationSeed,
            });
        } catch (error) {
            console.error('[Risk] Simulation failed:', error);
            simulationResult = null;
        } finally {
            simulationLoading = false;
        }
    }

    async function handleSynced(): Promise<void> {
        invalidateRisk();
        await loadBase(true);
        await onsynced?.();
    }

    function handleQualityAction(action: string, target: string | null): void {
        if (action.includes('sync')) {
            syncOpen = true;
        } else if (action === 'navigate_asset' && target) {
            void goto(`/assets/${target}`);
        } else if (action === 'navigate_fx' && target) {
            void goto(`/fx/${target}`);
        } else if (action === 'add_fx_pair') {
            void goto('/fx');
        }
    }

    function formatPercent(value: number | null | undefined, signed = false): string {
        if (value == null) return '—';
        const percentage = value * 100;
        const sign = signed && percentage > 0 ? '+' : '';
        return `${sign}${percentage.toFixed(2)}%`;
    }

    function formatRatio(value: number | null | undefined): string {
        return value == null ? '—' : value.toFixed(2);
    }

    function formatAmount(value: string | readonly (string | null)[] | null | undefined): string {
        const scalar = singleValue(value);
        if (scalar == null) return '—';
        const amount = Number(scalar);
        if (!Number.isFinite(amount)) return '—';
        return new Intl.NumberFormat(undefined, {style: 'currency', currency: targetCurrency, maximumFractionDigits: 2}).format(amount);
    }

    function addDays(baseDate: string, days: number): string {
        const parsed = new Date(`${baseDate}T00:00:00Z`);
        if (Number.isNaN(parsed.getTime())) return `day-${days}`;
        parsed.setUTCDate(parsed.getUTCDate() + days);
        return parsed.toISOString().slice(0, 10);
    }
</script>

<div class="space-y-4" data-testid="risk-analysis-panel">
    <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">{title || $t('risk.title')}</h2>
            {#if subtitle || internalSubset}
                <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="risk-scope-label">
                    {internalSubset ? $t('risk.internalSubset') : subtitle}
                </p>
            {/if}
        </div>
        <div class="flex items-center gap-2">
            <button
                type="button"
                class="flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-1.5 text-xs text-gray-600 dark:text-gray-300 disabled:opacity-50"
                onclick={() => (syncOpen = true)}
                disabled={syncAssets.length === 0 && syncFxPairs.length === 0}
                data-testid="risk-sync-button"
            >
                <RotateCw size={14} />
                {$t('common.sync')}
            </button>
            <button
                type="button"
                class="flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-1.5 text-xs text-gray-600 dark:text-gray-300 disabled:opacity-50"
                onclick={() => loadBase(true)}
                disabled={initialLoading || refreshing}
                data-testid="risk-refresh-button"
            >
                <RefreshCw size={14} class={refreshing ? 'animate-spin' : ''} />
                {$t('common.refresh')}
            </button>
        </div>
    </div>

    {#if loadError}
        <div class="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-300" data-testid="risk-load-error">
            {$t('risk.states.loadFailed')}
        </div>
    {/if}

    {#if dataQualityIssues.length > 0}
        <DataQualityBanner issues={dataQualityIssues} mode="grouped" onaction={(action, target) => handleQualityAction(action, target)} />
    {/if}

    {#if qualityStatus}
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-gray-100 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/60 px-3 py-2 text-xs text-gray-500 dark:text-gray-400" data-testid="risk-quality-summary">
            <span>{$t('risk.quality.status')}: <strong class="text-gray-700 dark:text-gray-200">{$t(`risk.quality.${qualityStatus}`)}</strong></span>
            <span>{$t('risk.quality.carriedPrices')}: {carriedPricePoints}</span>
            <span>{$t('risk.quality.carriedFx')}: {carriedFxPoints}</span>
        </div>
    {/if}

    {#if supportsKpi}
        <div class="flex flex-wrap items-end gap-3 rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-3" data-testid="risk-free-control">
            <label class="text-xs text-gray-500 dark:text-gray-400">
                {$t('chartSettings.params.riskFreeAnnualRate')}
                <span class="mt-1 flex items-center gap-1">
                    <input class="w-24 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200" type="number" step="0.1" min="-99.9" bind:value={riskFreePercentInput} data-testid="risk-free-rate-input" />
                    <span>%</span>
                </span>
            </label>
            <button class="rounded-lg bg-libre-green px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50" onclick={() => (appliedRiskFreePercent = riskFreePercentInput)} disabled={riskFreePercentInput === appliedRiskFreePercent} data-testid="risk-free-apply">
                {$t('common.apply')}
            </button>
        </div>

        <RiskResultFrame title={analyticTitle('portfolio_kpi', 'risk.analytics.portfolioKpi.name')} description={analyticDescription('portfolio_kpi')} result={kpiResult} loading={initialLoading} {refreshing} testId="risk-kpi-section">
            <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
                <KpiCard label={$t('risk.metrics.volatility')} value={formatPercent(kpiOutput?.volatility)} />
                <KpiCard label={$t('risk.metrics.maxDrawdown')} value={formatPercent(kpiOutput?.max_drawdown)} positive={false} />
                <KpiCard label={$t('risk.metrics.drawdownDuration')} value={kpiOutput ? `${kpiOutput.max_drawdown_duration_days} ${$t('signals.units.days')}` : '—'} />
                <KpiCard label={$t('risk.metrics.sharpe')} value={formatRatio(singleValue(kpiOutput?.sharpe))} />
                <KpiCard label={$t('risk.metrics.sortino')} value={formatRatio(singleValue(kpiOutput?.sortino))} />
            </div>
        </RiskResultFrame>
    {/if}

    {#if supportsCorrelation}
        <RiskResultFrame title={analyticTitle('correlation', 'risk.analytics.correlation.name')} description={analyticDescription('correlation')} result={correlationResult} loading={initialLoading} {refreshing} testId="risk-correlation-section">
            <div class="mt-4">
                {#if correlationOutput}
                    <CorrelationHeatmap output={correlationOutput} {assetLabels} />
                {/if}
            </div>
        </RiskResultFrame>
    {/if}

    {#if supportsContribution}
        <RiskResultFrame title={analyticTitle('risk_contribution', 'risk.analytics.riskContribution.name')} description={analyticDescription('risk_contribution')} result={contributionResult} loading={initialLoading} {refreshing} testId="risk-contribution-section">
            <div class="mt-4 space-y-3">
                <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <KpiCard label={$t('risk.metrics.portfolioVolatility')} value={formatPercent(contributionOutput?.portfolio_volatility)} />
                    <KpiCard label={$t('risk.metrics.cashWeight')} value={formatPercent(contributionOutput?.cash_weight ?? 0)} />
                </div>
                <div class="space-y-2" data-testid="risk-contribution-bars">
                    {#each contributionRows as row}
                        <div class="grid grid-cols-[minmax(7rem,1fr)_minmax(10rem,2fr)_5rem] items-center gap-2 text-xs" data-testid="risk-contribution-row-{row.asset_id}">
                            <span class="truncate text-gray-600 dark:text-gray-300" title={row.name}>{row.name}</span>
                            <div class="relative h-5 rounded bg-gray-100 dark:bg-slate-700">
                                <div class="absolute left-1/2 top-0 h-full w-px bg-gray-400 dark:bg-slate-500"></div>
                                <div class="absolute top-1/2 h-2 -translate-y-1/2 rounded {row.percentage != null && row.percentage < 0 ? 'right-1/2 bg-red-500' : 'left-1/2 bg-blue-500'}" style={`width: ${row.barWidth}%`}></div>
                            </div>
                            <span class="text-right font-mono text-gray-700 dark:text-gray-200">{formatPercent(row.percentage, true)}</span>
                        </div>
                    {/each}
                </div>
            </div>
        </RiskResultFrame>
    {/if}

    {#if supportsVar}
        <RiskResultFrame title={analyticTitle('historical_var', 'risk.analytics.historicalVar.name')} description={analyticDescription('historical_var')} result={varResult} loading={initialLoading} {refreshing} testId="risk-var-section">
            <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <KpiCard label={$t('risk.metrics.var')} value={formatPercent(varOutput?.value_at_risk)} subLabel={varOutput ? `${formatPercent(varOutput.confidence_level)} · ${varOutput.horizon_days} ${$t('signals.units.days')}` : undefined} positive={false} />
                <KpiCard label={$t('risk.metrics.cvar')} value={formatPercent(varOutput?.conditional_value_at_risk)} subLabel={varOutput ? `${varOutput.observations} ${$t('risk.metadata.observations').toLowerCase()}` : undefined} positive={false} />
            </div>
        </RiskResultFrame>
    {/if}

    {#if supportsComparison}
        <section class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid="risk-comparison-controls">
            <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{analyticTitle('comparison', 'risk.analytics.comparison.name')}</h3>
            <p class="text-xs text-gray-400 dark:text-gray-500">{analyticDescription('comparison')}</p>
            <div class="mt-3 flex flex-wrap items-end gap-2">
                <SignalAssetParamControl
                    value={comparisonAssetId}
                    excludeAssetIds={scope.kind === 'asset' ? [scope.asset_id] : []}
                    testId="risk-comparison-asset-select"
                    onchange={(assetId) => {
                        comparisonAssetId = assetId;
                        comparisonResult = null;
                    }}
                />
                <button class="flex items-center gap-1.5 rounded-lg bg-libre-green px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50" onclick={runComparison} disabled={!comparisonAssetId || comparisonLoading} data-testid="risk-comparison-run">
                    <Play size={13} />
                    {$t('risk.actions.compare')}
                </button>
            </div>
        </section>

        {#if comparisonResult || comparisonLoading}
            <RiskResultFrame title={$t('risk.comparison.results')} result={comparisonResult} loading={comparisonLoading} testId="risk-comparison-section">
                <div class="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
                    <KpiCard label={$t('risk.metrics.activeReturn')} value={formatPercent(comparisonOutput?.active_return, true)} />
                    <KpiCard label={$t('risk.metrics.trackingError')} value={formatPercent(comparisonOutput?.tracking_error)} />
                    <KpiCard label={$t('risk.metrics.informationRatio')} value={formatRatio(singleValue(comparisonOutput?.information_ratio))} />
                    <KpiCard label={$t('risk.metrics.correlation')} value={formatRatio(singleValue(comparisonOutput?.correlation))} />
                    <KpiCard label={$t('risk.metrics.beta')} value={formatRatio(singleValue(comparisonOutput?.beta))} />
                </div>
                {#if comparisonOutput && comparisonPrimaryData.length > 0}
                    <div class="mt-4" data-testid="risk-comparison-chart">
                        <LineChart data={comparisonPrimaryData} overlaySignals={comparisonOverlay} currency="%" viewMode="percentage" colorByBaseline={false} showGradient={false} height="320px" />
                    </div>
                {/if}
            </RiskResultFrame>
        {/if}
    {/if}

    {#if supportsStress}
        <section class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid="risk-stress-controls">
            <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{analyticTitle('stress', 'risk.analytics.stress.name')}</h3>
            <p class="text-xs text-gray-400 dark:text-gray-500">{analyticDescription('stress')}</p>
            <div class="mt-3 flex flex-wrap items-end gap-2">
                <label class="text-xs text-gray-500 dark:text-gray-400">
                    {$t('risk.stress.uniformShock')}
                    <span class="mt-1 flex items-center gap-1">
                        <input class="w-24 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200" type="number" min="-100" step="1" bind:value={stressPercent} data-testid="risk-stress-input" />
                        <span>%</span>
                    </span>
                </label>
                <button class="flex items-center gap-1.5 rounded-lg bg-libre-green px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50" onclick={runStress} disabled={stressLoading} data-testid="risk-stress-run">
                    <Play size={13} />
                    {$t('risk.actions.runScenario')}
                </button>
            </div>
            {#if stressClientError}
                <p class="mt-2 text-xs text-amber-600 dark:text-amber-400" data-testid="risk-stress-no-assets">{$t('risk.states.noAssets')}</p>
            {/if}
        </section>

        {#if stressResult || stressLoading}
            <RiskResultFrame title={$t('risk.stress.results')} result={stressResult} loading={stressLoading} testId="risk-stress-section">
                <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <KpiCard label={$t('risk.metrics.scenarioReturn')} value={formatPercent(singleValue(stressOutput?.portfolio_return), true)} />
                    <KpiCard label={$t('risk.metrics.impactAmount')} value={formatAmount(stressOutput?.impact_amount)} />
                </div>
                {#if stressOutput?.impacts?.length}
                    <div class="mt-3 overflow-x-auto">
                        <table class="w-full text-xs" data-testid="risk-stress-impacts">
                            <thead class="text-left text-gray-400">
                                <tr>
                                    <th class="py-1">{$t('common.asset')}</th>
                                    <th class="py-1 text-right">{$t('risk.metrics.shock')}</th>
                                    <th class="py-1 text-right">{$t('risk.metrics.contribution')}</th>
                                    <th class="py-1 text-right">{$t('risk.metrics.impactAmount')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each stressOutput.impacts as impact}
                                    <tr class="border-t border-gray-100 dark:border-slate-700">
                                        <td class="py-1.5 text-gray-700 dark:text-gray-200">{assetLabels.get(impact.asset_id) ?? `#${impact.asset_id}`}</td>
                                        <td class="py-1.5 text-right font-mono">{formatPercent(impact.shock_return, true)}</td>
                                        <td class="py-1.5 text-right font-mono">{formatPercent(singleValue(impact.contribution_return), true)}</td>
                                        <td class="py-1.5 text-right font-mono">{formatAmount(impact.impact_amount)}</td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                {/if}
            </RiskResultFrame>
        {/if}
    {/if}

    {#if supportsSimulation}
        <section class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid="risk-simulation-controls">
            <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{analyticTitle('simulation', 'risk.analytics.simulation.name')}</h3>
            <p class="text-xs text-gray-400 dark:text-gray-500">{analyticDescription('simulation')}</p>
            <div class="mt-3 flex flex-wrap items-end gap-3">
                <label class="text-xs text-gray-500 dark:text-gray-400">
                    {$t('risk.params.sampling')}
                    <div class="mt-1 w-28">
                        <SimpleSelect
                            value={simulationSampling}
                            options={samplingOptions}
                            compact
                            testId="risk-simulation-sampling"
                            onchange={(value) => {
                                simulationSampling = value as 'mc' | 'qmc';
                            }}
                        />
                    </div>
                </label>
                <label class="text-xs text-gray-500 dark:text-gray-400">
                    {$t('risk.params.horizonDays')}
                    <input class="mt-1 block w-24 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200" type="number" min="1" max="3650" step="1" bind:value={simulationHorizonDays} data-testid="risk-simulation-horizon" />
                </label>
                <label class="text-xs text-gray-500 dark:text-gray-400">
                    {$t('risk.params.paths')}
                    <div class="mt-1 w-28">
                        <SimpleSelect value={String(simulationPaths)} options={pathOptions} compact testId="risk-simulation-paths" onchange={(value) => (simulationPaths = Number(value))} />
                    </div>
                </label>
                <label class="text-xs text-gray-500 dark:text-gray-400">
                    {$t('risk.params.seed')}
                    <input class="mt-1 block w-28 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200 disabled:opacity-50" type="number" min="0" step="1" bind:value={simulationSeed} data-testid="risk-simulation-seed" />
                </label>
                <button class="flex items-center gap-1.5 rounded-lg bg-libre-green px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50" onclick={runSimulation} disabled={simulationLoading} data-testid="risk-simulation-run">
                    <Play size={13} />
                    {$t('risk.actions.simulate')}
                </button>
            </div>
        </section>

        {#if simulationResult || simulationLoading}
            <RiskResultFrame title={$t('risk.simulation.simulated')} result={simulationResult} loading={simulationLoading} testId="risk-simulation-section">
                <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <KpiCard label={$t('risk.metrics.terminalMean')} value={formatPercent(simulationOutput?.terminal_mean_return, true)} />
                    <KpiCard label={$t('risk.metrics.terminalVolatility')} value={formatPercent(simulationOutput?.terminal_volatility)} />
                    <KpiCard label={$t('risk.metrics.probabilityOfLoss')} value={formatPercent(simulationOutput?.probability_of_loss)} positive={false} />
                </div>
                {#if simulationOutput && simulationData.length > 0}
                    <div class="mt-4" data-testid="risk-simulation-chart">
                        <LineChart data={simulationData} overlaySignals={simulationOverlay} currency="%" viewMode="percentage" colorByBaseline={false} showGradient={false} height="320px" />
                    </div>
                    <p class="mt-2 text-xs text-gray-400 dark:text-gray-500" data-testid="risk-simulation-assumptions">
                        {$t('risk.simulation.assumptions', {values: {paths: simulationOutput.paths, days: simulationOutput.horizon_days}})}
                    </p>
                {/if}
            </RiskResultFrame>
        {/if}
    {/if}

    <div class="hidden" data-testid="risk-frontier-capability" data-available={hasRiskCapability(catalog, 'frontier', scope.kind, 'current_composition') ? 'true' : 'false'}></div>

    <PageSyncModal bind:open={syncOpen} {dateStart} {dateEnd} assets={syncAssets} fxPairs={syncFxPairs} onsynced={handleSynced} onclose={() => (syncOpen = false)} />
</div>
