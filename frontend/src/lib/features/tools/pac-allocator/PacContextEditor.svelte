<script lang="ts">
    import {_} from '$lib/i18n';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import type {SelectOption} from '$lib/components/ui/select';
    import {AlertTriangle, Copy, Database, Trash2} from 'lucide-svelte';
    import type {PacEditorRow} from './editorTypes';

    interface Props {
        row: PacEditorRow;
        index: number;
        disabled?: boolean;
        onduplicate: () => void;
        onremove: () => void;
        onchange: () => void;
    }

    let {row = $bindable(), index, disabled = false, onduplicate, onremove, onchange}: Props = $props();

    let gridModeOptions = $derived<SelectOption[]>([
        {value: '', label: $_('tools.pacAllocator.selectGrid')},
        {value: 'whole', label: $_('tools.pacAllocator.rows.whole')},
        {value: 'fractional', label: $_('tools.pacAllocator.rows.fractional')},
    ]);

    let quoteBasisOptions = $derived.by<SelectOption[]>(() => {
        const values = new Set(['1', '100']);
        if (row.value.quote.quote_base_quantity !== null) values.add(String(row.value.quote.quote_base_quantity));
        return [...values].sort((left, right) => Number(left) - Number(right)).map((value) => ({value, label: `${$_('tools.pacAllocator.perUnits')} ${value}`}));
    });

    function setPrice(value: string): void {
        row.value.quote.raw_price = value || null;
        onchange();
    }

    function setPriceDate(value: string): void {
        row.value.quote.reference_date = value || null;
        onchange();
    }

    function setQuoteBasis(value: string): void {
        row.value.quote.quote_base_quantity = value ? Number(value) : null;
        onchange();
    }

    function setGridMode(value: string): void {
        row.value.buy_grid.mode = value === 'whole' || value === 'fractional' ? value : null;
        onchange();
    }
</script>

<article class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900/50" data-testid="pac-row" data-row-index={index}>
    <div class="flex items-start gap-3 border-b border-gray-100 bg-gray-50/80 px-3 py-3 dark:border-gray-800 dark:bg-gray-900">
        <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
                <h4 class="truncate text-sm font-semibold text-gray-900 dark:text-white">
                    {row.value.name || row.value.instrument_key || `${$_('common.asset')} ${index + 1}`}
                </h4>
                {#if row.source}
                    <span class="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-medium text-blue-800 dark:bg-blue-900/40 dark:text-blue-200">
                        <Database size={11} />
                        {row.source.brokerName}
                    </span>
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                        {$_('tools.pacAllocator.fullCustody')}
                    </span>
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                        {row.source.ownershipSharePercent}% {$_('tools.pacAllocator.personalShare')}
                    </span>
                {:else}
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">{$_('tools.pacAllocator.manual')}</span>
                {/if}
                {#if row.stale}
                    <span class="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
                        <AlertTriangle size={11} />
                        {$_('tools.pacAllocator.staleLabel')}
                    </span>
                {/if}
            </div>
            {#if row.source}
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {$_('tools.pacAllocator.snapshotAt')}
                    {row.source.sourceAsOfDate}
                    {#if row.source.quoteReferenceDate}
                        · {$_('tools.pacAllocator.priceAt')} {row.source.quoteReferenceDate}{/if}
                    {#if row.source.quoteSource}
                        · {row.source.quoteSource}{/if}
                    · {$_('tools.pacAllocator.editableCopy')}
                </p>
            {/if}
        </div>
        <div class="flex shrink-0 items-center gap-1">
            <button class="btn btn-ghost px-2" type="button" onclick={onduplicate} {disabled} data-testid={`pac-duplicate-asset-${index}`} aria-label={$_('tools.pacAllocator.duplicate')}>
                <Copy size={15} />
                <span class="hidden sm:inline">{$_('tools.pacAllocator.duplicate')}</span>
            </button>
            <button class="btn btn-danger px-2" type="button" onclick={onremove} {disabled} data-testid={`pac-remove-asset-${index}`} aria-label={$_('common.remove')}>
                <Trash2 size={15} />
                <span class="hidden sm:inline">{$_('common.remove')}</span>
            </button>
        </div>
    </div>

    <div class="space-y-4 p-3">
        <div>
            <p class="section-kicker">{$_('tools.pacAllocator.identityAndCustody')}</p>
            <div class="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <label class="field-label">
                    <span>{$_('tools.pacAllocator.instrumentId')}</span>
                    <input class="input-field" bind:value={row.value.instrument_key} required {disabled} oninput={onchange} data-testid={`pac-instrument-id-${index}`} />
                </label>
                <label class="field-label">
                    <span>{$_('common.name')}</span>
                    <input
                        class="input-field"
                        value={row.value.name ?? ''}
                        required
                        {disabled}
                        oninput={(event) => {
                            row.value.name = event.currentTarget.value;
                            onchange();
                        }}
                        data-testid={`pac-display-name-${index}`}
                    />
                </label>
                <label class="field-label">
                    <span>{$_('tools.pacAllocator.custodyContext')}</span>
                    <input class="input-field" bind:value={row.value.row_key} required {disabled} oninput={onchange} data-testid={`pac-custody-context-${index}`} />
                </label>
                <label class="field-label">
                    <span>{$_('tools.pacAllocator.rows.initialQuantity')}</span>
                    <ExactDecimalInput
                        value={row.value.initial_quantity ?? ''}
                        step="0.000001"
                        maxIntegerDigits={12}
                        maxFractionDigits={12}
                        ariaLabel={$_('tools.pacAllocator.rows.initialQuantity')}
                        testid={`pac-initial-quantity-${index}`}
                        {disabled}
                        onchange={(value) => {
                            row.value.initial_quantity = value;
                            onchange();
                        }}
                    />
                </label>
            </div>
        </div>

        <div>
            <p class="section-kicker">{$_('tools.pacAllocator.marketFacts')}</p>
            <div class="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <label class="field-label">
                    <span>{$_('common.currency')}</span>
                    <CurrencySearchSelect
                        value={row.value.quote.currency ?? ''}
                        compact
                        testId={`pac-asset-currency-${index}`}
                        {disabled}
                        onchange={(value) => {
                            row.value.quote.currency = value;
                            onchange();
                        }}
                    />
                </label>
                <label class="field-label">
                    <span>{$_('tools.pacAllocator.rows.price')}</span>
                    <ExactDecimalInput value={row.value.quote.raw_price ?? ''} step="0.01" maxIntegerDigits={12} maxFractionDigits={12} placeholder={$_('common.optional')} ariaLabel={$_('tools.pacAllocator.rows.price')} testid={`pac-raw-price-${index}`} {disabled} onchange={setPrice} />
                </label>
                <label class="field-label">
                    <span>{$_('tools.pacAllocator.rows.quoteBasis')}</span>
                    <SimpleSelect
                        value={row.value.quote.quote_base_quantity === null ? '' : String(row.value.quote.quote_base_quantity)}
                        options={quoteBasisOptions}
                        placeholder={$_('tools.pacAllocator.selectPriceBasis')}
                        ariaLabel={$_('tools.pacAllocator.rows.quoteBasis')}
                        testId={`pac-price-basis-${index}`}
                        dropdownPosition="auto"
                        matchTriggerWidth
                        {disabled}
                        onchange={setQuoteBasis}
                    />
                </label>
                <label class="field-label">
                    <span>{$_('tools.pacAllocator.rows.quoteDate')}</span>
                    <SingleDatePicker value={row.value.quote.reference_date ?? ''} label={$_('tools.pacAllocator.rows.quoteDate')} inputStyle clearable {disabled} onchange={setPriceDate} testid={`pac-price-date-${index}`} />
                </label>
            </div>
        </div>

        <div>
            <p class="section-kicker">{$_('tools.pacAllocator.targetAndGrid')}</p>
            <div class="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <label class="field-label">
                    <span>{$_('tools.pacAllocator.rows.target')}</span>
                    <ExactDecimalInput
                        value={row.value.target_percent ?? ''}
                        step="0.01"
                        maxIntegerDigits={3}
                        maxFractionDigits={10}
                        ariaLabel={$_('tools.pacAllocator.rows.target')}
                        testid={`pac-target-weight-${index}`}
                        {disabled}
                        onchange={(value) => {
                            row.value.target_percent = value;
                            onchange();
                        }}
                    />
                </label>
                <label class="field-label">
                    <span>{$_('tools.pacAllocator.rows.gridMode')}</span>
                    <SimpleSelect
                        value={row.value.buy_grid.mode ?? ''}
                        options={gridModeOptions}
                        placeholder={$_('tools.pacAllocator.selectGrid')}
                        ariaLabel={$_('tools.pacAllocator.rows.gridMode')}
                        testId={`pac-grid-mode-${index}`}
                        dropdownPosition="auto"
                        matchTriggerWidth
                        {disabled}
                        onchange={setGridMode}
                    />
                </label>
                <label class="field-label">
                    <span>{$_('tools.pacAllocator.rows.quantityStep')}</span>
                    <ExactDecimalInput
                        value={row.value.buy_grid.quantity_step ?? ''}
                        step={row.value.buy_grid.mode === 'whole' ? '1' : '0.001'}
                        maxIntegerDigits={12}
                        maxFractionDigits={12}
                        ariaLabel={$_('tools.pacAllocator.rows.quantityStep')}
                        testid={`pac-step-quantity-${index}`}
                        {disabled}
                        onchange={(value) => {
                            row.value.buy_grid.quantity_step = value;
                            onchange();
                        }}
                    />
                </label>
            </div>
        </div>
    </div>
</article>

<style>
    .field-label {
        display: flex;
        min-width: 0;
        flex-direction: column;
        gap: 0.35rem;
        font-size: 0.75rem;
        font-weight: 500;
        color: rgb(75 85 99);
    }

    :global(.dark) .field-label {
        color: rgb(209 213 219);
    }

    .section-kicker {
        font-size: 0.6875rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: rgb(107 114 128);
    }

    :global(.dark) .section-kicker {
        color: rgb(156 163 175);
    }
</style>
