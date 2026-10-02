<!--
  Step «Strategia». The strategies come from the compiled contract (Q-C0-4). Each one says in plain
  words what it looks for and the order of its criteria, which is the backend cascade
  (objectives.py `build_objective_cascade`): a criterion only decides among the plans still tied
  on the ones before it, and a fixed canonical order settles whatever tie is left.
-->
<script lang="ts">
    import {Equal} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import type {PlannerDraft} from '../draft.svelte';
    import {contractPolicies, OBJECTIVE_FALLBACKS, OBJECTIVE_HELP_FALLBACKS, OBJECTIVE_TIPS, POLICY_OBJECTIVES} from '../policies';
    import HelpTip from '../shared/HelpTip.svelte';
    import {CARD, HINT, ICON_BUBBLE, NOTICE, SECTION_TITLE} from '../ui';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        draft: PlannerDraft;
    }

    let {draft}: Props = $props();

    const ids = $props.id();
    const policies = contractPolicies();
    const POLICY_FALLBACKS: Record<string, string> = {proportional: 'Proportional'};
    const POLICY_HELP_FALLBACKS: Record<string, string> = {
        proportional: 'It buys so that the money you invest splits among the Assets as close as possible to your targets.',
    };
    /** What the strategy may do, on its own line under the description. */
    const POLICY_SCOPE_FALLBACKS: Record<string, string> = {
        proportional: 'Purchases only: it sells nothing.',
    };
    const objectiveName = (code: string) => $t(`${PLANNER_KEY}.objectives.${code}`, {default: OBJECTIVE_FALLBACKS[code] ?? code});
</script>

<div class="space-y-4" data-testid="pac-planner-strategy">
    <p class="max-w-3xl text-sm text-gray-700 dark:text-gray-300">
        {$t('tools.pacAllocator.planner.strategy.intro', {default: 'Among all the purchase plans that respect what you set in the previous steps, the strategy picks the best one.'})}
    </p>

    {#if policies.length === 0}
        <div class={NOTICE.danger} role="alert" data-testid="pac-planner-strategy-none">{$t('tools.pacAllocator.planner.strategy.none', {default: 'The backend contract offers no strategy: the plan cannot be calculated.'})}</div>
    {/if}

    <fieldset class="max-w-3xl space-y-3">
        <legend class="sr-only">{$t('tools.pacAllocator.planner.steps.strategy', {default: 'Strategy'})}</legend>
        {#each policies as policy (policy)}
            {@const objectives = POLICY_OBJECTIVES[policy] ?? []}
            <div class={CARD} data-testid="pac-planner-policy" data-policy={policy}>
                <label for="{ids}-{policy}" class="flex cursor-pointer items-start gap-2">
                    <input
                        id="{ids}-{policy}"
                        type="radio"
                        name="{ids}-policy"
                        value={policy}
                        bind:group={draft.data.policy}
                        class="mt-1 shrink-0 accent-libre-green"
                        data-testid="pac-planner-policy-radio"
                    />
                    <span class="min-w-0">
                        <span class="block font-medium text-gray-900 dark:text-gray-100">{$t(`${PLANNER_KEY}.policies.${policy}`, {default: POLICY_FALLBACKS[policy] ?? policy})}</span>
                        {#if POLICY_HELP_FALLBACKS[policy]}
                            <span class="mt-0.5 block text-sm text-gray-600 dark:text-gray-400" data-testid="pac-planner-policy-help">
                                {$t(`${PLANNER_KEY}.policyHelp.${policy}`, {default: POLICY_HELP_FALLBACKS[policy]})}
                            </span>
                        {/if}
                        {#if POLICY_SCOPE_FALLBACKS[policy]}
                            <span class="mt-0.5 block text-sm text-gray-600 dark:text-gray-400" data-testid="pac-planner-policy-scope">
                                {$t(`${PLANNER_KEY}.policyScope.${policy}`, {default: POLICY_SCOPE_FALLBACKS[policy]})}
                            </span>
                        {/if}
                    </span>
                </label>
                {#if objectives.length > 0}
                    <div class="mt-4 border-t border-gray-100 pt-3 dark:border-gray-700">
                        <p class={SECTION_TITLE}>{$t('tools.pacAllocator.planner.strategy.cascade', {default: 'How it picks the plan, in order'})}</p>
                        <p class="mt-1 {HINT}" data-testid="pac-planner-policy-rule">
                            {$t('tools.pacAllocator.planner.strategy.cascadeRule', {default: 'Each criterion decides only among the plans still tied on the ones above it.'})}
                        </p>
                        <ol class="mt-3 space-y-2.5" data-testid="pac-planner-policy-objectives">
                            {#each objectives as objective, index (objective)}
                                {@const tip = OBJECTIVE_TIPS[objective]}
                                <li class="flex items-start gap-3" data-objective={objective}>
                                    <span class="{ICON_BUBBLE} text-xs font-semibold" aria-hidden="true">{index + 1}</span>
                                    <div class="min-w-0">
                                        <div class="flex flex-wrap items-center gap-0.5 text-sm font-medium text-gray-900 dark:text-gray-100">
                                            <span>{objectiveName(objective)}</span>
                                            {#if tip}
                                                <HelpTip
                                                    label={objectiveName(objective)}
                                                    help={$t(tip.key, {default: tip.fallback})}
                                                    math={tip.math}
                                                    spoken={tip.spoken ? $t(tip.spoken.key, {default: tip.spoken.fallback}) : undefined}
                                                    testid="pac-planner-objective-help"
                                                />
                                            {/if}
                                        </div>
                                        {#if OBJECTIVE_HELP_FALLBACKS[objective]}
                                            <p class={HINT}>{$t(`${PLANNER_KEY}.objectiveHelp.${objective}`, {default: OBJECTIVE_HELP_FALLBACKS[objective]})}</p>
                                        {/if}
                                    </div>
                                </li>
                            {/each}
                        </ol>
                        <div class="mt-2.5 flex items-start gap-3" data-testid="pac-planner-policy-tie-break">
                            <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400" aria-hidden="true"><Equal size={14} /></span>
                            <div class="min-w-0">
                                <p class="text-sm font-medium text-gray-900 dark:text-gray-100">{$t('tools.pacAllocator.planner.strategy.tieBreakTitle', {default: 'Final tie-break'})}</p>
                                <p class={HINT}>
                                    {$t('tools.pacAllocator.planner.strategy.tieBreak', {default: 'If a tie is still left, a fixed order of Assets and Brokers decides: the same data always give the same plan.'})}
                                </p>
                            </div>
                        </div>
                    </div>
                {/if}
            </div>
        {/each}
    </fieldset>
</div>
