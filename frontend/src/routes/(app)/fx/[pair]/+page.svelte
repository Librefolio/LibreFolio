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
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import {get} from 'svelte/store';
    import {zodiosApi} from '$lib/api';
    import {ArrowLeft, ArrowLeftRight, ChevronDown, Pencil, RefreshCw, RotateCcw, Settings, TrendingDown, TrendingUp, Ruler, Wrench} from 'lucide-svelte';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import PriceChartFull from '$lib/components/charts/PriceChartFull.svelte';
    import ChartAestheticsSection from '$lib/components/charts/ChartAestheticsSection.svelte';
    import ChartSignalsSection from '$lib/components/charts/ChartSignalsSection.svelte';
    import MeasurePanel from '$lib/components/charts/MeasurePanel.svelte';
    import FxDataEditorSection from '$lib/components/fx/FxDataEditorSection.svelte';
    import FxPairAddModal from '$lib/components/fx/FxPairAddModal.svelte';
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {RenderedSignal, SignalConfig} from '$lib/charts/signals';
    import {signalFromConfig} from '$lib/charts/signals';
    import {getSettingsForPair, setPairSettings} from '$lib/stores/chartSettingsStore.svelte';
    import {getCurrencyInfo, ensureCurrenciesLoaded, isCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {currentLanguage} from '$lib/stores/language';
    import type {ViewMode} from '$lib/components/charts/ChartToolbar.svelte';
    import {
        getFxStore, apiResultToFxDataPoint, getRegisteredPairs,
        type FxDataPoint
    } from '$lib/stores/fxStoreRegistry';

    // =========================================================================
    // Page data
    // =========================================================================

    interface Props {
        data: {base: string; quote: string; slug: string};
    }
    let {data}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let chartData: FxDataPoint[] = $state([]);
    let loading = $state(true);
    let error: string | null = $state(null);
    let inverted = $state(false);
    let syncing = $state(false);

    // Date range (default 3M)
    let dateEnd = $state(new Date().toISOString().slice(0, 10));
    let dateStart = $state((() => { const d = new Date(); d.setMonth(d.getMonth() - 3); return d.toISOString().slice(0, 10); })());
    let activePreset: any = $state('3M');

    // View mode (abs/%) — controlled by the page, not by chart toolbar
    let viewMode: ViewMode = $state('absolute');

    // Provider config
    let providers: Array<{providerCode: string; priority: number; chainSteps?: Array<{from: string; to: string; provider: string}>}> = $state([]);
    let availableProviders: Array<{code: string; name: string}> = $state([]);

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

    // Chart settings (from store) — derived so they react to slug changes
    let settings = $derived(getSettingsForPair(data.slug));
    let signals = $derived<SignalConfig[]>([...settings.signals]);

    // Measure panel
    let measureMode = $state(false);
    let measureSignals: RenderedSignal[] = $state([]);
    let measurePanel: MeasurePanel | undefined = $state(undefined);

    // Data editor
    let pendingEditPoints: LineDataPoint[] = $state([]);
    let savingEdit = $state(false);

    // Panel states before edit mode (to restore when exiting)
    let savedPanelStates: {aesthetics: boolean; measures: boolean; signals: boolean} | null = $state(null);

    // =========================================================================
    // Derived
    // =========================================================================

    let displayBase = $derived(inverted ? data.quote : data.base);
    let displayQuote = $derived(inverted ? data.base : data.quote);

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
            const results = instance.renderMulti(lineData, settings.colorByBaseline ? 'absolute' : 'absolute');
            for (const result of results) {
                if (result.data.length > 0) rendered.push(result);
            }
        }
        return rendered;
    });

    /** Combined overlay signals: computed from settings + measure signals */
    let allOverlaySignals: RenderedSignal[] = $derived([...overlaySignals, ...measureSignals]);

    let configuredPairSlugs = $derived(getRegisteredPairs());

    // Provider config: build editRoutes for the modal
    let editRoutes = $derived.by(() => {
        return providers.map(p => p.chainSteps ?? [{from: data.base, to: data.quote, provider: p.providerCode}]);
    });

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
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
    let baseFlag = $derived.by(() => { void flagVersion; return getCurrencyInfo(displayBase).flag_emoji; });
    let quoteFlag = $derived.by(() => { void flagVersion; return getCurrencyInfo(displayQuote).flag_emoji; });

    // ResizeObserver for adaptive filter bar layout (same breakpoints as FX list page)
    $effect(() => {
        const el = filterBarRef;
        if (!el) return;
        const ro = new ResizeObserver(([entry]) => {
            const w = entry.contentRect.width;
            if (w >= 810) layoutMode = 'wide';
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
        const store = getFxStore(data.slug);
        const gaps = store.getMissingIntervals(dateStart, dateEnd);

        if (gaps.length === 0) {
            chartData = store.getRange(dateStart, dateEnd).data;
            loading = false;
            return;
        }

        try {
            const convertRequests = gaps.map(gap => ({
                from_amount: {code: data.base, amount: 1},
                to: data.quote,
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
            providers = items
                .filter((i: any) =>
                    ((i.base === data.base && i.quote === data.quote) ||
                    (i.base === data.quote && i.quote === data.base)) &&
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
        const store = getFxStore(data.slug);
        store.invalidateRange(dateStart, dateEnd);
        await loadChartData();
    }

    async function handleSync() {
        syncing = true;
        try {
            const response = await zodiosApi.sync_rates_api_v1_fx_currencies_sync_post({
                pairs: [data.slug],
                start: dateStart,
                end: dateEnd,
            });
            const r = (response as any)?.results?.[0];
            if (r) {
                const label = data.slug.replace('-', '/');
                const tr = get(t);
                if (r.status === 'ok') {
                    toasts.success(tr('fx.sync.toastOk', {values: {pair: label, fetched: r.points_fetched ?? 0, changed: r.points_changed ?? 0, provider: r.provider_used ?? '?'}}));
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
        setPairSettings(data.slug, {...settings, ...values, signals: [...signals]});
    }

    function handleSignalsChange(newSignals: SignalConfig[]) {
        setPairSettings(data.slug, {...settings, signals: JSON.parse(JSON.stringify(newSignals))});
    }

    // Provider handlers (unchanged logic)
    async function handleAddProvider(detail: {providerCode: string; priority: number; chainSteps?: Array<{from: string; to: string; provider: string}>}) {
        try {
            const steps = detail.chainSteps ?? [{from: data.base, to: data.quote, provider: detail.providerCode}];
            await zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post([{
                base: data.base, quote: data.quote, chain_steps: steps, priority: detail.priority,
            }]);
            await loadProviders();
        } catch (e: any) {
            error = 'Failed to add provider: ' + (e?.message || 'unknown error');
        }
    }

    async function handleRemoveProvider(detail: {providerCode: string}) {
        try {
            await applyProviderDiff(providers.filter(p => p.providerCode !== detail.providerCode));
            await loadProviders();
        } catch (e: any) {
            error = 'Failed to remove provider: ' + (e?.message || 'unknown error');
        }
    }

    async function handleSaveProviderOrder(reorderedProviders: Array<{providerCode: string; priority: number}>) {
        try {
            await applyProviderDiff(reorderedProviders);
            await loadProviders();
        } catch (e: any) {
            error = 'Failed to save provider order: ' + (e?.message || 'unknown error');
        }
    }

    async function applyProviderDiff(desired: Array<{providerCode: string; priority: number; chainSteps?: Array<{from: string; to: string; provider: string}>}>) {
        const desiredNormalized = desired.map((p, idx) => ({
            providerCode: p.providerCode,
            priority: idx + 1,
            chainSteps: p.chainSteps ?? [{from: data.base, to: data.quote, provider: p.providerCode}],
        }));

        if (desiredNormalized.length > 0) {
            await zodiosApi.create_routes_bulk_api_v1_fx_providers_routes_post(
                desiredNormalized.map(p => ({
                    base: data.base, quote: data.quote, chain_steps: p.chainSteps, priority: p.priority,
                }))
            );
        }

        const freshResp = await zodiosApi.list_routes_api_v1_fx_providers_routes_get();
        const freshForPair = (freshResp.items ?? []).filter(
            (s: any) => s.base === data.base && s.quote === data.quote
        );

        const desiredPriorities = new Set(desiredNormalized.map(p => p.priority));
        const toDelete = freshForPair.filter((s: any) => !desiredPriorities.has(s.priority));

        if (toDelete.length > 0) {
            await zodiosApi.delete_routes_bulk_api_v1_fx_providers_routes_delete(
                toDelete.map((s: any) => ({base: data.base, quote: data.quote, priority: s.priority}))
            );
        }
    }

    /** Handle provider modal save — reload providers after edit */
    async function handleProviderModalCreated(detail: {base: string; quote: string; hasRealProvider: boolean}) {
        await loadProviders();
        showProviderModal = false;
    }
</script>

<div class="space-y-4">
    <!-- ======================================================================= -->
    <!-- Header: pair info + back button -->
    <!-- ======================================================================= -->
    <div class="flex items-center gap-3">
        <button
            class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors"
            onclick={() => goto('/fx')}
            title="Back to FX list"
        >
            <ArrowLeft size={20} />
        </button>
        <div class="flex items-center gap-2">
            <span class="text-2xl">{baseFlag}</span>
            <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">{displayBase}</h2>
            <span class="text-gray-400 dark:text-gray-500 text-lg">→</span>
            <span class="text-2xl">{quoteFlag}</span>
            <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">{displayQuote}</h2>
            <button
                class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                onclick={() => inverted = !inverted}
                title="Swap direction"
            >
                <ArrowLeftRight size={16} />
            </button>
        </div>
    </div>

    <!-- Error banner -->
    {#if error}
        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-700 dark:text-amber-400 flex items-center gap-2">
            <span>⚠️</span> <span>{error}</span>
            <button class="ml-auto text-xs px-2 py-1 bg-amber-100 dark:bg-amber-900/40 rounded hover:bg-amber-200" onclick={() => error = null}>Dismiss</button>
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
        class="flex gap-3 p-4 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700
               {layoutMode === 'mobile' ? 'flex-col items-center' : 'flex-row items-center justify-between'}"
    >
        <!-- Filters block -->
        <div class="flex gap-3 {layoutMode === 'mobile' ? 'flex-col items-center' : layoutMode === 'wide' ? 'flex-row items-center flex-1' : 'flex-col items-center'}">
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
                <div class="flex items-center gap-2 px-3 {layoutMode === 'wide' ? 'border-l border-r border-gray-200 dark:border-slate-600' : ''}">
                    <span class="font-mono text-lg font-semibold text-gray-700 dark:text-gray-200">
                        {lastRate.toFixed(4)}
                    </span>
                    {#if deltaPercent !== null}
                        <span class="flex items-center gap-0.5 text-xs font-medium {deltaPercent >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                            {#if deltaPercent >= 0}<TrendingUp size={12} />{:else}<TrendingDown size={12} />{/if}
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
                >Abs</button>
                <button
                    class="flex-1 px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors {viewMode === 'percentage'
                        ? 'bg-libre-green text-white'
                        : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => { viewMode = 'percentage'; }}
                >%</button>
            </div>
            <!-- Row 1, Col 2: Providers -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={() => showProviderModal = true}
                title="Configure providers"
            >
                <Wrench size={14} />
                {#if showActionLabels}<span>Providers</span>{/if}
            </button>
            <!-- Row 2, Col 1: Sync -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={handleSync}
                disabled={syncing}
                title="Sync rates from provider"
            >
                <RotateCcw size={14} class={syncing ? 'animate-spin' : ''} />
                {#if showActionLabels}<span>{syncing ? 'Syncing...' : 'Sync'}</span>{/if}
            </button>
            <!-- Row 2, Col 2: Refresh -->
            <button
                class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs whitespace-nowrap bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors"
                onclick={handleRefresh}
                disabled={loading}
                title="Refresh data"
            >
                <RefreshCw size={14} class={loading ? 'animate-spin' : ''} />
                {#if showActionLabels}<span>Refresh</span>{/if}
            </button>
        </div>
    </div>

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Aesthetics (ABOVE chart) -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <button
            class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
            onclick={() => showAesthetics = !showAesthetics}
        >
            <span class="flex items-center gap-2">
                <Settings size={15} class="text-libre-green" />
                Aesthetics
            </span>
            <ChevronDown size={15} class="transition-transform {showAesthetics ? 'rotate-180' : ''}" />
        </button>
        {#if showAesthetics}
            <div class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3">
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
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4">
        {#if loading && lineData.length === 0}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    <RefreshCw size={24} class="animate-spin text-libre-green mx-auto mb-2" />
                    <p class="text-sm text-gray-500 dark:text-gray-400">Loading rates...</p>
                </div>
            </div>
        {:else if lineData.length > 0}
            <div class="relative">
                <!-- Action buttons: top-right corner of chart -->
                <div class="absolute top-0 right-0 z-10 flex items-center gap-1.5">
                    <button
                        class="p-1.5 rounded-lg transition-colors {measureMode
                            ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 ring-1 ring-violet-300 dark:ring-violet-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200'}"
                        onclick={() => {
                            if (measureMode) {
                                measurePanel?.stopMeasureMode();
                            } else {
                                showMeasures = true;
                                measurePanel?.startMeasureMode();
                            }
                        }}
                        title={measureMode ? 'Exit measure mode' : 'Add measurement'}
                    >
                        <Ruler size={16} />
                    </button>
                    <button
                        class="p-1.5 rounded-lg transition-colors {showDataEditor
                            ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 ring-1 ring-amber-300 dark:ring-amber-700'
                            : 'bg-white/80 dark:bg-slate-700/80 text-amber-500 hover:bg-amber-50 dark:hover:bg-slate-600 hover:text-amber-600'}"
                        onclick={() => {
                            if (showDataEditor) {
                                // Exiting edit mode: hide editor, restore panel states
                                showDataEditor = false;
                                pendingEditPoints = [];
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
                        title={showDataEditor ? 'Close editor' : 'Edit rates'}
                    >
                        <Pencil size={16} />
                    </button>
                </div>

                <PriceChartFull
                    data={lineData}
                    pendingData={pendingEditPoints}
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
                    hideToolbar={true}
                    externalViewMode={viewMode}
                />
            </div>
        {:else}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    <p class="text-gray-400 dark:text-gray-500 mb-3">No rate data available for this range.</p>
                    <button
                        class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                        onclick={handleSync}
                        disabled={syncing}
                    >
                        {syncing ? 'Syncing...' : 'Sync Rates'}
                    </button>
                </div>
            </div>
        {/if}
    </div>

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Measures (below chart, above Signals) -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <button
            class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
            onclick={() => showMeasures = !showMeasures}
        >
            <span class="flex items-center gap-2">
                <Ruler size={15} class="text-violet-500" />
                Measures
                {#if measureMode}
                    <span class="text-[10px] px-1.5 py-0.5 bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400 rounded-full">Active — click chart</span>
                {/if}
            </span>
            <ChevronDown size={15} class="transition-transform {showMeasures ? 'rotate-180' : ''}" />
        </button>
        {#if showMeasures}
            <div class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3">
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
        {/if}
    </div>

    <!-- ======================================================================= -->
    <!-- Foldable Panel: Signals (below Measures) -->
    <!-- ======================================================================= -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700">
        <button
            class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors rounded-xl"
            onclick={() => showSignals = !showSignals}
        >
            <span class="flex items-center gap-2">
                <TrendingUp size={15} class="text-blue-500" />
                Signals
            </span>
            <ChevronDown size={15} class="transition-transform {showSignals ? 'rotate-180' : ''}" />
        </button>
        {#if showSignals}
            <div class="px-4 pb-4 border-t border-gray-100 dark:border-slate-700 pt-3">
                <ChartSignalsSection
                    signals={[...signals]}
                    availablePairs={configuredPairSlugs}
                    onchange={handleSignalsChange}
                />
            </div>
        {/if}
    </div>

    <!-- ======================================================================= -->
    <!-- Data Editor (shown only when toggled via pencil button) -->
    <!-- ======================================================================= -->
    {#if showDataEditor}
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-amber-200 dark:border-amber-800">
            <div class="flex items-center justify-between px-4 py-3 border-b border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-900/10 rounded-t-xl">
                <span class="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400">
                    <Pencil size={15} />
                    Edit Rates
                </span>
                <button
                    class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    onclick={() => {
                        showDataEditor = false;
                        pendingEditPoints = [];
                        if (savedPanelStates) {
                            showAesthetics = savedPanelStates.aesthetics;
                            showMeasures = savedPanelStates.measures;
                            showSignals = savedPanelStates.signals;
                            savedPanelStates = null;
                        }
                    }}
                    title="Close editor"
                >✕</button>
            </div>
            <div class="px-4 pb-4 pt-3">
                <FxDataEditorSection
                    base={displayBase}
                    quote={displayQuote}
                    {chartData}
                    bind:saving={savingEdit}
                    onsave={async () => {
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
                        pendingEditPoints = [];
                        if (savedPanelStates) {
                            showAesthetics = savedPanelStates.aesthetics;
                            showMeasures = savedPanelStates.measures;
                            showSignals = savedPanelStates.signals;
                            savedPanelStates = null;
                        }
                    }}
                    onpendingchange={(points) => pendingEditPoints = points}
                />
            </div>
        </div>
    {/if}

    <!-- ======================================================================= -->
    <!-- Provider Configuration Modal (reuses FxPairAddModal in editMode) -->
    <!-- ======================================================================= -->
    <FxPairAddModal
        bind:open={showProviderModal}
        editMode={true}
        editBase={data.base}
        editQuote={data.quote}
        {editRoutes}
        dateStart={dateStart}
        dateEnd={dateEnd}
        oncreated={handleProviderModalCreated}
        onclose={() => showProviderModal = false}
    />
</div>

