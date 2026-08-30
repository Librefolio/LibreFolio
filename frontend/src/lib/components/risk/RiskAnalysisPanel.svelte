<script lang="ts">
    import {untrack} from 'svelte';
    import {goto} from '$app/navigation';
    import {Play, RefreshCw, RotateCw} from 'lucide-svelte';
    import type {z} from 'zod';

    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import type {RenderedSignal} from '$lib/charts/signals';
    import SignalAssetParamControl from '$lib/components/charts/SignalAssetParamControl.svelte';
    import LineChart, {type LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import KpiCard from '$lib/components/dashboard/KpiCard.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import PageSyncModal from '$lib/components/ui/modals/PageSyncModal.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import TabBar from '$lib/components/ui/tabs/TabBar.svelte';
    import {buildHistoricalReplayParameters, buildHypotheticalShockParameters, buildRiskAnalyticRequest, buildRiskQueryRequest, buildSimulationParameters, type RiskScenarioDimension, type SimulationView} from '$lib/risk/riskRequest';
    import {assetStoreVersion, ensureAssetsLoaded, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {ensureCountriesLoaded, getAllCountries, getCountryInfo} from '$lib/stores/reference/countryStore';
    import {ensureFxRoutesLoaded, fxRoutesVersion, getConfiguredPairSlugs} from '$lib/stores/reference/fxRoutesStore';
    import {ensureSectorsLoaded, getSectorEmoji, getSectorKeys} from '$lib/stores/reference/sectorStore';
    import {
        fetchRiskCatalog,
        fetchRiskScenarioCatalog,
        getRiskDefinition,
        hasRiskCapability,
        invalidateRisk,
        queryRisk,
        type RiskAnalyticResult,
        type RiskCatalogResponse,
        type RiskMode,
        type RiskQueryRequest,
        type RiskScenarioCatalogResponse,
        type RiskScope,
    } from '$lib/stores/risk/riskStore.svelte';
    import {riskDataQuality, riskMetadata, riskOutput, singleValue, type RiskDataQualityReport} from '$lib/risk/riskTypes';
    import {sectorI18nKey} from '$lib/utils/assetTypes';
    import CorrelationHeatmap from './CorrelationHeatmap.svelte';
    import RiskBetaBanner from './RiskBetaBanner.svelte';
    import RiskResultFrame from './RiskResultFrame.svelte';

    import {numericArrows} from '$lib/actions/numericArrows';
    import {formatPercent as sharedFormatPercent} from '$lib/utils/core/formatPercent';
    import * as riskHelpers from './riskAnalysisHelpers';
    interface Props {
        scope: RiskScope;
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        assetIds?: number[];
        title?: string;
        subtitle?: string;
        internalSubset?: boolean;
        assetClass?: string | null;
        sectorExposure?: Record<string, number> | null;
        geographyExposure?: Record<string, number> | null;
        refreshVersion?: number;
        showHeaderActions?: boolean;
        showBetaBanner?: boolean;
        onsynced?: () => void | Promise<void>;
    }

    let {scope, dateStart, dateEnd, targetCurrency, assetIds = [], title = '', subtitle = '', internalSubset = false, assetClass = null, sectorExposure = null, geographyExposure = null, refreshVersion = 0, showHeaderActions = true, showBetaBanner = true, onsynced}: Props = $props();

    let catalog = $state<RiskCatalogResponse | null>(null);
    let scenarioCatalog = $state<RiskScenarioCatalogResponse | null>(null);
    let scenarioCatalogLoading = $state(false);
    let historicalResults = $state<RiskAnalyticResult[]>([]);
    let currentResults = $state<RiskAnalyticResult[]>([]);
    let comparisonResult = $state<RiskAnalyticResult | null>(null);
    let stressResult = $state<RiskAnalyticResult | null>(null);
    let replayResult = $state<RiskAnalyticResult | null>(null);
    let simulationResult = $state<RiskAnalyticResult | null>(null);
    let initialLoading = $state(true);
    let refreshing = $state(false);
    let loadError = $state(false);
    let requestGeneration = 0;
    let comparisonGeneration = 0;
    let stressGeneration = 0;
    let replayGeneration = 0;
    let simulationGeneration = 0;
    let lastBaseSignature = '';
    let lastRefreshVersion = untrack(() => refreshVersion);

    let comparisonAssetId = $state<number | undefined>(undefined);
    let comparisonLoading = $state(false);
    let stressLoading = $state(false);
    let replayLoading = $state(false);
    let simulationLoading = $state(false);
    let stressClientError = $state(false);
    let stressPercent = $state(-10);
    let stressPresetId = $state('');
    let stressDimension = $state<RiskScenarioDimension>('asset_class');
    let stressBucketShocks = $state<Record<string, number>>({});
    let stressShowAllBuckets = $state(false);
    let stressEditedBuckets = $state(new Set<string>());
    let stressPresetInitialized = $state(false);
    let replayPresetId = $state('');
    let replayStart = $state(untrack(() => dateStart));
    let replayEnd = $state(untrack(() => dateEnd));
    let replayProxyAssetId = $state<number | undefined>(undefined);
    let replayExcludeAsset = $state(false);
    let replayPresetInitialized = $state(false);
    let riskFreePercentInput = $state(0);
    let appliedRiskFreePercent = $state(0);
    let simulationSampling = $state<'mc' | 'qmc'>('mc');
    let simulationHorizonDays = $state(365);
    let simulationPaths = $state(8192);
    let simulationRandomSeed = $state(123456);
    let simulationSobolStartIndex = $state(123456);
    let simulationView = $state<SimulationView>('evolution');
    let syncOpen = $state(false);
    let referenceLabelsVersion = $state(0);

    const samplingOptions = [
        {value: 'mc', label: 'MC'},
        {value: 'qmc', label: 'QMC'},
    ];
    const pathOptions = [1024, 2048, 4096, 8192, 16384].map((value) => ({value: String(value), label: value.toLocaleString()}));
    const stressAssetClasses = ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'CROWDFUND', 'HOLD', 'INDEX', 'OTHER'] as const;
    const simulationTabs = $derived([
        {id: 'evolution', label: $t('risk.simulation.evolution'), testId: 'risk-simulation-view-evolution'},
        {id: 'terminal_distribution', label: $t('risk.simulation.terminalDistribution'), testId: 'risk-simulation-view-terminal'},
    ]);

    type HistoricalReplayScenario = z.output<typeof schemas.RiskHistoricalReplayScenario>;
    type HypotheticalShockScenario = z.output<typeof schemas.RiskHypotheticalShockScenario>;

    let supportsKpi = $derived(hasRiskCapability(catalog, 'historical_kpi', scope.kind, 'historical'));
    let supportsCorrelation = $derived(hasRiskCapability(catalog, 'correlation', scope.kind, 'historical'));
    let supportsContribution = $derived(hasRiskCapability(catalog, 'risk_contribution', scope.kind, 'current_composition'));
    let supportsVar = $derived(hasRiskCapability(catalog, 'historical_var', scope.kind, 'historical'));
    let supportsComparison = $derived(hasRiskCapability(catalog, 'comparison', scope.kind, 'historical'));
    let supportsStress = $derived(hasRiskCapability(catalog, 'stress', scope.kind, 'current_composition'));
    let supportsSimulation = $derived(hasRiskCapability(catalog, 'simulation', scope.kind, 'current_composition'));

    let kpiResult = $derived(resultByCode(historicalResults, 'historical_kpi'));
    let correlationResult = $derived(resultByCode(historicalResults, 'correlation'));
    let contributionResult = $derived(resultByCode(currentResults, 'risk_contribution'));
    let varResult = $derived(resultByCode(historicalResults, 'historical_var'));

    let kpiOutput = $derived(riskOutput(kpiResult, schemas.RiskKpiOutput));
    let correlationOutput = $derived(riskOutput(correlationResult, schemas.RiskCorrelationOutput));
    let contributionOutput = $derived(riskOutput(contributionResult, schemas.RiskContributionOutput));
    let varOutput = $derived(riskOutput(varResult, schemas.RiskVarCvarOutput));
    let comparisonOutput = $derived(riskOutput(comparisonResult, schemas.RiskComparisonOutput));
    let stressOutput = $derived(riskOutput(stressResult, schemas.RiskStressOutput));
    let replayOutput = $derived(riskOutput(replayResult, schemas.RiskStressOutput));
    let simulationOutput = $derived(riskOutput(simulationResult, schemas.RiskSimulationOutput));
    let replayAudit = $derived(singleValue(riskMetadata(replayResult)?.historical_replay_audit));
    let simulationTerminalPoint = $derived(simulationOutput?.percentile_bands.at(-1) ?? null);

    let historicalReplayScenarios = $derived.by<HistoricalReplayScenario[]>(() =>
        (scenarioCatalog?.items ?? []).flatMap((entry) => {
            const parsed = schemas.RiskHistoricalReplayScenario.safeParse(entry.scenario);
            return parsed.success ? [parsed.data] : [];
        }),
    );
    let hypotheticalShockScenarios = $derived.by<HypotheticalShockScenario[]>(() =>
        (scenarioCatalog?.items ?? []).flatMap((entry) => {
            const parsed = schemas.RiskHypotheticalShockScenario.safeParse(entry.scenario);
            return parsed.success ? [parsed.data] : [];
        }),
    );
    let historicalReplayOptions = $derived(historicalReplayScenarios.map((scenario) => ({value: scenario.id, label: localizedScenarioText(scenario.name)})));
    let hypotheticalShockOptions = $derived(hypotheticalShockScenarios.map((scenario) => ({value: scenario.id, label: localizedScenarioText(scenario.name)})));
    let selectedHypotheticalScenario = $derived(hypotheticalShockScenarios.find((scenario) => scenario.id === stressPresetId) ?? null);
    let stressDimensionOptions = $derived(
        (selectedHypotheticalScenario?.allowed_dimensions ?? ['asset_class', 'sector', 'geography']).map((dimension) => ({
            value: dimension,
            label: $t(`risk.stress.dimensions.${dimension}`),
        })),
    );
    let stressPresentBuckets = $derived(presentStressBuckets(stressDimension));
    let stressAllBuckets = $derived.by(() => {
        void referenceLabelsVersion;
        const buckets = new Set([...stressPresentBuckets, ...Object.keys(stressBucketShocks)]);
        if (stressDimension === 'asset_class') stressAssetClasses.forEach((bucket) => buckets.add(bucket));
        if (stressDimension === 'sector') getSectorKeys().forEach((bucket) => buckets.add(bucket));
        if (stressDimension === 'geography') {
            getAllCountries().forEach((country) => buckets.add(country.iso3));
            scenarioCatalog?.geography_groups?.forEach((group) => buckets.add(group.id));
        }
        if (stressDimension !== 'asset_class') buckets.add('Other');
        return [...buckets].sort((left, right) => left.localeCompare(right));
    });
    let stressVisibleBuckets = $derived.by(() => {
        if (stressShowAllBuckets) return stressAllBuckets;
        const visible = new Set([...stressPresentBuckets, ...stressEditedBuckets]);
        if (stressDimension !== 'asset_class') visible.add('Other');
        return [...visible].sort((left, right) => left.localeCompare(right));
    });

    let scopeAssetIds = $derived.by(() => {
        const ids = new Set<number>(assetIds);
        if (scope.kind === 'asset') ids.add(scope.asset_id);
        if (scope.kind === 'asset_set') scope.asset_ids.forEach((assetId) => ids.add(assetId));
        if (replayProxyAssetId) ids.add(replayProxyAssetId);
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
                aggregationProfile: 'last_with_range',
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
                aggregationProfile: 'band_envelope',
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

    let allResults = $derived([kpiResult, correlationResult, contributionResult, varResult, comparisonResult, stressResult, replayResult, simulationResult].filter((result): result is RiskAnalyticResult => result !== null && result !== undefined));
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
        // A run the user already asked for has to survive a late-arriving parameter.
        // The asset page resolves `dateStart` from the first price response and
        // `targetCurrency` from the asset payload, so on a slow link the signature
        // moves *after* the button was pressed. Dropping the in-flight answer is
        // right — it was computed for parameters that no longer hold — but dropping
        // the request with it leaves the user with no chart, no spinner and no
        // error, and nothing that says to press again. Re-issue instead.
        const rerun = untrack(() => ({
            comparison: comparisonLoading,
            stress: stressLoading,
            replay: replayLoading,
            simulation: simulationLoading,
        }));
        comparisonGeneration += 1;
        stressGeneration += 1;
        replayGeneration += 1;
        simulationGeneration += 1;
        comparisonResult = null;
        stressResult = null;
        replayResult = null;
        simulationResult = null;
        comparisonLoading = false;
        stressLoading = false;
        replayLoading = false;
        simulationLoading = false;
        untrack(() => {
            void loadBase(false);
            if (rerun.comparison) void runComparison();
            if (rerun.stress) void runStress();
            if (rerun.replay) void runReplay();
            if (rerun.simulation) void runSimulation();
        });
    });

    $effect(() => {
        const version = refreshVersion;
        if (version === lastRefreshVersion) return;
        lastRefreshVersion = version;
        untrack(() => void loadBase(true));
    });

    $effect(() => {
        untrack(() => {
            void Promise.all([ensureAssetsLoaded(), ensureFxRoutesLoaded()]);
            if (scope.kind === 'asset') void loadScenarioCatalog();
        });
    });

    $effect(() => {
        const language = $currentLanguage;
        untrack(() => {
            void Promise.all([ensureCountriesLoaded(language), ensureSectorsLoaded()]).then(() => {
                referenceLabelsVersion += 1;
            });
        });
    });

    function localizedScenarioText(value: unknown): string {
        return riskHelpers.localizedScenarioText(value, $currentLanguage);
    }

    function scalarString(value: unknown): string | null {
        return riskHelpers.scalarString(value);
    }

    function numberRecord(value: unknown): Record<string, number> {
        return riskHelpers.numberRecord(value);
    }

    function presentStressBuckets(dimension: RiskScenarioDimension): string[] {
        return riskHelpers.presentStressBuckets(dimension, {assetClass, sectorExposure, geographyExposure});
    }

    function stressBucketLabel(bucket: string, dimension: RiskScenarioDimension): string {
        void referenceLabelsVersion;
        if (bucket === 'Other') return $t('common.other');
        if (bucket === 'european_union') return $t('risk.stress.europeanUnion');
        if (dimension === 'asset_class') return $t(`assets.types.${bucket}`);
        if (dimension === 'sector') return `${getSectorEmoji(bucket)} ${$t(`sectors.${sectorI18nKey(bucket)}`)}`;
        const country = getCountryInfo(bucket);
        return `${country.flag_emoji} ${country.name}`;
    }

    function stressImpactDimension(value: unknown): RiskScenarioDimension {
        return riskHelpers.stressImpactDimension(value, stressDimension);
    }

    function applyReplayPreset(scenario: HistoricalReplayScenario): void {
        replayPresetId = scenario.id;
        replayStart = scalarString(scenario.defaults.start) ?? dateStart;
        replayEnd = scalarString(scenario.defaults.end) ?? dateEnd;
        replayPresetInitialized = true;
        replayResult = null;
        replayGeneration += 1;
    }

    function applyStressPreset(scenario: HypotheticalShockScenario): void {
        stressPresetId = scenario.id;
        stressDimension = scenario.defaults.dimension;
        stressBucketShocks = numberRecord(scenario.defaults.bucket_shocks);
        if (stressDimension !== 'asset_class' && stressBucketShocks.Other === undefined) stressBucketShocks = {...stressBucketShocks, Other: 0};
        stressEditedBuckets = new Set();
        stressShowAllBuckets = false;
        stressPresetInitialized = true;
        stressResult = null;
        stressGeneration += 1;
    }

    function initializeScenarioEditors(): void {
        if (!replayPresetInitialized) {
            const replayPreset = historicalReplayScenarios.find((scenario) => scenario.id === 'custom_period') ?? historicalReplayScenarios[0];
            if (replayPreset) applyReplayPreset(replayPreset);
            else {
                replayStart = dateStart;
                replayEnd = dateEnd;
                replayPresetInitialized = true;
            }
        }
        if (!stressPresetInitialized) {
            const stressPreset = hypotheticalShockScenarios.find((scenario) => scenario.id === 'global_risk_off') ?? hypotheticalShockScenarios[0];
            if (stressPreset) applyStressPreset(stressPreset);
            else {
                const bucket = presentStressBuckets('asset_class')[0];
                stressBucketShocks = {[bucket]: -0.1};
                stressPresetInitialized = true;
            }
        }
    }

    async function loadScenarioCatalog(): Promise<void> {
        if (scenarioCatalog || scenarioCatalogLoading) return;
        scenarioCatalogLoading = true;
        try {
            scenarioCatalog = await fetchRiskScenarioCatalog();
        } catch (error) {
            console.error('[Risk] Failed to load scenario catalog:', error);
        } finally {
            scenarioCatalogLoading = false;
            initializeScenarioEditors();
        }
    }

    function selectReplayPreset(presetId: string): void {
        const preset = historicalReplayScenarios.find((scenario) => scenario.id === presetId);
        if (preset) applyReplayPreset(preset);
    }

    function selectStressPreset(presetId: string): void {
        const preset = hypotheticalShockScenarios.find((scenario) => scenario.id === presetId);
        if (preset) applyStressPreset(preset);
    }

    function changeStressDimension(dimension: RiskScenarioDimension): void {
        stressDimension = dimension;
        const buckets = presentStressBuckets(dimension);
        stressBucketShocks = Object.fromEntries(buckets.map((bucket) => [bucket, stressBucketShocks[bucket] ?? 0]));
        if (dimension !== 'asset_class' && stressBucketShocks.Other === undefined) stressBucketShocks = {...stressBucketShocks, Other: 0};
        stressEditedBuckets = new Set();
        stressShowAllBuckets = false;
        stressResult = null;
        stressGeneration += 1;
    }

    function updateStressBucket(bucket: string, percentage: number): void {
        stressBucketShocks = {...stressBucketShocks, [bucket]: percentage / 100};
        stressEditedBuckets = new Set(stressEditedBuckets).add(bucket);
        stressResult = null;
        stressGeneration += 1;
    }

    function resultByCode(results: RiskAnalyticResult[], analyticCode: string): RiskAnalyticResult | null {
        return riskHelpers.resultByCode(results, analyticCode);
    }

    function normalizeQualityIssue(issue: NonNullable<RiskDataQualityReport['issues']>[number]): DataQualityIssue {
        return riskHelpers.normalizeQualityIssue(issue);
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
        return riskHelpers.buildBaseAnalytics(mode, {
            appliedRiskFreePercent,
            hasCapability: (code, capabilityMode) => hasRiskCapability(catalog, code, scope.kind, capabilityMode),
        });
    }

    async function loadBase(force: boolean): Promise<void> {
        const generation = ++requestGeneration;
        const hadResults = historicalResults.length > 0 || currentResults.length > 0;
        initialLoading = !hadResults;
        refreshing = hadResults;
        loadError = false;

        try {
            catalog = await fetchRiskCatalog();
            if (generation !== requestGeneration) return;
            // A null catalog is a *failure* to load, not a slow load: without this
            // the panel would sit at data-catalog="pending" forever and every gated
            // section would silently look "not supported".
            if (!catalog) {
                loadError = true;
                return;
            }

            const historicalAnalytics = buildBaseAnalytics('historical');
            const currentAnalytics = buildBaseAnalytics('current_composition');
            const [historical, current] = await Promise.all([
                historicalAnalytics.length > 0
                    ? queryRisk(
                          buildRiskQueryRequest({
                              scope,
                              dateStart,
                              dateEnd,
                              targetCurrency,
                              mode: 'historical',
                              analytics: historicalAnalytics,
                          }),
                          force,
                      )
                    : null,
                currentAnalytics.length > 0
                    ? queryRisk(
                          buildRiskQueryRequest({
                              scope,
                              dateStart,
                              dateEnd,
                              targetCurrency,
                              mode: 'current_composition',
                              compositionPolicy: 'current_buy_and_hold',
                              analytics: currentAnalytics,
                          }),
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
        const response = await queryRisk(
            buildRiskQueryRequest({
                scope,
                dateStart,
                dateEnd,
                targetCurrency,
                mode,
                compositionPolicy: mode === 'current_composition' ? 'current_buy_and_hold' : undefined,
                analytics: [buildRiskAnalyticRequest(`single-${code}`, code, parameters)],
            }),
        );
        return response?.items?.[0] ?? null;
    }

    async function runComparison(): Promise<void> {
        if (!comparisonAssetId) return;
        const generation = ++comparisonGeneration;
        comparisonLoading = true;
        try {
            const result = await runSingle('comparison', 'historical', {comparison_asset_id: comparisonAssetId});
            if (generation === comparisonGeneration) comparisonResult = result;
        } catch (error) {
            console.error('[Risk] Comparison failed:', error);
            if (generation === comparisonGeneration) comparisonResult = null;
        } finally {
            if (generation === comparisonGeneration) comparisonLoading = false;
        }
    }

    async function runStress(): Promise<void> {
        stressClientError = scopeAssetIds.length === 0;
        if (stressClientError) return;
        const generation = ++stressGeneration;
        stressLoading = true;
        try {
            const assetBucketShocks = Object.keys(stressBucketShocks).length > 0 ? stressBucketShocks : {[presentStressBuckets('asset_class')[0]]: stressPercent / 100};
            const result = await runSingle(
                'stress',
                'current_composition',
                scope.kind === 'asset'
                    ? buildHypotheticalShockParameters({
                          dimension: stressDimension,
                          bucketShocks: assetBucketShocks,
                      })
                    : buildHypotheticalShockParameters({
                          dimension: 'asset_class',
                          bucketShocks: Object.fromEntries(stressAssetClasses.map((assetType) => [assetType, stressPercent / 100])),
                      }),
            );
            if (generation === stressGeneration) stressResult = result;
        } catch (error) {
            console.error('[Risk] Stress failed:', error);
            if (generation === stressGeneration) stressResult = null;
        } finally {
            if (generation === stressGeneration) stressLoading = false;
        }
    }

    async function runReplay(): Promise<void> {
        if (scope.kind !== 'asset') return;
        const generation = ++replayGeneration;
        replayLoading = true;
        try {
            const result = await runSingle(
                'stress',
                'current_composition',
                buildHistoricalReplayParameters({
                    start: replayStart,
                    end: replayEnd,
                    missingHistoryPolicy: 'manual_proxy_or_exclude',
                    proxyAssets: replayProxyAssetId && !replayExcludeAsset ? [{asset_id: scope.asset_id, proxy_asset_id: replayProxyAssetId}] : [],
                    excludedAssetIds: replayExcludeAsset ? [scope.asset_id] : [],
                }),
            );
            if (generation === replayGeneration) replayResult = result;
        } catch (error) {
            console.error('[Risk] Historical replay failed:', error);
            if (generation === replayGeneration) replayResult = null;
        } finally {
            if (generation === replayGeneration) replayLoading = false;
        }
    }

    async function runSimulation(): Promise<void> {
        const generation = ++simulationGeneration;
        simulationLoading = true;
        try {
            const result = await runSingle(
                'simulation',
                'current_composition',
                buildSimulationParameters({
                    samplingMethod: simulationSampling,
                    horizonDays: simulationHorizonDays,
                    pathCount: simulationPaths,
                    randomSeed: simulationRandomSeed,
                    sobolStartIndex: simulationSobolStartIndex,
                }),
            );
            if (generation === simulationGeneration) simulationResult = result;
        } catch (error) {
            console.error('[Risk] Simulation failed:', error);
            if (generation === simulationGeneration) simulationResult = null;
        } finally {
            if (generation === simulationGeneration) simulationLoading = false;
        }
    }

    async function handleSynced(): Promise<void> {
        invalidateRisk();
        comparisonGeneration += 1;
        stressGeneration += 1;
        replayGeneration += 1;
        simulationGeneration += 1;
        comparisonResult = null;
        stressResult = null;
        replayResult = null;
        simulationResult = null;
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

    /** Fractions from the risk API, hence scale 100. Unlike the lot charts this
     *  one defaults to *unsigned*: most of these figures are shares, not deltas. */
    const formatPercent = (value: number | null | undefined, signed = false): string => sharedFormatPercent(value, {scale: 100, signed});

    function formatRatio(value: number | null | undefined): string {
        return riskHelpers.formatRatio(value);
    }

    function formatAmount(value: string | readonly (string | null)[] | null | undefined): string {
        return riskHelpers.formatCurrencyAmount(value, targetCurrency);
    }

    function addDays(baseDate: string, days: number): string {
        return riskHelpers.addDays(baseDate, days);
    }
</script>

<!--
    `data-catalog` publishes whether the capability catalog has landed. Every
    section below is gated on it (`supportsComparison`, `supportsStress`, …), so
    a caller that clicks straight into one of them is really betting on a fetch
    it cannot see. Absence of a section means "not supported" *or* "not loaded
    yet"; this attribute separates the two — and `error` separates a fetch that
    failed from one that is merely slow, which `pending` alone could not say.
-->
<div class="space-y-4" data-testid="risk-analysis-panel" data-catalog={catalog ? 'ready' : loadError ? 'error' : 'pending'} data-busy={initialLoading ? 'true' : 'false'}>
    {#if showBetaBanner}
        <RiskBetaBanner />
    {/if}

    <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">{title || $t('risk.title')}</h2>
            {#if subtitle || internalSubset}
                <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="risk-scope-label">
                    {internalSubset ? $t('risk.internalSubset') : subtitle}
                </p>
            {/if}
        </div>
        {#if showHeaderActions}
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
        {/if}
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
                    <input
                        class="w-24 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200"
                        type="number"
                        use:numericArrows={{step: 0.1}}
                        step="0.1"
                        min="-99.9"
                        bind:value={riskFreePercentInput}
                        data-testid="risk-free-rate-input"
                    />
                    <span>%</span>
                </span>
            </label>
            <button class="rounded-lg bg-libre-green px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50" onclick={() => (appliedRiskFreePercent = riskFreePercentInput)} disabled={riskFreePercentInput === appliedRiskFreePercent} data-testid="risk-free-apply">
                {$t('common.apply')}
            </button>
        </div>

        <RiskResultFrame title={analyticTitle('historical_kpi', 'risk.analytics.historicalKpi.name')} description={analyticDescription('historical_kpi')} result={kpiResult} loading={initialLoading} {refreshing} testId="risk-kpi-section">
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
                        comparisonGeneration += 1;
                        comparisonAssetId = assetId;
                        comparisonResult = null;
                        comparisonLoading = false;
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
            {#if scope.kind === 'asset'}
                <div class="mt-3 grid gap-3 sm:grid-cols-2">
                    <label class="text-xs text-gray-500 dark:text-gray-400">
                        {$t('risk.stress.preset')}
                        <div class="mt-1">
                            <SimpleSelect value={stressPresetId} options={hypotheticalShockOptions} compact testId="risk-stress-preset" onchange={selectStressPreset} />
                        </div>
                    </label>
                    <label class="text-xs text-gray-500 dark:text-gray-400">
                        {$t('risk.stress.dimension')}
                        <div class="mt-1">
                            <SimpleSelect value={stressDimension} options={stressDimensionOptions} compact testId="risk-stress-dimension" onchange={(value) => changeStressDimension(value as RiskScenarioDimension)} />
                        </div>
                    </label>
                </div>
                <div class="mt-3 space-y-2" data-testid="risk-stress-buckets">
                    {#each stressVisibleBuckets as bucket}
                        <label class="grid grid-cols-[minmax(8rem,1fr)_7rem] items-center gap-2 text-xs text-gray-500 dark:text-gray-400" data-testid="risk-stress-bucket-{bucket}">
                            <span class="truncate" title={stressBucketLabel(bucket, stressDimension)}>{stressBucketLabel(bucket, stressDimension)}</span>
                            <span class="flex items-center gap-1">
                                <input
                                    class="w-full rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200"
                                    type="number"
                                    use:numericArrows
                                    min="-100"
                                    max="100"
                                    step="1"
                                    value={(stressBucketShocks[bucket] ?? 0) * 100}
                                    data-testid="risk-stress-bucket-input-{bucket}"
                                    oninput={(event) => updateStressBucket(bucket, Number(event.currentTarget.value))}
                                />
                                <span>%</span>
                            </span>
                        </label>
                    {/each}
                </div>
                <label class="mt-3 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                    <input type="checkbox" bind:checked={stressShowAllBuckets} data-testid="risk-stress-show-all" />
                    {$t('risk.stress.showAllBuckets')}
                </label>
            {:else}
                <div class="mt-3 flex flex-wrap items-end gap-2">
                    <label class="text-xs text-gray-500 dark:text-gray-400">
                        {$t('risk.stress.uniformShock')}
                        <span class="mt-1 flex items-center gap-1">
                            <input class="w-24 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200" type="number" use:numericArrows min="-100" step="1" bind:value={stressPercent} data-testid="risk-stress-input" />
                            <span>%</span>
                        </span>
                    </label>
                </div>
            {/if}
            <div class="mt-3 flex items-center gap-2">
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
                    <div class="mt-4 space-y-3" data-testid="risk-stress-audit">
                        <h4 class="text-xs font-semibold text-gray-600 dark:text-gray-300">{$t('risk.stress.auditTitle')}</h4>
                        {#each stressOutput.impacts as impact}
                            <div class="rounded-lg border border-gray-100 p-3 dark:border-slate-700" data-testid="risk-stress-audit-asset-{impact.asset_id}">
                                <p class="text-xs font-medium text-gray-700 dark:text-gray-200">{assetLabels.get(impact.asset_id) ?? `#${impact.asset_id}`}</p>
                                {#if singleValue(impact.metadata_fallback)}
                                    <p class="mt-1 text-xs text-amber-600 dark:text-amber-400" data-testid="risk-stress-metadata-fallback-{impact.asset_id}">
                                        {$t('risk.stress.missingMetadataOther')}
                                    </p>
                                {/if}
                                {#if (impact.bucket_audit ?? []).length > 0}
                                    <div class="mt-2 overflow-x-auto">
                                        <table class="w-full text-xs">
                                            <thead class="text-left text-gray-400">
                                                <tr>
                                                    <th class="py-1">{$t('risk.stress.exposureBucket')}</th>
                                                    <th class="py-1 text-right">{$t('risk.stress.exposure')}</th>
                                                    <th class="py-1">{$t('risk.stress.appliedBucket')}</th>
                                                    <th class="py-1 text-right">{$t('risk.metrics.shock')}</th>
                                                    <th class="py-1 text-right">{$t('risk.metrics.contribution')}</th>
                                                    <th class="py-1">{$t('risk.stress.rule')}</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {#each impact.bucket_audit ?? [] as audit}
                                                    {@const appliedBucket = scalarString(audit.applied_bucket_id)}
                                                    <tr class="border-t border-gray-100 dark:border-slate-700" data-testid="risk-stress-audit-bucket-{impact.asset_id}-{audit.exposure_bucket_id}">
                                                        <td class="py-1.5 text-gray-700 dark:text-gray-200">{stressBucketLabel(audit.exposure_bucket_id, stressImpactDimension(impact.dimension))}</td>
                                                        <td class="py-1.5 text-right font-mono">{formatPercent(audit.exposure)}</td>
                                                        <td class="py-1.5 text-gray-700 dark:text-gray-200">{appliedBucket ? stressBucketLabel(appliedBucket, stressImpactDimension(impact.dimension)) : '—'}</td>
                                                        <td class="py-1.5 text-right font-mono">{formatPercent(audit.bucket_shock, true)}</td>
                                                        <td class="py-1.5 text-right font-mono">{formatPercent(audit.shock_contribution, true)}</td>
                                                        <td class="py-1.5 text-gray-700 dark:text-gray-200">{$t(`risk.stress.rules.${audit.rule}`)}</td>
                                                    </tr>
                                                {/each}
                                            </tbody>
                                        </table>
                                    </div>
                                {/if}
                            </div>
                        {/each}
                    </div>
                {/if}
            </RiskResultFrame>
        {/if}

        {#if scope.kind === 'asset'}
            <section class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid="risk-replay-controls">
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{$t('risk.replay.title')}</h3>
                <p class="text-xs text-gray-400 dark:text-gray-500">{$t('risk.replay.compositionNotice')}</p>
                <div class="mt-3 grid gap-3 sm:grid-cols-3">
                    <label class="text-xs text-gray-500 dark:text-gray-400">
                        {$t('risk.replay.preset')}
                        <div class="mt-1">
                            <SimpleSelect value={replayPresetId} options={historicalReplayOptions} compact testId="risk-replay-preset" onchange={selectReplayPreset} />
                        </div>
                    </label>
                    <label class="text-xs text-gray-500 dark:text-gray-400">
                        {$t('risk.replay.start')}
                        <input class="mt-1 block w-full rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200" type="date" bind:value={replayStart} data-testid="risk-replay-start" />
                    </label>
                    <label class="text-xs text-gray-500 dark:text-gray-400">
                        {$t('risk.replay.end')}
                        <input class="mt-1 block w-full rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200" type="date" bind:value={replayEnd} data-testid="risk-replay-end" />
                    </label>
                </div>
                <div class="mt-3 flex flex-wrap items-end gap-3">
                    <div>
                        <span class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.replay.proxy')}</span>
                        <SignalAssetParamControl
                            value={replayProxyAssetId}
                            excludeAssetIds={[scope.asset_id]}
                            testId="risk-replay-proxy-select"
                            onchange={(assetId) => {
                                replayGeneration += 1;
                                replayProxyAssetId = assetId;
                                if (assetId) replayExcludeAsset = false;
                                replayResult = null;
                            }}
                        />
                    </div>
                    <label class="flex items-center gap-2 pb-1 text-xs text-gray-500 dark:text-gray-400">
                        <input
                            type="checkbox"
                            checked={replayExcludeAsset}
                            data-testid="risk-replay-exclude"
                            onchange={(event) => {
                                replayGeneration += 1;
                                replayExcludeAsset = event.currentTarget.checked;
                                if (replayExcludeAsset) replayProxyAssetId = undefined;
                                replayResult = null;
                            }}
                        />
                        {$t('risk.replay.exclude')}
                    </label>
                    <button class="flex items-center gap-1.5 rounded-lg bg-libre-green px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50" onclick={runReplay} disabled={replayLoading || !replayStart || !replayEnd} data-testid="risk-replay-run">
                        <Play size={13} />
                        {$t('risk.actions.runReplay')}
                    </button>
                </div>
            </section>

            {#if replayResult || replayLoading}
                <RiskResultFrame title={$t('risk.replay.results')} result={replayResult} loading={replayLoading} testId="risk-replay-section">
                    <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <KpiCard label={$t('risk.metrics.scenarioReturn')} value={formatPercent(singleValue(replayOutput?.portfolio_return), true)} />
                        <KpiCard label={$t('risk.metrics.impactAmount')} value={formatAmount(replayOutput?.impact_amount)} />
                    </div>
                    {#if replayAudit}
                        <div class="mt-3 space-y-2 text-xs text-gray-600 dark:text-gray-300" data-testid="risk-replay-audit">
                            <p>{$t('risk.replay.proxyCount')}: <strong>{replayAudit.proxy_count}</strong></p>
                            <p>{$t('risk.replay.excludedCount')}: <strong>{replayAudit.excluded_count}</strong></p>
                            <p data-testid="risk-replay-audit-missing-history-policy">
                                {$t('risk.replay.missingHistoryPolicy')}:
                                <strong>{$t(`risk.replay.missingHistoryPolicies.${replayAudit.missing_history_policy}`)}</strong>
                            </p>
                            <p data-testid="risk-replay-audit-composition-policy">
                                {$t('risk.replay.compositionPolicy')}:
                                <strong>{$t(`risk.replay.compositionPolicies.${replayAudit.composition_policy}`)}</strong>
                            </p>
                            <p data-testid="risk-replay-audit-proxy-series-usage">
                                {$t('risk.replay.proxySeriesUsage')}:
                                <strong>{$t(`risk.replay.proxySeriesUsages.${replayAudit.proxy_series_usage}`)}</strong>
                            </p>
                            {#each replayAudit.proxy_assets ?? [] as mapping}
                                <p data-testid="risk-replay-audit-proxy-{mapping.asset_id}">
                                    {assetLabels.get(mapping.asset_id) ?? `#${mapping.asset_id}`} → {assetLabels.get(mapping.proxy_asset_id) ?? getAssetInfo(mapping.proxy_asset_id)?.display_name ?? `#${mapping.proxy_asset_id}`}
                                </p>
                            {/each}
                            {#each replayAudit.excluded_assets ?? [] as excluded}
                                <p data-testid="risk-replay-audit-excluded-{excluded.asset_id}">
                                    {assetLabels.get(excluded.asset_id) ?? `#${excluded.asset_id}`} · {$t(`risk.replay.treatment.${excluded.treatment}`)}
                                </p>
                            {/each}
                        </div>
                    {/if}
                </RiskResultFrame>
            {/if}
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
                    <input
                        class="mt-1 block w-24 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200"
                        type="number"
                        use:numericArrows
                        min="1"
                        max="3650"
                        step="1"
                        bind:value={simulationHorizonDays}
                        data-testid="risk-simulation-horizon"
                    />
                </label>
                <label class="text-xs text-gray-500 dark:text-gray-400">
                    {$t('risk.params.paths')}
                    <div class="mt-1 w-28">
                        <SimpleSelect value={String(simulationPaths)} options={pathOptions} compact testId="risk-simulation-paths" onchange={(value) => (simulationPaths = Number(value))} />
                    </div>
                </label>
                {#if simulationSampling === 'mc'}
                    <label class="text-xs text-gray-500 dark:text-gray-400">
                        {$t('risk.params.randomSeed')}
                        <input
                            class="mt-1 block w-28 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200"
                            type="number"
                            use:numericArrows
                            min="0"
                            step="1"
                            bind:value={simulationRandomSeed}
                            data-testid="risk-simulation-random-seed"
                        />
                    </label>
                {:else}
                    <label class="text-xs text-gray-500 dark:text-gray-400">
                        {$t('risk.params.sobolStartIndex')}
                        <input
                            class="mt-1 block w-28 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-2 py-1 text-sm text-gray-700 dark:text-gray-200"
                            type="number"
                            use:numericArrows
                            min="0"
                            step="1"
                            bind:value={simulationSobolStartIndex}
                            data-testid="risk-simulation-sobol-start-index"
                        />
                    </label>
                {/if}
                <button class="flex items-center gap-1.5 rounded-lg bg-libre-green px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50" onclick={runSimulation} disabled={simulationLoading} data-testid="risk-simulation-run">
                    <Play size={13} />
                    {$t('risk.actions.simulate')}
                </button>
            </div>
        </section>

        {#if simulationResult || simulationLoading}
            <RiskResultFrame title={$t('risk.simulation.simulated')} result={simulationResult} loading={simulationLoading} testId="risk-simulation-section">
                <div class="mt-3">
                    <TabBar tabs={simulationTabs} activeTab={simulationView} onchange={(tabId) => (simulationView = tabId as SimulationView)} fillWidth />
                </div>
                {#if simulationView === 'evolution'}
                    <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                        <KpiCard label={$t('risk.metrics.terminalMean')} value={formatPercent(simulationOutput?.terminal_mean_return, true)} />
                        <KpiCard label={$t('risk.metrics.terminalVolatility')} value={formatPercent(simulationOutput?.terminal_volatility)} />
                        <KpiCard label={$t('risk.metrics.probabilityOfLoss')} value={formatPercent(simulationOutput?.probability_of_loss)} positive={false} />
                    </div>
                    {#if simulationOutput && simulationData.length > 0}
                        <div class="mt-4" data-testid="risk-simulation-chart">
                            <LineChart data={simulationData} overlaySignals={simulationOverlay} currency="%" viewMode="percentage" colorByBaseline={false} showGradient={false} height="320px" />
                        </div>
                    {/if}
                {:else}
                    <div class="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4" data-testid="risk-simulation-terminal-distribution">
                        <KpiCard label={$t('risk.simulation.p05')} value={formatPercent(simulationTerminalPoint?.p05, true)} positive={false} />
                        <KpiCard label={$t('risk.simulation.p50')} value={formatPercent(simulationTerminalPoint?.p50, true)} />
                        <KpiCard label={$t('risk.simulation.p95')} value={formatPercent(simulationTerminalPoint?.p95, true)} />
                        <KpiCard label={$t('risk.metrics.probabilityOfLoss')} value={formatPercent(simulationOutput?.probability_of_loss)} positive={false} />
                    </div>
                {/if}
                {#if simulationOutput}
                    <p class="mt-2 text-xs text-gray-400 dark:text-gray-500" data-testid="risk-simulation-assumptions">
                        {$t('risk.simulation.assumptions', {values: {paths: simulationOutput.path_count, days: simulationOutput.horizon_days}})}
                    </p>
                {/if}
            </RiskResultFrame>
        {/if}
    {/if}

    <div class="hidden" data-testid="risk-frontier-capability" data-available={hasRiskCapability(catalog, 'frontier', scope.kind, 'current_composition') ? 'true' : 'false'}></div>

    <PageSyncModal bind:open={syncOpen} {dateStart} {dateEnd} assets={syncAssets} fxPairs={syncFxPairs} onsynced={handleSynced} onclose={() => (syncOpen = false)} />
</div>
