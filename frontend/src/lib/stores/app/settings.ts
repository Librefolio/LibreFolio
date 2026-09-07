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
import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, registerClientSessionReset} from '$lib/stores/app/clientSession';

// Re-export type for backward compatibility
export type {UserSettings} from '$lib/types';

const defaultSettings: UserSettings = {
    language: 'en',
    base_currency: 'EUR',
    theme: 'auto',
    avatar_url: null,
};

const LEGACY_STORAGE_KEY = 'user_settings';

function storageKey(): string | null {
    const userId = getClientSessionUserId();
    return userId ? `lf_${userId}_user_settings` : null;
}

function persist(settings: UserSettings): void {
    if (!browser) return;
    const key = storageKey();
    if (key) localStorage.setItem(key, JSON.stringify(settings));
    localStorage.removeItem(LEGACY_STORAGE_KEY);
}

/**
 * Create the user settings store
 */
function createUserSettingsStore() {
    const {subscribe, set, update} = writable<UserSettings | null>(null);

    return {
        subscribe,

        /**
         * Load settings from backend
         */
        async load(): Promise<void> {
            const sessionGeneration = getClientSessionGeneration();
            try {
                // Zodios returns UserSettingsRead directly
                const settings = await zodiosApi.get_user_settings_endpoint_api_v1_settings_user_get();
                if (!isClientSessionCurrent(sessionGeneration)) return;
                set(settings);

                // Cache in localStorage
                persist(settings);
            } catch (e) {
                if (!isClientSessionCurrent(sessionGeneration)) return;
                console.error('Failed to load user settings:', e);
                // Use defaults if not authenticated or error
                set(defaultSettings);
            }
        },

        /**
         * Update a single setting
         */
        async updateSetting(key: keyof UserSettings, value: string): Promise<boolean> {
            const sessionGeneration = getClientSessionGeneration();
            try {
                await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({[key]: value});
                if (!isClientSessionCurrent(sessionGeneration)) return false;

                update((current) => {
                    const updated = {...current, [key]: value} as UserSettings;
                    persist(updated);
                    return updated;
                });

                return true;
            } catch (e) {
                if (!isClientSessionCurrent(sessionGeneration)) return false;
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
                const key = storageKey();
                if (key) localStorage.removeItem(key);
                localStorage.removeItem(LEGACY_STORAGE_KEY);
            }
        },

        /** Reset only in-memory state when the authenticated account changes. */
        reset(): void {
            set(null);
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
            persist(settings);
        },
    };
}

export const userSettings = createUserSettingsStore();

registerClientSessionReset('userSettings', () => userSettings.reset());
