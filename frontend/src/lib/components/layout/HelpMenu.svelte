<script lang="ts">
    import {_} from '$lib/i18n';
    import {onMount} from 'svelte';
    import {Book, Bug, ChevronDown, Coffee, Download, ExternalLink, HelpCircle, MessageCircle} from 'lucide-svelte';

    let isOpen = $state(false);
    let menuRef: HTMLDivElement;
    let deferredPrompt: any = null;
    let isStandalone = $state(false);
    let isIos = $state(false);
    let showIosHint = $state(false);
    let showDesktopHint = $state(false);

    const githubIssuesUrl = 'https://github.com/Alfystar/LibreFolio/issues';
    const bmcUrl = 'https://www.buymeacoffee.com/librefolio';

    /** Build a MkDocs URL with locale prefix matching the app's current language. */
    function mkdocsUrl(path: string = ''): string {
        const lang = localStorage.getItem('librefolio-locale') || 'en';
        const prefix = lang !== 'en' ? `${lang}/` : '';
        return `/mkdocs/${prefix}${path}`;
    }

    function toggleMenu() {
        isOpen = !isOpen;
        showIosHint = false;
        showDesktopHint = false;
    }

    function handleClickOutside(event: MouseEvent) {
        if (menuRef && !menuRef.contains(event.target as Node)) {
            isOpen = false;
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
            // Desktop browser without captured prompt — show hint
            showDesktopHint = !showDesktopHint;
        }
    }

    onMount(() => {
        document.addEventListener('click', handleClickOutside);

        // Detect standalone mode
        isStandalone = window.matchMedia('(display-mode: standalone)').matches
            || (window.navigator as any).standalone === true;

        // Detect iOS
        const ua = navigator.userAgent;
        isIos = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

        // Listen for beforeinstallprompt (Chrome/Android/Edge)
        const handler = (e: Event) => {
            e.preventDefault();
            deferredPrompt = e;
        };
        window.addEventListener('beforeinstallprompt', handler);

        // Check if event already fired before mount (race condition workaround)
        if ((window as any).__pwaInstallPrompt) {
            deferredPrompt = (window as any).__pwaInstallPrompt;
        }

        return () => {
            document.removeEventListener('click', handleClickOutside);
            window.removeEventListener('beforeinstallprompt', handler);
        };
    });
</script>

<div bind:this={menuRef} class="relative">
    <button class="flex items-center space-x-1 p-2 rounded-lg hover:bg-white/20 dark:hover:bg-slate-600 transition-colors text-gray-600 dark:text-gray-300" onclick={toggleMenu} title={$_('help.helpAndSupport')}>
        <HelpCircle size={20} />
        <ChevronDown class="transition-transform {isOpen ? 'rotate-180' : ''}" size={14} />
    </button>

    {#if isOpen}
        <div class="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 dark:bg-slate-800 dark:border-slate-700 py-1 z-50">
            <!-- Install App (always shown unless already standalone) -->
            {#if !isStandalone}
                <button onclick={handleInstall} class="w-full flex items-center space-x-3 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors">
                    <Download size={18} class="text-libre-green dark:text-green-400" />
                    <span>{$_('help.installApp')}</span>
                </button>
                {#if showIosHint}
                    <p class="px-4 py-2 text-xs text-gray-500 dark:text-gray-400 italic">
                        {$_('help.installAppIos')}
                    </p>
                {/if}
                {#if showDesktopHint}
                    <p class="px-4 py-2 text-xs text-gray-500 dark:text-gray-400 italic">
                        {$_('help.installAppDesktop')}
                    </p>
                {/if}
                <div class="border-t border-gray-100 dark:border-slate-600 my-1"></div>
            {/if}

            <!-- FAQ -->
            <a href={mkdocsUrl('community/faq/')} target="_blank" rel="noopener noreferrer" class="flex items-center space-x-3 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors">
                <Book size={18} class="text-gray-500 dark:text-gray-400" />
                <span>{$_('help.faq')}</span>
            </a>

            <!-- Documentation -->
            <a href={mkdocsUrl()} target="_blank" rel="noopener noreferrer" class="flex items-center space-x-3 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors">
                <MessageCircle size={18} class="text-gray-500 dark:text-gray-400" />
                <span>{$_('common.documentation')}</span>
            </a>

            <div class="border-t border-gray-100 dark:border-slate-600 my-1"></div>

            <!-- Report Bug on GitHub -->
            <a href={githubIssuesUrl} target="_blank" rel="noopener noreferrer" class="flex items-center justify-between px-4 py-2.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors group">
                <div class="flex items-center space-x-3">
                    <Bug size={18} class="text-orange-500" />
                    <span>{$_('help.reportBug')}</span>
                </div>
                <ExternalLink size={14} class="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>

            <div class="border-t border-gray-100 dark:border-slate-600 my-1"></div>

            <!-- Buy Me a Coffee -->
            <a href={bmcUrl} target="_blank" rel="noopener noreferrer" class="flex items-center justify-between px-4 py-2.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors group">
                <div class="flex items-center space-x-3">
                    <Coffee size={18} class="text-amber-600" />
                    <span>{$_('help.buyMeACoffee')}</span>
                </div>
                <ExternalLink size={14} class="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>
        </div>
    {/if}
</div>
