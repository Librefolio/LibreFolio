<script lang="ts">
    import {_} from '$lib/i18n';
    import {Info, Shield, Sliders, User} from 'lucide-svelte';
    import {auth} from '$lib/stores/app/auth';
    import ProfileTab from '$lib/components/settings/tabs/ProfileTab.svelte';
    import PreferencesTab from '$lib/components/settings/tabs/PreferencesTab.svelte';
    import AboutTab from '$lib/components/settings/tabs/AboutTab.svelte';
    import GlobalSettingsTab from '$lib/components/settings/tabs/GlobalSettingsTab.svelte';
    import TabBar from '$lib/components/ui/tabs/TabBar.svelte';

    type TabId = 'profile' | 'preferences' | 'about' | 'admin';

    let activeTab: TabId = 'profile';

    // Check if user is superuser (for admin tab editing permissions)
    $: isSuperuser = $auth.user?.is_superuser ?? false;

    // All tabs - Admin visible to everyone but editable only by superuser
    const tabs: {id: TabId; icon: typeof User; labelKey: string}[] = [
        {id: 'profile', icon: User, labelKey: 'settings.profile'},
        {id: 'preferences', icon: Sliders, labelKey: 'settings.preferences'},
        {id: 'about', icon: Info, labelKey: 'settings.about'},
        {id: 'admin', icon: Shield, labelKey: 'settings.admin'},
    ];
</script>

<div class="space-y-6" data-testid="settings-page">
    <!-- Page Title - shows active tab name on mobile -->
    <h1 class="text-2xl font-bold text-gray-900 sm:hidden">
        {$_(tabs.find((t) => t.id === activeTab)?.labelKey ?? 'settings.profile')}
    </h1>

    <!-- Tabs Navigation -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <TabBar
            tabs={tabs.map((tab) => ({
                id: tab.id,
                icon: tab.icon,
                label: $_(tab.labelKey),
                testId: `settings-tab-${tab.id}`,
                className: tab.id === 'admin' ? 'sm:ml-auto' : '',
            }))}
            bind:activeTab
            hideLabelOnMobile={true}
        />

        <!-- Tab Content -->
        <div class="p-4 sm:p-6">
            {#if activeTab === 'profile'}
                <ProfileTab />
            {:else if activeTab === 'preferences'}
                <PreferencesTab />
            {:else if activeTab === 'about'}
                <AboutTab />
            {:else if activeTab === 'admin'}
                <GlobalSettingsTab canEdit={isSuperuser} />
            {/if}
        </div>
    </div>
</div>
