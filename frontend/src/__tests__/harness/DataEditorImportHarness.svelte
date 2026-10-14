<script lang="ts">
    import DataEditor from '$lib/components/ui/data-editor/DataEditor.svelte';
    import type {ParsedRow} from '$lib/components/ui/data-editor/CsvEditor.svelte';
    import type {ColumnDef, DataRow} from '$lib/components/ui/data-editor/DataEditorTypes';

    interface Props {
        columns: ColumnDef[];
        rows: DataRow[];
        /** One batch, imported by `data-editor-test-import`. */
        importedRows?: ParsedRow[];
        /** Further batches, imported one at a time by `data-editor-test-import-batch-{n}` (1-based): successive imports into one editor. */
        importBatches?: ParsedRow[][];
        /** Forwarded untouched; `undefined` leaves DataEditor's own default in charge. */
        importMatchKeys?: string[];
        onchange?: (dirtyRows: DataRow[]) => void;
    }

    let {columns, rows, importedRows = [], importBatches = [], importMatchKeys, onchange}: Props = $props();
</script>

{#snippet importModal({open, onimport}: {open: boolean; setOpen: (value: boolean) => void; onimport: (rows: ParsedRow[]) => void})}
    {#if open}
        <button data-testid="data-editor-test-import" onclick={() => onimport(importedRows)}>Import fixture</button>
        {#each importBatches as batch, i (i)}
            <button data-testid="data-editor-test-import-batch-{i + 1}" onclick={() => onimport(batch)}>Import batch {i + 1}</button>
        {/each}
    {/if}
{/snippet}

<DataEditor {columns} bind:rows {onchange} {importModal} {importMatchKeys} />
