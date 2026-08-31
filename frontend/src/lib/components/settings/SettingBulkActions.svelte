<!--
  SettingBulkActions — one header save-all / undo-all / reset-all cluster.

  The settings shell and the global-settings tab carried the same three header
  actions, but only the global tab disabled Save All while a write was already
  running. The shared component keeps that guard and preserves the public
  `data-testid` handles (`settings-save-all`, `settings-undo-all`,
  `settings-reset-all`) used by the tests.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {RotateCcw, Save, Undo} from 'lucide-svelte';

    interface Props {
        hasChanges?: boolean;
        hasNonDefaults?: boolean;
        isLocked?: boolean;
        isSaving?: boolean;
        onsaveAll?: () => void;
        onundoAll?: () => void;
        onresetAll?: () => void;
    }

    let {hasChanges = false, hasNonDefaults = false, isLocked = false, isSaving = false, onsaveAll, onundoAll, onresetAll}: Props = $props();
</script>

{#if !isLocked}
    {#if hasChanges}
        <button type="button" onclick={() => onsaveAll?.()} disabled={isSaving} class="p-2 rounded-lg transition-all bg-libre-green text-white hover:bg-libre-green/90 disabled:opacity-50" data-testid="settings-save-all" title={$_('common.saveAll')}>
            <Save size={18} />
        </button>
        <button type="button" onclick={() => onundoAll?.()} class="p-2 rounded-lg transition-all bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600" data-testid="settings-undo-all" title={$_('common.undoAll')}>
            <Undo size={18} />
        </button>
    {/if}
    {#if hasNonDefaults}
        <button type="button" onclick={() => onresetAll?.()} class="p-2 rounded-lg transition-all bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 hover:bg-orange-200 dark:hover:bg-orange-900/50" data-testid="settings-reset-all" title={$_('common.resetAll')}>
            <RotateCcw size={18} />
        </button>
    {/if}
{/if}
