<!--
  EventDataImportModal — Asset event CSV import modal.

  Wraps DataImportModal with event-specific columns:
  - Required: type, amount
  - Optional: currency, notes

  Header slot shows an InfoBanner with valid event types and a link to docs.
  Uses Svelte 5 runes.
-->
<script lang="ts">
    import type {CsvColumnDef, ParsedRow} from '$lib/components/ui/data-editor/CsvEditor.svelte';
    import DataImportModal from '$lib/components/ui/data-editor/DataImportModal.svelte';
    import InfoBanner from '$lib/components/ui/InfoBanner.svelte';
    import {BookOpen} from 'lucide-svelte';

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        open?: boolean;
        onimport?: (rows: ParsedRow[]) => void;
        onclose?: () => void;
    }

    let {
        open = $bindable(false),
        onimport,
        onclose,
    }: Props = $props();

    // =========================================================================
    // Column definitions for asset events
    // =========================================================================

    const eventColumns: CsvColumnDef[] = [
        {key: 'currency', label: 'currency', type: 'string', required: false},
        {key: 'type', label: 'type', type: 'string', required: true},
        {key: 'amount', label: 'amount', type: 'number', required: true},
        {key: 'notes', label: 'notes', type: 'string', required: false},
    ];

    function openDocs() {
        const lang = localStorage.getItem('librefolio-locale') || 'en';
        const prefix = lang !== 'en' ? `${lang}/` : '';
        window.open(`/mkdocs/${prefix}user/assets/detail/events/`, '_blank');
    }
</script>

<DataImportModal
        bind:open
        columns={eventColumns}
        {onclose}
        {onimport}
        title="📥 Import Events CSV"
>
    {#snippet headerSlot()}
        <InfoBanner variant="info">
            <div class="flex items-start gap-2">
                <div class="flex-1 space-y-1">
                    <p><strong>Format:</strong> date;currency;type;amount;notes</p>
                    <p class="text-[11px] opacity-80">
                        Types: <code class="bg-white/30 dark:bg-slate-700/50 px-1 rounded">DIVIDEND</code>
                        <code class="bg-white/30 dark:bg-slate-700/50 px-1 rounded">INTEREST</code>
                        <code class="bg-white/30 dark:bg-slate-700/50 px-1 rounded">SPLIT</code>
                        <code class="bg-white/30 dark:bg-slate-700/50 px-1 rounded">PRICE_ADJUSTMENT</code>
                        <code class="bg-white/30 dark:bg-slate-700/50 px-1 rounded">MATURITY_SETTLEMENT</code>
                    </p>
                </div>
                <button
                        class="p-1 text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 shrink-0"
                        onclick={openDocs}
                        title="Open documentation"
                        type="button"
                >
                    <BookOpen size={16}/>
                </button>
            </div>
        </InfoBanner>
    {/snippet}

    {#snippet helpContent()}
        <p class="font-semibold">Event CSV Format</p>
        <p>Each row represents an asset event. <code>type</code> and <code>amount</code> are required.</p>
        <pre class="bg-white/50 dark:bg-slate-800/50 rounded p-2 text-xs font-mono">date;currency;type;amount;notes
2024-03-15;USD;DIVIDEND;1.25;Q1 payout
2024-06-01;;SPLIT;2;2:1 split
2024-09-15;USD;DIVIDEND;1.30;</pre>
        <ul class="list-disc list-inside space-y-1 text-xs">
            <li>Date: YYYY-MM-DD format</li>
            <li>Type: DIVIDEND, INTEREST, SPLIT, PRICE_ADJUSTMENT, MATURITY_SETTLEMENT</li>
            <li>Amount: numeric value (e.g., dividend per share, split ratio)</li>
            <li>Currency and notes are optional — use <code>;;</code> to skip</li>
        </ul>
    {/snippet}
</DataImportModal>

