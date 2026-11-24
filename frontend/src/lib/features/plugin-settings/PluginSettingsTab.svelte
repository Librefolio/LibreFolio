<!--
  Settings › Plugins (workstream X, lot CP11b; plan 03 §4.4, decisions D-X13 to D-X15, N1): the settings the installed
  plugins declare, grouped by family — the price sources, then the exchange-rate sources, each title after the family's
  icon (`FAMILY_ICONS`, the one of the documentation's home). Everyone sees the tab: a personal field is the user's own;
  an instance field is read-only for a user who is not an administrator, its secret only «set» or «not set». A
  test-only plugin is never listed here (the API lists one only when named).

  Each plugin is a `PluginSettingsForm`, saved on its own. Colours are roles only (theme-roles skill).

  The menu (project 76, S1b; mock S0 approved by the developer on 19/11) is the shared `SettingsCategoryNav`, as on Global
  settings: «All», «To configure» and the families with short titles, each with its count and an amber dot where something
  is to configure; a phone shows it as the «Category» dropdown. A choice filters the page; «Open» on a shared group shows
  the groups first when the choice hides it.

  The search (S2b, the developer's rules of 19/11): every word typed must be in the same card — its name, code,
  description, the names and descriptions of its fields, never a number — as written (case and accents aside, no
  tolerance for typos). The menu's counts follow it; its entries stay, with 0. With nothing found, the empty state of the
  Assets and FX pages, and within a choice a link to search every family.

  The address (S2c): the choice and the search are read from `?family=` and `?q=` (a link from outside opens the page
  filtered; Back and Forward bring them back) and written there, a choice as a new step of the history, the search in
  place while typing. «All» and an empty search write nothing.
-->
<script lang="ts">
    import {onMount, tick, untrack} from 'svelte';
    import {goto} from '$app/navigation';
    import {page} from '$app/stores';
    import {Puzzle, Search} from 'lucide-svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {_} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import SettingsCategoryNav from '$lib/features/settings/SettingsCategoryNav.svelte';
    import PluginSettingsForm from './PluginSettingsForm.svelte';
    import {fetchPluginEntry, fetchPluginSettings, type PluginSettingsEntry} from './pluginSettingsApi';
    import {entryMatches, entryTitle, FAMILY_ICONS, FAMILY_TITLE_KEYS, filterByMenu, groupByFamily, groupFormId, MENU_ICONS, MENU_TITLE_KEYS, NOTE_CLASSES, pluginMenu, type PluginMenuId, pluginsHref, readPluginsAddress, searchWords} from './pluginSettingsForm';

    let entries = $state<PluginSettingsEntry[]>([]);
    let loading = $state(true);
    let loadFailed = $state(false);

    /** The menu's choice (S1b): everything, the entries not configured, or one family. */
    let selected = $state<PluginMenuId>('all');
    /** The search's text, as typed (S2b). */
    let query = $state('');
    const words = $derived(searchWords(query));
    /** The cards every word of the search is in, all choices of the menu together. */
    const matching = $derived(entries.filter((entry) => entryMatches(entry, words, $_, $currentLanguage)));
    const navEntries = $derived(pluginMenu(entries, selected, matching).map((item) => ({id: item.id, icon: MENU_ICONS[item.id], label: $_(MENU_TITLE_KEYS[item.id]), count: item.count, dot: item.dot})));
    const shown = $derived(filterByMenu(matching, selected));
    /** The shared groups the search finds: «All» does not list them (81 U37), so a search that finds only them offers «Shared». */
    const sharedMatching = $derived(matching.filter((entry) => entry.family === 'group').length);

    /** The addresses this page wrote and has not seen land yet: when one lands it is the page's own echo, not a new
     * address, and reading it would take back what was typed since (a fast typist, navigations landing late). */
    const written = new Set<string>();

    // The address names the choice and the search (S2c): read on open and whenever it changes (Back, Forward, a link)
    $effect(() => {
        const url = $page.url;
        const here = url.pathname + url.search;
        if (written.has(here)) {
            written.delete(here);
            return;
        }
        written.clear();
        const named = readPluginsAddress(url.searchParams);
        untrack(() => {
            if (named.selected !== selected) selected = named.selected;
            if (named.query !== query) query = named.query;
        });
    });

    /** Write the choice and the search into the address: a choice as a new step of the history, typing in place. */
    function writeAddress(replace: boolean): void {
        const target = pluginsHref(selected, query);
        if (target === $page.url.pathname + $page.url.search) return;
        written.add(target);
        void goto(target, {replaceState: replace, noScroll: true, keepFocus: true});
    }

    function choose(id: PluginMenuId): void {
        selected = id;
        writeAddress(false);
    }

    function typed(text: string): void {
        query = text;
        writeAddress(true);
    }
    const groups = $derived(groupByFamily(shown));
    /** The shared groups this tab lists (project 76): their names for the plugins' «in the group» rows, and the ones a
     * plugin can bring into view. A group the tab does not list (a test-only one) is named, with no button. */
    const groupNames = $derived(Object.fromEntries(entries.filter((entry) => entry.family === 'group').map((entry) => [entry.plugin_code, entryTitle(entry, $_)])));
    const listedGroups = $derived(Object.keys(groupNames));
    /** The listed groups that own a call count (project 76, U5): a plugin that reads one says its calls count there. */
    const countGroups = $derived(entries.filter((entry) => entry.family === 'group' && entry.call_usage !== undefined).map((entry) => entry.plugin_code));

    /** Bring a shared group's form into view, and the focus to its heading; first the groups, when the menu's choice hides it. */
    async function openGroup(name: string): Promise<void> {
        if (!document.getElementById(groupFormId(name))) {
            // The groups, the search cleared (mock S0): the group's form is shown whatever was typed
            query = '';
            choose('group');
            await tick();
        }
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

<section aria-busy={loading} class="text-lf-primary" data-busy={loading ? 'true' : 'false'} data-testid="plugin-settings-tab">
    {#if !loadFailed && entries.length > 0}
        <SettingsCategoryNav dotLabel={$_('pluginSettings.menu.hasUnconfigured')} entries={navEntries} mode="phone" onselect={(id) => choose(id as PluginMenuId)} {selected} testIdPrefix="plugin-settings" triggerIcon={MENU_ICONS[selected]} triggerLabel={$_(MENU_TITLE_KEYS[selected])} />
    {/if}
    <div class="flex flex-col gap-4 sm:flex-row sm:gap-6">
        {#if !loadFailed && entries.length > 0}
            <SettingsCategoryNav dotLabel={$_('pluginSettings.menu.hasUnconfigured')} entries={navEntries} mode="sidebar" onselect={(id) => choose(id as PluginMenuId)} {selected} testIdPrefix="plugin-settings" />
        {/if}
        <div class="min-w-0 flex-1 space-y-6">
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

            {#if !loadFailed && entries.length > 0}
                <div class="relative w-full sm:max-w-xs">
                    <Search aria-hidden="true" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-lf-muted" size={14} />
                    <input
                        aria-label={$_('pluginSettings.search.placeholder')}
                        class="w-full rounded-lg border border-lf-input bg-lf-field py-1.5 pl-8 pr-3 text-sm text-lf-primary placeholder:text-lf-placeholder hover:border-lf-input-hover focus:border-lf-focus focus:ring-1 focus:ring-lf-focus"
                        data-testid="plugin-settings-search"
                        oninput={(event) => typed(event.currentTarget.value)}
                        placeholder={$_('pluginSettings.search.placeholder')}
                        type="search"
                        value={query}
                    />
                </div>
            {/if}

            {#if loadFailed}
                <p class={NOTE_CLASSES.error} data-testid="plugin-settings-load-error" role="alert">{$_('pluginSettings.loadError')}</p>
            {:else if !loading && entries.length === 0}
                <p class="text-sm text-lf-muted" data-testid="plugin-settings-empty">{$_('pluginSettings.tab.empty')}</p>
            {:else}
                {#if shown.length === 0 && words.length > 0}
                    <!-- The empty state of the Assets and FX pages (common.noMatchesTitle), with the plugins' icon -->
                    <div class="rounded-xl border border-lf-subtle bg-lf-card p-12 text-center shadow-sm shadow-lf-shadow-card" data-testid="plugin-settings-no-matches">
                        <div class="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-lf-selected">
                            <Puzzle aria-hidden="true" class="text-lf-link" size={32} />
                        </div>
                        <h3 class="mb-2 text-lg font-semibold text-lf-secondary">{$_('common.noMatchesTitle')}</h3>
                        <p class="text-lf-muted">
                            {selected === 'all' ? $_('pluginSettings.search.noMatchAll', {values: {query: query.trim()}}) : $_('pluginSettings.search.noMatchFamily', {values: {family: $_(MENU_TITLE_KEYS[selected]), query: query.trim()}})}
                        </p>
                        {#if selected !== 'all' && matching.length > 0}
                            <button class="mt-3 text-sm text-lf-link hover:underline" data-testid="plugin-settings-search-all" onclick={() => choose('all')} type="button">
                                {$_('pluginSettings.search.searchAll', {values: {count: matching.length}})}
                            </button>
                        {/if}
                        {#if selected === 'all' && sharedMatching > 0}
                            <button class="mt-3 text-sm text-lf-link hover:underline" data-testid="plugin-settings-search-shared" onclick={() => choose('group')} type="button">
                                {$_('pluginSettings.search.inShared', {values: {count: sharedMatching}})}
                            </button>
                        {/if}
                    </div>
                {:else if selected === 'unconfigured' && shown.length === 0}
                    <p class="text-sm text-lf-muted" data-testid="plugin-settings-nothing-unconfigured">{$_('pluginSettings.menu.nothingUnconfigured')}</p>
                {/if}
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
                                <PluginSettingsForm {countGroups} {entry} {groupNames} onopengroup={openGroup} onsaved={replace} openableGroups={listedGroups} />
                            {/if}
                        {/each}
                    </section>
                {/each}
            {/if}
        </div>
    </div>
</section>
