<!--
  PriceDataImportModal — Asset price CSV import modal.

  Wraps DataImportModal with price-specific columns:
  - Required: currency, close
  - Optional: open, high, low, volume

  Header slot shows an InfoBanner explaining the format with a link to docs.
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
    // Column definitions for asset prices
    // =========================================================================

    const priceColumns: CsvColumnDef[] = [
        {key: 'currency', label: 'currency', type: 'string', required: true},
        {key: 'close', label: 'close', type: 'number', required: true},
        {key: 'open', label: 'open', type: 'number', required: false},
        {key: 'high', label: 'high', type: 'number', required: false},
        {key: 'low', label: 'low', type: 'number', required: false},
        {key: 'volume', label: 'volume', type: 'number', required: false},
    ];

    function openDocs() {
        const lang = localStorage.getItem('librefolio-locale') || 'en';
        const prefix = lang !== 'en' ? `${lang}/` : '';
        window.open(`/mkdocs/${prefix}user/assets/detail/data-editor/`, '_blank');
    }
</script>

<DataImportModal
        bind:open
        columns={priceColumns}
        {onclose}
        {onimport}
        title="📥 Import Prices CSV"
>
    {#snippet headerSlot()}
        <InfoBanner variant="info">
            <div class="flex items-start gap-2">
                <div class="flex-1 space-y-1">
                    <p><strong>Minimum:</strong> date;currency;close</p>
                    <p><strong>Extended:</strong> date;currency;close;open;high;low;volume</p>
                    <p class="text-[11px] opacity-80">Use <code class="bg-white/30 dark:bg-slate-700/50 px-1 rounded">;</code> to skip optional columns.</p>
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
        <p class="font-semibold">Price CSV Format</p>
        <p>Each row represents a daily price point. Only <code>date</code>, <code>currency</code>, and <code>close</code> are required.</p>
        <pre class="bg-white/50 dark:bg-slate-800/50 rounded p-2 text-xs font-mono">date;currency;close
2024-01-15;USD;145.50
2024-01-16;USD;146.10</pre>
        <p class="text-xs mt-1">Extended format with optional columns:</p>
        <pre class="bg-white/50 dark:bg-slate-800/50 rounded p-2 text-xs font-mono">date;currency;close;open;high;low;volume
2024-01-15;USD;145.50;144.00;146.20;143.80;1500000
2024-01-16;USD;146.10;;;;1200000</pre>
        <ul class="list-disc list-inside space-y-1 text-xs">
            <li>Date: YYYY-MM-DD format</li>
            <li>Currency: ISO 4217 code (e.g., USD, EUR)</li>
            <li>Use <code>;;</code> to skip optional columns</li>
            <li>Supports <code>.</code> and <code>,</code> as decimal separators</li>
        </ul>
    {/snippet}
</DataImportModal>

