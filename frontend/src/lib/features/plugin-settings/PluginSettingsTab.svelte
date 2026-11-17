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
    import {fetchPluginEntry, fetchPluginSettings, type PluginSettingsEntry} from './pluginSettingsApi';
    import {entryTitle, FAMILY_ICONS, FAMILY_TITLE_KEYS, groupByFamily, groupFormId, NOTE_CLASSES} from './pluginSettingsForm';

    let entries = $state<PluginSettingsEntry[]>([]);
    let loading = $state(true);
    let loadFailed = $state(false);

    const groups = $derived(groupByFamily(entries));
    /** The shared groups this tab lists (project 76): their names for the plugins' «in the group» rows, and the ones a
     * plugin can bring into view. A group the tab does not list (a test-only one) is named, with no button. */
    const groupNames = $derived(Object.fromEntries(entries.filter((entry) => entry.family === 'group').map((entry) => [entry.plugin_code, entryTitle(entry, $_)])));
    const listedGroups = $derived(Object.keys(groupNames));

    /** Bring a shared group's form into view, and the focus to its heading. */
    function openGroup(name: string): void {
        const target = document.getElementById(groupFormId(name));
        if (!target) return;
        target.scrollIntoView?.({behavior: 'smooth', block: 'start'});
        target.querySelector<HTMLElement>('h4')?.focus({preventScroll: true});
    }

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

    /** A shared group saved: its fresh state, then each plugin that reads it read again — their «configured» counts the
     * group's fields (project 76). A reader that cannot be read keeps the state shown until the next read. */
    async function groupSaved(fresh: PluginSettingsEntry): Promise<void> {
        replace(fresh);
        const readers = entries.filter((entry) => entry.family !== 'group' && (entry.groups ?? []).includes(fresh.plugin_code));
        await Promise.all(
            readers.map(async (reader) => {
                try {
                    const again = await fetchPluginEntry(reader.family, reader.plugin_code);
                    if (again) replace(again);
                } catch {
                    // The group is saved either way.
                }
            }),
        );
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
                    {#if entry.family === 'group'}
                        <div id={groupFormId(entry.plugin_code)}>
                            <PluginSettingsForm {entry} onsaved={groupSaved} />
                        </div>
                    {:else}
                        <PluginSettingsForm {entry} {groupNames} onopengroup={openGroup} onsaved={replace} openableGroups={listedGroups} />
                    {/if}
                {/each}
            </section>
        {/each}
    {/if}
</section>
