<!--
  PositionsPanel — Dashboard positions widget with 4 views.

  Views:
  - Exposure / Table: asset weights in portfolio
  - Exposure / Map: ECharts treemap Broker → Type → Asset
  - Contribution / Table: per-asset period P&L attribution
  - Contribution / Map: dual gain/loss treemap

  Data sources:
  - Exposure: summary.holdings from portfolioStore
  - Contribution: positions_contribution from portfolioStore (fetched on demand)

  Pattern: Svelte 5 Runes, data-testid, dark mode.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {BarChart3, Map} from 'lucide-svelte';
    import {getUserStorageKey} from '$lib/utils/storage';

    import ExposureTable from './ExposureTable.svelte';
    import ExposureTreemap from './ExposureTreemap.svelte';
    import ContributionTable from './ContributionTable.svelte';
    import ContributionTreemap from './ContributionTreemap.svelte';

    import type {PortfolioSummary, PositionsContribution} from '$lib/stores/portfolio/portfolioStore.svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        summary: PortfolioSummary | null;
        contribution: PositionsContribution | null;
        loading?: boolean;
        contributionLoading?: boolean;
        assetsHref?: string;
        /** Callback to request contribution data fetch (lazy load). */
        onRequestContribution?: () => void;
    }

    let {
        summary = null,
        contribution = null,
        loading = false,
        contributionLoading = false,
        assetsHref = '/assets',
        onRequestContribution,
    }: Props = $props();

    // =========================================================================
    // Toggle state (persisted in localStorage)
    // =========================================================================

    type SemanticMode = 'exposure' | 'contribution';
    type VisualMode = 'table' | 'map';
    type PositionFilter = 'open' | 'closed';

    const STORAGE_KEY_SEMANTIC = getUserStorageKey('dashboard-positions-semantic');
    const STORAGE_KEY_VISUAL = getUserStorageKey('dashboard-positions-visual');
    const STORAGE_KEY_POSITION_FILTER = getUserStorageKey('dashboard-positions-filter');

    function loadPref<T extends string>(key: string, fallback: T): T {
        try {
            const v = localStorage.getItem(key);
            return v ? (v as T) : fallback;
        } catch {
            return fallback;
        }
    }

    let semanticMode = $state<SemanticMode>(loadPref(STORAGE_KEY_SEMANTIC, 'exposure'));
    let visualMode = $state<VisualMode>(loadPref(STORAGE_KEY_VISUAL, 'table'));
    let positionFilter = $state<PositionFilter>(loadPref(STORAGE_KEY_POSITION_FILTER, 'open'));

    $effect(() => {
        try { localStorage.setItem(STORAGE_KEY_SEMANTIC, semanticMode); } catch { /* noop */ }
    });

    $effect(() => {
        try { localStorage.setItem(STORAGE_KEY_VISUAL, visualMode); } catch { /* noop */ }
    });

    $effect(() => {
        try { localStorage.setItem(STORAGE_KEY_POSITION_FILTER, positionFilter); } catch { /* noop */ }
    });

    // Request contribution data when user switches to contribution mode
    $effect(() => {
        if (
            (semanticMode === 'contribution' || (semanticMode === 'exposure' && visualMode === 'table' && positionFilter === 'closed')) &&
            !contribution &&
            !contributionLoading
        ) {
            onRequestContribution?.();
        }
    });

    // =========================================================================
    // Derived data
    // =========================================================================

    let holdings = $derived(summary?.holdings ?? []);
    let navAmount = $derived(summary ? parseFloat(summary.net_worth.amount) : 0);
    let displayCurrency = $derived(summary?.net_worth.code ?? 'EUR');

    let needsContributionData = $derived(
        semanticMode === 'contribution' ||
        (semanticMode === 'exposure' && visualMode === 'table' && positionFilter === 'closed')
    );
    let showLoading = $derived(loading || (needsContributionData && contributionLoading));
    let showExposureEmpty = $derived(
        semanticMode === 'exposure' &&
        (visualMode === 'map' || positionFilter === 'open') &&
        holdings.length === 0
    );
</script>

<div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col" data-testid="positions-panel">
    <!-- Header -->
    <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">
            {$_('dashboard.positions')}
        </h2>
        <div class="flex items-center gap-2">
            <!-- Semantic toggle: Exposure / Contribution -->
            <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 text-xs overflow-hidden" data-testid="positions-semantic-toggle">
                <button
                    class="px-2.5 py-1 transition-colors {semanticMode === 'exposure' ? 'bg-libre-green text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => (semanticMode = 'exposure')}
                    data-testid="positions-toggle-exposure"
                >
                    {$_('dashboard.exposure')}
                </button>
                <button
                    class="px-2.5 py-1 transition-colors {semanticMode === 'contribution' ? 'bg-libre-green text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => (semanticMode = 'contribution')}
                    data-testid="positions-toggle-contribution"
                >
                    {$_('dashboard.contribution')}
                </button>
            </div>

            <!-- Visual toggle: Table / Map -->
            <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 text-xs overflow-hidden" data-testid="positions-visual-toggle">
                <button
                    class="px-2 py-1 transition-colors {visualMode === 'table' ? 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200' : 'text-gray-400 dark:text-gray-500 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => (visualMode = 'table')}
                    title={$_('dashboard.viewTable')}
                    data-testid="positions-toggle-table"
                >
                    <BarChart3 size={14} />
                </button>
                <button
                    class="px-2 py-1 transition-colors {visualMode === 'map' ? 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200' : 'text-gray-400 dark:text-gray-500 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => (visualMode = 'map')}
                    title={$_('dashboard.viewMap')}
                    data-testid="positions-toggle-map"
                >
                    <Map size={14} />
                </button>
            </div>

            {#if semanticMode === 'exposure' && visualMode === 'table'}
                <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 text-xs overflow-hidden" data-testid="positions-filter-toggle">
                    <button
                        class="px-2.5 py-1 transition-colors {positionFilter === 'open' ? 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => (positionFilter = 'open')}
                        data-testid="positions-toggle-open"
                    >
                        {$_('dashboard.openPositions') || 'Open'}
                    </button>
                    <button
                        class="px-2.5 py-1 transition-colors {positionFilter === 'closed' ? 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                        onclick={() => (positionFilter = 'closed')}
                        data-testid="positions-toggle-closed"
                    >
                        {$_('dashboard.closedPositions') || 'Closed'}
                    </button>
                </div>
            {/if}

            <a href={assetsHref} class="text-xs text-libre-green dark:text-green-400 hover:underline font-medium ml-1" data-testid="positions-see-all">
                {$_('dashboard.seeAllPositions')}
            </a>
        </div>
    </div>

    <!-- Content -->
    {#if showLoading}
        <div class="space-y-2 flex-1">
            {#each {length: 5} as _}
                <div class="h-9 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
            {/each}
        </div>
    {:else if showExposureEmpty}
        <p class="text-sm text-gray-400 dark:text-gray-500 py-6 text-center flex-1 flex items-center justify-center">
            {$_('dashboard.noPositions')}
        </p>
    {:else if semanticMode === 'contribution' && (!contribution || !contribution.positions || contribution.positions.length === 0)}
        <p class="text-sm text-gray-400 dark:text-gray-500 py-6 text-center flex-1 flex items-center justify-center">
            {$_('dashboard.noPeriodPnl')}
        </p>
    {:else}
        <div class="flex-1 overflow-x-auto">
            {#if semanticMode === 'exposure' && visualMode === 'table'}
                <ExposureTable {holdings} {navAmount} {displayCurrency} {positionFilter} contribution={contribution} />
            {:else if semanticMode === 'exposure' && visualMode === 'map' && positionFilter === 'closed' && contribution}
                <ContributionTreemap
                    positions={(contribution.positions ?? []).filter((p) => p.is_fully_sold)}
                    grossGains={parseFloat(String(contribution.gross_gains))}
                    grossLosses={parseFloat(String(contribution.gross_losses))}
                    {displayCurrency}
                />
            {:else if semanticMode === 'exposure' && visualMode === 'map'}
                <ExposureTreemap {holdings} {displayCurrency} />
            {:else if semanticMode === 'contribution' && visualMode === 'table' && contribution}
                <ContributionTable positions={contribution.positions ?? []} unallocated={contribution.unallocated ?? []} {displayCurrency} />
            {:else if semanticMode === 'contribution' && visualMode === 'map' && contribution}
                <ContributionTreemap
                    positions={contribution.positions ?? []}
                    grossGains={parseFloat(String(contribution.gross_gains))}
                    grossLosses={parseFloat(String(contribution.gross_losses))}
                    {displayCurrency}
                />
            {/if}
        </div>
    {/if}
</div>
