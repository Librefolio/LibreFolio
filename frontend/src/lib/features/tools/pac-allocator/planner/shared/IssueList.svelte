<script lang="ts">
    import {CircleAlert, Info, TriangleAlert} from 'lucide-svelte';
    import {t} from '$lib/i18n';
    import {STEP_FALLBACKS, stepKey, type ListedIssue} from '../labels';
    import type {PlannerStep} from '../types';
    import {BUTTON_LINK} from '../ui';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        items: readonly ListedIssue[];
        /** `null` hides the "Go to" buttons (read-only lists). */
        ongoto?: ((step: PlannerStep) => void) | null;
        /** Show the backend code next to each message ([Details]). */
        showCodes?: boolean;
        testid: string;
    }

    let {items, ongoto = null, showCodes = false, testid}: Props = $props();
</script>

<ul class="divide-y divide-gray-100 dark:divide-gray-700" data-testid={testid}>
    {#each items as item (item.id)}
        <li class="flex flex-wrap items-start gap-3 py-2" data-testid="{testid}-item" data-code={item.code ?? ''} data-step={item.step ?? ''} data-severity={item.severity}>
            <span class="mt-0.5 shrink-0" aria-hidden="true">
                {#if item.severity === 'error'}
                    <CircleAlert size={16} class="text-red-600 dark:text-red-400" />
                {:else if item.severity === 'warning'}
                    <TriangleAlert size={16} class="text-amber-600 dark:text-amber-400" />
                {:else}
                    <Info size={16} class="text-sky-600 dark:text-sky-400" />
                {/if}
            </span>
            <div class="min-w-0 flex-1 text-sm">
                {#if item.step}
                    <span class="font-medium text-gray-900 dark:text-gray-100">{$t(stepKey(item.step), {default: STEP_FALLBACKS[item.step]})}</span>
                {/if}
                {#if item.entity}
                    <span class="text-gray-700 dark:text-gray-200">· {item.entity}</span>
                {/if}
                <span class="text-gray-700 dark:text-gray-200">· {$t(item.key, {default: item.fallback, values: item.values})}</span>
                {#if showCodes && item.code}
                    <code class="ml-1 rounded bg-gray-100 px-1 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300" data-testid="{testid}-code">{item.code}</code>
                {/if}
            </div>
            {#if ongoto && item.step}
                {@const step = item.step}
                <button type="button" class={BUTTON_LINK} data-testid="{testid}-goto" onclick={() => ongoto?.(step)}>
                    {$t(`${PLANNER_KEY}.actions.goTo`, {default: 'Go to {step}', values: {step: $t(stepKey(step), {default: STEP_FALLBACKS[step]})}})}
                </button>
            {/if}
        </li>
    {/each}
</ul>
