// @vitest-environment jsdom
/**
 * LoginCard and email verification (lot E5b, developer decision 44): the sign-in of an account that waits for its link.
 *
 * The contract under test:
 *   - `authError` `{key: 'email.verification.loginRequired'}` (the login's 403 `EMAIL_NOT_VERIFIED`) → the card shows
 *     `VerificationNotice` (`email-verification-notice`) instead of the danger box (`login-error`, absent);
 *   - the notice carries the username and the password typed in the form: «send the link again» sends exactly them;
 *   - every other error is drawn in the danger box as before, without the notice; no error, neither.
 *
 * Mocks, as in workstream A's `LoginCard.test.ts` (left to A): the identity translator, the auth store at rest with a
 * lazy `authError` the test sets, `$app/navigation`, the instance configuration and the global settings. The notice is
 * E's real `features/email/VerificationNotice.svelte`; only its request is a fake (`resendEmailVerification`), and
 * `notify` a spy. Red until E5b is applied (`LoginCard.svelte`, `AuthErrorKey`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {writable} from 'svelte/store';
import type {AuthError, AuthErrorKey} from '$lib/types';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';

vi.mock('$lib/i18n', () => ({_: {subscribe: (run: (value: unknown) => void) => translator.subscribe(run)}}));
vi.mock('$lib/stores/app/auth', async () => {
    const {readable} = await import('svelte/store');
    return {
        auth: {login: vi.fn()},
        authError: {subscribe: (run: (value: unknown) => void) => signInError.subscribe(run)},
        isAuthLoading: readable(false),
    };
});
vi.mock('$app/navigation', () => ({goto: vi.fn()}));
const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const OPEN: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
    return {
        OPEN,
        instance: reactiveBox<{config: InstanceConfig}>({config: OPEN}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
        resend: vi.fn().mockName('resendEmailVerification'),
        notify: vi.fn().mockName('notify'),
    };
});
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: mocks.OPEN,
    instanceConfig: {
        get config() {
            return mocks.instance.config;
        },
        get loaded() {
            return true;
        },
        get failed() {
            return false;
        },
        load: mocks.instanceLoad,
    },
}));
vi.mock('$lib/stores/app/globalSettings', async () => {
    const {readable} = await import('svelte/store');
    return {globalSettings: {subscribe: readable({enable_registration: false}).subscribe, load: vi.fn().mockResolvedValue(undefined)}};
});
vi.mock('$lib/features/email/verificationApi', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/features/email/verificationApi')>()),
    resendEmailVerification: mocks.resend,
}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: mocks.notify}));

import LoginCard from './LoginCard.svelte';

const translator = writable<(key: string) => string>((key: string) => key);
const signInError = writable<AuthError | null>(null);

const notice = () => screen.queryByTestId('email-verification-notice');
const dangerBox = () => screen.queryByTestId('login-error');

async function typeCredentials(username: string, password: string): Promise<void> {
    await fireEvent.input(screen.getByTestId('login-username'), {target: {value: username}});
    await fireEvent.input(screen.getByTestId('login-password'), {target: {value: password}});
}

beforeEach(() => {
    mocks.instance.config = mocks.OPEN;
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockResolvedValue(undefined);
    mocks.resend.mockReset();
    mocks.resend.mockResolvedValue('en');
    mocks.notify.mockReset();
    signInError.set(null);
});

afterEach(() => {
    cleanup();
    signInError.set(null);
});

describe('LoginCard — an account waiting for its email verification', () => {
    it('LVR-01: email.verification.loginRequired → the verification notice, and no danger box', async () => {
        render(LoginCard);

        signInError.set({key: 'email.verification.loginRequired'});

        await waitFor(() => expect(notice()).not.toBeNull());
        expect(notice()).toHaveTextContent('email.verification.loginRequired');
        expect(dangerBox()).toBeNull();
    });

    it('LVR-02: «send the link again» sends the username and the password typed in the form', async () => {
        render(LoginCard);
        await typeCredentials('zq_vera', 'Hooks-Pass-2026');
        signInError.set({key: 'email.verification.loginRequired'});
        await waitFor(() => expect(notice()).not.toBeNull());

        await fireEvent.click(screen.getByTestId('email-verification-resend'));

        await waitFor(() => expect(mocks.resend).toHaveBeenCalledTimes(1));
        expect(mocks.resend).toHaveBeenCalledWith('zq_vera', 'Hooks-Pass-2026');
    });

    it.each<AuthErrorKey>(['auth.invalidCredentials', 'auth.accountDisabled', 'auth.loginFailed'])('LVR-03: %s → the danger box, as before, and no notice', async (key) => {
        render(LoginCard);

        signInError.set({key});

        await waitFor(() => expect(dangerBox()).toHaveTextContent(key));
        expect(notice()).toBeNull();
    });

    it('LVR-04: no error — neither the notice nor the danger box', () => {
        render(LoginCard);

        expect(notice()).toBeNull();
        expect(dangerBox()).toBeNull();
    });
});
