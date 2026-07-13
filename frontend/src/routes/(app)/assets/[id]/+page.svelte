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
    import {onMount, tick} from 'svelte';
    import {page} from '$app/stores';
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {goBack} from '$lib/stores/app/navigationStore';
    import {ArrowLeft, ChevronDown, ExternalLink, Info, Pencil, RefreshCw, RotateCw, Ruler, Settings, TrendingUp, X} from 'lucide-svelte';
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
    import PageSyncModal from '$lib/components/ui/modals/PageSyncModal.svelte';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {RenderedSignal, SignalConfig} from '$lib/charts/signals';
    import {signalFromConfig} from '$lib/charts/signals';
    import {getSettingsForPair, setPairSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import type {ViewMode, ChartType} from '$lib/components/charts/ChartToolbar.svelte';
    import type {LayoutMode} from '$lib/utils/layout/responsiveLayout.svelte';
    import PageToolbar from '$lib/components/ui/toolbar/PageToolbar.svelte';
    import {ensureFxRangeLoaded, getFxStore} from '$lib/stores/fxStoreRegistry';
    import {getAssetPriceStore, invalidateAssetPriceStore, apiPricesToAssetPricePoints} from '$lib/stores/assetPriceStoreRegistry';
    import {getAssetTypeIconUrl, buildIdentifiersList} from '$lib/utils/assetTypes';
    import {ensureAssetProvidersCached, getAssetProviderIconUrl, getAssetProviderName, isParametricProvider, assetProvidersVersion} from '$lib/utils/providerHelpers';
    import {replaceHistoryDateRange} from '$lib/utils/url/dateRangeUrl';
    import type {AssetDetail, ProviderAssignmentFlat} from '$lib/types';
    import type {SignalLabelInfo} from '$lib/charts/signalLabel';
    import {buildOverlaySignalInfoMap} from '$lib/charts/signalLabel';
    import {loadComparisonAssetsData} from '$lib/charts/loadComparisonData';
    import {getStart, getEnd, setDateRange, resolveDateSentinel, isMaxSentinel} from '$lib/stores/dateRangeStore.svelte';
    import {fetchCurrentPrices} from '$lib/services/livePriceService';
    import {buildAssetSyncToast, buildFxSyncToast} from '$lib/utils/sync/syncToastHelpers';
    import {COLORS} from '$lib/components/charts/lineChartHelpers';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';

    // =========================================================================
    // Page data
    // =========================================================================

    interface Props {
        data: {assetId: number};
    }

    let {data}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let assetInfo = $state<AssetDetail | null>(null);
    let providerAssignment = $state<ProviderAssignmentFlat | null>(null);
    let chartData: any[] = $state([]);
    let events: any[] = $state([]);
    let comparisonEvents = $state<Map<number, any[]>>(new Map());

    let loading = $state(true);
    /** Stores either a raw message or an i18n key prefixed with `_i18n:` for reactive translation */
    let error: string | null = $state(null);
    let syncing = $state(false);
    let fxSyncing = $state(false);

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

    // Foldable panels
    let showAesthetics = $state(false);
    let showMeasures = $state(false);
    let showSignals = $state(false);
    let showDataEditor = $state(false);
    let showMetadata = $state(false);

    // Filter bar layout is now owned by PageToolbar (shared with dashboard/broker-detail/assets
    // list) — layoutMode is bound out (see bind:layoutMode below) for the one usage elsewhere on
    // this page (editor tip text). Tune live via window.__lfLayouts.assetDetail.thresholds.<field>.
    let pageLayoutMode = $state<LayoutMode>('denseRow');

    // Chart settings
    let settings = $derived(getSettingsForPair(`asset-${data.assetId}`, 'assets'));
    let signals = $derived<SignalConfig[]>([...settings.signals]);

    // Measure panel
    let measureMode = $state(false);
    let measureSignals: RenderedSignal[] = $state([]);
    let measurePanel: MeasurePanel | undefined = $state(undefined);

    // Editor panel state save/restore
    let savedPanelStates: {aesthetics: boolean; measures: boolean; signals: boolean} | null = $state(null);

    // Data editor state
    let savingEdit = $state(false);
    let editorDirtyCount = $state(0);
    let pendingPreviewSignal: RenderedSignal | null = $state(null);
    let assetDataEditorRef: AssetDataEditorSection | undefined = $state(undefined);

    let overlayDataVersion = $state(0);
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

    // #R3-4 — derive "parametric" status from provider kind (instead of hardcoded code),
    // so the detail page picks the "Regenerate" label for any parametric_generation provider.
    // Depends on assetProvidersVersion to re-evaluate after the providers cache is loaded.
    let isParametric = $derived.by(() => {
        void $assetProvidersVersion;
        return isParametricProvider(providerAssignment?.provider_code);
    });
    let isManualOnly = $derived(!providerAssignment);
    /** True when OHLCV price data is available (enables candlestick chart) */
    let hasOhlcv = $derived(lineData.some((p) => p.open != null));
    // Reset to line chart when OHLCV becomes unavailable (e.g. date range with no data)
    $effect(() => {
        if (!hasOhlcv) chartType = 'line';
    });
    /** Settings that don't apply in candlestick mode — greyed out in aesthetics panel */
    let disabledAesthetics = $derived((chartType as string) === 'candlestick' ? new Set(['colorByBaseline', 'areaFill', 'staleGradient']) : new Set<string>());

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
            const convFailed = Boolean(cfg.params._conversionFailed);
            const hasData = Boolean(cfg.params._resolvedData);
            let status: RequiredFxPairInfo['status'];
            if (missing) {
                status = 'missing';
            } else if (convFailed || !hasData) {
                status = 'no-data';
            } else {
                status = 'ok';
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
            const eventCurrencies = new Set<string>();
            for (const ev of events) {
                const c = ev.value?.code;
                if (c && c !== displayCurrency) eventCurrencies.add(c);
            }
            for (const [, evts] of comparisonEvents) {
                for (const ev of evts) {
                    const c = ev.value?.code;
                    if (c && c !== displayCurrency) eventCurrencies.add(c);
                }
            }
            for (const evCur of eventCurrencies) {
                const slug = toSlug(evCur, displayCurrency);
                if (seenSlugs.has(slug)) continue;
                seenSlugs.add(slug);
                const missing = !allConfiguredFxSlugs.includes(slug);
                // Check if there is at least one event in this currency that failed conversion.
                const hasFailedConversion = events.some((ev) => ev.value?.code === evCur && !ev.original_value);
                let status: RequiredFxPairInfo['status'];
                if (missing) {
                    status = 'missing';
                } else if (hasFailedConversion) {
                    status = 'no-data';
                } else {
                    status = 'ok';
                }
                pairs.push({
                    slug,
                    label: slug.replace('-', '/'),
                    forAsset: $t('events.fxBannerContext') ?? 'for dividend/cash events',
                    status,
                });
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

    // Overlay signals
    let overlaySignals: RenderedSignal[] = $derived.by(() => {
        void overlayDataVersion;
        const rendered: RenderedSignal[] = [];
        for (const cfg of signals) {
            const instance = signalFromConfig(cfg);
            if (!instance) continue;

            if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (!pairSlug) continue;
                try {
                    const store = getFxStore(pairSlug);
                    const storeData = store.getAllSorted();
                    if (storeData.length === 0) continue;
                    instance.params._resolvedData = storeData.map((d) => ({date: d.date, value: d.rate}));
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
        return rendered;
    });

    let allOverlaySignals: RenderedSignal[] = $derived([...overlaySignals, ...measureSignals, ...(pendingPreviewSignal ? [pendingPreviewSignal] : [])]);

    // Signal label info for MeasurePanel and PriceChartFull tooltip
    let mainSignalInfo: SignalLabelInfo = $derived({
        label: assetInfo?.display_name ?? '',
        iconUrl: assetInfo?.icon_url,
        assetType: assetInfo?.asset_type,
        isCrown: true,
        color: COLORS.lineLight,
    });

    let overlaySignalInfoMap = $derived(buildOverlaySignalInfoMap(overlaySignals));

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
        for (const cfg of signals) {
            if (cfg.signalType === 'asset-comparison') {
                const targetId = Number(cfg.params.assetId);
                if (!targetId) continue;
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

    /** Full page reload: fetches all data for the current assetId */
    async function reloadPage() {
        loading = true;
        error = null;
        // Reset state for new asset
        assetInfo = null;
        providerAssignment = null;
        chartData = [];
        events = [];
        comparisonEvents = new Map();
        currentLivePrice = null;
        livePriceConversionFailed = false;
        sectorDistribution = null;
        geographicDistribution = null;
        shortDescription = null;
        classificationLoaded = false;
        providerIconUrl = null;

        await Promise.all([ensureCurrenciesLoaded(get(currentLanguage)), ensureAssetProvidersCached(), loadAssetInfo(), loadProviderAssignment(), loadChartData(), loadFxPairSlugs(), loadAssetList()]);
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

    onMount(() => {
        _prevAssetId = data.assetId;
        reloadPage();
    });

    // Re-load everything when navigating to a different asset (same route pattern)
    $effect(() => {
        const newId = data.assetId;
        if (_prevAssetId !== undefined && newId !== _prevAssetId) {
            _prevAssetId = newId;
            reloadPage();
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
            return;
        }
        // Fetch immediately, then poll every 30s
        _fetchLivePrice(id, nativeCurrency ?? '', targetCurrency, fxMissing);
        const timer = setInterval(() => _fetchLivePrice(id, nativeCurrency ?? '', targetCurrency, fxMissing), 30_000);
        return () => clearInterval(timer);
    });

    async function _fetchLivePrice(assetId: number, nativeCurrency: string, targetCurrency: string, fxMissing: boolean) {
        try {
            const results = await fetchCurrentPrices([assetId]);
            if (results.length === 0 || results[0].value == null) return;
            const nativeValue = results[0].value;

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
            const response = await zodiosApi.get_all_assets_api_v1_assets_all_get();
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

    async function loadChartData(force = false) {
        const effectiveCurrency = displayCurrency && assetInfo?.currency && displayCurrency !== assetInfo.currency ? displayCurrency : (assetInfo?.currency ?? '');
        const targetCurrency = displayCurrency && assetInfo?.currency && displayCurrency !== assetInfo.currency ? displayCurrency : undefined;

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
                return;
            }
        }

        // Cache miss or force — full fetch with loading spinner
        loading = true;
        error = null;
        try {
            const response = await zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post([
                {
                    asset_id: data.assetId,
                    date_range: {start: dateStart, end: dateEnd},
                    include_events: true,
                    target_currency: targetCurrency,
                },
            ]);
            const result = (response as any)?.items?.[0];
            if (result) {
                chartData = result.prices ?? [];
                events = result.events ?? [];
                // Populate the price cache (derive currency from response if not known yet)
                const cacheCurrency = effectiveCurrency || chartData[0]?.currency || '';
                if (cacheCurrency && chartData.length > 0) {
                    const store = getAssetPriceStore(data.assetId, cacheCurrency);
                    store.merge(apiPricesToAssetPricePoints(chartData));
                    store.markFetched(dateStart, dateEnd);
                }
            } else {
                chartData = [];
                events = [];
            }
            if (chartData.length === 0 && !error) {
                error = '_i18n:assetDetail.noData';
            }
            resolveMaxStartFromChartData();
        } catch (e: any) {
            console.error('Failed to load chart data:', e);
            if (chartData.length === 0) error = e?.message || 'Failed to load prices';
        } finally {
            loading = false;
        }
    }

    async function loadFxPairSlugs() {
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            const items = (response as any)?.items || [];
            const slugSet = new Set<string>();
            for (const i of items) {
                const b = i.base < i.quote ? i.base : i.quote;
                const q = i.base < i.quote ? i.quote : i.base;
                slugSet.add(`${b}-${q}`);
            }
            allConfiguredFxSlugs = [...slugSet].sort();
        } catch (e) {
            console.error('Failed to load FX pair slugs:', e);
        }
    }

    async function loadAssetList() {
        try {
            const response = await zodiosApi.get_all_assets_api_v1_assets_all_get();
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
    async function maybeLoadComparison() {
        const compSignals = signals.filter((s) => s.signalType === 'asset-comparison');
        if (compSignals.length === 0 || lineData.length === 0) return;
        try {
            comparisonEvents = await loadComparisonAssetsData(compSignals, {start: dateStart, end: dateEnd}, allAssets, comparisonEvents, data.assetId, displayCurrency || undefined);
            overlayDataVersion++;
        } catch (e) {
            console.error('Failed to load comparison asset data:', e);
        }
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
        if (loading) return;
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
            if (isConvertedChart) {
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

    async function handleRefresh() {
        invalidateAssetPriceStore(data.assetId);
        rearmMaxPendingBeforeReload();
        await loadChartData(true);
        // Invalidate FX overlay stores so they refetch updated rates
        for (const pair of requiredFxPairs) {
            if (pair.status === 'missing') continue;
            getFxStore(pair.slug).invalidateAll();
            await ensureFxRangeLoaded(pair.slug, dateStart, dateEnd);
        }
        overlayDataVersion++;
        await maybeLoadComparison();
    }

    async function reloadMetadata() {
        await Promise.all([loadAssetInfo(), loadProviderAssignment()]);
        // Update provider icon if changed
        if (assetInfo?.provider_code) {
            providerIconUrl = getAssetProviderIconUrl(assetInfo.provider_code);
        }
        // Reload classification data if metadata is available (always refresh after sync)
        classificationLoaded = false;
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

    async function handlePageSyncComplete() {
        await handleRefresh();
        await reloadMetadata();
        await maybeLoadComparison();
        overlayDataVersion++;
    }

    async function handleFxPairCreated({base, quote, hasRealProvider}: {base: string; quote: string; hasRealProvider: boolean}) {
        const wasForComparison = !!fxPairCreateSlug;
        showFxPairAddModal = false;
        fxPairCreateSlug = '';
        await loadFxPairSlugs();
        // Only update display currency when creating the main asset's FX pair
        if (!wasForComparison) {
            const assetCur = assetInfo?.currency ?? '';
            const newQuote = assetCur === base ? quote : base;
            if (newQuote !== assetCur) {
                displayCurrency = newQuote;
            }
        }
        if (hasRealProvider) {
            toasts.success($t('assetDetail.fxPairCreatedSynced'));
        }
        await handleRefresh();
        await maybeLoadComparison();
        overlayDataVersion++;
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
        measurePanel?.addPoint(date, value);
    }

    function handleAestheticsChange(values: {colorByBaseline: boolean; areaFill: boolean; gridLines: boolean; staleGradient: boolean; yAxisMode: 'auto' | 'include0' | 'custom'; yAxisMin: number | undefined; yAxisMax: number | undefined}) {
        setPairSettings(`asset-${data.assetId}`, {...settings, ...values, signals: [...signals]});
    }

    function handleSignalsChange(newSignals: SignalConfig[]) {
        setPairSettings(`asset-${data.assetId}`, {...settings, signals: JSON.parse(JSON.stringify(newSignals))});
        maybeLoadComparison(); // fire-and-forget: load data for newly added comparison signals
    }

    async function handleSyncAsset(assetId: number, opts: {silent?: boolean} = {}) {
        const silent = opts.silent === true;
        try {
            const response = await zodiosApi.sync_prices_bulk_api_v1_assets_prices_sync_post([
                {
                    asset_id: assetId,
                    date_range: {start: syncDateStart, end: dateEnd},
                },
            ]);
            const r = (response as any)?.results?.[0];
            const tr = get(t);
            if (!silent) {
                if (r) {
                    const toast = buildAssetSyncToast(r, tr('common.sync'), tr);
                    toasts[toast.variant](toast.message);
                } else {
                    toasts.error(`${tr('common.sync')} — ${tr('prices.sync.noResponse')}`);
                }
            }

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
            if (assetId === data.assetId && r?.asset_id === assetId) {
                const changedPoints = Array.isArray(r.changed_points) ? r.changed_points : null;
                const isConvertedChart = !!(displayCurrency && assetInfo?.currency && displayCurrency !== assetInfo.currency);
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
                    invalidateAssetPriceStore(data.assetId);
                    rearmMaxPendingBeforeReload();
                    await loadChartData(true);
                } else {
                    // No delta from backend (no changes, or above cap,
                    // or reload is needed anyway): full reload.
                    invalidateAssetPriceStore(data.assetId);
                    rearmMaxPendingBeforeReload();
                    await loadChartData(true);
                }
            }
        } catch (e: any) {
            if (!silent) toasts.error('Sync failed: ' + (e?.message || 'unknown'));
        }
        // Reload comparison data for the synced asset, then trigger UI update
        await maybeLoadComparison();
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
        fxSyncing = true;
        try {
            const syncResponse = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                pairs: [slug],
                start: dateStart,
                end: dateEnd,
            });
            // Refetch FX data into store after sync (invalidate + reload)
            getFxStore(slug).invalidateAll();
            await ensureFxRangeLoaded(slug, dateStart, dateEnd);
            overlayDataVersion++;
            // Reload asset chart data to apply updated FX conversion
            invalidateAssetPriceStore(data.assetId);
            await loadChartData(true);
            const tr = get(t);
            const r = (syncResponse as any)?.results?.[0];
            const toast = buildFxSyncToast(r, slug, tr);
            toasts[toast.variant](toast.message);
        } catch (e: any) {
            toasts.error('FX sync failed: ' + (e?.message || 'unknown'));
        } finally {
            fxSyncing = false;
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
</script>

<div class="space-y-4" data-testid="asset-detail-page">
    <!-- ======================================================================= -->
    <!-- Header: asset info + back button -->
    <!-- ======================================================================= -->
    <div class="flex items-center gap-3" data-testid="asset-detail-header">
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

    <!-- Unified data quality banners -->
    <DataQualityBanner issues={assetDetailIssues} mode="flat" onaction={handleBannerAction} />

    <!-- ======================================================================= -->
    <!-- Filter bar — shared PageToolbar (same component as dashboard/broker-detail/assets
         list), so responsive/wrap fixes made there auto-propagate here too. -->
    <!-- oneRow:       [ datepicker  price-summary ─── actions-2×2 ]  1 row, picker 1-row     -->
    <!-- denseRow:     [ datepicker  price-summary ─── actions-2×2 ]  1 row, picker 2-row     -->
    <!-- stackFilters: [ datepicker       ] [ actions ]  filters+summary stacked, actions     -->
    <!--               [ price-summary    ] [ 2×2     ]  stay BESIDE (2×2)                    -->
    <!-- oneColumn:    [ datepicker       ]  whole bar now ONE column — actions moved BELOW,  -->
    <!--               [ price-summary    ]  still a labeled 2×2 grid (only position changed) -->
    <!--               [ actions ── 2×2   ]                                                   -->
    <!-- iconOnly:     [ datepicker       ]  everything stacked, actions icon-only centered   -->
    <!--               [ price-summary    ]  row                                              -->
    <!--               [ actions ─ icons  ]                                                   -->
    <!-- ======================================================================= -->
    <PageToolbar thresholds={{oneRow: 1090, denseRow: 870, stackFilters: 570, oneColumn: 445, iconOnly: 330, labelHide: 330}} filterRowTestId="asset-detail-filter-bar" layoutDebugName="assetDetail" bind:layoutMode={pageLayoutMode}>
        {#snippet filters()}
            <div class="flex flex-1 self-stretch min-w-0">
                <DateRangePicker bind:activePreset bind:end={dateEnd} bind:start={displayDateStart} compact={true} align="start" layoutMode={pageLayoutMode} debugName="assetDetail" onchange={handleDateRangeChange} />
            </div>
        {/snippet}

        {#snippet summary({layoutMode})}
            {#if assetInfo}
                <AssetPriceSummary {lastPrice} {deltaPercent} {deltaAbs} bind:displayCurrency assetCurrency={assetInfo.currency} {layoutMode} {livePriceConversionFailed} fxPairUrl={mainFxPairUrl} />
            {/if}
        {/snippet}

        {#snippet actions({showActionLabels})}
            <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                <button
                    class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {viewMode === 'absolute' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => {
                        viewMode = 'absolute';
                    }}>Abs</button
                >
                <button
                    class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {viewMode === 'percentage' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => {
                        viewMode = 'percentage';
                    }}>%</button
                >
            </div>
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                data-testid="asset-detail-edit-btn"
                onclick={() => {
                    editDataForModal = buildEditData();
                    editModalOpen = true;
                }}
            >
                <Pencil size={14} />
                {#if showActionLabels}<span>{$t('common.edit')}</span>{/if}
            </button>
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors
                           {isManualOnly ? 'opacity-50 cursor-not-allowed' : ''}"
                data-testid="asset-detail-sync-btn"
                disabled={syncing || isManualOnly}
                onclick={handleSync}
                title={isManualOnly ? $t('assetDetail.syncDisabledManual') : ''}
            >
                <RotateCw class={syncing ? 'animate-spin' : ''} size={14} />
                {#if showActionLabels}<span>{syncing ? $t('common.syncing') : isParametric ? $t('assetDetail.recalculate') : $t('common.sync')}</span>{/if}
            </button>
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                data-testid="asset-detail-refresh-btn"
                disabled={loading}
                onclick={handleRefresh}
            >
                <RefreshCw class={loading ? 'animate-spin' : ''} size={14} />
                {#if showActionLabels}<span>{$t('common.refresh')}</span>{/if}
            </button>
        {/snippet}
    </PageToolbar>

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Signals (ABOVE chart, replaces old Aesthetics position) -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <button class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl" data-testid="asset-detail-signals-toggle" onclick={() => (showSignals = !showSignals)}>
            <span class="flex items-center gap-2">
                <TrendingUp class="text-blue-500" size={15} />
                {$t('common.signals')}
            </span>
            <ChevronDown class="transition-transform {showSignals ? 'rotate-180' : ''}" size={15} />
        </button>
        {#if showSignals}
            <div data-testid="asset-detail-signals-panel" class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3">
                <ChartSignalsSection
                    signals={[...signals]}
                    availablePairs={allConfiguredFxSlugs}
                    availableAssets={allAssets.filter((a) => a.id !== data.assetId)}
                    mainPairSlug={`asset-${data.assetId}`}
                    onchange={handleSignalsChange}
                    onsyncpair={handleSyncPair}
                    ondetailpair={handleDetailPair}
                    onsyncasset={handleSyncAsset}
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
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4" data-testid="asset-detail-chart">
        {#if loading && lineData.length === 0}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    <RefreshCw size={24} class="animate-spin text-libre-green mx-auto mb-2" />
                    <p class="text-sm text-gray-500 dark:text-gray-400">{$t('assetDetail.loadingPrices')}</p>
                </div>
            </div>
        {:else if lineData.length > 0}
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
                        yAxisMode={settings.yAxisMode}
                        yAxisMin={settings.yAxisMin}
                        yAxisMax={settings.yAxisMax}
                        onchange={handleAestheticsChange}
                        disabledFields={disabledAesthetics}
                    />
                </div>
            {/if}

            <div class="relative">
                <!-- Right toolbar -->
                <div class="absolute top-0 right-0 z-10 flex items-center gap-1.5">
                    <button
                        data-testid="asset-detail-measure-btn"
                        class="p-1.5 rounded-lg transition-colors {measureMode
                            ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 ring-1 ring-violet-300 dark:ring-violet-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                        onclick={async () => {
                            if (measureMode) {
                                measurePanel?.stopMeasureMode();
                            } else {
                                showMeasures = true;
                                await tick();
                                measurePanel?.startMeasureMode();
                            }
                        }}
                        title={measureMode ? $t('common.exitMeasure') : $t('common.addMeasure')}
                    >
                        <Ruler size={16} />
                    </button>
                    <button
                        data-testid="asset-detail-editdata-btn"
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
                    data={lineData}
                    currency={displayCurrency}
                    mainSeriesLabel={assetInfo?.display_name ?? ''}
                    chartHeight="400px"
                    overlaySignals={allOverlaySignals}
                    eventMarkers={chartEventMarkers}
                    {overlaySignalInfoMap}
                    mainIconUrl={assetInfo?.icon_url}
                    mainAssetType={assetInfo?.asset_type}
                    colorByBaseline={settings.colorByBaseline}
                    areaFill={settings.areaFill}
                    showGridLines={settings.gridLines}
                    showGradient={settings.staleGradient}
                    yAxisMode={settings.yAxisMode}
                    yAxisMin={settings.yAxisMin}
                    yAxisMax={settings.yAxisMax}
                    {measureMode}
                    onMeasureClick={handleMeasureClick}
                    onMeasureHover={(date, value) => measurePanel?.updatePendingEnd(date, value)}
                    hideToolbar={true}
                    externalChartType={chartType}
                    onChartTypeChange={(t) => {
                        chartType = t;
                    }}
                    externalViewMode={viewMode}
                    editMode={showDataEditor}
                    staleLabel={$t('chart.tooltip.stale')}
                    fxStaleLabel={$t('chart.tooltip.fxStale')}
                    displayCurrency={displayCurrency !== assetInfo?.currency ? displayCurrency : undefined}
                    displayCurrencyFlag={displayCurrency !== assetInfo?.currency ? getCurrencyInfo(displayCurrency).flag_emoji : undefined}
                    mainCurrency={assetInfo?.currency ?? undefined}
                    mainCurrencyFlag={assetInfo?.currency ? getCurrencyInfo(assetInfo.currency).flag_emoji : undefined}
                    onDblClick={(date) => {
                        if (showDataEditor && assetDataEditorRef) {
                            assetDataEditorRef.scrollToDate(date, 'prices');
                        }
                    }}
                    onEventDblClick={(date) => {
                        if (showDataEditor && assetDataEditorRef) {
                            assetDataEditorRef.scrollToDate(date, 'events');
                        }
                    }}
                />
            </div>
        {:else}
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
                                class="px-4 py-2 text-sm bg-slate-200 dark:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-500 transition-colors"
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
                            class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
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
        <div data-testid="asset-detail-editor-panel" class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-amber-200 dark:border-amber-800">
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
                💡 {pageLayoutMode === 'oneColumn' || pageLayoutMode === 'iconOnly' ? $t('assetDetail.editorTipMobile') : $t('assetDetail.editorTipDesktop')}
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
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <div
            class="flex items-center justify-between px-4 py-2.5 cursor-pointer select-none hover:bg-gray-50 dark:hover:bg-slate-750 transition-colors rounded-t-xl"
            role="button"
            tabindex="0"
            data-testid="asset-detail-measures-toggle"
            onclick={() => (showMeasures = !showMeasures)}
            onkeydown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    showMeasures = !showMeasures;
                }
            }}
        >
            <div class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200">
                <Ruler class="text-violet-500" size={15} />
                {$t('common.measures')}
                {#if measureMode}
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
                    disabled={lineData.length < 2}
                    data-testid="asset-detail-add-measure-btn"
                    onclick={(e) => {
                        e.stopPropagation();
                        showMeasures = true;
                        measurePanel?.addMeasureFromChartData();
                    }}
                    title={$t('common.addMeasure')}
                >
                    <span class="text-sm leading-none">+</span>
                    <span class="hidden sm:inline">{$t('common.addMeasure')}</span>
                </button>
                <ChevronDown class="transition-transform text-gray-400 {showMeasures ? 'rotate-180' : ''}" size={15} />
            </div>
        </div>
        <div class={showMeasures ? 'px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3' : 'hidden'} data-testid="asset-detail-measures-panel">
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
            />
        </div>
    </div>

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Metadata & Classification -->
    <!-- ======================================================================= -->
    {#if assetInfo}
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
            <button class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl" data-testid="asset-detail-metadata-toggle" onclick={() => (showMetadata = !showMetadata)}>
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
                        class="text-xs text-libre-green hover:underline"
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

    <!-- ======================================================================= -->
    <!-- AssetModal for editing -->
    <!-- ======================================================================= -->
    {#if assetInfo}
        <AssetModal bind:open={editModalOpen} editMode={true} editData={editDataForModal} onupdated={handleAssetUpdated} onclose={() => (editModalOpen = false)} />

        <!-- FX Pair Add Modal (opened from FX warning or banner) -->
        {@const createParts = fxPairCreateSlug ? fxPairCreateSlug.split('-') : []}
        {@const createBase = createParts.length === 2 ? createParts[0] : assetInfo.currency}
        {@const createQuote = createParts.length === 2 ? createParts[1] : displayCurrency !== assetInfo.currency ? displayCurrency : ''}
        <FxPairAddModal
            bind:open={showFxPairAddModal}
            readonlyBase={!fxPairCreateSlug}
            initialBase={createBase}
            initialQuote={createQuote}
            {dateStart}
            {dateEnd}
            oncreated={handleFxPairCreated}
            onclose={() => {
                showFxPairAddModal = false;
                fxPairCreateSlug = '';
            }}
        />
    {/if}

    <!-- Page Sync Modal (sync all assets + FX pairs) -->
    {#if assetInfo}
        <PageSyncModal bind:open={showPageSyncModal} dateStart={syncDateStart} {dateEnd} assets={syncAllAssets} fxPairs={syncAllFxPairs} onsynced={handlePageSyncComplete} onclose={() => (showPageSyncModal = false)} />
    {/if}
</div>
