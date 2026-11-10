// @vitest-environment jsdom
/**
 * WelcomeForm — staged draft, submit payload, busy/error, no theme control.
 *
 * `SettingCurrency` is replaced with `$test/harness/SettingCurrencyProbe.svelte`:
 * the real component's `CurrencySearchSelect` child loads currencies and FX routes
 * from the network on mount, which would make this an integration test of two
 * unrelated stores instead of a unit test of WelcomeForm's own wiring. The probe
 * keeps the same bindable-`value` contract WelcomeForm actually depends on.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/features/settings/SettingCurrency.svelte', async () => ({
    default: (await import('$test/harness/SettingCurrencyProbe.svelte')).default,
}));
// The shape is an interface preference kept by the server (lot UIP): the PUT is answered with what the server would
// hold, built from the one `ui_preferences` the request names (null removes the key), so the store reads back its write.
const serverOwn = vi.hoisted(() => ({value: {} as Record<string, unknown>}));
const putUserSettings = vi.hoisted(() => vi.fn());
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: (_t, key) => (key === 'update_user_settings_endpoint_api_v1_settings_user_put' ? putUserSettings : vi.fn(async () => Promise.reject(new Error('no network in this test'))))}),
    axiosInstance: new Proxy({}, {get: () => vi.fn()}),
    ApiError: class ApiError extends Error {},
}));
vi.mock('$lib/components/charts/LineShapePreview.svelte', async () => ({
    default: (await import('$test/harness/LineShapePreviewProbe.svelte')).default,
}));

import {fireEvent, render, screen, setupI18n} from '$test/component';
import {waitFor} from '@testing-library/svelte';
import {availableLanguages} from '$lib/stores/app/language';
import type {WelcomeCopy} from '$lib/features/onboarding/welcome';
import {getGlobalLineShape} from '$lib/stores/chartSettingsStore.svelte';
import {userSettings, type UserSettings} from '$lib/stores/app/settings';
import WelcomeForm from './WelcomeForm.svelte';

const COPY: WelcomeCopy = {
    productName: 'LibreFolio',
    title: 'TITLE_TOKEN',
    description: 'DESCRIPTION_TOKEN',
    defaultsHint: 'DEFAULTS_HINT_TOKEN',
    avatarLabel: 'AVATAR_LABEL_TOKEN',
    avatarHint: 'AVATAR_HINT_TOKEN',
    chooseAvatar: 'CHOOSE_AVATAR_TOKEN',
    removeAvatar: 'REMOVE_AVATAR_TOKEN',
    avatarAlt: 'AVATAR_ALT_TOKEN',
    languageLabel: 'LANGUAGE_LABEL_TOKEN',
    languageHint: 'LANGUAGE_HINT_TOKEN',
    currencyLabel: 'CURRENCY_LABEL_TOKEN',
    currencyHint: 'CURRENCY_HINT_TOKEN',
    themeHint: 'THEME_HINT_TOKEN',
    skip: 'SKIP_TOKEN',
    skipHint: 'SKIP_HINT_TOKEN',
    continue: 'CONTINUE_TOKEN',
    logout: 'LOGOUT_TOKEN',
    completed: 'COMPLETED_TOKEN',
    skipped: 'SKIPPED_TOKEN',
};

beforeAll(async () => {
    await setupI18n();
});

interface MountProps {
    language?: string;
    baseCurrency?: string;
    avatarUrl?: string | null;
    busy?: boolean;
    error?: string | null;
}

function mount(props: MountProps = {}) {
    const onsubmit = vi.fn();
    const onskip = vi.fn();
    const onavatarrequest = vi.fn();
    const onavatarclear = vi.fn();
    const utils = render(WelcomeForm, {
        copy: COPY,
        initials: 'AB',
        language: 'en',
        baseCurrency: 'EUR',
        avatarUrl: null,
        busy: false,
        error: null,
        ...props,
        onsubmit,
        onskip,
        onavatarrequest,
        onavatarclear,
    });
    return {onsubmit, onskip, onavatarrequest, onavatarclear, ...utils};
}

describe('WelcomeForm — submit payload carries the staged draft', () => {
    it('submits exactly the language/currency/avatar it was given, unchanged', async () => {
        const {onsubmit} = mount({
            language: 'fr',
            baseCurrency: 'USD',
            avatarUrl: 'https://example.test/avatar.png',
        });

        await fireEvent.submit(screen.getByTestId('welcome-form'));

        expect(onsubmit).toHaveBeenCalledTimes(1);
        expect(onsubmit).toHaveBeenCalledWith({
            language: 'fr',
            baseCurrency: 'USD',
            avatarUrl: 'https://example.test/avatar.png',
        });
    });

    it('reflects a currency staged through the currency control at submit time', async () => {
        const {onsubmit} = mount({baseCurrency: 'EUR'});

        const currencyInput = screen.getByTestId('welcome-currency-input');
        await fireEvent.input(currencyInput, {target: {value: 'GBP'}});
        await fireEvent.click(screen.getByTestId('welcome-continue'));

        expect(onsubmit).toHaveBeenCalledWith(expect.objectContaining({baseCurrency: 'GBP'}));
    });

    it('reflects a language staged through the language select at submit time', async () => {
        const {onsubmit} = mount({language: 'en'});
        const other = availableLanguages.find((option) => option.code !== 'en');
        if (!other) throw new Error('Test fixture assumption broken: need a non-English language option');

        await fireEvent.click(screen.getByRole('combobox'));
        await fireEvent.click(screen.getByRole('option', {name: new RegExp(other.name)}));
        await fireEvent.click(screen.getByTestId('welcome-continue'));

        expect(onsubmit).toHaveBeenCalledWith(expect.objectContaining({language: other.code}));
    });

    it('delegates the permanent Skip action to its parent', async () => {
        const {onskip, onsubmit} = mount();

        await fireEvent.click(screen.getByTestId('welcome-skip'));

        expect(onskip).toHaveBeenCalledTimes(1);
        expect(onsubmit).not.toHaveBeenCalled();
    });
});

describe('WelcomeForm — avatar staging', () => {
    it('shows initials (not an image) when there is no avatar yet, and no clear button', () => {
        mount({avatarUrl: null});

        expect(screen.getByText('AB')).toBeInTheDocument();
        expect(screen.queryByRole('img')).toBeNull();
        expect(screen.queryByTestId('welcome-avatar-clear')).toBeNull();
    });

    it('shows the image and a clear button once an avatar is staged', () => {
        mount({avatarUrl: 'https://example.test/avatar.png'});

        const img = screen.getByRole('img', {name: 'AVATAR_ALT_TOKEN'});
        expect(img).toHaveAttribute('src', 'https://example.test/avatar.png');
        expect(screen.getByTestId('welcome-avatar-clear')).toBeInTheDocument();
    });

    it('choose avatar calls onavatarrequest', async () => {
        const {onavatarrequest} = mount();
        await fireEvent.click(screen.getByTestId('welcome-avatar-choose'));
        expect(onavatarrequest).toHaveBeenCalledTimes(1);
    });

    it('clear avatar calls onavatarclear (the parent owns clearing the bound value)', async () => {
        const {onavatarclear} = mount({avatarUrl: 'https://example.test/avatar.png'});
        await fireEvent.click(screen.getByTestId('welcome-avatar-clear'));
        expect(onavatarclear).toHaveBeenCalledTimes(1);
    });
});

describe('WelcomeForm — busy state', () => {
    it('publishes busy on the form and disables every actionable control', () => {
        mount({busy: true, avatarUrl: 'https://example.test/avatar.png'});

        const form = screen.getByTestId('welcome-form');
        expect(form).toHaveAttribute('aria-busy', 'true');
        expect(form).toHaveAttribute('data-busy', 'true');
        expect(screen.getByTestId('welcome-continue')).toBeDisabled();
        expect(screen.getByTestId('welcome-avatar-choose')).toBeDisabled();
        expect(screen.getByTestId('welcome-avatar-clear')).toBeDisabled();
    });

    it('publishes not-busy and enabled controls by default', () => {
        mount({busy: false});

        const form = screen.getByTestId('welcome-form');
        expect(form).toHaveAttribute('aria-busy', 'false');
        expect(form).toHaveAttribute('data-busy', 'false');
        expect(screen.getByTestId('welcome-continue')).not.toBeDisabled();
    });
});

describe('WelcomeForm — error state', () => {
    it('renders the given error as an alert and nothing when there is none', () => {
        mount({error: 'SOMETHING_WENT_WRONG_TOKEN'});

        const alert = screen.getByTestId('welcome-error');
        expect(alert).toHaveAttribute('role', 'alert');
        expect(alert).toHaveTextContent('SOMETHING_WENT_WRONG_TOKEN');
    });

    it('renders no error banner at all when error is null', () => {
        mount({error: null});
        expect(screen.queryByTestId('welcome-error')).toBeNull();
    });
});

describe('WelcomeForm — language control selector contract', () => {
    it('exposes a stable welcome-language testid for the language control, regardless of the copy/locale in effect', () => {
        mount();

        // Deliberately not asserting COPY.languageLabel or any rendered text here: the
        // element identity other code/tests rely on is the testid, and it must hold
        // however the UI is translated.
        expect(screen.getByTestId('welcome-language')).toBeInTheDocument();
    });
});

describe('WelcomeForm — no theme control', () => {
    it('never renders a theme selector — only the static theme hint text', () => {
        mount();

        expect(screen.queryByTestId('theme-toggle')).toBeNull();
        expect(screen.getByTestId('welcome-theme-hint')).toBeInTheDocument();

        const themeRelated = document.querySelectorAll('[data-testid*="theme"]');
        expect(themeRelated).toHaveLength(1);
        expect(themeRelated[0]).toBe(screen.getByTestId('welcome-theme-hint'));
    });
});

/** Server settings for a user with these own preferences and these administrator defaults. */
function seedSettings(own: UserSettings['ui_preferences'], shapeDefault: 'segments' | 'steps' | 'spline' = 'segments'): void {
    serverOwn.value = {...own};
    userSettings.setDirect({language: 'en', base_currency: 'EUR', avatar_url: null, ui_preferences: own, ui_preference_defaults: {theme: 'auto', chart_line_shape: shapeDefault}});
}

beforeEach(() => {
    putUserSettings.mockReset();
    putUserSettings.mockImplementation(async (body: {ui_preferences: Record<string, unknown>}) => {
        for (const [key, value] of Object.entries(body.ui_preferences)) {
            if (value === null) delete serverOwn.value[key];
            else serverOwn.value[key] = value;
        }
        return {language: 'en', base_currency: 'EUR', avatar_url: null, ui_preferences: {...serverOwn.value}, ui_preference_defaults: {theme: 'auto', chart_line_shape: 'segments'}};
    });
    seedSettings({});
});

afterEach(() => {
    userSettings.reset();
});

describe('WelcomeForm — the shape of the lines (Y2 FB-3, lot UIP)', () => {
    it('preselects the shape in force: the global default for a user who chose none', () => {
        seedSettings({}, 'steps');
        mount();
        expect(screen.getByTestId('line-shape-preview')).toHaveAttribute('data-shape', 'steps');
        expect(putUserSettings, 'showing a shape writes nothing').not.toHaveBeenCalled();
    });

    it('preselects the own shape over the default', () => {
        seedSettings({chart_line_shape: 'spline'}, 'steps');
        mount();
        expect(screen.getByTestId('line-shape-preview')).toHaveAttribute('data-shape', 'spline');
    });

    it('writes chart_line_shape when the user clicks, and changes the example live', async () => {
        mount();
        expect(screen.getByTestId('line-shape-preview')).toHaveAttribute('data-shape', 'segments');

        await fireEvent.click(screen.getByTestId('welcome-line-shape-picker-spline'));
        await waitFor(() => expect(getGlobalLineShape()).toBe('spline'));
        expect(screen.getByTestId('line-shape-preview')).toHaveAttribute('data-shape', 'spline');
        expect(putUserSettings).toHaveBeenLastCalledWith({ui_preferences: {chart_line_shape: 'spline'}});

        await fireEvent.click(screen.getByTestId('welcome-line-shape-picker-steps'));
        await waitFor(() => expect(screen.getByTestId('line-shape-preview')).toHaveAttribute('data-shape', 'steps'));
        expect(putUserSettings).toHaveBeenLastCalledWith({ui_preferences: {chart_line_shape: 'steps'}});
    });

    it('writes nothing without a click, not even when the form is submitted', async () => {
        const {onsubmit} = mount();
        await fireEvent.submit(screen.getByTestId('welcome-form'));
        expect(onsubmit).toHaveBeenCalledTimes(1);
        expect(putUserSettings).not.toHaveBeenCalled();
    });

    it('does not submit the form by picking a shape', async () => {
        const {onsubmit} = mount();
        await fireEvent.click(screen.getByTestId('welcome-line-shape-picker-steps'));
        expect(onsubmit).not.toHaveBeenCalled();
    });

    it('locks the picker while the form is busy', () => {
        mount({busy: true});
        expect(screen.getByTestId('welcome-line-shape-picker-steps')).toBeDisabled();
    });
});
