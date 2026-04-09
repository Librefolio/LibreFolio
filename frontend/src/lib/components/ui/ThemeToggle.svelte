<script lang="ts">
    /**
     * ThemeToggle - Switch between light and dark themes
     *
     * Uses centralized themeStore for all theme logic.
     */
    import {onMount} from 'svelte';
    import {Moon, Sun} from 'lucide-svelte';
    import {
        applyTheme,
        getCurrentResolvedTheme,
        getStoredThemePreference,
        initThemeListener
    } from '$lib/stores/themeStore';

    let theme: 'light' | 'dark' = 'light';
    let mounted = false;

    function toggleTheme() {
        const newTheme = theme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
        theme = newTheme;
    }

    onMount(() => {
        theme = getCurrentResolvedTheme();
        mounted = true;

        const cleanup = initThemeListener();

        // Also react to OS changes for the icon
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handleChange = () => {
            if (getStoredThemePreference() === 'auto') {
                theme = getCurrentResolvedTheme();
            }
        };
        mediaQuery.addEventListener('change', handleChange);

        return () => {
            cleanup();
            mediaQuery.removeEventListener('change', handleChange);
        };
    });
</script>

<button
        aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        class="p-2 rounded-lg transition-colors duration-200
           text-gray-600 dark:text-gray-300 hover:bg-white/20 dark:hover:bg-slate-600"
        data-testid="theme-toggle"
        on:click={toggleTheme}
        title={theme === 'light' ? 'Dark mode' : 'Light mode'}
>
    {#if !mounted}
        <!-- Placeholder during SSR -->
        <div class="w-5 h-5"></div>
    {:else if theme === 'light'}
        <Moon size={20}/>
    {:else}
        <Sun size={20}/>
    {/if}
</button>
