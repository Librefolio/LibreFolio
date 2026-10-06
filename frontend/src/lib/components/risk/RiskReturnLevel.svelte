<!--
  RiskReturnLevel — "what did each pay for its risk?", asset by asset: the table first, then
  the chart that draws the same figures, then the notes that say how to read it.

  One component for the portfolio's L3 (Dashboard, a broker's page) and Asset Global's L3°
  (developer's review of 05/10/2026: "rendi il tutto un componente così che nel tempo se
  aggiorniamo uno aggiorniamo entrambi"). It is the lab's section, moved here whole — the
  table, its columns and their tooltips, the linked selection, the chart — and each page keeps
  what belongs to its payload: the rows and the dots, its own states, and anything it says
  under the table (`afterTable`, the lab's period). What still differs between the pages is
  said as capabilities (`riskReturnLevel.ts`), never as a page name.

  **The data first, then its chart** (developer's review of 30/09, on the lab): the table opens
  the level, and only the reader sorts it — a click on a column's title, never the system, and
  no colour or arrow in a cell: a green cell is a grade, and a comparison between assets may
  not give one.

  **The selection is the table's.** A row click toggles its single selection and reports it
  here; the chart marks the same asset's dot, and a click on a dot goes through the table too,
  so a second click clears it, as on a row. The portfolio and a benchmark nobody holds have rows
  of their own (`added`), so their dots select too; a dot without a row selects nothing.

  **The columns are the reader's to size** (developer's review of 06/10/2026). The table is laid
  out `fixed`, DataTable's default, because only there does a dragged width hold: under `auto`
  a table wider than its box keeps every column at its minimum, and a drag moved nothing. A
  figure's column opens as wide as its title in the reader's language (`headerWidth`), which is
  also as narrow as it goes, so no drag cuts a title. The names are not pinned: they scroll with
  the rest of the row.

  ⚠️ **TWO TEST-ID PREFIXES, ON PURPOSE.** The blocks (`-table`, `-risk-return`, `-scatter`,
  `-scatter-note`) take `testIdPrefix`; the cells take `cellTestIdPrefix`, which defaults to it.
  On the portfolio's L3 the page's own blocks are `risk-l3-*` too (`-benchmark`, `-loading`,
  `-empty`), so its cells take a prefix of their own and a column can never collide with a
  block. The lab's cells keep the names its tests read.
-->
<script generics="T extends RiskReturnRow" lang="ts">
    import type {Snippet} from 'svelte';

    import {_ as t} from '$lib/i18n';
    import ScatterChart from '$lib/components/charts/ScatterChart.svelte';
    import {capitalMarketLineAnchor, type RiskReturnPoint} from '$lib/components/charts/scatterChartHelpers';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import {attachOverflowMarqueeToDescendants} from '$lib/actions/scrollOnOverflow';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';

    import {formatRatio} from './riskAnalysisHelpers';
    import {assetNameColumn, figureCell} from './assetSetTable';
    import {formatShare} from './levels/shareFormat';
    import {headerWidth, measureHeaderTitle, outsideParts, pointIdOf, referenceRowsFirst, riskReturnNotes, rowIdForPoint, rowIdOf, type RiskReturnCapabilities, type RiskReturnOutside, type RiskReturnRow} from './riskReturnLevel';

    interface Props {
        /** One per asset, in the order the page opens them in. */
        rows: T[];
        /** The chart's dots, built by the page: it alone knows which one is its benchmark. */
        points: readonly RiskReturnPoint[];
        /** What the payload carries: the columns and the notes that depend on it. */
        capabilities: RiskReturnCapabilities;
        /** Each asset's icon URL, by id. */
        assetIcons: ReadonlyMap<number, string>;
        /** Prefix of the blocks' test ids: `-table`, `-risk-return`, `-scatter`, `-scatter-note`… */
        testIdPrefix: string;
        /** Prefix of the cells' test ids (`-name`, `-icon`, `-<column>`); `testIdPrefix` when absent. */
        cellTestIdPrefix?: string;
        /** The table's own key, for its widths and visible columns. */
        storageKey: string;
        /** The chart's axis titles and the line's name, already translated. */
        labels: {volatility: string; return: string; capitalMarketLine: string};
        /** As a fraction. Anchors the line at x = 0, where a line is drawn. */
        riskFreeRate?: number;
        /** The chart's height. */
        height?: string;
        /** A heading over the table and the chart. */
        title?: string;
        /** What the chart leaves out, as shares of the whole: only a portfolio has a whole. */
        outside?: RiskReturnOutside | null;
        /**
         * The table's instance, for a column menu drawn elsewhere (the lab's levels draw one
         * beside their manual icon). Set only while the table is on screen.
         */
        tableRef?: DataTable<T>;
        /** Whatever the page says under the table, before the chart: the lab's period. */
        afterTable?: Snippet;
    }

    let {rows, points, capabilities, assetIcons, testIdPrefix, cellTestIdPrefix, storageKey, labels, riskFreeRate, height, title, outside = null, tableRef = $bindable(), afterTable}: Props = $props();

    let cellPrefix = $derived(cellTestIdPrefix ?? testIdPrefix);

    // The references open the table — the portfolio, then the benchmark — tinted like their dots
    // (developer's review of 06/10/2026); the reader's sort moves them like any other row.
    let orderedRows = $derived(referenceRowsFirst(rows));
    // One per asset: an added reference row is not an asset, so the page's per-asset counts hold.
    let assetRowCount = $derived(rows.filter((row) => !row.added).length);
    let addedRowCount = $derived(rows.length - assetRowCount);

    // Two dots are the least that can show a relationship; one is a fact without a comparison.
    let hasScatter = $derived(points.length >= 2);
    let lineAnchor = $derived(capitalMarketLineAnchor(points));
    let notes = $derived(riskReturnNotes({lineAnchor, capabilities, outside}));
    let outsideShown = $derived(outsideParts(outside));

    function percent(value: number): string {
        return formatPercent(value, {scale: 100, signed: false, digits: 1});
    }

    /** A return that may be a loss, so it carries its own sign. */
    function signedPercent(value: number): string {
        return `${value < 0 ? '\u2212' : '+'}${formatPercent(Math.abs(value), {scale: 100, signed: false, digits: 1})}`;
    }

    const VALUE_CLASS = 'tabular-nums text-gray-600 dark:text-gray-300';

    type ValueColumn = 'weight' | 'volatility' | 'expectedReturn' | 'sortino' | 'sharpe' | 'beta' | 'correlation';

    const TITLE_KEYS: Record<ValueColumn, string> = {
        weight: 'risk.levels.l3.table.weight',
        volatility: 'risk.levels.l3.volatility',
        expectedReturn: 'risk.levels.l3.table.expectedReturnShort',
        sortino: 'risk.levels.l3.sortino',
        sharpe: 'risk.levels.l3.sharpe',
        beta: 'risk.levels.l3.beta',
        correlation: 'risk.assetSet.levels.l3.correlation',
    };

    /**
     * The full name of a column whose title is short (developer's review of 06/10/2026: «se
     * riusciamo ad accorciare "Rendimento medio annuo" [...] nel tooltip mettiamo il nome
     * completo»). The column menu lists it, and the title's tooltip opens with it.
     */
    const FULL_TITLE_KEYS: Partial<Record<ValueColumn, string>> = {
        expectedReturn: 'risk.assetSet.levels.l3.expectedReturn',
    };

    const HELP_KEYS: Record<ValueColumn, string> = {
        weight: 'risk.levels.l3.table.weightHelp',
        volatility: 'risk.assetSet.levels.l3.columnHelp.volatility',
        expectedReturn: 'risk.assetSet.levels.l3.columnHelp.expectedReturn',
        sortino: 'risk.assetSet.levels.l3.columnHelp.sortino',
        sharpe: 'risk.assetSet.levels.l3.columnHelp.sharpe',
        beta: 'risk.assetSet.levels.l3.columnHelp.beta',
        correlation: 'risk.assetSet.levels.l3.columnHelp.correlation',
    };

    /** The columns a page may leave `undefined` per row: the ratios, measured by a query of their own. */
    const RATIO_COLUMNS: ReadonlySet<ValueColumn> = new Set<ValueColumn>(['sortino', 'sharpe', 'beta', 'correlation']);

    /**
     * A reference row's background, in the hue of its dot (`colorForRole`: sky for the portfolio,
     * amber for the benchmark), styled at the bottom of this file. The table's own hover and
     * selection still show over it.
     */
    function rowTint(row: T): string {
        if (row.role === 'portfolio') return 'risk-return-row-portfolio';
        if (row.role === 'benchmark') return 'risk-return-row-benchmark';
        return '';
    }

    /**
     * The mark before a reference's name: the shape and colour of its dot — a circle for the
     * portfolio, a diamond for the benchmark (developer's review of 06/10/2026) — so the row and
     * the dot are recognisably the same thing. It has no text, so a name read off the cell is
     * still only the name.
     */
    function roleMarkHtml(role: 'portfolio' | 'benchmark'): string {
        const shape = role === 'portfolio' ? 'rounded-full bg-sky-600 dark:bg-sky-400' : 'rotate-45 bg-amber-600 dark:bg-amber-400';
        return `<span aria-hidden="true" class="inline-block h-2.5 w-2.5 shrink-0 ${shape}" data-role-mark="${role}"></span>`;
    }

    /**
     * A reference row's name cell, its mark first. An added row has no asset behind the
     * portfolio's, so no asset id on it, and takes the `-ref-` test ids; a reference that is one of
     * the assets keeps the asset cell's test ids and asset id, as the lab's tests read them.
     */
    function referenceNameHtml(row: T, role: 'portfolio' | 'benchmark'): string {
        const prefix = row.added ? `${cellPrefix}-ref` : cellPrefix;
        const icon = role === 'benchmark' ? assetIcons.get(row.assetId) : undefined;
        const iconHtml = icon ? `<img src="${escapeHtml(icon)}" alt="" class="h-5 w-5 shrink-0 object-contain" data-testid="${prefix}-icon" />` : '';
        const assetId = role === 'benchmark' ? ` data-asset-id="${row.assetId}"` : '';
        const reference = row.added ? ` data-reference="${role}"` : '';
        return `<div class="flex min-w-0 items-center gap-2" data-testid="${prefix}-name"${reference}${assetId}>${roleMarkHtml(role)}${iconHtml}<span class="min-w-0 flex-1 text-gray-700 dark:text-gray-200 ${overflowScrollTextClass}">${escapeHtml(row.name)}</span></div>`;
    }

    /**
     * One value column. It sorts by the figure it shows, sign included, so an ascending
     * return puts the losses first; an unmeasured cell stays `null`, which the table always
     * sorts last, and its dash explains itself in a tooltip (`figureCell`).
     */
    function valueColumn(id: ValueColumn, figure: (row: T) => number | null | undefined, text: (value: number) => string): ColumnDef<T> {
        const fullTitleKey = FULL_TITLE_KEYS[id];
        const width = headerWidth($t(TITLE_KEYS[id]), measureHeaderTitle);
        return {
            id,
            header: () => $t(TITLE_KEYS[id]),
            ...(fullTitleKey ? {displayName: () => $t(fullTitleKey)} : {}),
            headerTooltip: () => (fullTitleKey ? $t('risk.levels.l3.table.namedHelp', {values: {name: $t(fullTitleKey), help: $t(HELP_KEYS[id])}}) : $t(HELP_KEYS[id])),
            type: 'number',
            align: 'right',
            width,
            minWidth: width,
            filterable: false,
            getValue: (row) => figure(row) ?? null,
            cell: (row) => {
                const testId = `${row.added ? `${cellPrefix}-ref` : cellPrefix}-${id}`;
                // The lab's D371, and a benchmark the reader holds: the benchmark's own beta and
                // correlation are not missing figures but inapplicable — measured against itself
                // they would be 1 by construction — so its dash says so, in the developer's words.
                if (row.isReference && (id === 'beta' || id === 'correlation')) {
                    return figureCell(`<span class="${VALUE_CLASS}" data-testid="${testId}" data-measured="false" data-reference="true">\u2014</span>`, false, () => $t('risk.assetSet.levels.l3.referenceItself'));
                }
                // A benchmark nobody holds has no weight in the portfolio, and its dash says that.
                if (id === 'weight' && row.added && row.role === 'benchmark') {
                    return figureCell(`<span class="${VALUE_CLASS}" data-testid="${testId}" data-measured="false" data-held="false">\u2014</span>`, false, () => $t('risk.levels.l3.table.notHeld'));
                }
                const raw = figure(row);
                // `undefined`: not calculated here at all — a plain dash, with no tooltip to claim a
                // measurement was attempted (developer's review of 06/10/2026: «togli il tooltip»).
                // Since Risk's k6 the backend sends every per-holding ratio, so this is left for an
                // answer that predates those fields; a holding k6 could not measure is `null`.
                if (raw === undefined && RATIO_COLUMNS.has(id)) {
                    return {type: 'html', html: `<span class="${VALUE_CLASS}" data-testid="${testId}" data-measured="false" data-calculated="false">\u2014</span>`};
                }
                const value = raw ?? null;
                return figureCell(`<span class="${VALUE_CLASS}" data-testid="${testId}" data-measured="${value !== null}">${value === null ? '\u2014' : text(value)}</span>`, value !== null, () => $t('risk.assetSet.levels.blankNote'));
            },
        };
    }

    /**
     * The lab's asset column (`assetSetTable`), whose cell a reference row replaces with its own.
     * Not pinned here (developer's review of 06/10/2026: «non li volevo fissi»): the names scroll
     * with their figures.
     */
    let nameColumn = $derived.by<ColumnDef<T>>(() => {
        const base = assetNameColumn<T>(
            () => $t('risk.assetSet.levels.asset'),
            () => assetIcons,
            cellPrefix,
        );
        return {...base, pinned: undefined, cell: (row: T) => (row.role ? {type: 'html', html: referenceNameHtml(row, row.role)} : base.cell(row))};
    });

    let columns = $derived<ColumnDef<T>[]>([
        nameColumn,
        ...(capabilities.weight
            ? [
                  valueColumn(
                      'weight',
                      (row) => row.weight,
                      (value) => formatShare(value, 1),
                  ),
              ]
            : []),
        valueColumn('volatility', (row) => row.volatility, percent),
        valueColumn('expectedReturn', (row) => row.expectedReturn, signedPercent),
        ...(capabilities.ratios ? [valueColumn('sortino', (row) => row.sortino, formatRatio), valueColumn('sharpe', (row) => row.sharpe, formatRatio)] : []),
        // Beta and correlation need a benchmark, so their columns exist only where one applies.
        ...(capabilities.benchmark ? [valueColumn('beta', (row) => row.beta, formatRatio), valueColumn('correlation', (row) => row.correlation, formatRatio)] : []),
    ]);

    let selectedRowId = $state<string | null>(null);
    /** The selected row's dot (`pointIdOf`), so the chart marks what the table selected. */
    let selectedPointId = $derived.by(() => {
        if (selectedRowId === null) return null;
        const row = rows.find((candidate) => rowIdOf(candidate) === selectedRowId);
        return row ? pointIdOf(row) : null;
    });

    /** A dot selects its row (`rowIdForPoint`); a dot with no row selects nothing. */
    function selectFromPoint(pointId: string): void {
        const rowId = rowIdForPoint(pointId, rows);
        if (rowId === null) return;
        tableRef?.toggleRowSelectionById(rowId);
    }

    let tableWrapper: HTMLDivElement | undefined = $state();

    // The cells are HTML strings, so the name spans are reached through the wrapper; the scan
    // re-attaches whenever the table re-renders its rows.
    $effect(() => {
        if (!tableWrapper) return;
        return attachOverflowMarqueeToDescendants(tableWrapper);
    });
</script>

<div class="space-y-4">
    {#if title}
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-200">{title}</h4>
    {/if}

    <div bind:this={tableWrapper} class="risk-return-table" data-testid="{testIdPrefix}-table" data-row-count={assetRowCount} data-reference-count={addedRowCount}>
        <DataTable
            bind:this={tableRef}
            data={orderedRows}
            {columns}
            getRowId={rowIdOf}
            getRowClass={rowTint}
            {storageKey}
            enableSelection={true}
            selectionMode="single"
            onSelectionChange={(ids) => (selectedRowId = ids.length > 0 ? ids[0] : null)}
            enableActions={false}
            enableColumnFilters={false}
            enablePagination={false}
            enableContextMenu={false}
        />
    </div>

    {#if afterTable}
        {@render afterTable()}
    {/if}

    {#if hasScatter}
        <div data-testid="{testIdPrefix}-risk-return">
            <ScatterChart {points} {labels} {riskFreeRate} {height} testId="{testIdPrefix}-scatter" emptyLabel={$t('risk.states.unavailable')} selectedId={selectedPointId} onpointclick={selectFromPoint} />
            <!-- One idea per line, one under the other (developer's review of 05/10/2026: the
                 paragraph was right but read as a wall), each said only where it applies
                 (`riskReturnNotes`). The axis title alone cannot carry the return's line: on a
                 very volatile asset the average return and the one actually lived through differ
                 by tens of percentage points, and a reader seeing "-11%" beside a coin that halved
                 will not guess that the word "average" was the warning — so the warning is the
                 part in bold. -->
            <ul class="mt-1 space-y-0.5 text-xs text-gray-500 dark:text-gray-400" data-testid="{testIdPrefix}-scatter-note">
                {#each notes as note (note)}
                    {#if note === 'outside'}
                        <li data-testid="{testIdPrefix}-scatter-outside">
                            {$t('risk.levels.l3.scatter.notes.outside')}
                            {#if outsideShown.cash}
                                <span data-testid="{testIdPrefix}-scatter-cash"><span aria-hidden="true">💰</span> {$t('risk.levels.l3.scatter.notes.outsideCash', {values: {share: formatShare(outside?.cash, 0)}})}</span>
                            {/if}
                            {#if outsideShown.cash && outsideShown.unpriced}<span aria-hidden="true">·</span>{/if}
                            {#if outsideShown.unpriced}
                                <span data-testid="{testIdPrefix}-scatter-unpriced"><span aria-hidden="true">🏷️</span> {$t('risk.levels.l3.scatter.notes.outsideUnpriced', {values: {share: formatShare(outside?.unpriced, 0)}})}</span>
                            {/if}
                        </li>
                    {:else if note === 'above'}
                        <li>{$t('risk.levels.l3.scatter.notes.above')}</li>
                    {:else if note === 'return'}
                        <li>{$t('risk.levels.l3.scatter.notes.expected')} <strong class="font-semibold text-gray-700 dark:text-gray-200">{$t('risk.levels.l3.scatter.notes.expectedWarning')}</strong></li>
                    {:else if note === 'priceOnly'}
                        <li data-testid="{testIdPrefix}-scatter-price-only">{$t('risk.levels.l3.scatter.notes.priceOnly')}</li>
                    {:else if note === 'line'}
                        <li class="flex items-start gap-1" data-testid="{testIdPrefix}-scatter-line" data-anchor={lineAnchor}>
                            <span>{$t(lineAnchor === 'benchmark' ? 'risk.levels.l3.scatter.notes.lineBenchmark' : 'risk.levels.l3.scatter.notes.line')}</span>
                            <DocsLink path="financial-theory/technical-analysis/risk-metrics/benchmark-selection/#the-risk-return-line" label={$t('risk.levels.l3.scatter.notes.lineDocs')} size={12} testId="{testIdPrefix}-scatter-line-docs" />
                        </li>
                    {:else if note === 'size'}
                        <li>{$t('risk.levels.l3.scatter.notes.size')}</li>
                    {/if}
                {/each}
            </ul>
        </div>
    {/if}
</div>

<style>
    /*
     * The table paints every row white (`DataTable`: `tbody tr`, scoped, specificity 0,2,2), so a
     * utility class on the row loses and a reference row looked like any other (developer's review
     * of 06/10/2026). These selectors carry 0,2,4 — above the white rows, below the table's own
     * hover and selection (0,3,2), which still show over a tinted row. The hues are the dots'
     * (`colorForRole`): sky for the portfolio, amber for the benchmark.
     */
    :global(div.risk-return-table table tbody tr.risk-return-row-portfolio) {
        background: rgb(2 132 199 / 0.1);
    }

    :global(div.risk-return-table table tbody tr.risk-return-row-benchmark) {
        background: rgb(217 119 6 / 0.1);
    }

    :global(.dark div.risk-return-table table tbody tr.risk-return-row-portfolio) {
        background: rgb(56 189 248 / 0.14);
    }

    :global(.dark div.risk-return-table table tbody tr.risk-return-row-benchmark) {
        background: rgb(251 191 36 / 0.14);
    }

    /*
     * The selected row: the table's green, lighter (developer's review of 06/10/2026: «la riga
     * selezionata verde va bene, ma serve sia più trasparente»). 0,3,4 here, above the table's own
     * selection (0,3,2) — for this table only.
     */
    :global(div.risk-return-table table tbody tr.clickable.selected) {
        background: rgb(34 197 94 / 0.12);
    }

    :global(.dark div.risk-return-table table tbody tr.clickable.selected) {
        background: rgb(74 222 128 / 0.14);
    }

    /*
     * The asset cell caps its content at 14rem (`assetSetTable`), for an `auto` table that would
     * otherwise widen to the longest name. This table is `fixed`: the column is as wide as the
     * reader made it, and a name may use all of it.
     */
    :global(div.risk-return-table td [data-testid$='-name']) {
        max-width: none;
    }
</style>
