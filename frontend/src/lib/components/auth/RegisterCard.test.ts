// @vitest-environment jsdom
/**
 * RegisterCard — component test (Vitest + jsdom).
 *
 * The sign-up form. Four fields, four client-side validators, and a `catch`
 * block that turns whatever the server said into one of eight messages. It is
 * mounted by `routes/+page.svelte` with no props at all, so everything that
 * decides its behaviour is either typed into it or comes back from
 * `POST /api/v1/auth/register` — both fully controllable from here.
 *
 * Two things make this a component test rather than an E2E:
 *   - the error ladder needs eight *different* server responses, and six of them
 *     (pydantic `loc`/`msg` shapes) are hard to provoke against a real backend;
 *   - the thing worth asserting on success is the `gotoLogin` event, which never
 *     appears on screen.
 *
 * On not asserting translated text. Every message in this component comes from
 * `$_()`, and the app ships in EN/IT/FR/ES. `$lib/i18n` is therefore mocked with
 * an identity translator, so `$_('auth.validation.usernameTaken')` renders as
 * the literal key. Every assertion below reads a *key*, which is stable in all
 * four languages, never a sentence — with one deliberate exception, marked where
 * it occurs, where the component echoes a raw server string that is not a key at
 * all. That exception is the defect this file documents.
 *
 * `createEventDispatcher` is Svelte 4 API kept alive by Svelte 5's legacy layer:
 * `$on()` is gone, and the listener arrives through the `$$events` prop instead.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

// The identity translator: components render i18n keys verbatim, so the tests
// can name the message that was chosen without naming any one language.
vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/api', () => ({zodiosApi: {register_api_v1_auth_register_post: vi.fn()}}));

import RegisterCard from './RegisterCard.svelte';
import {zodiosApi} from '$lib/api';

const register = vi.mocked(zodiosApi.register_api_v1_auth_register_post);

/** Satisfies all five password rules: length, upper, lower, digit, special. */
const GOOD_PASSWORD = 'Str0ng!pass';

interface Mounted {
    gotoLogin: ReturnType<typeof vi.fn>;
}

function mount(): Mounted {
    const gotoLogin = vi.fn();
    render(RegisterCard, {$$events: {gotoLogin: (event: CustomEvent) => gotoLogin(event.detail)}} as never);
    return {gotoLogin};
}

async function fill(testId: string, value: string): Promise<void> {
    await fireEvent.input(screen.getByTestId(testId), {target: {value}});
}

/** Types a set of credentials that passes every client-side validator. */
async function fillValid(overrides: Partial<Record<'username' | 'email' | 'password' | 'confirm', string>> = {}): Promise<void> {
    await fill('register-username', overrides.username ?? 'alice');
    await fill('register-email', overrides.email ?? 'alice@example.com');
    await fill('register-password', overrides.password ?? GOOD_PASSWORD);
    await fill('register-confirm-password', overrides.confirm ?? overrides.password ?? GOOD_PASSWORD);
}

async function submit(): Promise<void> {
    await fireEvent.submit(screen.getByTestId('register-form'));
}

/** The general error banner, or null while there is nothing to report. */
function banner(): HTMLElement | null {
    return screen.queryByTestId('info-banner-error');
}

/** An axios-shaped rejection carrying `response.data.detail`. */
function serverError(detail: unknown): Error {
    return Object.assign(new Error('Request failed with status code 400'), {
        isAxiosError: true,
        response: {data: {detail}},
    });
}

/** A promise this test resolves by hand, so "in flight" is a state we control. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

beforeEach(() => {
    register.mockReset();
    register.mockResolvedValue({} as never);
});

afterEach(cleanup);

describe('RegisterCard — validation keeps bad credentials off the wire', () => {
    it.each([
        ['a username under three characters', {username: 'ab'}, 'auth.validation.usernameMinLength'],
        ['an address with no @', {email: 'alice.example.com'}, 'auth.validation.invalidEmail'],
        ['an address with no domain dot', {email: 'alice@example'}, 'auth.validation.invalidEmail'],
        ['an address with a space in it', {email: 'ali ce@example.com'}, 'auth.validation.invalidEmail'],
    ])('refuses to send %s', async (_label, overrides, key) => {
        mount();
        await fillValid(overrides);
        await submit();

        expect(register).not.toHaveBeenCalled();
        expect(screen.getByText(key)).toBeInTheDocument();
    });

    it.each([
        ['too short', 'Sh0rt!'],
        ['no uppercase', 'str0ng!pass'],
        ['no lowercase', 'STR0NG!PASS'],
        ['no digit', 'Strong!pass'],
        ['no special character', 'Str0ngpass'],
    ])('refuses a password with %s', async (_label, password) => {
        mount();
        await fillValid({password});
        await submit();

        expect(register).not.toHaveBeenCalled();
        expect(screen.getByText('auth.validation.passwordTooWeak')).toBeInTheDocument();
    });

    it('refuses to send when the confirmation does not match', async () => {
        mount();
        await fillValid({confirm: `${GOOD_PASSWORD}x`});
        await submit();

        expect(register).not.toHaveBeenCalled();
        expect(screen.getByText('auth.validation.passwordsNoMatch')).toBeInTheDocument();
    });

    it('reports every broken field at once, not just the first', async () => {
        // An empty form: the user should not have to fix and resubmit four times
        // to discover four problems.
        mount();
        await fill('register-confirm-password', 'mismatch');
        await submit();

        expect(register).not.toHaveBeenCalled();
        expect(screen.getByText('auth.validation.usernameMinLength')).toBeInTheDocument();
        expect(screen.getByText('auth.validation.invalidEmail')).toBeInTheDocument();
        expect(screen.getByText('auth.validation.passwordTooWeak')).toBeInTheDocument();
        expect(screen.getByText('auth.validation.passwordsNoMatch')).toBeInTheDocument();
    });

    it('accepts a three-character username, the shortest allowed', async () => {
        mount();
        await fillValid({username: 'abc'});
        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(screen.queryByText('auth.validation.usernameMinLength')).not.toBeInTheDocument();
    });
});

describe('RegisterCard — validation on blur', () => {
    it('flags a field as soon as the user leaves it', async () => {
        mount();
        await fill('register-username', 'ab');
        await fireEvent.blur(screen.getByTestId('register-username'));

        expect(screen.getByText('auth.validation.usernameMinLength')).toBeInTheDocument();
    });

    it('clears the flag once the field is corrected', async () => {
        mount();
        await fill('register-email', 'nope');
        await fireEvent.blur(screen.getByTestId('register-email'));
        expect(screen.getByText('auth.validation.invalidEmail')).toBeInTheDocument();

        await fill('register-email', 'alice@example.com');
        await fireEvent.blur(screen.getByTestId('register-email'));

        expect(screen.queryByText('auth.validation.invalidEmail')).not.toBeInTheDocument();
    });

    it('re-checks the confirmation against the password it is compared with', async () => {
        mount();
        await fill('register-password', GOOD_PASSWORD);
        await fill('register-confirm-password', 'different');
        await fireEvent.blur(screen.getByTestId('register-confirm-password'));
        expect(screen.getByText('auth.validation.passwordsNoMatch')).toBeInTheDocument();

        await fill('register-confirm-password', GOOD_PASSWORD);
        await fireEvent.blur(screen.getByTestId('register-confirm-password'));

        expect(screen.queryByText('auth.validation.passwordsNoMatch')).not.toBeInTheDocument();
    });
});

describe('RegisterCard — what reaches the server', () => {
    it('sends exactly the three credentials the endpoint takes', async () => {
        mount();
        await fillValid();
        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(register).toHaveBeenCalledWith({username: 'alice', email: 'alice@example.com', password: GOOD_PASSWORD});
    });

    it('strips the spaces a phone keyboard adds to the username and address', async () => {
        mount();
        await fillValid({username: '  alice  ', email: ' alice@example.com '});
        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(register).toHaveBeenCalledWith(expect.objectContaining({username: 'alice', email: 'alice@example.com'}));
    });

    it('leaves the password exactly as typed, spaces included', async () => {
        // Trimming a password would silently lock the user out of the account
        // they think they just created.
        const spaced = ` ${GOOD_PASSWORD} `;
        mount();
        await fillValid({password: spaced});
        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(register).toHaveBeenCalledWith(expect.objectContaining({password: spaced}));
    });

    it('shows the trimmed username back to the user', async () => {
        mount();
        await fillValid({username: '  alice  '});
        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(screen.getByTestId('register-username')).toHaveValue('alice');
    });
});

describe('RegisterCard — after a successful registration', () => {
    it('hands the user back to the login card with something to say', async () => {
        const {gotoLogin} = mount();
        await fillValid();
        await submit();

        await waitFor(() => expect(gotoLogin).toHaveBeenCalledTimes(1));
        expect(gotoLogin).toHaveBeenCalledWith({message: 'auth.accountCreated'});
    });

    it('leaves no error behind', async () => {
        mount();
        await fillValid();
        await submit();

        await waitFor(() => expect(register).toHaveBeenCalled());
        expect(banner()).toBeNull();
    });
});

describe('RegisterCard — the login link', () => {
    it('goes back with no message when the user never registered', async () => {
        const {gotoLogin} = mount();
        await fireEvent.click(screen.getByTestId('goto-login'));

        expect(gotoLogin).toHaveBeenCalledWith({});
    });
});

describe('RegisterCard — field-level errors reported by the server', () => {
    async function submitAndRead(detail: unknown): Promise<string> {
        register.mockRejectedValue(serverError(detail));
        mount();
        await fillValid();
        await submit();

        await waitFor(() => expect(banner()).not.toBeNull());
        return banner()!.textContent?.trim() ?? '';
    }

    it.each([
        ['a special-use domain', 'value is not a valid email address: special-use domain', 'auth.validation.invalidEmailDomain'],
        ['a reserved domain', 'the domain name is reserved', 'auth.validation.invalidEmailDomain'],
        ['any other address complaint', 'value is not a valid email address', 'auth.validation.invalidEmail'],
    ])('explains %s rejected by the schema', async (_label, msg, key) => {
        expect(await submitAndRead([{loc: ['body', 'email'], msg, type: 'value_error'}])).toBe(key);
    });

    it.each([
        ['username', ['body', 'username'], 'auth.validation.usernameMinLength'],
        ['password', ['body', 'password'], 'auth.validation.passwordTooWeak'],
    ])('maps a schema complaint about %s back onto that field', async (_label, loc, key) => {
        expect(await submitAndRead([{loc, msg: 'too short', type: 'value_error'}])).toBe(key);
    });

    it('falls back to a general failure for a field it cannot place', async () => {
        expect(await submitAndRead([{loc: ['body', 'timezone'], msg: 'unknown', type: 'value_error'}])).toBe('auth.registrationFailed');
    });

    it('falls back to a general failure when the schema list arrives empty', async () => {
        expect(await submitAndRead([])).toBe('auth.registrationFailed');
    });

    it('falls back to a general failure when an entry carries no location', async () => {
        expect(await submitAndRead([{msg: 'something', type: 'value_error'}])).toBe('auth.registrationFailed');
    });
});

describe('RegisterCard — plain-text errors reported by the server', () => {
    async function submitAndRead(detail: unknown): Promise<string> {
        register.mockRejectedValue(serverError(detail));
        mount();
        await fillValid();
        await submit();

        await waitFor(() => expect(banner()).not.toBeNull());
        return banner()!.textContent?.trim() ?? '';
    }

    it.each([
        ['a lowercase username clash', 'that username is taken', 'auth.validation.usernameTaken'],
        ['a lowercase email clash', 'that email is taken', 'auth.validation.emailTaken'],
    ])('translates %s', async (_label, detail, key) => {
        expect(await submitAndRead(detail)).toBe(key);
    });

    it.each([
        // The exact sentences this backend returns — `user_service.py:139` and
        // `:144`. They are capitalised, and the match used to be case-sensitive,
        // so no branch fired and the raw English fell through to the banner:
        // eight translated strings, four languages by two keys, that nobody
        // could ever read. Asserted on the real wording rather than a lowercase
        // stand-in, because a stand-in is exactly what hid this.
        ['Username already taken', 'auth.validation.usernameTaken'],
        ['Email already registered', 'auth.validation.emailTaken'],
    ])('translates the server sentence %s', async (detail, key) => {
        expect(await submitAndRead(detail)).toBe(key);
    });

    it('translates the administrator having closed sign-ups', async () => {
        // `auth.py:191`. Unlike the other two it says nothing about what the
        // user typed, so it has wording of its own rather than the generic
        // failure — and, until this key existed, an Italian user read English.
        expect(await submitAndRead('New user registration is disabled')).toBe('auth.registrationDisabled');
    });

    it('still shows a sentence it has no translation for, rather than swallowing it', async () => {
        // Anything the three branches do not claim: the server's own words are
        // the best available answer, and silence would be the worst.
        const detail = 'Something the frontend has never heard of';
        expect(await submitAndRead(detail)).toBe(detail);
    });
});

describe('RegisterCard — errors with nothing usable in them', () => {
    it.each([
        ['the request never reached the server', new Error('Network Error')],
        ['the response carried no body', Object.assign(new Error('Timeout'), {isAxiosError: true})],
        ['the body carried no detail', serverError(undefined)],
        ['the detail was a bare object', serverError({code: 'weird'})],
    ])('reports a general failure when %s', async (_label, rejection) => {
        register.mockRejectedValue(rejection);
        mount();
        await fillValid();
        await submit();

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(within(banner()!).getByText('auth.registrationFailed')).toBeInTheDocument();
    });
});

describe('RegisterCard — while the request is in flight', () => {
    it('locks every field and the button', async () => {
        const pending = deferred<never>();
        register.mockReturnValue(pending.promise as never);
        mount();
        await fillValid();
        await submit();

        await waitFor(() => expect(screen.getByTestId('register-submit')).toBeDisabled());
        expect(screen.getByTestId('register-username')).toBeDisabled();
        expect(screen.getByTestId('register-email')).toBeDisabled();
        expect(screen.getByTestId('register-password')).toBeDisabled();
        expect(screen.getByTestId('register-confirm-password')).toBeDisabled();

        pending.resolve(undefined as never);
    });

    it('says it is working rather than inviting another click', async () => {
        const pending = deferred<never>();
        register.mockReturnValue(pending.promise as never);
        mount();
        await fillValid();
        await submit();

        await waitFor(() => expect(screen.getByTestId('register-submit')).toHaveTextContent('common.loading'));

        pending.resolve(undefined as never);
        await waitFor(() => expect(screen.getByTestId('register-submit')).toHaveTextContent('auth.register'));
    });

    it('unlocks the form again after a rejection, so the user can retry', async () => {
        register.mockRejectedValue(serverError('Username already taken'));
        mount();
        await fillValid();
        await submit();

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(screen.getByTestId('register-submit')).toBeEnabled();
        expect(screen.getByTestId('register-username')).toBeEnabled();
    });

    it('starts a second request if a second submit event reaches it: the handler has no guard of its own', async () => {
        // Characterisation, not an endorsement — and narrower than it first looks.
        //
        // `handleSubmit` has no `if (loading) return;`. Everything that stops a
        // double registration today lives in the markup: `disabled={loading}` on
        // the one submit button. That is currently enough for both user paths —
        // the click is refused, and implicit submission (Enter in a text field)
        // is suppressed by the same attribute, because a disabled default button
        // has no activation behaviour, so the browser fires nothing. The other
        // two buttons inside the form are both `type="button"`, so neither the
        // banner's dismiss nor the show-password eye submits it.
        //
        // What this test records is that the protection is single-layered. Drive
        // the form's submit event directly — as `form.requestSubmit()`, a second
        // submit control, or dropping `disabled` in a restyle all would — and two
        // registrations leave the browser.
        const pending = deferred<never>();
        register.mockReturnValue(pending.promise as never);
        mount();
        await fillValid();
        await submit();
        await waitFor(() => expect(screen.getByTestId('register-submit')).toBeDisabled());

        await submit();

        expect(register).toHaveBeenCalledTimes(2);
        pending.resolve(undefined as never);
    });
});

describe('RegisterCard — clearing an error', () => {
    it('lets the user dismiss the banner without retyping anything', async () => {
        register.mockRejectedValue(serverError([{loc: ['body', 'email'], msg: 'bad', type: 'value_error'}]));
        mount();
        await fillValid();
        await submit();
        await waitFor(() => expect(banner()).not.toBeNull());

        await fireEvent.click(within(banner()!).getByRole('button', {name: 'Dismiss'}));

        await waitFor(() => expect(banner()).toBeNull());
        expect(screen.getByTestId('register-email')).toHaveValue('alice@example.com');
    });

    it('drops the previous error when a new attempt begins', async () => {
        register.mockRejectedValueOnce(serverError('Username already taken'));
        mount();
        await fillValid();
        await submit();
        await waitFor(() => expect(banner()).not.toBeNull());

        await submit();

        await waitFor(() => expect(banner()).toBeNull());
    });
});
