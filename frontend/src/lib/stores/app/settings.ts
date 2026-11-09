/**
 * User Settings Store
 *
 * Manages user preferences like default currency, language, etc.
 * Loads settings from backend and caches them locally.
 *
 * Now uses Zodios client for type-safe API calls with Zod validation.
 */
import {derived, get, writable} from 'svelte/store';
import {browser} from '$app/environment';
import {zodiosApi} from '$lib/api';
import type {UserSettings} from '$lib/types';
import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent, registerClientSessionReset} from '$lib/stores/app/clientSession';
import {globalSettings} from '$lib/stores/app/globalSettings';
import {FALLBACK_UI_PREFERENCE_DEFAULTS, ownUiPreference, withUiPreference, type UiPreferenceKey, type UiPreferenceValues} from '$lib/stores/app/uiPreferences';

// Re-export type for backward compatibility
export type {UserSettings} from '$lib/types';

const defaultSettings: UserSettings = {
    language: 'en',
    base_currency: 'EUR',
    avatar_url: null,
    ui_preferences: {},
    ui_preference_defaults: {...FALLBACK_UI_PREFERENCE_DEFAULTS},
};

/** Whether `settings` are the built-in ones the store falls back to when the server could not be read: no user's data. */
export function isFallbackUserSettings(settings: UserSettings | null | undefined): boolean {
    return settings === defaultSettings;
}

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
        async load(): Promise<boolean> {
            const sessionGeneration = getClientSessionGeneration();
            try {
                // Zodios returns UserSettingsRead directly
                const settings = await zodiosApi.get_user_settings_endpoint_api_v1_settings_user_get();
                if (!isClientSessionCurrent(sessionGeneration)) return false;
                set(settings);

                // Cache in localStorage
                persist(settings);
                return true;
            } catch (e) {
                if (!isClientSessionCurrent(sessionGeneration)) return false;
                console.error('Failed to load user settings:', e);
                // Use defaults if not authenticated or error
                set(defaultSettings);
                return false;
            }
        },

        /**
         * Update a single setting
         */
        async updateSetting(key: 'language' | 'base_currency' | 'avatar_url', value: string): Promise<boolean> {
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
         * Set or remove one interface preference (lot UIP): applied at once, then written. The write names only `key`, so a
         * write from another tab is never undone; `null` removes the key, which then follows its global default. The
         * answer, every preference the server holds, replaces the store's; a refused write puts back the value it had.
         */
        async updateUiPreference<K extends UiPreferenceKey>(key: K, value: UiPreferenceValues[K] | null): Promise<boolean> {
            const sessionGeneration = getClientSessionGeneration();
            const before = get({subscribe});
            const previous = ownUiPreference(before, key) ?? null;
            update((current) => {
                if (!current) return current;
                const next = withUiPreference(current, key, value);
                persist(next);
                return next;
            });
            try {
                const response = await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({ui_preferences: {[key]: value}});
                if (!isClientSessionCurrent(sessionGeneration)) return false;
                set(response);
                persist(response);
                return true;
            } catch (e) {
                if (!isClientSessionCurrent(sessionGeneration)) return false;
                console.error('Failed to update an interface preference:', e);
                update((current) => {
                    if (!current) return current;
                    const restored = withUiPreference(current, key, previous);
                    persist(restored);
                    return restored;
                });
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

/**
 * The currency a page starts in: the user's own Default Currency. The instance's
 * `default_currency` is the one *new* users get, so it is only the fallback for a user
 * who has none — and 'EUR' the last resort before any settings are known.
 */
export const defaultDisplayCurrency = derived([userSettings, globalSettings], ([$user, $global]) => $user?.base_currency || $global.default_currency || 'EUR');

registerClientSessionReset('userSettings', () => userSettings.reset());
