<!--
  AssetBrowseNav — ‹ previous · n/N · next › between assets, in the asset detail header (K step 16, item 2).

  The developer's decisions (06/10): the buttons follow the list the user left — its filters, its view
  and, in the table, its sort, published by the list through `assetBrowse.ts`. With no such list (a
  direct link, another page, a reload, an asset that list does not hold) they follow every asset in
  the list's default order. A move replaces the current history entry, so one Back returns to the
  list. Disabled at the edges, hidden below two assets. Buttons only: no keyboard shortcut.

  The order is chosen when the page is entered and kept while moving sideways between assets, so a
  list that changed meanwhile cannot reshuffle the way through it. `data-state` (pending, ready, none)
  and `data-source` (list, default) publish the decision.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {get} from 'svelte/store';
    import {afterNavigate, goto} from '$app/navigation';
    import {navigating} from '$app/stores';
    import {ChevronLeft, ChevronRight} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {expectReplaceNavigation} from '$lib/stores/app/navigationStore';
    import {browseNeighbours, defaultAssetBrowseOrder, getAssetListOrder} from './assetBrowse';

    interface Props {
        /** The asset the detail page shows. */
        assetId: number;
    }

    let {assetId}: Props = $props();

    const DETAIL_ROUTE = '/(app)/assets/[id]';
    const LIST_ROUTE = '/(app)/assets';

    let order = $state<number[] | null>(null);
    let source = $state<'list' | 'default' | null>(null);
    let failed = $state(false);
    /** Discards a default-order fetch overtaken by a later decision (a plain counter: never rendered). */
    let decision = 0;

    let position = $derived(order ? browseNeighbours(order, assetId) : null);
    let browseState = $derived<'pending' | 'ready' | 'none'>(failed ? 'none' : order === null ? 'pending' : position !== null && position.total >= 2 ? 'ready' : 'none');

    async function followDefaultOrder(currentId: number): Promise<void> {
        const mine = ++decision;
        order = null;
        failed = false;
        source = 'default';
        try {
            const items = await zodiosApi.list_assets_api_v1_assets_query_get({queries: {}});
            if (mine !== decision) return;
            order = defaultAssetBrowseOrder(items, currentId);
        } catch {
            if (mine !== decision) return;
            failed = true;
        }
    }

    afterNavigate((navigation) => {
        const from = navigation.from?.route.id ?? null;
        // A first-load call arriving after the mount already decided (see onMount): nothing new.
        if (from === null && source !== null) return;
        // A sideways move between assets keeps the way already chosen, if it holds the new asset
        // (another link — the risk tab's — can land outside it: then the default order).
        if (from === DETAIL_ROUTE && order?.includes(assetId)) return;
        if (from === LIST_ROUTE) {
            const listOrder = getAssetListOrder();
            if (listOrder?.includes(assetId)) {
                decision++;
                failed = false;
                order = listOrder;
                source = 'list';
                return;
            }
        }
        void followDefaultOrder(assetId);
    });

    // SvelteKit calls afterNavigate callbacks only when a navigation ends, and `navigating` stays set
    // until then. Mounted with no navigation in flight, this component appeared after its navigation
    // had ended — the app layout shows the page only once the session is checked — so nobody will call
    // the callback: a direct entry, which follows the default order.
    onMount(() => {
        if (get(navigating) === null && source === null) void followDefaultOrder(assetId);
    });

    function browseTo(targetId: number | null): void {
        if (targetId === null) return;
        // The live query, not $page.url's: the detail page rewrites its date range with
        // history.replaceState (dateRangeUrl.ts), which SvelteKit does not track.
        const url = `/assets/${targetId}${window.location.search}`;
        expectReplaceNavigation(url);
        void goto(url, {replaceState: true, keepFocus: true});
    }

    const buttonClass = 'p-2 rounded-lg text-gray-500 dark:text-gray-400 transition-colors hover:bg-gray-100 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent dark:disabled:hover:bg-transparent';
</script>

<div class="contents" data-testid="asset-browse" data-state={browseState} data-source={source ?? undefined}>
    {#if browseState === 'ready' && position}
        <nav class="ml-auto flex shrink-0 items-center gap-0.5" data-testid="asset-browse-nav" aria-label={$t('assetDetail.browse.position', {values: {current: position.index + 1, total: position.total}})}>
            <button type="button" class={buttonClass} data-testid="asset-browse-prev" disabled={position.previous === null} aria-label={$t('assetDetail.browse.previous')} title={$t('assetDetail.browse.previous')} onclick={() => browseTo(position?.previous ?? null)}>
                <ChevronLeft size={20} />
            </button>
            <span class="text-xs tabular-nums whitespace-nowrap text-gray-500 dark:text-gray-400" data-testid="asset-browse-position" aria-hidden="true">{position.index + 1}/{position.total}</span>
            <button type="button" class={buttonClass} data-testid="asset-browse-next" disabled={position.next === null} aria-label={$t('assetDetail.browse.next')} title={$t('assetDetail.browse.next')} onclick={() => browseTo(position?.next ?? null)}>
                <ChevronRight size={20} />
            </button>
        </nav>
    {/if}
</div>
