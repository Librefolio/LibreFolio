<!--
  RiskMetricCard — One metric of the risk subsystem, presented once.

  Built on the card that already works: `KpiSection.svelte` Card 1. Every piece
  below is there for a reason that was measured, not chosen by taste:

  - `@container` + `text-[clamp(...)]` — the number scales with ITS CONTAINER,
    not the viewport. This is the real answer to "not optimised for screens":
    the old grid jumped `1 → sm:2 → xl:5` with nothing in between, so a 1366px
    laptop got two columns for five cards and one orphan on a third row. Adding
    breakpoints treats the symptom; sizing on the container removes the cause.
  - Accent strip — the sign is readable BEFORE the digits are.
  - `class:invisible` over an absolutely-positioned placeholder — the value
    stays in the DOM while loading, so nothing moves when it arrives. Cards 2
    and 3 of KpiSection use `{#if loading}{:else}` and DO shift; they are not
    the model.

  ⚠️ THE NO-SHIFT GUARANTEE COVERS THE VALUE LINE ONLY, AND THE REST IS ON THE
  CALLER. `caption`, `sparkline` and `submetrics` sit behind `{#if}` *inside*
  the invisible wrapper, so a caller who supplies them only once the data has
  arrived still gets a jump — and gets it precisely on the fullest panels, where
  it is most visible. If you pass any of the three, pass them during `loading`
  too, empty or as placeholders. The card cannot invent a caption it was never
  given; this half of the contract lives with whoever renders it.

  - `TweenedValue` + `tabular-nums` — digits do not dance mid-transition.
  - Double label — the plain-language question as the title, the technical name
    beside it. Someone who does not know what VaR is reads "A bad day (1 in
    20)"; someone who does finds `VaR 95%`; someone who wants to learn clicks ⓘ.

  The sparkline slot is OPTIONAL and must be filled only where a series really
  exists. On Dashboard and Broker Detail a portfolio rolling series does not
  exist anywhere in the codebase — `SignalDomain` has exactly two values, ASSET
  and FX — so the slot stays empty there, and that is correct, not missing (D18).

  Pattern: Svelte 5 Runes, Tailwind CSS 4.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';

    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import TweenedValue from '$lib/components/ui/TweenedValue.svelte';

    interface Props {
        /** Plain-language title. The question the metric answers. */
        label: string;
        /** Technical name shown small beside the title, e.g. `VaR 95%`. */
        technicalName?: string;
        /** Pre-formatted value. Used when `numericValue` is absent, and as the loading-time placeholder width. */
        value?: string;
        /** Raw value for the animated number. When set, `formatValue` is required. */
        numericValue?: number;
        /** Formatter for `numericValue`. */
        formatValue?: (value: number) => string;
        /** Secondary line under the value, e.g. a comparison or a unit. */
        caption?: string;
        /**
         * Sign of the metric, for the accent strip and the value colour.
         * `undefined` means "no opinion" — no strip, neutral text. A risk
         * metric is often neither good nor bad, so neutral is the default.
         */
        sentiment?: 'positive' | 'negative' | 'neutral';
        /** MkDocs path for the ⓘ link. Omitted → no link. Slugs come from the docs mandate. */
        docsPath?: string;
        /** Whether to show the skeleton instead of the value. */
        loading?: boolean;
        /** Stable E2E selector for the card root. */
        testId?: string;
        /** Sub-metric rows — normally `KpiMetricBar` instances. */
        submetrics?: Snippet;
        /** Optional sparkline. Fill ONLY where a real series exists. */
        sparkline?: Snippet;
    }

    let {label, technicalName, value = '—', numericValue, formatValue, caption, sentiment = 'neutral', docsPath, loading = false, testId, submetrics, sparkline}: Props = $props();

    const accentClass = $derived(sentiment === 'positive' ? 'bg-green-500 dark:bg-green-400' : sentiment === 'negative' ? 'bg-red-500 dark:bg-red-400' : null);
    const valueClass = $derived(sentiment === 'positive' ? 'text-green-700 dark:text-green-400' : sentiment === 'negative' ? 'text-red-700 dark:text-red-400' : 'text-gray-800 dark:text-gray-100');
</script>

<div class="relative @container bg-white dark:bg-slate-800 rounded-xl border border-gray-100 dark:border-slate-700 shadow-sm p-5 flex flex-col gap-2 overflow-hidden" data-testid={testId}>
    {#if accentClass}
        <div class="absolute top-0 left-0 right-0 h-0.5 {accentClass}" data-testid={testId ? `${testId}-accent` : undefined}></div>
    {/if}

    <div class="flex items-start justify-between gap-2">
        <div class="min-w-0">
            <p class="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500 truncate" title={label} data-testid={testId ? `${testId}-label` : undefined}>{label}</p>
            {#if technicalName}
                <p class="text-[10px] text-gray-400 dark:text-gray-600 truncate" title={technicalName} data-testid={testId ? `${testId}-technical` : undefined}>{technicalName}</p>
            {/if}
        </div>
        {#if docsPath}
            <DocsLink path={docsPath} {label} size={14} testId={testId ? `${testId}-docs` : undefined} />
        {/if}
    </div>

    <div class="relative">
        {#if loading}
            <div class="absolute inset-0 z-10 flex flex-col gap-2" data-testid={testId ? `${testId}-skeleton` : undefined}>
                <div class="h-7 w-3/4 bg-gray-200 dark:bg-slate-700 rounded animate-pulse"></div>
                <div class="h-3 w-1/2 bg-gray-100 dark:bg-slate-700 rounded animate-pulse"></div>
            </div>
        {/if}
        <div class:invisible={loading}>
            <p class="text-[clamp(0.95rem,8cqw,1.5rem)] font-bold text-right tabular-nums transition-colors duration-300 {valueClass}" data-testid={testId ? `${testId}-value` : undefined}>
                {#if numericValue !== undefined && formatValue}
                    <TweenedValue value={numericValue} format={formatValue} duration={700} />
                {:else}
                    {value}
                {/if}
            </p>

            {#if caption}
                <p class="text-xs text-right text-gray-500 dark:text-gray-400 truncate" title={caption} data-testid={testId ? `${testId}-caption` : undefined}>{caption}</p>
            {/if}

            {#if sparkline}
                <div class="mt-2" data-testid={testId ? `${testId}-sparkline` : undefined}>
                    {@render sparkline()}
                </div>
            {/if}

            {#if submetrics}
                <div class="flex flex-col gap-2 mt-2">
                    {@render submetrics()}
                </div>
            {/if}
        </div>
    </div>
</div>
