<!--
  SettingActions — one inline save / undo / reset cluster for settings rows.

  There were nine copies of this cluster: five in the reusable row controls and
  four in `GlobalSettingsTab`'s string/select rows. They started as the same UI
  and drifted in ways that changed behaviour:

    · only `SettingNumber`, `SettingToggle` and the four global-tab inline rows
      disabled Save while `isSaving` was true. Currency, select and theme rows
      kept accepting double-clicks during an open write, so a second save could
      leave the browser before the first one settled;
    · `SettingTheme` used `createEventDispatcher`, while the other row controls
      used Svelte 5 callback props. The cluster now has one callback API, so the
      calling control decides only what save/undo/reset means;
    · the five reusable controls hid Reset while a value had unsaved edits
      (`isNonDefault && !isModified`), but the four inline global rows showed it
      even during edits. That lets two destructive-looking choices compete for
      the same dirty value, so the shared rule is the safer majority rule.

  Test ids and titles are preserved exactly because the component tests and E2E
  selectors address these buttons by that public contract.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {RotateCcw, Save, Undo} from 'lucide-svelte';

    interface Props {
        isModified?: boolean;
        isNonDefault?: boolean;
        isLocked?: boolean;
        isSaving?: boolean;
        onsave?: () => void;
        onundo?: () => void;
        onreset?: () => void;
    }

    let {isModified = false, isNonDefault = false, isLocked = false, isSaving = false, onsave, onundo, onreset}: Props = $props();
</script>

{#if !isLocked}
    <div class="flex items-center space-x-1">
        {#if isModified}
            <button type="button" onclick={() => onsave?.()} disabled={isSaving} class="p-1.5 bg-libre-green text-white rounded-lg hover:bg-libre-green/90 transition-colors disabled:opacity-50" data-testid="setting-save" title={$_('common.save')}>
                <Save size={14} />
            </button>
            <button type="button" onclick={() => onundo?.()} class="p-1.5 bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors" data-testid="setting-undo" title={$_('common.undo')}>
                <Undo size={14} />
            </button>
        {/if}
        {#if isNonDefault && !isModified}
            <button type="button" onclick={() => onreset?.()} class="p-1.5 bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded-lg hover:bg-orange-200 dark:hover:bg-orange-900/50 transition-colors" data-testid="setting-reset" title={$_('common.reset')}>
                <RotateCcw size={14} />
            </button>
        {/if}
    </div>
{/if}
