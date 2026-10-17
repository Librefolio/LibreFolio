/**
 * Why `POST /auth/register` refused an account, as the registration card says it.
 *
 * The refusals of the registration rule carry an error code (`_REGISTRATION_REFUSALS` in `api/v1/auth.py`); a name or
 * an address already taken keeps the plain message it always had; a malformed field comes as Pydantic's list.
 */

import {isAxiosError} from 'axios';
import {isInstanceBlockedError} from '$lib/features/instance/instanceBlock.svelte';

/** A catalogue key, or the server's own words when nothing better is known. */
export type RegistrationErrorText = {key: string} | {raw: string};

const REFUSAL_KEYS: Record<string, string> = {
    REGISTRATION_DISABLED: 'auth.registrationDisabled',
    INVITE_REQUIRED: 'auth.registrationInviteOnly',
    INVITE_INVALID: 'auth.link.unknown',
    // Whoever registers is not signed in: the message says the server is full, and nothing about how full.
    USER_LIMIT_REACHED: 'auth.userLimitReached',
    // The password misses a rule of the server (decision 37): the checklist under the field says which.
    PASSWORD_TOO_WEAK: 'auth.validation.passwordTooWeak',
    // Email verification is required and no email with a link can go out now (workstream E)
    EMAIL_VERIFICATION_UNAVAILABLE: 'email.verification.signUpUnavailable',
    // A new username holding an @ (A-21a): the sign-in would read it as an email address
    USERNAME_INVALID: 'auth.validation.usernameNoAt',
};

function describeFieldErrors(errors: unknown[]): RegistrationErrorText {
    const first = errors[0] as {loc?: unknown; msg?: unknown} | undefined;
    const loc = Array.isArray(first?.loc) ? first.loc : [];
    const msg = typeof first?.msg === 'string' ? first.msg : '';
    if (loc.includes('email')) {
        return {key: msg.includes('special-use') || msg.includes('reserved') ? 'auth.validation.invalidEmailDomain' : 'auth.validation.invalidEmail'};
    }
    if (loc.includes('username')) return {key: 'auth.validation.usernameMinLength'};
    if (loc.includes('password')) return {key: 'auth.validation.passwordTooWeak'};
    return {key: 'auth.registrationFailed'};
}

export function describeRegistrationError(error: unknown): RegistrationErrorText {
    // The hosting provider blocked the instance (A-13): an anonymous caller gets a 401, one with a session a 423 (H)
    const status = isAxiosError(error) ? error.response?.status : undefined;
    if (status === 401 || (isAxiosError(error) && isInstanceBlockedError(status, error.response?.data))) return {key: 'auth.instanceBlocked'};
    const detail: unknown = isAxiosError(error) ? error.response?.data?.detail : undefined;
    if (Array.isArray(detail)) return describeFieldErrors(detail);
    if (typeof detail === 'object' && detail !== null) {
        const code = (detail as {error_code?: unknown}).error_code;
        return {key: typeof code === 'string' && code in REFUSAL_KEYS ? REFUSAL_KEYS[code] : 'auth.registrationFailed'};
    }
    if (typeof detail === 'string') {
        // The backend capitalises them ("Username already taken", "Email already registered"): compare case-folded.
        const lowered = detail.toLowerCase();
        if (lowered.includes('username')) return {key: 'auth.validation.usernameTaken'};
        if (lowered.includes('email')) return {key: 'auth.validation.emailTaken'};
        return {raw: detail};
    }
    return {key: 'auth.registrationFailed'};
}
