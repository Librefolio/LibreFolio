<!--
  FxDataImportModal — FX-specific wrapper around the generic DataImportModal.

  Adds the FX direction bar (currency badges + swap ⇄ + InfoBanner)
  via the headerSlot. The CSV format is 2-column: date;rate with the
  header label driven by the current direction (e.g., "AUD>EUR").

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import type {CsvColumnDef, ParsedRow} from '$lib/components/ui/data-editor/CsvEditor.svelte';
    import DataImportModal from '$lib/components/ui/data-editor/DataImportModal.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {CurrencySearchSelect} from '$lib/components/ui/select';
    import {ArrowRight} from 'lucide-svelte';
    import {t} from '$lib/i18n';

    // =========================================================================
    // Types
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
        /** Display base currency (follows page direction) */
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

    let directionFrom = $state('');
    let directionTo = $state('');
    let modalRef: DataImportModal;

    // Initialize direction on open
    $effect(() => {
        if (open) {
            if (!directionFrom) directionFrom = displayBase;
            if (!directionTo) directionTo = displayQuote;
        } else {
            directionFrom = '';
            directionTo = '';
        }
    });

    // =========================================================================
    // Derived
    // =========================================================================

    let displayFrom = $derived(directionFrom || displayBase);
    let displayTo = $derived(directionTo || displayQuote);

    /** CSV column: single rate column with direction in label */
    let fxColumns: CsvColumnDef[] = $derived([
        {
            key: 'rate',
            label: `${displayFrom}>${displayTo}`,
            type: 'number' as const,
            required: true,
        },
    ]);

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleSwap() {
        const oldFrom = directionFrom || displayBase;
        const oldTo = directionTo || displayQuote;
        directionFrom = oldTo;
        directionTo = oldFrom;

        // Rewrite CSV header: always output newFrom>newTo (using >)
        // Handles both > and < forms in the existing header
        if (modalRef) {
            const csv = modalRef.getCsvText();
            const lineArray = csv.split('\n');
            const headerIdx = lineArray.findIndex(l => l.trim() !== '');
            if (headerIdx >= 0) {
                const parts = lineArray[headerIdx].split(';');
                for (let i = 1; i < parts.length; i++) {
                    const trimmed = parts[i].trim();
                    // Match A>B or A<B
                    const gtMatch = trimmed.match(/^(.+)>(.+)$/);
                    const ltMatch = trimmed.match(/^(.+)<(.+)$/);
                    if (gtMatch || ltMatch) {
                        // Always rewrite as newFrom>newTo
                        parts[i] = `${directionFrom}>${directionTo}`;
                    }
                }
                lineArray[headerIdx] = parts.join(';');
            }
            modalRef.setCsvText(lineArray.join('\n'));
        }
    }

    function handleImport(rows: ParsedRow[]) {
        onimport?.(rows, {from: displayFrom, to: displayTo});
    }

    function handleClose() {
        onclose?.();
    }

    /**
     * Handle CSV text changes from user input or file load.
     * Detects direction syntax in the header:
     * - `A<B` means "from B to A" (e.g., `EUR<USD` → from=USD, to=EUR)
     * - `A>B` means "from A to B" (e.g., `EUR>USD` → from=EUR, to=USD)
     * Does NOT rewrite the CSV text — the user should see the original content
     * for verification. Only the swap ⇄ button rewrites with `>`.
     */
    function handleCsvTextChange(text: string) {
        const lineArray = text.split('\n');
        const headerIdx = lineArray.findIndex(l => l.trim() !== '');
        if (headerIdx < 0) return;

        const headerParts = lineArray[headerIdx].split(';');
        if (headerParts.length < 2) return;

        for (let i = 1; i < headerParts.length; i++) {
            const trimmed = headerParts[i].trim();
            // Detect < syntax: A<B means "from B to A"
            const ltMatch = trimmed.match(/^([A-Za-z]{3})\s*<\s*([A-Za-z]{3})$/);
            if (ltMatch) {
                const left = ltMatch[1].toUpperCase();
                const right = ltMatch[2].toUpperCase();
                directionFrom = right;
                directionTo = left;
                return;
            }
            // Detect > syntax: A>B means "from A to B"
            const gtMatch = trimmed.match(/^([A-Za-z]{3})\s*>\s*([A-Za-z]{3})$/);
            if (gtMatch) {
                const left = gtMatch[1].toUpperCase();
                const right = gtMatch[2].toUpperCase();
                directionFrom = left;
                directionTo = right;
                return;
            }
        }
    }
</script>

<DataImportModal
        bind:this={modalRef}
        bind:open
        columns={fxColumns}
        onclose={handleClose}
        onimport={handleImport}
        oncsvtextchange={handleCsvTextChange}
        title={$t('csvImport.title')}
>
    {#snippet headerSlot()}
        <!-- Direction: currency badges (readonly CurrencySearchSelect, centered) -->
        <div class="flex items-center justify-center gap-2">
            <div class="w-44">
                <CurrencySearchSelect
                        disabled={true}
                        value={displayFrom}
                />
            </div>
            <ArrowRight class="text-gray-400 dark:text-gray-500 shrink-0" size={18}/>
            <div class="w-44">
                <CurrencySearchSelect
                        disabled={true}
                        value={displayTo}
                />
            </div>
        </div>

        <!-- Swap ⇄ + InfoBanner on the same row -->
        <div class="flex items-center gap-2">
            <button
                    aria-label={$t('common.swapDirection')}
                    class="flex items-center justify-center w-9 h-9 rounded-lg bg-gray-100 dark:bg-slate-700 border border-gray-200 dark:border-slate-600
                       text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-slate-600 hover:text-gray-700 dark:hover:text-gray-200
                       transition-colors text-base font-bold shrink-0"
                    onclick={handleSwap}
                    title={$t('common.swapDirection')}
            >⇄
            </button>
            <div class="flex-1">
                <InfoBanner variant="info">
                    <span>{$t('csvImport.ratesInterpretedAs', {values: {from: displayFrom, to: displayTo}})}</span>
                </InfoBanner>
            </div>
        </div>
    {/snippet}

    {#snippet helpContent()}
        <p class="font-semibold">{$t('csvImport.helpTitle')}</p>
        <p>{$t('csvImport.helpFormat')}</p>
        <pre class="bg-white/50 dark:bg-slate-800/50 rounded p-2 text-xs font-mono">date;{displayFrom}>{displayTo}
2024-01-15;1.0823
2024-01-16;1.0845</pre>
        <ul class="list-disc list-inside space-y-1 text-xs">
            <li>{$t('csvImport.helpDateFormat')}</li>
            <li>{$t('csvImport.helpRatePositive')}</li>
            <li>{$t('csvImport.helpSemicolon')}</li>
            <li>{$t('csvImport.helpDecimals')}</li>
            <li>{$t('csvImport.helpDirection')}</li>
        </ul>
    {/snippet}
</DataImportModal>

