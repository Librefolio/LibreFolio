<script lang="ts">
    import {page} from '$app/stores';
    import {browser} from '$app/environment';
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {auth} from '$lib/stores/auth';
    import {getUserStorage, setUserStorage} from '$lib/utils/storage';
    import {userSettings} from '$lib/stores/settings';
    import {ArrowRightLeft, BarChart3, Briefcase, Coins, Files, LayoutDashboard, LogOut, Settings, User, X} from 'lucide-svelte';
    import {APP_VERSION} from '$lib/version';

    // Mobile sidebar state (exported so parent can control it)
    export let isOpen = false;

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
        {href: '/transactions', icon: ArrowRightLeft, labelKey: 'transactions.title'}
    ];

    // Group 2: Market Data (global/shared data)
    const marketDataItems = [
        {href: '/assets', icon: BarChart3, labelKey: 'assets.title'},
        {href: '/fx', icon: Coins, labelKey: 'fx.title'}
    ];

    // Group 3: Files & Settings
    const utilityItems = [
        {href: '/files', icon: Files, labelKey: 'uploads.title'},
        {href: '/settings', icon: Settings, labelKey: 'nav.settings'}
    ];

    // All items flat for active check
    const allNavItems = [...portfolioItems, ...marketDataItems, ...utilityItems];

    // Reactive: compute active item based on current path
    $: activeHref = allNavItems.find(item =>
        currentPath === item.href || currentPath.startsWith(item.href + '/')
    )?.href ?? '';

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

    function closeSidebar() {
        isOpen = false;
    }
</script>

<!-- Mobile Overlay -->
{#if isOpen}
    <div
            class="fixed inset-0 bg-black/50 z-40 lg:hidden"
            on:click={closeSidebar}
            on:keydown={(e) => e.key === 'Escape' && closeSidebar()}
            role="button"
            tabindex="-1"
            aria-label="Close sidebar"
    ></div>
{/if}

<!-- Sidebar -->
<nav
        class="fixed left-0 top-0 h-screen bg-libre-green text-white flex flex-col z-50 transform transition-all duration-300 ease-in-out overflow-hidden
		{collapsed ? 'w-16' : 'w-64'}
		{isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0"
>
    <!-- Logo Header -->
    <div class="p-4 flex items-center border-b border-white/10 {collapsed ? 'justify-center' : 'justify-between'}">
        <button
                class="flex items-center space-x-3 cursor-pointer"
                on:click={toggleCollapsed}
                title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
            <img alt="LibreFolio" class="h-8 w-auto flex-shrink-0" src="/logo.png"/>
            {#if !collapsed}
                <span class="text-xl font-bold tracking-wide whitespace-nowrap">LibreFolio</span>
            {/if}
        </button>
        <!-- Mobile close button -->
        {#if !collapsed}
            <button class="lg:hidden p-2 hover:bg-white/10 rounded-lg" on:click={closeSidebar}>
                <X size={20}/>
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
                            on:click={closeSidebar}
                            class="flex items-center px-4 py-3 transition-all relative group
						{collapsed ? 'justify-center' : 'space-x-3'}
						{activeHref === item.href
						? 'bg-white/20 border-r-4 border-white'
						: 'hover:bg-white/10'}"
                            title={collapsed ? $_(item.labelKey) : ''}
                    >
                        <svelte:component this={item.icon} size={20} class="flex-shrink-0"/>
                        {#if !collapsed}
                            <span class="whitespace-nowrap">{$_(item.labelKey)}</span>
                        {/if}
                        {#if collapsed}
                            <span class="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                                {$_(item.labelKey)}
                            </span>
                        {/if}
                    </a>
                </li>
            {/each}
        </ul>

        <!-- Divider -->
        <div class="my-3 mx-4 border-t border-white/20"></div>

        <!-- Market Data Group -->
        <ul>
            {#each marketDataItems as item (item.href)}
                <li>
                    <a
                            href={item.href}
                            on:click={closeSidebar}
                            class="flex items-center px-4 py-3 transition-all relative group
						{collapsed ? 'justify-center' : 'space-x-3'}
						{activeHref === item.href
						? 'bg-white/20 border-r-4 border-white'
						: 'hover:bg-white/10'}"
                            title={collapsed ? $_(item.labelKey) : ''}
                    >
                        <svelte:component this={item.icon} size={20} class="flex-shrink-0"/>
                        {#if !collapsed}
                            <span class="whitespace-nowrap">{$_(item.labelKey)}</span>
                        {/if}
                        {#if collapsed}
                            <span class="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                                {$_(item.labelKey)}
                            </span>
                        {/if}
                    </a>
                </li>
            {/each}
        </ul>

        <!-- Divider -->
        <div class="my-3 mx-4 border-t border-white/20"></div>

        <!-- Files & Settings Group -->
        <ul>
            {#each utilityItems as item (item.href)}
                <li>
                    <a
                            href={item.href}
                            on:click={closeSidebar}
                            class="flex items-center px-4 py-3 transition-all relative group
						{collapsed ? 'justify-center' : 'space-x-3'}
						{activeHref === item.href
						? 'bg-white/20 border-r-4 border-white'
						: 'hover:bg-white/10'}"
                            title={collapsed ? $_(item.labelKey) : ''}
                    >
                        <svelte:component this={item.icon} size={20} class="flex-shrink-0"/>
                        {#if !collapsed}
                            <span class="whitespace-nowrap">{$_(item.labelKey)}</span>
                        {/if}
                        {#if collapsed}
                            <span class="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                                {$_(item.labelKey)}
                            </span>
                        {/if}
                    </a>
                </li>
            {/each}
        </ul>
    </div>

    <!-- Bottom Section -->
    <div class="border-t border-white/10 p-4 space-y-2">

        <!-- User Avatar & Info -->
        <a
            href="/settings"
            class="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-white/10 transition-colors
                {collapsed ? 'justify-center' : ''}"
            title={collapsed ? $auth.user?.username || $_('settings.userPreferences') : ''}
            on:click={closeSidebar}
            data-testid="sidebar-user-avatar"
        >
            {#if avatarUrl}
                <img
                    src={avatarUrl}
                    alt="Avatar"
                    class="w-8 h-8 rounded-full object-cover border border-white/30 flex-shrink-0"
                />
            {:else}
                <div class="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                    <User size={16} class="text-white/70" />
                </div>
            {/if}
            {#if !collapsed}
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-white truncate">
                        {$auth.user?.username || $_('common.user')}
                    </div>
                    <div class="text-xs text-white/50 truncate">
                        {$auth.user?.email || ''}
                    </div>
                </div>
            {/if}
        </a>

        <!-- Logout Button -->
        <button
                class="w-full flex items-center justify-center px-4 py-2
				bg-white/10 hover:bg-white/20 rounded-lg transition-all text-sm
				{collapsed ? '' : 'space-x-2'}"
                data-testid="logout-button"
                on:click={handleLogout}
                title={collapsed ? $_('auth.logout') : ''}
        >
            <LogOut class="flex-shrink-0" size={16}/>
            {#if !collapsed}
                <span class="whitespace-nowrap">{$_('auth.logout')}</span>
            {/if}
        </button>

        <!-- Version -->
        {#if !collapsed}
            <div class="text-center text-white/40 text-xs pt-2" title="LibreFolio {APP_VERSION}">
                {APP_VERSION}
            </div>
        {/if}
    </div>
</nav>
