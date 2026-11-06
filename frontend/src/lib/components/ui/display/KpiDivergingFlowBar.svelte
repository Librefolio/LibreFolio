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
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {SIGN_BAR} from '$lib/theme/toneClasses';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';

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
         * `responsive` — `inline` while its own box is at least `inlineFromWidth` wide, and under that the name and the
         *   value on one line with the bar below: the row follows the room it is given, not the screen (container query),
         *   so it holds in a narrow column of a wide screen as on a phone. The caller adds what goes under the bar.
         */
        layout?: 'stacked' | 'inline' | 'responsive';
        /** Grid template used by `layout="inline"`, and by `responsive` from `inlineFromWidth` up. */
        inlineColumns?: string;
        /**
         * The name scrolls when it does not fit (`scrollOnOverflow`), instead of being cut with an ellipsis; the full
         * name stays in the `title`. Only the plain label (no tooltip) scrolls.
         */
        scrollLabel?: boolean;
        /** Extra classes on the value element, e.g. `font-mono`. */
        valueClass?: string;
        /** Stable E2E selector placed on the root element. */
        testId?: string;
        /**
         * Stable E2E selector placed on the VALUE element alone.
         *
         * Separate from `testId`, and not derived from it, because the two
         * answer different questions. `testId` finds the row; this finds the
         * number, and a test that asserts the number's exact text cannot use the
         * root — the root also contains the label, so `toHaveText` would compare
         * against "Apple Inc.+60.0pp".
         *
         * Without it a caller whose value text is under test has to render that
         * text twice, once inside the bar and once in a span beside it, and two
         * copies of one number is how the two start disagreeing.
         */
        valueTestId?: string;
    }

    let {
        label,
        value,
        tooltip = '',
        tooltipHtml = '',
        depositPct,
        withdrawPct,
        signedPct,
        valueColor = 'text-lf-secondary',
        positiveColor = SIGN_BAR.kpi.gain,
        negativeColor = SIGN_BAR.kpi.loss,
        barHeight = 'h-1.5',
        layout = 'stacked',
        inlineColumns = 'minmax(7rem,1fr) minmax(10rem,2fr) 5rem',
        scrollLabel = false,
        valueClass = '',
        testId,
        valueTestId,
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
            <span class="block truncate min-w-0 cursor-help border-b border-dotted border-lf-input text-lf-muted" title={label}>{label}</span>
        </Tooltip>
    {:else if tooltip}
        <Tooltip text={tooltip} position="top" wrapperClass="min-w-0">
            <span class="block truncate min-w-0 cursor-help border-b border-dotted border-lf-input text-lf-muted" title={label}>{label}</span>
        </Tooltip>
    {:else if scrollLabel}
        <span use:scrollOnOverflow class="{overflowScrollTextClass} text-lf-muted" title={label}>{label}</span>
    {:else}
        <span class="block truncate min-w-0 text-lf-muted" title={label}>{label}</span>
    {/if}
{/snippet}

{#snippet track()}
    <!-- Diverging bar: left half = negative side, right half = positive side -->
    <div class="relative w-full {barHeight} flex">
        <div class="relative w-1/2 h-full bg-lf-neutral rounded-l-full overflow-hidden">
            <div class="absolute right-0 top-0 h-full {negativeColor} rounded-l-full transition-all duration-700 ease-out" style="width: {clampedWithdraw}%"></div>
        </div>
        <!-- Center divider -->
        <div class="w-px h-full bg-lf-input flex-shrink-0"></div>
        <div class="relative w-1/2 h-full bg-lf-neutral rounded-r-full overflow-hidden">
            <div class="absolute left-0 top-0 h-full {positiveColor} rounded-r-full transition-all duration-700 ease-out" style="width: {clampedDeposit}%"></div>
        </div>
    </div>
{/snippet}

{#if layout === 'responsive'}
    <!-- Narrow: name and value on the first line, the bar full width under them. From 26rem of its own width: name │ bar │
         value, as `inline`. The three cells are placed by grid lines, so one markup serves both. -->
    <div class="@container" data-testid={testId} data-layout="responsive">
        <div class="grid items-center gap-x-2 gap-y-1 text-xs grid-cols-[minmax(0,1fr)_auto] @[26rem]:grid-cols-[var(--lf-bar-columns)]" style="--lf-bar-columns: {inlineColumns}">
            <div class="min-w-0 col-start-1 row-start-1">{@render labelNode()}</div>
            <div class="col-span-2 row-start-2 @[26rem]:col-span-1 @[26rem]:col-start-2 @[26rem]:row-start-1">{@render track()}</div>
            <span class="col-start-2 row-start-1 text-right whitespace-nowrap font-medium @[26rem]:col-start-3 {valueColor} {valueClass}" data-testid={valueTestId}>{value}</span>
        </div>
    </div>
{:else if layout === 'inline'}
    <div class="grid items-center gap-2 text-xs" style="grid-template-columns: {inlineColumns}" data-testid={testId}>
        {@render labelNode()}
        {@render track()}
        <span class="text-right whitespace-nowrap font-medium {valueColor} {valueClass}" data-testid={valueTestId}>{value}</span>
    </div>
{:else}
    <div class="flex flex-col gap-0.5" data-testid={testId}>
        <div class="flex items-center justify-between gap-2 text-xs">
            {@render labelNode()}
            <span class="shrink-0 whitespace-nowrap font-medium {valueColor} {valueClass}" data-testid={valueTestId}>{value}</span>
        </div>
        {@render track()}
    </div>
{/if}
