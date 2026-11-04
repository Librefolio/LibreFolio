<script lang="ts">
    import {_} from '$lib/i18n';
    import {isOutsideClick} from '$lib/utils/core/clickOutside';
    import {donationsVisible} from '$lib/features/support/donations.svelte';
    import {onMount} from 'svelte';
    import {Book, Bug, ChevronDown, Coffee, Download, ExternalLink, HelpCircle, MessageCircle} from 'lucide-svelte';

    interface Props {
        onOpenChange?: (open: boolean) => void;
    }

    let {onOpenChange = () => {}}: Props = $props();

    let isOpen = $state(false);
    let menuRef: HTMLDivElement | null = $state(null);
    let deferredPrompt: any = null;
    let isStandalone = $state(false);
    let isIos = $state(false);
    let isAndroid = $state(false);
    let showIosHint = $state(false);
    let showDesktopHint = $state(false);

    const githubIssuesUrl = 'https://github.com/Librefolio/LibreFolio/issues';
    const bmcUrl = 'https://www.buymeacoffee.com/librefolio';

    /** Build a MkDocs URL with locale prefix matching the app's current language. */
    function mkdocsUrl(path: string = ''): string {
        const lang = localStorage.getItem('librefolio-locale') || 'en';
        const prefix = lang !== 'en' ? `${lang}/` : '';
        return `/mkdocs/${prefix}${path}`;
    }

    function setOpen(next: boolean) {
        if (isOpen === next) return;
        isOpen = next;
        onOpenChange(next);
    }

    function toggleMenu() {
        setOpen(!isOpen);
        showIosHint = false;
        showDesktopHint = false;
    }

    function handleClickOutside(event: MouseEvent) {
        if (isOutsideClick(event.target, (el) => !menuRef || menuRef.contains(el))) {
            setOpen(false);
            showIosHint = false;
            showDesktopHint = false;
        }
    }

    async function handleInstall() {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const {outcome} = await deferredPrompt.userChoice;
            if (outcome === 'accepted') {
                isStandalone = true;
            }
            deferredPrompt = null;
        } else if (isIos) {
            showIosHint = !showIosHint;
        } else {
            showDesktopHint = !showDesktopHint;
        }
    }

    onMount(() => {
        onOpenChange(isOpen);
        document.addEventListener('click', handleClickOutside);

        isStandalone = window.matchMedia('(display-mode: standalone)').matches || (window.navigator as any).standalone === true;

        const ua = navigator.userAgent;
        isIos = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        isAndroid = /Android/.test(ua);

        const handler = (e: Event) => {
            e.preventDefault();
            deferredPrompt = e;
        };
        window.addEventListener('beforeinstallprompt', handler);

        if ((window as any).__pwaInstallPrompt) {
            deferredPrompt = (window as any).__pwaInstallPrompt;
        }

        return () => {
            document.removeEventListener('click', handleClickOutside);
            window.removeEventListener('beforeinstallprompt', handler);
        };
    });
</script>

<div bind:this={menuRef} class="relative" data-menu-open={isOpen ? 'true' : 'false'} data-testid="help-menu">
    <button
        type="button"
        class="flex items-center space-x-1 p-2 rounded-lg hover:bg-lf-hover transition-colors text-lf-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls="help-menu-panel"
        onclick={toggleMenu}
        title={$_('help.helpAndSupport')}
        data-testid="help-menu-button"
    >
        <HelpCircle size={20} />
        <ChevronDown class="transition-transform {isOpen ? 'rotate-180' : ''}" size={14} />
    </button>

    {#if isOpen}
        <div id="help-menu-panel" class="absolute right-0 mt-2 w-56 bg-lf-card rounded-lg shadow-lg shadow-lf-shadow border border-lf-raised py-1 z-50" role="menu" data-menu-open="true" data-testid="help-menu-panel">
            {#if !isStandalone}
                <button onclick={handleInstall} class="w-full flex items-center space-x-3 px-4 py-2.5 text-sm text-lf-primary hover:bg-lf-hover transition-colors" type="button" role="menuitem">
                    <Download size={18} class="text-lf-link" />
                    <span>{$_('help.installApp')}</span>
                </button>
                {#if showIosHint}
                    <p class="px-4 py-2 text-xs text-lf-muted italic">
                        {$_('help.installAppIos')}
                    </p>
                {/if}
                {#if showDesktopHint}
                    <p class="px-4 py-2 text-xs text-lf-muted italic">
                        {isAndroid ? $_('help.installAppAndroid') : $_('help.installAppDesktop')}
                    </p>
                {/if}
                <div class="border-t border-lf-subtle my-1"></div>
            {/if}

            <a href={mkdocsUrl('community/faq/')} target="_blank" rel="noopener noreferrer" class="flex items-center space-x-3 px-4 py-2.5 text-sm text-lf-primary hover:bg-lf-hover transition-colors" role="menuitem">
                <Book size={18} class="text-lf-muted" />
                <span>{$_('help.faq')}</span>
            </a>

            <a href={mkdocsUrl()} target="_blank" rel="noopener noreferrer" class="flex items-center space-x-3 px-4 py-2.5 text-sm text-lf-primary hover:bg-lf-hover transition-colors" role="menuitem">
                <MessageCircle size={18} class="text-lf-muted" />
                <span>{$_('common.documentation')}</span>
            </a>

            <div class="border-t border-lf-subtle my-1"></div>

            <a href={githubIssuesUrl} target="_blank" rel="noopener noreferrer" class="flex items-center justify-between px-4 py-2.5 text-sm text-lf-primary hover:bg-lf-hover transition-colors group" role="menuitem">
                <div class="flex items-center space-x-3">
                    <Bug size={18} class="text-lf-warning" />
                    <span>{$_('help.reportBug')}</span>
                </div>
                <ExternalLink size={14} class="text-lf-muted opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>

            <!-- F05 (workstream A): only once the server said self-hosted -->
            {#if donationsVisible()}
                <div class="border-t border-lf-subtle my-1"></div>

                <a href={bmcUrl} target="_blank" rel="noopener noreferrer" class="flex items-center justify-between px-4 py-2.5 text-sm text-lf-primary hover:bg-lf-hover transition-colors group" role="menuitem" data-testid="help-donate-link">
                    <div class="flex items-center space-x-3">
                        <Coffee size={18} class="text-lf-donate" />
                        <span>{$_('help.buyMeACoffee')}</span>
                    </div>
                    <ExternalLink size={14} class="text-lf-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                </a>
            {/if}
        </div>
    {/if}
</div>
