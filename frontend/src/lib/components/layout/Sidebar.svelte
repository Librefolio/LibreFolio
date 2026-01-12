<script lang="ts">
    import {page} from '$app/stores';
    import {browser} from '$app/environment';
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {auth} from '$lib/stores/auth';
    import {ArrowRightLeft, BarChart3, BookOpen, Briefcase, Coins, LayoutDashboard, LogOut, Settings, X} from 'lucide-svelte';

    // Mobile sidebar state (exported so parent can control it)
    export let isOpen = false;

    // Collapsed state (icons only) - exported and persisted in localStorage
    export let collapsed = false;

    // Current path for active state - reactive
    $: currentPath = $page.url.pathname;

    // Load collapsed state from localStorage on mount
    onMount(() => {
        if (browser) {
            const saved = localStorage.getItem('sidebar-collapsed');
            if (saved !== null) {
                collapsed = saved === 'true';
            }
        }
    });

    // Navigation items
    const navItems = [
        {href: '/dashboard', icon: LayoutDashboard, labelKey: 'nav.dashboard'},
        {href: '/brokers', icon: Briefcase, labelKey: 'nav.brokers'},
        {href: '/assets', icon: BarChart3, labelKey: 'nav.assets'},
        {href: '/transactions', icon: ArrowRightLeft, labelKey: 'nav.transactions'},
        {href: '/fx', icon: Coins, labelKey: 'nav.fx'},
        {href: '/settings', icon: Settings, labelKey: 'nav.settings'}
    ];

    // Reactive: compute active item based on current path
    $: activeHref = navItems.find(item =>
        currentPath === item.href || currentPath.startsWith(item.href + '/')
    )?.href ?? '';

    async function handleLogout() {
        await auth.logout();
    }

    function toggleCollapsed() {
        collapsed = !collapsed;
        if (browser) {
            localStorage.setItem('sidebar-collapsed', String(collapsed));
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
                class="flex items-center space-x-3 cursor-pointer hover:opacity-80 transition-opacity"
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
    <ul class="flex-1 py-4 overflow-y-auto overflow-x-hidden">
        {#each navItems as item (item.href)}
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
                    <!-- Tooltip for collapsed mode -->
                    {#if collapsed}
						<span class="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
							{$_(item.labelKey)}
						</span>
                    {/if}
                </a>
            </li>
        {/each}
    </ul>

    <!-- Bottom Section -->
    <div class="border-t border-white/10 p-4 space-y-2">
        <!-- Documentation Link -->
        <a
                class="w-full flex items-center justify-center px-4 py-2
				hover:bg-white/10 rounded-lg transition-all text-sm
				{collapsed ? '' : 'space-x-2'}"
                href="/mkdocs/"
                target="_blank"
                title={collapsed ? $_('nav.documentation') : ''}
        >
            <BookOpen class="flex-shrink-0" size={16}/>
            {#if !collapsed}
                <span class="whitespace-nowrap">{$_('nav.documentation')}</span>
            {/if}
        </a>

        <!-- Logout Button -->
        <button
                class="w-full flex items-center justify-center px-4 py-2
				bg-white/10 hover:bg-white/20 rounded-lg transition-all text-sm
				{collapsed ? '' : 'space-x-2'}"
                on:click={handleLogout}
                title={collapsed ? $_('auth.logout') : ''}
        >
            <LogOut class="flex-shrink-0" size={16}/>
            {#if !collapsed}
                <span class="whitespace-nowrap">{$_('auth.logout')}</span>
            {/if}
        </button>
    </div>
</nav>
