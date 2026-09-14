<script lang="ts">
    import {t} from '$lib/i18n';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {currencyStoreVersion, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {getIndexColor} from '$lib/utils/colors';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {AlertCircle, Check, LoaderCircle, Plus, RefreshCw, Search} from 'lucide-svelte';
    import type {PacAllocationUsageScope} from './allocationSource';
    import type {PacAssetChoice} from './editorTypes';

    interface Props {
        assets: readonly PacAssetChoice[];
        loading: boolean;
        error: string | null;
        disabled?: boolean;
        ontoggle: (asset: PacAssetChoice) => void;
        onretry: () => void;
        onaddmanual: () => void;
    }

    const SCOPE_ORDER: readonly PacAllocationUsageScope[] = ['owned', 'other_users', 'observed'];

    let {assets, loading, error, disabled = false, ontoggle, onretry, onaddmanual}: Props = $props();
    let query = $state('');
    let selectedScopes = $state<PacAllocationUsageScope[]>(['owned']);

    let scopeCounts = $derived.by(() => {
        const counts: Record<PacAllocationUsageScope, number> = {owned: 0, other_users: 0, observed: 0};
        for (const asset of assets) counts[asset.usageScope] += 1;
        return counts;
    });

    let filteredAssets = $derived.by(() => {
        const normalized = query.trim().toLocaleLowerCase();
        return assets
            .map((asset, index) => ({asset, index}))
            .filter(({asset}) => selectedScopes.includes(asset.usageScope) && (!normalized || asset.name.toLocaleLowerCase().includes(normalized)))
            .sort((left, right) => Number(right.asset.active) - Number(left.asset.active) || left.index - right.index)
            .map(({asset}) => asset);
    });

    function toggleScope(scope: PacAllocationUsageScope): void {
        const selected = new Set(selectedScopes);
        if (selected.has(scope)) selected.delete(scope);
        else selected.add(scope);
        selectedScopes = SCOPE_ORDER.filter((candidate) => selected.has(candidate));
    }

    function scopeLabel(scope: PacAllocationUsageScope): string {
        if (scope === 'owned') return $t('tools.pacAllocator.gallery.owned', {default: 'Owned'});
        if (scope === 'other_users') return $t('tools.pacAllocator.gallery.otherUsers', {default: 'Other users'});
        return $t('tools.pacAllocator.gallery.observed', {default: 'Observed'});
    }

    function scopeStyle(scope: PacAllocationUsageScope): string {
        const colors = getIndexColor(SCOPE_ORDER.indexOf(scope), 140);
        return `--scope-bg:${colors.bg};--scope-text:${colors.text};--scope-dark-bg:${colors.darkBg};--scope-dark-text:${colors.darkText};--scope-border:${colors.vivid};`;
    }

    function displayDecimal(value: string | null | undefined): string {
        return formatDecimalForDisplay(value, {maxFrac: 12}) || '0';
    }

    function currencyFlag(code: string | null | undefined): string {
        void $currencyStoreVersion;
        const flag = getCurrencyInfo(code ?? '').flag_emoji;
        return flag === '🏳️' ? '' : flag;
    }

    function cardClass(asset: PacAssetChoice): string {
        if (asset.selected && !asset.active) return 'border-libre-green bg-amber-50 ring-1 ring-libre-green/30 dark:border-green-600 dark:bg-amber-950/30';
        if (asset.selected) return 'border-libre-green bg-libre-green/5 dark:border-green-600 dark:bg-green-950/20';
        if (!asset.active) return 'border-amber-300 bg-amber-50 hover:border-amber-400 dark:border-amber-800 dark:bg-amber-950/30 dark:hover:border-amber-700';
        return 'border-gray-200 bg-white hover:border-libre-green/60 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900/40 dark:hover:border-green-700 dark:hover:bg-gray-800';
    }
</script>

<section class="space-y-3" data-testid="pac-owned-assets" data-gallery="catalog">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white">{$t('tools.pacAllocator.gallery.title', {default: '2. Assets and targets'})}</h3>
            <p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                {$t('tools.pacAllocator.gallery.hint', {default: 'Select current custody contexts or add a zero-position catalog candidate.'})}
            </p>
        </div>
        <div class="flex shrink-0 items-center gap-1.5">
            <Tooltip text={$t('common.refresh')} position="top" interactiveChild>
                <button
                    class="inline-flex h-10 w-10 items-center justify-center rounded-md text-gray-500 transition hover:bg-gray-100 hover:text-libre-green focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70 disabled:cursor-not-allowed disabled:opacity-50 sm:h-8 sm:w-8 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-green-300"
                    type="button"
                    onclick={onretry}
                    disabled={loading}
                    data-testid="pac-owned-assets-refresh"
                    aria-label={$t('common.refresh')}
                >
                    <RefreshCw class={loading ? 'animate-spin' : ''} size={15} />
                </button>
            </Tooltip>
            <button
                class="inline-flex min-h-10 items-center justify-center gap-1.5 whitespace-nowrap rounded-md border border-libre-green bg-libre-green px-2.5 py-1.5 text-xs font-semibold text-white transition hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70 sm:min-h-8 dark:text-gray-950"
                type="button"
                onclick={onaddmanual}
                data-testid="pac-add-manual-asset"
                aria-label={$t('tools.pacAllocator.addManualAsset')}
            >
                <Plus size={15} />
                <span class="hidden sm:inline">{$t('tools.pacAllocator.addManualAsset')}</span>
            </button>
        </div>
    </div>

    {#if loading && assets.length === 0}
        <div class="flex min-h-28 items-center justify-center gap-2 rounded-xl border border-gray-200 bg-gray-50 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900/40 dark:text-gray-400" data-testid="pac-owned-assets-loading">
            <LoaderCircle class="animate-spin" size={18} />
            <span>{$t('tools.pacAllocator.loadingOwnedAssets')}</span>
        </div>
    {:else if error && assets.length === 0}
        <div class="flex min-h-28 flex-col items-center justify-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 text-center dark:border-red-900/60 dark:bg-red-950/20" data-testid="pac-owned-assets-error">
            <div class="flex items-center gap-2 text-sm font-medium text-red-700 dark:text-red-300">
                <AlertCircle size={17} />
                <span>{error}</span>
            </div>
            <button
                class="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/70 disabled:cursor-not-allowed disabled:opacity-50 sm:min-h-8 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
                type="button"
                onclick={onretry}
                disabled={loading}
                data-testid="pac-owned-assets-retry"
            >
                <RefreshCw class={loading ? 'animate-spin' : ''} size={15} />
                <span>{$t('common.retry')}</span>
            </button>
        </div>
    {:else if assets.length === 0}
        <div class="rounded-xl border border-dashed border-gray-300 px-4 py-8 text-center dark:border-gray-700" data-testid="pac-owned-assets-empty">
            <p class="text-sm font-medium text-gray-700 dark:text-gray-200">{$t('tools.pacAllocator.gallery.empty', {default: 'No Asset candidates found'})}</p>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.noOwnedAssetsHint')}</p>
        </div>
    {:else}
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div class="flex flex-wrap gap-2" data-testid="pac-asset-scope-filters">
                {#each SCOPE_ORDER as scope}
                    {@const selected = selectedScopes.includes(scope)}
                    <button
                        type="button"
                        class="scope-badge inline-flex min-h-8 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/60 {selected ? 'ring-1 ring-current' : 'opacity-80 hover:opacity-100'}"
                        style={scopeStyle(scope)}
                        aria-pressed={selected}
                        onclick={() => toggleScope(scope)}
                        data-testid={`pac-asset-scope-${scope}`}
                        data-scope-color={scope}
                    >
                        {#if selected}<Check size={12} strokeWidth={3} />{/if}
                        {scopeLabel(scope)}
                        <span class="rounded-full bg-black/10 px-1.5 py-0.5 tabular-nums dark:bg-white/10">{scopeCounts[scope]}</span>
                    </button>
                {/each}
            </div>
            <div class="relative w-full lg:max-w-sm">
                <Search class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                <input
                    class="min-h-10 w-full rounded-lg border border-gray-300 bg-white py-1.5 pr-2 pl-9 text-sm text-gray-900 outline-none transition focus:border-libre-green focus:ring-1 focus:ring-libre-green sm:min-h-9 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                    type="search"
                    bind:value={query}
                    placeholder={$t('tools.pacAllocator.gallery.search', {default: 'Search by Asset name'})}
                    aria-label={$t('tools.pacAllocator.gallery.search', {default: 'Search by Asset name'})}
                    data-testid="pac-owned-assets-search"
                />
            </div>
        </div>

        {#if error}
            <div class="flex items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/20 dark:text-amber-200">
                <span>{error}</span>
                <Tooltip text={$t('common.retry')} position="top" interactiveChild>
                    <button
                        class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-amber-800 transition hover:bg-amber-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-600/70 disabled:cursor-not-allowed disabled:opacity-50 sm:h-8 sm:w-8 dark:text-amber-200 dark:hover:bg-amber-900/30"
                        type="button"
                        onclick={onretry}
                        disabled={loading}
                        data-testid="pac-owned-assets-retry-inline"
                        aria-label={$t('common.retry')}
                    >
                        <RefreshCw class={loading ? 'animate-spin' : ''} size={14} />
                    </button>
                </Tooltip>
            </div>
        {/if}

        <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {#each filteredAssets as asset (asset.assetId)}
                {@const modified = asset.modifiedSourceKeys.length > 0}
                {@const stale = asset.staleSourceKeys.length > 0}
                <button
                    type="button"
                    class={`group relative flex min-h-20 items-start gap-2.5 rounded-lg border p-2.5 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-libre-green/60 ${cardClass(asset)}`}
                    aria-pressed={asset.selected}
                    onclick={() => ontoggle(asset)}
                    {disabled}
                    data-testid={`pac-owned-asset-${asset.assetId}`}
                    data-usage-scope={asset.usageScope}
                    data-lifecycle={asset.active ? 'active' : 'inactive'}
                >
                    <AssetIcon iconUrl={asset.iconUrl} assetType={asset.assetType} altText={asset.name} size="md" />
                    <span class="min-w-0 flex-1">
                        <span class="flex items-start justify-between gap-2">
                            <span class="min-w-0">
                                <span class="block truncate text-sm font-semibold text-gray-900 dark:text-white">{asset.name}</span>
                                <span class="block truncate text-xs text-gray-500 dark:text-gray-400">
                                    {asset.ticker ?? asset.assetType} ·
                                    {#if asset.contexts.length > 0}
                                        {asset.contexts.length}
                                        {asset.contexts.length === 1 ? $t('tools.pacAllocator.custodyContext') : $t('tools.pacAllocator.custodyContexts')}
                                    {:else}
                                        {$t('tools.pacAllocator.gallery.zeroPosition', {default: 'initial quantity 0'})}
                                    {/if}
                                </span>
                            </span>
                            <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border {asset.selected ? 'border-libre-green bg-libre-green text-white' : 'border-gray-300 text-transparent dark:border-gray-600'}">
                                <Check size={13} strokeWidth={3} />
                            </span>
                        </span>
                        <span class="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
                            <span class="scope-badge rounded-full border px-2 py-0.5" style={scopeStyle(asset.usageScope)} data-scope-color={asset.usageScope}>{scopeLabel(asset.usageScope)}</span>
                            {#if !asset.active}
                                <span class="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200">{$t('tools.pacAllocator.gallery.inactive', {default: 'Inactive'})}</span>
                            {/if}
                            {#if asset.quote.rawPrice}
                                <span class="rounded-full bg-gray-100 px-2 py-0.5 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                                    {#if currencyFlag(asset.quote.currency)}<span class="emoji-flag" aria-hidden="true">{currencyFlag(asset.quote.currency)}</span>{/if}
                                    {asset.quote.currency}
                                    <span class="font-mono">{displayDecimal(asset.quote.rawPrice)}</span>
                                </span>
                            {:else}
                                <span class="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">{$t('tools.pacAllocator.missingPrice')}</span>
                            {/if}
                            {#if modified}
                                <span class="rounded-full bg-blue-100 px-2 py-0.5 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200">{$t('tools.pacAllocator.modified')}</span>
                            {/if}
                            {#if stale}
                                <span class="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">{$t('tools.pacAllocator.staleLabel')}</span>
                            {/if}
                        </span>
                    </span>
                </button>
            {/each}
        </div>

        {#if filteredAssets.length === 0}
            <p class="rounded-lg border border-dashed border-gray-300 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400" data-testid="pac-asset-gallery-no-match">
                {$t('tools.pacAllocator.noAssetMatches')}
            </p>
        {/if}
    {/if}
</section>

<style>
    .scope-badge {
        border-color: color-mix(in srgb, var(--scope-border) 45%, transparent);
        background: var(--scope-bg);
        color: var(--scope-text);
    }

    :global(.dark) .scope-badge {
        background: var(--scope-dark-bg);
        color: var(--scope-dark-text);
    }
</style>
