// @vitest-environment jsdom
/**
 * PasswordStrength — component test (Vitest + jsdom).
 *
 * The meter under every new-password field — the registration form, the
 * change-password dialog, a reset link: a strength bar scored by zxcvbn, and a
 * checklist of the password rules (by default the five of before: length, upper
 * case, lower case, a digit, a special character; since A6c, whatever the server
 * lists — see the last part of this header). It is a primitive — a password in,
 * markup out — so it is pinned here, in milliseconds, rather than through the
 * sign-up page.
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
 * strength label is asserted by key, stable in EN/IT/FR/ES. Since A6c the
 * translator also prints the ICU values a message is given, after the key —
 * `auth.passwordStrength.rules.minLength {"value":12}` — so the length the
 * min-length label names is read without reading any language.
 *
 * What it cannot see: colours. The checklist's background and the bar's three
 * states are `e2e/layout/theme-roles.spec.ts`'s, in a real browser. And the
 * bar's filled segments: they differ from the empty ones by a colour class and
 * nothing else, so their count has no handle — the label is the level's
 * non-colour channel.
 *
 * The describe on `valid` pins the one functional addition of accounts lot A5b: a
 * bindable `valid`, true exactly when every rule of the checklist holds. The
 * new password-reset card reads the app's rules through it (`bind:valid`)
 * instead of keeping a fifth copy of them (A-6). A legacy prop is bound from
 * here the way Svelte binds it: the props object carries an accessor, and the
 * component calls its setter when it writes the prop. Each case starts the
 * bound value at the opposite of what it expects, so the assertion proves a
 * write by the component, not a value that was never touched.
 *
 * Accounts lot A6c (decision 37) takes the rules out of the component. The
 * backend writes them once, applies them to every new password the API
 * receives, and exposes them in `GET /system/instance` as
 * `accounts.password_rules`, a list of `{code, value?}`;
 * `$lib/features/auth/passwordRules.ts` maps a code to the key the checklist has
 * always used (`min_length` → `minLength`, `digit` → `hasNumber`, …) and checks
 * it, with Unicode classes (`passwordRules.test.ts` pins both). What this file
 * holds the meter to:
 *   - its rules are `instanceConfig.config.accounts.password_rules` when the
 *     configuration carries them, and the five of before
 *     (`DEFAULT_PASSWORD_RULES`) until then — before the server answers, or
 *     with a backend older than A6c;
 *   - the checklist draws the rules this build knows, in the server's order,
 *     each still `password-rule-<key>` with its `data-passed`: the keys do not
 *     change, `e2e/layout/theme-roles.spec.ts` reads them;
 *   - a code it does not know draws no row and never makes `valid` false: the
 *     server checks it when the form is sent;
 *   - the min-length label takes the rule's length as the ICU `{value}`;
 *   - an answer that lands under a mounted meter changes the checklist, its
 *     label and `valid` in place, without a remount. The component is legacy
 *     (`$:`), and a `$:` statement does not track a runes field read through a
 *     module singleton (devWiki `problems/legacy-layout-gate-missed-runes-state`):
 *     the cases that change the answer after the mount are the ones that would
 *     catch a meter reading the rules once.
 *
 * The configuration is a fake with the real store's shape, as in
 * `LoginCard.test.ts`: enumerable getters over `$state` (`reactiveBox`), so a
 * change made by a test reaches the component the way a landed answer does. It
 * starts every test without `password_rules`, so every case above A6c runs on
 * the defaults, exactly as it did before.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`,
 * action `component-unit`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick, type ComponentProps} from 'svelte';
import {readable} from 'svelte/store';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, render, screen, within} from '$test/component';

// The instance configuration and the translator, hoisted: the factories below run while the component is being
// imported, before anything declared further down exists.
const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    /** What the store holds until the server answers (`DEFAULT_INSTANCE_CONFIG`), and what a backend older than A6c answers: no `password_rules`. */
    const BEFORE_ANSWER = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}} as InstanceConfig;
    type Values = Record<string, unknown>;
    /**
     * The identity translator, which also prints the ICU values a message is given: `$_('k')` renders `k`, and
     * `$_('k', {values: {value: 12}})` renders `k {"value":12}`. svelte-i18n also takes `$_({id, values})`: both print alike.
     */
    const translate = (id: string | {id: string; values?: Values}, options?: {values?: Values}): string => {
        const key = typeof id === 'string' ? id : id.id;
        const values = typeof id === 'string' ? options?.values : id.values;
        return values && Object.keys(values).length > 0 ? `${key} ${JSON.stringify(values)}` : key;
    };
    return {
        BEFORE_ANSWER,
        translate,
        instance: reactiveBox<{config: InstanceConfig; loaded: boolean}>({config: BEFORE_ANSWER, loaded: false}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
    };
});

// The identity translator: components render i18n keys verbatim, so the tests
// can name the label that was chosen without naming any one language.
vi.mock('$lib/i18n', () => ({_: readable(mocks.translate)}));
// A fake with the real store's shape: enumerable getters over `$state`, so a template or a `$derived` reading
// `instanceConfig.config` re-renders when a test changes it, as it would when the server answers.
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
/** All five rules of before, in eleven characters: length, upper case, lower case, a digit, a special character. */
const ALL_RULES = 'Str0ng!pass';
/** ALL_RULES and one more digit: twelve characters. */
const TWELVE = 'Str0ng!pass1';
/** Ten characters, lower case and a digit: no capital, no symbol. */
const TEN_WITH_A_DIGIT = 'abcdefghi1';
/**
 * Eight characters, none of them ASCII: `É` upper case, `çéüßà` lower case, `٣` (U+0663, Nd) a digit, `€` a symbol.
 * The ASCII classes of before (`[A-Z]`, `[a-z]`, `\d`, a fixed list of symbols) found none of the four.
 */
const UNICODE_EIGHT = 'Éçéüßà٣€';

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

beforeEach(() => {
    // Every test starts before the server's answer: no password_rules in the configuration, so the defaults.
    mocks.instance.config = mocks.BEFORE_ANSWER;
    mocks.instance.loaded = false;
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockResolvedValue(undefined);
});

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

describe("PasswordStrength — the rules are the server's, read from the instance configuration (A6c)", () => {
    it('draws the five rules of before, in their order, while the configuration carries none: the defaults', () => {
        // No password_rules (beforeEach): the store before the server answers, or the answer of a backend older than A6c.
        render(PasswordStrength, {password: THREE_RULES});

        expect(rulesDrawn().map(keyOf)).toEqual([...RULE_KEYS]);
        expect(rulesPassed()).toEqual(states({minLength: true, hasUppercase: false, hasLowercase: true, hasNumber: true, hasSpecial: false}));
    });

    it("draws the rules the server sends, in the server's order", () => {
        answer([{code: 'special'}, {code: 'digit'}, {code: 'lowercase'}, {code: 'uppercase'}, {code: 'min_length', value: 8}]);
        render(PasswordStrength, {password: THREE_RULES});

        expect(rulesDrawn().map(keyOf)).toEqual(['hasSpecial', 'hasNumber', 'hasLowercase', 'hasUppercase', 'minLength']);
        // The same verdicts as with the defaults: only the order is the server's.
        expect(rulesPassed()).toEqual(states({minLength: true, hasUppercase: false, hasLowercase: true, hasNumber: true, hasSpecial: false}));
    });

    it('draws only the rules the server sends, and valid asks only those', () => {
        answer([{code: 'digit'}, {code: 'min_length', value: 10}]);
        // Ten characters with a digit, no capital and no symbol: enough for these two rules, not for the five of before.
        const {bound} = mountBound(TEN_WITH_A_DIGIT, false);

        expect(rulesDrawn().map(keyOf)).toEqual(['hasNumber', 'minLength']);
        expect(rulesPassed()).toEqual({hasNumber: 'true', minLength: 'true'});
        expect(bound.value, 'valid, written by the meter').toBe(true);
    });

    it.each([
        ['eleven characters', ALL_RULES, false],
        ['twelve characters', TWELVE, true],
    ])('measures the length against the value the server sends, min_length 12: %s', (_label, password, met) => {
        answer(withMinLength(12));
        const {bound} = mountBound(password, !met);

        expect(rulesPassed()).toEqual(states({minLength: met, hasUppercase: true, hasLowercase: true, hasNumber: true, hasSpecial: true}));
        expect(bound.value, 'valid, written by the meter').toBe(met);
    });

    it('draws no row for a code it does not know, and never lets that code make valid false: the server checks it', () => {
        answer([
            {code: 'min_length', value: 4},
            {code: 'not_in_this_build', value: 3},
        ]);
        const {bound} = mountBound('abcd', false);

        expect(rulesDrawn().map(keyOf), 'the one rule this build knows').toEqual(['minLength']);
        expect(bound.value, 'valid, written by the meter').toBe(true);
    });

    it('keeps valid true beside codes it does not know, wherever they sit in the list', () => {
        answer([{code: 'no_dictionary_word'}, ...FIVE, {code: 'not_in_this_build', value: 3}]);
        const {bound} = mountBound(ALL_RULES, false);

        expect(rulesDrawn().map(keyOf)).toEqual([...RULE_KEYS]);
        expect(bound.value, 'valid, written by the meter').toBe(true);
    });

    it('follows an answer that lands under a mounted meter — the checklist and valid, both ways, without a remount', async () => {
        const {bound} = mountBound(ALL_RULES, false);
        expect(screen.getByTestId('password-rule-minLength'), 'the defaults: eleven characters are enough').toHaveAttribute('data-passed', 'true');
        expect(bound.value).toBe(true);

        answer(withMinLength(12));
        await tick();

        expect(screen.getByTestId('password-rule-minLength'), 'the answer asks for twelve').toHaveAttribute('data-passed', 'false');
        expect(bound.value).toBe(false);

        answer(withMinLength(10));
        await tick();

        expect(screen.getByTestId('password-rule-minLength'), 'a later answer asks for ten').toHaveAttribute('data-passed', 'true');
        expect(bound.value).toBe(true);
    });

    it('follows an answer that changes which rules there are, without a remount', async () => {
        render(PasswordStrength, {password: THREE_RULES});
        expect(rulesDrawn().map(keyOf), 'the defaults').toEqual([...RULE_KEYS]);

        answer([{code: 'digit'}, {code: 'min_length', value: 8}]);
        await tick();

        expect(rulesDrawn().map(keyOf)).toEqual(['hasNumber', 'minLength']);
    });

    it('checks with the Unicode classes: É, çéüßà, ٣ and € meet upper case, lower case, digit and special', () => {
        const {bound} = mountBound(UNICODE_EIGHT, false);

        expect(rulesPassed()).toEqual(states({minLength: true, hasUppercase: true, hasLowercase: true, hasNumber: true, hasSpecial: true}));
        expect(bound.value, 'valid, written by the meter').toBe(true);
    });

    it('does not count a space as a special character', () => {
        // Lower case, upper case and a digit, and two spaces where a symbol would be.
        render(PasswordStrength, {password: 'Pass word 12'});

        expect(screen.getByTestId('password-rule-hasSpecial')).toHaveAttribute('data-passed', 'false');
    });
});

describe('PasswordStrength — the min-length label names the length the rule asks for (A6c)', () => {
    it('gives the label the length of the default rule, 8, as the ICU {value}', () => {
        render(PasswordStrength, {password: WEAKEST});

        expect(screen.getByTestId('password-rule-minLength')).toHaveTextContent('auth.passwordStrength.rules.minLength {"value":8}');
    });

    it("gives it the server's length once the answer lands, without a remount", async () => {
        render(PasswordStrength, {password: WEAKEST});

        answer(withMinLength(12));
        await tick();

        expect(screen.getByTestId('password-rule-minLength')).toHaveTextContent('auth.passwordStrength.rules.minLength {"value":12}');
    });

    it('labels every rule with its i18n key of always, auth.passwordStrength.rules.<key>', () => {
        render(PasswordStrength, {password: WEAKEST});
        const rules = rulesDrawn();
        expect(rules.map(keyOf), 'premise: the five rows are drawn').toEqual([...RULE_KEYS]);

        for (const rule of rules) expect(rule, keyOf(rule)).toHaveTextContent(`auth.passwordStrength.rules.${keyOf(rule)}`);
    });
});

// =====================================================================================================================
// B4 — the rules a parent gives: the prop `rules` (workstream B, lot B4; written red first)
// =====================================================================================================================

/*
 * The «secure» backup asks for a password that follows the registration rules with at least twelve characters
 * (developer decision P12). The server publishes those rules in `GET /backup/instance/options`, and the backup card
 * hands them to this meter. The contract (B4 brief §7): an optional prop `rules?: PasswordRule[]`; when given, the
 * checklist and `valid` follow those rules instead of `instanceConfig`'s; without it, exactly today's behaviour.
 *
 * What this block holds the meter to — red today, because the meter has no such prop and reads the instance's rules
 * whatever it is given, unless said otherwise:
 *   - given rules, the checklist is theirs: their rows, in their order, the min-length label naming their length;
 *   - `valid` asks those rules, both ways: eleven characters fail a rule of twelve where the instance asks only eight,
 *     and twelve meet it where the instance asks sixteen;
 *   - an answer of the instance landing under a meter given rules changes nothing;
 *   - rules that change under a mounted meter — the options' answer landing — are followed without a remount;
 *   - a code this build does not know, among the rules given, draws no row and never makes `valid` false, as with the
 *     instance's rules (the server checks it);
 *   - `rules: undefined`, what a parent passes while its rules are on their way, is today's meter: the guard of
 *     «without it, exactly today's behaviour», green today and to stay so.
 *
 * The prop does not exist yet: the props are cast once, in `rulesProp()` and `mountWithRules()`, so the type check does
 * not wait for it.
 */

type MeterProps = ComponentProps<typeof PasswordStrength>;

/** The rules of a secure archive, as `GET /backup/instance/options` answers them while A's minimum is eight (B4 §2, §4). */
const ARCHIVE_RULES: RuleAnswer[] = withMinLength(12);

/** `{rules}` as the meter takes it (B4 §7). */
const rulesProp = (rules: RuleAnswer[] | undefined): Partial<MeterProps> => ({rules}) as unknown as Partial<MeterProps>;

/** Mounts the meter with `rules` and `valid` bound, as `mountBound` binds it; `start` is the opposite of what the case expects. */
function mountWithRules(password: string, rules: RuleAnswer[] | undefined, start: boolean) {
    const bound = {value: start};
    const props = {
        password,
        rules,
        get valid(): boolean {
            return bound.value;
        },
        set valid(next: boolean) {
            bound.value = next;
        },
    };
    const utils = render(PasswordStrength, {props: props as unknown as MeterProps});
    return {...utils, bound};
}

describe('B4 — PasswordStrength given rules: the checklist and valid follow them, not the instance (rules prop)', () => {
    it('draws the rules it is given, in their order, and names their length: min_length 12 as the ICU value of the label', () => {
        // The instance's rules are the defaults here (beforeEach): eight characters.
        mountWithRules(TWELVE, ARCHIVE_RULES, false);

        expect(rulesDrawn().map(keyOf)).toEqual([...RULE_KEYS]);
        expect(screen.getByTestId('password-rule-minLength')).toHaveTextContent('auth.passwordStrength.rules.minLength {"value":12}');
    });

    it.each<[string, RuleAnswer[] | null, string, boolean]>([
        ['eleven characters of every class, the instance asking eight: the rule of twelve fails', null, ALL_RULES, false],
        ['twelve characters of every class, the instance asking sixteen: the rule of twelve holds', withMinLength(16), TWELVE, true],
    ])("valid follows the rules given, not the instance's — %s", (_label, served, password, met) => {
        if (served !== null) answer(served);
        const {bound} = mountWithRules(password, ARCHIVE_RULES, !met);

        expect(rulesPassed()).toEqual(states({minLength: met, hasUppercase: true, hasLowercase: true, hasNumber: true, hasSpecial: true}));
        expect(bound.value, 'valid, written by the meter').toBe(met);
    });

    it("draws only the rules given, in their order, and valid asks only those — whatever the instance's five say", () => {
        answer(FIVE);
        // Twelve characters, lower case and a digit: enough for the two rules given, not for the instance's five.
        const {bound} = mountWithRules('abcdefghijk1', [{code: 'digit'}, {code: 'min_length', value: 12}], false);

        expect(rulesDrawn().map(keyOf)).toEqual(['hasNumber', 'minLength']);
        expect(rulesPassed()).toEqual({hasNumber: 'true', minLength: 'true'});
        expect(bound.value, 'valid, written by the meter').toBe(true);
    });

    it("an answer of the instance landing under a meter given rules changes nothing: the checklist, its label and valid stay the given rules'", async () => {
        const {bound} = mountWithRules(TWELVE, ARCHIVE_RULES, false);
        expect(bound.value, 'premise: twelve characters of every class meet the rules given').toBe(true);

        answer(withMinLength(16));
        await tick();

        expect(screen.getByTestId('password-rule-minLength'), 'the instance now asks sixteen: not the rule of this meter').toHaveAttribute('data-passed', 'true');
        expect(screen.getByTestId('password-rule-minLength')).toHaveTextContent('auth.passwordStrength.rules.minLength {"value":12}');
        expect(bound.value).toBe(true);
    });

    it('follows rules that change under a mounted meter — the answer of the options landing —, the checklist and valid, both ways, without a remount', async () => {
        const {bound, rerender} = mountWithRules(ALL_RULES, withMinLength(10), false);
        expect(screen.getByTestId('password-rule-minLength'), 'ten asked: eleven characters are enough').toHaveAttribute('data-passed', 'true');
        expect(bound.value).toBe(true);

        await rerender(rulesProp(ARCHIVE_RULES));

        expect(screen.getByTestId('password-rule-minLength'), 'twelve asked').toHaveAttribute('data-passed', 'false');
        expect(screen.getByTestId('password-rule-minLength')).toHaveTextContent('auth.passwordStrength.rules.minLength {"value":12}');
        expect(bound.value).toBe(false);

        await rerender(rulesProp(withMinLength(11)));

        expect(screen.getByTestId('password-rule-minLength'), 'eleven asked').toHaveAttribute('data-passed', 'true');
        expect(bound.value).toBe(true);
    });

    it('draws no row for a code it does not know among the rules given, and never lets that code make valid false', () => {
        // Twelve characters in lower case: the one rule this build knows holds; the other is the server's to check.
        const {bound} = mountWithRules(
            'abcdefghijkl',
            [
                {code: 'min_length', value: 12},
                {code: 'not_in_this_build', value: 3},
            ],
            false,
        );

        expect(rulesDrawn().map(keyOf), 'the one rule this build knows').toEqual(['minLength']);
        expect(bound.value, 'valid, written by the meter').toBe(true);
    });

    it("rules: undefined — what a parent passes while its rules are on their way — is today's meter: the instance's rules (green today: the guard)", () => {
        answer(withMinLength(12));
        const {bound} = mountWithRules(ALL_RULES, undefined, true);

        expect(rulesDrawn().map(keyOf)).toEqual([...RULE_KEYS]);
        expect(screen.getByTestId('password-rule-minLength'), 'the instance asks twelve').toHaveAttribute('data-passed', 'false');
        expect(bound.value, 'valid, written by the meter').toBe(false);
    });
});
