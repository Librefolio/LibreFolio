<script lang="ts">
    import DataImportModal from '$lib/components/ui/data-editor/DataImportModal.svelte';
    import type {CsvColumnDef, CsvIdentityDef, ParsedRow} from '$lib/components/ui/data-editor/CsvEditor.svelte';

    interface Props {
        open?: boolean;
        title: string;
        resolveName: (raw: string) => string | null;
        onimport?: (distribution: Record<string, number>) => void;
        onclose?: () => void;
    }

    let {open = $bindable(false), title, resolveName, onimport, onclose}: Props = $props();

    const identity: CsvIdentityDef = {
        key: 'name',
        label: 'name',
        parse: (raw) => resolveName(raw),
    };

    const columns: CsvColumnDef[] = [
        {
            key: 'weight',
            label: 'weight',
            type: 'number',
            required: true,
            validate: (value) => (typeof value === 'number' && value >= 0 && value <= 100 ? null : 'Weight must be between 0 and 100'),
        },
    ];

    function validateRows(rows: ParsedRow[]): string | null {
        const total = rows.reduce((sum, row) => sum + Number(row.values.weight), 0);
        return Math.abs(total - 100) < 0.005 ? null : `Weights must total 100 (current total: ${total})`;
    }

    function handleImport(rows: ParsedRow[]) {
        const distribution: Record<string, number> = {};
        for (const row of rows) {
            if (row.kind !== 'identified') return;
            distribution[row.identity] = Number(row.values.weight) / 100;
        }
        onimport?.(distribution);
    }
</script>

<DataImportModal bind:open {columns} {identity} {title} strict={true} {validateRows} onimport={handleImport} {onclose} />
