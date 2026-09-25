<script lang="ts">
    import {t} from '$lib/i18n';
    import {formatExactPercent} from '../format';
    import {UNAVAILABLE_FALLBACKS, weightWidth, type WeightRow} from './model';
    const PLANNER_KEY = 'tools.pacAllocator.planner';

    interface Props {
        rows: readonly WeightRow[];
        testid: string;
    }

    let {rows, testid}: Props = $props();
</script>

<ul class="space-y-3" data-testid={testid}>
    {#each rows as row (row.id)}
        <li class="grid grid-cols-1 gap-1 text-sm sm:grid-cols-[minmax(0,14rem)_5rem_5rem_minmax(0,1fr)] sm:items-center sm:gap-x-3" data-testid="{testid}-row" data-id={row.id}>
            <span class="min-w-0 break-words font-medium text-gray-900 dark:text-gray-100">{row.label}</span>
            <span class="tabular-nums text-gray-700 dark:text-gray-200 sm:text-right" data-testid="{testid}-target">
                <span class="sm:sr-only">{$t(`${PLANNER_KEY}.result.weights.targetShort`, {default: 'T'})}</span>
                {formatExactPercent(row.target)}
            </span>
            <span class="tabular-nums text-gray-700 dark:text-gray-200 sm:text-right" data-testid="{testid}-final">
                <span class="sm:sr-only">{$t(`${PLANNER_KEY}.result.weights.finalShort`, {default: 'A'})}</span>
                {#if row.final.kind === 'available'}
                    {formatExactPercent(row.final.value)}
                {:else}
                    <span title={$t(`${PLANNER_KEY}.result.unavailable.${row.final.reason}`, {default: UNAVAILABLE_FALLBACKS[row.final.reason]})}>—</span>
                    <span class="sr-only">{$t(`${PLANNER_KEY}.result.unavailable.${row.final.reason}`, {default: UNAVAILABLE_FALLBACKS[row.final.reason]})}</span>
                {/if}
            </span>
            <span class="space-y-1" aria-hidden="true">
                <span class="flex items-center gap-2">
                    <span class="w-3 text-xs text-gray-500 dark:text-gray-400">{$t(`${PLANNER_KEY}.result.weights.targetShort`, {default: 'T'})}</span>
                    <span class="h-2 flex-1 rounded bg-gray-100 dark:bg-gray-700">
                        <span class="block h-2 rounded bg-gray-400 dark:bg-gray-400" style:width={weightWidth(row.target)}></span>
                    </span>
                </span>
                <span class="flex items-center gap-2">
                    <span class="w-3 text-xs text-gray-500 dark:text-gray-400">{$t(`${PLANNER_KEY}.result.weights.finalShort`, {default: 'A'})}</span>
                    <span class="h-2 flex-1 rounded bg-gray-100 dark:bg-gray-700">
                        <span class="block h-2 rounded bg-libre-green" style:width={weightWidth(row.final)}></span>
                    </span>
                </span>
            </span>
        </li>
    {/each}
</ul>
