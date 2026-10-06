<script lang="ts">
    /**
     * L1° for Asset Global — "how much can it hurt?", asked of each asset.
     *
     * **The reduction is a transposition, not a smaller L1.** The portfolio's L1
     * takes one scope and produces three figures on one increasing scale: a bad
     * day, a bad month, the worst fall. Here the scale becomes the *columns* and
     * the assets become the *rows*, so the reader compares instruments along a
     * ruler instead of reading one instrument's ruler. That is why this is a
     * component of its own and not `L1HowMuchItHurts` with a flag: a prop cannot
     * change the arity of the input, and a boolean that switches arity is two
     * components sharing a name.
     *
     * **No money, and not by suppression.** `assetSetLevels` has no `currency`
     * parameter and returns no amount, so there is no euro figure to remember to
     * hide. An asset set has no weights; an amount here would be an arithmetic
     * claim about a portfolio the reader never described.
     *
     * **Never a ranking.** The table opens in the order of the selection and is
     * sorted only when the reader clicks a column's title — never ordered by
     * verdict by the system — and no cell is coloured relative to its
     * neighbours. `03-mappa-livelli-pagine` gives this page "a comparison, never
     * a judgement", and a badge saying which asset is "worst" is a judgement
     * wearing a comparison's clothes. The one colour used is the same negative
     * sentiment the portfolio's L1 gives *every* loss, which distinguishes a fall
     * from a rise and not one asset from another.
     *
     * **The project's table, not a hand-written one** (the developer's review,
     * 30/09). The rows are a `DataTable`, so sorting by any column comes with it,
     * and each figure's column explains itself in the tooltip of its title. The
     * titles carry no link: the manual icon of the frame above is the way to the
     * documentation, for the whole card. The asset cell is the Assets list's —
     * the type icon and the name on one line, scrolling when it does not fit —
     * and the name is escaped, because the table renders its cells as HTML.
     *
     * **A selected asset always has a row.** Rows come from the selection and the
     * cells are nullable. An analytic that could not measure an asset — too short
     * a series — leaves blanks with the reason in the section header, because a
     * missing row would read as "not selected" rather than "not measurable".
     */
    import {_ as t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {attachOverflowMarqueeToDescendants} from '$lib/actions/scrollOnOverflow';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

    import {buildAssetSetHurtRows, type AssetSetHurtRow} from './assetSetLevels';
    import {assetNameColumn, figureCell} from './assetSetTable';
    import {headerWidth, measureHeaderTitle} from './riskReturnLevel';

    interface Props {
        assetIds: number[];
        assetLabels: ReadonlyMap<number, string>;
        /**
         * Each asset's icon URL, by id, resolved by the panel the way the selection's
         * chips resolve it: the asset's own icon, else its type's. An asset without
         * one shows its name alone.
         */
        assetIcons: ReadonlyMap<number, string>;
        dailyVar: RiskAnalyticResult | null;
        monthlyVar: RiskAnalyticResult | null;
        drawdown: RiskAnalyticResult | null;
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
         * manual icon. Set only while the table is on screen: the states without one
         * (loading, failure, discarded answer, empty) leave it unset, and the toggle goes.
         */
        tableRef?: DataTable<AssetSetHurtRow>;
    }

    let {assetIds, assetLabels, assetIcons, dailyVar, monthlyVar, drawdown, loading = false, failed = false, discarded = false, onretry, tableRef = $bindable()}: Props = $props();

    let rows = $derived(buildAssetSetHurtRows(assetIds, assetLabels, dailyVar, monthlyVar, drawdown));
    let hasAnyFigure = $derived(rows.some((row) => row.badDay !== null || row.badMonth !== null || row.worstFall !== null));

    /**
     * A loss drawn as a fall, with the typographic minus.
     *
     * `formatPercent` emits an ASCII hyphen and the level nets assert U+2212, so
     * the sign is prefixed here rather than delegated. Both glyphs draw as a
     * short stroke, so a mismatch is invisible on screen and surfaces only as a
     * failing string comparison — which is the worst place to discover it.
     *
     * The magnitude is taken as an absolute value because the two contracts
     * disagree on sign by design: the VaR pair arrives positive (`ge=0`), the
     * drawdown pair negative (`le=0`). Normalising in the helper would have
     * hidden which contract a number came from; normalising here, at the last
     * moment before it is drawn, does not.
     */
    function fall(fraction: number): string {
        return `\u2212${formatPercent(Math.abs(fraction), {scale: 100, signed: false, digits: 1})}`;
    }

    /** A rise drawn as a rise: the recovery a fall demands is a gain. */
    function rise(fraction: number): string {
        return `+${formatPercent(fraction, {scale: 100, signed: false, digits: 1})}`;
    }

    /**
     * The figure as drawn, for sorting. A loss is drawn negative whatever sign its
     * contract gives it, so an ascending sort puts the largest loss first; an
     * unmeasured cell stays `null`, which the table always sorts last.
     */
    function drawnLoss(fraction: number | null): number | null {
        return fraction === null ? null : -Math.abs(fraction);
    }

    const LOSS_CLASS = 'tabular-nums text-red-600 dark:text-red-400';

    type LossColumn = 'badDay' | 'badMonth' | 'worstFall' | 'currentFall' | 'toPeak';

    /**
     * A value column's width: its title's, measured in the reader's language — L3°'s rule
     * (`headerWidth` in `riskReturnLevel`), shared rather than copied, so the two tables open
     * the same way. Used as the width and as the minimum: the table is laid out `fixed`
     * (the developer's review, 06/10: under `auto` a dragged width did not hold), so a column
     * keeps the width the reader drags, and no drag narrows it below its title. DataTable
     * draws its titles upper-case on one line; a width sized for Italian once let a French
     * title spill out of its column (the developer's review, 30/09).
     */
    function titleWidth(id: LossColumn): number {
        return headerWidth($t(`risk.assetSet.levels.l1.columns.${id}`), measureHeaderTitle);
    }

    function cellHtml(column: string, measured: boolean, text: string, classes: string, extra = ''): string {
        return `<span class="${classes}" data-testid="risk-asset-set-l1-${column}" data-measured="${measured}"${extra}>${text}</span>`;
    }

    /** What a dash means, said on the dash itself rather than in a note under the table. */
    const blankExplanation = () => $t('risk.assetSet.levels.blankNote');

    function lossColumn(id: 'badDay' | 'badMonth' | 'currentFall', figure: (row: AssetSetHurtRow) => number | null): ColumnDef<AssetSetHurtRow> {
        const width = titleWidth(id);
        return {
            id,
            header: () => $t(`risk.assetSet.levels.l1.columns.${id}`),
            headerTooltip: () => $t(`risk.assetSet.levels.l1.columnHelp.${id}`),
            type: 'number',
            align: 'right',
            width,
            minWidth: width,
            filterable: false,
            getValue: (row) => drawnLoss(figure(row)),
            cell: (row) => {
                const value = figure(row);
                return figureCell(cellHtml(id, value !== null, value === null ? '\u2014' : fall(value), LOSS_CLASS), value !== null, blankExplanation);
            },
        };
    }

    /**
     * The columns, in the order that carries the argument.
     *
     * Increasing in horizon from left to right — one day, one month, the whole
     * window — because the defect the redesign exists to cure was a one-day loss
     * printed beside a multi-year drawdown with no declared change of scale. The
     * reader summed them. Transposing the table does not make that safe; only the
     * ordering and the headings do. Sorting reorders the rows, never the columns.
     *
     * Derived, so the widths follow the reader's language when it changes.
     */
    let columns = $derived<ColumnDef<AssetSetHurtRow>[]>([
        // The asset column is shared with L3° (`assetSetTable`): icon, one-line name, by-name order.
        assetNameColumn<AssetSetHurtRow>(
            () => $t('risk.assetSet.levels.asset'),
            () => assetIcons,
            'risk-asset-set-l1',
        ),
        lossColumn('badDay', (row) => row.badDay),
        lossColumn('badMonth', (row) => row.badMonth),
        {
            id: 'worstFall',
            header: () => $t('risk.assetSet.levels.l1.columns.worstFall'),
            headerTooltip: () => $t('risk.assetSet.levels.l1.columnHelp.worstFall'),
            type: 'number',
            align: 'right',
            width: titleWidth('worstFall'),
            minWidth: titleWidth('worstFall'),
            filterable: false,
            getValue: (row) => drawnLoss(row.worstFall),
            // The deepest fall carries its duration as a second line: it refines one
            // figure rather than standing as one more risk, exactly as the portfolio's
            // L1 keeps its acquired measures as sub-rows instead of promoting them to cards.
            cell: (row) => {
                const lastedHtml =
                    row.worstFall !== null && row.worstFallDays !== null
                        ? `<span class="block text-[10px] font-normal text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-l1-worstFall-days">${escapeHtml($t('risk.assetSet.levels.l1.lastedDays', {values: {days: row.worstFallDays}}))}</span>`
                        : '';
                const text = row.worstFall === null ? '\u2014' : fall(row.worstFall);
                return figureCell(cellHtml('worstFall', row.worstFall !== null, `${text}${lastedHtml}`, LOSS_CLASS, ` data-recovery="${escapeHtml(row.recovery ?? '')}"`), row.worstFall !== null, blankExplanation);
            },
        },
        lossColumn('currentFall', (row) => row.currentFall),
        {
            // The number that teaches the asymmetry: a 50% fall needs a +100% rise, not
            // a +50% one. Drawn as a gain, because it is one.
            id: 'toPeak',
            header: () => $t('risk.assetSet.levels.l1.columns.toPeak'),
            headerTooltip: () => $t('risk.assetSet.levels.l1.columnHelp.toPeak'),
            type: 'number',
            align: 'right',
            width: titleWidth('toPeak'),
            minWidth: titleWidth('toPeak'),
            filterable: false,
            getValue: (row) => row.toPeak,
            cell: (row) => figureCell(cellHtml('toPeak', row.toPeak !== null, row.toPeak === null ? '\u2014' : rise(row.toPeak), 'tabular-nums text-gray-600 dark:text-gray-300'), row.toPeak !== null, blankExplanation),
        },
    ]);

    let tableWrapper: HTMLDivElement | undefined = $state();

    // The cells are HTML strings, so a `use:` action cannot reach the name spans: the
    // wrapper is scanned instead, as the Assets list does, and the scan re-attaches
    // whenever the table re-renders its rows (a sort, a new answer).
    $effect(() => {
        if (!tableWrapper) return;
        return attachOverflowMarqueeToDescendants(tableWrapper);
    });
</script>

<div class="space-y-3" data-testid="risk-asset-set-l1">
    <p class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.assetSet.levels.l1.description')}</p>

    {#if failed}
        <div class="py-4 text-center" data-testid="risk-asset-set-l1-error">
            <p class="text-sm text-red-600 dark:text-red-400">{$t('risk.states.loadFailed')}</p>
            <button type="button" class="mt-2 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700" onclick={() => onretry?.()} data-testid="risk-asset-set-l1-retry">{$t('common.retry')}</button>
        </div>
    {:else if loading && !hasAnyFigure}
        <div class="h-32 animate-pulse rounded-lg bg-gray-100 dark:bg-slate-700" data-testid="risk-asset-set-l1-loading"></div>
    {:else if discarded && !hasAnyFigure}
        <!-- The frame carries the sentence (`answer_discarded`); the body carries the cure. -->
        <div class="py-4 text-center" data-testid="risk-asset-set-l1-discarded">
            <button type="button" class="mt-2 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700" onclick={() => onretry?.()} data-testid="risk-asset-set-l1-retry">{$t('common.retry')}</button>
        </div>
    {:else if rows.length === 0}
        <p class="py-4 text-center text-sm text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-l1-empty">{$t('risk.states.empty')}</p>
    {:else}
        <div bind:this={tableWrapper} data-testid="risk-asset-set-l1-table" data-row-count={rows.length}>
            <DataTable bind:this={tableRef} data={rows} {columns} getRowId={(row) => String(row.assetId)} storageKey="risk-asset-set-l1" enableSelection={false} selectionMode="none" enableActions={false} enableColumnFilters={false} enablePagination={false} enableContextMenu={false} />
        </div>
    {/if}
</div>
