<!--
  FxCard — Card displaying a currency pair with mini chart and quick actions.
  Layout B: Header (pair + controls), Rate row, Mini chart, Footer (settings+sync+refresh | edit+delete).
  Svelte 5 runes, callback props.
  Used by: /fx list page
-->
<script lang="ts">
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {ArrowLeftRight, Percent, RefreshCw, RotateCw, Settings, Trash2} from 'lucide-svelte';
    import PriceChartCompact from '$lib/components/charts/PriceChartCompact.svelte';
    import {displayFxRate, type FxDataPoint} from '$lib/stores/fxStoreRegistry';
    import type {RangeDelta} from '$lib/utils/rangeChange';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {isCardInverted, setCardInverted} from '$lib/stores/fx/fxCardInversionStore';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import type {ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {normalizeToPercentage} from '$lib/utils/chartUtils';
    import {formatPrice} from '$lib/utils/core/formatFixed';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {SIGN_TEXT} from '$lib/theme/toneClasses';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        base: string;
        quote: string;
        slug: string;
        data?: FxDataPoint[];
        /** The pair's Δ over the range on screen, both ways, from the backend (X-R59); null while unknown. */
        rangeDeltas?: {direct: RangeDelta; inverse: RangeDelta} | null;
        loading?: boolean;
        /** Date range start (passed to detail page on navigation) */
        dateStart?: string;
        /** Date range end (passed to detail page on navigation) */
        dateEnd?: string;
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
        ondelete?: (info: {base: string; quote: string; slug: string}) => void;
        onrefresh?: (info: {slug: string}) => void;
        onsync?: (info: {slug: string; base: string; quote: string}) => void;
        onsettings?: (info: {slug: string}) => void;
        oninversionchange?: (info: {slug: string; inverted: boolean}) => void;
    }

    let {base, quote, slug, data = [], rangeDeltas = null, loading = false, dateStart, dateEnd, manualOnly = false, globalViewMode = 'absolute', chartSettings, renderSignals, ondelete, onrefresh, onsync, onsettings, oninversionchange}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    // Helper to read persisted inversion state (avoids Svelte warning about capturing props in $state)
    function getInitialInversion(): boolean {
        return isCardInverted(slug);
    }

    let inverted = $state(getInitialInversion());
    let localViewModeOverride: 'absolute' | 'percentage' | null = $state(null);

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
        return displayFxRate(last.rate, inverted);
    });

    /** The backend's Δ over the range, the way the card shows the pair (X-R59). */
    let deltaPercent = $derived((inverted ? rangeDeltas?.inverse : rangeDeltas?.direct)?.pct ?? null);

    let chartData = $derived.by((): LineDataPoint[] => {
        const absolute = data.map((d): LineDataPoint => {
            const rate = displayFxRate(d.rate, inverted);
            return {
                date: d.date,
                value: rate ?? 0,
                missing: rate === null,
                staleDays: d.backwardFillInfo?.daysBack ?? 0,
            };
        });
        if (cardViewMode === 'absolute' || absolute.length === 0) return absolute;
        return normalizeToPercentage(absolute);
    });

    /** Absolute data for signal rendering (before % conversion) */
    let absoluteData = $derived.by((): LineDataPoint[] =>
        data.map((d): LineDataPoint => {
            const rate = displayFxRate(d.rate, inverted);
            return {
                date: d.date,
                value: rate ?? 0,
                missing: rate === null,
                staleDays: d.backwardFillInfo?.daysBack ?? 0,
            };
        }),
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
        const params = dateStart && dateEnd ? `?start=${dateStart}&end=${dateEnd}` : '';
        goto(`/fx/${target}${params}`);
    }

    function stop(e: MouseEvent) {
        e.stopPropagation();
    }
</script>

<div
    class="w-full text-left bg-lf-card text-lf-primary rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle overflow-hidden cursor-pointer
       transition-all duration-200 hover:shadow-lg hover:border-lf-focus/30 hover:bg-lf-hover
       focus:outline-none focus:ring-2 focus:ring-lf-focus focus:ring-offset-2"
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
                <span class="inline-flex items-center gap-1.5" data-testid="fx-pair-label">
                    <span class="text-lg emoji-flag">{currencyFlag(displayBase)}</span>
                    <span class="font-semibold text-lf-primary">{displayBase}</span>
                    <span class="text-lf-muted text-sm">→</span>
                    <span class="text-lg emoji-flag">{currencyFlag(displayQuote)}</span>
                    <span class="font-semibold text-lf-primary">{displayQuote}</span>
                </span>

                <button
                    class="p-1 rounded-md hover:bg-lf-neutral text-lf-muted hover:text-lf-secondary transition-colors"
                    data-testid="fx-swap-btn"
                    onclick={(e) => {
                        stop(e);
                        inverted = !inverted;
                        setCardInverted(slug, inverted);
                        oninversionchange?.({slug, inverted});
                    }}
                    title={$t('common.swapDirection')}
                >
                    <ArrowLeftRight size={14} />
                </button>
            </div>

            <div class="flex items-center gap-1.5 shrink-0">
                <button
                    class="p-1 rounded-md transition-colors {cardViewMode === 'percentage' ? 'bg-lf-selected text-lf-link' : 'text-lf-muted hover:bg-lf-neutral hover:text-lf-secondary'}"
                    onclick={(e) => {
                        stop(e);
                        localViewModeOverride = cardViewMode === 'absolute' ? 'percentage' : 'absolute';
                    }}
                    title={cardViewMode === 'absolute' ? $t('chart.showPercentage') : $t('chart.showAbsolute')}
                >
                    <Percent size={14} />
                </button>
                {#if manualOnly}
                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-lf-warning-soft text-lf-warning-on-soft"> ✏️ Manual </span>
                {/if}
            </div>
        </div>
    </div>

    <!-- Row 2: Rate + delta -->
    <div class="px-4 pb-2">
        {#if lastRate !== null}
            <div class="flex items-baseline gap-2">
                <span class="text-xl font-mono font-bold text-lf-primary">
                    {formatPrice(lastRate, {minDecimals: 4})}
                </span>
                {#if deltaPercent !== null}
                    <span class="text-sm font-medium {deltaPercent >= 0 ? SIGN_TEXT.market.gain : SIGN_TEXT.market.loss}" data-testid="fx-range-delta">
                        {deltaPercent >= 0 ? '▲' : '▼'}
                        {formatPercent(deltaPercent)}
                    </span>
                {/if}
            </div>
        {:else if loading}
            <div class="text-lg text-lf-muted">...</div>
        {:else}
            <div class="text-lg text-lf-muted" data-fx-rate-state="missing" data-testid="fx-card-rate-missing">{$t('fx.rateNotAvailable')}</div>
        {/if}
    </div>

    <!-- Mini Chart -->
    <div class="px-4">
        {#if chartData.length > 0}
            <PriceChartCompact
                axisScale={chartSettings?.axisScales[cardViewMode]}
                data={chartData}
                height="80px"
                viewMode={cardViewMode}
                areaFill={chartSettings?.areaFill ?? true}
                colorByBaseline={chartSettings?.colorByBaseline}
                showGridLines={chartSettings?.gridLines}
                showGradient={chartSettings?.staleGradient ?? true}
                {overlaySignals}
                secondaryAxisScales={chartSettings?.axisScales.secondary}
            />
        {:else if loading}
            <div class="h-20 flex items-center justify-center">
                <div class="animate-pulse bg-lf-neutral rounded w-full h-12"></div>
            </div>
        {:else}
            <div class="h-20 flex items-center justify-center text-sm text-lf-muted">
                {$t('common.noData')}
            </div>
        {/if}
    </div>

    <!-- Footer: left actions (settings, sync, refresh) | right actions (edit, delete) -->
    <div class="px-4 py-2.5 flex items-center justify-between border-t border-lf-subtle">
        <div class="flex items-center gap-0.5">
            <button
                class="p-1.5 rounded-md hover:bg-lf-neutral text-lf-muted hover:text-lf-secondary transition-colors"
                onclick={(e) => {
                    stop(e);
                    onsettings?.({slug});
                }}
                title={$t('chartSettings.title')}
            >
                <Settings size={15} />
            </button>
            <button
                class="p-1.5 rounded-md transition-colors {manualOnly ? 'text-lf-muted/50 cursor-not-allowed' : 'hover:bg-lf-neutral text-lf-muted hover:text-lf-warning'}"
                disabled={manualOnly}
                onclick={(e) => {
                    stop(e);
                    if (!manualOnly) onsync?.({slug, base, quote});
                }}
                title={manualOnly ? $t('fx.card.manualOnly') : $t('fx.card.syncFromProvider')}
            >
                <RotateCw class={loading ? 'animate-spin' : ''} size={15} />
            </button>
            <button
                class="p-1.5 rounded-md hover:bg-lf-neutral text-lf-muted hover:text-lf-link transition-colors"
                onclick={(e) => {
                    stop(e);
                    onrefresh?.({slug});
                }}
                title={$t('common.refresh')}
            >
                <RefreshCw size={15} />
            </button>
        </div>
        <div class="flex items-center gap-0.5">
            <button
                class="p-1.5 rounded-md hover:bg-lf-neutral text-lf-muted hover:text-lf-danger transition-colors"
                onclick={(e) => {
                    stop(e);
                    ondelete?.({base, quote, slug});
                }}
                title={$t('fx.deletePair')}
            >
                <Trash2 size={15} />
            </button>
        </div>
    </div>
</div>
