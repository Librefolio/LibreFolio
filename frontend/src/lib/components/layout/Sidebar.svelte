<script lang="ts">
    import {page} from '$app/stores';
    import {browser} from '$app/environment';
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {auth} from '$lib/stores/app/auth';
    import {getUserStorage, setUserStorage} from '$lib/utils/storage';
    import {userSettings} from '$lib/stores/app/settings';
    import {resetNavDepth} from '$lib/stores/app/navigationStore';
    import {ArrowRightLeft, BarChart3, Briefcase, Coins, Files, LayoutDashboard, LogOut, Settings, User, Wrench, X} from 'lucide-svelte';
    import {APP_VERSION} from '$lib/version';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import ChangelogModal from './ChangelogModal.svelte';
    import ConnectionSecurityIndicator from './ConnectionSecurityIndicator.svelte';

    // Mobile sidebar state (exported so parent can control it)
    export let isOpen = false;

    /** Changelog modal visibility (F12) */
    let changelogOpen = false;

    // Collapsed state (icons only) - exported and persisted in localStorage
    export let collapsed = false;

    // Current path for active state - reactive
    $: currentPath = $page.url.pathname;

    // Load collapsed state from user-scoped localStorage on mount
    onMount(() => {
        if (browser) {
            const saved = getUserStorage('sidebar-collapsed', 'false');
            collapsed = saved === 'true';
        }
    });

    // Navigation groups
    // Group 1: My Portfolio (user-specific data)
    const portfolioItems = [
        {href: '/dashboard', icon: LayoutDashboard, labelKey: 'nav.dashboard'},
        {href: '/brokers', icon: Briefcase, labelKey: 'brokers.title'},
        {href: '/transactions', icon: ArrowRightLeft, labelKey: 'transactions.title'},
        {href: '/tools', icon: Wrench, labelKey: 'tools.title'},
    ];

    // Group 2: Market Data (global/shared data)
    const marketDataItems = [
        {href: '/assets', icon: BarChart3, labelKey: 'common.assets'},
        {href: '/fx', icon: Coins, labelKey: 'fx.title'},
    ];

    // Group 3: Files & Settings
    const utilityItems = [
        {href: '/files', icon: Files, labelKey: 'uploads.title'},
        {href: '/settings', icon: Settings, labelKey: 'nav.settings'},
    ];

    // All items flat for active check
    const allNavItems = [...portfolioItems, ...marketDataItems, ...utilityItems];

    // Reactive: compute active item based on current path
    $: activeHref = allNavItems.find((item) => currentPath === item.href || currentPath.startsWith(item.href + '/'))?.href ?? '';

    // Get avatar URL safely from user settings
    $: avatarUrl = $userSettings?.avatar_url as string | null | undefined;

    async function handleLogout() {
        await auth.logout();
    }

    function toggleCollapsed() {
        collapsed = !collapsed;
        if (browser) {
            setUserStorage('sidebar-collapsed', String(collapsed));
        }
    }

    /** The connection-security details need the full width (plan 36). */
    function expandSidebar() {
        if (collapsed) toggleCollapsed();
    }

    function closeSidebar() {
        isOpen = false;
        resetNavDepth();
    }

    function navigationAnchorId(href: string): string {
        return `nav.${href.slice(1).replaceAll('/', '.')}`;
    }

    function navigationTestId(href: string): string {
        return `nav-${href.slice(1).replaceAll('/', '-')}`;
    }
</script>

<!-- Mobile Overlay -->
{#if isOpen}
    <div class="fixed inset-0 bg-lf-overlay z-40 lg:hidden" on:click={closeSidebar} on:keydown={(e) => e.key === 'Escape' && closeSidebar()} role="button" tabindex="-1" aria-label="Close sidebar"></div>
{/if}

<!-- Sidebar -->
<nav
    class="fixed left-0 top-0 h-screen bg-lf-sidebar text-lf-primary border-r border-lf-subtle flex flex-col z-50 transform transition-all duration-300 ease-in-out overflow-hidden safe-top
		{collapsed ? 'w-16' : 'w-64'}
		{isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0"
>
    <!-- Logo Header -->
    <div class="p-4 flex items-center border-b border-lf-subtle {collapsed ? 'justify-center' : 'justify-between'}">
        <button class="flex items-center space-x-3 cursor-pointer" on:click={toggleCollapsed} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} data-testid="sidebar-collapse-toggle" use:guideAnchor={'nav.toggle.desktop'}>
            <div class="w-8 h-8 flex-shrink-0 rounded-lg flex items-center justify-center p-1 bg-lf-logo">
                <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
            </div>
            {#if !collapsed}
                <span class="text-xl font-bold tracking-wide whitespace-nowrap">LibreFolio</span>
            {/if}
        </button>
        <!-- Mobile close button -->
        {#if !collapsed}
            <button class="lg:hidden p-2 hover:bg-lf-hover rounded-lg" on:click={closeSidebar}>
                <X size={20} />
            </button>
        {/if}
    </div>

    <!-- Navigation -->
    <div class="flex-1 py-4 overflow-y-auto overflow-x-hidden">
        <!-- Portfolio Group -->
        <ul>
            {#each portfolioItems as item (item.href)}
                <li>
                    <a
                        href={item.href}
                        data-testid={navigationTestId(item.href)}
                        use:guideAnchor={navigationAnchorId(item.href)}
                        on:click={() => {
                            closeSidebar();
                            resetNavDepth();
                        }}
                        class="flex items-center px-4 py-3 transition-all relative group
						{collapsed ? 'justify-center' : 'space-x-3'}
						{activeHref === item.href ? 'bg-lf-panel text-lf-link border-r-4 border-lf-focus' : 'text-lf-secondary hover:bg-lf-hover hover:text-lf-primary'}"
                        title={collapsed ? $_(item.labelKey) : ''}
                    >
                        <svelte:component this={item.icon} size={20} class="flex-shrink-0" />
                        {#if !collapsed}
                            <span class="whitespace-nowrap">{$_(item.labelKey)}</span>
                        {/if}
                        {#if collapsed}
                            <span class="absolute left-full ml-2 px-2 py-1 bg-lf-inverse text-lf-on-inverse text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                                {$_(item.labelKey)}
                            </span>
                        {/if}
                    </a>
                </li>
            {/each}
        </ul>

        <!-- Divider -->
        <div class="my-3 mx-4 border-t border-lf-subtle"></div>

        <!-- Market Data Group -->
        <ul>
            {#each marketDataItems as item (item.href)}
                <li>
                    <a
                        href={item.href}
                        data-testid={navigationTestId(item.href)}
                        use:guideAnchor={navigationAnchorId(item.href)}
                        on:click={() => {
                            closeSidebar();
                            resetNavDepth();
                        }}
                        class="flex items-center px-4 py-3 transition-all relative group
						{collapsed ? 'justify-center' : 'space-x-3'}
						{activeHref === item.href ? 'bg-lf-panel text-lf-link border-r-4 border-lf-focus' : 'text-lf-secondary hover:bg-lf-hover hover:text-lf-primary'}"
                        title={collapsed ? $_(item.labelKey) : ''}
                    >
                        <svelte:component this={item.icon} size={20} class="flex-shrink-0" />
                        {#if !collapsed}
                            <span class="whitespace-nowrap">{$_(item.labelKey)}</span>
                        {/if}
                        {#if collapsed}
                            <span class="absolute left-full ml-2 px-2 py-1 bg-lf-inverse text-lf-on-inverse text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                                {$_(item.labelKey)}
                            </span>
                        {/if}
                    </a>
                </li>
            {/each}
        </ul>

        <!-- Divider -->
        <div class="my-3 mx-4 border-t border-lf-subtle"></div>

        <!-- Files & Settings Group -->
        <ul>
            {#each utilityItems as item (item.href)}
                <li>
                    <a
                        href={item.href}
                        data-testid={navigationTestId(item.href)}
                        use:guideAnchor={navigationAnchorId(item.href)}
                        on:click={() => {
                            closeSidebar();
                            resetNavDepth();
                        }}
                        class="flex items-center px-4 py-3 transition-all relative group
						{collapsed ? 'justify-center' : 'space-x-3'}
						{activeHref === item.href ? 'bg-lf-panel text-lf-link border-r-4 border-lf-focus' : 'text-lf-secondary hover:bg-lf-hover hover:text-lf-primary'}"
                        title={collapsed ? $_(item.labelKey) : ''}
                    >
                        <svelte:component this={item.icon} size={20} class="flex-shrink-0" />
                        {#if !collapsed}
                            <span class="whitespace-nowrap">{$_(item.labelKey)}</span>
                        {/if}
                        {#if collapsed}
                            <span class="absolute left-full ml-2 px-2 py-1 bg-lf-inverse text-lf-on-inverse text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                                {$_(item.labelKey)}
                            </span>
                        {/if}
                    </a>
                </li>
            {/each}
        </ul>
    </div>

    <!-- Bottom Section -->
    <div class="border-t border-lf-subtle {collapsed ? 'p-2' : 'p-4'} space-y-2">
        <!-- User Avatar & Info -->
        <a
            class="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-lf-hover transition-colors
                {collapsed ? 'justify-center' : ''}"
            data-testid="sidebar-user-avatar"
            href="/settings"
            on:click={closeSidebar}
            title={collapsed ? $auth.user?.username || $_('settings.userPreferences') : ''}
        >
            {#if avatarUrl}
                <img src={avatarUrl} alt="Avatar" class="w-8 h-8 rounded-full object-cover border border-lf-subtle flex-shrink-0" />
            {:else}
                <div class="w-8 h-8 rounded-full bg-lf-panel flex items-center justify-center flex-shrink-0">
                    <User size={16} class="text-lf-muted" />
                </div>
            {/if}
            {#if !collapsed}
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-lf-primary truncate">
                        {$auth.user?.username || $_('common.user')}
                    </div>
                    <div class="text-xs text-lf-muted truncate">
                        {$auth.user?.email || ''}
                    </div>
                </div>
            {/if}
        </a>

        <!-- Logout Button -->
        <button
            class="w-full flex items-center justify-center px-4 py-2
				bg-lf-panel hover:bg-lf-neutral rounded-lg transition-all text-sm
				{collapsed ? '' : 'space-x-2'}"
            data-testid="logout-button"
            on:click={handleLogout}
            title={collapsed ? $_('auth.logout') : ''}
        >
            <LogOut class="flex-shrink-0" size={16} />
            {#if !collapsed}
                <span class="whitespace-nowrap">{$_('auth.logout')}</span>
            {/if}
        </button>

        <!-- How safely this browser talks to LibreFolio (plan 36) -->
        <ConnectionSecurityIndicator {collapsed} onExpand={expandSidebar} />

        <!-- Version — click opens the bundled changelog (F12) -->
        {#if !collapsed}
            <button type="button" class="w-full text-center text-lf-muted hover:text-lf-primary text-xs pt-2 transition-colors cursor-pointer" title="LibreFolio {APP_VERSION} — {$_('changelog.title')}" on:click={() => (changelogOpen = true)} data-testid="sidebar-version">
                {APP_VERSION}
            </button>
        {/if}
    </div>
</nav>

<!-- Rendered OUTSIDE <nav>: the sidebar's transform/overflow-hidden would trap
     the modal's fixed positioning inside the narrow drawer (F12 round-2). -->
<ChangelogModal open={changelogOpen} onClose={() => (changelogOpen = false)} currentVersion={APP_VERSION} />
