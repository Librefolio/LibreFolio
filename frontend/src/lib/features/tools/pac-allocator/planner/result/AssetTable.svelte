<script lang="ts">
    import {t} from '$lib/i18n';
    import {formatExactMoneyPlain, formatExactPercent, type CurrencyDigits} from '../format';
    import type {PacAccounting, PacAssetRow} from '../types';
    import {HINT, TABLE, TD, TD_NUM, TH} from '../ui';
    import {UNAVAILABLE_FALLBACKS, type ResultNames} from './model';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        rows: readonly PacAssetRow[];
        accounting: PacAccounting;
        names: ResultNames;
        digits: CurrencyDigits;
    }

    let {rows, accounting, names, digits}: Props = $props();

    const assetLabel = (id: string) => [names.ticker(id), names.asset(id)].filter((part) => part).join(' ');
</script>

<div class="overflow-x-auto" data-testid="pac-planner-assets-table">
    <table class={TABLE}>
        <thead>
            <tr>
                <th scope="col" class={TH}>{$t(`${PLANNER_KEY}.result.assets.asset`, {default: 'Asset'})}</th>
                <th scope="col" class="{TH} text-right">{$t(`${PLANNER_KEY}.result.assets.target`, {default: 'Target'})}</th>
                <th scope="col" class="{TH} text-right">{$t(`${PLANNER_KEY}.result.assets.final`, {default: 'After'})}</th>
                <th scope="col" class="{TH} text-right">{$t(`${PLANNER_KEY}.result.assets.targetValue`, {default: 'Target value'})}</th>
                <th scope="col" class="{TH} text-right">{$t(`${PLANNER_KEY}.result.assets.finalValue`, {default: 'Value after'})}</th>
                <th scope="col" class="{TH} text-right">{$t(`${PLANNER_KEY}.result.assets.residual`, {default: 'Residual'})}</th>
                <th scope="col" class="{TH} text-right">{$t(`${PLANNER_KEY}.result.assets.buyMid`, {default: 'Purchase (mid)'})}</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            {#each rows as row (row.asset_id)}
                <tr data-testid="pac-planner-assets-row" data-asset={row.asset_id}>
                    <th scope="row" class="{TD} text-left font-medium">{assetLabel(row.asset_id)}</th>
                    <td class={TD_NUM}>{formatExactPercent(row.target_weight)}</td>
                    <td class={TD_NUM}>
                        {#if row.final_weight.kind === 'available'}
                            {formatExactPercent(row.final_weight.value)}
                        {:else}
                            <span title={$t(`${PLANNER_KEY}.result.unavailable.${row.final_weight.reason}`, {default: UNAVAILABLE_FALLBACKS[row.final_weight.reason]})}>—</span>
                        {/if}
                    </td>
                    <td class={TD_NUM}>{formatExactMoneyPlain(row.target_value, {digits})}</td>
                    <td class={TD_NUM}>{formatExactMoneyPlain(row.final_value, {digits})}</td>
                    <td class={TD_NUM} data-testid="pac-planner-assets-residual">{formatExactMoneyPlain(row.residual, {digits, signed: true})}</td>
                    <td class={TD_NUM}>{formatExactMoneyPlain(row.buy_mid_value, {digits})}</td>
                </tr>
            {/each}
        </tbody>
        <tfoot>
            <tr class="border-t border-gray-200 dark:border-gray-700" data-testid="pac-planner-assets-totals">
                <th scope="row" colspan="3" class="{TD} text-left font-medium">{$t(`${PLANNER_KEY}.result.assets.totals`, {default: 'Totals (accounting)'})}</th>
                <td class="{TD_NUM} font-medium">{formatExactMoneyPlain(accounting.fixed_reference, {digits})}</td>
                <td class="{TD_NUM} font-medium">{formatExactMoneyPlain(accounting.final_invested, {digits})}</td>
                <td class={TD_NUM}></td>
                <td class={TD_NUM}></td>
            </tr>
        </tfoot>
    </table>
</div>
<p class="mt-2 {HINT}">{$t(`${PLANNER_KEY}.result.assets.residualHint`, {default: 'Residual = the backend residual (after − target). The interface subtracts nothing.'})}</p>
