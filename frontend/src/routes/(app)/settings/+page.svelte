<script lang="ts">
    import {untrack} from 'svelte';
    import {_} from '$lib/i18n';
    import {page} from '$app/stores';
    import {auth} from '$lib/stores/app/auth';
    import {SETTINGS_TABS, visibleSettingsTabs, type SettingsTabContext} from '$lib/features/settings/settingsTabs';
    import TabBar from '$lib/components/ui/tabs/TabBar.svelte';

    // The tabs come from the registry: a tab is added there, not here.
    const ctx: SettingsTabContext = $derived({isSuperuser: $auth.user?.is_superuser ?? false});
    const tabs = $derived(visibleSettingsTabs(SETTINGS_TABS, ctx));

    let activeTab = $state('');
    let appliedTabParam = '';

    // Runs before the first render, so the tab ?tab= names is the first body mounted. A ?tab= value is
    // applied once, when it names a visible tab: one waiting for a tab that appears later is applied then.
    $effect.pre(() => {
        const tabParam = $page.url.searchParams.get('tab');
        const visibleIds = tabs.map((tab) => tab.id);
        if (tabParam && tabParam !== appliedTabParam && visibleIds.includes(tabParam)) {
            appliedTabParam = tabParam;
            activeTab = tabParam;
        } else if (!visibleIds.includes(untrack(() => activeTab))) {
            activeTab = visibleIds[0] ?? '';
        }
    });

    const active = $derived(tabs.find((tab) => tab.id === activeTab));
</script>

<div class="space-y-6" data-testid="settings-page">
    <!-- Page Title - shows active tab name on mobile -->
    <h1 class="text-2xl font-bold text-gray-900 sm:hidden">
        {active ? $_(active.labelKey) : ''}
    </h1>

    <!-- Tabs Navigation -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <TabBar
            tabs={tabs.map((tab) => ({
                id: tab.id,
                icon: tab.icon,
                label: $_(tab.labelKey),
                testId: `settings-tab-${tab.id}`,
                className: tab.alignEnd ? 'sm:ml-auto' : '',
            }))}
            bind:activeTab
            hideLabelOnMobile={true}
        />

        <!-- Tab Content -->
        <div class="p-4 sm:p-6">
            {#if active}
                <active.component {...active.props?.(ctx) ?? {}} />
            {/if}
        </div>
    </div>
</div>
