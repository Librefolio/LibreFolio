<script lang="ts">
    /**
     * LanguageSelector - Svelte 5
     * Language selector dropdown for header.
     * Uses custom dropdown styling optimized for header placement (minimal, transparent).
     */
    import {availableLanguages, currentLanguage, currentLanguageFlag, currentLanguageName} from '$lib/stores/app/language';
    import type {SupportedLocale} from '$lib/i18n';
    import {ChevronDown} from 'lucide-svelte';

    interface Props {
        onOpenChange?: (open: boolean) => void;
    }

    let {onOpenChange = () => {}}: Props = $props();

    let isOpen = $state(false);
    let containerRef: HTMLDivElement | null = $state(null);

    function setOpen(next: boolean) {
        if (isOpen === next) return;
        isOpen = next;
        onOpenChange(next);
    }

    // Close on click outside
    $effect(() => {
        if (!isOpen) return;

        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef && !containerRef.contains(event.target as Node)) {
                setOpen(false);
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
                setOpen(false);
            }
        };

        document.addEventListener('keydown', handleKeydown);
        return () => document.removeEventListener('keydown', handleKeydown);
    });

    function handleLanguageChange(code: SupportedLocale) {
        currentLanguage.set(code);
        setOpen(false);
    }
</script>

<div bind:this={containerRef} class="relative" data-menu-open={isOpen ? 'true' : 'false'} data-testid="language-selector">
    <button
        class="flex items-center space-x-1 p-2 rounded-lg hover:bg-white/20 dark:hover:bg-slate-600 transition-all"
        data-testid="language-selector-button"
        aria-label={$currentLanguageName}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls="language-selector-panel"
        onclick={() => setOpen(!isOpen)}
        type="button"
    >
        <span class="text-xl emoji-flag">{$currentLanguageFlag}</span>
        <ChevronDown class="text-gray-600 dark:text-gray-300 transition-transform {isOpen ? 'rotate-180' : ''}" size={14} />
    </button>

    {#if isOpen}
        <div id="language-selector-panel" class="absolute right-0 mt-2 w-40 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-gray-100 dark:border-slate-700 overflow-hidden z-50" role="menu" data-menu-open="true" data-testid="language-selector-panel">
            {#each availableLanguages as lang}
                <button
                    onclick={() => handleLanguageChange(lang.code)}
                    role="menuitem"
                    type="button"
                    class="w-full flex items-center space-x-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all text-left
                           {$currentLanguage === lang.code ? 'bg-libre-green/10 dark:bg-libre-green/20' : ''}"
                >
                    <span class="text-xl emoji-flag">{lang.flag}</span>
                    <span class="text-sm text-gray-700 dark:text-gray-200">{lang.name}</span>
                </button>
            {/each}
        </div>
    {/if}
</div>
