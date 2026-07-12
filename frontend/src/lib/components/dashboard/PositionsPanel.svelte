<!--
  PositionsPanel — Dashboard positions widget with 4 views.

  Views:
  - Holdings / Table: snapshot of open positions at date_to (weights, unrealized P&L, PMC)
  - Holdings / Map: ECharts treemap Broker → Type → Asset (area=Value, color=Unrealized P&L%)
  - Performance / Table: per-asset period P&L attribution (open+closed, Status is a filterable
    column, not a panel-level toggle) + Other Period Effects section below
  - Performance / Map: stacked diverging bar chart (positive components right of zero, negative
    left of zero) + Other Period Effects rows

  Data sources:
  - Holdings: summary.holdings from portfolioStore (engine snapshot at date_to)
  - Performance: positions_contribution from portfolioStore (fetched on demand)

  Pattern: Svelte 5 Runes, data-testid, dark mode.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Table2, Grid2x2} from 'lucide-svelte';
    import {getUserStorageKey} from '$lib/utils/storage';

    import ExposureTable from './ExposureTable.svelte';
    import ExposureTreemap from './ExposureTreemap.svelte';
    import ContributionTable from './ContributionTable.svelte';
    import OtherPeriodEffectsTable from './OtherPeriodEffectsTable.svelte';
    import PerformanceChart from './PerformanceChart.svelte';

    import type {PortfolioSummary, PositionsContribution} from '$lib/stores/portfolio/portfolioStore.svelte';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        summary: PortfolioSummary | null;
        contribution: PositionsContribution | null;
        loading?: boolean;
        contributionLoading?: boolean;
        assetsHref?: string;
        brokers?: ReadonlyArray<BrokerLike>;
        /** Callback to request contribution data fetch (lazy load). */
        onRequestContribution?: () => void;
        /** Single click on a row/tile/bar → open the FIFO lots analysis panel for that asset
         *  (double-click still navigates to asset detail, unchanged). Forwarded as-is to all
         *  4 sub-views. */
        onAnalyze?: (assetId: number) => void;
    }

    let {summary = null, contribution = null, loading = false, contributionLoading = false, assetsHref = '/assets', brokers = [], onRequestContribution, onAnalyze}: Props = $props();

    // =========================================================================
    // Toggle state (persisted in localStorage)
    // =========================================================================

    type SemanticMode = 'holdings' | 'performance';
    type VisualMode = 'table' | 'map';

    const STORAGE_KEY_SEMANTIC = getUserStorageKey('dashboard-positions-semantic');
    const STORAGE_KEY_VISUAL = getUserStorageKey('dashboard-positions-visual');

    function loadPref<T extends string>(key: string, fallback: T): T {
        try {
            const v = localStorage.getItem(key);
            return v ? (v as T) : fallback;
        } catch {
            return fallback;
        }
    }

    /** Back-compat: users with 'exposure'/'contribution' cached from before the
     *  Holdings/Performance rename get remapped transparently. */
    function normalizeSemanticMode(v: string): SemanticMode {
        if (v === 'exposure') return 'holdings';
        if (v === 'contribution') return 'performance';
        return v === 'performance' ? 'performance' : 'holdings';
    }

    let semanticMode = $state<SemanticMode>(normalizeSemanticMode(loadPref(STORAGE_KEY_SEMANTIC, 'holdings')));
    let visualMode = $state<VisualMode>(loadPref(STORAGE_KEY_VISUAL, 'table'));

    $effect(() => {
        try {
            localStorage.setItem(STORAGE_KEY_SEMANTIC, semanticMode);
        } catch {
            /* noop */
        }
    });

    $effect(() => {
        try {
            localStorage.setItem(STORAGE_KEY_VISUAL, visualMode);
        } catch {
            /* noop */
        }
    });

    // Request contribution data when user switches to the Performance view
    // (needed for both the table and the chart, plus Other Period Effects).
    $effect(() => {
        if (semanticMode === 'performance' && !contribution && !contributionLoading) {
            onRequestContribution?.();
        }
    });

    // =========================================================================
    // Derived data
    // =========================================================================

    let holdings = $derived(summary?.holdings ?? []);
    let navAmount = $derived(summary ? parseFloat(summary.net_worth.amount) : 0);
    let displayCurrency = $derived(summary?.net_worth.code ?? 'EUR');

    /** Performance shows open+closed positions together — Status is a filterable
     *  column inside ContributionTable/PerformanceChart, not a panel-level toggle. */
    let contributionPositions = $derived(contribution?.positions ?? []);
    let otherEffects = $derived(contribution?.other_effects ?? []);

    let showLoading = $derived(loading || (semanticMode === 'performance' && contributionLoading));
    let showHoldingsEmpty = $derived(semanticMode === 'holdings' && holdings.length === 0);
    let showPerformanceEmpty = $derived(semanticMode === 'performance' && (!contribution || (contributionPositions.length === 0 && otherEffects.length === 0)));
</script>

<div class="bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-4 flex flex-col" data-testid="positions-panel">
    <!-- Header -->
    <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200">
            {$_('dashboard.positions')}
        </h2>
        <div class="flex items-center gap-2">
            <!-- Semantic toggle: Holdings / Performance -->
            <div class="flex rounded-lg border border-gray-200 dark:border-slate-600 text-xs overflow-hidden" data-testid="positions-semantic-toggle">
                <button class="px-2.5 py-1 transition-colors {semanticMode === 'holdings' ? 'bg-libre-green text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}" onclick={() => (semanticMode = 'holdings')} data-testid="positions-toggle-holdings">
                    {$_('dashboard.holdingsTab') || 'Holdings'}
                </button>
                <button class="px-2.5 py-1 transition-colors {semanticMode === 'performance' ? 'bg-libre-green text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'}" onclick={() => (semanticMode = 'performance')} data-testid="positions-toggle-performance">
                    {$_('dashboard.performanceTab') || 'Performance'}
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
                    <Table2 size={14} />
                </button>
                <button
                    class="px-2 py-1 transition-colors {visualMode === 'map' ? 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-200' : 'text-gray-400 dark:text-gray-500 hover:bg-gray-50 dark:hover:bg-slate-700'}"
                    onclick={() => (visualMode = 'map')}
                    title={$_('dashboard.viewMap')}
                    data-testid="positions-toggle-map"
                >
                    <Grid2x2 size={14} />
                </button>
            </div>

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
    {:else if showHoldingsEmpty}
        <p class="text-sm text-gray-400 dark:text-gray-500 py-6 text-center flex-1 flex items-center justify-center">
            {$_('dashboard.noPositions')}
        </p>
    {:else if showPerformanceEmpty}
        <p class="text-sm text-gray-400 dark:text-gray-500 py-6 text-center flex-1 flex items-center justify-center">
            {$_('dashboard.noPeriodPnl')}
        </p>
    {:else}
        <div class="flex-1 {visualMode === 'table' ? 'overflow-x-auto' : ''}">
            {#if semanticMode === 'holdings' && visualMode === 'table'}
                <ExposureTable {holdings} {navAmount} {displayCurrency} {brokers} {onAnalyze} />
            {:else if semanticMode === 'holdings' && visualMode === 'map'}
                <ExposureTreemap {holdings} {displayCurrency} {onAnalyze} />
            {:else if semanticMode === 'performance' && visualMode === 'table' && contribution}
                <ContributionTable positions={contributionPositions} {holdings} {displayCurrency} {brokers} {onAnalyze} />
                <OtherPeriodEffectsTable effects={otherEffects} {displayCurrency} />
            {:else if semanticMode === 'performance' && visualMode === 'map' && contribution}
                <PerformanceChart positions={contributionPositions} {otherEffects} {displayCurrency} {onAnalyze} />
            {/if}
        </div>
    {/if}
</div>
