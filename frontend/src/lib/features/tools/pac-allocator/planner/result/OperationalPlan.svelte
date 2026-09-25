<script lang="ts">
    import {t} from '$lib/i18n';
    import {formatExactFxRate, formatExactMoneyPlain, formatPlannerMoneyPlain, type CurrencyDigits} from '../format';
    import type {PacOrderRow, PacSolution} from '../types';
    import {BADGE, BUTTON_LINK, HINT, TABLE, TD, TD_NUM, TH} from '../ui';
    import {ordersByBroker, planSteps, type PlanLookup, type ResultNames} from './model';
    import {instructionText, priceText} from './text';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        solution: PacSolution;
        names: ResultNames;
        lookup: PlanLookup;
        digits: CurrencyDigits;
        onorder: (order: PacOrderRow) => void;
    }

    let {solution, names, lookup, digits, onorder}: Props = $props();

    const steps = $derived(planSteps(solution.funding_actions, solution.fx_actions));
    const groups = $derived(ordersByBroker(solution.order_rows));
    const assetLabel = (id: string) => [names.ticker(id), names.asset(id)].filter((part) => part).join(' ');
    const routeAsset = (routeId: string) => {
        const route = lookup.route(routeId);
        return route ? (names.ticker(route.asset_id) ?? names.asset(route.asset_id)) : routeId;
    };
</script>

<div class="space-y-4" data-testid="pac-planner-plan">
    {#if steps.length > 0}
        <ol class="divide-y divide-gray-100 rounded-lg border border-gray-200 dark:divide-gray-700 dark:border-gray-700">
            {#each steps as step (step.action.action_id)}
                <li class="flex flex-wrap items-start gap-3 p-3 text-sm" data-testid="pac-planner-plan-step" data-kind={step.kind} data-sequence={step.sequence}>
                    <span class="w-6 shrink-0 text-right font-semibold tabular-nums">{step.sequence}</span>
                    <span class={step.kind === 'funding' ? BADGE.info : BADGE.warning}>
                        {step.kind === 'funding' ? $t(`${PLANNER_KEY}.result.plan.funding`, {default: 'Funding'}) : $t(`${PLANNER_KEY}.result.plan.fx`, {default: 'FX'})}
                    </span>
                    {#if step.kind === 'funding'}
                        {@const action = step.action}
                        {@const route = lookup.fundingRoute(action.funding_route_id)}
                        <div class="min-w-0 flex-1 space-y-1">
                            <p class="flex flex-wrap justify-between gap-2">
                                <span class="font-medium">{[lookup.sourceLabel(action.source), [names.broker(action.destination_broker_id), action.amount.currency].join(' · ')].join(' → ')}</span>
                                <span class="tabular-nums" data-testid="pac-planner-plan-amount">{formatPlannerMoneyPlain(action.amount.amount, action.amount.currency, {digits})}</span>
                            </p>
                            <p class={HINT}>
                                {$t(`${PLANNER_KEY}.result.plan.fundingDetail`, {
                                    default: 'funding route · priority {priority} · {reason}',
                                    values: {priority: route ? String(route.priority) : '—', reason: $t(`tools.pacAllocator.planner.result.reasons.${action.reason_code}`, {default: 'to pay for the orders of the plan'})},
                                })}
                            </p>
                        </div>
                    {:else}
                        {@const action = step.action}
                        <div class="min-w-0 flex-1 space-y-1">
                            <p class="font-medium">
                                {$t(`${PLANNER_KEY}.result.plan.fxTitle`, {
                                    default: '{broker} · {source} → {destination} · for the route of {asset}',
                                    values: {broker: names.broker(action.broker_id), source: action.source_debit.currency, destination: action.destination_credit.currency, asset: routeAsset(action.order_route_id)},
                                })}
                            </p>
                            <p class="tabular-nums">
                                {$t(`${PLANNER_KEY}.result.plan.fxAmounts`, {
                                    default: 'debit {debit} → credit {credit}',
                                    values: {
                                        debit: formatPlannerMoneyPlain(action.source_debit.amount, action.source_debit.currency, {digits}),
                                        credit: formatPlannerMoneyPlain(action.destination_credit.amount, action.destination_credit.currency, {digits}),
                                    },
                                })}
                            </p>
                            <p class="{HINT} tabular-nums">
                                {$t(`${PLANNER_KEY}.result.plan.fxRates`, {
                                    default: '1 {source} = {spot} {destination} spot · {effective} effective · spread loss {loss}',
                                    values: {
                                        source: action.spot_rate.source_currency,
                                        destination: action.spot_rate.destination_currency,
                                        spot: formatExactFxRate(action.spot_rate.value),
                                        effective: formatExactFxRate(action.effective_rate.value),
                                        loss: formatExactMoneyPlain(action.spread_loss, {digits}),
                                    },
                                })}
                            </p>
                        </div>
                    {/if}
                </li>
            {/each}
        </ol>
    {/if}

    {#each groups as group (group.brokerId)}
        <div data-testid="pac-planner-plan-orders" data-broker={group.brokerId}>
            <h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
                {$t(`${PLANNER_KEY}.result.plan.ordersAt`, {default: 'Orders · {broker}', values: {broker: names.broker(group.brokerId)}})}
            </h4>
            <div class="mt-2 overflow-x-auto">
                <table class={TABLE}>
                    <thead>
                        <tr>
                            <th scope="col" class="{TH} text-right">{$t(`${PLANNER_KEY}.result.plan.sequence`, {default: 'Seq'})}</th>
                            <th scope="col" class={TH}>{$t(`${PLANNER_KEY}.result.assets.asset`, {default: 'Asset'})}</th>
                            <th scope="col" class={TH}>{$t(`${PLANNER_KEY}.result.plan.instruction`, {default: 'Instruction'})}</th>
                            <th scope="col" class="{TH} text-right">{$t(`${PLANNER_KEY}.result.plan.midPrice`, {default: 'Mid price'})}</th>
                            <th scope="col" class="{TH} text-right">{$t(`${PLANNER_KEY}.result.plan.cashDebit`, {default: 'Cash debit'})}</th>
                            <th scope="col" class="{TH} text-right">{$t(`${PLANNER_KEY}.result.plan.fee`, {default: 'Fee'})}</th>
                            <th scope="col" class={TH}><span class="sr-only">{$t(`${PLANNER_KEY}.result.plan.detail`, {default: 'Detail'})}</span></th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                        {#each group.orders as order (order.order_id)}
                            <tr data-testid="pac-planner-plan-order" data-order={order.order_id} data-asset={order.asset_id}>
                                <td class={TD_NUM}>{order.sequence}</td>
                                <th scope="row" class="{TD} text-left font-medium">{assetLabel(order.asset_id)}</th>
                                <td class={TD} data-testid="pac-planner-plan-instruction">{instructionText(order, $t, digits)}</td>
                                <td class={TD_NUM}>{priceText(order.mid_price, $t, digits)}</td>
                                <td class={TD_NUM}>{formatPlannerMoneyPlain(order.cash_debit.amount, order.cash_debit.currency, {digits})}</td>
                                <td class={TD_NUM}>{formatPlannerMoneyPlain(order.fee.amount, order.fee.currency, {digits})}</td>
                                <td class={TD}>
                                    <button type="button" class={BUTTON_LINK} data-testid="pac-planner-plan-order-detail" onclick={() => onorder(order)}>
                                        {$t(`${PLANNER_KEY}.result.plan.detail`, {default: 'Detail'})}
                                    </button>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>
    {/each}

    <p class={HINT}>{$t(`${PLANNER_KEY}.result.plan.privacyHint`, {default: 'Market prices are public; quantities, amounts and charged fees are wealth (privacy).'})}</p>
    <p class={HINT}>{$t(`${PLANNER_KEY}.result.plan.sequenceHint`, {default: 'In the backend sequence order: the interface recalculates nothing.'})}</p>
</div>
