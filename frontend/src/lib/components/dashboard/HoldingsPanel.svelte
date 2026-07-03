<!--
  HoldingsPanel — Compact read-only list of current portfolio holdings.

  Shows a summary table of holdings from portfolioStore.fetchSummary().
  Columns: Asset (icon + name), Current Price, Value, Gain%.
  Footer: "See all →" link to /assets (preserves date range).

  Data is passed in as props (already fetched by the parent dashboard page).

  Pattern: Svelte 5 Runes, data-testid, dark mode.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {ensureAssetsLoaded, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {onMount} from 'svelte';

    // Use the holding type from portfolioStore's re-exported type
    interface Holding {
        asset_id: number;
        asset_name: string;
        asset_ticker?: string | (string | null)[] | null;
        asset_type: string;
        current_price?: string | (string | null)[] | null;
        current_value?: string | (string | null)[] | null;
        gain_loss_percent?: string | (string | null)[] | null;
    }

    interface Props {
        holdings: Holding[];
        loading?: boolean;
        /** Pre-built href for "See all" link (includes date range params). */
        assetsHref?: string;
    }

    let {holdings = [], loading = false, assetsHref = '/assets'}: Props = $props();

    onMount(async () => {
        await ensureAssetsLoaded();
    });

    // =========================================================================
    // Helpers
    // =========================================================================

    function safeNum(v: string | (string | null)[] | null | undefined): number | null {
        const s = Array.isArray(v) ? (v[0] ?? null) : v;
        if (s == null) return null;
        const n = parseFloat(s);
        return isNaN(n) ? null : n;
    }

    function formatPrice(v: string | (string | null)[] | null | undefined): string {
        const n = safeNum(v);
        return n == null ? '—' : n.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }

    function formatValue(v: string | (string | null)[] | null | undefined): string {
        const n = safeNum(v);
        return n == null ? '—' : n.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }

    function formatGainPct(v: string | (string | null)[] | null | undefined): string {
        const n = safeNum(v);
        if (n == null) return '—';
        const pct = n * 100;
        return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
    }

    function gainClass(v: string | (string | null)[] | null | undefined): string {
        const n = safeNum(v);
        if (n == null) return 'text-gray-400 dark:text-gray-500';
        return n >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400';
    }

    function assetIconHtml(holding: Holding): string {
        const info = getAssetInfo(holding.asset_id);
        const src = info?.icon_url || getAssetTypeIconUrl(holding.asset_type);
        if (src) {
            return `<img src="${src}" alt="" class="w-5 h-5 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />`;
        }
        return `<div class="w-5 h-5 rounded-full bg-libre-green/10 flex items-center justify-center shrink-0 text-[10px] text-libre-green font-bold">${(holding.asset_name ?? '?')[0].toUpperCase()}</div>`;
    }
</script>

<div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col" data-testid="holdings-panel">
    <!-- Header -->
    <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">
            {$_('dashboard.holdings')}
        </h2>
        <a href={assetsHref} class="text-xs text-libre-green dark:text-green-400 hover:underline font-medium" data-testid="holdings-see-all">
            {$_('common.seeAll')}
        </a>
    </div>

    {#if loading}
        <div class="space-y-2 flex-1">
            {#each {length: 4} as _}
                <div class="h-9 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
            {/each}
        </div>
    {:else if holdings.length === 0}
        <p class="text-sm text-gray-400 dark:text-gray-500 py-4 text-center flex-1 flex items-center justify-center">
            {$_('common.noData')}
        </p>
    {:else}
        <div class="overflow-x-auto flex-1">
            <table class="w-full text-xs">
                <thead>
                    <tr class="text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-slate-700">
                        <th class="text-left pb-2 pr-3 font-medium">{$_('common.asset')}</th>
                        <th class="text-right pb-2 pr-3 font-medium">{$_('assets.lastPrice')}</th>
                        <th class="text-right pb-2 pr-3 font-medium">{$_('common.value')}</th>
                        <th class="text-right pb-2 font-medium">Gain%</th>
                    </tr>
                </thead>
                <tbody>
                    {#each holdings as holding (holding.asset_id)}
                        <tr class="border-b border-gray-50 dark:border-slate-700/50 hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors" data-testid="holding-row">
                            <!-- Asset icon + name -->
                            <td class="py-2 pr-3">
                                <div class="flex items-center gap-1.5 min-w-0">
                                    {@html assetIconHtml(holding)}
                                    <span class="truncate max-w-[120px] text-gray-700 dark:text-gray-200 font-medium">{holding.asset_name}</span>
                                </div>
                            </td>
                            <!-- Current price -->
                            <td class="py-2 pr-3 text-right text-gray-600 dark:text-gray-300 whitespace-nowrap">
                                {formatPrice(holding.current_price)}
                            </td>
                            <!-- Current value -->
                            <td class="py-2 pr-3 text-right text-gray-700 dark:text-gray-200 font-medium whitespace-nowrap">
                                {formatValue(holding.current_value)}
                            </td>
                            <!-- Gain % -->
                            <td class="py-2 text-right font-medium whitespace-nowrap {gainClass(holding.gain_loss_percent)}">
                                {formatGainPct(holding.gain_loss_percent)}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>
