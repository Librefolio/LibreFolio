/**
 * describeRegistrationError and email verification (lot E5b, developer decision 44): what the sign-up form says when
 * `POST /api/v1/auth/register` answers 409 `EMAIL_VERIFICATION_UNAVAILABLE` — the instance requires a verified address
 * and cannot send the email with the link now.
 *
 * The contract under test: that code → `email.verification.signUpUnavailable`, and it is a sentence in the four
 * catalogues; the codes `registrationErrors.test.ts` (workstream A's) pins keep their keys.
 *
 * Node environment: nothing here renders. Red until E5b is applied.
 */
import {describe, expect, it} from 'vitest';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {describeRegistrationError} from './registrationErrors';

/** The 409 of `POST /auth/register` (`backend/app/api/v1/auth.py`), as the generated client rejects with it. */
function refused(errorCode: string): unknown {
    return {isAxiosError: true, response: {status: 409, data: {detail: {error_code: errorCode, message: 'This instance cannot send the verification email now'}}}};
}

describe('describeRegistrationError — EMAIL_VERIFICATION_UNAVAILABLE', () => {
    it('RVR-01: the 409 EMAIL_VERIFICATION_UNAVAILABLE → email.verification.signUpUnavailable', () => {
        expect(describeRegistrationError(refused('EMAIL_VERIFICATION_UNAVAILABLE'))).toEqual({key: 'email.verification.signUpUnavailable'});
    });

    it('RVR-02: the other refusals keep their keys: USER_LIMIT_REACHED is still auth.userLimitReached', () => {
        expect(describeRegistrationError(refused('USER_LIMIT_REACHED'))).toEqual({key: 'auth.userLimitReached'});
    });

    it.each(Object.entries({en, it: itCatalogue, fr, es}))('RVR-03: email.verification.signUpUnavailable is a sentence in %s', (_language, catalogue) => {
        const message = (catalogue as {email?: {verification?: {signUpUnavailable?: unknown}}}).email?.verification?.signUpUnavailable;

        expect(typeof message === 'string' && message.trim().length > 0).toBe(true);
    });
});
