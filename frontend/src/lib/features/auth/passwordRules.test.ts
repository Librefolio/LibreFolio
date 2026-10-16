/**
 * passwordRules — the password rules, one source for the whole interface (accounts lot A6c, decision 37).
 *
 * Decision 37 (the developer, 15/10): the rules are written once, in the backend, which applies them to every new
 * password the API receives and exposes them in the public `GET /api/v1/system/instance`, as
 * `accounts.password_rules: [{code, value?}]`; the interface shows them and checks them live from there, and the
 * strength meter stays. Until A6c the same five rules were written four times — `PasswordStrength`, `RegisterCard`,
 * `PasswordChangeModal` and the CLI's `validate_password` — and the copies already disagreed: ASCII classes and a fixed
 * list of symbols in the interface, Unicode classes and another list in the CLI.
 *
 * `passwordRules.ts` is the interface's half of that one source. It is pure — no store, no DOM, no request: whoever
 * reads the instance configuration passes the rules in. The contract (A6c.1):
 *   - `type PasswordRule = {code: string; value?: number | null}`, one entry of `password_rules`;
 *   - `DEFAULT_PASSWORD_RULES`, the five rules of today in their order — `min_length` 8, `uppercase`, `lowercase`,
 *     `digit`, `special` — which the interface uses until the server answers;
 *   - `RULE_UI_KEYS`, server code → the key the interface has always used for that rule: `min_length` → `minLength`,
 *     `uppercase` → `hasUppercase`, `lowercase` → `hasLowercase`, `digit` → `hasNumber`, `special` → `hasSpecial`.
 *     The keys are the checklist's test ids (`password-rule-<key>`) and its i18n keys
 *     (`auth.passwordStrength.rules.<key>`), and they do not change: workstream T's `e2e/layout/theme-roles.spec.ts`
 *     reads those test ids;
 *   - `ruleMet(rule, password)`: true or false for a code this build knows, `null` for one it does not — the server
 *     checks those when the form is sent;
 *   - `unmetRules(password, rules)`: the known codes the password does not meet, in the order of `rules`; unknown codes
 *     are left out.
 *
 * The classes are Unicode, the same in Python and in JS (the coordinator's night decision, approved «to review»): an
 * upper-case letter is `\p{Lu}`, a lower-case one `\p{Ll}`, a digit `\p{Nd}`, and a special character is any character
 * that is not a letter (`\p{L}`), not a number (`\p{N}`) and not whitespace. The length counts code points, as Python's
 * `len` does, not UTF-16 units. Each character below is named with its code point and general category, and most were
 * picked where the ASCII rules of before answered otherwise: `É` was no capital for `[A-Z]`, `٣` no digit for `\d`, `€`
 * not in the old list of symbols. Two are there for the backend's sake as much as for this module: `²` and `½` are
 * numbers (`No`) but not decimal digits, so they satisfy neither `digit` nor `special` — Python's `str.isdigit()` says
 * True for `²`, while `str.isdecimal()` and the general category `Nd` agree with `\p{Nd}`.
 *
 * Node environment: no DOM. Its place in the runner is `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`,
 * action `core-unit`), beside `registrationErrors.test.ts`.
 *
 * Written red-first, before `passwordRules.ts` exists: every case fails on the import until it does.
 */
import {describe, expect, it} from 'vitest';
import {DEFAULT_PASSWORD_RULES, RULE_UI_KEYS, ruleMet, unmetRules} from './passwordRules';
import type {PasswordRule} from './passwordRules';

/** One entry of `password_rules`, as the server sends it: `value` only where the rule has one. */
function rule(code: string, value?: number): PasswordRule {
    return value === undefined ? {code} : {code, value};
}

/** The five rules of today, in the server's order. */
const FIVE: PasswordRule[] = [rule('min_length', 8), rule('uppercase'), rule('lowercase'), rule('digit'), rule('special')];

/** Eleven characters and all five classes: the password the component tests use as the good one. */
const ELEVEN = 'Str0ng!pass';
/** The same and one more digit: twelve characters. */
const TWELVE = 'Str0ng!pass1';
/** Eight characters, none of them ASCII: `É` upper case, `çéüßà` lower case, `٣` a digit, `€` a symbol — the ASCII classes of before found none of the four. */
const UNICODE_EIGHT = 'Éçéüßà٣€';

describe('passwordRules — the defaults, and the keys of the interface', () => {
    it('defaults to the five rules of today, in their order: min_length 8, uppercase, lowercase, digit, special', () => {
        const defaults: readonly PasswordRule[] = DEFAULT_PASSWORD_RULES;

        // `value` read as null where absent: a rule with no parameter may come either way, and both mean the same.
        expect(defaults.map(({code, value}) => ({code, value: value ?? null}))).toEqual([
            {code: 'min_length', value: 8},
            {code: 'uppercase', value: null},
            {code: 'lowercase', value: null},
            {code: 'digit', value: null},
            {code: 'special', value: null},
        ]);
    });

    it('maps every code of the server to the key the checklist has always used, and to nothing else', () => {
        expect(RULE_UI_KEYS).toEqual({min_length: 'minLength', uppercase: 'hasUppercase', lowercase: 'hasLowercase', digit: 'hasNumber', special: 'hasSpecial'});
    });
});

describe('ruleMet — min_length: at least `value` characters, counted as code points', () => {
    it.each([
        ['exactly the value', 'abcdefgh', 8, true],
        ['one character short', 'abcdefg', 8, false],
        ['the empty password', '', 8, false],
        ['spaces, which count like any other character', 'abc defg', 8, true],
        ['eleven characters against a value of 12', ELEVEN, 12, false],
        ['twelve characters against a value of 12', TWELVE, 12, true],
    ])('%s: %j against %i → %s', (_label, password, value, met) => {
        expect(ruleMet(rule('min_length', value), password)).toBe(met);
    });

    it('counts an emoji once — one code point — not as its two UTF-16 units', () => {
        const fourEmoji = '\u{1F600}'.repeat(4);
        // The premise: four code points in eight UTF-16 units — what `.length` counted before A6c.
        expect([...fourEmoji]).toHaveLength(4);
        expect(fourEmoji).toHaveLength(8);

        expect(ruleMet(rule('min_length', 8), fourEmoji), 'four characters are not eight').toBe(false);
        expect(ruleMet(rule('min_length', 4), fourEmoji)).toBe(true);
    });
});

describe('ruleMet — the character classes are Unicode', () => {
    it.each([
        // uppercase: \p{Lu}
        ['uppercase', 'A', 'U+0041, Lu', true],
        ['uppercase', 'É', 'U+00C9, Lu — no capital for the [A-Z] of before', true],
        ['uppercase', 'Ω', 'U+03A9, Lu', true],
        ['uppercase', 'Ж', 'U+0416, Lu', true],
        ['uppercase', 'é', 'U+00E9, Ll', false],
        ['uppercase', '中', 'U+4E2D, Lo: a letter with no case', false],
        ['uppercase', '7', 'U+0037, Nd', false],
        // lowercase: \p{Ll}
        ['lowercase', 'a', 'U+0061, Ll', true],
        ['lowercase', 'é', 'U+00E9, Ll — outside the [a-z] of before', true],
        ['lowercase', 'ü', 'U+00FC, Ll', true],
        ['lowercase', 'ß', 'U+00DF, Ll', true],
        ['lowercase', 'É', 'U+00C9, Lu', false],
        ['lowercase', '中', 'U+4E2D, Lo: a letter with no case', false],
        ['lowercase', '٣', 'U+0663, Nd', false],
        // digit: \p{Nd}
        ['digit', '7', 'U+0037, Nd', true],
        ['digit', '٣', 'U+0663 ARABIC-INDIC DIGIT THREE, Nd — no digit for the \\d of before', true],
        ['digit', '²', 'U+00B2 SUPERSCRIPT TWO, No: a number, not a decimal digit', false],
        ['digit', '½', 'U+00BD VULGAR FRACTION ONE HALF, No: a number, not a decimal digit', false],
        ['digit', 'a', 'U+0061, Ll', false],
        // special: not \p{L}, not \p{N}, not whitespace
        ['special', '!', 'U+0021, Po — in the list of before', true],
        ['special', '_', 'U+005F, Pc — in the list of before', true],
        ['special', '€', 'U+20AC, Sc — not in the list of before', true],
        ['special', '£', 'U+00A3, Sc', true],
        ['special', '§', 'U+00A7, Po', true],
        ['special', '«', 'U+00AB, Pi', true],
        ['special', '\u{1F600}', 'U+1F600 GRINNING FACE, So', true],
        ['special', ' ', 'U+0020 SPACE: whitespace is no symbol', false],
        ['special', '\t', 'U+0009 TAB: whitespace', false],
        ['special', '\u00A0', 'U+00A0 NO-BREAK SPACE: whitespace', false],
        ['special', 'é', 'U+00E9: a letter', false],
        ['special', 'ü', 'U+00FC: a letter', false],
        ['special', '中', 'U+4E2D: a letter', false],
        ['special', '٣', 'U+0663: a number', false],
        ['special', '½', 'U+00BD: a number, though not a digit', false],
        ['special', '7', 'U+0037: a number', false],
    ])('%s for %j (%s) → %s', (code, character, _label, met) => {
        expect(ruleMet(rule(code), character)).toBe(met);
    });

    it.each([
        ['uppercase', 'abcÉdef'],
        ['lowercase', 'ABCéDEF'],
        ['digit', 'abc٣def'],
        ['special', 'abc€def'],
    ])('%s is met by one such character anywhere in the password: %j', (code, password) => {
        expect(ruleMet(rule(code), password)).toBe(true);
    });

    it.each(['uppercase', 'lowercase', 'digit', 'special'])('%s is not met by the empty password', (code) => {
        expect(ruleMet(rule(code), '')).toBe(false);
    });

    it('takes as special every symbol of the list of before: nothing the interface accepted is refused now', () => {
        // The old class `[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~;']` held exactly the printable ASCII characters that are
        // neither a letter nor a digit.
        const before = Array.from({length: 0x7e - 0x21 + 1}, (_unused, index) => String.fromCharCode(0x21 + index)).filter((character) => !/[A-Za-z0-9]/.test(character));
        expect(before, 'premise: the 32 symbols of before').toHaveLength(32);

        expect(before.filter((character) => ruleMet(rule('special'), character) !== true)).toEqual([]);
    });
});

describe('ruleMet — a code this build does not know', () => {
    it.each([
        ['no_dictionary_word', undefined],
        ['max_repeated_characters', 3],
    ])('answers null for %s, whatever the password: the server decides', (code, value) => {
        for (const password of ['', 'a', ELEVEN]) {
            expect(ruleMet(rule(code, value), password), `for ${JSON.stringify(password)}`).toBeNull();
        }
    });
});

describe('unmetRules — the known codes a password misses, in the order of the rules', () => {
    it('is empty for a password that meets the five defaults', () => {
        expect(unmetRules(ELEVEN, DEFAULT_PASSWORD_RULES)).toEqual([]);
    });

    it('names every rule for the empty password, in their order', () => {
        expect(unmetRules('', DEFAULT_PASSWORD_RULES)).toEqual(['min_length', 'uppercase', 'lowercase', 'digit', 'special']);
    });

    it('lists what is missing in the order of the rules it is given, not in an order of its own', () => {
        // 'abc': lower case only — too short, no capital, no digit, no symbol.
        expect(unmetRules('abc', FIVE)).toEqual(['min_length', 'uppercase', 'digit', 'special']);
        expect(unmetRules('abc', [...FIVE].reverse())).toEqual(['special', 'digit', 'uppercase', 'min_length']);
    });

    it('reads the length from the value the rule carries', () => {
        const twelve = [rule('min_length', 12), ...FIVE.slice(1)];

        expect(unmetRules(ELEVEN, twelve)).toEqual(['min_length']);
        expect(unmetRules(TWELVE, twelve)).toEqual([]);
    });

    it('leaves out the codes it does not know, wherever they sit', () => {
        const rules = [rule('no_dictionary_word'), rule('min_length', 8), rule('max_repeated_characters', 3), rule('digit')];

        expect(unmetRules('abc', rules)).toEqual(['min_length', 'digit']);
        expect(unmetRules('abcdefgh1', rules), 'every known rule is met: nothing to name, whatever the server says of the others').toEqual([]);
    });

    it('checks only the rules it is given', () => {
        expect(unmetRules('abc', [rule('lowercase')])).toEqual([]);
        expect(unmetRules('', [])).toEqual([]);
    });

    it('uses the Unicode classes: É, çéüßà, ٣ and € meet the five defaults in eight characters', () => {
        expect([...UNICODE_EIGHT], 'premise: eight code points').toHaveLength(8);

        expect(unmetRules(UNICODE_EIGHT, DEFAULT_PASSWORD_RULES)).toEqual([]);
    });
});
