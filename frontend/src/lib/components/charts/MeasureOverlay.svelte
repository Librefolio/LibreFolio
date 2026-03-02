<!-- MeasureOverlay — STUB. Will be implemented in Step 6.
     Click-drag on chart to show trend arrow with metrics (delta, %, days, values). -->
<script lang="ts">
    interface Props { enabled?: boolean; }
    let { enabled = false }: Props = $props();
</script>
{#if enabled}
<div class="hidden">MeasureOverlay placeholder</div>
{/if}
