/**
 * describeRegistrationError — what the sign-up form says when `POST /api/v1/auth/register` refuses (accounts lot A5b).
 *
 * The ladder used to live in the `catch` of `RegisterCard.svelte`. It moves to `registrationErrors.ts` and learns the
 * structured refusals of A5a, `{detail: {error_code, message}}`, which the old ladder could not read: a closed
 * instance answered with the generic failure. The function returns what to show, never the text itself:
 *   - `{key}`, a catalogue key the card translates;
 *   - `{raw}`, a server sentence it has no key for, shown as it came — better than silence.
 *
 * The contract (plan A5b.1):
 *   - an `error_code` → its key: `REGISTRATION_DISABLED` → `auth.registrationDisabled`, `INVITE_REQUIRED` →
 *     `auth.registrationInviteOnly`, `INVITE_INVALID` → `auth.link.unknown`, `USER_LIMIT_REACHED` →
 *     `auth.userLimitReached` (anonymous: no count reaches the user). The server's English `message` is never shown;
 *   - accounts lot A6c (decision 37) adds `PASSWORD_TOO_WEAK` → `auth.validation.passwordTooWeak`, the key the card's
 *     own check already shows: the server applies the same rules to every new password and refuses one that breaks
 *     them with a 400 `{error_code, message, rules}`, `rules` naming the codes it missed. The list does not change the
 *     key;
 *   - a string `detail`, case-folded: naming the username → `auth.validation.usernameTaken`, the email →
 *     `auth.validation.emailTaken`, anything else → `{raw: detail}`;
 *   - a Pydantic list: the first entry's `loc` decides — `email` → `auth.validation.invalidEmailDomain` when its `msg`
 *     speaks of a special-use or reserved domain, else `auth.validation.invalidEmail`; `username` →
 *     `auth.validation.usernameMinLength`; `password` → `auth.validation.passwordTooWeak`; anything else, an empty list
 *     included → `auth.registrationFailed`;
 *   - anything else — not axios, no response, no detail, an object without a known code → `auth.registrationFailed`.
 *
 * The rejections are shaped as axios builds them (`isAxiosError: true`, `response.status`, `response.data.detail`): the
 * real `isAxiosError` reads that flag, so no mock is needed. Node environment: no DOM.
 *
 * Written red-first, before `registrationErrors.ts` exists: every case fails on the import until it does.
 */
import {describe, expect, it} from 'vitest';
import {describeRegistrationError} from './registrationErrors';

/** An axios-shaped refusal carrying `response.status` and `response.data.detail`. */
function refusal(status: number, detail: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {
        isAxiosError: true,
        response: {status, data: {detail}},
    });
}

/** A structured refusal of A5a: `{detail: {error_code, message}}`, the message in the server's English. */
function coded(status: number, error_code: string): Error {
    return refusal(status, {error_code, message: 'An English sentence the user must not read'});
}

/** A Pydantic 422 whose first entry complains about `field`. */
function schemaRefusal(field: string, msg = 'value is not valid'): Error {
    return refusal(422, [{type: 'value_error', loc: ['body', field], msg}]);
}

describe('describeRegistrationError — the refusals A5a explains with a code', () => {
    it.each([
        [403, 'REGISTRATION_DISABLED', 'auth.registrationDisabled'],
        [403, 'INVITE_REQUIRED', 'auth.registrationInviteOnly'],
        [400, 'INVITE_INVALID', 'auth.link.unknown'],
        [409, 'USER_LIMIT_REACHED', 'auth.userLimitReached'],
        [400, 'PASSWORD_TOO_WEAK', 'auth.validation.passwordTooWeak'],
    ])('reads a %i %s as {key: %s}, never the server sentence', (status, code, key) => {
        expect(describeRegistrationError(coded(status, code))).toEqual({key});
    });

    it.each([
        ['one rule missed', ['min_length']],
        ['several rules missed', ['min_length', 'uppercase', 'special']],
        ['a code this build does not know', ['no_dictionary_word']],
    ])('reads the whole refusal of A6c — PASSWORD_TOO_WEAK with %s — as the key of a weak password', (_label, rules) => {
        const failure = refusal(400, {error_code: 'PASSWORD_TOO_WEAK', message: 'An English sentence the user must not read', rules});

        expect(describeRegistrationError(failure)).toEqual({key: 'auth.validation.passwordTooWeak'});
    });

    it('reads a code it does not know as the general failure, not as the server sentence', () => {
        expect(describeRegistrationError(coded(400, 'SOMETHING_A_LATER_BACKEND_ADDS'))).toEqual({key: 'auth.registrationFailed'});
    });

    it('reads an object detail with no code as the general failure', () => {
        expect(describeRegistrationError(refusal(400, {code: 'weird'}))).toEqual({key: 'auth.registrationFailed'});
    });
});

describe('describeRegistrationError — plain-text details', () => {
    it.each([
        // The exact sentences of `user_service.py`: capitalised, which is why the match is case-folded.
        ['Username already taken', 'auth.validation.usernameTaken'],
        ['Email already registered', 'auth.validation.emailTaken'],
        ['that USERNAME is taken', 'auth.validation.usernameTaken'],
        ['that email is taken', 'auth.validation.emailTaken'],
    ])('reads %j as {key: %s}', (detail, key) => {
        expect(describeRegistrationError(refusal(400, detail))).toEqual({key});
    });

    it('hands back a sentence it has no key for as it came, rather than swallowing it', () => {
        const detail = 'Something the frontend has never heard of';

        expect(describeRegistrationError(refusal(400, detail))).toEqual({raw: detail});
    });
});

describe('describeRegistrationError — schema refusals (Pydantic 422)', () => {
    it.each([
        ['a special-use domain', 'value is not a valid email address: special-use domain', 'auth.validation.invalidEmailDomain'],
        ['a reserved domain', 'the domain name is reserved', 'auth.validation.invalidEmailDomain'],
        ['any other address complaint', 'value is not a valid email address', 'auth.validation.invalidEmail'],
    ])('reads %s as {key: %s}', (_label, msg, key) => {
        expect(describeRegistrationError(schemaRefusal('email', msg))).toEqual({key});
    });

    it.each([
        ['username', 'auth.validation.usernameMinLength'],
        ['password', 'auth.validation.passwordTooWeak'],
    ])('maps a complaint about %s back onto that field', (field, key) => {
        expect(describeRegistrationError(schemaRefusal(field, 'too short'))).toEqual({key});
    });

    it('decides on the first entry when several fields are refused', () => {
        const detail = [
            {type: 'value_error', loc: ['body', 'password'], msg: 'too short'},
            {type: 'value_error', loc: ['body', 'email'], msg: 'value is not a valid email address'},
        ];

        expect(describeRegistrationError(refusal(422, detail))).toEqual({key: 'auth.validation.passwordTooWeak'});
    });

    it.each([
        ['a field it cannot place', [{type: 'value_error', loc: ['body', 'timezone'], msg: 'unknown'}]],
        ['an empty list', []],
        ['an entry with no location', [{type: 'value_error', msg: 'something'}]],
    ])('falls back to the general failure for %s', (_label, detail) => {
        expect(describeRegistrationError(refusal(422, detail))).toEqual({key: 'auth.registrationFailed'});
    });
});

describe('describeRegistrationError — failures with nothing usable in them', () => {
    it.each([
        ['the request never reached the server', new Error('Network Error')],
        ['an axios error with no response', Object.assign(new Error('timeout of 0ms exceeded'), {isAxiosError: true})],
        ['a response with no detail', refusal(500, undefined)],
        ['a thrown string', 'boom'],
        ['undefined', undefined],
        ['null', null],
    ])('reads %s as the general failure', (_label, failure) => {
        expect(describeRegistrationError(failure)).toEqual({key: 'auth.registrationFailed'});
    });
});
