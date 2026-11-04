<!--
  InstanceBlockedPageStub — test-only stand-in for InstanceBlockedPage (Vitest + jsdom).

  `layout.gate.test.ts` asks which branch the `(app)` layout chose, not what the block page says: that is
  `InstanceBlockedPage.test.ts`. The real page would also read the block from the API at mount. The stub renders one
  element with a testid of its own, and that element calls the `onlogout` the layout passed, so the spec can check the
  wiring to the layout's logout.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    let {onlogout}: {onlogout: () => void} = $props();
</script>

<button type="button" aria-label="instance-blocked-page-stub" data-testid="instance-blocked-page-stub" onclick={onlogout}></button>
