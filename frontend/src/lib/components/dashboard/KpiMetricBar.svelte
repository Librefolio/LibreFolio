<!--
  KpiMetricBar — Reusable horizontal bar for KPI card metrics.

  Shows: label (with optional tooltip), value, colored bar.
  Optional caret marker on the bar for start-of-period reference.

  Pattern: Svelte 5 Runes, Tailwind CSS 4.
-->
<script lang="ts">
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

    interface Props {
        label: string;
        value: string;
        tooltip?: string;
        tooltipHtml?: string;
        barPct: number;
        barColor?: string;
        valueColor?: string;
        marker?: number;
        markerTooltip?: string;
    }

    let {
        label,
        value,
        tooltip = '',
        tooltipHtml = '',
        barPct,
        barColor = 'bg-slate-400 dark:bg-slate-500',
        valueColor = 'text-gray-700 dark:text-gray-300',
        marker,
        markerTooltip = '',
    }: Props = $props();

    const clampedBar = $derived(Math.max(0, Math.min(barPct, 100)));
    const clampedMarker = $derived(marker != null ? Math.max(0, Math.min(marker, 100)) : null);
</script>

<div class="flex flex-col gap-0.5">
    <div class="flex items-center justify-between text-xs">
        {#if tooltipHtml}
            <Tooltip html={tooltipHtml} position="top">
                <span class="cursor-help border-b border-dotted border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400">{label}</span>
            </Tooltip>
        {:else if tooltip}
            <Tooltip text={tooltip} position="top">
                <span class="cursor-help border-b border-dotted border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400">{label}</span>
            </Tooltip>
        {:else}
            <span class="text-gray-500 dark:text-gray-400">{label}</span>
        {/if}
        <span class="font-medium {valueColor}">{value}</span>
    </div>
    <div class="relative w-full h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full">
        <div class="h-full rounded-full transition-all {barColor}" style="width: {clampedBar}%"></div>
    </div>
    {#if clampedMarker != null && clampedMarker > 0 && markerTooltip}
        <div class="relative w-full h-0">
            <div class="absolute" style="left: {clampedMarker}%; transform: translateX(-50%); top: -15px;">
                <Tooltip text={markerTooltip} position="top">
                    <div class="w-0 h-0 border-l-[4px] border-r-[4px] border-b-[5px] border-l-transparent border-r-transparent border-b-gray-600 dark:border-b-gray-300 cursor-help"></div>
                </Tooltip>
            </div>
        </div>
    {/if}
</div>
