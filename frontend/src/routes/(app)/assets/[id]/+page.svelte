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
    import {onDestroy, onMount, tick} from 'svelte';
    import {page} from '$app/stores';
    import {goto} from '$app/navigation';
    import {debug, isDebugEnabled} from '$lib/debug';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {axiosInstance, schemas, zodiosApi} from '$lib/api';
    import {goBack} from '$lib/stores/app/navigationStore';
    import {ArrowLeft, ChartLine, ChevronDown, ExternalLink, Info, Pencil, Percent, RefreshCw, RotateCw, Ruler, Settings, TrendingUp, X} from 'lucide-svelte';
    import AssetDataEditorSection from '$lib/components/assets/AssetDataEditorSection.svelte';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import PriceChartFull from '$lib/components/charts/PriceChartFull.svelte';
    import type {EventMarker} from '$lib/components/charts/PriceChartFull.svelte';
    import ChartAestheticsSection from '$lib/components/charts/ChartAestheticsSection.svelte';
    import ChartSignalsSection from '$lib/components/charts/ChartSignalsSection.svelte';
    import type {SignalDataSummary} from '$lib/components/charts/ChartSignalsSection.svelte';
    import MeasurePanel from '$lib/components/charts/MeasurePanel.svelte';
    import AllocationPieChart from '$lib/components/charts/AllocationPieChart.svelte';
    import {getSectorEmoji} from '$lib/stores/reference/sectorStore';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import AssetModal from '$lib/components/assets/AssetModal.svelte';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import AssetPriceSummary from '$lib/components/assets/AssetPriceSummary.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import PageSyncModal from '$lib/components/ui/modals/PageSyncModal.svelte';
    import AssetRiskScenariosView from '$lib/components/risk/AssetRiskScenariosView.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import CompactDurationBadge from '$lib/components/ui/date/CompactDurationBadge.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {
        backendSignalSchemas,
        buildBackendSignalRequestPlan,
        getSignalProblem,
        getSignalProblemSeverity,
        getLocalSignalDefinitions,
        mapSignalInstanceResults,
        renderBackendSignalResult,
        signalFromConfig,
        SignalResultState,
        type BackendSignalResult,
        type RenderedSignal,
        type SignalConfig,
        type SignalDefinition,
        type SignalInstanceResult,
        type SignalProblem,
    } from '$lib/charts/signals';
    import {DEFAULT_AXIS_SCALE, normalizeAxisScaleSettings, setPairSettings, getSettingsForPair, type AxisScaleSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {invalidateFxRoutes} from '$lib/stores/reference/fxRoutesStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import type {ViewMode, ChartType} from '$lib/components/charts/ChartToolbar.svelte';
    import type {LayoutMode} from '$lib/utils/layout/responsiveLayout.svelte';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import {displayFxRate, ensureFxRangeLoaded, getFxStore} from '$lib/stores/fxStoreRegistry';
    import {getAssetPriceStore, invalidateAssetPriceStore, apiPricesToAssetPricePoints} from '$lib/stores/assetPriceStoreRegistry';
    import {getAssetTypeIconUrl, buildIdentifiersList} from '$lib/utils/assetTypes';
    import {ensureAssetProvidersCached, getAssetProviderIconUrl, getAssetProviderName, isParametricProvider, assetProvidersVersion} from '$lib/utils/providerHelpers';
    import {replaceHistoryDateRange} from '$lib/utils/url/dateRangeUrl';
    import {buildTabUrl, getResolvedTabParam} from '$lib/utils/url/tabUrl';
    import type {AssetDetail, ProviderAssignmentFlat} from '$lib/types';
    import type {SignalLabelInfo} from '$lib/charts/signalLabel';
    import {buildOverlaySignalInfoMap} from '$lib/charts/signalLabel';
    import {applyComparisonAssetsData, buildComparisonSyncRange, clearComparisonAssetsData, collectConfiguredComparisonFxSlugs, COMPARISON_ASSET_RUNTIME_PARAM_KEYS, getComparisonEventFxDependency, loadComparisonAssetsData} from '$lib/charts/loadComparisonData';
    import {getStart, getEnd, setDateRange, resolveDateSentinel, isMaxSentinel} from '$lib/stores/dateRangeStore.svelte';
    import {fetchCurrentPrices, computeDirection} from '$lib/services/livePriceService';
    import type {LivePriceDirection} from '$lib/services/livePriceService';
    import {buildAssetSyncToast, buildFxSyncToast} from '$lib/utils/sync/syncToastHelpers';
    import {COLORS} from '$lib/components/charts/lineChartHelpers';
    import {collectConfigurableSecondaryAxes} from '$lib/components/charts/chartCoreHelpers';
    import {percentageAxisLabel, priceAxisLabel, secondaryAxisLabel} from '$lib/components/charts/axisLabelHelpers';
    import {formatSignalProblem} from '$lib/components/charts/chartSignalsHelpers';
    import {CALENDAR_RETURN_INSTANCE_ID, CALENDAR_RETURN_SIGNAL_CODE, extractCalendarReturnView, extractCalendarReturnViewsByAsset, isCalendarReturnSignalResult, type CalendarReturnView, type CalendarReturnViewState} from '$lib/components/charts/priceChartHelpers';
    import {CALENDAR_RETURN_PRESETS, DEFAULT_CALENDAR_RETURN_WINDOW, calendarReturnRangeDays, calendarReturnWindowDays, type CalendarReturnPresetKey, type CalendarReturnWindowSelection, type CalendarReturnWindowUnit} from '$lib/components/charts/calendarReturnWindow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import AiExportMenu from '$lib/features/ai-export/AiExportMenu.svelte';
    import {prepareAiExport, type PreparedAiExport} from '$lib/features/ai-export/aiExportClipboard';
    import type {AiExportOptionsSelection} from '$lib/features/ai-export/aiExportOptions';
    import {aiExportCatalogLoader, emptyAiExportCompatibility, type AiExportCatalogCompatibilityResult} from '$lib/features/ai-export/catalog/compatibility';
    import {buildAiExportMenuLabels, getAiExportErrorMessage, getAiExportSuccessMessages} from '$lib/features/ai-export/ui';
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
        {id: 'overview', label: $t('risk.assetDetail.overviewTab'), testId: 'asset-detail-tab-overview'},
        {id: 'risk', label: $t('risk.assetDetail.riskScenariosTab'), testId: 'asset-detail-tab-risk', guideAnchor: 'asset.detail.risk'},
    ]);

    $effect(() => {
        activeTab = getResolvedTabParam($page.url.searchParams, ASSET_DETAIL_TAB_IDS, 'overview');
    });

    // =========================================================================
    // State
    // =========================================================================

    let assetInfo = $state<AssetDetail | null>(null);
    let providerAssignment = $state<ProviderAssignmentFlat | null>(null);
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

    /** Reactively resolved error message — translates i18n keys when language changes */
    let errorMessage = $derived.by(() => {
        if (!error) return null;
        return error.startsWith('_i18n:') ? $t(error.slice(6)) : error;
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
    type AssetChartPrimaryMode = 'price' | 'calendar-return';
    let primaryMode = $state<AssetChartPrimaryMode>('price');
    let calendarWindowSelection: CalendarReturnWindowSelection = $state({
        ...DEFAULT_CALENDAR_RETURN_WINDOW,
    });
    let calendarCustomAmount = $state(DEFAULT_CALENDAR_RETURN_WINDOW.customAmount);
    let calendarCustomUnit: CalendarReturnWindowUnit = $state(DEFAULT_CALENDAR_RETURN_WINDOW.customUnit);
    let calendarCustomEditing = $state(false);
    let calendarWindowHydratedScope: string | null = null;
    let calendarWindowDays = $derived(calendarReturnWindowDays(calendarWindowSelection) ?? 30);
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
        calendarWindowSelection = {
            ...settings.calendarReturnWindow,
        };
        calendarCustomAmount = settings.calendarReturnWindow.customAmount;
        calendarCustomUnit = settings.calendarReturnWindow.customUnit;
        calendarWindowHydratedScope = scope;
    });
    let calendarDurationOptions = $derived([
        {
            value: 'weeks',
            label: $t('datePicker.granularity.weeksShort').toUpperCase(),
        },
        {
            value: 'months',
            label: $t('datePicker.granularity.monthsShort').toUpperCase(),
        },
        {
            value: 'years',
            label: $t('datePicker.granularity.yearsShort').toUpperCase(),
        },
    ]);

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
    let allAssets: Array<{id: number; display_name: string; icon_url?: string | null; asset_type?: string | null; currency?: string}> = $state([]);

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

    // Live current price (from provider, only when dateEnd = today)
    let currentLivePrice = $state<number | null>(null);
    /** True when live price conversion to displayCurrency failed (pair exists but rate unavailable) */
    let livePriceConversionFailed = $state(false);

    // --- Live price direction flash --------------------------------------------
    // Tracks whether the latest polled tick moved the price up/down vs the
    // PREVIOUS poll (not vs the day's open) so AssetPriceSummary can flash the
    // price text. Mirrors the assets list page's use of computeDirection, but
    // compares the asset's NATIVE-currency value (not the possibly FX-converted
    // display value) so switching displayCurrency never fabricates a fake
    // up/down tick on its own.
    /** Direction of the latest live-price tick — drives the transient flash animation. Resets to 'neutral' once the flash decays. */
    let livePriceDirection = $state<LivePriceDirection>('neutral');
    /** Increments on every non-neutral tick so the flash element can be re-keyed (forces the CSS animation to restart even for two consecutive same-direction ticks). */
    let livePriceFlashToken = $state(0);
    /** Previous poll's native-currency value — plain (non-reactive) bookkeeping var, not rendered directly. */
    let previousNativeLivePrice: number | null = null;
    /** Pending "decay back to neutral" timer for the current flash. */
    let livePriceFlashTimeoutId: ReturnType<typeof setTimeout> | null = null;
    /** How long the flash stays lit before decaying to the resting colour — kept in sync with the CSS animation duration in app.css (.lf-price-flash-*). */
    const LIVE_PRICE_FLASH_DECAY_MS = 1300;

    // =========================================================================
    // Derived
    // =========================================================================

    /** True when the chart end date is today (or later) → show live price from provider */
    let isHeadToday = $derived(dateEnd >= new Date().toISOString().slice(0, 10));

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

    function emptyCalendarReturnView(state: CalendarReturnViewState = 'idle'): CalendarReturnView {
        return {state, points: [], contextByDate: new Map(), problem: null};
    }

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
        if (mode === 'calendar-return') {
            void loadChartData(false);
        } else {
            calendarCustomEditing = false;
            void maybeLoadComparison();
            const hasBackendSignals = signals.some((config) => signalDefinitionsByType.get(config.signalType)?.source === 'backend');
            if (hasBackendSignals) void loadChartData(false);
        }
    }

    function persistCalendarWindow(selection: CalendarReturnWindowSelection): void {
        calendarWindowSelection = selection;
        setPairSettings(`asset-${data.assetId}`, {
            ...settings,
            calendarReturnWindow: {...selection},
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
            void loadChartData(false);
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
            void loadChartData(false);
        }
    }

    // #R3-4 — derive "parametric" status from provider kind (instead of hardcoded code),
    // so the detail page picks the "Regenerate" label for any parametric_generation provider.
    // Depends on assetProvidersVersion to re-evaluate after the providers cache is loaded.
    let isParametric = $derived.by(() => {
        void $assetProvidersVersion;
        return isParametricProvider(providerAssignment?.provider_code);
    });
    let isManualOnly = $derived(!providerAssignment);
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

    /** Effective last price: live from provider when head = today, otherwise last chart close */
    let lastPrice = $derived.by(() => {
        if (isHeadToday && currentLivePrice != null) return currentLivePrice;
        if (chartData.length === 0) return null;
        const last = chartData[chartData.length - 1];
        return last?.close != null ? Number(last.close) : null;
    });

    let deltaPercent = $derived.by(() => {
        if (chartData.length < 2 || lastPrice == null) return null;
        const first = Number(chartData[0].close ?? 0);
        if (first === 0) return null;
        return ((lastPrice - first) / first) * 100;
    });

    let deltaAbs = $derived.by(() => {
        if (chartData.length < 2 || lastPrice == null) return null;
        const first = Number(chartData[0].close ?? 0);
        if (first === 0) return null;
        return lastPrice - first;
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

    /**
     * All FX pairs required by the page (main + comparison signals).
     * Each entry has slug, label, forAsset, and status.
     */
    interface RequiredFxPairInfo {
        slug: string;
        label: string;
        forAsset: string;
        forAssetIconUrl?: string | null;
        forAssetType?: string | null;
        status: 'ok' | 'missing' | 'no-data' | 'partial-gap';
        firstDate?: string;
    }

    let requiredFxPairs: RequiredFxPairInfo[] = $derived.by(() => {
        if (!displayCurrency) return [];
        const pairs: RequiredFxPairInfo[] = [];
        const seenSlugs = new Set<string>();

        // Helper to compute canonical slug
        const toSlug = (a: string, b: string) => {
            const [lo, hi] = a < b ? [a, b] : [b, a];
            return `${lo}-${hi}`;
        };

        // Main asset FX pair
        if (assetInfo && displayCurrency !== assetInfo.currency) {
            const slug = toSlug(assetInfo.currency, displayCurrency);
            const missing = !allConfiguredFxSlugs.includes(slug);
            let status: RequiredFxPairInfo['status'];
            if (missing) {
                status = 'missing';
            } else if (!fxFirstConvertedDate && chartData.length > 0) {
                status = 'no-data';
            } else if (hasFxDataGap && fxFirstConvertedDate) {
                status = 'partial-gap';
            } else {
                status = 'ok';
            }
            pairs.push({
                slug,
                label: slug.replace('-', '/'),
                forAsset: assetInfo.display_name,
                forAssetIconUrl: assetInfo.icon_url,
                forAssetType: assetInfo.asset_type,
                status,
                firstDate: fxFirstConvertedDate ?? undefined,
            });
            seenSlugs.add(slug);
        }

        // Comparison signal FX pairs
        for (const cfg of signals) {
            if (cfg.signalType !== 'asset-comparison') continue;
            const targetId = Number(cfg.params.assetId);
            if (!targetId || targetId === data.assetId) continue;
            const targetAsset = allAssets.find((a) => a.id === targetId);
            if (!targetAsset?.currency || targetAsset.currency === displayCurrency) continue;
            const slug = toSlug(targetAsset.currency, displayCurrency);
            if (seenSlugs.has(slug)) continue;
            seenSlugs.add(slug);

            const missing = !allConfiguredFxSlugs.includes(slug);
            let status: RequiredFxPairInfo['status'];
            if (missing) {
                status = 'missing';
            } else if (primaryMode === 'calendar-return' && calendarSnapshotIsCurrent) {
                status = calendarComparisonFxFailures.has(targetId) || calendarComparisonProblems.get(targetId)?.code === 'fx_conversion_unavailable' ? 'no-data' : 'ok';
            } else {
                const convFailed = Boolean(cfg.params._conversionFailed);
                const hasData = Boolean(cfg.params._resolvedData);
                status = convFailed || !hasData ? 'no-data' : 'ok';
            }
            pairs.push({
                slug,
                label: slug.replace('-', '/'),
                forAsset: targetAsset.display_name,
                forAssetIconUrl: targetAsset.icon_url,
                forAssetType: targetAsset.asset_type,
                status,
            });
        }

        // E.8 — Event currencies: if any event is in a currency ≠ displayCurrency,
        // add its pair to the required list. This surfaces the same banner + CTA
        // already used for prices (asset native + comparison signals), without
        // duplicating detection code. `forAsset` uses an i18n-aware "for events"
        // label so the user understands the context.
        if (displayCurrency) {
            const eventSources: Array<{
                values: any[];
                forAsset: string;
                forAssetIconUrl?: string | null;
                forAssetType?: string | null;
            }> = [
                {
                    values: events,
                    forAsset: $t('events.fxBannerContext') ?? 'for dividend/cash events',
                },
                ...[...comparisonEvents].map(([assetId, values]) => {
                    const asset = allAssets.find((candidate) => candidate.id === assetId);
                    return {
                        values,
                        forAsset: asset?.display_name ?? `Asset #${assetId}`,
                        forAssetIconUrl: asset?.icon_url,
                        forAssetType: asset?.asset_type,
                    };
                }),
            ];
            for (const source of eventSources) {
                for (const event of source.values) {
                    const dependency = getComparisonEventFxDependency(event, displayCurrency);
                    if (!dependency) continue;
                    const slug = toSlug(dependency.sourceCurrency, displayCurrency);
                    const missing = !allConfiguredFxSlugs.includes(slug);
                    const existing = pairs.find((pair) => pair.slug === slug);
                    if (existing) {
                        if (missing) existing.status = 'missing';
                        else if (dependency.failed && existing.status === 'ok') existing.status = 'no-data';
                        continue;
                    }
                    seenSlugs.add(slug);
                    pairs.push({
                        slug,
                        label: slug.replace('-', '/'),
                        forAsset: source.forAsset,
                        forAssetIconUrl: source.forAssetIconUrl,
                        forAssetType: source.forAssetType,
                        status: missing ? 'missing' : dependency.failed ? 'no-data' : 'ok',
                    });
                }
            }
        }

        return pairs;
    });

    /** Build DataQualityIssue[] from page state for unified banner rendering */
    let assetDetailIssues: DataQualityIssue[] = $derived.by(() => {
        const issues: DataQualityIssue[] = [];

        // Archived banner
        if (assetInfo && assetInfo.active === false) {
            issues.push({
                domain: 'asset',
                code: 'ASSET_ARCHIVED',
                severity: 'warning',
                message_i18n_key: 'dataQuality.archivedAsset',
            });
        }

        // Range starts before first data
        if (rangeStartsBeforeData && !loading && !error && assetInfo) {
            issues.push({
                domain: 'asset',
                code: 'RANGE_BEFORE_FIRST_DATA',
                severity: 'info',
                message_i18n_key: 'dataQuality.rangeBeforeData',
                message_params: {date: firstDataDate ?? ''},
            });
        }

        // FX pair issues
        if (!loading && !error) {
            for (const pair of requiredFxPairs.filter((p) => p.status !== 'ok')) {
                const parts = pair.slug.split('-');
                if (pair.status === 'missing') {
                    issues.push({
                        domain: 'forex',
                        code: 'FX_PAIR_MISSING',
                        severity: 'warning',
                        group_key: pair.slug,
                        message_i18n_key: 'dataQuality.fxPairMissing',
                        affected_fx_pairs: [pair.slug],
                        affected_asset_names: [pair.forAsset],
                        cta_action: 'add_fx_pair',
                        cta_target: pair.slug,
                    });
                } else if (pair.status === 'no-data') {
                    issues.push({
                        domain: 'forex',
                        code: 'FX_PAIR_NO_DATA',
                        severity: 'warning',
                        group_key: pair.slug,
                        message_i18n_key: 'dataQuality.fxPairNoData',
                        affected_fx_pairs: [pair.slug],
                        affected_asset_names: [pair.forAsset],
                        cta_action: 'navigate_fx',
                        cta_target: pair.slug,
                    });
                } else if (pair.status === 'partial-gap') {
                    issues.push({
                        domain: 'forex',
                        code: 'FX_PAIR_PARTIAL_GAP',
                        severity: 'info',
                        group_key: pair.slug,
                        message_i18n_key: 'dataQuality.fxPairPartialGap',
                        message_params: {date: pair.firstDate ?? ''},
                        affected_fx_pairs: [pair.slug],
                        affected_asset_names: [pair.forAsset],
                        cta_action: 'navigate_fx',
                        cta_target: pair.slug,
                    });
                }
            }
        }

        return issues;
    });

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

    let backendOverlaySignals: RenderedSignal[] = $derived.by(() => {
        const rendered: RenderedSignal[] = [];
        for (const item of signalInstanceResults) {
            if (item.source !== 'backend' || !item.result) continue;
            const currentConfig = signals.find((config) => config.id === item.config.id) ?? item.config;
            const definition = signalDefinitionsByType.get(currentConfig.signalType);
            if (!definition || definition.source !== 'backend') {
                console.error(`Missing backend signal definition for '${currentConfig.signalType}'`);
                continue;
            }
            const outcome = renderBackendSignalResult(item.result, currentConfig, {
                baseData: lineData,
                viewMode,
                definition,
                translate: (key) => $t(key),
            });
            rendered.push(...outcome.signals);
        }
        return rendered;
    });

    let rollingRiskSignals = $derived.by(() => {
        const riskConfigIds = new Set(signals.filter((config) => signalDefinitionsByType.get(config.signalType)?.indicatorGroup === 'risk').map((config) => config.id));
        return backendOverlaySignals.filter((signal) => riskConfigIds.has(signal.id.split(':')[0]));
    });

    // Overlay signals
    let overlaySignals: RenderedSignal[] = $derived.by(() => {
        void overlayDataVersion;
        const rendered: RenderedSignal[] = [];
        for (const cfg of signals) {
            const definition = signalDefinitionsByType.get(cfg.signalType);
            if (!definition || definition.source === 'backend') continue;
            const instance = signalFromConfig(cfg);
            if (!instance) continue;

            if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (!pairSlug) continue;
                try {
                    const store = getFxStore(pairSlug);
                    const storeData = store.getAllSorted();
                    if (storeData.length === 0) continue;
                    instance.params._resolvedData = storeData.map((d) => {
                        const rate = displayFxRate(d.rate, false);
                        return {date: d.date, value: rate ?? 0, missing: rate === null};
                    });
                } catch {
                    continue;
                }
            }

            if (cfg.signalType === 'asset-comparison') {
                const targetId = Number(cfg.params.assetId);
                if (!targetId || targetId === data.assetId) continue;
                const targetAsset = allAssets.find((a) => a.id === targetId);
                instance.params._assetDisplayName = targetAsset?.display_name ?? `Asset #${targetId}`;
                if (!instance.params._resolvedData) continue;
            }

            const results = instance.renderMulti(lineData, viewMode);
            for (const result of results) {
                if (result.data.length > 0) rendered.push(result);
            }
        }
        return [...rendered, ...backendOverlaySignals];
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
                label: target?.display_name ?? String(config.params._assetDisplayName ?? `Asset #${assetId}`),
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
            const label = targetAsset?.display_name ?? `Asset #${aid}`;
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
                    pointCount: rendered.reduce((maximum, signal) => Math.max(maximum, signal.data.length), 0),
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

    function parseBackendSignalResults(value: unknown): BackendSignalResult[] {
        if (!Array.isArray(value)) return [];
        return value.map((item) => backendSignalSchemas.result.parse(item));
    }

    type AssetPriceBulkQueryBody = Parameters<typeof zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post>[0];

    async function queryAssetPricesBulkWithSignalIsolation(body: AssetPriceBulkQueryBody): Promise<{items: Record<string, unknown>[]}> {
        const response = await axiosInstance.post<unknown>('/api/v1/assets/prices/query', body);
        if (!isRecord(response.data)) {
            throw new Error('Invalid Asset price query response');
        }
        if (response.data.items === undefined) return {items: []};
        if (!Array.isArray(response.data.items)) {
            throw new Error('Invalid Asset price query items');
        }

        return {
            items: response.data.items.map((rawItem, index) => {
                if (!isRecord(rawItem)) {
                    throw new Error(`Invalid Asset price query item at index ${index}`);
                }
                const rawSignals = rawItem.signals;
                if (rawSignals !== undefined && !Array.isArray(rawSignals)) {
                    throw new Error(`Invalid Asset signal collection at item index ${index}`);
                }
                const validSignals = (rawSignals ?? []).flatMap((signal) => {
                    const parsed = backendSignalSchemas.result.safeParse(signal);
                    return parsed.success ? [parsed.data] : [];
                });
                const parsedItem = schemas.FAPriceQueryResult.safeParse({
                    ...rawItem,
                    signals: validSignals,
                });
                if (!parsedItem.success) {
                    throw new Error(`Invalid Asset price query item at index ${index}`);
                }
                return {
                    ...parsedItem.data,
                    signals: rawSignals ?? [],
                };
            }),
        };
    }

    function isRecord(value: unknown): value is Record<string, unknown> {
        return typeof value === 'object' && value !== null && !Array.isArray(value);
    }

    function priceConversionErrorFromItem(item: Record<string, unknown> | undefined): string | undefined {
        const errors = item && Array.isArray(item.errors) ? item.errors.filter((error): error is string => typeof error === 'string') : [];
        const firstError = errors[0];
        return firstError && !/\bfor event on\b/i.test(firstError) && /\b(?:fx|conversion|currenc)/i.test(firstError) ? firstError : undefined;
    }

    function calendarComparisonProblemsFromResponse(responseItems: unknown[], configs: SignalConfig[], assetIds: number[], views: Map<number, CalendarReturnView>): Map<number, SignalProblem> {
        const configByAssetId = new Map<number, SignalConfig>();
        for (const config of configs) {
            if (config.signalType !== 'asset-comparison') continue;
            const assetId = Number(config.params.assetId);
            if (Number.isSafeInteger(assetId) && assetId > 0) configByAssetId.set(assetId, config);
        }
        const problems = new Map<number, SignalProblem>();

        for (const assetId of assetIds) {
            const config = configByAssetId.get(assetId);
            if (!config) continue;
            const item = responseItems.find((candidate): candidate is Record<string, unknown> => isRecord(candidate) && candidate.asset_id === assetId);
            const rawResults: unknown[] = item && Array.isArray(item.signals) ? item.signals : [];
            const rawResult = rawResults.find((candidate) => isCalendarReturnSignalResult(candidate, CALENDAR_RETURN_INSTANCE_ID));
            let instance: SignalInstanceResult;

            if (!rawResult) {
                instance = {
                    config,
                    source: 'backend',
                    status: 'missing',
                    result: null,
                    error: `Calendar Return result for asset ${assetId} is missing`,
                };
            } else {
                const parsed = backendSignalSchemas.result.safeParse(rawResult);
                if (!parsed.success) {
                    instance = {
                        config,
                        source: 'backend',
                        status: 'missing',
                        result: null,
                        error: `Calendar Return result for asset ${assetId} is invalid`,
                    };
                } else {
                    const result = parsed.data;
                    const strictView = views.get(assetId);
                    if (strictView?.state === 'error' && result.status !== 'failed') {
                        instance = {
                            config,
                            source: 'backend',
                            status: 'missing',
                            result: null,
                            error: `Calendar Return result for asset ${assetId} is invalid`,
                        };
                    } else {
                        const resultError = Array.isArray(result.error) ? result.error.find((error) => error !== null)?.message : result.error?.message;
                        instance = {
                            config,
                            source: 'backend',
                            status: result.status,
                            result,
                            error: resultError ?? null,
                        };
                    }
                }
            }

            let problem = getSignalProblem(instance);
            const priceConversionError = priceConversionErrorFromItem(item);
            const targetAsset = allAssets.find((asset) => asset.id === assetId);
            if (problem?.code === 'missing_input_fields' && priceConversionError && targetAsset?.currency && displayCurrency && targetAsset.currency !== displayCurrency) {
                problem = {
                    ...problem,
                    code: 'fx_conversion_unavailable',
                    message: priceConversionError,
                };
            }
            if (problem) problems.set(assetId, problem);
        }
        return problems;
    }

    function calendarComparisonFxFailuresFromResponse(responseItems: unknown[], assetIds: number[], previousFailures: ReadonlySet<number>): Set<number> {
        const failedAssetIds = new Set<number>();
        for (const assetId of assetIds) {
            const item = responseItems.find((candidate): candidate is Record<string, unknown> => isRecord(candidate) && candidate.asset_id === assetId);
            if (!item) {
                if (previousFailures.has(assetId)) failedAssetIds.add(assetId);
                continue;
            }
            if (priceConversionErrorFromItem(item)) failedAssetIds.add(assetId);
        }
        return failedAssetIds;
    }

    function preserveFactualCalendarPeersForCurrentUnavailable(previousViews: ReadonlyMap<number, CalendarReturnView>, nextViews: ReadonlyMap<number, CalendarReturnView>, responseItems: unknown[], assetIds: number[]): Map<number, CalendarReturnView> {
        const merged = new Map(nextViews);
        for (const assetId of assetIds) {
            const itemPresent = responseItems.some((candidate) => isRecord(candidate) && candidate.asset_id === assetId);
            const next = nextViews.get(assetId);
            const previous = previousViews.get(assetId);
            const previousHasFacts = previous && ['ready', 'partial'].includes(previous.state) && previous.points.some((point) => !point.missing);
            if (itemPresent && next?.state === 'unavailable' && previousHasFacts) {
                merged.set(assetId, previous);
            }
        }
        return merged;
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

    const comparisonRuntimeParamKeys = new Set<string>(COMPARISON_ASSET_RUNTIME_PARAM_KEYS);

    function signalDataContextFingerprint(configs: SignalConfig[]): string {
        return JSON.stringify(
            configs
                .map((config) => ({
                    id: config.id,
                    signalType: config.signalType,
                    params: Object.fromEntries(
                        Object.entries(config.params)
                            .filter(([key]) => !comparisonRuntimeParamKeys.has(key))
                            .sort(([left], [right]) => left.localeCompare(right)),
                    ),
                }))
                .sort((left, right) => left.id.localeCompare(right.id)),
        );
    }

    function comparisonAssetIds(configs: SignalConfig[]): number[] {
        return [
            ...new Set(
                configs
                    .filter((config) => config.signalType === 'asset-comparison')
                    .map((config) => Number(config.params.assetId))
                    .filter((assetId) => Number.isSafeInteger(assetId) && assetId > 0 && assetId !== data.assetId),
            ),
        ].sort((left, right) => left - right);
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
        await loadAssetSignalDefinitions(true);
        await loadChartData(false);
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
        assetInfo = null;
        providerAssignment = null;
        chartData = [];
        events = [];
        signalInstanceResults = [];
        signalRequestFailed = false;
        primaryMode = 'price';
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
        currentLivePrice = null;
        livePriceConversionFailed = false;
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
    }

    // Track previous asset id for same-route navigation detection (plain var — not $state)
    let _prevAssetId: number | undefined;

    onMount(async () => {
        _prevAssetId = data.assetId;
        await reloadPage();
        void loadAssetAiExportCompatibility();
        if (assetInfo) onboardingGuide.maybeStartContextual('asset_detail_guide');
    });

    // Re-load everything when navigating to a different asset (same route pattern)
    $effect(() => {
        const newId = data.assetId;
        if (_prevAssetId !== undefined && newId !== _prevAssetId) {
            _prevAssetId = newId;
            void reloadPage().then(() => {
                if (assetInfo) onboardingGuide.maybeStartContextual('asset_detail_guide');
            });
        }
    });

    // Live current price polling — only when chart head date includes today
    // Re-runs when displayCurrency or assetInfo changes (to reconvert)
    $effect(() => {
        const id = assetInfo?.id;
        const nativeCurrency = assetInfo?.currency;
        const targetCurrency = displayCurrency;
        const fxMissing = fxConversionMissing;
        if (!isHeadToday || !id) {
            currentLivePrice = null;
            livePriceConversionFailed = false;
            // Polling context changed (asset switched, or range no longer heads
            // "today") — drop the direction/flash state so it can't carry over
            // and compare against a stale/unrelated previous value.
            previousNativeLivePrice = null;
            livePriceDirection = 'neutral';
            if (livePriceFlashTimeoutId) {
                clearTimeout(livePriceFlashTimeoutId);
                livePriceFlashTimeoutId = null;
            }
            return;
        }
        // Fetch immediately, then poll every 30s
        _fetchLivePrice(id, nativeCurrency ?? '', targetCurrency, fxMissing);
        const timer = setInterval(() => _fetchLivePrice(id, nativeCurrency ?? '', targetCurrency, fxMissing), 30_000);
        return () => {
            clearInterval(timer);
            if (livePriceFlashTimeoutId) {
                clearTimeout(livePriceFlashTimeoutId);
                livePriceFlashTimeoutId = null;
            }
        };
    });

    async function _fetchLivePrice(assetId: number, nativeCurrency: string, targetCurrency: string, fxMissing: boolean) {
        try {
            const results = await fetchCurrentPrices([assetId]);
            if (results.length === 0 || results[0].value == null) return;
            const nativeValue = results[0].value;

            // Direction compares this tick's NATIVE value to the previous poll's
            // NATIVE value (never the day's open, never the display-converted
            // value) — reuses computeDirection from livePriceService.ts (same
            // helper the assets list page uses) so a displayCurrency switch can
            // never fabricate a false up/down tick. First poll after (re)mount
            // has no previous value → computeDirection returns 'neutral'.
            const direction = computeDirection(nativeValue, previousNativeLivePrice);
            previousNativeLivePrice = nativeValue;
            if (direction !== 'neutral') {
                livePriceDirection = direction;
                livePriceFlashToken++;
                if (livePriceFlashTimeoutId) clearTimeout(livePriceFlashTimeoutId);
                livePriceFlashTimeoutId = setTimeout(() => {
                    livePriceDirection = 'neutral';
                    livePriceFlashTimeoutId = null;
                }, LIVE_PRICE_FLASH_DECAY_MS);
            }

            // No conversion needed
            if (!targetCurrency || !nativeCurrency || targetCurrency === nativeCurrency || fxMissing) {
                currentLivePrice = nativeValue;
                livePriceConversionFailed = false;
                return;
            }

            // Convert via FX API
            try {
                const today = new Date().toISOString().slice(0, 10);
                const convResponse = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post([
                    {
                        from_amount: {code: nativeCurrency, amount: String(nativeValue)},
                        to: targetCurrency,
                        date_range: {start: today, end: today},
                    },
                ]);
                const convResults = (convResponse as any)?.results ?? [];
                if (convResults.length > 0 && convResults[0].to_amount?.amount != null) {
                    currentLivePrice = parseFloat(convResults[0].to_amount.amount);
                    livePriceConversionFailed = false;
                } else {
                    // Conversion returned no results — fallback to native
                    currentLivePrice = nativeValue;
                    livePriceConversionFailed = true;
                }
            } catch {
                // FX conversion failed — fallback to native price
                currentLivePrice = nativeValue;
                livePriceConversionFailed = true;
            }
        } catch (e: any) {
            // Non-blocking: keep last known value or chart fallback
        }
    }

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
            loadChartData().then(() => maybeLoadComparison());
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
                error = `Asset #${data.assetId} not found`;
            }
        } catch (e: any) {
            console.error('Failed to load asset info:', e);
            error = e?.message || 'Failed to load asset info';
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

    async function loadChartData(force = false, requestedSignalConfigs: SignalConfig[] = signals, propagateError = false) {
        const requestedAssetId = data.assetId;
        const sessionGeneration = getClientSessionGeneration();
        const current = () => pageAlive && data.assetId === requestedAssetId && isClientSessionCurrent(sessionGeneration);
        if (!current()) return;
        const requestedStart = dateStart;
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

        // Cache-first: check if the price store already covers this range
        if (!force && effectiveCurrency) {
            const store = getAssetPriceStore(data.assetId, effectiveCurrency);
            const gaps = store.getMissingIntervals(dateStart, dateEnd);
            if (gaps.length === 0) {
                // Cache hit — update chart data without loading spinner
                const cached = store.getRange(dateStart, dateEnd).data;
                chartData = cached.map((p) => ({
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
                if (chartData.length === 0 && !error) {
                    error = '_i18n:assetDetail.noData';
                } else {
                    error = null;
                }
                resolveMaxStartFromChartData();
                pricesFromCache = true;
                // No early return here: events travel in the same response as prices,
                // so a price-cache hit would otherwise leave `events` empty and make
                // them vanish from the chart and the data editor. Fall through with
                // include_price:false to fetch just the events (a tiny payload).
            }
        }

        // Cache miss fetches prices + signals; cache hit requests events (+ signals) only.
        loading = !pricesFromCache;
        error = null;
        signalRequestFailed = false;
        signalsLoading = requestPlan.requests.length > 0 || calendarComparisonAssetIds.length > 0;
        if (requestedCalendarFingerprint !== null) {
            calendarSnapshotFingerprint = requestedCalendarFingerprint;
            if (retainCurrentCalendarDiagnostics) {
                calendarReturnView = {
                    ...calendarReturnView,
                    state: 'loading',
                };
            } else {
                calendarReturnView = emptyCalendarReturnView('loading');
                calendarComparisonViews = new Map();
                calendarComparisonProblems = new Map();
                calendarComparisonFxFailures = new Set();
                comparisonEvents = new Map();
            }
        }
        try {
            const response = await queryAssetPricesBulkWithSignalIsolation([
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
            ]);
            if (!dataRequestIsCurrent()) return;
            const responseItems: any[] = Array.isArray((response as any)?.items) ? (response as any).items : [];
            const result = responseItems.find((item) => item?.asset_id === requestedAssetId);
            if (result) {
                if (!pricesFromCache) {
                    chartData = result.prices ?? [];
                }
                events = result.events ?? [];
                const rawSignalResults: unknown[] = Array.isArray(result.signals) ? result.signals : [];
                if (wantsCalendarReturn && calendarRequestIsCurrent() && requestedCalendarWindow === calendarWindowDays) {
                    calendarReturnView = extractCalendarReturnView(rawSignalResults, CALENDAR_RETURN_INSTANCE_ID);
                    if (calendarComparisonsAreCurrent()) {
                        const nextComparisonViews = extractCalendarReturnViewsByAsset(responseItems, calendarComparisonAssetIds, CALENDAR_RETURN_INSTANCE_ID);
                        calendarComparisonViews = retainCurrentCalendarDiagnostics ? preserveFactualCalendarPeersForCurrentUnavailable(calendarComparisonViews, nextComparisonViews, responseItems, calendarComparisonAssetIds) : nextComparisonViews;
                        calendarComparisonProblems = calendarComparisonProblemsFromResponse(responseItems, requestedSignalConfigs, calendarComparisonAssetIds, calendarComparisonViews);
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
                    applyBackendSignalResults(backendSignalConfigs, requestVersion, parseBackendSignalResults(rawSignalResults.filter((item) => !isCalendarReturnSignalResult(item, CALENDAR_RETURN_INSTANCE_ID))));
                }
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
                error = '_i18n:assetDetail.noData';
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
            if (chartData.length === 0) error = e?.message || 'Failed to load prices';
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
        const requestedAssetId = data.assetId;
        const sessionGeneration = getClientSessionGeneration();
        const requestedFingerprint = priceComparisonLoadFingerprint(requestedSignalConfigs);
        if (!force && comparisonInFlight?.fingerprint === requestedFingerprint) {
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
        const promise = (async () => {
            try {
                const loaded = await loadComparisonAssetsData(requestedAssetIds, {start: dateStart, end: dateEnd}, allAssets, requestedAssetId, displayCurrency || undefined);
                if (!current()) return;
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

    // =========================================================================
    // I-bis #24 — Live current-price polling (contextual auto-refresh)
    // =========================================================================
    //
    // Why: clicking Sync already does a targeted merge (decision matrix in
    // handleSyncAsset), but the user wants updates to appear *without* any
    // manual click. This effect polls ``/assets/prices/current`` once per
    // minute and, when the polled close differs from the in-memory chart,
    // merges today's point in-place — zero flicker, signals auto-recompute.
    //
    // IMPORTANT (why we do NOT fall back to a silent ``/sync`` call):
    // the ``/current`` endpoint is NOT read-only — its F.2/F.3 side-effect
    // already persists today's OHLC to the DB. If we chained a silent
    // ``/sync`` after ``/current``, the sync's ``_count_actual_price_changes``
    // would see the DB already up-to-date and return ``changed_points=None``,
    // forcing the FE into the full-reload fallback (flicker) — exactly the
    // UX regression reported during retest. The polled item carries all we
    // need (close + currency + as_of_date) to update today's point.
    //
    // Constraints:
    // • Only polls when the asset has a provider assigned (otherwise the
    //   endpoint would just echo back the DB's last known value — useless).
    // • Skips polling when the browser tab is hidden (saves provider quota
    //   and rate limit budget).
    // • No polling during a full chart reload (``loading === true``) to
    //   avoid interleaving fetches on the same chartData array.
    // • Point merge is idempotent: if close == last known close for the
    //   same as_of_date, we skip the state update (no render, no network).
    // • Converted-currency chart (displayCurrency ≠ asset currency): the
    //   polled close is in the asset's native currency and would flash
    //   wrong values inside the FX-converted series — in that case we do
    //   a silent full reload (single loadChartData) as the fallback.
    // =========================================================================

    const CURRENT_PRICE_POLL_INTERVAL_MS = 60_000; // 1 minute — conservative
    let livePollTimerId: ReturnType<typeof setInterval> | null = null;

    async function pollCurrentPriceOnce() {
        // Guards: skip if tab hidden, no provider, or a full reload is in
        // progress. Also skip if the asset changed between schedule and
        // tick (route navigation races).
        if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
        if (!providerAssignment?.provider_code) return;
        if (loading || (primaryMode === 'calendar-return' && calendarReturnView.state === 'loading')) return;
        const assetIdAtTick = data.assetId;

        try {
            const response = await zodiosApi.get_current_prices_bulk_api_v1_assets_prices_current_post([assetIdAtTick]);
            // Route changed mid-request: drop the result.
            if (assetIdAtTick !== data.assetId) return;

            const item: any = (response as any)?.results?.[0];
            if (!item || item.error || item.value == null || !item.as_of_date) return;

            const newClose = Number(item.value);
            if (!Number.isFinite(newClose)) return;

            // Idempotent guard: compare with the point for the same date.
            const existingIdx = chartData.findIndex((p: any) => p.date === item.as_of_date);
            if (existingIdx >= 0) {
                const existingClose = Number((chartData[existingIdx] as any).close);
                if (Number.isFinite(existingClose) && Math.abs(existingClose - newClose) < 1e-9) return;
            }

            // Converted-currency chart: the polled close is in the asset's
            // native currency and would flash wrong numbers mid-series. A
            // single silent full reload is the pragmatic fallback here.
            const isConvertedChart = !!(displayCurrency && assetInfo?.currency && displayCurrency !== assetInfo.currency);
            if (isConvertedChart || primaryMode === 'calendar-return') {
                invalidateAssetPriceStore(data.assetId);
                await loadChartData(true);
                return;
            }

            // Point-level merge: update today's close + currency + as_of_date
            // via mergeChartPointsIncremental. Enriched fields on the existing
            // point (original_close, backward_fill_info, …) are preserved by
            // the shallow-merge rule (the polled item does not carry them,
            // so they are not overwritten). Signal derivatives ($derived
            // from chartData) recompute automatically.
            const polledPoint: any = {
                date: item.as_of_date,
                close: newClose,
                currency: item.currency,
            };
            chartData = mergeChartPointsIncremental(chartData, [polledPoint]);
        } catch {
            // Silent: polling is best-effort. Next tick will retry.
        }
    }

    $effect(() => {
        // Track provider assignment + asset id so the timer restarts on
        // route change or when a provider is (un)assigned.
        const hasProvider = !!providerAssignment?.provider_code;
        const assetId = data.assetId;
        if (!hasProvider || !assetId) return;

        livePollTimerId = setInterval(pollCurrentPriceOnce, CURRENT_PRICE_POLL_INTERVAL_MS);
        // Kick an initial poll after a short delay so the first tick feels
        // contextual (but not simultaneous with the page's own initial
        // loadChartData).
        const warmupId = setTimeout(pollCurrentPriceOnce, 5_000);

        return () => {
            if (livePollTimerId) clearInterval(livePollTimerId);
            clearTimeout(warmupId);
            livePollTimerId = null;
        };
    });

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

    function handleSync() {
        showPageSyncModal = true;
    }

    async function handlePageSyncComplete({accepted}: {accepted: boolean} = {accepted: true}) {
        if (accepted && primaryMode === 'calendar-return') {
            comparisonRequestGeneration += 1;
            comparisonInFlight = null;
            comparisonAppliedFingerprint = null;
            comparisonEvents = clearComparisonAssetsData(signals.filter((signal) => signal.signalType === 'asset-comparison'));
            overlayDataVersion++;
        }
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
            const newQuote = assetCurrency === base ? quote : base;
            if (newQuote !== assetCurrency) {
                displayCurrency = newQuote;
            }
        }
        await loadFxPairSlugs(true);
        if (current()) await handleRefresh();
    }

    async function handleFxPairCreationSynced(detail: FxPairSyncCompleteDetail, assetIdAtCreation: number) {
        const current = () => pageAlive && data.assetId === assetIdAtCreation && isClientSessionCurrent(detail.sessionGeneration);
        if (!current()) return;
        await loadFxPairSlugs(true);
        if (current()) await handleRefresh(true);
    }

    function createFxPairCallbacks(assetIdAtCreation: number, wasForComparison: boolean, assetCurrency: string) {
        return {
            oncreated: (detail: FxPairCreatedDetail) => handleFxPairCreated(detail, assetIdAtCreation, wasForComparison, assetCurrency),
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
        await loadChartData();
        await maybeLoadComparison();
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
        setPairSettings(`asset-${data.assetId}`, {...settings, signals: JSON.parse(JSON.stringify(newSignals))});
        if (primaryMode === 'price' && shouldReloadPriceComparisons) {
            void maybeLoadComparison(false, newSignals);
        }
        if ((primaryMode === 'calendar-return' && shouldReloadCalendarComparisons) || (primaryMode === 'price' && shouldReloadBackend)) {
            void loadChartData(false, newSignals);
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

    /**
     * I-bis #24 helper — merge ``changed_points`` from a sync response into
     * the current ``chartData`` array by date. New points are appended,
     * existing points by date are shallow-merged (so OHLC fields update
     * without losing enriched fields like ``original_close`` that may have
     * been set by ``loadChartData``). Result is sorted by date ascending.
     *
     * NOTE: the merge only runs when the chart is showing the asset's native
     * currency (no target_currency conversion), because the delta from the
     * sync endpoint carries raw DB values without FX applied.
     */
    function mergeChartPointsIncremental<T extends {date: string}>(existing: T[], delta: T[]): T[] {
        const byDate = new Map<string, T>(existing.map((p) => [p.date, p]));
        for (const np of delta) {
            const prev = byDate.get(np.date);
            byDate.set(np.date, prev ? ({...prev, ...np} as T) : np);
        }
        return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
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

<div class="space-y-4" data-testid="asset-detail-page" aria-busy={loading || (primaryMode === 'calendar-return' && calendarReturnView.state === 'loading')} data-busy={loading || (primaryMode === 'calendar-return' && calendarReturnView.state === 'loading') ? 'true' : 'false'}>
    <!-- ======================================================================= -->
    <!-- Header: asset info + back button -->
    <!-- ======================================================================= -->
    <div class="flex items-center gap-3" data-testid="asset-detail-header" use:guideAnchor={'asset.detail.header'}>
        <button class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors" data-testid="asset-detail-back-btn" onclick={() => goBack('/assets')} title={$t('assetDetail.backToList')}>
            <ArrowLeft size={20} />
        </button>

        {#if assetInfo}
            <div class="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3" data-testid="asset-detail-info">
                <div class="flex items-center gap-3">
                    <AssetIcon iconUrl={assetInfo.icon_url} assetType={assetInfo.asset_type} altText={assetInfo.display_name} size="md" />
                    <span class="w-2.5 h-2.5 rounded-full shrink-0 {assetInfo.active !== false ? 'bg-green-500' : 'bg-red-400'}" data-testid="asset-status-dot" title={assetInfo.active !== false ? $t('common.active') : $t('assets.status.archived')}></span>
                    <h2 use:scrollOnOverflow class="{overflowScrollTextClass} text-xl font-bold text-gray-800 dark:text-gray-100 max-w-[15ch] sm:max-w-[30ch] lg:max-w-none" title={assetInfo.display_name}>{assetInfo.display_name}</h2>
                </div>

                <div class="flex items-center gap-2 flex-wrap ml-0 sm:ml-0">
                    {#if assetInfo.asset_type}
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300">
                            <img src={getAssetTypeIconUrl(assetInfo.asset_type)} alt="" class="w-3.5 h-3.5" />
                            {$t(`assets.types.${assetInfo.asset_type}`)}
                        </span>
                    {/if}

                    <span class="text-lg emoji-flag">{currencyFlag}</span>
                    <span class="text-sm font-mono text-gray-500 dark:text-gray-400">{assetInfo.currency}</span>
                    {#if (assetInfo.tx_count ?? 0) > 0}
                        <a href={buildTransactionsFiltersUrl({asset_id: assetInfo.id})} data-testid="asset-detail-transactions-link" class="text-xs font-medium text-blue-600 hover:underline dark:text-blue-400">
                            {$t('transactions.title')} ({assetInfo.tx_count})
                        </a>
                    {/if}

                    {#if assetInfo.provider_code}
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
                            {#if providerIconUrl}
                                <img src={providerIconUrl} alt="" class="w-3.5 h-3.5 rounded-sm object-contain" />
                            {/if}
                            {getAssetProviderName(assetInfo.provider_code)}
                        </span>
                    {:else}
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"> ✏️ Manual </span>
                    {/if}

                    {#if userUrl || providerExternalUrl}
                        <a href={userUrl || providerExternalUrl} target="_blank" rel="noopener noreferrer" class="inline-flex items-center p-1 rounded text-gray-400 hover:text-libre-green transition-colors" title={userUrl || providerExternalUrl}>
                            <ExternalLink size={14} />
                        </a>
                    {/if}
                </div>
            </div>
        {:else if loading}
            <div class="h-8 w-48 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
        {/if}
    </div>

    <!-- Error banner (not data-quality — dismissible runtime error) -->
    {#if error}
        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-700 dark:text-amber-400 flex items-center gap-2">
            <span>⚠️</span> <span>{errorMessage}</span>
            <button class="ml-auto text-xs px-2 py-1 bg-amber-100 dark:bg-amber-900/40 rounded hover:bg-amber-200" onclick={() => (error = null)}>{$t('common.close')}</button>
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
        thresholds={{oneRow: 1215, denseRow: 780, stackFilters: 400, oneColumn: 360, labelHideActions: 230, labelHideTabs: 370}}
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
                    {livePriceConversionFailed}
                    {livePriceDirection}
                    {livePriceFlashToken}
                    fxPairUrl={mainFxPairUrl}
                    onCreateForex={() => (showFxPairAddModal = true)}
                />
            {/if}
        {/snippet}

        {#snippet actions({showActionLabels})}
            <AiExportMenu
                domain="asset"
                compatibility={assetAiExportCompatibility}
                memoryKey={`asset:${data.assetId}`}
                defaultSelectionId="asset.market_analysis"
                disabled={assetAiExportCatalogLoading || assetAiExportCatalogFailed || !assetInfo}
                labels={assetAiExportLabels}
                showLabel={showActionLabels}
                onprepare={handleAssetAiExport}
                oncopied={handleAssetAiExportCopied}
                onerror={(error) => toasts.error(getAiExportErrorMessage($t, error))}
            />
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="asset-detail-edit-btn"
                disabled={!assetInfo || !classificationLoaded}
                onclick={() => {
                    editDataForModal = buildEditData();
                    editModalOpen = true;
                }}
            >
                <Pencil size={14} />
                {#if showActionLabels}<span>{$t('common.edit')}</span>{/if}
            </button>
            {#if syncBlocked}
                <Tooltip text={syncDisabledReason} position="top" maxWidth="320px" interactiveChild>
                    <button
                        class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors opacity-50 cursor-not-allowed"
                        data-testid="asset-detail-sync-btn"
                        disabled={syncing || syncBlocked}
                        onclick={handleSync}
                    >
                        <RotateCw class={syncing ? 'animate-spin' : ''} size={14} />
                        {#if showActionLabels}<span class="line-through">{syncing ? $t('common.syncing') : isParametric ? $t('assetDetail.recalculate') : $t('common.sync')}</span>{/if}
                    </button>
                </Tooltip>
            {:else}
                <button
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    data-testid="asset-detail-sync-btn"
                    disabled={syncing || syncBlocked}
                    onclick={handleSync}
                >
                    <RotateCw class={syncing ? 'animate-spin' : ''} size={14} />
                    {#if showActionLabels}<span>{syncing ? $t('common.syncing') : isParametric ? $t('assetDetail.recalculate') : $t('common.sync')}</span>{/if}
                </button>
            {/if}
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                data-testid="asset-detail-refresh-btn"
                disabled={loading}
                onclick={() => handleRefresh()}
            >
                <RefreshCw class={loading ? 'animate-spin' : ''} size={14} />
                {#if showActionLabels}<span>{$t('common.refresh')}</span>{/if}
            </button>
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
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
            <div class="relative">
                <button type="button" class="absolute inset-0 z-0 w-full rounded-xl hover:bg-gray-50 dark:hover:bg-slate-700/50" data-testid="asset-detail-signals-toggle" aria-expanded={showSignals} aria-label={$t('common.signals')} onclick={() => (showSignals = !showSignals)}></button>
                <div class="relative z-10 pointer-events-none w-full flex items-center gap-1 px-2 py-1.5" data-testid="asset-detail-signals-header">
                    <span class="flex items-center gap-2 px-2 py-1 text-sm font-medium text-gray-700 dark:text-gray-200">
                        <TrendingUp class="text-blue-500" size={15} />
                        {$t('common.signals')}
                    </span>
                    <div class="flex-1"></div>
                    <span class="flex items-center px-1 py-1 text-gray-700 dark:text-gray-200" data-testid="asset-detail-signals-chevron">
                        <ChevronDown class="transition-transform {showSignals ? 'rotate-180' : ''}" size={15} />
                    </span>
                </div>
            </div>
            {#if showSignals}
                <div data-testid="asset-detail-signals-panel" class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3">
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
                </div>
            {/if}
        </div>

        <!-- ======================================================================= -->
        <!-- Chart with left toolbar -->
        <!-- ======================================================================= -->
        <div
            class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4"
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
                        <RefreshCw size={24} class="animate-spin text-libre-green mx-auto mb-2" />
                        <p class="text-sm text-gray-500 dark:text-gray-400">{$t('assetDetail.loadingPrices')}</p>
                    </div>
                </div>
            {:else if (primaryMode === 'price' && lineData.length > 0) || primaryMode === 'calendar-return'}
                <div class="mb-3 flex flex-wrap items-center justify-between gap-2" data-testid="asset-chart-primary-controls">
                    <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600 text-xs font-medium">
                        <button
                            class="inline-flex items-center gap-1.5 px-3 py-1 transition-colors {primaryMode === 'price' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                            data-testid="asset-chart-primary-price"
                            aria-pressed={primaryMode === 'price'}
                            onclick={() => setPrimaryMode('price')}
                        >
                            <ChartLine size={14} data-testid="asset-chart-primary-price-icon" />
                            {$t('assetDetail.pricesTab')}
                        </button>
                        <button
                            class="inline-flex items-center gap-1.5 px-3 py-1 border-l border-gray-200 dark:border-slate-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed {primaryMode === 'calendar-return'
                                ? 'bg-libre-green text-white'
                                : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                            data-testid="asset-chart-primary-calendar-return"
                            aria-pressed={primaryMode === 'calendar-return'}
                            onclick={() => setPrimaryMode('calendar-return')}
                        >
                            <Percent size={14} data-testid="asset-chart-primary-calendar-return-icon" />
                            {$t('signals.riskRollingReturn.name')}
                        </button>
                    </div>
                    {#if primaryMode === 'calendar-return'}
                        <div class="flex flex-wrap items-center gap-1.5" data-testid="asset-calendar-window-controls">
                            <span class="text-xs text-gray-500 dark:text-gray-400">{$t('chartSettings.params.window')}</span>
                            {#each CALENDAR_RETURN_PRESETS as preset}
                                <button
                                    class="min-w-10 px-2 py-1 rounded-md border text-xs font-medium transition-colors {calendarWindowSelection.kind === 'preset' && calendarWindowSelection.preset === preset.key
                                        ? 'border-libre-green bg-libre-green text-white'
                                        : 'border-gray-200 dark:border-slate-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                                    data-testid={`asset-calendar-window-${preset.key}`}
                                    aria-pressed={calendarWindowSelection.kind === 'preset' && calendarWindowSelection.preset === preset.key}
                                    title={`${$t('chartSettings.params.window')}: ${preset.windowDays} ${$t('chartSettings.units.days')}`}
                                    onclick={() => setCalendarPreset(preset.key)}
                                >
                                    {preset.label}
                                </button>
                            {/each}
                            <CompactDurationBadge
                                bind:amount={calendarCustomAmount}
                                bind:unit={calendarCustomUnit}
                                bind:editing={calendarCustomEditing}
                                active={calendarWindowSelection.kind === 'custom'}
                                options={calendarDurationOptions}
                                customLabel={$t('common.custom')}
                                min={1}
                                buttonTestId="asset-calendar-window-custom"
                                amountTestId="asset-calendar-custom-amount"
                                unitTestId="asset-calendar-custom-unit"
                                isAllowed={(amount, unit) =>
                                    unit !== 'days' &&
                                    calendarReturnWindowDays({
                                        ...calendarWindowSelection,
                                        kind: 'custom',
                                        customAmount: amount,
                                        customUnit: unit,
                                    }) !== null}
                                onapply={(amount, unit) => {
                                    if (unit !== 'days') {
                                        setCalendarCustom(amount, unit);
                                    }
                                }}
                            />
                        </div>
                    {/if}
                </div>

                <!-- Aesthetics panel (ABOVE chart, shown only when gear is active) -->
                {#if showAesthetics}
                    <div data-testid="asset-detail-aesthetics-panel" class="mb-3 pb-3 border-b border-gray-100 dark:border-slate-700 relative">
                        <button class="absolute top-0 right-0 p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-600 transition-colors" onclick={() => (showAesthetics = false)} title={$t('common.close')}>
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
                        <RefreshCw size={24} class="animate-spin text-libre-green" />
                    </div>
                {:else if primaryMode === 'calendar-return' && calendarChartState === 'unavailable'}
                    <div class="h-96 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400" data-testid="asset-calendar-return-unavailable">
                        <span data-testid="asset-calendar-primary-problem" data-problem-code={calendarReturnView.problem?.code} data-problem-status={calendarReturnView.problem?.status}>
                            {calendarPrimaryProblemMessage ?? $t('chartSettings.signalProblems.unavailable')}
                        </span>
                    </div>
                {:else if primaryMode === 'calendar-return' && calendarChartState === 'error'}
                    <div class="h-96 flex items-center justify-center text-sm text-red-600 dark:text-red-400" data-testid="asset-calendar-return-error">
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
                                class="p-1.5 rounded-lg transition-colors {activeMeasureMode()
                                    ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 ring-1 ring-violet-300 dark:ring-violet-700'
                                    : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
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
                                <button
                                    data-testid="asset-detail-editdata-btn"
                                    use:guideAnchor={'asset.detail.editor'}
                                    class="p-1.5 rounded-lg transition-colors {showDataEditor
                                        ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 ring-1 ring-amber-300 dark:ring-amber-700'
                                        : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
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
                            <button
                                data-testid="asset-detail-aesthetics-toggle"
                                class="p-1.5 rounded-lg transition-colors {showAesthetics
                                    ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-300 dark:ring-emerald-700'
                                    : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
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
                        <p
                            class="mt-2 text-center text-xs {calendarPrimaryProblemSeverity === 'error' ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'}"
                            data-testid="asset-calendar-primary-problem"
                            data-problem-code={calendarReturnView.problem.code}
                            data-problem-status={calendarReturnView.problem.status}
                        >
                            {calendarPrimaryProblemMessage}
                        </p>
                    {:else if primaryMode === 'calendar-return' && calendarReturnView.state === 'partial'}
                        <p class="mt-2 text-center text-xs text-amber-600 dark:text-amber-400" data-testid="asset-calendar-return-partial">
                            {$t('chartSettings.signalProblems.partialResult')}
                        </p>
                    {/if}
                {/if}
            {:else}
                <div class="mb-3 flex flex-wrap items-center justify-between gap-2" data-testid="asset-chart-primary-controls">
                    <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600 text-xs font-medium">
                        <button class="inline-flex items-center gap-1.5 px-3 py-1 transition-colors bg-libre-green text-white" data-testid="asset-chart-primary-price" aria-pressed="true" onclick={() => setPrimaryMode('price')}>
                            <ChartLine size={14} data-testid="asset-chart-primary-price-icon" />
                            {$t('assetDetail.pricesTab')}
                        </button>
                        <button
                            class="inline-flex items-center gap-1.5 px-3 py-1 border-l border-gray-200 dark:border-slate-600 transition-colors bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700"
                            data-testid="asset-chart-primary-calendar-return"
                            aria-pressed="false"
                            onclick={() => setPrimaryMode('calendar-return')}
                        >
                            <Percent size={14} data-testid="asset-chart-primary-calendar-return-icon" />
                            {$t('signals.riskRollingReturn.name')}
                        </button>
                    </div>
                </div>
                <div class="h-96 flex items-center justify-center">
                    <div class="text-center">
                        {#if isManualOnly}
                            <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('assetDetail.noDataManual')}</p>
                            <div class="flex items-center gap-2 justify-center">
                                <button
                                    class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
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
                                    class="px-4 py-2 text-sm bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
                            <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('assetDetail.noDataScheduled')}</p>
                            <button
                                class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                disabled={!assetInfo}
                                onclick={() => {
                                    editDataForModal = buildEditData();
                                    editModalOpen = true;
                                }}>{$t('common.edit')}</button
                            >
                        {:else}
                            <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('assetDetail.noData')}</p>
                            <div class="flex items-center gap-2 justify-center">
                                <button class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors" onclick={handleSync} disabled={syncing}>{syncing ? $t('common.syncing') : $t('assetDetail.syncPrices')}</button>
                                <!-- I-bis #6 — Add manually: open data editor pre-filtered on Prices tab -->
                                <button
                                    class="px-4 py-2 text-sm bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-500 transition-colors"
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
            <div data-testid="asset-detail-editor-panel" class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-amber-200 dark:border-amber-800 {primaryMode === 'price' ? '' : 'hidden'}" aria-hidden={primaryMode !== 'price'} inert={primaryMode !== 'price'}>
                <div class="flex items-center justify-between px-4 py-3 border-b border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-yellow-900/30 rounded-t-xl">
                    <span class="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400">
                        <Pencil size={15} />
                        {$t('assetDetail.editData')}
                    </span>
                    <button
                        class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
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
                        title={$t('common.closeEditor')}>✕</button
                    >
                </div>
                <p class="px-4 pt-2 text-xs text-amber-700/70 dark:text-amber-400/70">
                    💡 {pageLayoutMode === 'oneColumn' ? $t('assetDetail.editorTipMobile') : $t('assetDetail.editorTipDesktop')}
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
                            await handleRefresh();
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
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700" data-testid="asset-detail-measures-section" data-mode={primaryMode}>
            <div
                class="flex items-center justify-between px-4 py-2.5 cursor-pointer select-none hover:bg-gray-50 dark:hover:bg-slate-750 transition-colors rounded-t-xl"
                role="button"
                tabindex="0"
                data-testid="asset-detail-measures-toggle"
                onclick={() => setActiveMeasuresOpen(!activeMeasuresOpen())}
                onkeydown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setActiveMeasuresOpen(!activeMeasuresOpen());
                    }
                }}
            >
                <div class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200">
                    <Ruler class="text-violet-500" size={15} />
                    {$t('common.measures')}
                    {#if activeMeasureMode()}
                        <span class="text-[10px] px-1.5 py-0.5 bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 rounded-full">{$t('measure.active')}</span>
                    {/if}
                </div>
                <div class="flex items-center gap-1.5">
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md
                                   bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400
                                   hover:bg-violet-100 dark:hover:bg-violet-900/50
                                   transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={activeChartData.filter((point) => !point.missing).length < 2}
                        data-testid="asset-detail-add-measure-btn"
                        onclick={(e) => {
                            e.stopPropagation();
                            setActiveMeasuresOpen(true);
                            activeMeasurePanel()?.addMeasureFromChartData();
                        }}
                        title={$t('common.addMeasure')}
                    >
                        <span class="text-sm leading-none">+</span>
                        <span class="hidden sm:inline">{$t('common.addMeasure')}</span>
                    </button>
                    <ChevronDown class="transition-transform text-gray-400 {activeMeasuresOpen() ? 'rotate-180' : ''}" size={15} />
                </div>
            </div>
            <div class={primaryMode === 'price' && showMeasures ? 'px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3' : 'hidden'} data-testid="asset-detail-measures-panel" aria-hidden={primaryMode !== 'price' || !showMeasures} inert={primaryMode !== 'price' || !showMeasures}>
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
                class={primaryMode === 'calendar-return' && showCalendarMeasures ? 'px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3' : 'hidden'}
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
        </div>

        <!-- ======================================================================= -->
        <!-- Foldable Panel: Metadata & Classification -->
        <!-- ======================================================================= -->
        {#if assetInfo}
            <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
                <button
                    class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
                    data-testid="asset-detail-metadata-toggle"
                    use:guideAnchor={'asset.detail.metadata'}
                    onclick={() => (showMetadata = !showMetadata)}
                >
                    <span class="flex items-center gap-2">
                        <Info class="text-sky-500" size={15} />
                        {$t('assetDetail.metadata')}
                    </span>
                    <ChevronDown class="transition-transform {showMetadata ? 'rotate-180' : ''}" size={15} />
                </button>
                {#if showMetadata}
                    <div data-testid="asset-detail-metadata-panel" class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3 space-y-4">
                        <!-- Description (from classification_params.short_description) — always first if set -->
                        {#if shortDescription}
                            <div>
                                <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">{$t('common.description')}</h4>
                                <p class="text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">{shortDescription}</p>
                            </div>
                        {/if}

                        <!-- External URLs (provider URL only — user URL is in header) -->
                        {#if providerExternalUrl}
                            <div>
                                <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">{$t('assets.provider.providerUrl')}</h4>
                                <a href={providerExternalUrl} target="_blank" rel="noopener noreferrer" class="text-sm text-libre-green hover:underline break-all">{providerExternalUrl}</a>
                            </div>
                        {/if}

                        <!-- Classification Charts -->
                        {#if classificationLoaded && (sectorDistribution || geographicDistribution)}
                            <div class="space-y-3">
                                <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">{$t('common.classification')}</h4>

                                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                    {#if geographicDistribution && Object.keys(geographicDistribution).length > 0}
                                        <div class="bg-gray-50 dark:bg-slate-700/30 rounded-lg p-3">
                                            <h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{$t('common.geoDistribution')}</h5>
                                            <GeographyMap data={geographicDistribution} height="280px" language={$currentLanguage} />
                                        </div>
                                    {/if}

                                    {#if sectorDistribution && Object.keys(sectorDistribution).length > 0}
                                        <div class="bg-gray-50 dark:bg-slate-700/30 rounded-lg p-3">
                                            <h5 class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{$t('common.sectorDistribution')}</h5>
                                            <AllocationPieChart data={Object.entries(sectorDistribution).map(([name, w]) => ({name, value: w * 100, amount: 0, emoji: getSectorEmoji(name)}))} height="280px" />
                                        </div>
                                    {/if}
                                </div>
                            </div>
                        {:else if !classificationLoaded}
                            <div class="text-sm text-gray-500 dark:text-gray-400 italic">
                                {$t('common.classification')} — {$t('common.loading')}...
                            </div>
                        {:else}
                            <p class="text-sm text-gray-400 dark:text-gray-500">{$t('assetDetail.noClassification')}</p>
                        {/if}

                        <!-- Identifiers -->
                        {#if identifiersList.length > 0}
                            <div>
                                <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">{$t('common.identifiers')}</h4>
                                <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                    {#each identifiersList as [label, value]}
                                        <div class="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
                                            <span class="text-[10px] uppercase text-gray-400 dark:text-gray-500">{label}</span>
                                            <p class="text-sm font-mono text-gray-700 dark:text-gray-200">{value}</p>
                                        </div>
                                    {/each}
                                </div>
                            </div>
                        {:else}
                            <p class="text-sm text-gray-400 dark:text-gray-500">{$t('assetDetail.noIdentifiers')}</p>
                        {/if}

                        {#if providerAssignment}
                            <div>
                                <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">Provider</h4>
                                <div class="flex items-center gap-3 text-sm flex-wrap">
                                    <span class="inline-flex items-center gap-1.5 font-medium text-gray-700 dark:text-gray-200">
                                        {#if providerIconUrl}
                                            <img src={providerIconUrl} alt="" class="w-4 h-4 rounded-sm object-contain" />
                                        {/if}
                                        {getAssetProviderName(providerAssignment.provider_code)}
                                    </span>
                                    <span class="text-gray-400">→</span>
                                    <span class="font-mono text-gray-500 dark:text-gray-400">{providerAssignment.identifier} ({providerAssignment.identifier_type})</span>
                                    {#if providerAssignment.last_fetch_at}
                                        <span class="text-xs text-gray-400 dark:text-gray-500">
                                            {$t('assets.provider.lastFetch')}: {new Date(String(providerAssignment.last_fetch_at)).toLocaleDateString()}
                                        </span>
                                    {:else}
                                        <span class="text-xs text-gray-400 dark:text-gray-500">{$t('assets.provider.neverFetched')}</span>
                                    {/if}
                                </div>
                            </div>
                        {/if}

                        <button
                            class="text-xs text-libre-green hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={!assetInfo}
                            onclick={() => {
                                editDataForModal = buildEditData();
                                editModalOpen = true;
                            }}
                        >
                            {$t('assetDetail.editViaModal')} →
                        </button>
                    </div>
                {/if}
            </div>
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
            <RefreshCw size={24} class="animate-spin text-libre-green" />
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- AssetModal for editing -->
    <!-- ======================================================================= -->
    {#if assetInfo}
        <AssetModal bind:open={editModalOpen} editMode={true} editData={editDataForModal} onupdated={handleAssetUpdated} onclose={() => (editModalOpen = false)} />

        <!-- FX Pair Add Modal (opened from FX warning or banner) -->
        {@const createParts = fxPairCreateSlug ? fxPairCreateSlug.split('-') : []}
        {@const createBase = createParts.length === 2 ? createParts[0] : assetInfo.currency}
        {@const createQuote = createParts.length === 2 ? createParts[1] : displayCurrency !== assetInfo.currency ? displayCurrency : ''}
        {@const fxCreationCallbacks = createFxPairCallbacks(data.assetId, !!fxPairCreateSlug, assetInfo.currency)}
        <FxPairAddModal bind:open={showFxPairAddModal} readonlyBase={!fxPairCreateSlug} initialBase={createBase} initialQuote={createQuote} {dateStart} {dateEnd} oncreated={fxCreationCallbacks.oncreated} onsynced={fxCreationCallbacks.onsynced} onclose={fxCreationCallbacks.onclose} />
    {/if}

    <!-- Page Sync Modal (sync all assets + FX pairs) -->
    {#if assetInfo}
        <PageSyncModal bind:open={showPageSyncModal} dateStart={syncDateStart} {dateEnd} assets={syncAllAssets} fxPairs={syncAllFxPairs} onsynced={handlePageSyncComplete} onclose={() => (showPageSyncModal = false)} />
    {/if}
</div>
