<script lang="ts">
    import {untrack} from 'svelte';
    import {Plus, RefreshCw, X} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';
    import SearchSelect from '$lib/components/ui/select/SearchSelect.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import {singleValue} from '$lib/risk/riskTypes';
    import {fetchReport} from '$lib/stores/portfolio/portfolioStore.svelte';
    import {brokerStoreVersion, ensureBrokersLoaded, getAllBrokers} from '$lib/stores/reference/brokerStore';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import RiskAnalysisPanel from './RiskAnalysisPanel.svelte';

    interface AssetOption {
        id: number;
        display_name: string;
        currency: string;
        icon_url?: string | null;
        asset_type?: string | null;
        provider_code?: string | null;
        active?: boolean;
    }

    interface Props {
        assets: AssetOption[];
        dateStart: string;
        dateEnd: string;
        targetCurrency: string;
        onsynced?: () => void | Promise<void>;
    }

    let {assets, dateStart, dateEnd, targetCurrency, onsynced}: Props = $props();

    let selectedAssetIds = $state<number[]>([]);
    let selectedBrokerId = $state('');
    let addAssetId = $state('');
    let brokerAssetsLoading = $state(false);
    let brokerLoadFailed = $state(false);
    let seedInitialized = false;
    let brokerRequestGeneration = 0;
    let lastBrokerSignature = '';

    let brokers = $derived.by(() => {
        void $brokerStoreVersion;
        return getAllBrokers();
    });
    let brokerOptions = $derived([{value: '', label: $t('dashboard.allBrokers')}, ...brokers.map((broker) => ({value: String(broker.id), label: broker.name}))]);
    let selectedAssets = $derived(selectedAssetIds.map((assetId) => assets.find((asset) => asset.id === assetId)).filter((asset): asset is AssetOption => Boolean(asset)));
    let addOptions = $derived.by<SelectOption[]>(() =>
        assets
            .filter((asset) => !selectedAssetIds.includes(asset.id))
            .map((asset) => ({
                value: String(asset.id),
                label: asset.display_name,
                searchText: `${asset.display_name} ${asset.currency} ${asset.asset_type ?? ''}`,
                icon: asset.icon_url ?? getAssetTypeIconUrl(asset.asset_type),
                badge: asset.currency,
            }))
            .sort((left, right) => left.label.localeCompare(right.label)),
    );

    $effect(() => {
        untrack(() => void ensureBrokersLoaded());
    });

    $effect(() => {
        if (seedInitialized || assets.length === 0) return;
        seedInitialized = true;
        selectedAssetIds = assets
            .filter((asset) => asset.active !== false)
            .slice(0, 100)
            .map((asset) => asset.id);
    });

    $effect(() => {
        const signature = `${selectedBrokerId}|${dateStart}|${dateEnd}|${targetCurrency}`;
        if (signature === lastBrokerSignature) return;
        lastBrokerSignature = signature;
        untrack(() => void applyBrokerFilter());
    });

    async function applyBrokerFilter(): Promise<void> {
        const generation = ++brokerRequestGeneration;
        brokerLoadFailed = false;
        if (!selectedBrokerId) {
            selectedAssetIds = assets
                .filter((asset) => asset.active !== false)
                .slice(0, 100)
                .map((asset) => asset.id);
            return;
        }

        brokerAssetsLoading = true;
        try {
            const report = await fetchReport([Number(selectedBrokerId)], dateStart, dateEnd, targetCurrency);
            if (generation !== brokerRequestGeneration) return;
            const summary = singleValue(report?.summary);
            selectedAssetIds = [...new Set((summary?.holdings ?? []).map((holding) => holding.asset_id))].sort((left, right) => left - right).slice(0, 100);
        } catch (error) {
            console.error('[Risk] Failed to resolve broker asset set:', error);
            if (generation === brokerRequestGeneration) brokerLoadFailed = true;
        } finally {
            if (generation === brokerRequestGeneration) brokerAssetsLoading = false;
        }
    }

    function addAsset(): void {
        const assetId = Number(addAssetId);
        if (!Number.isInteger(assetId) || selectedAssetIds.includes(assetId) || selectedAssetIds.length >= 100) return;
        selectedAssetIds = [...selectedAssetIds, assetId].sort((left, right) => left - right);
        addAssetId = '';
    }

    function removeAsset(assetId: number): void {
        selectedAssetIds = selectedAssetIds.filter((id) => id !== assetId);
    }
</script>

<div class="space-y-4" data-testid="asset-global-risk-panel">
    <section class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-4" data-testid="risk-asset-set-controls">
        <div class="flex flex-wrap items-end gap-3">
            <label class="text-xs text-gray-500 dark:text-gray-400">
                {$t('common.broker')}
                <div class="mt-1 w-56">
                    <SimpleSelect value={selectedBrokerId} options={brokerOptions} compact testId="risk-broker-filter" optionTestId={(option) => `risk-broker-option-${option.value || 'all'}`} onchange={(value) => (selectedBrokerId = value)} />
                </div>
            </label>
            <label class="text-xs text-gray-500 dark:text-gray-400">
                {$t('risk.assetSet.addAsset')}
                <div class="mt-1 w-72 max-w-full">
                    <SearchSelect value={addAssetId} options={addOptions} compact inlineSearch dropdownPosition="auto" testId="risk-asset-add-select" onchange={(value) => (addAssetId = value)} />
                </div>
            </label>
            <button class="flex items-center gap-1.5 rounded-lg bg-libre-green px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50" onclick={addAsset} disabled={!addAssetId || selectedAssetIds.length >= 100} data-testid="risk-asset-add-button">
                <Plus size={13} />
                {$t('common.add')}
            </button>
            {#if brokerAssetsLoading}
                <RefreshCw size={16} class="animate-spin text-libre-green" data-testid="risk-broker-filter-loading" />
            {/if}
        </div>

        {#if brokerLoadFailed}
            <p class="mt-2 text-xs text-red-600 dark:text-red-400" data-testid="risk-broker-filter-error">{$t('risk.states.loadFailed')}</p>
        {/if}

        <div class="mt-3 flex flex-wrap gap-2" data-testid="risk-selected-assets">
            {#each selectedAssets as asset}
                <span class="inline-flex items-center gap-1 rounded-full bg-gray-100 dark:bg-slate-700 px-2 py-1 text-xs text-gray-600 dark:text-gray-300" data-testid="risk-selected-asset-{asset.id}">
                    {asset.display_name}
                    <button class="rounded-full p-0.5 hover:bg-gray-200 dark:hover:bg-slate-600" onclick={() => removeAsset(asset.id)} title={$t('common.remove')} data-testid="risk-remove-asset-{asset.id}">
                        <X size={11} />
                    </button>
                </span>
            {/each}
        </div>
        {#if selectedAssetIds.length >= 100}
            <p class="mt-2 text-xs text-amber-600 dark:text-amber-400">{$t('risk.assetSet.maxAssets')}</p>
        {/if}
    </section>

    {#if selectedAssetIds.length > 0}
        <RiskAnalysisPanel scope={{kind: 'asset_set', asset_ids: selectedAssetIds}} {dateStart} {dateEnd} {targetCurrency} assetIds={selectedAssetIds} title={$t('risk.analytics.correlation.name')} {onsynced} />
    {:else}
        <div class="rounded-xl border border-gray-100 dark:border-slate-700 bg-white dark:bg-slate-800 p-8 text-center text-sm text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-empty">
            {$t('risk.states.noAssets')}
        </div>
    {/if}
</div>
