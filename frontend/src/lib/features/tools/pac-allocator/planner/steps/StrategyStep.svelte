<script lang="ts">
    import {t} from '$lib/i18n';
    import type {PlannerDraft} from '../draft.svelte';
    import {contractPolicies, OBJECTIVE_FALLBACKS, POLICY_OBJECTIVES} from '../policies';
    import {CARD, HINT, NOTICE} from '../ui';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        draft: PlannerDraft;
    }

    let {draft}: Props = $props();

    const ids = $props.id();
    const policies = contractPolicies();
    const POLICY_FALLBACKS: Record<string, string> = {proportional: 'Proportional'};
</script>

<div class="space-y-4" data-testid="pac-planner-strategy">
    <p class="text-sm text-gray-700 dark:text-gray-300">{$t('tools.pacAllocator.planner.strategy.intro', {default: 'Every constraint of the previous steps stays hard.'})}</p>

    {#if policies.length === 0}
        <div class={NOTICE.danger} role="alert" data-testid="pac-planner-strategy-none">{$t('tools.pacAllocator.planner.strategy.none', {default: 'The backend contract offers no strategy: the plan cannot be calculated.'})}</div>
    {/if}

    <fieldset class="space-y-3">
        <legend class="sr-only">{$t('tools.pacAllocator.planner.steps.strategy', {default: 'Strategy'})}</legend>
        {#each policies as policy (policy)}
            {@const objectives = POLICY_OBJECTIVES[policy] ?? []}
            <div class={CARD} data-testid="pac-planner-policy" data-policy={policy}>
                <label for="{ids}-{policy}" class="flex items-center gap-2 font-medium">
                    <input id="{ids}-{policy}" type="radio" name="{ids}-policy" value={policy} bind:group={draft.data.policy} data-testid="pac-planner-policy-radio" />
                    {$t(`${PLANNER_KEY}.policies.${policy}`, {default: POLICY_FALLBACKS[policy] ?? policy})}
                </label>
                {#if objectives.length > 0}
                    <p class="mt-3 text-sm">{$t('tools.pacAllocator.planner.strategy.cascade', {default: 'Order of the objectives, most important first:'})}</p>
                    <ol class="mt-1 list-decimal space-y-0.5 pl-6 text-sm" data-testid="pac-planner-policy-objectives">
                        {#each objectives as objective (objective)}
                            <li data-objective={objective}>{$t(`${PLANNER_KEY}.objectives.${objective}`, {default: OBJECTIVE_FALLBACKS[objective] ?? objective})}</li>
                        {/each}
                    </ol>
                {/if}
                <p class="mt-2 {HINT}">{$t('tools.pacAllocator.planner.strategy.noParameters', {default: 'Additional parameters: none.'})}</p>
            </div>
        {/each}
    </fieldset>
    <p class={NOTICE.info}>{$t('tools.pacAllocator.planner.strategy.fromContract', {default: 'Strategies come from the backend contract.'})}</p>
</div>
