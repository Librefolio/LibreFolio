<!--
  EventReconciliationChooseModal.svelte — «Choose the event» over «Relink events» (plan 77, SEL-C; Q-SEL-5, Q-SEL-14).

  A row with several events of the right type that day is never guessed: this small window lists them (the `candidates`
  the server already sends), each with its type, its value and whether it is automatic or entered by hand. Nothing is
  chosen to start; «Link» turns on once one is chosen and links it through the same atomic commit as «Link»
  (`linkChosenEvent`). A refusal links nothing: the window stays open and says so.
  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Link2, ListChecks, X} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {sanitizeHtml} from '$lib/utils/core/sanitizeHtml';
    import {getEventTypeEmoji, typesVersion} from '$lib/features/transactions/transactionTypeStore';
    import {eventValueHtml, linkChosenEvent, type ReconciliationRow} from './eventReconciliation';

    interface Props {
        /** The row to choose an event for (none: closed). */
        row: ReconciliationRow | null;
        assetName: string;
        brokerName: string;
        /** The transaction's movement, as the window draws it (HTML). */
        movementHtml: string;
        zIndex?: number;
        onclose: () => void;
        /** The chosen event was linked. */
        onlinked: (row: ReconciliationRow) => void;
    }

    let {row, assetName, brokerName, movementHtml, zIndex = 60, onclose, onlinked}: Props = $props();

    let chosen = $state<number | null>(null);
    let linking = $state(false);
    let failed = $state(false);

    // A new row starts with nothing chosen.
    $effect(() => {
        void row?.transactionId;
        chosen = null;
        linking = false;
        failed = false;
    });

    function typeLabel(type: string): string {
        void $typesVersion;
        return `${getEventTypeEmoji(type)} ${$t(`assetDetail.eventType.${type}`) || type}`;
    }

    async function link() {
        if (!row || chosen === null || linking) return;
        linking = true;
        failed = false;
        try {
            const outcome = await linkChosenEvent(row, chosen);
            if (!outcome.linked) {
                failed = true;
                return;
            }
            onlinked(row);
        } finally {
            linking = false;
        }
    }
</script>

{#if row}
    <ModalBase open={true} {zIndex} maxWidth="lg" onRequestClose={onclose} testId="event-reconciliation-choose-modal" labelledBy="event-reconciliation-choose-title" trapFocus restoreFocus>
        <div class="flex items-center gap-3 px-5 py-4 border-b border-lf-subtle text-lf-primary">
            <ListChecks class="flex-shrink-0" size={20} />
            <h2 id="event-reconciliation-choose-title" class="text-base font-semibold">{$t('transactions.reconcile.chooseTitle')}</h2>
            <button type="button" class="ml-auto p-1 rounded text-lf-muted hover:bg-lf-hover transition-colors" onclick={onclose} aria-label={$t('common.close')} data-testid="event-reconciliation-choose-close">
                <X size={18} />
            </button>
        </div>

        <div class="px-5 py-4 space-y-3 text-sm text-lf-primary">
            <div class="rounded-lg bg-lf-panel px-3 py-2.5">
                <div><span class="font-semibold">{assetName}</span> · {brokerName} · {formatDay(row.date)}</div>
                <div class="mt-0.5">{@html sanitizeHtml(movementHtml)}</div>
            </div>
            <p class="text-xs text-lf-secondary">{$t('transactions.reconcile.chooseIntro', {values: {n: row.candidates.length}})}</p>
            <fieldset class="space-y-2" data-testid="event-reconciliation-choose-options">
                <legend class="sr-only">{$t('transactions.reconcile.chooseTitle')}</legend>
                {#each row.candidates as candidate (candidate.id)}
                    <label
                        class="flex flex-wrap items-center gap-x-2.5 gap-y-1 px-3 py-2.5 rounded-lg border cursor-pointer transition-colors {chosen === candidate.id ? 'border-lf-checked bg-lf-selected' : 'border-lf-subtle bg-lf-card hover:bg-lf-hover'}"
                        data-testid="event-reconciliation-choose-option-{candidate.id}"
                        data-source={candidate.isAuto ? 'auto' : 'manual'}
                    >
                        <input type="radio" name="event-reconciliation-choose" class="accent-lf-checked" value={candidate.id} checked={chosen === candidate.id} onchange={() => (chosen = candidate.id)} />
                        <span data-event-type={candidate.type}>{typeLabel(candidate.type)} · {@html sanitizeHtml(eventValueHtml(candidate))}</span>
                        <span class="ml-auto text-xs text-lf-muted whitespace-nowrap">{candidate.isAuto ? $t('transactions.reconcile.sourceAuto') : $t('transactions.reconcile.sourceManual')}</span>
                    </label>
                {/each}
            </fieldset>
            {#if failed}
                <p class="text-lf-danger" data-testid="event-reconciliation-choose-error">{$t('transactions.reconcile.linkError')}</p>
            {/if}
        </div>

        <div class="flex justify-end gap-2 px-5 py-3 border-t border-lf-subtle bg-lf-panel">
            <button type="button" class="px-4 py-2 text-sm rounded-lg text-lf-secondary hover:bg-lf-hover transition-colors" onclick={onclose} data-testid="event-reconciliation-choose-cancel">{$t('common.cancel')}</button>
            <button
                type="button"
                class="inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={chosen === null || linking}
                onclick={link}
                data-testid="event-reconciliation-choose-confirm"
            >
                <Link2 size={15} />
                {$t('transactions.reconcile.link')}
            </button>
        </div>
    </ModalBase>
{/if}
