<script lang="ts">
    import {_} from '$lib/i18n';
    import {onMount} from 'svelte';
    import {Book, Bug, ChevronDown, ExternalLink, HelpCircle, MessageCircle} from 'lucide-svelte';

    let isOpen = false;
    let menuRef: HTMLDivElement;

    const githubIssuesUrl = 'https://github.com/Alfystar/LibreFolio/issues';

    /** Build a MkDocs URL with locale prefix matching the app's current language. */
    function mkdocsUrl(path: string = ''): string {
        const lang = localStorage.getItem('librefolio-locale') || 'en';
        const prefix = lang !== 'en' ? `${lang}/` : '';
        return `/mkdocs/${prefix}${path}`;
    }

    function toggleMenu() {
        isOpen = !isOpen;
    }

    function handleClickOutside(event: MouseEvent) {
        if (menuRef && !menuRef.contains(event.target as Node)) {
            isOpen = false;
        }
    }

    onMount(() => {
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    });
</script>

<div bind:this={menuRef} class="relative">
    <button
            class="flex items-center space-x-1 p-2 rounded-lg hover:bg-white/20 dark:hover:bg-slate-600 transition-colors text-gray-600 dark:text-gray-300"
            on:click={toggleMenu}
            title={$_('help.helpAndSupport')}
    >
        <HelpCircle size={20}/>
        <ChevronDown class="transition-transform {isOpen ? 'rotate-180' : ''}" size={14}/>
    </button>

    {#if isOpen}
        <div class="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
            <!-- FAQ -->
            <a
                    href={mkdocsUrl('faq/')}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center space-x-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
                <Book size={18} class="text-gray-500"/>
                <span>{$_('help.faq')}</span>
            </a>

            <!-- Documentation -->
            <a
                    href={mkdocsUrl()}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center space-x-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
                <MessageCircle size={18} class="text-gray-500"/>
                <span>{$_('common.documentation')}</span>
            </a>

            <div class="border-t border-gray-100 my-1"></div>

            <!-- Report Bug on GitHub -->
            <a
                    href={githubIssuesUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center justify-between px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors group"
            >
                <div class="flex items-center space-x-3">
                    <Bug size={18} class="text-orange-500"/>
                    <span>{$_('help.reportBug')}</span>
                </div>
                <ExternalLink size={14} class="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity"/>
            </a>
        </div>
    {/if}
</div>

