/**
 * Who can sign up: the one place that knows the registration mode (lot N69c).
 *
 * The mode is the global setting `registration_mode`, written by `PATCH /api/v1/settings/global/bulk`; the environment
 * variable `LIBREFOLIO_REGISTRATION` can pin it on the server (then a save answers 409 `SETTING_LOCKED_BY_ENV` and
 * `GET /system/instance` carries `registration_locked`). The Users tab and the Global settings tab both show it and go
 * through here, so they agree on the options, on the variable and on what a save does.
 */
import {isAxiosError} from 'axios';
import {zodiosApi} from '$lib/api';
import type {SelectOption} from '$lib/components/ui/select';
import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';

/** The key of the global setting. */
export const REGISTRATION_KEY = 'registration_mode';

/** The environment variable that pins the mode on the server. */
export const REGISTRATION_VARIABLE = 'LIBREFOLIO_REGISTRATION';

/** Every mode, the most open first. */
export const REGISTRATION_MODES = ['open', 'invite', 'disabled'] as const;

export type RegistrationMode = (typeof REGISTRATION_MODES)[number];

/** The options of a select, labelled with `settings.registrationModes.<mode>`; `translate` is the current `$_`. */
export function registrationModeOptions(translate: (key: string) => string): SelectOption[] {
    return REGISTRATION_MODES.map((mode) => ({value: mode, label: translate(`settings.registrationModes.${mode}`)}));
}

/** The public configuration carries the mode (Users, login, Security follow it): ask for it again. */
export function refreshRegistrationConfig(): Promise<void> {
    return instanceConfig.load({force: true});
}

/** Saves the mode, then reads the public configuration again. A refusal reaches the caller, who words it. */
export async function saveRegistrationMode(mode: RegistrationMode): Promise<void> {
    await zodiosApi.axios.patch('/api/v1/settings/global/bulk', {items: [{key: REGISTRATION_KEY, value: mode}]});
    await refreshRegistrationConfig();
}

/** The variable that pinned the mode, when `error` is the server's 409 `SETTING_LOCKED_BY_ENV`; else `null`. */
export function lockedByEnv(error: unknown): string | null {
    if (!isAxiosError(error) || error.response?.status !== 409) return null;
    const detail = error.response.data?.detail;
    if (detail === null || typeof detail !== 'object' || detail.error_code !== 'SETTING_LOCKED_BY_ENV') return null;
    return typeof detail.variable === 'string' && detail.variable !== '' ? detail.variable : REGISTRATION_VARIABLE;
}
