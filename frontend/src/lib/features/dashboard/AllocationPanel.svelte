<!--
  AllocationPanel — Dashboard allocation block.

  Extracted from dashboard/+page.svelte as behavior-preserving refactor.
  Keep markup/data-testid/i18n/classes/colors identical for safe reuse.

  The selected view (now/history) and dimension tab persist per user; Dashboard and
  Broker detail share the same keys, like PositionsPanel.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {PieChart, AreaChart} from 'lucide-svelte';

    import type {AllocationHistoryDimensions, PortfolioSummary} from '$lib/stores/portfolio/portfolioStore.svelte';
    import AllocationPieChart from '$lib/components/charts/AllocationPieChart.svelte';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import AllocationHistoryChart from '$lib/features/dashboard/AllocationHistoryChart.svelte';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {getUserStorage, setUserStorage} from '$lib/utils/storage';
    import {rankAssetsByWeight} from './positionsSeries';

    type AllocationTab = 'type' | 'sector' | 'geo' | 'asset';
    type AllocationView = 'now' | 'history';
    /** `id` is the asset id of a slice of the asset dimension (its colour key); null for the Liquidity slice. */
    type AllocEntry = {name: string; value: number; amount: number; id?: number | null};

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

    const allocationTabs = [
        ['type', 'dashboard.typeAllocation'],
        ['sector', 'dashboard.sectorAllocation'],
        ['geo', 'dashboard.geoAllocation'],
        ['asset', 'dashboard.assetAllocation'],
    ] as const satisfies readonly [AllocationTab, string][];

    const VIEW_STORAGE_KEY = 'dashboard-allocation-view';
    const TAB_STORAGE_KEY = 'dashboard-allocation-tab';

    // A stored value this version does not know (garbage, or a renamed option) falls
    // back to the default instead of leaving the panel without a selected button.
    function readStoredView(): AllocationView {
        return getUserStorage(VIEW_STORAGE_KEY, 'now') === 'history' ? 'history' : 'now';
    }

    function readStoredTab(): AllocationTab {
        const stored = getUserStorage(TAB_STORAGE_KEY, 'type');
        return allocationTabs.find(([tab]) => tab === stored)?.[0] ?? 'type';
    }

    let allocationTab = $state<AllocationTab>(readStoredTab());
    let allocationView = $state<AllocationView>(readStoredView());

    function toAllocEntries(items: any[] | null | undefined): AllocEntry[] {
        if (!items) return [];
        return (items as any[]).flatMap((i) => {
            const v = parseFloat(i?.value ?? '0');
            if (v <= 0) return [];
            return [{name: i.name ?? '', value: v, amount: parseFloat(i?.amount ?? '0'), id: i?.id ?? null}];
        });
    }

    /** The cash the backend reports in a list when it is below zero: an overdraft the pie cannot draw (decision 49). */
    function negativeCash(items: any[] | null | undefined): number | null {
        const amount = parseFloat((items ?? []).find((i) => i?.name === 'Liquidity')?.amount ?? '');
        return Number.isFinite(amount) && amount < 0 ? amount : null;
    }

    async function loadAllocationHistory(dimension: AllocationTab) {
        await onRequestAllocationHistory?.(dimension, brokerIds);
    }

    function selectView(view: AllocationView) {
        allocationView = view;
        setUserStorage(VIEW_STORAGE_KEY, view);
        if (view === 'history') loadAllocationHistory(allocationTab);
    }

    function selectTab(tab: AllocationTab) {
        allocationTab = tab;
        setUserStorage(TAB_STORAGE_KEY, tab);
        if (allocationView === 'history') loadAllocationHistory(tab);
    }

    // A restored History view must request its data exactly as the click does.
    onMount(() => {
        if (allocationView === 'history') loadAllocationHistory(allocationTab);
    });

    const allocationHistoryLoading = $derived(loading && !allocationHistory);
    const allocationByType = $derived(toAllocEntries(summary?.allocation_by_type as any));
    const allocationBySector = $derived(toAllocEntries(summary?.allocation_by_sector as any));
    const allocationByGeo = $derived(toAllocEntries(summary?.allocation_by_geography as any));
    // The asset dimension (Y5-2, #48): today's weight per asset, and its history with the assets that left the portfolio.
    const allocationByAssetItems = $derived((summary?.allocation_by_asset ?? []) as any[]);
    const allocationByAsset = $derived(toAllocEntries(allocationByAssetItems));
    const allocationHistoryAsset = $derived((allocationHistory?.asset ?? []) as Array<{date: string; through: string; components: any[]}>);
    /** One colour rank per asset, shared by the pie and the history: the heaviest today first, then the closed ones, the latest closed first. */
    const assetColorRanks = $derived(
        rankAssetsByWeight(
            allocationByAssetItems.map((item) => ({id: item?.id ?? null, amount: parseFloat(item?.amount ?? '0')})),
            allocationHistoryAsset.map((point) => ({date: point.date, through: point.through, components: (point.components ?? []).map((component) => ({id: component?.id ?? null, amount: parseFloat(component?.amount ?? '0')}))})),
        ),
    );
    // Type and sector carry the cash; geography never does. The history chart draws it below zero by itself.
    const shownNegativeCash = $derived(
        allocationView !== 'now' ? null : allocationTab === 'type' ? negativeCash(summary?.allocation_by_type as any) : allocationTab === 'sector' ? negativeCash(summary?.allocation_by_sector as any) : allocationTab === 'asset' ? negativeCash(allocationByAssetItems) : null,
    );
    const allocationByGeoMap = $derived(Object.fromEntries(allocationByGeo.map((e) => [e.name, e.value / 100])));
    const allocationByGeoAmounts = $derived(Object.fromEntries(allocationByGeo.filter((e) => e.amount > 0).map((e) => [e.name, e.amount])));
    const allocationHistoryData = $derived.by(() => {
        if (!allocationHistory) return [];
        if (allocationTab === 'asset') return allocationHistoryAsset;
        const dimMap: Record<Exclude<AllocationTab, 'asset'>, keyof AllocationHistoryDimensions> = {type: 'type', sector: 'sector', geo: 'geography'};
        const dim = dimMap[allocationTab] ?? 'type';
        return allocationHistory[dim] ?? [];
    });
</script>

<div class="lg:col-span-2 bg-lf-card text-lf-primary rounded-xl border border-lf-subtle shadow-sm shadow-lf-shadow-card p-4 flex flex-col gap-3 min-h-[380px] lg:min-h-0" data-testid="allocation-panel">
    <div class="flex items-center justify-between">
        <h2 class="text-sm font-semibold text-lf-secondary">{$_('dashboard.allocation')}</h2>
        <div class="flex rounded-lg overflow-hidden border border-lf-subtle text-xs font-medium">
            <button
                class="px-2.5 py-1.5 transition-colors {allocationView === 'now' ? 'bg-lf-action text-lf-on-action' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                onclick={() => selectView('now')}
                aria-pressed={allocationView === 'now'}
                data-testid="allocation-view-now"
                title={$_('dashboard.now')}><PieChart size={14} /></button
            >
            <button
                class="px-2.5 py-1.5 transition-colors border-l border-lf-subtle {allocationView === 'history' ? 'bg-lf-action text-lf-on-action' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
                onclick={() => selectView('history')}
                aria-pressed={allocationView === 'history'}
                data-testid="allocation-view-history"
                title={$_('dashboard.history')}><AreaChart size={14} /></button
            >
        </div>
    </div>

    <div class="flex rounded-lg overflow-hidden border border-lf-subtle text-xs font-medium self-start">
        {#each allocationTabs as [tab, labelKey]}
            <button
                class="px-3 py-1 transition-colors {allocationTab === tab ? 'bg-lf-action text-lf-on-action' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'} {tab !== 'type' ? 'border-l border-lf-subtle' : ''}"
                onclick={() => selectTab(tab)}
                aria-pressed={allocationTab === tab}
                data-testid="allocation-tab-{tab}"
            >
                {$_(labelKey)}
            </button>
        {/each}
    </div>

    <div class="flex-1 min-h-0 relative">
        {#if loading || allocationHistoryLoading}
            <div class="absolute inset-0 z-10 bg-lf-neutral rounded animate-pulse"></div>
        {/if}
        <div class="w-full h-full" class:invisible={allocationView !== 'history' || loading || allocationHistoryLoading}>
            <AllocationHistoryChart data={allocationHistoryData} dimension={allocationTab} colorRanks={assetColorRanks} height="100%" loading={false} />
        </div>
        {#if allocationView === 'now'}
            {#if !summary}
                <div class="absolute inset-0 flex items-center justify-center text-sm text-lf-muted">
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
            {:else if allocationTab === 'asset'}
                <div class="absolute inset-0">
                    <AllocationPieChart data={allocationByAsset} height="100%" mode="asset" colorRanks={assetColorRanks} legendPosition="bottom" currency={displayCurrency} />
                </div>
            {:else}
                <div class="absolute inset-0">
                    <GeographyMap data={allocationByGeoMap} amounts={allocationByGeoAmounts} currency={displayCurrency} height="100%" language={currentLanguage} />
                </div>
            {/if}
        {/if}
    </div>
    {#if shownNegativeCash !== null}
        <p class="text-xs text-lf-muted text-center" data-testid="allocation-negative-cash-note">
            {$_('dashboard.allocationNegativeCash', {values: {amount: formatCurrencyAmountPlain(shownNegativeCash, displayCurrency)}})}
        </p>
    {/if}
</div>
