<!--
  KpiDivergingFlowBar — Symmetric diverging bar for deposit/withdrawal visualization.

  Shows: label (with optional tooltip), net value, symmetric bar (left=withdrawals red, right=deposits green).

  Pattern: Svelte 5 Runes, Tailwind CSS 4.
-->
<script lang="ts">
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

    interface Props {
        label: string;
        value: string;
        tooltip?: string;
        tooltipHtml?: string;
        depositPct: number;
        withdrawPct: number;
        valueColor?: string;
    }

    let {label, value, tooltip = '', tooltipHtml = '', depositPct, withdrawPct, valueColor = 'text-gray-700 dark:text-gray-300'}: Props = $props();

    const clampedDeposit = $derived(Math.max(0, Math.min(depositPct, 100)));
    const clampedWithdraw = $derived(Math.max(0, Math.min(withdrawPct, 100)));
</script>

<div class="flex flex-col gap-0.5">
    <div class="flex items-center justify-between gap-2 text-xs">
        {#if tooltipHtml}
            <Tooltip html={tooltipHtml} position="top" wrapperClass="min-w-0">
                <span class="block truncate min-w-0 cursor-help border-b border-dotted border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400" title={label}>{label}</span>
            </Tooltip>
        {:else if tooltip}
            <Tooltip text={tooltip} position="top" wrapperClass="min-w-0">
                <span class="block truncate min-w-0 cursor-help border-b border-dotted border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400" title={label}>{label}</span>
            </Tooltip>
        {:else}
            <span class="block truncate min-w-0 text-gray-500 dark:text-gray-400" title={label}>{label}</span>
        {/if}
        <span class="shrink-0 whitespace-nowrap font-medium {valueColor}">{value}</span>
    </div>
    <!-- Diverging bar: left half = withdrawals (red), right half = deposits (green) -->
    <div class="relative w-full h-1.5 flex">
        <!-- Left half (withdrawals) -->
        <div class="relative w-1/2 h-full bg-gray-100 dark:bg-slate-700 rounded-l-full overflow-hidden">
            <div class="absolute right-0 top-0 h-full bg-red-400 dark:bg-red-500 rounded-l-full transition-all duration-700 ease-out" style="width: {clampedWithdraw}%"></div>
        </div>
        <!-- Center divider -->
        <div class="w-px h-full bg-gray-300 dark:bg-slate-500 flex-shrink-0"></div>
        <!-- Right half (deposits) -->
        <div class="relative w-1/2 h-full bg-gray-100 dark:bg-slate-700 rounded-r-full overflow-hidden">
            <div class="absolute left-0 top-0 h-full bg-green-500 dark:bg-green-400 rounded-r-full transition-all duration-700 ease-out" style="width: {clampedDeposit}%"></div>
        </div>
    </div>
</div>
