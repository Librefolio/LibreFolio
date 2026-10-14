<!--
  AppLayoutGateHarness — test-only parent for the `(app)` layout (Vitest + jsdom).

  The layout renders the requested page through a legacy `<slot />`, and a slot is filled by a
  parent's markup, not by a prop a spec can pass to `render()`. This harness is that parent: it
  fills the slot with one stand-in for the requested page, so `layout.gate.test.ts` can assert
  whether the page itself was rendered, and not only which wrapper the route gate chose.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    import AppLayout from '../../routes/(app)/+layout.svelte';
</script>

<AppLayout>
    <div data-testid="app-layout-requested-page"></div>
</AppLayout>
