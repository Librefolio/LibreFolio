<!--
  The table «Maximum acceptable cost» of the Rebalancer's Strategy step (F3a of project 67, step 10a; M30–M33).

  How much the plan may spend at most, in fees and taxes, to put back money that is in the wrong place, per fidelity level.
  The figures are the backend preview's as it gives them (N1): no figure is computed here. The «Custom» column is there
  only while that choice is active and the answer carries it (M32); «Target first» has no column, the line under the
  table says why (M33). While the preview waits the figures stay, muted; after a failure the table goes and a line says
  why. Every figure derives from the user's total: masked in privacy mode.
-->
<script lang="ts">
    import {MediaQuery} from 'svelte/reactivity';
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';
    import type {DraftFidelity} from '../draft.svelte';
    import {formatExactMoneyCompact, formatExactMoneyPlain} from '../format';
    import type {PlannerPreview, PreviewCostRow, PreviewMoney} from '../preview.svelte';
    import {fidelityName} from '../strategyText';
    import {BADGE, HINT, SECTION_TITLE} from '../ui';
    import {getPlannerProfile, storageKey, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    interface Props {
        /** The scenario preview (step 8): the table, already counted. */
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
        row: PreviewCostRow;
    }

    const numbers = $derived(preview?.numbers ?? null);
    const table = $derived(numbers?.table ?? null);
    const stale = $derived(preview?.stale ?? false);
    const rows = $derived<Row[]>((table?.rows ?? []).map((row, index) => ({id: String(index), index, row})));
    const showCustom = $derived(fidelity.kind === 'custom' && (table?.rows[0]?.custom ?? null) !== null);
    const totalText = $derived(numbers ? formatExactMoneyPlain(numbers.total) : null);

    function cellHtml(row: Row, level: Level | 'misplaced', amount: PreviewMoney | null): string {
        // G6-1: two significant digits and the symbol alone; the currency is named once, in the line above the table.
        const figure = amount ? formatExactMoneyCompact(amount) : '';
        const text = level === 'misplaced' || phone.current || figure === '' ? figure : $t(`${T}.upTo`, {values: {amount: figure}});
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
            minWidth: phone.current ? 64 : 110,
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
            minWidth: phone.current ? 96 : 200,
            cell: (row) => ({type: 'html', html: cellHtml(row, 'misplaced', row.row.misplaced)}),
        },
        levelColumn('cost_aware'),
        levelColumn('balanced'),
        levelColumn('faithful'),
        ...(showCustom ? [levelColumn('custom')] : []),
    ]);
</script>

<section class="space-y-2" data-testid={testId('fidelity', profile)} data-preview={preview?.state ?? 'idle'} data-stale={stale ? 'true' : 'false'}>
    <h3 class={SECTION_TITLE}>{$t(`${T}.title`)}</h3>
    <p class="text-sm text-lf-secondary">
        {$t(`${T}.lead`)}
        {#if totalText !== null}<span data-testid={testId('fidelity-total', profile)}>{$t(`${T}.leadTotal`, {values: {total: totalText}})}</span>{/if}
    </p>
    {#if table}
        <DataTable data={rows} {columns} getRowId={(row) => row.id} storageKey={storageKey('fidelity', profile)} enableSorting={false} enablePagination={false} enableSelection={false} enableColumnFilters={false} tableLayout="auto" />
        <p class={HINT} data-testid={testId('fidelity-target-first', profile)}>{$t(`${T}.targetFirst`)}</p>
    {:else if preview?.reason}
        <p class={HINT} role="status" data-testid={testId('fidelity-reason', profile)} data-reason={preview.reason}>
            {preview.reason === 'incomplete' ? $t(`${T}.incomplete`) : preview.reason === 'unavailable' ? $t(`${T}.unavailable`) : $t(`tools.pacAllocator.planner.issues.${preview.reason}`, {default: $t(`${T}.unavailable`)})}
        </p>
    {/if}
</section>
