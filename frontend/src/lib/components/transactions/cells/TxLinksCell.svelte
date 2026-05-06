<!--
  TxLinksCell — TX table cell that hosts up to two action icons (event-dot +
  link-icon), each with its own `<Tooltip>`. Replaces the previous `HtmlCell`
  flavor that used inline `title=""` attributes (triggering the native browser
  tooltip in addition to / instead of the styled one).

  The cell is "custom" because DataTable's HtmlCell only supports a single
  whole-cell tooltip; here we need two distinct ones with different text and
  positioning, in the same cell.
-->
<script lang="ts">
    import Tooltip from '$lib/components/ui/Tooltip.svelte';

    interface Props {
        /** HTML for the `tx-event-dot` button (asset-event linkage). Empty/undefined → not rendered. */
        eventHtml?: string;
        /** Tooltip text for the event dot. */
        eventTooltip?: string;
        /** HTML for the partner-arrow + `tx-link-icon` button (linked TX pair). */
        linkHtml?: string;
        /** Tooltip text for the link icon. */
        linkTooltip?: string;
    }

    let {eventHtml = '', eventTooltip = '', linkHtml = '', linkTooltip = ''}: Props = $props();
</script>

<div class="tx-links-cell">
    {#if eventHtml}
        <Tooltip text={eventTooltip} position="top">
            <span class="tx-links-slot">{@html eventHtml}</span>
        </Tooltip>
    {/if}
    {#if linkHtml}
        <Tooltip html={linkTooltip} position="top">
            <span class="tx-links-slot">{@html linkHtml}</span>
        </Tooltip>
    {/if}
</div>

<style>
    .tx-links-cell {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }
    .tx-links-slot {
        display: inline-flex;
        align-items: center;
    }
</style>
