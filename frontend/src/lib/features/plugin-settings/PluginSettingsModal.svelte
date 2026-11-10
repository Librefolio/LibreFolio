<!--
  PluginSettingsModal — «Configure»: one plugin's settings over the dialog that asked for them (workstream X, lot CP11b;
  plan 03 §4.4). Opened from the provider panel of the asset dialog and from the search's «to configure» row; the
  same form as Settings › Plugins, filtered on the plugin (the API names it, so a test-only plugin is listed too).

  Layer 80 by default: above the asset dialog (50) and its prompts (70). The body scrolls between the title and «Close»:
  a plugin with many fields fits any window. Colours are roles only (theme-roles skill).
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import PluginSettingsForm from './PluginSettingsForm.svelte';
    import {fetchPluginEntry, type PluginSettingsEntry, type SettingsFamily} from './pluginSettingsApi';
    import {NOTE_CLASSES, SECONDARY_BUTTON_CLASS} from './pluginSettingsForm';

    interface Props {
        open: boolean;
        family: SettingsFamily;
        pluginCode: string;
        /** The plugin's name while its settings load. */
        pluginName?: string;
        zIndex?: number;
        onClose: () => void;
        /** After a save, with the plugin's state read again. */
        onSaved?: (fresh: PluginSettingsEntry) => void;
    }

    let {open, family, pluginCode, pluginName = '', zIndex = 80, onClose, onSaved}: Props = $props();

    const uid = $props.id();
    let entry = $state<PluginSettingsEntry | null>(null);
    let loading = $state(false);
    let loadFailed = $state(false);

    /** Only the latest read writes: an older answer never replaces a newer one. */
    let loadGeneration = 0;

    async function load(target: {family: SettingsFamily; pluginCode: string}): Promise<void> {
        const generation = ++loadGeneration;
        loading = true;
        loadFailed = false;
        entry = null;
        try {
            const found = await fetchPluginEntry(target.family, target.pluginCode);
            if (generation === loadGeneration) entry = found;
        } catch {
            if (generation === loadGeneration) loadFailed = true;
        } finally {
            if (generation === loadGeneration) loading = false;
        }
    }

    // Every opening reads the plugin's state afresh; closing drops an answer still on its way.
    $effect(() => {
        if (open) void load({family, pluginCode});
        return () => {
            loadGeneration++;
        };
    });

    function saved(fresh: PluginSettingsEntry): void {
        entry = fresh;
        onSaved?.(fresh);
    }

    const title = $derived(entry?.plugin_name || pluginName || pluginCode);
</script>

<ModalBase labelledBy="{uid}-title" maxWidth="xl" onRequestClose={onClose} {open} testId="plugin-settings-modal" trapFocus {zIndex}>
    <!-- The box is a column capped at 90vh (ModalBase): the title and «Close» stay, the form scrolls between them. Selects
         draw their list with position:fixed, so the scrolling body does not clip it. -->
    <div aria-busy={loading} class="flex min-h-0 flex-1 flex-col text-lf-primary" data-busy={loading ? 'true' : 'false'} data-plugin={pluginCode}>
        <h2 class="shrink-0 px-5 pt-5 text-lg font-semibold" id="{uid}-title">{$_('pluginSettings.modal.title', {values: {plugin: title}})}</h2>

        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4" data-testid="plugin-settings-modal-body">
            {#if loadFailed}
                <p class={NOTE_CLASSES.error} data-testid="plugin-settings-load-error" role="alert">{$_('pluginSettings.loadError')}</p>
            {:else if loading}
                <p class="text-sm text-lf-muted">{$_('common.loading')}</p>
            {:else if entry}
                <PluginSettingsForm {entry} onsaved={saved} />
            {:else}
                <p class="text-sm text-lf-muted" data-testid="plugin-settings-none">{$_('pluginSettings.modal.none')}</p>
            {/if}
        </div>

        <div class="flex shrink-0 justify-end px-5 pb-5">
            <button class={SECONDARY_BUTTON_CLASS} data-testid="plugin-settings-modal-close" onclick={onClose} type="button">{$_('common.close')}</button>
        </div>
    </div>
</ModalBase>
