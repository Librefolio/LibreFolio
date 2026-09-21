<script lang="ts">
    import {t} from '$lib/i18n';
    import {AlertCircle, AlertTriangle, CheckCircle2, Info} from 'lucide-svelte';

    interface AllocationIssue {
        kind: 'missing' | 'invalid' | 'unsupported' | 'info';
        code: string;
        path: Array<string | number>;
        related_indices: number[];
        params: Record<string, unknown>;
    }

    interface Props {
        availability: 'ready' | 'needs_input' | 'invalid' | 'unsupported';
        issues: readonly AllocationIssue[];
    }

    let {availability, issues}: Props = $props();

    function issueText(issue: AllocationIssue): string {
        const currency = typeof issue.params.currency === 'string' ? issue.params.currency : '—';
        const limit = typeof issue.params.limit === 'string' || typeof issue.params.limit === 'number' ? issue.params.limit : '—';
        const messages: Record<string, string> = {
            assets_required: $t('tools.allocation.issues.assetsRequired', {default: 'Select at least one Asset.'}),
            holdings_required: $t('tools.allocation.issues.holdingsRequired', {default: 'Select at least one portfolio holding.'}),
            targets_required: $t('tools.allocation.issues.targetsRequired', {default: 'Set a target allocation for the selected Assets.'}),
            target_required: $t('tools.allocation.issues.targetRequired', {default: 'Every selected Asset needs a target percentage.'}),
            field_required: $t('tools.allocation.issues.fieldRequired', {default: 'Complete this required field.'}),
            incomplete_decimal: $t('tools.allocation.issues.incompleteDecimal', {default: 'Complete the decimal value.'}),
            quote_required: $t('tools.allocation.issues.quoteRequired', {default: 'Enter the current price and its currency.'}),
            cash_vector_required: $t('tools.allocation.issues.cashRequired', {default: 'Enter cash rows, or keep an explicit empty list.'}),
            valuation_rate_required: $t('tools.allocation.issues.valuationRateRequired', {
                default: 'Enter a valuation rate for {currency}.',
                values: {currency},
            }),
            invalid_decimal_syntax: $t('tools.allocation.issues.invalidDecimal', {default: 'Enter a valid decimal number.'}),
            invalid_currency: $t('tools.allocation.issues.invalidCurrency', {default: 'Choose a valid three-letter currency.'}),
            invalid_date: $t('tools.allocation.issues.invalidDate', {default: 'Enter a valid date.'}),
            reference_after_asof: $t('tools.allocation.issues.referenceAfterAsOf', {default: 'The source date cannot be after the analysis date.'}),
            nonpositive_price: $t('tools.allocation.issues.nonpositivePrice', {default: 'The current price must be greater than zero.'}),
            nonpositive_fx_rate: $t('tools.allocation.issues.nonpositiveFxRate', {default: 'The valuation rate must be greater than zero.'}),
            invalid_quote_basis: $t('tools.allocation.issues.invalidQuoteBasis', {default: 'The quoted unit basis must be a positive whole number.'}),
            target_percent_out_of_range: $t('tools.allocation.issues.targetOutOfRange', {default: 'Each target must be between 0% and 100%.'}),
            target_total_not_100: $t('tools.allocation.issues.targetTotal', {default: 'Target percentages must total exactly 100%.'}),
            nonpositive_quantity_step: $t('tools.allocation.issues.nonpositiveQuantityStep', {default: 'The purchase quantity step must be greater than zero.'}),
            noninteger_whole_step: $t('tools.allocation.issues.nonintegerWholeStep', {default: 'A whole-unit purchase step must be a whole number.'}),
            negative_contribution: $t('tools.allocation.issues.negativeContribution', {default: 'A new contribution cannot be negative.'}),
            nonpositive_monetary_step: $t('tools.allocation.issues.nonpositiveMonetaryStep', {default: 'The monetary step must be greater than zero.'}),
            contribution_not_multiple_of_monetary_step: $t('tools.allocation.issues.contributionStep', {default: 'The contribution must be a multiple of its monetary step.'}),
            duplicate_row_key: $t('tools.allocation.issues.duplicateRow', {default: 'Two custody rows have the same technical identity.'}),
            duplicate_instrument: $t('tools.allocation.issues.duplicateInstrument', {default: 'This Asset is selected more than once.'}),
            duplicate_target_instrument: $t('tools.allocation.issues.duplicateTarget', {default: 'This Asset has more than one target.'}),
            target_instrument_not_selected: $t('tools.allocation.issues.unselectedTarget', {default: 'A target refers to an Asset that is no longer selected.'}),
            identity_rate_mismatch: $t('tools.allocation.issues.identityRate', {
                default: 'The report currency {currency} must use an identity valuation rate of 1.',
                values: {currency},
            }),
            duplicate_currency: $t('tools.allocation.issues.duplicateCurrency', {
                default: '{currency} appears more than once where only one row per currency is allowed.',
                values: {currency},
            }),
            numeric_domain_exceeded: $t('tools.allocation.issues.numericDomain', {default: 'A number exceeds the supported exact numeric domain.'}),
            currency_domain_exceeded: $t('tools.allocation.issues.currencyDomain', {
                default: 'This scenario contains more currencies than the P1 limit of {limit}.',
                values: {limit},
            }),
            short_inventory_unsupported: $t('tools.allocation.issues.shortInventory', {default: 'Short positions are outside this P1 analysis.'}),
            initial_debt_unsupported: $t('tools.allocation.issues.initialDebt', {default: 'Negative existing cash is outside this P1 analysis.'}),
            reference_date_unspecified: $t('tools.allocation.issues.referenceDateUnspecified', {default: 'A reference date was not provided; review data freshness manually.'}),
            inventory_off_buy_grid: $t('tools.allocation.issues.inventoryOffGrid', {default: 'Existing fractional custody does not match the future purchase step. It was preserved exactly.'}),
            identity_rate_redundant: $t('tools.allocation.issues.identityRateRedundant', {default: 'The report-currency rate is redundant and was treated as 1.'}),
            unused_valuation_reference: $t('tools.allocation.issues.unusedValuation', {
                default: 'The valuation rate for {currency} is not used by this scenario.',
                values: {currency},
            }),
        };
        return messages[issue.code] ?? $t('tools.allocation.issues.generic', {default: 'Review this scenario input.'});
    }

    function pathText(path: readonly (string | number)[]): string {
        if (path.length === 0) return '';
        const labels: Record<string, string> = {
            report_currency: $t('tools.pacAllocator.reportCurrency'),
            as_of_date: $t('tools.pacAllocator.asOfDate'),
            assets: $t('tools.allocation.path.assets', {default: 'Assets'}),
            holdings: $t('tools.allocation.path.holdings', {default: 'Holdings'}),
            targets: $t('tools.allocation.path.targets', {default: 'Targets'}),
            cash_balances: $t('tools.allocation.path.cash', {default: 'Existing cash'}),
            contributions: $t('tools.allocation.path.contributions', {default: 'Contributions'}),
            valuation_rates: $t('tools.allocation.path.valuationRates', {default: 'Valuation rates'}),
            row_key: $t('tools.pacAllocator.result.row'),
            instrument_key: $t('tools.pacAllocator.instrumentId'),
            name: $t('common.name'),
            quote: $t('common.currentPrice'),
            amount: $t('common.amount'),
            currency: $t('common.currency'),
            quote_base_quantity: $t('tools.pacAllocator.rows.quoteBasis'),
            reference_date: $t('tools.pacAllocator.rows.quoteDate'),
            buy_grid: $t('tools.allocation.asset.futureConstraints', {default: 'Future purchase constraints'}),
            mode: $t('tools.pacAllocator.rows.gridMode'),
            target_percent: $t('tools.pacAllocator.rows.target'),
            quantity: $t('tools.pacAllocator.rows.initialQuantity'),
            raw_price: $t('common.currentPrice'),
            quantity_step: $t('tools.pacAllocator.rows.quantityStep'),
            monetary_step: $t('tools.pacAllocator.cash.monetaryStep', {default: 'Amount increment'}),
            rate_to_report: $t('tools.pacAllocator.rates.value'),
        };
        return path.map((part) => (typeof part === 'number' ? `#${part + 1}` : (labels[part] ?? part.replaceAll('_', ' ')))).join(' · ');
    }

    let grouped = $derived.by(() => {
        const result = new Map<string, {issue: AllocationIssue; count: number}>();
        for (const issue of issues) {
            const key = `${issue.kind}:${issue.code}:${issue.path.join('.')}`;
            const existing = result.get(key);
            if (existing) existing.count += 1;
            else result.set(key, {issue, count: 1});
        }
        return [...result.values()];
    });
</script>

<section
    class="rounded-xl border p-3 {availability === 'ready'
        ? 'border-green-200 bg-green-50/70 dark:border-green-900 dark:bg-green-950/20'
        : availability === 'needs_input'
          ? 'border-amber-200 bg-amber-50/70 dark:border-amber-900 dark:bg-amber-950/20'
          : 'border-red-200 bg-red-50/70 dark:border-red-900 dark:bg-red-950/20'}"
    data-testid="allocation-diagnostics"
>
    <div class="flex items-start gap-2">
        {#if availability === 'ready'}
            <CheckCircle2 class="mt-0.5 shrink-0 text-green-700 dark:text-green-300" size={17} />
        {:else if availability === 'needs_input'}
            <AlertTriangle class="mt-0.5 shrink-0 text-amber-700 dark:text-amber-300" size={17} />
        {:else}
            <AlertCircle class="mt-0.5 shrink-0 text-red-700 dark:text-red-300" size={17} />
        {/if}
        <div class="min-w-0 flex-1">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white">
                {#if availability === 'ready'}
                    {$t('tools.allocation.diagnostics.ready', {default: 'Scenario ready'})}
                {:else if availability === 'needs_input'}
                    {$t('tools.allocation.diagnostics.needsInput', {default: 'Complete the scenario'})}
                {:else if availability === 'unsupported'}
                    {$t('tools.allocation.diagnostics.unsupported', {default: 'Scenario outside P1 boundaries'})}
                {:else}
                    {$t('tools.allocation.diagnostics.invalid', {default: 'Correct the scenario'})}
                {/if}
            </h3>
            {#if grouped.length > 0}
                <ul class="mt-2 space-y-1.5">
                    {#each grouped as entry (`${entry.issue.kind}:${entry.issue.code}:${entry.issue.path.join('.')}`)}
                        <li class="flex items-start gap-1.5 text-xs leading-5 text-gray-700 dark:text-gray-200">
                            <Info class="mt-1 shrink-0 text-gray-400" size={12} />
                            <span>
                                {issueText(entry.issue)}
                                {#if pathText(entry.issue.path)}
                                    <span class="text-gray-500 dark:text-gray-400">({pathText(entry.issue.path)})</span>
                                {/if}
                                {#if entry.count > 1}<span class="ml-1 font-medium">×{entry.count}</span>{/if}
                            </span>
                        </li>
                    {/each}
                </ul>
                <details class="mt-2 text-[11px] text-gray-500 dark:text-gray-400">
                    <summary class="cursor-pointer font-medium">{$t('tools.allocation.diagnostics.technical', {default: 'Technical details'})}</summary>
                    <ul class="mt-1 space-y-0.5 font-mono">
                        {#each issues as issue, index (`${issue.code}:${issue.path.join('.')}:${index}`)}
                            <li>{issue.kind}: {issue.code} [{issue.path.join('.') || 'root'}]</li>
                        {/each}
                    </ul>
                </details>
            {:else}
                <p class="mt-1 text-xs text-gray-600 dark:text-gray-300">
                    {$t('tools.allocation.diagnostics.noIssues', {default: 'All required inputs are valid for this P1 analysis.'})}
                </p>
            {/if}
        </div>
    </div>
</section>
