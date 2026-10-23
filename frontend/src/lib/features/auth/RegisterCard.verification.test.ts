// @vitest-environment jsdom
/**
 * RegisterCard and email verification (lot E5b, developer decision 44): the sign-up of an instance that requires a
 * verified address.
 *
 * The contract under test:
 *   - an answer with `verification_required: true` sends the user to the sign-in with `email.verification.registered`
 *     (open the link in the email first), instead of `auth.accountCreated` — whether `verification_email` says
 *     `"sending"` (the email is queued) or the field is absent (an older server, which never sent it: the fallback);
 *   - an answer with `verification_required: true` and `verification_email: "held"` (lot E-26 (b): the client address
 *     sent too many registration emails, so this account's email is held) sends the user to the sign-in with
 *     `email.verification.registeredHeld` instead — the sign-in's «send the link again» is how the account gets it;
 *   - an answer without `verification_required`, or with it false (`verification_email` then `null`, or absent), keeps
 *     `auth.accountCreated`, as before;
 *   - a 409 `EMAIL_VERIFICATION_UNAVAILABLE` stays on the form, saying `email.verification.signUpUnavailable` in the
 *     general error banner, and goes nowhere.
 *
 * Mocks, as in workstream A's `RegisterCard.test.ts` (left to A): the identity translator — a message renders as its
 * key — and the generated client's register alias, answered per test. Red until E5b is applied; RCV-04 until lot E-26 (b)
 * is (RCV-01, RCV-02 and RCV-05 pass before and after it: RCV-05 pins the fallback of an older server).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';

// The identity translator, a spy: the values a message was given, which the identity drops, are read from its calls
const translate = vi.hoisted(() => vi.fn((key: string, _options?: {values?: Record<string, unknown>}) => key));
vi.mock('$lib/i18n', () => ({_: readable(translate)}));
vi.mock('$lib/api', () => ({zodiosApi: {register_api_v1_auth_register_post: vi.fn()}}));

import RegisterCard from './RegisterCard.svelte';
import {zodiosApi} from '$lib/api';

const register = vi.mocked(zodiosApi.register_api_v1_auth_register_post);

/** Satisfies all five password rules: length, upper, lower, digit, special. */
const GOOD_PASSWORD = 'Str0ng!pass';

/** What `verification_email` says: the email is queued, held by the per-address limit, or none is expected. */
type VerificationEmail = 'sending' | 'held' | null;

/** One register answer. A field passed as `undefined` is left out of the body altogether, as an older server leaves it out. */
function answer(verificationRequired: boolean | undefined, verificationEmail?: VerificationEmail, retryAfterSeconds?: number | null) {
    const user = {id: 2, username: 'zq_vera', email: 'zq_vera@example.com', is_active: verificationRequired !== true, is_superuser: false, created_at: '2026-10-16T00:00:00Z'};
    return {
        user,
        message: 'Registration successful',
        ...(verificationRequired === undefined ? {} : {verification_required: verificationRequired}),
        ...(verificationEmail === undefined ? {} : {verification_email: verificationEmail}),
        ...(retryAfterSeconds === undefined ? {} : {verification_retry_after_seconds: retryAfterSeconds}),
    };
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
    translate.mockClear();
});

afterEach(() => {
    cleanup();
});

describe('RegisterCard — a sign-up that waits for its email verification', () => {
    it('RCV-01: verification_required true, verification_email "sending" → to the sign-in with email.verification.registered', async () => {
        register.mockResolvedValueOnce(answer(true, 'sending') as never);
        const {gotoLogin} = mount();

        await fillValidAndSubmit();

        await waitFor(() => expect(gotoLogin).toHaveBeenCalledTimes(1));
        expect(gotoLogin).toHaveBeenCalledWith({message: 'email.verification.registered'});
    });

    it.each([
        ['false, verification_email absent', false, undefined],
        ['false, verification_email null', false, null],
        ['absent (an older server)', undefined, undefined],
    ] as const)('RCV-02: verification_required %s → auth.accountCreated, as before', async (_label, required, verificationEmail) => {
        register.mockResolvedValueOnce(answer(required, verificationEmail) as never);
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

    it('RCV-04: verification_required true, verification_email "held" → to the sign-in with email.verification.registeredHeld, as a warning', async () => {
        register.mockResolvedValueOnce(answer(true, 'held') as never);
        const {gotoLogin} = mount();

        await fillValidAndSubmit();

        await waitFor(() => expect(gotoLogin).toHaveBeenCalledTimes(1));
        // the held case is a warning for the sign-in's box (lot E-26 (b)); the others carry no tone, as before
        expect(gotoLogin).toHaveBeenCalledWith({message: 'email.verification.registeredHeld', tone: 'warning'});
    });

    // The sentence says how long until an email fits again (E-26-q1, decision of 23/10/2026): the server's
    // `verification_retry_after_seconds`, in whole minutes rounded up, at least one — the `{minutes}` of the message.
    it.each([
        [150, 3],
        [60, 1],
        [61, 2],
        [1, 1],
        [3600, 60],
    ])('RCV-04b: held for %i s → the message is given {minutes: %i}', async (seconds, minutes) => {
        register.mockResolvedValueOnce(answer(true, 'held', seconds) as never);
        const {gotoLogin} = mount();

        await fillValidAndSubmit();

        await waitFor(() => expect(gotoLogin).toHaveBeenCalledTimes(1));
        expect(translate).toHaveBeenCalledWith('email.verification.registeredHeld', {values: {minutes}});
    });

    it.each([
        ['null', null],
        ['absent (a server that does not say)', undefined],
    ])('RCV-04c: held with the time %s → at least one minute, never a missing value', async (_label, seconds) => {
        register.mockResolvedValueOnce(answer(true, 'held', seconds) as never);
        const {gotoLogin} = mount();

        await fillValidAndSubmit();

        await waitFor(() => expect(gotoLogin).toHaveBeenCalledTimes(1));
        expect(translate).toHaveBeenCalledWith('email.verification.registeredHeld', {values: {minutes: 1}});
    });

    it('RCV-05: verification_required true and no verification_email key at all (an older server) → email.verification.registered, the fallback', async () => {
        const fromAnOlderServer = answer(true);
        expect('verification_email' in fromAnOlderServer, 'setup: the answer must not carry the field at all').toBe(false);
        register.mockResolvedValueOnce(fromAnOlderServer as never);
        const {gotoLogin} = mount();

        await fillValidAndSubmit();

        await waitFor(() => expect(gotoLogin).toHaveBeenCalledTimes(1));
        expect(gotoLogin).toHaveBeenCalledWith({message: 'email.verification.registered'});
    });
});
