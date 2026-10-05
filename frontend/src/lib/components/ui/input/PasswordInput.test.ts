// @vitest-environment jsdom
/**
 * PasswordInput — component test (Vitest + jsdom).
 *
 * The password field behind every credential form in the app — login,
 * registration, change password — plus the eye button that shows the secret as
 * plain text. It is a UI primitive: props in, one `<input>` out, which is
 * exactly what a component test is for.
 *
 * Why it has a test now (developer note, 30/09). Chrome's password manager
 * offered the saved credentials on the login password field only, never on the
 * username. It reads a form through each field's `autocomplete` token together
 * with its `name`, its `id` and its label, and this component gave it little to
 * read: there was no `name` prop at all, and `{id}` with its default `''`
 * printed `id=""` on every caller that passed no id — invalid HTML (an id needs
 * at least one character), a target no `<label for>` can point at, and noise for
 * any parser that keys fields by id. `LoginCard.test.ts` tells the symptom in
 * full.
 *
 * Decision D2 (30/09) aligns the three forms, and this is the part that lives in
 * the primitive:
 *   - a `name` prop; `id` and `name` rendered only when non-empty, so an unnamed
 *     field carries no attribute at all rather than an empty one;
 *   - `autocapitalize="none"` and `spellcheck="false"` on the input. While the
 *     field is `type="password"` browsers already leave it alone; once the eye
 *     turns it into `type="text"` they stop doing so — a phone keyboard
 *     capitalises the first letter of the secret, and an enhanced spell-checker
 *     sends what it checks to a remote service (the 2022 "spell-jacking" reports
 *     were about precisely this show-password case). So the attributes are
 *     asserted again after the toggle, which is when they matter.
 *
 * The eye button is found by role, as the component's only button: its `title`
 * is an English sentence, and a test does not select on user-facing text.
 */
import {afterEach, describe, expect, it} from 'vitest';
import {cleanup, fireEvent, render, screen, within} from '$test/component';
import PasswordInput from './PasswordInput.svelte';

const TEST_ID = 'password-under-test';

function setup(props: Record<string, unknown> = {}) {
    const utils = render(PasswordInput, {testId: TEST_ID, ...props});
    return {input: screen.getByTestId(TEST_ID) as HTMLInputElement, ...utils};
}

/**
 * The named attributes of the input as a single object, `null` where absent,
 * so a red shows every mismatch in one diff instead of stopping at the first.
 */
function attributes(el: Element, names: readonly string[]): Record<string, string | null> {
    return Object.fromEntries(names.map((name) => [name, el.getAttribute(name)]));
}

afterEach(cleanup);

describe('PasswordInput — the attributes a form parser reads', () => {
    it('renders neither an id nor a name when it is given none', () => {
        // `null` means *absent*. An empty `id=""` is the defect: it is present,
        // it is invalid, and it names nothing.
        const {input} = setup();

        expect(attributes(input, ['id', 'name'])).toEqual({id: null, name: null});
    });

    it('renders the id, the name and the autocomplete token it is given', () => {
        const {input} = setup({id: 'account-password', name: 'password', autocomplete: 'new-password'});

        expect(attributes(input, ['id', 'name', 'autocomplete'])).toEqual({id: 'account-password', name: 'password', autocomplete: 'new-password'});
    });
});

describe('PasswordInput — keeping the keyboard out of the secret', () => {
    it('turns off autocapitalisation and spell-checking', () => {
        const {input} = setup();

        expect(input).toHaveAttribute('type', 'password');
        expect(attributes(input, ['autocapitalize', 'spellcheck'])).toEqual({autocapitalize: 'none', spellcheck: 'false'});
    });

    it('keeps both off once the eye shows the password as plain text', async () => {
        const {input, container} = setup();

        await fireEvent.click(within(container).getByRole('button'));

        // The barrier: prove the field really turned into text, or the next
        // assertion would only re-check the masked field it started as.
        expect(input).toHaveAttribute('type', 'text');
        expect(attributes(input, ['autocapitalize', 'spellcheck'])).toEqual({autocapitalize: 'none', spellcheck: 'false'});
    });
});
