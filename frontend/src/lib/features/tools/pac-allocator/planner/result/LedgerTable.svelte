<!--
  R9.8: balances per Broker and currency, one row each. A column appears only when it says
  something in this plan; the silent ones are one click away. Every figure is the backend's.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatExactMoneyPlain, type CurrencyDigits} from '../format';
    import type {PacAccounting, PacLedgerRow} from '../types';
    import {BUTTON_LINK, HINT} from '../ui';
    import ResultCell, {type ResultCellContent} from './ResultCell.svelte';
    import {LEDGER_FIELDS, LEDGER_PAC_ZERO_FIELDS, ledgerColumns, ledgerFields, type LedgerField, type ResultNames} from './model';
    import {withHelpCues} from '../shared/columnHelp';
    import TableColumns from '../shared/TableColumns.svelte';

    interface Props {
        rows: readonly PacLedgerRow[];
        accounting: PacAccounting;
        names: ResultNames;
        digits: CurrencyDigits;
        draft: PlannerDraft;
    }

    let {rows, accounting, names, digits, draft}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.ledger';
    const FALLBACKS: Record<LedgerField, string> = {
        initial_selected: 'Starting cash',
        funding_in: 'Incoming',
        funding_out: 'Outgoing',
        fx_debit: 'Exchange out',
        fx_credit: 'Exchange in',
        gross_sell_credit: 'Sales',
        buy_debit: 'Purchases',
        buy_fees: 'Purchase fees',
        sell_fees: 'Sale fees',
        broker_withheld_tax: 'Tax withheld by the Broker',
        self_reserved_tax: 'Tax reserved by you',
        rounding_delta: 'Rounding',
        final_spendable: 'Left available',
        final_physical: 'Physical balance',
    };
    const HELP_FALLBACKS: Record<string, string> = {
        initial_selected: 'The cash of this Broker in this currency that you made available to the plan.',
        funding_in: 'What the plan brings into this cash: deposits, transfers, and this cash itself when the orders here use it.',
        funding_out: 'What the plan takes from this cash: transfers to other Brokers, and what the orders here use (counted in Incoming too).',
        fx_debit: 'What the currency exchanges of the plan take from this cash.',
        fx_credit: 'What the currency exchanges of the plan add to this cash.',
        buy_debit: 'The amounts of the orders on this Broker in this currency, fees excluded.',
        buy_fees: 'The Broker fees of those orders.',
        rounding_delta: 'How much of the amounts in this row comes from rounding to the smallest unit of the currency. It is already included in them.',
        final_spendable: 'What stays in this cash after the plan.',
        final_physical: 'What is left available plus the taxes you set aside.',
        alwaysZero: 'Always 0 in a PAC: it only buys.',
    };

    let showAll = $state(false);
    let table = $state<DataTable<PacLedgerRow>>();
    const data = $derived(ledgerColumns(rows));
    // R11.8: every column stays in the table, so the column button lists them all. The silent ones
    // start hidden and «show more» only changes that default: a choice made in the button wins.
    const speaking = $derived(new Set(ledgerFields(rows, false)));
    const hidden = $derived(LEDGER_FIELDS.length - speaking.size);
    const cell = (content: ResultCellContent) => ({type: 'custom' as const, component: ResultCell, props: {cell: content}});
    const helpKey = (field: LedgerField) => (LEDGER_PAC_ZERO_FIELDS.has(field) ? 'alwaysZero' : field);

    const columns = $derived.by((): ColumnDef<PacLedgerRow>[] => withHelpCues<PacLedgerRow>([
        {
            id: 'pool',
            header: () => $t(`${KEY}.item`, {default: 'Broker and currency'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            pinned: 'left',
            minWidth: 180,
            cell: (row) => cell({type: 'broker', brokerId: row.broker_id, label: names.broker(row.broker_id), broker: draft.broker(row.broker_id) ?? null, currency: row.currency, testid: 'pac-planner-ledger-row'}),
        },
        ...LEDGER_FIELDS.map(
            (field): ColumnDef<PacLedgerRow> => ({
                id: field,
                hiddenByDefault: !showAll && !speaking.has(field),
                header: () => $t(`${KEY}.fields.${field}`, {default: FALLBACKS[field]}),
                headerTooltip: () => $t(`${KEY}.help.${helpKey(field)}`, {default: HELP_FALLBACKS[helpKey(field)]}),
                type: 'number',
                sortable: false,
                filterable: false,
                align: 'right',
                minWidth: 110,
                cell: (row) => cell({type: 'money', amount: row[field], currency: row.currency, digits, testid: `pac-planner-ledger-${field}`}),
            }),
        ),
    ]));
</script>

<div class="space-y-3" data-testid="pac-planner-ledger">
    <TableColumns {table} testid="pac-planner-ledger-columns" />
    <DataTable
        bind:this={table}
        {data}
        {columns}
        getRowId={(row) => `${row.broker_id}|${row.currency}`}
        storageKey="pac-planner-result-ledger"
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
    {#if hidden > 0}
        <p class="{HINT} flex flex-wrap items-center gap-2">
            {#if !showAll}<span>{$t(`${KEY}.zeroHint`, {default: 'Hidden: the columns at 0 in this plan, and the physical balance when it equals what is left available.'})}</span>{/if}
            <button type="button" class={BUTTON_LINK} aria-expanded={showAll} data-testid="pac-planner-ledger-zero-toggle" onclick={() => (showAll = !showAll)}>
                {showAll ? $t(`${KEY}.hideZero`, {default: 'Show fewer columns'}) : $t(`${KEY}.showZero`, {default: 'Show {count, plural, one {# more column} other {# more columns}}', values: {count: hidden}})}
            </button>
        </p>
    {/if}
    <p class="text-sm" data-testid="pac-planner-ledger-free-cash">
        {$t(`${KEY}.freeCash`, {default: 'Cash left free after the plan, in total: {amount}', values: {amount: formatExactMoneyPlain(accounting.free_cash, {digits})}})}
    </p>
</div>
