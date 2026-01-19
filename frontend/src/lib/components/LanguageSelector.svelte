<script lang="ts">
    import {currentLanguage, currentLanguageFlag} from '$lib/stores/language';
    import {LANGUAGE_OPTIONS, type SupportedLocale} from '$lib/i18n';
    import {ChevronDown} from 'lucide-svelte';

    // Position variant: 'dropdown' for header usage, 'inline' for sidebar
    export let variant: 'dropdown' | 'inline' = 'dropdown';

    let showMenu = false;

    function handleLanguageChange(code: SupportedLocale) {
        currentLanguage.set(code);
        showMenu = false;
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            showMenu = false;
        }
    }
</script>

{#if variant === 'dropdown'}
    <!-- Dropdown style (for header/top-right) -->
    <div class="relative">
        <button
                on:click={() => showMenu = !showMenu}
                class="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-white/20 dark:hover:bg-slate-600 transition-all"
        >
            <span class="text-xl">{$currentLanguageFlag}</span>
            <ChevronDown size={16} class="text-gray-600 dark:text-gray-300"/>
        </button>

        {#if showMenu}
            <div
                    class="absolute right-0 mt-2 w-40 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-gray-100 dark:border-slate-700 overflow-hidden z-50"
                    on:keydown={handleKeydown}
                    role="menu"
                    tabindex="-1"
            >
                {#each LANGUAGE_OPTIONS as lang}
                    <button
                            on:click={() => handleLanguageChange(lang.code)}
                            class="w-full flex items-center space-x-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-700 transition-all text-left
							{$currentLanguage === lang.code ? 'bg-libre-green/10 dark:bg-libre-green/20' : ''}"
                            role="menuitem"
                    >
                        <span class="text-xl">{lang.flag}</span>
                        <span class="text-sm text-gray-700 dark:text-gray-200">{lang.name}</span>
                    </button>
                {/each}
            </div>
        {/if}
    </div>

    <!-- Click outside to close -->
    {#if showMenu}
        <div
                class="fixed inset-0 z-40"
                on:click={() => showMenu = false}
                on:keydown={handleKeydown}
                role="button"
                tabindex="-1"
        ></div>
    {/if}

{:else}
    <!-- Inline select style (for sidebar) -->
    <select
            class="w-full bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-sm
			appearance-none cursor-pointer hover:bg-white/20 transition-all"
            value={$currentLanguage}
            on:change={(e) => handleLanguageChange(e.currentTarget.value as SupportedLocale)}
    >
        {#each LANGUAGE_OPTIONS as lang}
            <option value={lang.code} class="bg-libre-green text-white">
                {lang.flag} {lang.name}
            </option>
        {/each}
    </select>
{/if}

