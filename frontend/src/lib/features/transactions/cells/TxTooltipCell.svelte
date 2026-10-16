<!--
  TxTooltipCell — single-element TX table cell that wraps arbitrary inner HTML
  inside a real `<Tooltip>` component (replacing the native HTML `title=`
  attribute). Used by the `cash` and `broker` columns of TransactionsTable.

  Why a component: DataTable's `HtmlCell` doesn't render Svelte children, so
  injecting a Tooltip there would require touching DataTable's API. The
  CustomCell escape hatch keeps the table generic — the consumer owns the
  tooltip wiring.
-->
<script lang="ts">
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

    interface Props {
        /** Inner HTML rendered inside the Tooltip trigger span. */
        html: string;
        /** Tooltip text shown on hover/focus. */
        tooltip: string;
        /** Tooltip placement (default: top). */
        position?: 'top' | 'bottom' | 'left' | 'right';
    }

    let {html, tooltip, position = 'top'}: Props = $props();
</script>

<Tooltip text={tooltip} {position}>
    <span class="tx-tooltip-cell-inner">{@html html}</span>
</Tooltip>

<style>
    .tx-tooltip-cell-inner {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }
</style>
