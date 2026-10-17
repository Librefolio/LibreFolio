// @vitest-environment jsdom
/**
 * RegisterCard — component test (Vitest + jsdom).
 *
 * The sign-up form. Four fields, four client-side validators, and an error
 * ladder that turns whatever the server said into one message. It is mounted by
 * `routes/+page.svelte` with no props at all, and by `routes/invite/+page.svelte`
 * with an invitation (accounts lot A5b), so everything that decides its
 * behaviour is either typed into it, handed over by the invitation page, or
 * comes back from `POST /api/v1/auth/register` — all fully controllable from
 * here.
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
 *
 * The block before the last pins markup no user looks at and Chrome's password
 * manager reads (developer note, 30/09: Chrome offered saved credentials on the
 * login password field only, never on the username; `LoginCard.test.ts` tells
 * the story in full). Decision D2 aligns all three credential forms on one
 * contract: every field with an `id`, a `name`, the right `autocomplete` token
 * and a visually hidden `<label for>` reading its placeholder's key; the
 * username safe from autocapitalisation and spell-check; no empty `id`
 * anywhere. On a sign-up form it is what lets Chrome offer a generated password
 * on both password fields and save the new account under the username just
 * typed.
 *
 * The last block pins the designer's round 1 (workstream T, step T-2). The
 * header lost its subtitle, `auth.registerTitle` — the Register button already
 * says it — and the key left the four catalogues; with the identity translator a
 * rendered key is its own text, so the key appearing nowhere in the card is the
 * check, behind a barrier proving that this card does print keys. And each field
 * draws its icon inside it — User, Mail, and a Lock on both passwords — as
 * decoration, `aria-hidden`, the `<label for>` staying its only name.
 *
 * Accounts lot A5b (plan A5b.1) adds two things, each in a describe of its own.
 *   - The refusals A5a explains with a code, `{detail: {error_code, message}}`:
 *     the ladder moved to `describeRegistrationError` (`registrationErrors.ts`,
 *     pinned case by case in `registrationErrors.test.ts`), and here the card is
 *     held to drawing its answer — a key through the translator, a raw sentence
 *     as it came. The old string match on «registration is disabled» is gone with
 *     the sentence: A5a answers a closed instance with `REGISTRATION_DISABLED`.
 *   - The invitation: props `inviteToken` (`null` by default), `initialEmail`
 *     (`''`) and `grantsAdmin` (`false`). The address the invitation suggests
 *     fills the email field and stays editable (D-A16 rejected: a suggestion,
 *     not a constraint); `register-invite-notice` says the form is an
 *     invitation, `register-invite-admin-notice` that it makes an administrator;
 *     `invite_token` goes in the body only with an invitation — no key at all
 *     otherwise.
 *
 * Accounts lot A6c (decision 37) takes the password rules out of the card. The
 * backend writes them once, refuses a new password that breaks one with a 400
 * `{detail: {error_code: "PASSWORD_TOO_WEAK", message, rules}}`, and exposes
 * them in `GET /system/instance` (`accounts.password_rules`), where the meter,
 * `PasswordStrength`, reads them. The card keeps no copy any more: it binds the
 * meter's `valid`, as `ResetPasswordCard` does since A5b, and refuses to send
 * exactly when it is false. Its old copy hard-wired eight characters and ASCII
 * classes, so the cases of the A6c describe tell the two apart with rules only
 * the server could have given: twelve characters asked for (the copy let eleven
 * through), a rule set that asks only for length (the copy refused a passphrase),
 * an answer that lands after the password was typed, a code this build does not
 * know (never a reason to refuse: the server decides). The configuration is a
 * fake with the real store's shape — `reactiveBox` behind getters, as in
 * `LoginCard.test.ts` — and starts every test without `password_rules`, so every
 * other case runs on the defaults, the five rules of before. The server's
 * refusal is drawn like the other codes, through `describeRegistrationError`:
 * `auth.validation.passwordTooWeak`, never the server's sentence.
 *
 * Accounts lot A-21a: a new username may not hold `@`. The sign-in reads an
 * identifier holding one as an email address first, so the server refuses it
 * with a 400 `{detail: {error_code: "USERNAME_INVALID", message}}`, which
 * `describeRegistrationError` reads as `auth.validation.usernameNoAt` (pinned in
 * `registrationErrors.test.ts`). The card refuses it first, as it refuses a
 * username under three characters: `validateUsername` shows that key and
 * nothing reaches the server — for an address, and for `a@b`, three characters,
 * which only the `@` can refuse; on blur too. Red until A-21a. A guard keeps the
 * other characters a username of three or more may hold — a space, accents,
 * `.`, `_`, `-`, `+` — going out as typed. Not pinned: which key a username both
 * under three characters and holding `@` shows; the contract does not say.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {readable} from 'svelte/store';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

// The identity translator: components render i18n keys verbatim, so the tests
// can name the message that was chosen without naming any one language.
vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/api', () => ({zodiosApi: {register_api_v1_auth_register_post: vi.fn()}}));
// The instance configuration the meter reads its rules from (A6c): a fake with the real store's shape, enumerable
// getters over `$state` (`reactiveBox`), so an answer a test lands reaches the meter the way the server's does.
const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    /** What the store holds until the server answers (`DEFAULT_INSTANCE_CONFIG`), and what a backend older than A6c answers: no `password_rules`. */
    const BEFORE_ANSWER = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}} as InstanceConfig;
    return {
        BEFORE_ANSWER,
        instance: reactiveBox<{config: InstanceConfig; loaded: boolean}>({config: BEFORE_ANSWER, loaded: false}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
    };
});
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: mocks.BEFORE_ANSWER,
    instanceConfig: {
        get config() {
            return mocks.instance.config;
        },
        get loaded() {
            return mocks.instance.loaded;
        },
        get failed() {
            return false;
        },
        load: mocks.instanceLoad,
    },
}));

import RegisterCard from './RegisterCard.svelte';
import {zodiosApi} from '$lib/api';

const register = vi.mocked(zodiosApi.register_api_v1_auth_register_post);

/** Satisfies all five password rules: length, upper, lower, digit, special. */
const GOOD_PASSWORD = 'Str0ng!pass';

interface Mounted {
    gotoLogin: ReturnType<typeof vi.fn>;
}

/** The props an invitation hands over; a plain sign-up passes none. */
interface InviteProps {
    inviteToken?: string | null;
    initialEmail?: string;
    grantsAdmin?: boolean;
}

function mount(props: InviteProps = {}): Mounted {
    const gotoLogin = vi.fn();
    render(RegisterCard, {...props, $$events: {gotoLogin: (event: CustomEvent) => gotoLogin(event.detail)}} as never);
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

/** A structured refusal of A5a, with its status: `{detail: {error_code, message}}`, the message in English. */
function codedRefusal(status: number, error_code: string): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {
        isAxiosError: true,
        response: {status, data: {detail: {error_code, message: 'An English sentence the user must not read'}}},
    });
}

/** One entry of `accounts.password_rules`, as the server sends it (A6c). */
type RuleAnswer = {code: string; value?: number | null};
/** The five rules of before, as a server of A6c sends them: the defaults, in their order. */
const FIVE: RuleAnswer[] = [{code: 'min_length', value: 8}, {code: 'uppercase'}, {code: 'lowercase'}, {code: 'digit'}, {code: 'special'}];
/** The five, asking for `value` characters. */
const withMinLength = (value: number): RuleAnswer[] => [{code: 'min_length', value}, ...FIVE.slice(1)];

/** The server's answer lands: from now on the configuration carries these rules. */
function answer(password_rules: RuleAnswer[]): void {
    mocks.instance.config = {...mocks.BEFORE_ANSWER, accounts: {...mocks.BEFORE_ANSWER.accounts, password_rules}} as InstanceConfig;
    mocks.instance.loaded = true;
}

/** GOOD_PASSWORD and one more digit: twelve characters, all five classes. */
const TWELVE = 'Str0ng!pass1';
/** Twenty-eight characters of lower case and spaces: no capital, no digit, no symbol. */
const PASSPHRASE = 'correct horse battery staple';
/** What the card says of a password the rules refuse, its own check or the server's. */
const WEAK_KEY = 'auth.validation.passwordTooWeak';

/** The refusal of A6c: a 400 naming the codes of the rules the password missed, the message in English. */
function weakRefusal(rules: string[]): Error {
    return Object.assign(new Error('Request failed with status code 400'), {
        isAxiosError: true,
        response: {status: 400, data: {detail: {error_code: 'PASSWORD_TOO_WEAK', message: 'An English sentence the user must not read', rules}}},
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
    // Every test starts before the server's answer: no password_rules, so the meter checks the defaults.
    mocks.instance.config = mocks.BEFORE_ANSWER;
    mocks.instance.loaded = false;
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockResolvedValue(undefined);
});

afterEach(cleanup);

describe('RegisterCard — validation keeps bad credentials off the wire', () => {
    it.each([
        ['a username under three characters', {username: 'ab'}, 'auth.validation.usernameMinLength'],
        ['an address with no @', {email: 'alice.example.com'}, 'auth.validation.invalidEmail'],
        ['an address with no domain dot', {email: 'alice@example'}, 'auth.validation.invalidEmail'],
        ['an address with a space in it', {email: 'ali ce@example.com'}, 'auth.validation.invalidEmail'],
        // red until A-21a: the sign-in reads an identifier holding @ as an email address, so a new username may not hold one
        ['a username that is an address', {username: 'bob.smith@example.com'}, 'auth.validation.usernameNoAt'],
        // red until A-21a: three characters, enough for the length rule — only the @ can refuse it
        ['a three-character username holding an @', {username: 'a@b'}, 'auth.validation.usernameNoAt'],
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

    // guard (A-21a): only the @ is refused — a username of three or more characters without one goes out as typed
    it.each([
        ['a space', 'Bob Smith'],
        ['accents', 'Zoë Müller'],
        ['a dot', 'bob.smith'],
        ['an underscore', 'bob_smith'],
        ['a hyphen', 'bob-smith'],
        ['a plus', 'bob+lf'],
    ])('still sends a username holding %s and no @ (%j), as typed', async (_label, name) => {
        mount();
        await fillValid({username: name});
        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(register).toHaveBeenCalledWith(expect.objectContaining({username: name}));
        expect(screen.queryByText('auth.validation.usernameNoAt')).not.toBeInTheDocument();
    });
});

describe('RegisterCard — validation on blur', () => {
    it('flags a field as soon as the user leaves it', async () => {
        mount();
        await fill('register-username', 'ab');
        await fireEvent.blur(screen.getByTestId('register-username'));

        expect(screen.getByText('auth.validation.usernameMinLength')).toBeInTheDocument();
    });

    // red until A-21a
    it('flags a username holding an @ as soon as the user leaves it, and clears the flag once the @ is gone', async () => {
        mount();
        await fill('register-username', 'bob.smith@example.com');
        await fireEvent.blur(screen.getByTestId('register-username'));

        expect(screen.getByText('auth.validation.usernameNoAt')).toBeInTheDocument();

        await fill('register-username', 'bob.smith');
        await fireEvent.blur(screen.getByTestId('register-username'));

        expect(screen.queryByText('auth.validation.usernameNoAt')).not.toBeInTheDocument();
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

describe('RegisterCard — joining by invitation (A5b)', () => {
    const INVITE = 'inv-token-0123';

    it('starts the email field on the address the invitation suggests, and leaves it editable', async () => {
        mount({inviteToken: INVITE, initialEmail: 'eve@example.com'});
        const email = screen.getByTestId('register-email');

        expect(email).toHaveValue('eve@example.com');
        // A suggestion, not a constraint (D-A16 rejected): the user may register another address.
        expect(email).toBeEnabled();
        expect(email).not.toHaveAttribute('readonly');

        await fillValid({email: 'eve.private@example.com'});
        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(register.mock.calls[0][0]).toMatchObject({email: 'eve.private@example.com'});
    });

    it('sends the suggested address when the user keeps it', async () => {
        mount({inviteToken: INVITE, initialEmail: 'eve@example.com'});
        await fill('register-username', 'eve');
        await fill('register-password', GOOD_PASSWORD);
        await fill('register-confirm-password', GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(register.mock.calls[0][0]).toMatchObject({email: 'eve@example.com'});
    });

    it('starts the email field empty when nothing is suggested', () => {
        mount();

        expect(screen.getByTestId('register-email')).toHaveValue('');
    });

    it('says the form is an invitation', () => {
        mount({inviteToken: INVITE});

        expect(screen.getByTestId('register-invite-notice')).toHaveTextContent('auth.invite.notice');
        expect(screen.queryByTestId('register-invite-admin-notice'), 'an ordinary invitation makes an ordinary account').toBeNull();
    });

    it('says, too, that the invitation makes an administrator', () => {
        mount({inviteToken: INVITE, grantsAdmin: true});

        expect(screen.getByTestId('register-invite-notice')).toBeInTheDocument();
        expect(screen.getByTestId('register-invite-admin-notice')).toHaveTextContent('auth.invite.adminNotice');
    });

    it('says nothing about invitations on a plain sign-up', () => {
        mount();

        expect(screen.getByTestId('register-form'), 'premise: the form is drawn').toBeInTheDocument();
        expect(screen.queryByTestId('register-invite-notice')).toBeNull();
        expect(screen.queryByTestId('register-invite-admin-notice')).toBeNull();
    });

    it('sends the invitation token with the three credentials', async () => {
        mount({inviteToken: INVITE, initialEmail: 'eve@example.com'});
        await fillValid({username: 'eve', email: 'eve@example.com'});

        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(register.mock.calls[0][0]).toStrictEqual({username: 'eve', email: 'eve@example.com', password: GOOD_PASSWORD, invite_token: INVITE});
    });

    it('sends no invite_token key at all without an invitation', async () => {
        // Not `invite_token: null` nor `undefined`: a plain sign-up keeps the body it always had.
        mount();
        await fillValid();

        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(Object.keys(register.mock.calls[0][0] as object).sort()).toEqual(['email', 'password', 'username']);
    });

    it('hands the user back to the login card with something to say, as a plain sign-up does', async () => {
        const {gotoLogin} = mount({inviteToken: INVITE, initialEmail: 'eve@example.com'});
        await fillValid({email: 'eve@example.com'});

        await submit();

        await waitFor(() => expect(gotoLogin).toHaveBeenCalledTimes(1));
        expect(gotoLogin).toHaveBeenCalledWith({message: 'auth.accountCreated'});
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

    it('still shows a sentence it has no translation for, rather than swallowing it', async () => {
        // Anything the two branches do not claim: the server's own words are
        // the best available answer, and silence would be the worst.
        const detail = 'Something the frontend has never heard of';
        expect(await submitAndRead(detail)).toBe(detail);
    });
});

describe('RegisterCard — refusals the server explains with a code (A5a, drawn since A5b)', () => {
    /** Submits valid credentials against a server that refuses with `failure`; returns the banner's text. */
    async function submitAndRead(failure: Error, props: InviteProps = {}): Promise<string> {
        register.mockRejectedValue(failure);
        mount(props);
        await fillValid();
        await submit();

        await waitFor(() => expect(banner()).not.toBeNull());
        return banner()!.textContent?.trim() ?? '';
    }

    it.each([
        // A closed instance: until A5b the card read only string details, and
        // this object fell through to the generic failure.
        [403, 'REGISTRATION_DISABLED', 'auth.registrationDisabled'],
        [403, 'INVITE_REQUIRED', 'auth.registrationInviteOnly'],
        [409, 'USER_LIMIT_REACHED', 'auth.userLimitReached'],
    ])('draws a %i %s as %s, never the server sentence', async (status, code, key) => {
        expect(await submitAndRead(codedRefusal(status, code))).toBe(key);
    });

    it('draws an invitation the server no longer accepts as an unknown link', async () => {
        expect(await submitAndRead(codedRefusal(400, 'INVITE_INVALID'), {inviteToken: 'spent-invite'})).toBe('auth.link.unknown');
    });

    it('unlocks the form after a coded refusal, so the user can retry', async () => {
        await submitAndRead(codedRefusal(403, 'INVITE_REQUIRED'));

        expect(screen.getByTestId('register-submit')).toBeEnabled();
        expect(screen.getByTestId('register-username')).toHaveValue('alice');
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

describe("RegisterCard — the password rules are the server's, read through the meter (A6c)", () => {
    it("refuses to send a password the server's rules refuse, though it meets the five of before: min_length 12", async () => {
        answer(withMinLength(12));
        mount();
        await fillValid(); // GOOD_PASSWORD: eleven characters, all five classes — what the old copy let through

        await submit();

        expect(register).not.toHaveBeenCalled();
        expect(screen.getByText(WEAK_KEY)).toBeInTheDocument();
        // The meter under the field says which rule: one set of rules decides both.
        expect(screen.getByTestId('password-rule-minLength')).toHaveAttribute('data-passed', 'false');
    });

    it('sends a password of the length the server asks for', async () => {
        // The barrier of the case above: the same rules, twelve characters, and the card sends.
        answer(withMinLength(12));
        mount();
        await fillValid({password: TWELVE});

        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(register).toHaveBeenCalledWith(expect.objectContaining({password: TWELVE}));
    });

    it("sends a password the server's rules accept though the old copy refused it: a rule set that asks only for length", async () => {
        answer([{code: 'min_length', value: 16}]);
        mount();
        await fillValid({password: PASSPHRASE});

        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(register).toHaveBeenCalledWith(expect.objectContaining({password: PASSPHRASE}));
        expect(screen.queryByText(WEAK_KEY)).toBeNull();
    });

    it('follows an answer that lands after the password was typed, both ways, without a remount', async () => {
        mount();
        await fillValid(); // eleven characters: enough for the defaults
        answer(withMinLength(12));
        await tick();

        await submit();

        expect(register, 'the answer asks for twelve').not.toHaveBeenCalled();
        expect(screen.getByText(WEAK_KEY)).toBeInTheDocument();

        // A later answer asks for eight again: the same password goes through.
        answer(FIVE);
        await tick();
        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
        expect(register).toHaveBeenCalledWith(expect.objectContaining({password: GOOD_PASSWORD}));
    });

    it('never refuses for a rule code it does not know: the server checks it', async () => {
        answer([{code: 'no_dictionary_word'}, ...FIVE, {code: 'not_in_this_build', value: 3}]);
        mount();
        await fillValid();

        await submit();

        await waitFor(() => expect(register).toHaveBeenCalledTimes(1));
    });

    it("draws the server's PASSWORD_TOO_WEAK as auth.validation.passwordTooWeak, never its sentence, and lets the user retry", async () => {
        // The meter let the password through and the server did not: its rules changed after the page had read them.
        register.mockRejectedValue(weakRefusal(['min_length']));
        mount();
        await fillValid();

        await submit();

        await waitFor(() => expect(banner()).not.toBeNull());
        const shown = banner()!.textContent ?? '';
        expect(shown).toContain(WEAK_KEY);
        expect(shown, "never the server's English").not.toContain('An English sentence the user must not read');
        expect(screen.getByTestId('register-submit')).toBeEnabled();
        expect(screen.getByTestId('register-password')).toBeEnabled();
    });
});

describe("RegisterCard — the markup Chrome's password manager reads", () => {
    // Decision D2 (30/09). The label key of each field is the key its
    // placeholder already shows, so sighted users see no change at all.
    const FIELDS = [
        {testId: 'register-username', id: 'register-username', name: 'username', autocomplete: 'username', type: 'text', key: 'auth.username'},
        {testId: 'register-email', id: 'register-email', name: 'email', autocomplete: 'email', type: 'email', key: 'auth.email'},
        {testId: 'register-password', id: 'register-password', name: 'new-password', autocomplete: 'new-password', type: 'password', key: 'auth.password'},
        {testId: 'register-confirm-password', id: 'register-confirm-password', name: 'confirm-password', autocomplete: 'new-password', type: 'password', key: 'auth.confirmPassword'},
    ];

    /** Mounts the card and returns the element everything it rendered lives in. */
    function mountCard(): HTMLElement {
        return render(RegisterCard).container;
    }

    function input(testId: string): HTMLInputElement {
        return screen.getByTestId(testId) as HTMLInputElement;
    }

    /**
     * The named attributes of one element as a single object, `null` where
     * absent, so a red shows every mismatch in one diff instead of the first.
     */
    function attributes(el: Element, names: readonly string[]): Record<string, string | null> {
        return Object.fromEntries(names.map((name) => [name, el.getAttribute(name)]));
    }

    /** Tag and test id of an element: enough for a red to say which one it means. */
    function describeElement(el: Element): string {
        const testId = el.getAttribute('data-testid');
        return testId ? `${el.tagName.toLowerCase()}[data-testid="${testId}"]` : el.tagName.toLowerCase();
    }

    it.each(FIELDS)('names $testId by id, name and autocomplete', ({testId, id, name, autocomplete, type}) => {
        mountCard();

        expect(attributes(input(testId), ['id', 'name', 'autocomplete', 'type'])).toEqual({id, name, autocomplete, type});
    });

    it.each(FIELDS)('labels $testId with the key its placeholder shows', ({testId, key}) => {
        mountCard();
        const field = input(testId);

        expect(screen.getByLabelText(key)).toBe(field);
        // A `<label for>`, specifically: an `aria-label` would satisfy the query
        // above and give the password manager no label element to read.
        expect(field.labels).toHaveLength(1);
        const label = field.labels![0];
        expect(label).toHaveAttribute('for', field.id);
        expect(field).toHaveAttribute('placeholder', key);
        expect(label.textContent?.trim()).toBe(key);
        // Hidden from sight, not from assistive technology.
        expect(label).not.toHaveAttribute('hidden');
        expect(label).not.toHaveAttribute('aria-hidden', 'true');
    });

    it('keeps a phone keyboard from capitalising or correcting the username', () => {
        mountCard();

        expect(attributes(input('register-username'), ['autocapitalize', 'spellcheck'])).toEqual({autocapitalize: 'none', spellcheck: 'false'});
    });

    it('leaves no element with an empty id', () => {
        // Both `PasswordInput`s printed `id=""`: invalid HTML, and a target no
        // label can point at.
        const root = mountCard();

        expect(Array.from(root.querySelectorAll('[id=""]'), describeElement)).toEqual([]);
    });

    it('gives every id in the card to one element only', () => {
        // A guard for the ids the fix introduces: two password fields built from
        // one component are exactly where a copied id would slip in.
        const root = mountCard();
        const ids = Array.from(root.querySelectorAll('[id]'), (el) => el.id).filter((id) => id !== '');

        expect([...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))]).toEqual([]);
    });

    it('keeps the four fields in the one registration form', () => {
        // Chrome reads a sign-up as one `<form>`: the username and both new
        // passwords must share it. A guard, not a change.
        mountCard();
        const form = screen.getByTestId('register-form');

        for (const {testId} of FIELDS) expect(input(testId).form, testId).toBe(form);
    });
});

describe('RegisterCard — the header without a subtitle, and the field icons', () => {
    it('renders the key auth.registerTitle nowhere: the subtitle is gone', () => {
        const root = render(RegisterCard).container;

        // The barrier: this card prints its keys as text — the Register button
        // reads its own — so a key that appears nowhere was not rendered.
        expect(screen.getByTestId('register-submit').textContent?.trim()).toBe('auth.register');
        // Text and attributes alike: a title or an aria-label would count too.
        expect(root.innerHTML).not.toContain('auth.registerTitle');
    });

    it.each([
        {icon: 'register-username-icon', input: 'register-username'},
        {icon: 'register-email-icon', input: 'register-email'},
        {icon: 'register-password-icon', input: 'register-password'},
        {icon: 'register-confirm-password-icon', input: 'register-confirm-password'},
    ])('draws $icon inside $input, hidden from assistive technology', ({icon, input}) => {
        render(RegisterCard);
        const svg = screen.getByTestId(icon);

        expect(svg.tagName.toLowerCase()).toBe('svg');
        expect(svg).toHaveAttribute('aria-hidden', 'true');
        // Inside the field: the positioned wrapper its input sits in.
        expect(svg.parentElement).toBe(screen.getByTestId(input).parentElement);
    });
});
