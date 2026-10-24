<!--
  PositionsPanel — Dashboard positions widget with 4 views.

  Views:
  - Holdings / Table: snapshot of open positions at date_to (weights, unrealized P&L, PMC)
  - Holdings / Map: ECharts treemap Broker → Type → Asset (area=Value, color=Unrealized P&L%)
  - Performance / Table: per-asset period P&L attribution (open+closed, Status is a filterable
    column, not a panel-level toggle) + Other Period Effects section below
  - Performance / Map: stacked diverging bar chart (positive components right of zero, negative
    left of zero) + Other Period Effects rows

  Holdings / Table also carries the return chart of the positions (Y5-2, #48): the rows the user ticks are
  drawn as lines over the portfolio's own (Abs or «base 100»); the legend turns them on and off.

  Data sources:
  - Holdings: summary.holdings from portfolioStore (engine snapshot at date_to)
  - Performance: positions_contribution from portfolioStore (fetched on demand)

  Pattern: Svelte 5 Runes, data-testid, dark mode.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Table2, Grid2x2} from 'lucide-svelte';
    import {getUserStorage, getUserStorageKey, setUserStorage} from '$lib/utils/storage';
    import {onDestroy} from 'svelte';
    import {isDarkTheme, onChartColorsChange, onThemeClassChange} from '$lib/theme/themeMode';
    import {themed} from '$lib/theme/themePair';
    import {GROWTH_SERIES} from '$lib/theme/chartTheme';
    import {growthBrokerColor} from '$lib/theme/chartPalettes';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';
    import type DataTable from '$lib/components/table/DataTable.svelte';

    import ExposureTable from './ExposureTable.svelte';
    import ExposureTreemap from './ExposureTreemap.svelte';
    import ContributionTable from './ContributionTable.svelte';
    import OtherPeriodEffectsTable from './OtherPeriodEffectsTable.svelte';
    import PerformanceChart from './PerformanceChart.svelte';
    import PositionsReturnChart from './PositionsReturnChart.svelte';
    import {PORTFOLIO_LINE_ID, portfolioLine, positionLines, selectionKeys, type HistoryPointLike, type PositionKey, type PositionsChartView, type PositionsSeriesResponse} from './positionsSeries';

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
        /** Asset whose lot-analysis panel is open — its table row stays tinted (F9).
         *  Forwarded to the table sub-views. */
        analyzedAssetId?: number | null;
        /** The daily series of the ticked positions (Y5-2): the answer of the last request. */
        positionsSeries?: PositionsSeriesResponse | null;
        positionsSeriesLoading?: boolean;
        positionsSeriesFailed?: boolean;
        /** Asks the series of the ticked positions; called once per change of the selection, never with an empty one. */
        onRequestPositionsSeries?: (keys: PositionKey[]) => void;
        /** The Dashboard's own history: the chart's portfolio line (its return, not the positions' P&L). */
        portfolioHistory?: ReadonlyArray<HistoryPointLike>;
    }

    let {
        summary = null,
        contribution = null,
        loading = false,
        contributionLoading = false,
        assetsHref = '/assets',
        brokers = [],
        onRequestContribution,
        onAnalyze,
        analyzedAssetId = null,
        positionsSeries = null,
        positionsSeriesLoading = false,
        positionsSeriesFailed = false,
        onRequestPositionsSeries,
        portfolioHistory = [],
    }: Props = $props();

    // =========================================================================
    // Toggle state (persisted in localStorage)
    // =========================================================================

    type SemanticMode = 'holdings' | 'performance';
    type VisualMode = 'table' | 'map';
    type DashboardTableComponent = {
        getTableRef: () => DataTable<any> | undefined;
    };

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
    let exposureTableComponent: DashboardTableComponent | undefined = $state(undefined);
    let contributionTableComponent: DashboardTableComponent | undefined = $state(undefined);
    let activeTableRef = $derived.by<DataTable<any> | undefined>(() => (semanticMode === 'holdings' ? exposureTableComponent?.getTableRef() : contributionTableComponent?.getTableRef()));

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
    // The return chart of the positions (Y5-2)
    // =========================================================================

    const CHART_VIEW_KEY = 'dashboard-positions-chart-view';

    function readChartView(): PositionsChartView {
        return getUserStorage(CHART_VIEW_KEY, 'percentage') === 'absolute' ? 'absolute' : 'percentage';
    }

    type SelectedRow = {key: string; assetId: number; brokerId: number | null};

    let chartView = $state<PositionsChartView>(readChartView());
    let selectedRows = $state<SelectedRow[]>([]);
    let hiddenIds = $state<ReadonlySet<string>>(new Set());
    let isDark = $state(isDarkTheme());

    const themeWatcher = onThemeClassChange(() => (isDark = isDarkTheme()));
    const colourWatcher = onChartColorsChange(() => (isDark = isDarkTheme()));
    onDestroy(() => {
        themeWatcher.disconnect();
        colourWatcher.disconnect();
    });

    function handleSelectionChange(rows: SelectedRow[]) {
        selectedRows = rows;
        if (rows.length > 0) onRequestPositionsSeries?.(selectionKeys(rows));
    }

    function handleChartViewChange(view: PositionsChartView) {
        chartView = view;
        setUserStorage(CHART_VIEW_KEY, view);
    }

    function toggleLine(id: string) {
        const next = new Set(hiddenIds);
        if (!next.delete(id)) next.add(id);
        hiddenIds = next;
    }

    /** A line keeps its colour while the selection changes: ids get their number in the order they are first drawn. */
    const colourSlots = new Map<string, number>();
    function colourOf(id: string): string {
        if (id === PORTFOLIO_LINE_ID) return themed(GROWTH_SERIES.nav, isDark);
        let slot = colourSlots.get(id);
        if (slot === undefined) {
            slot = colourSlots.size;
            colourSlots.set(id, slot);
        }
        return growthBrokerColor(slot, isDark);
    }

    let selectedKeys = $derived(selectedRows.map((row) => row.key));
    let chartLines = $derived.by(() => {
        const portfolio = portfolioLine(portfolioHistory, chartView, $_('dashboard.positionsChart.portfolio'));
        const picked = new Set(selectedKeys);
        const positions = positionLines(positionsSeries, chartView).filter((line) => picked.has(line.id));
        return portfolio ? [portfolio, ...positions] : positions;
    });

    // =========================================================================
    // Derived data
    // =========================================================================

    let holdings = $derived(summary?.holdings ?? []);
    let displayCurrency = $derived(summary?.net_worth.code ?? 'EUR');

    /** Performance shows open+closed positions together — Status is a filterable
     *  column inside ContributionTable/PerformanceChart, not a panel-level toggle. */
    let contributionPositions = $derived(contribution?.positions ?? []);
    let otherEffects = $derived(contribution?.other_effects ?? []);

    let showLoading = $derived(loading || (semanticMode === 'performance' && contributionLoading));
    let showHoldingsEmpty = $derived(semanticMode === 'holdings' && holdings.length === 0);
    let showPerformanceEmpty = $derived(semanticMode === 'performance' && (!contribution || (contributionPositions.length === 0 && otherEffects.length === 0)));
</script>

<div class="bg-lf-card text-lf-primary rounded-xl border border-lf-subtle shadow-sm shadow-lf-shadow-card p-4 flex flex-col" data-testid="positions-panel" aria-busy={showLoading} data-busy={showLoading ? 'true' : 'false'}>
    <!-- Header -->
    <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 class="text-sm font-semibold text-lf-secondary">
            {$_('dashboard.positions')}
        </h2>
        <div class="flex items-center gap-2">
            <!-- Semantic toggle: Holdings / Performance -->
            <div class="flex rounded-lg border border-lf-subtle text-xs overflow-hidden" data-testid="positions-semantic-toggle">
                <button class="px-2.5 py-1 transition-colors {semanticMode === 'holdings' ? 'bg-lf-checked text-lf-on-checked' : 'text-lf-muted hover:bg-lf-hover'}" onclick={() => (semanticMode = 'holdings')} aria-pressed={semanticMode === 'holdings'} data-testid="positions-toggle-holdings">
                    {$_('dashboard.holdingsTab') || 'Holdings'}
                </button>
                <button
                    class="px-2.5 py-1 transition-colors {semanticMode === 'performance' ? 'bg-lf-checked text-lf-on-checked' : 'text-lf-muted hover:bg-lf-hover'}"
                    onclick={() => (semanticMode = 'performance')}
                    aria-pressed={semanticMode === 'performance'}
                    data-testid="positions-toggle-performance"
                >
                    {$_('dashboard.performanceTab') || 'Performance'}
                </button>
            </div>

            <!-- Visual toggle: Table / Map -->
            <div class="flex rounded-lg border border-lf-subtle text-xs overflow-hidden" data-testid="positions-visual-toggle">
                <button
                    class="px-2 py-1 transition-colors {visualMode === 'table' ? 'bg-lf-neutral text-lf-secondary' : 'text-lf-muted hover:bg-lf-hover'}"
                    onclick={() => (visualMode = 'table')}
                    aria-pressed={visualMode === 'table'}
                    title={$_('dashboard.viewTable')}
                    data-testid="positions-toggle-table"
                >
                    <Table2 size={14} />
                </button>
                <button class="px-2 py-1 transition-colors {visualMode === 'map' ? 'bg-lf-neutral text-lf-secondary' : 'text-lf-muted hover:bg-lf-hover'}" onclick={() => (visualMode = 'map')} aria-pressed={visualMode === 'map'} title={$_('dashboard.viewMap')} data-testid="positions-toggle-map">
                    <Grid2x2 size={14} />
                </button>
            </div>

            {#if visualMode === 'table' && activeTableRef}
                <div data-testid="positions-column-visibility-toggle">
                    <ColumnVisibilityToggle tableRef={activeTableRef} />
                </div>
            {/if}

            <a href={assetsHref} class="text-xs text-lf-link hover:underline font-medium ml-1" data-testid="positions-see-all">
                {$_('dashboard.seeAllPositions')}
            </a>
        </div>
    </div>

    <!-- Content -->
    {#if showLoading}
        <div class="space-y-2 flex-1">
            {#each {length: 5} as _}
                <div class="h-9 bg-lf-neutral rounded animate-pulse"></div>
            {/each}
        </div>
    {:else if showHoldingsEmpty}
        <p class="text-sm text-lf-muted py-6 text-center flex-1 flex items-center justify-center">
            {$_('dashboard.noPositions')}
        </p>
    {:else if showPerformanceEmpty}
        <p class="text-sm text-lf-muted py-6 text-center flex-1 flex items-center justify-center">
            {$_('dashboard.noPeriodPnl')}
        </p>
    {:else}
        <div class="flex-1 {visualMode === 'table' ? 'overflow-x-auto' : ''}">
            {#if semanticMode === 'holdings' && visualMode === 'table'}
                <ExposureTable bind:this={exposureTableComponent} {holdings} {displayCurrency} {brokers} {onAnalyze} {analyzedAssetId} selectable {selectedKeys} onSelectionChange={handleSelectionChange} />
                <div class="mt-4" data-testid="positions-chart-section">
                    <PositionsReturnChart
                        lines={chartLines}
                        view={chartView}
                        onviewchange={handleChartViewChange}
                        {hiddenIds}
                        ontoggle={toggleLine}
                        colorOf={colourOf}
                        currency={displayCurrency}
                        loading={positionsSeriesLoading && selectedRows.length > 0}
                        failed={positionsSeriesFailed && selectedRows.length > 0}
                        portfolioLabel={$_('dashboard.positionsChart.portfolio')}
                        note={$_('dashboard.positionsChart.portfolioNote')}
                    />
                </div>
            {:else if semanticMode === 'holdings' && visualMode === 'map'}
                <ExposureTreemap {holdings} holdingGroups={summary?.holding_groups ?? []} {displayCurrency} {onAnalyze} />
            {:else if semanticMode === 'performance' && visualMode === 'table' && contribution}
                <ContributionTable bind:this={contributionTableComponent} positions={contributionPositions} {holdings} {displayCurrency} {brokers} {onAnalyze} {analyzedAssetId} />
                <OtherPeriodEffectsTable effects={otherEffects} {displayCurrency} />
            {:else if semanticMode === 'performance' && visualMode === 'map' && contribution}
                <PerformanceChart positions={contributionPositions} {otherEffects} {displayCurrency} {onAnalyze} />
            {/if}
        </div>
    {/if}
</div>
