<!--
  SettingsTabProbe — test-only tab body for `routes/(app)/settings/page.tabs.test.ts` (Vitest + jsdom).

  The Settings page renders the body of its active tab from the tab registry (`settingsTabs.ts`), with
  the tab's `props(ctx)` spread on it. The page test hands the registry synthetic tabs, and each of
  their bodies is this probe, told which tab it stands for:
    - `probe` names the synthetic tab;
    - `received` is the props object the page rendered the body with, read again on every update, so a
      prop the page changes later (`canEdit` once the user becomes an administrator) shows up here too.
  It draws one empty element and nothing else; `data-received` is what the page passed, as JSON, minus
  Svelte's own `$$` keys.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    interface Props {
        /** The synthetic tab this body stands for. */
        probe: string;
        /** The props object the page rendered the body with. */
        received: Record<string, unknown>;
    }

    let {probe, received}: Props = $props();

    const shown = $derived(JSON.stringify(Object.fromEntries(Object.entries(received).filter(([key]) => !key.startsWith('$$')))));
</script>

<div data-probe={probe} data-received={shown} data-testid="settings-tab-probe"></div>
