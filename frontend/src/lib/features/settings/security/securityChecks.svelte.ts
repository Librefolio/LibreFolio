/**
 * The state of the «Security» checks (lot A8b): one read of `GET /security/checks` per page load, shared by the tab and
 * by the badge of its tab and of the «Administration» group, which the Settings page asks for before the tab is
 * opened (`prefetch` of the registry).
 *
 * - `ensureLoaded()` reads once: nothing while a read is under way or after one succeeded; again after a failure.
 *   Concurrent calls share one request.
 * - `reload()` reads again (the tab's «check again»); the last checks stay listed meanwhile, and after a failure.
 * - `findings` and `attentionCount` follow the checks and what the browser knows (the public configuration and the
 *   host of the page); before the first answer they are empty.
 */
import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {fetchSecurityChecks, type SecurityCheck} from './securityChecksApi';
import {attentionCount, securityFindings, type BrowserSecurityState, type SecurityFindings} from './securityFindings';

export type SecurityChecksStatus = 'idle' | 'loading' | 'ready' | 'error';

export interface SecurityChecksDependencies {
    fetch?: () => Promise<SecurityCheck[]>;
    browser?: () => BrowserSecurityState;
}

/** The public configuration once the server gave it (before, an open instance would warn for nothing) and the host. */
function browserState(): BrowserSecurityState {
    const accounts = instanceConfig.loaded ? instanceConfig.config.accounts : null;
    return {
        registrationMode: accounts?.registration_mode ?? '',
        registrationLocked: accounts?.registration_locked === true,
        hostname: typeof window === 'undefined' ? '' : window.location.hostname,
    };
}

const NO_FINDINGS: SecurityFindings = {attention: [], passed: []};

export function createSecurityChecks(dependencies: SecurityChecksDependencies = {}) {
    const fetchChecks = dependencies.fetch ?? fetchSecurityChecks;
    const browser = dependencies.browser ?? browserState;

    let status = $state<SecurityChecksStatus>('idle');
    let checks = $state<SecurityCheck[]>([]);
    let answered = $state(false);
    let pending: Promise<void> | null = null;

    function read(): Promise<void> {
        if (pending) return pending;
        status = 'loading';
        const attempt = fetchChecks()
            .then(
                (items) => {
                    checks = items;
                    answered = true;
                    status = 'ready';
                },
                () => {
                    status = 'error';
                },
            )
            .finally(() => {
                if (pending === attempt) pending = null;
            });
        pending = attempt;
        return attempt;
    }

    return {
        get status(): SecurityChecksStatus {
            return status;
        },
        get checks(): SecurityCheck[] {
            return checks;
        },
        /** True once the server answered: the findings and the badge are real from then on. */
        get answered(): boolean {
            return answered;
        },
        get findings(): SecurityFindings {
            return answered ? securityFindings(checks, browser()) : NO_FINDINGS;
        },
        get attentionCount(): number {
            return answered ? attentionCount(securityFindings(checks, browser())) : 0;
        },
        ensureLoaded(): Promise<void> {
            if (status === 'ready') return Promise.resolve();
            return read();
        },
        reload(): Promise<void> {
            return read();
        },
    };
}

export type SecurityChecksStore = ReturnType<typeof createSecurityChecks>;

export const securityChecks = createSecurityChecks();
