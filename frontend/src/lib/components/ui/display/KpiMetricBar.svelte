<!--
  KpiMetricBar — Horizontal labelled bar for a single metric.

  Shows: label (with optional tooltip), value, colored bar.
  Optional caret marker on the bar for start-of-period reference.

  Generic on purpose: it has nothing to do with the dashboard, and lives here so
  that anyone building a panel finds it. It was parked under `dashboard/` until
  the risk work needed it and did not think to look there.

  Pattern: Svelte 5 Runes, Tailwind CSS 4.
-->
<script lang="ts">
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import TweenedValue from '$lib/components/ui/TweenedValue.svelte';

    interface Props {
        label: string;
        value: string;
        /** Raw numeric value for tweened animation. When provided, overrides `value` display with TweenedValue. */
        numericValue?: number;
        /** Format function for numericValue. Required when numericValue is set. */
        formatValue?: (v: number) => string;
        tooltip?: string;
        tooltipHtml?: string;
        barPct: number;
        barColor?: string;
        valueColor?: string;
        marker?: number;
        markerTooltip?: string;
    }

    let {label, value, numericValue, formatValue, tooltip = '', tooltipHtml = '', barPct, barColor = 'bg-slate-400 dark:bg-slate-500', valueColor = 'text-gray-700 dark:text-gray-300', marker, markerTooltip = ''}: Props = $props();

    /**
     * Clamp to 0..100, and send anything non-finite to 0.
     *
     * `width: NaN%` is invalid CSS, so the browser DISCARDS the declaration and
     * the fill keeps whatever width it had before — a stale number presented as
     * a current one. The dashboard never hit it because its caller divides by
     * `|| 1`; the risk panels that now reuse this bar have no such guard.
     */
    const clampPct = (value: number): number => (Number.isFinite(value) ? Math.max(0, Math.min(value, 100)) : 0);

    const clampedBar = $derived(clampPct(barPct));
    /**
     * A non-finite marker becomes "no marker".
     *
     * The template's `clampedMarker > 0` test already excluded NaN, because
     * every comparison with NaN is false — but that is an accident of IEEE
     * semantics that happens to help here, not an expressed intention, and it
     * would stop helping the moment that condition is rewritten. Stating it
     * makes the marker path safe for a reason instead of by luck.
     */
    const clampedMarker = $derived(marker != null && Number.isFinite(marker) ? clampPct(marker) : null);
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
        <span class="shrink-0 whitespace-nowrap font-medium tabular-nums transition-colors duration-300 {valueColor}">
            {#if numericValue !== undefined && formatValue}
                <TweenedValue value={numericValue} format={formatValue} duration={700} />
            {:else}
                {value}
            {/if}
        </span>
    </div>
    <div class="relative w-full h-1.5 bg-gray-100 dark:bg-slate-700 rounded-full">
        <div class="h-full rounded-full transition-all duration-700 ease-out {barColor}" style="width: {clampedBar}%"></div>
    </div>
    {#if clampedMarker != null && clampedMarker > 0 && markerTooltip}
        <div class="relative w-full h-0">
            <div class="absolute transition-[left] duration-700 ease-out" style="left: {clampedMarker}%; transform: translateX(-50%); top: -15px;">
                <Tooltip text={markerTooltip} position="top">
                    <div class="w-0 h-0 border-l-[4px] border-r-[4px] border-b-[5px] border-l-transparent border-r-transparent border-b-gray-600 dark:border-b-gray-300 cursor-help"></div>
                </Tooltip>
            </div>
        </div>
    {/if}
</div>
