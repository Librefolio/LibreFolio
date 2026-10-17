// @vitest-environment jsdom
/**
 * PasswordChangeModal — component test (Vitest + jsdom).
 *
 * The change-password dialog. Three fields, a reactive `canSubmit`, and a
 * `trySave` call whose `onError` hook turns the backend's sentence into one of
 * three messages. It is mounted by `ProfileTab` with a single `isOpen` prop and
 * reports back through the `close` / `success` events, so everything that
 * decides its behaviour is either typed into it or comes back from
 * `POST /api/v1/auth/change-password`.
 *
 * Why this is a component test and not an E2E. Reaching the "current password
 * is incorrect" path against a real backend means knowing a wrong password,
 * which is easy; reaching "must be different" means knowing the right one,
 * which in a shared-database suite means changing a real user's credentials and
 * putting them back — the exact thing rule 8 asks a test not to gamble on. And
 * the interesting half of the success path is a 1500 ms timer plus two events
 * that never appear on screen.
 *
 * On not asserting translated text. Every message here comes from `$_()` and the
 * app ships in EN/IT/FR/ES, so `$lib/i18n` is mocked with an identity
 * translator: `$_('settings.currentPasswordIncorrect')` renders as that literal
 * key. Every assertion below names a key, which is stable in all four languages,
 * never a sentence — except where the component deliberately echoes the server's
 * own words, which is marked where it happens.
 *
 * `createEventDispatcher` is Svelte 4 API kept alive by Svelte 5's legacy layer:
 * `$on()` is gone, and the listener arrives through the `$$events` prop instead.
 *
 * One behaviour recorded here is a characterisation, not an endorsement: the
 * submit *event* bypasses `canSubmit` entirely.
 *
 * The last block pins markup no user looks at and Chrome's password manager
 * reads (developer note, 30/09: Chrome offered saved credentials on the login
 * password field only, never on the username; `LoginCard.test.ts` tells the
 * story in full). Decision D2 aligns all three credential forms. This one's own
 * gap is the username: there is none on screen, so when the new password is
 * saved Chrome cannot tell which stored account it replaces. Chromium's advice
 * for change-password forms is a username field the user does not see, carrying
 * the account name, inside the same form. The account name comes from
 * `currentUser`, mocked below as a writable so a test can rename the user, or
 * end the session, under a mounted dialog.
 *
 * Accounts lot A6c (decision 37) takes the password rules out of the dialog. The
 * backend writes them once, refuses a new password that breaks one with a 400
 * `{detail: {error_code: "PASSWORD_TOO_WEAK", message, rules}}`, and exposes
 * them in `GET /system/instance` (`accounts.password_rules`), where the meter,
 * `PasswordStrength`, reads them. The dialog keeps no copy any more: it binds
 * the meter's `valid`, as `ResetPasswordCard` does since A5b, and both Save and
 * the submit guard follow it. Its old copy hard-wired eight characters and
 * ASCII classes, so the A6c describe tells the two apart with rules only the
 * server could have given: twelve characters asked for, a rule set that asks
 * only for length, an answer that lands while the dialog is open, a code this
 * build does not know (never a reason to withhold Save: the server decides). The
 * configuration is a fake with the real store's shape — `reactiveBox` behind
 * getters, as in `LoginCard.test.ts` — and starts every test without
 * `password_rules`, so every other case runs on the defaults, the five rules of
 * before. The server's refusal is an object `detail`, which the dialog's
 * `onError` used to lower-case as if it were a sentence: it must be drawn as
 * `auth.validation.passwordTooWeak`, the key the dialog's own check already
 * shows, never as the server's English, and leave the form usable.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import {tick} from 'svelte';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

// The identity translator: components render i18n keys verbatim, so the tests
// can name the message that was chosen without naming any one language.
vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/api', () => ({zodiosApi: {change_password_api_v1_auth_change_password_post: vi.fn()}}));
// The signed-in user, read by the hidden username field (last block). A lazy
// `subscribe`, as in `ProfileTab.test.ts`: the factory runs while the component
// is being imported, before `signedIn` below exists, so it must not touch the
// store until the component subscribes to it.
vi.mock('$lib/stores/app/auth', () => ({
    currentUser: {subscribe: (run: (value: unknown) => void) => signedIn.subscribe(run)},
}));
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

import PasswordChangeModal from './PasswordChangeModal.svelte';
import {zodiosApi} from '$lib/api';
// The real toast store, the one `trySave` raises its toasts in: the limit's block (A8b) reads it to prove none was raised.
import {toasts} from '$lib/stores/app/toastStore.svelte';

const changePassword = vi.mocked(zodiosApi.change_password_api_v1_auth_change_password_post);

/** Satisfies all five rules: length, upper, lower, digit, special. */
const GOOD_PASSWORD = 'Str0ng!pass';
/** A second one, equally valid, for "the new one differs from the old". */
const OLD_PASSWORD = 'Old3r!pass';
/** The account the dialog changes the password of, and the name it is renamed to. */
const USERNAME = 'alice';
const RENAMED = 'alice.renamed';

const signedIn = writable<{username: string} | null>({username: USERNAME});

interface Mounted {
    close: ReturnType<typeof vi.fn>;
    success: ReturnType<typeof vi.fn>;
    container: HTMLElement;
}

function mount(): Mounted {
    const close = vi.fn();
    const success = vi.fn();
    const {container} = render(PasswordChangeModal, {
        isOpen: true,
        $$events: {close, success},
    } as never);
    return {close, success, container};
}

async function fill(testId: string, value: string): Promise<void> {
    await fireEvent.input(screen.getByTestId(testId), {target: {value}});
}

/** Types a set of values that turns `canSubmit` on. */
async function fillValid(overrides: Partial<Record<'current' | 'next' | 'confirm', string>> = {}): Promise<void> {
    await fill('password-current', overrides.current ?? OLD_PASSWORD);
    await fill('password-new', overrides.next ?? GOOD_PASSWORD);
    await fill('password-confirm', overrides.confirm ?? overrides.next ?? GOOD_PASSWORD);
}

function saveButton(): HTMLElement {
    return screen.getByTestId('password-change-submit');
}

/** The error banner, or null while there is nothing to report. */
function banner(): HTMLElement | null {
    return screen.queryByTestId('info-banner-error');
}

/** An axios-shaped rejection carrying `response.data.detail`. */
function serverError(detail: unknown, status = 400): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {
        isAxiosError: true,
        response: {status, data: {detail}},
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
/** What the dialog says of a password the rules refuse, its own check or the server's. */
const WEAK_KEY = 'auth.validation.passwordTooWeak';

beforeEach(() => {
    changePassword.mockReset();
    changePassword.mockResolvedValue({message: 'Password changed successfully'} as never);
    // `trySave` logs every failure to the console by contract; the failure paths
    // below are deliberate, so the noise is suppressed rather than read.
    vi.spyOn(console, 'error').mockImplementation(() => {});
    // Every test starts before the server's answer: no password_rules, so the meter checks the defaults.
    mocks.instance.config = mocks.BEFORE_ANSWER;
    mocks.instance.loaded = false;
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockResolvedValue(undefined);
});

afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    cleanup();
});

describe('PasswordChangeModal — what makes Save available', () => {
    it('offers Save once all three fields agree', async () => {
        mount();
        await fillValid();

        expect(saveButton()).toBeEnabled();
    });

    it.each([
        ['the current password is missing', {current: ''}],
        ['the new password is missing', {next: '', confirm: ''}],
        ['the confirmation is missing', {confirm: ''}],
    ])('withholds Save while %s', async (_label, overrides) => {
        mount();
        await fillValid(overrides);

        expect(saveButton()).toBeDisabled();
    });

    it.each([
        ['too short', 'Sh0rt!'],
        ['no uppercase', 'str0ng!pass'],
        ['no lowercase', 'STR0NG!PASS'],
        ['no digit', 'Strong!pass'],
        ['no special character', 'Str0ngpass'],
    ])('withholds Save for a new password with %s', async (_label, weak) => {
        mount();
        await fillValid({next: weak});

        expect(saveButton()).toBeDisabled();
    });

    it('withholds Save while the confirmation does not match', async () => {
        mount();
        await fillValid({confirm: `${GOOD_PASSWORD}x`});

        expect(saveButton()).toBeDisabled();
    });

    it('tells the user why, inline, as soon as the confirmation diverges', async () => {
        mount();
        await fillValid({confirm: `${GOOD_PASSWORD}x`});

        expect(screen.getByText('settings.passwordsMustMatch')).toBeInTheDocument();
    });

    it('withdraws that inline complaint once the two agree again', async () => {
        mount();
        await fillValid({confirm: `${GOOD_PASSWORD}x`});
        expect(screen.getByText('settings.passwordsMustMatch')).toBeInTheDocument();

        await fill('password-confirm', GOOD_PASSWORD);

        expect(screen.queryByText('settings.passwordsMustMatch')).not.toBeInTheDocument();
        expect(saveButton()).toBeEnabled();
    });

    it('says nothing about matching while the confirmation is still empty', async () => {
        // The complaint is gated on `confirmPassword &&` precisely so that an
        // untouched field is not an error; typing the first character is what
        // turns an empty box into a wrong one.
        mount();
        await fill('password-new', GOOD_PASSWORD);

        expect(screen.queryByText('settings.passwordsMustMatch')).not.toBeInTheDocument();
    });

    it('measures the strength of the new password, not of the other two', async () => {
        // The meter is wired to `newPassword`; wiring it to the current password
        // would grade the secret the user is replacing.
        mount();
        await fill('password-current', OLD_PASSWORD);

        expect(screen.queryByTestId('password-strength-meter')).toBeNull();

        await fill('password-new', GOOD_PASSWORD);

        expect(screen.getByTestId('password-strength-meter')).toBeInTheDocument();
    });
});

describe('PasswordChangeModal — what reaches the server', () => {
    it('sends exactly the two secrets the endpoint takes', async () => {
        mount();
        await fillValid();

        await fireEvent.click(saveButton());

        await waitFor(() => expect(changePassword).toHaveBeenCalledTimes(1));
        expect(changePassword).toHaveBeenCalledWith({current_password: OLD_PASSWORD, new_password: GOOD_PASSWORD});
    });

    it('leaves both passwords exactly as typed, spaces included', async () => {
        // Trimming either one would silently lock the user out of the account
        // they think they just secured.
        const spacedOld = ` ${OLD_PASSWORD} `;
        const spacedNew = ` ${GOOD_PASSWORD} `;
        mount();
        await fillValid({current: spacedOld, next: spacedNew});

        await fireEvent.click(saveButton());

        await waitFor(() => expect(changePassword).toHaveBeenCalledTimes(1));
        expect(changePassword).toHaveBeenCalledWith({current_password: spacedOld, new_password: spacedNew});
    });
});

describe('PasswordChangeModal — errors reported by the server', () => {
    async function submitAndRead(detail: unknown): Promise<string> {
        changePassword.mockRejectedValue(serverError(detail));
        mount();
        await fillValid();
        await fireEvent.click(saveButton());

        await waitFor(() => expect(banner()).not.toBeNull());
        return banner()!.textContent?.trim() ?? '';
    }

    it.each([
        // The exact sentences this backend returns — `backend/app/api/v1/auth.py`
        // lines 228 and 232. Asserted on the real wording rather than a lowercase
        // stand-in, because a stand-in is what hid the same bug in RegisterCard:
        // the match is case-insensitive only because `onError` lowercases first,
        // and a test that feeds it pre-lowercased text never checks that.
        ['Current password is incorrect', 'settings.currentPasswordIncorrect'],
        ['New password must be different from current password', 'settings.passwordMustBeDifferent'],
    ])('translates the server sentence %s', async (detail, key) => {
        expect(await submitAndRead(detail)).toBe(key);
    });

    it('still shows a sentence it has no mapping for, rather than swallowing it', async () => {
        // Neither keyword present: `onError` returns false, `trySave` extracts the
        // detail, and the server's own words are the best available answer.
        // Deliberately asserted on a raw sentence — it is not a key and never
        // passes through the catalogue.
        const detail = 'Account is locked by the administrator';
        expect(await submitAndRead(detail)).toBe(detail);
    });

    it.each([
        ['the rejection carries no words at all', new Error('')],
        ['the rejection is a bare object', {response: {data: {}}}],
    ])('falls back to its own translated sentence when %s', async (_label, rejection) => {
        // `trySave` only reaches for `fallback` when what it extracted turns out
        // to say nothing — an empty message, a bare class name, `[object Object]`.
        // These two are the shapes that qualify, and they are the only way
        // `settings.passwordChangeFailed` is ever seen.
        changePassword.mockRejectedValue(rejection);
        mount();
        await fillValid();
        await fireEvent.click(saveButton());

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(within(banner()!).getByText('settings.passwordChangeFailed')).toBeInTheDocument();
    });

    it.each([
        ['a transport failure', new Error('Network Error'), 'Network Error'],
        ['an axios status message with no detail', serverError(undefined), 'Request failed with status code 400'],
    ])('prefers the raw text of %s over its own fallback', async (_label, rejection, shown) => {
        // Deliberately asserted on English sentences: these are not keys and never
        // pass through the catalogue. That is `trySave`'s documented ladder —
        // anything informative beats the caller's generic sentence — and it means
        // an Italian user reads "Network Error" here. Recorded, not judged: the
        // decision belongs to `trySave`, which has tests of its own.
        changePassword.mockRejectedValue(rejection);
        mount();
        await fillValid();
        await fireEvent.click(saveButton());

        await waitFor(() => expect(banner()).not.toBeNull());
        expect(within(banner()!).getByText(shown)).toBeInTheDocument();
    });

    it('keeps the draft on screen so the user can correct one field and retry', async () => {
        changePassword.mockRejectedValue(serverError('Current password is incorrect'));
        mount();
        await fillValid();
        await fireEvent.click(saveButton());
        await waitFor(() => expect(banner()).not.toBeNull());

        expect(screen.getByTestId('password-new')).toHaveValue(GOOD_PASSWORD);
        expect(screen.getByTestId('password-confirm')).toHaveValue(GOOD_PASSWORD);
        expect(saveButton()).toBeEnabled();
    });

    it('lets the user dismiss the banner without retyping anything', async () => {
        changePassword.mockRejectedValue(serverError('Current password is incorrect'));
        mount();
        await fillValid();
        await fireEvent.click(saveButton());
        await waitFor(() => expect(banner()).not.toBeNull());

        await fireEvent.click(within(banner()!).getByRole('button', {name: 'Dismiss'}));

        await waitFor(() => expect(banner()).toBeNull());
        expect(screen.getByTestId('password-current')).toHaveValue(OLD_PASSWORD);
    });

    it('drops the previous error when a new attempt begins', async () => {
        changePassword.mockRejectedValueOnce(serverError('Current password is incorrect'));
        mount();
        await fillValid();
        await fireEvent.click(saveButton());
        await waitFor(() => expect(banner()).not.toBeNull());

        await fireEvent.click(saveButton());

        await waitFor(() => expect(banner()).toBeNull());
    });
});

describe('PasswordChangeModal — while the request is in flight', () => {
    it('locks all three fields and both buttons', async () => {
        const pending = deferred<never>();
        changePassword.mockReturnValue(pending.promise as never);
        mount();
        await fillValid();

        await fireEvent.click(saveButton());

        await waitFor(() => expect(saveButton()).toBeDisabled());
        expect(screen.getByTestId('password-current')).toBeDisabled();
        expect(screen.getByTestId('password-new')).toBeDisabled();
        expect(screen.getByTestId('password-confirm')).toBeDisabled();
        expect(screen.getByTestId('password-change-cancel')).toBeDisabled();

        pending.resolve(undefined as never);
    });

    it('says it is working rather than inviting another click', async () => {
        const pending = deferred<never>();
        changePassword.mockReturnValue(pending.promise as never);
        mount();
        await fillValid();

        await fireEvent.click(saveButton());

        await waitFor(() => expect(saveButton()).toHaveTextContent('common.loading'));

        pending.resolve(undefined as never);
        await waitFor(() => expect(saveButton()).not.toHaveTextContent('common.loading'));
    });
});

describe('PasswordChangeModal — after the password has changed', () => {
    it('confirms in place first, and only then hands control back', async () => {
        // The 1500 ms pause is the whole point of the success path: the user is
        // meant to read the confirmation before the dialog disappears.
        vi.useFakeTimers();
        const {close, success} = mount();
        await fillValid();

        await fireEvent.click(saveButton());
        await vi.advanceTimersByTimeAsync(0);
        await tick();

        expect(screen.getByText('settings.passwordChanged')).toBeInTheDocument();
        expect(success).not.toHaveBeenCalled();
        expect(close).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(1500);

        expect(success).toHaveBeenCalledTimes(1);
        expect(close).toHaveBeenCalledTimes(1);
    });

    it('empties every field as soon as the change succeeds, so the old password cannot be sent again', async () => {
        vi.useFakeTimers();
        mount();
        await fillValid();

        await fireEvent.click(saveButton());
        await vi.advanceTimersByTimeAsync(0);
        await tick();

        expect(screen.getByTestId('password-current')).toHaveValue('');
        expect(screen.getByTestId('password-new')).toHaveValue('');
        expect(screen.getByTestId('password-confirm')).toHaveValue('');
    });

    it('keeps Save disabled during the 1500 ms confirmation and ignores another submit', async () => {
        vi.useFakeTimers();
        const {container} = mount();
        await fillValid();

        await fireEvent.click(saveButton());
        await vi.advanceTimersByTimeAsync(0);
        await tick();

        expect(screen.getByText('settings.passwordChanged')).toBeInTheDocument();
        expect(saveButton()).toBeDisabled();

        await fireEvent.click(saveButton());
        await fireEvent.submit(container.querySelector('form') as HTMLFormElement);
        await vi.advanceTimersByTimeAsync(0);

        expect(changePassword).toHaveBeenCalledTimes(1);
    });
});

describe('PasswordChangeModal — leaving without changing anything', () => {
    it('reports the dismissal and clears the draft', async () => {
        const {close} = mount();
        await fillValid();

        await fireEvent.click(screen.getByTestId('password-change-cancel'));

        expect(close).toHaveBeenCalledTimes(1);
        expect(changePassword).not.toHaveBeenCalled();
        expect(screen.getByTestId('password-current')).toHaveValue('');
    });

    it('clears the error too, so a reopened dialog is not still complaining', async () => {
        changePassword.mockRejectedValue(serverError('Current password is incorrect'));
        mount();
        await fillValid();
        await fireEvent.click(saveButton());
        await waitFor(() => expect(banner()).not.toBeNull());

        await fireEvent.click(screen.getByTestId('password-change-cancel'));

        await waitFor(() => expect(banner()).toBeNull());
    });
});

describe('PasswordChangeModal — the submit event bypasses the button that guards it', () => {
    /** The `<form>` carries `on:submit|preventDefault`, but has no test id. */
    function form(container: HTMLElement): HTMLFormElement {
        const el = container.querySelector('form');
        if (!el) throw new Error('the modal rendered no form');
        return el;
    }

    it.each([
        ['a new password that breaks the rules', {next: 'weak', confirm: 'weak'}, 'auth.validation.passwordTooWeak'],
        ['a confirmation that does not match', {confirm: `${GOOD_PASSWORD}x`}, 'settings.passwordsMustMatch'],
    ])('refuses %s and says so', async (_label, overrides, key) => {
        // These two guards live inside `handleSubmit`, and `canSubmit` already
        // encodes both — so through the Save button they are unreachable, which
        // is why they had never been executed. The submit event is the only way
        // in, and it is the path that would open the day someone adds a
        // `type="submit"` control to this form.
        const {container} = mount();
        await fillValid(overrides);

        await fireEvent.submit(form(container));

        expect(changePassword).not.toHaveBeenCalled();
        expect(banner()).not.toBeNull();
        expect(within(banner()!).getByText(key)).toBeInTheDocument();
    });

    it('sends an empty current password, which the disabled button would have stopped', async () => {
        // Characterisation. `handleSubmit` re-checks the password rules and the
        // match, but never re-checks that the three fields are non-empty — that
        // part of `canSubmit` exists only in the markup. Today nothing user-facing
        // reaches this: the form holds three password inputs and no submit
        // control, so implicit submission is not performed by the browser. It is
        // a latent hazard, recorded so that adding a submit button cannot make it
        // real in silence.
        const {container} = mount();
        await fillValid({current: ''});
        expect(saveButton()).toBeDisabled();

        await fireEvent.submit(form(container));

        await waitFor(() => expect(changePassword).toHaveBeenCalledTimes(1));
        expect(changePassword).toHaveBeenCalledWith({current_password: '', new_password: GOOD_PASSWORD});
    });
});

describe("PasswordChangeModal — the password rules are the server's, read through the meter (A6c)", () => {
    it("withholds Save for a new password the server's rules refuse, though it meets the five of before: min_length 12", async () => {
        answer(withMinLength(12));
        mount();
        await fillValid(); // GOOD_PASSWORD: eleven characters, all five classes — what the old copy let through

        expect(saveButton()).toBeDisabled();
        // The meter under the field says which rule: one set of rules decides both.
        expect(screen.getByTestId('password-rule-minLength')).toHaveAttribute('data-passed', 'false');
    });

    it('offers Save for a new password of the length the server asks for', async () => {
        // The barrier of the case above: the same rules, twelve characters, and Save is there.
        answer(withMinLength(12));
        mount();
        await fillValid({next: TWELVE});

        expect(saveButton()).toBeEnabled();
    });

    it("offers Save, and sends, a password the server's rules accept though the old copy refused it: a rule set that asks only for length", async () => {
        answer([{code: 'min_length', value: 16}]);
        mount();
        await fillValid({next: PASSPHRASE});
        expect(saveButton()).toBeEnabled();

        await fireEvent.click(saveButton());

        await waitFor(() => expect(changePassword).toHaveBeenCalledTimes(1));
        expect(changePassword).toHaveBeenCalledWith({current_password: OLD_PASSWORD, new_password: PASSPHRASE});
    });

    it('follows an answer that lands while the dialog is open, both ways, without a remount', async () => {
        mount();
        await fillValid();
        expect(saveButton(), 'the defaults: eleven characters are enough').toBeEnabled();

        answer(withMinLength(12));
        await tick();
        expect(saveButton(), 'the answer asks for twelve').toBeDisabled();

        answer(FIVE);
        await tick();
        expect(saveButton(), 'a later answer asks for eight again').toBeEnabled();
    });

    it("refuses through the submit event as well, by the server's rules, and says so", async () => {
        // The guard inside `handleSubmit` reads the same `valid` as Save: no second copy there either.
        answer(withMinLength(12));
        const {container} = mount();
        await fillValid();

        await fireEvent.submit(container.querySelector('form') as HTMLFormElement);

        expect(changePassword).not.toHaveBeenCalled();
        expect(banner()).not.toBeNull();
        expect(within(banner()!).getByText(WEAK_KEY)).toBeInTheDocument();
    });

    it('never withholds Save for a rule code it does not know: the server checks it', async () => {
        answer([{code: 'no_dictionary_word'}, ...FIVE, {code: 'not_in_this_build', value: 3}]);
        mount();
        await fillValid();

        expect(saveButton()).toBeEnabled();
    });

    it("shows the server's PASSWORD_TOO_WEAK as auth.validation.passwordTooWeak, never its sentence, and lets the user retry", async () => {
        // The meter let the password through and the server did not: its rules changed after the page had read them.
        changePassword.mockRejectedValue(serverError({error_code: 'PASSWORD_TOO_WEAK', message: 'An English sentence the user must not read', rules: ['min_length']}));
        mount();
        await fillValid();

        await fireEvent.click(saveButton());

        await waitFor(() => expect(banner()).not.toBeNull());
        const shown = banner()!.textContent ?? '';
        expect(shown).toContain(WEAK_KEY);
        expect(shown, "never the server's English").not.toContain('An English sentence the user must not read');
        // The form is usable again: the draft is kept, and Save is back once the request is over.
        expect(screen.getByTestId('password-new')).toHaveValue(GOOD_PASSWORD);
        expect(saveButton()).toBeEnabled();
    });
});

describe("PasswordChangeModal — the markup Chrome's password manager reads", () => {
    // Decision D2 (30/09). The three passwords keep their ids and labels; they
    // gain a `name`. The username is new: see the header.
    const PASSWORDS = [
        {testId: 'password-current', id: 'currentPassword', name: 'current-password', autocomplete: 'current-password', key: 'settings.currentPassword'},
        {testId: 'password-new', id: 'newPassword', name: 'new-password', autocomplete: 'new-password', key: 'settings.newPassword'},
        {testId: 'password-confirm', id: 'confirmPassword', name: 'confirm-password', autocomplete: 'new-password', key: 'settings.confirmNewPassword'},
    ];

    beforeEach(() => signedIn.set({username: USERNAME}));

    function input(testId: string): HTMLInputElement {
        return screen.getByTestId(testId) as HTMLInputElement;
    }

    /** The dialog's one `<form>`, reached through a field in it: it has no test id. */
    function theForm(): HTMLFormElement {
        const form = input('password-current').form;
        if (!form) throw new Error('the current-password field is not inside a form');
        return form;
    }

    /** The form's one field that declares itself a username — red if none, or several. */
    function usernameField(): HTMLInputElement {
        const fields = Array.from(theForm().querySelectorAll<HTMLInputElement>('input[autocomplete="username"]'));
        expect(fields, 'fields with autocomplete="username" inside the change-password form').toHaveLength(1);
        return fields[0];
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

    it('hides a username field in the form, as Chromium asks of change-password forms', () => {
        mount();
        const field = usernameField();

        // `type="text"`, not `type="hidden"`: the password manager reads
        // text-like inputs, and Chromium's own example hides a real input rather
        // than using a hidden one. `hidden` keeps it off screen and out of the
        // tab order; `readonly` keeps it out of the user's hands.
        expect(attributes(field, ['type', 'name', 'autocomplete'])).toEqual({type: 'text', name: 'username', autocomplete: 'username'});
        expect(field).toHaveAttribute('hidden');
        expect(field).not.toBeVisible();
        expect(field).toHaveAttribute('readonly');
        expect(field.form).toBe(theForm());
    });

    it("carries the signed-in user's username", () => {
        mount();

        expect(usernameField()).toHaveValue(USERNAME);
    });

    it('carries the new username after a rename made while the dialog was closed', async () => {
        // `ProfileTab` keeps this dialog mounted, closed, for as long as the tab
        // is open, and lets the user rename themselves there; `checkAuth()` then
        // refreshes `currentUser`. A value read once at mount would file the new
        // password under the old name.
        const {rerender} = render(PasswordChangeModal, {isOpen: false} as never);
        signedIn.set({username: RENAMED});

        await rerender({isOpen: true} as never);

        expect(usernameField()).toHaveValue(RENAMED);
    });

    it('holds an empty value, not an error, when the session ends under the open dialog', async () => {
        mount();

        signedIn.set(null);
        await tick();

        expect(usernameField()).toHaveValue('');
    });

    it.each(PASSWORDS)('names $testId by id, name and autocomplete, and keeps its label', ({testId, id, name, autocomplete, key}) => {
        mount();
        const field = input(testId);

        expect(attributes(field, ['id', 'name', 'autocomplete', 'type'])).toEqual({id, name, autocomplete, type: 'password'});
        expect(screen.getByLabelText(key)).toBe(field);
        expect(field.form).toBe(theForm());
    });

    it('leaves no element with an empty id', () => {
        // A guard: the three passwords already pass their ids, and the new
        // username field must not bring an empty one with it.
        const {container} = mount();

        expect(Array.from(container.querySelectorAll('[id=""]'), describeElement)).toEqual([]);
    });

    it('gives every id in the dialog to one element only', () => {
        const {container} = mount();
        const ids = Array.from(container.querySelectorAll('[id]'), (el) => el.id).filter((id) => id !== '');

        expect([...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))]).toEqual([]);
    });
});

/**
 * Accounts lot A8b (release 1.3, workstream A, contract C11) — the server's limit on failed passwords.
 *
 * Since A8a the server counts a wrong current password typed here as a failed sign-in (F15): past 10 for the account,
 * or 50 from the address, in 15 minutes, `POST /auth/change-password` refuses with a 429
 * `{detail: {error_code: "TOO_MANY_ATTEMPTS", message}}` and a `Retry-After`, before it reads any password — the right
 * one included. The dialog has no word for it: `onError` maps `PASSWORD_TOO_WEAK` and two sentences, so the refusal
 * falls through to `trySave`'s extractor and the user reads the server's English `message`.
 *
 * The contract, the dialog's half:
 *   - status 429 **and** `detail.error_code` `TOO_MANY_ATTEMPTS` → the error banner shows
 *     `$_('settings.tooManyPasswordAttempts')`, and nothing of the server's `message`;
 *   - the three fields keep what was typed (the user may try again later); no success state; no toast (the dialog
 *     passes `toast: false` already);
 *   - a 429 with another `error_code`, or none, keeps today's fallback: never the new key.
 * Where the contract leaves room, its «and» is read both ways: the code on a status that is not 429 keeps today's
 * fallback as well.
 *
 * Red until A8b: the wording. Guards, green today and to stay so: the form after the refusal, and the refusals that are
 * not the limit's — their fallback asserted on the raw words each fixture carries (a server's or axios's, never a
 * catalogue entry), as the block «errors reported by the server» does. The `Retry-After` is in the fixture because the
 * server sends it; the contract asks nothing of it. «Usable» after the refusal is today's state after any refusal: the
 * contract adds no wait before Save comes back.
 */
describe("PasswordChangeModal — the server's limit on failed passwords (A8b, C11)", () => {
    /** The key the contract adds for the limit's refusal. */
    const LIMIT_KEY = 'settings.tooManyPasswordAttempts';
    /** The server's own sentence for it (`_refuse_too_many_failures`, `backend/app/api/v1/auth.py`): never on screen. */
    const LIMIT_MESSAGE = 'Too many failed attempts: try again later';

    /** A rejection as axios raises it once the server has answered: its status, its headers, its body. */
    function answered(status: number, body: unknown, headers: Record<string, string> = {}): Error {
        return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, response: {status, headers, data: body}});
    }

    /** The limit's refusal, as A8a sends it. */
    const limitRefusal = () => answered(429, {detail: {error_code: 'TOO_MANY_ATTEMPTS', message: LIMIT_MESSAGE}}, {'retry-after': '900'});

    /** Types a valid change, saves it against `failure`, and waits for the refusal on screen with the request over. */
    async function submitRefused(failure: Error): Promise<Mounted> {
        changePassword.mockRejectedValue(failure);
        const mounted = mount();
        await fillValid();

        await fireEvent.click(saveButton());

        // Both: an `onError` that words the refusal sets the banner while the request is still in flight.
        await waitFor(() => {
            expect(banner()).not.toBeNull();
            expect(saveButton()).not.toHaveTextContent('common.loading');
        });
        expect(changePassword).toHaveBeenCalledTimes(1);
        return mounted;
    }

    /** What the banner says, and nothing else. */
    const shown = () => banner()!.textContent?.trim() ?? '';

    // red until A8b (C11)
    it("words the limit's 429 as settings.tooManyPasswordAttempts, never as the server's sentence", async () => {
        await submitRefused(limitRefusal());

        expect(shown(), 'the key of the limit, alone').toBe(LIMIT_KEY);
        expect(shown(), "nothing of the server's English").not.toContain(LIMIT_MESSAGE);
    });

    // guard
    it('keeps the three fields as typed and usable after it, with no success state and no toast', async () => {
        toasts.clear();
        const {close, success} = await submitRefused(limitRefusal());

        expect(screen.getByTestId('password-current')).toHaveValue(OLD_PASSWORD);
        expect(screen.getByTestId('password-new')).toHaveValue(GOOD_PASSWORD);
        expect(screen.getByTestId('password-confirm')).toHaveValue(GOOD_PASSWORD);
        for (const testId of ['password-current', 'password-new', 'password-confirm']) expect(screen.getByTestId(testId), `${testId}: usable`).toBeEnabled();
        // No success state: neither its confirmation, nor the Save it locks, nor the two events it ends with.
        expect(screen.queryByText('settings.passwordChanged')).toBeNull();
        expect(saveButton()).toBeEnabled();
        expect(success).not.toHaveBeenCalled();
        expect(close).not.toHaveBeenCalled();
        expect(toasts.items, 'the refusal is told inline only').toEqual([]);
    });

    // guard
    it.each([
        ['a 429 with another error_code', () => answered(429, {detail: {error_code: 'RATE_LIMITED', message: 'Slow down: rate limited'}}), 'Slow down: rate limited'],
        ['a 429 whose detail is a sentence', () => answered(429, {detail: 'Too many requests'}), 'Too many requests'],
        ['a 429 from a proxy, its own page for a body', () => answered(429, '<html><body><h1>429 Too Many Requests</h1></body></html>'), 'Request failed with status code 429'],
        ['the code TOO_MANY_ATTEMPTS on a 400', () => answered(400, {detail: {error_code: 'TOO_MANY_ATTEMPTS', message: LIMIT_MESSAGE}}), LIMIT_MESSAGE],
    ])("%s keeps today's fallback: never the new key", async (_label, failure, fallback) => {
        await submitRefused(failure());

        expect(shown()).not.toContain(LIMIT_KEY);
        expect(shown()).toBe(fallback);
    });
});
