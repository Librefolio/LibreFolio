<script lang="ts">
    /**
     * ThemeToggle - Switch between light and dark themes
     *
     * Uses centralized themeStore for all theme logic. The standard icon button (85 BTN-2a): one name, the action it
     * performs («Switch to dark theme»), by long press, rest or Tab — no browser `title` saying something else (D14).
     */
    import {onMount} from 'svelte';
    import {Moon, Sun} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import Button from '$lib/components/ui/button/Button.svelte';
    import {applyTheme, getCurrentResolvedTheme, getStoredThemePreference, initThemeListener} from '$lib/stores/app/themeStore';

    /** Read at once in the browser, so the button has its icon from the first frame. */
    let theme = $state<'light' | 'dark'>(typeof window === 'undefined' ? 'light' : getCurrentResolvedTheme());

    function toggleTheme() {
        const newTheme = theme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
        theme = newTheme;
    }

    onMount(() => {
        theme = getCurrentResolvedTheme();

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

<Button label={theme === 'light' ? $_('header.theme.switchToDark') : $_('header.theme.switchToLight')} icon={theme === 'light' ? Moon : Sun} display="icon" variant="ghost-strong" size="lg" onclick={toggleTheme} data-testid="theme-toggle" />
