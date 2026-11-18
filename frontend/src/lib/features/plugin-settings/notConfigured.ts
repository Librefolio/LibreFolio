/**
 * A provider that is not configured cannot be used (project 76, D7, lot N3): which case of the common window it is in.
 *
 * The provider lists (`GET /assets/provider`, `GET /fx/providers`) say, for the caller, whether each provider is
 * configured and, when not, why (N1, N2b): `missing_reason` is `missing_fields` (a value to set) or
 * `invalid_locked_setting` (an environment variable that locks a field has an invalid value), and `invalid_variables`
 * names those variables outside the managed profile, never in it. The case decides the window's text and buttons:
 *
 * - `missing_admin` (A): the administrator can set the value, «Configure»;
 * - `missing_member` (B): another user asks an administrator, a link to the read-only settings;
 * - `invalid_admin` (C): the variable is fixed on the server, named, no «Configure»;
 * - `invalid_limit_admin`: the same for a call-limit variable, the consultant's text of mock section 2.4;
 * - `invalid_member`: another user is told the provider is stopped (mock section 2.4, any variable);
 * - `managed` (D): the managed profile names no variable, for everyone.
 */

/** What the window reads of a provider list entry: the readiness fields of N1 and N2b. */
export interface ProviderReadiness {
    configured?: boolean;
    missing_settings?: string[];
    missing_reason?: string | null;
    invalid_variables?: string[];
}

export type NotConfiguredCase = 'missing_admin' | 'missing_member' | 'invalid_admin' | 'invalid_limit_admin' | 'invalid_member' | 'managed';

/** The core's call-limit variables end with the window: `…_CALL_LIMIT_DAY` (project 76, U4). */
const CALL_LIMIT_VARIABLE = /_CALL_LIMIT_(MINUTE|HOUR|DAY|WEEK|MONTH)$/;

/** Whether the server says this provider is not configured; a list without the field (an older server) is configured. */
export function needsSetup(info: ProviderReadiness | null | undefined): boolean {
    return info?.configured === false;
}

/** Whether ``name`` is one of the core's call-limit variables. */
export function isCallLimitVariable(name: string): boolean {
    return CALL_LIMIT_VARIABLE.test(name);
}

/** The window's case for a provider that is not configured, seen by an administrator or another user. */
export function notConfiguredCase(info: ProviderReadiness, isAdmin: boolean): NotConfiguredCase {
    if (info.missing_reason !== 'invalid_locked_setting') return isAdmin ? 'missing_admin' : 'missing_member';
    const variables = info.invalid_variables ?? [];
    // The managed profile never names a variable: an invalid one with no name is that profile (decision N2b).
    if (variables.length === 0) return 'managed';
    if (!isAdmin) return 'invalid_member';
    return variables.every(isCallLimitVariable) ? 'invalid_limit_admin' : 'invalid_admin';
}
