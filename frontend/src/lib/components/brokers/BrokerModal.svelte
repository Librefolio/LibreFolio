<script lang="ts">
    /**
     * BrokerModal - Modal wrapper for broker create/edit form
     */
    import {_} from '$lib/i18n';
    import {onDestroy} from 'svelte';
    import {AlertTriangle, X} from 'lucide-svelte';
    import BrokerForm from './BrokerForm.svelte';
    import {zodiosApi} from '$lib/api';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {extractErrorMessage, trySave} from '$lib/utils/trySave';
    import {toasts} from '$lib/stores/app/toastStore.svelte';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {mergeBrokers} from '$lib/stores/reference/brokerStore';
    import {getClientSessionGeneration, isClientSessionCurrent} from '$lib/stores/app/clientSession';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';

    interface Props {
        isOpen?: boolean;
        mode?: 'create' | 'edit';
        brokerId?: number | null;
        /** Z-index override for stacked modal contexts (e.g. opened from FormModal). */
        zIndex?: number;
        initialData?: {
            name?: string;
            description?: string | null;
            portal_url?: string | null;
            icon_url?: string | null;
            default_import_plugin?: string | null;
            allow_cash_overdraft?: boolean;
            allow_asset_shorting?: boolean;
            is_active?: boolean;
            opened_at?: string | null;
        };
        onclose?: () => void;
        oncreated?: (detail: {id: number}) => void;
        onupdated?: (detail: {id: number}) => void;
    }

    let {isOpen = false, mode = 'create', brokerId = null, zIndex = 50, initialData = {}, onclose, oncreated, onupdated}: Props = $props();

    let loading = $state(false);
    let error: string | null = $state(null);
    let formTouched = $state(false);
    let showDiscardConfirm = $state(false);
    let openingContext: string | null = null;
    let openingEpoch = 0;
    let alive = true;
    const brokerNameRecovery = 'To resolve this, rename the existing broker or choose a different name for the broker you are adding.';

    $effect(() => {
        const context = isOpen ? `${mode}:${brokerId ?? 'new'}` : null;
        if (context === openingContext) return;
        openingContext = context;
        openingEpoch++;
        error = null;
        formTouched = false;
        showDiscardConfirm = false;
        loading = false;
    });

    onDestroy(() => {
        alive = false;
        openingEpoch++;
    });

    function localizeDuplicateName(message: string, name: string): string | null {
        const suffix = `. ${brokerNameRecovery}`;
        const base = message.endsWith(suffix) ? message.slice(0, -suffix.length) : message;
        let localized: string;
        if (base === `You already have a broker named '${name}'`) {
            localized = $_('brokers.duplicateNameOwn', {values: {name}});
        } else if (base === `Broker with name '${name}' already exists` || base === 'A broker with that name already exists') {
            localized = $_('brokers.duplicateNameExists', {values: {name}});
        } else {
            const ownerPrefix = `Broker '${name}' already exists (owned by '`;
            if (!base.startsWith(ownerPrefix) || !base.endsWith("')")) return null;
            localized = $_('brokers.duplicateNameOwned', {values: {name, owner: base.slice(ownerPrefix.length, -2)}});
        }
        return `${localized} ${$_('brokers.duplicateNameRecovery')}`;
    }

    // Track if form has been modified
    function handleFormChange() {
        formTouched = true;
    }

    async function handleSubmit(
        event: CustomEvent<{
            name: string;
            description?: string;
            portal_url?: string;
            icon_url?: string;
            default_import_plugin?: string;
            allow_cash_overdraft: boolean;
            allow_asset_shorting: boolean;
            is_active: boolean;
            opened_at?: string;
            initial_balances?: Array<{code: string; amount: number}>;
        }>,
    ) {
        const sessionGeneration = getClientSessionGeneration();
        const epoch = openingEpoch;
        const isCurrent = () => alive && isOpen && epoch === openingEpoch && isClientSessionCurrent(sessionGeneration);
        loading = true;
        error = null;

        // I-bis #22 — route both create and update through ``trySave``
        // so HTTP failures (network, 4xx, 5xx) surface via a toast + keep
        // the modal open with ``formTouched`` preserved, instead of
        // closing silently with only a console.error.
        try {
            if (mode === 'create') {
                const result = await trySave(() => zodiosApi.create_brokers_api_v1_brokers_post([event.detail]), {
                    fallback: $_('brokers.createFailed'),
                    onError: (failure) => {
                        if (!isCurrent()) return true;
                        const message = extractErrorMessage(failure, $_('brokers.createFailed'));
                        const localized = localizeDuplicateName(message, event.detail.name);
                        if (!localized) return false;
                        error = localized;
                        toasts.error(escapeHtml(error));
                        return true;
                    },
                });
                if (!isCurrent()) return;
                if (result.status === 'error') {
                    error ??= result.message;
                    return;
                }
                const apiResult = result.data.results[0];
                const createdId = Array.isArray(apiResult?.broker_id) ? apiResult.broker_id[0] : apiResult?.broker_id;
                const errorMsg = Array.isArray(apiResult?.error) ? apiResult.error[0] : apiResult?.error;
                if (apiResult?.success && createdId) {
                    // Upsert the new broker into the shared cache so other
                    // pages (transactions, files, selectors) see it without
                    // a manual reload. The BE response only carries the id;
                    // we merge the fields the FE just submitted.
                    mergeBrokers([{id: createdId, ...event.detail}]);
                    formTouched = false;
                    notify({
                        name: 'broker.created',
                        detail: {brokerId: createdId},
                        toast: {variant: 'success', message: escapeHtml($_('brokers.created', {values: {name: event.detail.name}}))},
                    });
                    oncreated?.({id: createdId});
                    onclose?.();
                } else {
                    error = errorMsg ? (localizeDuplicateName(errorMsg, event.detail.name) ?? errorMsg) : $_('brokers.createFailed');
                }
            } else if (brokerId) {
                const result = await trySave(
                    () =>
                        zodiosApi.update_broker_api_v1_brokers__broker_id__patch(
                            {
                                name: event.detail.name,
                                description: event.detail.description,
                                portal_url: event.detail.portal_url,
                                icon_url: event.detail.icon_url,
                                default_import_plugin: event.detail.default_import_plugin,
                                allow_cash_overdraft: event.detail.allow_cash_overdraft,
                                allow_asset_shorting: event.detail.allow_asset_shorting,
                                is_active: event.detail.is_active,
                                opened_at: event.detail.opened_at || null,
                            },
                            {params: {broker_id: brokerId}},
                        ),
                    {fallback: $_('brokers.updateFailed'), onError: () => !isCurrent()},
                );
                if (!isCurrent()) return;
                if (result.status === 'error') {
                    error = result.message;
                    return;
                }
                // Sync the patched fields into the cache so other pages
                // (e.g. icon refresh) reflect the change immediately.
                mergeBrokers([
                    {
                        id: brokerId,
                        name: event.detail.name,
                        description: event.detail.description,
                        portal_url: event.detail.portal_url,
                        icon_url: event.detail.icon_url,
                        default_import_plugin: event.detail.default_import_plugin,
                        allow_cash_overdraft: event.detail.allow_cash_overdraft,
                        allow_asset_shorting: event.detail.allow_asset_shorting,
                        is_active: event.detail.is_active,
                        opened_at: event.detail.opened_at || null,
                    },
                ]);
                formTouched = false;
                onupdated?.({id: brokerId});
                onclose?.();
            }
        } finally {
            if (isCurrent()) loading = false;
        }
    }

    function handleClose() {
        if (loading) return;

        if (formTouched) {
            showDiscardConfirm = true;
        } else {
            onclose?.();
        }
    }

    function confirmDiscard() {
        formTouched = false;
        showDiscardConfirm = false;
        onclose?.();
    }

    function cancelDiscard() {
        showDiscardConfirm = false;
    }
</script>

<ModalBase closeOnBackdropClick={!loading} closeOnEscape={!loading} maxWidth="lg" onRequestClose={handleClose} open={isOpen} testId="broker-modal" {zIndex}>
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div class="flex flex-col max-h-[85vh]" oninput={handleFormChange}>
        <!-- Header (sticky top) -->
        <div class="flex items-center justify-between p-4 border-b border-gray-100 dark:border-slate-700 shrink-0">
            <h2 class="text-xl font-semibold text-gray-800 dark:text-gray-100">
                {mode === 'create' ? $_('brokers.addBroker') : $_('brokers.editBroker')}
            </h2>
            <button type="button" class="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50" disabled={loading} onclick={handleClose} aria-label={$_('common.close')} data-testid="broker-modal-close">
                <X size={20} />
            </button>
        </div>

        <!-- Error message -->
        <InfoBanner class="mx-4 mt-4 shrink-0" dismissible message={error} ondismiss={() => (error = '')} variant="error" />

        <!-- Form (scrollable area with sticky footer inside) -->
        <div class="overflow-y-auto flex-1 min-h-0 scrollbar-hidden">
            <div class="p-4 pb-0">
                <BrokerForm {initialData} {loading} {mode} on:cancel={handleClose} on:submit={handleSubmit} />
            </div>
        </div>
    </div>
</ModalBase>

<!-- Discard Changes Confirmation Modal -->
<ModalBase maxWidth="sm" onRequestClose={cancelDiscard} open={showDiscardConfirm} zIndex={zIndex + 10} testId="broker-modal-discard-confirm">
    <div class="p-6">
        <div class="flex items-center gap-3 mb-3">
            <div class="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-full">
                <AlertTriangle class="text-amber-600 dark:text-amber-400" size={20} />
            </div>
            <h2 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {$_('common.discardChanges')}
            </h2>
        </div>
        <p class="text-gray-600 dark:text-gray-300 text-sm mb-4">
            {$_('brokers.discardChangesWarning')}
        </p>
        <div class="flex justify-end gap-3">
            <button type="button" class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors" onclick={cancelDiscard} data-testid="broker-modal-continue-editing">
                {$_('common.continueEditing')}
            </button>
            <button type="button" class="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors" onclick={confirmDiscard} data-testid="broker-modal-discard">
                {$_('common.discardAndClose')}
            </button>
        </div>
    </div>
</ModalBase>
