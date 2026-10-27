<!--
  EventCreateMiniModal.svelte — Svelte 5

  Minimal overlay modal for creating an asset event inline from the transaction form.
  Uses ModalBase for consistent styling, SingleDatePicker for date, InfoBanner for errors.
  Same API as AssetDataEditorSection (upsert_events_bulk).
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {getEventTypeOptions, eventTypesForTx, defaultEventTypeForTx} from './eventTypes';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';
    import {decimalArrowStep, normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import ConfirmModal from '$lib/components/ui/modals/ConfirmModal.svelte';
    import SingleDatePicker from '$lib/components/ui/date/SingleDatePicker.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import EventExistsPanel from './EventExistsPanel.svelte';
    import {eventSaveErrorMessage, existingAmountText, existingEvents, type ExistingEvent} from './eventSaveError';
    import {X} from 'lucide-svelte';
    import {formatExactDecimal} from '$lib/utils/core/formatFixed';
    import {uiLocale} from '$lib/stores/app/uiLocale';

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

    // The event type a transaction type starts with: a split for an adjustment, the event of the same name for an interest.
    function resolveDefaultEventType(txType: string): string {
        return defaultEventTypeForTx(txType);
    }

    // Form state
    let eventType = $state('DIVIDEND');
    /** A SPLIT's value is its ratio (new shares per old share): a plain number, no currency, never padded to two decimals. */
    let isRatio = $derived(eventType === 'SPLIT');
    let eventDate = $state('');
    let eventAmount = $state('');
    let eventNotes = $state('');
    let saving = $state(false);
    let error = $state('');
    let confirmDiscardOpen = $state(false);
    let userTouched = $state(false);
    let initialAmount = $state('');
    // Decision 20: «+ New event» never overwrites. On EVENT_EXISTS the panel shows the events already there.
    let existing = $state<ExistingEvent[] | null>(null);
    // «Edit this»: the form edits that manual event, saved by its id.
    let editingId = $state<number | null>(null);

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

    /** The decimals an event value keeps (``AssetEvent.value``, ``Numeric(18, 6)``): past them the backend refuses
     *  (EVENT_TOO_MANY_DIGITS), never rounds (C-97a). */
    const EVENT_VALUE_DECIMALS = 6;

    /** ``text`` as a plain unsigned decimal (``normalizeDecimalInput``: the locale's punctuation read), or null. */
    function plainAmount(text: string): string | null {
        const raw = normalizeDecimalInput(text.trim());
        return /^(?:\d+(?:\.\d*)?|\.\d+)$/.test(raw) ? raw : null;
    }

    /** Two decimals at least, the typed ones kept as they are: ``1`` → ``1.00``, ``0.2345`` stays. */
    function withTwoDecimals(plain: string): string {
        const [integer, fraction = ''] = plain.split('.');
        return `${integer || '0'}.${fraction.padEnd(2, '0')}`;
    }

    /** The decimals of a plain amount, trailing zeros not counted: what the backend counts. */
    function amountDecimals(plain: string): number {
        return (plain.split('.')[1] ?? '').replace(/0+$/, '').length;
    }

    // C-97b: past six decimals the field says why, and the event is not sent; the value stays as typed.
    let amountOverBudget = $derived.by(() => {
        const plain = plainAmount(eventAmount);
        return plain !== null && amountDecimals(plain) > EVENT_VALUE_DECIMALS;
    });

    // Format amount on blur: two decimals at least, the typed ones kept — never rounded nor cut (C-97b), so an event
    // edited here keeps a per-share amount with more (decision 20, «Edit this»), and one past six is said, not changed.
    function formatAmount() {
        if (isRatio) return;
        const plain = plainAmount(eventAmount);
        if (plain !== null) eventAmount = withTwoDecimals(plain);
    }

    // Reset form when modal opens
    $effect(() => {
        if (open) {
            eventType = resolveDefaultEventType(defaultEventType);
            eventDate = defaultDate;
            // The suggestion whole, two decimals at least (C-97b): 0.2345 stays 0.2345.
            const suggested = plainAmount(suggestedAmount || '');
            const formatted = suggested !== null && /[1-9]/.test(suggested) ? (eventType === 'SPLIT' ? suggested : withTwoDecimals(suggested)) : '';
            eventAmount = formatted;
            initialAmount = formatted;
            eventNotes = '';
            error = '';
            saving = false;
            userTouched = false;
            existing = null;
            editingId = null;
        }
    });

    const typeOptions = $derived(
        getEventTypeOptions($t, eventTypesForTx(defaultEventType)).map((o) => ({
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
        // Sent as its digits, never through a float (C-97b).
        const amount = plainAmount(eventAmount);
        if (amount === null || !/[1-9]/.test(amount)) {
            error = $t('transactions.form.eventCreateAmountRequired') || 'Amount required';
            return;
        }
        if (amountDecimals(amount) > EVENT_VALUE_DECIMALS) return;
        if (!eventDate) {
            error = $t('transactions.form.eventCreateDateRequired') || 'Date required';
            return;
        }

        saving = true;
        try {
            const resp = await zodiosApi.upsert_events_bulk_api_v1_assets_events_post([
                {
                    asset_id: assetId,
                    // A new event never overwrites another (decision 20); an edit names the event it changes.
                    mode: editingId === null ? 'create' : 'upsert',
                    events: [
                        {
                            id: editingId ?? undefined,
                            date: eventDate,
                            type: eventType,
                            value: {code: assetCurrency, amount},
                            notes: eventNotes || undefined,
                        },
                    ],
                },
            ]);

            // The event the save wrote, by its id (I-10 S4): re-reading the day by type could find another one.
            const savedId = resp.results?.[0]?.event_ids?.[0] ?? editingId;

            // Build descriptive toast
            const typeLabel = $t(`assetDetail.eventType.${eventType}`) || eventType;
            const emoji = typeOptions.find((o) => o.value === eventType)?.icon || '📋';
            const fmtDate = new Date(eventDate + 'T00:00:00').toLocaleDateString(uiLocale(), {day: 'numeric', month: 'short', year: 'numeric'});
            // C-97c: the value as saved, exact, 2 to 6 decimals (an event value keeps 6), never through a float at 2.
            const amountText = normalizeDecimalInput(eventAmount);
            const fmtAmt = !isNaN(parseFloat(amountText)) ? `${formatExactDecimal(amountText, {minFrac: 2, maxFrac: 6})} ${assetCurrency}` : '';
            const toastMsg = `${emoji} ${typeLabel} · ${fmtDate}${fmtAmt ? ` · ${fmtAmt}` : ''}${eventNotes ? ` · 📝 ${eventNotes}` : ''}`;
            toasts.success(toastMsg);
            if (savedId) {
                oncreated?.(savedId);
            }
            onclose?.();
        } catch (err: unknown) {
            const found = existingEvents(err);
            if (found) {
                existing = found;
                return;
            }
            error = eventSaveErrorMessage(err, $t, [{date: eventDate, type: eventType}], (type) => $t(`assetDetail.eventType.${type}`) || type);
        } finally {
            saving = false;
        }
    }

    /** «Use this»: link the event already there, write nothing. */
    function useExisting(event: ExistingEvent) {
        existing = null;
        oncreated?.(event.id);
        onclose?.();
    }

    /** «Edit this»: the form now edits that manual event, with its own values, and saves it by id. */
    function editExisting(event: ExistingEvent) {
        editingId = event.id;
        eventType = event.type;
        eventDate = event.date;
        eventAmount = existingAmountText(event.value.amount);
        eventNotes = event.notes ?? '';
        existing = null;
        error = '';
    }
</script>

<ModalBase {open} maxWidth="sm" onRequestClose={requestClose} {zIndex} testId="event-create-mini-modal">
    <div class="flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between p-5 pb-4 border-b border-lf-subtle shrink-0">
            <h2 class="text-lg font-semibold text-lf-primary">
                {#if editingId === null}
                    ✨ {$t('transactions.form.eventCreateTitle', {values: {asset: assetName}})}
                {:else}
                    ✏️ {$t('transactions.form.eventEditTitle', {values: {asset: assetName}})}
                {/if}
            </h2>
            <button class="p-2 text-lf-muted hover:text-lf-secondary hover:bg-lf-hover rounded-lg transition-colors disabled:opacity-50" disabled={saving} onclick={requestClose} type="button">
                <X size={20} />
            </button>
        </div>

        <!-- Body -->
        <div class="px-5 py-4 space-y-4">
            <!-- Error banner -->
            {#if error}
                <InfoBanner variant="error" message={error} dismissible ondismiss={() => (error = '')} />
            {/if}

            {#if existing}
                <EventExistsPanel events={existing} onuse={useExisting} onedit={editExisting} oncancel={() => (existing = null)} />
            {:else}
                <!-- Type -->
                <div class="space-y-1.5">
                    <span class="block text-xs font-medium text-lf-muted">
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
                        <span class="block text-xs font-medium text-lf-muted">
                            {$t('common.date')}
                        </span>
                        {#if deltaDays != null && deltaDays !== 0}
                            <span class="text-xs font-mono text-lf-warning">Δ{deltaDays > 0 ? '+' : ''}{deltaDays}d</span>
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
                    <label for="event-amount" class="block text-xs font-medium text-lf-muted">
                        {isRatio ? $t('transactions.bulk.possibleSplit.ratioLabel') : $t('transactions.fields.amount')}
                    </label>
                    <div class="flex items-center gap-2">
                        <input
                            id="event-amount"
                            type="text"
                            inputmode="decimal"
                            class="flex-1 rounded-lg border border-lf-input hover:border-lf-input-hover bg-lf-field text-lf-primary placeholder:text-lf-placeholder px-3 py-2 text-sm font-mono text-right focus:ring-2 focus:ring-lf-focus/30 focus:border-lf-focus aria-invalid:border-lf-danger [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none [-moz-appearance:textfield]"
                            aria-invalid={amountOverBudget}
                            bind:value={eventAmount}
                            oninput={() => (userTouched = true)}
                            onkeydown={(e) => {
                                const stepped = decimalArrowStep(e, eventAmount, 0.01);
                                if (stepped === null) return;
                                eventAmount = stepped;
                                userTouched = true;
                            }}
                            onblur={formatAmount}
                            placeholder={isRatio ? '2' : '0.00'}
                            data-testid="event-create-amount"
                        />
                        {#if !isRatio}
                            <span class="text-sm text-lf-muted whitespace-nowrap">
                                {currencyInfo.symbol}
                                {currencyInfo.flag_emoji}
                                {assetCurrency}
                            </span>
                        {/if}
                    </div>
                    {#if isRatio}
                        <p class="text-xs text-lf-muted" data-testid="event-create-ratio-hint">{$t('transactions.bulk.possibleSplit.ratioHint')}</p>
                    {/if}
                    {#if amountOverBudget}
                        <p class="text-xs text-lf-danger" data-testid="event-create-amount-digits-error" data-max={EVENT_VALUE_DECIMALS}>
                            {$t('common.decimalPlacesExceeded', {values: {max: EVENT_VALUE_DECIMALS}})}
                        </p>
                    {/if}
                </div>

                <!-- Notes -->
                <div class="space-y-1.5">
                    <label for="event-notes" class="block text-xs font-medium text-lf-muted">
                        {$t('common.notes')}
                    </label>
                    <input
                        id="event-notes"
                        type="text"
                        class="w-full rounded-lg border border-lf-input hover:border-lf-input-hover bg-lf-field text-lf-primary placeholder:text-lf-placeholder px-3 py-2 text-sm focus:ring-2 focus:ring-lf-focus/30 focus:border-lf-focus"
                        bind:value={eventNotes}
                        oninput={() => (userTouched = true)}
                        placeholder={$t('common.optional')}
                        data-testid="event-create-notes"
                    />
                </div>
            {/if}
        </div>

        <!-- Footer -->
        <div class="flex justify-end gap-2 px-5 py-3 border-t border-lf-subtle shrink-0">
            <button type="button" class="px-3 py-1.5 text-sm bg-lf-panel text-lf-secondary rounded-lg hover:bg-lf-neutral transition-colors" disabled={saving} onclick={requestClose}>
                {$t('common.cancel')}
            </button>
            <button
                type="button"
                class="px-3 py-1.5 text-sm bg-lf-action text-lf-on-action rounded-lg hover:bg-lf-action-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={saving || !eventAmount || existing !== null || amountOverBudget}
                onclick={handleSubmit}
                data-testid="event-create-submit"
            >
                {saving ? $t('common.saving') : editingId === null ? $t('common.create') : $t('common.save')}
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
