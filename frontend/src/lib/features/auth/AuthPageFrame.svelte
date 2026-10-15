<script lang="ts">
    /**
     * The page around an access card — sign-in, invitation, password reset: the bar at the top right (support link,
     * theme, language, help) and the card centred below it. The animated background stays with the page, so it does not
     * restart when the page swaps its loading state for the card.
     */
    import type {Snippet} from 'svelte';
    import {Coffee} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import HelpMenu from '$lib/components/layout/HelpMenu.svelte';
    import LanguageSelector from '$lib/components/layout/LanguageSelector.svelte';
    import ThemeToggle from '$lib/components/ui/ThemeToggle.svelte';

    interface Props {
        testId?: string;
        children: Snippet;
    }

    let {testId, children}: Props = $props();
</script>

<div class="min-h-screen flex items-center justify-center p-4" data-testid={testId}>
    <!-- Language & Theme Selector (top right) -->
    <div class="fixed right-4 z-50 flex items-center space-x-2 safe-top-offset">
        <a href="https://www.buymeacoffee.com/librefolio" target="_blank" rel="noopener noreferrer" class="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-lf-hover transition-colors text-lf-donate" title={$_('help.buyMeACoffee')}>
            <span class="hidden sm:inline text-sm font-medium leading-5">{$_('help.buyMeACoffee')}</span>
            <Coffee size={20} class="flex-shrink-0" />
        </a>
        <ThemeToggle />
        <LanguageSelector />
        <HelpMenu />
    </div>

    {@render children()}
</div>
