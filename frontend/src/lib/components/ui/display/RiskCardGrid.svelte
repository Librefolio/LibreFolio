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

    const templateColumns = $derived(`repeat(auto-fit, minmax(min(${minWidth}, 100%), 1fr))`);
</script>

<div class="grid gap-4" style="grid-template-columns: {templateColumns};" data-testid={testId}>
    {@render children()}
</div>
