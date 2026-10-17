/**
 * describeAccountError — how the Users tab, and the deletion dialog, word a refused account call (`accountErrors.ts`),
 * and the refusal accounts lot A7b adds (contract C5 — plan-phase01Accounts «A7b — Analisi e contratto», decision (2)
 * of the coordinator, 21:10).
 *
 * `PATCH /users/{id}` with `{is_active: true}` on the initial administrator waiting for its setup link answers 409
 * `{detail: {error_code: 'PENDING_SETUP', message}}` and changes nothing (UADM-065, `test_users_admin_api.py`): its
 * password is a secret nobody knows, and the way in is its setup link. The row stops offering «Reactivate» for it
 * (`UserRow.pendingSetup.test.ts`), but the backend stays the authority, as for `LAST_ADMIN`: a list drawn earlier may
 * still ask, and the toast must then say why instead of the generic failure.
 *
 * The contract under test:
 *   - that 409 → `{code: 'PENDING_SETUP', key: 'settings.usersTab.errors.PENDING_SETUP'}`, the server's English
 *     `message` never shown; `PENDING_SETUP` joins `ACCOUNT_ERROR_CODES`; `accountErrorText`, the text of the tab's
 *     toast, is that key translated;
 *   - the key is a sentence in the four catalogues (C6), naming no value `describeAccountError` does not fill — it fills
 *     none, and a `{placeholder}` nobody fills reaches the user raw.
 * The guards, green today: the six codes keep their keys (`USER_LIMIT_REACHED` its subscription page); the answers read
 * from the status (a 404, a 422, a 500 on a deletion, a sentence without a code); a code this build does not know → the
 * generic failure — what `PENDING_SETUP` gets until A7b, hence the reds; and every key the function answers is a
 * sentence in the four catalogues — green on today's codes, which proves the reader, and the gate `PENDING_SETUP`
 * passes through once it joins the list.
 *
 * Accounts lot A-51 (release 1.3, workstream A — the coordinator's OK of 17/10, 14:52): «Cancel setup link» sends
 * `PATCH /users/{id}` with `{is_active: false, cancel_setup: true}`, and when the administrator completed its setup
 * meanwhile the backend answers 409 `{detail: {error_code: 'SETUP_COMPLETED', message}}` and changes nothing (the
 * backend reds of A-51, `test_users_admin_api.py`; the tab's side, `UsersTab.test.ts` UTAB-61…62). The contract under
 * test, as for `PENDING_SETUP`: that 409 → `{code: 'SETUP_COMPLETED', key: 'settings.usersTab.errors.SETUP_COMPLETED'}`,
 * the server's `message` never shown — `SETUP_COMPLETED` joins `ACCOUNT_ERROR_CODES` (AERR-13); and that key is a
 * sentence in the four catalogues, naming no value, as `describeAccountError` fills none for it (AERR-14). Until A-51
 * the code is one this build does not know, so it gets the generic failure (AERR-08's guard) — hence the reds; AERR-11
 * picks it up once it joins the list. Red until A-51, both cases.
 *
 * Accounts lot A-16 (release 1.3, workstream A — «A-11 + A-16 + A-40 + A-26 as one lot: GO, reds first», 17/10):
 * `DELETE /auth/users/me` refuses the last active administrator with a 400 which, until A-16, carried a bare English
 * sentence and no code — and the deletion dialog showed that sentence as it was. Since A-16 the status stays 400 and
 * the body is `{detail: {error_code: 'LAST_ADMIN', message}}`. `LAST_ADMIN` already answers the 409 of
 * `PATCH /users/{id}`, and its sentence («neither deactivated nor demoted») does not fit a deletion; on a deletion the
 * code can only come from one's own (deleting another administrator answers 409 `DEMOTE_FIRST`). The contract under
 * test: on `'delete'`, that 400 → `{code: 'LAST_ADMIN', key: 'settings.usersTab.errors.LAST_ADMIN_DELETION'}`, the
 * server's `message` never shown (AERR-15, AERR-16); that key is a sentence of its own — not `LAST_ADMIN`'s — in the
 * four catalogues, naming no value, as `describeAccountError` fills none for it (AERR-17). The guards, green today:
 * without `'delete'` — the Users tab's PATCH, which passes no action — `LAST_ADMIN` keeps its key (AERR-18); on a
 * deletion the other refusals keep theirs (AERR-19); and a 400 or 409 whose detail is a sentence without a code still
 * shows that sentence (AERR-09, AERR-10: no longer the last administrator's answer, the fallback stays). Red until A-16:
 * AERR-15, AERR-16, AERR-17.
 *
 * The refusals are shaped as axios builds them (`isAxiosError`, `response.status`, `response.data.detail`), with the
 * bodies of `api/v1/users.py` — and of `api/v1/auth.py` for A-16's. Node environment: nothing renders.
 */
import {describe, expect, it, vi} from 'vitest';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {ACCOUNT_ERROR_CODES, accountErrorText, describeAccountError, type AccountError} from './accountErrors';

// --- Refusals -------------------------------------------------------------

/** The server's own sentence: a coded refusal never shows it. */
const SERVER_SENTENCE = 'An English sentence nobody should read';
const BILLING = 'https://billing.example.test/librefolio/subscription';
const PENDING_SETUP_KEY = 'settings.usersTab.errors.PENDING_SETUP';
const SETUP_COMPLETED_KEY = 'settings.usersTab.errors.SETUP_COMPLETED';
/** The refusal of a deactivation or a demotion of the last active administrator (the Users tab's PATCH). */
const LAST_ADMIN_KEY = 'settings.usersTab.errors.LAST_ADMIN';
/** The refusal of the last active administrator's own deletion (A-16): a key of its own, `LAST_ADMIN` does not fit. */
const LAST_ADMIN_DELETION_KEY = 'settings.usersTab.errors.LAST_ADMIN_DELETION';

/**
 * A refusal whose detail is a sentence with no code: still shown as it is (AERR-09, AERR-10). Not the last administrator
 * deleting their own account any more — that one carries `LAST_ADMIN` since A-16 —, any refusal a backend words without one.
 */
const CODELESS_SENTENCE = 'A reason the server gives without a code';

/** The codes `ACCOUNT_ERROR_CODES` lists before A7b. */
const CODES_BEFORE_A7B = ['LAST_ADMIN', 'USER_LIMIT_REACHED', 'REGISTRATION_DISABLED', 'ACCOUNT_PROTECTED', 'SELF_DELETION', 'DEMOTE_FIRST'];

/** An axios-shaped refusal, with the body the backend sends: an object `detail` for a coded refusal, a sentence otherwise. */
function refusal(status: number, detail: unknown): Error {
    return Object.assign(new Error(`Request failed with status code ${status}`), {isAxiosError: true, response: {status, data: {detail}}});
}

/** A coded refusal of `api/v1/users.py`: 409 `{detail: {error_code, message, …extra}}`. */
const conflict = (error_code: string, extra: Record<string, unknown> = {}) => refusal(409, {error_code, message: SERVER_SENTENCE, ...extra});

/** The server's own sentence for the last active administrator's own deletion, as `api/v1/auth.py` words it since A-16. */
const LAST_ADMIN_DELETION_MESSAGE = 'Cannot delete account: you are the last active administrator';

/** `DELETE /auth/users/me` refusing the last active administrator since A-16: the status stays 400, the detail gains a code. */
const LAST_ADMIN_ON_DELETION = refusal(400, {error_code: 'LAST_ADMIN', message: LAST_ADMIN_DELETION_MESSAGE});

/** The answers read from the status, the deletion dialog's `'delete'` included. */
const BY_STATUS: Array<{label: string; failure: unknown; action?: string; expected: AccountError}> = [
    {label: 'a 404, the account gone', failure: refusal(404, 'User not found'), expected: {code: 'NOT_FOUND', key: 'settings.usersTab.errors.NOT_FOUND'}},
    {label: 'a 422, an address refused', failure: refusal(422, [{type: 'value_error', loc: ['body', 'email'], msg: 'value is not a valid email address'}]), expected: {code: 'INVALID_INPUT', key: 'settings.usersTab.errors.INVALID_INPUT'}},
    {label: 'a 500 on a deletion', failure: refusal(500, 'Internal Server Error'), action: 'delete', expected: {code: 'DELETION_FAILED', key: 'settings.usersTab.errors.DELETION_FAILED'}},
    {label: 'a 500 on anything else', failure: refusal(500, 'Internal Server Error'), action: 'reactivate', expected: {code: null, key: 'settings.usersTab.errors.generic'}},
    {label: 'a 400 with its own sentence', failure: refusal(400, CODELESS_SENTENCE), expected: {code: null, key: 'settings.usersTab.errors.generic', message: CODELESS_SENTENCE}},
    {label: 'a 409 with its own sentence', failure: refusal(409, 'Something changed meanwhile'), expected: {code: null, key: 'settings.usersTab.errors.generic', message: 'Something changed meanwhile'}},
    {label: 'a request that never reached the server', failure: new Error('Network Error'), expected: {code: null, key: 'settings.usersTab.errors.generic'}},
    {label: 'null', failure: null, expected: {code: null, key: 'settings.usersTab.errors.generic'}},
];

/** A translator that shows what it was asked: the key in guillemets, then the values it was given. */
function translator() {
    return vi.fn((key: string, options?: {values?: Record<string, string | number>}) => (options?.values ? `«${key}» ${JSON.stringify(options.values)}` : `«${key}»`));
}

// --- Catalogues -----------------------------------------------------------

const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

/** The leaf at a dotted key, read from the catalogue itself. */
function messageOf(catalogue: unknown, key: string): unknown {
    let node = catalogue;
    for (const part of key.split('.')) node = node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined;
    return node;
}

/** The ICU arguments a message names, read as `emailText.test.ts` reads them: `billingUrl` for «… {billingUrl} …». */
function placeholdersOf(message: string): string[] {
    return [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();
}

/** `key` is a sentence in all four catalogues, naming no value but those `params` fills. */
function expectSentenceInEveryCatalogue(key: string, params: AccountError['params']): void {
    const filled = Object.keys(params ?? {});
    for (const [language, catalogue] of Object.entries(CATALOGUES)) {
        const message = messageOf(catalogue, key);
        expect(typeof message === 'string' && message.trim() !== '', `${language}: ${key} is a sentence of the catalogue`).toBe(true);
        const unfilled = placeholdersOf(message as string).filter((name) => !filled.includes(name));
        expect(unfilled, `${language}: ${key} names only the values describeAccountError fills (${filled.join(', ') || 'none'})`).toEqual([]);
    }
}

// =========================================================================
describe('describeAccountError — the pending administrator (A7b, C5)', () => {
    // red until A7b
    it('AERR-01: the 409 PENDING_SETUP → its code and settings.usersTab.errors.PENDING_SETUP, never the server sentence', () => {
        expect(describeAccountError(conflict('PENDING_SETUP'))).toEqual({code: 'PENDING_SETUP', key: PENDING_SETUP_KEY});
    });

    // red until A7b
    it('AERR-02: PENDING_SETUP joins ACCOUNT_ERROR_CODES', () => {
        expect(ACCOUNT_ERROR_CODES).toContain('PENDING_SETUP');
    });

    // red until A7b
    it('AERR-03: the text of the tab’s toast — accountErrorText — is that key translated, not the server sentence', () => {
        const text = accountErrorText(describeAccountError(conflict('PENDING_SETUP')), translator());

        expect(text).toContain(`«${PENDING_SETUP_KEY}»`);
        expect(text).not.toContain(SERVER_SENTENCE);
    });

    // red until A7b
    it('AERR-04: settings.usersTab.errors.PENDING_SETUP is a sentence in the four catalogues, naming no value it is not given', () => {
        expectSentenceInEveryCatalogue(PENDING_SETUP_KEY, describeAccountError(conflict('PENDING_SETUP')).params);
    });
});

// =========================================================================
describe('describeAccountError — what it answers before A7b', () => {
    // guard
    it.each(CODES_BEFORE_A7B)('AERR-05: a 409 %s → its code and its key, never the server sentence', (code) => {
        expect(describeAccountError(conflict(code))).toEqual({code, key: `settings.usersTab.errors.${code}`});
    });

    // guard
    it('AERR-06: USER_LIMIT_REACHED with a subscription page carries it, and the text hands it to the translator', () => {
        const error = describeAccountError(conflict('USER_LIMIT_REACHED', {limit: 6, used: 6, billing_url: BILLING}));

        expect(error).toEqual({code: 'USER_LIMIT_REACHED', key: 'settings.usersTab.errors.USER_LIMIT_REACHED', params: {billingUrl: BILLING}});
        expect(accountErrorText(error, translator())).toBe(`«settings.usersTab.errors.USER_LIMIT_REACHED» ${JSON.stringify({billingUrl: BILLING})}`);
    });

    // guard
    it('AERR-07: ACCOUNT_ERROR_CODES keeps the six codes it had', () => {
        expect(ACCOUNT_ERROR_CODES).toEqual(expect.arrayContaining(CODES_BEFORE_A7B));
    });

    // guard — what PENDING_SETUP gets until A7b, hence the reds above
    it('AERR-08: a code this build does not know → the generic failure, and still not the server sentence', () => {
        expect(describeAccountError(conflict('SOMETHING_A_LATER_BACKEND_ADDS'))).toEqual({code: null, key: 'settings.usersTab.errors.generic'});
    });

    // guard
    it.each(BY_STATUS)('AERR-09: $label → as before', ({failure, action, expected}) => {
        expect(describeAccountError(failure, action)).toEqual(expected);
    });

    // guard
    it('AERR-10: a refusal with its own sentence and no code shows that sentence, without asking the translator', () => {
        const translate = translator();

        expect(accountErrorText(describeAccountError(refusal(400, CODELESS_SENTENCE)), translate)).toBe(CODELESS_SENTENCE);
        expect(translate).not.toHaveBeenCalled();
    });
});

// =========================================================================
describe('describeAccountError — every key it answers is a sentence in the four catalogues', () => {
    // guard — today's codes prove the reader; PENDING_SETUP passes through here once it joins the list
    it.each([...ACCOUNT_ERROR_CODES])('AERR-11: the key of %s, with the values it is given', (code) => {
        expectSentenceInEveryCatalogue(`settings.usersTab.errors.${code}`, describeAccountError(conflict(code)).params);
    });

    // guard
    it.each(['NOT_FOUND', 'INVALID_INPUT', 'DELETION_FAILED', 'generic'])('AERR-12: the key of %s, read from the status: no value given', (name) => {
        expectSentenceInEveryCatalogue(`settings.usersTab.errors.${name}`, undefined);
    });
});

// =========================================================================
describe('describeAccountError — a setup completed meanwhile (A-51)', () => {
    // red until A-51
    it('AERR-13: the 409 SETUP_COMPLETED → its code and settings.usersTab.errors.SETUP_COMPLETED, never the server sentence', () => {
        expect(describeAccountError(conflict('SETUP_COMPLETED'))).toEqual({code: 'SETUP_COMPLETED', key: SETUP_COMPLETED_KEY});
    });

    // red until A-51
    it('AERR-14: settings.usersTab.errors.SETUP_COMPLETED is a sentence in the four catalogues, naming no value it is not given', () => {
        expectSentenceInEveryCatalogue(SETUP_COMPLETED_KEY, describeAccountError(conflict('SETUP_COMPLETED')).params);
    });
});

// =========================================================================
describe('describeAccountError — the last active administrator deleting their own account (A-16)', () => {
    // red until A-16
    it('AERR-15: on a deletion, the 400 LAST_ADMIN → its code and settings.usersTab.errors.LAST_ADMIN_DELETION, never the server sentence', () => {
        expect(describeAccountError(LAST_ADMIN_ON_DELETION, 'delete')).toEqual({code: 'LAST_ADMIN', key: LAST_ADMIN_DELETION_KEY});
    });

    // red until A-16
    it('AERR-16: the text of the dialog and of its toast — accountErrorText — is that key translated: neither the server sentence nor LAST_ADMIN’s', () => {
        const text = accountErrorText(describeAccountError(LAST_ADMIN_ON_DELETION, 'delete'), translator());

        expect(text).toBe(`«${LAST_ADMIN_DELETION_KEY}»`);
        expect(text).not.toContain(LAST_ADMIN_DELETION_MESSAGE);
    });

    // red until A-16
    it('AERR-17: settings.usersTab.errors.LAST_ADMIN_DELETION is a sentence of its own in the four catalogues — not LAST_ADMIN’s —, naming no value it is not given', () => {
        expectSentenceInEveryCatalogue(LAST_ADMIN_DELETION_KEY, describeAccountError(LAST_ADMIN_ON_DELETION, 'delete').params);
        for (const [language, catalogue] of Object.entries(CATALOGUES)) {
            expect(messageOf(catalogue, LAST_ADMIN_DELETION_KEY), `${language}: ${LAST_ADMIN_DELETION_KEY} speaks of a deletion, not with the words of ${LAST_ADMIN_KEY}`).not.toBe(messageOf(catalogue, LAST_ADMIN_KEY));
        }
    });

    // guard — the Users tab passes no action; deactivating and demoting are the two refusals LAST_ADMIN answers there
    it.each([undefined, 'deactivate', 'demote'])('AERR-18: without a deletion (action %s), the 409 LAST_ADMIN keeps settings.usersTab.errors.LAST_ADMIN', (action) => {
        expect(describeAccountError(conflict('LAST_ADMIN'), action)).toEqual({code: 'LAST_ADMIN', key: LAST_ADMIN_KEY});
    });

    // guard — the deletion of another account (`DELETE /users/{id}`) refuses with these: only LAST_ADMIN changes key
    it.each(['SELF_DELETION', 'DEMOTE_FIRST', 'ACCOUNT_PROTECTED'])('AERR-19: on a deletion, the 409 %s keeps its own key', (code) => {
        expect(describeAccountError(conflict(code), 'delete')).toEqual({code, key: `settings.usersTab.errors.${code}`});
    });
});
