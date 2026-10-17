// @vitest-environment jsdom
/**
 * ForgotPasswordEmailForm — «forgot password» by email (workstream E, lot E4a), tested standalone; its host on the
 * sign-in, A's `ForgotPasswordCard` (lot E4b), is tested in `features/auth/ForgotPasswordCard.email.test.ts`.
 *
 * The contract under test:
 *   - the form (`forgot-email-form`) has the identifier field (`forgot-email-identifier`, labelled `email.forgot.label`)
 *     and the submit (`forgot-email-submit`, `email.forgot.submit`), disabled while the field is empty or blank — a
 *     submit then sends nothing; it publishes `data-busy`/`aria-busy`;
 *   - a submit sends `requestPasswordResetEmail(identifier)` once, the identifier trimmed; while it runs the form is busy,
 *     the field and the submit disabled, the submit `email.forgot.sending`, no outcome, and a second submit sends nothing;
 *   - accepted (the 202, the same for everyone): the outcome `accepted` (`email.forgot.accepted`) drawn as an info notice
 *     (`NOTICE_CLASSES.info`), and the event `email.forgot.accepted`; refused: the outcome `failed`, worded by
 *     `forgotFailureMessage($_, readForgotFailure(error))`, drawn with `OUTCOME_CLASSES.failed`, and the event
 *     `email.forgot.refused` with the failure; the field keeps what was typed (the route has had no hold since lot E4b:
 *     no `FORGOT_PASSWORD_DISABLED` to word);
 *   - a new submit clears the previous outcome; the outcome follows a change of language.
 *
 * Mocks, all owned here: `./forgotPasswordApi`'s `requestPasswordResetEmail` is a fake the test answers (deferred where
 * the request in flight is the subject) — `readForgotFailure` stays the real one, and a refusal is built as the client
 * raises it, axios's own `AxiosError`; `$lib/stores/app/notify.svelte` a spy; `$lib/i18n`: `_` is a writable translator
 * answering `[<language>] <key> {<values>}`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Writable} from 'svelte/store';
import {AxiosError, AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const fake = vi.hoisted(() => {
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
        requestPasswordResetEmail: vi.fn().mockName('requestPasswordResetEmail'),
        notify: vi.fn().mockName('notify'),
    };
});

vi.mock('./forgotPasswordApi', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./forgotPasswordApi')>()),
    requestPasswordResetEmail: fake.requestPasswordResetEmail,
}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: fake.notify}));
vi.mock('$lib/i18n', async () => {
    const {writable} = await import('svelte/store');
    return {_: writable(fake.translatorFor('en'))};
});

import ForgotPasswordEmailForm from './ForgotPasswordEmailForm.svelte';
import {_} from '$lib/i18n';
import {NOTICE_CLASSES, OUTCOME_CLASSES} from './emailText';

type Translator = ReturnType<typeof fake.translatorFor>;
const translator = _ as unknown as Writable<Translator>;

function say(key: string, values?: Record<string, unknown>, language = 'en'): string {
    return fake.translatorFor(language)(key, values ? {values} : undefined);
}

const REQUEST = {headers: new AxiosHeaders()} as InternalAxiosRequestConfig;

function axiosRefusal(status: number, data: unknown): AxiosError {
    const response: AxiosResponse = {status, statusText: '', headers: {'content-type': 'application/json'}, config: REQUEST, request: {}, data};
    return new AxiosError(`Request failed with status code ${status}`, status < 500 ? AxiosError.ERR_BAD_REQUEST : AxiosError.ERR_BAD_RESPONSE, REQUEST, {}, response);
}

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** A refusal of `POST /email/password-reset`: the instance cannot send emails. */
const UNAVAILABLE = {detail: {error_code: 'EMAIL_UNAVAILABLE', message: 'This instance cannot send emails'}};

const form = () => screen.getByTestId('forgot-email-form');
const field = () => screen.getByTestId('forgot-email-identifier') as HTMLInputElement;
const submit = () => screen.getByTestId('forgot-email-submit');
const outcome = () => screen.queryByTestId('forgot-email-outcome');

async function type(value: string): Promise<void> {
    await fireEvent.input(field(), {target: {value}});
}

async function idle(): Promise<void> {
    await waitFor(() => expect(form()).toHaveAttribute('data-busy', 'false'));
}

beforeAll(() => {
    assertEffectsRun();
});

beforeEach(() => {
    fake.requestPasswordResetEmail.mockReset();
    fake.requestPasswordResetEmail.mockResolvedValue(undefined);
    fake.notify.mockReset();
    translator.set(fake.translatorFor('en'));
});

afterEach(() => {
    cleanup();
});

describe('ForgotPasswordEmailForm — at rest', () => {
    it('FPF-01: the labelled identifier field, empty; the submit disabled; no outcome', () => {
        render(ForgotPasswordEmailForm);

        expect(form()).toHaveAttribute('data-busy', 'false');
        expect(form()).toHaveAttribute('aria-busy', 'false');
        expect(screen.getByLabelText(say('email.forgot.label'))).toBe(field());
        expect(field()).toHaveValue('');
        expect(submit()).toHaveTextContent(say('email.forgot.submit'));
        expect(submit()).toBeDisabled();
        expect(outcome()).toBeNull();
    });

    it('FPF-02: a blank identifier keeps the submit disabled, and submitting the form sends nothing', async () => {
        render(ForgotPasswordEmailForm);

        await type('   ');
        expect(submit()).toBeDisabled();
        await fireEvent.submit(form());

        expect(fake.requestPasswordResetEmail).not.toHaveBeenCalled();
        expect(outcome()).toBeNull();
    });
});

describe('ForgotPasswordEmailForm — asking for a link', () => {
    it('FPF-03: the identifier trimmed, once; busy while it runs — the field and the submit disabled, a second submit sends nothing; then accepted as an info notice, and the event', async () => {
        const request = deferred<void>();
        fake.requestPasswordResetEmail.mockReturnValueOnce(request.promise);
        render(ForgotPasswordEmailForm);
        await type('  zq_alice@example.com  ');
        expect(submit()).toBeEnabled();

        await fireEvent.click(submit());
        await waitFor(() => expect(form()).toHaveAttribute('data-busy', 'true'));
        expect(form()).toHaveAttribute('aria-busy', 'true');
        expect(field()).toBeDisabled();
        expect(submit()).toBeDisabled();
        expect(submit()).toHaveTextContent(say('email.forgot.sending'));
        expect(outcome()).toBeNull();
        await fireEvent.submit(form());
        expect(fake.requestPasswordResetEmail).toHaveBeenCalledTimes(1);
        expect(fake.requestPasswordResetEmail).toHaveBeenCalledWith('zq_alice@example.com');
        expect(fake.notify).not.toHaveBeenCalled();

        request.resolve();
        await idle();

        expect(outcome()).toHaveAttribute('data-outcome', 'accepted');
        expect(outcome()).toHaveTextContent(say('email.forgot.accepted'));
        expect(outcome()).toHaveAttribute('class', NOTICE_CLASSES.info);
        expect(outcome()).toHaveAttribute('aria-live', 'polite');
        expect(fake.notify).toHaveBeenCalledTimes(1);
        expect(fake.notify).toHaveBeenCalledWith({name: 'email.forgot.accepted'});
        expect(submit()).toBeEnabled();
    });

    it('FPF-04: a refusal — the instance cannot send — its message, and the event; the field keeps what was typed, the form usable again', async () => {
        fake.requestPasswordResetEmail.mockRejectedValueOnce(axiosRefusal(409, UNAVAILABLE));
        render(ForgotPasswordEmailForm);
        await type('zq_alice');

        await fireEvent.click(submit());
        await waitFor(() => expect(outcome()).toHaveAttribute('data-outcome', 'failed'));
        await idle();

        expect(outcome()).toHaveTextContent(say('email.forgot.errors.unavailable'));
        expect(outcome()).toHaveAttribute('class', OUTCOME_CLASSES.failed);
        expect(fake.notify).toHaveBeenCalledWith({name: 'email.forgot.refused', detail: {errorCode: 'EMAIL_UNAVAILABLE'}});
        expect(field()).toHaveValue('zq_alice');
        expect(field()).toBeEnabled();
        expect(submit()).toBeEnabled();
    });

    it.each<{label: string; raise: () => unknown; failure: Record<string, unknown>; key: string; values?: Record<string, unknown>}>([
        {label: '409 EMAIL_UNAVAILABLE', raise: () => axiosRefusal(409, {detail: {error_code: 'EMAIL_UNAVAILABLE', message: 'This instance cannot send emails'}}), failure: {errorCode: 'EMAIL_UNAVAILABLE'}, key: 'email.forgot.errors.unavailable'},
        {label: '409 EMAIL_LINKS_UNAVAILABLE', raise: () => axiosRefusal(409, {detail: {error_code: 'EMAIL_LINKS_UNAVAILABLE', message: 'This instance cannot send emails with a link'}}), failure: {errorCode: 'EMAIL_LINKS_UNAVAILABLE'}, key: 'email.forgot.errors.unavailable'},
        {label: '429 EMAIL_RATE_LIMITED', raise: () => axiosRefusal(429, {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 840}}), failure: {errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 840}, key: 'email.forgot.errors.EMAIL_RATE_LIMITED', values: {minutes: 14}},
        {label: '422', raise: () => axiosRefusal(422, {detail: [{loc: ['body', 'identifier'], msg: 'too long', type: 'string_too_long'}]}), failure: {errorCode: 'INVALID'}, key: 'email.forgot.errors.generic'},
        {label: 'a request that reached no server', raise: () => new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {}), failure: {errorCode: 'UNKNOWN'}, key: 'email.forgot.errors.generic'},
    ])('FPF-05: $label — the outcome failed with its message, and the event with the failure', async ({raise, failure, key, values}) => {
        fake.requestPasswordResetEmail.mockRejectedValueOnce(raise());
        render(ForgotPasswordEmailForm);
        await type('zq_alice');

        await fireEvent.click(submit());
        await waitFor(() => expect(outcome()).not.toBeNull());
        await idle();

        expect(outcome()).toHaveAttribute('data-outcome', 'failed');
        expect(outcome()).toHaveTextContent(say(key, values));
        expect(outcome()).toHaveAttribute('class', OUTCOME_CLASSES.failed);
        expect(fake.notify).toHaveBeenCalledTimes(1);
        expect(fake.notify).toHaveBeenCalledWith({name: 'email.forgot.refused', detail: failure});
    });

    it('FPF-06: a new submit clears the previous outcome while it runs, and the outcome follows a change of language', async () => {
        const second = deferred<void>();
        fake.requestPasswordResetEmail.mockRejectedValueOnce(axiosRefusal(409, UNAVAILABLE)).mockReturnValueOnce(second.promise);
        render(ForgotPasswordEmailForm);
        await type('zq_alice');
        await fireEvent.click(submit());
        await waitFor(() => expect(outcome()).toHaveTextContent(say('email.forgot.errors.unavailable')));

        translator.set(fake.translatorFor('it'));
        await waitFor(() => expect(outcome()).toHaveTextContent(say('email.forgot.errors.unavailable', undefined, 'it')));
        expect(submit()).toHaveTextContent(say('email.forgot.submit', undefined, 'it'));

        await fireEvent.click(submit());
        await waitFor(() => expect(form()).toHaveAttribute('data-busy', 'true'));
        expect(outcome(), 'the old outcome is gone while the new request runs').toBeNull();
        second.resolve();
        await waitFor(() => expect(outcome()).toHaveTextContent(say('email.forgot.accepted', undefined, 'it')));
        expect(fake.notify.mock.calls.map(([event]) => event.name)).toEqual(['email.forgot.refused', 'email.forgot.accepted']);
    });
});
