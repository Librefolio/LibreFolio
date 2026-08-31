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
 * Two behaviours recorded here are characterisations, not endorsements, and both
 * are called out in their own tests: the submit *event* bypasses `canSubmit`
 * entirely, and the Save button comes back to life during the 1500 ms victory
 * lap while the old password is still on screen.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {tick} from 'svelte';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

// The identity translator: components render i18n keys verbatim, so the tests
// can name the message that was chosen without naming any one language.
vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/api', () => ({zodiosApi: {change_password_api_v1_auth_change_password_post: vi.fn()}}));

import PasswordChangeModal from './PasswordChangeModal.svelte';
import {zodiosApi} from '$lib/api';

const changePassword = vi.mocked(zodiosApi.change_password_api_v1_auth_change_password_post);

/** Satisfies all five rules: length, upper, lower, digit, special. */
const GOOD_PASSWORD = 'Str0ng!pass';
/** A second one, equally valid, for "the new one differs from the old". */
const OLD_PASSWORD = 'Old3r!pass';

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

beforeEach(() => {
    changePassword.mockReset();
    changePassword.mockResolvedValue({message: 'Password changed successfully'} as never);
    // `trySave` logs every failure to the console by contract; the failure paths
    // below are deliberate, so the noise is suppressed rather than read.
    vi.spyOn(console, 'error').mockImplementation(() => {});
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

    it('empties every field on the way out, so nothing is left for the next open', async () => {
        vi.useFakeTimers();
        mount();
        await fillValid();

        await fireEvent.click(saveButton());
        await vi.advanceTimersByTimeAsync(1500);
        await tick();

        expect(screen.getByTestId('password-current')).toHaveValue('');
        expect(screen.getByTestId('password-new')).toHaveValue('');
        expect(screen.getByTestId('password-confirm')).toHaveValue('');
    });

    it('re-enables Save during the 1500 ms confirmation, with the stale password still loaded', async () => {
        // Characterisation of a real gap, not an endorsement.
        //
        // `handleSubmit` sets `isSubmitting = false` synchronously after the await,
        // then schedules the close 1500 ms later. For that second and a half the
        // dialog is fully interactive and all three fields still hold the values
        // that were just spent: `canSubmit` is true again, so the Save button is
        // enabled underneath the success message.
        //
        // A second click there sends `current_password` = the password that no
        // longer exists, and the server answers "Current password is incorrect" —
        // so the user, having just succeeded, is told their password is wrong. The
        // pending `setTimeout` still fires and closes the dialog on top of that
        // error, which is why it is easy to miss.
        //
        // The fix is one line (`if (isSubmitting || success) return;` in
        // `handleSubmit`, or keeping `isSubmitting` true until the timer runs).
        // When it lands, this test goes red and says exactly what changed.
        vi.useFakeTimers();
        mount();
        await fillValid();

        await fireEvent.click(saveButton());
        await vi.advanceTimersByTimeAsync(0);
        await tick();

        expect(screen.getByText('settings.passwordChanged')).toBeInTheDocument();
        expect(saveButton()).toBeEnabled();

        await fireEvent.click(saveButton());
        await vi.advanceTimersByTimeAsync(0);

        expect(changePassword).toHaveBeenCalledTimes(2);
        expect(changePassword).toHaveBeenLastCalledWith({current_password: OLD_PASSWORD, new_password: GOOD_PASSWORD});
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
