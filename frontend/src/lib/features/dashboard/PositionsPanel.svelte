<!--
  PositionsPanel — Dashboard positions widget with 4 views.

  Views:
  - Holdings / Table: snapshot of open positions at date_to (weights, unrealized P&L, PMC)
  - Holdings / Map: ECharts treemap Broker → Type → Asset (area=Value, color=Unrealized P&L%)
  - Performance / Table: per-asset period P&L attribution (open+closed, Status is a filterable
    column, not a panel-level toggle) + Other Period Effects section below
  - Performance / Map: stacked diverging bar chart (positive components right of zero, negative
    left of zero) + Other Period Effects rows

  Holdings / Table and Performance / Table carry the return chart of the positions (Y5-2, #48; FB-12): the rows
  the user ticks are drawn as lines over the portfolio's own (Abs or «base 100»); the legend turns them on and
  off. Beside it, the allocation by asset (pie and history), as the Dashboard shows the portfolio's allocation.
  The Portfolio table also lists, last and in italics, the positions sold out inside the period (FB-13): they
  come from the period's contribution, which the Portfolio view therefore asks too.

  Data sources:
  - Holdings: summary.holdings from portfolioStore (engine snapshot at date_to)
  - Performance: positions_contribution from portfolioStore (fetched on demand)

  «Globale / Broker» (project 74): with two brokers or more in the scope, a switch shows the rows one per asset, summed over its
  brokers by the backend (`group_by=asset`): the grouped rows come with the contribution's answer (`groupedSummary`). The page
  owns the choice (it changes what is asked) and persists it; the ticked lines follow it (`regroupSelection`).

  Pattern: Svelte 5 Runes, data-testid, dark mode.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Table2, Grid2x2, Globe, Briefcase, ArrowUpRight} from 'lucide-svelte';
    import ViewModeToggle from '$lib/components/ui/ViewModeToggle.svelte';
    import type {PositionsGrouping} from '$lib/features/portfolio-view/portfolioDataScope';
    import {getUserStorage, getUserStorageKey, setUserStorage} from '$lib/utils/storage';
    import {onDestroy, untrack} from 'svelte';
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
    import AllocationPanel from './AllocationPanel.svelte';
    import AssetCalendarWindowControls from '$lib/features/assets/detail/AssetCalendarWindowControls.svelte';
    import {DEFAULT_CALENDAR_RETURN_WINDOW, type CalendarReturnPresetKey, type CalendarReturnWindowSelection, type CalendarReturnWindowUnit} from '$lib/components/charts/calendarReturnWindow';
    import {assetColorRanks, assetIdOfLineId, PORTFOLIO_LINE_ID, portfolioLine, positionLines, regroupSelection, selectionKeys, type HistoryPointLike, type PositionKey, type PositionLine, type PositionsChartView, type PositionsSeriesResponse, type SelectedPosition} from './positionsSeries';
    import {makePositionKey} from './positionKey';
    import {rollingLine, type PositionsRollingState} from './positionsRolling';

    import {closedPositionsToList} from './closedPositions';
    import type {AllocationHistoryDimensions, PortfolioSummary, PositionsContribution} from '$lib/stores/portfolio/portfolioStore.svelte';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';

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
        /** The Rolling view (FB-15): the rolling return of the ticked positions' assets, by asset, as the page's controller holds it. */
        positionsRolling?: PositionsRollingState | null;
        /** Asks the rolling return of these assets (each once); called when the Rolling view is on and the selection changes, never with none. */
        onRequestPositionsRolling?: (assetIds: number[]) => void;
        /** The window of the Rolling view the user chose; null (the start): the automatic one, the largest preset that fits the period (F-2). */
        rollingSelection?: CalendarReturnWindowSelection | null;
        /** The preset the automatic window is, for the controls to show it picked. */
        rollingAutoPreset?: CalendarReturnPresetKey;
        /** The user picked a window; the page asks the views again with it. */
        onRollingSelectionChange?: (selection: CalendarReturnWindowSelection) => void;
        /** The Dashboard's own history: the chart's portfolio line (its return, not the positions' P&L). */
        portfolioHistory?: ReadonlyArray<HistoryPointLike>;
        /** The allocation by asset beside the chart (FB-12): the same inputs the Dashboard's allocation panel takes. */
        brokerIds?: number[];
        currentLanguage?: string;
        allocationHistory?: AllocationHistoryDimensions | null;
        onRequestAllocationHistory?: (dimension: 'type' | 'sector' | 'geo' | 'asset', brokerIds: number[] | undefined) => void | Promise<void>;
        /** How the rows are grouped (project 74): one per asset and broker, or one per asset over its brokers («Globale»). */
        grouping?: PositionsGrouping;
        /** The scope has two brokers or more: the «Globale / Broker» switch is shown. */
        groupingAvailable?: boolean;
        /** The user picked a grouping; the page persists it and asks the rows again. */
        onGroupingChange?: (grouping: PositionsGrouping) => void;
        /** «Globale»: the summary of the grouped question, whose holdings and groups are one per asset; null until it lands. */
        groupedSummary?: PortfolioSummary | null;
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
        positionsRolling = null,
        onRequestPositionsRolling,
        rollingSelection = null,
        rollingAutoPreset = DEFAULT_CALENDAR_RETURN_WINDOW.preset,
        onRollingSelectionChange,
        portfolioHistory = [],
        brokerIds,
        currentLanguage = 'en',
        allocationHistory = null,
        onRequestAllocationHistory,
        grouping = 'broker',
        groupingAvailable = false,
        onGroupingChange,
        groupedSummary = null,
    }: Props = $props();

    /** «Globale» is on screen (project 74): the rows are the grouped question's. */
    let globalView = $derived(grouping === 'asset');

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
    // (needed for both the table and the chart, plus Other Period Effects), and with the Portfolio table:
    // the positions sold out inside the period are its last rows (FB-13).
    $effect(() => {
        // In «Globale» every view reads the grouped question, which is the contribution's (project 74)
        const needsContribution = globalView || semanticMode === 'performance' || (semanticMode === 'holdings' && visualMode === 'table');
        if (needsContribution && !contribution && !contributionLoading) {
            onRequestContribution?.();
        }
    });

    // =========================================================================
    // The return chart of the positions (Y5-2)
    // =========================================================================

    const CHART_VIEW_KEY = 'dashboard-positions-chart-view';

    function readChartView(): PositionsChartView {
        const stored = getUserStorage(CHART_VIEW_KEY, 'percentage');
        return stored === 'absolute' || stored === 'rolling' ? stored : 'percentage';
    }

    type SelectedRow = SelectedPosition;

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

    let selectedKeys = $derived(selectedRows.map((row) => row.key));

    // The ticked lines follow the switch (project 74): Globale ticks the assets, Broker every row of a ticked asset.
    let shownGrouping: PositionsGrouping = untrack(() => grouping);
    $effect(() => {
        const next = grouping;
        if (next === shownGrouping) return;
        shownGrouping = next;
        const perBroker = untrack(() => [...(summary?.holdings ?? [])]).map((holding) => {
            const brokerId = safeNumberOrNull(holding.broker_id);
            return {key: makePositionKey(holding.asset_id, brokerId), assetId: holding.asset_id, brokerId};
        });
        untrack(() => handleSelectionChange(regroupSelection(selectedRows, next, perBroker)));
    });

    // The Rolling view asks the rolling return of the ticked positions' assets; the controller keeps what it already has.
    $effect(() => {
        if (chartView !== 'rolling' || selectedRows.length === 0) return;
        onRequestPositionsRolling?.([...new Set(selectedRows.map((row) => row.assetId))]);
    });

    // The window of the Rolling view (F-2): what the controls show is the user's choice or, before one, the automatic preset.
    let customAmount = $state(DEFAULT_CALENDAR_RETURN_WINDOW.customAmount);
    let customUnit = $state<CalendarReturnWindowUnit>(DEFAULT_CALENDAR_RETURN_WINDOW.customUnit);
    let customEditing = $state(false);
    let windowShown = $derived<CalendarReturnWindowSelection>(rollingSelection ?? {...DEFAULT_CALENDAR_RETURN_WINDOW, kind: 'preset', preset: rollingAutoPreset});

    function pickWindowPreset(preset: CalendarReturnPresetKey) {
        customEditing = false;
        onRollingSelectionChange?.({kind: 'preset', preset, customAmount, customUnit});
    }

    function pickWindowCustom(amount: number, unit: CalendarReturnWindowUnit) {
        customEditing = false;
        customAmount = amount;
        customUnit = unit;
        onRollingSelectionChange?.({kind: 'custom', preset: windowShown.preset, customAmount: amount, customUnit: unit});
    }

    /** A ticked position's name for the legend of the Rolling view: its asset's name, then the broker, as the positions' own lines say it. */
    function rollingLabel(row: SelectedRow): string {
        const open = holdings.find((holding) => holding.asset_id === row.assetId && (safeNumberOrNull(holding.broker_id) ?? null) === row.brokerId);
        const sold = soldPositions.find((position) => position.asset_id === row.assetId && (position.broker_id ?? null) === row.brokerId);
        const source = open ?? sold;
        if (!source) return `#${row.assetId}`;
        const name = source.asset_name;
        const broker = typeof source.broker_name === 'string' ? source.broker_name : '';
        return broker ? `${name} · ${broker}` : name;
    }

    function safeNumberOrNull(value: unknown): number | null {
        return typeof value === 'number' ? value : null;
    }

    let chartLines = $derived.by<PositionLine[]>(() => {
        if (chartView === 'rolling') {
            // No portfolio line: the portfolio has no price. A ticked position whose asset has no view yet draws nothing.
            return selectedRows.flatMap((row) => {
                const view = positionsRolling?.views.get(row.assetId);
                return view ? [rollingLine(row.key, rollingLabel(row), view)] : [];
            });
        }
        const portfolio = portfolioLine(portfolioHistory, chartView, $_('dashboard.positionsChart.portfolio'));
        const picked = new Set(selectedKeys);
        const positions = positionLines(positionsSeries, chartView).filter((line) => picked.has(line.id));
        return portfolio ? [portfolio, ...positions] : positions;
    });
    let chartLoading = $derived(chartView === 'rolling' ? !!positionsRolling?.loading && selectedRows.length > 0 : positionsSeriesLoading && selectedRows.length > 0);
    let chartFailed = $derived(chartView === 'rolling' ? !!positionsRolling?.failed && selectedRows.length > 0 : positionsSeriesFailed && selectedRows.length > 0);

    // =========================================================================
    // Derived data
    // =========================================================================

    // «Globale»: the grouped question's rows (project 74); the totals, the allocation and the currency stay the main report's
    let holdings = $derived((globalView ? groupedSummary?.holdings : summary?.holdings) ?? []);
    let holdingGroups = $derived((globalView ? groupedSummary?.holding_groups : summary?.holding_groups) ?? []);
    let groupedLoading = $derived(globalView && !groupedSummary);
    let displayCurrency = $derived(summary?.net_worth.code ?? 'EUR');

    /** Performance shows open+closed positions together — Status is a filterable
     *  column inside ContributionTable/PerformanceChart, not a panel-level toggle. */
    let contributionPositions = $derived(contribution?.positions ?? []);
    let otherEffects = $derived(contribution?.other_effects ?? []);

    /** The positions sold out inside the period: they are no longer holdings, but the Portfolio table lists them last (FB-13) — except those that moved to another broker of the report (T1). */
    let soldPositions = $derived(
        closedPositionsToList(contributionPositions, holdings).map((position) => ({
            asset_id: position.asset_id,
            asset_name: position.asset_name,
            asset_type: position.asset_type,
            broker_id: typeof position.broker_id === 'number' ? position.broker_id : null,
            broker_name: typeof position.broker_name === 'string' ? position.broker_name : null,
            broker_ids: position.broker_ids,
            asset_ticker: typeof position.asset_ticker === 'string' ? position.asset_ticker : null,
        })),
    );

    /**
     * A line wears its asset's colour, the pie's and the history's: the asset's rank by weight (`assetColorRanks`, the one place the ranks are computed),
     * whatever is ticked and in whatever order. The assets sold out in the period come after the ranked ones.
     */
    let assetRanks = $derived(
        assetColorRanks((summary?.allocation_by_asset ?? []) as Array<{id?: number | null; amount?: string | null}>, (allocationHistory?.asset ?? []) as Array<{date: string; through?: string; components?: Array<{id?: number | null; amount?: string | null}>}>, [
            ...holdings.map((holding) => holding.asset_id),
            ...soldPositions.map((position) => position.asset_id),
        ]),
    );
    // A new function each time the ranks or the theme move: the chart redraws when its `colorOf` changes.
    let colourOf = $derived((id: string): string => {
        if (id === PORTFOLIO_LINE_ID) return themed(GROWTH_SERIES.nav, isDark);
        const assetId = assetIdOfLineId(id);
        const rank = assetId === null ? undefined : assetRanks.get(assetId);
        return growthBrokerColor(rank ?? assetRanks.size, isDark);
    });

    let showLoading = $derived(loading || groupedLoading || (semanticMode === 'performance' && contributionLoading));
    let showHoldingsEmpty = $derived(semanticMode === 'holdings' && holdings.length === 0);
    let showPerformanceEmpty = $derived(semanticMode === 'performance' && (!contribution || (contributionPositions.length === 0 && otherEffects.length === 0)));
</script>

{#snippet rollingWindowControls()}
    <AssetCalendarWindowControls selection={windowShown} bind:customAmount bind:customUnit bind:customEditing onpreset={pickWindowPreset} oncustom={pickWindowCustom} idPrefix="positions" />
{/snippet}

{#snippet chartSection()}
    <!-- The return chart (3/5) beside the allocation by asset (2/5): the proportions and the look of the Dashboard's Growth and Allocation (FB-12). -->
    <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-5" data-testid="positions-chart-section">
        <div class="lg:col-span-3 rounded-xl border border-lf-subtle bg-lf-card p-4 shadow-sm shadow-lf-shadow-card">
            <PositionsReturnChart
                lines={chartLines}
                view={chartView}
                onviewchange={handleChartViewChange}
                {hiddenIds}
                ontoggle={toggleLine}
                colorOf={colourOf}
                currency={displayCurrency}
                height="20rem"
                loading={chartLoading}
                failed={chartFailed}
                portfolioLabel={$_('dashboard.positionsChart.portfolio')}
                note={$_('dashboard.positionsChart.portfolioNote')}
                windowControls={rollingWindowControls}
            />
        </div>
        <AllocationPanel {summary} {loading} {displayCurrency} {brokerIds} {currentLanguage} {allocationHistory} {onRequestAllocationHistory} lockedTab="asset" viewStorageKey="dashboard-positions-allocation-view" />
    </div>
{/snippet}

<div class="bg-lf-card text-lf-primary rounded-xl border border-lf-subtle shadow-sm shadow-lf-shadow-card p-4 flex flex-col" data-testid="positions-panel" aria-busy={showLoading} data-busy={showLoading ? 'true' : 'false'}>
    <!-- Header (project 74, layout rev 2): from sm up one row — title, then Portfolio/Period, Global/Broker, Table/Map, the
         columns and the «see all» badge; on a phone the title row keeps the columns and the badge, the three selectors go below. -->
    <div class="mb-3 flex flex-wrap items-center gap-2" data-testid="positions-header">
        <h2 class="order-1 text-sm font-semibold text-lf-secondary">
            {$_('dashboard.positions')}
        </h2>
        <div class="order-3 flex w-full items-center gap-2 sm:order-2 sm:ml-auto sm:w-auto" data-testid="positions-selectors">
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

            <!-- Grouping toggle: Global / Broker (project 74), with two brokers or more -->
            {#if groupingAvailable}
                <ViewModeToggle
                    mode={grouping}
                    options={[
                        {value: 'asset', icon: Globe, label: $_('dashboard.groupBy.global'), hint: $_('dashboard.groupBy.globalHint'), testId: 'positions-grouping-asset'},
                        {value: 'broker', icon: Briefcase, label: $_('dashboard.groupBy.broker'), hint: $_('dashboard.groupBy.brokerHint'), testId: 'positions-grouping-broker'},
                    ]}
                    compact
                    showLabels
                    groupLabel={$_('dashboard.groupBy.label')}
                    testId="positions-grouping-toggle"
                    onchange={(mode) => onGroupingChange?.(mode === 'asset' ? 'asset' : 'broker')}
                />
            {/if}

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
        </div>
        <div class="order-2 ml-auto flex items-center gap-2 sm:order-3 sm:ml-0" data-testid="positions-header-links">
            {#if visualMode === 'table' && activeTableRef}
                <div data-testid="positions-column-visibility-toggle">
                    <ColumnVisibilityToggle tableRef={activeTableRef} />
                </div>
            {/if}

            <!-- «See all» as a badge (layout rev 2), as the Transactions link of an asset's header -->
            <a href={assetsHref} class="inline-flex items-center gap-1 rounded-full border border-lf-focus px-2 py-0.5 text-xs font-medium whitespace-nowrap text-lf-link hover:bg-lf-selected focus-visible:outline-lf-focus" data-testid="positions-see-all">
                <ArrowUpRight size={12} />
                {$_('dashboard.seeAllPositions')}
            </a>
            <DocsLink path="user/dashboard/positions/" label={$_('dashboard.docsHelp.positions')} icon="book" size={16} testId="positions-docs" />
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
                <ExposureTable bind:this={exposureTableComponent} {holdings} {soldPositions} {displayCurrency} {brokers} {onAnalyze} {analyzedAssetId} selectable {selectedKeys} onSelectionChange={handleSelectionChange} />
                {@render chartSection()}
            {:else if semanticMode === 'holdings' && visualMode === 'map'}
                <ExposureTreemap {holdings} {holdingGroups} {displayCurrency} {onAnalyze} {globalView} />
            {:else if semanticMode === 'performance' && visualMode === 'table' && contribution}
                <ContributionTable bind:this={contributionTableComponent} positions={contributionPositions} {holdings} {displayCurrency} {brokers} {onAnalyze} {analyzedAssetId} selectable {selectedKeys} onSelectionChange={handleSelectionChange} />
                <OtherPeriodEffectsTable effects={otherEffects} {displayCurrency} />
                {@render chartSection()}
            {:else if semanticMode === 'performance' && visualMode === 'map' && contribution}
                <PerformanceChart positions={contributionPositions} {otherEffects} {displayCurrency} {onAnalyze} />
            {/if}
        </div>
    {/if}
</div>
