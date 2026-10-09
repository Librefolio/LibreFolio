<script lang="ts">
    import {t} from '$lib/i18n';
    import {formatExactMoneyPlain, formatPlannerMoneyPlain, type CurrencyDigits} from '../format';
    import type {PacReadyResult, PacResolvedRequest, PacRoundingTopUp, PlannerStep} from '../types';
    import {BUTTON_LINK, BUTTON_SECONDARY, HINT, NOTICE} from '../ui';
    import {requiredMinimumRoutes, type ResultNames} from './model';
    import {routeMinimumText} from './text';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        result: PacReadyResult;
        request: PacResolvedRequest;
        names: ResultNames;
        digits: CurrencyDigits;
        ongoto: (step: PlannerStep) => void;
        onedit: () => void;
    }

    let {result, request, names, digits, ongoto, onedit}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.states';
    const limited = $derived(result.result_state === 'ready_incumbent' && result.stop_reason !== 'completed');
    const stages = $derived(result.solver_evidence.stages);
    const finished = $derived(stages.filter((stage) => stage.status === 'finished').length);
    const minimums = $derived(result.result_state === 'ready_infeasible' ? requiredMinimumRoutes(request) : []);
    // Cash the plan still needs per pool because every posting rounds against the plan (QX1-b): computed by the backend.
    const topUps: PacRoundingTopUp[] = $derived('primary_solution' in result ? result.primary_solution.rounding_top_ups : []);
    const assetLabel = (id: string) => [names.ticker(id), names.asset(id)].filter((part) => part).join(' ');
    const goToLabel = (step: PlannerStep, fallback: string) => $t(`${PLANNER_KEY}.actions.goTo`, {default: 'Go to {step}', values: {step: $t(`${PLANNER_KEY}.steps.${step}`, {default: fallback})}});
</script>

{#if result.result_state === 'ready_no_op'}
    <div class="{NOTICE.info} space-y-2" role="status" data-testid="pac-planner-state" data-state="no_op">
        <p class="font-semibold">{$t(`${KEY}.noOp.title`, {default: 'No operation'})}</p>
        <p>
            {$t(`${KEY}.noOp.body`, {
                default: 'With {amount} no purchase meets the constraints: the plan is to do nothing.',
                values: {amount: formatExactMoneyPlain(result.primary_solution.accounting.selected_funding, {digits})},
            })}
        </p>
        <p>{$t(`${KEY}.noOp.empty`, {default: 'No order, no FX, no funding.'})}</p>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-state-edit" onclick={onedit}>{$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}</button>
    </div>
{:else if limited}
    <div class="{NOTICE.warning} space-y-2" role="status" data-testid="pac-planner-state" data-state="limit" data-stop={result.stop_reason}>
        <p>
            {result.stop_reason === 'time_limit' ? $t(`${KEY}.limit.time`, {default: 'The solver stopped at the time limit with a valid plan. A better one may exist.'}) : $t(`${KEY}.limit.node`, {default: 'The solver stopped at the node limit with a valid plan. A better one may exist.'})}
        </p>
        <p class="tabular-nums">
            {$t(`${KEY}.limit.stages`, {
                default: 'Stages: {finished} finished · {unfinished} unfinished · no certified gap.',
                values: {finished, unfinished: stages.length - finished},
            })}
        </p>
        <div class="flex flex-wrap items-center gap-3">
            <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-state-edit" onclick={onedit}>{$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}</button>
            <span class={HINT}>{$t(`${KEY}.limit.complete`, {default: 'The result below stays complete and can be consulted.'})}</span>
        </div>
    </div>
{:else if result.result_state === 'ready_infeasible'}
    <div class="{NOTICE.danger} space-y-3" role="alert" data-testid="pac-planner-state" data-state="infeasible" data-proof-source={result.proof.proof_source}>
        <p class="font-semibold">{$t(`${KEY}.infeasible.title`, {default: 'Infeasible with these constraints'})}</p>
        <p>{$t(`${KEY}.infeasible.body`, {default: 'Proven: no combination meets every hard constraint together.'})}</p>
        <div class="space-y-1">
            <p class="font-medium">{$t(`${KEY}.infeasible.constraints`, {default: 'Hard constraints involved (from the request; caps and minimums masked with privacy on):'})}</p>
            <ul class="space-y-1" data-testid="pac-planner-state-constraints">
                {#each minimums as route (route.route_id)}
                    <li class="flex flex-wrap items-center justify-between gap-2" data-testid="pac-planner-state-constraint" data-kind="required_minimum" data-route={route.route_id}>
                        <span>
                            {$t(`${KEY}.infeasible.minimum`, {
                                default: '{asset} · {broker}: required minimum {minimum}',
                                values: {asset: assetLabel(route.asset_id), broker: names.broker(route.broker_id), minimum: routeMinimumText(route.required_minimum, $t, digits)},
                            })}
                        </span>
                        <button type="button" class={BUTTON_LINK} data-testid="pac-planner-state-goto" onclick={() => ongoto('routing')}>{goToLabel('routing', 'Routing')}</button>
                    </li>
                {/each}
                <li class="flex flex-wrap items-center justify-between gap-2" data-testid="pac-planner-state-constraint" data-kind="reachable_funding">
                    <span>{$t(`${KEY}.infeasible.funding`, {default: 'Liquidity reachable: {amount}', values: {amount: formatExactMoneyPlain(result.scenario_basis.reachable_funding, {digits})}})}</span>
                    <button type="button" class={BUTTON_LINK} data-testid="pac-planner-state-goto" onclick={() => ongoto('liquidity')}>{goToLabel('liquidity', 'Liquidity')}</button>
                </li>
            </ul>
        </div>
        <p class={HINT}>{$t(`${KEY}.infeasible.note`, {default: 'The interface does not choose which constraint to relax: it lists them. No partial plan is shown as valid.'})}</p>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-state-edit" onclick={onedit}>{$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}</button>
    </div>
{:else if result.result_state === 'ready_no_incumbent'}
    <div class="{NOTICE.warning} space-y-2" role="alert" data-testid="pac-planner-state" data-state="no_incumbent" data-stop={result.stop_reason}>
        <p class="font-semibold">{$t(`${KEY}.noIncumbent.title`, {default: 'No plan within the limits'})}</p>
        <p>{$t(`${KEY}.noIncumbent.body`, {default: 'The solver found no plan before the limit. This is not a proof that no plan exists.'})}</p>
        <p>{$t(`${KEY}.noIncumbent.tips`, {default: 'To reduce the search: fewer Assets or routes, tighter caps, larger steps.'})}</p>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-state-edit" onclick={onedit}>{$t(`${PLANNER_KEY}.actions.editConfiguration`, {default: 'Edit configuration'})}</button>
    </div>
{/if}

{#if topUps.length > 0}
    <div class="{NOTICE.warning} space-y-1" role="status" data-testid="pac-planner-top-up">
        {#each topUps as row (`${row.broker_id}:${row.currency}`)}
            <p data-testid="pac-planner-top-up-row" data-broker={row.broker_id} data-currency={row.currency}>
                {$t(`${KEY}.topUp.row`, {
                    default: 'To execute the plan you need {amount} more on {broker} ({currency}), because of rounding to the minimum unit.',
                    values: {amount: formatPlannerMoneyPlain(row.amount, row.currency, {digits}), broker: names.broker(row.broker_id), currency: row.currency},
                })}
            </p>
        {/each}
    </div>
{/if}
