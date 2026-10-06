<!--
  R11.8: the shared column button above a planner table, on the right: it moves and hides the
  columns, and the choices are saved per user with the table's `storageKey`. Tables that share a
  key (the orders, one per Broker) are passed as `others` so they change together. The shared
  button keeps its own test id; this wrapper carries the planner's. The label gives the button a
  name, for the eye and for screen readers.
-->
<script lang="ts">
    import type DataTable from '$lib/components/table/DataTable.svelte';
    import ColumnVisibilityToggle from '$lib/components/table/ColumnVisibilityToggle.svelte';

    interface Props {
        /** Any row type: the button reads only the columns. */
        table: DataTable<any> | undefined;
        others?: (DataTable<any> | undefined)[];
        testid: string;
    }

    let {table, others = [], testid}: Props = $props();
</script>

<div class="ml-auto flex shrink-0 justify-end" data-testid={testid}>
    <ColumnVisibilityToggle tableRef={table} additionalTableRefs={others} showLabel />
</div>
