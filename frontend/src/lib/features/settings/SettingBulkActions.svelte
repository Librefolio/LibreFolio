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
        <button type="button" onclick={() => onsaveAll?.()} disabled={isSaving} class="p-2 rounded-lg transition-all bg-lf-action text-lf-on-action hover:bg-lf-action-hover disabled:opacity-50" data-testid="settings-save-all" title={$_('common.saveAll')}>
            <Save size={18} />
        </button>
        <button type="button" onclick={() => onundoAll?.()} class="p-2 rounded-lg transition-all bg-lf-panel text-lf-secondary hover:bg-lf-neutral" data-testid="settings-undo-all" title={$_('common.undoAll')}>
            <Undo size={18} />
        </button>
    {/if}
    {#if hasNonDefaults}
        <button type="button" onclick={() => onresetAll?.()} class="p-2 rounded-lg transition-all bg-lf-warning-soft text-lf-warning hover:bg-lf-warning-line" data-testid="settings-reset-all" title={$_('common.resetAll')}>
            <RotateCcw size={18} />
        </button>
    {/if}
{/if}
