// @vitest-environment jsdom
/**
 * PasswordStrength — component test (Vitest + jsdom).
 *
 * The meter under the new-password field of the registration form: a strength
 * bar scored by zxcvbn, and a checklist of the five rules `RegisterCard` itself
 * enforces before it sends anything (length, upper case, lower case, a digit, a
 * special character). It is a primitive — a password in, markup out — so it is
 * pinned here, in milliseconds, rather than through the sign-up page.
 *
 * What it publishes, and what this file holds it to (workstream T, step T-2):
 *   - nothing at all for an empty password: no bar and no checklist under a field
 *     the user has not touched;
 *   - the score on the bar, `data-strength` = zxcvbn's 0–4, so that the level has
 *     a handle that is not a colour (the bar's colours went to three states,
 *     decision D-T13: 0–1 danger, 2 warning, 3–4 success — never asserted here,
 *     jsdom loads no stylesheet);
 *   - the checklist, `password-requirements`, only with `showRules`; one
 *     `password-rule-<key>` per rule, its state in `data-passed`;
 *   - a check for a rule that holds and a cross for one that does not: the state
 *     is told by the shape of the glyph, never by its colour alone.
 *
 * Which glyph a rule draws is read from the class token lucide-svelte writes on
 * every icon it renders: `lucide-<name>` (dist/Icon.svelte merges `lucide-icon`,
 * `lucide` and `lucide-${name}` into the svg's class). That token is the
 * library's name of the glyph, not a style, and it is the only class this file
 * reads; the Tailwind colour classes beside it are never looked at. A name alone
 * would still let a check and a cross be one shape painted twice, so the
 * geometry is compared as well: the svg's children, which differ between the two
 * glyphs whatever their colour — what a monochrome screen still shows.
 *
 * The passwords are chosen so that no answer is a coin toss. Two of them split
 * the five rules between them, each rule holding in exactly one, so every rule
 * is seen in both states. The scores are zxcvbn's own on the dictionaries the
 * component loads: 'a' scores 0 (about 10¹ guesses) and the passphrase 4 (about
 * 10²⁴, fourteen orders past the 10¹⁰ that 4 needs).
 *
 * On not asserting translated text. `$lib/i18n` is mocked with an identity
 * translator, as in `RegisterCard.test.ts`, so a label renders as its key; the
 * strength label is asserted by key, stable in EN/IT/FR/ES.
 *
 * What it cannot see: colours. The checklist's background and the bar's three
 * states are `e2e/layout/theme-roles.spec.ts`'s, in a real browser. And the
 * bar's filled segments: they differ from the empty ones by a colour class and
 * nothing else, so their count has no handle — the label is the level's
 * non-colour channel.
 *
 * The last describe pins the one functional addition of accounts lot A5b: a
 * bindable `valid`, true exactly when every rule of the checklist holds. The
 * new password-reset card reads the app's rules through it (`bind:valid`)
 * instead of keeping a fifth copy of them (A-6). A legacy prop is bound from
 * here the way Svelte binds it: the props object carries an accessor, and the
 * component calls its setter when it writes the prop. Each case starts the
 * bound value at the opposite of what it expects, so the assertion proves a
 * write by the component, not a value that was never touched.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`,
 * action `component-unit`).
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, render, screen, within} from '$test/component';

// The identity translator: components render i18n keys verbatim, so the tests
// can name the label that was chosen without naming any one language.
vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));

import PasswordStrength from './PasswordStrength.svelte';

/** The five rules, in the order the checklist lists them. */
const RULE_KEYS = ['minLength', 'hasUppercase', 'hasLowercase', 'hasNumber', 'hasSpecial'] as const;
type RuleKey = (typeof RULE_KEYS)[number];

/** Nine characters, lower case and a digit: length, lower case and digit hold; upper case and special do not. */
const THREE_RULES = 'abcdefgh1';
/** Three characters, upper case and a special one: exactly the two rules THREE_RULES misses. */
const TWO_RULES = 'AB!';
/** zxcvbn's score 0: about 10¹ guesses. */
const WEAKEST = 'a';
/** zxcvbn's score 4: about 10²⁴ guesses on the component's dictionaries. */
const STRONGEST = 'vivid-otter-quartz-lantern-91';

/** Every rule the checklist draws. */
function rulesDrawn(): HTMLElement[] {
    return screen.queryAllByTestId(/^password-rule-/);
}

const keyOf = (rule: HTMLElement): string => (rule.getAttribute('data-testid') ?? '').replace(/^password-rule-/, '');

/** `{key: data-passed}` for every rule drawn: one object, so a red shows every rule at once. */
function rulesPassed(): Record<string, string | null> {
    return Object.fromEntries(rulesDrawn().map((rule) => [keyOf(rule), rule.getAttribute('data-passed')]));
}

/** The one icon a rule draws. */
function iconOf(rule: HTMLElement): SVGSVGElement {
    const icons = rule.querySelectorAll('svg');
    expect(icons, `${rule.getAttribute('data-testid')} draws one icon`).toHaveLength(1);
    return icons[0];
}

/** The glyph a rule draws, by lucide's name for it: `lucide-check` gives `check`. */
function glyphOf(rule: HTMLElement): string {
    const token = Array.from(iconOf(rule).classList).find((name) => name.startsWith('lucide-') && name !== 'lucide-icon');
    return token ? token.slice('lucide-'.length) : '(no lucide glyph)';
}

/** The expected `data-passed` of every rule, as the checklist prints it. */
const states = (passed: Record<RuleKey, boolean>): Record<string, string> => Object.fromEntries(RULE_KEYS.map((key) => [key, String(passed[key])]));

afterEach(cleanup);

describe('PasswordStrength — nothing under an empty field', () => {
    it('draws nothing for an empty password, and nothing again once the password is cleared', async () => {
        const {container, rerender} = render(PasswordStrength, {password: ''});
        expect(container.querySelector('*'), 'no element at all: no meter, no bar, no checklist').toBeNull();

        // The barrier: the same mount draws the meter as soon as there is a
        // password, so the emptiness above is the component's answer.
        await rerender({password: WEAKEST});
        expect(screen.getByTestId('password-strength-meter')).toBeInTheDocument();

        await rerender({password: ''});
        expect(container.querySelector('*'), 'a cleared field takes the meter away').toBeNull();
    });
});

describe('PasswordStrength — the rules checklist', () => {
    it.each([
        {password: THREE_RULES, passed: states({minLength: true, hasUppercase: false, hasLowercase: true, hasNumber: true, hasSpecial: false})},
        {password: TWO_RULES, passed: states({minLength: false, hasUppercase: true, hasLowercase: false, hasNumber: false, hasSpecial: true})},
    ])('marks in data-passed exactly the rules "$password" meets', ({password, passed}) => {
        render(PasswordStrength, {password});

        expect(screen.getByTestId('password-requirements')).toBeInTheDocument();
        expect(rulesPassed()).toEqual(passed);
    });

    it('draws a check for a rule that holds and a cross for one that does not: the shape tells them apart, not only the colour', () => {
        render(PasswordStrength, {password: THREE_RULES});
        const rules = rulesDrawn();

        expect(Object.fromEntries(rules.map((rule) => [keyOf(rule), glyphOf(rule)]))).toEqual({minLength: 'check', hasUppercase: 'x', hasLowercase: 'check', hasNumber: 'check', hasSpecial: 'x'});

        const shapes = (state: string): string[] => rules.filter((rule) => rule.getAttribute('data-passed') === state).map((rule) => iconOf(rule).innerHTML);
        const holds = shapes('true');
        const fails = shapes('false');
        expect(new Set(holds).size, 'every rule that holds draws the same glyph').toBe(1);
        expect(new Set(fails).size, 'every rule that fails draws the same glyph').toBe(1);
        expect(holds[0], 'and the two glyphs differ in shape, whatever their colour classes').not.toBe(fails[0]);
    });

    it('leaves the checklist out with showRules: false, and keeps the strength', () => {
        render(PasswordStrength, {password: THREE_RULES, showRules: false});

        // The barrier: the meter is drawn, so the checklist is absent by choice.
        expect(screen.getByTestId('password-strength-bar')).toBeInTheDocument();
        expect(screen.queryByTestId('password-requirements')).toBeNull();
        expect(rulesDrawn()).toEqual([]);
    });
});

describe('PasswordStrength — the strength', () => {
    it('publishes the zxcvbn score in data-strength and names its level, and follows the password', async () => {
        const {rerender} = render(PasswordStrength, {password: WEAKEST});
        const meter = (): HTMLElement => screen.getByTestId('password-strength-meter');

        expect(screen.getByTestId('password-strength-bar')).toHaveAttribute('data-strength', '0');
        // The level in words: the channel that does not depend on colour.
        expect(within(meter()).getByText('auth.passwordStrength.veryWeak')).toBeInTheDocument();

        await rerender({password: STRONGEST});

        expect(screen.getByTestId('password-strength-bar')).toHaveAttribute('data-strength', '4');
        expect(within(meter()).getByText('auth.passwordStrength.veryStrong')).toBeInTheDocument();
    });
});

describe('PasswordStrength — valid, bindable: true exactly when every rule holds (A5b)', () => {
    /** All five rules: length, upper case, lower case, a digit, a special character. */
    const ALL_RULES = 'Str0ng!pass';

    /**
     * Mounts the meter with `valid` bound, as a parent's `bind:valid` binds a legacy prop: an accessor on the props
     * object, whose setter the component calls when it writes the prop. `bound.value` is what the parent holds; it
     * starts at `start`, the opposite of what the case expects.
     */
    function mountBound(password: string, start: boolean) {
        const bound = {value: start};
        const props = {
            password,
            get valid(): boolean {
                return bound.value;
            },
            set valid(next: boolean) {
                bound.value = next;
            },
        };
        const utils = render(PasswordStrength, {props});
        return {...utils, bound};
    }

    it('is true once all five rules hold', () => {
        const {bound} = mountBound(ALL_RULES, false);

        expect(rulesPassed(), 'premise: the checklist marks every rule as held').toEqual(states({minLength: true, hasUppercase: true, hasLowercase: true, hasNumber: true, hasSpecial: true}));
        expect(bound.value, 'valid, written by the meter').toBe(true);
    });

    it.each([
        ['an empty password', ''],
        ['three rules out of five', THREE_RULES],
        ['two rules out of five', TWO_RULES],
        ['one character', WEAKEST],
        // zxcvbn scores it 4, yet it has no capital: valid follows the rules, not the strength.
        ['a passphrase zxcvbn scores 4 but with no capital', STRONGEST],
    ])('is false for %s', (_label, password) => {
        const {bound} = mountBound(password, true);

        expect(bound.value, 'valid, written by the meter').toBe(false);
    });

    it('follows the password as it changes, both ways', async () => {
        const {bound, rerender} = mountBound(THREE_RULES, true);
        expect(bound.value, 'three rules out of five').toBe(false);

        await rerender({password: ALL_RULES});
        expect(bound.value, 'all five').toBe(true);

        await rerender({password: TWO_RULES});
        expect(bound.value, 'two out of five').toBe(false);
    });
});
