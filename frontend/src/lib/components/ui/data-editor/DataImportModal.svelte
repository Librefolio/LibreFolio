<!--
  DataImportModal — Generic CSV import modal with configurable columns and optional header slot.

  Features:
  - Compact drop zone for .csv/.txt files
  - CsvEditor with configurable N-column format
  - Optional headerSlot for domain-specific content (e.g., FX direction bar)
  - Help ? toggle with collapsible content (helpContent snippet)
  - Confirm discard if user has edited data and tries to close
  - Footer with valid row count + Cancel/Import

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import type {ParsedRow, CsvColumnDef, CsvIdentityDef} from './CsvEditor.svelte';
    import CsvEditor from './CsvEditor.svelte';
    import {FileText, HelpCircle, Upload} from 'lucide-svelte';
    import {t} from '$lib/i18n';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Whether the modal is open */
        open?: boolean;
        /** Modal title */
        title?: string;
        /** Column definitions for CSV parsing */
        columns: CsvColumnDef[];
        /** Optional non-date primary identity column. */
        identity?: CsvIdentityDef;
        /** Require every non-empty row to be valid and unique. */
        strict?: boolean;
        /** Optional cross-row domain validation. */
        validateRows?: (rows: ParsedRow[]) => string | null;
        /** Optional snippet rendered between drop zone and CsvEditor */
        headerSlot?: Snippet;
        /** Optional action rendered beside the modal title/help control */
        headerActions?: Snippet;
        /** Optional snippet for help section content */
        helpContent?: Snippet;
        /** Called when import is confirmed with valid rows */
        onimport?: (rows: ParsedRow[]) => void;
        /** Called when modal is closed/cancelled */
        onclose?: () => void;
        /** Called when CSV text changes (user input, file load) */
        oncsvtextchange?: (text: string) => void;
    }

    let {open = $bindable(false), title = 'Import CSV Data', columns, identity, strict = false, validateRows, headerSlot, headerActions, helpContent, onimport, onclose, oncsvtextchange}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let csvValue = $state('');
    let validRows: ParsedRow[] = $state([]);
    let errorCount = $state(0);
    let hasDuplicates = $state(false);
    let isDragOver = $state(false);
    let fileName = $state('');
    let showHelp = $state(false);
    let showDiscardConfirm = $state(false);

    // Guard to prevent re-initialization on csvValue changes
    let wasOpen = false;
    let initialCsvValue = '';

    // =========================================================================
    // Derived
    // =========================================================================

    /** Expected header for pre-population */
    let expectedHeader = $derived((identity?.label ?? 'date') + ';' + columns.map((c) => c.label).join(';'));
    let domainError = $derived(validRows.length > 0 ? (validateRows?.(validRows) ?? null) : null);
    let canImport = $derived(validRows.length > 0 && !domainError && (!strict || (errorCount === 0 && !hasDuplicates)));

    /** True when user has typed/pasted/dropped something beyond the initial header */
    let isDirty = $derived.by(() => {
        const trimmed = csvValue.trim();
        if (!trimmed) return false;
        if (trimmed === initialCsvValue.trim()) return false;
        const lines = trimmed.split('\n').filter((l) => l.trim());
        return lines.length > 1 || trimmed !== initialCsvValue.trim();
    });

    // =========================================================================
    // Initialize on open
    // =========================================================================

    $effect(() => {
        if (open && !wasOpen) {
            wasOpen = true;
            const initValue = expectedHeader + '\n';
            csvValue = initValue;
            initialCsvValue = initValue;
        }
        if (!open && wasOpen) {
            wasOpen = false;
        }
    });

    // =========================================================================
    // Public API — parent can read/write CSV text
    // =========================================================================

    /** Get the current CSV text content */
    export function getCsvText(): string {
        return csvValue;
    }

    /** Set the CSV text content. Auto-updates initialCsvValue if not dirty, or if updateInitial is explicitly true. */
    export function setCsvText(text: string, updateInitial?: boolean) {
        const shouldUpdateInitial = updateInitial ?? !isDirty;
        csvValue = text;
        if (shouldUpdateInitial) {
            initialCsvValue = text;
        }
    }

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleValidChange(rows: ParsedRow[], errors: number, duplicates: boolean) {
        validRows = rows;
        errorCount = errors;
        hasDuplicates = duplicates;
    }

    function requestClose() {
        if (isDirty) {
            showDiscardConfirm = true;
        } else {
            doClose();
        }
    }

    function doClose() {
        csvValue = '';
        initialCsvValue = '';
        validRows = [];
        errorCount = 0;
        hasDuplicates = false;
        fileName = '';
        showHelp = false;
        showDiscardConfirm = false;
        open = false;
        onclose?.();
    }

    function handleConfirm() {
        if (!canImport) return;
        onimport?.(validRows);
        doClose();
    }

    // ── File handling ──

    function handleFileContent(file: File) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target?.result as string;
            if (text) {
                csvValue = text;
                fileName = file.name;
                oncsvtextchange?.(text);
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

<ModalBase maxWidth="3xl" onRequestClose={requestClose} {open} testId="data-import-modal">
    <!-- Header -->
    <div class="flex items-center justify-between p-4 border-b border-lf-subtle" data-testid="data-import-modal-header">
        <div class="flex items-center gap-2">
            <h2 class="text-lg font-semibold text-lf-primary">{title}</h2>
            {#if helpContent}
                <button aria-label={$t('csvImport.helpTitle')} data-testid="data-import-modal-help" class="p-1 text-lf-muted hover:text-lf-info rounded transition-colors" onclick={() => (showHelp = !showHelp)} title={$t('csvImport.helpTitle')}>
                    <HelpCircle size={18} />
                </button>
            {/if}
        </div>
        <div class="flex items-center gap-1">
            {#if headerActions}
                {@render headerActions()}
            {/if}
            <button aria-label={$t('common.close')} data-testid="data-import-modal-close" class="p-1 text-lf-muted hover:text-lf-secondary rounded" onclick={requestClose}>✕ </button>
        </div>
    </div>

    <!-- Content -->
    <div class="p-4 space-y-3 max-h-[70vh] overflow-y-auto">
        <!-- Help section (collapsible) -->
        {#if showHelp && helpContent}
            <div
                class="bg-lf-info-soft border border-lf-info-line
                        rounded-lg px-4 py-3 text-sm text-lf-info-on-soft space-y-2"
            >
                {@render helpContent()}
            </div>
        {/if}

        <!-- Drop zone (compact) -->
        <div
            class="relative border-2 border-dashed rounded-lg px-4 py-3 text-center transition-colors
                {isDragOver ? 'border-lf-focus bg-lf-selected' : 'border-lf-input hover:border-lf-input-hover'}"
            ondragleave={handleDragLeave}
            ondragover={handleDragOver}
            ondrop={handleDrop}
            role="button"
            tabindex="0"
        >
            <input accept=".csv,.txt" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" onchange={handleFileSelect} type="file" />
            <div class="flex items-center justify-center gap-2">
                {#if fileName}
                    <FileText size={18} class="text-lf-link shrink-0" />
                    <span class="text-sm font-medium text-lf-secondary">{fileName}</span>
                    <span class="text-xs text-lf-muted">— {$t('csvImport.dropReplace')}</span>
                {:else}
                    <Upload size={18} class="text-lf-muted shrink-0" />
                    <span class="text-sm text-lf-secondary">{$t('csvImport.dropFile')}</span>
                {/if}
            </div>
        </div>

        <!-- Optional header slot (e.g., FX direction bar, info banners) -->
        {#if headerSlot}
            {@render headerSlot()}
        {/if}

        <!-- CSV Editor -->
        <CsvEditor {columns} {identity} bind:value={csvValue} minHeight="250px" onvalidchange={handleValidChange} oninput={oncsvtextchange} placeholder={$t('csvImport.placeholder')} />
        {#if domainError}
            <p class="text-sm text-lf-danger" data-testid="csv-domain-error">{domainError}</p>
        {/if}
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between p-4 border-t border-lf-subtle">
        <div class="text-sm text-lf-muted">
            {#if validRows.length > 0}
                <span class="text-lf-success font-medium">{$t('csvImport.validRows', {values: {n: validRows.length}})}</span>
                {#if errorCount > 0}
                    <span class="text-lf-danger ml-2">• {errorCount} error{errorCount !== 1 ? 's' : ''}</span>
                {/if}
                {#if hasDuplicates}
                    <span class="text-lf-warning ml-2">• duplicates</span>
                {/if}
            {:else if csvValue.trim()}
                <span class="text-lf-muted">{$t('csvImport.noValidRows')}</span>
            {/if}
        </div>
        <div class="flex gap-2">
            <button class="px-4 py-2 text-sm bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-colors" data-testid="data-import-cancel" onclick={requestClose}>{$t('common.cancel')}</button>
            <button
                class="px-4 py-2 text-sm bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-domain-error={domainError ? 'true' : 'false'}
                data-error-count={errorCount}
                data-has-duplicates={hasDuplicates ? 'true' : 'false'}
                data-testid="data-import-confirm"
                data-valid-rows={validRows.length}
                disabled={!canImport}
                onclick={handleConfirm}
            >
                {$t('csvImport.import', {values: {n: validRows.length}})}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Confirm discard modal (stacked above) -->
<ConfirmModal confirmText={$t('common.discardAndClose')} message={$t('csvImport.discardMessage')} onCancel={() => (showDiscardConfirm = false)} onConfirm={doClose} open={showDiscardConfirm} testId="data-import-discard-confirm" title={$t('common.discardImport')} warning={true} />
