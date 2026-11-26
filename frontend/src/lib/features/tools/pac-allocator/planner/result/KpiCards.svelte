<!--
  R10.6: the key figures of the plan as tiles, each with its «?» and, under the value, the parts it
  is made of as badges; beside them the «Calcolo» box: how long the optimizer worked and how far it
  got. Every amount is the backend's accounting and a part that is exactly 0 is left out. Without a
  plan (infeasible, nothing found within the limits) only the box is shown.

  The Rebalancer (F4a of project 67, step 4; contract §6.1, X14) has its own six tiles, chosen by the Tool's profile:
  «Worth today» (`F`), «Worth after» (`W`), «Costs and fees» (`F − W`, from the score) with its published entries, «Largest gap
  from target» after and before (points) with the item each one names (X14: the score's references, and the share and target
  of the row they point to), «Uninvested», «Orders». Every one is a published field: none is a sum, a difference or a
  maximum of others.
  TL-5 of project 67 (the developer's answers of 24/11): «Uninvested» becomes «Rimasto in cassa», all the cash at the end
  (`plan_accounts.final_cash`), and «Money lost» «Costi e commissioni». Under the cash, currency by currency and each in
  its own (`plan_accounts.cash_by_currency`), the cash at the start and at the end, and the contributions not used: in the
  Rebalancer's tile and under the parts of the PAC's «Not invested», which keeps its figure (the shortfall, an objective).
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import type {ToolItemMetrics} from '$lib/features/tools/contracts';
    import HelpTip from '../shared/HelpTip.svelte';
    import {formatExactMoneyPlain, formatExactPercent, formatExactPoints, formatObjectiveValue, type CurrencyDigits} from '../format';
    import type {PlannerCosts, PlannerExactMoney, PlannerReadyResult, PlannerSolution, RebalancerSolution} from '../types';
    import {BADGE, CARD, HINT, SECTION_TITLE} from '../ui';
    import {exactSign, objectiveStage, resultNames} from './model';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import {getPlannerProfile, testId} from '../profile';
    import {isTieBreak} from '../policies';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    interface Props {
        solution: PlannerSolution | null;
        result: PlannerReadyResult;
        metrics: ToolItemMetrics;
        digits: CurrencyDigits;
    }

    let {solution, result, metrics, digits}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.kpi';
    const RESULT_KEY = 'tools.pacAllocator.planner.result';

    type Tone = keyof typeof BADGE;
    type Chip = {id: string; label: string; value?: string; tone: Tone};
    type Kpi = 'fixed_reference' | 'final_invested' | 'shortfall' | 'selected_funding' | 'explicit_cost' | 'orders' | 'value_today' | 'value_after' | 'money_lost' | 'largest_deviation' | 'final_cash';
    /** The cash of one currency, in that currency (TL-5): at the start, at the end, the contributions not used (null when 0). */
    type CashLine = {currency: string; initial: string; final: string; unused: string | null};
    type Tile = {kpi: Kpi; label: string; help: string; value: string; chips: Chip[]; cash?: CashLine[]};

    const COST_PARTS = [
        {field: 'buy_fees', key: `${RESULT_KEY}.ledger.fields.buy_fees`, fallback: 'Purchase fees'},
        {field: 'sell_fees', key: `${RESULT_KEY}.ledger.fields.sell_fees`, fallback: 'Sale fees'},
        {field: 'fx_spread_loss', key: `${RESULT_KEY}.detail.spreadLoss`, fallback: 'Spread loss'},
        {field: 'execution_margin_cost', key: `${RESULT_KEY}.detail.marginCost`, fallback: 'Margin cost'},
        {field: 'broker_withheld_tax', key: `${RESULT_KEY}.ledger.fields.broker_withheld_tax`, fallback: 'Tax withheld by the Broker'},
        {field: 'self_reserved_tax', key: `${RESULT_KEY}.ledger.fields.self_reserved_tax`, fallback: 'Tax reserved by you'},
    ] as const satisfies readonly {field: keyof PlannerCosts; key: string; fallback: string}[];

    const money = (value: PlannerExactMoney) => formatExactMoneyPlain(value, {digits});
    /** A part that is exactly 0 is left out; one that cannot be read is shown. */
    const shown = (value: PlannerExactMoney) => exactSign(value.value) !== 0;
    const text = (key: string, fallback: string) => $t(`${KEY}.${key}`, {default: fallback});
    const part = (id: string, label: string, value: PlannerExactMoney, tone: Tone = 'neutral'): Chip => ({id, label, value: money(value), tone});

    const trapped = $derived(solution !== null && shown(solution.accounting.trapped_funding));

    /** The plan's cash currency by currency, as published (TL-5): nothing is summed or converted here. */
    function cashLines(accounts: PlannerSolution['plan_accounts']): CashLine[] {
        return accounts.cash_by_currency.map((row) => ({currency: row.currency, initial: money(row.initial), final: money(row.final), unused: shown(row.unused_contributions) ? money(row.unused_contributions) : null}));
    }

    const R = 'tools.portfolioRebalancer.planner.result.kpi';
    /** The money lost, entry by entry (contract §6.1): each published part, never grouped. */
    const LOSS_PARTS = [
        {field: 'buy_fees', key: `${RESULT_KEY}.ledger.fields.buy_fees`, fallback: 'Purchase fees'},
        {field: 'sell_fees', key: `${RESULT_KEY}.ledger.fields.sell_fees`, fallback: 'Sale fees'},
        {field: 'fx_spread_loss', key: `${RESULT_KEY}.detail.spreadLoss`, fallback: 'Spread loss'},
        {field: 'execution_margin_cost', key: `${RESULT_KEY}.detail.marginCost`, fallback: 'Margin cost'},
        {field: 'broker_withheld_tax', key: `${RESULT_KEY}.ledger.fields.broker_withheld_tax`, fallback: 'Tax withheld by the Broker'},
        {field: 'self_reserved_tax', key: `${RESULT_KEY}.ledger.fields.self_reserved_tax`, fallback: 'Tax reserved by you'},
        {field: 'foreign_withholding_tax', key: `${R}.foreignWithholding`, fallback: 'Foreign withholding tax'},
        {field: 'rounding', key: `${RESULT_KEY}.ledger.fields.rounding_delta`, fallback: 'Rounding'},
    ] as const;

    /** The item a largest gap names (X14), its row and its label; a reference the rows do not hold names nothing. */
    function deviationItem(rebalancer: RebalancerSolution, ref: RebalancerSolution['score']['largest_deviation_after_item']) {
        if (!ref) return null;
        const names = resultNames(result);
        if (ref.kind === 'asset') {
            const row = rebalancer.asset_rows.find((item) => item.asset_id === ref.asset_id);
            return row ? {row, label: names.asset(ref.asset_id)} : null;
        }
        const row = rebalancer.cash_rows.find((item) => item.broker_id === ref.broker_id && item.currency === ref.currency);
        return row ? {row, label: $t(`${R}.cashItem`, {values: {broker: names.broker(ref.broker_id), currency: ref.currency}})} : null;
    }

    function deviationChips(rebalancer: RebalancerSolution): Chip[] {
        const score = rebalancer.score;
        const points = formatExactPoints(score.largest_deviation_before);
        const after = deviationItem(rebalancer, score.largest_deviation_after_item);
        const before = deviationItem(rebalancer, score.largest_deviation_before_item);
        const chips: Chip[] = [];
        if (after) {
            chips.push({id: 'after_item', label: $t(`${R}.deviationItem`, {values: {item: after.label, weight: formatExactPercent(after.row.final_weight), target: formatExactPercent(after.row.target_weight)}}), tone: 'neutral'});
        }
        chips.push({
            id: 'before',
            label: before ? $t(`${R}.beforePointsItem`, {values: {value: points, item: before.label, weight: formatExactPercent(before.row.before_weight), target: formatExactPercent(before.row.target_weight)}}) : $t(`${R}.beforePoints`, {values: {value: points}}),
            tone: 'neutral',
        });
        return chips;
    }

    function rebalancerTiles(rebalancer: RebalancerSolution): Tile[] {
        const accounts = rebalancer.plan_accounts;
        const score = rebalancer.score;
        const lost = accounts.money_lost;
        const losses = LOSS_PARTS.filter((entry) => shown(lost[entry.field])).map((entry) => part(entry.field, $t(entry.key, {default: entry.fallback}), lost[entry.field]));
        const held = {
            assets: rebalancer.asset_rows.filter((row) => shown(row.final_value)).length,
            cash: rebalancer.cash_rows.filter((row) => shown(row.final_value)).length,
        };
        const brokers = new Set(rebalancer.order_rows.map((order) => order.broker_id)).size;
        const manualConversions = rebalancer.conversions.filter((action) => action.mode === 'manual').length;
        const automaticConversions = rebalancer.conversions.length - manualConversions;
        const count = (id: string, key: string, fallback: string, value: number): Chip[] => (value > 0 ? [{id, label: $t(key, {default: fallback, values: {count: value}}), tone: 'neutral'}] : []);
        const tile = (kpi: Kpi, key: string, value: string, chips: Chip[]): Tile => ({kpi, label: $t(`${R}.${key}`), help: $t(`${R}.${key}Help`), value, chips});
        return [
            tile('value_today', 'valueToday', money(accounts.initial_wealth), [part('assets', $t(`${R}.partsAssets`), rebalancer.accounting.current_invested), part('cash', $t(`${R}.partsCash`), rebalancer.accounting.selected_funding)]),
            tile('value_after', 'valueAfter', money(accounts.final_wealth), [{id: 'held', label: $t(`${R}.valueAfterHeld`, {values: held}), tone: 'neutral'}]),
            tile('money_lost', 'moneyLost', money(score.wealth_loss), losses.length > 0 ? losses : [{id: 'none', label: $t(`${R}.noLoss`), tone: 'success'}]),
            tile('largest_deviation', 'largestDeviation', $t(`${R}.points`, {values: {value: formatExactPoints(score.largest_deviation_after)}}), deviationChips(rebalancer)),
            {...tile('final_cash', 'finalCash', money(accounts.final_cash), []), cash: cashLines(accounts)},
            {
                kpi: 'orders',
                label: text('orders', 'Orders'),
                help: text('help.orders', 'How many orders the plan asks you to place.'),
                value: String(rebalancer.order_rows.length),
                chips: [
                    ...count('brokers', `${KEY}.brokers`, 'at {count, plural, one {# Broker} other {# Brokers}}', brokers),
                    ...count('transfers', `${R}.transfers`, '{count, plural, one {# transfer} other {# transfers}}', rebalancer.transfers.length),
                    ...count('fx', `${KEY}.fxActions`, '{count, plural, one {# currency exchange} other {# currency exchanges}}', manualConversions),
                    ...count('fx_auto', `${KEY}.autoConversions`, '{count, plural, one {# automatic conversion} other {# automatic conversions}}', automaticConversions),
                ],
            },
        ];
    }

    const tiles = $derived.by((): Tile[] => {
        if (!solution) return [];
        if (profile.text === 'rebalancer') return rebalancerTiles(solution as unknown as RebalancerSolution);
        const accounting = solution.accounting;
        const costs = solution.costs;
        const explicitCost = objectiveStage(solution.objectives.stages, 'explicit_cost');
        const reachable = () => part('reachable_funding', text('parts.reachable', 'Reachable cash'), accounting.reachable_funding);

        const base = shown(accounting.current_invested) ? [part('current_invested', text('parts.currentInvested', 'Already invested'), accounting.current_invested), reachable()] : [];

        const held = solution.asset_rows.filter((row) => shown(row.final_value)).length;
        const invested: Chip[] = solution.asset_rows.length > 0 ? [{id: 'assets', label: $t(`${KEY}.assetsHeld`, {default: 'in {held} of {total, plural, one {# Asset} other {# Assets}}', values: {held, total: solution.asset_rows.length}}), tone: 'neutral'}] : [];

        const shortfall: Chip[] = shown(accounting.shortfall)
            ? [
                  ...(shown(accounting.free_cash) ? [part('free_cash', text('parts.freeCash', 'Free cash'), accounting.free_cash)] : []),
                  ...(shown(accounting.economic_losses) ? [part('economic_losses', text('explicitCost', 'Costs'), accounting.economic_losses)] : []),
                  ...(shown(accounting.physical_reserves) ? [part('physical_reserves', $t(`${RESULT_KEY}.ledger.fields.self_reserved_tax`, {default: 'Tax reserved by you'}), accounting.physical_reserves)] : []),
                  ...(shown(accounting.rounding_delta) ? [part('rounding_delta', $t(`${RESULT_KEY}.ledger.fields.rounding_delta`, {default: 'Rounding'}), accounting.rounding_delta)] : []),
              ]
            : [{id: 'all_invested', label: text('allInvested', 'All invested'), tone: 'success'}];

        const funding: Chip[] = trapped ? [reachable(), part('trapped_funding', text('parts.trapped', 'Not reachable'), accounting.trapped_funding, 'warning')] : shown(accounting.selected_funding) ? [{id: 'all_reachable', label: text('allReachable', 'All reachable'), tone: 'success'}] : [];

        const costParts = COST_PARTS.filter((cost) => shown(costs[cost.field])).map((cost) => part(cost.field, $t(cost.key, {default: cost.fallback}), costs[cost.field]));
        const cost: Chip[] = costParts.length > 0 ? costParts : [{id: 'no_cost', label: text('noCost', 'No costs'), tone: 'success'}];

        const brokers = new Set(solution.order_rows.map((order) => order.broker_id)).size;
        const manualConversions = solution.conversions.filter((action) => action.mode === 'manual').length;
        const automaticConversions = solution.conversions.length - manualConversions;
        const orders: Chip[] = [
            ...(brokers > 0 ? [{id: 'brokers', label: $t(`${KEY}.brokers`, {default: 'at {count, plural, one {# Broker} other {# Brokers}}', values: {count: brokers}}), tone: 'neutral' as const}] : []),
            ...(manualConversions > 0 ? [{id: 'fx', label: $t(`${KEY}.fxActions`, {default: '{count, plural, one {# currency exchange} other {# currency exchanges}}', values: {count: manualConversions}}), tone: 'neutral' as const}] : []),
            ...(automaticConversions > 0 ? [{id: 'fx_auto', label: $t(`${KEY}.autoConversions`, {default: '{count, plural, one {# automatic conversion} other {# automatic conversions}}', values: {count: automaticConversions}}), tone: 'neutral' as const}] : []),
        ];

        const tile = (kpi: Kpi, key: string, fallback: string, help: string, value: string, chips: Chip[]): Tile => ({kpi, label: text(key, fallback), help: text(`help.${key}`, help), value, chips});
        return [
            tile('fixed_reference', 'fixedReference', 'Base of the targets', 'The amount the target percentages apply to: what you already hold of the chosen Assets, plus the cash the plan can reach.', money(accounting.fixed_reference), base),
            tile('final_invested', 'finalInvested', 'Invested after', 'The value of the chosen Assets at the end of the plan.', money(accounting.final_invested), invested),
            {
                ...tile(
                    'shortfall',
                    'shortfall',
                    'Not invested',
                    'The part of the base that does not end up in the Assets: cash left free, costs and rounding. Under it, the cash currency by currency, each in its own: at the start and at the end, contributions included.',
                    money(accounting.shortfall),
                    shortfall,
                ),
                cash: cashLines(solution.plan_accounts),
            },
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
    // The Rebalancer's tie-breaks are not objectives (F4a of project 67, step 6): only its score, or the distance and the
    // money lost, are counted. Every stage of the PAC's cascade is an objective.
    const objectiveStages = $derived(stages.filter((stage) => !isTieBreak(stage.objective_code, profile.text)));
    const closed = $derived(objectiveStages.filter((stage) => stage.status === 'finished').length);
    const engines = $derived([...new Set(stages.map((stage) => `${stage.engine} ${stage.version}`))].join(', '));

    const formats = $derived.by(() => {
        const tag = uiLocale();
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

<section class={CARD} aria-label={solution ? text('title', 'Key figures') : computeTitle} data-testid={testId('kpi', profile)}>
    {#if solution}
        <div class="mb-3 flex items-center gap-1">
            <h3 class={SECTION_TITLE}>{text('title', 'Key figures')}</h3>
            <HelpTip label={text('title', 'Key figures')} help={text('source', 'Every figure comes from the backend accounting; the interface adds nothing up.')} testid={testId('kpi-source', profile)} />
        </div>
    {/if}
    <div class={solution ? 'grid gap-3 lg:grid-cols-[minmax(0,1fr)_16rem]' : ''}>
        {#if solution}
            <dl class="grid content-start gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {#each tiles as tile (tile.kpi)}
                    <div class="rounded-lg border border-lf-subtle p-3" data-testid={testId('kpi-item', profile)} data-kpi={tile.kpi} data-trapped={tile.kpi === 'selected_funding' ? (trapped ? 'true' : 'false') : undefined}>
                        <dt class="{HINT} flex items-center gap-1">
                            <span>{tile.label}</span>
                            <HelpTip label={tile.label} help={tile.help} testid={testId('kpi-help', profile)} />
                        </dt>
                        <dd class="mt-1 text-lg font-semibold tabular-nums text-lf-primary" data-testid={testId('kpi-value', profile)}>{tile.value}</dd>
                        {#if tile.chips.length > 0}
                            <dd class="mt-2">
                                <ul class="flex flex-wrap gap-1">
                                    {#each tile.chips as chip (chip.id)}
                                        <li class={BADGE[chip.tone]} data-testid={testId('kpi-chip', profile)} data-chip={chip.id} data-tone={chip.tone}>
                                            <span>{chip.label}</span>
                                            {#if chip.value !== undefined}<span class="font-semibold tabular-nums">{chip.value}</span>{/if}
                                        </li>
                                    {/each}
                                </ul>
                            </dd>
                        {/if}
                        {#if tile.cash && tile.cash.length > 0}
                            <dd class="mt-2 text-xs text-lf-secondary" data-testid={testId('kpi-cash', profile)}>
                                <p class="text-lf-muted">{text('cashTitle', 'Cash at the start → at the end')}</p>
                                <ul class="mt-0.5 space-y-0.5">
                                    {#each tile.cash as line (line.currency)}
                                        <li class="tabular-nums [overflow-wrap:anywhere]" data-testid={testId('kpi-cash-row', profile)} data-currency={line.currency}>
                                            <span>{line.initial}</span>
                                            <span aria-hidden="true">→</span><span class="sr-only">{text('cashTo', 'at the end')}</span>
                                            <span class="font-semibold text-lf-primary">{line.final}</span>
                                            {#if line.unused !== null}
                                                <span class="block text-lf-muted" data-testid={testId('kpi-cash-unused', profile)}>{$t(`${KEY}.cashUnused`, {default: 'of which contributions not used: {value}', values: {value: line.unused}})}</span>
                                            {/if}
                                        </li>
                                    {/each}
                                </ul>
                            </dd>
                        {/if}
                    </div>
                {/each}
            </dl>
        {/if}
        <div class="rounded-lg bg-lf-panel p-3" data-testid={testId('kpi-compute', profile)}>
            <div class="flex items-center gap-1">
                <svelte:element this={solution ? 'h4' : 'h3'} class={SECTION_TITLE}>{computeTitle}</svelte:element>
                <HelpTip label={computeTitle} help={text('compute.help', 'How long the optimizer worked on this plan and how far it got within the time it was given. The details are in «Proof and solver».')} testid={testId('kpi-compute-help', profile)} />
            </div>
            <dl class="mt-2 space-y-2 text-sm">
                <div data-testid={testId('kpi-compute-row', profile)} data-row="time">
                    <dt class="{HINT} flex items-center gap-1">
                        <span>{text('compute.time', 'Calculation time')}</span>
                        <HelpTip
                            label={text('compute.time', 'Calculation time')}
                            help={text('compute.timeHelp', 'The time the backend spent computing the plan. The total also counts the wait in the queue, the start of the worker and the checks on input and output.')}
                            testid={testId('kpi-compute-row-help', profile)}
                        />
                    </dt>
                    <dd class="font-semibold tabular-nums text-lf-primary">
                        {duration(metrics.compute_ms)}
                        {#if metrics.total_ms !== null}
                            <span class="{HINT} font-normal">{$t(`${KEY}.compute.total`, {default: 'total {value}', values: {value: duration(metrics.total_ms)}})}</span>
                        {/if}
                    </dd>
                </div>
                {#if budget !== null}
                    <div data-testid={testId('kpi-compute-row', profile)} data-row="budget">
                        <dt class="{HINT} flex items-center gap-1">
                            <span>{text('compute.budget', 'Time allowed')}</span>
                            <HelpTip
                                label={text('compute.budget', 'Time allowed')}
                                help={text('compute.budgetHelp', 'The longest the optimizer may search for each objective. When it runs out before the plan is proven, the best plan found so far is kept and marked «Local optimum».')}
                                testid={testId('kpi-compute-row-help', profile)}
                            />
                        </dt>
                        <dd class="font-semibold tabular-nums text-lf-primary">{settingNumber(budget, formats.budget)}</dd>
                    </div>
                {/if}
                {#if !infeasible}
                    <div data-testid={testId('kpi-compute-row', profile)} data-row="objectives">
                        <dt class="{HINT} flex items-center gap-1">
                            <span>{text('compute.objectives', 'Objectives closed')}</span>
                            <HelpTip
                                label={text('compute.objectives', 'Objectives closed')}
                                help={text('compute.objectivesHelp', 'The objectives are optimized one after the other. An objective is closed when the optimizer proved that nothing better exists for it; the others stopped at a limit.')}
                                testid={testId('kpi-compute-row-help', profile)}
                            />
                        </dt>
                        <dd class="font-semibold tabular-nums text-lf-primary" data-closed={closed} data-total={objectiveStages.length}>
                            {$t(`${KEY}.compute.objectivesValue`, {default: '{closed} of {total}', values: {closed, total: objectiveStages.length}})}
                        </dd>
                    </div>
                {/if}
                {#if nodeLimit !== null}
                    <div data-testid={testId('kpi-compute-row', profile)} data-row="node_limit">
                        <dt class={HINT}>{text('compute.nodeLimit', 'Node limit')}</dt>
                        <dd class="font-semibold tabular-nums text-lf-primary">{settingNumber(nodeLimit, formats.integer)}</dd>
                    </div>
                {/if}
                <div data-testid={testId('kpi-compute-row', profile)} data-row="engine">
                    <dt class={HINT}>{text('compute.engine', 'Engine')}</dt>
                    <dd class="text-lf-primary">{engines}</dd>
                </div>
            </dl>
        </div>
    </div>
</section>
