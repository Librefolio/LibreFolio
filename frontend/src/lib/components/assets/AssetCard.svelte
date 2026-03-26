<!--
  AssetCard — Card displaying an asset with mini chart and quick actions.
  Layout: Header (icon + name + type badge), Rate row, Mini chart, Footer (edit + delete).
  NO swap button (unlike FxCard).
  Svelte 5 runes, dark mode.
  Used by: /assets list page (grid view)
-->
<script lang="ts">
    import {goto} from '$app/navigation';
    import {_ as t} from '$lib/i18n';
    import {RefreshCw, RotateCw, Trash2} from 'lucide-svelte';
    import PriceChartCompact from '$lib/components/charts/PriceChartCompact.svelte';
    import AssetIcon from './AssetIcon.svelte';
    import type {LineDataPoint} from '$lib/components/charts/LineChart.svelte';
    import {getCurrencyInfo, ensureCurrenciesLoaded} from '$lib/stores/currencyStore';
    import {currentLanguage} from '$lib/stores/language';

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
        /** Last price close value */
        lastPrice?: number | null;
        /** Delta percent (first vs last in range) */
        deltaPercent?: number | null;
        /** Delta absolute */
        deltaAbs?: number | null;
        /** Which delta to display on the card: 'percentage' (default) or 'absolute' */
        deltaDisplayMode?: 'percentage' | 'absolute';
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
    }

    let {
        asset,
        lastPrice = null,
        deltaPercent = null,
        deltaAbs = null,
        deltaDisplayMode = 'percentage',
        chartData = [],
        loading = false,
        syncing = false,
        onsync,
        onrefresh,
        ondelete,
    }: Props = $props();

    // =========================================================================
    // Helpers
    // =========================================================================

    ensureCurrenciesLoaded($currentLanguage);

    function currencyFlag(code: string): string {
        return getCurrencyInfo(code).flag_emoji;
    }

    function handleCardClick() {
        goto(`/assets/${asset.id}`);
    }

    function stop(e: MouseEvent) { e.stopPropagation(); }

    // Type badge color mapping
    function typeBadgeClass(type: string | null | undefined): string {
        switch (type) {
            case 'STOCK': return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400';
            case 'ETF': return 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400';
            case 'BOND': return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400';
            case 'CRYPTO': return 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400';
            case 'FUND': return 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-400';
            case 'HOLD': return 'bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-400';
            case 'CROWDFUND_LOAN': return 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400';
            default: return 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400';
        }
    }

    // Asset type → icon PNG filename mapping
    const ASSET_TYPE_ICON_MAP: Record<string, string> = {
        STOCK: 'stock', ETF: 'etf', BOND: 'bond', CRYPTO: 'crypto',
        FUND: 'fund', HOLD: 'hold', CROWDFUND_LOAN: 'crowdfunding', OTHER: 'other',
    };
</script>

<div
    class="w-full text-left bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 overflow-hidden cursor-pointer
       transition-all duration-200 hover:shadow-lg hover:border-libre-green/30 hover:bg-libre-green/5 dark:hover:bg-slate-700
       focus:outline-none focus:ring-2 focus:ring-libre-green focus:ring-offset-2"
    data-testid="asset-card-{asset.id}"
    onclick={handleCardClick}
    onkeydown={(e) => e.key === 'Enter' && handleCardClick()}
    role="button"
    tabindex="0"
>
    <!-- Row 1: Icon + Name + Type Badge -->
    <div class="px-4 pt-3 pb-1">
        <div class="flex items-center gap-2">
            <AssetIcon iconUrl={asset.icon_url} assetType={asset.asset_type} altText={asset.display_name} size="sm" />
            <div class="flex-1 min-w-0">
                <span class="font-semibold text-gray-800 dark:text-gray-100 truncate block">{asset.display_name}</span>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
                {#if asset.asset_type}
                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded {typeBadgeClass(asset.asset_type)}">
                        <img src="/icons/asset-types/{ASSET_TYPE_ICON_MAP[asset.asset_type] ?? 'other'}.png" alt="" class="w-3.5 h-3.5 object-contain" />
                        {$t(`assets.types.${asset.asset_type}`) || asset.asset_type}
                    </span>
                {/if}
                <span class="w-2 h-2 rounded-full shrink-0 {asset.active ? 'bg-emerald-500' : 'bg-red-400'}"></span>
            </div>
        </div>
    </div>

    <!-- Row 2: Price + delta -->
    <div class="px-4 pb-2">
        {#if lastPrice !== null}
            <div class="flex items-baseline gap-2">
                <span class="text-xl font-mono font-bold text-gray-800 dark:text-gray-100">
                    {Number(lastPrice).toFixed(2)}
                </span>
                <span class="text-xs text-gray-500 dark:text-gray-400 emoji-flag">{currencyFlag(asset.currency)} {asset.currency}</span>
                {#if deltaDisplayMode === 'absolute' && deltaAbs !== null}
                    <span class="text-sm font-medium {deltaAbs >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                        {deltaAbs >= 0 ? '▲' : '▼'} {deltaAbs >= 0 ? '+' : ''}{Number(deltaAbs).toFixed(2)}
                    </span>
                {:else if deltaPercent !== null}
                    <span class="text-sm font-medium {deltaPercent >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                        {deltaPercent >= 0 ? '▲' : '▼'} {deltaPercent >= 0 ? '+' : ''}{Number(deltaPercent).toFixed(2)}%
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
                areaFill={true}
                showGradient={true}
            />
        {:else if loading}
            <div class="h-20 flex items-center justify-center">
                <div class="animate-pulse bg-gray-100 dark:bg-slate-700 rounded w-full h-12"></div>
            </div>
        {:else}
            <div class="h-20 flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
                {$t('common.noData')}
            </div>
        {/if}
    </div>

    <!-- Footer: actions (sync, refresh, delete) -->
    <div class="px-4 py-2.5 flex items-center justify-between border-t border-gray-50 dark:border-slate-700/50">
        <div class="flex items-center gap-0.5">
            <button
                class="p-1.5 rounded-md transition-colors {!asset.provider_code ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed' : 'hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-amber-600'}"
                onclick={(e) => { stop(e); if (asset.provider_code) onsync?.(asset); }}
                title={asset.provider_code ? 'Sync prices from provider' : 'No provider assigned'}
                disabled={!asset.provider_code || syncing}
            >
                <RotateCw size={15} class={syncing ? 'animate-spin' : ''} />
            </button>
            <button
                class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-libre-green transition-colors"
                onclick={(e) => { stop(e); onrefresh?.(asset); }}
                title={$t('common.refresh')}
            >
                <RefreshCw size={15} />
            </button>
        </div>
        <div class="flex items-center gap-0.5">
            <button
                class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 hover:text-red-500 transition-colors"
                onclick={(e) => { stop(e); ondelete?.(asset); }}
                title={$t('common.delete')}
            >
                <Trash2 size={15} />
            </button>
        </div>
    </div>
</div>

