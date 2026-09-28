<script lang="ts">
    import {t} from '$lib/i18n';
    import ToolExecutionMetrics from '$lib/features/tools/components/ToolExecutionMetrics.svelte';
    import type {ToolBatchMetrics, ToolItemMetrics} from '$lib/features/tools/contracts';
    import {formatObjectiveValue, formatPlannerPlainDecimal, formatSolverNumber, type CurrencyDigits} from '../format';
    import {OBJECTIVE_FALLBACKS} from '../policies';
    import type {PacObjectiveUnit, PacReadyResult} from '../types';
    import {HINT, TABLE, TD, TD_NUM, TH} from '../ui';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        result: PacReadyResult;
        metrics: ToolItemMetrics;
        batch: ToolBatchMetrics;
        digits: CurrencyDigits;
    }

    let {result, metrics, batch, digits}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.proof';
    const OUTCOME_FALLBACKS = {incumbent_found: 'Plan found', no_op: 'No operation', infeasible_proven: 'Infeasible', no_incumbent: 'No plan found'} as const;
    const STOP_FALLBACKS = {completed: 'Completed', time_limit: 'Time limit', node_limit: 'Node limit'} as const;
    const STATUS_FALLBACKS = {finished: 'finished', unfinished: 'unfinished', infeasible: 'infeasible'} as const;

    const proof = $derived(result.proof);
    const solver = $derived(result.solver_evidence);
    const verified = $derived('primary_solution' in result && result.primary_solution.validation === 'decimal_verified');
    const objectives = $derived('primary_solution' in result ? result.primary_solution.objectives : null);
    const stages = $derived(solver.stages);
    const unfinished = $derived(stages.filter((stage) => stage.status === 'unfinished').length);
    const engines = $derived([...new Set(stages.map((stage) => [stage.engine, stage.version].join(' ')))]);
    const scopes = $derived([...new Set(stages.map((stage) => stage.scope))]);

    const objectiveName = (code: string) => $t(`${PLANNER_KEY}.objectives.${code}`, {default: OBJECTIVE_FALLBACKS[code] ?? code});

    function unitSuffix(unit: PacObjectiveUnit): string {
        if (unit.kind === 'valuation_money') return unit.currency_code;
        if (unit.kind === 'valuation_money_squared') return unit.currency_code + '²';
        return '';
    }

    function scopeText(scope: 'global' | 'incumbent_face'): string {
        return $t(`${KEY}.scopes.${scope}`, {default: scope === 'global' ? 'global scope' : 'incumbent face'});
    }
</script>

<div class="space-y-4 text-sm" data-testid="pac-planner-proof" data-proof={proof.kind} data-solver={solver.kind}>
    <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
        <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.outcome`, {default: 'Outcome'})}</dt>
        <dd data-testid="pac-planner-proof-outcome">
            {$t(`${PLANNER_KEY}.result.outcomes.${result.outcome}`, {default: OUTCOME_FALLBACKS[result.outcome]})}
            {#if verified}
                · {$t(`${KEY}.decimalVerified`, {default: 'plan verified in exact Decimal by the backend'})}
            {/if}
        </dd>

        <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.proof`, {default: 'Proof'})}</dt>
        <dd class="space-y-1" data-testid="pac-planner-proof-kind">
            {#if proof.kind === 'optimal_proven'}
                <p>
                    {$t(`${KEY}.optimal`, {default: 'Proven optimal'})} ·
                    {$t(`${KEY}.sources.solver_status`, {default: 'solver status'})} ·
                    {$t(`${KEY}.tieBreakClosed`, {default: 'tie-break closed'})}
                </p>
                <p class={HINT} data-testid="pac-planner-proof-witness">
                    {$t(`${KEY}.solverWitness`, {
                        default: '{objectives, plural, one {# objective of the cascade} other {# objectives of the cascade}} closed at the optimum by the solver',
                        values: {objectives: proof.witness.objective_codes.length},
                    })}
                </p>
            {:else if proof.kind === 'not_proven'}
                <p>
                    {$t(`${KEY}.notProven`, {default: 'Not proven'})} ·
                    {$t(`tools.pacAllocator.planner.result.proof.reasons.${proof.reason_code}`, {default: 'an exact proof was not established'})}
                </p>
                <p class={HINT}>
                    {#if unfinished === 0}
                        {$t(`${KEY}.floatingFinished`, {default: 'The solver closed every stage, but its plan did not pass the exact Decimal check.'})}
                    {:else}
                        {$t(`${KEY}.floatingUnfinished`, {default: 'The solver stopped before closing every stage: this is the best plan found, not a proven one.'})}
                    {/if}
                </p>
            {:else}
                <p>
                    {$t(`${KEY}.infeasible`, {default: 'Infeasibility proven'})} ·
                    {$t(`${KEY}.sources.solver_status`, {default: 'solver status'})}
                </p>
                <p class={HINT} data-testid="pac-planner-proof-witness">
                    {$t(`${KEY}.solverInfeasibleWitness`, {default: 'The solver closed the first stage as infeasible: no plan meets every hard constraint.'})}
                </p>
            {/if}
        </dd>

        <dt class="font-medium text-gray-600 dark:text-gray-400">{$t(`${KEY}.stop`, {default: 'Stop'})}</dt>
        <dd data-testid="pac-planner-proof-stop">{$t(`${PLANNER_KEY}.result.stop.${result.stop_reason}`, {default: STOP_FALLBACKS[result.stop_reason]})}</dd>
    </dl>

    <div class="space-y-2 border-t border-gray-200 pt-3 dark:border-gray-700" data-testid="pac-planner-solver">
        <p class="font-medium">
            {[$t(`${KEY}.solverStages`, {default: 'Solver stages'}), $t(`${KEY}.reportedFloating`, {default: 'reported in floating point'}), ...engines, ...(scopes.length === 1 ? [scopeText(scopes[0])] : [])].join(' · ')}
        </p>
        <div class="overflow-x-auto">
            <table class={TABLE} data-testid="pac-planner-solver-stages">
                <thead>
                    <tr>
                        <th scope="col" class="{TH} text-right">{$t(`${KEY}.ordinal`, {default: 'Ord'})}</th>
                        <th scope="col" class={TH}>{$t(`${KEY}.objective`, {default: 'Objective'})}</th>
                        <th scope="col" class={TH}>{$t(`${KEY}.status`, {default: 'Status'})}</th>
                        {#if scopes.length > 1}
                            <th scope="col" class={TH}>{$t(`${KEY}.scope`, {default: 'Scope'})}</th>
                        {/if}
                        <th scope="col" class="{TH} text-right">{$t(`${KEY}.primal`, {default: 'Primal'})}</th>
                        <th scope="col" class="{TH} text-right">{$t(`${KEY}.dual`, {default: 'Dual'})}</th>
                        <th scope="col" class="{TH} text-right">{$t(`${KEY}.absoluteGap`, {default: 'Abs. gap'})}</th>
                        <th scope="col" class="{TH} text-right">{$t(`${KEY}.relativeGap`, {default: 'Rel. gap'})}</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                    {#each stages as stage (stage.stage)}
                        <tr data-testid="pac-planner-solver-stage" data-objective={stage.objective_code} data-status={stage.status}>
                            <td class={TD_NUM}>{stage.ordinal}</td>
                            <th scope="row" class="{TD} text-left font-medium">
                                {objectiveName(stage.objective_code)}
                                {#if unitSuffix(stage.unit)}<span class="font-normal text-gray-500 dark:text-gray-400">({unitSuffix(stage.unit)})</span>{/if}
                            </th>
                            <td class={TD}>{$t(`${KEY}.statuses.${stage.status}`, {default: STATUS_FALLBACKS[stage.status]})}</td>
                            {#if scopes.length > 1}
                                <td class={TD}>{scopeText(stage.scope)}</td>
                            {/if}
                            <td class={TD_NUM}>{formatSolverNumber(stage.primal, stage.unit)}</td>
                            <td class={TD_NUM}>{formatSolverNumber(stage.dual, stage.unit)}</td>
                            <td class={TD_NUM}>{formatPlannerPlainDecimal(stage.absolute_gap)}</td>
                            <td class={TD_NUM}>{formatPlannerPlainDecimal(stage.relative_gap)}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    </div>

    {#if objectives}
        <div class="space-y-2 border-t border-gray-200 pt-3 dark:border-gray-700" data-testid="pac-planner-objectives">
            <p class="font-medium">{$t(`${KEY}.exactObjectives`, {default: 'Exact objective values (backend, Decimal)'})}</p>
            <ol class="space-y-1">
                {#each objectives.stages as stage (stage.objective_code)}
                    <li class="flex flex-wrap justify-between gap-2" data-testid="pac-planner-objective" data-objective={stage.objective_code}>
                        <span>{stage.ordinal} · {objectiveName(stage.objective_code)}</span>
                        <span class="tabular-nums">{formatObjectiveValue(stage.value, stage.unit, digits)}</span>
                    </li>
                {/each}
            </ol>
            <p class={HINT}>{$t(`${KEY}.tieBreak`, {default: 'Final tie-break: {code}.', values: {code: objectives.tie_break.code}})}</p>
        </div>
    {/if}

    <div class="border-t border-gray-200 pt-3 dark:border-gray-700">
        <ToolExecutionMetrics item={metrics} {batch} />
    </div>
</div>
