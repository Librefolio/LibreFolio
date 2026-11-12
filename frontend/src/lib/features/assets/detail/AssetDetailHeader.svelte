<!--
  AssetDetailHeader — the header of the asset detail page: back button, icon, status dot, name,
  type, currency, transactions link, provider chip, external link, live-updates status, and the
  browse navigation. Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {ArrowLeft, ArrowRightLeft, ExternalLink} from 'lucide-svelte';
    import AssetBrowseNav from '$lib/features/assets/AssetBrowseNav.svelte';
    import AssetIcon from '$lib/features/assets/AssetIcon.svelte';
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

    /** Layout of the header pills; the colour roles stay literal in the markup. */
    const badgeBase = 'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium';

    /** The page the provider badge opens: the address set on the asset, else the provider's. */
    const externalHref = $derived(userUrl || providerExternalUrl || null);
    const badgeName = $derived(assetInfo?.provider_code ? assetProviderName : $t('assetDetail.manualChip'));
    /** The host of an address, or the address itself when it does not parse. */
    function siteOf(href: string): string {
        try {
            return new URL(href).hostname;
        } catch {
            return href;
        }
    }
    /** Where the badge leads (tooltip and accessible name; it contains the visible name, WCAG 2.5.3). */
    const hint = $derived(externalHref ? $t('assetDetail.externalLinkHint', {values: {name: badgeName, site: siteOf(externalHref)}}) : undefined);
</script>

<div class="flex flex-wrap sm:flex-nowrap items-start lg:items-center gap-x-3 gap-y-2" data-testid="asset-detail-header" use:guideAnchor={'asset.detail.header'}>
    <button class="p-2 rounded-lg hover:bg-lf-hover text-lf-muted transition-colors focus-visible:outline-lf-focus" data-testid="asset-detail-back-btn" onclick={() => goBack('/assets')} title={$t('assetDetail.backToList')} aria-label={$t('assetDetail.backToList')}>
        <ArrowLeft size={20} />
    </button>

    {#if assetInfo}
        <!-- min-w-0 on both wrappers: without it their minimum width is the whole title on one
             line, so a long name widened the page; the title itself scrolls (scrollOnOverflow).
             Below lg the badges sit on a row of their own under the icon and name, and the name
             may use the whole width (max-w-full); from lg up it is one row, as it always was.
             Below sm the block takes a full row after the back button and the nav (order-last
             basis-full): row 1 ← and ‹ n/N ›, row 2 the name, rows 3-4 the two badge groups. -->
        <div class="order-last basis-full sm:order-none sm:basis-auto flex flex-col lg:flex-row lg:items-center gap-1 lg:gap-3 min-w-0" data-testid="asset-detail-info">
            <div class="flex items-center gap-3 min-w-0" data-testid="asset-detail-identity">
                <AssetIcon iconUrl={assetInfo.icon_url} assetType={assetInfo.asset_type} altText={assetInfo.display_name} size="md" />
                <span class="w-2.5 h-2.5 rounded-full shrink-0 {assetInfo.active !== false ? 'bg-lf-success' : 'bg-lf-danger'}" data-testid="asset-status-dot" title={assetInfo.active !== false ? $t('common.active') : $t('assets.status.archived')}></span>
                <h2 use:scrollOnOverflow data-testid="asset-detail-name" class="{overflowScrollTextClass} text-xl font-bold text-lf-primary max-w-full lg:max-w-none" title={assetInfo.display_name}>{assetInfo.display_name}</h2>
            </div>

            <div class="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:flex-wrap min-w-0">
                <div class="flex items-center gap-2 flex-nowrap" data-testid="asset-detail-badges-what">
                    {#if assetInfo.asset_type}
                        <span data-testid="asset-detail-type-badge" class="{badgeBase} bg-lf-neutral text-lf-secondary">
                            <img src={getAssetTypeIconUrl(assetInfo.asset_type)} alt="" class="w-3.5 h-3.5" />
                            {$t(`assets.types.${assetInfo.asset_type}`)}
                        </span>
                    {/if}

                    <span class="text-lg emoji-flag">{currencyFlag}</span>
                    <span class="text-sm font-mono text-lf-muted" data-testid="asset-detail-currency">{assetInfo.currency}</span>
                </div>
                <div class="flex items-center gap-2 flex-nowrap max-w-full min-w-0" data-testid="asset-detail-badges-where">
                    {#if (assetInfo.tx_count ?? 0) > 0}
                        <a href={transactionsHref} data-testid="asset-detail-transactions-link" class="{badgeBase} border border-lf-focus text-lf-link hover:bg-lf-selected focus-visible:outline-lf-focus">
                            <ArrowRightLeft size={12} />
                            {$t('transactions.title')}
                            <span class="font-bold" data-testid="asset-detail-transactions-count">{assetInfo.tx_count}</span>
                        </a>
                    {/if}

                    <svelte:element
                        this={externalHref ? 'a' : 'span'}
                        data-testid="asset-detail-provider-badge"
                        data-linked={externalHref ? 'true' : 'false'}
                        href={externalHref ?? undefined}
                        target={externalHref ? '_blank' : undefined}
                        rel={externalHref ? 'noopener noreferrer' : undefined}
                        title={hint}
                        aria-label={hint}
                        class="{badgeBase} min-w-0 max-w-full {assetInfo.provider_code ? 'bg-lf-success-soft text-lf-success-on-soft' : 'bg-lf-warning-soft text-lf-warning-on-soft'} {externalHref ? 'hover:underline focus-visible:outline-lf-focus' : ''}"
                    >
                        {#if assetInfo.provider_code}
                            {#if providerIconUrl}
                                <img src={providerIconUrl} alt="" class="w-3.5 h-3.5 rounded-sm object-contain shrink-0" />
                            {/if}
                            <span class="truncate">{badgeName}</span>
                        {:else}
                            <span class="truncate">✏️ {badgeName}</span>
                        {/if}
                        {#if externalHref}
                            <ExternalLink size={12} class="shrink-0" />
                        {/if}
                    </svelte:element>
                </div>
                <LiveUpdatesStatus state={liveUpdatesState} />
            </div>
        </div>
    {:else if loading}
        <div class="order-last basis-full sm:order-none sm:basis-auto h-8 w-48 bg-lf-neutral rounded animate-pulse"></div>
    {/if}
    <AssetBrowseNav {assetId} />
</div>
