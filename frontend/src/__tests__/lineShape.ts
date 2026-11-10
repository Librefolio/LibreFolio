import {userSettings} from '$lib/stores/app/settings';

export type ChosenLineShape = 'segments' | 'steps' | 'spline';

/** The line shape the user chose (lot UIP): it lives in the user settings store, so a chart test seeds the choice through the real store. */
export function chooseLineShape(shape: ChosenLineShape): void {
    userSettings.setDirect({
        language: 'en',
        base_currency: 'EUR',
        avatar_url: null,
        ui_preferences: {chart_line_shape: shape},
        ui_preference_defaults: {theme: 'auto', chart_line_shape: 'segments'},
    });
}
