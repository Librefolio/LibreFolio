<script lang="ts">
    import {onDestroy} from 'svelte';
    import {t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';
    import CurrencySearchSelect from '$lib/components/ui/select/CurrencySearchSelect.svelte';
    import {assertToolAccount} from '$lib/features/tools/contracts';
    import {lookupFxRate} from '$lib/stores/fxStoreRegistry';
    import {currencyStoreVersion, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {formatDecimalForDisplay} from '$lib/utils/core/formatDecimal';
    import {CloudDownload, Info, LoaderCircle, PencilLine, Plus, Trash2} from 'lucide-svelte';
    import type {PacRateInput} from './editorTypes';

    interface Props {
        rates: PacRateInput[];
        requiredCurrencies: readonly string[];
        reportCurrency: string;
        asOfDate: string;
        accountGeneration: number;
        disabled?: boolean;
        onchange: () => void;
    }

    let {rates, requiredCurrencies, reportCurrency, asOfDate, accountGeneration, disabled = false, onchange}: Props = $props();

    const MAX_VALUATION_RATES = 4;
    let requestSequence = 0;
    let copyingCurrency = $state<string | null>(null);
    let copyErrors = $state<Record<string, boolean>>({});
    let visible = $derived(requiredCurrencies.length > 0 || rates.length > 0);

    function flag(code: string): string {
        void $currencyStoreVersion;
        const value = getCurrencyInfo(code).flag_emoji;
        return value === '🏳️' ? '' : value;
    }

    function createRate(currency = ''): PacRateInput {
        return {currency, rate_to_report: '', reference_date: ''};
    }

    function addRate(currency = ''): void {
        if (rates.length >= MAX_VALUATION_RATES) return;
        const configured = new Set(rates.map((rate) => rate.currency?.trim().toUpperCase()));
        const selected = currency || requiredCurrencies.find((item) => !configured.has(item)) || '';
        rates.push(createRate(selected));
        if (selected) copyErrors = {...copyErrors, [selected]: false};
        onchange();
    }

    function rateChanged(...currencies: Array<string | null | undefined>): void {
        const nextErrors = {...copyErrors};
        for (const currency of currencies) {
            const code = currency?.trim().toUpperCase();
            if (code) nextErrors[code] = false;
        }
        copyErrors = nextErrors;
        onchange();
    }

    function removeRate(index: number): void {
        requestSequence += 1;
        copyingCurrency = null;
        rates.splice(index, 1);
        onchange();
    }

    async function copyRate(currency: string): Promise<void> {
        const native = currency.trim().toUpperCase();
        const reporting = reportCurrency.trim().toUpperCase();
        const requestedDate = asOfDate;
        if (!native || !reporting || !requestedDate || native === reporting) return;

        const existing = rates.find((rate) => rate.currency?.trim().toUpperCase() === native);
        if (!existing && rates.length >= MAX_VALUATION_RATES) return;
        const sequence = ++requestSequence;
        const generation = accountGeneration;
        const original = existing ? `${existing.rate_to_report}|${existing.reference_date}` : null;
        copyingCurrency = native;
        copyErrors = {...copyErrors, [native]: false};
        try {
            const point = await lookupFxRate(native, reporting, requestedDate);
            if (sequence !== requestSequence || generation !== accountGeneration || reportCurrency.trim().toUpperCase() !== reporting || asOfDate !== requestedDate) return;
            assertToolAccount(generation);
            const current = rates.find((rate) => rate.currency?.trim().toUpperCase() === native);
            if (existing ? current !== existing || `${current.rate_to_report}|${current.reference_date}` !== original : current !== undefined) return;
            if (!point || point.rate === null) {
                copyErrors = {...copyErrors, [native]: true};
                return;
            }
            const target = existing ?? createRate(native);
            target.rate_to_report = formatDecimalForDisplay(String(point.rate), {maxFrac: 12});
            target.reference_date = point.backwardFillInfo?.actualRateDate ?? point.date;
            if (!existing) {
                if (rates.length >= MAX_VALUATION_RATES) return;
                rates.push(target);
            }
            onchange();
        } catch {
            if (sequence !== requestSequence || generation !== accountGeneration || reportCurrency.trim().toUpperCase() !== reporting || asOfDate !== requestedDate) return;
            try {
                assertToolAccount(generation);
            } catch {
                return;
            }
            copyErrors = {...copyErrors, [native]: true};
        } finally {
            if (sequence === requestSequence) copyingCurrency = null;
        }
    }

    onDestroy(() => {
        requestSequence += 1;
    });
</script>

{#if visible}
    <section class="rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800/60" data-testid="allocation-valuation-rates">
        <div class="flex items-start gap-2">
            <div class="min-w-0 flex-1">
                <h2 class="text-sm font-semibold text-gray-900 dark:text-white">
                    {$t('tools.pacAllocator.rates.title', {default: 'Valuation exchange rates'})}
                </h2>
                <p class="mt-0.5 text-xs leading-5 text-gray-500 dark:text-gray-400">
                    {$t('tools.pacAllocator.rates.description', {
                        default: 'Convert facts into the reporting currency for comparison only. No cash is exchanged or transferred.',
                    })}
                </p>
            </div>
            <Tooltip
                text={$t('tools.pacAllocator.rates.equationHint', {
                    default: 'Example: 1 USD = 0.90 EUR means one USD is valued at 0.90 EUR in this report.',
                })}
                position="left"
                maxWidth="320px"
            >
                <button type="button" class="inline-flex shrink-0 text-gray-400" aria-label={$t('tools.pacAllocator.rates.equationHint', {default: 'Valuation-rate details'})}>
                    <Info size={15} />
                </button>
            </Tooltip>
        </div>

        {#if requiredCurrencies.length > 0}
            <div class="mt-3 flex flex-wrap gap-2">
                {#each requiredCurrencies as currency (currency)}
                    {@const configured = rates.some((rate) => rate.currency?.trim().toUpperCase() === currency)}
                    <div class="flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-2 text-xs text-blue-950 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-100">
                        <span class="font-semibold">
                            {#if flag(currency)}<span class="emoji-flag" aria-hidden="true">{flag(currency)}</span>{/if}
                            1 {currency} → {reportCurrency}
                        </span>
                        <button
                            class="inline-flex h-7 items-center gap-1 rounded-md border border-blue-300 bg-white px-2 font-medium text-blue-800 hover:bg-blue-100 disabled:opacity-50 dark:border-blue-800 dark:bg-gray-900 dark:text-blue-200"
                            type="button"
                            onclick={() => void copyRate(currency)}
                            disabled={disabled || copyingCurrency !== null || (!configured && rates.length >= MAX_VALUATION_RATES)}
                        >
                            {#if copyingCurrency === currency}<LoaderCircle class="animate-spin" size={12} />{:else}<CloudDownload size={12} />{/if}
                            {$t('tools.pacAllocator.rates.copySaved', {default: 'Copy rate'})}
                        </button>
                        {#if !configured}
                            <button class="inline-flex h-7 items-center gap-1 rounded-md px-2 font-medium text-blue-800 hover:bg-blue-100 disabled:opacity-50 dark:text-blue-200" type="button" onclick={() => addRate(currency)} {disabled}>
                                <PencilLine size={12} />
                                {$t('tools.pacAllocator.rates.enterManually', {default: 'Enter manually'})}
                            </button>
                        {/if}
                    </div>
                    {#if copyErrors[currency]}
                        <p class="w-full text-xs text-red-700 dark:text-red-300" role="alert">
                            {$t('tools.pacAllocator.rates.copyUnavailable', {
                                default: `No saved ${currency} to ${reportCurrency} rate is available for ${asOfDate}.`,
                                values: {currency, reportCurrency, date: asOfDate},
                            })}
                        </p>
                    {/if}
                {/each}
            </div>
        {/if}

        {#if rates.length > 0}
            <div class="mt-3 space-y-2 border-t border-gray-200 pt-3 dark:border-gray-700">
                {#each rates as rate, index}
                    <div class="grid gap-2 rounded-lg border border-gray-200 p-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_minmax(0,1fr)_auto] sm:items-end dark:border-gray-700" data-testid="allocation-rate-row">
                        <label class="field-label">
                            <span>{$t('tools.pacAllocator.rates.nativeCurrency', {default: 'Native currency'})}</span>
                            <CurrencySearchSelect
                                value={rate.currency ?? ''}
                                compact
                                testId={`allocation-rate-currency-${index}`}
                                {disabled}
                                onchange={(value) => {
                                    const previous = rate.currency;
                                    rate.currency = value;
                                    rateChanged(previous, value);
                                }}
                            />
                        </label>
                        <label class="field-label">
                            <span>{$t('tools.pacAllocator.rates.value')}</span>
                            <div class="flex items-center gap-1.5">
                                <ExactDecimalInput
                                    value={rate.rate_to_report ?? ''}
                                    step="0.0001"
                                    maxIntegerDigits={12}
                                    maxFractionDigits={12}
                                    ariaLabel={$t('tools.pacAllocator.rates.value')}
                                    testid={`allocation-rate-value-${index}`}
                                    className="min-h-9 !px-2 !py-1.5 text-sm"
                                    {disabled}
                                    onchange={(value) => {
                                        rate.rate_to_report = value;
                                        rateChanged(rate.currency);
                                    }}
                                />
                                <span class="shrink-0 text-xs font-semibold text-gray-500 dark:text-gray-300">{reportCurrency}</span>
                            </div>
                        </label>
                        <SingleDatePicker
                            value={rate.reference_date ?? ''}
                            label={$t('tools.pacAllocator.rates.date')}
                            inputStyle
                            clearable
                            {disabled}
                            onchange={(value) => {
                                rate.reference_date = value;
                                rateChanged(rate.currency);
                            }}
                            testid={`allocation-rate-date-${index}`}
                        />
                        <button class="inline-flex h-9 w-9 items-center justify-center rounded-md text-red-600 hover:bg-red-50 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-950/30" type="button" onclick={() => removeRate(index)} {disabled} aria-label={$t('common.remove')}>
                            <Trash2 size={14} />
                        </button>
                    </div>
                {/each}
            </div>
        {/if}

        <button
            class="mt-3 inline-flex min-h-8 items-center gap-1.5 rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200"
            type="button"
            onclick={() => addRate()}
            disabled={disabled || rates.length >= MAX_VALUATION_RATES}
            data-testid="allocation-rate-add"
        >
            <Plus size={13} />
            {$t('tools.pacAllocator.rates.add')}
        </button>
    </section>
{/if}

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
