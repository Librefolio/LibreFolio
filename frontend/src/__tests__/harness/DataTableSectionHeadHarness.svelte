<!-- Test harness (77 SEL-D): a table inside a section, whose bar sits in the section's head (title, bar, the section's own button). -->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import DataTable from '$lib/components/table/DataTable.svelte';
    import type {BulkAction, ColumnDef} from '$lib/components/table/types';

    interface Row {
        id: string;
    }

    interface Props {
        rows: Row[];
        bulkActions: BulkAction<Row>[];
        selectionPanel?: boolean;
        enableSelection?: boolean;
        enablePagination?: boolean;
        selectionHint?: string;
    }

    let {rows, bulkActions, selectionPanel = true, enableSelection = true, enablePagination = false, selectionHint}: Props = $props();
    const columns: ColumnDef<Row>[] = [{id: 'id', header: 'Id', type: 'text', cell: (r) => r.id, getValue: (r) => r.id}];
</script>

{#snippet head(bar: Snippet)}
    <div data-testid="section-head">
        <span data-testid="section-title">Identifiers</span>
        {@render bar()}
        <button type="button" data-testid="section-add">Add</button>
    </div>
{/snippet}

<DataTable data={rows} {columns} getRowId={(r) => r.id} storageKey="section-head-fixture-{Math.random()}" enableActions={false} {enableSelection} {enablePagination} defaultPageSize={5} pageSizeOptions={[5, 10]} {bulkActions} {selectionPanel} {selectionHint} selectionHead={head} />
