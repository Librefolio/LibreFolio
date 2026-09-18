<script lang="ts">
    import {t} from '$lib/i18n';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {currencyStoreVersion, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {Copy, Info, Settings2, Trash2} from 'lucide-svelte';
    import type {RebalanceEditorHolding} from './editorTypes';

    interface Props {
        holding: RebalanceEditorHolding;
        index: number;
        disabled?: boolean;
        onduplicate: () => void;
        onremove: () => void;
        onchange: () => void;
    }

    let {holding = $bindable(), index, disabled = false, onduplicate, onremove, onchange}: Props = $props();

    function display(value: string | null | undefined): string {
        return formatDecimalForDisplay(value, {maxFrac: 12}) || '—';
    }

    function flag(code: string | null | undefined): string {
        void $currencyStoreVersion;
        const value = getCurrencyInfo(code ?? '').flag_emoji;
        return value === '🏳️' ? '' : value;
    }

    function setGridMode(mode: 'whole' | 'fractional'): void {
        holding.value.buy_grid.mode = mode;
        if (!holding.value.buy_grid.quantity_step) holding.value.buy_grid.quantity_step = mode === 'whole' ? '1' : '0.001';
        onchange();
    }
</script>

<article class="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid="rebalancer-holding" data-index={index} data-stale={holding.stale}>
    <header class="flex items-start gap-2.5">
        <div class="flex shrink-0 items-center -space-x-2">
            <AssetIcon iconUrl={holding.source?.assetIconUrl ?? null} assetType={holding.source?.assetType ?? null} altText={holding.value.name} size="md" />
            {#if holding.source?.brokerId !== null && holding.source?.brokerId !== undefined}
                <div class="rounded-full border-2 border-white bg-white dark:border-gray-800 dark:bg-gray-800">
                    <BrokerIcon brokerId={holding.source.brokerId} iconUrl={holding.source.brokerIconUrl} portalUrl={holding.source.brokerPortalUrl} pluginCode={holding.source.brokerDefaultImportPlugin} altText={holding.source.brokerName ?? $t('common.broker')} size="sm" />
                </div>
            {/if}
        </div>
        <div class="min-w-0 flex-1">
            {#if holding.source}
                <h3 class="truncate text-sm font-semibold text-gray-900 dark:text-white">{holding.value.name}</h3>
            {:else}
                <input
                    class="min-h-9 w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm font-semibold text-gray-900 outline-none focus:border-libre-green focus:ring-1 focus:ring-libre-green dark:border-gray-600 dark:bg-gray-900 dark:text-white"
                    value={holding.value.name}
                    placeholder={$t('tools.pacAllocator.newManualAsset', {default: 'New manual Asset'})}
                    {disabled}
                    oninput={(event) => {
                        holding.value.name = event.currentTarget.value;
                        onchange();
                    }}
                    data-testid={`rebalancer-holding-name-${index}`}
                />
            {/if}
            <div class="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-gray-600 dark:text-gray-300">
                {#if holding.source?.brokerName}
                    <span class="rounded-full bg-blue-100 px-2 py-0.5 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200">{holding.source.brokerName}</span>
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 dark:bg-gray-700">
                        {$t('tools.portfolioRebalancer.custodyContext', {default: 'Custody context'})}
                    </span>
                {:else if holding.source}
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 dark:bg-gray-700">
                        {$t('tools.portfolioRebalancer.uncustodied', {default: 'No custody'})}
                    </span>
                {:else}
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 dark:bg-gray-700">{$t('tools.pacAllocator.manual')}</span>
                {/if}
                {#if holding.stale}
                    <span class="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
                        {$t('tools.pacAllocator.staleLabel')}
                    </span>
                {/if}
            </div>
        </div>
        <div class="flex shrink-0 items-center gap-0.5">
            <Tooltip text={$t('tools.pacAllocator.duplicate')} position="top" interactiveChild>
                <button
                    class="inline-flex h-8 w-8 items-center justify-center rounded-md text-gray-500 hover:bg-gray-100 hover:text-libre-green dark:hover:bg-gray-700"
                    type="button"
                    onclick={onduplicate}
                    {disabled}
                    data-testid={`rebalancer-duplicate-${index}`}
                    aria-label={$t('tools.pacAllocator.duplicate')}
                >
                    <Copy size={15} />
                </button>
            </Tooltip>
            <Tooltip text={$t('common.remove')} position="top" interactiveChild>
                <button class="inline-flex h-8 w-8 items-center justify-center rounded-md text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/30" type="button" onclick={onremove} {disabled} data-testid={`rebalancer-remove-${index}`} aria-label={$t('common.remove')}>
                    <Trash2 size={15} />
                </button>
            </Tooltip>
        </div>
    </header>

    {#if holding.source}
        <details class="mt-2 rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-2 text-xs dark:border-gray-700 dark:bg-gray-900/50" data-testid={`rebalancer-holding-facts-${index}`}>
            <summary class="cursor-pointer font-medium text-gray-600 dark:text-gray-300">
                {$t('tools.pacAllocator.identityAndCustody')}
            </summary>
            <dl class="mt-2 grid gap-2 text-gray-700 sm:grid-cols-2 lg:grid-cols-4 dark:text-gray-200">
                <div>
                    <dt class="text-[10px] text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.fullCustody')}</dt>
                    <dd class="mt-0.5 font-mono">{display(holding.value.quantity)} <span class="font-sans">{$t('tools.pacAllocator.units', {default: 'units'})}</span></dd>
                </div>
                {#if holding.source.ownershipSharePercent}
                    <div>
                        <dt class="text-[10px] text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.personalShare')}</dt>
                        <dd class="mt-0.5 font-mono">{display(holding.source.ownershipSharePercent)}%</dd>
                    </div>
                {/if}
                <div data-testid={`rebalancer-current-price-${index}`}>
                    <dt class="text-[10px] text-gray-500 dark:text-gray-400">{$t('common.currentPrice')}</dt>
                    <dd class="mt-0.5 inline-flex items-center gap-1">
                        {#if flag(holding.value.quote.currency)}<span class="emoji-flag" aria-hidden="true">{flag(holding.value.quote.currency)}</span>{/if}
                        <span>{holding.value.quote.currency}</span>
                        <span class="font-mono">{display(holding.value.quote.raw_price)}</span>
                    </dd>
                </div>
                <div>
                    <dt class="text-[10px] text-gray-500 dark:text-gray-400">{$t('tools.pacAllocator.rows.quoteBasis')}</dt>
                    <dd class="mt-0.5 font-mono">{holding.value.quote.quote_base_quantity ?? '—'}</dd>
                </div>
            </dl>
            <p class="mt-2 border-t border-gray-200 pt-1.5 text-[10px] text-gray-400 dark:border-gray-700 dark:text-gray-500">
                {$t('tools.pacAllocator.snapshotAt')}: {holding.source.sourceAsOfDate}
                {#if holding.source.quoteReferenceDate}<span aria-hidden="true"> · </span>{$t('tools.pacAllocator.priceAt')}: {holding.source.quoteReferenceDate}{/if}
                {#if holding.source.quoteSource}<span aria-hidden="true"> · </span>{$t('common.provider')}: {holding.source.quoteSource}{/if}
            </p>
        </details>
    {/if}

    {#if !holding.source}
        <div class="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <label class="field-label">
                <span>{$t('tools.pacAllocator.rows.initialQuantity')}</span>
                <ExactDecimalInput
                    value={holding.value.quantity}
                    step="0.000001"
                    maxIntegerDigits={12}
                    maxFractionDigits={12}
                    ariaLabel={$t('tools.pacAllocator.rows.initialQuantity')}
                    testid={`rebalancer-quantity-${index}`}
                    className="min-h-9 !px-2 !py-1.5 text-sm"
                    {disabled}
                    onchange={(value) => {
                        holding.value.quantity = value;
                        onchange();
                    }}
                />
            </label>
            <label class="field-label">
                <span>{$t('common.currency')}</span>
                <CurrencySearchSelect
                    value={holding.value.quote.currency ?? ''}
                    compact
                    testId={`rebalancer-currency-${index}`}
                    {disabled}
                    onchange={(value) => {
                        holding.value.quote.currency = value;
                        onchange();
                    }}
                />
            </label>
            <label class="field-label">
                <span>{$t('common.currentPrice')}</span>
                <ExactDecimalInput
                    value={holding.value.quote.raw_price ?? ''}
                    step="0.01"
                    maxIntegerDigits={12}
                    maxFractionDigits={12}
                    ariaLabel={$t('common.currentPrice')}
                    testid={`rebalancer-price-${index}`}
                    className="min-h-9 !px-2 !py-1.5 text-sm"
                    {disabled}
                    onchange={(value) => {
                        holding.value.quote.raw_price = value;
                        onchange();
                    }}
                />
            </label>
            <label class="field-label">
                <span class="inline-flex items-center gap-1">
                    {$t('tools.pacAllocator.rows.quoteBasis')}
                    <Tooltip text={$t('tools.pacAllocator.quoteBasisHint', {default: 'Number of Asset units represented by the quoted price.'})} position="top" maxWidth="280px">
                        <button type="button" class="inline-flex text-gray-400" aria-label={$t('tools.pacAllocator.quoteBasisHint', {default: 'Number of Asset units represented by the quoted price.'})}><Info size={13} /></button>
                    </Tooltip>
                </span>
                <ExactDecimalInput
                    value={holding.value.quote.quote_base_quantity === null ? '' : String(holding.value.quote.quote_base_quantity)}
                    step="1"
                    maxIntegerDigits={12}
                    maxFractionDigits={0}
                    ariaLabel={$t('tools.pacAllocator.rows.quoteBasis')}
                    testid={`rebalancer-quote-basis-${index}`}
                    className="min-h-9 !px-2 !py-1.5 text-sm"
                    {disabled}
                    onchange={(value) => {
                        holding.value.quote.quote_base_quantity = value === '' ? null : Number(value);
                        onchange();
                    }}
                />
            </label>
            <div class="sm:col-span-2 lg:col-span-4">
                <SingleDatePicker
                    value={holding.value.quote.reference_date ?? ''}
                    label={$t('tools.pacAllocator.rows.quoteDate')}
                    inputStyle
                    clearable
                    {disabled}
                    onchange={(value) => {
                        holding.value.quote.reference_date = value;
                        onchange();
                    }}
                    testid={`rebalancer-price-date-${index}`}
                />
            </div>
        </div>
    {/if}

    <details class="mt-3 border-t border-gray-200 pt-2 dark:border-gray-700">
        <summary class="inline-flex cursor-pointer list-none items-center gap-1.5 text-xs font-medium text-gray-600 dark:text-gray-300">
            <Settings2 size={14} />
            {$t('tools.allocation.asset.futureConstraints', {default: 'Future purchase constraints'})}
        </summary>
        <div class="mt-2 grid gap-2 sm:grid-cols-2">
            <div class="grid grid-cols-2 rounded-md border border-gray-300 bg-gray-100 p-1 dark:border-gray-600 dark:bg-gray-900" role="group">
                <button
                    class="rounded px-2 py-1 text-xs font-medium {holding.value.buy_grid.mode === 'whole' ? 'bg-white text-libre-green shadow-sm dark:bg-gray-700 dark:text-green-300' : 'text-gray-500'}"
                    type="button"
                    aria-pressed={holding.value.buy_grid.mode === 'whole'}
                    onclick={() => setGridMode('whole')}
                    {disabled}
                >
                    {$t('tools.pacAllocator.rows.whole')}
                </button>
                <button
                    class="rounded px-2 py-1 text-xs font-medium {holding.value.buy_grid.mode === 'fractional' ? 'bg-white text-libre-green shadow-sm dark:bg-gray-700 dark:text-green-300' : 'text-gray-500'}"
                    type="button"
                    aria-pressed={holding.value.buy_grid.mode === 'fractional'}
                    onclick={() => setGridMode('fractional')}
                    {disabled}
                >
                    {$t('tools.pacAllocator.rows.fractional')}
                </button>
            </div>
            <ExactDecimalInput
                value={holding.value.buy_grid.quantity_step ?? ''}
                step={holding.value.buy_grid.mode === 'whole' ? '1' : '0.001'}
                maxIntegerDigits={12}
                maxFractionDigits={holding.value.buy_grid.mode === 'whole' ? 0 : 12}
                ariaLabel={$t('tools.pacAllocator.rows.quantityStep')}
                testid={`rebalancer-quantity-step-${index}`}
                className="min-h-8 !rounded-md !px-2 !py-1 text-sm"
                {disabled}
                onchange={(value) => {
                    holding.value.buy_grid.quantity_step = value;
                    onchange();
                }}
            />
        </div>
    </details>
</article>

<style>
    .field-label {
        display: flex;
        min-width: 0;
        flex-direction: column;
        gap: 0.25rem;
        font-size: 0.75rem;
        font-weight: 500;
        color: rgb(75 85 99);
    }

    :global(.dark) .field-label {
        color: rgb(209 213 219);
    }
</style>
