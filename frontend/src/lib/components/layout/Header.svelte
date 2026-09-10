<script lang="ts">
    import {onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {Menu, Coffee} from 'lucide-svelte';
    import LanguageSelector from '$lib/components/layout/LanguageSelector.svelte';
    import ThemeToggle from '$lib/components/ui/ThemeToggle.svelte';
    import HelpMenu from '$lib/components/layout/HelpMenu.svelte';
    import {getDocumentScrollY} from '$lib/utils/layout/headerScroll';

    type ScrollState = 'visible' | 'hidden' | 'pinned';

    interface Props {
        onToggleSidebar?: () => void;
        sidebarOpen?: boolean;
        routeKey?: string;
        keepVisible?: boolean;
    }

    let {onToggleSidebar = () => {}, sidebarOpen = false, routeKey = '', keepVisible = false}: Props = $props();

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
        return keepVisible || sidebarOpen || helpMenuOpen || languageMenuOpen || modalScrollLockCount > 0 || focusPinned;
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

    function handleFocusIn(event: FocusEvent) {
        if (event.target instanceof Element && headerRef?.contains(event.target)) {
            focusPinned = true;
            syncScrollContext();
        }
    }

    function handleFocusOut() {
        cancelFocusRecheckFrame();
        focusRecheckFrame = requestAnimationFrame(() => {
            focusRecheckFrame = null;
            const activeElement = document.activeElement;
            const nextFocusPinned = activeElement instanceof Element && headerRef?.contains(activeElement) === true;
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
        sidebarOpen;
        routeKey;
        syncScrollContext();
    });
</script>

<header
    bind:this={headerRef}
    class={`sticky top-0 z-30 bg-libre-beige dark:bg-slate-900 border-b border-gray-200 dark:border-slate-700 px-4 py-3 safe-top transition-transform duration-200 motion-reduce:transition-none ${scrollState === 'hidden' ? '-translate-y-full' : 'translate-y-0'}`}
    data-testid="app-header"
    data-scroll-state={scrollState}
    data-menu-open={helpMenuOpen || languageMenuOpen ? 'true' : 'false'}
    data-sidebar-open={sidebarOpen ? 'true' : 'false'}
    data-modal-open={modalScrollLockCount > 0 ? 'true' : 'false'}
    data-help-menu-open={helpMenuOpen ? 'true' : 'false'}
    data-language-menu-open={languageMenuOpen ? 'true' : 'false'}
>
    <div class="flex items-center justify-between">
        <button aria-label="Toggle menu" class="lg:hidden p-2 rounded-lg transition-colors" data-testid="mobile-menu-toggle" onclick={onToggleSidebar}>
            <Menu class="text-libre-dark dark:text-gray-200" size={24} />
        </button>

        <div class="hidden lg:block"></div>

        <div class="flex items-center space-x-2">
            <a href="https://www.buymeacoffee.com/librefolio" target="_blank" rel="noopener noreferrer" class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/20 dark:hover:bg-slate-600 transition-colors text-amber-600 dark:text-amber-400" title={$_('help.buyMeACoffee')}>
                <span class="hidden sm:inline text-sm font-medium leading-5">{$_('help.buyMeACoffee')}</span>
                <Coffee size={20} class="flex-shrink-0" />
            </a>
            <ThemeToggle />
            <LanguageSelector onOpenChange={handleLanguageOpenChange} />
            <HelpMenu onOpenChange={handleHelpMenuOpenChange} />
        </div>
    </div>
</header>
