<!--
  KpiCard — Key Performance Indicator card for the Dashboard Home.

  Displays a single KPI metric with optional change indicator (gain/loss).
  Three instances are shown in the top row of the dashboard:
    1. Net Worth
    2. Gain / Loss
    3. Weighted ROI (TWRR + MWRR)

  Props:
  - label: Card title (translated by parent)
  - value: Primary formatted value string (e.g. "EUR 124,500.00")
  - subLabel: Secondary line (e.g. "TWRR: 12.1% | MWRR: 11.2%")
  - changeValue: Change amount string (e.g. "+14,250.32")
  - changePercent: Change percentage (number, used for positive/negative styling)
  - positive: Override for green/red coloring (inferred from changePercent if omitted)
  - loading: Show skeleton placeholder
  - refreshing: Data is being refreshed — show value at reduced opacity

  Pattern: Svelte 5 Runes, Tailwind CSS 4, dark mode.
-->
<script lang="ts">
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {SIGN_BAR, SIGN_TEXT} from '$lib/theme/toneClasses';

    interface Props {
        label: string;
        value: string;
        subLabel?: string;
        changeValue?: string;
        changePercent?: number;
        /** Override gain/loss color — inferred from changePercent if not provided. */
        positive?: boolean;
        loading?: boolean;
        /** When true, show existing value at reduced opacity (stale-while-revalidate). */
        refreshing?: boolean;
    }

    let {label, value, subLabel, changeValue, changePercent, positive, loading = false, refreshing = false}: Props = $props();

    const isPositive = $derived(positive ?? (changePercent !== undefined ? changePercent >= 0 : undefined));
</script>

<div class="relative bg-lf-card text-lf-primary rounded-xl border border-lf-subtle shadow-sm shadow-lf-shadow-card p-6 flex flex-col gap-1 overflow-hidden" data-testid="kpi-card">
    <!-- Subtle accent line on top based on positive/negative state -->
    {#if isPositive !== undefined}
        <div class="absolute top-0 left-0 right-0 h-0.5 {isPositive ? SIGN_BAR.accent.gain : SIGN_BAR.accent.loss}"></div>
    {/if}

    <!-- Label -->
    <p use:scrollOnOverflow class="{overflowScrollTextClass} text-xs font-medium uppercase tracking-wide text-lf-muted" title={label}>
        {label}
    </p>

    {#if loading}
        <!-- Skeleton -->
        <div class="mt-1 h-8 w-3/4 bg-lf-neutral rounded animate-pulse"></div>
        {#if subLabel !== undefined}
            <div class="mt-1 h-4 w-1/2 bg-lf-panel rounded animate-pulse"></div>
        {/if}
    {:else}
        <!-- Primary value (reduced opacity when refreshing for stale-while-revalidate) -->
        <p use:scrollOnOverflow class="{overflowScrollTextClass} text-2xl font-bold text-lf-primary transition-opacity duration-300" class:opacity-50={refreshing} data-testid="kpi-value" title={value}>
            {value}
        </p>

        <!-- Change badge (gain / loss) -->
        {#if changeValue !== undefined || changePercent !== undefined}
            <p class="text-sm font-medium transition-opacity duration-300 {isPositive ? SIGN_TEXT.kpi.gain : SIGN_TEXT.kpi.loss}" class:opacity-50={refreshing} data-testid="kpi-change">
                {changeValue ?? ''}{changeValue !== undefined && changePercent !== undefined ? ' ' : ''}{changePercent !== undefined ? `(${formatPercent(changePercent)})` : ''}
            </p>
        {/if}

        <!-- Sub-label (e.g. TWRR / MWRR breakdown) -->
        {#if subLabel}
            <p use:scrollOnOverflow class="{overflowScrollTextClass} text-xs text-lf-muted mt-0.5 transition-opacity duration-300" class:opacity-50={refreshing} data-testid="kpi-sublabel" title={subLabel}>
                {subLabel}
            </p>
        {/if}
    {/if}
</div>
