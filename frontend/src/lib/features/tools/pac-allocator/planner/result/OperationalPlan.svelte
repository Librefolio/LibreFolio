<!--
  R9.8: the operational plan, in the backend's sequence. Numbered steps first (cash, transfers,
  deposits, the currency exchanges the user makes), then one table of orders per Broker. R4.9: a
  conversion the Broker makes by itself has no number; it is shown above that Broker's orders and
  on the orders it pays for. Every amount is a backend figure rendered through the planner
  formatters: nothing is added up here.
-->
<script lang="ts">
    import {ArrowRight, Eye} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef, RowAction} from '$lib/components/table/types';
    import type {PlannerDraft} from '../draft.svelte';
    import {formatExactFxRate, formatExactMoneyPlain, formatPlannerMoneyPlain, type CurrencyDigits} from '../format';
    import CurrencyCode from '../shared/CurrencyCode.svelte';
    import HelpTip from '../shared/HelpTip.svelte';
    import PlannerBrokerIcon from '../shared/PlannerBrokerIcon.svelte';
    import type {PacConversion, PacFundingAction, PacOrderRow, PacSolution} from '../types';
    import {BADGE, HINT, NOTICE, STEP_NUMBER} from '../ui';
    import ResultCell, {type ResultCellContent} from './ResultCell.svelte';
    import {automaticConversions, conversionsFor, ordersByBroker, planSteps, type PlanLookup, type PlanSource, type ResultNames} from './model';
    import {withHelpCues} from '../shared/columnHelp';
    import TableColumns from '../shared/TableColumns.svelte';

    interface Props {
        solution: PacSolution;
        names: ResultNames;
        lookup: PlanLookup;
        digits: CurrencyDigits;
        draft: PlannerDraft;
        onorder: (order: PacOrderRow) => void;
    }

    let {solution, names, lookup, digits, draft, onorder}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.plan';
    type FundingKind = 'cash' | 'transfer' | 'deposit';
    const FUNDING_FALLBACKS: Record<FundingKind, string> = {cash: 'Available cash', transfer: 'Transfer', deposit: 'Deposit'};
    const FUNDING_BADGES: Record<FundingKind, string> = {cash: BADGE.neutral, transfer: BADGE.info, deposit: BADGE.success};

    const steps = $derived(planSteps(solution.funding_actions, solution.conversions));
    const groups = $derived(ordersByBroker(solution.order_rows));
    let orderTables = $state<Record<string, DataTable<PacOrderRow> | undefined>>({});
    const otherTables = (brokerId: string) => groups.filter((group) => group.brokerId !== brokerId).map((group) => orderTables[group.brokerId]);
    const assetLabel = (id: string) => [names.ticker(id), names.asset(id)].filter((part) => part).join(' ');
    const paidByAutomaticConversion = (order: PacOrderRow) => conversionsFor(solution.conversions, order).some((action) => action.mode === 'automatic');
    /** An automatic conversion is shown above its Broker's orders; one on a Broker with no order is listed after them, never dropped. */
    const orphanAutomatic = $derived(solution.conversions.filter((action) => action.mode === 'automatic' && !groups.some((group) => group.brokerId === action.broker_id)));
    const cell = (content: ResultCellContent) => ({type: 'custom' as const, component: ResultCell, props: {cell: content}});
    const brokerCell = (brokerId: string, currency: string | null): ResultCellContent => ({type: 'broker', brokerId, label: names.broker(brokerId), broker: draft.broker(brokerId) ?? null, currency});
    const sourceCell = (source: PlanSource): ResultCellContent =>
        source.kind === 'contribution' ? {type: 'contribution', label: source.label, currency: source.currency} : source.brokerId ? brokerCell(source.brokerId, source.currency) : {type: 'broker', brokerId: '', label: source.label, broker: null, currency: source.currency};

    function fundingKind(action: PacFundingAction, source: PlanSource): FundingKind {
        if (source.kind === 'contribution') return 'deposit';
        return source.brokerId === action.destination_broker_id ? 'cash' : 'transfer';
    }

    /** The reason of a funding step; its priority is named only where the user set more than one route. */
    function fundingDetail(action: PacFundingAction): string {
        const reason = $t(`tools.pacAllocator.planner.result.reasons.${action.reason_code}`, {default: 'to pay for the orders of the plan'});
        const route = lookup.fundingRoute(action.funding_route_id);
        if (!route || lookup.fundingChoices(action.destination_broker_id, action.amount.currency) < 2) return reason;
        return $t(`${KEY}.fundingDetail`, {default: '{reason} · priority {priority}', values: {reason, priority: String(route.priority)}});
    }

    const orderColumns = $derived.by((): ColumnDef<PacOrderRow>[] => withHelpCues<PacOrderRow>([
        {
            id: 'asset',
            header: () => $t('tools.pacAllocator.planner.result.assets.asset', {default: 'Asset'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            pinned: 'left',
            minWidth: 180,
            cell: (order) => cell({type: 'asset', assetId: order.asset_id, label: assetLabel(order.asset_id), asset: draft.asset(order.asset_id) ?? null, sequence: order.sequence, orderId: order.order_id, testid: 'pac-planner-plan-order'}),
        },
        {
            id: 'instruction',
            header: () => $t(`${KEY}.instruction`, {default: 'Instruction'}),
            headerTooltip: () => $t(`${KEY}.instructionHelp`, {default: 'What to enter in the order at the Broker.'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            minWidth: 160,
            cell: (order) => cell({type: 'instruction', order, digits, autoConversion: paidByAutomaticConversion(order)}),
        },
        {
            id: 'midPrice',
            header: () => $t(`${KEY}.midPrice`, {default: 'Price'}),
            headerTooltip: () => $t(`${KEY}.midPriceHelp`, {default: 'The Asset price used by the calculation, before the price margin.'}),
            type: 'number',
            sortable: false,
            filterable: false,
            align: 'right',
            minWidth: 110,
            cell: (order) => cell({type: 'price', price: order.mid_price, digits}),
        },
        {
            id: 'cashDebit',
            header: () => $t(`${KEY}.cashDebit`, {default: 'Order amount'}),
            headerTooltip: () => $t(`${KEY}.cashDebitHelp`, {default: 'What the order takes from the Broker cash: the price plus the price margin set in the Routing step, fees excluded.'}),
            type: 'number',
            sortable: false,
            filterable: false,
            align: 'right',
            minWidth: 120,
            cell: (order) => cell({type: 'money', amount: order.cash_debit.amount, currency: order.cash_debit.currency, digits}),
        },
        {
            id: 'fee',
            header: () => $t(`${KEY}.fee`, {default: 'Fee'}),
            headerTooltip: () => $t(`${KEY}.feeHelp`, {default: 'The Broker fee for this order, from the fees set in the Brokers step.'}),
            type: 'number',
            sortable: false,
            filterable: false,
            align: 'right',
            minWidth: 100,
            cell: (order) => cell({type: 'money', amount: order.fee.amount, currency: order.fee.currency, digits}),
        },
    ]));

    const orderActions = $derived.by((): RowAction<PacOrderRow>[] => [
        {id: 'detail', icon: Eye, label: () => $t(`${KEY}.detail`, {default: 'Detail'}), onClick: (order) => onorder(order), testid: 'pac-planner-plan-order-detail'},
    ]);
</script>

{#snippet pair(action: PacConversion)}
    <span class="flex items-center gap-1.5">
        <CurrencyCode code={action.source_debit.currency} />
        <ArrowRight class="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
        <CurrencyCode code={action.destination_credit.currency} />
    </span>
{/snippet}

{#snippet rates(action: PacConversion)}
    <p class="{HINT} tabular-nums">
        {$t(`${KEY}.fxRates`, {
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
{/snippet}

{#snippet autoBox(action: PacConversion, withBroker: boolean)}
    <div class="{NOTICE.info} space-y-1" data-testid="pac-planner-plan-auto-conversion" data-conversion={action.conversion_id}>
        <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
            <div class="flex min-w-0 flex-wrap items-center gap-2">
                <span class={BADGE.info}>{$t(`${KEY}.autoConversion`, {default: 'Automatic conversion'})}</span>
                {#if withBroker}<ResultCell cell={brokerCell(action.broker_id, null)} />{/if}
                {@render pair(action)}
            </div>
            <span class="flex items-center gap-1.5">
                <span class="font-medium tabular-nums" data-testid="pac-planner-plan-auto-conversion-amounts">
                    {$t(`${KEY}.autoConversionAmounts`, {
                        default: 'about {debit} → {credit}',
                        values: {
                            debit: formatPlannerMoneyPlain(action.source_debit.amount, action.source_debit.currency, {digits}),
                            credit: formatPlannerMoneyPlain(action.destination_credit.amount, action.destination_credit.currency, {digits}),
                        },
                    })}
                </span>
                <HelpTip
                    label={$t(`${KEY}.autoConversion`, {default: 'Automatic conversion'})}
                    help={$t(`${KEY}.autoConversionHelp`, {
                        default: 'You do nothing: the Broker converts when you place the orders in {destination}. It takes about this much from your {source} cash; the exact amount depends on its rate at that moment, while the plan uses the rate and spread of the FX step.',
                        values: {source: action.source_debit.currency, destination: action.destination_credit.currency},
                    })}
                    testid="pac-planner-plan-auto-conversion-help"
                />
            </span>
        </div>
        {@render rates(action)}
    </div>
{/snippet}

<div class="space-y-4" data-testid="pac-planner-plan">
    <p class={HINT}>{$t(`${KEY}.sequenceHint`, {default: 'Follow the numbers: first the cash, then the currency exchanges, then the orders.'})}</p>

    {#if steps.length > 0}
        <ol class="divide-y divide-gray-100 rounded-lg border border-gray-200 dark:divide-gray-700 dark:border-gray-700">
            {#each steps as step (step.kind === 'funding' ? step.action.action_id : step.action.conversion_id)}
                <li class="flex items-start gap-3 p-3 text-sm" data-testid="pac-planner-plan-step" data-kind={step.kind} data-sequence={step.sequence}>
                    <span class={STEP_NUMBER}>{step.sequence}</span>
                    {#if step.kind === 'funding'}
                        {@const action = step.action}
                        {@const source = lookup.source(action.source)}
                        {@const kind = fundingKind(action, source)}
                        <div class="min-w-0 flex-1 space-y-1" data-funding={kind}>
                            <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
                                <div class="flex min-w-0 flex-wrap items-center gap-2">
                                    <span class={FUNDING_BADGES[kind]}>{$t(`${KEY}.kind.${kind}`, {default: FUNDING_FALLBACKS[kind]})}</span>
                                    <ResultCell cell={sourceCell(source)} />
                                    {#if kind !== 'cash'}
                                        <ArrowRight class="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
                                        <ResultCell cell={brokerCell(action.destination_broker_id, action.amount.currency)} />
                                    {/if}
                                </div>
                                <span class="font-medium tabular-nums text-gray-900 dark:text-gray-100" data-testid="pac-planner-plan-amount">{formatPlannerMoneyPlain(action.amount.amount, action.amount.currency, {digits})}</span>
                            </div>
                            <p class="{HINT} first-letter:uppercase">{fundingDetail(action)}</p>
                        </div>
                    {:else}
                        {@const action = step.action}
                        <div class="min-w-0 flex-1 space-y-1" data-conversion={action.conversion_id}>
                            <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
                                <div class="flex min-w-0 flex-wrap items-center gap-2">
                                    <span class={BADGE.info}>{$t(`${KEY}.fx`, {default: 'Currency exchange'})}</span>
                                    <ResultCell cell={brokerCell(action.broker_id, null)} />
                                    {@render pair(action)}
                                </div>
                                <span class="flex items-center gap-1.5">
                                    <span class="font-medium tabular-nums text-gray-900 dark:text-gray-100" data-testid="pac-planner-plan-fx-amounts">
                                        {$t(`${KEY}.fxAmounts`, {
                                            default: '{debit} → about {credit}',
                                            values: {
                                                debit: formatPlannerMoneyPlain(action.source_debit.amount, action.source_debit.currency, {digits}),
                                                credit: formatPlannerMoneyPlain(action.destination_credit.amount, action.destination_credit.currency, {digits}),
                                            },
                                        })}
                                    </span>
                                    <HelpTip
                                        label={$t(`${KEY}.fx`, {default: 'Currency exchange'})}
                                        help={$t(`${KEY}.fxEstimateHelp`, {
                                            default: 'Enter the {source} amount in the conversion at the Broker. What you receive in {destination} depends on the rate at that moment: the plan uses the rate and spread of the FX step.',
                                            values: {source: action.source_debit.currency, destination: action.destination_credit.currency},
                                        })}
                                        testid="pac-planner-plan-fx-estimate-help"
                                    />
                                </span>
                            </div>
                            <p class="{HINT} first-letter:uppercase">{$t(`${KEY}.conversionFor`, {default: 'for the orders in {currency}', values: {currency: action.destination_credit.currency}})}</p>
                            {@render rates(action)}
                        </div>
                    {/if}
                </li>
            {/each}
        </ol>
    {/if}

    {#each groups as group (group.brokerId)}
        <section class="space-y-2" data-testid="pac-planner-plan-orders" data-broker={group.brokerId}>
            <div class="flex flex-wrap items-center gap-2">
                <h4 class="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                    <PlannerBrokerIcon broker={draft.broker(group.brokerId)} size={24} />
                    {$t(`${KEY}.ordersAt`, {default: 'Orders on {broker}', values: {broker: names.broker(group.brokerId)}})}
                </h4>
                <TableColumns table={orderTables[group.brokerId]} others={otherTables(group.brokerId)} testid="pac-planner-plan-orders-columns" />
            </div>
            {#each automaticConversions(solution.conversions, group.brokerId) as action (action.conversion_id)}
                {@render autoBox(action, false)}
            {/each}
            <DataTable
                bind:this={orderTables[group.brokerId]}
                data={[...group.orders]}
                columns={orderColumns}
                getRowId={(order) => order.order_id}
                storageKey="pac-planner-result-orders"
                onRowClick={(order) => onorder(order)}
                enableSorting={false}
                enableSelection={false}
                selectionMode="none"
                enablePagination={false}
                enableColumnVisibility
                enableColumnFilters={false}
                enableColumnResize
                enableContextMenu={false}
                enableActions
                rowActions={orderActions}
                actionsColumnWidth="64px"
                tableLayout="auto"
            />
        </section>
    {/each}

    {#each orphanAutomatic as action (action.conversion_id)}
        {@render autoBox(action, true)}
    {/each}
</div>
