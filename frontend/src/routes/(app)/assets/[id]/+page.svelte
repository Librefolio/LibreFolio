<script lang="ts">
    /**
     * Asset Detail Page — Phase 06 Step 4 Part A
     *
     * Layout:
     * - Header: asset info + back button
     * - Filter bar: DateRangePicker | CurrencySelect | price summary | 2×2 button matrix
     * - Chart: PriceChartFull with overlay signals + event markers
     * - Foldable panels: Aesthetics, Data Editor (placeholder), Measures, Signals
     * - Metadata section (accordion, readonly)
     * - AssetModal for edit
     *
     * Uses Svelte 5 runes. Reference: fx/[pair]/+page.svelte
     */
    import {onDestroy, onMount, tick, untrack} from 'svelte';
    import {onPricesCaughtUp} from '$lib/features/price-refresh/onPricesCaughtUp';
    import {page} from '$app/stores';
    import {goto} from '$app/navigation';
    import {debug, isDebugEnabled} from '$lib/debug';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {axiosInstance, zodiosApi} from '$lib/api';
    import {ChartLine, Pencil, RefreshCw, Ruler, Settings, Shield, X} from 'lucide-svelte';
    import AssetDataEditorSection from '$lib/components/assets/AssetDataEditorSection.svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import PriceChartFull from '$lib/components/charts/PriceChartFull.svelte';
    import type {EventMarker} from '$lib/components/charts/PriceChartFull.svelte';
    import ChartAestheticsSection from '$lib/components/charts/ChartAestheticsSection.svelte';
    import ChartSignalsSection from '$lib/components/charts/ChartSignalsSection.svelte';
    import type {SignalDataSummary} from '$lib/components/charts/ChartSignalsSection.svelte';
    import MeasurePanel from '$lib/components/charts/MeasurePanel.svelte';
    import AssetModal from '$lib/components/assets/AssetModal.svelte';
    import AssetPriceSummary from '$lib/components/assets/AssetPriceSummary.svelte';
    import {fetchSeriesRangeDelta, summaryRangeDelta} from '$lib/components/assets/detail/assetDetailRangeChange';
    import type {RangeDelta} from '$lib/utils/rangeChange';
    import AssetChartModeToggle, {type AssetChartPrimaryMode} from '$lib/components/assets/detail/AssetChartModeToggle.svelte';
    import AssetCalendarWindowControls from '$lib/components/assets/detail/AssetCalendarWindowControls.svelte';
    import AssetDetailSignalsPanel from '$lib/components/assets/detail/AssetDetailSignalsPanel.svelte';
    import AssetDetailMeasuresSection from '$lib/components/assets/detail/AssetDetailMeasuresSection.svelte';
    import AssetDetailHeader from '$lib/components/assets/detail/AssetDetailHeader.svelte';
    import AssetDetailMetadataPanel from '$lib/components/assets/detail/AssetDetailMetadataPanel.svelte';
    import AssetDetailToolbarActions from '$lib/components/assets/detail/AssetDetailToolbarActions.svelte';
    import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import PageSyncModal from '$lib/components/ui/modals/PageSyncModal.svelte';
    import AssetRiskScenariosView from '$lib/features/risk/AssetRiskScenariosView.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {
        buildBackendSignalRequestPlan,
        getSignalProblem,
        getSignalProblemSeverity,
        getLocalSignalDefinitions,
        mapSignalInstanceResults,
        renderedSignalPointCount,
        SignalResultState,
        type BackendSignalResult,
        type RenderedSignal,
        type SignalConfig,
        type SignalDefinition,
        type SignalInstanceResult,
        type SignalProblem,
    } from '$lib/charts/signals';
    import {DEFAULT_AXIS_SCALE, detailModesForPrimaryView, effectiveCalendarReturnWindow, normalizeAxisScaleSettings, primaryViewForDetailModes, setPairSettings, getSettingsForPair, type AxisScaleSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {invalidateFxRoutes} from '$lib/stores/reference/fxRoutesStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import type {ViewMode, ChartType} from '$lib/components/charts/ChartToolbar.svelte';
    import type {LayoutMode} from '$lib/utils/layout/responsiveLayout.svelte';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import {ensureFxRangeLoaded, getFxStore} from '$lib/stores/fxStoreRegistry';
    import {getAssetPriceStore, invalidateAssetPriceStore, apiPricesToAssetPricePoints} from '$lib/stores/assetPriceStoreRegistry';
    import {hasStoredPointInRange} from '$lib/utils/sync/syncHelpers';
    import {buildIdentifiersList} from '$lib/utils/assetTypes';
    import {ensureAssetProvidersCached, getAssetProviderIconUrl, getAssetProviderName, isParametricProvider, assetProvidersVersion} from '$lib/utils/providerHelpers';
    import {replaceHistoryDateRange} from '$lib/utils/url/dateRangeUrl';
    import {buildTabUrl, getResolvedTabParam} from '$lib/utils/url/tabUrl';
    import {todayIso} from '$lib/utils/dateOnly';
    import type {AssetDetail, ProviderAssignmentFlat} from '$lib/types';
    import type {SignalLabelInfo} from '$lib/charts/signalLabel';
    import {buildOverlaySignalInfoMap} from '$lib/charts/signalLabel';
    import {ensureSignalFxPairs, fxPairSlugsOf} from '$lib/charts/comparisonSeries';
    import {applyComparisonAssetsData, buildComparisonSyncRange, clearComparisonAssetsData, collectConfiguredComparisonFxSlugs, comparisonAnswerGenerations, comparisonAnswerIsCacheable, comparisonAnswerKey, loadComparisonAssetsData} from '$lib/charts/loadComparisonData';
    import {comparisonAssetIds as comparisonPeerAssetIds, detailPageSignalSources, parseBackendSignalResults, signalDataContextFingerprint} from '$lib/charts/chartPageSignals';
    import {renderBackendResults, renderLocalSignals, type SignalDataSources} from '$lib/charts/chartSignalRendering';
    import {getStart, getEnd, setDateRange, resolveDateSentinel, isMaxSentinel} from '$lib/stores/dateRangeStore.svelte';
    import {buildAssetSyncToast, buildFxSyncToast} from '$lib/utils/sync/syncToastHelpers';
    import {COLORS} from '$lib/components/charts/lineChartHelpers';
    import {collectConfigurableSecondaryAxes} from '$lib/components/charts/chartCoreHelpers';
    import {percentageAxisLabel, priceAxisLabel, secondaryAxisLabel} from '$lib/components/charts/axisLabelHelpers';
    import {formatSignalProblem} from '$lib/components/charts/chartSignalsHelpers';
    import {CALENDAR_RETURN_INSTANCE_ID, CALENDAR_RETURN_SIGNAL_CODE, emptyCalendarReturnView, extractCalendarReturnView, extractCalendarReturnViewsByAsset, isCalendarReturnSignalResult, type CalendarReturnView, type CalendarReturnViewState} from '$lib/components/charts/priceChartHelpers';
    import {assetChartAnswerForCache, assetChartAnswerKey, calendarComparisonFxFailuresFromResponse, calendarComparisonProblemsFromResponse, parseAssetPriceQueryWithSignalIsolation, preserveFactualCalendarPeersForCurrentUnavailable} from '$lib/components/assets/detail/assetDetailPriceQuery';
    import {assetChartAnswers, clearAssetPageAnswers, comparisonSeriesAnswers} from '$lib/stores/signalResultCache';
    import {mergeChartPointsIncremental} from '$lib/components/assets/detail/assetDetailChartPoints';
    import {AssetDetailLive} from '$lib/components/assets/detail/assetDetailLive.svelte';
    import {buildAssetDetailIssues, buildRequiredFxPairs, type AssetDetailIssuesInput, type RequiredFxPairInfo, type RequiredFxPairsInput} from '$lib/components/assets/detail/assetDetailFxRequirements';
    import {displayCurrencyAfterFxPairCreated, fxPairCreateDefaults} from '$lib/components/assets/detail/assetDetailFxPair';
    import {CALENDAR_RETURN_PRESETS, DEFAULT_CALENDAR_RETURN_WINDOW, calendarReturnRangeDays, calendarReturnWindowDays, type CalendarReturnPresetKey, type CalendarReturnWindowSelection, type CalendarReturnWindowUnit} from '$lib/components/charts/calendarReturnWindow';
    import {prepareAiExport, type PreparedAiExport} from '$lib/features/ai-export/aiExportClipboard';
    import type {AiExportOptionsSelection} from '$lib/features/ai-export/aiExportOptions';
    import {aiExportCatalogLoader, emptyAiExportCompatibility, type AiExportCatalogCompatibilityResult} from '$lib/features/ai-export/catalog/compatibility';
    import {buildAiExportMenuLabels, getAiExportSuccessMessages} from '$lib/features/ai-export/ui';
    import {signalCatalogStore} from '$lib/stores/signalCatalogStore.svelte';
    import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
    import type {FxPairCreatedDetail, FxPairSyncCompleteDetail} from '$lib/services/fxCreationSync';
    import {buildTransactionsFiltersUrl} from '../../transactions/filterState';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';

    const DISABLED_AI_EXPORT_COMPATIBILITY = emptyAiExportCompatibility();

    // =========================================================================
    // Page data
    // =========================================================================

    interface Props {
        data: {assetId: number};
    }

    let {data}: Props = $props();
    let pageAlive = true;
    onDestroy(() => {
        pageAlive = false;
    });

    const ASSET_DETAIL_TAB_IDS = ['overview', 'risk'] as const;
    type AssetDetailTabId = (typeof ASSET_DETAIL_TAB_IDS)[number];
    let activeTab = $state<AssetDetailTabId>('overview');
    let assetDetailTabs = $derived([
        {id: 'overview', label: $t('risk.assetDetail.overviewTab'), icon: ChartLine, testId: 'asset-detail-tab-overview'},
        {id: 'risk', label: $t('risk.assetDetail.riskScenariosTab'), icon: Shield, testId: 'asset-detail-tab-risk', guideAnchor: 'asset.detail.risk'},
    ]);

    $effect(() => {
        activeTab = getResolvedTabParam($page.url.searchParams, ASSET_DETAIL_TAB_IDS, 'overview');
    });

    // =========================================================================
    // State
    // =========================================================================

    let assetInfo = $state<AssetDetail | null>(null);
    let providerAssignment = $state<ProviderAssignmentFlat | null>(null);
    // Unknown is not "manual": until the assignment request settles, Sync is merely disabled.
    let providerAssignmentLoaded = $state(false);
    let chartData: any[] = $state([]);
    let events: any[] = $state([]);
    let comparisonEvents = $state<Map<number, any[]>>(new Map());

    let loading = $state(true);
    let riskRefreshVersion = $state(0);
    /** Stores either a raw message or an i18n key prefixed with `_i18n:` for reactive translation */
    let error: string | null = $state(null);
    let syncing = $state(false);
    let fxSyncing = $state(false);
    const fxSyncRequestGenerations = new Map<string, number>();
    const activeFxSyncRequests = new Map<string, number>();
    const assetSyncRequestGenerations = new Map<number, number>();
    const activeAssetSyncRequests = new Map<number, number>();
    let syncingComparisonAssetIds = $state<Set<number>>(new Set());

    /**
     * An error the banner words from the catalogue. The key is written whole at each call, so the
     * catalogue audit sees it; the banner below translates it, with this asset's id as `{id}`.
     */
    function catalogueError(key: string): string {
        return `_i18n:${key}`;
    }

    /** Reactively resolved error message — translates i18n keys when language changes */
    let errorMessage = $derived.by(() => {
        if (!error) return null;
        return error.startsWith('_i18n:') ? $t(error.slice(6), {values: {id: String(data.assetId)}}) : error;
    });

    // Date range — global store is source of truth (resolve min/max sentinels for API)
    let dateEnd = $state(resolveDateSentinel(getEnd()));
    const initialStart = getStart();
    let dateStart = $state(resolveDateSentinel(initialStart));
    // Whether "All" (MAX) is the active semantic choice and its real earliest date
    // hasn't been resolved yet from backend data (survives navigation via the store).
    const initialIsMaxPending = isMaxSentinel(initialStart);
    let isMaxPending = $state(initialIsMaxPending);
    // Bound to the picker's `start` — shows the literal "min" sentinel (pending
    // label) while isMaxPending, otherwise mirrors the resolved dateStart.
    // Seeded from the plain `initialIsMaxPending`/`initialStart` above (not from the
    // dateStart/isMaxPending $state bindings) to avoid a state_referenced_locally warning —
    // displayDateStart is manually resynced elsewhere and bound bidirectionally to
    // DateRangePicker, so it's intentionally NOT a pure $derived of dateStart/isMaxPending.
    let displayDateStart = $state(initialIsMaxPending ? 'min' : resolveDateSentinel(initialStart));
    let activePreset: any = $state(initialIsMaxPending ? 'MAX' : null);

    /**
     * Sentinel-aware values for building URLs (own history + cross-page nav
     * links). While "All" is the active selection, these stay "min"/"max"
     * (generic) instead of a concrete resolved date, for the lifetime of the
     * selection — not just until the real date is resolved.
     */
    let urlDateStart = $derived(activePreset === 'MAX' ? 'min' : dateStart);
    let urlDateEnd = $derived(activePreset === 'MAX' ? 'max' : dateEnd);
    let syncDateStart = $derived(activePreset === 'MAX' ? 'min' : dateStart);
    let viewMode: ViewMode = $state('percentage');
    let chartType: ChartType = $state('line');
    let displayCurrency = $state('');
    let primaryMode = $state<AssetChartPrimaryMode>('price');
    let calendarCustomAmount = $state(DEFAULT_CALENDAR_RETURN_WINDOW.customAmount);
    let calendarCustomUnit: CalendarReturnWindowUnit = $state(DEFAULT_CALENDAR_RETURN_WINDOW.customUnit);
    let calendarCustomEditing = $state(false);
    let calendarWindowHydratedScope: string | null = null;
    let calendarRangeDays = $derived(calendarReturnRangeDays(dateStart, dateEnd));
    let calendarReturnView: CalendarReturnView = $state(emptyCalendarReturnView());
    let calendarComparisonViews: Map<number, CalendarReturnView> = $state(new Map());
    let calendarComparisonProblems: Map<number, SignalProblem> = $state(new Map());
    let calendarComparisonFxFailures: Set<number> = $state(new Set());
    let calendarSnapshotFingerprint: string | null = $state(null);
    let chartRequestGeneration = 0;
    let comparisonRequestGeneration = 0;
    let refreshRequestGeneration = 0;
    let comparisonAppliedFingerprint: string | null = null;
    let comparisonInFlight: {fingerprint: string; promise: Promise<void>} | null = null;
    /**
     * N64 (Q1): whether the last call of `loadChartData` / `maybeLoadComparison` asked the server. Set before their first
     * await, so the trigger reads it right after the call: the busy token goes with a request, never with a load the
     * caches answered whole (`trackChartLoad`, `trackComparisonLoad`, `trackChartAndComparison`).
     */
    let lastChartLoadAskedServer = false;
    let lastComparisonLoadAskedServer = false;

    // Foldable panels
    let showAesthetics = $state(false);
    let showMeasures = $state(false);
    let showCalendarMeasures = $state(false);
    let showSignals = $state(false);
    let showDataEditor = $state(false);
    let showMetadata = $state(false);

    // Filter bar layout is now owned by PageToolbar (shared with dashboard/broker-detail/assets
    // list) — layoutMode is bound out (see bind:layoutMode below) for the one usage elsewhere on
    // this page (editor tip text). Tune live via window.__lfLayouts.assetDetail.thresholds.<field>.
    let pageLayoutMode = $state<LayoutMode>('denseRow');
    /** Mirrors the DateRangePicker's own effective 2-row max-width, passed down into
     *  AssetPriceSummary so its Center content can be capped to the SAME pixel value when
     *  filtersStacked (matches the established dashboard/brokerDetail/fxList "giustificata"
     *  pattern). MUST start non-undefined (390 = DateRangePicker's own maxWidthTwoRow default)
     *  — Svelte forbids bind:key={undefined} when the child prop has a declared fallback. */
    let pickerMaxWidth = $state<number>(390);

    // Chart settings
    let settings = $derived(getSettingsForPair(`asset-${data.assetId}`, 'assets'));
    let signals = $derived<SignalConfig[]>([...settings.signals]);
    /**
     * Y-40: the rolling-return window in force, the one the asset's card shows too: the window chosen for this asset, else
     * the largest preset that fits the period on screen. Derived, so a change of period reads the new window at once.
     */
    let calendarWindowSelection: CalendarReturnWindowSelection = $derived(effectiveCalendarReturnWindow(settings, calendarRangeDays));
    let calendarWindowDays = $derived(calendarReturnWindowDays(calendarWindowSelection) ?? 30);
    let calendarSnapshotIsCurrent = $derived.by(() => calendarSnapshotFingerprint === calendarDataFingerprint(signals));
    let signalDefinitions = $state<SignalDefinition[]>([]);
    let signalInstanceResults = $state<SignalInstanceResult[]>([]);
    let signalCatalogFailed = $state(false);
    let signalRequestFailed = $state(false);
    let signalsLoading = $state(false);
    const signalResultState = new SignalResultState();
    let signalBackendError = $derived(signalCatalogFailed ? $t('chartSettings.signalCatalogUnavailable') : signalRequestFailed ? $t('chartSettings.signalResultsUnavailable') : null);

    $effect(() => {
        const scope = `${getClientSessionGeneration()}:${data.assetId}`;
        if (calendarWindowHydratedScope === scope) return;
        calendarCustomAmount = settings.calendarReturnWindow.customAmount;
        calendarCustomUnit = settings.calendarReturnWindow.customUnit;
        calendarWindowHydratedScope = scope;
    });
    // Measure panel
    let measureMode = $state(false);
    let measureSignals: RenderedSignal[] = $state([]);
    let measurePanel: MeasurePanel | undefined = $state(undefined);
    let calendarMeasureMode = $state(false);
    let calendarMeasureSignals: RenderedSignal[] = $state([]);
    let calendarMeasurePanel: MeasurePanel | undefined = $state(undefined);

    // Editor panel state save/restore
    let savedPanelStates: {aesthetics: boolean; measures: boolean; signals: boolean} | null = $state(null);

    // Data editor state
    let savingEdit = $state(false);
    let editorDirtyCount = $state(0);
    let pendingPreviewSignal: RenderedSignal | null = $state(null);
    let assetDataEditorRef: AssetDataEditorSection | undefined = $state(undefined);

    let overlayDataVersion = $state(0);
    let signalPanelConfigs = $derived.by(() => {
        void overlayDataVersion;
        return signals.map((signal) => ({
            ...signal,
            params: {...signal.params},
        }));
    });
    let editModalOpen = $state(false);

    // Edit data — computed on-demand when modal opens (NOT $derived, to avoid effect loops)
    let editDataForModal = $state<ReturnType<typeof buildEditData>>(null);

    // Cross-domain data for signals
    let allConfiguredFxSlugs: string[] = $state([]);
    let allAssets: Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null; currency?: string; is_benchmark?: boolean}> = $state([]);

    // Classification data (loaded when has_metadata)
    let sectorDistribution: Record<string, number> | null = $state(null);
    let geographicDistribution: Record<string, number> | null = $state(null);
    let shortDescription: string | null = $state(null);
    let classificationLoaded = $state(false);

    // AI export (page toolbar) — dropdown open/position handled internally by AiExportMenu
    let assetAiExportCompatibility = $state<AiExportCatalogCompatibilityResult>(DISABLED_AI_EXPORT_COMPATIBILITY);
    let assetAiExportCatalogLoading = $state(true);
    let assetAiExportCatalogFailed = $state(false);
    let assetAiExportLabels = $derived(buildAiExportMenuLabels($t, assetAiExportCompatibility, $t('assetDetail.aiExport')));

    // Provider icon for header badge
    let providerIconUrl = $state<string | null>(null);

    // FX pair add modal (opened from FX warning or banner)
    let showFxPairAddModal = $state(false);
    /** Pre-filled slug for FxPairAddModal (e.g. "EUR-RON" from banner) */
    let fxPairCreateSlug = $state('');

    // =========================================================================
    // Derived
    // =========================================================================

    /** True when the chart end date is today (or later) → show live price from provider. Today on the user's calendar,
     *  like `dateEnd`: the UTC date is already tomorrow in the evening west of Greenwich (Z-3). */
    let isHeadToday = $derived(dateEnd >= todayIso());

    let lineData: LineDataPoint[] = $derived(
        chartData.map((p: any) => ({
            date: p.date,
            value: Number(p.close ?? 0),
            staleDays: Math.max(p.backward_fill_info?.days_back ?? 0, p.backward_fill_info?.fx_days_back ?? 0),
            fxStaleDays: p.backward_fill_info?.fx_days_back ?? 0,
            originalCurrency: p.original_currency ?? undefined,
            originalCurrencyFlag: p.original_currency ? getCurrencyInfo(p.original_currency).flag_emoji : undefined,
            originalValue: p.original_close != null ? Number(p.original_close) : undefined,
            open: p.open != null ? Number(p.open) : null,
            high: p.high != null ? Number(p.high) : null,
            low: p.low != null ? Number(p.low) : null,
            close: Number(p.close ?? 0),
            volume: p.volume != null ? Number(p.volume) : null,
        })),
    );
    let calendarChartData = $derived.by(() => {
        if (!calendarSnapshotIsCurrent) return [];
        const primaryByDate = new Map(calendarReturnView.points.map((point) => [point.date, point]));
        const dates = new Set(primaryByDate.keys());
        for (const assetId of comparisonAssetIds(signals)) {
            const view = calendarComparisonViews.get(assetId);
            if (!view || !['ready', 'partial'].includes(view.state)) continue;
            for (const point of view.points) dates.add(point.date);
        }
        return [...dates].sort((left, right) => left.localeCompare(right)).map((date) => primaryByDate.get(date) ?? {date, value: 0, missing: true});
    });
    let calendarHasFactualPeerData = $derived(
        calendarSnapshotIsCurrent &&
            comparisonAssetIds(signals).some((assetId) => {
                const view = calendarComparisonViews.get(assetId);
                return !!view && ['ready', 'partial'].includes(view.state) && view.points.some((point) => !point.missing);
            }),
    );
    let calendarChartState = $derived.by((): CalendarReturnViewState => {
        if (primaryMode === 'calendar-return' && !calendarSnapshotIsCurrent) return 'loading';
        if (calendarReturnView.state === 'loading') return 'loading';
        if (calendarHasFactualPeerData && ['idle', 'unavailable', 'error'].includes(calendarReturnView.state)) return 'partial';
        return calendarReturnView.state;
    });
    let activeChartData = $derived(primaryMode === 'price' ? lineData : calendarChartData);
    let calendarPointContext = $derived(primaryMode === 'calendar-return' ? calendarReturnView.contextByDate : undefined);
    let chartSeriesState = $derived.by(() => {
        if (primaryMode === 'calendar-return') return calendarChartState;
        if (loading) return 'loading';
        return lineData.length > 0 ? 'ready' : error ? 'error' : 'unavailable';
    });

    function translateCalendarProblem(key: string, values?: Record<string, string | number>): string {
        return values ? $t(key, {values}) : $t(key);
    }

    let calendarPrimaryProblemMessage = $derived(calendarReturnView.problem ? formatSignalProblem(calendarReturnView.problem, translateCalendarProblem, (field) => $t(`signals.dataFields.${field}`)) : null);
    let calendarPrimaryProblemSeverity = $derived(calendarReturnView.problem ? getSignalProblemSeverity(calendarReturnView.problem) : null);

    function setPrimaryMode(mode: AssetChartPrimaryMode) {
        if (mode === primaryMode) return;
        if (primaryMode === 'price') {
            measurePanel?.stopMeasureMode();
        } else {
            calendarMeasurePanel?.stopMeasureMode();
        }
        primaryMode = mode;
        persistPrimaryView();
        if (mode === 'calendar-return') {
            void trackChartLoad('asset-mode');
        } else {
            calendarCustomEditing = false;
            void trackComparisonLoad('asset-mode');
            void loadSignalFxPairs();
            const hasBackendSignals = signals.some((config) => signalDefinitionsByType.get(config.signalType)?.source === 'backend');
            if (hasBackendSignals) void trackChartLoad('asset-mode');
        }
    }

    /**
     * Y-40 (V-2 a): the view the detail shows — its mode, and Abs or % under prices — is this asset's view: its card and its
     * next visit open in it. Saved like the page's other settings, with its configs as they are: a save rebuilt from the
     * stored override (`setItemPrimaryView`) would drop the comparison data the page wrote into them, and an Abs/% switch
     * would lose the comparison lines.
     */
    function persistPrimaryView(): void {
        const view = primaryViewForDetailModes(primaryMode, viewMode);
        if (settings.primaryView === view) return;
        setPairSettings(`asset-${data.assetId}`, {...settings, primaryView: view, signals: [...signals]});
    }

    function persistCalendarWindow(selection: CalendarReturnWindowSelection): void {
        setPairSettings(`asset-${data.assetId}`, {
            ...settings,
            calendarReturnWindow: {...selection},
            // Y-40: a window picked here is chosen, no longer the automatic one — also when it equals the window saved before.
            calendarReturnWindowAuto: false,
            signals: [...signals],
        });
    }

    function setCalendarPreset(preset: CalendarReturnPresetKey) {
        if (!CALENDAR_RETURN_PRESETS.some((candidate) => candidate.key === preset)) return;
        if (calendarWindowSelection.kind === 'preset' && calendarWindowSelection.preset === preset) return;
        calendarCustomEditing = false;
        persistCalendarWindow({
            ...calendarWindowSelection,
            kind: 'preset',
            preset,
        });
        if (primaryMode === 'calendar-return') {
            void trackChartLoad('asset-calendar-window');
        }
    }

    function setCalendarCustom(customAmount: number, customUnit: CalendarReturnWindowUnit): void {
        const selection: CalendarReturnWindowSelection = {
            ...calendarWindowSelection,
            kind: 'custom',
            customAmount,
            customUnit,
        };
        if (calendarReturnWindowDays(selection) === null) return;
        const changed = calendarWindowSelection.kind !== 'custom' || calendarWindowSelection.customAmount !== customAmount || calendarWindowSelection.customUnit !== customUnit;
        persistCalendarWindow(selection);
        if (changed && primaryMode === 'calendar-return') {
            void trackChartLoad('asset-calendar-window');
        }
    }

    // #R3-4 — derive "parametric" status from provider kind (instead of hardcoded code),
    // so the detail page picks the "Regenerate" label for any parametric_generation provider.
    // Depends on assetProvidersVersion to re-evaluate after the providers cache is loaded.
    let isParametric = $derived.by(() => {
        void $assetProvidersVersion;
        return isParametricProvider(providerAssignment?.provider_code);
    });
    // The providers' names come from the same cache, which may land after the asset (both load in parallel): read in the
    // template alone, a name read before it kept the raw code (`yfinance`) for good.
    let assetProviderName = $derived.by(() => {
        void $assetProvidersVersion;
        return assetInfo?.provider_code ? getAssetProviderName(assetInfo.provider_code) : '';
    });
    let assignmentProviderName = $derived.by(() => {
        void $assetProvidersVersion;
        return providerAssignment?.provider_code ? getAssetProviderName(providerAssignment.provider_code) : '';
    });
    let isManualOnly = $derived(providerAssignmentLoaded && !providerAssignment);
    let isInactive = $derived(assetInfo?.active === false);
    let syncDisabledReason = $derived(isManualOnly ? $t('assetDetail.syncDisabledManual') : isInactive ? $t('assetDetail.syncDisabledInactive') : '');
    let syncBlocked = $derived(isManualOnly || isInactive);
    /** True when OHLCV price data is available (enables candlestick chart) */
    let hasOhlcv = $derived(lineData.some((p) => p.open != null));
    // Reset to line chart when OHLCV becomes unavailable (e.g. date range with no data)
    $effect(() => {
        if (!hasOhlcv) chartType = 'line';
    });
    /** Settings that don't apply in candlestick mode — greyed out in aesthetics panel */
    let disabledAesthetics = $derived(primaryMode === 'price' && (chartType as string) === 'candlestick' ? new Set(['colorByBaseline', 'areaFill', 'staleGradient']) : new Set<string>());

    /** First data point date — used for "no data before" banner */
    let firstDataDate = $derived(chartData.length > 0 ? chartData[0].date : null);
    /** True when the selected date range starts before the first available data point */
    let rangeStartsBeforeData = $derived(firstDataDate != null && dateStart < firstDataDate);

    /** First date with FX-converted data (original_close present) — null if no conversion active */
    let fxFirstConvertedDate = $derived.by(() => {
        if (!displayCurrency || !assetInfo || displayCurrency === assetInfo.currency) return null;
        for (const p of chartData) {
            if (p.original_close != null) return p.date as string;
        }
        return null;
    });

    /** True when conversion is active but earliest chart points lack FX rates */
    let hasFxDataGap = $derived.by(() => {
        if (!displayCurrency || !assetInfo || displayCurrency === assetInfo.currency) return false;
        if (fxConversionMissing) return false; // FX pair doesn't exist at all → different warning
        if (chartData.length === 0) return false;
        // Case 1: first chart point has no conversion but later points do (partial gap)
        if (fxFirstConvertedDate && chartData[0].original_close == null && fxFirstConvertedDate > chartData[0].date) return true;
        // Case 2: FX pair exists but NO chart point has original_close at all (0 rates, or all rates after window)
        // (chartData.length > 0 already guaranteed by the guard above)
        return !fxFirstConvertedDate;
    });

    /** The summary shows the live quote: the range ends today and a live price is there. */
    let liveShown = $derived.by(() => isHeadToday && live.currentPrice != null);

    /** Effective last price: live from provider when head = today, otherwise last chart close */
    let lastPrice = $derived.by(() => {
        if (liveShown) return live.currentPrice;
        if (chartData.length === 0) return null;
        const last = chartData[chartData.length - 1];
        return last?.close != null ? Number(last.close) : null;
    });

    // The Δ over the range is the backend's (X-R59): the live quote's comes with each poll (`live.rangeDelta`), the stored
    // series' is asked here — when the asset, the range or the display currency changes, and after a reload
    // (`seriesRangeDeltaRefresh`). A Δ of another context is cleared at once: never one beside another range's price.
    // It completes what the page is doing, so it joins the page's token (N55): the Refresh button waits for it after the
    // user's request, and stays still through the reload that follows a sync, which `handleRefresh()` runs without one (P3).
    let seriesRangeDelta = $state<RangeDelta | null>(null);
    let seriesRangeDeltaRefresh = $state(0);
    let seriesRangeDeltaVersion = 0;
    let seriesRangeDeltaKey: string | null = null;

    let summaryDelta = $derived.by(() => summaryRangeDelta(liveShown, live.rangeDelta, seriesRangeDelta));
    let deltaPercent = $derived(summaryDelta.pct);
    let deltaAbs = $derived(summaryDelta.abs);

    async function loadSeriesRangeDelta(assetId: number, start: string, end: string, targetCurrency: string | null): Promise<void> {
        const version = ++seriesRangeDeltaVersion;
        const sessionGeneration = getClientSessionGeneration();
        const key = `${assetId} ${start}…${end} ${targetCurrency ?? ''}`;
        if (key !== seriesRangeDeltaKey) seriesRangeDelta = null;
        try {
            const delta = await fetchSeriesRangeDelta({assetId, asOf: end, dateStart: start, targetCurrency});
            if (version !== seriesRangeDeltaVersion || !isClientSessionCurrent(sessionGeneration)) return;
            seriesRangeDelta = delta;
            seriesRangeDeltaKey = key;
        } catch (requestError) {
            if (version !== seriesRangeDeltaVersion) return;
            console.error('Failed to fetch the change of the asset over the range:', requestError);
        }
    }

    $effect(() => {
        const assetId = assetInfo?.id;
        const nativeCurrency = assetInfo?.currency;
        const [start, end] = [dateStart, dateEnd];
        // In the display currency only when the chart is really converted: with the pair missing the summary shows native prices.
        const targetCurrency = displayCurrency && nativeCurrency && displayCurrency !== nativeCurrency && !fxConversionMissing ? displayCurrency : null;
        void seriesRangeDeltaRefresh;
        if (!assetId) return;
        untrack(() => void pageBusy.join('asset-detail-range-delta', () => loadSeriesRangeDelta(assetId, start, end, targetCurrency)));
    });

    let currencyFlag = $derived.by(() => {
        if (!assetInfo?.currency) return '';
        return getCurrencyInfo(assetInfo.currency).flag_emoji;
    });

    let userUrl = $derived(assetInfo?.user_url || null);
    let providerExternalUrl = $derived(providerAssignment?.provider_url || null);

    /** True when display currency differs from asset currency and FX pair is not configured */
    let fxConversionMissing = $derived.by(() => {
        if (!assetInfo || !displayCurrency || displayCurrency === assetInfo.currency) return false;
        const a = assetInfo.currency < displayCurrency ? assetInfo.currency : displayCurrency;
        const b = assetInfo.currency < displayCurrency ? displayCurrency : assetInfo.currency;
        const slug = `${a}-${b}`;
        return !allConfiguredFxSlugs.includes(slug);
    });

    /** Canonical FX pair slug (alphabetically ordered) for linking */
    let fxPairSlug = $derived.by(() => {
        if (!assetInfo || !displayCurrency || displayCurrency === assetInfo.currency) return '';
        const a = assetInfo.currency < displayCurrency ? assetInfo.currency : displayCurrency;
        const b = assetInfo.currency < displayCurrency ? displayCurrency : assetInfo.currency;
        return `${a}-${b}`;
    });

    /**
     * Quick-access URL to the FX pair detail page.
     * Only populated when the main FX pair is healthy (status === 'ok') — if the pair
     * is missing / no-data / partial-gap, the full-width banner already handles the
     * issue with a dedicated CTA, and a link here would be confusing or dead.
     */
    let mainFxPairUrl = $derived.by(() => {
        if (!fxPairSlug) return undefined;
        const main = requiredFxPairs.find((p) => p.slug === fxPairSlug);
        if (!main || main.status !== 'ok') return undefined;
        return `/fx/${fxPairSlug}?start=${urlDateStart}&end=${urlDateEnd}`;
    });

    /** The page state the required FX pairs and the banner issues read, through getters: the same reads, in the same order, as the former derived blocks. */
    const fxRequirementsState: RequiredFxPairsInput = {
        get displayCurrency() {
            return displayCurrency;
        },
        get asset() {
            return assetInfo;
        },
        get pageAssetId() {
            return data.assetId;
        },
        get configuredFxSlugs() {
            return allConfiguredFxSlugs;
        },
        get fxFirstConvertedDate() {
            return fxFirstConvertedDate;
        },
        get hasChartData() {
            return chartData.length > 0;
        },
        get hasFxDataGap() {
            return hasFxDataGap;
        },
        get signals() {
            return signals;
        },
        get assets() {
            return allAssets;
        },
        get primaryMode() {
            return primaryMode;
        },
        get calendarSnapshotIsCurrent() {
            return calendarSnapshotIsCurrent;
        },
        get calendarComparisonFxFailures() {
            return calendarComparisonFxFailures;
        },
        get calendarComparisonProblems() {
            return calendarComparisonProblems;
        },
        get events() {
            return events;
        },
        get comparisonEvents() {
            return comparisonEvents;
        },
        get eventsLabel() {
            return $t('events.fxBannerContext') ?? 'for dividend/cash events';
        },
        assetFallbackLabel: (assetId) => $t('chartSettings.signals.assetFallback', {values: {id: String(assetId)}}),
    };

    let requiredFxPairs: RequiredFxPairInfo[] = $derived(buildRequiredFxPairs(fxRequirementsState));

    const assetDetailIssuesState: AssetDetailIssuesInput = {
        get asset() {
            return assetInfo;
        },
        get rangeStartsBeforeData() {
            return rangeStartsBeforeData;
        },
        get loading() {
            return loading;
        },
        get error() {
            return error;
        },
        get firstDataDate() {
            return firstDataDate;
        },
        get requiredFxPairs() {
            return requiredFxPairs;
        },
    };

    /** Build DataQualityIssue[] from page state for unified banner rendering */
    let assetDetailIssues: DataQualityIssue[] = $derived(buildAssetDetailIssues(assetDetailIssuesState));

    function handleBannerAction(action: string, target: string | null, _issue: DataQualityIssue) {
        if (action === 'add_fx_pair' && target) {
            fxPairCreateSlug = target;
            showFxPairAddModal = true;
        } else if (action === 'navigate_fx' && target) {
            goto(`/fx/${target}?start=${urlDateStart}&end=${urlDateEnd}`);
        } else if (action === 'sync_fx' && target) {
            handleSyncPair(target);
        }
    }

    let identifiersList = $derived.by((): [string, string][] => {
        if (!assetInfo) return [];
        return buildIdentifiersList(assetInfo as Record<string, unknown>);
    });

    let signalDefinitionsByType = $derived(new Map(signalDefinitions.map((definition) => [definition.type, definition])));

    let backendOverlaySignals: RenderedSignal[] = $derived(renderBackendResults(signals, signalInstanceResults, signalDefinitionsByType, lineData, viewMode, (key) => $t(key)));

    let rollingRiskSignals = $derived.by(() => {
        const riskConfigIds = new Set(signals.filter((config) => signalDefinitionsByType.get(config.signalType)?.indicatorGroup === 'risk').map((config) => config.id));
        return backendOverlaySignals.filter((signal) => riskConfigIds.has(signal.id.split(':')[0]));
    });

    // Overlay signals: the saved local signals, drawn by the one renderer with the page's data (Y-42), then the backend results.
    // A comparison reads the series its load wrote into its config; an asset that is gone is named by the signal's own
    // catalogue fallback; the page's own asset is never compared with itself.
    let signalSources: SignalDataSources = $derived(detailPageSignalSources({configs: signals, assets: allAssets, fxPairPoints: (pairSlug) => getFxStore(pairSlug).getAllSorted(), selfAssetId: data.assetId}));
    let overlaySignals: RenderedSignal[] = $derived.by(() => {
        void overlayDataVersion;
        return [...renderLocalSignals(signals, signalDefinitionsByType, lineData, viewMode, signalSources), ...backendOverlaySignals];
    });

    let allOverlaySignals: RenderedSignal[] = $derived([...overlaySignals, ...measureSignals, ...(pendingPreviewSignal ? [pendingPreviewSignal] : [])]);
    let calendarComparisonSignals: RenderedSignal[] = $derived.by(() => {
        const rendered: RenderedSignal[] = [];
        if (!calendarSnapshotIsCurrent) return rendered;
        for (const config of signals) {
            if (config.signalType !== 'asset-comparison') continue;
            const assetId = Number(config.params.assetId);
            const view = calendarComparisonViews.get(assetId);
            if (!assetId || !view || !['ready', 'partial'].includes(view.state)) continue;
            const target = allAssets.find((asset) => asset.id === assetId);
            rendered.push({
                id: `${config.id}:calendar-return`,
                label: target?.display_name ?? String(config.params._assetDisplayName ?? $t('chartSettings.signals.assetFallback', {values: {id: String(assetId)}})),
                data: view.points,
                color: config.style.color,
                lineWidth: config.style.lineWidth,
                lineType: config.style.lineType,
                markerStart: config.style.markerStart,
                markerEnd: config.style.markerEnd,
                yAxisIndex: 0,
                axisRole: 'price',
                unit: 'percentage',
                connectNulls: false,
                aggregationProfile: 'last_with_range',
                iconUrl: target?.icon_url ?? null,
                assetType: target?.asset_type ?? null,
            });
        }
        return rendered;
    });
    let calendarOverlaySignals = $derived([...calendarComparisonSignals, ...calendarMeasureSignals]);
    let calendarComparisonState = $derived.by(() => {
        const state: Record<CalendarReturnViewState, number[]> = {
            idle: [],
            loading: [],
            ready: [],
            partial: [],
            unavailable: [],
            error: [],
        };
        if (!calendarSnapshotIsCurrent) return state;
        for (const [assetId, view] of calendarComparisonViews) {
            state[view.state].push(assetId);
        }
        for (const ids of Object.values(state)) {
            ids.sort((left, right) => left - right);
        }
        return state;
    });
    let activePrimaryAxisKind = $derived<'absolute' | 'percentage'>(primaryMode === 'calendar-return' || viewMode === 'percentage' ? 'percentage' : 'absolute');
    let activePrimaryAxisScale = $derived(settings.axisScales[activePrimaryAxisKind]);
    let activeSecondaryAxes = $derived(primaryMode === 'price' ? collectConfigurableSecondaryAxes(allOverlaySignals) : collectConfigurableSecondaryAxes(calendarOverlaySignals));
    let aestheticsAxisRows = $derived([
        {
            key: `primary:${activePrimaryAxisKind}`,
            label: activePrimaryAxisKind === 'percentage' ? percentageAxisLabel((key, values) => $t(key, {values})) : priceAxisLabel((key, values) => $t(key, {values}), displayCurrency || assetInfo?.currency || '—'),
            settings: activePrimaryAxisScale,
        },
        ...activeSecondaryAxes.map((axis) => ({
            key: axis.key,
            label: secondaryAxisLabel((key, values) => $t(key, {values}), axis),
            settings: settings.axisScales.secondary[axis.key] ?? DEFAULT_AXIS_SCALE,
        })),
    ]);

    // Signal label info for MeasurePanel and PriceChartFull tooltip
    let mainSignalInfo: SignalLabelInfo = $derived({
        label: assetInfo?.display_name ?? '',
        iconUrl: assetInfo?.icon_url,
        assetType: assetInfo?.asset_type,
        isCrown: true,
        color: COLORS.lineLight,
    });
    let calendarMainSignalInfo: SignalLabelInfo = $derived({
        label: $t('signals.riskRollingReturn.name'),
        iconUrl: assetInfo?.icon_url,
        assetType: assetInfo?.asset_type,
        isCrown: true,
        color: COLORS.lineLight,
    });

    let overlaySignalInfoMap = $derived(buildOverlaySignalInfoMap(overlaySignals));
    let calendarOverlaySignalInfoMap = $derived(buildOverlaySignalInfoMap(calendarComparisonSignals));

    // Event markers for the chart (own events + comparison asset events)
    // E.8 — events whose FX conversion failed (conversion requested but original_value
    // stays undefined) are HIDDEN from the chart. The FX pair issue is surfaced by
    // the existing `requiredFxPairs` banner (extended below to include event currencies).
    let chartEventMarkers: EventMarker[] = $derived.by(() => {
        const markers: EventMarker[] = [];
        const wantConversion = displayCurrency && assetInfo?.currency && displayCurrency !== assetInfo.currency;

        // Own asset events
        for (const ev of events) {
            const evCurrency = ev.value?.code ?? assetInfo?.currency ?? '';
            const originalValueRaw = ev.original_value?.amount;
            const originalCurrency = ev.original_value?.code;
            // Hide event if conversion was requested but did not apply.
            // Heuristic: asset native currency ≠ displayCurrency AND event currency stays
            // ≠ displayCurrency AND no original_* populated → FX missing.
            if (wantConversion && evCurrency !== displayCurrency && !originalCurrency) {
                continue;
            }
            markers.push({
                date: ev.date,
                type: ev.type ?? 'OTHER',
                value: ev.value?.amount != null ? Number(ev.value.amount) : undefined,
                currency: evCurrency,
                currencyFlag: evCurrency ? getCurrencyInfo(evCurrency).flag_emoji : undefined,
                notes: ev.notes ?? undefined,
                originalValue: originalValueRaw != null ? Number(originalValueRaw) : undefined,
                originalCurrency: originalCurrency ?? undefined,
                originalCurrencyFlag: originalCurrency ? getCurrencyInfo(originalCurrency).flag_emoji : undefined,
                fxRateDate: ev.fx_info?.fx_rate_date ?? undefined,
                fxDaysBack: ev.fx_info?.fx_days_back ?? undefined,
            });
        }

        // Comparison asset events
        for (const [aid, evts] of comparisonEvents) {
            const targetAsset = allAssets.find((a) => a.id === aid);
            const label = targetAsset?.display_name ?? $t('chartSettings.signals.assetFallback', {values: {id: String(aid)}});
            // Find signal color for this comparison asset
            const sigColor = overlaySignals.find((s) => s.label === label)?.color;
            for (const ev of evts) {
                const evCurrency = ev.value?.code ?? '';
                const originalValueRaw = ev.original_value?.amount;
                const originalCurrency = ev.original_value?.code;
                if (wantConversion && evCurrency && evCurrency !== displayCurrency && !originalCurrency) {
                    continue;
                }
                markers.push({
                    date: ev.date,
                    type: ev.type ?? 'OTHER',
                    value: ev.value?.amount != null ? Number(ev.value.amount) : undefined,
                    currency: evCurrency,
                    currencyFlag: evCurrency ? getCurrencyInfo(evCurrency).flag_emoji : undefined,
                    notes: ev.notes ?? undefined,
                    assetLabel: label,
                    signalColor: sigColor,
                    originalValue: originalValueRaw != null ? Number(originalValueRaw) : undefined,
                    originalCurrency: originalCurrency ?? undefined,
                    originalCurrencyFlag: originalCurrency ? getCurrencyInfo(originalCurrency).flag_emoji : undefined,
                    fxRateDate: ev.fx_info?.fx_rate_date ?? undefined,
                    fxDaysBack: ev.fx_info?.fx_days_back ?? undefined,
                });
            }
        }

        return markers;
    });

    // Summary data per signal (point count, event counts, first date) — for ChartSignalsSection
    let signalSummaries: Map<string, SignalDataSummary> = $derived.by(() => {
        void overlayDataVersion; // recompute when overlay data changes (e.g. after sync)
        const result = new Map<string, SignalDataSummary>();
        const instanceById = new Map(signalInstanceResults.map((item) => [item.config.id, item]));
        for (const cfg of signals) {
            const definition = signalDefinitionsByType.get(cfg.signalType);
            if (definition?.source === 'backend') {
                const rendered = backendOverlaySignals.filter((signal) => signal.id === cfg.id || signal.id.startsWith(`${cfg.id}:`));
                const dates = rendered.flatMap((signal) => signal.data.map((point) => point.date)).sort();
                result.set(cfg.id, {
                    pointCount: renderedSignalPointCount(rendered),
                    eventCounts: {},
                    firstDate: dates[0] ?? null,
                    problem: getSignalProblem(instanceById.get(cfg.id)) ?? undefined,
                });
            } else if (cfg.signalType === 'asset-comparison') {
                const targetId = Number(cfg.params.assetId);
                if (!targetId) continue;
                if (primaryMode === 'calendar-return') {
                    const calendarView = calendarComparisonViews.get(targetId);
                    const availablePoints = calendarView?.points.filter((point) => !point.missing) ?? [];
                    result.set(cfg.id, {
                        pointCount: availablePoints.length,
                        eventCounts: {},
                        firstDate: null,
                        problem: calendarComparisonProblems.get(targetId) ?? undefined,
                        comparisonStatusAuthoritative: true,
                    });
                    continue;
                }
                const resolvedData = cfg.params._resolvedData as Array<{date: string; value: number}> | undefined;
                const evts = comparisonEvents.get(targetId) ?? [];
                const eventCounts: Record<string, number> = {};
                for (const ev of evts) {
                    const t = ev.type ?? 'OTHER';
                    eventCounts[t] = (eventCounts[t] ?? 0) + 1;
                }
                result.set(cfg.id, {
                    pointCount: resolvedData?.length ?? 0,
                    eventCounts,
                    firstDate: resolvedData && resolvedData.length > 0 ? resolvedData[0].date : null,
                });
            } else if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (!pairSlug) continue;
                try {
                    const store = getFxStore(pairSlug);
                    const storeData = store.getAllSorted();
                    result.set(cfg.id, {
                        pointCount: storeData.length,
                        eventCounts: {},
                        firstDate: storeData.length > 0 ? storeData[0].date : null,
                    });
                } catch {
                    result.set(cfg.id, {pointCount: 0, eventCounts: {}, firstDate: null});
                }
            }
        }
        return result;
    });

    // =========================================================================
    // Lifecycle
    // =========================================================================

    async function loadAssetSignalDefinitions(force = false) {
        try {
            signalDefinitions = await signalCatalogStore.load('asset', force);
            signalCatalogFailed = false;
        } catch (catalogError) {
            console.error('Failed to load Asset signal catalog:', catalogError);
            signalDefinitions = getLocalSignalDefinitions();
            signalCatalogFailed = true;
        }
    }

    type AssetPriceBulkQueryBody = Parameters<typeof zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post>[0];

    async function queryAssetPricesBulkWithSignalIsolation(body: AssetPriceBulkQueryBody): Promise<{items: Record<string, unknown>[]}> {
        const response = await axiosInstance.post<unknown>('/api/v1/assets/prices/query', body);
        return parseAssetPriceQueryWithSignalIsolation(response.data);
    }

    function applyBackendSignalResults(configs: SignalConfig[], requestVersion: number, results: BackendSignalResult[]) {
        const plan = buildBackendSignalRequestPlan(configs, signalDefinitions);
        const mapped = mapSignalInstanceResults(configs, plan, results);
        if (signalResultState.apply(requestVersion, mapped)) {
            signalInstanceResults = [...signalResultState.values()];
            if (isDebugEnabled()) {
                const assetLabel = assetInfo?.display_name ?? `Asset #${data.assetId}`;
                for (const item of mapped) {
                    const problem = getSignalProblem(item);
                    if (!problem) continue;
                    const severity = getSignalProblemSeverity(problem);
                    const logProblem = severity === 'error' ? debug.error : severity === 'warning' ? debug.warn : debug.info;
                    logProblem('AssetSignals', `${assetLabel} (#${data.assetId}) · ${item.result?.signal_code ?? item.config.signalType} · ${item.status}`, {
                        asset: {
                            id: data.assetId,
                            name: assetLabel,
                            ticker: assetInfo?.identifier_ticker ?? null,
                        },
                        signal: {
                            instanceId: item.config.id,
                            type: item.config.signalType,
                            code: item.result?.signal_code ?? null,
                            params: item.config.params,
                        },
                        status: item.status,
                        severity,
                        warningMessages: item.result?.warnings?.map((warning) => warning.message) ?? [],
                        problem,
                        availability: item.result?.availability ?? null,
                        warmup: item.result?.warmup ?? null,
                        error: item.result?.error ?? item.error,
                    });
                }
            }
        }
    }

    function backendRequestFingerprint(configs: SignalConfig[]): string {
        return JSON.stringify(
            buildBackendSignalRequestPlan(configs, signalDefinitions)
                .requests.map((request) => `${request.signal_code}:${JSON.stringify(request.params ?? {})}`)
                .sort(),
        );
    }

    /** The comparison peers of `configs`, without the asset this page shows. */
    function comparisonAssetIds(configs: SignalConfig[]): number[] {
        return comparisonPeerAssetIds(configs, data.assetId);
    }

    function calendarComparisonFingerprint(configs: SignalConfig[]): string {
        return JSON.stringify(comparisonAssetIds(configs));
    }

    function calendarDataFingerprint(configs: SignalConfig[], windowDays = calendarWindowDays): string {
        return JSON.stringify({
            assetId: data.assetId,
            start: urlDateStart,
            end: urlDateEnd,
            targetCurrency: displayCurrency || assetInfo?.currency || '',
            windowDays,
            peers: comparisonAssetIds(configs),
        });
    }

    function priceComparisonLoadFingerprint(configs: SignalConfig[]): string {
        return JSON.stringify({
            peers: configs
                .filter((config) => config.signalType === 'asset-comparison')
                .map((config) => ({configId: config.id, assetId: Number(config.params.assetId)}))
                .filter((peer) => Number.isSafeInteger(peer.assetId) && peer.assetId > 0 && peer.assetId !== data.assetId)
                .sort((left, right) => left.configId.localeCompare(right.configId)),
            start: dateStart,
            end: dateEnd,
            targetCurrency: displayCurrency || '',
        });
    }

    function priceComparisonRuntimeIsAuthoritative(configs: SignalConfig[]): boolean {
        return configs
            .filter((config) => config.signalType === 'asset-comparison')
            .filter((config) => {
                const assetId = Number(config.params.assetId);
                return Number.isSafeInteger(assetId) && assetId > 0 && assetId !== data.assetId;
            })
            .every((config) => Object.hasOwn(config.params, '_conversionFailed') && comparisonEvents.has(Number(config.params.assetId)));
    }

    async function retryBackendSignals() {
        await pageBusy.track('asset-signals-retry', async () => {
            await loadAssetSignalDefinitions(true);
            await loadChartData(false);
        });
    }

    /** Full page reload: fetches all data for the current assetId */
    async function reloadPage() {
        measurePanel?.clearMeasures();
        calendarMeasurePanel?.clearMeasures();
        measureSignals = [];
        calendarMeasureSignals = [];
        measureMode = false;
        calendarMeasureMode = false;
        loading = true;
        error = null;
        // Reset state for new asset
        // «All» resolves against the new asset's own history, not the earliest date of the one before.
        rearmMaxPendingBeforeReload();
        assetInfo = null;
        providerAssignment = null;
        providerAssignmentLoaded = false;
        chartData = [];
        events = [];
        signalInstanceResults = [];
        signalRequestFailed = false;
        // Y-40 (V-1 a): the detail opens in the view chosen for this asset — in the list, or here last time.
        const openingModes = detailModesForPrimaryView(settings.primaryView);
        primaryMode = openingModes.primaryMode;
        viewMode = openingModes.viewMode;
        chartRequestGeneration += 1;
        comparisonRequestGeneration += 1;
        comparisonAppliedFingerprint = null;
        comparisonInFlight = null;
        calendarReturnView = emptyCalendarReturnView();
        calendarComparisonViews = new Map();
        calendarComparisonProblems = new Map();
        calendarComparisonFxFailures = new Set();
        calendarSnapshotFingerprint = null;
        comparisonEvents = new Map();
        live.resetPrice();
        seriesRangeDeltaRefresh++;
        sectorDistribution = null;
        geographicDistribution = null;
        shortDescription = null;
        classificationLoaded = false;
        providerIconUrl = null;

        await Promise.all([ensureCurrenciesLoaded(get(currentLanguage)), ensureAssetProvidersCached(), loadAssetInfo(), loadProviderAssignment(), loadAssetSignalDefinitions(), loadFxPairSlugs(), loadAssetList()]);
        await loadChartData();
        // Resolve provider icon after data loads (use local ref to avoid TS narrowing)
        const info = assetInfo as AssetDetail | null;
        if (info?.provider_code) {
            providerIconUrl = getAssetProviderIconUrl(info.provider_code);
        }
        // Load classification data if available
        if (info?.has_metadata) {
            await loadClassificationData();
        } else {
            classificationLoaded = true;
        }
        // Load comparison asset data after initial data is ready
        await maybeLoadComparison();
        await loadSignalFxPairs();
    }

    // Track previous asset id for same-route navigation detection (plain var — not $state)
    let _prevAssetId: number | undefined;

    onMount(async () => {
        _prevAssetId = data.assetId;
        // The first load holds the page's Refresh button (Y11).
        await pageBusy.track('asset-first-load', () => reloadPage());
        void loadAssetAiExportCompatibility();
        if (assetInfo) onboardingGuide.maybeStartContextual('asset_detail_guide');
    });

    // A price catch-up (the bus's `{kind: 'prices'}`, Y5-1, Z-14b): the chart on screen is asked again, in silence — the stale points stay up, nothing
    // says the page is busy — and outside `pageBusy`: it is not the user's Refresh. The compared assets' prices follow the chart (they need its days).
    onMount(() =>
        onPricesCaughtUp(async () => {
            if (!pageAlive || !assetInfo) return;
            await loadChartData(false, signals, false, true);
            if (pageAlive && primaryMode === 'price') await maybeLoadComparison(false, signals, true);
        }),
    );

    // Re-load everything when navigating to a different asset (same route pattern)
    $effect(() => {
        const newId = data.assetId;
        if (_prevAssetId !== undefined && newId !== _prevAssetId) {
            _prevAssetId = newId;
            void pageBusy
                .track('asset-change', () => reloadPage())
                .then(() => {
                    if (assetInfo) onboardingGuide.maybeStartContextual('asset_detail_guide');
                });
        }
    });

    // Live current price — one poll feeds the price summary and the chart's last point (F26, decision 31): every 30 s
    // while the chart reaches today, paused while the tab is hidden or nobody uses the page. Created here, during the
    // page's initialisation, so its polling effect keeps its place among the page's effects.
    const live = new AssetDetailLive({
        get assetInfo() {
            return assetInfo;
        },
        get pageAssetId() {
            return data.assetId;
        },
        get displayCurrency() {
            return displayCurrency;
        },
        get fxConversionMissing() {
            return fxConversionMissing;
        },
        get isHeadToday() {
            return isHeadToday;
        },
        get rangeStart() {
            return dateStart;
        },
        get providerAssignment() {
            return providerAssignment;
        },
        get loading() {
            return loading;
        },
        get primaryMode() {
            return primaryMode;
        },
        get calendarReturnView() {
            return calendarReturnView;
        },
        get chartData() {
            return chartData;
        },
        set chartData(points) {
            chartData = points;
        },
        loadChartData: (force) => loadChartData(force),
    });

    // Reload chart data when displayCurrency changes (currency conversion)
    let prevDisplayCurrency = $state('');
    $effect(() => {
        const cur = displayCurrency;
        if (!cur || !prevDisplayCurrency) {
            // First run or not yet initialized — just track, don't reload
            prevDisplayCurrency = cur;
            return;
        }
        if (cur !== prevDisplayCurrency) {
            prevDisplayCurrency = cur;
            void trackChartAndComparison('asset-currency');
        }
    });

    // =========================================================================
    // Data Loading
    // =========================================================================

    async function loadAssetInfo() {
        try {
            // Tri-state `active` omitted on purpose: an expired or delisted instrument is
            // filed as inactive and must still be able to open its own detail page.
            const response = await zodiosApi.list_assets_api_v1_assets_query_get({queries: {}});
            const items = response as any[];
            const asset = items.find((a: any) => a.id === data.assetId);
            if (asset) {
                assetInfo = asset as AssetDetail;
                if (!displayCurrency) displayCurrency = asset.currency;
            } else {
                error = catalogueError('assetDetail.notFound');
            }
        } catch (e: any) {
            console.error('Failed to load asset info:', e);
            error = e?.message || catalogueError('assetDetail.loadFailed');
        }
    }

    async function loadProviderAssignment() {
        try {
            const response = await zodiosApi.get_provider_assignments_api_v1_assets_provider_assignments_get({
                queries: {asset_ids: [data.assetId]},
            });
            const items = response as any[];
            providerAssignment = items.length > 0 ? (items[0] as ProviderAssignmentFlat) : null;
        } catch (e: any) {
            console.error('Failed to load provider assignment:', e);
        } finally {
            providerAssignmentLoaded = true;
        }
    }

    /**
     * When "All" (MAX) is pending resolution, extract the real earliest date
     * from just-loaded chart data and update dateStart/displayDateStart.
     * The URL is left untouched — it keeps showing the generic "min"/"max"
     * sentinel (set in handleDateRangeChange) so the "All" selection survives
     * reloads/shares instead of freezing to a specific historical date.
     * No-op once already resolved or if there's no data yet.
     */
    function resolveMaxStartFromChartData() {
        if (!isMaxPending || chartData.length === 0) return;
        dateStart = chartData[0].date;
        displayDateStart = dateStart;
        isMaxPending = false;
        const resolvedStart = dateStart;
        if (primaryMode === 'price') {
            queueMicrotask(() => {
                if (pageAlive && primaryMode === 'price' && !isMaxPending && dateStart === resolvedStart) {
                    void maybeLoadComparison(false, signals, true);
                }
            });
        }
    }

    /**
     * Counterpart to resolveMaxStartFromChartData(): re-arm "All" resolution
     * before a forced full reload. Once isMaxPending resolves, dateStart
     * freezes at whatever the earliest stored date was AT THAT TIME — a sync
     * "Tutti" that later reaches further into the past would silently not
     * show, because the query itself never asks for it again (it keeps using
     * the frozen, narrower dateStart). Widening dateStart back to the anchor
     * and re-arming isMaxPending lets resolveMaxStartFromChartData() pick up
     * the new true earliest date once the fresh (wide) query returns.
     */
    function rearmMaxPendingBeforeReload() {
        if (activePreset !== 'MAX') return;
        isMaxPending = true;
        dateStart = resolveDateSentinel('min');
        displayDateStart = 'min';
    }

    /**
     * `silent`: the reload after a price catch-up (Y5-1) — the chart and the signals on screen stay as they are, and nothing
     * says the page is busy (no `loading`, no calendar `loading`, no `signalsLoading`): it is not a load the user asked for.
     */
    async function loadChartData(force = false, requestedSignalConfigs: SignalConfig[] = signals, propagateError = false, silent = false) {
        lastChartLoadAskedServer = false;
        const requestedAssetId = data.assetId;
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && data.assetId === requestedAssetId && isClientSessionCurrent(sessionGeneration);
        if (!current()) return;
        let requestedStart = dateStart;
        const requestedEnd = dateEnd;
        const requestedDisplayCurrency = displayCurrency;
        const requestedNativeCurrency = assetInfo?.currency ?? '';
        const effectiveCurrency = displayCurrency && assetInfo?.currency && displayCurrency !== assetInfo.currency ? displayCurrency : (assetInfo?.currency ?? '');
        const targetCurrency = displayCurrency && assetInfo?.currency && displayCurrency !== assetInfo.currency ? displayCurrency : undefined;
        const wantsCalendarReturn = primaryMode === 'calendar-return';
        const backendSignalConfigs = wantsCalendarReturn ? [] : requestedSignalConfigs;
        const requestPlan = buildBackendSignalRequestPlan(backendSignalConfigs, signalDefinitions);
        const requestVersion = signalResultState.beginRequest();
        const chartRequestVersion = ++chartRequestGeneration;
        const requestIsCurrent = () => current() && chartRequestVersion === chartRequestGeneration;
        const dataRequestIsCurrent = () => requestIsCurrent() && dateStart === requestedStart && dateEnd === requestedEnd && displayCurrency === requestedDisplayCurrency && (assetInfo?.currency ?? '') === requestedNativeCurrency;
        const requestedCalendarComparisonFingerprint = calendarComparisonFingerprint(requestedSignalConfigs);
        const calendarComparisonsAreCurrent = () => dataRequestIsCurrent() && calendarComparisonFingerprint(signals) === requestedCalendarComparisonFingerprint;
        const requestedCalendarWindow = calendarWindowDays;
        const requestedCalendarFingerprint = wantsCalendarReturn ? calendarDataFingerprint(requestedSignalConfigs, requestedCalendarWindow) : null;
        const retainCurrentCalendarDiagnostics = requestedCalendarFingerprint !== null && calendarSnapshotFingerprint === requestedCalendarFingerprint;
        const calendarRequestIsCurrent = () => requestedCalendarFingerprint !== null && dataRequestIsCurrent() && primaryMode === 'calendar-return' && calendarDataFingerprint(signals, calendarWindowDays) === requestedCalendarFingerprint;
        const calendarRequests = wantsCalendarReturn
            ? [
                  {
                      instance_id: CALENDAR_RETURN_INSTANCE_ID,
                      signal_code: CALENDAR_RETURN_SIGNAL_CODE,
                      params: {window_days: requestedCalendarWindow},
                  },
              ]
            : [];
        const calendarComparisonAssetIds = wantsCalendarReturn
            ? [
                  ...new Set(
                      requestedSignalConfigs
                          .filter((config) => config.signalType === 'asset-comparison')
                          .map((config) => Number(config.params.assetId))
                          .filter((assetId) => assetId > 0 && assetId !== requestedAssetId),
                  ),
              ]
            : [];
        let pricesFromCache = false;
        // A store a catch-up marked stale that still holds points for the range (Y5-1, D3): they go on screen at once and the
        // prices are asked in background, with no loading state.
        let staleShown = false;
        const chartPointsOf = (held: ReturnType<ReturnType<typeof getAssetPriceStore>['getRange']>['data']) =>
            held.map((p) => ({
                date: p.date,
                close: p.close,
                open: p.open,
                high: p.high,
                low: p.low,
                volume: p.volume,
                currency: p.currency,
                original_close: p.originalClose,
                backward_fill_info: p.backwardFillInfo ? {days_back: p.backwardFillInfo.daysBack} : null,
            }));

        // Cache-first: check if the price store already covers this range
        if (!force && effectiveCurrency) {
            const store = getAssetPriceStore(data.assetId, effectiveCurrency);
            const gaps = store.getMissingIntervals(dateStart, dateEnd);
            if (gaps.length > 0 && store.isStale) {
                const held = store.getRange(dateStart, dateEnd).data;
                if (held.length > 0) {
                    staleShown = true;
                    // A silent reload of the range already on screen leaves the chart alone; a return to the page, or another range, shows them.
                    if (!silent || chartData.length === 0) {
                        chartData = chartPointsOf(held);
                        error = null;
                    }
                }
            }
            if (gaps.length === 0) {
                // Cache hit — update chart data without loading spinner
                const cached = store.getRange(dateStart, dateEnd).data;
                chartData = chartPointsOf(cached);
                if (chartData.length === 0 && !error) {
                    error = catalogueError('assetDetail.noData');
                } else {
                    error = null;
                }
                resolveMaxStartFromChartData();
                // This request resolved "All" itself: track the resolved start, so its own answer is not taken for a stale one.
                requestedStart = dateStart;
                pricesFromCache = true;
                // No early return here: events travel in the same response as prices,
                // so a price-cache hit would otherwise leave `events` empty and make
                // them vanish from the chart and the data editor. Fall through with
                // include_price:false to fetch just the events (a tiny payload).
            }
        }

        const requestBody: AssetPriceBulkQueryBody = [
            {
                asset_id: data.assetId,
                date_range: {start: dateStart, end: dateEnd},
                include_price: !pricesFromCache,
                include_events: true,
                target_currency: targetCurrency,
                signals: [...requestPlan.requests, ...calendarRequests],
            },
            ...calendarComparisonAssetIds.map((assetId) => ({
                asset_id: assetId,
                date_range: {start: dateStart, end: dateEnd},
                include_price: false,
                include_events: true,
                target_currency: effectiveCurrency || undefined,
                signals: calendarRequests,
            })),
        ];
        // N64: the same request, answered over the same price data (the generations of this asset's store and of each
        // peer's, read now), comes back from the signal cache with its events: no request, no spinner, no token (Q1).
        // Any invalidation of those stores — Refresh, a sync, a save, a catch-up marking them stale (Q2) — misses.
        const answerKey = effectiveCurrency ? assetChartAnswerKey(requestBody) : null;
        const answerGenerations = answerKey ? [requestedAssetId, ...calendarComparisonAssetIds].map((assetId) => getAssetPriceStore(assetId, effectiveCurrency).generation) : [];
        const cachedAnswer = answerKey && pricesFromCache && !force ? assetChartAnswers.get(answerKey, answerGenerations) : null;

        // Cache miss fetches prices + signals; cache hit requests events (+ signals) only.
        if (!silent) loading = !pricesFromCache && !staleShown;
        error = null;
        signalRequestFailed = false;
        signalsLoading = !silent && cachedAnswer === null && (requestPlan.requests.length > 0 || calendarComparisonAssetIds.length > 0);
        if (requestedCalendarFingerprint !== null) {
            calendarSnapshotFingerprint = requestedCalendarFingerprint;
            if (retainCurrentCalendarDiagnostics) {
                if (!silent) {
                    calendarReturnView = {
                        ...calendarReturnView,
                        state: 'loading',
                    };
                }
            } else {
                calendarReturnView = emptyCalendarReturnView('loading');
                calendarComparisonViews = new Map();
                calendarComparisonProblems = new Map();
                calendarComparisonFxFailures = new Set();
                comparisonEvents = new Map();
            }
        }
        lastChartLoadAskedServer = cachedAnswer === null;
        try {
            // A hit never awaits: the whole load runs before this call returns, in the same tick.
            const response = cachedAnswer ?? (await queryAssetPricesBulkWithSignalIsolation(requestBody));
            if (!dataRequestIsCurrent()) return;
            const responseItems: any[] = Array.isArray((response as any)?.items) ? (response as any).items : [];
            const result = responseItems.find((item) => item?.asset_id === requestedAssetId);
            if (result) {
                if (!pricesFromCache) {
                    chartData = result.prices ?? [];
                }
                events = result.events ?? [];
                const rawSignalResults: unknown[] = Array.isArray(result.signals) ? result.signals : [];
                const answeredCalendarView = wantsCalendarReturn ? extractCalendarReturnView(rawSignalResults, CALENDAR_RETURN_INSTANCE_ID) : null;
                // N64: only an answer the page can apply is kept — valid signal results, a calendar return that is not an error.
                let answerIsValid = answeredCalendarView === null || (answeredCalendarView.state !== 'error' && [...extractCalendarReturnViewsByAsset(responseItems, calendarComparisonAssetIds, CALENDAR_RETURN_INSTANCE_ID).values()].every((view) => view.state !== 'error'));
                if (wantsCalendarReturn && calendarRequestIsCurrent() && requestedCalendarWindow === calendarWindowDays && answeredCalendarView) {
                    calendarReturnView = answeredCalendarView;
                    if (calendarComparisonsAreCurrent()) {
                        const nextComparisonViews = extractCalendarReturnViewsByAsset(responseItems, calendarComparisonAssetIds, CALENDAR_RETURN_INSTANCE_ID);
                        calendarComparisonViews = retainCurrentCalendarDiagnostics ? preserveFactualCalendarPeersForCurrentUnavailable(calendarComparisonViews, nextComparisonViews, responseItems, calendarComparisonAssetIds) : nextComparisonViews;
                        calendarComparisonProblems = calendarComparisonProblemsFromResponse(responseItems, requestedSignalConfigs, calendarComparisonAssetIds, calendarComparisonViews, {assets: allAssets, displayCurrency});
                        calendarComparisonFxFailures = calendarComparisonFxFailuresFromResponse(responseItems, calendarComparisonAssetIds, calendarComparisonFxFailures);
                        comparisonEvents = new Map(
                            calendarComparisonAssetIds.map((assetId) => {
                                const item = responseItems.find((candidate) => candidate?.asset_id === assetId);
                                return [assetId, item && Array.isArray(item.events) ? [...item.events] : []];
                            }),
                        );
                    }
                }
                if (!wantsCalendarReturn) {
                    // X-R16: an invalid signal result fails the signals only, as a failed request does: nothing applied, the
                    // banner says so. The prices below still reach the cache and resolve «All».
                    let backendSignalResults: BackendSignalResult[] | null = null;
                    try {
                        backendSignalResults = parseBackendSignalResults(rawSignalResults.filter((item) => !isCalendarReturnSignalResult(item, CALENDAR_RETURN_INSTANCE_ID)));
                    } catch (signalError) {
                        console.error('Invalid signal results:', signalError);
                        signalRequestFailed = requestPlan.requests.length > 0;
                    }
                    if (backendSignalResults !== null) applyBackendSignalResults(backendSignalConfigs, requestVersion, backendSignalResults);
                    else answerIsValid = false;
                }
                if (cachedAnswer === null && answerKey !== null && answerIsValid) assetChartAnswers.set(answerKey, answerGenerations, assetChartAnswerForCache(response));
                // Populate the price cache (derive currency from response if not known yet)
                const cacheCurrency = effectiveCurrency || chartData[0]?.currency || '';
                if (!pricesFromCache && cacheCurrency && chartData.length > 0) {
                    const store = getAssetPriceStore(data.assetId, cacheCurrency);
                    store.merge(apiPricesToAssetPricePoints(chartData));
                    store.markFetched(dateStart, dateEnd);
                }
            } else {
                if (!pricesFromCache) chartData = [];
                events = [];
                if (!wantsCalendarReturn) {
                    applyBackendSignalResults(backendSignalConfigs, requestVersion, []);
                }
                if (wantsCalendarReturn && calendarRequestIsCurrent()) {
                    calendarReturnView = emptyCalendarReturnView('error');
                    calendarComparisonViews = new Map();
                    if (!retainCurrentCalendarDiagnostics) {
                        calendarComparisonProblems = new Map();
                        calendarComparisonFxFailures = new Set();
                    }
                }
            }
            if (chartData.length === 0 && !error) {
                error = catalogueError('assetDetail.noData');
            }
            resolveMaxStartFromChartData();
        } catch (e: any) {
            if (!dataRequestIsCurrent()) return;
            console.error('Failed to load chart data:', e);
            signalRequestFailed = requestPlan.requests.length > 0;
            if (wantsCalendarReturn && calendarRequestIsCurrent()) {
                calendarReturnView = emptyCalendarReturnView('error');
                calendarComparisonViews = new Map();
                if (!retainCurrentCalendarDiagnostics) {
                    calendarComparisonProblems = new Map();
                    calendarComparisonFxFailures = new Set();
                }
            }
            if (chartData.length === 0) error = e?.message || catalogueError('assetDetail.pricesLoadFailed');
            if (propagateError) throw e;
        } finally {
            if (requestIsCurrent()) {
                loading = false;
                signalsLoading = false;
            }
        }
    }

    async function loadFxPairSlugs(propagateError = false) {
        const requestedAssetId = data.assetId;
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && data.assetId === requestedAssetId && isClientSessionCurrent(sessionGeneration);
        if (!current()) return;
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            if (!current()) return;
            const items = response.items ?? [];
            const slugSet = new Set<string>();
            for (const i of items) {
                const b = i.base < i.quote ? i.base : i.quote;
                const q = i.base < i.quote ? i.quote : i.base;
                slugSet.add(`${b}-${q}`);
            }
            allConfiguredFxSlugs = [...slugSet].sort();
        } catch (e) {
            if (!current()) return;
            console.error('Failed to load FX pair slugs:', e);
            if (propagateError) throw e;
        }
    }

    async function loadAssetList() {
        try {
            const response = await zodiosApi.list_assets_api_v1_assets_query_get({queries: {}});
            allAssets = (response as any[]).map((a: any) => ({
                id: a.id,
                display_name: a.display_name,
                icon_url: a.icon_url ?? null,
                asset_type: a.asset_type ?? null,
                currency: a.currency ?? undefined,
                is_benchmark: a.is_benchmark === true,
            }));
        } catch (e) {
            console.error('Failed to load asset list:', e);
        }
    }

    async function loadClassificationData() {
        try {
            const response = await zodiosApi.read_assets_bulk_api_v1_assets_get({
                queries: {asset_ids: [data.assetId]},
            });
            const items = response as any[];
            if (items.length > 0 && items[0].classification_params) {
                const cp = items[0].classification_params;
                sectorDistribution = cp.sector_area?.distribution ?? null;
                geographicDistribution = cp.geographic_area?.distribution ?? null;
                shortDescription = cp.short_description ?? null;
            } else {
                // No classification data — reset to null (prevents stale data from previous asset)
                sectorDistribution = null;
                geographicDistribution = null;
                shortDescription = null;
            }
        } catch (e) {
            console.error('Failed to load classification data:', e);
            sectorDistribution = null;
            geographicDistribution = null;
            shortDescription = null;
        } finally {
            classificationLoaded = true;
        }
    }

    /**
     * Load comparison asset data if any comparison signals are configured.
     * Called explicitly from onMount, handleRefresh, handleDateRangeChange, handleSignalsChange.
     */
    function maybeLoadComparison(propagateError = false, requestedSignalConfigs: SignalConfig[] = signals, force = false): Promise<void> {
        lastComparisonLoadAskedServer = false;
        const requestedAssetId = data.assetId;
        const sessionGeneration = getClientSessionGeneration();
        const requestedFingerprint = priceComparisonLoadFingerprint(requestedSignalConfigs);
        if (!force && comparisonInFlight?.fingerprint === requestedFingerprint) {
            lastComparisonLoadAskedServer = true;
            return comparisonInFlight.promise;
        }
        if (!force && comparisonAppliedFingerprint === requestedFingerprint && priceComparisonRuntimeIsAuthoritative(requestedSignalConfigs)) {
            return Promise.resolve();
        }
        comparisonInFlight = null;
        const requestVersion = ++comparisonRequestGeneration;
        const current = () => pageAlive && data.assetId === requestedAssetId && isClientSessionCurrent(sessionGeneration) && primaryMode === 'price' && requestVersion === comparisonRequestGeneration && priceComparisonLoadFingerprint(signals) === requestedFingerprint;
        if (!current()) return Promise.resolve();
        if (requestedFingerprint !== comparisonAppliedFingerprint) {
            comparisonEvents = clearComparisonAssetsData(signals.filter((signal) => signal.signalType === 'asset-comparison'));
            overlayDataVersion++;
        }
        const requestedAssetIds = comparisonAssetIds(requestedSignalConfigs);
        if (requestedAssetIds.length === 0) {
            comparisonAppliedFingerprint = requestedFingerprint;
            return Promise.resolve();
        }
        if (lineData.length === 0) return Promise.resolve();
        // N64b: the same request over the same price data comes back from the cache, in this very tick: nothing is asked, no
        // busy token opens (`lastComparisonLoadAskedServer` stays false). Any invalidation of a peer's store, a sync, a refresh
        // misses.
        const answerPeerIds = requestedAssetIds.filter((assetId) => assetId !== requestedAssetId);
        const answerKey = comparisonAnswerKey(answerPeerIds, {start: dateStart, end: dateEnd}, displayCurrency || undefined);
        const answerGenerations = comparisonAnswerGenerations(answerPeerIds, allAssets, displayCurrency || undefined);
        const cachedLoad = !force && answerGenerations !== null ? comparisonSeriesAnswers.get(answerKey, answerGenerations) : null;
        if (cachedLoad !== null) {
            comparisonEvents = applyComparisonAssetsData(
                signals.filter((signal) => signal.signalType === 'asset-comparison'),
                cachedLoad,
            );
            comparisonAppliedFingerprint = requestedFingerprint;
            overlayDataVersion++;
            return Promise.resolve();
        }
        lastComparisonLoadAskedServer = true;
        const promise = (async () => {
            try {
                const loaded = await loadComparisonAssetsData(requestedAssetIds, {start: dateStart, end: dateEnd}, allAssets, requestedAssetId, displayCurrency || undefined);
                if (!current()) return;
                if (answerGenerations !== null && comparisonAnswerIsCacheable(loaded)) comparisonSeriesAnswers.set(answerKey, answerGenerations, loaded);
                comparisonEvents = applyComparisonAssetsData(
                    signals.filter((signal) => signal.signalType === 'asset-comparison'),
                    loaded,
                );
                comparisonAppliedFingerprint = requestedFingerprint;
                overlayDataVersion++;
            } catch (error) {
                if (!current()) return;
                console.error('Failed to load comparison asset data:', error);
                if (propagateError) throw error;
            }
        })();
        comparisonInFlight = {fingerprint: requestedFingerprint, promise};
        const clearInFlight = () => {
            if (comparisonInFlight?.promise === promise) comparisonInFlight = null;
        };
        void promise.then(clearInFlight, clearInFlight);
        return promise;
    }

    /**
     * Y-41: load into the FX store the rates of the pairs the saved `fx-pair` signals name, over the period on screen, then
     * redraw. A signal draws from the store, which only a sync or a refresh filled before: on a clean load, or on a pair
     * just chosen, it said «no data». The store finds its own gaps, so a pair it already holds asks nothing. Only the price
     * view draws these signals; never throws (`ensureSignalFxPairs`).
     */
    async function loadSignalFxPairs(requestedSignalConfigs: SignalConfig[] = signals): Promise<void> {
        if (primaryMode !== 'price' || fxPairSlugsOf(requestedSignalConfigs).length === 0) return;
        const requestedAssetId = data.assetId;
        const sessionGeneration = getClientSessionGeneration();
        const range = {start: dateStart, end: dateEnd};
        await ensureSignalFxPairs(requestedSignalConfigs, undefined, range);
        if (!pageAlive || data.assetId !== requestedAssetId || !isClientSessionCurrent(sessionGeneration) || dateStart !== range.start || dateEnd !== range.end) return;
        overlayDataVersion++;
    }

    /** N64 (Q1): the chart load under the page's busy token only when it asks the server; one the caches answer runs without. */
    function trackChartLoad(label: string, requestedSignalConfigs: SignalConfig[] = signals): Promise<void> {
        const running = loadChartData(false, requestedSignalConfigs);
        return lastChartLoadAskedServer ? pageBusy.track(label, () => running) : running;
    }

    /** N64 (Q1): the price-mode comparisons under the busy token only when they ask the server; their memo answers without. */
    function trackComparisonLoad(label: string, requestedSignalConfigs: SignalConfig[] = signals): Promise<void> {
        const running = maybeLoadComparison(false, requestedSignalConfigs);
        return lastComparisonLoadAskedServer ? pageBusy.track(label, () => running) : running;
    }

    /**
     * N64 (Q1): the chart, then the comparisons, as a change of period or currency always loaded them, with one busy
     * token if either asks the server: a period and currency already seen change the chart at once, with no token.
     */
    async function trackChartAndComparison(label: string): Promise<void> {
        const chart = loadChartData();
        if (lastChartLoadAskedServer) {
            await pageBusy.track(label, async () => {
                await chart;
                await maybeLoadComparison();
                await loadSignalFxPairs();
            });
            return;
        }
        await chart;
        await trackComparisonLoad(label);
        await loadSignalFxPairs();
    }

    // =========================================================================
    // Actions
    // =========================================================================

    async function loadAssetAiExportCompatibility() {
        assetAiExportCatalogLoading = true;
        try {
            assetAiExportCompatibility = await aiExportCatalogLoader.load();
            assetAiExportCatalogFailed = false;
        } catch {
            assetAiExportCatalogFailed = true;
            toasts.error($t('aiExport.catalogUnavailable'));
        } finally {
            assetAiExportCatalogLoading = false;
        }
    }

    function handleAssetAiExport(options: AiExportOptionsSelection): Promise<PreparedAiExport> {
        if (!assetInfo) return Promise.reject(new Error('Asset is not loaded'));
        return prepareAiExport({
            context: {
                domain: 'asset',
                assetId: data.assetId,
                snapshotAsOf: dateEnd,
                targetCurrency: displayCurrency || assetInfo.currency,
            },
            options,
            compatibility: assetAiExportCompatibility,
            translate: (key) => $t(key),
        });
    }

    function handleAssetAiExportCopied(result: PreparedAiExport) {
        const messages = getAiExportSuccessMessages($t, result);
        toasts.success(messages.copied);
        toasts.info(messages.privacyNotice);
    }

    async function handleRefresh(propagateError = false) {
        const requestedAssetId = data.assetId;
        const sessionGeneration = getClientSessionGeneration();
        const requestGeneration = ++refreshRequestGeneration;
        const resolvingMax = activePreset === 'MAX';
        const requestedMode = primaryMode;
        const requestedCurrency = displayCurrency;
        const requestedSignals = signals;
        const requestedSignalDataFingerprint = signalDataContextFingerprint(requestedSignals);
        invalidateAssetPriceStore(requestedAssetId);
        // N64: Refresh asks everything again — the signal answers too, the comparisons' calendar returns included.
        clearAssetPageAnswers();
        rearmMaxPendingBeforeReload();
        const requestedUrlStart = urlDateStart;
        const requestedUrlEnd = urlDateEnd;
        const current = () =>
            pageAlive &&
            data.assetId === requestedAssetId &&
            isClientSessionCurrent(sessionGeneration) &&
            requestGeneration === refreshRequestGeneration &&
            urlDateStart === requestedUrlStart &&
            urlDateEnd === requestedUrlEnd &&
            primaryMode === requestedMode &&
            displayCurrency === requestedCurrency &&
            signalDataContextFingerprint(signals) === requestedSignalDataFingerprint;
        if (!current()) return;
        seriesRangeDeltaRefresh++;
        await loadChartData(true, requestedSignals, propagateError);
        if (!current()) return;
        // Invalidate FX overlay stores so they refetch updated rates
        for (const pair of requiredFxPairs) {
            if (pair.status === 'missing') continue;
            getFxStore(pair.slug).invalidateAll();
            await ensureFxRangeLoaded(pair.slug, dateStart, dateEnd);
            if (!current()) return;
        }
        overlayDataVersion++;
        await maybeLoadComparison(propagateError, requestedSignals, !resolvingMax);
        if (current()) riskRefreshVersion += 1;
    }

    async function reloadMetadata() {
        // Mark the classification as stale immediately: `buildEditData()` reads it, so the
        // edit button must stay disabled for the whole reload, not just from the moment the
        // classification fetch starts. Otherwise reopening the modal right after a save
        // prefills it with the pre-save values.
        classificationLoaded = false;
        await Promise.all([loadAssetInfo(), loadProviderAssignment()]);
        // Update provider icon if changed
        if (assetInfo?.provider_code) {
            providerIconUrl = getAssetProviderIconUrl(assetInfo.provider_code);
        }
        // Reload classification data if metadata is available (always refresh after sync)
        if (assetInfo?.has_metadata) {
            await loadClassificationData();
        } else {
            sectorDistribution = null;
            geographicDistribution = null;
            shortDescription = null;
            classificationLoaded = true;
        }
    }

    // Page sync modal state
    let showPageSyncModal = $state(false);

    /** Collect all assets and FX pairs for sync-all modal */
    let syncAllAssets = $derived.by(() => {
        const items: Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null; provider_code?: string | null}> = [];
        // Main asset
        if (assetInfo?.provider_code) {
            items.push({id: data.assetId, display_name: assetInfo.display_name, icon_url: assetInfo.icon_url, asset_type: assetInfo.asset_type ?? null, provider_code: assetInfo.provider_code});
        }
        // Comparison assets with provider
        for (const cfg of signals) {
            if (cfg.signalType !== 'asset-comparison') continue;
            const aid = Number(cfg.params.assetId);
            if (!aid || aid === data.assetId) continue;
            const meta = allAssets.find((a) => a.id === aid);
            if (meta) {
                items.push({id: aid, display_name: meta.display_name, icon_url: meta.icon_url ?? undefined, asset_type: (meta as any).asset_type ?? null, provider_code: 'unknown'});
            }
        }
        return items;
    });

    let syncAllFxPairs = $derived(requiredFxPairs.filter((p) => p.status !== 'missing').map((p) => p.slug));

    /** The sync dialog's targets whose shown data holds a stored row in its range (C-66), for its warning: this asset
     * from its chart, a pair from its rate store; a comparison asset is not counted. */
    let syncAssetsWithData = $derived(showPageSyncModal && hasStoredPointInRange(chartData, syncDateStart, dateEnd) ? [data.assetId] : []);
    let syncFxPairsWithData = $derived(showPageSyncModal ? syncAllFxPairs.filter((slug) => hasStoredPointInRange(getFxStore(slug).getRange(dateStart, dateEnd).data, syncDateStart, dateEnd)) : []);

    function handleSync() {
        showPageSyncModal = true;
    }

    // The default only matters to a caller that forgets the detail, and such a caller must
    // read as a cancel: an omission must never invalidate the comparison as an acceptance.
    async function handlePageSyncComplete({accepted}: {accepted: boolean} = {accepted: false}) {
        if (accepted && primaryMode === 'calendar-return') {
            comparisonRequestGeneration += 1;
            comparisonInFlight = null;
            comparisonAppliedFingerprint = null;
            comparisonEvents = clearComparisonAssetsData(signals.filter((signal) => signal.signalType === 'asset-comparison'));
            overlayDataVersion++;
        }
        // No pageBusy token: the sync has its own indicator, and this reload is not one the user asked for (P3, Y11).
        await handleRefresh();
        await reloadMetadata();
        overlayDataVersion++;
    }

    async function handleFxPairCreated({base, quote}: FxPairCreatedDetail, assetIdAtCreation: number, wasForComparison: boolean, assetCurrency: string) {
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && data.assetId === assetIdAtCreation && isClientSessionCurrent(sessionGeneration);
        if (!current()) return;
        showFxPairAddModal = false;
        fxPairCreateSlug = '';
        invalidateFxRoutes();
        // Only update display currency when creating the main asset's FX pair
        if (!wasForComparison) {
            const nextDisplayCurrency = displayCurrencyAfterFxPairCreated({base, quote}, assetCurrency);
            if (nextDisplayCurrency !== null) {
                displayCurrency = nextDisplayCurrency;
            }
        }
        await loadFxPairSlugs(true);
        if (current()) await handleRefresh();
    }

    async function handleFxPairCreationSynced(detail: FxPairSyncCompleteDetail, assetIdAtCreation: number) {
        const current = () => pageAlive && data.assetId === assetIdAtCreation && isClientSessionCurrent(detail.sessionGeneration);
        if (!current()) return;
        await loadFxPairSlugs(true);
        // After the new pair's sync: no pageBusy token (P3, Y11).
        if (current()) await handleRefresh(true);
    }

    function createFxPairCallbacks(assetIdAtCreation: number, wasForComparison: boolean, assetCurrency: string) {
        return {
            oncreated: (detail: FxPairCreatedDetail) => pageBusy.track('asset-reload', () => handleFxPairCreated(detail, assetIdAtCreation, wasForComparison, assetCurrency)),
            onsynced: (detail: FxPairSyncCompleteDetail) => handleFxPairCreationSynced(detail, assetIdAtCreation),
            onclose: () => {
                if (!pageAlive || data.assetId !== assetIdAtCreation) return;
                showFxPairAddModal = false;
                fxPairCreateSlug = '';
            },
        };
    }

    async function handleDateRangeChange(newStart: string, newEnd: string) {
        isMaxPending = isMaxSentinel(newStart);
        dateStart = resolveDateSentinel(newStart);
        dateEnd = resolveDateSentinel(newEnd);
        displayDateStart = isMaxPending ? 'min' : dateStart;
        setDateRange(newStart, newEnd);
        // Sync URL for shareability. Keep the generic "min"/"max" sentinel when
        // "All" is selected (instead of a concrete resolved date) so the URL
        // stays meaningful across reloads/shares and the "All" badge doesn't
        // look stuck on a specific historical date.
        replaceHistoryDateRange(newStart, newEnd);
        await trackChartAndComparison('asset-period');
    }

    function handleMeasureClick(date: string, value: number) {
        if (primaryMode === 'price') {
            measurePanel?.addPoint(date, value);
        } else {
            calendarMeasurePanel?.addPoint(date, value);
        }
    }

    function activeMeasurePanel(): MeasurePanel | undefined {
        return primaryMode === 'price' ? measurePanel : calendarMeasurePanel;
    }

    function activeMeasureMode(): boolean {
        return primaryMode === 'price' ? measureMode : calendarMeasureMode;
    }

    // The measure tool's violet is its identity (categorical, left legacy); only the idle look is on roles. Each branch is its own literal (G3).
    function measureButtonClass(active: boolean): string {
        return active ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 ring-1 ring-violet-300 dark:ring-violet-700' : 'bg-lf-card/80 text-lf-muted hover:bg-lf-hover hover:text-lf-secondary';
    }

    function activeMeasuresOpen(): boolean {
        return primaryMode === 'price' ? showMeasures : showCalendarMeasures;
    }

    function setActiveMeasuresOpen(open: boolean): void {
        if (primaryMode === 'price') showMeasures = open;
        else showCalendarMeasures = open;
    }

    function handleAestheticsChange(values: {colorByBaseline: boolean; areaFill: boolean; gridLines: boolean; staleGradient: boolean; yAxisMode: 'auto' | 'include0' | 'custom'; yAxisMin: number | undefined; yAxisMax: number | undefined}) {
        setPairSettings(`asset-${data.assetId}`, {
            ...settings,
            colorByBaseline: values.colorByBaseline,
            areaFill: values.areaFill,
            gridLines: values.gridLines,
            staleGradient: values.staleGradient,
            signals: [...signals],
        });
    }

    function handleAxisScaleChange(key: string, scale: AxisScaleSettings) {
        const normalized = normalizeAxisScaleSettings(scale, DEFAULT_AXIS_SCALE);
        const axisScales = {
            absolute: {...settings.axisScales.absolute},
            percentage: {...settings.axisScales.percentage},
            secondary: {...settings.axisScales.secondary},
        };
        if (key === 'primary:absolute') {
            axisScales.absolute = normalized;
        } else if (key === 'primary:percentage') {
            axisScales.percentage = normalized;
        } else {
            axisScales.secondary[key] = normalized;
        }
        setPairSettings(`asset-${data.assetId}`, {
            ...settings,
            axisScales,
            signals: [...signals],
        });
    }

    function handleSignalsChange(newSignals: SignalConfig[]) {
        const shouldReloadBackend = backendRequestFingerprint(signals) !== backendRequestFingerprint(newSignals);
        const shouldReloadCalendarComparisons = calendarComparisonFingerprint(signals) !== calendarComparisonFingerprint(newSignals);
        const shouldReloadPriceComparisons = priceComparisonLoadFingerprint(signals) !== priceComparisonLoadFingerprint(newSignals);
        const shouldLoadFxPairs = fxPairSlugsOf(signals).join() !== fxPairSlugsOf(newSignals).join();
        setPairSettings(`asset-${data.assetId}`, {...settings, signals: JSON.parse(JSON.stringify(newSignals))});
        if (shouldLoadFxPairs) void loadSignalFxPairs(newSignals);
        if (primaryMode === 'price' && shouldReloadPriceComparisons) {
            void trackComparisonLoad('asset-comparison', newSignals);
        }
        if ((primaryMode === 'calendar-return' && shouldReloadCalendarComparisons) || (primaryMode === 'price' && shouldReloadBackend)) {
            void trackChartLoad('asset-signals', newSignals);
        }
    }

    async function handleSyncAsset(assetId: number, opts: {silent?: boolean} = {}) {
        if (activeAssetSyncRequests.has(assetId)) return;
        const requestGeneration = (assetSyncRequestGenerations.get(assetId) ?? 0) + 1;
        assetSyncRequestGenerations.set(assetId, requestGeneration);
        activeAssetSyncRequests.set(assetId, requestGeneration);
        syncingComparisonAssetIds = new Set(activeAssetSyncRequests.keys());
        try {
            await runSyncAsset(assetId, opts, requestGeneration);
        } finally {
            if (activeAssetSyncRequests.get(assetId) === requestGeneration) {
                activeAssetSyncRequests.delete(assetId);
            }
            syncingComparisonAssetIds = new Set(activeAssetSyncRequests.keys());
        }
    }

    async function runSyncAsset(assetId: number, opts: {silent?: boolean}, requestGeneration: number) {
        const silent = opts.silent === true;
        const pageAssetId = data.assetId;
        const sessionGeneration = getClientSessionGeneration();
        const requestedStart = syncDateStart;
        const requestedCacheStart = dateStart;
        const requestedEnd = dateEnd;
        const requestedDisplayCurrency = displayCurrency;
        const requestedPrimaryMode = primaryMode;
        const requestedCalendarWindow = calendarWindowDays;
        const calendarLookbackDays = requestedPrimaryMode === 'calendar-return' ? requestedCalendarWindow : 0;
        const requestedSyncRange = buildComparisonSyncRange({start: requestedStart, end: requestedEnd}, {calendarLookbackDays});
        const requestedCacheRange = buildComparisonSyncRange({start: requestedCacheStart, end: requestedEnd}, {calendarLookbackDays});
        const requestedSignals = signals;
        const requestedSignalDataFingerprint = signalDataContextFingerprint(requestedSignals);
        const comparisonAsset = allAssets.find((asset) => asset.id === assetId);
        const requiredFxSlugs = collectConfiguredComparisonFxSlugs(comparisonAsset?.currency, requestedDisplayCurrency, comparisonEvents.get(assetId) ?? [], allConfiguredFxSlugs);
        const requestedMainAssetCurrency = assetInfo?.currency;
        const mainConversionFxSlug = requestedMainAssetCurrency && requestedDisplayCurrency && requestedMainAssetCurrency !== requestedDisplayCurrency ? [requestedMainAssetCurrency, requestedDisplayCurrency].sort((left, right) => left.localeCompare(right)).join('-') : null;
        const current = () =>
            pageAlive &&
            data.assetId === pageAssetId &&
            isClientSessionCurrent(sessionGeneration) &&
            activeAssetSyncRequests.get(assetId) === requestGeneration &&
            syncDateStart === requestedStart &&
            dateStart === requestedCacheStart &&
            dateEnd === requestedEnd &&
            displayCurrency === requestedDisplayCurrency &&
            primaryMode === requestedPrimaryMode &&
            (requestedPrimaryMode !== 'calendar-return' || calendarWindowDays === requestedCalendarWindow) &&
            signalDataContextFingerprint(signals) === requestedSignalDataFingerprint;

        const assetRequest = zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([
            {
                asset_id: assetId,
                date_range: requestedSyncRange,
            },
        ]);
        const fxRequest =
            requiredFxSlugs.length > 0
                ? zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                      pairs: requiredFxSlugs,
                      start: requestedSyncRange.start,
                      end: requestedSyncRange.end,
                  })
                : Promise.resolve(null);
        const [assetOutcome, fxOutcome] = await Promise.allSettled([assetRequest, fxRequest]);
        // N64: a sync may have changed what a kept signal answer was computed from — this asset, a comparison peer, a
        // pair — even when its answer finds the page moved on: every answer is asked again, as before the cache.
        clearAssetPageAnswers();
        if (!current()) return;

        const tr = get(t);
        let acceptedSyncInvalidated = false;
        const invalidateAcceptedSyncRequests = () => {
            if (acceptedSyncInvalidated) return;
            acceptedSyncInvalidated = true;
            chartRequestGeneration += 1;
            comparisonRequestGeneration += 1;
            comparisonInFlight = null;
        };
        let assetSyncAccepted = false;
        if (assetOutcome.status === 'fulfilled') {
            const response = assetOutcome.value;
            const r = (response as any)?.results?.[0];
            if (!silent) {
                if (r) {
                    const toast = buildAssetSyncToast(r, tr('common.sync'), tr);
                    toasts[toast.variant](toast.message);
                } else {
                    toasts.error(`${tr('common.sync')} — ${tr('prices.sync.noResponse')}`);
                }
            }
            assetSyncAccepted = r?.status === 'ok' || r?.status === 'partial';
            if (assetSyncAccepted) invalidateAcceptedSyncRequests();

            // I-bis #24 (2026-04-24) — targeted post-sync refresh.
            //
            // Design rationale (post-§2a-1 retest feedback): prefer a
            // point-targeted merge over a full chart reload whenever the
            // backend returned a reliable ``changed_points`` delta. This is
            // the intended UX — when a current-price tick updates today's
            // OHLC, only that point changes and all derived signals
            // (EMA/MACD/RSI/Bollinger) recompute automatically via $derived
            // since they depend on ``chartData``.
            //
            // Full ``loadChartData()`` reload is used ONLY as a fallback
            // when the delta is either:
            //   (a) missing / above the backend cap (CHANGED_POINTS_PAYLOAD_CAP)
            //   (b) too large for an in-place merge (more than DELTA_MERGE_LIMIT)
            //   (c) tainted by side channels needing a full query:
            //       - display currency ≠ asset currency (delta is raw DB
            //         values, unsuitable for the FX-converted chart — would
            //         flash wrong numbers in the middle of the series)
            //       - events changed (events are reloaded by the query
            //         endpoint, not present in ``changed_points``)
            if (assetId === pageAssetId && r?.asset_id === assetId) {
                const changedPoints = Array.isArray(r.changed_points) ? r.changed_points : null;
                const isConvertedChart = !!(requestedDisplayCurrency && assetInfo?.currency && requestedDisplayCurrency !== assetInfo.currency);
                const eventsChanged = Number(r.events_changed ?? 0) > 0;
                const DELTA_MERGE_LIMIT = 50;

                const canMergeOnly = changedPoints && changedPoints.length > 0 && changedPoints.length <= DELTA_MERGE_LIMIT && !isConvertedChart && !eventsChanged;

                if (canMergeOnly) {
                    // In-place targeted refresh — no full reload, no flicker.
                    chartData = mergeChartPointsIncremental(chartData, changedPoints);
                } else if (changedPoints && changedPoints.length > 0) {
                    // Partial info available: merge for instant feedback,
                    // then still run a full reload to pick up FX/events.
                    if (!isConvertedChart) {
                        chartData = mergeChartPointsIncremental(chartData, changedPoints);
                    }
                    invalidateAssetPriceStore(pageAssetId);
                    rearmMaxPendingBeforeReload();
                    await loadChartData(true);
                    if (!current()) return;
                } else {
                    // No delta from backend (no changes, or above cap,
                    // or reload is needed anyway): full reload.
                    invalidateAssetPriceStore(pageAssetId);
                    rearmMaxPendingBeforeReload();
                    await loadChartData(true);
                    if (!current()) return;
                }
            }
        } else if (!silent) {
            const reason = assetOutcome.reason;
            toasts.error('Sync failed: ' + (reason instanceof Error ? reason.message : String(reason ?? 'unknown')));
        }

        let fxSyncAccepted = false;
        const acceptedRequiredFxSlugs = new Set<string>();
        let mainConversionFxAccepted = false;
        if (fxOutcome.status === 'fulfilled' && fxOutcome.value) {
            const fxResults = Array.isArray((fxOutcome.value as any)?.results) ? (fxOutcome.value as any).results : [];
            for (const slug of requiredFxSlugs) {
                const result = fxResults.find((candidate: any) => candidate?.pair === slug);
                const toast = buildFxSyncToast(result, slug, tr);
                if (!silent) toasts[toast.variant](toast.message);
                if (result?.status === 'ok' || result?.status === 'partial') {
                    fxSyncAccepted = true;
                    acceptedRequiredFxSlugs.add(slug);
                    if (slug === mainConversionFxSlug) mainConversionFxAccepted = true;
                    invalidateAcceptedSyncRequests();
                    getFxStore(slug).invalidateAll();
                    try {
                        await ensureFxRangeLoaded(slug, requestedCacheRange.start, requestedCacheRange.end);
                    } catch (error: any) {
                        if (current() && !silent) toasts.error(`FX sync failed: ${error?.message || 'unknown'}`);
                    }
                    if (!current()) return;
                }
            }
        } else if (fxOutcome.status === 'rejected' && !silent) {
            const reason = fxOutcome.reason;
            toasts.error(`FX sync failed: ${reason instanceof Error ? reason.message : String(reason ?? 'unknown')}`);
        }

        if (!current() || (!assetSyncAccepted && !fxSyncAccepted)) return;
        const allRequiredFxAccepted = requiredFxSlugs.length > 0 && requiredFxSlugs.every((slug) => acceptedRequiredFxSlugs.has(slug));
        if (allRequiredFxAccepted) comparisonAppliedFingerprint = null;
        if (mainConversionFxAccepted) invalidateAssetPriceStore(pageAssetId);
        // Reload comparison data for the synced asset, then trigger UI update.
        if (requestedPrimaryMode === 'calendar-return') {
            await loadChartData(mainConversionFxAccepted, requestedSignals);
            if (!current()) return;
            comparisonAppliedFingerprint = null;
            clearComparisonAssetsData(signals.filter((signal) => signal.signalType === 'asset-comparison'));
        } else {
            await loadChartData(mainConversionFxAccepted, requestedSignals);
            if (!current()) return;
            await maybeLoadComparison(false, requestedSignals, true);
            if (!current()) return;
        }
        overlayDataVersion++;
    }

    function handleDetailAsset(assetId: number) {
        goto(`/assets/${assetId}?start=${urlDateStart}&end=${urlDateEnd}`);
    }

    async function handleSyncPair(slug: string) {
        const pageAssetId = data.assetId;
        const sessionGeneration = getClientSessionGeneration();
        const requestGeneration = (fxSyncRequestGenerations.get(slug) ?? 0) + 1;
        fxSyncRequestGenerations.set(slug, requestGeneration);
        activeFxSyncRequests.set(slug, requestGeneration);
        const requestedStart = syncDateStart;
        const requestedCacheStart = dateStart;
        const requestedEnd = dateEnd;
        const requestedDisplayCurrency = displayCurrency;
        const requestedPrimaryMode = primaryMode;
        const requestedSignals = signals;
        const requestedSignalDataFingerprint = signalDataContextFingerprint(requestedSignals);
        const current = () =>
            pageAlive &&
            data.assetId === pageAssetId &&
            isClientSessionCurrent(sessionGeneration) &&
            requestGeneration === activeFxSyncRequests.get(slug) &&
            syncDateStart === requestedStart &&
            dateStart === requestedCacheStart &&
            dateEnd === requestedEnd &&
            displayCurrency === requestedDisplayCurrency &&
            primaryMode === requestedPrimaryMode &&
            signalDataContextFingerprint(signals) === requestedSignalDataFingerprint;
        fxSyncing = true;
        try {
            const syncResponse = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                pairs: [slug],
                start: requestedStart,
                end: requestedEnd,
            });
            // N64: the rates may have changed under a converted answer, even when this one finds the page moved on.
            clearAssetPageAnswers();
            if (!current()) return;
            const tr = get(t);
            const r = (syncResponse as any)?.results?.[0];
            const toast = buildFxSyncToast(r, slug, tr);
            toasts[toast.variant](toast.message);
            if (r?.status !== 'ok' && r?.status !== 'partial') return;
            chartRequestGeneration += 1;
            comparisonRequestGeneration += 1;
            comparisonInFlight = null;
            // Refetch FX data into store after sync (invalidate + reload)
            getFxStore(slug).invalidateAll();
            try {
                await ensureFxRangeLoaded(slug, requestedCacheStart, requestedEnd);
            } catch (error: any) {
                if (current()) toasts.error('FX sync failed: ' + (error?.message || 'unknown'));
            }
            if (!current()) return;
            overlayDataVersion++;
            // Reload asset chart data to apply updated FX conversion
            invalidateAssetPriceStore(pageAssetId);
            await loadChartData(true, requestedSignals);
            if (!current()) return;
            if (requestedPrimaryMode === 'price') {
                await maybeLoadComparison(false, requestedSignals, true);
                if (!current()) return;
            } else {
                comparisonAppliedFingerprint = null;
                clearComparisonAssetsData(signals.filter((signal) => signal.signalType === 'asset-comparison'));
                overlayDataVersion++;
            }
        } catch (e: any) {
            if (current()) toasts.error('FX sync failed: ' + (e?.message || 'unknown'));
        } finally {
            if (requestGeneration === activeFxSyncRequests.get(slug)) {
                activeFxSyncRequests.delete(slug);
            }
            if (pageAlive) fxSyncing = activeFxSyncRequests.size > 0;
        }
    }

    function handleDetailPair(slug: string) {
        goto(`/fx/${slug}?start=${urlDateStart}&end=${urlDateEnd}`);
    }

    async function handleAssetUpdated() {
        editModalOpen = false;
        const prevCurrency = assetInfo?.currency;
        await reloadMetadata();
        // I.6 post-feedback: if the asset currency was changed via the wipe-on-change
        // flow, the previously-selected `displayCurrency` is now stale (still pointing
        // to the OLD asset currency). Reset it to the NEW asset.currency so the chart
        // does not attempt a meaningless self-conversion and the "Display currency"
        // selector visually reflects the new baseline.
        if (prevCurrency && assetInfo?.currency && assetInfo.currency !== prevCurrency) {
            displayCurrency = assetInfo.currency;
        }
        await handleRefresh();
    }

    function buildEditData() {
        if (!assetInfo) return null;
        // Build classification_params from loaded data. `short_description` is
        // included here (bug-fix 2026-04-22): without it the edit modal opens
        // with an empty "Description" textarea even though the DB has a value,
        // because the modal reads `data.classification_params.short_description`.
        const hasClassification = sectorDistribution || geographicDistribution || shortDescription;
        const classification_params = hasClassification
            ? {
                  short_description: shortDescription ?? null,
                  sector_area: sectorDistribution ? {distribution: sectorDistribution} : null,
                  geographic_area: geographicDistribution ? {distribution: geographicDistribution} : null,
              }
            : null;
        return {
            id: assetInfo.id,
            display_name: assetInfo.display_name,
            currency: assetInfo.currency,
            asset_type: assetInfo.asset_type ?? '',
            icon_url: assetInfo.icon_url,
            quote_base_quantity: assetInfo.quote_base_quantity ?? 1,
            active: assetInfo.active,
            is_benchmark: assetInfo.is_benchmark,
            classification_params,
            identifier_isin: assetInfo.identifier_isin,
            identifier_ticker: assetInfo.identifier_ticker,
            identifier_cusip: assetInfo.identifier_cusip,
            identifier_sedol: assetInfo.identifier_sedol,
            identifier_figi: assetInfo.identifier_figi,
            identifier_uuid: assetInfo.identifier_uuid,
            identifier_other: assetInfo.identifier_other,
            provider_code: providerAssignment?.provider_code ?? null,
            provider_identifier: providerAssignment?.identifier ?? '',
            provider_identifier_type: providerAssignment?.identifier_type ?? '',
            provider_params: providerAssignment?.provider_params ?? null,
            provider_user_url: assetInfo.user_url ?? '',
            provider_url: providerAssignment?.provider_url ?? null,
        };
    }

    function handleAssetDetailTabChange(tabId: string): void {
        if (!ASSET_DETAIL_TAB_IDS.includes(tabId as AssetDetailTabId)) return;
        activeTab = tabId as AssetDetailTabId;
        void goto(buildTabUrl($page.url, tabId === 'overview' ? null : tabId), {replaceState: true, noScroll: true});
    }

    async function openSignalConfiguration(): Promise<void> {
        setPrimaryMode('price');
        handleAssetDetailTabChange('overview');
        showSignals = true;
        await tick();
        document.querySelector('[data-testid="asset-detail-signals-toggle"]')?.scrollIntoView({behavior: 'smooth', block: 'start'});
    }
</script>

<div
    class="space-y-4 text-lf-primary"
    data-testid="asset-detail-page"
    data-live-updates={live.updatesState}
    aria-busy={loading || (primaryMode === 'calendar-return' && calendarReturnView.state === 'loading')}
    data-busy={loading || (primaryMode === 'calendar-return' && calendarReturnView.state === 'loading') ? 'true' : 'false'}
>
    <!-- ======================================================================= -->
    <!-- Header: asset info + back button -->
    <!-- ======================================================================= -->
    <AssetDetailHeader assetId={data.assetId} {assetInfo} {loading} {currencyFlag} {providerIconUrl} {assetProviderName} {userUrl} {providerExternalUrl} transactionsHref={assetInfo ? buildTransactionsFiltersUrl({asset_id: assetInfo.id}) : ''} liveUpdatesState={live.updatesState} />

    <!-- Error banner (not data-quality — dismissible runtime error) -->
    {#if error}
        <div class="bg-lf-warning-soft border border-lf-warning-line rounded-xl p-4 text-sm text-lf-warning-on-soft flex items-center gap-2">
            <span>⚠️</span> <span>{errorMessage}</span>
            <button class="ml-auto text-xs px-2 py-1 bg-lf-warning-line/50 rounded hover:bg-lf-warning-line" onclick={() => (error = null)}>{$t('common.close')}</button>
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- Page controls — shared PageToolbar (same component as dashboard/broker-detail/assets
         list), including the integrated Overview/Risk tab row. -->
    <!-- oneRow:       [ datepicker  price-summary ─── actions-2×2 ]  1 row, picker 1-row     -->
    <!-- denseRow:     [ datepicker  price-summary ─── actions-2×2 ]  1 row, picker 2-row     -->
    <!-- stackFilters: [ datepicker       ] [ actions ]  filters+summary stacked+justified     -->
    <!--               [ price-summary    ] [ 4×1     ]  (start-aligned, capped to picker's     -->
    <!--                                                  width via pickerMaxWidth), actions    -->
    <!--                                                  stay BESIDE (4×1 column)               -->
    <!-- oneColumn:    [ datepicker       ]  whole bar now ONE column — actions moved BELOW,  -->
    <!--               [ price-summary    ]  still a labeled 2×2 grid (only position changed) -->
    <!--               [ actions ── 2×2   ]  (narrowest tier — Round 12 removed iconOnly)     -->
    <!-- ======================================================================= -->
    <PageToolbar
        thresholds={{oneRow: 1215, denseRow: 890, stackFilters: 510, oneColumn: 360, labelHideActions: 230, labelHideTabs: 370}}
        tabs={assetDetailTabs}
        {activeTab}
        ontabchange={handleAssetDetailTabChange}
        testId="asset-detail-controls"
        filterRowTestId="asset-detail-filter-bar"
        layoutDebugName="assetDetail"
        bind:layoutMode={pageLayoutMode}
    >
        {#snippet filters()}
            <!-- Round 14 bugfix: `contents` (not `flex flex-1 ...`) — see assets/+page.svelte's
                 equivalent wrapper for the full explanation (DateRangePicker self-applies
                 grow+max-width when align="start"; an extra flex-1 wrapper with no cap grows
                 past the picker's own capped width, pushing the summary sibling too far right). -->
            <div class="contents">
                <DateRangePicker bind:activePreset bind:end={dateEnd} bind:start={displayDateStart} compact={true} align="start" maxWidthTwoRow={445} layoutMode={pageLayoutMode} debugName="assetDetail" onchange={handleDateRangeChange} bind:effectiveMaxWidth={pickerMaxWidth} />
            </div>
        {/snippet}

        {#snippet summary({layoutMode, filtersStacked})}
            {#if assetInfo}
                <AssetPriceSummary
                    {lastPrice}
                    {deltaPercent}
                    {deltaAbs}
                    bind:displayCurrency
                    assetCurrency={assetInfo.currency}
                    {layoutMode}
                    {filtersStacked}
                    maxWidth={pickerMaxWidth}
                    livePriceConversionFailed={live.conversionFailed}
                    livePriceDirection={live.direction}
                    livePriceFlashToken={live.flashToken}
                    fxPairUrl={mainFxPairUrl}
                    onCreateForex={() => (showFxPairAddModal = true)}
                />
            {/if}
        {/snippet}

        {#snippet actions({showActionLabels})}
            <AssetDetailToolbarActions
                {showActionLabels}
                assetId={data.assetId}
                aiExportCompatibility={assetAiExportCompatibility}
                aiExportLabels={assetAiExportLabels}
                aiExportDisabled={assetAiExportCatalogLoading || assetAiExportCatalogFailed || !assetInfo}
                onaiexportprepare={handleAssetAiExport}
                onaiexportcopied={handleAssetAiExportCopied}
                editDisabled={!assetInfo || !classificationLoaded}
                onedit={() => {
                    editDataForModal = buildEditData();
                    editModalOpen = true;
                }}
                {syncBlocked}
                {syncDisabledReason}
                {syncing}
                {isParametric}
                {providerAssignmentLoaded}
                onsync={handleSync}
                busy={pageBusy.busy}
                onrefresh={() => void pageBusy.track('asset-refresh', () => handleRefresh())}
            />
        {/snippet}
    </PageToolbar>

    {#if activeTab === 'overview'}
        <!-- Unified data quality banners -->
        <DataQualityBanner issues={assetDetailIssues} mode="flat" onaction={handleBannerAction} />
    {/if}

    {#if activeTab === 'overview'}
        <!-- ======================================================================= -->
        <!-- Foldable Panel: Signals (ABOVE chart, replaces old Aesthetics position) -->
        <!-- ======================================================================= -->
        <AssetDetailSignalsPanel bind:open={showSignals}>
            <ChartSignalsSection
                signals={signalPanelConfigs}
                definitions={signalDefinitions}
                allowedSignalTypes={primaryMode === 'calendar-return' ? ['asset-comparison'] : undefined}
                backendError={primaryMode === 'price' ? signalBackendError : null}
                {signalsLoading}
                onretrybackend={retryBackendSignals}
                availablePairs={allConfiguredFxSlugs}
                availableAssets={allAssets.filter((a) => a.id !== data.assetId)}
                mainPairSlug={`asset-${data.assetId}`}
                onchange={handleSignalsChange}
                onsyncpair={handleSyncPair}
                ondetailpair={handleDetailPair}
                onsyncasset={handleSyncAsset}
                syncingAssetIds={syncingComparisonAssetIds}
                ondetailasset={handleDetailAsset}
                {signalSummaries}
                {dateStart}
                {displayCurrency}
                configuredFxSlugs={allConfiguredFxSlugs}
                oncreatefxpair={(slug) => {
                    fxPairCreateSlug = slug;
                    showFxPairAddModal = true;
                }}
                onsyncfxpair={handleSyncPair}
            />
        </AssetDetailSignalsPanel>

        <!-- ======================================================================= -->
        <!-- Chart with left toolbar -->
        <!-- ======================================================================= -->
        <div
            class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle p-4"
            data-testid="asset-detail-chart"
            data-view-mode={viewMode}
            data-primary-mode={primaryMode}
            data-window-days={primaryMode === 'calendar-return' ? calendarWindowDays : undefined}
            data-window-kind={primaryMode === 'calendar-return' ? calendarWindowSelection.kind : undefined}
            data-window-amount={primaryMode === 'calendar-return' && calendarWindowSelection.kind === 'custom' ? calendarWindowSelection.customAmount : undefined}
            data-window-unit={primaryMode === 'calendar-return' && calendarWindowSelection.kind === 'custom' ? calendarWindowSelection.customUnit : undefined}
            data-calendar-range-days={calendarRangeDays}
            data-calendar-comparison-ready={primaryMode === 'calendar-return' ? calendarComparisonState.ready.join(',') : undefined}
            data-calendar-comparison-partial={primaryMode === 'calendar-return' ? calendarComparisonState.partial.join(',') : undefined}
            data-calendar-comparison-unavailable={primaryMode === 'calendar-return' ? calendarComparisonState.unavailable.join(',') : undefined}
            data-calendar-comparison-error={primaryMode === 'calendar-return' ? calendarComparisonState.error.join(',') : undefined}
            data-calendar-primary-problem-code={primaryMode === 'calendar-return' ? (calendarReturnView.problem?.code ?? undefined) : undefined}
            data-calendar-primary-problem-status={primaryMode === 'calendar-return' ? (calendarReturnView.problem?.status ?? undefined) : undefined}
            data-series-state={chartSeriesState}
            use:guideAnchor={'asset.detail.chart'}
        >
            {#if primaryMode === 'price' && loading && lineData.length === 0}
                <div class="h-96 flex items-center justify-center">
                    <div class="text-center">
                        <RefreshCw size={24} class="animate-spin text-lf-link mx-auto mb-2" />
                        <p class="text-sm text-lf-muted">{$t('assetDetail.loadingPrices')}</p>
                    </div>
                </div>
            {:else if (primaryMode === 'price' && lineData.length > 0) || primaryMode === 'calendar-return'}
                <div class="mb-3 flex flex-wrap items-center justify-between gap-2" data-testid="asset-chart-primary-controls">
                    <AssetChartModeToggle {primaryMode} onselect={setPrimaryMode} />
                    {#if primaryMode === 'calendar-return'}
                        <AssetCalendarWindowControls selection={calendarWindowSelection} bind:customAmount={calendarCustomAmount} bind:customUnit={calendarCustomUnit} bind:customEditing={calendarCustomEditing} onpreset={setCalendarPreset} oncustom={setCalendarCustom} />
                    {/if}
                </div>

                <!-- Aesthetics panel (ABOVE chart, shown only when gear is active) -->
                {#if showAesthetics}
                    <div data-testid="asset-detail-aesthetics-panel" class="mb-3 pb-3 border-b border-lf-subtle relative">
                        <button class="absolute top-0 right-0 p-1 rounded-lg text-lf-muted hover:text-lf-secondary hover:bg-lf-hover transition-colors" onclick={() => (showAesthetics = false)} title={$t('common.close')}>
                            <X size={16} />
                        </button>
                        <ChartAestheticsSection
                            colorByBaseline={settings.colorByBaseline}
                            areaFill={settings.areaFill}
                            gridLines={settings.gridLines}
                            staleGradient={settings.staleGradient}
                            axisRows={aestheticsAxisRows}
                            onchange={handleAestheticsChange}
                            onaxischange={handleAxisScaleChange}
                            disabledFields={disabledAesthetics}
                        />
                    </div>
                {/if}

                {#if primaryMode === 'calendar-return' && calendarChartState === 'loading'}
                    <div class="h-96 flex items-center justify-center" data-testid="asset-calendar-return-loading">
                        <RefreshCw size={24} class="animate-spin text-lf-link" />
                    </div>
                {:else if primaryMode === 'calendar-return' && calendarChartState === 'unavailable'}
                    <div class="h-96 flex items-center justify-center text-sm text-lf-muted" data-testid="asset-calendar-return-unavailable">
                        <span data-testid="asset-calendar-primary-problem" data-problem-code={calendarReturnView.problem?.code} data-problem-status={calendarReturnView.problem?.status}>
                            {calendarPrimaryProblemMessage ?? $t('chartSettings.signalProblems.unavailable')}
                        </span>
                    </div>
                {:else if primaryMode === 'calendar-return' && calendarChartState === 'error'}
                    <div class="h-96 flex items-center justify-center text-sm text-lf-danger" data-testid="asset-calendar-return-error">
                        <span data-testid="asset-calendar-primary-problem" data-problem-code={calendarReturnView.problem?.code} data-problem-status={calendarReturnView.problem?.status}>
                            {calendarPrimaryProblemMessage ?? $t('chartSettings.signalResultsUnavailable')}
                        </span>
                    </div>
                {:else}
                    <div class="relative">
                        <!-- Right toolbar -->
                        <div class="absolute top-0 right-0 z-20 flex items-center gap-1.5">
                            <button
                                data-testid="asset-detail-measure-btn"
                                class="p-1.5 rounded-lg transition-colors {measureButtonClass(activeMeasureMode())}"
                                onclick={async () => {
                                    if (activeMeasureMode()) {
                                        activeMeasurePanel()?.stopMeasureMode();
                                    } else {
                                        setActiveMeasuresOpen(true);
                                        await tick();
                                        activeMeasurePanel()?.startMeasureMode();
                                    }
                                }}
                                title={activeMeasureMode() ? $t('common.exitMeasure') : $t('common.addMeasure')}
                            >
                                <Ruler size={16} />
                            </button>
                            {#if primaryMode === 'price'}
                                <!-- colour: closest role, to review: the edit toggle's active amber is a mode accent, not a warning; warning roles keep the hue (alternative: bg-lf-selected text-lf-link) -->
                                <button
                                    data-testid="asset-detail-editdata-btn"
                                    use:guideAnchor={'asset.detail.editor'}
                                    class="p-1.5 rounded-lg transition-colors {showDataEditor ? 'bg-lf-warning-soft text-lf-warning ring-1 ring-lf-warning-line' : 'bg-lf-card/80 text-lf-muted hover:bg-lf-hover hover:text-lf-secondary'}"
                                    onclick={() => {
                                        if (showDataEditor) {
                                            showDataEditor = false;
                                            pendingPreviewSignal = null;
                                            if (savedPanelStates) {
                                                showAesthetics = savedPanelStates.aesthetics;
                                                showMeasures = savedPanelStates.measures;
                                                showSignals = savedPanelStates.signals;
                                                savedPanelStates = null;
                                            }
                                        } else {
                                            savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                            showAesthetics = false;
                                            showMeasures = false;
                                            showSignals = false;
                                            showDataEditor = true;
                                        }
                                    }}
                                    title={showDataEditor ? $t('common.closeEditor') : $t('assetDetail.editData')}
                                >
                                    <Pencil size={16} />
                                </button>
                            {/if}
                            <!-- colour: closest role, to review: the aesthetics toggle's active emerald is a mode accent, not a success; success roles keep the hue (alternative: bg-lf-selected text-lf-link) -->
                            <button
                                data-testid="asset-detail-aesthetics-toggle"
                                class="p-1.5 rounded-lg transition-colors {showAesthetics ? 'bg-lf-success-soft text-lf-success ring-1 ring-lf-success-line' : 'bg-lf-card/80 text-lf-muted hover:bg-lf-hover hover:text-lf-secondary'}"
                                onclick={() => (showAesthetics = !showAesthetics)}
                                title={$t('common.aesthetics')}
                            >
                                <Settings size={16} />
                            </button>
                        </div>

                        <PriceChartFull
                            data={activeChartData}
                            currency={primaryMode === 'price' ? displayCurrency : ''}
                            mainSeriesLabel={primaryMode === 'price' ? (assetInfo?.display_name ?? '') : $t('signals.riskRollingReturn.name')}
                            chartHeight="400px"
                            overlaySignals={primaryMode === 'price' ? allOverlaySignals : calendarOverlaySignals}
                            eventMarkers={primaryMode === 'price' ? chartEventMarkers : []}
                            overlaySignalInfoMap={primaryMode === 'price' ? overlaySignalInfoMap : calendarOverlaySignalInfoMap}
                            mainIconUrl={assetInfo?.icon_url}
                            mainAssetType={assetInfo?.asset_type}
                            colorByBaseline={settings.colorByBaseline}
                            areaFill={settings.areaFill}
                            showGridLines={settings.gridLines}
                            showGradient={settings.staleGradient}
                            yAxisMode={activePrimaryAxisScale.mode}
                            yAxisMin={activePrimaryAxisScale.min}
                            yAxisMax={activePrimaryAxisScale.max}
                            secondaryAxisScales={settings.axisScales.secondary}
                            measureMode={primaryMode === 'price' ? measureMode : calendarMeasureMode}
                            onMeasureClick={handleMeasureClick}
                            onMeasureHover={(date, value) => activeMeasurePanel()?.updatePendingEnd(date, value)}
                            hideToolbar={true}
                            externalChartType={primaryMode === 'price' ? chartType : 'line'}
                            onChartTypeChange={(t) => {
                                chartType = t;
                            }}
                            externalViewMode={primaryMode === 'price' ? viewMode : 'absolute'}
                            onViewModeChange={(mode) => {
                                viewMode = mode;
                                persistPrimaryView();
                            }}
                            editMode={primaryMode === 'price' && showDataEditor}
                            disableCandlestick={primaryMode === 'calendar-return'}
                            valueUnit={primaryMode === 'calendar-return' ? 'percentage' : 'price'}
                            hideViewModeToggle={primaryMode === 'calendar-return'}
                            showMainDelta={primaryMode === 'price'}
                            mainPointContext={calendarPointContext}
                            staleLabel={$t('chart.tooltip.stale')}
                            fxStaleLabel={$t('chart.tooltip.fxStale')}
                            displayCurrency={primaryMode === 'price' && displayCurrency !== assetInfo?.currency ? displayCurrency : undefined}
                            displayCurrencyFlag={primaryMode === 'price' && displayCurrency !== assetInfo?.currency ? getCurrencyInfo(displayCurrency).flag_emoji : undefined}
                            mainCurrency={primaryMode === 'price' ? (assetInfo?.currency ?? undefined) : undefined}
                            mainCurrencyFlag={primaryMode === 'price' && assetInfo?.currency ? getCurrencyInfo(assetInfo.currency).flag_emoji : undefined}
                            onDblClick={(date) => {
                                if (primaryMode === 'price' && showDataEditor && assetDataEditorRef) {
                                    assetDataEditorRef.scrollToDate(date, 'prices');
                                }
                            }}
                            onEventDblClick={(date) => {
                                if (primaryMode === 'price' && showDataEditor && assetDataEditorRef) {
                                    assetDataEditorRef.scrollToDate(date, 'events');
                                }
                            }}
                        />
                    </div>
                    {#if primaryMode === 'calendar-return' && calendarReturnView.problem}
                        <p class="mt-2 text-center text-xs {calendarPrimaryProblemSeverity === 'error' ? 'text-lf-danger' : 'text-lf-warning'}" data-testid="asset-calendar-primary-problem" data-problem-code={calendarReturnView.problem.code} data-problem-status={calendarReturnView.problem.status}>
                            {calendarPrimaryProblemMessage}
                        </p>
                    {:else if primaryMode === 'calendar-return' && calendarReturnView.state === 'partial'}
                        <p class="mt-2 text-center text-xs text-lf-warning" data-testid="asset-calendar-return-partial">
                            {$t('chartSettings.signalProblems.partialResult')}
                        </p>
                    {/if}
                {/if}
            {:else}
                <div class="mb-3 flex flex-wrap items-center justify-between gap-2" data-testid="asset-chart-primary-controls">
                    <AssetChartModeToggle {primaryMode} onselect={setPrimaryMode} />
                </div>
                <div class="h-96 flex items-center justify-center">
                    <div class="text-center">
                        {#if isManualOnly}
                            <p class="text-lf-muted mb-3">{$t('assetDetail.noDataManual')}</p>
                            <div class="flex items-center gap-2 justify-center">
                                <button
                                    class="px-4 py-2 text-sm bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors"
                                    onclick={() => {
                                        savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                        showAesthetics = false;
                                        showMeasures = false;
                                        showSignals = false;
                                        showDataEditor = true;
                                    }}
                                >
                                    <Pencil class="inline mr-1" size={14} />
                                    {$t('fxDetail.insertManually')}
                                </button>
                                <button
                                    class="px-4 py-2 text-sm bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    disabled={!assetInfo}
                                    onclick={() => {
                                        editDataForModal = buildEditData();
                                        editModalOpen = true;
                                    }}
                                >
                                    {$t('common.edit')}
                                </button>
                            </div>
                        {:else if isParametric}
                            <p class="text-lf-muted mb-3">{$t('assetDetail.noDataScheduled')}</p>
                            <button
                                class="px-4 py-2 text-sm bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                disabled={!assetInfo}
                                onclick={() => {
                                    editDataForModal = buildEditData();
                                    editModalOpen = true;
                                }}>{$t('common.edit')}</button
                            >
                        {:else}
                            <p class="text-lf-muted mb-3">{$t('assetDetail.noData')}</p>
                            <div class="flex items-center gap-2 justify-center">
                                <button class="px-4 py-2 text-sm bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors" onclick={handleSync} disabled={syncing}>{syncing ? $t('common.syncing') : $t('assetDetail.syncPrices')}</button>
                                <!-- I-bis #6 — Add manually: open data editor pre-filtered on Prices tab -->
                                <button
                                    class="px-4 py-2 text-sm bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-colors"
                                    data-testid="asset-detail-add-prices-manually"
                                    onclick={() => {
                                        savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                        showAesthetics = false;
                                        showMeasures = false;
                                        showSignals = false;
                                        showDataEditor = true;
                                    }}
                                >
                                    <Pencil class="inline mr-1" size={14} />
                                    {$t('assetDetail.addPricesManually')}
                                </button>
                            </div>
                        {/if}
                    </div>
                </div>
            {/if}
        </div>

        <!-- ======================================================================= -->
        <!-- Data Editor Placeholder -->
        <!-- ======================================================================= -->
        {#if showDataEditor}
            <div data-testid="asset-detail-editor-panel" class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-warning-line {primaryMode === 'price' ? '' : 'hidden'}" aria-hidden={primaryMode !== 'price'} inert={primaryMode !== 'price'}>
                <div class="flex items-center justify-between px-4 py-3 border-b border-lf-warning-line bg-lf-warning-soft rounded-t-xl">
                    <span class="flex items-center gap-2 text-sm font-medium text-lf-warning-on-soft">
                        <Pencil size={15} />
                        {$t('assetDetail.editData')}
                    </span>
                    <button
                        class="text-lf-muted hover:text-lf-secondary transition-colors"
                        onclick={() => {
                            showDataEditor = false;
                            pendingPreviewSignal = null;
                            if (savedPanelStates) {
                                showAesthetics = savedPanelStates.aesthetics;
                                showMeasures = savedPanelStates.measures;
                                showSignals = savedPanelStates.signals;
                                savedPanelStates = null;
                            }
                        }}
                        title={$t('common.closeEditor')}
                        data-testid="asset-detail-editor-close">✕</button
                    >
                </div>
                <p class="px-4 pt-2 text-xs text-lf-warning-on-soft/70">
                    💡 {pageLayoutMode === 'oneColumn' ? $t('dataEditor.editorTipMobile') : $t('dataEditor.editorTipDesktop')}
                </p>
                <div class="px-4 py-4">
                    <AssetDataEditorSection
                        bind:this={assetDataEditorRef}
                        assetId={data.assetId}
                        currency={assetInfo?.currency}
                        {chartData}
                        {events}
                        bind:saving={savingEdit}
                        bind:dirtyCount={editorDirtyCount}
                        onsave={async (expandedRange) => {
                            showDataEditor = false;
                            pendingPreviewSignal = null;
                            if (savedPanelStates) {
                                showAesthetics = savedPanelStates.aesthetics;
                                showMeasures = savedPanelStates.measures;
                                showSignals = savedPanelStates.signals;
                                savedPanelStates = null;
                            }
                            if (expandedRange) {
                                dateStart = expandedRange.start;
                                dateEnd = expandedRange.end;
                                displayDateStart = isMaxPending ? 'min' : dateStart;
                            }
                            await pageBusy.track('asset-reload', () => handleRefresh());
                        }}
                        oncancel={() => {
                            showDataEditor = false;
                            pendingPreviewSignal = null;
                            if (savedPanelStates) {
                                showAesthetics = savedPanelStates.aesthetics;
                                showMeasures = savedPanelStates.measures;
                                showSignals = savedPanelStates.signals;
                                savedPanelStates = null;
                            }
                        }}
                        onpendingchange={(sig) => (pendingPreviewSignal = sig)}
                    />
                </div>
            </div>
        {/if}

        <!-- ======================================================================= -->
        <!-- Foldable Panel: Measures -->
        <!-- ======================================================================= -->
        <AssetDetailMeasuresSection
            mode={primaryMode}
            open={activeMeasuresOpen()}
            measureModeActive={activeMeasureMode()}
            canAddMeasure={activeChartData.filter((point) => !point.missing).length >= 2}
            ontoggle={() => setActiveMeasuresOpen(!activeMeasuresOpen())}
            onaddmeasure={() => {
                setActiveMeasuresOpen(true);
                activeMeasurePanel()?.addMeasureFromChartData();
            }}
        >
            <div class={primaryMode === 'price' && showMeasures ? 'px-4 pb-4 border-t border-lf-subtle pt-3' : 'hidden'} data-testid="asset-detail-measures-panel" aria-hidden={primaryMode !== 'price' || !showMeasures} inert={primaryMode !== 'price' || !showMeasures}>
                <MeasurePanel
                    bind:this={measurePanel}
                    chartData={lineData}
                    onmeasuremodechange={(active) => (measureMode = active)}
                    onmeasureschange={(m) => (measureSignals = m)}
                    {overlaySignals}
                    {mainSignalInfo}
                    {viewMode}
                    displayCurrency={displayCurrency !== assetInfo?.currency ? displayCurrency : undefined}
                    displayCurrencyFlag={displayCurrency !== assetInfo?.currency ? getCurrencyInfo(displayCurrency).flag_emoji : undefined}
                    mainCurrency={assetInfo?.currency ?? undefined}
                    mainCurrencyFlag={assetInfo?.currency ? getCurrencyInfo(assetInfo.currency).flag_emoji : undefined}
                    preserveUnavailableMeasures={true}
                />
            </div>
            <div
                class={primaryMode === 'calendar-return' && showCalendarMeasures ? 'px-4 pb-4 border-t border-lf-subtle pt-3' : 'hidden'}
                data-testid="asset-detail-calendar-measures-panel"
                aria-hidden={primaryMode !== 'calendar-return' || !showCalendarMeasures}
                inert={primaryMode !== 'calendar-return' || !showCalendarMeasures}
            >
                <MeasurePanel
                    bind:this={calendarMeasurePanel}
                    chartData={calendarReturnView.points}
                    onmeasuremodechange={(active) => (calendarMeasureMode = active)}
                    onmeasureschange={(measures) => (calendarMeasureSignals = measures)}
                    overlaySignals={calendarComparisonSignals}
                    mainSignalInfo={calendarMainSignalInfo}
                    viewMode="absolute"
                    measurementUnit="percentage-points"
                    preserveUnavailableMeasures={true}
                    storageKeyPrefix="asset-calendar-measure-summary"
                />
            </div>
        </AssetDetailMeasuresSection>

        <!-- ======================================================================= -->
        <!-- Foldable Panel: Metadata & Classification -->
        <!-- ======================================================================= -->
        {#if assetInfo}
            <AssetDetailMetadataPanel
                bind:open={showMetadata}
                {shortDescription}
                {providerExternalUrl}
                {classificationLoaded}
                {sectorDistribution}
                {geographicDistribution}
                {identifiersList}
                {providerAssignment}
                {providerIconUrl}
                {assignmentProviderName}
                onedit={() => {
                    editDataForModal = buildEditData();
                    editModalOpen = true;
                }}
            />
        {/if}
    {:else if assetInfo && displayCurrency}
        <div data-testid="asset-detail-risk-panel">
            <AssetRiskScenariosView
                assetId={data.assetId}
                {dateStart}
                {dateEnd}
                targetCurrency={displayCurrency}
                assetClass={assetInfo.asset_type}
                sectorExposure={sectorDistribution}
                geographyExposure={geographicDistribution}
                {rollingRiskSignals}
                refreshVersion={riskRefreshVersion}
                onconfigure={openSignalConfiguration}
                onsynced={handlePageSyncComplete}
            />
        </div>
    {:else}
        <div class="flex min-h-48 items-center justify-center" data-testid="asset-detail-risk-loading">
            <RefreshCw size={24} class="animate-spin text-lf-link" />
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- AssetModal for editing -->
    <!-- ======================================================================= -->
    {#if assetInfo}
        <AssetModal bind:open={editModalOpen} editMode={true} editData={editDataForModal} onupdated={() => void pageBusy.track('asset-reload', () => handleAssetUpdated())} onclose={() => (editModalOpen = false)} />

        <!-- FX Pair Add Modal (opened from FX warning or banner) -->
        {@const fxCreateDefaults = fxPairCreateDefaults(fxPairCreateSlug, assetInfo.currency, displayCurrency)}
        {@const fxCreationCallbacks = createFxPairCallbacks(data.assetId, !!fxPairCreateSlug, assetInfo.currency)}
        <FxPairAddModal bind:open={showFxPairAddModal} readonlyBase={!fxPairCreateSlug} initialBase={fxCreateDefaults.base} initialQuote={fxCreateDefaults.quote} oncreated={fxCreationCallbacks.oncreated} onsynced={fxCreationCallbacks.onsynced} onclose={fxCreationCallbacks.onclose} />
    {/if}

    <!-- Page Sync Modal (sync all assets + FX pairs) -->
    {#if assetInfo}
        <PageSyncModal
            bind:open={showPageSyncModal}
            dateStart={syncDateStart}
            {dateEnd}
            assets={syncAllAssets}
            fxPairs={syncAllFxPairs}
            assetsWithDataInRange={syncAssetsWithData}
            fxPairsWithDataInRange={syncFxPairsWithData}
            onsynced={handlePageSyncComplete}
            onclose={() => (showPageSyncModal = false)}
        />
    {/if}
</div>
