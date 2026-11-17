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
    import type {PlannerAccounting, PlannerLedgerRow} from '../types';
    import {BUTTON_LINK, HINT} from '../ui';
    import ResultCell, {type ResultCellContent} from './ResultCell.svelte';
    import {ledgerColumns, ledgerFieldList, ledgerFields, ledgerHelpKey, ledgerLabelKey, type LedgerField, type ResultNames} from './model';
    import {withHelpCues} from '../shared/columnHelp';
    import TableColumns from '../shared/TableColumns.svelte';
    import {getPlannerProfile, storageKey, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    interface Props {
        rows: readonly PlannerLedgerRow[];
        accounting: PlannerAccounting;
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
        transfer_in: 'Transfers in',
        transfer_out: 'Transfers out',
    };
    /** The English default of each help key `ledgerHelpKey` chooses, by its last segment. */
    const HELP_FALLBACKS: Record<string, string> = {
        initial_selected: 'The cash of this Broker in this currency that you made available to the plan.',
        funding_in: 'What the plan brings into this cash: deposits, transfers, and this cash itself when the orders here use it.',
        funding_out: 'What the plan takes from this cash: transfers to other Brokers, and what the orders here use (counted in Incoming too).',
        fx_debit: 'What the currency exchanges of the plan take from this cash.',
        fx_credit: 'What the currency exchanges of the plan add to this cash.',
        buy_debit: 'The amounts of the orders on this Broker in this currency, fees excluded.',
        buy_fees: 'The Broker fees of those orders.',
        rounding_delta: 'How much of the amounts in this row comes from rounding to the smallest unit of the currency. It is already included in them.',
        final_spendable: 'What stays in this cash at the end of the plan.',
        final_physical: 'What is left available plus the taxes you set aside.',
        alwaysZero: 'Always 0 in a PAC: it only buys.',
        alwaysZeroInvestOnly: 'Always 0 with «Invest only»: the plan only buys.',
        transfer_in: 'What arrives in this cash from another Broker of the plan.',
        transfer_out: 'What leaves this cash for another Broker of the plan.',
    };
    /** The Rebalancer's own help for the funding columns: its deposits, and nothing going out as funding. */
    const REBALANCER_HELP_FALLBACKS: Record<string, string> = {
        funding_in: 'The deposits of your contributions into this cash.',
        funding_out: 'Always 0 in the Rebalancer: money moves between Brokers as transfers, in their own columns.',
    };
    const fields = ledgerFieldList(profile.text);
    const helpDefault = (key: string) => {
        const last = key.slice(key.lastIndexOf('.') + 1);
        return (key.startsWith('tools.portfolioRebalancer.') ? REBALANCER_HELP_FALLBACKS[last] : undefined) ?? HELP_FALLBACKS[last];
    };

    let showAll = $state(false);
    let table = $state<DataTable<PlannerLedgerRow>>();
    const data = $derived(ledgerColumns(rows));
    // R11.8: every column stays in the table, so the column button lists them all. The silent ones
    // start hidden and «show more» only changes that default: a choice made in the button wins.
    const speaking = $derived(new Set(ledgerFields(rows, false, fields)));
    const hidden = $derived(fields.length - speaking.size);
    const cell = (content: ResultCellContent) => ({type: 'custom' as const, component: ResultCell, props: {cell: content}});

    const columns = $derived.by((): ColumnDef<PlannerLedgerRow>[] =>
        withHelpCues<PlannerLedgerRow>([
            {
                id: 'pool',
                header: () => $t(`${KEY}.item`, {default: 'Broker and currency'}),
                type: 'custom',
                sortable: false,
                filterable: false,
                pinned: 'left',
                minWidth: 180,
                cell: (row) => cell({type: 'broker', brokerId: row.broker_id, label: names.broker(row.broker_id), broker: draft.broker(row.broker_id) ?? null, currency: row.currency, testid: testId('ledger-row', profile)}),
            },
            ...fields.map(
                (field): ColumnDef<PlannerLedgerRow> => ({
                    id: field,
                    hiddenByDefault: !showAll && !speaking.has(field),
                    header: () => $t(ledgerLabelKey(field), {default: FALLBACKS[field]}),
                    headerTooltip: () => $t(ledgerHelpKey(field, profile.text), {default: helpDefault(ledgerHelpKey(field, profile.text))}),
                    type: 'number',
                    sortable: false,
                    filterable: false,
                    align: 'right',
                    minWidth: 150,
                    cell: (row) =>
                        cell(
                            field === 'rounding_delta'
                                ? {type: 'exactMoney', money: {value: row.rounding_delta, currency: row.currency}, digits, testid: testId(`ledger-${field}`, profile)}
                                : {type: 'money', amount: row[field], currency: row.currency, digits, testid: testId(`ledger-${field}`, profile)},
                        ),
                }),
            ),
        ]),
    );
</script>

<div class="space-y-3" data-testid={testId('ledger', profile)}>
    <TableColumns {table} testid={testId('ledger-columns', profile)} />
    <DataTable
        bind:this={table}
        {data}
        {columns}
        getRowId={(row) => `${row.broker_id}|${row.currency}`}
        storageKey={storageKey('result-ledger', profile)}
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
            <button type="button" class={BUTTON_LINK} aria-expanded={showAll} data-testid={testId('ledger-zero-toggle', profile)} onclick={() => (showAll = !showAll)}>
                {showAll ? $t(`${KEY}.hideZero`, {default: 'Show fewer columns'}) : $t(`${KEY}.showZero`, {default: 'Show {count, plural, one {# more column} other {# more columns}}', values: {count: hidden}})}
            </button>
        </p>
    {/if}
    <p class="text-sm" data-testid={testId('ledger-free-cash', profile)}>
        {$t(`${KEY}.freeCash`, {default: 'Cash left free at the end of the plan, in total: {amount}', values: {amount: formatExactMoneyPlain(accounting.free_cash, {digits})}})}
    </p>
</div>
