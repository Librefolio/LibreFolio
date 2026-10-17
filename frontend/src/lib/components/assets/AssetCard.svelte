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
    import {Merge, Percent, RefreshCw, RotateCw, Settings, Trash2} from 'lucide-svelte';
    import PriceChartCompact from '$lib/components/charts/PriceChartCompact.svelte';
    import AssetIcon from './AssetIcon.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import type {ChartSettings} from '$lib/stores/chartSettingsStore.svelte';
    import type {RenderedSignal} from '$lib/charts/signals';
    import {normalizeToPercentage} from '$lib/utils/chartUtils';
    import type {LivePriceDirection} from '$lib/services/livePriceService';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {assetTypeBadgeClass, getAssetTypeIconUrl} from '$lib/utils/assetTypes';
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
        /** Global view mode from parent: 'percentage' (default) or 'absolute' */
        globalViewMode?: 'percentage' | 'absolute';
        /** Chart settings for this card (resolved from store by parent) */
        chartSettings?: ChartSettings;
        renderSignals?: (chartData: LineDataPoint[], viewMode: 'absolute' | 'percentage') => RenderedSignal[];
        /** Chart data points */
        chartData?: LineDataPoint[];
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
        globalViewMode = 'percentage',
        chartSettings,
        renderSignals,
        chartData = [],
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

    let localViewModeOverride: 'absolute' | 'percentage' | null = $state(null);
    let cardViewMode = $derived(localViewModeOverride ?? globalViewMode);

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

    let absoluteData = $derived(chartData);

    let displayData = $derived.by((): LineDataPoint[] => {
        if (cardViewMode === 'absolute' || chartData.length === 0) return chartData;
        return normalizeToPercentage(chartData);
    });

    let overlaySignals = $derived.by((): RenderedSignal[] => {
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
    data-view-mode={cardViewMode}
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
                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded {typeBadgeClass(asset.asset_type)}">
                        <img src={getAssetTypeIconUrl(asset.asset_type)} alt="" class="w-3.5 h-3.5 object-contain" />
                        {$t(`assets.types.${asset.asset_type}`) || asset.asset_type}
                    </span>
                {/if}
                {#if !asset.provider_code}
                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-lf-warning-soft text-lf-warning-on-soft"> ✏️ Manual </span>
                {/if}
                <button
                    class="p-1 rounded-md transition-colors {cardViewMode === 'percentage' ? 'bg-lf-selected text-lf-link' : 'text-lf-muted hover:bg-lf-neutral hover:text-lf-secondary'}"
                    data-testid="asset-card-view-toggle"
                    onclick={(e) => {
                        stop(e);
                        localViewModeOverride = cardViewMode === 'absolute' ? 'percentage' : 'absolute';
                    }}
                    title={cardViewMode === 'absolute' ? $t('chart.showPercentage') : $t('chart.showAbsolute')}
                >
                    <Percent size={14} />
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
        {#if displayData.length > 0}
            <PriceChartCompact
                axisScale={chartSettings?.axisScales[cardViewMode]}
                data={displayData}
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

    <!-- Footer: actions -->
    <div class="px-4 py-2.5 flex items-center justify-between border-t border-lf-subtle">
        <div class="flex items-center gap-0.5">
            <button
                class="p-1.5 rounded-md hover:bg-lf-neutral text-lf-muted hover:text-lf-secondary transition-colors"
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
