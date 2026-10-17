<script lang="ts">
    /**
     * The page around an access card — sign-in, invitation, password reset: the bar at the top right (support link,
     * theme, language, help), the card centred below it, and the compact legal notice under the card (F09). The animated
     * background stays with the page, so it does not restart when the page swaps its loading state for the card.
     */
    import {onMount, type Snippet} from 'svelte';
    import {Coffee} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
    import LegalLinks from '$lib/features/legal/LegalLinks.svelte';
    import {donationsVisible} from '$lib/features/support/donations.svelte';
    import HelpMenu from '$lib/components/layout/HelpMenu.svelte';
    import LanguageSelector from '$lib/components/layout/LanguageSelector.svelte';
    import ThemeToggle from '$lib/components/ui/ThemeToggle.svelte';

    interface Props {
        testId?: string;
        children: Snippet;
    }

    let {testId, children}: Props = $props();

    // The bar and the legal line read the instance configuration: a page that does not load it (the email link's) gets
    // it here; the pages that do share the same request.
    onMount(() => {
        void instanceConfig.load();
    });
</script>

<!-- Below lg the page keeps the top clear for the row of controls (4rem: their safe-top-offset, 1rem plus the safe-area
     inset, and their height), so a card too tall to centre starts below them instead of beneath them -->
<div class="min-h-screen flex flex-col items-center justify-center p-4 pt-[calc(4rem_+_env(safe-area-inset-top,0px))] lg:pt-4" data-testid={testId}>
    <!-- Language & Theme Selector (top right): fixed on desktop; on a phone it scrolls away with the page, so it never
         sits over the card (absolute, below the shell's lg breakpoint) -->
    <div class="absolute lg:fixed right-4 z-50 flex items-center space-x-2 safe-top-offset" data-testid="auth-page-controls">
        <!-- F05: only once the server said self-hosted, so a managed instance never flashes it -->
        {#if donationsVisible()}
            <a href="https://www.buymeacoffee.com/librefolio" target="_blank" rel="noopener noreferrer" class="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-lf-hover transition-colors text-lf-donate" title={$_('help.buyMeACoffee')} data-testid="auth-donate-link">
                <span class="hidden sm:inline text-sm font-medium leading-5">{$_('help.buyMeACoffee')}</span>
                <Coffee size={20} class="flex-shrink-0" />
            </a>
        {/if}
        <ThemeToggle />
        <LanguageSelector />
        <HelpMenu />
    </div>

    {@render children()}

    <!-- The compact legal notice of the instance (F09), under the card on every sign-in page -->
    <div class="mt-6 w-full max-w-lg text-center" data-testid="auth-legal-links">
        <LegalLinks />
    </div>
</div>
