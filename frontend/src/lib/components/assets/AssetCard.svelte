<!--
  AssetCard — Card displaying an asset with mini chart and quick actions.
  Layout: Header (icon + name + % toggle + type badge), Live Price row, Mini chart, Footer (settings + sync + refresh | delete).
  Live price flashes green/red on value changes.
  Svelte 5 runes, dark mode.
  Used by: /assets list page (grid view)
-->
<script lang="ts">
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import {CalendarSync, ChartLine, Merge, Percent, RefreshCw, RotateCw, Settings, Trash2} from 'lucide-svelte';
    import PriceChartCompact from '$lib/components/charts/PriceChartCompact.svelte';
    import {compactPlotWidth} from '$lib/components/charts/timeSeriesAggregation';
    import AssetIcon from './AssetIcon.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import {nextCardPrimaryView, type ChartPrimaryView, type ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
    import type {CalendarReturnViewState} from '$lib/components/charts/priceChartHelpers';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {normalizeToPercentage} from '$lib/utils/chartUtils';
    import type {LivePriceDirection} from '$lib/services/livePriceService';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {assetTypeBadgeClass, assetTypeBadgeDotClass, getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {formatPrice} from '$lib/utils/core/formatFixed';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {SIGN_TEXT} from '$lib/theme/toneClasses';

    // =========================================================================
    // Props
    // =========================================================================

    interface AssetData {
        id: number;
        display_name: string;
        currency: string;
        icon_url?: string | null;
        asset_type?: string | null;
        provider_code?: string | null;
        active: boolean;
    }

    interface Props {
        asset: AssetData;
        /** F15 — transactions using this asset; shown as a small badge on the header. */
        txCount?: number;
        /** Live current price (from bulk current-price endpoint) */
        livePrice?: number | null;
        /** Direction of last price change (for flash animation) */
        livePriceDirection?: LivePriceDirection;
        /** Δ over the range on screen, in percent: the backend's (X-R59), null where it has none */
        deltaPercent?: number | null;
        /** Δ over the range on screen, absolute, in the asset's currency: the backend's (X-R59) */
        deltaAbs?: number | null;
        /** Date range start (passed to detail page on navigation) */
        dateStart?: string;
        /** Date range end (passed to detail page on navigation) */
        dateEnd?: string;
        /** The view the page resolves for this card (Y-40): its saved choice, else the list's. */
        primaryView?: ChartPrimaryView;
        /** The card's button asks the next view of the turn (percent → rolling return → absolute); the page saves it. */
        onprimaryviewchange?: (assetId: number, view: ChartPrimaryView) => void;
        /** The card's rolling return, in percent, for the rolling-return view (Y-40); with the detail's problem when there is none. */
        calendarReturn?: {state: CalendarReturnViewState; points: LineDataPoint[]; problemCode?: string | null; problemMessage?: string | null};
        /** The comparisons' rolling returns, drawn over the card's in the rolling-return view (V-5 a: the only signals there). */
        calendarOverlaySignals?: RenderedSignal[];
        /** Chart settings for this card (resolved from store by parent) */
        chartSettings?: ChartSettings;
        renderSignals?: (chartData: LineDataPoint[], viewMode: 'absolute' | 'percentage') => RenderedSignal[];
        /** Chart data points */
        chartData?: LineDataPoint[];
        /**
         * The value on the first day of the series (Z-29b): the percentage view is measured from it, and the line's colour and
         * dashed reference in the absolute view (`baselineValue`). A sampled series opens on the end of its first bucket, so its own first point is not it. Without
         * it, the first point is the base.
         */
        baseValue?: number | null;
        /** The width of the chart's plot, reported when it is measured or changes (Z-29b): the page asks the series for it. */
        onplotwidth?: (assetId: number, plotWidthPx: number) => void;
        /** Loading state */
        loading?: boolean;
        /** True when this asset is currently syncing */
        syncing?: boolean;
        /** Callbacks */
        onsync?: (asset: AssetData) => void;
        onrefresh?: (asset: AssetData) => void;
        ondelete?: (asset: AssetData) => void;
        onmerge?: (asset: AssetData) => void;
        onsettings?: (asset: AssetData) => void;
    }

    let {
        asset,
        txCount = undefined,
        livePrice = null,
        livePriceDirection = 'neutral',
        deltaPercent = null,
        deltaAbs = null,
        dateStart,
        dateEnd,
        primaryView = 'percentage',
        onprimaryviewchange,
        calendarReturn,
        calendarOverlaySignals = [],
        chartSettings,
        renderSignals,
        chartData = [],
        baseValue = null,
        onplotwidth,
        loading = false,
        syncing = false,
        onsync,
        onrefresh,
        ondelete,
        onmerge,
        onsettings,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    /** The price views draw the prices; the rolling-return view draws the return, already in percent. */
    let isCalendarView = $derived(primaryView === 'calendar-return');
    let cardViewMode: 'absolute' | 'percentage' = $derived(primaryView === 'absolute' ? 'absolute' : 'percentage');
    let nextView = $derived(nextCardPrimaryView(primaryView));

    // =========================================================================
    // Derived
    // =========================================================================

    let absoluteData = $derived(chartData);

    let displayData = $derived.by((): LineDataPoint[] => {
        if (isCalendarView) return calendarReturn?.points ?? [];
        if (cardViewMode === 'absolute' || chartData.length === 0) return chartData;
        return normalizeToPercentage(chartData, baseValue);
    });

    /** The width of the chart's box: its plot's is that minus the grid's paddings (`compactPlotWidth`). */
    let chartWidth = $state(0);
    $effect(() => {
        if (chartWidth > 0) onplotwidth?.(asset.id, compactPlotWidth(chartWidth));
    });

    let overlaySignals = $derived.by((): RenderedSignal[] => {
        if (isCalendarView) return calendarOverlaySignals;
        if (!renderSignals || absoluteData.length === 0) return [];
        return renderSignals(absoluteData, cardViewMode);
    });

    /** Dynamic card border based on price direction (flash effect) */
    let cardBorderClass = $derived.by(() => {
        switch (livePriceDirection) {
            case 'up':
                return 'border-lf-gain/50';
            case 'down':
                return 'border-lf-loss/50';
            default:
                return asset.active ? 'border-lf-subtle' : 'border-lf-warning-line';
        }
    });

    let cardSurfaceClass = $derived(asset.active ? 'bg-lf-card hover:bg-lf-hover' : 'bg-lf-warning-soft hover:bg-lf-warning-line/50');

    // =========================================================================
    // Helpers
    // =========================================================================

    ensureCurrenciesLoaded($currentLanguage);

    function currencyFlag(code: string): string {
        return getCurrencyInfo(code).flag_emoji;
    }

    function handleCardClick() {
        const params = dateStart && dateEnd ? `?start=${dateStart}&end=${dateEnd}` : '';
        goto(`/assets/${asset.id}${params}`);
    }

    function stop(e: MouseEvent) {
        e.stopPropagation();
    }

    function typeBadgeClass(type: string | null | undefined): string {
        return assetTypeBadgeClass(type);
    }
</script>

<div
    class="w-full text-left text-lf-primary rounded-xl shadow-sm shadow-lf-shadow-card border overflow-hidden cursor-pointer
       transition-all duration-300 hover:shadow-lg hover:border-lf-focus/30
       focus:outline-none focus:ring-2 focus:ring-lf-focus focus:ring-offset-2
       {cardSurfaceClass} {cardBorderClass}"
    data-testid="asset-card-{asset.id}"
    data-lifecycle={asset.active ? 'active' : 'inactive'}
    data-view-mode={primaryView}
    data-calendar-state={isCalendarView ? (calendarReturn?.state ?? 'idle') : undefined}
    onclick={handleCardClick}
    onkeydown={(e) => e.key === 'Enter' && handleCardClick()}
    role="button"
    tabindex="0"
>
    <!-- Row 1: Icon + Name + % toggle + Type Badge -->
    <div class="px-4 pt-3 pb-1">
        <div class="flex items-center gap-2">
            <AssetIcon altText={asset.display_name} assetType={asset.asset_type} iconUrl={asset.icon_url} size="sm" />
            <div class="flex-1 min-w-0">
                <span use:scrollOnOverflow class="{overflowScrollTextClass} font-semibold text-lf-primary" title={asset.display_name}>{asset.display_name}</span>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
                {#if asset.asset_type}
                    {@const typeDot = assetTypeBadgeDotClass(asset.asset_type)}
                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded {typeBadgeClass(asset.asset_type)}">
                        <img src={getAssetTypeIconUrl(asset.asset_type)} alt="" class="w-3.5 h-3.5 object-contain" />
                        {$t(`assets.types.${asset.asset_type}`) || asset.asset_type}
                        {#if typeDot}
                            <span class="inline-block w-1.5 h-1.5 shrink-0 rounded-full {typeDot}" aria-hidden="true" data-testid="asset-type-dot"></span>
                        {/if}
                    </span>
                {/if}
                {#if !asset.provider_code}
                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-lf-warning-soft text-lf-warning-on-soft"> ✏️ Manual </span>
                {/if}
                <!-- One button, three views in turn (Y-40): it shows where it goes -->
                <button
                    class="p-1 rounded-md transition-colors {primaryView === 'absolute' ? 'text-lf-muted hover:bg-lf-neutral hover:text-lf-secondary' : 'bg-lf-selected text-lf-link'}"
                    data-testid="asset-card-view-toggle"
                    data-next-view={nextView}
                    onclick={(e) => {
                        stop(e);
                        onprimaryviewchange?.(asset.id, nextView);
                    }}
                    title={nextView === 'percentage' ? $t('chart.showPercentage') : nextView === 'absolute' ? $t('chart.showAbsolute') : $t('signals.riskRollingReturn.name')}
                >
                    {#if nextView === 'percentage'}
                        <Percent size={14} />
                    {:else if nextView === 'calendar-return'}
                        <CalendarSync size={14} />
                    {:else}
                        <ChartLine size={14} />
                    {/if}
                </button>
                <span class="w-2 h-2 rounded-full shrink-0 {asset.active ? 'bg-lf-success' : 'bg-lf-danger'}"></span>
                {#if txCount !== undefined}
                    <span class="text-[10px] font-mono text-lf-muted shrink-0" title={$t('assets.table.txCountTooltip')} data-testid="asset-card-tx-count">
                        {txCount} tx
                    </span>
                {/if}
            </div>
        </div>
    </div>

    <!-- Row 2: Live Price + flag + code + delta -->
    <div class="px-4 pb-2">
        <div class="flex items-baseline gap-2">
            <span
                class="text-xl font-mono font-bold transition-colors duration-300
                         {livePriceDirection === 'up' ? SIGN_TEXT.market.gain : livePriceDirection === 'down' ? SIGN_TEXT.market.loss : 'text-lf-primary'}"
            >
                {livePrice != null ? formatPrice(livePrice) : '--'}
            </span>
            <span class="text-xs text-lf-muted emoji-flag">{currencyFlag(asset.currency)}</span>
            <span class="text-xs text-lf-muted">{asset.currency}</span>
            {#if cardViewMode === 'absolute' && deltaAbs !== null}
                <span class="text-sm font-medium {deltaAbs >= 0 ? SIGN_TEXT.market.gain : SIGN_TEXT.market.loss}" data-testid="asset-range-delta" data-mode="absolute">
                    {deltaAbs >= 0 ? '▲' : '▼'}
                    {formatPrice(deltaAbs, {signed: true})}
                    {asset.currency}
                </span>
            {:else if deltaPercent !== null}
                <span class="text-sm font-medium {deltaPercent >= 0 ? SIGN_TEXT.market.gain : SIGN_TEXT.market.loss}" data-testid="asset-range-delta" data-mode="percentage">
                    {deltaPercent >= 0 ? '▲' : '▼'}
                    {formatPercent(Number(deltaPercent))}
                </span>
            {/if}
        </div>
    </div>

    <!-- Mini Chart -->
    <div class="px-4">
        <div bind:clientWidth={chartWidth}>
            {#if isCalendarView && calendarReturn?.state === 'loading' && displayData.length === 0}
                <div class="h-20 flex items-center justify-center" data-testid="asset-card-calendar-loading">
                    <div class="animate-pulse bg-lf-neutral rounded w-full h-12"></div>
                </div>
            {:else if isCalendarView && displayData.length === 0}
                <div class="h-20 flex items-center justify-center px-2 text-center text-xs text-lf-muted" data-testid="asset-card-calendar-problem" data-state={calendarReturn?.state ?? 'idle'} data-problem-code={calendarReturn?.problemCode ?? undefined}>
                    {calendarReturn?.problemMessage ?? $t('chartSettings.signalProblems.unavailable')}
                </div>
            {:else if displayData.length > 0}
                <PriceChartCompact
                    axisScale={chartSettings?.axisScales[cardViewMode]}
                    data={displayData}
                    height="80px"
                    viewMode={cardViewMode}
                    areaFill={chartSettings?.areaFill ?? true}
                    colorByBaseline={chartSettings?.colorByBaseline}
                    baselineValue={isCalendarView ? undefined : (baseValue ?? undefined)}
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
    </div>

    <!-- Footer: actions -->
    <div class="px-4 py-2.5 flex items-center justify-between border-t border-lf-subtle">
        <div class="flex items-center gap-0.5">
            <button
                class="p-1.5 rounded-md hover:bg-lf-neutral text-lf-muted hover:text-lf-secondary transition-colors"
                data-testid="asset-card-settings"
                onclick={(e) => {
                    stop(e);
                    onsettings?.(asset);
                }}
                title={$t('chartSettings.title')}
            >
                <Settings size={15} />
            </button>
            <button
                class="p-1.5 rounded-md transition-colors {!asset.provider_code ? 'text-lf-muted/50 cursor-not-allowed' : 'hover:bg-lf-neutral text-lf-muted hover:text-lf-warning'}"
                disabled={!asset.provider_code || syncing}
                onclick={(e) => {
                    stop(e);
                    if (asset.provider_code) onsync?.(asset);
                }}
                title={asset.provider_code ? 'Sync prices from provider' : 'No provider assigned'}
            >
                <RotateCw class={syncing ? 'animate-spin' : ''} size={15} />
            </button>
            <button
                class="p-1.5 rounded-md hover:bg-lf-neutral text-lf-muted hover:text-lf-link transition-colors"
                onclick={(e) => {
                    stop(e);
                    onrefresh?.(asset);
                }}
                title={$t('common.refresh')}
            >
                <RefreshCw size={15} />
            </button>
        </div>
        <div class="flex items-center gap-0.5">
            <button
                class="p-1.5 rounded-md hover:bg-lf-neutral text-lf-muted hover:text-lf-link transition-colors"
                data-testid="asset-card-merge"
                onclick={(e) => {
                    stop(e);
                    onmerge?.(asset);
                }}
                title={$t('assets.merge.action')}
            >
                <Merge size={15} />
            </button>
            <button
                class="p-1.5 rounded-md hover:bg-lf-neutral text-lf-muted hover:text-lf-danger transition-colors"
                data-testid="asset-card-delete-btn"
                onclick={(e) => {
                    stop(e);
                    ondelete?.(asset);
                }}
                title={$t('common.delete')}
            >
                <Trash2 size={15} />
            </button>
        </div>
    </div>
</div>
