<!--
  Settings › Plugins (workstream X, lot CP11b; plan 03 §4.4, decisions D-X13 to D-X15, N1): the settings the installed
  plugins declare, grouped by family — the price sources, then the exchange-rate sources, each title after the family's
  icon (`FAMILY_ICONS`, the one of the documentation's home). Everyone sees the tab: a personal field is the user's own;
  an instance field is read-only for a user who is not an administrator, its secret only «set» or «not set». A
  test-only plugin is never listed here (the API lists one only when named).

  Each plugin is a `PluginSettingsForm`, saved on its own. Colours are roles only (theme-roles skill).
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {Puzzle} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import PluginSettingsForm from './PluginSettingsForm.svelte';
    import {fetchPluginSettings, type PluginSettingsEntry} from './pluginSettingsApi';
    import {FAMILY_ICONS, FAMILY_TITLE_KEYS, groupByFamily, NOTE_CLASSES} from './pluginSettingsForm';

    let entries = $state<PluginSettingsEntry[]>([]);
    let loading = $state(true);
    let loadFailed = $state(false);

    const groups = $derived(groupByFamily(entries));

    /** Only the latest read writes: an older answer never replaces a newer one, nor ends its `loading`. */
    let loadGeneration = 0;

    async function load(): Promise<void> {
        const generation = ++loadGeneration;
        loading = true;
        try {
            const next = await fetchPluginSettings();
            if (generation !== loadGeneration) return;
            entries = next;
            loadFailed = false;
        } catch {
            if (generation === loadGeneration) loadFailed = true;
        } finally {
            if (generation === loadGeneration) loading = false;
        }
    }

    function replace(fresh: PluginSettingsEntry): void {
        entries = entries.map((entry) => (entry.family === fresh.family && entry.plugin_code === fresh.plugin_code ? fresh : entry));
    }

    onMount(() => {
        void load();
    });
</script>

<section aria-busy={loading} class="space-y-6 text-lf-primary" data-busy={loading ? 'true' : 'false'} data-testid="plugin-settings-tab">
    <header class="flex items-start justify-between gap-4">
        <div class="space-y-1">
            <h2 class="flex items-center gap-2 text-lg font-semibold">
                <Puzzle aria-hidden="true" class="h-5 w-5 text-lf-link" />
                {$_('pluginSettings.tab.title')}
            </h2>
            <p class="text-sm text-lf-secondary">{$_('pluginSettings.tab.intro')}</p>
        </div>
        <DocsLink icon="book" label={$_('common.documentation')} path="user/settings/plugins/" size={18} testId="plugin-settings-docs" />
    </header>

    {#if loadFailed}
        <p class={NOTE_CLASSES.error} data-testid="plugin-settings-load-error" role="alert">{$_('pluginSettings.loadError')}</p>
    {:else if !loading && entries.length === 0}
        <p class="text-sm text-lf-muted" data-testid="plugin-settings-empty">{$_('pluginSettings.tab.empty')}</p>
    {:else}
        {#each groups as group (group.family)}
            {@const FamilyIcon = FAMILY_ICONS[group.family]}
            <section class="space-y-3" data-family={group.family} data-testid="plugin-settings-family">
                <h3 class="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-lf-secondary">
                    <FamilyIcon aria-hidden="true" class="h-4 w-4 shrink-0" data-testid="plugin-settings-family-icon" />
                    {$_(FAMILY_TITLE_KEYS[group.family])}
                </h3>
                {#each group.entries as entry (entry.plugin_code)}
                    <PluginSettingsForm {entry} onsaved={replace} />
                {/each}
            </section>
        {/each}
    {/if}
</section>
