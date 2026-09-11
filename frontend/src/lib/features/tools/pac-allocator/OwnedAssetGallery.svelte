<script lang="ts">
    import {_} from '$lib/i18n';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import {AlertCircle, Check, LoaderCircle, Plus, RefreshCw, Search} from 'lucide-svelte';
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

    let {assets, loading, error, disabled = false, ontoggle, onretry, onaddmanual}: Props = $props();
    let query = $state('');

    let filteredAssets = $derived.by(() => {
        const normalized = query.trim().toLocaleLowerCase();
        if (!normalized) return assets;
        return assets.filter((asset) => {
            const brokerNames = asset.contexts.map((context) => context.brokerName).join(' ');
            return `${asset.name} ${asset.ticker ?? ''} ${asset.assetType} ${brokerNames}`.toLocaleLowerCase().includes(normalized);
        });
    });
</script>

<section class="space-y-3" data-testid="pac-owned-assets">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white">{$_('tools.pacAllocator.ownedAssets')}</h3>
            <p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{$_('tools.pacAllocator.ownedAssetsHint')}</p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
            <button class="btn btn-ghost px-2" type="button" onclick={onretry} disabled={loading} data-testid="pac-owned-assets-refresh" aria-label={$_('common.refresh')}>
                <RefreshCw class={loading ? 'animate-spin' : ''} size={15} />
                <span class="hidden sm:inline">{$_('common.refresh')}</span>
            </button>
            <button class="btn btn-secondary" type="button" onclick={onaddmanual} data-testid="pac-add-manual-asset">
                <Plus size={15} />
                <span>{$_('tools.pacAllocator.addManualAsset')}</span>
            </button>
        </div>
    </div>

    {#if loading && assets.length === 0}
        <div class="flex min-h-28 items-center justify-center gap-2 rounded-xl border border-gray-200 bg-gray-50 text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900/40 dark:text-gray-400" data-testid="pac-owned-assets-loading">
            <LoaderCircle class="animate-spin" size={18} />
            <span>{$_('tools.pacAllocator.loadingOwnedAssets')}</span>
        </div>
    {:else if error && assets.length === 0}
        <div class="flex min-h-28 flex-col items-center justify-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 text-center dark:border-red-900/60 dark:bg-red-950/20" data-testid="pac-owned-assets-error">
            <div class="flex items-center gap-2 text-sm font-medium text-red-700 dark:text-red-300">
                <AlertCircle size={17} />
                <span>{error}</span>
            </div>
            <button class="btn btn-secondary" type="button" onclick={onretry} disabled={loading} data-testid="pac-owned-assets-retry">
                <RefreshCw class={loading ? 'animate-spin' : ''} size={15} />
                <span>{$_('common.retry')}</span>
            </button>
        </div>
    {:else if assets.length === 0}
        <div class="rounded-xl border border-dashed border-gray-300 px-4 py-8 text-center dark:border-gray-700" data-testid="pac-owned-assets-empty">
            <p class="text-sm font-medium text-gray-700 dark:text-gray-200">{$_('tools.pacAllocator.noOwnedAssets')}</p>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{$_('tools.pacAllocator.noOwnedAssetsHint')}</p>
        </div>
    {:else}
        <div class="relative max-w-sm">
            <Search class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
            <input class="input-field w-full pl-9" type="search" bind:value={query} placeholder={$_('tools.pacAllocator.searchOwnedAssets')} aria-label={$_('tools.pacAllocator.searchOwnedAssets')} data-testid="pac-owned-assets-search" />
        </div>

        {#if error}
            <div class="flex items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/20 dark:text-amber-200">
                <span>{error}</span>
                <button class="btn btn-ghost shrink-0" type="button" onclick={onretry} disabled={loading} data-testid="pac-owned-assets-retry-inline">
                    <RefreshCw class={loading ? 'animate-spin' : ''} size={14} />
                    <span class="hidden sm:inline">{$_('common.retry')}</span>
                </button>
            </div>
        {/if}

        <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {#each filteredAssets as asset (asset.assetId)}
                {@const selected = asset.selectedContextKeys.length > 0}
                {@const modified = asset.modifiedContextKeys.length > 0}
                {@const stale = asset.staleContextKeys.length > 0}
                <button
                    type="button"
                    class="group relative flex min-h-24 items-start gap-3 rounded-xl border p-3 text-left transition focus:outline-none focus:ring-2 focus:ring-libre-green/50 {selected
                        ? 'border-libre-green bg-libre-green/5 dark:border-green-600 dark:bg-green-950/20'
                        : 'border-gray-200 bg-white hover:border-libre-green/60 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900/40 dark:hover:border-green-700 dark:hover:bg-gray-800'}"
                    aria-pressed={selected}
                    onclick={() => ontoggle(asset)}
                    {disabled}
                    data-testid={`pac-owned-asset-${asset.assetId}`}
                >
                    <AssetIcon iconUrl={asset.iconUrl} assetType={asset.assetType} altText={asset.name} size="md" />
                    <span class="min-w-0 flex-1">
                        <span class="flex items-start justify-between gap-2">
                            <span class="min-w-0">
                                <span class="block truncate text-sm font-semibold text-gray-900 dark:text-white">{asset.name}</span>
                                <span class="block truncate text-xs text-gray-500 dark:text-gray-400">
                                    {asset.ticker ?? asset.assetType} · {asset.contexts.length}
                                    {asset.contexts.length === 1 ? $_('tools.pacAllocator.custodyContext') : $_('tools.pacAllocator.custodyContexts')}
                                </span>
                            </span>
                            <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border {selected ? 'border-libre-green bg-libre-green text-white' : 'border-gray-300 text-transparent dark:border-gray-600'}">
                                <Check size={13} strokeWidth={3} />
                            </span>
                        </span>
                        <span class="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
                            {#if asset.quote.rawPrice}
                                <span class="rounded-full bg-gray-100 px-2 py-0.5 text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                                    {asset.quote.rawPrice}
                                    {asset.quote.currency}
                                </span>
                            {:else}
                                <span class="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">{$_('tools.pacAllocator.missingPrice')}</span>
                            {/if}
                            {#if modified}
                                <span class="rounded-full bg-blue-100 px-2 py-0.5 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200">{$_('tools.pacAllocator.modified')}</span>
                            {/if}
                            {#if stale}
                                <span class="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">{$_('tools.pacAllocator.staleLabel')}</span>
                            {/if}
                        </span>
                    </span>
                </button>
            {/each}
        </div>

        {#if filteredAssets.length === 0}
            <p class="rounded-lg border border-dashed border-gray-300 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">{$_('tools.pacAllocator.noAssetMatches')}</p>
        {/if}
    {/if}
</section>
