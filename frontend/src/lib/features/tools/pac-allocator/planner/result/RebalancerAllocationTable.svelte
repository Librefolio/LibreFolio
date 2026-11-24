<!--
  The Rebalancer's allocation (F4a of project 67, step 3; contract §6.2): before, target and after for every Asset, every
  cash entry with a target and, last, the uninvested row in its two parts (TL-5 of project 67): «Cassa senza obiettivo»
  and «Costi e commissioni», the money the plan lost. The weights are shares of the whole portfolio, cash included: before
  and after, both as shares of the total today. Every figure is a published field; a cell the row has no field for stays
  empty: the two parts publish no target (the specification gives the uninvested row a target of 0). The minimum and
  maximum columns exist only when an entry carries a limit. The PAC keeps its own table (`AssetTable`); `ResultView` picks
  one by the Tool's profile.
-->
<script lang="ts">
    import {MediaQuery} from 'svelte/reactivity';
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import type {PlannerDraft} from '../draft.svelte';
    import type {CurrencyDigits} from '../format';
    import type {PlannerExactMoney, PlannerExactNumber, PlannerNumberAvailability, RebalancerSolution} from '../types';
    import {HINT} from '../ui';
    import ResultCell, {type ResultCellContent} from './ResultCell.svelte';
    import {allocationRows, isUninvestedPart, UNINVESTED_PARTS, weightScale, type AllocationRow, type ResultNames} from './model';
    import {withHelpCues} from '../shared/columnHelp';
    import TableColumns from '../shared/TableColumns.svelte';
    import {getPlannerProfile, storageKey, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    interface Props {
        solution: RebalancerSolution;
        names: ResultNames;
        digits: CurrencyDigits;
        draft: PlannerDraft;
    }

    let {solution, names, digits, draft}: Props = $props();
    /** On a phone (the table's own 768 px breakpoint) the pinned item column is narrower, so the others have room to scroll. */
    const phone = new MediaQuery('max-width: 768px');
    let table = $state<DataTable<AllocationRow>>();

    const A = 'tools.pacAllocator.planner.result.assets';
    const R = 'tools.portfolioRebalancer.planner.result.allocation';
    const rows = $derived(allocationRows(solution));
    const limited = $derived(rows.some((entry) => !isUninvestedPart(entry) && (entry.row.minimum != null || entry.row.maximum != null)));
    const scale = $derived(weightScale(rows.flatMap((entry) => (isUninvestedPart(entry) ? [entry.row.final_weight] : [entry.row.target_weight, entry.row.final_weight]))));
    /** The two parts' names and helps (TL-5 of project 67). */
    const PART_KEYS = {untargeted_cash: 'untargetedCash', costs: 'costs'} as const;
    const assetLabel = (id: string) => [names.ticker(id), names.asset(id)].filter((part) => part).join(' ');
    const cell = (content: ResultCellContent) => ({type: 'custom' as const, component: ResultCell, props: {cell: content}});
    const EMPTY = {type: 'html' as const, html: ''};
    const weight = (value: PlannerExactNumber | PlannerNumberAvailability | undefined) => (value ? cell({type: 'weight', value}) : EMPTY);
    const money = (value: PlannerExactMoney | null | undefined, signed = false) => (value ? cell({type: 'exactMoney', money: value, digits, signed}) : EMPTY);

    function item(entry: AllocationRow): ResultCellContent {
        if (entry.kind === 'asset') return {type: 'asset', assetId: entry.row.asset_id, label: assetLabel(entry.row.asset_id), asset: draft.asset(entry.row.asset_id) ?? null, testid: testId('allocation-item', profile)};
        if (entry.kind === 'cash') return {type: 'broker', brokerId: entry.row.broker_id, label: names.broker(entry.row.broker_id), broker: draft.broker(entry.row.broker_id) ?? null, currency: entry.row.currency, testid: testId('allocation-item', profile)};
        return {type: 'label', text: $t(`${R}.${PART_KEYS[entry.kind]}`), testid: testId('allocation-item', profile), attrs: {'data-kind': entry.kind}};
    }

    const target = (entry: AllocationRow) => (isUninvestedPart(entry) ? undefined : entry.row.target_weight);

    function numberColumn(id: string, header: () => string, help: () => string, content: (entry: AllocationRow) => ReturnType<typeof cell> | typeof EMPTY, minWidth = 120): ColumnDef<AllocationRow> {
        return {id, header, headerTooltip: help, type: 'number', sortable: false, filterable: false, align: 'right', minWidth, cell: content};
    }

    const columns = $derived.by((): ColumnDef<AllocationRow>[] =>
        withHelpCues<AllocationRow>([
            {
                id: 'item',
                header: () => $t('tools.portfolioRebalancer.planner.targets.entry'),
                type: 'custom',
                sortable: false,
                filterable: false,
                pinned: 'left',
                // Wider than the PAC's on a large screen: a cash entry shows its Broker and its currency side by side. On a phone
                // a long name scrolls in its cell (MarqueeName), as everywhere in the planner.
                minWidth: phone.current ? 150 : 260,
                cell: (entry) => cell(item(entry)),
            },
            numberColumn(
                'beforeShare',
                () => $t(`${R}.beforeShare`),
                () => $t(`${R}.beforeShareHelp`),
                (entry) => weight(entry.row.before_weight),
                90,
            ),
            numberColumn(
                'target',
                () => $t(`${A}.targetShare`, {default: 'Target share'}),
                () => $t(`${R}.targetShareHelp`),
                (entry) => weight(target(entry)),
                90,
            ),
            numberColumn(
                'final',
                () => $t(`${A}.finalShare`, {default: 'Final share'}),
                () => $t(`${R}.finalShareHelp`),
                (entry) => weight(entry.row.final_weight),
                90,
            ),
            {
                id: 'bars',
                header: '',
                displayName: () => $t(`${A}.bars`, {default: 'Target and after'}),
                type: 'custom',
                sortable: false,
                filterable: false,
                minWidth: 120,
                cell: (entry) => (isUninvestedPart(entry) ? EMPTY : cell({type: 'bars', target: entry.row.target_weight, final: entry.row.final_weight, scale})),
            },
            numberColumn(
                'beforeValue',
                () => $t(`${R}.beforeValue`),
                () => $t(`${R}.beforeValueHelp`),
                (entry) => money(entry.row.before_value),
                150,
            ),
            numberColumn(
                'targetValue',
                () => $t(`${A}.targetValue`, {default: 'Ideal value'}),
                () => $t(`${R}.targetValueHelp`),
                (entry) => money(isUninvestedPart(entry) ? null : entry.row.target_value),
                150,
            ),
            numberColumn(
                'finalValue',
                () => $t(`${A}.finalValue`, {default: 'Final value'}),
                () => $t(`${R}.finalValueHelp`),
                (entry) => money(entry.row.final_value),
                150,
            ),
            numberColumn(
                'residual',
                () => $t(`${A}.residual`, {default: 'Gap from ideal'}),
                () => $t(`${R}.residualHelp`),
                (entry) => money(isUninvestedPart(entry) ? null : entry.row.residual, true),
                150,
            ),
            numberColumn(
                'bought',
                () => $t(`${A}.buyMid`, {default: 'Value bought'}),
                () => $t(`${R}.boughtHelp`),
                (entry) => money(entry.kind === 'asset' && 'buy_mid_value' in entry.row ? entry.row.buy_mid_value : null),
                150,
            ),
            ...(limited
                ? [
                      numberColumn(
                          'minimum',
                          () => $t(`${R}.minimum`),
                          () => $t(`${R}.minimumHelp`),
                          (entry) => money(isUninvestedPart(entry) ? null : entry.row.minimum),
                          130,
                      ),
                      numberColumn(
                          'maximum',
                          () => $t(`${R}.maximum`),
                          () => $t(`${R}.maximumHelp`),
                          (entry) => money(isUninvestedPart(entry) ? null : entry.row.maximum),
                          130,
                      ),
                  ]
                : []),
        ]),
    );
</script>

<div class="space-y-2" data-testid={testId('allocation-table', profile)}>
    <div class="flex flex-wrap items-center gap-2">
        <p class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-lf-secondary" data-testid={testId('allocation-legend', profile)}>
            <span class="flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-lf-secondary" aria-hidden="true"></span>{$t(`${A}.targetShare`, {default: 'Target share'})}</span>
            <span class="flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-lf-checked" aria-hidden="true"></span>{$t(`${A}.finalShare`, {default: 'Final share'})}</span>
        </p>
        <TableColumns {table} testid={testId('allocation-columns', profile)} />
    </div>
    <DataTable
        bind:this={table}
        data={rows}
        {columns}
        getRowId={(entry) => entry.id}
        storageKey={storageKey('result-allocation', profile)}
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
    />
    {#each UNINVESTED_PARTS as part (part)}
        <p class={HINT} data-testid={testId('allocation-uninvested-note', profile)} data-kind={part}>
            <span class="font-medium">{$t(`${R}.${PART_KEYS[part]}`)}:</span>
            {$t(`${R}.${PART_KEYS[part]}Help`)}
        </p>
    {/each}
</div>
