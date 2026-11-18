<script lang="ts">
    /**
     * «How did each one move?» — the positive twin of «How much did each one hurt?», asked of each asset (RN-19,
     * developer's decision of 12/11/2026: a table of its own in the lab, made with `DataTable`, beside the loss table).
     *
     * Same shape as its twin (`AssetSetLossComparisonSection`): the assets are the rows, the measures the columns, the
     * selection's order until the reader sorts, no money, no ranking, the project's table with each column explaining
     * itself in the tooltip of its title, the frame's manual icon for the documentation. Every figure is read from L1°'s
     * own request — its own KPI instance, the monthly VaR's best window, the drawdown's largest rally — so a row never
     * mixes two calendars, and a benchmark chosen for L3° never moves it.
     *
     * The measures are the ones fixed on 12/11 («Le misure, fissate»): the best day, the best 30 days, the largest rally,
     * gains against losses, the positive days and the semi-deviation; the average up and down day and the longest positive
     * streak (Q21 c) start hidden, a click away in the column toggle, and so do «below the peak, on average» (ADD) and the
     * extreme days (the consultant, 17/11: the lab is those two measures' only reader). A blank says why: the backend's
     * warning naming the asset when there is one (no gaining day, no losing day, no day below the target, a series that
     * does not move), the table's blank note otherwise.
     */
    import {_ as t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import {RISK_PAGE_SIZE, RISK_PAGE_SIZES} from './riskTablePaging';
    import type {ColumnDef} from '$lib/components/table/types';
    import {attachOverflowMarqueeToDescendants} from '$lib/actions/scrollOnOverflow';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {formatDay, formatDayRange} from '$lib/utils/core/formatAxisDate';
    import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';
    import {SIGN_TEXT} from '$lib/theme/toneClasses';

    import {buildAssetSetMoveRows, type AssetSetMoveColumn, type AssetSetMoveRow} from './assetSetLevels';
    import {assetNameColumn, figureCell} from './assetSetTable';
    import {headerFontsSettled} from './headerFonts.svelte';
    import {headerWidth, measureHeaderTitle} from './riskReturnLevel';
    import {usedRiskFreeRate, withRateKey} from './riskFreeRate';

    interface Props {
        assetIds: number[];
        assetLabels: ReadonlyMap<number, string>;
        assetIcons: ReadonlyMap<number, string>;
        /** The KPI of L1°'s request (`ASSET_SET_MOVE_KPI_INSTANCE`): one calendar with the two below. */
        kpi: RiskAnalyticResult | null;
        monthlyVar: RiskAnalyticResult | null;
        drawdown: RiskAnalyticResult | null;
        loading?: boolean;
        failed?: boolean;
        discarded?: boolean;
        onretry?: () => void;
        /** The table's instance, for the column toggle beside the frame's manual icon; set only while the table is shown. */
        tableRef?: DataTable<AssetSetMoveRow>;
    }

    let {assetIds, assetLabels, assetIcons, kpi, monthlyVar, drawdown, loading = false, failed = false, discarded = false, onretry, tableRef = $bindable()}: Props = $props();

    let rows = $derived(buildAssetSetMoveRows(assetIds, assetLabels, kpi, monthlyVar, drawdown));
    let hasAnyFigure = $derived(rows.some((row) => row.bestDay !== null || row.bestMonth !== null || row.rally !== null || row.omega !== null));

    type MoveColumnId = 'bestDay' | 'bestMonth' | 'rally' | 'omega' | 'positiveShare' | 'downsideDeviation' | 'meanUpDown' | 'streak' | 'averageDrawdown' | 'extremeDays';

    /** A signed return, with the typographic minus, as the loss table draws its figures; a zero has no sign (no rise, no fall). */
    function signed(fraction: number): string {
        const text = formatPercent(Math.abs(fraction), {scale: 100, signed: false, digits: 1});
        return fraction === 0 ? text : `${fraction < 0 ? '−' : '+'}${text}`;
    }

    function percent(fraction: number): string {
        return formatPercent(fraction, {scale: 100, signed: false, digits: 1});
    }

    /** The gain tone for a rise, the loss tone for a fall, none for a zero: one sentiment per sign, never one asset against another. */
    function tone(fraction: number): string {
        if (fraction === 0) return 'tabular-nums text-lf-secondary';
        return `tabular-nums ${fraction < 0 ? SIGN_TEXT.riskTable.loss : SIGN_TEXT.riskTable.gain}`;
    }

    /** A value column's width: its title's, measured in the reader's language — the twin's rule, shared. */
    function titleWidth(id: MoveColumnId): number {
        void headerFontsSettled();
        return headerWidth($t(`risk.assetSet.levels.move.columns.${id}`), measureHeaderTitle);
    }

    function cellHtml(column: string, measured: boolean, text: string, classes: string): string {
        return `<span class="${classes}" data-testid="risk-asset-set-move-${column}" data-measured="${measured}">${text}</span>`;
    }

    function detailHtml(column: string, line: string): string {
        return line ? `<span class="block text-[10px] font-normal text-lf-muted" data-testid="risk-asset-set-move-${column}-detail">${escapeHtml(line)}</span>` : '';
    }

    /** What a dash means: the backend's reasons for this asset and these columns when it named them, the table's note otherwise. */
    function blankFor(row: AssetSetMoveRow, columns: readonly AssetSetMoveColumn[] = []): () => string {
        const reasons = [...new Set(columns.map((column) => row.reasons[column]).filter((key): key is string => key !== undefined))];
        return () => (reasons.length > 0 ? reasons.map((key) => $t(key)).join(' ') : $t('risk.assetSet.levels.blankNote'));
    }

    /** The halves of the average day ± that are blank: a cell with one half drawn still owes the reader the other's reason. */
    function blankHalves(row: AssetSetMoveRow): AssetSetMoveColumn[] {
        return [row.meanUp === null ? 'meanUp' : null, row.meanDown === null ? 'meanDown' : null].filter((half): half is AssetSetMoveColumn => half !== null);
    }

    /** The columns that count from the risk-free rate the KPI was charged (RN-21): their helps say so when there is one. */
    const RATE_COLUMNS: ReadonlySet<MoveColumnId> = new Set<MoveColumnId>(['omega', 'downsideDeviation']);

    function column(
        id: MoveColumnId,
        value: (row: AssetSetMoveRow) => number | null,
        render: (row: AssetSetMoveRow, value: number) => {text: string; classes: string; detail?: string},
        options: {hidden?: boolean; reason?: AssetSetMoveColumn; halves?: (row: AssetSetMoveRow) => AssetSetMoveColumn[]} = {},
    ): ColumnDef<AssetSetMoveRow> {
        const width = titleWidth(id);
        return {
            id,
            header: () => $t(`risk.assetSet.levels.move.columns.${id}`),
            headerTooltip: () => $t(RATE_COLUMNS.has(id) ? withRateKey(`risk.assetSet.levels.move.columnHelp.${id}`, usedRiskFreeRate(kpi)) : `risk.assetSet.levels.move.columnHelp.${id}`),
            type: 'number',
            align: 'right',
            width,
            minWidth: width,
            filterable: false,
            hiddenByDefault: options.hidden === true,
            getValue: value,
            cell: (row) => {
                const figure = value(row);
                const blankHalvesOfRow = options.halves?.(row) ?? [];
                if (figure === null) return figureCell(cellHtml(id, false, '—', 'tabular-nums text-lf-muted'), false, blankFor(row, options.halves ? blankHalvesOfRow : options.reason ? [options.reason] : []));
                const drawn = render(row, figure);
                const html = cellHtml(id, true, `${escapeHtml(drawn.text)}${detailHtml(id, drawn.detail ?? '')}`, drawn.classes);
                // A figure with a half dash in it explains that dash, as a whole dash would (Q20).
                return figureCell(html, blankHalvesOfRow.length === 0, blankFor(row, blankHalvesOfRow));
            },
        };
    }

    /**
     * The columns: the three best moments first — a day, a month, the whole window, the loss table's increasing
     * horizons — then the shape of the days; the four hidden ones last (Q21 c, then ADD and the extreme days). Derived, so the widths follow the
     * reader's language when it changes.
     */
    let columns = $derived<ColumnDef<AssetSetMoveRow>[]>([
        assetNameColumn<AssetSetMoveRow>(
            () => $t('risk.assetSet.levels.asset'),
            () => assetIcons,
            'risk-asset-set-move',
        ),
        column(
            'bestDay',
            (row) => row.bestDay,
            (row, value) => ({text: signed(value), classes: tone(value), detail: row.bestDayDate ? formatDay(row.bestDayDate) : ''}),
            {reason: 'bestDay'},
        ),
        column(
            'bestMonth',
            (row) => row.bestMonth?.gain ?? null,
            (row, value) => ({text: signed(value), classes: tone(value), detail: row.bestMonth ? formatDayRange(row.bestMonth.from, row.bestMonth.to) : ''}),
        ),
        column(
            'rally',
            (row) => row.rally?.gain ?? null,
            (row, value) => ({
                text: signed(value),
                classes: tone(value),
                detail: row.rally?.from && row.rally.to ? `${formatDayRange(row.rally.from, row.rally.to)}${row.rally.days !== null ? ` · ${$t('risk.assetSet.levels.l1.lastedDays', {values: {days: row.rally.days}})}` : ''}` : '',
            }),
        ),
        column(
            'omega',
            (row) => row.omega,
            (_row, value) => ({text: $t('risk.assetSet.levels.move.times', {values: {value: value.toFixed(2)}}), classes: 'tabular-nums text-lf-secondary'}),
            {reason: 'omega'},
        ),
        column(
            'positiveShare',
            (row) => row.positiveShare,
            (_row, value) => ({text: percent(value), classes: 'tabular-nums text-lf-secondary'}),
        ),
        column(
            'downsideDeviation',
            (row) => row.downsideDeviation,
            (_row, value) => ({text: percent(value), classes: 'tabular-nums text-lf-secondary'}),
        ),
        column(
            'meanUpDown',
            (row) => row.meanUp ?? row.meanDown,
            (row) => ({text: `${row.meanUp !== null ? signed(row.meanUp) : '—'} · ${row.meanDown !== null ? signed(row.meanDown) : '—'}`, classes: 'tabular-nums text-lf-secondary'}),
            {hidden: true, halves: blankHalves},
        ),
        column(
            'streak',
            (row) => row.streak?.days ?? null,
            (row, value) => ({text: $t('risk.assetSet.levels.move.days', {values: {days: value}}), classes: 'tabular-nums text-lf-secondary', detail: row.streak ? formatDayRange(row.streak.from, row.streak.to) : ''}),
            {hidden: true, reason: 'streak'},
        ),
        // Below the peak on average: never a gain — a fall in the loss tone, a never-fallen asset a plain 0.
        column(
            'averageDrawdown',
            (row) => row.averageDrawdown,
            (_row, value) => ({text: signed(value), classes: tone(value)}),
            {hidden: true},
        ),
        column(
            'extremeDays',
            (row) => row.extremeDays,
            (_row, value) => ({text: $t('risk.assetSet.levels.move.times', {values: {value: value.toFixed(1)}}), classes: 'tabular-nums text-lf-secondary'}),
            {hidden: true, reason: 'extremeDays'},
        ),
    ]);

    let tableWrapper: HTMLDivElement | undefined = $state();

    $effect(() => {
        if (!tableWrapper) return;
        return attachOverflowMarqueeToDescendants(tableWrapper);
    });
</script>

<div class="space-y-3" data-testid="risk-asset-set-move">
    <p class="text-xs text-lf-muted">{$t('risk.assetSet.levels.move.description')}</p>

    {#if failed}
        <div class="py-4 text-center" data-testid="risk-asset-set-move-error">
            <p class="text-sm text-lf-danger">{$t('risk.states.loadFailed')}</p>
            <button type="button" class="mt-2 rounded-md border border-lf-input px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover" onclick={() => onretry?.()} data-testid="risk-asset-set-move-retry">{$t('common.retry')}</button>
        </div>
    {:else if loading && !hasAnyFigure}
        <div class="h-32 animate-pulse rounded-lg bg-lf-panel" data-testid="risk-asset-set-move-loading"></div>
    {:else if discarded && !hasAnyFigure}
        <div class="py-4 text-center" data-testid="risk-asset-set-move-discarded">
            <button type="button" class="mt-2 rounded-md border border-lf-input px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover" onclick={() => onretry?.()} data-testid="risk-asset-set-move-retry">{$t('common.retry')}</button>
        </div>
    {:else if rows.length === 0}
        <p class="py-4 text-center text-sm text-lf-muted" data-testid="risk-asset-set-move-empty">{$t('risk.states.empty')}</p>
    {:else}
        <div bind:this={tableWrapper} data-testid="risk-asset-set-move-table" data-row-count={rows.length}>
            <!-- Drawn again once the page's fonts are in, as the twin (RN-09): column widths are taken when it is created. -->
            {#key headerFontsSettled()}
                <DataTable
                    bind:this={tableRef}
                    data={rows}
                    {columns}
                    getRowId={(row) => String(row.assetId)}
                    storageKey="risk-asset-set-move"
                    enableSelection={false}
                    selectionMode="none"
                    enableActions={false}
                    enableColumnFilters={false}
                    defaultPageSize={RISK_PAGE_SIZE}
                    pageSizeOptions={RISK_PAGE_SIZES}
                    enableContextMenu={false}
                />
            {/key}
        </div>
    {/if}
</div>
