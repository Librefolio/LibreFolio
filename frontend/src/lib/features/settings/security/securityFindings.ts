/**
 * What the «Security» tab lists (lot A8b), as a pure function of the server's checks and of what only the browser
 * knows.
 *
 * - `attention`: every check that is not `ok`, most severe first (error, warning, info), each severity in the server's
 *   order; then, after the server's findings of its severity, the browser's own: open registration reached through a
 *   host outside the local network (`openRegistrationNoticeFor`, lot A7b).
 * - `passed`: the `ok` checks, in the server's order.
 * - An in-app link where a setting of the app fixes it: the email checks → the Email tab, the plugin secrets → the
 *   Plugins tab, open registration → what its notice links to.
 * - `attentionCount`: the badge of the tab, errors and warnings; `info` is listed and not counted.
 */
import {openRegistrationNoticeFor} from '$lib/features/auth/openRegistrationNotice.svelte';
import type {SecurityCheck} from './securityChecksApi';

export type FindingSeverity = 'error' | 'warning' | 'info';

export interface FindingAction {
    labelKey: string;
    href: string;
}

export interface SecurityFinding {
    id: string;
    severity: FindingSeverity;
    messageKey: string;
    params: Record<string, string | number>;
    action?: FindingAction;
    source: 'server' | 'browser';
}

export interface BrowserSecurityState {
    registrationMode: string;
    registrationLocked: boolean;
    /** The host the browser reached the instance through, as `location.hostname` writes it. */
    hostname: string;
}

export interface SecurityFindings {
    attention: SecurityFinding[];
    passed: SecurityFinding[];
}

const SEVERITY_RANK: Record<FindingSeverity, number> = {error: 0, warning: 1, info: 2};

const OPEN_EMAIL: FindingAction = {labelKey: 'settings.securityTab.openEmail', href: '/settings?tab=email'};
const OPEN_PLUGINS: FindingAction = {labelKey: 'settings.securityTab.openPlugins', href: '/settings?tab=plugins'};

/** The in-app link of a server check, where a setting of the app fixes it. */
const SERVER_ACTIONS: Record<string, FindingAction> = {
    'email.smtp': OPEN_EMAIL,
    'email.smtp_encryption': OPEN_EMAIL,
    'email.links': OPEN_EMAIL,
    'platform.plugin_secrets': OPEN_PLUGINS,
};

function fromCheck(check: SecurityCheck, severity: FindingSeverity, withAction: boolean): SecurityFinding {
    const action = withAction ? SERVER_ACTIONS[check.check_id] : undefined;
    return {
        id: check.check_id,
        severity,
        messageKey: check.i18n_key,
        params: {...check.detail},
        ...(action ? {action: {...action}} : {}),
        source: 'server',
    };
}

export function securityFindings(checks: readonly SecurityCheck[], browser: BrowserSecurityState): SecurityFindings {
    const attention: SecurityFinding[] = [];
    const passed: SecurityFinding[] = [];
    for (const check of checks) {
        if (check.severity === 'ok') passed.push(fromCheck(check, 'info', false));
        else attention.push(fromCheck(check, check.severity, true));
    }
    const notice = openRegistrationNoticeFor({isAdmin: true, ...browser});
    if (notice) {
        attention.push({
            id: notice.id,
            severity: 'warning',
            messageKey: notice.messageKey,
            params: {...(notice.params ?? {})},
            ...(notice.action ? {action: {labelKey: notice.action.labelKey, href: notice.action.href}} : {}),
            source: 'browser',
        });
    }
    // A stable sort: within a severity the server's order holds, and the browser's finding, pushed last, comes after
    attention.sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]);
    return {attention, passed};
}

/** The badge: the findings that ask for the administrator, errors and warnings. */
export function attentionCount(findings: Pick<SecurityFindings, 'attention'>): number {
    return findings.attention.filter((finding) => finding.severity === 'error' || finding.severity === 'warning').length;
}

/** The dot's state (N69-1): the worst of the findings the badge counts, an error before a warning; null with none. */
export function attentionSeverity(findings: Pick<SecurityFindings, 'attention'>): 'error' | 'warning' | null {
    if (findings.attention.some((finding) => finding.severity === 'error')) return 'error';
    if (findings.attention.some((finding) => finding.severity === 'warning')) return 'warning';
    return null;
}
