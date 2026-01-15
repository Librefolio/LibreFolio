/**
 * User Settings Store
 *
 * Manages user preferences like default currency, language, etc.
 * Loads settings from backend and caches them locally.
 */
import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';
import { api } from '$lib/api';

/**
 * User settings structure
 */
export interface UserSettings {
    default_currency: string;
    default_language: string;
    theme?: 'light' | 'dark' | 'auto';
}

const defaultSettings: UserSettings = {
    default_currency: 'EUR',
    default_language: 'en',
    theme: 'auto'
};

/**
 * Create the user settings store
 */
function createUserSettingsStore() {
    const { subscribe, set, update } = writable<UserSettings | null>(null);

    // Load from localStorage on init
    if (browser) {
        const cached = localStorage.getItem('user_settings');
        if (cached) {
            try {
                set(JSON.parse(cached));
            } catch {
                // Invalid cache, ignore
            }
        }
    }

    return {
        subscribe,

        /**
         * Load settings from backend
         */
        async load(): Promise<void> {
            try {
                const response = await api.get<{ settings: UserSettings }>('/settings/user');
                const settings = response.settings || defaultSettings;
                set(settings);

                // Cache in localStorage
                if (browser) {
                    localStorage.setItem('user_settings', JSON.stringify(settings));
                }
            } catch (e) {
                console.error('Failed to load user settings:', e);
                // Use defaults if not authenticated or error
                set(defaultSettings);
            }
        },

        /**
         * Update a single setting
         */
        async updateSetting(key: keyof UserSettings, value: string): Promise<boolean> {
            try {
                await api.patch('/settings/user', { [key]: value });

                update(current => {
                    const updated = { ...current, [key]: value } as UserSettings;
                    if (browser) {
                        localStorage.setItem('user_settings', JSON.stringify(updated));
                    }
                    return updated;
                });

                return true;
            } catch (e) {
                console.error('Failed to update setting:', e);
                return false;
            }
        },

        /**
         * Clear settings (on logout)
         */
        clear(): void {
            set(null);
            if (browser) {
                localStorage.removeItem('user_settings');
            }
        },

        /**
         * Get current value
         */
        get(): UserSettings | null {
            return get({ subscribe });
        }
    };
}

export const userSettings = createUserSettingsStore();

