<!-- Test harness (77 SEL-B): a DataTable whose pages are cut outside it, hosting the caller's pager in its dock. -->
<script lang="ts">
    import DataTable from '$lib/components/table/DataTable.svelte';
    import DataTablePagination from '$lib/components/table/DataTablePagination.svelte';
    import type {BulkAction, ColumnDef} from '$lib/components/table/types';

    interface Row {
        id: string;
    }

    interface Props {
        rows: Row[];
        bulkActions: BulkAction<Row>[];
    }

    let {rows, bulkActions}: Props = $props();
    const columns: ColumnDef<Row>[] = [{id: 'id', header: 'Id', type: 'text', cell: (r) => r.id, getValue: (r) => r.id}];
</script>

<DataTable data={rows} {columns} getRowId={(r) => r.id} storageKey="external-pager-fixture" enableActions={false} enablePagination={false} {bulkActions} selectionPanel={true}>
    {#snippet pager(docked: boolean)}
        <DataTablePagination pageIndex={0} pageSize={10} totalItems={40} pageSizeOptions={[10, 25]} onPageChange={() => {}} onPageSizeChange={() => {}} {docked} />
    {/snippet}
</DataTable>
