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
 * label assertions name keys, stable in EN/IT/FR/ES, never a sentence.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, render, screen} from '$test/component';

// The identity translator: components render i18n keys verbatim, so the tests
// can name the text that was chosen without naming any one language.
vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
// The auth store at rest — nothing loading, no error — so the form renders as a
// user first sees it. Signing in is not the subject here: `login` only has to exist.
vi.mock('$lib/stores/app/auth', () => ({
    auth: {login: vi.fn()},
    authError: readable(null),
    isAuthLoading: readable(false),
}));
vi.mock('$app/navigation', () => ({goto: vi.fn()}));

import LoginCard from './LoginCard.svelte';

/** Mounts the card and returns the element everything it rendered lives in. */
function mount(): HTMLElement {
    return render(LoginCard).container;
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

afterEach(cleanup);

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
