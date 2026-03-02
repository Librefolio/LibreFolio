<!--
  FxCard — Card displaying a currency pair with mini chart and quick actions.

  Shows: flag + pair + swap button, last rate + delta %, mini chart (PriceChartCompact),
  refresh/edit/delete buttons. Click navigates to detail page.

  Used by: /fx list page
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import {ArrowLeftRight, Pencil, RefreshCw, RotateCcw, Trash2} from 'lucide-svelte';
    import PriceChartCompact from '$lib/components/charts/PriceChartCompact.svelte';
    import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';

    const dispatch = createEventDispatcher<{
        edit: { base: string; quote: string; slug: string };
        delete: { base: string; quote: string; slug: string };
        refresh: { slug: string };
        sync: { slug: string; base: string; quote: string };
    }>();

    // =========================================================================
    // Props
    // =========================================================================

    export let base: string;
    export let quote: string;
    export let slug: string;
    export let data: FxDataPoint[] = [];
    export let loading: boolean = false;

    // =========================================================================
    // State
    // =========================================================================

    let inverted = false;

    // =========================================================================
    // Derived
    // =========================================================================

    $: displayBase = inverted ? quote : base;
    $: displayQuote = inverted ? base : quote;

    // Last rate and change
    $: lastRate = (() => {
        if (data.length === 0) return null;
        const last = data[data.length - 1];
        return inverted && last.rate !== 0 ? 1 / last.rate : last.rate;
    })();

    $: deltaPercent = (() => {
        if (data.length < 2) return null;
        const first = data[0].rate;
        const last = data[data.length - 1].rate;
        if (first === 0) return null;
        return ((last - first) / first) * 100;
    })();

    // Chart data (convert FxDataPoint → LineDataPoint)
    $: chartData = data.map((d): LineDataPoint => ({
        date: d.date,
        value: inverted && d.rate !== 0 ? 1 / d.rate : d.rate,
        staleDays: d.backwardFillInfo?.daysBack ?? 0,
    }));

    // =========================================================================
    // Currency flag emoji helper
    // =========================================================================

    function currencyFlag(code: string): string {
        // Map common currencies to flag emoji via country code
        const map: Record<string, string> = {
            EUR: '🇪🇺', USD: '🇺🇸', GBP: '🇬🇧', JPY: '🇯🇵', CHF: '🇨🇭',
            CAD: '🇨🇦', AUD: '🇦🇺', NZD: '🇳🇿', CNY: '🇨🇳', SEK: '🇸🇪',
            NOK: '🇳🇴', DKK: '🇩🇰', PLN: '🇵🇱', CZK: '🇨🇿', HUF: '🇭🇺',
            RON: '🇷🇴', BGN: '🇧🇬', HRK: '🇭🇷', TRY: '🇹🇷', BRL: '🇧🇷',
            MXN: '🇲🇽', INR: '🇮🇳', KRW: '🇰🇷', SGD: '🇸🇬', HKD: '🇭🇰',
            THB: '🇹🇭', ZAR: '🇿🇦', RUB: '🇷🇺', ILS: '🇮🇱',
        };
        return map[code] || '💱';
    }

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleCardClick() {
        goto(`/fx/${slug}`);
    }

    function handleSwap(e: MouseEvent) {
        e.stopPropagation();
        inverted = !inverted;
    }

    function handleEdit(e: MouseEvent) {
        e.stopPropagation();
        dispatch('edit', {base, quote, slug});
    }

    function handleDelete(e: MouseEvent) {
        e.stopPropagation();
        dispatch('delete', {base, quote, slug});
    }

    function handleRefresh(e: MouseEvent) {
        e.stopPropagation();
        dispatch('refresh', {slug});
    }

    function handleSync(e: MouseEvent) {
        e.stopPropagation();
        dispatch('sync', {slug, base, quote});
    }
</script>

<div
    class="w-full text-left bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden cursor-pointer
       transition-all duration-200 hover:shadow-lg hover:border-libre-green/30 hover:bg-libre-green/5 dark:hover:bg-slate-700
       focus:outline-none focus:ring-2 focus:ring-libre-green focus:ring-offset-2"
    data-testid="fx-card-{slug}"
    on:click={handleCardClick}
    on:keydown={(e) => e.key === 'Enter' && handleCardClick()}
    role="button"
    tabindex="0"
>
    <!-- Header -->
    <div class="p-4 pb-2">
        <div class="flex items-center justify-between">
            <!-- Pair display -->
            <div class="flex items-center gap-2">
                <span class="text-lg">{currencyFlag(displayBase)}</span>
                <span class="font-semibold text-gray-800 dark:text-gray-100">{displayBase}</span>
                <span class="text-gray-400 dark:text-gray-500">→</span>
                <span class="text-lg">{currencyFlag(displayQuote)}</span>
                <span class="font-semibold text-gray-800 dark:text-gray-100">{displayQuote}</span>

                <!-- Swap button -->
                <button
                    class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    on:click={handleSwap}
                    title="Swap direction"
                >
                    <ArrowLeftRight size={14} />
                </button>
            </div>

            <!-- Last rate + delta -->
            <div class="text-right">
                {#if lastRate !== null}
                    <div class="font-mono font-semibold text-gray-800 dark:text-gray-100">
                        {lastRate.toFixed(4)}
                    </div>
                    {#if deltaPercent !== null}
                        <div class="text-xs font-medium {deltaPercent >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                            {deltaPercent >= 0 ? '+' : ''}{deltaPercent.toFixed(2)}%
                        </div>
                    {/if}
                {:else if loading}
                    <div class="text-sm text-gray-400 dark:text-gray-500">...</div>
                {:else}
                    <div class="text-sm text-gray-400 dark:text-gray-500">—</div>
                {/if}
            </div>
        </div>
    </div>

    <!-- Mini Chart -->
    <div class="px-4">
        {#if chartData.length > 0}
            <PriceChartCompact data={chartData} height="80px" />
        {:else if loading}
            <div class="h-20 flex items-center justify-center">
                <div class="animate-pulse bg-gray-100 dark:bg-slate-700 rounded w-full h-12"></div>
            </div>
        {:else}
            <div class="h-20 flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
                No data
            </div>
        {/if}
    </div>

    <!-- Actions -->
    <div class="px-4 py-3 flex items-center justify-end gap-1 border-t border-gray-50 dark:border-slate-700/50">
        <button
            class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-amber-600 transition-colors"
            on:click={handleSync}
            title="Sync rates from provider"
        >
            <RotateCcw size={15} class={loading ? 'animate-spin' : ''} />
        </button>
        <button
            class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-libre-green transition-colors"
            on:click={handleRefresh}
            title="Refresh"
        >
            <RefreshCw size={15} class={loading ? 'animate-spin' : ''} />
        </button>
        <button
            class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-blue-600 transition-colors"
            on:click={handleEdit}
            title="Edit pair config"
        >
            <Pencil size={15} />
        </button>
        <button
            class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-red-500 transition-colors"
            on:click={handleDelete}
            title="Delete pair"
        >
            <Trash2 size={15} />
        </button>
    </div>
</div>

