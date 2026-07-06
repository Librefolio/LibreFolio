<!--
  BrokerSharingModal - Modal wrapper for managing broker access sharing

  Thin wrapper around BrokerSharingPanel.svelte (the actual sharing UI: donut
  chart, add/edit/remove users, save) — adds modal chrome only (title, X
  close button, unsaved-changes confirmation on close). The broker detail
  page's "Info" tab embeds BrokerSharingPanel directly, without this wrapper.

  Uses ModalBase for consistent modal behavior.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Users, X} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {ConfirmModal} from '$lib/components/table';
    import BrokerSharingPanel from './BrokerSharingPanel.svelte';

    export let open: boolean = false;
    export let brokerId: number;
    export let brokerName: string = '';
    export let readOnly: boolean = false;
    export let onClose: () => void = () => {};
    export let onChanged: (() => void) | undefined = undefined;

    let hasChanges = false;
    let confirmCloseOpen = false;

    function handleRequestClose() {
        if (!readOnly && hasChanges) {
            confirmCloseOpen = true;
        } else {
            doClose();
        }
    }

    function doClose() {
        confirmCloseOpen = false;
        onClose();
    }

    function confirmDiscard() {
        confirmCloseOpen = false;
        doClose();
    }
</script>

<ModalBase maxWidth="2xl" onRequestClose={handleRequestClose} {open} testId="broker-sharing-modal" zIndex={50}>
    <div class="bg-white dark:bg-slate-800 rounded-xl w-full flex flex-col max-h-[85vh]">
        <!-- Header -->
        <div class="p-4 border-b border-gray-200 dark:border-slate-700 shrink-0">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <Users class="text-libre-green" size={20} />
                    <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {$_('brokers.sharing.title')} — {brokerName}
                    </h2>
                </div>
                <button class="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg transition-colors" on:click={handleRequestClose} type="button">
                    <X size={20} />
                </button>
            </div>
        </div>

        <!-- Body (scrollable) -->
        <div class="flex-1 overflow-y-auto p-4">
            <BrokerSharingPanel {brokerId} {readOnly} {onChanged} onCancel={handleRequestClose} bind:hasChanges />
        </div>
    </div>
</ModalBase>

<!-- Confirm Discard Changes Dialog -->
<ConfirmModal confirmText={$_('common.discardAndClose')} danger={false} message={$_('brokers.unsavedChanges')} onCancel={() => (confirmCloseOpen = false)} onConfirm={confirmDiscard} open={confirmCloseOpen} title={$_('common.discardChanges')} warning={true} zIndex={60} />
