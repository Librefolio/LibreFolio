<script lang="ts">
    import {t, locale} from '$lib/i18n';
    import OriginBadge from '../shared/OriginBadge.svelte';
    import PlannerDialog from '../shared/PlannerDialog.svelte';
    import {formatExactFxRate, formatExactMoneyPlain, formatExactQuantity, formatExactPricePlain, formatPlannerDate, formatPlannerMoneyPlain, formatPlannerTimestamp, type CurrencyDigits} from '../format';
    import type {PacFxAction, PacOrderRow} from '../types';
    import {BUTTON_LINK, BUTTON_SECONDARY, HINT} from '../ui';
    import type {PacProvenanceRow, PlanLookup, ResultNames} from './model';
    import {instructionStepText, instructionText, priceText, ratePercentText, routeCapText, routeMinimumText} from './text';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        order: PacOrderRow | null;
        fxActions: readonly PacFxAction[];
        names: ResultNames;
        lookup: PlanLookup;
        digits: CurrencyDigits;
        onclose: () => void;
    }

    let {order, fxActions, names, lookup, digits, onclose}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.detail';
    let showProvenance = $state(false);

    const route = $derived(order ? lookup.route(order.route_id) : null);
    const quote = $derived(order ? lookup.quote(order.asset_id) : null);
    const quoteOrigin = $derived(quote ? lookup.provenance(quote.provenance_id) : null);
    const conversions = $derived(order ? fxActions.filter((action) => action.order_route_id === order.route_id) : []);
    const provenance = $derived(order ? order.provenance_ids.map((id) => lookup.provenance(id)).filter((row): row is PacProvenanceRow => row !== null) : []);
    const assetLabel = $derived(order ? [names.ticker(order.asset_id), names.asset(order.asset_id)].filter((part) => part).join(' ') : '');
    const title = $derived(order ? $t(`${KEY}.title`, {default: 'Order {sequence} · {asset} · {broker} · {currency}', values: {sequence: order.sequence, asset: assetLabel, broker: names.broker(order.broker_id), currency: order.cash_debit.currency}}) : '');

    function provenanceLabel(row: PacProvenanceRow): string {
        if (row.kind === 'manual') return row.label;
        return row.source_label ?? $t(`${PLANNER_KEY}.result.domains.${row.domain}`, {default: row.domain});
    }

    function provenanceWhen(row: PacProvenanceRow): string {
        return formatPlannerTimestamp(row.kind === 'manual' ? row.entered_at : row.captured_at, $locale);
    }

    $effect(() => {
        if (!order) showProvenance = false;
    });
</script>

<PlannerDialog open={order !== null} {title} testid="pac-planner-order-detail" {onclose} maxWidth="3xl">
    {#if order}
        <dl class="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-[auto_1fr_auto_1fr]" data-testid="pac-planner-order-detail-facts">
            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.instruction`, {default: 'Instruction'})}</dt>
            <dd data-testid="pac-planner-order-detail-instruction">{[instructionText(order, $t, digits), instructionStepText(order, $t, digits)].join(' · ')}</dd>
            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.economicQuantity`, {default: 'Economic quantity'})}</dt>
            <dd>
                {order.economic_quantity.kind === 'exact'
                    ? $t(`${KEY}.quantityExact`, {default: '{quantity} units (exact)', values: {quantity: formatExactQuantity(order.economic_quantity.value)}})
                    : $t(`${KEY}.quantityEstimated`, {default: '{quantity} units (estimated)', values: {quantity: formatExactQuantity(order.economic_quantity.value)}})}
            </dd>

            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.sourcePrice`, {default: 'Source price'})}</dt>
            <dd class="tabular-nums">{priceText(order.source_price, $t, digits)}</dd>
            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.priceDate`, {default: 'Price date'})}</dt>
            <dd class="flex flex-wrap items-center gap-2" data-testid="pac-planner-order-detail-price-date">
                {#if quote}
                    <span>{formatPlannerDate(quote.reference_date, $locale)}</span>
                    {#if quote.freshness.kind === 'stale'}
                        <span class={HINT}>{$t(`${KEY}.staleQuote`, {default: '{count, plural, one {# day} other {# days}} old · accepted', values: {count: quote.freshness.age_days}})}</span>
                    {/if}
                    {#if quoteOrigin}
                        <OriginBadge origin={quoteOrigin.kind === 'manual' ? 'manual' : 'copied'} />
                    {/if}
                {:else}
                    <span>—</span>
                {/if}
            </dd>

            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.midPrice`, {default: 'Mid price'})}</dt>
            <dd class="tabular-nums">{formatExactPricePlain(order.mid_price, digits)}</dd>
            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.chargePrice`, {default: 'Charge price'})}</dt>
            <dd class="tabular-nums">
                {route ? $t(`${KEY}.chargeWithMargin`, {default: '{price} · margin {margin}', values: {price: formatExactPricePlain(order.charge_price, digits), margin: ratePercentText(route.execution_margin_rate)}}) : formatExactPricePlain(order.charge_price, digits)}
            </dd>

            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.midValue`, {default: 'Mid value'})}</dt>
            <dd class="tabular-nums">{formatExactMoneyPlain(order.mid_value, {digits})}</dd>
            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.marginCost`, {default: 'Margin cost'})}</dt>
            <dd class="tabular-nums">{formatExactMoneyPlain(order.execution_margin_cost, {digits})}</dd>

            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.cashDebit`, {default: 'Cash debit'})}</dt>
            <dd class="tabular-nums">{formatPlannerMoneyPlain(order.cash_debit.amount, order.cash_debit.currency, {digits})}</dd>
            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.fee`, {default: 'Fee'})}</dt>
            <dd class="tabular-nums">{formatPlannerMoneyPlain(order.fee.amount, order.fee.currency, {digits})}</dd>

            {#each conversions as action (action.action_id)}
                <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.conversion`, {default: 'Conversion'})}</dt>
                <dd data-testid="pac-planner-order-detail-conversion">
                    {$t(`${KEY}.conversionAction`, {
                        default: 'action {sequence} · {source} → {destination} · 1 {source} = {rate} {destination} effective',
                        values: {sequence: action.sequence, source: action.effective_rate.source_currency, destination: action.effective_rate.destination_currency, rate: formatExactFxRate(action.effective_rate.value)},
                    })}
                </dd>
                <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.spreadLoss`, {default: 'Spread loss'})}</dt>
                <dd class="tabular-nums">{formatExactMoneyPlain(action.spread_loss, {digits})}</dd>
            {/each}

            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.route`, {default: 'Route'})}</dt>
            <dd data-testid="pac-planner-order-detail-route">
                {route ? $t(`${KEY}.routeFacts`, {default: 'priority {priority} · cap {cap}', values: {priority: route.priority, cap: routeCapText(route.cap, $t, digits)}}) : '—'}
            </dd>
            <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.minimums`, {default: 'Minimums'})}</dt>
            <dd data-testid="pac-planner-order-detail-minimums">
                {#if !route}
                    —
                {:else if route.minimum_if_active.kind === 'none' && route.required_minimum.kind === 'none'}
                    {$t(`${PLANNER_KEY}.result.text.none`, {default: 'none'})}
                {:else}
                    {$t(`${KEY}.minimumFacts`, {
                        default: 'if active {ifActive} · required {required}',
                        values: {ifActive: routeMinimumText(route.minimum_if_active, $t, digits), required: routeMinimumText(route.required_minimum, $t, digits)},
                    })}
                {/if}
            </dd>
        </dl>

        <div class="space-y-2 border-t border-gray-200 pt-3 dark:border-gray-700">
            <button type="button" class={BUTTON_LINK} aria-expanded={showProvenance} data-testid="pac-planner-order-detail-provenance-toggle" onclick={() => (showProvenance = !showProvenance)}>
                {showProvenance ? $t(`${KEY}.hideProvenance`, {default: 'Hide provenance'}) : $t(`${KEY}.showProvenance`, {default: 'Show provenance ({count})', values: {count: provenance.length}})}
            </button>
            {#if showProvenance}
                <ul class="space-y-1" data-testid="pac-planner-order-detail-provenance">
                    {#each provenance as row (row.provenance_id)}
                        <li class="flex flex-wrap items-center gap-2" data-provenance={row.provenance_id}>
                            <OriginBadge origin={row.kind === 'manual' ? 'manual' : 'copied'} when={provenanceWhen(row)} />
                            <span>{provenanceLabel(row)}</span>
                        </li>
                    {/each}
                </ul>
            {/if}
        </div>
    {/if}
    {#snippet footer()}
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-order-detail-done" onclick={onclose}>{$t('common.close', {default: 'Close'})}</button>
    {/snippet}
</PlannerDialog>
