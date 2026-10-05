<script lang="ts">
    /**
     * L3° for Asset Global — "what did each of these risk, and what did it pay?"
     *
     * **The scatter is the whole level, and the cards are what is missing.** The
     * portfolio's L3 leads with Sortino, Sharpe and beta as cards, and on that
     * page they are answers about one thing. Repeat them per asset and each cell
     * reads as a grade: "0.4" beside "1.9" is a verdict about two instruments,
     * which is exactly what `03-mappa-livelli-pagine` forbids here — *"a
     * comparison between assets, never a judgement"*. A scatter states two
     * coordinates and lets the reader see the trade-off without ranking anyone.
     *
     * 🔴 **AND THE JUDGEMENT IS NOT SUPPRESSED, IT IS IMPOSSIBLE.** On a
     * risk/return plot the verdict is the Capital Market Line: above it means
     * "paid well for the risk". `capitalMarketLine()` draws only when a point
     * whose role is `portfolio` exists, and that point exists only when the
     * payload carries both a portfolio volatility and a portfolio expected
     * return. `RiskAssetSetReturnOutput` **has no field for either** — not
     * `None`, absent — and the model is `extra="forbid"`, so a fabricated
     * aggregate is not merely rejected, it is unexpressible. Nothing on this
     * surface can turn the line back on, because there is no switch to turn: the
     * defence lives in a shape, in a file that would have to be edited.
     *
     * **No money.** `assetSetLevels` has no currency parameter and returns no
     * amount; a set of assets has no weights and therefore no sum.
     *
     * **The benchmark is the shared one, and there is no picker here.** It comes
     * from `riskBenchmark`, the same module-scope choice Dashboard and Broker
     * Detail read. `03` §3.1 says the benchmark must be identical across pages or
     * the pages stop being comparable, which is the property the whole redesign
     * builds; a second picker on this page would be a second way to disagree.
     *
     * **The table comes first, is the project's, and only the reader sorts it**
     * (the developer's review, 30/09, as for L1°; the data first, then its chart). It
     * opens in the order of the
     * selection, and only a click on a column's title reorders it — never the system,
     * and still no colour or arrow in a cell. Each title explains its figure in a
     * tooltip, and the asset column is L1°'s (`assetSetTable`). The return is named
     * for what it is, the period's average per year: "expected" read as a forecast,
     * so the developer asked for the plain name and for its computation in the tooltip.
     */
    import {_ as t} from '$lib/i18n';
    import ScatterChart from '$lib/components/charts/ScatterChart.svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {attachOverflowMarqueeToDescendants} from '$lib/actions/scrollOnOverflow';
    import {assetStoreVersion, getAssetInfo} from '$lib/stores/reference/assetStore';
    import {currentLanguage} from '$lib/stores/app/language';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

    import {formatRatio} from './riskAnalysisHelpers';
    import {assetSetCalculationWindow, buildAssetSetBenchmarkPoint, buildAssetSetChartPoints, buildAssetSetPaidRows, calendarLength, type AssetSetPaidRow} from './assetSetLevels';
    import {assetNameColumn, figureCell} from './assetSetTable';
    import {dayFormatter} from './eligibility';

    interface Props {
        assetIds: number[];
        assetLabels: ReadonlyMap<number, string>;
        /** Each asset's icon URL, by id, resolved by the panel as for L1°'s table. */
        assetIcons: ReadonlyMap<number, string>;
        riskReturn: RiskAnalyticResult | null;
        kpi: RiskAnalyticResult | null;
        comparison: RiskAnalyticResult | null;
        /** Set when a benchmark is chosen and the comparison against it was measured. */
        benchmarkApplies: boolean;
        loading?: boolean;
        /**
         * The base wave failed (`controller.loadError`): the body says so and offers a retry.
         * Without it the rows, which come from the selected ids, read as a table of dashes.
         */
        failed?: boolean;
        /**
         * The base answer arrived and was discarded on every attempt (`controller.loadDiscarded`).
         * The frame says so (`answer_discarded` in its `errorCodes`); the body only offers
         * the cure, a retry, when there is no figure to show.
         */
        discarded?: boolean;
        /** Ask the base again, past the cache (`controller.loadBase(true)`). */
        onretry?: () => void;
        /**
         * The table's instance, for the column toggle the levels draw beside the frame's
         * manual icon. Set only while the table is on screen.
         */
        tableRef?: DataTable<AssetSetPaidRow>;
        /**
         * The toolbar's period, as ISO days. The note under the table states the window the
         * figures were actually calculated on, and says when it falls short of this one.
         */
        dateStart: string;
        dateEnd: string;
    }

    let {assetIds, assetLabels, assetIcons, riskReturn, kpi, comparison, benchmarkApplies, loading = false, failed = false, discarded = false, onretry, tableRef = $bindable(), dateStart, dateEnd}: Props = $props();

    let rows = $derived(buildAssetSetPaidRows(assetIds, assetLabels, riskReturn, kpi, comparison));
    /**
     * The reference's name comes from the selection when it is one of the selected
     * assets (D371), and otherwise from the asset store, as the portfolio L3 names its
     * own benchmark (`RiskLevelsPanel`, `benchmarkName`): read only from the selection's
     * map, a benchmark outside it was labelled `#id` on every chart. `$assetStoreVersion`
     * is read so a name that arrives after the first render replaces the fallback.
     */
    let benchmarkPoint = $derived.by(() => {
        void $assetStoreVersion;
        return buildAssetSetBenchmarkPoint(comparison, assetLabels, (assetId) => getAssetInfo(assetId)?.display_name);
    });

    /**
     * The dots, the benchmark among them (`buildAssetSetChartPoints`): a selected
     * reference is its own row's dot, drawn as the benchmark; any other gets a dot of
     * its own, last, so it draws over the cloud.
     */
    let points = $derived(buildAssetSetChartPoints(rows, benchmarkPoint));

    // Two dots are the least that can show a relationship; one is a fact without
    // a comparison, and this level exists to compare.
    let hasScatter = $derived(points.length >= 2);
    let hasAnyFigure = $derived(rows.some((row) => row.volatility !== null || row.expectedReturn !== null));

    /**
     * The period the figures were calculated on, recalled under the table because the toolbar
     * that chose it is far away (the developer's review, round 4). Read from the answers' own
     * metadata, never from the toolbar, so it always describes the figures on screen, and says
     * so when an asset — or the benchmark — with a shorter history narrowed the window.
     */
    let calculationWindow = $derived(assetSetCalculationWindow([riskReturn, kpi, comparison], dateStart, dateEnd));
    let formatDay = $derived(dayFormatter($currentLanguage));
    /**
     * The length in calendar years, months and days — «3 mesi e 1 giorno», «1 anno» — never
     * as a count of days (the developer's review, round 4). Zero parts are left out, and the
     * rest are joined the way the reader's language joins a list.
     */
    let periodLength = $derived.by(() => {
        if (calculationWindow === null) return '';
        const {years, months, days} = calendarLength(calculationWindow.start, calculationWindow.end);
        const parts = [years > 0 ? $t('risk.assetSet.levels.l3.period.years', {values: {count: years}}) : null, months > 0 ? $t('risk.assetSet.levels.l3.period.months', {values: {count: months}}) : null, days > 0 ? $t('risk.assetSet.levels.l3.period.days', {values: {count: days}}) : null].filter(
            (part): part is string => part !== null,
        );
        if (parts.length === 0) return $t('risk.assetSet.levels.l3.period.days', {values: {count: calculationWindow.days}});
        return new Intl.ListFormat($currentLanguage, {style: 'long', type: 'conjunction'}).format(parts);
    });
    /** The first line: the window, and — only when it is shorter — the period that was asked for. */
    let periodWindowText = $derived.by(() => {
        if (calculationWindow === null) return '';
        const sentences = [$t('risk.assetSet.levels.l3.period.window', {values: {start: formatDay(calculationWindow.start), end: formatDay(calculationWindow.end), length: periodLength}})];
        if (calculationWindow.narrowed) sentences.push($t('risk.assetSet.levels.l3.period.narrowed', {values: {selectedStart: formatDay(dateStart), selectedEnd: formatDay(dateEnd)}}));
        return sentences.join(' ');
    });

    function percent(value: number): string {
        return formatPercent(value, {scale: 100, signed: false, digits: 1});
    }

    /** A return that may be a loss, so it carries its own sign. */
    function signedPercent(value: number): string {
        return `${value < 0 ? '\u2212' : '+'}${formatPercent(Math.abs(value), {scale: 100, signed: false, digits: 1})}`;
    }

    // Minimums only: the table is laid out `auto`, so every column widens to its own
    // upper-case title in whatever language, as in L1°.
    const VALUE_WIDTH = 110;
    const VALUE_MIN_WIDTH = 90;
    const VALUE_CLASS = 'tabular-nums text-gray-600 dark:text-gray-300';

    type ValueColumn = 'volatility' | 'expectedReturn' | 'sortino' | 'sharpe' | 'beta' | 'correlation';

    const TITLE_KEYS: Record<ValueColumn, string> = {
        volatility: 'risk.levels.l3.volatility',
        expectedReturn: 'risk.assetSet.levels.l3.expectedReturn',
        sortino: 'risk.levels.l3.sortino',
        sharpe: 'risk.levels.l3.sharpe',
        beta: 'risk.levels.l3.beta',
        correlation: 'risk.assetSet.levels.l3.correlation',
    };

    /**
     * One value column. It sorts by the figure it shows, sign included, so an
     * ascending return puts the losses first; an unmeasured cell stays `null`, which
     * the table always sorts last. Ratios stay plain: no colour, no arrow — a grade is
     * what this level may not give, and a green cell is a grade.
     */
    function valueColumn(id: ValueColumn, figure: (row: AssetSetPaidRow) => number | null, text: (value: number) => string): ColumnDef<AssetSetPaidRow> {
        return {
            id,
            header: () => $t(TITLE_KEYS[id]),
            headerTooltip: () => $t(`risk.assetSet.levels.l3.columnHelp.${id}`),
            type: 'number',
            align: 'right',
            width: VALUE_WIDTH,
            minWidth: VALUE_MIN_WIDTH,
            filterable: false,
            getValue: (row) => figure(row),
            cell: (row) => {
                // D371: the benchmark's own beta and correlation are not missing figures but
                // inapplicable — measured against itself they would be 1 by construction — so
                // its dash says so, in the developer's words, instead of the generic one.
                if (row.isReference && (id === 'beta' || id === 'correlation')) {
                    return figureCell(`<span class="${VALUE_CLASS}" data-testid="risk-asset-set-l3-${id}" data-measured="false" data-reference="true">\u2014</span>`, false, () => $t('risk.assetSet.levels.l3.referenceItself'));
                }
                const value = figure(row);
                // A dash explains itself in a tooltip, as in L1° (`figureCell`); a figure carries none.
                return figureCell(`<span class="${VALUE_CLASS}" data-testid="risk-asset-set-l3-${id}" data-measured="${value !== null}">${value === null ? '\u2014' : text(value)}</span>`, value !== null, () => $t('risk.assetSet.levels.blankNote'));
            },
        };
    }

    /** Beta and correlation need a benchmark, so their columns exist only with one. */
    let columns = $derived<ColumnDef<AssetSetPaidRow>[]>([
        // The asset column is L1°'s (`assetSetTable`): icon, one-line name, by-name order.
        assetNameColumn<AssetSetPaidRow>(
            () => $t('risk.assetSet.levels.asset'),
            () => assetIcons,
            'risk-asset-set-l3',
        ),
        valueColumn('volatility', (row) => row.volatility, percent),
        valueColumn('expectedReturn', (row) => row.expectedReturn, signedPercent),
        valueColumn(
            'sortino',
            (row) => row.sortino,
            (value) => formatRatio(value),
        ),
        valueColumn(
            'sharpe',
            (row) => row.sharpe,
            (value) => formatRatio(value),
        ),
        ...(benchmarkApplies
            ? [
                  valueColumn(
                      'beta',
                      (row) => row.beta,
                      (value) => formatRatio(value),
                  ),
                  valueColumn(
                      'correlation',
                      (row) => row.correlation,
                      (value) => formatRatio(value),
                  ),
              ]
            : []),
    ]);

    /**
     * The asset picked in the table, or `null`. The table is the one source: a row click
     * toggles its own single selection and reports it here, so the table and whatever
     * reads this value cannot disagree. The scatter marks the same asset's dot, and a
     * click on a dot goes through the table too, so a second click on it clears it, as
     * on a row.
     */
    let selectedAssetId = $state<number | null>(null);

    /**
     * A dot is `asset-<id>`, and its row carries `<id>`. The benchmark's dot has no row,
     * so a click on it leaves the selection as it was.
     */
    function selectFromPoint(pointId: string): void {
        if (!pointId.startsWith('asset-')) return;
        const rowId = pointId.slice('asset-'.length);
        if (!rows.some((row) => String(row.assetId) === rowId)) return;
        tableRef?.toggleRowSelectionById(rowId);
    }

    let tableWrapper: HTMLDivElement | undefined = $state();

    // The cells are HTML strings, so the name spans are reached through the wrapper, as
    // in L1°; the scan re-attaches whenever the table re-renders its rows.
    $effect(() => {
        if (!tableWrapper) return;
        return attachOverflowMarqueeToDescendants(tableWrapper);
    });
</script>

<div class="space-y-4" data-testid="risk-asset-set-l3" data-benchmark={benchmarkApplies ? 'true' : 'false'}>
    <p class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.assetSet.levels.l3.description')}</p>

    {#if failed}
        <div class="py-4 text-center" data-testid="risk-asset-set-l3-error">
            <p class="text-sm text-red-600 dark:text-red-400">{$t('risk.states.loadFailed')}</p>
            <button type="button" class="mt-2 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700" onclick={() => onretry?.()} data-testid="risk-asset-set-l3-retry">{$t('common.retry')}</button>
        </div>
    {:else if loading && !hasAnyFigure}
        <div class="h-64 animate-pulse rounded-lg bg-gray-100 dark:bg-slate-700" data-testid="risk-asset-set-l3-loading"></div>
    {:else if discarded && !hasAnyFigure}
        <!-- The frame carries the sentence (`answer_discarded`); the body carries the cure. -->
        <div class="py-4 text-center" data-testid="risk-asset-set-l3-discarded">
            <button type="button" class="mt-2 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700" onclick={() => onretry?.()} data-testid="risk-asset-set-l3-retry">{$t('common.retry')}</button>
        </div>
    {:else if rows.length === 0}
        <p class="py-4 text-center text-sm text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-l3-empty">{$t('risk.states.empty')}</p>
    {:else}
        <div bind:this={tableWrapper} data-testid="risk-asset-set-l3-table" data-row-count={rows.length}>
            <DataTable
                bind:this={tableRef}
                data={rows}
                {columns}
                getRowId={(row) => String(row.assetId)}
                storageKey="risk-asset-set-l3"
                tableLayout="auto"
                enableSelection={true}
                selectionMode="single"
                onSelectionChange={(ids) => (selectedAssetId = ids.length > 0 ? Number(ids[0]) : null)}
                enableActions={false}
                enableColumnFilters={false}
                enablePagination={false}
                enableContextMenu={false}
            />
        </div>

        {#if calculationWindow}
            <!-- Two lines (the developer's review, round 4): the window, then what is annualised.
                 Only volatility and the average return are; Sharpe and Sortino derive from them,
                 and beta and correlation have no unit of time — the line claims no more. -->
            <p class="text-xs text-gray-500 dark:text-gray-400" data-testid="risk-asset-set-l3-period" data-start={calculationWindow.start} data-end={calculationWindow.end} data-days={calculationWindow.days} data-narrowed={String(calculationWindow.narrowed)}>
                <span class="block" data-testid="risk-asset-set-l3-period-window">{periodWindowText}</span><span class="block" data-testid="risk-asset-set-l3-period-annualized">{$t('risk.assetSet.levels.l3.period.annualized')}</span>
            </p>
        {/if}

        <!-- The data first, then its chart (the developer's review, 30/09): the table
             and its period open the level, the scatter draws the same figures. -->
        {#if hasScatter}
            <div data-testid="risk-asset-set-l3-risk-return">
                <!-- `riskFreeRate` is left at its default and anchors nothing here:
                     with no portfolio point there is no line for it to anchor. The
                     label is still supplied because the component asks for it; it
                     names a line that this payload cannot produce. -->
                <ScatterChart
                    {points}
                    labels={{
                        volatility: $t('risk.levels.l3.scatter.axisVolatility'),
                        return: $t('risk.assetSet.levels.l3.axisReturn'),
                        capitalMarketLine: $t('risk.levels.l3.scatter.line'),
                    }}
                    height="360px"
                    testId="risk-asset-set-l3-scatter"
                    emptyLabel={$t('risk.states.unavailable')}
                    selectedId={selectedAssetId === null ? null : `asset-${selectedAssetId}`}
                    onpointclick={selectFromPoint}
                />
                <!-- The axis label alone cannot carry this. On a very volatile
                     holding the average return and the one actually lived through
                     differ by tens of percentage points, and a reader seeing "−11%"
                     beside a coin that halved has to be told that the average is
                     not the return lived through.

                     A key of this page's own, and not the portfolio L3's note. That
                     one opens with "above the line means better paid for the risk",
                     which is true where the line is drawn — and was borrowed here,
                     under a chart that by construction has no line, putting back in
                     words the one verdict the payload's shape makes impossible.
                     `assetSetI18n.test.ts` now fails if this note names a line. -->
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400" data-testid="risk-asset-set-l3-scatter-note">{$t('risk.assetSet.levels.l3.scatterNote')}</p>
            </div>
        {/if}
    {/if}
</div>
