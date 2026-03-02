<script lang="ts">
    /**
     * FX Pair Detail Page
     *
     * Shows full chart with toolbar, edit mode, and provider configuration.
     * Reuses TimeSeriesStore from the global registry (shared with FxCard).
     */
    import {onMount} from 'svelte';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {ArrowLeft, ArrowLeftRight, Pencil, RefreshCw, RotateCcw, TrendingDown, TrendingUp, X} from 'lucide-svelte';
    import PriceChartFull from '$lib/components/charts/PriceChartFull.svelte';
    import FxEditSection from '$lib/components/fx/FxEditSection.svelte';
    import FxProviderConfig from '$lib/components/fx/FxProviderConfig.svelte';
    import DateRangePicker from '$lib/components/ui/DateRangePicker.svelte';
    import type {ParsedRow} from '$lib/components/fx/CsvEditor.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {
        getFxStore, apiResultToFxDataPoint,
        type FxDataPoint
    } from '$lib/stores/fxStoreRegistry';

    // =========================================================================
    // Page data
    // =========================================================================

    export let data: {base: string; quote: string; slug: string};

    // =========================================================================
    // State
    // =========================================================================

    let chartData: FxDataPoint[] = [];
    let loading = true;
    let error: string | null = null;
    let inverted = false;
    let editMode = false;
    let syncing = false;
    let savingEdit = false;
    let editSection: FxEditSection;

    // Date range (default 3M — same as list page)
    let dateStart = '';
    let dateEnd = '';
    let activePreset: any = '3M';

    // Provider config
    let providers: Array<{providerCode: string; priority: number}> = [];
    let availableProviders: Array<{code: string; name: string}> = [];

    // =========================================================================
    // Derived
    // =========================================================================

    $: {
        if (!dateEnd) {
            const now = new Date();
            dateEnd = now.toISOString().slice(0, 10);
        }
        if (!dateStart) {
            const d = new Date();
            d.setMonth(d.getMonth() - 3);
            dateStart = d.toISOString().slice(0, 10);
        }
    }

    $: displayBase = inverted ? data.quote : data.base;
    $: displayQuote = inverted ? data.base : data.quote;

    $: lastRate = (() => {
        if (chartData.length === 0) return null;
        const last = chartData[chartData.length - 1];
        return inverted && last.rate !== 0 ? 1 / last.rate : last.rate;
    })();

    $: deltaPercent = (() => {
        if (chartData.length < 2) return null;
        const first = chartData[0].rate;
        const last = chartData[chartData.length - 1].rate;
        if (first === 0) return null;
        const pct = ((last - first) / first) * 100;
        return inverted ? -pct : pct;
    })();

    $: lastDate = chartData.length > 0 ? chartData[chartData.length - 1].date : null;

    // Convert to LineDataPoint for chart
    $: lineData = chartData.map((d): LineDataPoint => ({
        date: d.date,
        value: inverted && d.rate !== 0 ? 1 / d.rate : d.rate,
        staleDays: d.backwardFillInfo?.daysBack ?? 0,
    }));

    // Currency flag helper
    function currencyFlag(code: string): string {
        const map: Record<string, string> = {
            EUR: '🇪🇺', USD: '🇺🇸', GBP: '🇬🇧', JPY: '🇯🇵', CHF: '🇨🇭',
            CAD: '🇨🇦', AUD: '🇦🇺', NZD: '🇳🇿', CNY: '🇨🇳', SEK: '🇸🇪',
            NOK: '🇳🇴', DKK: '🇩🇰', PLN: '🇵🇱', CZK: '🇨🇿', HUF: '🇭🇺',
            RON: '🇷🇴', BGN: '🇧🇬', TRY: '🇹🇷', BRL: '🇧🇷', MXN: '🇲🇽',
            INR: '🇮🇳', KRW: '🇰🇷', SGD: '🇸🇬', HKD: '🇭🇰', ZAR: '🇿🇦',
        };
        return map[code] || '💱';
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(async () => {
        await Promise.all([loadChartData(), loadProviders(), loadAvailableProviders()]);
    });

    // =========================================================================
    // Data Loading
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

            const response = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post(
                convertRequests
            );

            const results = (response as any)?.results || [];
            const points: FxDataPoint[] = results.map((r: any) => apiResultToFxDataPoint(r));
            store.merge(points);
            chartData = store.getRange(dateStart, dateEnd).data;
        } catch (e: any) {
            // Gracefully handle 404 (no data in that range)
            const existingData = store.getRange(dateStart, dateEnd).data;
            if (existingData.length > 0) {
                chartData = existingData;
            } else if (e?.response?.status === 404) {
                // Show informative message instead of raw error
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
            const response = await zodiosApi.list_pair_sources_api_v1_fx_providers_pair_sources_get();
            const items = (response as any)?.items || [];
            providers = items
                .filter((i: any) =>
                    (i.base === data.base && i.quote === data.quote) ||
                    (i.base === data.quote && i.quote === data.base)
                )
                .sort((a: any, b: any) => a.priority - b.priority)
                .map((i: any) => ({providerCode: i.provider_code, priority: i.priority}));
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
            await zodiosApi.sync_rates_api_v1_fx_currencies_sync_get({
                queries: {
                    start: dateStart,
                    end: dateEnd,
                    currencies: `${data.base},${data.quote}`,
                }
            });
            // After sync, refresh the chart
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

    function handlePointClick(date: string, value: number) {
        if (editSection) {
            editSection.onPointEdit(date, value);
        }
    }

    async function handleSaveEdits(event: CustomEvent<ParsedRow[]>) {
        const rows = event.detail;
        if (rows.length === 0) return;
        savingEdit = true;
        try {
            const rateItems = rows.map(r => ({
                base: r.base < r.quote ? r.base : r.quote,
                quote: r.base < r.quote ? r.quote : r.base,
                date: r.date,
                rate: r.base < r.quote ? r.value : 1 / r.value,
            }));
            await zodiosApi.upsert_rates_endpoint_api_v1_fx_currencies_rate_post(rateItems);
            // Refresh chart
            await handleRefresh();
            editMode = false;
        } catch (e: any) {
            console.error('Failed to save rates:', e);
            error = 'Failed to save: ' + (e?.message || 'unknown error');
        } finally {
            savingEdit = false;
        }
    }

    function handleCancelEdit() {
        editMode = false;
    }

    async function handleAddProvider(event: CustomEvent<{providerCode: string; priority: number}>) {
        try {
            await zodiosApi.create_pair_sources_bulk_api_v1_fx_providers_pair_sources_post([{
                base: data.base,
                quote: data.quote,
                provider_code: event.detail.providerCode,
                priority: event.detail.priority,
            }]);
            await loadProviders();
        } catch (e: any) {
            console.error('Failed to add provider:', e);
            error = 'Failed to add provider: ' + (e?.message || 'unknown error');
        }
    }

    async function handleRemoveProvider(event: CustomEvent<{providerCode: string}>) {
        try {
            await zodiosApi.delete_pair_sources_bulk_api_v1_fx_providers_pair_sources_delete([{
                base: data.base,
                quote: data.quote,
            }]);
            await loadProviders();
        } catch (e: any) {
            console.error('Failed to remove provider:', e);
        }
    }
</script>

<div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <!-- Left: back + pair info -->
        <div class="flex items-center gap-3">
            <button
                class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors"
                on:click={() => goto('/fx')}
                title="Back to FX list"
            >
                <ArrowLeft size={20} />
            </button>
            <div>
                <div class="flex items-center gap-2">
                    <span class="text-2xl">{currencyFlag(displayBase)}</span>
                    <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">{displayBase}</h2>
                    <span class="text-gray-400 dark:text-gray-500 text-lg">→</span>
                    <span class="text-2xl">{currencyFlag(displayQuote)}</span>
                    <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">{displayQuote}</h2>
                    <button
                        class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                        on:click={() => inverted = !inverted}
                        title="Swap direction"
                    >
                        <ArrowLeftRight size={16} />
                    </button>
                </div>
                <div class="flex items-center gap-3 mt-1">
                    {#if lastRate !== null}
                        <span class="font-mono text-lg font-semibold text-gray-700 dark:text-gray-200">
                            {lastRate.toFixed(4)}
                        </span>
                        {#if deltaPercent !== null}
                            <span class="flex items-center gap-1 text-sm font-medium {deltaPercent >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                                {#if deltaPercent >= 0}
                                    <TrendingUp size={14} />
                                {:else}
                                    <TrendingDown size={14} />
                                {/if}
                                {deltaPercent >= 0 ? '+' : ''}{deltaPercent.toFixed(2)}%
                            </span>
                        {/if}
                        {#if lastDate}
                            <span class="text-xs text-gray-400 dark:text-gray-500">{lastDate}</span>
                        {/if}
                    {/if}
                </div>
            </div>
        </div>

        <!-- Right: action buttons -->
        <div class="flex items-center gap-2">
            <button
                class="flex items-center gap-1.5 px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 text-gray-600 dark:text-gray-300 transition-colors"
                on:click={handleRefresh}
                disabled={loading}
            >
                <RefreshCw size={15} class={loading ? 'animate-spin' : ''} />
                Refresh
            </button>
            <button
                class="flex items-center gap-1.5 px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 text-gray-600 dark:text-gray-300 transition-colors"
                on:click={handleSync}
                disabled={syncing}
            >
                <RotateCcw size={15} class={syncing ? 'animate-spin' : ''} />
                {syncing ? 'Syncing...' : 'Sync'}
            </button>
            <button
                class="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg transition-colors {editMode
                    ? 'bg-amber-500 text-white hover:bg-amber-600'
                    : 'bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700 text-gray-600 dark:text-gray-300'}"
                on:click={() => editMode = !editMode}
            >
                {#if editMode}
                    <X size={15} />
                    Exit Edit
                {:else}
                    <Pencil size={15} />
                    Edit
                {/if}
            </button>
        </div>
    </div>

    <!-- Error banner -->
    {#if error}
        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4 text-sm text-amber-700 dark:text-amber-400 flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
            <button
                class="ml-auto text-xs px-2 py-1 bg-amber-100 dark:bg-amber-900/40 rounded hover:bg-amber-200 dark:hover:bg-amber-900/60 transition-colors"
                on:click={() => error = null}
            >
                Dismiss
            </button>
        </div>
    {/if}

    <!-- Chart Section -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4 space-y-4">
        <!-- Date Range Picker (inside chart card) -->
        <DateRangePicker
            bind:start={dateStart}
            bind:end={dateEnd}
            bind:activePreset
            compact={true}
            onchange={handleDateRangeChange}
        />

        {#if loading && lineData.length === 0}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    <RefreshCw size={24} class="animate-spin text-libre-green mx-auto mb-2" />
                    <p class="text-sm text-gray-500 dark:text-gray-400">Loading rates...</p>
                </div>
            </div>
        {:else if lineData.length > 0}
            <PriceChartFull
                data={lineData}
                currency={displayQuote}
                chartHeight="400px"
                zoomHeight="60px"
                {editMode}
                onPointClick={editMode ? handlePointClick : undefined}
            />
        {:else}
            <div class="h-96 flex items-center justify-center">
                <div class="text-center">
                    <p class="text-gray-400 dark:text-gray-500 mb-3">No rate data available for this range.</p>
                    <button
                        class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors"
                        on:click={handleSync}
                        disabled={syncing}
                    >
                        {syncing ? 'Syncing...' : 'Sync Rates'}
                    </button>
                </div>
            </div>
        {/if}
    </div>

    <!-- Edit Section (visible in edit mode) -->
    {#if editMode}
        <FxEditSection
            bind:this={editSection}
            base={data.base}
            quote={data.quote}
            saving={savingEdit}
            on:save={handleSaveEdits}
            on:cancel={handleCancelEdit}
        />
    {/if}

    <!-- Provider Configuration -->
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 p-4">
        <FxProviderConfig
            {providers}
            {availableProviders}
            base={data.base}
            quote={data.quote}
            on:addProvider={handleAddProvider}
            on:removeProvider={handleRemoveProvider}
        />
    </div>
</div>

