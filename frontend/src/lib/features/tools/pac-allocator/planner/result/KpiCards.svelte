<!--
  R10.6: the key figures of the plan as tiles, each with its «?» and, under the value, the parts it
  is made of as badges; beside them the «Calcolo» box: how long the optimizer worked and how far it
  got. Every amount is the backend's accounting and a part that is exactly 0 is left out. Without a
  plan (infeasible, nothing found within the limits) only the box is shown.
-->
<script lang="ts">
    import {locale, t} from '$lib/i18n';
    import type {ToolItemMetrics} from '$lib/features/tools/contracts';
    import HelpTip from '../shared/HelpTip.svelte';
    import {formatExactMoneyPlain, formatObjectiveValue, type CurrencyDigits} from '../format';
    import type {PacCosts, PacExactMoney, PacReadyResult, PacSolution} from '../types';
    import {BADGE, CARD, HINT, SECTION_TITLE} from '../ui';
    import {exactSign, objectiveStage} from './model';

    interface Props {
        solution: PacSolution | null;
        result: PacReadyResult;
        metrics: ToolItemMetrics;
        digits: CurrencyDigits;
    }

    let {solution, result, metrics, digits}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.kpi';
    const RESULT_KEY = 'tools.pacAllocator.planner.result';

    type Tone = keyof typeof BADGE;
    type Chip = {id: string; label: string; value?: string; tone: Tone};
    type Kpi = 'fixed_reference' | 'final_invested' | 'shortfall' | 'selected_funding' | 'explicit_cost' | 'orders';
    type Tile = {kpi: Kpi; label: string; help: string; value: string; chips: Chip[]};

    const COST_PARTS = [
        {field: 'buy_fees', key: `${RESULT_KEY}.ledger.fields.buy_fees`, fallback: 'Purchase fees'},
        {field: 'sell_fees', key: `${RESULT_KEY}.ledger.fields.sell_fees`, fallback: 'Sale fees'},
        {field: 'fx_spread_loss', key: `${RESULT_KEY}.detail.spreadLoss`, fallback: 'Spread loss'},
        {field: 'execution_margin_cost', key: `${RESULT_KEY}.detail.marginCost`, fallback: 'Margin cost'},
        {field: 'broker_withheld_tax', key: `${RESULT_KEY}.ledger.fields.broker_withheld_tax`, fallback: 'Tax withheld by the Broker'},
        {field: 'self_reserved_tax', key: `${RESULT_KEY}.ledger.fields.self_reserved_tax`, fallback: 'Tax reserved by you'},
    ] as const satisfies readonly {field: keyof PacCosts; key: string; fallback: string}[];

    const money = (value: PacExactMoney) => formatExactMoneyPlain(value, {digits});
    /** A part that is exactly 0 is left out; one that cannot be read is shown. */
    const shown = (value: PacExactMoney) => exactSign(value.value) !== 0;
    const text = (key: string, fallback: string) => $t(`${KEY}.${key}`, {default: fallback});
    const part = (id: string, label: string, value: PacExactMoney, tone: Tone = 'neutral'): Chip => ({id, label, value: money(value), tone});

    const trapped = $derived(solution !== null && shown(solution.accounting.trapped_funding));

    const tiles = $derived.by((): Tile[] => {
        if (!solution) return [];
        const accounting = solution.accounting;
        const costs = solution.costs;
        const explicitCost = objectiveStage(solution.objectives.stages, 'explicit_cost');
        const reachable = () => part('reachable_funding', text('parts.reachable', 'Reachable cash'), accounting.reachable_funding);

        const base = shown(accounting.current_invested) ? [part('current_invested', text('parts.currentInvested', 'Already invested'), accounting.current_invested), reachable()] : [];

        const held = solution.asset_rows.filter((row) => shown(row.final_value)).length;
        const invested: Chip[] =
            solution.asset_rows.length > 0
                ? [{id: 'assets', label: $t(`${KEY}.assetsHeld`, {default: 'in {held} of {total, plural, one {# Asset} other {# Assets}}', values: {held, total: solution.asset_rows.length}}), tone: 'neutral'}]
                : [];

        const shortfall: Chip[] = shown(accounting.shortfall)
            ? [
                  ...(shown(accounting.free_cash) ? [part('free_cash', text('parts.freeCash', 'Free cash'), accounting.free_cash)] : []),
                  ...(shown(accounting.economic_losses) ? [part('economic_losses', text('explicitCost', 'Costs'), accounting.economic_losses)] : []),
                  ...(shown(accounting.physical_reserves) ? [part('physical_reserves', $t(`${RESULT_KEY}.ledger.fields.self_reserved_tax`, {default: 'Tax reserved by you'}), accounting.physical_reserves)] : []),
                  ...(shown(accounting.rounding_delta) ? [part('rounding_delta', $t(`${RESULT_KEY}.ledger.fields.rounding_delta`, {default: 'Rounding'}), accounting.rounding_delta)] : []),
              ]
            : [{id: 'all_invested', label: text('allInvested', 'All invested'), tone: 'success'}];

        const funding: Chip[] = trapped
            ? [reachable(), part('trapped_funding', text('parts.trapped', 'Not reachable'), accounting.trapped_funding, 'warning')]
            : shown(accounting.selected_funding)
              ? [{id: 'all_reachable', label: text('allReachable', 'All reachable'), tone: 'success'}]
              : [];

        const costParts = COST_PARTS.filter((cost) => shown(costs[cost.field])).map((cost) => part(cost.field, $t(cost.key, {default: cost.fallback}), costs[cost.field]));
        const cost: Chip[] = costParts.length > 0 ? costParts : [{id: 'no_cost', label: text('noCost', 'No costs'), tone: 'success'}];

        const brokers = new Set(solution.order_rows.map((order) => order.broker_id)).size;
        const manualConversions = solution.conversions.filter((action) => action.mode === 'manual').length;
        const automaticConversions = solution.conversions.length - manualConversions;
        const orders: Chip[] = [
            ...(brokers > 0 ? [{id: 'brokers', label: $t(`${KEY}.brokers`, {default: 'at {count, plural, one {# Broker} other {# Brokers}}', values: {count: brokers}}), tone: 'neutral' as const}] : []),
            ...(manualConversions > 0
                ? [{id: 'fx', label: $t(`${KEY}.fxActions`, {default: '{count, plural, one {# currency exchange} other {# currency exchanges}}', values: {count: manualConversions}}), tone: 'neutral' as const}]
                : []),
            ...(automaticConversions > 0
                ? [{id: 'fx_auto', label: $t(`${KEY}.autoConversions`, {default: '{count, plural, one {# automatic conversion} other {# automatic conversions}}', values: {count: automaticConversions}}), tone: 'neutral' as const}]
                : []),
        ];

        const tile = (kpi: Kpi, key: string, fallback: string, help: string, value: string, chips: Chip[]): Tile => ({kpi, label: text(key, fallback), help: text(`help.${key}`, help), value, chips});
        return [
            tile('fixed_reference', 'fixedReference', 'Base of the targets', 'The amount the target percentages apply to: what you already hold of the chosen Assets, plus the cash the plan can reach.', money(accounting.fixed_reference), base),
            tile('final_invested', 'finalInvested', 'Invested after', 'The value of the chosen Assets after the plan.', money(accounting.final_invested), invested),
            tile('shortfall', 'shortfall', 'Not invested', 'The part of the base that does not end up in the Assets: cash left free, costs and rounding.', money(accounting.shortfall), shortfall),
            tile(
                'selected_funding',
                'selectedFunding',
                'Cash chosen',
                'The cash you chose for the plan, existing and new, at the rates of the FX step. A part that cannot reach a Broker where you can buy is marked not reachable and stays out of the base of the targets.',
                money(accounting.selected_funding),
                funding,
            ),
            tile('explicit_cost', 'explicitCost', 'Costs', 'Broker fees, currency exchange spreads and the price margins you set, over the whole plan.', explicitCost ? formatObjectiveValue(explicitCost.value, explicitCost.unit, digits) : '—', cost),
            tile('orders', 'orders', 'Orders', 'How many orders the plan asks you to place.', String(solution.order_rows.length), orders),
        ];
    });

    // -- the «Calcolo» box: backend timings and the solver's own report, no money ----------
    const stages = $derived(result.solver_evidence.stages);
    const setting = (name: string) => stages.flatMap((stage) => stage.settings).find((entry) => entry.name === name)?.value ?? null;
    const budget = $derived(setting('time_budget'));
    const nodeLimit = $derived(setting('limits/nodes'));
    const infeasible = $derived(stages.some((stage) => stage.status === 'infeasible'));
    const closed = $derived(stages.filter((stage) => stage.status === 'finished').length);
    const engines = $derived([...new Set(stages.map((stage) => `${stage.engine} ${stage.version}`))].join(', '));

    const formats = $derived.by(() => {
        const tag = $locale ?? 'en';
        return {
            milliseconds: new Intl.NumberFormat(tag, {style: 'unit', unit: 'millisecond', unitDisplay: 'short', maximumFractionDigits: 0}),
            seconds: new Intl.NumberFormat(tag, {style: 'unit', unit: 'second', unitDisplay: 'short', maximumFractionDigits: 1}),
            budget: new Intl.NumberFormat(tag, {style: 'unit', unit: 'second', unitDisplay: 'short', maximumFractionDigits: 3}),
            integer: new Intl.NumberFormat(tag, {maximumFractionDigits: 0}),
        };
    });

    /** A backend timing in its unit: milliseconds below one second, seconds above. Null was not measured. */
    function duration(ms: number | null): string {
        if (ms === null) return '—';
        return ms < 1000 ? formats.milliseconds.format(ms) : formats.seconds.format(ms / 1000);
    }

    /** The solver settings are reported as text: a number is shown in its unit, anything else as it came. */
    function settingNumber(value: string, format: Intl.NumberFormat): string {
        const number = Number(value);
        return value.trim() !== '' && Number.isFinite(number) ? format.format(number) : value;
    }

    const computeTitle = $derived(text('compute.title', 'Calculation'));
</script>

<section class={CARD} aria-label={solution ? text('title', 'Key figures') : computeTitle} data-testid="pac-planner-kpi">
    {#if solution}
        <div class="mb-3 flex items-center gap-1">
            <h3 class={SECTION_TITLE}>{text('title', 'Key figures')}</h3>
            <HelpTip label={text('title', 'Key figures')} help={text('source', 'Every figure comes from the backend accounting; the interface adds nothing up.')} testid="pac-planner-kpi-source" />
        </div>
    {/if}
    <div class={solution ? 'grid gap-3 lg:grid-cols-[minmax(0,1fr)_16rem]' : ''}>
        {#if solution}
            <dl class="grid content-start gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {#each tiles as tile (tile.kpi)}
                    <div
                        class="rounded-lg border border-gray-200 p-3 dark:border-gray-700"
                        data-testid="pac-planner-kpi-item"
                        data-kpi={tile.kpi}
                        data-trapped={tile.kpi === 'selected_funding' ? (trapped ? 'true' : 'false') : undefined}
                    >
                        <dt class="{HINT} flex items-center gap-1">
                            <span>{tile.label}</span>
                            <HelpTip label={tile.label} help={tile.help} testid="pac-planner-kpi-help" />
                        </dt>
                        <dd class="mt-1 text-lg font-semibold tabular-nums text-gray-900 dark:text-gray-100">{tile.value}</dd>
                        {#if tile.chips.length > 0}
                            <dd class="mt-2">
                                <ul class="flex flex-wrap gap-1">
                                    {#each tile.chips as chip (chip.id)}
                                        <li class={BADGE[chip.tone]} data-testid="pac-planner-kpi-chip" data-chip={chip.id} data-tone={chip.tone}>
                                            <span>{chip.label}</span>
                                            {#if chip.value !== undefined}<span class="font-semibold tabular-nums">{chip.value}</span>{/if}
                                        </li>
                                    {/each}
                                </ul>
                            </dd>
                        {/if}
                    </div>
                {/each}
            </dl>
        {/if}
        <div class="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/40" data-testid="pac-planner-kpi-compute">
            <div class="flex items-center gap-1">
                <svelte:element this={solution ? 'h4' : 'h3'} class={SECTION_TITLE}>{computeTitle}</svelte:element>
                <HelpTip
                    label={computeTitle}
                    help={text('compute.help', 'How long the optimizer worked on this plan and how far it got within the time it was given. The details are in «Proof and solver».')}
                    testid="pac-planner-kpi-compute-help"
                />
            </div>
            <dl class="mt-2 space-y-2 text-sm">
                <div data-testid="pac-planner-kpi-compute-row" data-row="time">
                    <dt class="{HINT} flex items-center gap-1">
                        <span>{text('compute.time', 'Calculation time')}</span>
                        <HelpTip
                            label={text('compute.time', 'Calculation time')}
                            help={text('compute.timeHelp', 'The time the backend spent computing the plan. The total also counts the wait in the queue, the start of the worker and the checks on input and output.')}
                            testid="pac-planner-kpi-compute-row-help"
                        />
                    </dt>
                    <dd class="font-semibold tabular-nums text-gray-900 dark:text-gray-100">
                        {duration(metrics.compute_ms)}
                        {#if metrics.total_ms !== null}
                            <span class="{HINT} font-normal">{$t(`${KEY}.compute.total`, {default: 'total {value}', values: {value: duration(metrics.total_ms)}})}</span>
                        {/if}
                    </dd>
                </div>
                {#if budget !== null}
                    <div data-testid="pac-planner-kpi-compute-row" data-row="budget">
                        <dt class="{HINT} flex items-center gap-1">
                            <span>{text('compute.budget', 'Time allowed')}</span>
                            <HelpTip
                                label={text('compute.budget', 'Time allowed')}
                                help={text('compute.budgetHelp', 'The longest the optimizer may search for each objective. When it runs out, the best plan found so far is kept and the result says it is not proven optimal.')}
                                testid="pac-planner-kpi-compute-row-help"
                            />
                        </dt>
                        <dd class="font-semibold tabular-nums text-gray-900 dark:text-gray-100">{settingNumber(budget, formats.budget)}</dd>
                    </div>
                {/if}
                {#if !infeasible}
                    <div data-testid="pac-planner-kpi-compute-row" data-row="objectives">
                        <dt class="{HINT} flex items-center gap-1">
                            <span>{text('compute.objectives', 'Objectives closed')}</span>
                            <HelpTip
                                label={text('compute.objectives', 'Objectives closed')}
                                help={text('compute.objectivesHelp', 'The objectives are optimized one after the other. An objective is closed when the optimizer proved that nothing better exists for it; the others stopped at a limit.')}
                                testid="pac-planner-kpi-compute-row-help"
                            />
                        </dt>
                        <dd class="font-semibold tabular-nums text-gray-900 dark:text-gray-100">
                            {$t(`${KEY}.compute.objectivesValue`, {default: '{closed} of {total}', values: {closed, total: stages.length}})}
                        </dd>
                    </div>
                {/if}
                {#if nodeLimit !== null}
                    <div data-testid="pac-planner-kpi-compute-row" data-row="node_limit">
                        <dt class={HINT}>{text('compute.nodeLimit', 'Node limit')}</dt>
                        <dd class="font-semibold tabular-nums text-gray-900 dark:text-gray-100">{settingNumber(nodeLimit, formats.integer)}</dd>
                    </div>
                {/if}
                <div data-testid="pac-planner-kpi-compute-row" data-row="engine">
                    <dt class={HINT}>{text('compute.engine', 'Engine')}</dt>
                    <dd class="text-gray-900 dark:text-gray-100">{engines}</dd>
                </div>
            </dl>
        </div>
    </div>
</section>
