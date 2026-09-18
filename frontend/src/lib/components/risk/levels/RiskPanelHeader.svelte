<script lang="ts">
    import {goto} from '$app/navigation';

    import {DataQualityBanner} from '$lib/components/ui/feedback';
    import PageSyncModal from '$lib/components/ui/modals/PageSyncModal.svelte';
    import {_ as t} from '$lib/i18n';
    import {assetStoreVersion, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {fxRoutesVersion, getConfiguredPairSlugs} from '$lib/stores/reference/fxRoutesStore';
    import type {RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';

    import RiskBetaBanner from '../RiskBetaBanner.svelte';
    import {RefreshCw, RotateCw} from 'lucide-svelte';

    /**
     * Everything above the answer: what it is, how stale it is, how to refresh it.
     *
     * Extracted rather than copied. The scope picker changed, the four levels are
     * new, but "these prices are three days old and here is the button that fixes
     * it" is the same sentence on every risk surface — and two copies of one
     * sentence is how two pages begin to disagree about it.
     */
    interface Props {
        controller: RiskPanelController;
        title?: string;
        subtitle?: string;
        internalSubset?: boolean;
        /** Asset ids whose prices this answer rests on. */
        assetIds?: number[];
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        showBetaBanner?: boolean;
        showActions?: boolean;
    }

    let {controller, title = '', subtitle = '', internalSubset = false, assetIds = [], dateStart, dateEnd, targetCurrency, showBetaBanner = true, showActions = true}: Props = $props();

    let syncOpen = $state(false);

    let syncAssets = $derived.by(() => {
        void $assetStoreVersion;
        return [...new Set(assetIds)]
            .sort((left, right) => left - right)
            .map((assetId) => getAssetInfo(assetId))
            .filter((asset) => Boolean(asset))
            .map((asset) => ({
                id: asset!.id,
                display_name: asset!.display_name,
                currency: asset!.currency,
                icon_url: asset!.icon_url,
                asset_type: asset!.asset_type,
                provider_code: asset!.provider_code,
            }));
    });

    let syncFxPairs = $derived.by(() => {
        void $fxRoutesVersion;
        const configured = getConfiguredPairSlugs();
        const pairs = new Set<string>();
        for (const asset of syncAssets) {
            if (!asset || asset.currency === targetCurrency) continue;
            const slug = [asset.currency, targetCurrency].sort().join('-');
            if (configured.has(slug)) pairs.add(slug);
        }
        return [...pairs].sort();
    });

    function handleQualityAction(action: string, target: string | null): void {
        if (action.includes('sync')) syncOpen = true;
        else if (action === 'navigate_asset' && target) void goto(`/assets/${target}`);
        else if (action === 'navigate_fx' && target) void goto(`/fx/${target}`);
        else if (action === 'add_fx_pair') void goto('/fx');
    }
</script>

{#if showBetaBanner}
    <RiskBetaBanner />
{/if}

<div class="flex flex-wrap items-start justify-between gap-3">
    <div>
        <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100" data-testid="risk-levels-title">{title || $t('risk.title')}</h2>
        {#if subtitle || internalSubset}
            <p class="text-sm text-gray-500 dark:text-gray-400" data-testid="risk-scope-label">
                {internalSubset ? $t('risk.internalSubset') : subtitle}
            </p>
        {/if}
    </div>
    {#if showActions}
        <div class="flex items-center gap-2">
            <button
                type="button"
                class="flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-1.5 text-xs text-gray-600 dark:text-gray-300 disabled:opacity-50"
                onclick={() => (syncOpen = true)}
                disabled={syncAssets.length === 0 && syncFxPairs.length === 0}
                data-testid="risk-sync-button"
            >
                <RotateCw size={14} />
                {$t('common.sync')}
            </button>
            <button
                type="button"
                class="flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-1.5 text-xs text-gray-600 dark:text-gray-300 disabled:opacity-50"
                onclick={() => controller.loadBase(true)}
                disabled={controller.initialLoading || controller.refreshing}
                data-testid="risk-refresh-button"
            >
                <RefreshCw size={14} class={controller.refreshing ? 'animate-spin' : ''} />
                {$t('common.refresh')}
            </button>
        </div>
    {/if}
</div>

{#if controller.loadError}
    <div class="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-300" data-testid="risk-load-error">
        {$t('risk.states.loadFailed')}
    </div>
{/if}

{#if controller.dataQualityIssues.length > 0}
    <DataQualityBanner issues={controller.dataQualityIssues} mode="grouped" onaction={(action, target) => handleQualityAction(action, target)} />
{/if}

<PageSyncModal bind:open={syncOpen} {dateStart} {dateEnd} assets={syncAssets} fxPairs={syncFxPairs} onsynced={() => controller.handleSynced()} onclose={() => (syncOpen = false)} />
