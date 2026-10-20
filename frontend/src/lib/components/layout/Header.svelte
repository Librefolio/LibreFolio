<script lang="ts">
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {Menu, Coffee} from 'lucide-svelte';
    import LanguageSelector from '$lib/components/layout/LanguageSelector.svelte';
    import ThemeToggle from '$lib/components/ui/ThemeToggle.svelte';
    import PrivacyToggle from '$lib/components/ui/PrivacyToggle.svelte';
    import HelpMenu from '$lib/components/layout/HelpMenu.svelte';
    import {getDocumentScrollY} from '$lib/utils/layout/headerScroll';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';
    import {connectionSecurity} from '$lib/stores/app/connectionSecurityStore';
    import {auth} from '$lib/stores/app/auth';
    import {securityChecks} from '$lib/features/settings/security/securityChecks.svelte';
    import {donationsVisible} from '$lib/features/support/donations.svelte';

    type ScrollState = 'visible' | 'hidden' | 'pinned';

    interface Props {
        onToggleSidebar?: () => void;
        sidebarOpen?: boolean;
        routeKey?: string;
        keepVisible?: boolean;
        guideActive?: boolean;
    }

    let {onToggleSidebar = () => {}, sidebarOpen = false, routeKey = '', keepVisible = false, guideActive = false}: Props = $props();

    // On a phone the burger stands for the sidebar's connection line: an insecure connection (plan 36) or an
    // administrator's security warnings (N69-1) mark it, the worse first. The sidebar's line loads the checks.
    const insecure = $derived($connectionSecurity.level === 'insecure');
    const menuAttention = $derived($auth.user?.is_superuser === true ? securityChecks.attentionCount : 0);
    const menuDot = $derived(insecure || (menuAttention > 0 && securityChecks.attentionSeverity === 'error') ? 'error' : menuAttention > 0 ? 'warning' : null);
    const menuLabel = $derived(['Toggle menu', insecure ? $_('connectionSecurity.level.insecure') : null, menuAttention > 0 ? $_('connectionSecurity.attention', {values: {count: menuAttention}}) : null].filter(Boolean).join(' — '));

    const HIDE_SCROLL_THRESHOLD = 8;
    const SHOW_SCROLL_THRESHOLD = 4;

    let headerRef: HTMLElement | null = $state(null);
    let helpMenuOpen = $state(false);
    let languageMenuOpen = $state(false);
    let modalScrollLockCount = $state(0);
    let focusPinned = $state(false);
    let headerHeight = $state(0);
    let scrollState: ScrollState = $state('visible');

    let lastScrollY = 0;
    let downAccumulator = 0;
    let upAccumulator = 0;
    let scrollFrame: number | null = null;
    let focusRecheckFrame: number | null = null;
    let headerResizeObserver: ResizeObserver | null = null;
    let modalObserver: MutationObserver | null = null;

    function isPinned(): boolean {
        return guideActive || keepVisible || sidebarOpen || helpMenuOpen || languageMenuOpen || modalScrollLockCount > 0 || focusPinned;
    }

    function cancelScrollFrame() {
        if (scrollFrame != null) {
            cancelAnimationFrame(scrollFrame);
            scrollFrame = null;
        }
    }

    function cancelFocusRecheckFrame() {
        if (focusRecheckFrame != null) {
            cancelAnimationFrame(focusRecheckFrame);
            focusRecheckFrame = null;
        }
    }

    function readHeaderHeight() {
        if (!headerRef) return 0;
        return Math.ceil(headerRef.getBoundingClientRect().height);
    }

    function resetScrollBaseline() {
        cancelScrollFrame();
        lastScrollY = getDocumentScrollY();
        downAccumulator = 0;
        upAccumulator = 0;
    }

    function syncScrollContext() {
        resetScrollBaseline();
        scrollState = isPinned() ? 'pinned' : 'visible';
    }

    function scheduleScrollFrame() {
        if (scrollFrame != null) return;
        scrollFrame = requestAnimationFrame(handleScrollFrame);
    }

    function handleScrollFrame() {
        scrollFrame = null;

        const currentScrollY = getDocumentScrollY();
        if (isPinned()) {
            lastScrollY = currentScrollY;
            downAccumulator = 0;
            upAccumulator = 0;
            scrollState = 'pinned';
            return;
        }

        if (currentScrollY <= headerHeight) {
            lastScrollY = currentScrollY;
            downAccumulator = 0;
            upAccumulator = 0;
            scrollState = 'visible';
            return;
        }

        const delta = currentScrollY - lastScrollY;
        if (delta > 0) {
            downAccumulator += delta;
            upAccumulator = 0;
            if (scrollState !== 'hidden' && downAccumulator >= HIDE_SCROLL_THRESHOLD) {
                scrollState = 'hidden';
            }
        } else if (delta < 0) {
            upAccumulator += -delta;
            downAccumulator = 0;
            if (scrollState === 'hidden' && upAccumulator >= SHOW_SCROLL_THRESHOLD) {
                scrollState = 'visible';
            }
        }

        lastScrollY = currentScrollY;
    }

    function handleScroll() {
        scheduleScrollFrame();
    }

    /**
     * Keyboard focus inside the header pins it. The focus a mouse click leaves on a button does not (Chrome keeps it
     * there): after a click on the theme toggle the header must still hide on scroll. An engine that cannot read
     * `:focus-visible` keeps the old rule, any focus.
     */
    function focusPinsHeader(element: unknown): boolean {
        if (!(element instanceof Element) || headerRef?.contains(element) !== true) return false;
        try {
            return element.matches(':focus-visible');
        } catch {
            return true;
        }
    }

    function handleFocusIn(event: FocusEvent) {
        if (focusPinsHeader(event.target)) {
            focusPinned = true;
            syncScrollContext();
        }
    }

    function handleFocusOut() {
        cancelFocusRecheckFrame();
        focusRecheckFrame = requestAnimationFrame(() => {
            focusRecheckFrame = null;
            const nextFocusPinned = focusPinsHeader(document.activeElement);
            if (nextFocusPinned !== focusPinned) {
                focusPinned = nextFocusPinned;
                syncScrollContext();
            }
        });
    }

    function handleHelpMenuOpenChange(open: boolean) {
        helpMenuOpen = open;
        syncScrollContext();
    }

    function handleLanguageOpenChange(open: boolean) {
        languageMenuOpen = open;
        syncScrollContext();
    }

    function updateModalScrollLockCount() {
        const body = document.body;
        const nextCount = Number(body.dataset.modalScrollLockCount || '0');
        if (nextCount === modalScrollLockCount) return;
        modalScrollLockCount = nextCount;
        syncScrollContext();
    }

    onMount(() => {
        headerHeight = readHeaderHeight();
        syncScrollContext();

        const body = document.body;
        updateModalScrollLockCount();

        headerResizeObserver = new ResizeObserver(() => {
            const nextHeight = readHeaderHeight();
            if (nextHeight !== headerHeight) {
                headerHeight = nextHeight;
            }
            syncScrollContext();
        });
        if (headerRef) headerResizeObserver.observe(headerRef);

        modalObserver = new MutationObserver(updateModalScrollLockCount);
        modalObserver.observe(body, {
            attributes: true,
            attributeFilter: ['data-modal-scroll-lock-count'],
        });

        window.addEventListener('scroll', handleScroll, {passive: true});
        window.addEventListener('resize', syncScrollContext);
        document.addEventListener('focusin', handleFocusIn, true);
        document.addEventListener('focusout', handleFocusOut, true);

        return () => {
            window.removeEventListener('scroll', handleScroll);
            window.removeEventListener('resize', syncScrollContext);
            document.removeEventListener('focusin', handleFocusIn, true);
            document.removeEventListener('focusout', handleFocusOut, true);
            headerResizeObserver?.disconnect();
            modalObserver?.disconnect();
            cancelScrollFrame();
            cancelFocusRecheckFrame();
        };
    });

    $effect(() => {
        keepVisible;
        guideActive;
        sidebarOpen;
        routeKey;
        syncScrollContext();
    });
</script>

<header
    bind:this={headerRef}
    class={`sticky top-0 z-30 bg-lf-header text-lf-primary border-b border-lf-subtle px-4 py-3 safe-top transition-transform duration-200 motion-reduce:transition-none ${scrollState === 'hidden' ? '-translate-y-full' : 'translate-y-0'}`}
    data-testid="app-header"
    data-scroll-state={scrollState}
    data-menu-open={helpMenuOpen || languageMenuOpen ? 'true' : 'false'}
    data-sidebar-open={sidebarOpen ? 'true' : 'false'}
    data-modal-open={modalScrollLockCount > 0 ? 'true' : 'false'}
    data-help-menu-open={helpMenuOpen ? 'true' : 'false'}
    data-language-menu-open={languageMenuOpen ? 'true' : 'false'}
    data-guide-active={guideActive ? 'true' : 'false'}
>
    <div class="flex items-center justify-between">
        <!-- The sidebar's connection line hides behind the burger on a phone: an insecure level, or an administrator's
             security warnings, mark it (plan 36, N69-1). -->
        <button aria-label={menuLabel} class="relative lg:hidden p-2 rounded-lg transition-colors hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus" data-testid="mobile-menu-toggle" use:guideAnchor={'nav.toggle.mobile'} onclick={onToggleSidebar}>
            <Menu class="text-lf-primary" size={24} />
            {#if menuDot}
                <span class="absolute top-1 right-1 h-2.5 w-2.5 rounded-full ring-2 ring-lf-header {menuDot === 'error' ? 'bg-lf-danger' : 'bg-lf-warning'}" data-testid="mobile-menu-security-dot" data-severity={menuDot} aria-hidden="true"></span>
            {/if}
        </button>

        <div class="hidden lg:block"></div>

        <div class="flex items-center space-x-2">
            <!-- F05 (workstream A): only once the server said self-hosted -->
            {#if donationsVisible()}
                <a
                    href="https://www.buymeacoffee.com/librefolio"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-lf-hover transition-colors text-lf-donate focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
                    data-testid="header-donate-link"
                    title={$_('help.buyMeACoffee')}
                >
                    <span class="hidden sm:inline text-sm font-medium leading-5">{$_('help.buyMeACoffee')}</span>
                    <Coffee size={20} class="flex-shrink-0" />
                </a>
            {/if}
            <PrivacyToggle />
            <ThemeToggle />
            <LanguageSelector onOpenChange={handleLanguageOpenChange} />
            <HelpMenu onOpenChange={handleHelpMenuOpenChange} />
        </div>
    </div>
</header>
