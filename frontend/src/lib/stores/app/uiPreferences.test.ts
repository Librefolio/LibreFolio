/** Pure helpers of the interface preferences (lot UIP): own vs default vs effective, and the optimistic merge. */
import {describe, expect, it} from 'vitest';
import {FALLBACK_UI_PREFERENCE_DEFAULTS, effectiveUiPreference, followsGlobalUiPreference, ownUiPreference, uiPreferenceDefault, withUiPreference} from '$lib/stores/app/uiPreferences';
import type {UserSettings} from '$lib/types';

function settings(own: UserSettings['ui_preferences'], defaults: UserSettings['ui_preference_defaults'] = {theme: 'dark', chart_line_shape: 'steps'}): UserSettings {
    return {language: 'en', base_currency: 'EUR', avatar_url: null, ui_preferences: own, ui_preference_defaults: defaults};
}

describe('uiPreferences helpers', () => {
    it('has the built-in fallback defaults', () => {
        expect(FALLBACK_UI_PREFERENCE_DEFAULTS).toEqual({theme: 'auto', chart_line_shape: 'segments'});
    });

    it('own: the chosen value, undefined when absent', () => {
        const s = settings({theme: 'light'});
        expect(ownUiPreference(s, 'theme')).toBe('light');
        expect(ownUiPreference(s, 'chart_line_shape')).toBeUndefined();
    });

    it('default: the server default, not the own value', () => {
        const s = settings({theme: 'light'});
        expect(uiPreferenceDefault(s, 'theme')).toBe('dark');
        expect(uiPreferenceDefault(s, 'chart_line_shape')).toBe('steps');
    });

    it('effective: own wins, else the default', () => {
        const s = settings({theme: 'light'});
        expect(effectiveUiPreference(s, 'theme')).toBe('light');
        expect(effectiveUiPreference(s, 'chart_line_shape')).toBe('steps');
    });

    it('followsGlobal: true only when there is no own key', () => {
        const s = settings({theme: 'light'});
        expect(followsGlobalUiPreference(s, 'theme')).toBe(false);
        expect(followsGlobalUiPreference(s, 'chart_line_shape')).toBe(true);
    });

    it('falls back to the built-in defaults with null settings', () => {
        expect(ownUiPreference(null, 'theme')).toBeUndefined();
        expect(effectiveUiPreference(null, 'theme')).toBe('auto');
        expect(effectiveUiPreference(undefined, 'chart_line_shape')).toBe('segments');
        expect(followsGlobalUiPreference(null, 'theme')).toBe(true);
    });

    it('falls back to the built-in defaults when settings lack ui_preference_defaults', () => {
        const legacy = {ui_preferences: {}} as unknown as UserSettings;
        expect(uiPreferenceDefault(legacy, 'theme')).toBe('auto');
        expect(effectiveUiPreference(legacy, 'chart_line_shape')).toBe('segments');
        const bare = {} as unknown as UserSettings;
        expect(effectiveUiPreference(bare, 'theme')).toBe('auto');
        expect(followsGlobalUiPreference(bare, 'theme')).toBe(true);
    });

    it('withUiPreference sets a key without mutating the input or touching other keys', () => {
        const s = settings({theme: 'light'});
        const next = withUiPreference(s, 'chart_line_shape', 'spline');
        expect(next.ui_preferences).toEqual({theme: 'light', chart_line_shape: 'spline'});
        expect(s.ui_preferences).toEqual({theme: 'light'});
        expect(next.ui_preference_defaults).toEqual(s.ui_preference_defaults);
    });

    it('withUiPreference removes a key on null', () => {
        const next = withUiPreference(settings({theme: 'light', chart_line_shape: 'steps'}), 'theme', null);
        expect(next.ui_preferences).toEqual({chart_line_shape: 'steps'});
        expect('theme' in (next.ui_preferences ?? {})).toBe(false);
    });

    it('withUiPreference tolerates missing ui_preferences', () => {
        const bare = {language: 'en'} as unknown as UserSettings;
        expect(withUiPreference(bare, 'theme', 'dark').ui_preferences).toEqual({theme: 'dark'});
    });
});
