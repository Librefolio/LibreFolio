<!--
  FxCard — Card displaying a currency pair with mini chart and quick actions.
  Layout B: Header (pair + controls), Rate row, Mini chart, Footer (settings+sync+refresh | edit+delete).
  Svelte 5 runes, callback props.
  Used by: /fx list page
-->
<script lang="ts">
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';
    import {ArrowLeftRight, Pencil, Percent, RefreshCw, RotateCw, Settings, Trash2} from 'lucide-svelte';
    import PriceChartCompact from '$lib/components/charts/PriceChartCompact.svelte';
    import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';
    import {getCurrencyInfo, ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {isCardInverted, setCardInverted} from '$lib/stores/fxCardInversionStore';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        base: string;
        quote: string;
        slug: string;
        data?: FxDataPoint[];
        loading?: boolean;
        /** Whether this pair has only a MANUAL sentinel provider */
        manualOnly?: boolean;
        /** Global view mode from parent */
        globalViewMode?: 'absolute' | 'percentage';
        /** Chart settings for this card (resolved from store by parent) */
        chartSettings?: ChartSettings;
        /**
         * Callback to render overlay signals on demand.
         * Called reactively whenever cardViewMode or inverted changes.
         * @param chartData absolute chart data (after inversion)
         * @param viewMode  current card view mode
         */
        renderSignals?: (chartData: LineDataPoint[], viewMode: 'absolute' | 'percentage') => RenderedSignal[];
        /** Callbacks */
        onedit?: (info: { base: string; quote: string; slug: string }) => void;
        ondelete?: (info: { base: string; quote: string; slug: string }) => void;
        onrefresh?: (info: { slug: string }) => void;
        onsync?: (info: { slug: string; base: string; quote: string }) => void;
        onsettings?: (info: { slug: string }) => void;
    }

    let {
        base,
        quote,
        slug,
        data = [],
        loading = false,
        manualOnly = false,
        globalViewMode = 'absolute',
        chartSettings,
        renderSignals,
        onedit,
        ondelete,
        onrefresh,
        onsync,
        onsettings,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    // Helper to read persisted inversion state (avoids Svelte warning about capturing props in $state)
    function getInitialInversion(): boolean {
        return isCardInverted(slug);
    }

    let inverted = $state(getInitialInversion());
    let localViewModeOverride = $state<'absolute' | 'percentage' | null>(null);

    // Card view mode: local override takes precedence, otherwise follows global
    let cardViewMode = $derived(localViewModeOverride ?? globalViewMode);

    // Reset local override when global changes
    let prevGlobal: string | undefined;
    $effect(() => {
        if (prevGlobal !== undefined && globalViewMode !== prevGlobal) {
            localViewModeOverride = null;
        }
        prevGlobal = globalViewMode;
    });

    // =========================================================================
    // Derived
    // =========================================================================

    let displayBase = $derived(inverted ? quote : base);
    let displayQuote = $derived(inverted ? base : quote);

    let lastRate = $derived.by(() => {
        if (data.length === 0) return null;
        const last = data[data.length - 1];
        return inverted && last.rate !== 0 ? 1 / last.rate : last.rate;
    });

    let deltaPercent = $derived.by(() => {
        if (data.length < 2) return null;
        const rawFirst = data[0].rate;
        const rawLast = data[data.length - 1].rate;
        if (rawFirst === 0 || rawLast === 0) return null;
        const first = inverted ? 1 / rawFirst : rawFirst;
        const last = inverted ? 1 / rawLast : rawLast;
        return ((last - first) / first) * 100;
    });

    let chartData = $derived.by((): LineDataPoint[] => {
        const absolute = data.map((d): LineDataPoint => ({
            date: d.date,
            value: inverted && d.rate !== 0 ? 1 / d.rate : d.rate,
            staleDays: d.backwardFillInfo?.daysBack ?? 0,
        }));
        if (cardViewMode === 'absolute' || absolute.length === 0) return absolute;
        const baseValue = absolute[0].value;
        if (baseValue === 0) return absolute;
        return absolute.map(d => ({
            ...d,
            value: ((d.value - baseValue) / baseValue) * 100,
        }));
    });

    /** Absolute data for signal rendering (before % conversion) */
    let absoluteData = $derived.by((): LineDataPoint[] =>
        data.map((d): LineDataPoint => ({
            date: d.date,
            value: inverted && d.rate !== 0 ? 1 / d.rate : d.rate,
            staleDays: d.backwardFillInfo?.daysBack ?? 0,
        }))
    );

    /** Overlay signals — re-rendered reactively when cardViewMode or inverted changes */
    let overlaySignals = $derived.by((): RenderedSignal[] => {
        if (!renderSignals || absoluteData.length === 0) return [];
        return renderSignals(absoluteData, cardViewMode);
    });

    // =========================================================================
    // Currency flag
    // =========================================================================

    ensureCurrenciesLoaded($currentLanguage);

    function currencyFlag(code: string): string {
        return getCurrencyInfo(code).flag_emoji;
    }

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleCardClick() {
        // If inverted, navigate to the inverted URL — detail page reads direction from URL
        const target = inverted ? `${displayBase}-${displayQuote}` : slug;
        goto(`/fx/${target}`);
    }

    function stop(e: MouseEvent) { e.stopPropagation(); }
</script>

<div
    class="w-full text-left bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden cursor-pointer
       transition-all duration-200 hover:shadow-lg hover:border-libre-green/30 hover:bg-libre-green/5 dark:hover:bg-slate-700
       focus:outline-none focus:ring-2 focus:ring-libre-green focus:ring-offset-2"
    data-testid="fx-card-{slug}"
    onclick={handleCardClick}
    onkeydown={(e) => e.key === 'Enter' && handleCardClick()}
    role="button"
    tabindex="0"
>
    <!-- Row 1: Pair + controls + badge -->
    <div class="px-4 pt-3 pb-1">
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-1.5">
                <span data-testid="fx-pair-label" class="inline-flex items-center gap-1.5">
                    <span class="text-lg">{currencyFlag(displayBase)}</span>
                    <span class="font-semibold text-gray-800 dark:text-gray-100">{displayBase}</span>
                    <span class="text-gray-400 dark:text-gray-500 text-sm">→</span>
                    <span class="text-lg">{currencyFlag(displayQuote)}</span>
                    <span class="font-semibold text-gray-800 dark:text-gray-100">{displayQuote}</span>
                </span>

                <button
                    class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    onclick={(e) => { stop(e); inverted = !inverted; setCardInverted(slug, inverted); }}
                    title="Swap direction"
                    data-testid="fx-swap-btn"
                >
                    <ArrowLeftRight size={14} />
                </button>

                <button
                    class="p-1 rounded-md transition-colors {cardViewMode === 'percentage'
                        ? 'bg-libre-green/10 text-libre-green dark:bg-libre-green/20 dark:text-green-400'
                        : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700 hover:text-gray-600 dark:hover:text-gray-300'}"
                    onclick={(e) => { stop(e); localViewModeOverride = cardViewMode === 'absolute' ? 'percentage' : 'absolute'; }}
                    title={cardViewMode === 'absolute' ? 'Show percentage' : 'Show absolute'}
                >
                    <Percent size={14} />
                </button>
            </div>

            {#if manualOnly}
                <span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                    ✏️ Manual
                </span>
            {/if}
        </div>
    </div>

    <!-- Row 2: Rate + delta -->
    <div class="px-4 pb-2">
        {#if lastRate !== null}
            <div class="flex items-baseline gap-2">
                <span class="text-xl font-mono font-bold text-gray-800 dark:text-gray-100">
                    {lastRate.toFixed(4)}
                </span>
                {#if deltaPercent !== null}
                    <span class="text-sm font-medium {deltaPercent >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                        {deltaPercent >= 0 ? '▲' : '▼'} {deltaPercent >= 0 ? '+' : ''}{deltaPercent.toFixed(2)}%
                    </span>
                {/if}
            </div>
        {:else if loading}
            <div class="text-lg text-gray-400 dark:text-gray-500">...</div>
        {:else}
            <div class="text-lg text-gray-400 dark:text-gray-500">—</div>
        {/if}
    </div>

    <!-- Mini Chart -->
    <div class="px-4">
        {#if chartData.length > 0}
            <PriceChartCompact
                data={chartData}
                height="80px"
                viewMode={cardViewMode}
                areaFill={chartSettings?.areaFill ?? true}
                colorByBaseline={chartSettings?.colorByBaseline}
                showGridLines={chartSettings?.gridLines}
                showGradient={chartSettings?.staleGradient ?? true}
                overlaySignals={overlaySignals}
            />
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

    <!-- Footer: left actions (settings, sync, refresh) | right actions (edit, delete) -->
    <div class="px-4 py-2.5 flex items-center justify-between border-t border-gray-50 dark:border-slate-700/50">
        <div class="flex items-center gap-0.5">
            <button
                class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                onclick={(e) => { stop(e); onsettings?.({ slug }); }}
                title={$t('chartSettings.title')}
            >
                <Settings size={15} />
            </button>
            <button
                class="p-1.5 rounded-md transition-colors {manualOnly ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed' : 'hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-amber-600'}"
                onclick={(e) => { stop(e); if (!manualOnly) onsync?.({ slug, base, quote }); }}
                title={manualOnly ? 'Manual-only pair' : 'Sync rates from provider'}
                disabled={manualOnly}
            >
                <RotateCw size={15} class={loading ? 'animate-spin' : ''} />
            </button>
            <button
                class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-libre-green transition-colors"
                onclick={(e) => { stop(e); onrefresh?.({ slug }); }}
                title="Refresh"
            >
                <RefreshCw size={15} />
            </button>
        </div>
        <div class="flex items-center gap-0.5">
            <button
                class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-blue-600 transition-colors"
                onclick={(e) => { stop(e); onedit?.({ base, quote, slug }); }}
                title="Edit pair config"
            >
                <Pencil size={15} />
            </button>
            <button
                class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-red-500 transition-colors"
                onclick={(e) => { stop(e); ondelete?.({ base, quote, slug }); }}
                title="Delete pair"
            >
                <Trash2 size={15} />
            </button>
        </div>
    </div>
</div>

