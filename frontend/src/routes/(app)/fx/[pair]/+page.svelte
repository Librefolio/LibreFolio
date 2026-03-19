<script lang="ts">
    /**
     * FX Pair Detail Page — Redesigned v2
     *
     * Layout:
     * - Header: pair info + invert
     * - Filter bar: 3-column (DateRangePicker | pair summary | 2×2 button matrix)
     * - Chart: PriceChartFull (unified 2-grid with dataZoom) + edit/measure buttons overlay
     * - Foldable panels: Aesthetics (above chart area), Measures, Signals (below chart)
     * - Data Editor: shown via edit button on chart
     * - Provider Config: via modal (not inline panel)
     *
     * Uses Svelte 5 runes. Replaces old FxEditSection with FxDataEditorSection.
     */
    import {onMount, tick} from 'svelte';
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {ArrowLeft, ArrowLeftRight, ChevronDown, Pencil, RefreshCw, RotateCw, Ruler, Settings, TrendingDown, TrendingUp, Wrench} from 'lucide-svelte';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import PriceChartFull from '$lib/components/charts/PriceChartFull.svelte';
    import ChartAestheticsSection from '$lib/components/charts/ChartAestheticsSection.svelte';
    import ChartSignalsSection from '$lib/components/charts/ChartSignalsSection.svelte';
    import MeasurePanel from '$lib/components/charts/MeasurePanel.svelte';
    import FxDataEditorSection from '$lib/components/fx/FxDataEditorSection.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {RenderedSignal, SignalConfig} from '$lib/charts/signals';
    import {signalFromConfig} from '$lib/charts/signals';
    import {getSettingsForPair, setPairSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/currencyStore';
    import {currentLanguage} from '$lib/stores/language';
    import type {ViewMode} from '$lib/components/charts/ChartToolbar.svelte';
    import {apiResultToFxDataPoint, type FxDataPoint, getFxStore} from '$lib/stores/fxStoreRegistry';
    import {setCardInverted} from '$lib/stores/fxCardInversionStore';

    // =========================================================================
    // Page data
    // =========================================================================

    interface Props {
        data: {
            urlBase: string; urlQuote: string;
            canonicalBase: string; canonicalQuote: string; canonicalSlug: string;
            inverted: boolean;
        };
    }

    let {data}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartData: FxDataPoint[] = $state([]);
    let loading = $state(true);
    let error: string | null = $state(null);
    let syncing = $state(false);

    // Confirm modal for swap while editing
    let showSwapConfirm = $state(false);

    // Date range (default 3M)
    let dateEnd = $state(new Date().toISOString().slice(0, 10));
    let dateStart = $state((() => {
        const d = new Date();
        d.setMonth(d.getMonth() - 3);
        return d.toISOString().slice(0, 10);
    })());
    let activePreset: any = $state('3M');

    // View mode (abs/%) — controlled by the page, not by chart toolbar
    let viewMode: ViewMode = $state('absolute');

    // Provider config
    let providers: Array<{ providerCode: string; priority: number; chainSteps?: Array<{ from: string; to: string; provider: string }> }> = $state([]);
    let availableProviders: Array<{ code: string; name: string }> = $state([]);

    // Foldable panels
    let showAesthetics = $state(false);
    let showMeasures = $state(false);
    let showSignals = $state(false);
    let showDataEditor = $state(false);

    // Provider config modal
    let showProviderModal = $state(false);

    // Filter bar adaptive layout (same ResizeObserver as FX list page)
    let filterBarRef = $state<HTMLDivElement | null>(null);
    let layoutMode = $state<'wide' | 'tablet' | 'mobile'>('tablet');
    let showActionLabels = $state(true);

    // Chart settings (from store) — keyed by canonical slug (not URL direction)
    let settings = $derived(getSettingsForPair(data.canonicalSlug));
    let signals = $derived<SignalConfig[]>([...settings.signals]);

    // Measure panel
    let measureMode = $state(false);
    let measureSignals: RenderedSignal[] = $state([]);
    let measurePanel: MeasurePanel | undefined = $state(undefined);

    // Data editor
    let pendingPreviewSignal: RenderedSignal | null = $state(null);
    let savingEdit = $state(false);
    let fxDataEditorRef: FxDataEditorSection | undefined = $state(undefined);
    let editorDirtyCount = $state(0);

    // All configured FX pair slugs (from backend, for FxPair signal dropdown)
    let allConfiguredSlugs: string[] = $state([]);

    // Panel states before edit mode (to restore when exiting)
    let savedPanelStates: { aesthetics: boolean; measures: boolean; signals: boolean } | null = $state(null);

    // =========================================================================
    // Derived
    // =========================================================================

    let inverted = $derived(data.inverted);
    let displayBase = $derived(data.urlBase);
    let displayQuote = $derived(data.urlQuote);

    let lastRate = $derived.by(() => {
        if (chartData.length === 0) return null;
        const last = chartData[chartData.length - 1];
        return inverted && last.rate !== 0 ? 1 / last.rate : last.rate;
    });

    let deltaPercent = $derived.by(() => {
        if (chartData.length < 2) return null;
        const first = chartData[0].rate;
        const last = chartData[chartData.length - 1].rate;
        if (first === 0) return null;
        const pct = ((last - first) / first) * 100;
        return inverted ? -pct : pct;
    });

    let lastDate = $derived(chartData.length > 0 ? chartData[chartData.length - 1].date : null);

    let lineData: LineDataPoint[] = $derived(chartData.map((d) => ({
        date: d.date,
        value: inverted && d.rate !== 0 ? 1 / d.rate : d.rate,
        staleDays: d.backwardFillInfo?.daysBack ?? 0,
    })));

    // Computed overlay signals from settings
    let overlaySignals: RenderedSignal[] = $derived.by(() => {
        const rendered: RenderedSignal[] = [];
        for (const cfg of signals) {
            const instance = signalFromConfig(cfg);
            if (!instance) continue;

            // For FxPairSignal: resolve data from the TimeSeriesStore before rendering
            if (cfg.signalType === 'fx-pair') {
                const pairSlug = String(cfg.params.pairSlug || '');
                if (!pairSlug) continue;
                try {
                    const store = getFxStore(pairSlug);
                    const storeData = store.getAllSorted();
                    if (storeData.length === 0) continue;
                    instance.params._resolvedData = storeData.map(d => ({
                        date: d.date,
                        value: d.rate,
                    }));
                } catch {
                    continue; // Store not available for this pair
                }
            }

            const results = instance.renderMulti(lineData, viewMode);
            for (const result of results) {
                if (result.data.length > 0) rendered.push(result);
            }
        }
        return rendered;
    });

    /** Combined overlay signals: computed from settings + measure signals */
    let allOverlaySignals: RenderedSignal[] = $derived([
        ...overlaySignals,
        ...measureSignals,
        ...(pendingPreviewSignal ? [pendingPreviewSignal] : []),
    ]);

    let configuredPairSlugs = $derived(allConfiguredSlugs);

    // Provider config: build editRoutes for the modal
    let editRoutes = $derived.by(() => {
        return providers.map(p => p.chainSteps ?? [{from: data.canonicalBase, to: data.canonicalQuote, provider: p.providerCode}]);
    });

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        // Persist the inversion state from the URL so FxCard reflects it on back-navigation
        setCardInverted(data.canonicalSlug, data.inverted);

        await Promise.all([
            ensureCurrenciesLoaded(get(currentLanguage)),
            loadChartData(),
            loadProviders(),
            loadAvailableProviders(),
        ]);
        // Force flag reactivity after currencies load
        flagVersion++;
    });

    // Trigger flag re-evaluation when currencies finish loading
    let flagVersion = $state(0);
    let baseFlag = $derived.by(() => {
        void flagVersion;
        return getCurrencyInfo(displayBase).flag_emoji;
    });
    let quoteFlag = $derived.by(() => {
        void flagVersion;
        return getCurrencyInfo(displayQuote).flag_emoji;
    });

    // ResizeObserver for adaptive filter bar layout (same breakpoints as FX list page)
    $effect(() => {
        const el = filterBarRef;
        if (!el) return;
        const ro = new ResizeObserver(([entry]) => {
            const w = entry.contentRect.width;
            if (w >= 730) layoutMode = 'wide';
            else if (w >= 550) layoutMode = 'tablet';
            else layoutMode = 'mobile';
            showActionLabels = w >= 600;
        });
        ro.observe(el);
        return () => ro.disconnect();
    });

    // =========================================================================
    // Data Loading (same as before, unchanged logic)
    // =========================================================================

    async function loadChartData() {
        loading = true;
        error = null;
        const store = getFxStore(data.canonicalSlug);
        const gaps = store.getMissingIntervals(dateStart, dateEnd);

        if (gaps.length === 0) {
            chartData = store.getRange(dateStart, dateEnd).data;
            loading = false;
            return;
        }

        try {
            const convertRequests = gaps.map(gap => ({
                from_amount: {code: data.canonicalBase, amount: 1},
                to: data.canonicalQuote,
                date_range: {start: gap.start, end: gap.end},
            }));
            const response = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post(convertRequests);
            const results = (response as any)?.results || [];
            const points: FxDataPoint[] = results.map((r: any) => apiResultToFxDataPoint(r));
            store.merge(points);
            chartData = store.getRange(dateStart, dateEnd).data;
        } catch (e: any) {
            const existingData = store.getRange(dateStart, dateEnd).data;
            if (existingData.length > 0) {
                chartData = existingData;
            } else if (e?.response?.status === 404) {
                error = 'No rate data available for this range. Try syncing first or adjusting the date range.';
            } else {
                console.error('Failed to load chart data:', e);
                error = e?.message || 'Failed to load rates';
            }
        } finally {
            loading = false;
        }
    }

    async function loadProviders() {
        try {
            const response = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
            const items = (response as any)?.items || [];

            // Extract ALL unique configured pair slugs (for FxPair signal dropdown)
            const slugSet = new Set<string>();
            for (const i of items) {
                const b = i.base < i.quote ? i.base : i.quote;
                const q = i.base < i.quote ? i.quote : i.base;
                slugSet.add(`${b}-${q}`);
            }
            allConfiguredSlugs = [...slugSet].sort();

            // Filter routes for current pair only
            providers = items
                .filter((i: any) =>
                    ((i.base === data.canonicalBase && i.quote === data.canonicalQuote) ||
                        (i.base === data.canonicalQuote && i.quote === data.canonicalBase)) &&
                    !(i.chain_steps?.length === 1 && i.chain_steps[0].provider === 'MANUAL')
                )
                .sort((a: any, b: any) => a.priority - b.priority)
                .map((i: any) => {
                    const steps = i.chain_steps ?? [];
                    return {
                        providerCode: steps.length === 1
                            ? steps[0].provider
                            : 'CHAIN:' + steps.map((s: any) => s.provider).join('+'),
                        priority: i.priority,
                        chainSteps: steps,
                    };
                });
        } catch (e) {
            console.error('Failed to load providers:', e);
        }
    }

    async function loadAvailableProviders() {
        try {
            const response = await zodiosApi.list_providers_api_v1_fx_providers_get();
            availableProviders = (response as any[]).map((p: any) => ({code: p.code, name: p.name}));
        } catch (e) {
            console.error('Failed to load available providers:', e);
        }
    }

    // =========================================================================
    // Actions
    // =========================================================================

    async function handleRefresh() {
        const store = getFxStore(data.canonicalSlug);
        store.invalidateRange(dateStart, dateEnd);
        await loadChartData();
    }

    async function handleSync() {
        syncing = true;
        try {
            const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                pairs: [data.canonicalSlug],
                start: dateStart,
                end: dateEnd,
            });
            const r = (response as any)?.results?.[0];
            if (r) {
                const label = data.canonicalSlug.replace('-', '/');
                const tr = get(t);
                if (r.status === 'ok') {
                    toasts.success(tr('fx.sync.toastOk', {
                        values: {
                            pair: label,
                            fetched: r.points_fetched ?? 0,
                            changed: r.points_changed ?? 0,
                            provider: r.provider_used ?? '?'
                        }
                    }));
                } else if (r.status === 'partial') {
                    toasts.warning(tr('fx.sync.toastPartial', {values: {pair: label, changed: r.points_changed ?? 0}}));
                } else if (r.status === 'skipped') {
                    toasts.info(tr('fx.sync.toastSkipped', {values: {pair: label}}));
                } else {
                    toasts.error(tr('fx.sync.toastFailed', {values: {pair: label}}) + (r.message ? ': ' + r.message : ''));
                }
            }
            await handleRefresh();
        } catch (e: any) {
            console.error('Sync failed:', e);
            error = 'Sync failed: ' + (e?.message || 'unknown error');
        } finally {
            syncing = false;
        }
    }

    function handleDateRangeChange(newStart: string, newEnd: string) {
        dateStart = newStart;
        dateEnd = newEnd;
        loadChartData();
    }

    function handleMeasureClick(date: string, value: number) {
        measurePanel?.addPoint(date, value);
    }

    function handleAestheticsChange(values: {
        colorByBaseline: boolean; areaFill: boolean; gridLines: boolean;
        staleGradient: boolean; yAxisMode: 'auto' | 'include0' | 'custom';
        yAxisMin: number | undefined; yAxisMax: number | undefined;
    }) {
        setPairSettings(data.canonicalSlug, {...settings, ...values, signals: [...signals]});
    }

    function handleSignalsChange(newSignals: SignalConfig[]) {
        setPairSettings(data.canonicalSlug, {...settings, signals: JSON.parse(JSON.stringify(newSignals))});
    }

    async function handleSyncPair(slug: string) {
        try {
            syncing = true;
            const tr = get(t);
            await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                pairs: [slug], start: dateStart, end: dateEnd,
            });
            toasts.success(tr('fx.sync.toastSuccess', {values: {pair: slug}}));
            // If it's our pair, refresh chart
            if (slug === data.canonicalSlug) await handleRefresh();
        } catch (e: any) {
            toasts.error('Sync failed: ' + (e?.message || 'unknown'));
        } finally {
            syncing = false;
        }
    }

    function handleDetailPair(slug: string) {
        goto(`/fx/${slug}`);
    }

    // Provider handlers (unchanged logic)
    async function handleAddProvider(detail: { providerCode: string; priority: number; chainSteps?: Array<{ from: string; to: string; provider: string }> }) {
        try {
            const steps = detail.chainSteps ?? [{from: data.canonicalBase, to: data.canonicalQuote, provider: detail.providerCode}];
            await zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post([{
                base: data.canonicalBase, quote: data.canonicalQuote, chain_steps: steps, priority: detail.priority,
            }]);
            await loadProviders();
        } catch (e: any) {
            error = 'Failed to add provider: ' + (e?.message || 'unknown error');
        }
    }

    async function handleRemoveProvider(detail: { providerCode: string }) {
        try {
            await applyProviderDiff(providers.filter(p => p.providerCode !== detail.providerCode));
            await loadProviders();
        } catch (e: any) {
            error = 'Failed to remove provider: ' + (e?.message || 'unknown error');
        }
    }

    async function handleSaveProviderOrder(reorderedProviders: Array<{ providerCode: string; priority: number }>) {
        try {
            await applyProviderDiff(reorderedProviders);
            await loadProviders();
        } catch (e: any) {
            error = 'Failed to save provider order: ' + (e?.message || 'unknown error');
        }
    }

    async function applyProviderDiff(desired: Array<{ providerCode: string; priority: number; chainSteps?: Array<{ from: string; to: string; provider: string }> }>) {
        const desiredNormalized = desired.map((p, idx) => ({
            providerCode: p.providerCode,
            priority: idx + 1,
            chainSteps: p.chainSteps ?? [{from: data.canonicalBase, to: data.canonicalQuote, provider: p.providerCode}],
        }));

        if (desiredNormalized.length > 0) {
            await zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post(
                desiredNormalized.map(p => ({
                    base: data.canonicalBase, quote: data.canonicalQuote, chain_steps: p.chainSteps, priority: p.priority,
                }))
            );
        }

        const freshResp = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
        const freshForPair = (freshResp.items ?? []).filter(
            (s: any) => s.base === data.canonicalBase && s.quote === data.canonicalQuote
        );

        const desiredPriorities = new Set(desiredNormalized.map(p => p.priority));
        const toDelete = freshForPair.filter((s: any) => !desiredPriorities.has(s.priority));

        if (toDelete.length > 0) {
            await zodiosApi.delete_routes_bulk_api_v1_fx_providers_routes_delete(
                toDelete.map((s: any) => ({base: data.canonicalBase, quote: data.canonicalQuote, priority: s.priority}))
            );
        }
    }

    /** Handle provider modal save — reload providers after edit */
    async function handleProviderModalCreated(detail: { base: string; quote: string; hasRealProvider: boolean }) {
        await loadProviders();
        showProviderModal = false;
    }

    // =========================================================================
    // Swap direction (Step 8+9)
    // =========================================================================

    function doSwap() {
        // Exit edit mode if active
        if (showDataEditor) {
            showDataEditor = false;
            pendingPreviewSignal = null;
            if (savedPanelStates) {
                showAesthetics = savedPanelStates.aesthetics;
                showMeasures = savedPanelStates.measures;
                showSignals = savedPanelStates.signals;
                savedPanelStates = null;
            }
        }
        // Persist inversion state so FxCard shows the same direction on back-navigation
        setCardInverted(data.canonicalSlug, !inverted);
        goto(`/fx/${displayQuote}-${displayBase}`, {replaceState: true});
    }

    function handleSwapDirection() {
        if (!showDataEditor || editorDirtyCount === 0) {
            doSwap();
        } else {
            showSwapConfirm = true;
        }
    }
</script>

<div class="space-y-4" data-testid="fx-detail-page">
    <!-- ======================================================================= -->
    <!-- Header: pair info + back button -->
    <!-- ======================================================================= -->
    <div class="flex items-center gap-3" data-testid="fx-detail-header">
        <button
                data-testid="fx-detail-back-btn"
                class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors"
                onclick={() => goto('/fx')}
                title={$t('fxDetail.backToList')}
        >
            <ArrowLeft size={20}/>
        </button>
        <div class="flex items-center gap-2" data-testid="fx-detail-pair-label">
            <span class="text-2xl">{baseFlag}</span>
            <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">{displayBase}</h2>
            <span class="text-gray-400 dark:text-gray-500 text-lg">→</span>
            <span class="text-2xl">{quoteFlag}</span>
            <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">{displayQuote}</h2>
            <button
                    data-testid="fx-detail-swap-btn"
                    class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    onclick={handleSwapDirection}
                    title={$t('fxDetail.swapDirection')}
            >
                <ArrowLeftRight size={16}/>
            </button>
        </div>
    </div>

    <!-- Error banner -->
    {#if error}
        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-700 dark:text-amber-400 flex items-center gap-2">
            <span>⚠️</span> <span>{error}</span>
            <button class="ml-auto text-xs px-2 py-1 bg-amber-100 dark:bg-amber-900/40 rounded hover:bg-amber-200" onclick={() => error = null}>{$t('common.dismiss')}</button>
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- Filter bar: responsive layout matching FX list page -->
    <!-- wide:   [ datepicker  pair-info ─── actions-2×2 ]  all in one row -->
    <!-- tablet: [ datepicker       ] [ actions-2×2 ]      filters stacked, actions grid right -->
    <!--         [ pair-info        ] [             ]                                           -->
    <!-- mobile: [ datepicker       ]  all stacked centered                                    -->
    <!--         [ pair-info        ]                                                            -->
    <!--         [ actions-row      ]                                                            -->
    <!-- ======================================================================= -->
    <div
            bind:this={filterBarRef}
            data-testid="fx-detail-filter-bar"
            class="flex gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700
               {layoutMode === 'mobile' ? 'flex-col items-center' : 'flex-row items-start justify-between'}"
    >
        <!-- Filters block -->
        <div class="flex gap-3 {layoutMode === 'mobile' ? 'flex-col items-center' : layoutMode === 'wide' ? 'flex-row items-center flex-1' : 'flex-col items-start'}">
            <!-- DateRangePicker -->
            <div class="max-w-md">
                <DateRangePicker
                        bind:start={dateStart}
                        bind:end={dateEnd}
                        bind:activePreset
                        compact={true}
                        onchange={handleDateRangeChange}
                />
            </div>

            <!-- Pair Summary (rate + delta) — no date, already in DateRangePicker -->
            {#if lastRate !== null}
                <div class="flex items-center gap-2 px-3 {layoutMode === 'wide' ? 'border-l border-r border-gray-200 dark:border-slate-600' : ''} {layoutMode === 'tablet' ? 'w-full justify-center' : ''}">
                    <span class="font-mono text-lg font-semibold text-gray-700 dark:text-gray-200">
                        {lastRate.toFixed(4)}
                    </span>
                    {#if deltaPercent !== null}
                        <span class="flex items-center gap-0.5 text-xs font-medium {deltaPercent >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                            {#if deltaPercent >= 0}<TrendingUp size={12}/>{:else}<TrendingDown size={12}/>{/if}
                            {deltaPercent >= 0 ? '+' : ''}{deltaPercent.toFixed(2)}%
                        </span>
                    {/if}
                </div>
            {/if}
        </div>

        <!-- Actions: 2×2 grid (wide+tablet), horizontal row (mobile) -->
        <div class="flex shrink-0 gap-1.5
                    {layoutMode === 'mobile' ? 'flex-row justify-center' : 'grid grid-cols-2'}">
            <!-- Row 1, Col 1: Abs/% segmented toggle -->
            <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden">
                <button
                        class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {viewMode === 'absolute'
                        ? 'bg-libre-green text-white'
                        : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => { viewMode = 'absolute'; }}
                >Abs
                </button>
                <button
                        class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {viewMode === 'percentage'
                        ? 'bg-libre-green text-white'
                        : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => { viewMode = 'percentage'; }}
                >%
                </button>
            </div>
            <!-- Row 1, Col 2: Providers -->
            <button
                    data-testid="fx-detail-provider-btn"
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    onclick={() => showProviderModal = true}
                    title={$t('fxDetail.providers')}
            >
                <Wrench size={14}/>
                {#if showActionLabels}<span>{$t('fxDetail.providers')}</span>{/if}
            </button>
            <!-- Row 2, Col 1: Sync -->
            <button
                    data-testid="fx-detail-sync-btn"
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    onclick={handleSync}
                    disabled={syncing}
                    title={$t('fxDetail.syncFromProvider')}
            >
                <RotateCw size={14} class={syncing ? 'animate-spin' : ''}/>
                {#if showActionLabels}<span>{syncing ? $t('fx.actions.syncing') : $t('common.sync')}</span>{/if}
            </button>
            <!-- Row 2, Col 2: Refresh -->
            <button
                    data-testid="fx-detail-refresh-btn"
                    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                    onclick={handleRefresh}
                    disabled={loading}
                    title={$t('fxDetail.refreshData')}
            >
                <RefreshCw size={14} class={loading ? 'animate-spin' : ''}/>
                {#if showActionLabels}<span>{$t('common.refresh')}</span>{/if}
            </button>
        </div>
    </div>

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Aesthetics (ABOVE chart) -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <button
                data-testid="fx-detail-aesthetics-toggle"
                class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
                onclick={() => showAesthetics = !showAesthetics}
        >
            <span class="flex items-center gap-2">
                <Settings size={15} class="text-libre-green"/>
                {$t('fxDetail.aesthetics')}
            </span>
            <ChevronDown size={15} class="transition-transform {showAesthetics ? 'rotate-180' : ''}"/>
        </button>
        {#if showAesthetics}
            <div data-testid="fx-detail-aesthetics-panel" class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3">
                <ChartAestheticsSection
                        colorByBaseline={settings.colorByBaseline}
                        areaFill={settings.areaFill}
                        gridLines={settings.gridLines}
                        staleGradient={settings.staleGradient}
                        yAxisMode={settings.yAxisMode}
                        yAxisMin={settings.yAxisMin}
                        yAxisMax={settings.yAxisMax}
                        onchange={handleAestheticsChange}
                />
            </div>
        {/if}
    </div>

    <!-- ======================================================================= -->
    <!-- Chart with overlay action buttons (Edit + Add Measure) -->
    <!-- ======================================================================= -->
    <div data-testid="fx-detail-chart" class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4">
        {#if loading && lineData.length === 0}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    <RefreshCw size={24} class="animate-spin text-libre-green mx-auto mb-2"/>
                    <p class="text-sm text-gray-500 dark:text-gray-400">{$t('fxDetail.loadingRates')}</p>
                </div>
            </div>
        {:else if lineData.length > 0}
            <div class="relative">
                <!-- Action buttons: top-right corner of chart -->
                <div class="absolute top-0 right-0 z-10 flex items-center gap-1.5">
                    <button
                            data-testid="fx-detail-measure-btn"
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
                            title={measureMode ? $t('fxDetail.exitMeasure') : $t('fxDetail.addMeasure')}
                    >
                        <Ruler size={16}/>
                    </button>
                    <button
                            data-testid="fx-detail-edit-btn"
                            class="p-1.5 rounded-lg transition-colors {showDataEditor
                            ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 ring-1 ring-amber-300 dark:ring-amber-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                            onclick={() => {
                            if (showDataEditor) {
                                // Exiting edit mode: hide editor, restore panel states
                                showDataEditor = false;
                                pendingPreviewSignal = null;
                                if (savedPanelStates) {
                                    showAesthetics = savedPanelStates.aesthetics;
                                    showMeasures = savedPanelStates.measures;
                                    showSignals = savedPanelStates.signals;
                                    savedPanelStates = null;
                                }
                            } else {
                                // Entering edit mode: save panel states, fold all, show editor
                                savedPanelStates = {aesthetics: showAesthetics, measures: showMeasures, signals: showSignals};
                                showAesthetics = false;
                                showMeasures = false;
                                showSignals = false;
                                showDataEditor = true;
                            }
                        }}
                            title={showDataEditor ? $t('fxDetail.closeEditor') : $t('fxDetail.editRatesBtn')}
                    >
                        <Pencil size={16}/>
                    </button>
                </div>

                <PriceChartFull
                        data={lineData}
                        currency={displayQuote}
                        chartHeight="400px"
                        overlaySignals={allOverlaySignals}
                        colorByBaseline={settings.colorByBaseline}
                        areaFill={settings.areaFill}
                        showGridLines={settings.gridLines}
                        showGradient={settings.staleGradient}
                        yAxisMode={settings.yAxisMode}
                        yAxisMin={settings.yAxisMin}
                        yAxisMax={settings.yAxisMax}
                        measureMode={measureMode}
                        onMeasureClick={handleMeasureClick}
                        onMeasureHover={(date, value) => measurePanel?.updatePendingEnd(date, value)}
                        hideToolbar={true}
                        externalViewMode={viewMode}
                        editMode={showDataEditor}
                        onPointClick={(date, _value) => fxDataEditorRef?.scrollToDate(date)}
                />
            </div>
        {:else}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('fxDetail.noData')}</p>
                    <button
                            class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                            onclick={handleSync}
                            disabled={syncing}
                    >
                        {syncing ? $t('fx.actions.syncing') : $t('fxDetail.syncRates')}
                    </button>
                </div>
            </div>
        {/if}
    </div>

    <!-- ======================================================================= -->
    <!-- Data Editor (shown only when toggled via pencil button) -->
    <!-- ======================================================================= -->
    {#if showDataEditor}
        <div data-testid="fx-detail-editor-panel" class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-amber-200 dark:border-amber-800">
            <div class="flex items-center justify-between px-4 py-3 border-b border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-yellow-900/30 rounded-t-xl">
    <span class="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400">
                    <Pencil size={15}/>
        {$t('fxDetail.editRates')}
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
                        title={$t('fxDetail.closeEditor')}
                >✕
                </button>
            </div>
            <div class="px-4 pb-4 pt-3">
                <FxDataEditorSection
                        bind:this={fxDataEditorRef}
                        base={displayBase}
                        quote={displayQuote}
                        {chartData}
                        bind:saving={savingEdit}
                        bind:dirtyCount={editorDirtyCount}
                        onsave={async (expandedRange) => {
                        if (expandedRange) {
                            dateStart = expandedRange.start;
                            dateEnd = expandedRange.end;
                            activePreset = null;
                        }
                        await handleRefresh();
                        showDataEditor = false;
                        if (savedPanelStates) {
                            showAesthetics = savedPanelStates.aesthetics;
                            showMeasures = savedPanelStates.measures;
                            showSignals = savedPanelStates.signals;
                            savedPanelStates = null;
                        }
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
                        onpendingchange={(signal) => pendingPreviewSignal = signal}
                />
            </div>
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Measures (below DataEditor, above Signals) -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <button
                data-testid="fx-detail-measures-toggle"
                class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
                onclick={() => showMeasures = !showMeasures}
        >
            <span class="flex items-center gap-2">
                <Ruler size={15} class="text-violet-500"/>
                {$t('fxDetail.measures')}
                {#if measureMode}
                    <span class="text-[10px] px-1.5 py-0.5 bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 rounded-full">{$t('measure.active')}</span>
                {/if}
            </span>
            <ChevronDown size={15} class="transition-transform {showMeasures ? 'rotate-180' : ''}"/>
        </button>
        <!-- Single MeasurePanel instance — always mounted, hidden via CSS to preserve state -->
        <div data-testid="fx-detail-measures-panel" class={showMeasures ? "px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3" : "hidden"}>
            <MeasurePanel
                    bind:this={measurePanel}
                    chartData={lineData}
                    overlaySignals={overlaySignals}
                    pairLabel={`${baseFlag} ${displayBase} → ${quoteFlag} ${displayQuote}`}
                    onmeasureschange={(m) => measureSignals = m}
                    onmeasuremodechange={(active) => measureMode = active}
                    {viewMode}
            />
        </div>
    </div>

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Signals (below Measures) -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <button
                data-testid="fx-detail-signals-toggle"
                class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
                onclick={() => showSignals = !showSignals}
        >
            <span class="flex items-center gap-2">
                <TrendingUp size={15} class="text-blue-500"/>
                {$t('fxDetail.signals')}
            </span>
            <ChevronDown size={15} class="transition-transform {showSignals ? 'rotate-180' : ''}"/>
        </button>
        {#if showSignals}
            <div data-testid="fx-detail-signals-panel" class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3">
                <ChartSignalsSection
                        signals={[...signals]}
                        availablePairs={configuredPairSlugs}
                        onchange={handleSignalsChange}
                        onsyncpair={handleSyncPair}
                        ondetailpair={handleDetailPair}
                />
            </div>
        {/if}
    </div>


    <!-- ======================================================================= -->
    <!-- Provider Configuration Modal (reuses FxPairAddModal in editMode) -->
    <!-- ======================================================================= -->
    <div data-testid="fx-detail-provider-modal">
    <FxPairAddModal
            bind:open={showProviderModal}
            editMode={true}
            editBase={data.canonicalBase}
            editQuote={data.canonicalQuote}
            {editRoutes}
            dateStart={dateStart}
            dateEnd={dateEnd}
            oncreated={handleProviderModalCreated}
            onclose={() => showProviderModal = false}
    />
    </div>

    <!-- Confirm modal for swap direction while editing -->
    <ConfirmModal
            open={showSwapConfirm}
            title={$t('fxDetail.swapConfirmTitle')}
            message={$t('fxDetail.swapConfirmMessage')}
            confirmText={$t('common.continue')}
            cancelText={$t('common.cancel')}
            warning={true}
            onConfirm={() => { showSwapConfirm = false; doSwap(); }}
            onCancel={() => showSwapConfirm = false}
    />
</div>

