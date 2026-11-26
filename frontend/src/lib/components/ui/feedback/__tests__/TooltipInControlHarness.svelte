<!--
  Test harness for Tooltip.test.ts (85 BTN-0c, D16): a Tooltip that names a part of a larger control — a provider
  badge inside a route row, a ⚠ inside an option. The control is a <button> with its own click; the next button is
  where the keyboard goes after it. `insideControl` off reproduces the old wrapper (D16's defect) as the control case.
-->
<script lang="ts">
    import Tooltip from '../Tooltip.svelte';

    let {onpress, insideControl = true}: {onpress: (event: MouseEvent) => void; insideControl?: boolean} = $props();
</script>

<button type="button" data-testid="probe-control" onclick={onpress}>
    Route
    <Tooltip text="European Central Bank" {insideControl} testId="probe-part">
        <span data-testid="probe-badge">ECB</span>
    </Tooltip>
</button>
<button type="button" data-testid="probe-next">Next</button>
