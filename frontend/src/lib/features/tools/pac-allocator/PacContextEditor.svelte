<script lang="ts">
    import {_} from '$lib/i18n';
    import AssetIcon from '$lib/components/assets/AssetIcon.svelte';
    import BrokerIcon from '$lib/components/brokers/BrokerIcon.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {assetProvidersVersion, ensureAssetProvidersCached, getAssetProviderIconUrl} from '$lib/utils/providerHelpers';
    import {AlertTriangle, Copy, Database, Info, LockKeyhole, Trash2} from 'lucide-svelte';
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

    let providerIconUrl = $derived.by(() => {
        void $assetProvidersVersion;
        return row.source?.quoteSource ? getAssetProviderIconUrl(row.source.quoteSource) : null;
    });

    $effect(() => {
        if (row.source?.quoteSource) void ensureAssetProvidersCached();
    });

    function displayDecimal(value: string | null | undefined): string {
        return formatDecimalForDisplay(value, {maxFrac: 12}) || '—';
    }

    function sourceScopeLabel(): string {
        if (row.source?.usageScope === 'owned') return $_('tools.pacAllocator.gallery.owned', {default: 'Owned'});
        if (row.source?.usageScope === 'other_users') return $_('tools.pacAllocator.gallery.otherUsers', {default: 'Other users'});
        return $_('tools.pacAllocator.gallery.observed', {default: 'Observed'});
    }

    function setPrice(value: string): void {
        row.value.quote.raw_price = value || null;
        onchange();
    }

    function setPriceDate(value: string): void {
        row.value.quote.reference_date = value || null;
        onchange();
    }

    function setGridMode(mode: 'whole' | 'fractional'): void {
        const previousMode = row.value.buy_grid.mode;
        const previousStep = row.value.buy_grid.quantity_step ?? '';
        const previousDefault = previousMode === 'whole' ? '1' : previousMode === 'fractional' ? '0.001' : '';
        if (!previousStep || previousStep === previousDefault) {
            row.value.buy_grid.quantity_step = mode === 'whole' ? '1' : '0.001';
        }
        row.value.buy_grid.mode = mode;
        onchange();
    }
</script>

<article class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900/50" data-testid="pac-row" data-row-index={index} data-origin={row.origin} data-source-mode={row.source ? 'locked' : 'manual'}>
    <div class="flex items-start gap-3 border-b border-gray-100 bg-gray-50/80 px-3 py-3 dark:border-gray-800 dark:bg-gray-900">
        <div class="flex shrink-0 items-center -space-x-2">
            <AssetIcon iconUrl={row.source?.assetIconUrl ?? null} assetType={row.source?.assetType ?? null} altText={row.value.name || $_('common.asset')} size="md" />
            {#if row.source?.brokerId !== null && row.source?.brokerId !== undefined}
                <div class="rounded-full border-2 border-gray-50 bg-white dark:border-gray-900 dark:bg-gray-900">
                    <BrokerIcon brokerId={row.source.brokerId} iconUrl={row.source.brokerIconUrl} portalUrl={row.source.brokerPortalUrl} pluginCode={row.source.brokerDefaultImportPlugin} altText={row.source.brokerName ?? $_('common.broker')} size="sm" />
                </div>
            {/if}
        </div>

        <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
                <h4 class="truncate text-sm font-semibold text-gray-900 dark:text-white">
                    {row.value.name || $_('tools.pacAllocator.newManualAsset', {default: 'New manual Asset'})}
                </h4>
                {#if row.source?.brokerName}
                    <span class="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-medium text-blue-800 dark:bg-blue-900/40 dark:text-blue-200">
                        <Database size={11} />
                        {row.source.brokerName}
                    </span>
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                        {$_('tools.pacAllocator.fullCustody')}
                    </span>
                {:else if row.source}
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">{sourceScopeLabel()}</span>
                {:else}
                    <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                        {row.origin === 'manual_duplicate' ? $_('tools.pacAllocator.manualCopy', {default: 'Independent manual copy'}) : $_('tools.pacAllocator.manual')}
                    </span>
                {/if}
                {#if row.stale}
                    <span class="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
                        <AlertTriangle size={11} />
                        {$_('tools.pacAllocator.staleLabel')}
                    </span>
                {/if}
            </div>

            {#if row.source}
                <div class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
                    <span>
                        {row.source.kind === 'portfolio_context' ? $_('tools.pacAllocator.importedSnapshot', {default: 'Imported custody snapshot'}) : $_('tools.pacAllocator.noCurrentCustody', {default: 'No current custody'})}
                    </span>
                    <span aria-hidden="true">·</span>
                    <span>{$_('tools.pacAllocator.snapshotAt')} {row.source.sourceAsOfDate}</span>
                    {#if row.source.quoteReferenceDate}
                        <span aria-hidden="true">·</span>
                        <span>{$_('tools.pacAllocator.priceAt')} {row.source.quoteReferenceDate}</span>
                    {/if}
                    {#if row.source.quoteSource}
                        <span aria-hidden="true">·</span>
                        <span class="inline-flex items-center gap-1" data-testid={`pac-provider-source-${index}`}>
                            {#if providerIconUrl}
                                <img src={providerIconUrl} alt="" class="h-3.5 w-3.5 rounded-sm object-contain" />
                            {:else}
                                <Database size={12} />
                            {/if}
                            {row.source.quoteSource}
                        </span>
                    {/if}
                    <span aria-hidden="true">·</span>
                    <span class="inline-flex items-center gap-1 font-medium text-gray-600 dark:text-gray-300">
                        <LockKeyhole size={12} />
                        {$_('tools.pacAllocator.readOnlyFacts', {default: 'source facts read-only'})}
                    </span>
                </div>
            {/if}
        </div>

        <div class="flex shrink-0 items-center gap-1">
            <button class="btn btn-ghost px-2" type="button" onclick={onduplicate} {disabled} data-testid={`pac-duplicate-asset-${index}`} aria-label={$_('tools.pacAllocator.duplicate')}>
                <Copy size={15} />
                <span class="hidden sm:inline">{$_('tools.pacAllocator.duplicate')}</span>
            </button>
            <button class="btn btn-ghost px-2 text-red-600 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:hover:bg-red-950/30 dark:hover:text-red-300" type="button" onclick={onremove} {disabled} data-testid={`pac-remove-asset-${index}`} aria-label={$_('common.remove')}>
                <Trash2 size={15} />
                <span class="hidden sm:inline">{$_('common.remove')}</span>
            </button>
        </div>
    </div>

    <div class="grid gap-3 p-3 lg:grid-cols-2">
        <section class="rounded-lg border border-gray-200 bg-gray-50/60 p-3 dark:border-gray-700 dark:bg-gray-900/40" data-testid={`pac-initial-state-${index}`}>
            <p class="section-kicker">{$_('tools.pacAllocator.initialState', {default: 'Initial state'})}</p>

            {#if row.source}
                <dl class="mt-3 grid gap-3 sm:grid-cols-2">
                    <div class="fact-cell">
                        <dt>{row.source.kind === 'portfolio_context' ? $_('tools.pacAllocator.brokerCustody', {default: 'Broker custody'}) : $_('tools.pacAllocator.rows.initialQuantity')}</dt>
                        <dd data-testid={`pac-imported-initial-quantity-${index}`}>{displayDecimal(row.value.initial_quantity)} {$_('tools.pacAllocator.units', {default: 'units'})}</dd>
                    </div>
                    {#if row.source.ownershipSharePercent !== null}
                        <div class="fact-cell">
                            <dt class="inline-flex items-center gap-1">
                                {$_('tools.pacAllocator.economicShare', {default: 'Personal economic share'})}
                                <Tooltip
                                    text={$_('tools.pacAllocator.economicShareHint', {
                                        default: 'Informational ownership share. Imported custody quantities remain whole and are never scaled.',
                                    })}
                                    position="top"
                                    maxWidth="300px"
                                >
                                    <button type="button" class="inline-flex text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" aria-label={$_('tools.pacAllocator.economicShareHint', {default: 'Ownership share details'})}>
                                        <Info size={13} />
                                    </button>
                                </Tooltip>
                            </dt>
                            <dd data-testid={`pac-imported-ownership-share-${index}`}>{displayDecimal(row.source.ownershipSharePercent)}%</dd>
                        </div>
                    {/if}
                    <div class="fact-cell">
                        <dt>{$_('tools.pacAllocator.nativePrice', {default: 'Native price'})}</dt>
                        <dd data-testid={`pac-imported-price-${index}`}>
                            {displayDecimal(row.value.quote.raw_price)}
                            {row.value.quote.currency ?? ''}
                        </dd>
                    </div>
                    <div class="fact-cell">
                        <dt>{$_('tools.pacAllocator.rows.quoteBasis')}</dt>
                        <dd data-testid={`pac-imported-price-basis-${index}`}>
                            {row.value.quote.quote_base_quantity ?? '—'}
                            {$_('tools.pacAllocator.units', {default: 'units'})}
                        </dd>
                    </div>
                </dl>
            {:else}
                <div class="mt-3 grid gap-3 sm:grid-cols-2">
                    <label class="field-label sm:col-span-2">
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
                    <div class="field-label">
                        <span class="inline-flex items-center gap-1">
                            {$_('tools.pacAllocator.rows.quoteBasis')}
                            <Tooltip
                                text={$_('tools.pacAllocator.quoteBasisHint', {
                                    default: 'Positive integer number of units represented by the native price.',
                                })}
                                position="top"
                                maxWidth="280px"
                            >
                                <button type="button" class="inline-flex text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" aria-label={$_('tools.pacAllocator.quoteBasisHint', {default: 'Quote-basis details'})}>
                                    <Info size={13} />
                                </button>
                            </Tooltip>
                        </span>
                        <input
                            class="input-field"
                            type="number"
                            min="1"
                            step="1"
                            inputmode="numeric"
                            value={row.value.quote.quote_base_quantity ?? ''}
                            aria-label={$_('tools.pacAllocator.rows.quoteBasis')}
                            required
                            {disabled}
                            oninput={(event) => {
                                row.value.quote.quote_base_quantity = event.currentTarget.value === '' ? null : Number(event.currentTarget.value);
                                onchange();
                            }}
                            data-testid={`pac-price-basis-${index}`}
                        />
                    </div>
                    <div class="sm:col-span-2">
                        <SingleDatePicker value={row.value.quote.reference_date ?? ''} label={$_('tools.pacAllocator.rows.quoteDate')} inputStyle clearable {disabled} onchange={setPriceDate} testid={`pac-price-date-${index}`} />
                    </div>
                </div>
            {/if}
        </section>

        <section class="rounded-lg border border-gray-200 p-3 dark:border-gray-700" data-testid={`pac-target-state-${index}`}>
            <p class="section-kicker">{$_('tools.pacAllocator.target', {default: 'Target'})}</p>
            <div class="mt-3 space-y-3">
                <label class="field-label">
                    <span>{$_('tools.pacAllocator.rows.target')}</span>
                    <div class="flex items-center gap-2">
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
                        <span class="text-sm font-medium text-gray-500 dark:text-gray-400">%</span>
                    </div>
                </label>

                <div class="field-label">
                    <span class="inline-flex items-center gap-1">
                        {$_('tools.pacAllocator.rows.gridMode')}
                        <Tooltip
                            text={$_('tools.pacAllocator.gridModeHint', {
                                default: 'Controls only the quantity increment of future purchases. Existing fractional inventory is never rounded.',
                            })}
                            position="top"
                            maxWidth="300px"
                        >
                            <button type="button" class="inline-flex text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" aria-label={$_('tools.pacAllocator.gridModeHint', {default: 'Purchase-grid details'})}>
                                <Info size={13} />
                            </button>
                        </Tooltip>
                    </span>
                    <div class="grid grid-cols-2 rounded-lg border border-gray-300 bg-gray-100 p-1 dark:border-gray-600 dark:bg-gray-800" role="group" aria-label={$_('tools.pacAllocator.rows.gridMode')} data-testid={`pac-grid-mode-${index}`}>
                        <button
                            class="rounded-md px-2 py-1.5 text-xs font-semibold transition {row.value.buy_grid.mode === 'whole' ? 'bg-white text-libre-green shadow-sm dark:bg-gray-700 dark:text-green-300' : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-100'}"
                            type="button"
                            aria-pressed={row.value.buy_grid.mode === 'whole'}
                            onclick={() => setGridMode('whole')}
                            {disabled}
                            data-testid={`pac-grid-whole-${index}`}
                        >
                            # {$_('tools.pacAllocator.rows.whole')}
                        </button>
                        <button
                            class="rounded-md px-2 py-1.5 text-xs font-semibold transition {row.value.buy_grid.mode === 'fractional' ? 'bg-white text-libre-green shadow-sm dark:bg-gray-700 dark:text-green-300' : 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-100'}"
                            type="button"
                            aria-pressed={row.value.buy_grid.mode === 'fractional'}
                            onclick={() => setGridMode('fractional')}
                            {disabled}
                            data-testid={`pac-grid-fractional-${index}`}
                        >
                            .1 {$_('tools.pacAllocator.rows.fractional')}
                        </button>
                    </div>
                </div>

                <div class="field-label">
                    <span class="inline-flex items-center gap-1">
                        {$_('tools.pacAllocator.rows.quantityStep')}
                        <Tooltip
                            text={$_('tools.pacAllocator.quantityStepHint', {
                                default: 'Minimum quantity increment for new purchases. This is separate from contribution monetary step.',
                            })}
                            position="top"
                            maxWidth="300px"
                        >
                            <button type="button" class="inline-flex text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" aria-label={$_('tools.pacAllocator.quantityStepHint', {default: 'Quantity-step details'})}>
                                <Info size={13} />
                            </button>
                        </Tooltip>
                    </span>
                    <ExactDecimalInput
                        value={row.value.buy_grid.quantity_step ?? ''}
                        step={row.value.buy_grid.mode === 'whole' ? '1' : '0.001'}
                        maxIntegerDigits={12}
                        maxFractionDigits={row.value.buy_grid.mode === 'whole' ? 0 : 12}
                        ariaLabel={$_('tools.pacAllocator.rows.quantityStep')}
                        testid={`pac-step-quantity-${index}`}
                        {disabled}
                        onchange={(value) => {
                            row.value.buy_grid.quantity_step = value;
                            onchange();
                        }}
                    />
                </div>
            </div>
        </section>
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

    .fact-cell {
        min-width: 0;
        border-radius: 0.5rem;
        background: rgb(255 255 255 / 0.8);
        padding: 0.625rem;
    }

    .fact-cell dt {
        font-size: 0.6875rem;
        font-weight: 500;
        color: rgb(107 114 128);
    }

    .fact-cell dd {
        margin-top: 0.2rem;
        overflow-wrap: anywhere;
        font-size: 0.875rem;
        font-weight: 600;
        color: rgb(31 41 55);
    }

    :global(.dark) .fact-cell {
        background: rgb(17 24 39 / 0.65);
    }

    :global(.dark) .fact-cell dt {
        color: rgb(156 163 175);
    }

    :global(.dark) .fact-cell dd {
        color: rgb(243 244 246);
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
