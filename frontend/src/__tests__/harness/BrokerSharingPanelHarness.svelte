<!--
  BrokerSharingPanelHarness — test-only host for BrokerSharingPanel (Vitest + jsdom).

  Exists for one reason: `hasChanges` is a *bound* prop of the panel (the modal
  wrapper reads it to decide whether closing needs the unsaved-changes confirm),
  and a bare `render(Panel, {props})` cannot express `bind:`. The harness binds
  it and, when the panel fires `onCancel`, records the value the binding holds
  AT THAT MOMENT — the F3 regression was the panel calling `onCancel` one flush
  too early, so the modal still saw `hasChanges === true` right after a
  successful save and popped the confirm it had just made pointless.

  `onCancelProbe(hasChangesWhenCancelFired)` is the observation: the save path
  must call it with `false`. The mirror span below publishes the same bound
  value continuously, so a test can first prove the binding is LIVE (dirty draft
  → `data-value="true"`) before trusting the `false` the probe records — a
  probe that can only ever read false proves nothing.

  Lives under `src/__tests__/`, excluded from coverage: the harness must never
  inflate the numbers it exists to improve.
-->
<script lang="ts">
    import BrokerSharingPanel from '$lib/components/brokers/BrokerSharingPanel.svelte';

    export let brokerId: number;
    export let onChanged: (() => void) | undefined = undefined;
    /** Fired from the panel's onCancel with the bound hasChanges at call time. */
    export let onCancelProbe: ((hasChangesWhenCancelFired: boolean) => void) | undefined = undefined;

    let hasChanges = false;
</script>

<BrokerSharingPanel {brokerId} {onChanged} onCancel={() => onCancelProbe?.(hasChanges)} bind:hasChanges />

<!-- Continuous read-out of the bound value: the parent-side half of `bind:`. -->
<span data-testid="harness-has-changes" data-value={hasChanges}></span>
