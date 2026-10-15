<!--
  AssetModalFooter — the footer of AssetModal: the Active and Benchmark switches, Cancel and Save.
  Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {Info, Loader2} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

    interface Props {
        active: boolean;
        isBenchmark: boolean;
        saving: boolean;
        isValid: boolean;
        /** Tour-only preview: no Save button. */
        tourPreview: boolean;
        editMode: boolean;
        oncancel: () => void;
        onsave: () => void;
    }

    let {active = $bindable(), isBenchmark = $bindable(), saving, isValid, tourPreview, editMode, oncancel, onsave}: Props = $props();
</script>

<!-- Footer: switches and buttons share a row when they fit; on a phone the buttons wrap
     under the switches (right-aligned), and each group can wrap in longer locales. Below `sm`
     the switches fill their row, justified: each with its label and info is one piece, Active
     on the left edge, Benchmark on the right one — also when it wraps. -->
<div class="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-t border-gray-200 dark:border-slate-700">
    <div class="flex w-full flex-wrap items-center gap-2 sm:w-auto">
        <div class="flex shrink-0 items-center gap-1.5 sm:gap-2">
            <Tooltip text={$t('assets.modal.activeTooltip')} position="top" maxWidth="320px">
                <Info size={14} class="text-gray-400 cursor-help shrink-0" />
            </Tooltip>
            <span id="asset-active-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
                {active ? $t('common.active') : $t('assets.edit.status.inactive')}
            </span>
            <button
                type="button"
                role="switch"
                aria-checked={active}
                aria-labelledby="asset-active-label"
                data-testid="asset-active-toggle"
                disabled={saving}
                onclick={() => (active = !active)}
                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {active ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
            >
                <span class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform {active ? 'translate-x-6' : 'translate-x-1'}"></span>
            </button>
        </div>

        <span class="mx-1 hidden h-5 w-px bg-gray-200 sm:block dark:bg-slate-700"></span>

        <div class="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
            <Tooltip text={$t('assets.modal.benchmarkTooltip')} position="top" maxWidth="320px">
                <Info size={14} class="text-gray-400 cursor-help shrink-0" />
            </Tooltip>
            <span id="asset-benchmark-label" class="text-sm font-medium text-gray-700 dark:text-gray-200">
                {$t('assets.modal.benchmark')}
            </span>
            <button
                type="button"
                role="switch"
                aria-checked={isBenchmark}
                aria-labelledby="asset-benchmark-label"
                data-testid="asset-benchmark-toggle"
                disabled={saving}
                onclick={() => (isBenchmark = !isBenchmark)}
                class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors {isBenchmark ? 'bg-libre-green' : 'bg-gray-300 dark:bg-slate-600'}"
            >
                <span class="inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform {isBenchmark ? 'translate-x-6' : 'translate-x-1'}"></span>
            </button>
        </div>
    </div>

    <div class="flex flex-wrap items-center justify-end gap-3 ml-auto">
        <button
            type="button"
            onclick={oncancel}
            disabled={saving}
            data-testid="asset-modal-cancel"
            class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
        >
            {$t('common.cancel')}
        </button>
        {#if !tourPreview}
            <button
                type="button"
                onclick={onsave}
                disabled={!isValid || saving}
                data-testid="asset-modal-save"
                class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-libre-green rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
                {#if saving}
                    <Loader2 size={14} class="animate-spin" />
                {/if}
                <span>{editMode ? $t('assets.modal.saveChanges') : $t('assets.modal.createAsset')}</span>
            </button>
        {/if}
    </div>
</div>
