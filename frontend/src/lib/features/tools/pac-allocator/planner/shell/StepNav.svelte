<script lang="ts">
    import {ChevronDown, ChevronUp, Circle, CircleAlert, CircleCheck, CircleDot} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import {STEP_FALLBACKS, stepKey} from '../labels';
    import {PLANNER_STEPS, type PlannerStep} from '../types';

    interface Props {
        current: PlannerStep;
        visited: ReadonlySet<PlannerStep>;
        problemSteps: ReadonlySet<PlannerStep>;
        variant: 'vertical' | 'horizontal' | 'compact';
        disabled?: boolean;
        onselect: (step: PlannerStep) => void;
    }

    let {current, visited, problemSteps, variant, disabled = false, onselect}: Props = $props();

    let open = $state(false);

    const index = $derived(PLANNER_STEPS.indexOf(current));
    const progress = $derived([Math.round(((index + 1) / PLANNER_STEPS.length) * 100), '%'].join(''));

    function stepState(step: PlannerStep): 'current' | 'problem' | 'visited' | 'pending' {
        if (step === current) return 'current';
        if (!visited.has(step)) return 'pending';
        return problemSteps.has(step) ? 'problem' : 'visited';
    }

    function label(step: PlannerStep): string {
        return $t(stepKey(step), {default: STEP_FALLBACKS[step]});
    }

    function choose(step: PlannerStep): void {
        open = false;
        onselect(step);
    }

    const stateLabels = $derived({
        current: $t('tools.pacAllocator.planner.nav.current', {default: 'current step'}),
        problem: $t('tools.pacAllocator.planner.nav.problem', {default: 'to complete'}),
        visited: $t('tools.pacAllocator.planner.nav.visited', {default: 'visited'}),
        pending: $t('tools.pacAllocator.planner.nav.pending', {default: 'not visited'}),
    });
</script>

{#snippet marker(step: PlannerStep)}
    {@const value = stepState(step)}
    {#if value === 'current'}
        <CircleDot class="h-4 w-4 shrink-0 text-libre-green" aria-hidden="true" />
    {:else if value === 'problem'}
        <CircleAlert class="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
    {:else if value === 'visited'}
        <CircleCheck class="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
    {:else}
        <Circle class="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
    {/if}
{/snippet}

{#snippet list(horizontal: boolean)}
    <ol class={horizontal ? 'flex flex-wrap gap-1' : 'space-y-1'}>
        {#each PLANNER_STEPS as step, position (step)}
            {@const value = stepState(step)}
            <li>
                <button
                    type="button"
                    class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-60 {value === 'current'
                        ? 'bg-emerald-50 font-semibold text-gray-900 dark:bg-emerald-900/30 dark:text-white'
                        : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'}"
                    aria-current={value === 'current' ? 'step' : undefined}
                    {disabled}
                    data-testid="pac-planner-nav-step"
                    data-step={step}
                    data-state={value}
                    onclick={() => choose(step)}
                >
                    {@render marker(step)}
                    <span class="tabular-nums">{position + 1}</span>
                    <span>{label(step)}</span>
                    <span class="sr-only">({stateLabels[value]})</span>
                </button>
            </li>
        {/each}
    </ol>
{/snippet}

<nav aria-label={$t('tools.pacAllocator.planner.nav.label', {default: 'Configuration progress'})} data-testid="pac-planner-nav" data-variant={variant}>
    {#if variant === 'compact'}
        <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-medium" data-testid="pac-planner-nav-position">
                {$t('tools.pacAllocator.planner.nav.position', {default: '{index}/{total} {step}', values: {index: index + 1, total: PLANNER_STEPS.length, step: label(current)}})}
            </p>
            <button type="button" class="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-2 py-1 text-sm dark:border-gray-600" aria-expanded={open} aria-controls="pac-planner-nav-list" {disabled} data-testid="pac-planner-nav-toggle" onclick={() => (open = !open)}>
                {$t('tools.pacAllocator.planner.nav.steps', {default: 'Steps'})}
                {#if open}<ChevronUp class="h-4 w-4" aria-hidden="true" />{:else}<ChevronDown class="h-4 w-4" aria-hidden="true" />{/if}
            </button>
        </div>
        <div class="mt-2 h-1.5 w-full rounded bg-gray-200 dark:bg-gray-700" aria-hidden="true">
            <div class="h-1.5 rounded bg-libre-green motion-safe:transition-[width]" style:width={progress}></div>
        </div>
        {#if open}
            <div id="pac-planner-nav-list" class="mt-2" data-testid="pac-planner-nav-list">{@render list(false)}</div>
        {/if}
    {:else}
        {@render list(variant === 'horizontal')}
    {/if}
</nav>
