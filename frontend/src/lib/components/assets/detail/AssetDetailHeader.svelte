<!--
  AssetDetailHeader — the header of the asset detail page: back button, icon, status dot, name,
  type, currency, transactions link, provider chip, external link, live-updates status, and the
  browse navigation. Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ArrowLeft, ExternalLink} from 'lucide-svelte';
    import AssetBrowseNav from '$lib/components/assets/AssetBrowseNav.svelte';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import LiveUpdatesStatus from '$lib/features/live-updates/LiveUpdatesStatus.svelte';
    import type {ActivePollingState} from '$lib/features/live-updates/activePolling';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {goBack} from '$lib/stores/app/navigationStore';
    import type {AssetDetail} from '$lib/types';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';

    interface Props {
        /** The asset the page shows, for its browse navigation; known before its details load. */
        assetId: number;
        assetInfo: AssetDetail | null;
        loading: boolean;
        currencyFlag: string;
        providerIconUrl: string | null;
        assetProviderName: string;
        userUrl: string | null;
        providerExternalUrl: string | null;
        /** The asset's transactions list, filtered on it (built by the page). */
        transactionsHref: string;
        liveUpdatesState: ActivePollingState;
    }

    let {assetId, assetInfo, loading, currencyFlag, providerIconUrl, assetProviderName, userUrl, providerExternalUrl, transactionsHref, liveUpdatesState}: Props = $props();
</script>

<div class="flex items-center gap-3" data-testid="asset-detail-header" use:guideAnchor={'asset.detail.header'}>
    <button class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-gray-400 transition-colors" data-testid="asset-detail-back-btn" onclick={() => goBack('/assets')} title={$t('assetDetail.backToList')}>
        <ArrowLeft size={20} />
    </button>

    {#if assetInfo}
        <!-- min-w-0 on both wrappers: without it their minimum width is the whole title on one
             line, so a long name widened the page (below ~341 px, and just above 1024 px where
             the title loses its max width); the title itself scrolls (scrollOnOverflow). -->
        <div class="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 min-w-0" data-testid="asset-detail-info">
            <div class="flex items-center gap-3 min-w-0">
                <AssetIcon iconUrl={assetInfo.icon_url} assetType={assetInfo.asset_type} altText={assetInfo.display_name} size="md" />
                <span class="w-2.5 h-2.5 rounded-full shrink-0 {assetInfo.active !== false ? 'bg-green-500' : 'bg-red-400'}" data-testid="asset-status-dot" title={assetInfo.active !== false ? $t('common.active') : $t('assets.status.archived')}></span>
                <h2 use:scrollOnOverflow class="{overflowScrollTextClass} text-xl font-bold text-gray-800 dark:text-gray-100 max-w-[15ch] sm:max-w-[30ch] lg:max-w-none" title={assetInfo.display_name}>{assetInfo.display_name}</h2>
            </div>

            <div class="flex items-center gap-2 flex-wrap ml-0 sm:ml-0">
                {#if assetInfo.asset_type}
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300">
                        <img src={getAssetTypeIconUrl(assetInfo.asset_type)} alt="" class="w-3.5 h-3.5" />
                        {$t(`assets.types.${assetInfo.asset_type}`)}
                    </span>
                {/if}

                <span class="text-lg emoji-flag">{currencyFlag}</span>
                <span class="text-sm font-mono text-gray-500 dark:text-gray-400">{assetInfo.currency}</span>
                {#if (assetInfo.tx_count ?? 0) > 0}
                    <a href={transactionsHref} data-testid="asset-detail-transactions-link" class="text-xs font-medium text-blue-600 hover:underline dark:text-blue-400">
                        {$t('transactions.title')} ({assetInfo.tx_count})
                    </a>
                {/if}

                {#if assetInfo.provider_code}
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
                        {#if providerIconUrl}
                            <img src={providerIconUrl} alt="" class="w-3.5 h-3.5 rounded-sm object-contain" />
                        {/if}
                        {assetProviderName}
                    </span>
                {:else}
                    <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"> ✏️ Manual </span>
                {/if}

                {#if userUrl || providerExternalUrl}
                    <a href={userUrl || providerExternalUrl} target="_blank" rel="noopener noreferrer" class="inline-flex items-center p-1 rounded text-gray-400 hover:text-libre-green transition-colors" title={userUrl || providerExternalUrl}>
                        <ExternalLink size={14} />
                    </a>
                {/if}
                <LiveUpdatesStatus state={liveUpdatesState} />
            </div>
        </div>
    {:else if loading}
        <div class="h-8 w-48 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
    {/if}
    <AssetBrowseNav {assetId} />
</div>
