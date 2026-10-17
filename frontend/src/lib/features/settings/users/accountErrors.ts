/** The answer of a failed account call, as a code and the key of the message to show (Users tab, deletion dialog). */

export const ACCOUNT_ERROR_CODES = ['LAST_ADMIN', 'USER_LIMIT_REACHED', 'REGISTRATION_DISABLED', 'ACCOUNT_PROTECTED', 'SELF_DELETION', 'DEMOTE_FIRST', 'PENDING_SETUP', 'SETUP_COMPLETED'] as const;

export type AccountErrorCode = (typeof ACCOUNT_ERROR_CODES)[number] | 'NOT_FOUND' | 'DELETION_FAILED' | 'INVALID_INPUT';

export interface AccountError {
    code: AccountErrorCode | null;
    key: string;
    params?: Record<string, string | number>;
    /** The server's own sentence, for a refusal that carries no code (shown instead of the generic message). */
    message?: string;
}

interface ErrorResponse {
    status?: number;
    data?: {detail?: unknown};
}

/** `error` (an Axios error, or anything) described for the UI; `action` is `'delete'` for a deletion, whose 500 means that nothing was deleted. */
export function describeAccountError(error: unknown, action?: string): AccountError {
    const response = (error as {response?: ErrorResponse} | null | undefined)?.response;
    const detail = response?.data?.detail;
    const code = detail !== null && typeof detail === 'object' ? (detail as {error_code?: unknown}).error_code : undefined;
    if (typeof code === 'string' && (ACCOUNT_ERROR_CODES as readonly string[]).includes(code)) {
        const billingUrl = (detail as {billing_url?: unknown}).billing_url;
        return {code: code as AccountErrorCode, key: `settings.usersTab.errors.${code}`, params: typeof billingUrl === 'string' && billingUrl ? {billingUrl} : undefined};
    }
    if (response?.status === 404) {
        return {code: 'NOT_FOUND', key: 'settings.usersTab.errors.NOT_FOUND'};
    }
    if (response?.status === 422) {
        return {code: 'INVALID_INPUT', key: 'settings.usersTab.errors.INVALID_INPUT'};
    }
    if (response?.status === 500 && action === 'delete') {
        return {code: 'DELETION_FAILED', key: 'settings.usersTab.errors.DELETION_FAILED'};
    }
    // A refusal without a code still says why (the only administrator deleting their own account answers 400 so)
    if ((response?.status === 400 || response?.status === 409) && typeof detail === 'string' && detail.trim()) {
        return {code: null, key: 'settings.usersTab.errors.generic', message: detail};
    }
    return {code: null, key: 'settings.usersTab.errors.generic'};
}

/** The text to show for `error`: the server's own sentence when it gave one without a code, the translated message otherwise. */
export function accountErrorText(error: AccountError, translate: (key: string, options?: {values?: Record<string, string | number>}) => string): string {
    return error.message ?? translate(error.key, error.params ? {values: error.params} : undefined);
}
