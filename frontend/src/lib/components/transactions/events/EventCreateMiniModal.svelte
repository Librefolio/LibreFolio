<!--
  EventCreateMiniModal.svelte — Svelte 5

  Minimal overlay modal for creating an asset event inline from the transaction form.
  Uses ModalBase for consistent styling, SingleDatePicker for date, InfoBanner for errors.
  Same API as AssetDataEditorSection (upsert_events_bulk).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {getEventTypeOptions, EVENT_TYPES_TX_COMPATIBLE} from '$lib/utils/eventTypes';
    import {getCurrencyInfo} from '$lib/stores/currencyStore';
    import {toasts} from '$lib/stores/toastStore.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {X} from 'lucide-svelte';

    interface Props {
        open: boolean;
        assetId: number;
        assetName: string;
        assetCurrency: string;
        defaultDate: string;
        /** Pre-fill amount from form cash (suggestion) */
        suggestedAmount?: string;
        /** Pre-set type from form transaction type */
        defaultEventType?: string;
        zIndex?: number;
        oncreated?: (eventId: number) => void;
        onclose?: () => void;
    }

    let {open, assetId, assetName, assetCurrency, defaultDate, suggestedAmount = '', defaultEventType = 'DIVIDEND', zIndex = 60, oncreated, onclose}: Props = $props();

    // Map transaction type to event type
    const TX_TO_EVENT_TYPE: Record<string, string> = {
        DIVIDEND: 'DIVIDEND',
        INTEREST: 'INTEREST',
    };

    function resolveDefaultEventType(txType: string): string {
        return TX_TO_EVENT_TYPE[txType] ?? 'DIVIDEND';
    }

    // Form state
    let eventType = $state('DIVIDEND');
    let eventDate = $state('');
    let eventAmount = $state('');
    let eventNotes = $state('');
    let saving = $state(false);
    let error = $state('');
    let confirmDiscardOpen = $state(false);
    let userTouched = $state(false);
    let initialAmount = $state('');

    // Track if form is dirty — only if user actively changed something
    let isDirty = $derived(userTouched && (eventNotes !== '' || eventType !== resolveDefaultEventType(defaultEventType) || eventDate !== defaultDate || eventAmount !== initialAmount));

    // Delta days between event date and form date
    let deltaDays = $derived.by(() => {
        if (!eventDate || !defaultDate) return null;
        const d1 = new Date(eventDate);
        const d2 = new Date(defaultDate);
        const diff = Math.round((d1.getTime() - d2.getTime()) / (1000 * 60 * 60 * 24));
        return diff;
    });

    // Format amount on blur to 2 decimals
    function formatAmount() {
        const n = parseFloat(eventAmount);
        if (!isNaN(n) && n >= 0) {
            eventAmount = n.toFixed(2);
        }
    }

    // Reset form when modal opens
    $effect(() => {
        if (open) {
            eventType = resolveDefaultEventType(defaultEventType);
            eventDate = defaultDate;
            const amt = parseFloat(suggestedAmount || '');
            const formatted = !isNaN(amt) && amt > 0 ? amt.toFixed(2) : '';
            eventAmount = formatted;
            initialAmount = formatted;
            eventNotes = '';
            error = '';
            saving = false;
            userTouched = false;
        }
    });

    const typeOptions = $derived(
        getEventTypeOptions($t, EVENT_TYPES_TX_COMPATIBLE).map((o) => ({
            value: o.value,
            label: o.label,
            icon: o.emoji,
        })),
    );
    const currencyInfo = $derived(getCurrencyInfo(assetCurrency));

    function requestClose() {
        if (saving) return;
        if (isDirty) {
            confirmDiscardOpen = true;
            return;
        }
        onclose?.();
    }

    function confirmDiscard() {
        confirmDiscardOpen = false;
        onclose?.();
    }

    async function handleSubmit() {
        error = '';
        const amount = parseFloat(eventAmount);
        if (!amount || amount <= 0) {
            error = $t('transactions.form.eventCreateAmountRequired') || 'Amount required';
            return;
        }
        if (!eventDate) {
            error = $t('transactions.form.eventCreateDateRequired') || 'Date required';
            return;
        }

        saving = true;
        try {
            await zodiosApi.upsert_events_bulk_api_v1_assets_events_post([
                {
                    asset_id: assetId,
                    events: [
                        {
                            date: eventDate,
                            type: eventType,
                            value: {code: assetCurrency, amount},
                            notes: eventNotes || undefined,
                        },
                    ],
                },
            ]);

            // After upsert, fetch the event to get its ID
            const resp = (await zodiosApi.query_events_bulk_api_v1_assets_events_query_post([{asset_id: assetId, date_range: {start: eventDate, end: eventDate}}])) as any;
            const items = resp?.items?.[0]?.events ?? [];
            const created = items.find((e: any) => e.type === eventType && e.date === eventDate);

            // Build descriptive toast
            const typeLabel = $t(`assetDetail.eventType.${eventType}`) || eventType;
            const emoji = typeOptions.find((o) => o.value === eventType)?.icon || '📋';
            const fmtDate = new Date(eventDate + 'T00:00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'});
            const amt = parseFloat(eventAmount);
            const fmtAmt = !isNaN(amt) ? `${amt.toFixed(2)} ${assetCurrency}` : '';
            const toastMsg = `${emoji} ${typeLabel} · ${fmtDate}${fmtAmt ? ` · ${fmtAmt}` : ''}${eventNotes ? ` · 📝 ${eventNotes}` : ''}`;
            toasts.success(toastMsg);
            if (created?.id) {
                oncreated?.(created.id);
            }
            onclose?.();
        } catch (err: any) {
            const msg = err?.response?.data?.detail || err?.message || 'Error creating event';
            error = msg;
        } finally {
            saving = false;
        }
    }
</script>

<ModalBase {open} maxWidth="sm" onRequestClose={requestClose} {zIndex} testId="event-create-mini-modal">
    <div class="flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-gray-100 dark:border-slate-700 shrink-0">
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                ✨ {$t('transactions.form.eventCreateTitle', {values: {asset: assetName}})}
            </h2>
            <button class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50" disabled={saving} onclick={requestClose} type="button">
                <X size={20} />
            </button>
        </div>

        <!-- Body -->
        <div class="px-5 py-4 space-y-4">
            <!-- Error banner -->
            {#if error}
                <InfoBanner variant="error" message={error} dismissible ondismiss={() => (error = '')} />
            {/if}

            <!-- Type -->
            <div class="space-y-1.5">
                <span class="block text-xs font-medium text-gray-500 dark:text-gray-400">
                    {$t('common.type')}
                </span>
                <SimpleSelect
                    value={eventType}
                    options={typeOptions}
                    testId="event-create-type"
                    onchange={(v) => {
                        eventType = v;
                        userTouched = true;
                    }}
                />
            </div>

            <!-- Date -->
            <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                    <span class="block text-xs font-medium text-gray-500 dark:text-gray-400">
                        {$t('common.date')}
                    </span>
                    {#if deltaDays != null && deltaDays !== 0}
                        <span class="text-xs font-mono text-amber-500">Δ{deltaDays > 0 ? '+' : ''}{deltaDays}d</span>
                    {/if}
                </div>
                <SingleDatePicker
                    value={eventDate}
                    label=""
                    inputStyle={true}
                    allowFuture={false}
                    onchange={(d) => {
                        eventDate = d;
                        userTouched = true;
                    }}
                />
            </div>

            <!-- Amount -->
            <div class="space-y-1.5">
                <label for="event-amount" class="block text-xs font-medium text-gray-500 dark:text-gray-400">
                    {$t('transactions.fields.amount')}
                </label>
                <div class="flex items-center gap-2">
                    <input
                        id="event-amount"
                        type="number"
                        step="any"
                        min="0"
                        class="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm font-mono text-right focus:ring-2 focus:ring-libre-green/30 focus:border-libre-green [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none [-moz-appearance:textfield]"
                        bind:value={eventAmount}
                        oninput={() => (userTouched = true)}
                        onblur={formatAmount}
                        placeholder="0.00"
                        data-testid="event-create-amount"
                    />
                    <span class="text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        {currencyInfo.symbol}
                        {currencyInfo.flag_emoji}
                        {assetCurrency}
                    </span>
                </div>
            </div>

            <!-- Notes -->
            <div class="space-y-1.5">
                <label for="event-notes" class="block text-xs font-medium text-gray-500 dark:text-gray-400">
                    {$t('common.notes')}
                </label>
                <input
                    id="event-notes"
                    type="text"
                    class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm focus:ring-2 focus:ring-libre-green/30 focus:border-libre-green"
                    bind:value={eventNotes}
                    oninput={() => (userTouched = true)}
                    placeholder={$t('common.optional')}
                    data-testid="event-create-notes"
                />
            </div>
        </div>

        <!-- Footer -->
        <div class="flex justify-end gap-2 px-5 py-3 border-t border-gray-100 dark:border-slate-700 shrink-0">
            <button type="button" class="px-3 py-1.5 text-sm bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors" disabled={saving} onclick={requestClose}>
                {$t('common.cancel')}
            </button>
            <button type="button" class="px-3 py-1.5 text-sm bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed" disabled={saving || !eventAmount} onclick={handleSubmit} data-testid="event-create-submit">
                {saving ? $t('common.saving') : $t('common.create')}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Discard confirmation -->
<ConfirmModal
    open={confirmDiscardOpen}
    title={$t('common.discardChanges') || 'Discard changes?'}
    message={$t('common.discardChangesMessage') || 'You have unsaved changes. Are you sure you want to close?'}
    confirmText={$t('common.discard') || 'Discard'}
    warning
    zIndex={zIndex + 10}
    onConfirm={confirmDiscard}
    onCancel={() => (confirmDiscardOpen = false)}
/>
