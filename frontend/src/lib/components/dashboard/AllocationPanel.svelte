<!--
  AllocationPanel — Dashboard allocation block.

  Extracted from dashboard/+page.svelte as behavior-preserving refactor.
  Keep markup/data-testid/i18n/classes/colors identical for safe reuse.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {PieChart, AreaChart} from 'lucide-svelte';

    import type {AllocationHistoryDimensions, PortfolioSummary} from '$lib/stores/portfolio/portfolioStore.svelte';
    import AllocationPieChart from '$lib/components/charts/AllocationPieChart.svelte';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import AllocationHistoryChart from '$lib/components/dashboard/AllocationHistoryChart.svelte';

    type AllocationTab = 'type' | 'sector' | 'geo';
    type AllocEntry = {name: string; value: number; amount: number; emoji?: string | null};

    interface Props {
        summary: PortfolioSummary | null;
        loading: boolean;
        displayCurrency: string;
        brokerIds: number[] | undefined;
        currentLanguage: string;
        allocationHistory: AllocationHistoryDimensions | null;
        onRequestAllocationHistory?: (dimension: AllocationTab, brokerIds: number[] | undefined) => void | Promise<void>;
    }

    let {summary, loading, displayCurrency, brokerIds, currentLanguage, allocationHistory, onRequestAllocationHistory}: Props = $props();

    let allocationTab = $state<AllocationTab>('type');
    let allocationView = $state<'now' | 'history'>('now');
    const allocationTabs = [
        ['type', 'dashboard.typeAllocation'],
        ['sector', 'dashboard.sectorAllocation'],
        ['geo', 'dashboard.geoAllocation'],
    ] as const satisfies readonly [AllocationTab, string][];

    function toAllocEntries(items: any[] | null | undefined): AllocEntry[] {
        if (!items) return [];
        return (items as any[]).flatMap((i) => {
            const v = parseFloat(i?.value ?? '0');
            if (v <= 0) return [];
            return [{name: i.name ?? '', value: v, amount: parseFloat(i?.amount ?? '0'), emoji: i?.emoji ?? null}];
        });
    }

    async function loadAllocationHistory(dimension: AllocationTab) {
        await onRequestAllocationHistory?.(dimension, brokerIds);
    }

    const allocationHistoryLoading = $derived(loading && !allocationHistory);
    const allocationByType = $derived(toAllocEntries(summary?.allocation_by_type as any));
    const allocationBySector = $derived(toAllocEntries(summary?.allocation_by_sector as any));
    const allocationByGeo = $derived(toAllocEntries(summary?.allocation_by_geography as any));
    const allocationByGeoMap = $derived(Object.fromEntries(allocationByGeo.map((e) => [e.name, e.value / 100])));
    const allocationByGeoAmounts = $derived(Object.fromEntries(allocationByGeo.filter((e) => e.amount > 0).map((e) => [e.name, e.amount])));
    const allocationHistoryData = $derived.by(() => {
        if (!allocationHistory) return [];
        const dimMap: Record<AllocationTab, keyof AllocationHistoryDimensions> = {type: 'type', sector: 'sector', geo: 'geography'};
        const dim = dimMap[allocationTab] ?? 'type';
        return allocationHistory[dim] ?? [];
    });
</script>

<div class="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col gap-3 min-h-[380px] lg:min-h-0" data-testid="allocation-panel">
    <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">{$_('dashboard.allocation')}</h2>
        <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600 text-xs font-medium">
            <button
                class="px-2.5 py-1.5 transition-colors {allocationView === 'now' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                onclick={() => (allocationView = 'now')}
                data-testid="allocation-view-now"
                title={$_('dashboard.now')}><PieChart size={14} /></button
            >
            <button
                class="px-2.5 py-1.5 transition-colors border-l border-gray-200 dark:border-slate-600 {allocationView === 'history' ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                onclick={() => {
                    allocationView = 'history';
                    loadAllocationHistory(allocationTab);
                }}
                data-testid="allocation-view-history"
                title={$_('dashboard.history')}><AreaChart size={14} /></button
            >
        </div>
    </div>

    <div class="flex rounded-lg overflow-hidden border border-gray-200 dark:border-slate-600 text-xs font-medium self-start">
        {#each allocationTabs as [tab, labelKey]}
            <button
                class="px-3 py-1 transition-colors {allocationTab === tab ? 'bg-libre-green text-white' : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'} {tab !== 'type' ? 'border-l border-gray-200 dark:border-slate-600' : ''}"
                onclick={() => {
                    allocationTab = tab;
                    if (allocationView === 'history') loadAllocationHistory(tab);
                }}
                data-testid="allocation-tab-{tab}"
            >
                {$_(labelKey)}
            </button>
        {/each}
    </div>

    <div class="flex-1 min-h-0 relative">
        {#if loading || allocationHistoryLoading}
            <div class="absolute inset-0 z-10 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
        {/if}
        <div class="w-full h-full" class:invisible={allocationView !== 'history' || loading || allocationHistoryLoading}>
            <AllocationHistoryChart data={allocationHistoryData} dimension={allocationTab} height="100%" loading={false} />
        </div>
        {#if allocationView === 'now'}
            {#if !summary}
                <div class="absolute inset-0 flex items-center justify-center text-sm text-gray-400 dark:text-gray-500">
                    {$_('common.noData')}
                </div>
            {:else if allocationTab === 'type'}
                <div class="absolute inset-0">
                    <AllocationPieChart data={allocationByType} height="100%" mode="type" legendPosition="bottom" currency={displayCurrency} />
                </div>
            {:else if allocationTab === 'sector'}
                <div class="absolute inset-0">
                    <AllocationPieChart data={allocationBySector} height="100%" legendPosition="bottom" currency={displayCurrency} />
                </div>
            {:else}
                <div class="absolute inset-0">
                    <GeographyMap data={allocationByGeoMap} amounts={allocationByGeoAmounts} currency={displayCurrency} height="100%" language={currentLanguage} />
                </div>
            {/if}
        {/if}
    </div>
</div>
