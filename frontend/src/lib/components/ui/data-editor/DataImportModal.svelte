<!--
  DataImportModal v2 — Modal for importing CSV data into the DataEditor.

  Features:
  - Compact drop zone for .csv/.txt files — drop overwrites editor content
  - Direction bar: CurrencySearchSelect (disabled) + swap ⇄ + info banner
  - CsvEditor preview with 2-column format (date;rate) + semantic header
  - Auto-detect direction from CSV header (>, < normalized)
  - Help ? toggle with collapsible format guide
  - Confirm discard if user has edited data and tries to close
  - Footer with valid row count + Cancel/Import

  Direction is driven by a SINGLE source of truth: the CsvEditor header.
  The ondirectiondetect callback updates the direction labels.
  Swap only modifies the header text → triggers ondirectiondetect → labels update.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import ModalBase from '$lib/components/ui/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/ConfirmModal.svelte';
    import CsvEditor from './CsvEditor.svelte';
    import type {ParsedRow} from './CsvEditor.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import {Upload, FileText, ArrowRight, HelpCircle} from 'lucide-svelte';
    import {t} from '$lib/i18n';

    // =========================================================================
    // Types (exported for external use)
    // =========================================================================

    export interface ImportDirection {
        from: string;
        to: string;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Whether the modal is open */
        open?: boolean;
        /** Display base currency (follows page direction, not canonical) */
        displayBase: string;
        /** Display quote currency (follows page direction) */
        displayQuote: string;
        /** Called when import is confirmed with valid rows + direction */
        onimport?: (rows: ParsedRow[], direction: ImportDirection) => void;
        /** Called when modal is closed/cancelled */
        onclose?: () => void;
    }

    let {
        open = $bindable(false),
        displayBase,
        displayQuote,
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
    let showHelp = $state(false);
    let showDiscardConfirm = $state(false);

    // Direction state — driven ONLY by ondirectiondetect (single source of truth)
    let directionFrom = $state('');
    let directionTo = $state('');

    // Guard to prevent re-initialization on csvValue changes
    let wasOpen = false;

    // Track the initial header-only text to detect user edits
    let initialCsvValue = '';

    // =========================================================================
    // Derived
    // =========================================================================

    let allowedCurrencies = $derived<[string, string]>([displayBase, displayQuote]);
    let displayFrom = $derived(directionFrom || displayBase);
    let displayTo = $derived(directionTo || displayQuote);

    /** True when user has typed/pasted/dropped something beyond the initial header */
    let isDirty = $derived.by(() => {
        const trimmed = csvValue.trim();
        if (!trimmed) return false;
        // Compare against initial header-only content
        if (trimmed === initialCsvValue.trim()) return false;
        // Also check if only the header line exists (no data rows)
        const lines = trimmed.split('\n').filter(l => l.trim());
        return lines.length > 1 || trimmed !== initialCsvValue.trim();
    });

    // =========================================================================
    // Initialize on open (one-shot, not reactive to csvValue)
    // =========================================================================

    $effect(() => {
        if (open && !wasOpen) {
            // First time opening — pre-populate header
            wasOpen = true;
            directionFrom = displayBase;
            directionTo = displayQuote;
            const initValue = `date;${displayBase}>${displayQuote}\n`;
            csvValue = initValue;
            initialCsvValue = initValue;
        }
        if (!open && wasOpen) {
            wasOpen = false;
        }
    });

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleValidChange(rows: ParsedRow[], errors: number, duplicates: boolean) {
        validRows = rows;
        errorCount = errors;
        hasDuplicates = duplicates;
    }

    /** Single source of truth: direction labels driven by CsvEditor header parsing */
    function handleDirectionDetect(from: string, to: string) {
        directionFrom = from;
        directionTo = to;
    }

    /** Request close — show confirm if dirty, otherwise close immediately */
    function requestClose() {
        if (isDirty) {
            showDiscardConfirm = true;
        } else {
            doClose();
        }
    }

    /** Actually close and reset all state */
    function doClose() {
        csvValue = '';
        initialCsvValue = '';
        validRows = [];
        errorCount = 0;
        hasDuplicates = false;
        fileName = '';
        directionFrom = '';
        directionTo = '';
        showHelp = false;
        showDiscardConfirm = false;
        open = false;
        onclose?.();
    }

    function handleConfirm() {
        if (validRows.length === 0) return;
        onimport?.(validRows, {from: directionFrom, to: directionTo});
        doClose();
    }

    /** Swap: ONLY modifies the header text. ondirectiondetect handles the rest. */
    function handleSwap() {
        const newFrom = directionTo || displayQuote;
        const newTo = directionFrom || displayBase;
        csvEditor?.setHeader(newFrom, newTo);
    }

    // ── File handling ──

    function handleFileContent(file: File) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target?.result as string;
            if (text) {
                csvValue = text;
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
        input.value = '';
    }
</script>

<ModalBase {open} maxWidth="3xl" onRequestClose={requestClose}>
    <!-- Header -->
    <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-slate-600">
        <div class="flex items-center gap-2">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">{$t('csvImport.title')}</h2>
            <button
                class="p-1 text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 rounded transition-colors"
                onclick={() => showHelp = !showHelp}
                title={$t('csvImport.helpTitle')}
                aria-label="Help"
            >
                <HelpCircle size={18} />
            </button>
        </div>
        <button
            class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded"
            onclick={requestClose}
            aria-label="Close"
        >✕</button>
    </div>

    <!-- Content -->
    <div class="p-4 space-y-3 max-h-[70vh] overflow-y-auto">
        <!-- Help section (collapsible) -->
        {#if showHelp}
            <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800
                        rounded-lg px-4 py-3 text-sm text-blue-700 dark:text-blue-300 space-y-2">
                <p class="font-semibold">{$t('csvImport.helpTitle')}</p>
                <p>{$t('csvImport.helpFormat')}</p>
                <pre class="bg-white/50 dark:bg-slate-800/50 rounded p-2 text-xs font-mono">date;{displayBase}>{displayQuote}
2024-01-15;1.0823
2024-01-16;1.0845</pre>
                <ul class="list-disc list-inside space-y-1 text-xs">
                    <li>{$t('csvImport.helpDateFormat')}</li>
                    <li>{$t('csvImport.helpRatePositive')}</li>
                    <li>{$t('csvImport.helpSemicolon')}</li>
                    <li>{$t('csvImport.helpDecimals')}</li>
                    <li>{$t('csvImport.helpDirection')}</li>
                </ul>
            </div>
        {/if}

        <!-- Drop zone (compact) -->
        <div
            class="relative border-2 border-dashed rounded-lg px-4 py-3 text-center transition-colors
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
            <div class="flex items-center justify-center gap-2">
                {#if fileName}
                    <FileText size={18} class="text-libre-green shrink-0" />
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{fileName}</span>
                    <span class="text-xs text-gray-400 dark:text-gray-500">— {$t('csvImport.dropReplace')}</span>
                {:else}
                    <Upload size={18} class="text-gray-400 dark:text-gray-500 shrink-0" />
                    <span class="text-sm text-gray-600 dark:text-gray-400">{$t('csvImport.dropFile')}</span>
                {/if}
            </div>
        </div>

        <!-- Direction: currency badges (readonly CurrencySearchSelect, centered) -->
        <div class="flex items-center justify-center gap-2">
            <div class="w-44">
                <CurrencySearchSelect
                    value={displayFrom}
                    disabled={true}
                />
            </div>
            <ArrowRight size={18} class="text-gray-400 dark:text-gray-500 shrink-0" />
            <div class="w-44">
                <CurrencySearchSelect
                    value={displayTo}
                    disabled={true}
                />
            </div>
        </div>

        <!-- Swap ⇄ + InfoBanner on the same row -->
        <div class="flex items-center gap-2">
            <button
                class="flex items-center justify-center w-9 h-9 rounded-lg bg-gray-100 dark:bg-slate-700 border border-gray-200 dark:border-slate-600
                       text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200
                       transition-colors text-base font-bold shrink-0"
                onclick={handleSwap}
                title={$t('common.swapDirection')}
                aria-label={$t('common.swapDirection')}
            >⇄</button>
            <div class="flex-1">
                <InfoBanner variant="info">
                    <span>{$t('csvImport.ratesInterpretedAs', {values: {from: displayFrom, to: displayTo}})}</span>
                </InfoBanner>
            </div>
        </div>

        <!-- CSV Editor preview -->
        <CsvEditor
            bind:this={csvEditor}
            bind:value={csvValue}
            {allowedCurrencies}
            onvalidchange={handleValidChange}
            ondirectiondetect={handleDirectionDetect}
            placeholder="Paste CSV data here or drop a file above..."
            minHeight="250px"
        />
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between p-4 border-t border-gray-200 dark:border-slate-600">
        <div class="text-sm text-gray-500 dark:text-gray-400">
            {#if validRows.length > 0}
                <span class="text-emerald-600 dark:text-emerald-400 font-medium">{$t('csvImport.validRows', {values: {count: validRows.length}})}</span>
                {#if errorCount > 0}
                    <span class="text-red-500 ml-2">• {errorCount} error{errorCount !== 1 ? 's' : ''}</span>
                {/if}
                {#if hasDuplicates}
                    <span class="text-amber-500 ml-2">• duplicates</span>
                {/if}
            {:else if csvValue.trim()}
                <span class="text-gray-400">{$t('csvImport.noValidRows')}</span>
            {/if}
        </div>
        <div class="flex gap-2">
            <button
                class="px-4 py-2 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors"
                onclick={requestClose}
            >{$t('common.cancel')}</button>
            <button
                class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                onclick={handleConfirm}
                disabled={validRows.length === 0}
            >{$t('csvImport.import', {values: {count: validRows.length}})}</button>
        </div>
    </div>
</ModalBase>

<!-- Confirm discard modal (stacked above) -->
<ConfirmModal
    open={showDiscardConfirm}
    title={$t('csvImport.discardTitle')}
    message={$t('csvImport.discardMessage')}
    warning={true}
    confirmText={$t('common.discardAndClose')}
    onConfirm={doClose}
    onCancel={() => showDiscardConfirm = false}
/>
