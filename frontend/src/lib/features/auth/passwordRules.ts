/**
 * The password rules as the server publishes them (`GET /system/instance`, `accounts.password_rules`, decision 37), and the
 * checks the app runs while the user types. The server is the one source: until it answers, the app assumes the rules of
 * release 1.3, and a rule this app does not know is never checked here — the server, which knows it, decides.
 *
 * The character classes are the server's (`password_policy.py`): an uppercase letter is `\p{Lu}`, a lowercase one `\p{Ll}`,
 * a digit `\p{Nd}`, and a symbol any character that is not a letter, a number or whitespace. Length counts code points.
 */

export interface PasswordRule {
    code: string;
    value?: number | null;
}

/** The rules of release 1.3, assumed until the server answers. */
export const DEFAULT_PASSWORD_RULES: readonly PasswordRule[] = [{code: 'min_length', value: 8}, {code: 'uppercase'}, {code: 'lowercase'}, {code: 'digit'}, {code: 'special'}];

/** The app's key for each code it knows: the checklist's `password-rule-<key>` and its label `auth.passwordStrength.rules.<key>`. */
export const RULE_UI_KEYS: Readonly<Record<string, string>> = {
    min_length: 'minLength',
    uppercase: 'hasUppercase',
    lowercase: 'hasLowercase',
    digit: 'hasNumber',
    special: 'hasSpecial',
};

const UPPERCASE = /\p{Lu}/u;
const LOWERCASE = /\p{Ll}/u;
const DIGIT = /\p{Nd}/u;
const SYMBOL = /[^\p{L}\p{N}\s]/u;

/** Whether `password` meets `rule`; null for a code this app does not know. */
export function ruleMet(rule: PasswordRule, password: string): boolean | null {
    switch (rule.code) {
        case 'min_length':
            return [...password].length >= (rule.value ?? 0);
        case 'uppercase':
            return UPPERCASE.test(password);
        case 'lowercase':
            return LOWERCASE.test(password);
        case 'digit':
            return DIGIT.test(password);
        case 'special':
            return SYMBOL.test(password);
        default:
            return null;
    }
}

/** The codes of the known rules `password` does not meet, in the rules' order. */
export function unmetRules(password: string, rules: readonly PasswordRule[]): string[] {
    return rules.filter((rule) => ruleMet(rule, password) === false).map((rule) => rule.code);
}
