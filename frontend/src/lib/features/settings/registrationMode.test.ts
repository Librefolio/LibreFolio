// @vitest-environment node
/**
 * registrationMode — the one place that knows «who can sign up» (lot N69c of A; decision D5 b, 19/10/2026).
 *
 * The mode is a global setting (`registration_mode`) written by `PATCH /api/v1/settings/global/bulk`, and
 * `LIBREFOLIO_REGISTRATION` can pin it on the server. Two tabs show it — Users and Global settings — and both go through
 * this module, so they cannot disagree on the options, on the variable, or on what a save does.
 *
 * The contract under test:
 *   - `REGISTRATION_MODES`: `open`, `invite`, `disabled`, in that order; `REGISTRATION_VARIABLE` is the name of the variable;
 *   - `registrationModeOptions(translate)`: one option per mode, in that order, whose label is `translate` of
 *     `settings.registrationModes.<mode>`;
 *   - `saveRegistrationMode(mode)`: exactly one `PATCH /api/v1/settings/global/bulk` with `{items: [{key: 'registration_mode',
 *     value: mode}]}`, and only after it succeeded the public configuration is read again, forced (it carries the mode:
 *     Users, the login page and the Security tab follow it). A refusal is not swallowed — the caller words it — and reads
 *     nothing again;
 *   - `lockedByEnv(error)`: the variable named by a 409 `SETTING_LOCKED_BY_ENV` (the answer to a save that the variable
 *     forbids), `null` for any other error and for anything that is not an error.
 *
 * Mocks: the API client's axios (the call and its body are what is read) and the instance configuration (a spy).
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const axiosPatch = vi.hoisted(() => vi.fn<(url: string, body?: unknown) => Promise<unknown>>());
const instanceLoad = vi.hoisted(() => vi.fn<(options?: {force?: boolean}) => Promise<void>>());

vi.mock('$lib/api', () => ({zodiosApi: {axios: {patch: axiosPatch}}}));
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({instanceConfig: {load: instanceLoad}}));

import {REGISTRATION_MODES, REGISTRATION_VARIABLE, lockedByEnv, registrationModeOptions, saveRegistrationMode} from './registrationMode';

const refusal = (status: number, detail: unknown): Error => Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, response: {status, data: {detail}}});

beforeEach(() => {
    axiosPatch.mockReset().mockResolvedValue({data: null});
    instanceLoad.mockReset().mockResolvedValue(undefined);
});

describe('registrationMode — what it names (RMODE-01…02)', () => {
    it('RMODE-01: three modes, open first, and the variable that pins them', () => {
        expect([...REGISTRATION_MODES]).toEqual(['open', 'invite', 'disabled']);
        expect(REGISTRATION_VARIABLE).toBe('LIBREFOLIO_REGISTRATION');
    });

    it('RMODE-02: one option per mode, in order, labelled by settings.registrationModes.<mode>', () => {
        const options = registrationModeOptions((key) => `«${key}»`);

        expect(options.map((option) => option.value)).toEqual(['open', 'invite', 'disabled']);
        expect(options.map((option) => option.label)).toEqual(['«settings.registrationModes.open»', '«settings.registrationModes.invite»', '«settings.registrationModes.disabled»']);
    });
});

describe('registrationMode — saving (RMODE-03…05)', () => {
    it.each(REGISTRATION_MODES)('RMODE-03: %s — one bulk PATCH with that mode, then the configuration is read again, forced', async (mode) => {
        await saveRegistrationMode(mode);

        expect(axiosPatch).toHaveBeenCalledTimes(1);
        expect(axiosPatch).toHaveBeenCalledWith('/api/v1/settings/global/bulk', {items: [{key: 'registration_mode', value: mode}]});
        expect(instanceLoad).toHaveBeenCalledTimes(1);
        expect(instanceLoad).toHaveBeenCalledWith({force: true});
    });

    it('RMODE-04: the configuration is read again only after the PATCH answered', async () => {
        const order: string[] = [];
        axiosPatch.mockImplementation(async () => {
            order.push('patch');
            return {data: null};
        });
        instanceLoad.mockImplementation(async () => void order.push('load'));

        await saveRegistrationMode('invite');

        expect(order).toEqual(['patch', 'load']);
    });

    it('RMODE-05: a refused save reaches the caller, and reads nothing again', async () => {
        const error = refusal(500, 'boom');
        axiosPatch.mockRejectedValue(error);

        await expect(saveRegistrationMode('open')).rejects.toBe(error);
        expect(instanceLoad).not.toHaveBeenCalled();
    });
});

describe('registrationMode — a mode pinned by the variable (RMODE-06…07)', () => {
    it('RMODE-06: a 409 SETTING_LOCKED_BY_ENV names the variable the server says', () => {
        expect(lockedByEnv(refusal(409, {error_code: 'SETTING_LOCKED_BY_ENV', variable: 'LIBREFOLIO_REGISTRATION'}))).toBe('LIBREFOLIO_REGISTRATION');
    });

    it("RMODE-07: the variable is the module's when the answer omits it; any other error, or none, is not a lock", () => {
        expect(lockedByEnv(refusal(409, {error_code: 'SETTING_LOCKED_BY_ENV'}))).toBe(REGISTRATION_VARIABLE);
        expect(lockedByEnv(refusal(409, {error_code: 'EMAIL_VERIFICATION_UNAVAILABLE'}))).toBeNull();
        expect(lockedByEnv(refusal(500, {error_code: 'SETTING_LOCKED_BY_ENV'}))).toBeNull();
        expect(lockedByEnv(new Error('network'))).toBeNull();
        expect(lockedByEnv(undefined)).toBeNull();
        expect(lockedByEnv('SETTING_LOCKED_BY_ENV')).toBeNull();
    });
});
