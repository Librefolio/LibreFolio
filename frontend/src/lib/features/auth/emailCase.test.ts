/**
 * emailCase — when two e-mail addresses are one (decision P18; accounts lot A-25, contract C1).
 *
 * P18 (the developer's, now in the backend): an address is the same whatever the case of its letters A–Z, and of those
 * only. The database holds a unique index on `lower(email)` (`ux_users_email_lower`, step 6 of migration
 * `005_release_1_3_0_schema`), and `user_service.email_fold` folds as SQLite's `lower()` does: A–Z to a–z, and nothing
 * else. Letters outside A–Z compare as written — a documented limit: `émile@` and `Émile@` are two addresses.
 *
 * `emailCase.ts` is the interface's copy of that fold, written once, beside `passwordRules.ts` (decision 37): the
 * Profile tab asks for the current password, and sends it, only when the address really changes (A-25). The contract:
 *   - `emailFold(address)`: `address` with A–Z folded to a–z and every other character as written — no trim, no
 *     Unicode case mapping, no normalisation;
 *   - `sameEmail(a, b)`: whether the two fold alike.
 * Pure and synchronous: no store, no DOM, no request.
 *
 * Why the server's fold, and nothing more. Wherever the tab calls two addresses one, the server must too: a wider fold —
 * `toLowerCase()`, which turns `É` into `é` — would send a real change of address without the password; the server
 * refuses it (400 `CURRENT_PASSWORD_REQUIRED`), and the tab, which shows no password field for what it took for the
 * same address, leaves the user nowhere to type one. The other way round costs less — a password asked for and not
 * read — and is the side to err on where the server sees a form the tab does not (`EmailStr` hands it the domain in
 * small letters, before the fold). So the cases below pin the fold itself, and each character that `toLowerCase()`
 * would change is there to prove that this module does not.
 *
 * Node environment: no DOM. Its place in the runner is `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`,
 * action `core-unit`), beside `passwordRules.test.ts`.
 *
 * Written red-first, before `emailCase.ts` exists: every case fails on the import until it does.
 */
import {describe, expect, it} from 'vitest';
import {emailFold, sameEmail} from './emailCase';

/** Pairs that fold alike, each with what it shows. */
const SAME: [string, string, string][] = [
    ['Alice@Example.com', 'alice@example.com', 'capitals A–Z in the local part and in the domain'],
    ['ALICE@EXAMPLE.COM', 'alice@example.com', 'every letter in capitals'],
    ['éMILE@example.com', 'émile@example.com', 'capitals A–Z beside an é written alike on both sides'],
    ['alice@example.com', 'alice@example.com', 'the same string'],
];

/** Pairs that do not fold alike, each with what keeps them apart. */
const DIFFERENT: [string, string, string][] = [
    ['Émile@x.com', 'émile@x.com', 'É and é: a capital outside A–Z compares as written, the ASCII limit (P18, C5)'],
    ['ÉMILE@X.COM', 'émile@x.com', 'every A–Z folds back, the É does not'],
    ['alice@example.com', 'bob@example.com', 'another local part'],
    ['alice@example.com', 'alice@example.org', 'another domain'],
    [' a@x.com', 'a@x.com', 'a space before: nothing is trimmed'],
    ['a@x.com ', 'a@x.com', 'a space after'],
];

describe('emailFold — A–Z to a–z, and nothing else', () => {
    it('folds every capital A–Z to its small letter', () => {
        expect(emailFold('ABCDEFGHIJKLMNOPQRSTUVWXYZ')).toBe('abcdefghijklmnopqrstuvwxyz');
        expect(emailFold('Alice.Smith@Example.COM')).toBe('alice.smith@example.com');
    });

    it('leaves an address already folded as it is: small letters, digits and the symbols of an address', () => {
        const folded = 'alice.o-brien+tag_1@mail-2.example.com';

        expect(emailFold(folded)).toBe(folded);
    });

    it('folds the A–Z around a capital outside A–Z, which stays: ÉMILE@X.COM → Émile@x.com', () => {
        // The premise of every É and é in this file: written precomposed, one code point each, as a keyboard types them.
        expect(
            ['É', 'é'].map((letter) => letter.codePointAt(0)),
            'premise: É is U+00C9 and é is U+00E9',
        ).toEqual([0xc9, 0xe9]);

        expect(emailFold('ÉMILE@X.COM')).toBe('Émile@x.com');
    });

    it.each([
        ['ÄÖÜ', 'U+00C4 U+00D6 U+00DC: Latin capitals outside A–Z'],
        ['Ünïcödé', 'letters outside A–Z, small ones too, never change'],
        ['ΩΣЖ', 'U+03A9 U+03A3 U+0416: Greek and Cyrillic capitals'],
        ['\u0130', 'U+0130 LATIN CAPITAL LETTER I WITH DOT ABOVE, which toLowerCase() turns into two characters'],
        ['\u212A', 'U+212A KELVIN SIGN, which toLowerCase() turns into the ASCII k'],
        ['\uFF21\uFF22\uFF23', 'U+FF21 to U+FF23 FULLWIDTH LATIN CAPITAL A, B and C: not the A–Z they look like'],
    ])('leaves %j as written (%s), alone and in an address whose A–Z fold', (letters) => {
        expect(emailFold(letters)).toBe(letters);
        expect(emailFold(`${letters}@EXAMPLE.COM`)).toBe(`${letters}@example.com`);
    });

    it('trims nothing: the white space around an address stays, and only its A–Z fold', () => {
        expect(emailFold(' A@X.COM')).toBe(' a@x.com');
        expect(emailFold('A@X.COM ')).toBe('a@x.com ');
        expect(emailFold('\tA@X.COM\n')).toBe('\ta@x.com\n');
    });

    it('normalises nothing: an é written as e and a combining acute (U+0065 U+0301) stays two characters, and only the A–Z fold', () => {
        expect(emailFold('e\u0301mile@example.com')).toBe('e\u0301mile@example.com');
        expect(emailFold('E\u0301MILE@EXAMPLE.COM')).toBe('e\u0301mile@example.com');
        expect(emailFold('e\u0301mile@example.com'), 'not the é of U+00E9').not.toBe(emailFold('\u00E9mile@example.com'));
    });

    it('folds the empty string to itself', () => {
        expect(emailFold('')).toBe('');
    });
});

describe('sameEmail — whether two addresses fold alike', () => {
    it.each(SAME)('sameEmail(%j, %j) is true: %s', (first, second) => {
        expect(sameEmail(first, second)).toBe(true);
        expect(sameEmail(second, first), 'either way round').toBe(true);
    });

    it.each(DIFFERENT)('sameEmail(%j, %j) is false: %s', (first, second) => {
        expect(sameEmail(first, second)).toBe(false);
        expect(sameEmail(second, first), 'either way round').toBe(false);
    });

    it('answers exactly as emailFold compares, for every pair of the addresses of this file', () => {
        const addresses = [...new Set([...SAME, ...DIFFERENT].flatMap(([first, second]) => [first, second]))];

        for (const first of addresses) {
            for (const second of addresses) {
                expect(sameEmail(first, second), `sameEmail(${JSON.stringify(first)}, ${JSON.stringify(second)})`).toBe(emailFold(first) === emailFold(second));
            }
        }
    });
});
