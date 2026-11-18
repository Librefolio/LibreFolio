<!--
  PageSyncModalStub — test-only stand-in for PageSyncModal (Vitest + jsdom).

  `RiskPanelHeader.test.ts` asks what the panel does once the sync modal reports back, not what the modal does: that is
  the modal's own business, and the real one fetches providers and rates when it opens. The stub keeps the props the
  panels pass that matter here — `open` (bindable), `onsynced`, `onclose` — publishes `data-open`, and has two buttons,
  the modal's two ways of completing: a sync that wrote something (`accepted: true`) and one that did not.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    interface Props {
        open?: boolean;
        onsynced: (detail: {accepted: boolean}) => void;
        onclose: () => void;
    }

    let {open = $bindable(false), onsynced, onclose}: Props = $props();
</script>

<div data-testid="page-sync-modal-stub" data-open={open ? 'true' : 'false'}>
    <button type="button" data-testid="page-sync-modal-stub-accepted" onclick={() => onsynced({accepted: true})}>accepted</button>
    <button type="button" data-testid="page-sync-modal-stub-unchanged" onclick={() => onsynced({accepted: false})}>unchanged</button>
    <button type="button" data-testid="page-sync-modal-stub-close" onclick={onclose}>close</button>
</div>
