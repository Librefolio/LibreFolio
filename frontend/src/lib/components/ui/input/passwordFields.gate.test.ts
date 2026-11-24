/**
 * Which fields are a password for the browser (81 U39).
 *
 * The testlist (23/11): typing an API key in Settings › Plugins made the browser offer to save a password, under a user
 * name it took from the field before. A `type="password"` field is a promise that the value is an account's password, and
 * the browser and the password managers act on it. So the rule is by kind:
 *
 *   - **An account's password** (sign in, sign up, reset, change, the check before a change of address) is a real password
 *     field, with its `autocomplete` (`current-password`, `new-password`): `PasswordInput` as it is, in the files below.
 *   - **Any other secret** — an API key, a token, the password of a backup — is `PasswordInput neverSaved`: a text field drawn
 *     masked, which nothing offers to save.
 *
 * Read in the source, as the other coverage gates are: a new secret field that forgets `neverSaved`, or a raw
 * `type="password"` input outside the account's files, fails here by file name. A new account form is added to
 * `ACCOUNT_PASSWORD_FILES` with its reason.
 */
import {readdirSync, readFileSync, statSync} from 'node:fs';
import {join, relative, resolve} from 'node:path';
import {describe, expect, it} from 'vitest';

const SRC = resolve(__dirname, '../../../..');

/** The files where a real password field is right: the account's own password, and nothing else. */
const ACCOUNT_PASSWORD_FILES: ReadonlyMap<string, string> = new Map([
    ['lib/features/auth/LoginCard.svelte', 'sign in'],
    ['lib/features/auth/RegisterCard.svelte', 'sign up'],
    ['lib/features/auth/ResetPasswordCard.svelte', 'reset by link'],
    ['lib/features/auth/SetupCard.svelte', 'the first administrator'],
    ['lib/features/settings/PasswordChangeModal.svelte', 'change of the account password'],
    ['lib/features/settings/tabs/ProfileTab.svelte', 'the account password asked before a change of address'],
]);

function sources(dir: string, found: string[] = []): string[] {
    for (const name of readdirSync(dir)) {
        const path = join(dir, name);
        if (statSync(path).isDirectory()) {
            if (name !== 'node_modules' && name !== '__tests__') sources(path, found);
        } else if (name.endsWith('.svelte')) found.push(path);
    }
    return found;
}

const FILES = sources(SRC).map((path) => ({path, rel: relative(SRC, path).replaceAll('\\', '/'), text: readFileSync(path, 'utf8')}));

/** Every `<PasswordInput … />` tag of a source, as written. */
function passwordInputTags(text: string): string[] {
    const tags: string[] = [];
    for (let at = text.indexOf('<PasswordInput'); at !== -1; at = text.indexOf('<PasswordInput', at + 1)) {
        const end = text.indexOf('/>', at);
        tags.push(text.slice(at, end === -1 ? undefined : end + 2));
    }
    return tags;
}

describe('password fields (81 U39)', () => {
    it('reads the sources it judges (the scan is not empty)', () => {
        expect(FILES.length, 'no source read').toBeGreaterThan(100);
        expect(FILES.filter((file) => passwordInputTags(file.text).length > 0).length, 'no PasswordInput found').toBeGreaterThan(5);
    });

    it('draws a real password field only for an account’s password', () => {
        const offenders = FILES.filter((file) => /<input\b[^>]*\btype=["']password["']/s.test(file.text) && file.rel !== 'lib/components/ui/input/PasswordInput.svelte' && !ACCOUNT_PASSWORD_FILES.has(file.rel)).map((file) => file.rel);
        expect(offenders, 'a raw type="password" input outside the account’s files: use PasswordInput neverSaved').toEqual([]);
    });

    it('draws every PasswordInput outside the account’s files as neverSaved', () => {
        const offenders = FILES.filter((file) => file.rel !== 'lib/components/ui/input/PasswordInput.svelte' && !ACCOUNT_PASSWORD_FILES.has(file.rel))
            .flatMap((file) => passwordInputTags(file.text).map((tag) => ({file: file.rel, tag})))
            .filter(({tag}) => !/\bneverSaved\b/.test(tag))
            .map(({file}) => file);
        expect(offenders, 'a PasswordInput that is not an account’s password and not neverSaved: the browser offers to save it').toEqual([]);
    });

    it('keeps the account files honest: each still draws a password field', () => {
        for (const [rel, reason] of ACCOUNT_PASSWORD_FILES) {
            const file = FILES.find((candidate) => candidate.rel === rel);
            expect(file, `${rel} (${reason}) no longer exists: take it off the list`).toBeDefined();
            const draws = passwordInputTags(file!.text).length > 0 || /<input\b[^>]*\btype=["']password["']/s.test(file!.text);
            expect(draws, `${rel} (${reason}) draws no password field any more: take it off the list`).toBe(true);
        }
    });
});
