<!--
  DataTableStub — test-only stand-in for DataTable (Vitest + jsdom).

  A host component that only HANDS ROWS to a table (the import wizard's review step draws one under its banners) does not need
  the table to prove what it shows around it, and the real one — columns, filters, resizing, persistence — is covered by its
  own tests. The stub takes any props, draws nothing but a marker publishing how many rows it was handed, and exposes the
  methods a host calls on its `bind:this` ref as inert no-ops, so a host that reaches for them does not throw.

  Lives under `src/__tests__/`, excluded from coverage by `vitest.config.ts`.
-->
<script lang="ts">
    let {data = [], ...rest}: {data?: unknown[]; [key: string]: unknown} = $props();
    void rest;

    export function navigateToRowId(): void {}
    export function getSortedRowIds(): string[] {
        return [];
    }
</script>

<div data-testid="data-table-stub" data-row-count={data.length}></div>
