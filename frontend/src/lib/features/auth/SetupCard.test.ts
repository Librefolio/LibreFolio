// @vitest-environment jsdom
/**
 * SetupCard — the form the setup link of the initial administrator opens (accounts lot A7b, F02).
 *
 * On a hosted instance (F02) the first administrator is created without a password, and its holder receives a
 * one-time link, `/setup#token=…` (A7a: `./dev.py user setup-link`; the token in the fragment, out of the server's
 * logs). The `/setup` page checks the token (`POST /auth/tokens/inspect`, purpose `admin_setup`) and, for a valid one,
 * shows this card: the account it sets up, a password, its confirmation. The card spends the link with
 * `POST /api/v1/auth/setup {token, new_password}`, which answers like the login — the session cookie and an
 * `AuthLoginResponse` — so once it succeeds the administrator is signed in; the page then reads the session and enters
 * the app (`src/routes/setup/page.test.ts`).
 *
 * The contract (plan A7b, C2, approved 2026-10-16), in the shape of `ResetPasswordCard`:
 *   - props `token`, `username` (the account the link sets up, `null` when the server named none), `ondone`,
 *     `oninvalid`;
 *   - test ids: the root `setup-card` (the AuthCard), the form `setup-form`, the account line `setup-account` showing
 *     the username, the two `PasswordInput`s `setup-new` and `setup-confirm` (the input carries the test id),
 *     `setup-submit`, the error area `setup-error`, and `setup-blocked`, the message of a blocked instance;
 *   - the rules are the server's, read from `PasswordStrength` through its bindable `valid` (decision 37): a password
 *     that breaks one is refused with `auth.validation.passwordTooWeak`, a confirmation that differs with
 *     `auth.validation.passwordsNoMatch`, and neither is sent;
 *   - otherwise `{token, new_password}` goes to `setup_admin_api_v1_auth_setup_post`, the password exactly as typed, and
 *     the submit is disabled while the request is in flight;
 *   - resolved → `ondone()`; 400 `TOKEN_INVALID` (used, expired, revoked, unknown, or its account already active) →
 *     `oninvalid()`; 400 `PASSWORD_TOO_WEAK` or 422 → `auth.validation.passwordTooWeak`; 401 → the instance is
 *     blocked (decision P16 d: `tokens/inspect` still answers on a blocked instance, so the form opens, and the setup
 *     is refused with the 401 of a caller without a session): `setup-blocked` says `auth.setup.blocked`, the submit is
 *     no longer offered (gone, or disabled), and nothing is handed back to the page; anything else →
 *     `auth.setup.failed`.
 *   - follow-up decided by the coordinator (2026-10-16, 21:10): H's refusal of a blocked instance, the 423 a browser
 *     holding a session gets (`isInstanceBlockedError` in `features/instance/instanceBlock.svelte.ts`: status 423 and
 *     `detail.code === 'instance_blocked'`), is drawn exactly like the 401. A 423 without that code, or that code
 *     under another status, stays «anything else».
 *
 * Beyond the C2 list, mirrored from `ResetPasswordCard` (decision D2, the describe «the markup a password manager
 * reads»): the administrator chooses a password here, so the browser should file it under the right account — the
 * same hidden read-only username field, and `autocomplete="new-password"` on both password fields.
 *
 * On not asserting translated text. `$lib/i18n` keeps its real exports with the translator replaced by the identity,
 * so a message renders as its key: every message is asserted by key, stable in EN/IT/FR/ES. The translator also
 * writes out the values of an interpolated message after the key, so the username shows whether the card puts it
 * beside its label or inside it (`{values: {username}}`). The username is a value this test passes in.
 *
 * The instance configuration is a fake with the real store's shape (`reactiveBox` behind getters, as in
 * `ResetPasswordCard.test.ts`), without `password_rules` at the start of every test: every case runs on the built-in
 * rules but those of the describe «the rules are the server's», which land an answer of the server.
 *
 * No timers: every wait is a `waitFor` on a state, every negative assertion follows a positive barrier.
 *
 * Written red-first, before `SetupCard.svelte` exists: every case fails on the import until it does.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    /** What the store holds until the server answers (`DEFAULT_INSTANCE_CONFIG`): no `password_rules`. */
    const BEFORE_ANSWER = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}} as InstanceConfig;
    return {
        setup: vi.fn().mockName('zodiosApi.setup_admin_api_v1_auth_setup_post'),
        BEFORE_ANSWER,
        instance: reactiveBox<{config: InstanceConfig; loaded: boolean}>({config: BEFORE_ANSWER, loaded: false}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
    };
});

vi.mock('$lib/api', () => ({zodiosApi: {setup_admin_api_v1_auth_setup_post: mocks.setup}}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    // The identity: a message renders as its key, with the values of an interpolated one written out after it.
    const identity = readable((key: string, options?: {values?: Record<string, unknown>}) => (options?.values ? `${key} ${Object.values(options.values).join(' ')}` : key));
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: identity, t: identity};
});
// The instance configuration the meter reads its rules from (decision 37): a fake with the real store's shape,
// enumerable getters over `$state` (`reactiveBox`), so an answer a test lands reaches the meter the way the server's does.
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

import SetupCard from './SetupCard.svelte';

/** Satisfies all five built-in rules: length, upper, lower, digit, special. Eleven characters. */
const GOOD_PASSWORD = 'Str0ng!pass';
const TOKEN = 'setup-token-0123';
/** The account the link sets up: a value no message key contains. */
const USERNAME = 'carla.rossi';

const WEAK_KEY = 'auth.validation.passwordTooWeak';
const NO_MATCH_KEY = 'auth.validation.passwordsNoMatch';
const FAILED_KEY = 'auth.setup.failed';
const BLOCKED_KEY = 'auth.setup.blocked';

/** H's refusal on a blocked instance (`backend/app/api/v1/instance_block.py`), the `detail` of its 423. */
const INSTANCE_BLOCKED_DETAIL = {code: 'instance_blocked', message: 'This instance is blocked by its hosting provider'};

/** What `POST /auth/setup` answers on success: the login's answer, the session cookie riding with it. */
const SIGNED_IN = {
    user: {id: 1, username: USERNAME, email: 'carla@example.com', is_active: true, is_superuser: true, created_at: '2026-10-16T18:00:00Z'},
    user_settings: null,
    message: 'Setup complete',
    show_donation_popup: false,
};

interface Mounted {
    ondone: ReturnType<typeof vi.fn>;
    oninvalid: ReturnType<typeof vi.fn>;
}

function mount(props: {username?: string | null} = {}): Mounted {
    const ondone = vi.fn().mockName('ondone');
    const oninvalid = vi.fn().mockName('oninvalid');
    render(SetupCard, {props: {token: TOKEN, username: USERNAME, ondone, oninvalid, ...props}});
    return {ondone, oninvalid};
}

async function fill(testId: string, value: string): Promise<void> {
    await fireEvent.input(screen.getByTestId(testId), {target: {value}});
}

/** Types a password and its confirmation (the same, unless told otherwise). */
async function fillPasswords(password: string, confirmation = password): Promise<void> {
    await fill('setup-new', password);
    await fill('setup-confirm', confirmation);
}

async function submit(): Promise<void> {
    await fireEvent.click(screen.getByTestId('setup-submit'));
}

/**
 * What the error area says, `''` when it says nothing: absent, or present and empty — the card may keep the area
 * mounted, so "no error" is read from its text, never from its presence.
 */
function errorShown(): string {
    return screen.queryByTestId('setup-error')?.textContent?.trim() ?? '';
}

/** What the message of a blocked instance says, `''` when the card draws none. */
function blockedShown(): string {
    return screen.queryByTestId('setup-blocked')?.textContent?.trim() ?? '';
}

/** Whether the card offers a submit the user can press: drawn, and enabled. */
function submitOffered(): boolean {
    const button = screen.queryByTestId('setup-submit') as HTMLButtonElement | null;
    return button !== null && !button.disabled;
}

/** An axios-shaped refusal carrying `response.status` and `response.data.detail`. */
function refusal(status: number, detail: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {
        isAxiosError: true,
        response: {status, data: {detail}},
    });
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

/** One entry of `accounts.password_rules`, as the server sends it (decision 37). */
type RuleAnswer = {code: string; value?: number | null};
/** The five built-in rules, as the server sends them: the defaults, in their order. */
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

beforeEach(() => {
    // The refusals below assert that nothing was sent; they would pass vacuously where effects (the meter's
    // `bind:valid`) never run.
    assertEffectsRun();
    mocks.setup.mockReset();
    mocks.setup.mockResolvedValue(SIGNED_IN);
    // Every test starts before the server's answer: no password_rules, so the meter checks the defaults.
    mocks.instance.config = mocks.BEFORE_ANSWER;
    mocks.instance.loaded = false;
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockResolvedValue(undefined);
});

afterEach(cleanup);

describe('SetupCard — the form', () => {
    // red until A7b
    it('is one card, setup-card, whose form setup-form holds the two password fields and the submit', () => {
        mount();
        const form = within(screen.getByTestId('setup-card')).getByTestId('setup-form');

        expect(form.tagName, 'a form: Enter in a field submits it, and a password manager reads it').toBe('FORM');
        expect(within(form).getByTestId('setup-new')).toHaveAttribute('type', 'password');
        expect(within(form).getByTestId('setup-confirm')).toHaveAttribute('type', 'password');
        expect(within(form).getByTestId('setup-submit')).toBeEnabled();
    });

    // red until A7b
    it('says which account the link sets up', () => {
        mount({username: USERNAME});

        expect(within(screen.getByTestId('setup-card')).getByTestId('setup-account')).toHaveTextContent(USERNAME);
    });

    // red until A7b
    it('names no account when the server named none', () => {
        mount({username: null});

        expect(screen.getByTestId('setup-form'), 'premise: the card is drawn').toBeInTheDocument();
        expect(screen.queryByTestId('setup-account')).toBeNull();
    });

    // red until A7b
    it('shows the strength meter of the app under the password', async () => {
        mount();

        await fill('setup-new', 'abc');

        expect(within(screen.getByTestId('setup-card')).getByTestId('password-strength-meter')).toBeInTheDocument();
    });

    // red until A7b
    it('shows no error and no blocked instance before anything was tried, and offers the submit', () => {
        mount();

        expect(screen.getByTestId('setup-form'), 'premise: the card is drawn').toBeInTheDocument();
        expect(errorShown()).toBe('');
        expect(blockedShown()).toBe('');
        expect(submitOffered()).toBe(true);
    });
});

describe('SetupCard — the rules keep a bad password off the wire', () => {
    // red until A7b
    it.each([
        ['too short', 'Sh0rt!'],
        ['no uppercase', 'str0ng!pass'],
        ['no lowercase', 'STR0NG!PASS'],
        ['no digit', 'Strong!pass'],
        ['no special character', 'Str0ngpass'],
    ])('refuses a password with %s, with auth.validation.passwordTooWeak', async (_label, password) => {
        const {ondone, oninvalid} = mount();
        await fillPasswords(password);

        await submit();

        await waitFor(() => expect(errorShown(), 'a refusal the user can read, in setup-error').toContain(WEAK_KEY));
        expect(mocks.setup).not.toHaveBeenCalled();
        expect(ondone).not.toHaveBeenCalled();
        expect(oninvalid).not.toHaveBeenCalled();
    });

    // red until A7b
    it('refuses an empty form, with auth.validation.passwordTooWeak', async () => {
        mount();

        await submit();

        await waitFor(() => expect(errorShown()).toContain(WEAK_KEY));
        expect(mocks.setup).not.toHaveBeenCalled();
    });

    // red until A7b
    it('refuses when the confirmation differs, with auth.validation.passwordsNoMatch', async () => {
        const {ondone} = mount();
        await fillPasswords(GOOD_PASSWORD, `${GOOD_PASSWORD}x`);

        await submit();

        await waitFor(() => expect(errorShown()).toContain(NO_MATCH_KEY));
        expect(errorShown(), 'the password itself meets the rules').not.toContain(WEAK_KEY);
        expect(mocks.setup).not.toHaveBeenCalled();
        expect(ondone).not.toHaveBeenCalled();
    });
});

describe('SetupCard — what reaches the server', () => {
    // red until A7b
    it('sends the token of the link and the password, nothing else', async () => {
        mount();
        await fillPasswords(GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(mocks.setup).toHaveBeenCalledTimes(1));
        expect(mocks.setup.mock.calls[0][0]).toStrictEqual({token: TOKEN, new_password: GOOD_PASSWORD});
    });

    // red until A7b
    it('sends the password exactly as typed, spaces included', async () => {
        // Trimming it would lock the administrator out with a password nobody chose.
        const spaced = ` ${GOOD_PASSWORD} `;
        mount();
        await fillPasswords(spaced);

        await submit();

        await waitFor(() => expect(mocks.setup).toHaveBeenCalledTimes(1));
        expect(mocks.setup.mock.calls[0][0]).toMatchObject({new_password: spaced});
    });

    // red until A7b
    it('disables the submit while the server answers, so a second press sends nothing, and enables it again after a failure', async () => {
        const inFlight = deferred<unknown>();
        mocks.setup.mockReturnValue(inFlight.promise);
        const {ondone} = mount();
        await fillPasswords(GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(screen.getByTestId('setup-submit'), 'the request is in flight').toBeDisabled());
        await submit();
        expect(mocks.setup, 'a single request: the link is spent once').toHaveBeenCalledTimes(1);

        inFlight.reject(refusal(500, 'Internal Server Error'));

        await waitFor(() => expect(errorShown()).toContain(FAILED_KEY));
        await waitFor(() => expect(screen.getByTestId('setup-submit'), 'the user can try again').toBeEnabled());
        expect(ondone).not.toHaveBeenCalled();
    });
});

describe('SetupCard — after the server answers', () => {
    // red until A7b
    it('hands back to the page once the administrator is set up and signed in', async () => {
        const {ondone, oninvalid} = mount();
        await fillPasswords(GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(ondone).toHaveBeenCalledTimes(1));
        expect(oninvalid).not.toHaveBeenCalled();
        expect(errorShown()).toBe('');
        expect(blockedShown()).toBe('');
    });

    // red until A7b
    it('tells the page the link is no longer valid on a 400 TOKEN_INVALID', async () => {
        mocks.setup.mockRejectedValue(refusal(400, {error_code: 'TOKEN_INVALID', message: 'This setup link is not valid'}));
        const {ondone, oninvalid} = mount();
        await fillPasswords(GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(oninvalid).toHaveBeenCalledTimes(1));
        expect(ondone).not.toHaveBeenCalled();
        expect(blockedShown(), 'a dead link is not a blocked instance').toBe('');
    });

    // red until A7b
    it.each([
        ['a 422: the schema refused the password', refusal(422, [{type: 'string_too_short', loc: ['body', 'new_password'], msg: 'String should have at least 1 character'}]), WEAK_KEY],
        // The server's rules refused it: they changed after the page read them. Never the English `message`.
        ["a 400 PASSWORD_TOO_WEAK: the server's rules refused the password", refusal(400, {error_code: 'PASSWORD_TOO_WEAK', message: 'An English sentence the user must not read', rules: ['min_length']}), WEAK_KEY],
        ['a 400 with another code', refusal(400, {error_code: 'SOMETHING_ELSE', message: 'An English sentence'}), FAILED_KEY],
        ['a 500', refusal(500, 'Internal Server Error'), FAILED_KEY],
        ['a request that never reached the server', new Error('Network Error'), FAILED_KEY],
        // A 423 is a blocked instance only with H's code (`isInstanceBlockedError`): any other 423 is a plain failure.
        ['a 423 with another code', refusal(423, {code: 'locked', message: 'An English sentence'}), FAILED_KEY],
        ['a 423 with no detail', refusal(423, undefined), FAILED_KEY],
        // And the code alone is not enough: the status must be 423.
        ['a 403 carrying the code of a blocked instance', refusal(403, {code: 'instance_blocked', message: 'An English sentence'}), FAILED_KEY],
    ])('shows %s as %s, and stays on the form', async (_label, failure, key) => {
        mocks.setup.mockRejectedValue(failure);
        const {ondone, oninvalid} = mount();
        await fillPasswords(GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(errorShown()).toContain(key));
        expect(errorShown(), "a key, never the server's English").not.toContain('An English sentence');
        expect(blockedShown(), 'only a 401, or a 423 instance_blocked, means a blocked instance').toBe('');
        expect(ondone).not.toHaveBeenCalled();
        expect(oninvalid, 'only TOKEN_INVALID means the link is gone').not.toHaveBeenCalled();
        expect(screen.getByTestId('setup-new'), 'the form stays, so the user can try again').toBeInTheDocument();
        await waitFor(() => expect(submitOffered(), 'and the submit with it').toBe(true));
    });
});

describe('SetupCard — a blocked instance (decision P16 d): the 401, or the 423 instance_blocked', () => {
    // red until A7b — both rows: the 401 of the first round, and the 423 the coordinator added (21:10)
    it.each([
        // `tokens/inspect` answers on a blocked instance, so the form opened; the setup is refused with the 401 that
        // the instance block gives a caller without a session (`instance_block.py`).
        ['a 401: the refusal of a caller without a session', refusal(401, 'Not authenticated')],
        // The same block, met by a browser that holds a session (another account signed in on it): H answers 423.
        ["a 423 instance_blocked: H's refusal of a caller with a session", refusal(423, INSTANCE_BLOCKED_DETAIL)],
    ])('on %s, says the instance is blocked, in setup-blocked, and offers the submit no more', async (_label, failure) => {
        mocks.setup.mockRejectedValue(failure);
        const {ondone, oninvalid} = mount();
        await fillPasswords(GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(blockedShown(), 'the message of a blocked instance, in setup-blocked').toContain(BLOCKED_KEY));
        expect(within(screen.getByTestId('setup-card')).getByTestId('setup-blocked'), 'inside the card').toBeInTheDocument();
        expect(submitOffered(), 'nothing to retry: every setup is refused until the provider lifts the block').toBe(false);
        expect(mocks.setup).toHaveBeenCalledTimes(1);
        expect(ondone, 'nobody is signed in').not.toHaveBeenCalled();
        expect(oninvalid, 'the link is not the problem').not.toHaveBeenCalled();
        expect(errorShown(), 'not drawn as the generic failure').not.toContain(FAILED_KEY);
        expect(errorShown(), 'nor as a weak password').not.toContain(WEAK_KEY);
        const cardText = screen.getByTestId('setup-card').textContent ?? '';
        expect(cardText, "a key, never the server's English (A-13: not the raw «Not authenticated»)").not.toContain('Not authenticated');
        expect(cardText, "a key, never the server's English").not.toContain(INSTANCE_BLOCKED_DETAIL.message);
    });
});

describe("SetupCard — the rules are the server's, read through the meter (decision 37)", () => {
    // red until A7b
    it("refuses a password the server's rules refuse, though it meets the built-in ones: min_length 12", async () => {
        answer(withMinLength(12));
        const {ondone, oninvalid} = mount();
        await fillPasswords(GOOD_PASSWORD); // eleven characters, all five classes

        await submit();

        await waitFor(() => expect(errorShown(), 'a refusal the user can read, in setup-error').toContain(WEAK_KEY));
        expect(mocks.setup).not.toHaveBeenCalled();
        expect(ondone).not.toHaveBeenCalled();
        expect(oninvalid).not.toHaveBeenCalled();
        // The meter under the field says which rule: one set of rules decides both.
        expect(screen.getByTestId('password-rule-minLength')).toHaveAttribute('data-passed', 'false');
    });

    // red until A7b
    it('sends a password of the length the server asks for', async () => {
        // The barrier of the case above: the same rules, twelve characters, and the card sends.
        answer(withMinLength(12));
        mount();
        await fillPasswords(TWELVE);

        await submit();

        await waitFor(() => expect(mocks.setup).toHaveBeenCalledTimes(1));
        expect(mocks.setup.mock.calls[0][0]).toStrictEqual({token: TOKEN, new_password: TWELVE});
    });

    // red until A7b
    it("sends a password the server's rules accept though the built-in ones refuse it: a rule set that asks only for length", async () => {
        answer([{code: 'min_length', value: 16}]);
        mount();
        await fillPasswords(PASSPHRASE);

        await submit();

        await waitFor(() => expect(mocks.setup).toHaveBeenCalledTimes(1));
        expect(mocks.setup.mock.calls[0][0]).toStrictEqual({token: TOKEN, new_password: PASSPHRASE});
        expect(errorShown()).toBe('');
    });

    // red until A7b
    it('follows an answer that lands after the password was typed, without a remount', async () => {
        mount();
        await fillPasswords(GOOD_PASSWORD); // eleven characters: enough for the defaults
        answer(withMinLength(12));
        await tick();

        await submit();

        await waitFor(() => expect(errorShown(), 'the answer asks for twelve').toContain(WEAK_KEY));
        expect(mocks.setup).not.toHaveBeenCalled();
    });
});

describe('SetupCard — the markup a password manager reads (decision D2, as ResetPasswordCard)', () => {
    // The administrator chooses the password of the account here: a password manager files it under the username of
    // the same form, so the card carries the account in a field of its own, hidden and read-only, beside the two new
    // passwords. Without an account there is nothing to file it under, and no such field.

    /** The card's form. */
    function theForm(): HTMLFormElement {
        return screen.getByTestId('setup-form') as HTMLFormElement;
    }

    /** Every field of the card that declares itself a username. */
    function usernameFields(): HTMLInputElement[] {
        return Array.from(screen.getByTestId('setup-card').querySelectorAll<HTMLInputElement>('input[autocomplete="username"]'));
    }

    /** The named attributes of one element as a single object, `null` where absent, so a red shows every mismatch. */
    function attributes(el: Element, names: readonly string[]): Record<string, string | null> {
        return Object.fromEntries(names.map((name) => [name, el.getAttribute(name)]));
    }

    // red until A7b
    it('hides a read-only username field carrying the account, in the form of the new passwords', () => {
        mount({username: USERNAME});
        const fields = usernameFields();

        expect(fields, 'fields with autocomplete="username" in the card').toHaveLength(1);
        const [field] = fields;
        expect(attributes(field, ['type', 'name', 'autocomplete'])).toEqual({type: 'text', name: 'username', autocomplete: 'username'});
        expect(field).toHaveValue(USERNAME);
        expect(field).toHaveAttribute('hidden');
        expect(field).not.toBeVisible();
        expect(field).toHaveAttribute('readonly');
        expect(field.form, 'the form of the new passwords').toBe(theForm());
    });

    // red until A7b
    it('has no username field when the server named no account', () => {
        mount({username: null});

        expect(theForm(), 'premise: the form and its password fields are drawn').toBeInTheDocument();
        expect(usernameFields()).toEqual([]);
    });

    // red until A7b
    it.each(['setup-new', 'setup-confirm'])('marks %s as a new password: type password, autocomplete="new-password", in the form', (testId) => {
        mount();
        const field = screen.getByTestId(testId) as HTMLInputElement;

        expect(attributes(field, ['type', 'autocomplete'])).toEqual({type: 'password', autocomplete: 'new-password'});
        expect(field.form).toBe(theForm());
    });
});
