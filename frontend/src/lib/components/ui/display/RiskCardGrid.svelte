<!--
  RiskCardGrid — the one way risk cards are laid out.

  This is a component and not a documented class string, and the reason is a
  measurement rather than a preference: `components/risk/` already contains 20
  grid declarations in 12 distinct variants, including
  `RiskAnalysisPanel:632` → `grid-cols-1 sm:grid-cols-2 xl:grid-cols-5`. That is
  the very `1 → sm:2 → xl:5` jump the RiskMetricCard header denounces, still in
  place. A documented string is copy-paste, which is precisely the mechanism
  that produced those twenty: a document can describe a convention, it cannot
  stop five mandates from each adapting it. Twenty declarations are the proof
  that the documented-convention approach has already failed once here.

  No breakpoints, on purpose. `RiskMetricCard` sizes its own number with
  `@container` (`text-[clamp(0.95rem,8cqw,1.5rem)]`), so the grid does not need
  to enumerate viewport widths for the cards to stay readable — it only needs to
  say how narrow a card may get. `repeat(auto-fit, minmax(...))` enumerates
  nothing: the column count falls out of the space available. The old jump was
  the *symptom* of enumeration; auto-fit removes the cause instead.

  ⚠️ `min(minWidth, 100%)` and not a bare `minWidth`. With
  `minmax(16rem, 1fr)` a container narrower than 16rem still gets a 16rem track
  and overflows horizontally — on a narrow phone the cards would be cut off
  rather than stacked. `min(..., 100%)` caps the floor at the container's own
  width, so the last step down to a single column happens by itself.

  ⚠️ ROWS ARE ALWAYS FULL. Auto-fit alone fills as many columns as fit, so four
  cards at a width that fits three came out as three and then one, alone on a
  row of its own (developer's review of 05/10/2026: "sempre in riga, 2x2 o in
  colonna"). Once the grid is on screen it measures how many columns fit and
  lowers that to the largest count that divides the number of cards: four cards
  go 4, 2 or 1 across, three go 3 or 1. Still no breakpoint is enumerated: both
  numbers come from the space and from the cards. Until the first measurement
  the auto-fit template stands, so nothing is hidden before it.

  Only `minWidth` is exposed. Gap is fixed at `gap-4`, matching `KpiSection`,
  and that omission is deliberate: a second knob is a second axis along which
  five surfaces can drift apart, which is the defect this component exists to
  remove. A surface that truly needs different spacing should say so and get it
  added here once, for everyone.

  Pattern: Svelte 5 Runes, Tailwind CSS 4.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';

    interface Props {
        /**
         * Narrowest a card may become before the grid drops a column.
         * The default suits a `RiskMetricCard` showing a number and a caption;
         * raise it for cards carrying submetrics or a sparkline.
         */
        minWidth?: string;
        /** Stable E2E selector for the grid root. */
        testId?: string;
        /** The cards. */
        children: Snippet;
    }

    let {minWidth = '16rem', testId, children}: Props = $props();

    let grid: HTMLDivElement | undefined = $state(undefined);
    /** Columns that keep every row full; `null` until the grid has been measured. */
    let columns: number | null = $state(null);

    const autoFitColumns = $derived(`repeat(auto-fit, minmax(min(${minWidth}, 100%), 1fr))`);
    const templateColumns = $derived(columns === null ? autoFitColumns : `repeat(${columns}, minmax(0, 1fr))`);

    /** `minWidth` in pixels: rem against the root font size, px as written. */
    function minWidthPx(): number {
        const value = parseFloat(minWidth);
        if (minWidth.endsWith('rem')) return value * parseFloat(getComputedStyle(document.documentElement).fontSize);
        return value;
    }

    /** The most columns that fit, lowered to the largest count that divides the cards. */
    function measure(): void {
        if (!grid) return;
        const cards = grid.children.length;
        // No width is no layout yet — a hidden tab, or jsdom — and auto-fit is the honest answer there.
        if (cards === 0 || grid.clientWidth === 0) {
            columns = null;
            return;
        }
        const gap = parseFloat(getComputedStyle(grid).columnGap) || 0;
        const fit = Math.max(1, Math.floor((grid.clientWidth + gap) / (minWidthPx() + gap)));
        let count = Math.min(fit, cards);
        while (cards % count !== 0) count -= 1;
        columns = count;
    }

    $effect(() => {
        if (!grid) return;
        void minWidth;
        measure();
        // The width changes with the window, the count with the data: a card can come and go
        // under `{#if}`, and a resize alone would leave the old count in place.
        const resizeObserver = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => measure());
        const childObserver = new MutationObserver(() => measure());
        resizeObserver?.observe(grid);
        childObserver.observe(grid, {childList: true});
        return () => {
            resizeObserver?.disconnect();
            childObserver.disconnect();
        };
    });
</script>

<div bind:this={grid} class="grid gap-4" style="grid-template-columns: {templateColumns};" data-testid={testId} data-columns={columns ?? ''}>
    {@render children()}
</div>
