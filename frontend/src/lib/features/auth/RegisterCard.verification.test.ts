// @vitest-environment jsdom
/**
 * RegisterCard and email verification (lot E5b, developer decision 44): the sign-up of an instance that requires a
 * verified address.
 *
 * The contract under test:
 *   - an answer with `verification_required: true` sends the user to the sign-in with `email.verification.registered`
 *     (open the link in the email first), instead of `auth.accountCreated`;
 *   - an answer without it, or with it false, keeps `auth.accountCreated`, as before;
 *   - a 409 `EMAIL_VERIFICATION_UNAVAILABLE` stays on the form, saying `email.verification.signUpUnavailable` in the
 *     general error banner, and goes nowhere.
 *
 * Mocks, as in workstream A's `RegisterCard.test.ts` (left to A): the identity translator — a message renders as its
 * key — and the generated client's register alias, answered per test. Red until E5b is applied.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/api', () => ({zodiosApi: {register_api_v1_auth_register_post: vi.fn()}}));

import RegisterCard from './RegisterCard.svelte';
import {zodiosApi} from '$lib/api';

const register = vi.mocked(zodiosApi.register_api_v1_auth_register_post);

/** Satisfies all five password rules: length, upper, lower, digit, special. */
const GOOD_PASSWORD = 'Str0ng!pass';

function answer(verificationRequired: boolean | undefined) {
    const user = {id: 2, username: 'zq_vera', email: 'zq_vera@example.com', is_active: verificationRequired !== true, is_superuser: false, created_at: '2026-10-16T00:00:00Z'};
    return verificationRequired === undefined ? {user, message: 'Registration successful'} : {user, message: 'Registration successful', verification_required: verificationRequired};
}

function mount(): {gotoLogin: ReturnType<typeof vi.fn>} {
    const gotoLogin = vi.fn();
    render(RegisterCard, {$$events: {gotoLogin: (event: CustomEvent) => gotoLogin(event.detail)}} as never);
    return {gotoLogin};
}

async function fillValidAndSubmit(): Promise<void> {
    await fireEvent.input(screen.getByTestId('register-username'), {target: {value: 'zq_vera'}});
    await fireEvent.input(screen.getByTestId('register-email'), {target: {value: 'zq_vera@example.com'}});
    await fireEvent.input(screen.getByTestId('register-password'), {target: {value: GOOD_PASSWORD}});
    await fireEvent.input(screen.getByTestId('register-confirm-password'), {target: {value: GOOD_PASSWORD}});
    await fireEvent.submit(screen.getByTestId('register-form'));
}

beforeEach(() => {
    register.mockReset();
});

afterEach(() => {
    cleanup();
});

describe('RegisterCard — a sign-up that waits for its email verification', () => {
    it('RCV-01: verification_required true → to the sign-in with email.verification.registered', async () => {
        register.mockResolvedValueOnce(answer(true) as never);
        const {gotoLogin} = mount();

        await fillValidAndSubmit();

        await waitFor(() => expect(gotoLogin).toHaveBeenCalledTimes(1));
        expect(gotoLogin).toHaveBeenCalledWith({message: 'email.verification.registered'});
    });

    it.each([
        ['false', false],
        ['absent (an older server)', undefined],
    ])('RCV-02: verification_required %s → auth.accountCreated, as before', async (_label, required) => {
        register.mockResolvedValueOnce(answer(required) as never);
        const {gotoLogin} = mount();

        await fillValidAndSubmit();

        await waitFor(() => expect(gotoLogin).toHaveBeenCalledTimes(1));
        expect(gotoLogin).toHaveBeenCalledWith({message: 'auth.accountCreated'});
    });

    it('RCV-03: 409 EMAIL_VERIFICATION_UNAVAILABLE → the banner says email.verification.signUpUnavailable, and the form stays', async () => {
        register.mockRejectedValueOnce(
            Object.assign(new Error('Request failed with status code 409'), {
                isAxiosError: true,
                response: {status: 409, data: {detail: {error_code: 'EMAIL_VERIFICATION_UNAVAILABLE', message: 'An English sentence the user must not read'}}},
            }),
        );
        const {gotoLogin} = mount();

        await fillValidAndSubmit();

        await waitFor(() => expect(screen.getByTestId('info-banner-error')).toHaveTextContent('email.verification.signUpUnavailable'));
        expect(screen.getByTestId('info-banner-error')).not.toHaveTextContent('An English sentence');
        expect(gotoLogin).not.toHaveBeenCalled();
        expect(screen.getByTestId('register-form')).toBeInTheDocument();
    });
});
