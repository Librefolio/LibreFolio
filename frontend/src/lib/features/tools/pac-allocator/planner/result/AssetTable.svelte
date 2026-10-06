<script lang="ts">
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef, FooterCellContent} from '$lib/components/table/types';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatExactMoneyPlain, type CurrencyDigits} from '../format';
    import type {PacAccounting, PacAssetRow} from '../types';
    import ResultCell, {type ResultCellContent} from './ResultCell.svelte';
    import {weightScale, type ResultNames} from './model';
    import {withHelpCues} from '../shared/columnHelp';
    import TableColumns from '../shared/TableColumns.svelte';

    interface Props {
        rows: readonly PacAssetRow[];
        accounting: PacAccounting;
        names: ResultNames;
        digits: CurrencyDigits;
        draft: PlannerDraft;
    }

    let {rows, accounting, names, digits, draft}: Props = $props();
    let table = $state<DataTable<PacAssetRow>>();

    const KEY = 'tools.pacAllocator.planner.result.assets';
    const data = $derived([...rows]);
    const scale = $derived(weightScale(rows.flatMap((row) => [row.target_weight, row.final_weight])));
    const assetLabel = (id: string) => [names.ticker(id), names.asset(id)].filter((part) => part).join(' ');
    const cell = (content: ResultCellContent) => ({type: 'custom' as const, component: ResultCell, props: {cell: content}});

    const columns = $derived.by((): ColumnDef<PacAssetRow>[] => withHelpCues<PacAssetRow>([
        {
            id: 'asset',
            header: () => $t(`${KEY}.asset`, {default: 'Asset'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            pinned: 'left',
            minWidth: 180,
            cell: (row) => cell({type: 'asset', assetId: row.asset_id, label: assetLabel(row.asset_id), asset: draft.asset(row.asset_id) ?? null, testid: 'pac-planner-assets-row'}),
        },
        {
            id: 'target',
            header: () => $t(`${KEY}.targetShare`, {default: 'Target share'}),
            headerTooltip: () => $t(`${KEY}.targetShareHelp`, {default: 'The share you chose for this Asset in the Targets step.'}),
            type: 'number',
            sortable: false,
            filterable: false,
            align: 'right',
            minWidth: 90,
            cell: (row) => cell({type: 'weight', value: row.target_weight}),
        },
        {
            id: 'final',
            header: () => $t(`${KEY}.finalShare`, {default: 'Share after the plan'}),
            headerTooltip: () =>
                $t(`${KEY}.finalShareHelp`, {
                    default: 'The share of the Asset in the value of all these Assets after the plan. Compare it with the target share to see how the balance between the Assets changes.',
                }),
            type: 'number',
            sortable: false,
            filterable: false,
            align: 'right',
            minWidth: 90,
            cell: (row) => cell({type: 'weight', value: row.final_weight}),
        },
        {
            id: 'bars',
            header: '',
            displayName: () => $t(`${KEY}.bars`, {default: 'Target and after'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            minWidth: 120,
            cell: (row) => cell({type: 'bars', target: row.target_weight, final: row.final_weight, scale}),
        },
        {
            id: 'finalValue',
            header: () => $t(`${KEY}.finalValue`, {default: 'Value after the plan'}),
            headerTooltip: () =>
                $t(`${KEY}.finalValueHelp`, {
                    default: 'What the Asset is worth after the plan: the units you had plus the ones bought, at the quote price and, when needed, at the rate of the FX step.',
                }),
            type: 'number',
            sortable: false,
            filterable: false,
            align: 'right',
            minWidth: 120,
            cell: (row) => cell({type: 'exactMoney', money: row.final_value, digits}),
        },
        {
            id: 'targetValue',
            header: () => $t(`${KEY}.targetValue`, {default: 'Ideal value'}),
            headerTooltip: () =>
                $t(`${KEY}.targetValueHelp`, {
                    default: 'What the Asset would be worth with exactly its target share: target share × base of the targets (already invested in these Assets plus usable cash).',
                }),
            type: 'number',
            sortable: false,
            filterable: false,
            align: 'right',
            minWidth: 120,
            cell: (row) => cell({type: 'exactMoney', money: row.target_value, digits}),
        },
        {
            id: 'residual',
            header: () => $t(`${KEY}.residual`, {default: 'Gap from ideal'}),
            headerTooltip: () =>
                $t(`${KEY}.residualHint`, {
                    default: 'Value after the plan minus ideal value: positive if the Asset ends above its share, negative if below.',
                }),
            type: 'number',
            sortable: false,
            filterable: false,
            align: 'right',
            minWidth: 110,
            cell: (row) => cell({type: 'exactMoney', money: row.residual, digits, signed: true, testid: 'pac-planner-assets-residual'}),
        },
        {
            id: 'buyMid',
            header: () => $t(`${KEY}.buyMid`, {default: 'Value bought'}),
            headerTooltip: () =>
                $t(`${KEY}.buyMidHelp`, {
                    default: 'The value of what the plan buys of this Asset, at the quote price: without fees or price margin. In a PAC, which starts from zero, it equals the value after the plan. What really leaves the cash is in the Operational plan.',
                }),
            // R11.5: in a PAC it repeats «Value after the plan»; it comes back from the column menu.
            hiddenByDefault: true,
            type: 'number',
            sortable: false,
            filterable: false,
            align: 'right',
            minWidth: 120,
            cell: (row) => cell({type: 'exactMoney', money: row.buy_mid_value, digits}),
        },
    ]));

    const footerCells = (): Record<string, FooterCellContent> => ({
        asset: $t(`${KEY}.totals`, {default: 'Totals (accounting)'}),
        targetValue: formatExactMoneyPlain(accounting.fixed_reference, {digits}),
        finalValue: formatExactMoneyPlain(accounting.final_invested, {digits}),
    });
</script>

<div class="space-y-2" data-testid="pac-planner-assets-table">
    <div class="flex flex-wrap items-center gap-2">
        <p class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-600 dark:text-gray-400" data-testid="pac-planner-assets-legend">
            <span class="flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-gray-400 dark:bg-gray-500" aria-hidden="true"></span>{$t(`${KEY}.targetShare`, {default: 'Target share'})}</span>
            <span class="flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-libre-green" aria-hidden="true"></span>{$t(`${KEY}.finalShare`, {default: 'Share after the plan'})}</span>
        </p>
        <TableColumns {table} testid="pac-planner-assets-columns" />
    </div>
    <DataTable
        bind:this={table}
        {data}
        {columns}
        getRowId={(row) => row.asset_id}
        storageKey="pac-planner-result-assets"
        enableSorting={false}
        enableSelection={false}
        selectionMode="none"
        enableActions={false}
        enablePagination={false}
        enableColumnVisibility
        enableColumnFilters={false}
        enableColumnResize
        enableContextMenu={false}
        tableLayout="auto"
        {footerCells}
    />
</div>
