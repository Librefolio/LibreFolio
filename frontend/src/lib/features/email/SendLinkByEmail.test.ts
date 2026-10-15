// @vitest-environment jsdom
/**
 * SendLinkByEmail — «send by email» next to a shared link (workstream E, lot E4a), tested standalone: A's registry line
 * that hosts it in the share dialogs comes with lot E4b.
 *
 * The contract under test:
 *   - an invitation (`data-purpose="invite"`) shows the address field (`send-link-email-to`), labelled and prefilled with
 *     the address the dialog knows (`context.email`, empty without one) and editable; a reset link shows no field, only
 *     `email.sendLink.resetTarget`: it goes to its account's address alone. Both say where the link starts
 *     (`email.sendLink.publicUrlHint`);
 *   - the button (`send-link-email-button`) sends the token of the link — `tokenFromLink` — once: an invitation with the
 *     address trimmed, or with none when the field is empty or blank; a reset link never with an address, whatever the
 *     dialog knows. Without a token the button is disabled and sends nothing;
 *   - while it runs: `data-busy`/`aria-busy`, the field and the button disabled, the button `email.sendLink.sending`, no
 *     outcome, and a second click sends nothing;
 *   - sent: the outcome `sent` names the address the server answered (`email.sendLink.sent {to}`), drawn with
 *     `OUTCOME_CLASSES.sent`, and the event `email.link.sent` with the purpose and the language; refused: the outcome
 *     `failed`, worded by `linkSendFailureMessage($_, readLinkSendFailure(error))` — the SMTP reason for a refused
 *     delivery —, drawn with `OUTCOME_CLASSES.failed`, and the event `email.link.sendFailed` with the purpose and the
 *     failure; the button usable again either way. A typed address FastAPI refuses on its own (a 422 whose `detail` is
 *     a list) is said to be an invalid address, and stays in the field to be corrected;
 *   - a new attempt clears the previous outcome; the outcome follows a change of language.
 *
 * Mocks, all owned here: `./sendLinkApi`'s `sendLinkByEmail` is a fake the test answers (deferred where the request in
 * flight is the subject) — `tokenFromLink` and `readLinkSendFailure` stay the real ones, and a refusal is built as the
 * client raises it, axios's own `AxiosError`; `$lib/features/instance/instanceConfig.svelte` a still fake (the
 * component never reads it); `$lib/stores/app/notify.svelte` a spy; `$lib/i18n`: `_` is a writable translator
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
        sendLinkByEmail: vi.fn().mockName('sendLinkByEmail'),
        notify: vi.fn().mockName('notify'),
    };
});

vi.mock('./sendLinkApi', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./sendLinkApi')>()),
    sendLinkByEmail: fake.sendLinkByEmail,
}));
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({instanceConfig: {config: {profile: 'selfhosted', accounts: {registration_mode: 'invite', registration_locked: false}}}}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: fake.notify}));
vi.mock('$lib/i18n', async () => {
    const {writable} = await import('svelte/store');
    return {_: writable(fake.translatorFor('en'))};
});

import SendLinkByEmail from './SendLinkByEmail.svelte';
import {_} from '$lib/i18n';
import {OUTCOME_CLASSES} from './emailText';

type Translator = ReturnType<typeof fake.translatorFor>;
const translator = _ as unknown as Writable<Translator>;

function say(key: string, values?: Record<string, unknown>, language = 'en'): string {
    return fake.translatorFor(language)(key, values ? {values} : undefined);
}

const TOKEN = 'inv-Token_0123';
const INVITE_LINK = `https://folio.example.com/invite#token=${TOKEN}`;
const RESET_LINK = `https://folio.example.com/reset-password#token=${TOKEN}`;
const GUEST = 'zq-guest@example.com';

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

const root = () => screen.getByTestId('send-link-email');
const field = () => screen.queryByTestId('send-link-email-to') as HTMLInputElement | null;
const button = () => screen.getByTestId('send-link-email-button');
const outcome = () => screen.queryByTestId('send-link-email-outcome');

async function idle(): Promise<void> {
    await waitFor(() => expect(root()).toHaveAttribute('data-busy', 'false'));
}

/** The request the fake received: what the component asked to send. */
function sentRequest(): Record<string, unknown> {
    expect(fake.sendLinkByEmail).toHaveBeenCalledTimes(1);
    return fake.sendLinkByEmail.mock.calls[0][0];
}

beforeAll(() => {
    assertEffectsRun();
});

beforeEach(() => {
    fake.sendLinkByEmail.mockReset();
    fake.sendLinkByEmail.mockResolvedValue({to: GUEST, language: 'it'});
    fake.notify.mockReset();
    translator.set(fake.translatorFor('en'));
});

afterEach(() => {
    cleanup();
});

describe('SendLinkByEmail — an invitation', () => {
    it('SLE-01: the address field, labelled, prefilled with the address the dialog knows; the hint; the button', () => {
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {email: GUEST}}});

        expect(root()).toHaveAttribute('data-purpose', 'invite');
        expect(root()).toHaveAttribute('data-busy', 'false');
        expect(screen.getByLabelText(say('email.sendLink.toLabel'))).toBe(field());
        expect(field()).toHaveValue(GUEST);
        expect(field()).toHaveAttribute('placeholder', say('email.sendLink.toPlaceholder'));
        expect(screen.queryByTestId('send-link-email-target')).toBeNull();
        expect(root()).toHaveTextContent(say('email.sendLink.publicUrlHint'));
        expect(button()).toHaveTextContent(say('email.sendLink.button'));
        expect(button()).toBeEnabled();
        expect(outcome()).toBeNull();
    });

    it.each([
        {label: 'no address known', context: {}},
        {label: 'a null address', context: {email: null}},
    ])('SLE-02: $label — the field starts empty', ({context}) => {
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context}});

        expect(field()).toHaveValue('');
    });

    it.each<{label: string; typed: string | null; known: string | null; to: string | undefined}>([
        {label: 'the address the dialog knows, untouched', typed: null, known: GUEST, to: GUEST},
        {label: 'an address typed, trimmed', typed: '  zq-other@example.com  ', known: GUEST, to: 'zq-other@example.com'},
        {label: 'the field emptied: no address', typed: '', known: GUEST, to: undefined},
        {label: 'the field blank: no address', typed: '   ', known: GUEST, to: undefined},
        {label: 'nothing known, nothing typed: no address', typed: null, known: null, to: undefined},
    ])('SLE-03: $label', async ({typed, known, to}) => {
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {email: known}}});
        if (typed !== null) await fireEvent.input(field()!, {target: {value: typed}});

        await fireEvent.click(button());
        await idle();

        expect(sentRequest()).toEqual({purpose: 'invite', token: TOKEN, to});
        expect(sentRequest().to).toBe(to);
    });
});

describe('SendLinkByEmail — a reset link', () => {
    it('SLE-04: no address field, the account’s address said instead; sent without an address, whatever the dialog knows', async () => {
        render(SendLinkByEmail, {props: {link: RESET_LINK, purpose: 'password_reset', context: {email: 'zq-alice@example.com', username: 'zq_alice'}}});

        expect(root()).toHaveAttribute('data-purpose', 'password_reset');
        expect(field()).toBeNull();
        expect(screen.getByTestId('send-link-email-target')).toHaveTextContent(say('email.sendLink.resetTarget'));
        expect(root()).toHaveTextContent(say('email.sendLink.publicUrlHint'));
        await fireEvent.click(button());
        await idle();

        expect(sentRequest()).toEqual({purpose: 'password_reset', token: TOKEN, to: undefined});
        expect(sentRequest().to).toBeUndefined();
    });
});

describe('SendLinkByEmail — sending', () => {
    it.each([
        {label: 'a link without a fragment', link: 'https://folio.example.com/invite'},
        {label: 'a link with an empty token', link: 'https://folio.example.com/invite#token='},
    ])('SLE-05: $label — the button is disabled and a click sends nothing', async ({link}) => {
        render(SendLinkByEmail, {props: {link, purpose: 'invite', context: {email: GUEST}}});

        expect(button()).toBeDisabled();
        await fireEvent.click(button());

        expect(fake.sendLinkByEmail).not.toHaveBeenCalled();
    });

    it('SLE-06: busy while it runs — the field and the button disabled, no outcome, a second click sends nothing; then sent, naming the address the server answered, and the event', async () => {
        const request = deferred<{to: string; language: string}>();
        fake.sendLinkByEmail.mockReturnValueOnce(request.promise);
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {}}});

        await fireEvent.click(button());
        await waitFor(() => expect(root()).toHaveAttribute('data-busy', 'true'));
        expect(root()).toHaveAttribute('aria-busy', 'true');
        expect(field()).toBeDisabled();
        expect(button()).toBeDisabled();
        expect(button()).toHaveTextContent(say('email.sendLink.sending'));
        expect(outcome()).toBeNull();
        await fireEvent.click(button());
        expect(fake.sendLinkByEmail).toHaveBeenCalledTimes(1);

        request.resolve({to: 'zq-written-in-the-invitation@example.com', language: 'fr'});
        await idle();

        expect(outcome()).toHaveAttribute('data-outcome', 'sent');
        expect(outcome()).toHaveTextContent(say('email.sendLink.sent', {to: 'zq-written-in-the-invitation@example.com'}));
        expect(outcome()).toHaveAttribute('class', OUTCOME_CLASSES.sent);
        expect(fake.notify).toHaveBeenCalledTimes(1);
        expect(fake.notify).toHaveBeenCalledWith({name: 'email.link.sent', detail: {purpose: 'invite', language: 'fr'}});
        expect(button()).toBeEnabled();
        expect(field()).toBeEnabled();
    });

    it.each<{label: string; raise: () => unknown; failure: Record<string, unknown>; key: string; values?: Record<string, unknown>}>([
        {label: '409 EMAIL_UNAVAILABLE', raise: () => axiosRefusal(409, {detail: {error_code: 'EMAIL_UNAVAILABLE', problem: 'SMTP_PORT_INVALID'}}), failure: {errorCode: 'EMAIL_UNAVAILABLE'}, key: 'email.sendLink.errors.EMAIL_UNAVAILABLE'},
        {label: '409 EMAIL_LINKS_UNAVAILABLE', raise: () => axiosRefusal(409, {detail: {error_code: 'EMAIL_LINKS_UNAVAILABLE', problem: 'PUBLIC_URL_MISSING'}}), failure: {errorCode: 'EMAIL_LINKS_UNAVAILABLE'}, key: 'email.sendLink.errors.EMAIL_LINKS_UNAVAILABLE'},
        {label: '409 EMAIL_LINK_INVALID', raise: () => axiosRefusal(409, {detail: {error_code: 'EMAIL_LINK_INVALID', status: 'expired'}}), failure: {errorCode: 'EMAIL_LINK_INVALID'}, key: 'email.sendLink.errors.EMAIL_LINK_INVALID'},
        {label: '409 EMAIL_ACCOUNT_INACTIVE', raise: () => axiosRefusal(409, {detail: {error_code: 'EMAIL_ACCOUNT_INACTIVE'}}), failure: {errorCode: 'EMAIL_ACCOUNT_INACTIVE'}, key: 'email.sendLink.errors.EMAIL_ACCOUNT_INACTIVE'},
        {label: '422 EMAIL_RECIPIENT_REQUIRED', raise: () => axiosRefusal(422, {detail: {error_code: 'EMAIL_RECIPIENT_REQUIRED'}}), failure: {errorCode: 'EMAIL_RECIPIENT_REQUIRED'}, key: 'email.sendLink.errors.EMAIL_RECIPIENT_REQUIRED'},
        {label: '422 EMAIL_RECIPIENT_NOT_ALLOWED', raise: () => axiosRefusal(422, {detail: {error_code: 'EMAIL_RECIPIENT_NOT_ALLOWED'}}), failure: {errorCode: 'EMAIL_RECIPIENT_NOT_ALLOWED'}, key: 'email.sendLink.errors.EMAIL_RECIPIENT_NOT_ALLOWED'},
        {label: '422 EMAIL_RECIPIENT_INVALID', raise: () => axiosRefusal(422, {detail: {error_code: 'EMAIL_RECIPIENT_INVALID'}}), failure: {errorCode: 'EMAIL_RECIPIENT_INVALID'}, key: 'email.sendLink.errors.EMAIL_RECIPIENT_INVALID'},
        {label: '429 EMAIL_RATE_LIMITED', raise: () => axiosRefusal(429, {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 1800}}), failure: {errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 1800}, key: 'email.sendLink.errors.EMAIL_RATE_LIMITED', values: {minutes: 30}},
        {label: '502 EMAIL_DELIVERY_FAILED AUTH_FAILED', raise: () => axiosRefusal(502, {detail: {error_code: 'EMAIL_DELIVERY_FAILED', smtp_code: 'AUTH_FAILED'}}), failure: {errorCode: 'EMAIL_DELIVERY_FAILED', smtpCode: 'AUTH_FAILED'}, key: 'email.smtpErrors.AUTH_FAILED'},
        {label: 'a request that reached no server', raise: () => new AxiosError('Network Error', AxiosError.ERR_NETWORK, REQUEST, {}), failure: {errorCode: 'UNKNOWN'}, key: 'email.sendLink.errors.generic'},
    ])('SLE-07: $label — the outcome failed with its message, the event with the purpose and the failure, the button usable again', async ({raise, failure, key, values}) => {
        fake.sendLinkByEmail.mockRejectedValueOnce(raise());
        render(SendLinkByEmail, {props: {link: RESET_LINK, purpose: 'password_reset', context: {}}});

        await fireEvent.click(button());
        await waitFor(() => expect(outcome()).not.toBeNull());
        await idle();

        expect(outcome()).toHaveAttribute('data-outcome', 'failed');
        expect(outcome()).toHaveTextContent(say(key, values));
        expect(outcome()).toHaveAttribute('class', OUTCOME_CLASSES.failed);
        expect(fake.notify).toHaveBeenCalledTimes(1);
        expect(fake.notify).toHaveBeenCalledWith({name: 'email.link.sendFailed', detail: {purpose: 'password_reset', ...failure}});
        expect(button()).toBeEnabled();
    });

    it('SLE-08: a new attempt clears the previous outcome while it runs, and the outcome follows a change of language', async () => {
        const second = deferred<{to: string; language: string}>();
        fake.sendLinkByEmail.mockRejectedValueOnce(axiosRefusal(429, {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 120}})).mockReturnValueOnce(second.promise);
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {email: GUEST}}});
        await fireEvent.click(button());
        await waitFor(() => expect(outcome()).toHaveTextContent(say('email.sendLink.errors.EMAIL_RATE_LIMITED', {minutes: 2})));

        translator.set(fake.translatorFor('it'));
        await waitFor(() => expect(outcome()).toHaveTextContent(say('email.sendLink.errors.EMAIL_RATE_LIMITED', {minutes: 2}, 'it')));

        await fireEvent.click(button());
        await waitFor(() => expect(root()).toHaveAttribute('data-busy', 'true'));
        expect(outcome(), 'the old outcome is gone while the new request runs').toBeNull();
        second.resolve({to: GUEST, language: 'it'});
        await waitFor(() => expect(outcome()).toHaveTextContent(say('email.sendLink.sent', {to: GUEST}, 'it')));
        expect(fake.notify.mock.calls.map(([event]) => event.name)).toEqual(['email.link.sendFailed', 'email.link.sent']);
    });

    it('SLE-09: an invitation to a typed address FastAPI refuses (its own 422, a list): the address is said to be invalid', async () => {
        fake.sendLinkByEmail.mockRejectedValueOnce(axiosRefusal(422, {detail: [{type: 'value_error', loc: ['body', 'to'], msg: 'value is not a valid email address', input: 'not-an-address'}]}));
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {}}});
        await fireEvent.input(field()!, {target: {value: 'not-an-address'}});

        await fireEvent.click(button());
        await waitFor(() => expect(outcome()).toHaveAttribute('data-outcome', 'failed'));

        expect(sentRequest()).toEqual({purpose: 'invite', token: TOKEN, to: 'not-an-address'});
        expect(outcome()).toHaveTextContent(say('email.sendLink.errors.EMAIL_RECIPIENT_INVALID'));
        expect(fake.notify).toHaveBeenCalledWith({name: 'email.link.sendFailed', detail: {purpose: 'invite', errorCode: 'EMAIL_RECIPIENT_INVALID'}});
        expect(field(), 'the address stays, to be corrected').toHaveValue('not-an-address');
    });
});
