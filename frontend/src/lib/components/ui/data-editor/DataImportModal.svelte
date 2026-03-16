<!--
  DataImportModal — Modal for importing CSV data into the DataEditor.

  Features:
  - Drag & drop / file picker zone for .csv, .txt files
  - CsvEditor preview/edit of imported content
  - OK merges valid rows into the parent DataEditor
  - Cancel discards

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import CsvEditor from '$lib/components/fx/CsvEditor.svelte';
    import type {ParsedRow} from '$lib/components/fx/CsvEditor.svelte';
    import {Upload, FileText} from 'lucide-svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Whether the modal is open */
        open?: boolean;
        /** CSV header format */
        header?: string;
        /** Called when import is confirmed with valid rows */
        onimport?: (rows: ParsedRow[]) => void;
        /** Called when modal is closed/cancelled */
        onclose?: () => void;
    }

    let {
        open = $bindable(false),
        header = 'date;base;quote;base2quote',
        onimport,
        onclose,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let csvEditor: CsvEditor | undefined = $state(undefined);
    let csvValue = $state('');
    let validRows: ParsedRow[] = $state([]);
    let errorCount = $state(0);
    let hasDuplicates = $state(false);
    let isDragOver = $state(false);
    let fileName = $state('');

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleValidChange(rows: ParsedRow[], errors: number, duplicates: boolean) {
        validRows = rows;
        errorCount = errors;
        hasDuplicates = duplicates;
    }

    function handleClose() {
        csvValue = '';
        validRows = [];
        errorCount = 0;
        hasDuplicates = false;
        fileName = '';
        open = false;
        onclose?.();
    }

    function handleConfirm() {
        if (validRows.length === 0) return;
        onimport?.(validRows);
        handleClose();
    }

    // ── File handling ──

    function handleFileContent(file: File) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target?.result as string;
            if (text && csvEditor) {
                csvEditor.setText(text);
                fileName = file.name;
            }
        };
        reader.readAsText(file);
    }

    function handleDragOver(e: DragEvent) {
        e.preventDefault();
        isDragOver = true;
    }

    function handleDragLeave() {
        isDragOver = false;
    }

    function handleDrop(e: DragEvent) {
        e.preventDefault();
        isDragOver = false;
        const file = e.dataTransfer?.files?.[0];
        if (file && (file.name.endsWith('.csv') || file.name.endsWith('.txt'))) {
            handleFileContent(file);
        }
    }

    function handleFileSelect(e: Event) {
        const input = e.target as HTMLInputElement;
        const file = input.files?.[0];
        if (file) {
            handleFileContent(file);
        }
        // Reset input so the same file can be re-selected
        input.value = '';
    }
</script>

<ModalBase {open} maxWidth="3xl" onRequestClose={handleClose}>
    <!-- Header -->
    <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-600">
        <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">Import CSV Data</h2>
        <button
            class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded"
            onclick={handleClose}
            aria-label="Close"
        >✕</button>
    </div>

    <!-- Content -->
    <div class="p-4 space-y-4 max-h-[70vh] overflow-y-auto">
        <!-- Drop zone -->
        <div
            class="relative border-2 border-dashed rounded-lg p-6 text-center transition-colors
                {isDragOver
                    ? 'border-libre-green bg-emerald-50 dark:bg-emerald-900/20'
                    : 'border-gray-300 dark:border-slate-600 hover:border-gray-400 dark:hover:border-slate-500'}"
            role="button"
            tabindex="0"
            ondragover={handleDragOver}
            ondragleave={handleDragLeave}
            ondrop={handleDrop}
        >
            <input
                type="file"
                accept=".csv,.txt"
                class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                onchange={handleFileSelect}
            />
            <div class="flex flex-col items-center gap-2">
                {#if fileName}
                    <FileText size={24} class="text-libre-green" />
                    <p class="text-sm font-medium text-gray-700 dark:text-gray-300">{fileName}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-400">Drop another file to replace</p>
                {:else}
                    <Upload size={24} class="text-gray-400 dark:text-gray-500" />
                    <p class="text-sm text-gray-600 dark:text-gray-400">
                        Drop a <span class="font-mono">.csv</span> or <span class="font-mono">.txt</span> file here, or click to browse
                    </p>
                    <p class="text-xs text-gray-400 dark:text-gray-500">Format: {header}</p>
                {/if}
            </div>
        </div>

        <!-- CSV Editor preview -->
        <CsvEditor
            bind:this={csvEditor}
            bind:value={csvValue}
            {header}
            onvalidchange={handleValidChange}
            placeholder="Paste CSV data here or drop a file above..."
            minHeight="250px"
        />
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between p-4 border-t border-gray-200 dark:border-slate-600">
        <div class="text-sm text-gray-500 dark:text-gray-400">
            {#if validRows.length > 0}
                <span class="text-emerald-600 dark:text-emerald-400 font-medium">{validRows.length} valid row{validRows.length !== 1 ? 's' : ''}</span>
                {#if errorCount > 0}
                    <span class="text-red-500 ml-2">• {errorCount} error{errorCount !== 1 ? 's' : ''}</span>
                {/if}
                {#if hasDuplicates}
                    <span class="text-amber-500 ml-2">• duplicates</span>
                {/if}
            {:else if csvValue.trim()}
                <span class="text-gray-400">No valid rows found</span>
            {/if}
        </div>
        <div class="flex gap-2">
            <button
                class="px-4 py-2 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors"
                onclick={handleClose}
            >Cancel</button>
            <button
                class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                onclick={handleConfirm}
                disabled={validRows.length === 0}
            >Import ({validRows.length})</button>
        </div>
    </div>
</ModalBase>

