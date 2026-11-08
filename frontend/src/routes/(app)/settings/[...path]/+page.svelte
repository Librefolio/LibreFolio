<script lang="ts">
    import {untrack} from 'svelte';
    import {_} from '$lib/i18n';
    import {page} from '$app/stores';
    import {goto} from '$app/navigation';
    import {auth} from '$lib/stores/app/auth';
    import {SETTINGS_TABS, SETTINGS_TAB_GROUPS, settingsBar, settingsPlaceOf, visibleSettingsTabs, type SettingsBarEntry, type SettingsTab, type SettingsTabContext} from '$lib/features/settings/settingsTabs';
    import {SETTINGS_ROOT} from '$lib/features/settings/settingsPaths';
    import TabBar from '$lib/components/ui/tabs/TabBar.svelte';

    // The tabs come from the registry: a tab is added there, not here.
    const ctx: SettingsTabContext = $derived({isSuperuser: $auth.user?.is_superuser ?? false});
    const tabs = $derived(visibleSettingsTabs(SETTINGS_TABS, ctx));
    // The top bar: the tabs, each group standing for its members (decision P13 b)
    const entries = $derived(settingsBar(SETTINGS_TABS, SETTINGS_TAB_GROUPS, ctx));

    let activeTab = $state('');
    let appliedTabParam = '';
    let appliedPath = '';

    function entryId(entry: SettingsBarEntry): string {
        return entry.kind === 'tab' ? entry.tab.id : entry.group.id;
    }

    /** The tab an id opens: a visible tab, or the first visible member of a group; null for anything else. */
    function tabFor(id: string): string | null {
        if (tabs.some((tab) => tab.id === id)) return id;
        const group = entries.find((entry) => entry.kind === 'group' && entry.group.id === id);
        return group?.kind === 'group' ? group.members[0].id : null;
    }

    /** The address of a tab (lot B10): its `path` in the registry. */
    function pathOf(id: string): string {
        return tabs.find((tab) => tab.id === id)?.path ?? SETTINGS_ROOT;
    }

    const NAVIGATION = {noScroll: true, keepFocus: true} as const;

    // Runs before the first render, so the tab the address names is the first body mounted (lot B10):
    //   - `/settings/<tab>` and `/settings/admin/<tab>` open that tab, `/settings/admin` the group's first visible member,
    //     each time the address changes (a click writes it, Back and Forward read it);
    //   - `/settings` opens the first visible tab and keeps its address; `?tab=` there is the address of 1.2: it opens the
    //     tab it names, once, and the address becomes the tab's own. A `?tab=` naming a tab not visible yet waits for it;
    //   - an address the registry does not know, or a tab this user cannot see once the user is known, goes back to
    //     `/settings`, the first tab.
    $effect.pre(() => {
        const url = $page.url;
        const userKnown = $auth.user != null;
        const visibleIds = tabs.map((tab) => tab.id);
        const place = settingsPlaceOf(url.pathname, SETTINGS_TABS, SETTINGS_TAB_GROUPS);
        if (place.kind === 'root') {
            // Back to `/settings` from a tab's address: the first tab again.
            if (appliedPath !== '' && appliedPath !== SETTINGS_ROOT) activeTab = visibleIds[0] ?? '';
            appliedPath = SETTINGS_ROOT;
            const tabParam = url.searchParams.get('tab');
            const target = tabParam ? tabFor(tabParam) : null;
            if (tabParam && tabParam !== appliedTabParam && target) {
                appliedTabParam = tabParam;
                activeTab = target;
                void goto(pathOf(target), {...NAVIGATION, replaceState: true});
                return;
            }
        } else if (place.kind === 'tab' || place.kind === 'group') {
            // A later `/settings?tab=` (an old link) is a new request.
            appliedTabParam = '';
            const target = tabFor(place.id);
            if (target && url.pathname !== appliedPath) {
                appliedPath = url.pathname;
                activeTab = target;
                return;
            }
            if (!target && userKnown) {
                void goto(SETTINGS_ROOT, {...NAVIGATION, replaceState: true});
            }
        } else {
            void goto(SETTINGS_ROOT, {...NAVIGATION, replaceState: true});
        }
        if (!visibleIds.includes(untrack(() => activeTab))) {
            activeTab = visibleIds[0] ?? '';
        }
    });

    /** Open a tab and write its address: Back returns to the tab before. */
    function openTab(id: string): void {
        activeTab = id;
        const path = pathOf(id);
        if (untrack(() => $page.url.pathname) !== path) void goto(path, NAVIGATION);
    }

    // What the badges need is read before a tab is opened: each visible tab's prefetch, at the start and whenever the
    // context changes. Untracked: a prefetch reads the state it fills, and must not run again when that state moves.
    $effect(() => {
        const current = ctx;
        const visible = tabs;
        untrack(() => {
            for (const tab of visible) tab.prefetch?.(current);
        });
    });

    const active = $derived(tabs.find((tab) => tab.id === activeTab));
    const activeEntry = $derived(entries.find((entry) => (entry.kind === 'tab' ? entry.tab.id === activeTab : entry.members.some((member) => member.id === activeTab))));
    // The second bar: the members of the open group, when it has at least two
    const members = $derived(activeEntry?.kind === 'group' && activeEntry.members.length >= 2 ? activeEntry.members : []);

    function badgeOf(tab: SettingsTab): number {
        return tab.badge?.(ctx) ?? 0;
    }

    const topTabs = $derived(
        entries.map((entry) =>
            entry.kind === 'tab'
                ? {
                      id: entry.tab.id,
                      icon: entry.tab.icon,
                      label: $_(entry.tab.labelKey),
                      testId: `settings-tab-${entry.tab.id}`,
                      className: entry.tab.alignEnd ? 'sm:ml-auto' : '',
                      badge: badgeOf(entry.tab),
                  }
                : {
                      id: entry.group.id,
                      icon: entry.group.icon,
                      label: $_(entry.group.labelKey),
                      testId: `settings-tab-${entry.group.id}`,
                      className: entry.group.alignEnd ? 'sm:ml-auto' : '',
                      badge: entry.members.reduce((sum, member) => sum + badgeOf(member), 0),
                  },
        ),
    );

    const memberTabs = $derived(members.map((tab) => ({id: tab.id, icon: tab.icon, label: $_(tab.labelKey), testId: `settings-tab-${tab.id}`, badge: badgeOf(tab)})));

    /** A tab of the top bar: the tab itself, or a group's first visible member unless one of its members is open. */
    function selectTop(id: string): void {
        const entry = entries.find((candidate) => entryId(candidate) === id);
        if (!entry) return;
        if (entry.kind === 'tab') openTab(entry.tab.id);
        else if (!entry.members.some((member) => member.id === activeTab)) openTab(entry.members[0].id);
    }
</script>

<div class="space-y-6 text-lf-primary" data-testid="settings-page">
    <!-- Page Title - shows active tab name on mobile -->
    <h1 class="text-2xl font-bold text-lf-primary sm:hidden">
        {active ? $_(active.labelKey) : ''}
    </h1>

    <!-- Tabs Navigation -->
    <div class="bg-lf-card rounded-xl shadow-sm shadow-lf-shadow-card border border-lf-subtle overflow-hidden">
        <TabBar tabs={topTabs} activeTab={activeEntry ? entryId(activeEntry) : ''} onchange={selectTop} hideLabelOnMobile={true} scrollable />

        {#if members.length > 0}
            <!-- The members of the open group: the same bar, the same roles as the one above -->
            <div data-testid="settings-subtabs">
                <TabBar tabs={memberTabs} {activeTab} onchange={openTab} hideLabelOnMobile={true} scrollable />
            </div>
        {/if}

        <!-- Tab Content -->
        <div class="p-4 sm:p-6">
            {#if active}
                <active.component {...active.props?.(ctx) ?? {}} />
            {/if}
        </div>
    </div>
</div>
