// @vitest-environment jsdom
/**
 * SendLinkByEmail — «send by email» next to a shared link (workstream E, lot E4a; the language of the email, lot E-8),
 * tested standalone; its registration in A's share dialogs (`LINK_SHARE_ACTIONS`, lot E4b) is tested in
 * `linkShareRegistration.test.ts`.
 *
 * The contract under test:
 *   - an invitation (`data-purpose="invite"`) shows the address field (`send-link-email-to`), labelled and prefilled with
 *     the address the dialog knows (`context.email`, empty without one) and editable; a reset link shows no field, only
 *     `email.sendLink.resetTarget`: it goes to its account's address alone. Both say where the link starts
 *     (`email.sendLink.publicUrlHint`);
 *   - an invitation also chooses the language of its email (lot E-8, decision N69): `send-link-email-language`, the
 *     app's `SimpleSelect`, under a visible label `email.sendLink.languageLabel` that is also its `ariaLabel`. Its
 *     options, in order: the instance's language (`email.sendLink.languageInstance`, `…-option-instance`), chosen by
 *     default, then `LANGUAGE_OPTIONS` — `en`, `it`, `fr`, `es` — each by its native name (`LOCALE_NAMES`) with its
 *     flag as icon (`…-option-<code>`); its own texts follow a change of language. A reset link has no such select:
 *     its email goes in the account's language;
 *   - the button (`send-link-email-button`) sends the token of the link — `tokenFromLink` — once: an invitation with the
 *     address trimmed, or with none when the field is empty or blank; a reset link never with an address, whatever the
 *     dialog knows. Without a token the button is disabled and sends nothing. An invitation left on (or brought back
 *     to) the instance's language goes with no `language` key at all — the backend decides —, one in a language
 *     chosen with `language: '<code>'`; a reset link never with a language;
 *   - while it runs: `data-busy`/`aria-busy`, the field, the language select and the button disabled, the button
 *     `email.sendLink.sending`, no outcome, and a second click sends nothing;
 *   - sent: the outcome `sent` names the address and the language the server ANSWERED — `email.sendLink.sent {to,
 *     language}`, the language by the native name of the answered code, or as the code itself when the UI does not
 *     know it, even when it is not the one chosen —, publishes that code in `data-language`, is drawn with
 *     `OUTCOME_CLASSES.sent`, and the event `email.link.sent` carries the purpose and that code; refused: the outcome
 *     `failed`, worded by `linkSendFailureMessage($_, readLinkSendFailure(error))` — the SMTP reason for a refused
 *     delivery —, drawn with `OUTCOME_CLASSES.failed`, and the event `email.link.sendFailed` with the purpose and the
 *     failure; the button usable again either way. A typed address FastAPI refuses on its own (a 422 whose `detail` is
 *     a list) is said to be an invalid address, and stays in the field to be corrected;
 *   - a new attempt clears the previous outcome; the outcome follows a change of language.
 *
 * Mocks, all owned here: `./sendLinkApi`'s `sendLinkByEmail` is a fake the test answers (deferred where the request in
 * flight is the subject) — `tokenFromLink` and `readLinkSendFailure` stay the real ones, and a refusal is built as the
 * client raises it, axios's own `AxiosError`; `$lib/features/instance/instanceConfig.svelte` a still fake (the
 * component never reads it); `$lib/stores/app/notify.svelte` a spy; `$lib/i18n`: the real module — its
 * `LANGUAGE_OPTIONS`, `LOCALE_NAMES` and `LOCALE_FLAGS` —, with `_` a writable translator answering
 * `[<language>] <key> {<values>}`. The select is the real `SimpleSelect`, driven as a user does: its trigger opens the
 * list, a click on an option chooses it.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Writable} from 'svelte/store';
import {AxiosError, AxiosHeaders, type AxiosResponse, type InternalAxiosRequestConfig} from 'axios';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import type {LinkPurpose} from '$lib/features/auth/linkToken';

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
vi.mock('$lib/i18n', async (importOriginal) => {
    const {writable} = await import('svelte/store');
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: writable(fake.translatorFor('en'))};
});

import SendLinkByEmail from './SendLinkByEmail.svelte';
import {_, LANGUAGE_OPTIONS, LOCALE_FLAGS} from '$lib/i18n';
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
const languageSelect = () => screen.queryByTestId('send-link-email-language');
const languageTrigger = () => screen.getByTestId('send-link-email-language-button');
const languageList = () => screen.queryByTestId('send-link-email-language-dropdown');

/** The languages the select offers after the instance's, in order, each by its native name (decision N69). */
const LANGUAGES = [
    {code: 'en', name: 'English'},
    {code: 'it', name: 'Italiano'},
    {code: 'fr', name: 'Français'},
    {code: 'es', name: 'Español'},
] as const;

async function idle(): Promise<void> {
    await waitFor(() => expect(root()).toHaveAttribute('data-busy', 'false'));
}

/** The request the fake received: what the component asked to send. */
function sentRequest(): Record<string, unknown> {
    expect(fake.sendLinkByEmail).toHaveBeenCalledTimes(1);
    return fake.sendLinkByEmail.mock.calls[0][0];
}

/** What an element shows, its white space collapsed: an option with an icon is drawn as the icon, a space, the label. */
function shown(element: Element): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** The select's accessible name, as `SimpleSelect` composes it: its `ariaLabel`, then the label of the option chosen. */
function languageName(chosen: string, language = 'en'): string {
    return `${say('email.sendLink.languageLabel', undefined, language)}, ${chosen}`;
}

/** Open the language select as a user does, with a click on its trigger; returns its list. */
async function openLanguageList(): Promise<HTMLElement> {
    await fireEvent.click(languageTrigger());
    const list = languageList();
    expect(list, 'the trigger opens the list').not.toBeNull();
    return list!;
}

/** Choose an option of the language select — `instance`, or a language code — as a user does; ends on the list closed. */
async function chooseLanguage(option: string): Promise<void> {
    const list = await openLanguageList();
    await fireEvent.click(within(list).getByTestId(`send-link-email-language-option-${option}`));
    expect(languageList(), 'a choice closes the list').toBeNull();
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

    it('SLE-06: busy while it runs — the field and the button disabled, no outcome, a second click sends nothing; then sent, naming the address and the language the server answered, and the event', async () => {
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
        expect(outcome()).toHaveTextContent(say('email.sendLink.sent', {to: 'zq-written-in-the-invitation@example.com', language: 'Français'}));
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
        await waitFor(() => expect(outcome()).toHaveTextContent(say('email.sendLink.sent', {to: GUEST, language: 'Italiano'}, 'it')));
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

describe('SendLinkByEmail — the language of the email (lot E-8, decision N69)', () => {
    it('SLE-10: an invitation — the select under a visible label that is also its accessible name; the instance’s language first and chosen, then the four languages by native name with their flag', async () => {
        expect(
            LANGUAGE_OPTIONS.map(({code, name, flag}) => ({code, name, flag})),
            'premise: the app’s languages, in this order, by native name, with their flag',
        ).toEqual(LANGUAGES.map(({code, name}) => ({code, name, flag: LOCALE_FLAGS[code]})));
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {email: GUEST}}});

        const label = screen.getByText(say('email.sendLink.languageLabel'));
        expect(root()).toContainElement(label);
        expect(languageSelect(), 'the label is a visible text of its own, not a part of the select').not.toContainElement(label);
        expect(languageTrigger(), 'named by the label, then by the language chosen: the instance’s').toHaveAttribute('aria-label', languageName(say('email.sendLink.languageInstance')));
        expect(languageTrigger(), 'the instance’s language by default').toHaveTextContent(say('email.sendLink.languageInstance'));
        expect(languageTrigger()).toBeEnabled();

        const list = await openLanguageList();
        expect(list, 'the list is named by the label too').toHaveAttribute('aria-label', say('email.sendLink.languageLabel'));
        const options = within(list).getAllByRole('option');
        expect(options.map((option) => option.getAttribute('data-testid'))).toEqual(['send-link-email-language-option-instance', ...LANGUAGES.map(({code}) => `send-link-email-language-option-${code}`)]);
        expect(options[0]).toHaveTextContent(say('email.sendLink.languageInstance'));
        expect(options.slice(1).map(shown), 'each language by its native name, its flag as icon').toEqual(LANGUAGES.map(({code, name}) => `${LOCALE_FLAGS[code]} ${name}`));
        expect(
            options.map((option) => option.getAttribute('aria-selected')),
            'the instance’s language is the one chosen',
        ).toEqual(['true', 'false', 'false', 'false', 'false']);
    });

    it('SLE-11: a reset link — no language to choose, no label: its email goes in the account’s language, sent with no language at all', async () => {
        render(SendLinkByEmail, {props: {link: RESET_LINK, purpose: 'password_reset', context: {email: 'zq-alice@example.com', username: 'zq_alice'}}});

        expect(screen.getByTestId('send-link-email-target'), 'premise: the reset link’s own line is drawn').toBeInTheDocument();
        expect(languageSelect()).toBeNull();
        expect(screen.queryByTestId('send-link-email-language-button')).toBeNull();
        expect(screen.queryByText(say('email.sendLink.languageLabel'))).toBeNull();
        await fireEvent.click(button());
        await idle();

        expect(sentRequest()).toEqual({purpose: 'password_reset', token: TOKEN, to: undefined});
        expect(sentRequest(), 'no language key, not even an undefined one').not.toHaveProperty('language');
    });

    it('SLE-12: an invitation left on the instance’s language — sent with no language key at all: the backend decides', async () => {
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {email: GUEST}}});
        expect(languageTrigger(), 'premise: the select is there, on its default').toHaveTextContent(say('email.sendLink.languageInstance'));

        await fireEvent.click(button());
        await idle();

        expect(sentRequest()).toEqual({purpose: 'invite', token: TOKEN, to: GUEST});
        expect(sentRequest(), 'no language key, not even an empty or undefined one').not.toHaveProperty('language');
    });

    it.each(LANGUAGES)('SLE-13: $name chosen — the trigger shows it with its flag and is named by it; sent with language: $code', async ({code, name}) => {
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {email: GUEST}}});

        await chooseLanguage(code);
        expect(shown(languageTrigger())).toBe(`${LOCALE_FLAGS[code]} ${name}`);
        expect(languageTrigger(), 'the label of the option is the native name alone: the flag is its icon').toHaveAttribute('aria-label', languageName(name));
        await fireEvent.click(button());
        await idle();

        expect(sentRequest()).toStrictEqual({purpose: 'invite', token: TOKEN, to: GUEST, language: code});
    });

    it('SLE-14: a language chosen, then the instance’s language again — sent with no language key, as if none had been chosen', async () => {
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {email: GUEST}}});

        await chooseLanguage('fr');
        await chooseLanguage('instance');
        expect(languageTrigger()).toHaveAttribute('aria-label', languageName(say('email.sendLink.languageInstance')));
        await fireEvent.click(button());
        await idle();

        expect(sentRequest()).toEqual({purpose: 'invite', token: TOKEN, to: GUEST});
        expect(sentRequest(), 'no language key, not even an empty one').not.toHaveProperty('language');
    });

    it('SLE-15: while it runs the select is disabled, like the address field, and does not open; usable again once answered', async () => {
        const request = deferred<{to: string; language: string}>();
        fake.sendLinkByEmail.mockReturnValueOnce(request.promise);
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {email: GUEST}}});
        await chooseLanguage('es');

        await fireEvent.click(button());
        await waitFor(() => expect(root()).toHaveAttribute('data-busy', 'true'));
        expect(field()).toBeDisabled();
        expect(languageTrigger()).toBeDisabled();
        await fireEvent.click(languageTrigger());
        expect(languageList(), 'a disabled select does not open').toBeNull();

        request.resolve({to: GUEST, language: 'es'});
        await idle();

        expect(languageTrigger()).toBeEnabled();
        expect(field()).toBeEnabled();
    });

    it.each<{label: string; purpose: LinkPurpose; choose: string | null; answered: string; named: string}>([
        {label: 'an invitation on the instance’s language, written in English', purpose: 'invite', choose: null, answered: 'en', named: 'English'},
        {label: 'an invitation in Italiano, written in Italiano', purpose: 'invite', choose: 'it', answered: 'it', named: 'Italiano'},
        {label: 'an invitation in Italiano the server wrote in Français: the answer, not the choice', purpose: 'invite', choose: 'it', answered: 'fr', named: 'Français'},
        {label: 'an invitation written in a language the UI does not know: its code, as is', purpose: 'invite', choose: null, answered: 'de', named: 'de'},
        {label: 'a reset link, written in its account’s Español', purpose: 'password_reset', choose: null, answered: 'es', named: 'Español'},
    ])('SLE-16: $label — the outcome names it and publishes its code in data-language; the event carries the code', async ({purpose, choose, answered, named}) => {
        fake.sendLinkByEmail.mockResolvedValueOnce({to: GUEST, language: answered});
        render(SendLinkByEmail, {props: {link: purpose === 'invite' ? INVITE_LINK : RESET_LINK, purpose, context: {email: GUEST}}});
        if (choose !== null) await chooseLanguage(choose);

        await fireEvent.click(button());
        await idle();

        expect(sentRequest().language, 'premise: the request carried the choice, if any').toBe(choose ?? undefined);
        expect(outcome()).toHaveAttribute('data-outcome', 'sent');
        expect(outcome()).toHaveAttribute('data-language', answered);
        expect(outcome()).toHaveTextContent(say('email.sendLink.sent', {to: GUEST, language: named}));
        expect(fake.notify).toHaveBeenCalledTimes(1);
        expect(fake.notify).toHaveBeenCalledWith({name: 'email.link.sent', detail: {purpose, language: answered}});
    });

    it('SLE-17: its label, its accessible name and the instance’s option follow a change of language; the languages keep their native names', async () => {
        render(SendLinkByEmail, {props: {link: INVITE_LINK, purpose: 'invite', context: {email: GUEST}}});
        expect(screen.getByText(say('email.sendLink.languageLabel')), 'premise: drawn in English first').toBeInTheDocument();

        translator.set(fake.translatorFor('it'));

        await waitFor(() => expect(screen.getByText(say('email.sendLink.languageLabel', undefined, 'it'))).toBeInTheDocument());
        expect(languageTrigger()).toHaveAttribute('aria-label', languageName(say('email.sendLink.languageInstance', undefined, 'it'), 'it'));
        expect(languageTrigger()).toHaveTextContent(say('email.sendLink.languageInstance', undefined, 'it'));
        const options = within(await openLanguageList()).getAllByRole('option');
        expect(options[0]).toHaveTextContent(say('email.sendLink.languageInstance', undefined, 'it'));
        expect(options.slice(1).map(shown), 'a language is named in its own language, whatever the interface’s').toEqual(LANGUAGES.map(({code, name}) => `${LOCALE_FLAGS[code]} ${name}`));
    });
});
