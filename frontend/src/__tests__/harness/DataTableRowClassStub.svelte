<!--
  DataTableRowClassStub — test-only stand-in for DataTable that publishes what the host's `getRowClass` answers.

  The import review tints some rows (a date before 1900, a duplicate keeper) through `getRowClass`. The real table is
  covered by its own tests; this stub draws one marker per row, `data-testid="data-table-row-stub"`, whose
  `data-row-class` is the host's answer for that row and `data-row-index` the position in `data`, so a test compares the
  answers between rows without naming a CSS class. Exposes the ref methods a host calls as inert no-ops.

  Lives under `src/__tests__/`, excluded from coverage by `vitest.config.ts`.
-->
<script lang="ts">
    let {data = [], getRowClass, ...rest}: {data?: unknown[]; getRowClass?: (row: unknown) => string; [key: string]: unknown} = $props();
    void rest;

    export function navigateToRowId(): void {}
    export function getSortedRowIds(): string[] {
        return [];
    }
</script>

<div data-testid="data-table-stub" data-row-count={data.length}>
    {#each data as row, index}
        <div data-testid="data-table-row-stub" data-row-index={index} data-row-class={getRowClass?.(row) ?? ''}></div>
    {/each}
</div>
