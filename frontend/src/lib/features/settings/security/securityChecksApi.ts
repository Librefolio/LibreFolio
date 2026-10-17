/**
 * The seam of the «Security» tab over the generated client: `GET /api/v1/security/checks` (administrators only, lot
 * A8a). Every configuration check of the instance, evaluated when asked, in the platform's order, each with its
 * severity and the key and the parameters of its message.
 */
import {zodiosApi} from '$lib/api';

export type SecurityCheckSeverity = 'ok' | 'info' | 'warning' | 'error';

export interface SecurityCheck {
    check_id: string;
    severity: SecurityCheckSeverity;
    i18n_key: string;
    detail: Record<string, string | number>;
}

/** The checks as the server evaluated them now; a refusal or a network error propagates. */
export async function fetchSecurityChecks(): Promise<SecurityCheck[]> {
    const response = await zodiosApi.list_security_checks_api_v1_security_checks_get();
    return response.items as SecurityCheck[];
}
