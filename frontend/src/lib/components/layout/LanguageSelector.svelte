<script lang="ts">
    /**
     * LanguageSelector - Svelte 5
     * Language selector dropdown for header.
     * Uses custom dropdown styling optimized for header placement (minimal, transparent).
     * The trigger is the standard Button (85 BTN-2d): the flag in `leading`, named by the current language, a disclosure
     * (`expanded`, the turning ▾) whose panel is a menu; the rows stay `menuitem`s.
     */
    import {availableLanguages, currentLanguage, currentLanguageFlag, currentLanguageName} from '$lib/stores/app/language';
    import type {SupportedLocale} from '$lib/i18n';
    import Button from '$lib/components/ui/button/Button.svelte';

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

<div bind:this={containerRef} class="relative" data-language={$currentLanguage} data-menu-open={isOpen ? 'true' : 'false'} data-testid="language-selector">
    <Button variant="ghost-strong" display="icon" label={$currentLanguageName} expanded={isOpen} aria-haspopup="menu" aria-controls="language-selector-panel" tipPosition="bottom" onclick={() => setOpen(!isOpen)} data-testid="language-selector-button">
        {#snippet leading()}
            <span class="text-xl emoji-flag">{$currentLanguageFlag}</span>
        {/snippet}
    </Button>

    {#if isOpen}
        <div id="language-selector-panel" class="absolute right-0 mt-2 w-40 bg-lf-card rounded-lg shadow-xl shadow-lf-shadow border border-lf-raised overflow-hidden z-50" role="menu" data-menu-open="true" data-testid="language-selector-panel">
            {#each availableLanguages as lang}
                <button
                    onclick={() => handleLanguageChange(lang.code)}
                    role="menuitem"
                    type="button"
                    class="w-full flex items-center space-x-3 px-4 py-3 hover:bg-lf-hover transition-all text-left
                           {$currentLanguage === lang.code ? 'bg-lf-selected' : ''}"
                >
                    <span class="text-xl emoji-flag">{lang.flag}</span>
                    <span class="text-sm text-lf-primary">{lang.name}</span>
                </button>
            {/each}
        </div>
    {/if}
</div>
