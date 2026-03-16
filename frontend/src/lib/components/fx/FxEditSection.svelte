<!--
  FxEditSection — Edit mode panel for manual rate entry.
  CsvEditor + "+" button + Save/Cancel + CSV format link.
  NOTE: Will be replaced by FxDataEditorSection in Step 4.
-->
<script lang="ts">
    import {Plus, Save, X, Info} from 'lucide-svelte';
    import CsvEditor from './CsvEditor.svelte';
    import type {ParsedRow} from './CsvEditor.svelte';

    interface Props {
        base: string;
        quote: string;
        saving?: boolean;
        onsave?: (rows: ParsedRow[]) => void;
        oncancel?: () => void;
    }

    let {
        base,
        quote,
        saving = false,
        onsave,
        oncancel,
    }: Props = $props();

    let csvValue = $state(`date;base;quote;base2quote`);
    let parsedRows: ParsedRow[] = $state([]);
    let csvEditor: CsvEditor | undefined = $state(undefined);
    let hasEdits = $state(false);
    let showAddForm = $state(false);
    let newDate = $state(new Date().toISOString().slice(0, 10));
    let newRate = $state('');

    function handleCsvChange(validRows: ParsedRow[], _errorCount: number, _hasDuplicates: boolean) {
        parsedRows = validRows;
        hasEdits = parsedRows.length > 0;
    }

    function handleAddPoint() {
        const rateNum = parseFloat(newRate);
        if (!newDate || isNaN(rateNum) || rateNum <= 0) return;
        csvEditor?.appendRow(newDate, base, quote, rateNum);
        showAddForm = false;
        newRate = '';
    }

    function handleSave() {
        if (parsedRows.length === 0) return;
        onsave?.(parsedRows);
    }

    function handleCancel() {
        csvValue = `date;base;quote;base2quote`;
        parsedRows = [];
        hasEdits = false;
        oncancel?.();
    }

    export function onPointEdit(date: string, value: number) {
        csvEditor?.appendRow(date, base, quote, value);
    }

    export function scrollToLine(lineNumber: number) {
        csvEditor?.scrollToLine(lineNumber);
    }
</script>

<div class="bg-amber-50 dark:bg-amber-900/10 rounded-xl border border-amber-200 dark:border-amber-800 p-4 space-y-4">
    <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-amber-800 dark:text-amber-300">Edit Mode — Manual Rate Entry</h3>
        <a href="/docs/user/fx-csv-format" target="_blank" class="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-600 hover:underline">
            <Info size={12} /> CSV Format Guide
        </a>
    </div>

    <p class="text-xs text-amber-700 dark:text-amber-400">
        Click on chart points to edit, paste CSV data below, or use the + button. Changes are saved only when you click "Save All".
    </p>

    <CsvEditor bind:this={csvEditor} bind:value={csvValue} onvalidchange={handleCsvChange} minHeight="180px" />

    {#if showAddForm}
        <div class="flex items-end gap-2 p-3 bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-600">
            <div>
                <!-- svelte-ignore a11y_label_has_associated_control -->
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Date
                    <input type="date" bind:value={newDate} class="mt-1 block px-2 py-1 text-sm border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200" />
                </label>
            </div>
            <div class="flex-1">
                <!-- svelte-ignore a11y_label_has_associated_control -->
                <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Rate ({base} → {quote})
                    <input type="number" bind:value={newRate} step="0.0001" min="0" placeholder="1.0823" class="mt-1 block w-full px-2 py-1 text-sm border border-gray-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-200" />
                </label>
            </div>
            <button class="px-3 py-1.5 text-sm bg-libre-green text-white rounded hover:bg-libre-green/90 disabled:opacity-50" onclick={handleAddPoint} disabled={!newDate || !newRate}>Add</button>
            <button class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-slate-600 rounded hover:bg-gray-300" onclick={() => showAddForm = false}>✕</button>
        </div>
    {/if}

    <div class="flex items-center gap-2">
        {#if !showAddForm}
            <button class="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 text-gray-600 dark:text-gray-300 transition-colors" onclick={() => showAddForm = true}>
                <Plus size={14} /> Add Point
            </button>
        {/if}
        {#if hasEdits}
            <button class="flex items-center gap-1.5 px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50" onclick={handleSave} disabled={saving || parsedRows.length === 0}>
                <Save size={15} /> {saving ? 'Saving...' : `Save All (${parsedRows.length})`}
            </button>
            <button class="flex items-center gap-1.5 px-4 py-2 text-sm bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/30" onclick={handleCancel}>
                <X size={15} /> Cancel
            </button>
        {/if}
    </div>
</div>
