/**
 * Centralized theme management store.
 *
 * Single source of truth for dark/light mode. Uses localStorage key
 * 'librefolio-theme' with values: 'light' | 'dark' | '' (empty = auto/system).
 *
 * Usage:
 *   import { applyTheme, getCurrentResolvedTheme, getStoredThemePreference, initThemeListener } from '$lib/stores/themeStore';
 */

const STORAGE_KEY = 'librefolio-theme';

export type ThemePreference = 'light' | 'dark' | 'auto';
export type ResolvedTheme = 'light' | 'dark';

/**
 * Get the OS-level preferred color scheme.
 */
function getSystemTheme(): ResolvedTheme {
    if (typeof window === 'undefined') return 'light';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Read the stored preference from localStorage.
 * Returns 'auto' if nothing saved or value is empty.
 */
export function getStoredThemePreference(): ThemePreference {
    if (typeof localStorage === 'undefined') return 'auto';
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    return 'auto';
}

/**
 * Resolve the current effective theme (what the user actually sees).
 * If preference is 'auto', delegates to the OS setting.
 */
export function getCurrentResolvedTheme(): ResolvedTheme {
    const pref = getStoredThemePreference();
    if (pref === 'auto') return getSystemTheme();
    return pref;
}

/**
 * Apply a theme preference: update localStorage, set class on <html>.
 *
 * @param mode - 'light' | 'dark' | 'auto'
 */
export function applyTheme(mode: ThemePreference): void {
    if (typeof localStorage !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, mode === 'auto' ? '' : mode);
    }
    if (typeof document !== 'undefined') {
        const resolved: ResolvedTheme = mode === 'auto' ? getSystemTheme() : mode;
        document.documentElement.classList.remove('light', 'dark');
        document.documentElement.classList.add(resolved);
        // Update PWA theme-color meta tag for title bar (matches sidebar color)
        const themeColor = resolved === 'dark' ? '#156534' : '#1a4031';
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) meta.setAttribute('content', themeColor);
    }
}

/**
 * Initialize the OS prefers-color-scheme listener.
 * When the OS switches day/night, re-apply theme only if preference is 'auto'.
 *
 * @returns cleanup function to remove the listener
 */
export function initThemeListener(): () => void {
    if (typeof window === 'undefined') return () => {};

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (_e: MediaQueryListEvent) => {
        if (getStoredThemePreference() === 'auto') {
            applyTheme('auto');
        }
    };
    mediaQuery.addEventListener('change', handleChange);

    return () => {
        mediaQuery.removeEventListener('change', handleChange);
    };
}
