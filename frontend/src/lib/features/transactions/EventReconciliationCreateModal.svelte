<!--
  EventReconciliationCreateModal.svelte — create the events the «Relink events» window finds missing (FB-19).

  Opened from the window with the rows that have no event that day. Rows of the same asset, day and type share one event, so the
  dialog lists ONE line per event to create, with the transactions it serves. Each line asks the event's type (a split or a price
  adjustment for an adjustment, a fixed one otherwise) and its value, in the asset's currency; the value starts from the
  transaction's cash, as the transaction form suggests it. Create sends ONE request (all or nothing: `createMissingEvents`) and
  tells the window (`oncreated`): the window reads its list again, where the rows now have their event, to be linked as any other.
  Nothing is linked here.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {untrack} from 'svelte';
    import {Plus, X} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {getAssetInfo, assetStoreVersion} from '$lib/stores/reference/assetStore';
    import {formatDay} from '$lib/utils/core/formatAxisDate';
    import {getEventTypeEmoji} from '$lib/features/transactions/transactionTypeStore';
    import {eventSaveErrorMessage} from './events/eventSaveError';
    import {createMissingEvents, eventTypesOfRow, plainEventAmount, suggestedEventAmount, type NewEventEntry, type ReconciliationRow} from './eventReconciliation';

    interface Props {
        open: boolean;
        /** The rows that have no event: the dialog creates what they miss. */
        rows: readonly ReconciliationRow[];
        zIndex?: number;
        onclose?: () => void;
        /** Called after the events were created, so the window reads its list again. */
        oncreated?: () => void;
    }

    let {open, rows, zIndex = 60, onclose, oncreated}: Props = $props();

    /** An event to create, for the rows that share its asset, day and type. */
    interface Line {
        key: string;
        /** The first transaction of the group: the id the line is named by. */
        id: number;
        assetId: number;
        date: string;
        type: string;
        transactions: number;
        row: ReconciliationRow;
    }

    let lines = $derived.by(() => {
        const byKey = new Map<string, Line>();
        for (const row of rows) {
            const key = `${row.assetId}|${row.date}|${row.type}`;
            const held = byKey.get(key);
            if (held) held.transactions += 1;
            else byKey.set(key, {key, id: row.transactionId, assetId: row.assetId, date: row.date, type: row.type, transactions: 1, row});
        }
        return [...byKey.values()];
    });

    /** What the user chose per line: the event's type and the value's text. */
    let chosenType = $state<Record<string, string>>({});
    let amounts = $state<Record<string, string>>({});
    let saving = $state(false);
    let error = $state('');

    function assetCurrency(assetId: number): string | undefined {
        void $assetStoreVersion;
        return getAssetInfo(assetId)?.currency;
    }

    function assetName(assetId: number): string {
        void $assetStoreVersion;
        return getAssetInfo(assetId)?.display_name ?? `#${assetId}`;
    }

    // Opening starts every line from its suggestion. Only the opening: a cache that fills later (the assets' currencies) must not
    // write over a value the user has typed
    $effect(() => {
        if (!open) return;
        untrack(() => {
            const types: Record<string, string> = {};
            const values: Record<string, string> = {};
            for (const line of lines) {
                types[line.key] = eventTypesOfRow(line.row)[0];
                values[line.key] = suggestedEventAmount(line.row, assetCurrency(line.assetId));
            }
            chosenType = types;
            amounts = values;
            error = '';
        });
    });

    const typeLabel = (type: string): string => $t(`assetDetail.eventType.${type}`) || type;

    /** The lines that cannot be sent yet: no value, or one that is not a plain amount of at most six decimals. */
    let incomplete = $derived(lines.filter((line) => plainEventAmount(amounts[line.key] ?? '') === null || !assetCurrency(line.assetId)));

    async function create() {
        if (saving || incomplete.length > 0 || lines.length === 0) return;
        const entries: NewEventEntry[] = lines.map((line) => ({row: line.row, type: chosenType[line.key] ?? eventTypesOfRow(line.row)[0], amount: plainEventAmount(amounts[line.key] ?? '') as string, currency: assetCurrency(line.assetId) as string}));
        saving = true;
        error = '';
        try {
            await createMissingEvents(entries);
            oncreated?.();
        } catch (err: unknown) {
            console.error('[event-reconciliation] the events could not be created', err);
            error = eventSaveErrorMessage(
                err,
                $t,
                entries.map((entry) => ({date: entry.row.date, type: entry.type})),
                typeLabel,
                (iso) => formatDay(iso),
            );
        } finally {
            saving = false;
        }
    }
</script>

{#if open}
    <ModalBase {open} {zIndex} maxWidth="3xl" onRequestClose={() => !saving && onclose?.()} testId="event-reconciliation-create-modal" labelledBy="event-reconciliation-create-title">
        <div class="flex items-center gap-3 px-5 py-4 border-b border-lf-subtle">
            <Plus class="text-lf-link flex-shrink-0" size={20} />
            <h2 id="event-reconciliation-create-title" class="text-base font-semibold text-lf-primary">{$t('transactions.reconcile.createTitle')}</h2>
            <button type="button" class="ml-auto p-1 rounded text-lf-muted hover:bg-lf-hover transition-colors disabled:opacity-50" disabled={saving} onclick={() => onclose?.()} aria-label={$t('transactions.reconcile.close')} data-testid="event-reconciliation-create-close">
                <X size={18} />
            </button>
        </div>

        <div class="px-5 py-4 space-y-3 text-sm overflow-y-auto">
            <p class="text-lf-secondary">{$t('transactions.reconcile.createIntro')}</p>
            {#if error}
                <div data-testid="event-reconciliation-create-error">
                    <InfoBanner variant="error" message={error} />
                </div>
            {/if}
            <ul class="divide-y divide-lf-subtle border border-lf-subtle rounded-md">
                {#each lines as line (line.key)}
                    {@const currency = assetCurrency(line.assetId)}
                    <li class="flex flex-wrap items-center gap-3 px-3 py-2" data-testid="event-reconciliation-create-row-{line.id}" data-transactions={line.transactions}>
                        <div class="min-w-0 flex-1">
                            <div class="truncate text-lf-primary">{assetName(line.assetId)}</div>
                            <div class="text-xs text-lf-muted">
                                {formatDay(line.date)}
                                {#if line.transactions > 1}
                                    · {$t('transactions.reconcile.createServes', {values: {n: line.transactions}})}{/if}
                            </div>
                        </div>
                        <div class="w-52">
                            {#if eventTypesOfRow(line.row).length > 1}
                                <SimpleSelect
                                    compact
                                    value={chosenType[line.key] ?? eventTypesOfRow(line.row)[0]}
                                    options={eventTypesOfRow(line.row).map((type) => ({value: type, label: `${getEventTypeEmoji(type)} ${typeLabel(type)}`}))}
                                    testId="event-reconciliation-create-type-{line.id}"
                                    onchange={(value) => (chosenType = {...chosenType, [line.key]: value})}
                                />
                            {:else}
                                <span class="text-lf-primary" data-testid="event-reconciliation-create-type-{line.id}" data-event-type={eventTypesOfRow(line.row)[0]}>{getEventTypeEmoji(eventTypesOfRow(line.row)[0])} {typeLabel(eventTypesOfRow(line.row)[0])}</span>
                            {/if}
                        </div>
                        <label class="flex items-center gap-1.5">
                            <input
                                type="text"
                                inputmode="decimal"
                                class="w-28 rounded-lg border border-lf-input hover:border-lf-input-hover bg-lf-field text-lf-primary px-2 py-1.5 text-sm font-mono text-right focus:ring-2 focus:ring-lf-focus/30 focus:border-lf-focus"
                                value={amounts[line.key] ?? ''}
                                oninput={(event) => (amounts = {...amounts, [line.key]: event.currentTarget.value})}
                                aria-label={$t('transactions.reconcile.createValue')}
                                data-testid="event-reconciliation-create-amount-{line.id}"
                            />
                            <span class="text-xs text-lf-muted">{currency ?? ''}</span>
                        </label>
                    </li>
                {/each}
            </ul>
            {#if incomplete.length > 0}
                <p class="text-xs text-lf-warning" data-testid="event-reconciliation-create-hint">{$t('transactions.reconcile.createHint')}</p>
            {/if}
        </div>

        <div class="flex justify-end gap-2 px-5 py-3 border-t border-lf-subtle bg-lf-panel">
            <button type="button" class="px-4 py-2 text-sm rounded-lg bg-lf-panel text-lf-secondary hover:bg-lf-neutral transition-colors disabled:opacity-50" disabled={saving} onclick={() => onclose?.()} data-testid="event-reconciliation-create-cancel">
                {$t('common.cancel')}
            </button>
            <button
                type="button"
                class="px-4 py-2 text-sm rounded-lg bg-lf-action text-lf-on-action hover:bg-lf-action-hover transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={saving || incomplete.length > 0 || lines.length === 0}
                onclick={create}
                data-testid="event-reconciliation-create-confirm"
            >
                {$t('transactions.reconcile.createConfirm', {values: {n: lines.length}})}
            </button>
        </div>
    </ModalBase>
{/if}
