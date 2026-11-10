/**
 * The user's interface preferences (lot UIP): the theme and the shape of the chart lines.
 *
 * The server keeps them in `user_settings.ui_preferences`, one key per preference. `GET /settings/user` answers
 * `ui_preferences` with the keys the user chose and `ui_preference_defaults` with the administrator's global default of
 * every key: a key the user did not choose follows its default, and the GUI says so with a «Global» badge. A write names
 * only the keys it changes; `null` removes a key, so it follows the global default again.
 *
 * These helpers read a settings object; the write is `userSettings.updateUiPreference` (`stores/app/settings`).
 *
 * @module stores/app/uiPreferences
 */

import type {LineShape} from '$lib/components/charts/lineShape';
import type {ThemePreference} from '$lib/stores/app/themeStore';
import type {UserSettings} from '$lib/types';

/** The value of each interface preference. */
export interface UiPreferenceValues {
    theme: ThemePreference;
    chart_line_shape: LineShape;
}

export type UiPreferenceKey = keyof UiPreferenceValues;

/** The defaults when no settings were read from the server: the server's own built-in ones. */
export const FALLBACK_UI_PREFERENCE_DEFAULTS: UiPreferenceValues = {theme: 'auto', chart_line_shape: 'segments'};

type SettingsLike = Pick<UserSettings, 'ui_preferences' | 'ui_preference_defaults'> | null | undefined;

/** The value the user chose for `key`, or `undefined` when they did not: the key follows its global default. */
export function ownUiPreference<K extends UiPreferenceKey>(settings: SettingsLike, key: K): UiPreferenceValues[K] | undefined {
    const value = settings?.ui_preferences?.[key];
    return (value ?? undefined) as UiPreferenceValues[K] | undefined;
}

/** The administrator's global default for `key`. */
export function uiPreferenceDefault<K extends UiPreferenceKey>(settings: SettingsLike, key: K): UiPreferenceValues[K] {
    return (settings?.ui_preference_defaults?.[key] ?? FALLBACK_UI_PREFERENCE_DEFAULTS[key]) as UiPreferenceValues[K];
}

/** The value in force for `key`: the user's own, else the global default. */
export function effectiveUiPreference<K extends UiPreferenceKey>(settings: SettingsLike, key: K): UiPreferenceValues[K] {
    return ownUiPreference(settings, key) ?? uiPreferenceDefault(settings, key);
}

/** Whether `key` follows the global default: the user has not chosen it. */
export function followsGlobalUiPreference(settings: SettingsLike, key: UiPreferenceKey): boolean {
    return ownUiPreference(settings, key) === undefined;
}

/** `settings` with `key` set to `value`, or removed when `value` is `null`: what a write leaves, for an optimistic update. */
export function withUiPreference<S extends NonNullable<SettingsLike>, K extends UiPreferenceKey>(settings: S, key: K, value: UiPreferenceValues[K] | null): S {
    const own = {...(settings.ui_preferences ?? {})} as Record<string, unknown>;
    if (value === null) delete own[key];
    else own[key] = value;
    return {...settings, ui_preferences: own as S['ui_preferences']};
}
