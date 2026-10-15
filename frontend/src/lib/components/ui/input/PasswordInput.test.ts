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
 * The eye button is found by role, as the component's only button. Its name is
 * a catalogue key drawn through the translator (K-17, below), so where the name
 * is the subject the cases read it as `⟦key⟧`, the mark of the translator this
 * file installs, never as a sentence in one language.
 *
 * The decorative icon (workstream T, step T-2: the designer's round 1 puts a
 * lock inside the password fields of the credential forms). The optional `icon`
 * prop draws the component it is given — a lucide icon — on the left inside the
 * field. It is decoration: `aria-hidden="true"`, so the field's `<label for>`
 * stays its only name, and it is no second button beside the eye. Its test id is
 * derived from the field's, `${testId}-icon`, and like `id` and `name` it is not
 * printed at all when there is nothing to derive it from. Its colour and the
 * input's left padding are classes, which these tests never read: the colours
 * are `e2e/layout/theme-roles.spec.ts`'s, in a real browser.
 *
 * The eye button for a keyboard and a screen reader (backlog 38, item K-17;
 * plan A3). It showed a hard-coded English `title` — "Show password" / "Hide
 * password" in every language — had no `aria-label`, and `tabindex="-1"` took
 * it out of the tab order, so a keyboard user could not reveal what they typed
 * at all. The approved contract:
 *   - its accessible name is an `aria-label`, and its `title` says the same:
 *     `$_('auth.showPassword')` while the field is masked (`type="password"`),
 *     `$_('auth.hidePassword')` while it shows the text (`type="text"`). The
 *     name says what pressing it does, as in GOV.UK's show-password pattern;
 *   - no `aria-pressed`: a toggle whose name changes must not also report a
 *     pressed state, or a screen reader announces both and contradicts itself
 *     (WAI-ARIA APG, Button pattern). This corrects the plan's §4.11, which had
 *     asked for it; the case is green today on purpose, as a guard;
 *   - in the tab order: no `tabindex` attribute at all;
 *   - unchanged: `type="button"` (it must never submit the form around it), it
 *     is disabled with the field, the `icon` prop, and the keyboard attributes
 *     after the toggle (the cases above).
 * The English sentences are the words of the old title, so an English reader
 * sees no change; Italian, French and Spanish are the translator's, and only
 * their presence is asserted, read from the four generated catalogues as in
 * `stores/app/auth.test.ts`. The component now reads `$lib/i18n`, which this
 * file mocks with the marking translator; the other tests that mount it
 * (`LoginCard`, `RegisterCard`, `PasswordChangeModal`, `ProfileTab`) already
 * mock `_` as a store.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {writable} from 'svelte/store';
import {Lock} from 'lucide-svelte';
import type {SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

// The translator the component reads, as a lazy `subscribe`: the factory runs
// while the component is being imported, before `translator` below exists, so
// it must not touch the store until the component subscribes to it (the
// pattern of `LoginCard.test.ts`).
vi.mock('$lib/i18n', () => ({_: {subscribe: (run: (value: unknown) => void) => translator.subscribe(run)}}));

import PasswordInput from './PasswordInput.svelte';

/** What the marking translator draws for a key: proof the key went through `$_`. */
const marked = (key: string): string => `⟦${key}⟧`;
/** The translator the component reads: the marking one, unless a case swaps it. */
const translator = writable<(key: string) => string>(marked);

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

/** The icons the field draws outside its eye button: the decorative one, when it is given one. */
function iconsBesideTheEye(container: HTMLElement): SVGSVGElement[] {
    return Array.from(container.querySelectorAll('svg')).filter((svg) => svg.closest('button') === null);
}

afterEach(cleanup);
// Back to the marking translator, for whichever case comes next.
afterEach(() => {
    translator.set(marked);
});

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

describe('PasswordInput — the decorative icon inside the field', () => {
    it('draws no icon without the prop', () => {
        const {container} = setup();

        // The barrier: the eye draws its own svg, so an icon that is absent here
        // was not asked for — not lost by an environment that renders no svg.
        expect(within(container).getByRole('button').querySelector('svg')).not.toBeNull();
        expect(screen.queryByTestId(`${TEST_ID}-icon`)).toBeNull();
        expect(iconsBesideTheEye(container)).toEqual([]);
    });

    it('draws the icon it is given inside the field, hidden from assistive technology', () => {
        const {container, input} = setup({icon: Lock});
        const icon = screen.getByTestId(`${TEST_ID}-icon`);

        expect(icon.tagName.toLowerCase()).toBe('svg');
        expect(icon).toHaveAttribute('aria-hidden', 'true');
        // Inside the field: the positioned wrapper the input sits in, not the
        // eye button, which draws its own svg.
        expect(icon.parentElement).toBe(input.parentElement);
        const beside = iconsBesideTheEye(container);
        expect(beside).toHaveLength(1);
        expect(beside[0]).toBe(icon);
    });

    it('prints no test id on the icon when the field has none', () => {
        // `null` means *absent*: neither `data-testid=""` nor `"-icon"`, the
        // same rule as `id` and `name` above.
        const {container} = render(PasswordInput, {icon: Lock});
        const icons = iconsBesideTheEye(container);

        expect(icons, 'premise: the icon is drawn').toHaveLength(1);
        expect(icons[0]).toHaveAttribute('aria-hidden', 'true');
        expect(icons[0].getAttribute('data-testid')).toBeNull();
        expect(Array.from(container.querySelectorAll('[data-testid]'), (el) => el.getAttribute('data-testid'))).toEqual([]);
    });

    it('stays out of the way of the eye: still one button, still showing the password', async () => {
        // `getByRole('button')` throws on a second button: an icon drawn as a
        // control would be one more tab stop with no name.
        const {input, container} = setup({icon: Lock});

        await fireEvent.click(within(container).getByRole('button'));

        expect(input).toHaveAttribute('type', 'text');
        expect(attributes(input, ['autocapitalize', 'spellcheck'])).toEqual({autocapitalize: 'none', spellcheck: 'false'});
    });
});

describe('PasswordInput — the eye button, for a keyboard and a screen reader (K-17)', () => {
    /** The eye: the component's only button. */
    function eye(container: HTMLElement): HTMLButtonElement {
        return within(container).getByRole('button') as HTMLButtonElement;
    }

    /** The two attributes that name the eye, `null` where absent, read together so a red shows both. */
    function naming(container: HTMLElement): Record<string, string | null> {
        return attributes(eye(container), ['aria-label', 'title']);
    }

    it('is named after what pressing it does, «show», while the field is masked: aria-label and title alike', () => {
        const {input, container} = setup();
        expect(input, 'premise: the field starts masked').toHaveAttribute('type', 'password');

        expect(naming(container), 'the name is $_(auth.showPassword), in aria-label, and the title says the same').toEqual({'aria-label': marked('auth.showPassword'), title: marked('auth.showPassword')});
        expect(within(container).queryByRole('button', {name: marked('auth.showPassword')}), 'a screen reader announces it by that name').toBe(eye(container));
    });

    it('is renamed «hide» once the field shows the text, and «show» again after a second press', async () => {
        const {input, container} = setup();

        await fireEvent.click(eye(container));
        expect(input, 'premise: the first press shows the text').toHaveAttribute('type', 'text');
        expect(naming(container), 'while the text shows, the name is $_(auth.hidePassword)').toEqual({'aria-label': marked('auth.hidePassword'), title: marked('auth.hidePassword')});

        await fireEvent.click(eye(container));
        expect(input, 'premise: the second press masks it again').toHaveAttribute('type', 'password');
        expect(naming(container), 'masked again, the name is $_(auth.showPassword) again').toEqual({'aria-label': marked('auth.showPassword'), title: marked('auth.showPassword')});
    });

    it('guard — reports no pressed state in either position: its name already says what pressing it does', async () => {
        const {input, container} = setup();
        expect(eye(container).getAttribute('aria-pressed'), 'masked: no aria-pressed').toBeNull();

        await fireEvent.click(eye(container));

        expect(input, 'premise: the press showed the text').toHaveAttribute('type', 'text');
        expect(eye(container).getAttribute('aria-pressed'), 'shown: no aria-pressed either — a changing name and a pressed state would contradict each other').toBeNull();
    });

    it('is in the tab order: it carries no tabindex at all', () => {
        const {container} = setup();

        expect(eye(container).getAttribute('tabindex'), 'tabindex="-1" took the eye out of the keyboard’s reach').toBeNull();
        expect(eye(container).tabIndex, 'a button without tabindex is reached by Tab in document order').toBe(0);
    });

    it('stays a type="button", never a submit, and is disabled with the field', () => {
        const {input, container} = setup({disabled: true});

        expect(eye(container), 'a press must never submit the form around it').toHaveAttribute('type', 'button');
        expect(input, 'premise: the field is disabled').toBeDisabled();
        expect(eye(container), 'the eye follows the field').toBeDisabled();
    });

    it('is named in the language of the moment: the name follows a language change', async () => {
        translator.set((key) => `first:${key}`);
        const {container} = setup();
        expect(eye(container).getAttribute('aria-label'), 'named through the translator of the moment').toBe('first:auth.showPassword');

        translator.set((key) => `second:${key}`);
        await tick();

        expect(naming(container), 'the name is translated when it is drawn, so it follows the language').toEqual({'aria-label': 'second:auth.showPassword', title: 'second:auth.showPassword'});
    });
});

/**
 * The eye's two names — a sentence in all four catalogues, the English words
 * those of the old title. A key a catalogue lacks is drawn as the key itself in
 * that language, and here it would be the only name a screen reader has.
 */
describe('PasswordInput — the eye’s names are sentences in all four catalogues', () => {
    const ENGLISH: Record<'auth.showPassword' | 'auth.hidePassword', string> = {
        'auth.showPassword': 'Show password',
        'auth.hidePassword': 'Hide password',
    };
    const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

    /** The leaf behind a dotted key, read from the catalogue file itself. */
    function leaf(catalogue: unknown, key: string): unknown {
        return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    }

    it.each(Object.keys(ENGLISH))('%s is a sentence in en, it, fr and es', (key) => {
        const missing = Object.entries(CATALOGUES)
            .filter(([, catalogue]) => {
                const sentence = leaf(catalogue, key);
                return typeof sentence !== 'string' || sentence.trim() === '';
            })
            .map(([locale]) => locale);

        expect(missing, `${key} is a sentence in every catalogue: a key one of them lacks is drawn as the key itself in that language`).toEqual([]);
    });

    it.each(Object.entries(ENGLISH))('%s keeps the English words of the old title: "%s"', (key, english) => {
        expect(leaf(en, key), `the English catalogue words ${key} as the hard-coded title did: nothing changes for an English reader`).toBe(english);
    });
});
