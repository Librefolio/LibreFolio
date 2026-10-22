/**
 * The words and colours of the Email tab: every code the API sends maps to a whole i18n key, and every state to whole
 * role classes, so that the i18n audit and the colour gates see each one (theme-roles skill, rule 6).
 */
import type {EmailStatus, EmailTestFailure} from './emailApi';
import type {LinksProbeState} from './emailLinks';
import type {ForgotFailure} from './forgotPasswordApi';
import type {LinkSendFailure} from './sendLinkApi';
import type {ResendFailure, VerificationLinkRefusal} from './verificationApi';

type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

export const STATE_LABEL_KEYS: Record<EmailStatus['state'], string> = {
    off: 'email.state.off',
    ready: 'email.state.ready',
    invalid: 'email.state.invalid',
};

export const STATE_BADGE_CLASSES: Record<EmailStatus['state'], string> = {
    off: 'inline-flex items-center gap-1 rounded-full bg-lf-neutral px-2.5 py-0.5 text-xs font-semibold text-lf-secondary',
    ready: 'inline-flex items-center gap-1 rounded-full bg-lf-success-soft px-2.5 py-0.5 text-xs font-semibold text-lf-success-on-soft',
    invalid: 'inline-flex items-center gap-1 rounded-full bg-lf-danger-soft px-2.5 py-0.5 text-xs font-semibold text-lf-danger-on-soft',
};

/** A check worth a line in the tab: anything but `ok`. */
export const NOTICE_CLASSES: Record<'info' | 'warning' | 'error', string> = {
    info: 'rounded-lg border border-lf-info-line bg-lf-info-soft px-4 py-3 text-sm text-lf-info-on-soft',
    warning: 'rounded-lg border border-lf-warning-line bg-lf-warning-soft px-4 py-3 text-sm text-lf-warning-on-soft',
    error: 'rounded-lg border border-lf-danger-line bg-lf-danger-soft px-4 py-3 text-sm text-lf-danger-on-soft',
};

export const OUTCOME_CLASSES: Record<'sent' | 'failed', string> = {
    sent: 'rounded-lg border border-lf-success-line bg-lf-success-soft px-4 py-3 text-sm text-lf-success-on-soft',
    failed: 'rounded-lg border border-lf-danger-line bg-lf-danger-soft px-4 py-3 text-sm text-lf-danger-on-soft',
};

/** The check of the emailed links' base: what to say for each outcome. */
export const LINKS_PROBE_KEYS: Record<LinksProbeState, string> = {
    checking: 'email.links.probe.checking',
    match: 'email.links.probe.match',
    otherInstance: 'email.links.probe.otherInstance',
    unreachable: 'email.links.probe.unreachable',
    insecure: 'email.links.probe.insecure',
    invalid: 'email.links.probe.invalid',
};

/** A running check and a match read as a line; anything else is a configuration notice, with a warning's colours. */
export const LINKS_PROBE_CLASSES: Record<LinksProbeState, string> = {
    checking: 'text-sm text-lf-muted',
    match: 'text-sm text-lf-success',
    otherInstance: 'rounded-lg border border-lf-warning-line bg-lf-warning-soft px-4 py-3 text-sm text-lf-warning-on-soft',
    unreachable: 'rounded-lg border border-lf-warning-line bg-lf-warning-soft px-4 py-3 text-sm text-lf-warning-on-soft',
    insecure: 'rounded-lg border border-lf-warning-line bg-lf-warning-soft px-4 py-3 text-sm text-lf-warning-on-soft',
    invalid: 'rounded-lg border border-lf-warning-line bg-lf-warning-soft px-4 py-3 text-sm text-lf-warning-on-soft',
};

/** Whether an outcome is a notice the administrator may want to check again: anything but a running check or a match. */
export function linksProbeWarns(state: LinksProbeState | null): boolean {
    return state !== null && state !== 'checking' && state !== 'match';
}

const PROBLEM_KEYS: Record<string, string> = {
    SMTP_HOST_INVALID: 'email.problems.SMTP_HOST_INVALID',
    SMTP_TLS_INVALID: 'email.problems.SMTP_TLS_INVALID',
    SMTP_PORT_INVALID: 'email.problems.SMTP_PORT_INVALID',
    SMTP_FROM_MISSING: 'email.problems.SMTP_FROM_MISSING',
    SMTP_FROM_INVALID: 'email.problems.SMTP_FROM_INVALID',
    SMTP_REPLY_TO_INVALID: 'email.problems.SMTP_REPLY_TO_INVALID',
    SMTP_MAX_PER_HOUR_INVALID: 'email.problems.SMTP_MAX_PER_HOUR_INVALID',
    SMTP_PASSWORD_UNREADABLE: 'email.problems.SMTP_PASSWORD_UNREADABLE',
    SMTP_CREDENTIALS_INCOMPLETE: 'email.problems.SMTP_CREDENTIALS_INCOMPLETE',
};

const SMTP_ERROR_KEYS: Record<string, string> = {
    CONNECTION_FAILED: 'email.smtpErrors.CONNECTION_FAILED',
    TLS_FAILED: 'email.smtpErrors.TLS_FAILED',
    AUTH_FAILED: 'email.smtpErrors.AUTH_FAILED',
    SENDER_REFUSED: 'email.smtpErrors.SENDER_REFUSED',
    RECIPIENT_REFUSED: 'email.smtpErrors.RECIPIENT_REFUSED',
    TIMEOUT: 'email.smtpErrors.TIMEOUT',
    SEND_FAILED: 'email.smtpErrors.SEND_FAILED',
};

/** The key of ``code`` in ``keys``: only its own entries, so a code such as ``constructor`` finds nothing. */
function ownKey(keys: Record<string, string>, code: string | null | undefined): string | undefined {
    return code && Object.hasOwn(keys, code) ? keys[code] : undefined;
}

/** The i18n key that explains a configuration problem; its `{variable}` names the variable at fault. */
export function problemKey(problem: string | null | undefined): string {
    return ownKey(PROBLEM_KEYS, problem) ?? 'email.problems.unknown';
}

/** Whole minutes, at least one: how long until an email fits again. */
export function minutesUntil(seconds: number | null | undefined): number {
    return Math.max(1, Math.ceil((seconds ?? 60) / 60));
}

/** What to tell the administrator when the test email failed. */
export function testFailureMessage(translate: Translate, failure: EmailTestFailure): string {
    switch (failure.errorCode) {
        case 'EMAIL_UNAVAILABLE':
            return translate('email.test.errors.EMAIL_UNAVAILABLE');
        case 'EMAIL_RATE_LIMITED':
            return translate('email.test.errors.EMAIL_RATE_LIMITED', {values: {minutes: minutesUntil(failure.retryAfter)}});
        case 'EMAIL_RECIPIENT_INVALID':
            return translate('email.test.errors.EMAIL_RECIPIENT_INVALID');
        case 'EMAIL_DELIVERY_FAILED':
            return translate(ownKey(SMTP_ERROR_KEYS, failure.smtpCode) ?? 'email.smtpErrors.SEND_FAILED');
        default:
            return translate('email.test.errors.generic');
    }
}

/** What the page of a verification link shows: a link waiting for its owner's click (lot E-25), the wait, why the link
 * cannot be used, a blocked instance, or a check that failed. */
export type VerifyPageStatus = 'ready' | 'checking' | VerificationLinkRefusal | 'blocked' | 'missing' | 'error';

export const VERIFY_PAGE_KEYS: Record<VerifyPageStatus, string> = {
    ready: 'email.verification.page.ready',
    checking: 'email.verification.page.checking',
    expired: 'email.verification.page.expired',
    consumed: 'email.verification.page.consumed',
    revoked: 'email.verification.page.revoked',
    unknown: 'email.verification.page.unknown',
    blocked: 'email.verification.page.blocked',
    missing: 'email.verification.page.missing',
    error: 'email.verification.page.error',
};

/** The sign-in's «send the link again» failed: what to tell its owner. */
export function resendFailureMessage(translate: Translate, failure: ResendFailure): string {
    switch (failure.errorCode) {
        case 'INVALID_CREDENTIALS':
            return translate('email.verification.resendErrors.INVALID_CREDENTIALS');
        case 'INSTANCE_BLOCKED':
            // The hosting provider blocks the instance: the text of lot A7b, one home for it.
            return translate('auth.instanceBlocked');
        case 'EMAIL_RATE_LIMITED':
            return translate('email.verification.resendErrors.EMAIL_RATE_LIMITED', {values: {minutes: minutesUntil(failure.retryAfter)}});
        case 'EMAIL_VERIFICATION_NOT_NEEDED':
            return translate('email.verification.resendErrors.EMAIL_VERIFICATION_NOT_NEEDED');
        case 'USER_LIMIT_REACHED':
            return translate('email.verification.resendErrors.USER_LIMIT_REACHED');
        case 'ACCOUNT_DISABLED':
            return translate('email.verification.resendErrors.ACCOUNT_DISABLED');
        case 'EMAIL_UNAVAILABLE':
        case 'EMAIL_LINKS_UNAVAILABLE':
        case 'EMAIL_DELIVERY_FAILED':
        case 'EMAIL_RECIPIENT_INVALID':
            return translate('email.verification.resendErrors.unavailable');
        default:
            return translate('email.verification.resendErrors.generic');
    }
}

/** «Send by email» failed: what to tell the administrator. */
export function linkSendFailureMessage(translate: Translate, failure: LinkSendFailure): string {
    switch (failure.errorCode) {
        case 'EMAIL_UNAVAILABLE':
            return translate('email.sendLink.errors.EMAIL_UNAVAILABLE');
        case 'EMAIL_LINKS_UNAVAILABLE':
            return translate('email.sendLink.errors.EMAIL_LINKS_UNAVAILABLE');
        case 'EMAIL_LINK_INVALID':
            return translate('email.sendLink.errors.EMAIL_LINK_INVALID');
        case 'EMAIL_ACCOUNT_INACTIVE':
            return translate('email.sendLink.errors.EMAIL_ACCOUNT_INACTIVE');
        case 'EMAIL_RECIPIENT_REQUIRED':
            return translate('email.sendLink.errors.EMAIL_RECIPIENT_REQUIRED');
        case 'EMAIL_RECIPIENT_NOT_ALLOWED':
            return translate('email.sendLink.errors.EMAIL_RECIPIENT_NOT_ALLOWED');
        case 'EMAIL_RECIPIENT_INVALID':
            return translate('email.sendLink.errors.EMAIL_RECIPIENT_INVALID');
        case 'EMAIL_RATE_LIMITED':
            return translate('email.sendLink.errors.EMAIL_RATE_LIMITED', {values: {minutes: minutesUntil(failure.retryAfter)}});
        case 'EMAIL_DELIVERY_FAILED':
            // The refused recipient is the invitee or the account here, not the administrator's own address of the test email.
            if (failure.smtpCode === 'RECIPIENT_REFUSED') return translate('email.sendLink.errors.RECIPIENT_REFUSED');
            return translate(ownKey(SMTP_ERROR_KEYS, failure.smtpCode) ?? 'email.smtpErrors.SEND_FAILED');
        default:
            return translate('email.sendLink.errors.generic');
    }
}

/** «Forgot password» was refused: what to tell whoever asked. */
export function forgotFailureMessage(translate: Translate, failure: ForgotFailure): string {
    switch (failure.errorCode) {
        case 'EMAIL_UNAVAILABLE':
        case 'EMAIL_LINKS_UNAVAILABLE':
            return translate('email.forgot.errors.unavailable');
        case 'EMAIL_RATE_LIMITED':
            return translate('email.forgot.errors.EMAIL_RATE_LIMITED', {values: {minutes: minutesUntil(failure.retryAfter)}});
        default:
            return translate('email.forgot.errors.generic');
    }
}
