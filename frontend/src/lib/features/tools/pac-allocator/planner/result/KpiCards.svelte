<script lang="ts">
    import {t} from '$lib/i18n';
    import {formatExactMoneyPlain, formatObjectiveValue, type CurrencyDigits} from '../format';
    import type {PacExactMoney, PacSolution} from '../types';
    import {CARD, HINT} from '../ui';
    import {objectiveStage} from './model';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        solution: PacSolution;
        digits: CurrencyDigits;
    }

    let {solution, digits}: Props = $props();

    const accounting = $derived(solution.accounting);
    const explicitCost = $derived(objectiveStage(solution.objectives.stages, 'explicit_cost'));
    const money = (value: PacExactMoney) => formatExactMoneyPlain(value, {digits});
</script>

<section class={CARD} aria-label={$t(`${PLANNER_KEY}.result.kpi.title`, {default: 'Key figures'})} data-testid="pac-planner-kpi">
    <dl class="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
        <div data-testid="pac-planner-kpi-item" data-kpi="fixed_reference">
            <dt class={HINT}>{$t(`${PLANNER_KEY}.result.kpi.fixedReference`, {default: 'Fixed reference'})}</dt>
            <dd class="mt-1 text-base font-semibold tabular-nums">{money(accounting.fixed_reference)}</dd>
        </div>
        <div data-testid="pac-planner-kpi-item" data-kpi="final_invested">
            <dt class={HINT}>{$t(`${PLANNER_KEY}.result.kpi.finalInvested`, {default: 'Invested after'})}</dt>
            <dd class="mt-1 text-base font-semibold tabular-nums">{money(accounting.final_invested)}</dd>
        </div>
        <div data-testid="pac-planner-kpi-item" data-kpi="shortfall">
            <dt class={HINT}>{$t(`${PLANNER_KEY}.result.kpi.shortfall`, {default: 'Not invested (U)'})}</dt>
            <dd class="mt-1 text-base font-semibold tabular-nums">{money(accounting.shortfall)}</dd>
        </div>
        <div data-testid="pac-planner-kpi-item" data-kpi="explicit_cost">
            <dt class={HINT}>{$t(`${PLANNER_KEY}.result.kpi.explicitCost`, {default: 'Explicit costs'})}</dt>
            <dd class="mt-1 text-base font-semibold tabular-nums">{explicitCost ? formatObjectiveValue(explicitCost.value, explicitCost.unit, digits) : '—'}</dd>
        </div>
        <div data-testid="pac-planner-kpi-item" data-kpi="orders">
            <dt class={HINT}>{$t(`${PLANNER_KEY}.result.kpi.orders`, {default: 'Orders'})}</dt>
            <dd class="mt-1 text-base font-semibold tabular-nums">{solution.order_rows.length}</dd>
        </div>
    </dl>
    <p class="mt-3 text-sm text-gray-700 dark:text-gray-300" data-testid="pac-planner-kpi-shortfall-parts">
        {$t(`${PLANNER_KEY}.result.kpi.shortfallParts`, {
            default: 'U = free cash {free} + economic losses {losses} + rounding {rounding}',
            values: {free: money(accounting.free_cash), losses: money(accounting.economic_losses), rounding: money(accounting.rounding_delta)},
        })}
    </p>
    <p class="mt-1 text-sm text-gray-700 dark:text-gray-300" data-testid="pac-planner-kpi-funding">
        {$t(`${PLANNER_KEY}.result.kpi.funding`, {
            default: 'Funding selected {selected} · reachable {reachable} · trapped {trapped}',
            values: {selected: money(accounting.selected_funding), reachable: money(accounting.reachable_funding), trapped: money(accounting.trapped_funding)},
        })}
    </p>
    <p class="mt-1 {HINT}">{$t(`${PLANNER_KEY}.result.kpi.source`, {default: 'Every figure comes from the backend accounting; the interface adds nothing up.'})}</p>
</section>
