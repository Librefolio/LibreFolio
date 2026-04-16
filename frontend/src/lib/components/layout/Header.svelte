<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {Menu, Coffee} from 'lucide-svelte';
    import LanguageSelector from '$lib/components/layout/LanguageSelector.svelte';
    import ThemeToggle from '$lib/components/ui/ThemeToggle.svelte';
    import HelpMenu from '$lib/components/layout/HelpMenu.svelte';

    const dispatch = createEventDispatcher();

    function toggleSidebar() {
        dispatch('toggleSidebar');
    }
</script>

<header class="sticky top-0 z-30 bg-libre-beige dark:bg-slate-900 border-b border-gray-200 dark:border-slate-700 px-4 py-3">
    <div class="flex items-center justify-between">
        <!-- Mobile menu button -->
        <button
                aria-label="Toggle menu"
                class="lg:hidden p-2 rounded-lg transition-colors"
                data-testid="mobile-menu-toggle"
                on:click={toggleSidebar}
        >
            <Menu class="text-libre-dark dark:text-gray-200" size={24}/>
        </button>

        <!-- Spacer for desktop (sidebar visible) -->
        <div class="hidden lg:block"></div>

        <!-- Right side - Theme Toggle, Language, Help Menu -->
        <div class="flex items-center space-x-2">
            <a
                    href="https://www.buymeacoffee.com/librefolio"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/20 dark:hover:bg-slate-600 transition-colors text-amber-600 dark:text-amber-400"
                    title={$_('help.buyMeACoffee')}
            >
                <span class="hidden sm:inline text-sm font-medium leading-5">{$_('help.buyMeACoffee')}</span>
                <Coffee size={20} class="flex-shrink-0"/>
            </a>
            <ThemeToggle/>
            <LanguageSelector/>
            <HelpMenu/>
        </div>
    </div>
</header>
