<!--
  LotAnalysisFailedNotice — what a FAILED lots analysis means, and which transactions to fix (J-12, N81 option A).

  A FAILED analysis has no reliable lot: the FIFO replay of the quantities broke on some transactions. The panel then
  draws no lot visual and shows this notice instead: a plain explanation and, per blocking issue, the broker's name,
  the day, the message and a button to the transaction to fix.

  - The panel hands over only the blocking issues (`partitionLotIssues`); the rows are `buildFailureRows`.
  - The way in is `transaction_id` only, never `related_transaction_id` (a partner leg the user may not see).
  - `missing_quantity` is a lot quantity: written as the lots write one, and masked under privacy (D5′). The rows are
    derived, so they follow the privacy toggle in place.

  Svelte 5 runes, colour roles only, data-testid selectors.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {AlertCircle, ExternalLink} from 'lucide-svelte';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';
    import type {BrokerLike} from '$lib/utils/broker/brokerColors';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {formatExactDecimal} from '$lib/utils/core/formatFixed';
    import {maskableQuantity} from '$lib/utils/privacy/maskable';
    import {buildFailureRows} from './lotDataQualityHelpers';

    interface Props {
        /** The blocking issues of the analysis (flagged `fails_analysis`), already split from the banner's. */
        issues: DataQualityIssue[];
        /** The panel's broker list: names each issue's broker. */
        brokers: ReadonlyArray<BrokerLike>;
        /** Open a transaction in the transactions page. */
        onGotoTransaction: (transactionId: number) => void;
    }

    let {issues, brokers, onGotoTransaction}: Props = $props();

    /** A lot quantity: the lots' pattern (LotCustodyModal), masked under privacy. */
    function formatQuantity(raw: unknown): string {
        if (typeof raw !== 'string' && typeof raw !== 'number') return String(raw);
        return maskableQuantity(formatExactDecimal(raw, {minFrac: 0, maxFrac: 10}));
    }

    let rows = $derived(buildFailureRows(issues, brokers, formatQuantity));
</script>

<div class="rounded-lg border border-lf-danger-line bg-lf-danger-soft px-4 py-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="lots-analysis-panel-failed">
    <div class="flex items-start gap-2">
        <AlertCircle size={16} class="mt-0.5 shrink-0" />
        <p class="min-w-0" data-testid="lots-analysis-failed-explanation">{$_('brokers.lots.analysisFailed')}</p>
    </div>

    {#if rows.length > 0}
        <p class="mt-3 ml-6 text-xs font-medium">{$_('brokers.lots.analysisFailedFix')}</p>
        <ul class="mt-1.5 ml-6 flex flex-col gap-2" data-testid="lots-analysis-failed-list">
            {#each rows as row (row.key)}
                <li class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs" data-testid="lots-analysis-failed-row-{row.code}-{row.transactionId ?? 'none'}">
                    {#if row.transactionDate}
                        <span class="font-medium tabular-nums" data-testid="lots-analysis-failed-date">{formatDay(row.transactionDate)}</span>
                        <span aria-hidden="true">·</span>
                    {/if}
                    <span class="font-medium" data-testid="lots-analysis-failed-broker">{row.brokerName}</span>
                    <span aria-hidden="true">—</span>
                    <span class="min-w-0" data-testid="lots-analysis-failed-message">{$_(row.messageKey, {values: row.messageParams})}</span>
                    {#if row.transactionId != null}
                        {@const transactionId = row.transactionId}
                        <button
                            type="button"
                            class="inline-flex items-center gap-1 rounded font-medium underline underline-offset-2 hover:no-underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                            onclick={() => onGotoTransaction(transactionId)}
                            data-testid="lots-analysis-failed-goto-{transactionId}"
                        >
                            <ExternalLink size={12} class="shrink-0" />
                            {$_('brokers.lots.modal.goToTransaction')}
                        </button>
                    {/if}
                </li>
            {/each}
        </ul>
    {/if}
</div>
