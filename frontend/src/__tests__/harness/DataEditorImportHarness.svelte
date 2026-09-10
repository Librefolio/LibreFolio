<script lang="ts">
    import DataEditor from '$lib/components/ui/data-editor/DataEditor.svelte';
    import type {ParsedRow} from '$lib/components/ui/data-editor/CsvEditor.svelte';
    import type {ColumnDef, DataRow} from '$lib/components/ui/data-editor/DataEditorTypes';

    interface Props {
        columns: ColumnDef[];
        rows: DataRow[];
        importedRows: ParsedRow[];
        onchange?: (dirtyRows: DataRow[]) => void;
    }

    let {columns, rows, importedRows, onchange}: Props = $props();
</script>

{#snippet importModal({open, onimport}: {open: boolean; setOpen: (value: boolean) => void; onimport: (rows: ParsedRow[]) => void})}
    {#if open}
        <button data-testid="data-editor-test-import" onclick={() => onimport(importedRows)}>Import fixture</button>
    {/if}
{/snippet}

<DataEditor {columns} bind:rows {onchange} {importModal} />
