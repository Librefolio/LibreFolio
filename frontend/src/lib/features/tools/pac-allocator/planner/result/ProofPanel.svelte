<!--
  How the plan was proven (R9.8). Outcome, proof and stop are three tiles with the badges of the
  header and their explanations; the exact values of the objectives are cards in cascade order,
  with the «?» of Strategy (R11.10); the solver stages in floating point stay on `DataTable`. The
  final tie-break is described, not coded.
-->
<script lang="ts">
    import {MediaQuery} from 'svelte/reactivity';
    import {t} from '$lib/i18n';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {ColumnDef} from '$lib/components/table/types';
    import ToolExecutionMetrics from '$lib/features/tools/components/ToolExecutionMetrics.svelte';
    import type {ToolBatchMetrics, ToolItemMetrics} from '$lib/features/tools/contracts';
    import {exactDisplay, formatExactMoneyPlain, formatObjectiveValue, formatPlannerPlainDecimal, type CurrencyDigits} from '../format';
    import {isTieBreak, OBJECTIVE_HELP_FALLBACKS, OBJECTIVE_TIPS, objectiveNameKey} from '../policies';
    import type {PlannerReadyResult, RebalancerSolution} from '../types';
    import {HINT, ICON_BUBBLE, TILE, TILE_LABEL} from '../ui';
    import BackendTimingBar from './BackendTimingBar.svelte';
    import {proofStatusHelpKey, resultBadges} from './model';
    import ResultBadgeTip from './ResultBadgeTip.svelte';
    import ResultCell, {type ResultCellContent} from './ResultCell.svelte';
    import {withHelpCues} from '../shared/columnHelp';
    import HelpTip from '../shared/HelpTip.svelte';
    import TableColumns from '../shared/TableColumns.svelte';
    import {getPlannerProfile, storageKey, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        result: PlannerReadyResult;
        metrics: ToolItemMetrics;
        batch: ToolBatchMetrics;
        digits: CurrencyDigits;
    }

    let {result, metrics, batch, digits}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.proof';
    const STATUS_FALLBACKS = {finished: 'finished', unfinished: 'unfinished', infeasible: 'infeasible'} as const;
    const STATUS_VARIANTS = {finished: 'success', unfinished: 'warning', infeasible: 'error'} as const;
    const STATUS_HELP_FALLBACKS = {
        pac: 'Whether the solver closed this stage. Finished: it proved the best value. Unfinished: it stopped at a limit. After a stage that stopped, the later ones only searched among plans as good as the one already found, so a gap of 0 there proves nothing.',
        rebalancer:
            'Whether the solver closed this stage. Finished: it proved the best value. Unfinished: it stopped at the time limit, or, for a tie-break, its plan was set aside because it was no better, in exact arithmetic, on the objectives above. After a stage that stopped, the later ones only searched among plans as good as the one already found, so a gap of 0 there proves nothing.',
    } as const;
    const HELP_FALLBACKS = {
        primal: 'The value of the best plan the solver found for this stage.',
        dual: 'The bound the solver proved for this stage: none of the plans it searched can do better. From the second stage on, it searched only among plans as good as the chosen one on the stages above.',
        absoluteGap: 'Distance between the two values. A gap of 0 proves the best value only when the stage is finished.',
        relativeGap: 'The same distance, as a fraction of the value.',
    } as const;

    type Stage = PlannerReadyResult['solver_evidence']['stages'][number];
    let stagesTable = $state<DataTable<Stage>>();

    const proof = $derived(result.proof);
    const solver = $derived(result.solver_evidence);
    const badges = $derived(resultBadges(result, profile.text, digits));
    const outcomeBadges = $derived(badges.filter((badge) => badge.id === 'availability' || badge.id === 'validation'));
    const proofBadge = $derived(badges.find((badge) => badge.id === 'proof'));
    const stopBadge = $derived(badges.find((badge) => badge.id === 'stop'));
    const objectives = $derived('primary_solution' in result ? result.primary_solution.objectives : null);
    /** The objective cards: the Rebalancer's objective (the score, or the distance and the money lost), its tie-breaks named
     * below them (F4a of project 67, step 6); every stage of the PAC's cascade. */
    const objectiveCards = $derived(objectives ? objectives.stages.filter((stage) => !isTieBreak(stage.objective_code, profile.text)) : []);
    const tieBreaks = $derived(objectives ? objectives.stages.filter((stage) => isTieBreak(stage.objective_code, profile.text)) : []);
    /** The Rebalancer's score and its parts (contract §6.6), on the score's card. */
    const score = $derived(profile.text === 'rebalancer' && 'primary_solution' in result ? (result.primary_solution as unknown as RebalancerSolution).score : null);
    const scoreMoney = (value: Parameters<typeof formatExactMoneyPlain>[0]) => formatExactMoneyPlain(value, {digits});
    /** The objectives the solver closed at the optimum: the witness, without the Rebalancer's tie-breaks. */
    const closedObjectives = $derived(proof.kind === 'optimal_proven' ? proof.witness.objective_codes.filter((code) => !isTieBreak(code, profile.text)).length : 0);
    const R = 'tools.portfolioRebalancer.planner.result';
    const stages = $derived(solver.stages);
    const engines = $derived([...new Set(stages.map((stage) => [stage.engine, stage.version].join(' ')))]);
    const scopes = $derived([...new Set(stages.map((stage) => stage.scope))]);

    const objectiveName = (code: string) => {
        const name = objectiveNameKey(code, profile.text);
        return $t(name.key, {default: name.fallback});
    };
    const cell = (content: ResultCellContent) => ({type: 'custom' as const, component: ResultCell, props: {cell: content}});
    const help = (key: keyof typeof HELP_FALLBACKS) => () => $t(`${KEY}.help.${key}`, {default: HELP_FALLBACKS[key]});
    // On a phone (the table's own 768 px breakpoint) the stages table follows the Review step's scheme (Y-9): each column is fluid down to a
    // floor of its own and the least useful ones (the scope, and the three floating-point figures: the exact objective values are in the cards above) start hidden, so the table fits a card some
    // 300 px wide; «Columns» brings them back.
    const phone = new MediaQuery('max-width: 768px');

    const numberColumn = (id: string, header: string, value: (stage: Stage) => ResultCellContent | string, tooltip?: () => string, secondary = false): ColumnDef<Stage> => ({
        id,
        header: () => header,
        headerTooltip: tooltip,
        type: 'number',
        sortable: false,
        filterable: false,
        align: 'right',
        minWidth: phone.current ? 72 : undefined,
        hiddenByDefault: phone.current && secondary,
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

    const stageColumns = $derived.by((): ColumnDef<Stage>[] =>
        withHelpCues<Stage>([
            {
                id: 'objective',
                header: () => $t(`${KEY}.objective`, {default: 'Objective'}),
                type: 'custom',
                sortable: false,
                filterable: false,
                pinned: 'left',
                minWidth: phone.current ? 110 : 200,
                cell: (stage) => cell({type: 'label', text: objectiveName(stage.objective_code), sequence: stage.ordinal, testid: testId('solver-stage', profile), attrs: {'data-objective': stage.objective_code, 'data-status': stage.status}}),
            },
            {
                id: 'status',
                header: () => $t(`${KEY}.status`, {default: 'Status'}),
                headerTooltip: () => $t(proofStatusHelpKey(profile.text), {default: STATUS_HELP_FALLBACKS[profile.text]}),
                type: 'text',
                sortable: false,
                filterable: false,
                minWidth: phone.current ? 80 : undefined,
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
                          hiddenByDefault: phone.current,
                          cell: (stage: Stage) => scopeText(stage.scope),
                      } satisfies ColumnDef<Stage>,
                  ]
                : []),
            numberColumn('primal', $t(`${KEY}.primal`, {default: 'Primal'}), (stage) => ({type: 'solver', value: stage.primal, unit: stage.unit, digits}), help('primal'), true),
            numberColumn('dual', $t(`${KEY}.dual`, {default: 'Dual'}), (stage) => ({type: 'solver', value: stage.dual, unit: stage.unit, digits}), help('dual'), true),
            numberColumn('absoluteGap', $t(`${KEY}.absoluteGap`, {default: 'Abs. gap'}), (stage) => ({type: 'solver', value: stage.absolute_gap, unit: stage.unit, digits}), help('absoluteGap'), true),
            numberColumn('relativeGap', $t(`${KEY}.relativeGap`, {default: 'Rel. gap'}), (stage) => formatPlannerPlainDecimal(stage.relative_gap), help('relativeGap')),
        ]),
    );

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

<div class="space-y-4 text-sm" data-testid={testId('proof', profile)} data-proof={proof.kind} data-solver={solver.kind}>
    <!-- R11.10: the badges of the header, one tile per question, each with its explanation. -->
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-3" data-testid={testId('proof-facts', profile)}>
        <div class="{TILE} space-y-2" data-testid={testId('proof-outcome', profile)}>
            <p class={TILE_LABEL}>{$t(`${KEY}.outcome`, {default: 'Outcome'})}</p>
            <div class="flex flex-wrap gap-1.5">
                {#each outcomeBadges as badge (badge.id)}
                    <ResultBadgeTip {badge} />
                {/each}
            </div>
        </div>

        <div class="{TILE} space-y-2" data-testid={testId('proof-kind', profile)}>
            <p class={TILE_LABEL}>{$t(`${KEY}.proof`, {default: 'Proof'})}</p>
            {#if proofBadge}
                <div class="flex flex-wrap gap-1.5"><ResultBadgeTip badge={proofBadge} /></div>
            {/if}
            {#if proof.kind === 'optimal_proven'}
                <p class={HINT} data-testid={testId('proof-witness', profile)} data-closed={closedObjectives}>
                    {$t(`${KEY}.solverWitness`, {
                        default: '{objectives, plural, one {# objective of the cascade} other {# objectives of the cascade}} closed at the optimum by the solver',
                        values: {objectives: closedObjectives},
                    })}
                </p>
            {:else if proof.kind === 'not_proven'}
                <!-- Not proven: either a stage is still open, or every stage closed but the final exact check contradicted the solver's bounds; the badge help says which. -->
                <p class="{HINT} first-letter:uppercase" data-testid={testId('proof-reason', profile)} data-reason={proof.reason_code}>
                    {$t(`tools.pacAllocator.planner.result.proof.reasons.${proof.reason_code}`, {default: 'an exact proof was not established'})}
                </p>
            {/if}
            <!-- Infeasibility proven: the witness is the badge's own explanation, and the state notice above says it in full. -->
        </div>

        <div class="{TILE} space-y-2" data-testid={testId('proof-stop', profile)}>
            <p class={TILE_LABEL}>{$t(`${KEY}.stop`, {default: 'Stop'})}</p>
            {#if stopBadge}
                <div class="flex flex-wrap gap-1.5"><ResultBadgeTip badge={stopBadge} /></div>
            {/if}
        </div>
    </div>

    {#if objectives}
        <div class="space-y-2 border-t border-lf-subtle pt-3" data-testid={testId('objectives', profile)}>
            <p class="font-medium text-lf-primary">{$t(`${KEY}.exactObjectives`, {default: 'Exact objective values (backend, Decimal)'})}</p>
            <!-- R11.10: one card per objective, in cascade order, with the «?» of Strategy. -->
            <ol class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {#each objectiveCards as stage (stage.objective_code)}
                    {@const tip = objectiveHelp(stage.objective_code)}
                    <li class="{TILE} flex items-start gap-3" data-testid={testId('objective', profile)} data-objective={stage.objective_code}>
                        <span class="{ICON_BUBBLE} text-xs font-semibold" aria-hidden="true">{stage.ordinal}</span>
                        <div class="min-w-0 flex-1">
                            <div class="flex flex-wrap items-center gap-0.5 font-medium text-lf-primary">
                                <span>{objectiveName(stage.objective_code)}</span>
                                {#if tip.help}
                                    <HelpTip label={objectiveName(stage.objective_code)} help={tip.help} math={tip.math} spoken={tip.spoken} testid={testId('objective-help', profile)} />
                                {/if}
                            </div>
                            <p class="mt-1 break-words text-lg font-semibold tabular-nums text-lf-primary" data-testid={testId('objective-value', profile)}>
                                {formatObjectiveValue(stage.value, stage.unit, digits)}
                            </p>
                            {#if score && stage.objective_code === 'plan_score' && score.distance_weight && score.distance_per_wealth}
                                <!-- The score's three parts: J = λ × distance/F + money lost (contract §6.6), each a published field. -->
                                <ul class="{HINT} mt-1 space-y-0.5 tabular-nums">
                                    <li data-part="distance_weight">{$t(`${R}.proof.lambda`, {default: 'λ {value}', values: {value: formatPlannerPlainDecimal(exactDisplay(score.distance_weight).text)}})}</li>
                                    <li data-part="distance_per_wealth">{$t(`${R}.header.distance`, {default: 'Distance/F {value}', values: {value: scoreMoney(score.distance_per_wealth)}})}</li>
                                    <li data-part="wealth_loss">{$t(`${R}.header.moneyLost`, {default: 'Costs and fees {value}', values: {value: scoreMoney(score.wealth_loss)}})}</li>
                                </ul>
                            {/if}
                        </div>
                    </li>
                {/each}
            </ol>
            <!-- The Rebalancer's tie-breaks, named in the cascade's order, then the fixed order (B2, D4); the PAC's sentence. -->
            <svelte:element this={profile.text === 'rebalancer' ? 'div' : 'p'} class={profile.text === 'rebalancer' ? `${HINT} space-y-1` : HINT} data-testid={testId('proof-tie-break', profile)}>
                {#if profile.text === 'rebalancer'}
                    <p><span class="font-medium">{$t(`${R}.proof.tieBreaks`, {default: 'Tie-breaks, among the plans as good on the objectives above'})}</span></p>
                    <ol class="list-inside list-decimal">
                        {#each tieBreaks as stage (stage.objective_code)}
                            <li data-objective={stage.objective_code}>{objectiveName(stage.objective_code)}</li>
                        {/each}
                        <li data-objective="fixed_order">{$t(`${R}.proof.fixedOrder`, {default: 'a fixed order of Assets and Brokers'})}</li>
                    </ol>
                    <p>{$t(`${R}.proof.sameData`, {default: 'A search that ends by itself gives the same plan for the same data; one stopped by the time limit may give another.'})}</p>
                {:else}
                    <span class="font-medium">{$t(`${PLANNER_KEY}.strategy.tieBreakTitle`, {default: 'Final tie-break'})}</span> ·
                    {$t(`${PLANNER_KEY}.strategy.tieBreak`, {
                        default: 'If a tie is still left, a fixed order of Assets and Brokers decides. A search that ends by itself always gives the same plan for the same data; one stopped by a time or node limit may give a different plan.',
                    })}
                {/if}
            </svelte:element>
        </div>
    {/if}

    <div class="space-y-2 border-t border-lf-subtle pt-3" data-testid={testId('solver', profile)}>
        <div class="flex flex-wrap items-center gap-2">
            <p class="font-medium text-lf-primary">
                {[$t(`${KEY}.solverStages`, {default: 'Solver stages'}), $t(`${KEY}.reportedFloating`, {default: 'reported in floating point'}), ...engines, ...(scopes.length === 1 ? [scopeText(scopes[0])] : [])].join(' · ')}
            </p>
            <TableColumns table={stagesTable} testid={testId('solver-stages-columns', profile)} />
        </div>
        <div data-testid={testId('solver-stages', profile)}>
            <DataTable bind:this={stagesTable} data={stages} columns={stageColumns} getRowId={(stage) => String(stage.stage)} storageKey={storageKey('result-solver-stages', profile)} {...TABLE_PROPS} />
        </div>
    </div>

    <div class="space-y-3 border-t border-lf-subtle pt-3">
        <ToolExecutionMetrics item={metrics} {batch} />
        <!-- R10.9: local to the PAC; the shared box belongs to the platform. -->
        <BackendTimingBar {metrics} />
    </div>
</div>
