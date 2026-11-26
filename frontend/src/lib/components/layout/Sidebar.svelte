<script lang="ts">
    import {page} from '$app/stores';
    import {browser} from '$app/environment';
    import {onDestroy, onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {auth} from '$lib/stores/app/auth';
    import {getUserStorage, setUserStorage} from '$lib/utils/storage';
    import {userSettings} from '$lib/stores/app/settings';
    import {resetNavDepth} from '$lib/stores/app/navigationStore';
    import {ArrowRightLeft, BarChart3, Briefcase, Coins, Files, LayoutDashboard, LogOut, Settings, User, Wrench} from 'lucide-svelte';
    import {APP_VERSION} from '$lib/version';
    import {guideAnchor, guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
    import Button from '$lib/components/ui/button/Button.svelte';
    import CloseButton from '$lib/components/ui/button/CloseButton.svelte';
    import ChangelogModal from './ChangelogModal.svelte';
    import {changelogModal} from '$lib/features/changelog/changelogModalStore.svelte';
    import ConnectionSecurityIndicator from './ConnectionSecurityIndicator.svelte';
    import LegalLinks from '$lib/features/legal/LegalLinks.svelte';

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

    // The app's one changelog window lives as long as the sidebar that mounts it (A-CL1)
    onDestroy(() => changelogModal.close());

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

    // The collapse toggle is a Button, and a component takes no action: it registers its own element as the guide's
    // anchor of the navigation step (the target is the button itself, `sidebar-collapse-toggle`).
    let collapseToggle: HTMLElement | undefined;
    let releaseToggleAnchor: (() => void) | null = null;

    function anchorCollapseToggle(element: HTMLElement | undefined) {
        releaseToggleAnchor?.();
        releaseToggleAnchor = element ? guideAnchors.register('nav.toggle.desktop', element) : null;
    }

    $: anchorCollapseToggle(collapseToggle);
    onDestroy(() => releaseToggleAnchor?.());

    function navigationAnchorId(href: string): string {
        return `nav.${href.slice(1).replaceAll('/', '.')}`;
    }

    function navigationTestId(href: string): string {
        return `nav-${href.slice(1).replaceAll('/', '-')}`;
    }
</script>

<!-- Mobile Overlay -->
{#if isOpen}
    <div class="fixed inset-0 bg-lf-overlay z-40 lg:hidden" on:click={closeSidebar} on:keydown={(e) => e.key === 'Escape' && closeSidebar()} role="button" tabindex="-1" aria-label={$_('nav.closeSidebar')}></div>
{/if}

<!-- Sidebar -->
<nav
    class="fixed left-0 top-0 h-screen bg-lf-bar text-lf-bar-text flex flex-col z-50 transform transition-all duration-300 ease-in-out overflow-hidden safe-top
		{collapsed ? 'w-16' : 'w-64'}
		{isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0"
>
    <!-- Logo Header: one with the green sidebar (D-T17); the logo keeps its white tile (N1). The row's padding plus the
         toggle's own keep the logo where it was (16 px from the edges). -->
    <div class="px-1 py-2 flex items-center text-lf-on-brand {collapsed ? 'justify-center' : 'justify-between'}" data-testid="sidebar-brand">
        <!-- The logo is the collapse toggle: named by its action, the wordmark is its rich word (85 BTN-2d, C1 + C6). The
             wordmark is in view, so the action shows as the help of a mouse rest; collapsed, the name itself shows. -->
        <Button
            bind:element={collapseToggle}
            variant="bar-ghost"
            label={collapsed ? $_('nav.expandSidebar') : $_('nav.collapseSidebar')}
            display={collapsed ? 'icon' : 'icon-text'}
            help={collapsed ? undefined : $_('nav.collapseSidebar')}
            tipPosition="right"
            onclick={toggleCollapsed}
            data-testid="sidebar-collapse-toggle"
        >
            {#snippet leading()}
                <span class="w-8 h-8 flex-shrink-0 rounded-lg flex items-center justify-center p-1 bg-lf-logo">
                    <img alt="" class="max-w-full max-h-full object-contain" src="/logo.png" />
                </span>
            {/snippet}
            {#snippet children()}
                <span class="ml-1.5 text-xl font-bold tracking-wide text-lf-on-brand">LibreFolio</span>
            {/snippet}
        </Button>
        <!-- Mobile close button -->
        {#if !collapsed}
            <div class="lg:hidden pr-2.5">
                <CloseButton variant="bar-ghost" size="lg" label={$_('nav.closeSidebar')} onclick={closeSidebar} />
            </div>
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
                        class="flex items-center px-4 py-3 transition-all relative group focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-lf-bar-focus
						{collapsed ? 'justify-center' : 'space-x-3'}
						{activeHref === item.href ? 'bg-lf-bar-active text-lf-on-bar-active border-l-4 border-lf-bar-indicator' : 'text-lf-bar-text hover:bg-lf-bar-hover'}"
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
        <div class="my-3 mx-4 border-t border-lf-bar-line"></div>

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
                        class="flex items-center px-4 py-3 transition-all relative group focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-lf-bar-focus
						{collapsed ? 'justify-center' : 'space-x-3'}
						{activeHref === item.href ? 'bg-lf-bar-active text-lf-on-bar-active border-l-4 border-lf-bar-indicator' : 'text-lf-bar-text hover:bg-lf-bar-hover'}"
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
        <div class="my-3 mx-4 border-t border-lf-bar-line"></div>

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
                        class="flex items-center px-4 py-3 transition-all relative group focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-lf-bar-focus
						{collapsed ? 'justify-center' : 'space-x-3'}
						{activeHref === item.href ? 'bg-lf-bar-active text-lf-on-bar-active border-l-4 border-lf-bar-indicator' : 'text-lf-bar-text hover:bg-lf-bar-hover'}"
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
    <div class="border-t border-lf-bar-line {collapsed ? 'p-2' : 'p-4'} space-y-2">
        <!-- User Avatar & Info -->
        <a
            class="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-lf-bar-hover transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-lf-bar-focus
                {collapsed ? 'justify-center' : ''}"
            data-testid="sidebar-user-avatar"
            href="/settings"
            on:click={closeSidebar}
            title={collapsed ? $auth.user?.username || $_('settings.userPreferences') : ''}
        >
            {#if avatarUrl}
                <img src={avatarUrl} alt="Avatar" class="w-8 h-8 rounded-full object-cover border border-lf-bar-line flex-shrink-0" />
            {:else}
                <div class="w-8 h-8 rounded-full bg-lf-bar-active flex items-center justify-center flex-shrink-0">
                    <User size={16} class="text-lf-bar-text" />
                </div>
            {/if}
            {#if !collapsed}
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-lf-on-bar-active truncate">
                        {$auth.user?.username || $_('common.user')}
                    </div>
                    <div class="text-xs text-lf-bar-muted truncate">
                        {$auth.user?.email || ''}
                    </div>
                </div>
            {/if}
        </a>

        <!-- Logout Button: the word hides while the sidebar is collapsed, the name then shows by long press, rest or Tab -->
        <Button variant="bar-solid" icon={LogOut} label={$_('auth.logout')} display="auto" hideWord={collapsed} tipPosition="right" class="w-full" onclick={handleLogout} data-testid="logout-button" />

        <!-- How safely this browser talks to LibreFolio (plan 36) -->
        <ConnectionSecurityIndicator {collapsed} onExpand={expandSidebar} />

        <!-- Version — click opens the bundled changelog (F12) -->
        {#if !collapsed}
            <Button variant="bar-link" size="sm" label="LibreFolio {APP_VERSION} — {$_('changelog.title')}" shortLabel={APP_VERSION} class="w-full mt-2" onclick={() => changelogModal.show()} data-testid="sidebar-version" />
            <!-- The compact legal notice of the instance (F09, workstream A) -->
            <div class="px-2 text-center" data-testid="sidebar-legal-links">
                <LegalLinks tone="bar" />
            </div>
        {/if}
    </div>
</nav>

<!-- The app's one changelog window (A-CL1): every entry point opens it through changelogModal.show().
     Rendered OUTSIDE <nav>: the sidebar's transform/overflow-hidden would trap
     the modal's fixed positioning inside the narrow drawer (F12 round-2). -->
<ChangelogModal open={changelogModal.open} onClose={changelogModal.close} currentVersion={APP_VERSION} />
