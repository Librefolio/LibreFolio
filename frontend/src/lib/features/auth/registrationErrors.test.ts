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
 *   - accounts lot A-21a adds `USERNAME_INVALID` → `auth.validation.usernameNoAt` (red until A-21a): a new username may
 *     not hold `@`, which the sign-in reads as an email address first, and the server refuses one with a 400
 *     `{error_code, message}`. The key is the one the card's own check shows (`validateUsername`, pinned in
 *     `RegisterCard.test.ts`): one rule, the same words, on the client or from the server. It comes with the code, so it
 *     must be a sentence in the four catalogues — without it the card and the profile would show the key (red until
 *     A-21a too);
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
 *
 * Accounts lot A7b (decided by the coordinator, 2026-10-16 21:10; closes A-13): on a blocked instance the registration
 * is refused with a 401 — `POST /auth/register` is public and outside `ALLOWED_WHEN_BLOCKED`, so the instance block
 * answers an anonymous caller with the 401 of `get_current_user` (`backend/app/api/v1/instance_block.py`) — or, to a
 * browser holding a session, with H's 423 `{detail: {code: 'instance_blocked'}}` (`isInstanceBlockedError`). `/invite`
 * opens its form there (`tokens/inspect` still answers) and showed the raw «Not authenticated». Now:
 *   - a 401, whatever its body → `{key: 'auth.instanceBlocked'}`: the status decides before the body is read;
 *   - a 423 `instance_blocked` → the same key; a 423 with anything else, and that code under another status, are read
 *     as before (guards);
 *   - `auth.instanceBlocked` is a sentence in the four catalogues — without it the form would show the key instead of
 *     «Not authenticated», which is the same defect;
 *   - every mapping above is unchanged: those cases are the guards, and none of them uses a 401 or a 423.
 */
import {describe, expect, it} from 'vitest';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
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
        // red until A-21a: a new username holding @, which the sign-in would read as an email address
        [400, 'USERNAME_INVALID', 'auth.validation.usernameNoAt'],
    ])('reads a %i %s as {key: %s}, never the server sentence', (status, code, key) => {
        expect(describeRegistrationError(coded(status, code))).toEqual({key});
    });

    // red until A-21a: the key USERNAME_INVALID reads as comes with the code
    it.each(Object.entries({en, it: itCatalogue, fr, es}))('has auth.validation.usernameNoAt as a sentence in %s, or the sign-up card and the profile would show the key', (language, catalogue) => {
        const validation = (catalogue as {auth?: {validation?: {usernameMinLength?: unknown; usernameNoAt?: unknown}}}).auth?.validation;
        // The premise: the path reaches the validation keys — the length rule's, which the card already shows, is there.
        expect(typeof validation?.usernameMinLength, `auth.validation.usernameMinLength in ${language}`).toBe('string');

        const message = validation?.usernameNoAt;

        expect(typeof message === 'string' && message.trim().length > 0, `auth.validation.usernameNoAt in ${language}`).toBe(true);
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

describe('describeRegistrationError — a blocked instance (A7b, closes A-13)', () => {
    const BLOCKED_KEY = 'auth.instanceBlocked';
    /** H's refusal on a blocked instance, the `detail` of its 423 (`instance_block.py`). */
    const INSTANCE_BLOCKED_DETAIL = {code: 'instance_blocked', message: 'This instance is blocked by its hosting provider'};

    // red until A7b
    it.each([
        // The real one: what the instance block answers an anonymous caller (`get_current_user`).
        ['the 401 of an anonymous caller, «Not authenticated»', refusal(401, 'Not authenticated')],
        ['a 401 with another sentence of get_current_user', refusal(401, 'Session expired or invalid')],
        // The status decides before the body: a 401 whose body would map to another key is still the block.
        ['a 401 whose sentence names the username', refusal(401, 'Username already taken')],
        ['a 401 carrying a code of the registration rule', coded(401, 'REGISTRATION_DISABLED')],
        ['a 401 carrying a schema list', refusal(401, [{type: 'value_error', loc: ['body', 'email'], msg: 'value is not a valid email address'}])],
        ['a 401 with no detail', refusal(401, undefined)],
        ['a 401 with no body at all', {isAxiosError: true, response: {status: 401}}],
    ])('reads %s as auth.instanceBlocked, never the server sentence', (_label, failure) => {
        expect(describeRegistrationError(failure)).toEqual({key: BLOCKED_KEY});
    });

    // red until A7b
    it("reads H's 423 instance_blocked — what a browser holding a session gets — as auth.instanceBlocked", () => {
        expect(describeRegistrationError(refusal(423, INSTANCE_BLOCKED_DETAIL))).toEqual({key: BLOCKED_KEY});
    });

    // guard
    it.each([
        ['a 423 with another code', refusal(423, {code: 'locked'}), {key: 'auth.registrationFailed'}],
        ['a 423 with a plain sentence', refusal(423, 'Locked'), {raw: 'Locked'}],
        ['a 423 with no detail', refusal(423, undefined), {key: 'auth.registrationFailed'}],
        ['a 403 carrying the code of a blocked instance', refusal(403, INSTANCE_BLOCKED_DETAIL), {key: 'auth.registrationFailed'}],
    ])('reads %s as before: only a 401, or a 423 with the code of a blocked instance, is the block', (_label, failure, expected) => {
        expect(describeRegistrationError(failure)).toEqual(expected);
    });

    // red until A7b
    it.each(Object.entries({en, it: itCatalogue, fr, es}))('has auth.instanceBlocked as a sentence in %s, or the form would show the key', (language, catalogue) => {
        const message = (catalogue as {auth?: {instanceBlocked?: unknown}}).auth?.instanceBlocked;

        expect(typeof message === 'string' && message.trim().length > 0, `auth.instanceBlocked in ${language}`).toBe(true);
    });
});
