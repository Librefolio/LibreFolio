// @vitest-environment jsdom
/**
 * ResetPasswordCard — the form a password-reset link opens (accounts lot A5b).
 *
 * An administrator creates a reset link for an account (A5a: `POST /api/v1/users/{user_id}/password-reset-link`); its
 * holder opens `/reset-password#token=…` (the token in the fragment, out of the server's logs), the page checks the
 * token, and for a valid one shows this card: which account, a new password, its confirmation. The card receives the
 * token as a prop and spends the link with `POST /api/v1/auth/password-reset {token, new_password}`.
 *
 * The contract (plan A5b.1):
 *   - props `token`, `username` (the account the link resets, `null` when the server named none), `ondone`, `oninvalid`;
 *   - test ids: the root `reset-password-modal`; `reset-password-account`, showing the username when there is one; the
 *     two `PasswordInput`s `reset-password-new` and `reset-password-confirm` (the input carries the test id);
 *     `reset-password-submit`; the error area `reset-password-error`;
 *   - the rules are the app's, read from `PasswordStrength` through its new bindable `valid` — no fifth copy of them
 *     (A-6): a password that breaks one, or a confirmation that differs, is refused with an error and never sent;
 *   - otherwise `{token, new_password}` goes to `reset_password_with_link_api_v1_auth_password_reset_post`, the password
 *     exactly as typed;
 *   - success → `ondone()`; a 400 `TOKEN_INVALID` (the link was spent, expired or revoked in the meantime) →
 *     `oninvalid()`, and the page shows the link as unknown; any other failure → an error in the card:
 *     `auth.validation.passwordTooWeak` for a 422 (the server's schema refused the password),
 *     `auth.resetPassword.failed` for everything else;
 *   - for password managers, as `PasswordChangeModal` does it (decision D2): with a `username`, the form holds
 *     `<input type="text" name="username" autocomplete="username" hidden readonly>` carrying it, so the new password is
 *     filed under that account; with `null`, no such input. Both password fields are `autocomplete="new-password"`.
 *
 * Driven like `RegisterCard.test.ts`: the fields are typed into with `input` events, the form submitted from its button.
 * The five rules are each broken once, as there: the card must refuse exactly what the meter under the field marks.
 *
 * On not asserting translated text. `$lib/i18n` keeps its real exports with the translator replaced by the identity, so
 * a message renders as its key: every error is asserted by key, stable in EN/IT/FR/ES. The username is a value this
 * test passes in.
 *
 * Written red-first, before `ResetPasswordCard.svelte` exists: the file fails on the import until it does.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

const mocks = vi.hoisted(() => ({
    reset: vi.fn().mockName('zodiosApi.reset_password_with_link_api_v1_auth_password_reset_post'),
}));

vi.mock('$lib/api', () => ({zodiosApi: {reset_password_with_link_api_v1_auth_password_reset_post: mocks.reset}}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const identity = readable((key: string) => key);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: identity, t: identity};
});

import ResetPasswordCard from './ResetPasswordCard.svelte';

/** Satisfies all five rules: length, upper, lower, digit, special. */
const GOOD_PASSWORD = 'Str0ng!pass';
const TOKEN = 'rst-token-0123';

interface Mounted {
    ondone: ReturnType<typeof vi.fn>;
    oninvalid: ReturnType<typeof vi.fn>;
}

function mount(props: {username?: string | null} = {}): Mounted {
    const ondone = vi.fn().mockName('ondone');
    const oninvalid = vi.fn().mockName('oninvalid');
    render(ResetPasswordCard, {props: {token: TOKEN, username: 'alice', ondone, oninvalid, ...props}});
    return {ondone, oninvalid};
}

async function fill(testId: string, value: string): Promise<void> {
    await fireEvent.input(screen.getByTestId(testId), {target: {value}});
}

/** Types a new password and its confirmation (the same, unless told otherwise). */
async function fillPasswords(password: string, confirmation = password): Promise<void> {
    await fill('reset-password-new', password);
    await fill('reset-password-confirm', confirmation);
}

async function submit(): Promise<void> {
    await fireEvent.click(screen.getByTestId('reset-password-submit'));
}

/**
 * What the error area says, `''` when it says nothing: absent, or present and empty — the card may keep the area
 * mounted, so "no error" is read from its text, never from its presence.
 */
function errorShown(): string {
    return screen.queryByTestId('reset-password-error')?.textContent?.trim() ?? '';
}

/** An axios-shaped refusal carrying `response.status` and `response.data.detail`. */
function refusal(status: number, detail: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {
        isAxiosError: true,
        response: {status, data: {detail}},
    });
}

beforeEach(() => {
    mocks.reset.mockReset();
    mocks.reset.mockResolvedValue({message: 'Password reset successfully'});
});

afterEach(cleanup);

describe('ResetPasswordCard — the form', () => {
    it('is one card holding the two password fields and the submit button', () => {
        mount();
        const card = screen.getByTestId('reset-password-modal');

        expect(within(card).getByTestId('reset-password-new')).toHaveAttribute('type', 'password');
        expect(within(card).getByTestId('reset-password-confirm')).toHaveAttribute('type', 'password');
        expect(within(card).getByTestId('reset-password-submit')).toBeInTheDocument();
    });

    it('says which account the link resets', () => {
        mount({username: 'alice'});

        expect(within(screen.getByTestId('reset-password-modal')).getByTestId('reset-password-account')).toHaveTextContent('alice');
    });

    it('names no account when the server named none', () => {
        mount({username: null});

        expect(screen.getByTestId('reset-password-modal'), 'premise: the card is drawn').toBeInTheDocument();
        expect(screen.queryByTestId('reset-password-account')).toBeNull();
    });

    it('shows the strength meter of the app under the new password', async () => {
        mount();

        await fill('reset-password-new', 'abc');

        expect(within(screen.getByTestId('reset-password-modal')).getByTestId('password-strength-meter')).toBeInTheDocument();
    });

    it('shows no error before anything was tried', () => {
        mount();

        expect(errorShown()).toBe('');
    });
});

describe('ResetPasswordCard — the rules keep a bad password off the wire', () => {
    it.each([
        ['too short', 'Sh0rt!'],
        ['no uppercase', 'str0ng!pass'],
        ['no lowercase', 'STR0NG!PASS'],
        ['no digit', 'Strong!pass'],
        ['no special character', 'Str0ngpass'],
    ])('refuses a password with %s, and says so', async (_label, password) => {
        const {ondone, oninvalid} = mount();
        await fillPasswords(password);

        await submit();

        await waitFor(() => expect(errorShown(), 'a refusal the user can read, in reset-password-error').not.toBe(''));
        expect(mocks.reset).not.toHaveBeenCalled();
        expect(ondone).not.toHaveBeenCalled();
        expect(oninvalid).not.toHaveBeenCalled();
    });

    it('refuses an empty form', async () => {
        mount();

        await submit();

        await waitFor(() => expect(errorShown()).not.toBe(''));
        expect(mocks.reset).not.toHaveBeenCalled();
    });

    it('refuses when the confirmation differs', async () => {
        mount();
        await fillPasswords(GOOD_PASSWORD, `${GOOD_PASSWORD}x`);

        await submit();

        await waitFor(() => expect(errorShown()).not.toBe(''));
        expect(mocks.reset).not.toHaveBeenCalled();
    });
});

describe('ResetPasswordCard — what reaches the server', () => {
    it('sends the token of the link and the new password, nothing else', async () => {
        mount();
        await fillPasswords(GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(mocks.reset).toHaveBeenCalledTimes(1));
        expect(mocks.reset.mock.calls[0][0]).toStrictEqual({token: TOKEN, new_password: GOOD_PASSWORD});
    });

    it('sends the password exactly as typed, spaces included', async () => {
        // Trimming it would lock the user out with a password they never chose.
        const spaced = ` ${GOOD_PASSWORD} `;
        mount();
        await fillPasswords(spaced);

        await submit();

        await waitFor(() => expect(mocks.reset).toHaveBeenCalledTimes(1));
        expect(mocks.reset.mock.calls[0][0]).toMatchObject({new_password: spaced});
    });
});

describe('ResetPasswordCard — after the server answers', () => {
    it('hands back to the page once the password is changed', async () => {
        const {ondone, oninvalid} = mount();
        await fillPasswords(GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(ondone).toHaveBeenCalledTimes(1));
        expect(oninvalid).not.toHaveBeenCalled();
        expect(errorShown()).toBe('');
    });

    it('tells the page the link is no longer valid on a 400 TOKEN_INVALID', async () => {
        mocks.reset.mockRejectedValue(refusal(400, {error_code: 'TOKEN_INVALID', message: 'This link is not valid'}));
        const {ondone, oninvalid} = mount();
        await fillPasswords(GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(oninvalid).toHaveBeenCalledTimes(1));
        expect(ondone).not.toHaveBeenCalled();
    });

    it.each([
        ['a 422: the server refused the password', refusal(422, [{type: 'string_too_short', loc: ['body', 'new_password'], msg: 'String should have at least 8 characters'}]), 'auth.validation.passwordTooWeak'],
        ['a 400 with another code', refusal(400, {error_code: 'SOMETHING_ELSE', message: 'An English sentence'}), 'auth.resetPassword.failed'],
        ['a 500', refusal(500, 'Internal Server Error'), 'auth.resetPassword.failed'],
        ['a request that never reached the server', new Error('Network Error'), 'auth.resetPassword.failed'],
    ])('shows %s as %s, and stays on the form', async (_label, failure, key) => {
        mocks.reset.mockRejectedValue(failure);
        const {ondone, oninvalid} = mount();
        await fillPasswords(GOOD_PASSWORD);

        await submit();

        await waitFor(() => expect(errorShown()).toContain(key));
        expect(ondone).not.toHaveBeenCalled();
        expect(oninvalid, 'only TOKEN_INVALID means the link is gone').not.toHaveBeenCalled();
        expect(screen.getByTestId('reset-password-new'), 'the form stays, so the user can try again').toBeInTheDocument();
    });
});

describe('ResetPasswordCard — the markup a password manager reads', () => {
    // As in `PasswordChangeModal` (decision D2): a password manager files a new password under the username of the same
    // form, so the card carries the account the link resets in a field of its own, hidden and read-only, beside the two
    // new passwords. Without an account there is nothing to file it under, and no such field.

    /** The card's `<form>`, reached through the new-password field: it has no test id. */
    function theForm(): HTMLFormElement {
        const form = (screen.getByTestId('reset-password-new') as HTMLInputElement).form;
        if (!form) throw new Error('the new-password field is not inside a form');
        return form;
    }

    /** Every field of the card that declares itself a username. */
    function usernameFields(): HTMLInputElement[] {
        return Array.from(screen.getByTestId('reset-password-modal').querySelectorAll<HTMLInputElement>('input[autocomplete="username"]'));
    }

    /**
     * The named attributes of one element as a single object, `null` where
     * absent, so a red shows every mismatch in one diff instead of the first.
     */
    function attributes(el: Element, names: readonly string[]): Record<string, string | null> {
        return Object.fromEntries(names.map((name) => [name, el.getAttribute(name)]));
    }

    it('hides a read-only username field carrying the account, in the form of the new passwords', () => {
        mount({username: 'alice'});
        const fields = usernameFields();

        expect(fields, 'fields with autocomplete="username" in the card').toHaveLength(1);
        const [field] = fields;
        // The modal's technique: `type="text"`, not `type="hidden"` (a password manager reads text-like inputs), kept off
        // screen and out of the tab order by `hidden`, and out of the user's hands by `readonly`.
        expect(attributes(field, ['type', 'name', 'autocomplete'])).toEqual({type: 'text', name: 'username', autocomplete: 'username'});
        expect(field).toHaveValue('alice');
        expect(field).toHaveAttribute('hidden');
        expect(field).not.toBeVisible();
        expect(field).toHaveAttribute('readonly');
        expect(field.form, 'the form of the new passwords: a manager pairs a username with the passwords of its form').toBe(theForm());
    });

    it('has no username field when the server named no account', () => {
        mount({username: null});

        expect(theForm(), 'premise: the form and its password fields are drawn').toBeInTheDocument();
        expect(usernameFields()).toEqual([]);
    });

    it.each(['reset-password-new', 'reset-password-confirm'])('marks %s as a new password: type password, autocomplete="new-password", in the form', (testId) => {
        mount();
        const field = screen.getByTestId(testId) as HTMLInputElement;

        expect(attributes(field, ['type', 'autocomplete'])).toEqual({type: 'password', autocomplete: 'new-password'});
        expect(field.form).toBe(theForm());
    });
});
