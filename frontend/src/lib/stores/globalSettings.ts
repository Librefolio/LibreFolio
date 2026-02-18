/**
 * Global Settings Store
 *
 * Manages application-wide settings (admin-only configuration).
 * Loads settings from backend and caches them locally.
 */
import {get, writable} from 'svelte/store';
import {browser} from '$app/environment';
import {zodiosApi} from '$lib/api';

/**
 * Global settings structure
 */
export interface GlobalSettings {
    default_language: string;
    default_currency: string;
    default_theme: string;
    session_ttl_hours: number;
    auto_sync_fx_rates: boolean;
    auto_sync_prices: boolean;
    price_sync_interval_hours: number;
    max_file_upload_mb: number;
}

const defaultGlobalSettings: GlobalSettings = {
    default_language: 'en',
    default_currency: 'EUR',
    default_theme: 'auto',
    session_ttl_hours: 24,
    auto_sync_fx_rates: false,
    auto_sync_prices: false,
    price_sync_interval_hours: 24,
    max_file_upload_mb: 10
};

/**
 * Create the global settings store
 */
function createGlobalSettingsStore() {
    const {subscribe, set, update} = writable<GlobalSettings>(defaultGlobalSettings);

    // Load from localStorage on init
    if (browser) {
        const cached = localStorage.getItem('global_settings');
        if (cached) {
            try {
                const parsed = JSON.parse(cached);
                set({...defaultGlobalSettings, ...parsed});
            } catch {
                // Invalid cache, use defaults
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
                const response = await zodiosApi.list_global_settings_api_v1_settings_global_get();
                const settings = response.settings || [];

                // Convert array of {key, value} to object
                const settingsObj: Partial<GlobalSettings> = {};
                for (const s of settings) {
                    const key = s.key as keyof GlobalSettings;
                    const value = s.value;

                    // Parse based on expected type
                    if (key === 'session_ttl_hours' || key === 'price_sync_interval_hours' || key === 'max_file_upload_mb') {
                        settingsObj[key] = parseInt(value, 10) || defaultGlobalSettings[key];
                    } else if (key === 'auto_sync_fx_rates' || key === 'auto_sync_prices') {
                        settingsObj[key] = value === 'true';
                    } else {
                        (settingsObj as any)[key] = value;
                    }
                }

                const merged = {...defaultGlobalSettings, ...settingsObj};
                set(merged);

                // Cache in localStorage
                if (browser) {
                    localStorage.setItem('global_settings', JSON.stringify(merged));
                }
            } catch (e) {
                console.error('Failed to load global settings:', e);
                // Keep current values
            }
        },

        /**
         * Update a single setting (also updates store)
         */
        async updateSetting(key: keyof GlobalSettings, value: string | number | boolean): Promise<boolean> {
            try {
                const stringValue = String(value);
                await zodiosApi.update_global_setting_endpoint_api_v1_settings_global__key__put(
                    {value: stringValue},
                    {params: {key}}
                );

                update(current => {
                    const updated = {...current};
                    // Parse value based on type
                    if (key === 'session_ttl_hours' || key === 'price_sync_interval_hours' || key === 'max_file_upload_mb') {
                        updated[key] = typeof value === 'number' ? value : parseInt(String(value), 10);
                    } else if (key === 'auto_sync_fx_rates' || key === 'auto_sync_prices') {
                        updated[key] = value === true || value === 'true';
                    } else {
                        (updated as any)[key] = value;
                    }

                    if (browser) {
                        localStorage.setItem('global_settings', JSON.stringify(updated));
                    }
                    return updated;
                });

                return true;
            } catch (e) {
                console.error('Failed to update global setting:', e);
                return false;
            }
        },

        /**
         * Set all settings directly (used after bulk updates)
         */
        setDirect(settings: Partial<GlobalSettings>): void {
            update(current => {
                const merged = {...current, ...settings};
                if (browser) {
                    localStorage.setItem('global_settings', JSON.stringify(merged));
                }
                return merged;
            });
        },

        /**
         * Get current value synchronously
         */
        get(): GlobalSettings {
            return get({subscribe});
        },

        /**
         * Get a specific setting value
         */
        getValue<K extends keyof GlobalSettings>(key: K): GlobalSettings[K] {
            return get({subscribe})[key];
        },

        /**
         * Clear settings (on logout if needed)
         */
        clear(): void {
            set(defaultGlobalSettings);
            if (browser) {
                localStorage.removeItem('global_settings');
            }
        }
    };
}

export const globalSettings = createGlobalSettingsStore();

