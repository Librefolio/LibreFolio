<script lang="ts">
    /**
     * LanguageSelector - Svelte 5
     * Language selector dropdown for header.
     * Uses custom dropdown styling optimized for header placement (minimal, transparent).
     */
    import { currentLanguage } from '$lib/stores/language';
    import { LANGUAGE_OPTIONS, type SupportedLocale } from '$lib/i18n';
    import { ChevronDown } from 'lucide-svelte';

    let isOpen = $state(false);
    let containerRef = $state<HTMLDivElement | null>(null);

    // Get current language info
    let currentLangInfo = $derived(
        LANGUAGE_OPTIONS.find(l => l.code === $currentLanguage) || LANGUAGE_OPTIONS[0]
    );

    // Close on click outside
    $effect(() => {
        if (!isOpen) return;

        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef && !containerRef.contains(event.target as Node)) {
                isOpen = false;
            }
        };

        document.addEventListener('mousedown', handleClickOutside, true);
        return () => document.removeEventListener('mousedown', handleClickOutside, true);
    });

    // Close on Escape
    $effect(() => {
        if (!isOpen) return;

        const handleKeydown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                isOpen = false;
            }
        };

        document.addEventListener('keydown', handleKeydown);
        return () => document.removeEventListener('keydown', handleKeydown);
    });

    function handleLanguageChange(code: SupportedLocale) {
        currentLanguage.set(code);
        isOpen = false;
    }
</script>

<div class="relative" bind:this={containerRef} data-testid="language-selector">
    <button
        onclick={() => isOpen = !isOpen}
        class="flex items-center space-x-1 p-2 rounded-lg hover:bg-white/20 dark:hover:bg-slate-600 transition-all"
        data-testid="language-selector-button"
    >
        <span class="text-xl">{currentLangInfo.flag}</span>
        <ChevronDown size={14} class="text-gray-600 dark:text-gray-300 transition-transform {isOpen ? 'rotate-180' : ''}"/>
    </button>

    {#if isOpen}
        <div
            class="absolute right-0 mt-2 w-40 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-gray-100 dark:border-slate-700 overflow-hidden z-50"
            role="menu"
        >
            {#each LANGUAGE_OPTIONS as lang}
                <button
                    onclick={() => handleLanguageChange(lang.code)}
                    role="menuitem"
                    class="w-full flex items-center space-x-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all text-left
                           {$currentLanguage === lang.code ? 'bg-libre-green/10 dark:bg-libre-green/20' : ''}"
                >
                    <span class="text-xl">{lang.flag}</span>
                    <span class="text-sm text-gray-700 dark:text-gray-200">{lang.name}</span>
                </button>
            {/each}
        </div>
    {/if}
</div>

