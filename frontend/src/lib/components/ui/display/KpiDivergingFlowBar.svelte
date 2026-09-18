<!--
  KpiDivergingFlowBar — Symmetric diverging bar around a centre line.

  Shows: label (with optional tooltip), value, and a track whose fill grows LEFT
  for the negative side and RIGHT for the positive side.

  Generic on purpose: it has nothing to do with the dashboard, and lives here so
  that anyone building a panel finds it. It was parked under `dashboard/` until
  the risk work needed it and did not think to look there.

  Two ways to feed it, because two shapes of data want the same picture:

  - `depositPct` / `withdrawPct` — two independent magnitudes (cash in vs cash
    out). This is what the dashboard passes.
  - `signedPct` — ONE signed magnitude (a risk contribution, an active weight).
    Positive fills right, negative fills left.

  Everything else is presentation and is optional. THE DEFAULTS REPRODUCE THE
  DASHBOARD RENDERING EXACTLY — if a change here alters how the dashboard looks,
  the change is wrong.

  Pattern: Svelte 5 Runes, Tailwind CSS 4.
-->
<script lang="ts">
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

    interface Props {
        label: string;
        value: string;
        tooltip?: string;
        tooltipHtml?: string;
        /** Magnitude of the right-hand (positive) side, 0-100. */
        depositPct?: number;
        /** Magnitude of the left-hand (negative) side, 0-100. */
        withdrawPct?: number;
        /**
         * One signed magnitude, -100..100, as an alternative to the pair above.
         * Consulted only when NEITHER `depositPct` nor `withdrawPct` is given.
         *
         * So a caller that passes one flow and also passes `signedPct` gets the
         * flow it asked for and a zero on the other side — the bar renders what
         * was written rather than guessing from the other prop.
         */
        signedPct?: number;
        valueColor?: string;
        /** Fill colour of the right-hand side. */
        positiveColor?: string;
        /** Fill colour of the left-hand side. */
        negativeColor?: string;
        /** Track height utility class. */
        barHeight?: string;
        /**
         * `stacked` — label and value on a line above the bar (the dashboard).
         * `inline`  — label │ bar │ value on a single row (dense tables).
         */
        layout?: 'stacked' | 'inline';
        /** Grid template used by `layout="inline"`. */
        inlineColumns?: string;
        /** Extra classes on the value element, e.g. `font-mono`. */
        valueClass?: string;
        /** Stable E2E selector placed on the root element. */
        testId?: string;
    }

    let {
        label,
        value,
        tooltip = '',
        tooltipHtml = '',
        depositPct,
        withdrawPct,
        signedPct,
        valueColor = 'text-gray-700 dark:text-gray-300',
        positiveColor = 'bg-green-500 dark:bg-green-400',
        negativeColor = 'bg-red-400 dark:bg-red-500',
        barHeight = 'h-1.5',
        layout = 'stacked',
        inlineColumns = 'minmax(7rem,1fr) minmax(10rem,2fr) 5rem',
        valueClass = '',
        testId,
    }: Props = $props();

    // An explicit pair always wins, so `signedPct` cannot silently override a
    // caller that passed only one of the two flows.
    const usesFlowPair = $derived(depositPct !== undefined || withdrawPct !== undefined);
    const rightPct = $derived(usesFlowPair ? (depositPct ?? 0) : Math.max(0, signedPct ?? 0));
    const leftPct = $derived(usesFlowPair ? (withdrawPct ?? 0) : Math.abs(Math.min(0, signedPct ?? 0)));

    /**
     * Clamp to 0..100, and send anything non-finite to 0.
     *
     * The NaN case is not theoretical bookkeeping. `width: NaN%` is invalid CSS,
     * so the browser DISCARDS the declaration and the fill keeps whatever width
     * it had before — a stale number presented as a current one, which is the
     * worst way for this component to fail. The dashboard never hit it because
     * its caller divides by `|| 1`; the risk panels that now reuse this bar have
     * no such guard and no reason to know one is needed.
     */
    const clampPct = (value: number): number => (Number.isFinite(value) ? Math.max(0, Math.min(value, 100)) : 0);

    const clampedDeposit = $derived(clampPct(rightPct));
    const clampedWithdraw = $derived(clampPct(leftPct));
</script>

{#snippet labelNode()}
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
{/snippet}

{#snippet track()}
    <!-- Diverging bar: left half = negative side, right half = positive side -->
    <div class="relative w-full {barHeight} flex">
        <div class="relative w-1/2 h-full bg-gray-100 dark:bg-slate-700 rounded-l-full overflow-hidden">
            <div class="absolute right-0 top-0 h-full {negativeColor} rounded-l-full transition-all duration-700 ease-out" style="width: {clampedWithdraw}%"></div>
        </div>
        <!-- Center divider -->
        <div class="w-px h-full bg-gray-300 dark:bg-slate-500 flex-shrink-0"></div>
        <div class="relative w-1/2 h-full bg-gray-100 dark:bg-slate-700 rounded-r-full overflow-hidden">
            <div class="absolute left-0 top-0 h-full {positiveColor} rounded-r-full transition-all duration-700 ease-out" style="width: {clampedDeposit}%"></div>
        </div>
    </div>
{/snippet}

{#if layout === 'inline'}
    <div class="grid items-center gap-2 text-xs" style="grid-template-columns: {inlineColumns}" data-testid={testId}>
        {@render labelNode()}
        {@render track()}
        <span class="text-right whitespace-nowrap font-medium {valueColor} {valueClass}">{value}</span>
    </div>
{:else}
    <div class="flex flex-col gap-0.5" data-testid={testId}>
        <div class="flex items-center justify-between gap-2 text-xs">
            {@render labelNode()}
            <span class="shrink-0 whitespace-nowrap font-medium {valueColor} {valueClass}">{value}</span>
        </div>
        {@render track()}
    </div>
{/if}
