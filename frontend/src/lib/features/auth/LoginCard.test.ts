// @vitest-environment jsdom
/**
 * LoginCard — component test (Vitest + jsdom).
 *
 * The sign-in form: a username field, a `PasswordInput`, the submit button and
 * two links. This file pins the part of it that no user looks at and one
 * program reads: the markup Chrome's password manager parses to decide which
 * saved account goes into which field.
 *
 * The symptom (developer note, 30/09). Chrome offered the saved username and
 * password only when the password field was clicked, never on the username
 * field. The password manager classifies a form from each field's
 * `autocomplete` token together with its `name`, its `id` and its label. Here
 * the username field carried the token and nothing else — no `id`, no `name`,
 * no `<label>`, only a placeholder — and `PasswordInput` printed an empty
 * `id=""`, which is not a valid id and names nothing. The password field could
 * still be recognised by `type="password"`; the username field was left with
 * almost nothing to be recognised by.
 *
 * Decision D2 (30/09) aligns all three credential forms — this one,
 * `RegisterCard` and `PasswordChangeModal` — on one contract:
 *   - every field has a stable `id`, a `name` and the right `autocomplete` token;
 *   - every field has a visually hidden `<label for>` reading the same i18n key
 *     as its placeholder, which also gives a screen reader a name that does not
 *     vanish with the first keystroke;
 *   - a field that holds a username asks the keyboard not to capitalise or
 *     spell-check it (`autocapitalize="none"`, `spellcheck="false"`);
 *   - no element carries an empty `id`, and no id is carried twice;
 *   - the `data-testid`s stay exactly as they are: every E2E login goes through
 *     them, and every selector below is one of them.
 *
 * Why a component test. The contract is markup — props in, attributes out —
 * and the autofill itself belongs to Chrome, which nothing here can drive: the
 * developer checks it by hand on his own browser. What Chrome is *given* to
 * parse can be pinned in milliseconds, with no backend.
 *
 * What it deliberately does not assert: that the labels are *visually* hidden.
 * That is Tailwind's `sr-only`, a CSS class, and jsdom loads no stylesheet, so
 * the assertion would be either on a class name or on nothing. What is asserted
 * is the half a parser and a screen reader depend on: the label exists, points
 * at its field with `for`, and is not taken out of the accessibility tree.
 *
 * On not asserting translated text. `$lib/i18n` is mocked with an identity
 * translator, so `$_('auth.usernameOrEmail')` renders as that literal key; the
 * label assertions name keys, stable in EN/IT/FR/ES, never a sentence. The
 * sign-in error cases at the bottom swap it for a translator that marks what
 * it translated: the identity cannot tell a key that went through `$_` from one
 * printed as it is.
 *
 * The second describe ties «Register here» to the registration mode of the
 * instance (accounts lot A5b; it was K, step 22, on the bool setting
 * `enable_registration`, which A5a replaced). An instance is `open` (anyone),
 * `invite` (an invitation link) or `disabled` (nobody), and only an open one has
 * a use for the link: elsewhere the backend refuses `POST /auth/register`
 * without an invitation, and the refusal came only after a filled-in form. The
 * contract: on mount the card asks `instanceConfig.load()` once (the public
 * `GET /system/instance`, the shared request of the page load) and no longer
 * `globalSettings.load()`; it draws the register block — the `auth.noAccount`
 * text and `goto-register` — exactly while
 * `instanceConfig.config.accounts.registration_mode` is `open`. Until the
 * server answers the store holds `DEFAULT_INSTANCE_CONFIG`, whose mode is
 * `open`, so the link is there; it goes as soon as an answer says otherwise,
 * without a remount. The store is a fake with the real one's shape — enumerable
 * getters over `$state` (`reactiveBox`) and a `load` spy — open before every
 * test, so every other test mounts the card as on an open instance. The global
 * settings are still mocked, with the old «closed» value in them: the card must
 * not read them any more.
 *
 * Accounts lot A6d (decision 36) adds one flag to that contract. A new install
 * now defaults to `invite`, and the first account of an empty instance can
 * always be created — it becomes the administrator — so `GET /system/instance`
 * answers `accounts.first_account_open`, true exactly while the instance has no
 * account at all. The card offers the link while the mode is `open` OR that flag
 * is true. Before the server answers nothing changes: the defaults carry no flag
 * and their mode is `open`, so the link is there. The flag is optional in the
 * schema — absent reads as false — and reaches the generated `InstanceConfig`
 * only with the `api sync` that follows the backend: `AccountsAnswer` types it
 * here, so the file compiles before that sync and after it. The A6d cases say
 * the flag, true or false; the A5b cases above them still leave it out.
 *
 * The third describe gives the success message a handle (A5b): `login-success`,
 * the box the login page fills from a registration or from the flash a link
 * page left (`authFlash.ts`). Its text is a prop this file passes in.
 *
 * The last describe pins the field icons of the designer's round 1 (workstream
 * T, step T-2): a User beside the username and a Lock beside the password, drawn
 * inside each field. They are decoration — `aria-hidden`, so the `<label for>`
 * stays each field's only name, as the label tests above still prove with the
 * icons in place. Their colours are classes, never read here: they are
 * `e2e/layout/theme-roles.spec.ts`'s.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {readable, writable} from 'svelte/store';
import type {AuthError, AuthErrorKey} from '$lib/types';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, render, screen} from '$test/component';

// The identity translator: components render i18n keys verbatim, so the tests
// can name the text that was chosen without naming any one language. Lazy, like
// `authError` below, so the sign-in error cases can swap it.
vi.mock('$lib/i18n', () => ({_: {subscribe: (run: (value: unknown) => void) => translator.subscribe(run)}}));
// The auth store at rest — nothing loading, no error — so the form renders as a
// user first sees it. Signing in is not the subject here: `login` only has to exist.
// `authError` is a lazy `subscribe`, as in `PasswordChangeModal.test.ts`: the
// factory runs while the component is being imported, before `signInError` below
// exists, so it must not touch the store until the component subscribes to it.
vi.mock('$lib/stores/app/auth', () => ({
    auth: {login: vi.fn()},
    authError: {subscribe: (run: (value: unknown) => void) => signInError.subscribe(run)},
    isAuthLoading: readable(false),
}));
vi.mock('$app/navigation', () => ({goto: vi.fn()}));
/**
 * The accounts part of an answer, with the flag of A6d: `first_account_open`, true while the instance has no account.
 * Optional in the schema (absent reads as false), and part of the generated `InstanceConfig` only after the `api sync`
 * that follows the backend: the intersection names it both before that sync and after it.
 */
type AccountsAnswer = InstanceConfig['accounts'] & {first_account_open?: boolean};
// The instance configuration held by the test: a fake with the real store's shape — enumerable getters over `$state`
// (`reactiveBox`), so a template reading `instanceConfig.config` re-renders when the test changes it, as it would when
// the server answers — and a `load` spy that resolves at once. Open before every test (`beforeEach`), like
// `DEFAULT_INSTANCE_CONFIG`. `globalSettings` is still mocked, holding the old «closed» value: the card must neither
// follow it nor load it any more.
const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    type Mode = 'open' | 'invite' | 'disabled';
    /** `first_account_open` is in the answer only when given: left out, the answer reads as one from before A6d. */
    const accounts = (registration_mode: Mode, registration_locked = false, first_account_open?: boolean): AccountsAnswer => (first_account_open === undefined ? {registration_mode, registration_locked} : {registration_mode, registration_locked, first_account_open});
    const OPEN: InstanceConfig = {profile: 'selfhosted', accounts: accounts('open')};
    return {
        OPEN,
        INVITE: {profile: 'selfhosted', accounts: accounts('invite')} as InstanceConfig,
        DISABLED: {profile: 'selfhosted', accounts: accounts('disabled')} as InstanceConfig,
        /** The answer of a self-hosted instance in `mode` that says `first_account_open` (A6d). */
        answer: (mode: Mode, first_account_open: boolean): InstanceConfig => ({profile: 'selfhosted', accounts: accounts(mode, false, first_account_open)}),
        instance: reactiveBox<{config: InstanceConfig}>({config: OPEN}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
        settingsLoad: vi.fn<() => Promise<void>>().mockResolvedValue(undefined).mockName('globalSettings.load'),
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
    return {globalSettings: {subscribe: readable({enable_registration: false}).subscribe, load: mocks.settingsLoad}};
});

import LoginCard from './LoginCard.svelte';

/** Every key comes back as itself. */
const identity = (key: string): string => key;
/** The translator the card reads: the identity, unless a case swaps it. */
const translator = writable<(key: string) => string>(identity);
/** What `authError` holds: no error, as a user first sees the card, unless a case sets one. */
const signInError = writable<AuthError | null>(null);

/** Mounts the card and returns the element everything it rendered lives in. */
function mount(props: {successMessage?: string; successTone?: 'success' | 'warning'} = {}): HTMLElement {
    return render(LoginCard, props).container;
}

function field(testId: string): HTMLInputElement {
    return screen.getByTestId(testId) as HTMLInputElement;
}

/**
 * The named attributes of one element as a single object, `null` where absent,
 * so a red shows every mismatch in one diff instead of stopping at the first.
 */
function attributes(el: Element, names: readonly string[]): Record<string, string | null> {
    return Object.fromEntries(names.map((name) => [name, el.getAttribute(name)]));
}

/** Tag and test id of an element: enough for a red to say which one it means. */
function describeElement(el: Element): string {
    const testId = el.getAttribute('data-testid');
    return testId ? `${el.tagName.toLowerCase()}[data-testid="${testId}"]` : el.tagName.toLowerCase();
}

/** Every element under `root` that prints `id=""`. */
function emptyIds(root: Element): string[] {
    return Array.from(root.querySelectorAll('[id=""]'), describeElement);
}

/** Every non-empty id under `root` that more than one element carries. */
function duplicateIds(root: Element): string[] {
    const ids = Array.from(root.querySelectorAll('[id]'), (el) => el.id).filter((id) => id !== '');
    return [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
}

type RegisterOffer = Record<'goto-register' | 'auth.noAccount', boolean>;
const OFFERED: RegisterOffer = {'goto-register': true, 'auth.noAccount': true};
const WITHDRAWN: RegisterOffer = {'goto-register': false, 'auth.noAccount': false};

/**
 * What the card offers a visitor without an account: the `goto-register` link
 * and the `auth.noAccount` text in front of it. Read together, so that a red
 * names each of the two.
 */
function registerOffer(): RegisterOffer {
    return {
        'goto-register': screen.queryByTestId('goto-register') !== null,
        'auth.noAccount': screen.queryByText('auth.noAccount') !== null,
    };
}

beforeEach(() => {
    // Every test starts on an open instance, with no read of the configuration or of the settings asked yet.
    mocks.instance.config = mocks.OPEN;
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockResolvedValue(undefined);
    mocks.settingsLoad.mockClear();
});

afterEach(cleanup);
// Back to the card at rest, for whichever case comes next.
afterEach(() => {
    signInError.set(null);
    translator.set(identity);
});

describe("LoginCard — the markup Chrome's password manager reads", () => {
    it('names the username field, so Chrome can pair it with a saved account', () => {
        mount();

        expect(attributes(field('login-username'), ['id', 'name', 'autocomplete', 'type'])).toEqual({id: 'login-username', name: 'username', autocomplete: 'username', type: 'text'});
    });

    it('keeps a phone keyboard from capitalising or correcting the username', () => {
        // Neither attribute changes what Chrome parses; both change what gets
        // typed. A username the keyboard "fixed" is not the one the user meant.
        mount();

        expect(attributes(field('login-username'), ['autocapitalize', 'spellcheck'])).toEqual({autocapitalize: 'none', spellcheck: 'false'});
    });

    it('names the password field as the current password', () => {
        mount();

        expect(attributes(field('login-password'), ['id', 'name', 'autocomplete', 'type'])).toEqual({id: 'login-password', name: 'password', autocomplete: 'current-password', type: 'password'});
    });

    it.each([
        {testId: 'login-username', key: 'auth.usernameOrEmail'},
        {testId: 'login-password', key: 'auth.password'},
    ])('labels $testId with the key its placeholder shows', ({testId, key}) => {
        mount();
        const input = field(testId);

        expect(screen.getByLabelText(key)).toBe(input);
        // A `<label for>`, specifically: an `aria-label` would satisfy the query
        // above and give the password manager no label element to read.
        expect(input.labels).toHaveLength(1);
        const label = input.labels![0];
        expect(label).toHaveAttribute('for', input.id);
        expect(input).toHaveAttribute('placeholder', key);
        expect(label.textContent?.trim()).toBe(key);
        // Hidden from sight, not from assistive technology: once the placeholder
        // is gone, the label is the only name a screen reader has for the field.
        expect(label).not.toHaveAttribute('hidden');
        expect(label).not.toHaveAttribute('aria-hidden', 'true');
    });

    it('leaves no element with an empty id', () => {
        // `PasswordInput` printed `id=""` whenever it was given no id: invalid
        // HTML (an id needs at least one character), a target no label can
        // point at, and noise for any parser that keys fields by id.
        expect(emptyIds(mount())).toEqual([]);
    });

    it('gives every id in the card to one element only', () => {
        // Chromium's own advice to password-form authors: "no two elements
        // should have the same id". A guard for the ids the fix introduces.
        expect(duplicateIds(mount())).toEqual([]);
    });

    it('keeps both fields in the one login form', () => {
        // Chrome pairs a username with a password of the same `<form>`; a field
        // moved outside it would be parsed on its own. A guard, not a change.
        mount();
        const form = screen.getByTestId('login-form');

        expect(field('login-username').form).toBe(form);
        expect(field('login-password').form).toBe(form);
    });
});

describe('LoginCard — «Register here» follows the registration mode of the instance (A5b)', () => {
    it('offers registration while the instance is open', async () => {
        // And only the instance decides: the mocked global settings still hold `enable_registration: false`, the key
        // A5a removed, which the card used to follow.
        mocks.instance.config = mocks.OPEN;
        mount();
        await tick();

        expect(registerOffer()).toEqual(OFFERED);
    });

    it.each([
        ['invite', mocks.INVITE],
        ['disabled', mocks.DISABLED],
    ])('offers no registration on an instance whose mode is %s', async (_mode, config) => {
        // No `first_account_open` in this answer, as in one from before A6d: absent reads as false, an instance that
        // has an account. The A6d cases below say the flag.
        mocks.instance.config = config;
        mount();
        await tick();

        // The card is there: only the way to an account the backend would refuse goes.
        expect(screen.getByTestId('login-form')).toBeInTheDocument();
        expect(screen.getByTestId('goto-forgot')).toBeInTheDocument();
        expect(registerOffer()).toEqual(WITHDRAWN);
    });

    it('offers it before the server has answered: the defaults are open', async () => {
        // `load()` never settles here, and the store still holds DEFAULT_INSTANCE_CONFIG. The backend refuses a
        // registration it does not allow anyway.
        mocks.instanceLoad.mockReturnValue(new Promise<void>(() => {}));
        mount();
        await tick();

        expect(registerOffer()).toEqual(OFFERED);
    });

    it('follows the answer as soon as it lands, both ways, without a remount', async () => {
        mount();
        await tick();
        expect(registerOffer(), 'open at mount: the defaults').toEqual(OFFERED);

        // What the server's answer brings on an invite-only instance.
        mocks.instance.config = mocks.INVITE;
        await tick();
        expect(screen.getByTestId('goto-forgot')).toBeInTheDocument();
        expect(registerOffer(), 'the answer says invite').toEqual(WITHDRAWN);

        mocks.instance.config = mocks.OPEN;
        await tick();
        expect(registerOffer(), 'a later answer says open again').toEqual(OFFERED);
    });

    // A6d (decision 36): the first account of an empty instance can always be created, and becomes its administrator.
    // So while the answer says `first_account_open: true` the link is offered whatever the mode — a new install defaults
    // to invite, and its very first visitor must still find the way to the account that will run it.
    it.each(['invite', 'disabled'] as const)('offers registration on an instance in mode %s that has no account yet: first_account_open true (A6d)', async (mode) => {
        mocks.instance.config = mocks.answer(mode, true);
        mount();
        await tick();

        expect(registerOffer(), `mode ${mode}, first_account_open true: the first account can always be created`).toEqual(OFFERED);
    });

    it.each(['invite', 'disabled'] as const)('offers no registration in mode %s once the instance has an account: first_account_open false, said (A6d)', async (mode) => {
        // The flag said false, beside the cases above that leave it out: the mode alone decides again.
        mocks.instance.config = mocks.answer(mode, false);
        mount();
        await tick();

        // The card is there: only the way to an account the backend would refuse goes.
        expect(screen.getByTestId('login-form')).toBeInTheDocument();
        expect(screen.getByTestId('goto-forgot')).toBeInTheDocument();
        expect(registerOffer(), `mode ${mode}, first_account_open false`).toEqual(WITHDRAWN);
    });

    it('offers registration on an open instance that already has an account: first_account_open false (A6d)', async () => {
        // The flag only adds the first account: it never takes the link away from an instance where anyone may register.
        mocks.instance.config = mocks.answer('open', false);
        mount();
        await tick();

        expect(registerOffer(), 'mode open, first_account_open false').toEqual(OFFERED);
    });

    it('follows first_account_open as soon as an answer changes it, both ways, without a remount (A6d)', async () => {
        mount();
        await tick();
        expect(registerOffer(), 'open at mount: the defaults').toEqual(OFFERED);

        // The answer of a new install: invitation only, and no account yet.
        mocks.instance.config = mocks.answer('invite', true);
        await tick();
        expect(registerOffer(), 'invite, first_account_open true: the first account can always be created').toEqual(OFFERED);

        // A later answer, once the first account exists: the same mode, only the flag changed.
        mocks.instance.config = mocks.answer('invite', false);
        await tick();
        expect(screen.getByTestId('goto-forgot')).toBeInTheDocument();
        expect(registerOffer(), 'invite, first_account_open false: the instance has an account now').toEqual(WITHDRAWN);

        mocks.instance.config = mocks.answer('invite', true);
        await tick();
        expect(registerOffer(), 'and back: the card draws whatever the latest answer says').toEqual(OFFERED);
    });

    it('asks for the instance configuration once, on mount, not forced — and no longer for the global settings', async () => {
        // `GET /system/instance` is public, and `load()` without force shares the one request of the page load.
        mount();
        await tick();

        expect(mocks.instanceLoad).toHaveBeenCalledTimes(1);
        expect(mocks.instanceLoad.mock.calls[0][0]?.force, 'the shared request of the page load, not a forced one').not.toBe(true);
        expect(mocks.settingsLoad, 'the global settings no longer decide anything here').not.toHaveBeenCalled();
    });
});

describe('LoginCard — the success message has a handle (A5b)', () => {
    it('draws the message it is given in login-success', () => {
        mount({successMessage: 'A message the page handed over'});

        expect(screen.getByTestId('login-success')).toHaveTextContent('A message the page handed over');
    });

    it('draws a success by default: data-tone success, the success roles', () => {
        mount({successMessage: 'Account created'});

        const box = screen.getByTestId('login-success');
        expect(box).toHaveAttribute('data-tone', 'success');
        expect(box.className).toContain('lf-success');
        expect(box.className).not.toContain('lf-warning');
    });

    it('draws a warning when its tone says so (an activation email that was held): data-tone warning, the warning roles of the design system', () => {
        mount({successMessage: 'Account created, email held', successTone: 'warning'});

        const box = screen.getByTestId('login-success');
        expect(box).toHaveTextContent('Account created, email held');
        expect(box).toHaveAttribute('data-tone', 'warning');
        for (const role of ['bg-lf-warning-soft', 'border-lf-warning-line', 'text-lf-warning-on-soft']) expect(box.className, role).toContain(role);
        expect(box.className, 'no success role left on a warning').not.toContain('lf-success');
        expect(box.className.includes('dark:'), 'a role changes value under html.dark by itself').toBe(false);
    });

    it('draws no login-success without a message', () => {
        mount();

        expect(screen.getByTestId('login-form'), 'premise: the card is drawn').toBeInTheDocument();
        expect(screen.queryByTestId('login-success')).toBeNull();
    });
});

/**
 * The sign-in error (O, step 21, finding 5; backlog 38, item O-15; plan A3).
 *
 * The card printed `{$authError}` as it was, and the store put an English
 * sentence there, so the error read in English in every language. Step 21 made
 * `authError` an `AuthError` (`$lib/types`) the card draws in `login-error`: a
 * `{key}` through the translator, a `{message}` — the axios words — verbatim.
 * Plan A3 (O-15) removes the `{message}` variant: the store now turns every
 * failure into a catalogue key (`stores/app/auth.test.ts`), so the card has one
 * way left to draw an error, and the cases that drew a message as it came are
 * gone with it:
 *   - `{key}`, a catalogue key, through the translator (`$_(key)`): translated
 *     when it is drawn, not when the sign-in failed, so it also follows a
 *     language change while it is on screen;
 *   - `null`: no error box at all.
 *
 * These cases swap the identity for a translator that marks what it translated,
 * `⟦key⟧`. The keys come from a `Record<AuthErrorKey, true>`, so a key the store
 * can emit and this file does not draw fails `front check`. Every case is green
 * at runtime today — the card already sends a `{key}` through `$_` — and the
 * three keys of O-15 fail only the type check until `AuthErrorKey` grows: what
 * A3 changes in the card is that the verbatim branch can no longer be reached.
 * `email.verification.loginRequired` (workstream E, E5b) is left out: it draws the
 * verification notice instead of the box, covered in `LoginCard.verification.test.ts` (LVR).
 */
describe('LoginCard — the sign-in error is a key, drawn through the translator', () => {
    /** Every key the store can emit, each drawn below in the box — but `email.verification.loginRequired` (workstream E, E5b), which draws the verification notice instead (LVR, `LoginCard.verification.test.ts`). */
    const EMITTED: Record<Exclude<AuthErrorKey, 'email.verification.loginRequired'>, true> = {
        'auth.invalidCredentials': true,
        'auth.invalidInput': true,
        'auth.loginFailed': true,
        'auth.accountDisabled': true,
        'auth.loginServerUnreachable': true,
        'auth.loginServerError': true,
        'auth.tooManyAttempts': true,
    };
    const KEYS = Object.keys(EMITTED) as AuthErrorKey[];
    const marked = (key: string): string => `⟦${key}⟧`;
    const errorBox = () => screen.queryByTestId('login-error');
    /** What the box reads, whitespace collapsed: the markup around the text is the card's business. */
    const shown = (box: HTMLElement | null): string | undefined => box?.textContent?.replace(/\s+/g, ' ').trim();

    it.each(KEYS)('draws {key: %s} through the translator', (key) => {
        translator.set(marked);
        signInError.set({key});

        mount();

        expect(errorBox(), 'premise: an error draws the box').not.toBeNull();
        expect(shown(errorBox()), 'a {key} error is drawn through the translator, in the language of the page').toBe(marked(key));
    });

    it('follows a language change while the error is on screen', async () => {
        translator.set((key) => `first:${key}`);
        signInError.set({key: 'auth.invalidCredentials'});
        mount();
        expect(shown(errorBox()), 'a {key} error is drawn through the translator of the moment').toBe('first:auth.invalidCredentials');

        translator.set((key) => `second:${key}`);
        await tick();

        expect(shown(errorBox()), 'the key is translated when the card draws it, so the error follows the language').toBe('second:auth.invalidCredentials');
    });

    it('draws no box while there is no error, and takes it away when the error clears', async () => {
        mount();
        expect(errorBox(), 'no error, no box').toBeNull();

        signInError.set({key: 'auth.invalidCredentials'});
        await tick();
        expect(errorBox(), 'premise: an error draws the box').not.toBeNull();

        signInError.set(null);
        await tick();
        expect(errorBox(), 'a cleared error takes the box away').toBeNull();
    });
});

describe('LoginCard — the field icons are decoration', () => {
    it.each([
        {icon: 'login-username-icon', input: 'login-username'},
        {icon: 'login-password-icon', input: 'login-password'},
    ])('draws $icon inside $input, hidden from assistive technology', ({icon, input}) => {
        mount();
        const svg = screen.getByTestId(icon);

        expect(svg.tagName.toLowerCase()).toBe('svg');
        expect(svg).toHaveAttribute('aria-hidden', 'true');
        // Inside the field: the positioned wrapper its input sits in.
        expect(svg.parentElement).toBe(field(input).parentElement);
    });
});
