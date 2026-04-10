<!--
  LiveTicker.svelte — Svelte 5

  Compact live-price badges for assets.
  Polls POST /api/v1/assets/prices/current every 30 seconds.
  Shows asset icon + name + price + flag + currency code.

  Usage:
  - Dashboard:          <LiveTicker />                           (all active assets)
  - AssetPriceSummary:  <LiveTicker assetIds={[42]} maxItems={1} />

  Behaviour:
  - Only polls while mounted (stops on unmount)
  - Shows "--" placeholder while prices are loading (non-blocking)
  - Badge colors change dynamically (green if price went up, red if down)
  - Fully responsive (visible on mobile too)
-->
<script lang="ts">
    import {onMount, onDestroy} from 'svelte';
    import {_} from '$lib/i18n';
    import {axiosInstance} from '$lib/api';
    import {RefreshCw} from 'lucide-svelte';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import {fetchCurrentPrices, computeDirection} from '$lib/services/livePriceService';
    import type {LivePriceDirection} from '$lib/services/livePriceService';
    import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/currencyStore';
    import {currentLanguage} from '$lib/stores/language';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Explicit asset IDs to track. If empty/undefined, loads all active assets. */
        assetIds?: number[];
        /** Polling interval in milliseconds (default: 30s) */
        pollInterval?: number;
        /** Max items to show (0 = unlimited) */
        maxItems?: number;
    }

    let {
        assetIds: propAssetIds,
        pollInterval = 30_000,
        maxItems = 0,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    interface TickerItem {
        assetId: number;
        displayName: string;
        currency: string;
        iconUrl: string | null;
        assetType: string | null;
        value: number | null;
        direction: LivePriceDirection;
        source: string | null;
    }

    let items: TickerItem[] = $state([]);
    let initializing = $state(true);
    let error: string | null = $state(null);
    let intervalId: ReturnType<typeof setInterval> | null = null;

    // Resolved asset IDs (from props or loaded from API)
    let resolvedIds: number[] = $state([]);
    let assetMetaMap = new Map<number, { name: string; currency: string; iconUrl: string | null; assetType: string | null }>();

    // Ensure currency info is loaded for flag display
    ensureCurrenciesLoaded($currentLanguage);

    // =========================================================================
    // Data fetching
    // =========================================================================

    /** Load asset list and build placeholder items immediately, then fetch prices in background. */
    async function loadAndFetch() {
        try {
            const assetsRes = await axiosInstance.get('/api/v1/assets/query');
            const assets: any[] = Array.isArray(assetsRes.data) ? assetsRes.data : [];
            for (const a of assets) {
                assetMetaMap.set(a.id, {
                    name: a.display_name ?? `#${a.id}`,
                    currency: a.currency ?? '',
                    iconUrl: a.icon_url ?? null,
                    assetType: a.asset_type ?? null,
                });
            }

            if (propAssetIds && propAssetIds.length > 0) {
                resolvedIds = propAssetIds;
            } else {
                resolvedIds = assets.map((a: any) => a.id);
            }

            if (resolvedIds.length === 0) {
                items = [];
                initializing = false;
                return;
            }

            // Build placeholder items with value=null (renders "--")
            items = resolvedIds.map(id => {
                const meta = assetMetaMap.get(id);
                return {
                    assetId: id,
                    displayName: meta?.name ?? `#${id}`,
                    currency: meta?.currency ?? '',
                    iconUrl: meta?.iconUrl ?? null,
                    assetType: meta?.assetType ?? null,
                    value: null,
                    direction: 'neutral' as LivePriceDirection,
                    source: null,
                };
            });
            initializing = false;

            // Fire-and-forget: fetch prices in background (non-blocking)
            fetchPrices();
        } catch (e: any) {
            console.error('[LiveTicker] loadAndFetch error', e);
            error = e?.message || 'Failed';
            initializing = false;
        }
    }

    /** Fetch current prices using shared service (non-blocking update). */
    async function fetchPrices() {
        if (resolvedIds.length === 0) return;

        try {
            const results = await fetchCurrentPrices(resolvedIds);

            // Build previous value lookup from current items
            const prevMap = new Map<number, number | null>();
            for (const it of items) {
                prevMap.set(it.assetId, it.value);
            }

            items = results.map(r => {
                const meta = assetMetaMap.get(r.assetId);
                const prev = prevMap.get(r.assetId) ?? null;
                return {
                    assetId: r.assetId,
                    displayName: meta?.name ?? `#${r.assetId}`,
                    currency: r.currency || meta?.currency || '',
                    iconUrl: meta?.iconUrl ?? null,
                    assetType: meta?.assetType ?? null,
                    value: r.value,
                    direction: computeDirection(r.value, prev),
                    source: r.source,
                };
            });
            error = null;
        } catch (e: any) {
            console.error('[LiveTicker] fetchPrices error', e);
            error = e?.message || 'Fetch error';
        }
    }

    // =========================================================================
    // Lifecycle
    // =========================================================================

    onMount(() => {
        loadAndFetch();
        intervalId = setInterval(fetchPrices, pollInterval);
    });

    onDestroy(() => {
        if (intervalId) clearInterval(intervalId);
    });

    // =========================================================================
    // Helpers
    // =========================================================================

    /** Dynamic badge color based on price direction. */
    function badgeClasses(dir: LivePriceDirection): string {
        switch (dir) {
            case 'up':
                return 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-300 dark:border-emerald-700 text-emerald-800 dark:text-emerald-200';
            case 'down':
                return 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700 text-red-800 dark:text-red-200';
            default:
                return 'bg-gray-50 dark:bg-slate-800 border-gray-200 dark:border-slate-700 text-gray-900 dark:text-white';
        }
    }

    // Computed: visible items (optionally capped)
    let visibleItems = $derived(maxItems > 0 ? items.slice(0, maxItems) : items);
</script>

<!-- Ticker container -->
<div class="flex flex-wrap items-center gap-2" data-testid="live-ticker">

    {#if initializing}
        <span class="text-xs text-gray-400 dark:text-gray-500 animate-pulse flex items-center gap-1">
            <RefreshCw size={12} class="animate-spin"/>
            {$_('ticker.loading')}
        </span>

    {:else if error && items.length === 0}
        <span class="text-xs text-red-500 dark:text-red-400" title={error}>
            {$_('ticker.errorFetching')}
        </span>

    {:else if items.length === 0}
        <span class="text-xs text-gray-400 dark:text-gray-500">
            {$_('ticker.noAssets')}
        </span>

    {:else}
        {#each visibleItems as item (item.assetId)}
            <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full
                        text-xs whitespace-nowrap border transition-colors duration-300
                        {badgeClasses(item.direction)}"
                 title="{item.displayName} — {item.source ?? ''}">

                <!-- Asset icon -->
                <AssetIcon iconUrl={item.iconUrl} assetType={item.assetType} altText={item.displayName} size="sm" />

                <!-- Asset name (truncated) -->
                <span class="font-medium max-w-[6rem] truncate">
                    {item.displayName}
                </span>

                <!-- Price: value + flag + code -->
                <span class="font-semibold">
                    {item.value != null ? item.value.toFixed(2) : '--'}
                </span>
                <span class="emoji-flag">{getCurrencyInfo(item.currency).flag_emoji}</span>
                <span class="text-[10px] text-gray-500 dark:text-gray-400">{item.currency}</span>
            </div>
        {/each}
    {/if}
</div>
