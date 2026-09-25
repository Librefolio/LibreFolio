<script lang="ts">
    import {t} from '$lib/i18n';
    import {formatExactMoneyPlain, formatPlannerMoneyPlain, type CurrencyDigits} from '../format';
    import type {PacAccounting, PacLedgerRow} from '../types';
    import {BUTTON_LINK, HINT, TABLE, TD_NUM, TH} from '../ui';
    import {LEDGER_FIELDS, LEDGER_ZERO_FIELDS, ledgerColumns, type LedgerField, type ResultNames} from './model';

    interface Props {
        rows: readonly PacLedgerRow[];
        accounting: PacAccounting;
        names: ResultNames;
        digits: CurrencyDigits;
    }

    let {rows, accounting, names, digits}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.ledger';
    const FALLBACKS: Record<LedgerField, string> = {
        initial_selected: 'Initial selected',
        funding_in: 'Funding in',
        funding_out: 'Funding out',
        fx_debit: 'FX debit',
        fx_credit: 'FX credit',
        buy_debit: 'Purchases',
        buy_fees: 'BUY fees',
        rounding_delta: 'Rounding',
        final_spendable: 'Final spendable',
        final_physical: 'Final physical',
        gross_sell_credit: 'Sales',
        sell_fees: 'SELL fees',
        broker_withheld_tax: 'Tax withheld by the Broker',
        self_reserved_tax: 'Tax reserved by you',
    };

    let showZero = $state(false);
    const columns = $derived(ledgerColumns(rows));
    const fields = $derived<readonly LedgerField[]>(showZero ? [...LEDGER_FIELDS, ...LEDGER_ZERO_FIELDS] : LEDGER_FIELDS);
</script>

<div class="space-y-3" data-testid="pac-planner-ledger">
    <div class="overflow-x-auto">
        <table class={TABLE}>
            <thead>
                <tr>
                    <th scope="col" class={TH}>{$t(`${KEY}.item`, {default: 'Item'})}</th>
                    {#each columns as column (`${column.broker_id}|${column.currency}`)}
                        <th scope="col" class="{TH} text-right" data-testid="pac-planner-ledger-column" data-broker={column.broker_id} data-currency={column.currency}>
                            {[names.broker(column.broker_id), column.currency].join(' · ')}
                        </th>
                    {/each}
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                {#each fields as field (field)}
                    <tr data-testid="pac-planner-ledger-row" data-field={field}>
                        <th scope="row" class="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300">{$t(`${KEY}.fields.${field}`, {default: FALLBACKS[field]})}</th>
                        {#each columns as column (`${column.broker_id}|${column.currency}`)}
                            <td class={TD_NUM}>{formatPlannerMoneyPlain(column[field], column.currency, {digits})}</td>
                        {/each}
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>
    <p class="{HINT} flex flex-wrap items-center gap-2">
        <span>{$t(`${KEY}.zeroHint`, {default: 'Sales, SELL fees, withheld and reserved taxes: always 0 in PAC 2.0.0.'})}</span>
        <button type="button" class={BUTTON_LINK} aria-expanded={showZero} data-testid="pac-planner-ledger-zero-toggle" onclick={() => (showZero = !showZero)}>
            {showZero ? $t(`${KEY}.hideZero`, {default: 'Hide the zero rows'}) : $t(`${KEY}.showZero`, {default: 'Show {count, plural, one {# zero row} other {# zero rows}}', values: {count: LEDGER_ZERO_FIELDS.length}})}
        </button>
    </p>
    <p class="text-sm" data-testid="pac-planner-ledger-free-cash">
        {$t(`${KEY}.freeCash`, {default: 'Free cash (accounting): {amount}', values: {amount: formatExactMoneyPlain(accounting.free_cash, {digits})}})}
    </p>
</div>
