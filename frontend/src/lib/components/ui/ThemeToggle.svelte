<script lang="ts">
    /**
     * ThemeToggle - Switch between light and dark themes
     *
     * Features:
     * - Sun/Moon icon toggle
     * - Respects prefers-color-scheme as default
     * - Saves preference to localStorage
     * - Applies theme class to html element
     */
    import { onMount } from 'svelte';
    import { Sun, Moon } from 'lucide-svelte';

    let theme: 'light' | 'dark' = 'light';
    let mounted = false;

    // Key for localStorage
    const STORAGE_KEY = 'librefolio-theme';

    function getSystemTheme(): 'light' | 'dark' {
        if (typeof window === 'undefined') return 'light';
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function getSavedTheme(): 'light' | 'dark' | null {
        if (typeof localStorage === 'undefined') return null;
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved === 'light' || saved === 'dark') return saved;
        return null;
    }

    function applyTheme(newTheme: 'light' | 'dark') {
        theme = newTheme;
        if (typeof document !== 'undefined') {
            document.documentElement.classList.remove('light', 'dark');
            document.documentElement.classList.add(newTheme);
        }
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem(STORAGE_KEY, newTheme);
        }
    }

    function toggleTheme() {
        applyTheme(theme === 'light' ? 'dark' : 'light');
    }

    onMount(() => {
        // Check saved preference first, then system preference
        const saved = getSavedTheme();
        const initial = saved ?? getSystemTheme();
        applyTheme(initial);
        mounted = true;

        // Listen for system theme changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handleChange = (e: MediaQueryListEvent) => {
            // Only apply if user hasn't explicitly set a preference
            if (!getSavedTheme()) {
                applyTheme(e.matches ? 'dark' : 'light');
            }
        };
        mediaQuery.addEventListener('change', handleChange);

        return () => {
            mediaQuery.removeEventListener('change', handleChange);
        };
    });
</script>

<button
    on:click={toggleTheme}
    data-testid="theme-toggle"
    class="p-2 rounded-lg transition-colors duration-200
           text-gray-600 dark:text-gray-300 hover:bg-white/20 dark:hover:bg-slate-600"
    aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
    title={theme === 'light' ? 'Dark mode' : 'Light mode'}
>
    {#if !mounted}
        <!-- Placeholder during SSR -->
        <div class="w-5 h-5"></div>
    {:else if theme === 'light'}
        <Moon size={20} />
    {:else}
        <Sun size={20} />
    {/if}
</button>
