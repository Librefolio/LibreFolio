<script lang="ts">
    import {Info} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {currencyStoreVersion, ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {formatAxisDate} from '$lib/utils/core/formatAxisDate';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';

    type YieldOnCostStatus = 'available' | 'no_income' | 'unavailable';
    type YieldOnCostReason = 'insufficient_history' | 'income_without_eligible_quantity' | 'replay_inconsistent' | 'invalid_split' | 'missing_fx' | 'missing_wac' | 'non_positive_wac';

    interface FxProvenance {
        purpose: 'income' | 'wac';
        requested_date: string;
        rate_date: string;
        from_currency: string;
        to_currency: string;
        days_back: number;
    }

    interface Provenance {
        window_start: string;
        window_end: string;
        first_pair_transaction_date: string | null;
        gross_income_transaction_count: number;
        gross_income_per_unit: {code: string; amount: string | number} | null;
        net_zero: boolean;
        fx: FxProvenance[];
        issue_date: string | null;
        issue_pair: string | null;
    }

    interface YieldOnCostLike {
        status: YieldOnCostStatus;
        value: string | number | null;
        reason: YieldOnCostReason | null;
        provenance: Provenance;
    }

    interface Props {
        result: YieldOnCostLike;
    }

    let {result}: Props = $props();
    void $currencyStoreVersion;
    ensureCurrenciesLoaded($currentLanguage);

    function label(key: string, fallback: string): string {
        const translated = $t(key);
        return translated === key ? fallback : translated;
    }

    function labelWithValues(key: string, fallback: string, values: Record<string, string>): string {
        const translated = $t(key, {values});
        if (translated !== key) return translated;
        return Object.entries(values).reduce((message, [name, value]) => message.replace(`{${name}}`, value), fallback);
    }

    function reasonLabel(reason: string | null | undefined): string {
        const labels: Record<string, [string, string]> = {
            insufficient_history: ['dashboard.yieldOnCostReasons.insufficientHistory', 'History at this broker is shorter than one year.'],
            income_without_eligible_quantity: ['dashboard.yieldOnCostReasons.incomeWithoutEligibleQuantity', 'A recorded payment has no quantity held on the previous day.'],
            replay_inconsistent: ['dashboard.yieldOnCostReasons.replayInconsistent', 'Purchase, sale, or transfer history cannot be reconstructed correctly.'],
            invalid_split: ['dashboard.yieldOnCostReasons.invalidSplit', 'A linked split is inconsistent with the recorded quantities.'],
            missing_fx: ['dashboard.yieldOnCostReasons.missingFx', 'The exchange rate required for a payment is unavailable.'],
            missing_wac: ['dashboard.yieldOnCostReasons.missingWac', 'The average purchase price (WAC) is unavailable.'],
            non_positive_wac: ['dashboard.yieldOnCostReasons.nonPositiveWac', 'The average purchase price (WAC) is zero or negative.'],
        };
        const entry = reason ? labels[reason] : undefined;
        return entry ? label(entry[0], entry[1]) : label('dashboard.yieldOnCostUnavailable', 'Yield on Cost is unavailable.');
    }

    function formatDate(value: string): string {
        return formatAxisDate($currentLanguage, value, true);
    }

    function formatCurrencyCode(code: string): string {
        const flag = getCurrencyInfo(code).flag_emoji;
        return flag && flag !== '🏳️' ? `${flag} ${code}` : code;
    }

    function formatFxPair(pair: string): string {
        const [fromCurrency, toCurrency] = pair.split('/');
        if (!fromCurrency || !toCurrency) return pair;
        return `${formatCurrencyCode(fromCurrency)} → ${formatCurrencyCode(toCurrency)}`;
    }

    function fxLines(provenance: Provenance): string[] {
        const unique = new Map(provenance.fx.filter((entry) => entry.from_currency !== entry.to_currency).map((entry) => [`${entry.from_currency}/${entry.to_currency}/${entry.rate_date}`, entry]));
        const lines = [...unique.values()].map((entry) => `${label('dashboard.yieldOnCostFxPair', 'Conversion')}: ${formatCurrencyCode(entry.from_currency)} → ${formatCurrencyCode(entry.to_currency)} · ${label('dashboard.yieldOnCostFxRateDate', 'rate from')} ${formatDate(entry.rate_date)}`);
        return lines.length > 3 ? [...lines.slice(0, 3), `… (+${lines.length - 3})`] : lines;
    }

    function periodLine(provenance: Provenance): string {
        return `${label('dashboard.yieldOnCostPeriod', 'Period')}: ${formatDate(provenance.window_start)} – ${formatDate(provenance.window_end)}`;
    }

    function availableTooltip(provenance: Provenance, value: number): string {
        const lines = [`${label('dashboard.yieldOnCostValue', 'Yield on Cost')}: ${(value * 100).toFixed(2)}%`];
        if (provenance.gross_income_per_unit) {
            lines.push(`${label('dashboard.yieldOnCostGrossPerUnit', 'Gross income per unit')}: ${formatCurrencyAmountPlain(Number(provenance.gross_income_per_unit.amount), provenance.gross_income_per_unit.code, {minFraction: 0, maxFraction: 6})}`);
        }
        lines.push(periodLine(provenance));
        lines.push(...fxLines(provenance));
        return lines.join('\n');
    }

    function unavailableTooltip(reason: YieldOnCostReason | null, provenance: Provenance): string {
        const lines = [label('dashboard.yieldOnCostUnavailable', 'Yield on Cost unavailable')];
        if (reason === 'missing_fx' && provenance.issue_pair && provenance.issue_date) {
            lines.push(
                labelWithValues('dashboard.yieldOnCostReasons.missingFxDetails', 'The {pair} exchange rate required for the calculation is missing on {date}.', {
                    pair: formatFxPair(provenance.issue_pair),
                    date: formatDate(provenance.issue_date),
                }),
            );
            return lines.join('\n');
        }
        lines.push(reasonLabel(reason));
        if (provenance.issue_date) lines.push(`${label('dashboard.yieldOnCostIssueDate', 'Payment date')}: ${formatDate(provenance.issue_date)}`);
        if (reason === 'insufficient_history' && provenance.first_pair_transaction_date) {
            lines.push(`${label('dashboard.yieldOnCostFirstTransaction', 'First transaction')}: ${formatDate(provenance.first_pair_transaction_date)}`);
        }
        lines.push(...fxLines(provenance));
        return lines.join('\n');
    }

    function noIncomeTooltip(provenance: Provenance): string {
        return [label('dashboard.yieldOnCostNoIncomeTitle', 'No income recorded'), label('dashboard.yieldOnCostNoIncome', 'No dividends or interest in the last year.'), periodLine(provenance)].join('\n');
    }

    let numericValue = $derived(Number(result.value));
    let availableText = $derived(`${(numericValue * 100).toFixed(2)}%`);
</script>

{#if result.status === 'available'}
    <Tooltip text={availableTooltip(result.provenance, numericValue)} position="top" maxWidth="360px" interactiveChild={true}>
        <button type="button" class="font-medium tabular-nums text-gray-700 dark:text-gray-200" aria-label={availableTooltip(result.provenance, numericValue)} data-testid="yield-on-cost-value">
            {availableText}
        </button>
    </Tooltip>
{:else if result.status === 'no_income'}
    <Tooltip text={noIncomeTooltip(result.provenance)} position="top" maxWidth="340px" interactiveChild={true}>
        <button type="button" class="font-medium tabular-nums text-gray-500 dark:text-gray-400" aria-label={noIncomeTooltip(result.provenance)} data-testid="yield-on-cost-no-income"> - </button>
    </Tooltip>
{:else if result.status === 'unavailable'}
    {@const tooltip = unavailableTooltip(result.reason, result.provenance)}
    <span class="inline-flex items-center justify-end gap-1 text-gray-500 dark:text-gray-400" data-testid="yield-on-cost-unavailable">
        <span aria-hidden="true">-</span>
        <Tooltip text={tooltip} position="top" maxWidth="360px" interactiveChild={true}>
            <button type="button" class="inline-flex text-amber-500 dark:text-amber-400" aria-label={tooltip} data-testid="yield-on-cost-info">
                <Info size={13} />
            </button>
        </Tooltip>
    </span>
{/if}
