<!--
  How the plan was proven (R9.8). Outcome, proof and stop are three tiles with the badges of the
  header and their explanations; the exact values of the objectives are cards in cascade order,
  with the «?» of Strategy (R11.10); the solver stages in floating point stay on `DataTable`. The
  final tie-break is described, not coded.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import ToolExecutionMetrics from '$lib/features/tools/components/ToolExecutionMetrics.svelte';
    import type {ToolBatchMetrics, ToolItemMetrics} from '$lib/features/tools/contracts';
    import {formatObjectiveValue, formatPlannerPlainDecimal, type CurrencyDigits} from '../format';
    import {OBJECTIVE_FALLBACKS, OBJECTIVE_HELP_FALLBACKS, OBJECTIVE_TIPS} from '../policies';
    import type {PacReadyResult} from '../types';
    import {HINT, ICON_BUBBLE, TILE, TILE_LABEL} from '../ui';
    import BackendTimingBar from './BackendTimingBar.svelte';
    import {resultBadges} from './model';
    import ResultBadgeTip from './ResultBadgeTip.svelte';
    import ResultCell, {type ResultCellContent} from './ResultCell.svelte';
    import {withHelpCues} from '../shared/columnHelp';
    import HelpTip from '../shared/HelpTip.svelte';
    import TableColumns from '../shared/TableColumns.svelte';

    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        result: PacReadyResult;
        metrics: ToolItemMetrics;
        batch: ToolBatchMetrics;
        digits: CurrencyDigits;
    }

    let {result, metrics, batch, digits}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.proof';
    const STATUS_FALLBACKS = {finished: 'finished', unfinished: 'unfinished', infeasible: 'infeasible'} as const;
    const STATUS_VARIANTS = {finished: 'success', unfinished: 'warning', infeasible: 'error'} as const;
    const HELP_FALLBACKS = {
        status: 'Whether the solver closed this stage. Finished: it proved the best value. Unfinished: it stopped at a limit. After a stage that stopped, the later ones only searched among plans as good as the one already found, so a gap of 0 there proves nothing.',
        primal: 'The value of the best plan the solver found for this stage.',
        dual: 'The bound the solver proved for this stage: none of the plans it searched can do better. From the second stage on, it searched only among plans as good as the chosen one on the stages above.',
        absoluteGap: 'Distance between the two values. A gap of 0 proves the best value only when the stage is finished.',
        relativeGap: 'The same distance, as a fraction of the value.',
    } as const;

    type Stage = PacReadyResult['solver_evidence']['stages'][number];
    let stagesTable = $state<DataTable<Stage>>();

    const proof = $derived(result.proof);
    const solver = $derived(result.solver_evidence);
    const badges = $derived(resultBadges(result));
    const outcomeBadges = $derived(badges.filter((badge) => badge.id === 'availability' || badge.id === 'validation'));
    const proofBadge = $derived(badges.find((badge) => badge.id === 'proof'));
    const stopBadge = $derived(badges.find((badge) => badge.id === 'stop'));
    const objectives = $derived('primary_solution' in result ? result.primary_solution.objectives : null);
    const stages = $derived(solver.stages);
    const engines = $derived([...new Set(stages.map((stage) => [stage.engine, stage.version].join(' ')))]);
    const scopes = $derived([...new Set(stages.map((stage) => stage.scope))]);

    const objectiveName = (code: string) => $t(`${PLANNER_KEY}.objectives.${code}`, {default: OBJECTIVE_FALLBACKS[code] ?? code});
    const cell = (content: ResultCellContent) => ({type: 'custom' as const, component: ResultCell, props: {cell: content}});
    const help = (key: keyof typeof HELP_FALLBACKS) => () => $t(`${KEY}.help.${key}`, {default: HELP_FALLBACKS[key]});
    const numberColumn = (id: string, header: string, value: (stage: Stage) => ResultCellContent | string, tooltip?: () => string): ColumnDef<Stage> => ({
        id,
        header: () => header,
        headerTooltip: tooltip,
        type: 'number',
        sortable: false,
        filterable: false,
        align: 'right',
        cell: (stage) => {
            const content = value(stage);
            return typeof content === 'string' ? content : cell(content);
        },
    });

    function scopeText(scope: 'global' | 'incumbent_face'): string {
        return $t(`${KEY}.scopes.${scope}`, {default: scope === 'global' ? 'all plans' : 'only plans as good as the one found'});
    }

    interface ObjectiveHelp {
        help: string;
        math: boolean;
        spoken?: string;
    }

    /** The «?» of an objective card: the longer explanation of Strategy where there is one, otherwise its one-line help. */
    function objectiveHelp(code: string): ObjectiveHelp {
        const tip = OBJECTIVE_TIPS[code];
        if (tip) return {help: $t(tip.key, {default: tip.fallback}), math: tip.math ?? false, spoken: tip.spoken ? $t(tip.spoken.key, {default: tip.spoken.fallback}) : undefined};
        return {help: OBJECTIVE_HELP_FALLBACKS[code] ? $t(`${PLANNER_KEY}.objectiveHelp.${code}`, {default: OBJECTIVE_HELP_FALLBACKS[code]}) : '', math: false};
    }

    const stageColumns = $derived.by((): ColumnDef<Stage>[] => withHelpCues<Stage>([
        {
            id: 'objective',
            header: () => $t(`${KEY}.objective`, {default: 'Objective'}),
            type: 'custom',
            sortable: false,
            filterable: false,
            pinned: 'left',
            minWidth: 200,
            cell: (stage) => cell({type: 'label', text: objectiveName(stage.objective_code), sequence: stage.ordinal, testid: 'pac-planner-solver-stage', attrs: {'data-objective': stage.objective_code, 'data-status': stage.status}}),
        },
        {
            id: 'status',
            header: () => $t(`${KEY}.status`, {default: 'Status'}),
            headerTooltip: help('status'),
            type: 'text',
            sortable: false,
            filterable: false,
            cell: (stage) => ({type: 'badge', text: $t(`${KEY}.statuses.${stage.status}`, {default: STATUS_FALLBACKS[stage.status]}), variant: STATUS_VARIANTS[stage.status]}),
        },
        ...(scopes.length > 1
            ? [
                  {
                      id: 'scope',
                      header: () => $t(`${KEY}.scope`, {default: 'Scope'}),
                      type: 'text',
                      sortable: false,
                      filterable: false,
                      cell: (stage: Stage) => scopeText(stage.scope),
                  } satisfies ColumnDef<Stage>,
              ]
            : []),
        numberColumn('primal', $t(`${KEY}.primal`, {default: 'Primal'}), (stage) => ({type: 'solver', value: stage.primal, unit: stage.unit, digits}), help('primal')),
        numberColumn('dual', $t(`${KEY}.dual`, {default: 'Dual'}), (stage) => ({type: 'solver', value: stage.dual, unit: stage.unit, digits}), help('dual')),
        numberColumn('absoluteGap', $t(`${KEY}.absoluteGap`, {default: 'Abs. gap'}), (stage) => ({type: 'solver', value: stage.absolute_gap, unit: stage.unit, digits}), help('absoluteGap')),
        numberColumn('relativeGap', $t(`${KEY}.relativeGap`, {default: 'Rel. gap'}), (stage) => formatPlannerPlainDecimal(stage.relative_gap), help('relativeGap')),
    ]));

    const TABLE_PROPS = {
        enableSorting: false,
        enableSelection: false,
        selectionMode: 'none',
        enableActions: false,
        enablePagination: false,
        enableColumnVisibility: true,
        enableColumnFilters: false,
        enableColumnResize: true,
        enableContextMenu: false,
        tableLayout: 'auto',
    } as const;
</script>

<div class="space-y-4 text-sm" data-testid="pac-planner-proof" data-proof={proof.kind} data-solver={solver.kind}>
    <!-- R11.10: the badges of the header, one tile per question, each with its explanation. -->
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-3" data-testid="pac-planner-proof-facts">
        <div class="{TILE} space-y-2" data-testid="pac-planner-proof-outcome">
            <p class={TILE_LABEL}>{$t(`${KEY}.outcome`, {default: 'Outcome'})}</p>
            <div class="flex flex-wrap gap-1.5">
                {#each outcomeBadges as badge (badge.id)}
                    <ResultBadgeTip {badge} />
                {/each}
            </div>
        </div>

        <div class="{TILE} space-y-2" data-testid="pac-planner-proof-kind">
            <p class={TILE_LABEL}>{$t(`${KEY}.proof`, {default: 'Proof'})}</p>
            {#if proofBadge}
                <div class="flex flex-wrap gap-1.5"><ResultBadgeTip badge={proofBadge} /></div>
            {/if}
            {#if proof.kind === 'optimal_proven'}
                <p class={HINT} data-testid="pac-planner-proof-witness">
                    {$t(`${KEY}.solverWitness`, {
                        default: '{objectives, plural, one {# objective of the cascade} other {# objectives of the cascade}} closed at the optimum by the solver',
                        values: {objectives: proof.witness.objective_codes.length},
                    })}
                </p>
            {:else if proof.kind === 'not_proven'}
                <!-- Not proven: either a stage is still open, or every stage closed but the final exact check contradicted the solver's bounds; the badge help says which. -->
                <p class="{HINT} first-letter:uppercase" data-testid="pac-planner-proof-reason">
                    {$t(`tools.pacAllocator.planner.result.proof.reasons.${proof.reason_code}`, {default: 'an exact proof was not established'})}
                </p>
            {/if}
            <!-- Infeasibility proven: the witness is the badge's own explanation, and the state notice above says it in full. -->
        </div>

        <div class="{TILE} space-y-2" data-testid="pac-planner-proof-stop">
            <p class={TILE_LABEL}>{$t(`${KEY}.stop`, {default: 'Stop'})}</p>
            {#if stopBadge}
                <div class="flex flex-wrap gap-1.5"><ResultBadgeTip badge={stopBadge} /></div>
            {/if}
        </div>
    </div>

    {#if objectives}
        <div class="space-y-2 border-t border-gray-200 pt-3 dark:border-gray-700" data-testid="pac-planner-objectives">
            <p class="font-medium text-gray-900 dark:text-gray-100">{$t(`${KEY}.exactObjectives`, {default: 'Exact objective values (backend, Decimal)'})}</p>
            <!-- R11.10: one card per objective, in cascade order, with the «?» of Strategy. -->
            <ol class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {#each objectives.stages as stage (stage.objective_code)}
                    {@const tip = objectiveHelp(stage.objective_code)}
                    <li class="{TILE} flex items-start gap-3" data-testid="pac-planner-objective" data-objective={stage.objective_code}>
                        <span class="{ICON_BUBBLE} text-xs font-semibold" aria-hidden="true">{stage.ordinal}</span>
                        <div class="min-w-0 flex-1">
                            <div class="flex flex-wrap items-center gap-0.5 font-medium text-gray-900 dark:text-gray-100">
                                <span>{objectiveName(stage.objective_code)}</span>
                                {#if tip.help}
                                    <HelpTip label={objectiveName(stage.objective_code)} help={tip.help} math={tip.math} spoken={tip.spoken} testid="pac-planner-objective-help" />
                                {/if}
                            </div>
                            <p class="mt-1 break-words text-lg font-semibold tabular-nums text-gray-900 dark:text-gray-100" data-testid="pac-planner-objective-value">
                                {formatObjectiveValue(stage.value, stage.unit, digits)}
                            </p>
                        </div>
                    </li>
                {/each}
            </ol>
            <p class={HINT} data-testid="pac-planner-proof-tie-break">
                <span class="font-medium">{$t(`${PLANNER_KEY}.strategy.tieBreakTitle`, {default: 'Final tie-break'})}</span> ·
                {$t(`${PLANNER_KEY}.strategy.tieBreak`, {
                    default: 'If a tie is still left, a fixed order of Assets and Brokers decides. A search that ends by itself always gives the same plan for the same data; one stopped by a time or node limit may give a different plan.',
                })}
            </p>
        </div>
    {/if}

    <div class="space-y-2 border-t border-gray-200 pt-3 dark:border-gray-700" data-testid="pac-planner-solver">
        <div class="flex flex-wrap items-center gap-2">
            <p class="font-medium text-gray-900 dark:text-gray-100">
                {[$t(`${KEY}.solverStages`, {default: 'Solver stages'}), $t(`${KEY}.reportedFloating`, {default: 'reported in floating point'}), ...engines, ...(scopes.length === 1 ? [scopeText(scopes[0])] : [])].join(' · ')}
            </p>
            <TableColumns table={stagesTable} testid="pac-planner-solver-stages-columns" />
        </div>
        <div data-testid="pac-planner-solver-stages">
            <DataTable bind:this={stagesTable} data={stages} columns={stageColumns} getRowId={(stage) => String(stage.stage)} storageKey="pac-planner-result-solver-stages" {...TABLE_PROPS} />
        </div>
    </div>

    <div class="space-y-3 border-t border-gray-200 pt-3 dark:border-gray-700">
        <ToolExecutionMetrics item={metrics} {batch} />
        <!-- R10.9: local to the PAC; the shared box belongs to the platform. -->
        <BackendTimingBar {metrics} />
    </div>
</div>
