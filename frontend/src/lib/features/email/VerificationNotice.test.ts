// @vitest-environment jsdom
/**
 * VerificationNotice — the sign-in of an account that waits for its verification link (workstream E, lot E5a; developer
 * decision 44): «verify your email», and «send the link again» with the credentials just typed in the sign-in form.
 *
 * The contract under test:
 *   - the notice (`email-verification-notice`) says `email.verification.loginRequired` in an alert, with the resend
 *     button (`email-verification-resend`, `email.verification.resend`); it publishes `data-busy`/`aria-busy`;
 *   - the button is disabled while the username or the password is empty, and a click then sends nothing; typing them
 *     later enables it;
 *   - a click sends `resendEmailVerification(username, password)` once, with the props as they are; while it runs the
 *     notice is busy, the button disabled and labelled `email.verification.resending`, no outcome shown, and a second
 *     click sends nothing;
 *   - sent: the outcome `sent` (`email.verification.resent`, `OUTCOME_CLASSES.sent`) and the event
 *     `email.verification.resent` with the language; refused: the outcome `failed`, worded by
 *     `resendFailureMessage($_, readResendFailure(error))`, drawn with `OUTCOME_CLASSES.failed`, and the event
 *     `email.verification.resendFailed` with the failure — the button usable again either way;
 *   - on a blocked instance (lot E-11): the route's own 401 is coded `INVALID_CREDENTIALS` and says the credentials are
 *     wrong; the plain 401 the block answers a caller without a session says the sign-in's `auth.instanceBlocked`, never
 *     that the credentials are wrong, and the event carries `INSTANCE_BLOCKED`; the button stays, for once it is unblocked;
 *   - a new attempt clears the previous outcome; the outcome is rendered from state, so it follows a change of language.
 *
 * Mocks, all owned here: `./verificationApi`'s `resendEmailVerification` is a fake the test answers (deferred where the
 * request in flight is the subject) — `readResendFailure` stays the real one, and a refusal is built as the client
 * raises it, axios's own `AxiosError` carrying the response; `$lib/stores/app/notify.svelte`: a spy (the event, not a
 * toast, is the contract); `$lib/i18n`: `_` is a writable translator answering `[<language>] <key> {<values>}`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Writable} from 'svelte/store';
import {AxiosError, AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const fake = vi.hoisted(() => {
    /** The translator of one language: `[it] email.verification.resendErrors.EMAIL_RATE_LIMITED {minutes=3}`. */
    function translatorFor(language: string) {
        return (key: string, options?: {values?: Record<string, unknown>}): string => {
            const values = options?.values ?? {};
            const shown = Object.keys(values)
                .sort()
                .map((name) => `${name}=${String(values[name])}`);
            return shown.length > 0 ? `[${language}] ${key} {${shown.join(', ')}}` : `[${language}] ${key}`;
        };
    }
    return {
        translatorFor,
        resendEmailVerification: vi.fn().mockName('resendEmailVerification'),
        notify: vi.fn().mockName('notify'),
    };
});

vi.mock('./verificationApi', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./verificationApi')>()),
    resendEmailVerification: fake.resendEmailVerification,
}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: fake.notify}));
vi.mock('$lib/i18n', async () => {
    const {writable} = await import('svelte/store');
    return {_: writable(fake.translatorFor('en'))};
});

import VerificationNotice from './VerificationNotice.svelte';
import {_} from '$lib/i18n';
import {OUTCOME_CLASSES} from './emailText';

type Translator = ReturnType<typeof fake.translatorFor>;
const translator = _ as unknown as Writable<Translator>;

/** What the notice must render for `key` with `values` in `language`: this file's translator, never the catalogue. */
function say(key: string, values?: Record<string, unknown>, language = 'en'): string {
    return fake.translatorFor(language)(key, values ? {values} : undefined);
}

const USERNAME = 'zq_alice';
const PASSWORD = 'Verify-Pass-2026';

const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

/** What «resend» answers wrong credentials since lot E-11 (`api/v1/email.py`): its own 401, coded like E's other refusals. */
const INVALID_CREDENTIALS_BODY = {detail: {error_code: 'INVALID_CREDENTIALS', message: 'Invalid credentials'}};

/** What axios rejects with when the server answers `status` (lib/core/settle.js). */
function axiosRefusal(status: number, data: unknown): AxiosError {
    const response: AxiosResponse = {status, statusText: '', headers: {'content-type': 'application/json'}, config: REQUEST, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, REQUEST, {}, response);
}

/** A promise this test settles by hand, so "in flight" is a state it controls. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

const notice = () => screen.getByTestId('email-verification-notice');
const resendButton = () => screen.getByTestId('email-verification-resend');
const outcome = () => screen.queryByTestId('email-verification-outcome');

/** Waits for the notice to be idle again. */
async function idle(): Promise<void> {
    await waitFor(() => expect(notice()).toHaveAttribute('data-busy', 'false'));
}

beforeAll(() => {
    // The absences asserted below would pass vacuously in an environment where effects never run.
    assertEffectsRun();
});

beforeEach(() => {
    fake.resendEmailVerification.mockReset();
    fake.notify.mockReset();
    translator.set(fake.translatorFor('en'));
});

afterEach(() => {
    cleanup();
});

describe('VerificationNotice — at rest', () => {
    it('VNT-01: says the address is not verified yet, in an alert, and offers to send the link again', () => {
        render(VerificationNotice, {props: {username: USERNAME, password: PASSWORD}});

        expect(notice()).toHaveAttribute('data-busy', 'false');
        expect(notice()).toHaveAttribute('aria-busy', 'false');
        expect(screen.getByRole('alert')).toHaveTextContent(say('email.verification.loginRequired'));
        expect(resendButton()).toHaveTextContent(say('email.verification.resend'));
        expect(resendButton()).toBeEnabled();
        expect(outcome()).toBeNull();
    });

    it.each([
        {label: 'no username', username: '', password: PASSWORD},
        {label: 'no password', username: USERNAME, password: ''},
        {label: 'neither', username: '', password: ''},
    ])('VNT-02: with $label the button is disabled, and a click sends nothing', async ({username, password}) => {
        render(VerificationNotice, {props: {username, password}});

        expect(resendButton()).toBeDisabled();
        await fireEvent.click(resendButton());

        expect(fake.resendEmailVerification).not.toHaveBeenCalled();
        expect(outcome()).toBeNull();
    });

    it('VNT-03: the credentials typed later enable it', async () => {
        const view = render(VerificationNotice, {props: {username: USERNAME, password: ''}});
        expect(resendButton()).toBeDisabled();

        await view.rerender({username: USERNAME, password: PASSWORD});

        expect(resendButton()).toBeEnabled();
    });
});

describe('VerificationNotice — sending the link again', () => {
    it('VNT-04: one request with the credentials; busy while it runs, a second click sends nothing; sent, then the event with the language', async () => {
        const request = deferred<string>();
        fake.resendEmailVerification.mockReturnValueOnce(request.promise);
        render(VerificationNotice, {props: {username: USERNAME, password: PASSWORD}});

        await fireEvent.click(resendButton());
        await waitFor(() => expect(notice()).toHaveAttribute('data-busy', 'true'));
        expect(notice()).toHaveAttribute('aria-busy', 'true');
        expect(resendButton()).toBeDisabled();
        expect(resendButton()).toHaveTextContent(say('email.verification.resending'));
        expect(outcome()).toBeNull();
        await fireEvent.click(resendButton());
        expect(fake.resendEmailVerification).toHaveBeenCalledTimes(1);
        expect(fake.resendEmailVerification).toHaveBeenCalledWith(USERNAME, PASSWORD);
        expect(fake.notify).not.toHaveBeenCalled();

        request.resolve('it');
        await idle();

        expect(outcome()).toHaveAttribute('data-outcome', 'sent');
        expect(outcome()).toHaveTextContent(say('email.verification.resent'));
        expect(outcome()).toHaveAttribute('class', OUTCOME_CLASSES.sent);
        expect(outcome()).toHaveAttribute('aria-live', 'polite');
        expect(fake.notify).toHaveBeenCalledTimes(1);
        expect(fake.notify).toHaveBeenCalledWith({name: 'email.verification.resent', detail: {language: 'it'}});
        expect(resendButton()).toBeEnabled();
        expect(resendButton()).toHaveTextContent(say('email.verification.resend'));
    });

    it.each<{label: string; raise: () => unknown; failure: Record<string, unknown>; key: string; values?: Record<string, unknown>}>([
        {label: '401 INVALID_CREDENTIALS, the route’s own refusal', raise: () => axiosRefusal(401, INVALID_CREDENTIALS_BODY), failure: {errorCode: 'INVALID_CREDENTIALS'}, key: 'email.verification.resendErrors.INVALID_CREDENTIALS'},
        {
            label: '429 EMAIL_RATE_LIMITED',
            raise: () => axiosRefusal(429, {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 180, message: 'Too many requests: try again later'}}),
            failure: {errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 180},
            key: 'email.verification.resendErrors.EMAIL_RATE_LIMITED',
            values: {minutes: 3},
        },
        {
            label: '409 EMAIL_VERIFICATION_NOT_NEEDED',
            raise: () => axiosRefusal(409, {detail: {error_code: 'EMAIL_VERIFICATION_NOT_NEEDED', message: 'This account is active: sign in'}}),
            failure: {errorCode: 'EMAIL_VERIFICATION_NOT_NEEDED'},
            key: 'email.verification.resendErrors.EMAIL_VERIFICATION_NOT_NEEDED',
        },
        {
            label: '409 USER_LIMIT_REACHED',
            raise: () => axiosRefusal(409, {detail: {error_code: 'USER_LIMIT_REACHED', message: 'The instance has reached its maximum number of users'}}),
            failure: {errorCode: 'USER_LIMIT_REACHED'},
            key: 'email.verification.resendErrors.USER_LIMIT_REACHED',
        },
        {label: '403 ACCOUNT_DISABLED', raise: () => axiosRefusal(403, {detail: {error_code: 'ACCOUNT_DISABLED', message: 'Account is disabled'}}), failure: {errorCode: 'ACCOUNT_DISABLED'}, key: 'email.verification.resendErrors.ACCOUNT_DISABLED'},
        {label: '409 EMAIL_UNAVAILABLE', raise: () => axiosRefusal(409, {detail: {error_code: 'EMAIL_UNAVAILABLE', message: 'This instance cannot send emails'}}), failure: {errorCode: 'EMAIL_UNAVAILABLE'}, key: 'email.verification.resendErrors.unavailable'},
        {
            label: '502 EMAIL_DELIVERY_FAILED',
            raise: () => axiosRefusal(502, {detail: {error_code: 'EMAIL_DELIVERY_FAILED', message: 'The email could not be sent'}}),
            failure: {errorCode: 'EMAIL_DELIVERY_FAILED'},
            key: 'email.verification.resendErrors.unavailable',
        },
        {label: 'a request that reached no server', raise: () => new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {}), failure: {errorCode: 'UNKNOWN'}, key: 'email.verification.resendErrors.generic'},
    ])('VNT-05: $label — the outcome failed with its message, the event with the failure, the button usable again', async ({raise, failure, key, values}) => {
        fake.resendEmailVerification.mockRejectedValueOnce(raise());
        render(VerificationNotice, {props: {username: USERNAME, password: PASSWORD}});

        await fireEvent.click(resendButton());
        await waitFor(() => expect(outcome()).not.toBeNull());
        await idle();

        expect(outcome()).toHaveAttribute('data-outcome', 'failed');
        expect(outcome()).toHaveTextContent(say(key, values));
        expect(outcome()).toHaveAttribute('class', OUTCOME_CLASSES.failed);
        expect(fake.notify).toHaveBeenCalledTimes(1);
        expect(fake.notify).toHaveBeenCalledWith({name: 'email.verification.resendFailed', detail: failure});
        expect(resendButton()).toBeEnabled();
    });

    it('VNT-06: a new attempt clears the previous outcome while it runs', async () => {
        const second = deferred<string>();
        fake.resendEmailVerification.mockRejectedValueOnce(axiosRefusal(401, INVALID_CREDENTIALS_BODY)).mockReturnValueOnce(second.promise);
        render(VerificationNotice, {props: {username: USERNAME, password: PASSWORD}});
        await fireEvent.click(resendButton());
        await waitFor(() => expect(outcome()).toHaveAttribute('data-outcome', 'failed'));

        await fireEvent.click(resendButton());
        await waitFor(() => expect(notice()).toHaveAttribute('data-busy', 'true'));

        expect(outcome(), 'the old outcome is gone while the new request runs').toBeNull();
        second.resolve('en');
        await waitFor(() => expect(outcome()).toHaveAttribute('data-outcome', 'sent'));
        expect(fake.notify.mock.calls.map(([event]) => event.name)).toEqual(['email.verification.resendFailed', 'email.verification.resent']);
    });

    it('VNT-07: the outcome follows a change of language', async () => {
        fake.resendEmailVerification.mockRejectedValueOnce(axiosRefusal(429, {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 240}}));
        render(VerificationNotice, {props: {username: USERNAME, password: PASSWORD}});
        await fireEvent.click(resendButton());
        await waitFor(() => expect(outcome()).toHaveTextContent(say('email.verification.resendErrors.EMAIL_RATE_LIMITED', {minutes: 4})));

        translator.set(fake.translatorFor('it'));

        await waitFor(() => expect(outcome()).toHaveTextContent(say('email.verification.resendErrors.EMAIL_RATE_LIMITED', {minutes: 4}, 'it')));
        expect(resendButton()).toHaveTextContent(say('email.verification.resend', undefined, 'it'));
        expect(fake.resendEmailVerification, 'no new request: the words changed, not the outcome').toHaveBeenCalledTimes(1);
    });
});

describe('VerificationNotice — on a blocked instance (lot E-11)', () => {
    it('VNT-08: the plain 401 the block answers a caller without a session says the instance is blocked, never that the credentials are wrong', async () => {
        fake.resendEmailVerification.mockRejectedValueOnce(axiosRefusal(401, {detail: 'Not authenticated'}));
        render(VerificationNotice, {props: {username: USERNAME, password: PASSWORD}});

        await fireEvent.click(resendButton());
        await waitFor(() => expect(outcome()).not.toBeNull());
        await idle();

        expect(outcome()).toHaveAttribute('data-outcome', 'failed');
        expect(outcome(), 'a 401 that is not the route’s own is the instance’s block: the sign-in’s own words for it').toHaveTextContent(say('auth.instanceBlocked'));
        expect(outcome(), 'never «wrong username or password» on a blocked instance').not.toHaveTextContent(say('email.verification.resendErrors.INVALID_CREDENTIALS'));
        expect(outcome()).toHaveAttribute('class', OUTCOME_CLASSES.failed);
        expect(fake.notify).toHaveBeenCalledTimes(1);
        expect(fake.notify, 'the event carries the failure the notice read').toHaveBeenCalledWith({name: 'email.verification.resendFailed', detail: {errorCode: 'INSTANCE_BLOCKED'}});
        expect(resendButton(), 'the button stays: once the instance is unblocked, the click works').toBeEnabled();
    });
});
