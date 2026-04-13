<!--
  FxPriceSummary.svelte — Price summary for FX detail page.

  Extends the same visual pattern as AssetPriceSummary:
  - Delta % (left) | Rate (right)

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {TrendingUp, TrendingDown} from 'lucide-svelte';
    import type {LayoutMode} from '$lib/utils/responsiveLayout.svelte';

    interface Props {
        /** Last exchange rate */
        lastRate: number | null;
        /** Period delta in percent */
        deltaPercent: number | null;
        /** Current responsive layout mode */
        layoutMode: LayoutMode;
    }

    let {
        lastRate,
        deltaPercent,
        layoutMode,
    }: Props = $props();
</script>

{#if lastRate !== null}
    <div class="flex items-center gap-3 {layoutMode === 'wide' ? 'px-3' : 'justify-center'}">
        <!-- Left half: rate -->
        <span class="font-mono text-lg font-semibold text-gray-700 dark:text-gray-200">
            {lastRate.toFixed(4)}
        </span>

        <!-- Right half: delta % -->
        {#if deltaPercent !== null}
            <span class="flex items-center gap-0.5 text-xs font-medium {deltaPercent >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'}">
                {#if deltaPercent >= 0}<TrendingUp size={12}/>{:else}<TrendingDown size={12}/>{/if}
                {deltaPercent >= 0 ? '+' : ''}{deltaPercent.toFixed(2)}%
            </span>
        {/if}
    </div>
{/if}

