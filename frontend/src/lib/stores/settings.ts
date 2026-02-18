/**
 * User Settings Store
 *
 * Manages user preferences like default currency, language, etc.
 * Loads settings from backend and caches them locally.
 *
 * Now uses Zodios client for type-safe API calls with Zod validation.
 */
import {get, writable} from 'svelte/store';
import {browser} from '$app/environment';
import {zodiosApi} from '$lib/api';
import type {UserSettings} from '$lib/types';

// Re-export type for backward compatibility
export type {UserSettings} from '$lib/types';

const defaultSettings: UserSettings = {
    language: 'en',
    base_currency: 'EUR',
    theme: 'auto'
};

/**
 * Create the user settings store
 */
function createUserSettingsStore() {
    const {subscribe, set, update} = writable<UserSettings | null>(null);

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
                // Zodios returns UserSettingsRead directly
                const settings = await zodiosApi.get_user_settings_endpoint_api_v1_settings_user_get();
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
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({[key]: value});

                update(current => {
                    const updated = {...current, [key]: value} as UserSettings;
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
            return get({subscribe});
        },

        /**
         * Set settings directly (used after login when we already have the data)
         * This updates both the store and localStorage
         */
        setDirect(settings: UserSettings): void {
            set(settings);
            if (browser) {
                localStorage.setItem('user_settings', JSON.stringify(settings));
            }
        }
    };
}

export const userSettings = createUserSettingsStore();

