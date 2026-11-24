<!--
  The table «Maximum acceptable cost» of the Rebalancer's Strategy step (F3a of project 67, step 10a; M30–M33).

  How much the plan may spend at most, in fees and taxes, to put back money that is in the wrong place, per fidelity level.
  The figures are the page's own (`acceptableCost.ts`, R1-F (b) of project 67), on the preview's total and the λ of its
  three levels: a level chosen or a figure typed changes them at once, with no call. The «Custom» column is there only
  while that choice is active with a λ (M32); «Target first» has no column, the line under the table says why (M33).
  While the preview waits the figures stay, muted; after a failure the table goes and a line says why. Every figure
  derives from the user's total: masked in privacy mode.

  G6d (the developer's call): each column's minimum width fits its widest cell, so our `DataTable`, which cuts a cell
  wider than its column, never cuts one; a phone scrolls sideways. A header never wraps and widens its column by itself.
  The width is measured on the very text the cell shows, in the page's font; where no canvas exists (jsdom) a generous
  estimate stands in. The planner's columns button moves and hides the columns, saved with the table's `storageKey`.
-->
<script lang="ts">
    import {MediaQuery} from 'svelte/reactivity';
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import type {DraftFidelity} from '../draft.svelte';
    import {formatExactMoneyCompact, formatExactMoneyPlain} from '../format';
    import type {PlannerPreview, PreviewMoney} from '../preview.svelte';
    import {acceptableCostTable, type AcceptableCostRow} from '../acceptableCost';
    import {fidelityName} from '../strategyText';
    import TableColumns from '../shared/TableColumns.svelte';
    import {BADGE, HINT, SECTION_TITLE} from '../ui';
    import {getPlannerProfile, storageKey, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    interface Props {
        /** The scenario preview (step 8): the total and the λ of the levels the table is counted on. */
        preview: PlannerPreview | null;
        /** The draft's fidelity: the «Custom» column shows only while it is the choice. */
        fidelity: DraftFidelity;
    }

    let {preview, fidelity}: Props = $props();

    const T = 'tools.portfolioRebalancer.planner.strategy.table';
    /** On a phone (the table's own 768 px breakpoint) the headers are short and the cells drop «up to» (mockup screen 6). */
    const phone = new MediaQuery('max-width: 768px');

    type Level = 'cost_aware' | 'balanced' | 'faithful' | 'custom';
    interface Row {
        id: string;
        index: number;
        row: AcceptableCostRow;
    }

    const numbers = $derived(preview?.numbers ?? null);
    /** The draft's λ for the «Custom» column: only while that choice is active. */
    const customLambda = $derived(fidelity.kind === 'custom' ? fidelity.lambda : null);
    const table = $derived(numbers?.fidelity_level_weights ? acceptableCostTable(numbers.total, numbers.fidelity_level_weights, customLambda) : null);
    const stale = $derived(preview?.stale ?? false);
    const rows = $derived<Row[]>((table ?? []).map((row, index) => ({id: String(index), index, row})));
    const showCustom = $derived((table?.[0]?.custom ?? null) !== null);
    const totalText = $derived(numbers ? formatExactMoneyPlain(numbers.total) : null);

    let tableRef: DataTable<Row> | undefined = $state(undefined);

    /** A cell's text, the one the cell shows and the one its column is sized on. */
    function cellText(level: Level | 'misplaced', amount: PreviewMoney | null): string {
        // G6-1: two significant digits and the symbol alone; the currency is named once, in the line above the table.
        const figure = amount ? formatExactMoneyCompact(amount) : '';
        return level === 'misplaced' || phone.current || figure === '' ? figure : $t(`${T}.upTo`, {values: {amount: figure}});
    }

    /** A canvas to measure text on, made once; `null` where none exists (jsdom). */
    let ruler: OffscreenCanvasRenderingContext2D | null | undefined;

    /**
     * A text's width in pixels at `fontPx` and `weight`, in the page's font. Without a canvas, `em` per character, a factor
     * above Inter's widest common glyphs (digits, `€`), so the stand-in errs wide.
     */
    function textWidth(text: string, fontPx: number, weight: number, em: number): number {
        if (ruler === undefined) ruler = typeof OffscreenCanvas === 'undefined' ? null : new OffscreenCanvas(1, 1).getContext('2d');
        if (!ruler) return Math.ceil(text.length * fontPx * em);
        ruler.font = `${weight} ${fontPx}px ${getComputedStyle(document.documentElement).fontFamily}`;
        // The cells draw `tabular-nums`, which a canvas cannot: every digit is measured as a «0», as wide as a tabular one.
        return Math.ceil(ruler.measureText(text.replace(/\d/g, '0')).width);
    }

    /** The cell's padding (0.5 rem a side), the shade's (`px-2` a side), the badge's (`px-2`, its border, the space before it), a margin. */
    const CELL_PADDING = 16;
    const SHADE_PADDING = 16;
    const BADGE_PADDING = 22;
    const MARGIN = 4;

    /** The narrowest a column may be: its widest cell (G6d). */
    function fitWidth(level: Level | 'misplaced'): number {
        let widest = 0;
        for (const row of rows) {
            const amount = level === 'misplaced' ? row.row.misplaced : row.row[level];
            // The «Custom» column is bold and shaded; the reference row carries its badge beside the figure.
            let width = textWidth(cellText(level, amount), 14, level === 'custom' ? 600 : 400, 0.64) + CELL_PADDING + MARGIN;
            if (level === 'custom') width += SHADE_PADDING;
            if (level === 'misplaced' && row.row.reference) width += textWidth($t(`${T}.reference`), 12, 400, 0.66) + BADGE_PADDING;
            widest = Math.max(widest, width);
        }
        return widest;
    }

    function cellHtml(row: Row, level: Level | 'misplaced', amount: PreviewMoney | null): string {
        const text = cellText(level, amount);
        const reference = level === 'misplaced' && row.row.reference ? ` <span class="${BADGE.neutral}">${escapeHtml($t(`${T}.reference`))}</span>` : '';
        const tone = stale ? 'text-lf-muted' : level === 'misplaced' || level === 'custom' ? 'text-lf-primary' : 'text-lf-secondary';
        // G6-2: the «Custom» column in the chosen cards' shade, bold, as the mockup.
        const highlight = level === 'custom';
        const shade = highlight ? ' rounded-md bg-lf-selected px-2 py-0.5 font-semibold' : '';
        return `<span class="whitespace-nowrap tabular-nums ${tone}${shade}" data-testid="${testId('fidelity-cell', profile)}" data-level="${level}" data-row="${row.index}" data-reference="${row.row.reference ? 'true' : 'false'}" data-highlight="${highlight ? 'true' : 'false'}">${escapeHtml(text)}${reference}</span>`;
    }

    function levelHeader(level: Level): string {
        if (phone.current && level === 'cost_aware') return $t(`${T}.costAwareShort`);
        if (phone.current && level === 'faithful') return $t(`${T}.faithfulShort`);
        if (phone.current && level === 'custom') return $t(`${T}.customShort`);
        if (level === 'custom') return fidelityName($t, {kind: 'custom', lambda: ''});
        return fidelityName($t, {kind: 'level', level});
    }

    function levelColumn(level: Level): ColumnDef<Row> {
        return {
            id: level,
            header: () => levelHeader(level),
            type: 'custom',
            sortable: false,
            filterable: false,
            align: 'right',
            minWidth: fitWidth(level),
            cell: (row) => ({type: 'html', html: cellHtml(row, level, row.row[level])}),
        };
    }

    const columns = $derived.by((): ColumnDef<Row>[] => [
        {
            id: 'misplaced',
            header: () => $t(`${T}.misplaced`),
            type: 'custom',
            sortable: false,
            filterable: false,
            minWidth: fitWidth('misplaced'),
            cell: (row) => ({type: 'html', html: cellHtml(row, 'misplaced', row.row.misplaced)}),
        },
        levelColumn('cost_aware'),
        levelColumn('balanced'),
        levelColumn('faithful'),
        ...(showCustom ? [levelColumn('custom')] : []),
    ]);
</script>

<section class="space-y-2" data-testid={testId('fidelity', profile)} data-preview={preview?.state ?? 'idle'} data-stale={stale ? 'true' : 'false'}>
    <div class="flex items-center gap-2">
        <h3 class={SECTION_TITLE}>{$t(`${T}.title`)}</h3>
        {#if table}<TableColumns table={tableRef} testid={testId('fidelity-columns', profile)} />{/if}
    </div>
    <p class="text-sm text-lf-secondary">
        {$t(`${T}.lead`)}
        {#if totalText !== null}<span data-testid={testId('fidelity-total', profile)}>{$t(`${T}.leadTotal`, {values: {total: totalText}})}</span>{/if}
    </p>
    {#if table}
        <DataTable bind:this={tableRef} data={rows} {columns} getRowId={(row) => row.id} storageKey={storageKey('fidelity', profile)} enableSorting={false} enablePagination={false} enableSelection={false} enableColumnFilters={false} tableLayout="auto" />
        <p class={HINT} data-testid={testId('fidelity-target-first', profile)}>{$t(`${T}.targetFirst`)}</p>
    {:else if preview?.reason}
        <p class={HINT} role="status" data-testid={testId('fidelity-reason', profile)} data-reason={preview.reason}>
            {preview.reason === 'incomplete' ? $t(`${T}.incomplete`) : preview.reason === 'unavailable' ? $t(`${T}.unavailable`) : $t(`tools.pacAllocator.planner.issues.${preview.reason}`, {default: $t(`${T}.unavailable`)})}
        </p>
    {/if}
</section>
