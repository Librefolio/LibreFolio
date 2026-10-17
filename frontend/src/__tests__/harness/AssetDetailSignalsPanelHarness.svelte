<!--
  AssetDetailSignalsPanelHarness — test-only host for AssetDetailSignalsPanel (Vitest + jsdom).

  The asset page keeps the panel's `open` and binds it: it reads it, and it opens the panel itself to configure a
  signal. The host binds it the same way, publishes the bound value (`probe-signals-open`) and flips it from outside
  (`probe-signals-host-toggle`), so a spec can follow the binding both ways. Its children are a real snippet, the
  stand-in for the page's signals section (`probe-signals-section`).

  Lives under `src/__tests__/`, which `vitest.config.ts` excludes from coverage.
-->
<script lang="ts">
    import AssetDetailSignalsPanel from '$lib/components/assets/detail/AssetDetailSignalsPanel.svelte';

    let open = $state(false);
</script>

<AssetDetailSignalsPanel bind:open>
    <div data-testid="probe-signals-section">signals</div>
</AssetDetailSignalsPanel>
<output data-testid="probe-signals-open">{open}</output>
<button type="button" data-testid="probe-signals-host-toggle" onclick={() => (open = !open)}>flip</button>
