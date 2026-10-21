/**
 * securityFindings — what Settings › Security lists (accounts lot A8b): the server's checks and the browser's own one,
 * as two lists, sorted and linked to where each problem is fixed.
 *
 * The contract under test (approved for A8b):
 *   1. `securityFindings(checks, browser)` returns `{attention, passed}`, and changes neither input.
 *   2. `attention` holds every check whose severity is not `ok`, as a finding `{id: check_id, severity, messageKey:
 *      i18n_key, params: detail, source: 'server'}`, plus the browser's finding when
 *      `openRegistrationNoticeFor({isAdmin: true, ...browser})` gives a notice: `{id: 'accounts.openRegistration',
 *      severity: 'warning', messageKey: the notice's, action: the notice's when it has one, source: 'browser'}`.
 *      Sorted error → warning → info; within one severity, the server's order, and the browser's finding after the
 *      server's findings of its severity.
 *   3. `passed` holds the `ok` checks, in the server's order, mapped the same way, never with an action.
 *   4. A server finding links to where it is fixed: `email.smtp`, `email.smtp_encryption` and `email.links` to Settings ›
 *      Email (`settings.securityTab.openEmail`, `/settings?tab=email`), `platform.plugin_secrets` to Settings › Plugins
 *      (`settings.securityTab.openPlugins`, `/settings?tab=plugins`); any other check has none.
 *   5. `attentionCount({attention})` counts the attention findings that are errors or warnings: an `info` is listed,
 *      not counted.
 *   6. (N69b, the security-attention dot) `attentionSeverity({attention})` says how serious the attention is: `'error'`
 *      when any attention finding is an error, else `'warning'` when any is a warning, else `null`; an `info` never
 *      counts, as in `attentionCount`, so it is `null` exactly when the badge counts nothing.
 *
 * How the cases read it. The expected findings are written from the fixtures with the contract's own mapping (`server()`
 * below), never read from the module under test. The browser's finding is compared with literals for the two notices of
 * today, and, for every combination of mode, pin and host, with what `openRegistrationNoticeFor` itself answers for an
 * administrator: the rule of when to warn is that function's (its own file pins it), so this one only proves it is
 * reused, not copied.
 *
 * Read as pinned, where the contract leaves a word to interpret:
 *   - the browser's finding carries `params: {}` — `params` is a required field of a finding, and the notice has none;
 *   - a finding is exactly its six fields: a notice's `dismissible` does not come along.
 * Not pinned: the `severity` of a passed finding (a `FindingSeverity` has no `ok`, so «mapped the same way» cannot
 * keep it), and whether `params` is the check's own `detail` object or a copy.
 *
 * H-55 v2 (step 4): the browser knows a second thing, `platform.blockedScript` — a warning while the tab holds at least one
 * source of a script the enforced Content-Security-Policy blocked and this instance did not send (`cspNotice.ts`). It is
 * fed through the same `browser` state, as an optional `blockedScripts` list of source names (the caller reads
 * `sessionStorage['librefolio-csp-blocked']`: the contract names the storage, not this field — an interface decision the
 * cases below pin as `blockedScripts`). The last block of this file reads it; red until the check exists.
 *
 * Red until A8b: `securityFindings.ts` does not exist yet. It is loaded by a computed specifier, so each case fails on
 * its own with the contract in its message rather than the whole file at import, and the type check does not depend on
 * the module landing first. No DOM: the node environment, with `$lib/api` inert because `openRegistrationNoticeFor`'s
 * module imports the auth store, which imports the client.
 */
import {describe, expect, it, vi} from 'vitest';
import {openRegistrationNoticeFor} from '$lib/features/auth/openRegistrationNotice.svelte';

// `$lib/api`: every operation an inert spy pending forever — nothing here may reach the network, nothing may settle
// behind the assertions. The shape of `openRegistrationNotice.test.ts`.
vi.mock('$lib/api', () => {
    const inert = new Map<string, unknown>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, operation) {
                if (typeof operation !== 'string' || operation === 'then') return undefined;
                if (!inert.has(operation))
                    inert.set(
                        operation,
                        vi.fn(() => new Promise(() => {})),
                    );
                return inert.get(operation);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

// --- The module under test, by a computed specifier: Vite does not resolve it when it transforms this file ----------

const FINDINGS_MODULE = './securityFindings';

type Severity = 'ok' | 'info' | 'warning' | 'error';
type FindingSeverity = 'error' | 'warning' | 'info';

interface SecurityCheck {
    check_id: string;
    severity: Severity;
    i18n_key: string;
    detail: Record<string, string | number>;
}

interface FindingAction {
    labelKey: string;
    href: string;
}

interface SecurityFinding {
    id: string;
    severity: FindingSeverity;
    messageKey: string;
    params: Record<string, string | number>;
    action?: FindingAction;
    source: 'server' | 'browser';
}

interface BrowserState {
    registrationMode: string;
    registrationLocked: boolean;
    hostname: string;
    /** H-55 v2: the sources of the scripts the policy blocked on this tab (`sessionStorage['librefolio-csp-blocked']`), read by the caller; absent means none. */
    blockedScripts?: readonly string[];
}

interface Findings {
    attention: SecurityFinding[];
    passed: SecurityFinding[];
}

interface FindingsModule {
    securityFindings(checks: SecurityCheck[], browser: BrowserState): Findings;
    attentionCount(findings: {attention: SecurityFinding[]}): number;
}

async function loadFindings(): Promise<FindingsModule> {
    let module: Record<string, unknown>;
    try {
        module = (await import(/* @vite-ignore */ FINDINGS_MODULE)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`src/lib/features/settings/security/securityFindings.ts cannot be loaded (red until A8b: it does not exist yet): nothing turns the security checks into what the Security tab lists — ${String(error)}`);
    }
    for (const name of ['securityFindings', 'attentionCount']) {
        expect(typeof module[name], `securityFindings.ts exports no ${name}()`).toBe('function');
    }
    return module as unknown as FindingsModule;
}

type AttentionSeverity = (findings: {attention: SecurityFinding[]}) => 'error' | 'warning' | null;

/**
 * `attentionSeverity` (N69b), read from the module's namespace rather than imported by name: until it lands, each case
 * fails on this assertion, and the cases of A8b above keep running.
 */
async function loadAttentionSeverity(): Promise<AttentionSeverity> {
    const module = (await loadFindings()) as unknown as Record<string, unknown>;
    expect(typeof module.attentionSeverity, 'securityFindings.ts exports no attentionSeverity(): nothing says how serious the attention findings are (red until N69b)').toBe('function');
    return module.attentionSeverity as AttentionSeverity;
}

// --- The contract's literals, never read from the module under test --------------------------------------------------

const OPEN_EMAIL: FindingAction = {labelKey: 'settings.securityTab.openEmail', href: '/settings?tab=email'};
const OPEN_PLUGINS: FindingAction = {labelKey: 'settings.securityTab.openPlugins', href: '/settings?tab=plugins'};

const BROWSER_ID = 'accounts.openRegistration';

/** The browser's finding: an instance open to registration, reached from outside the local network. */
const BROWSER_OPEN: SecurityFinding = {
    id: BROWSER_ID,
    severity: 'warning',
    messageKey: 'auth.notices.openRegistration',
    params: {},
    action: {labelKey: 'auth.notices.openRegistrationAction', href: '/settings?tab=admin'},
    source: 'browser',
};

/** The same with the mode pinned by LIBREFOLIO_REGISTRATION: nothing in the app can change it, so no link. */
const BROWSER_LOCKED: SecurityFinding = {id: BROWSER_ID, severity: 'warning', messageKey: 'auth.notices.openRegistrationLocked', params: {}, source: 'browser'};

const EXTERNAL_HOST = 'librefolio.example.com';

/** Nothing to warn about: an instance on invitation only. */
const SILENT: BrowserState = {registrationMode: 'invite', registrationLocked: false, hostname: EXTERNAL_HOST};
const OPEN_EXTERNAL: BrowserState = {registrationMode: 'open', registrationLocked: false, hostname: EXTERNAL_HOST};
const OPEN_LOCKED_EXTERNAL: BrowserState = {registrationMode: 'open', registrationLocked: true, hostname: EXTERNAL_HOST};

function check(check_id: string, severity: Severity, i18n_key: string, detail: Record<string, string | number> = {}): SecurityCheck {
    return {check_id, severity, i18n_key, detail};
}

/** The finding the contract makes of a server check: its fields renamed, and its action when it has one. */
function server(source: SecurityCheck, action?: FindingAction): SecurityFinding {
    return {id: source.check_id, severity: source.severity as FindingSeverity, messageKey: source.i18n_key, params: source.detail, ...(action ? {action} : {}), source: 'server'};
}

/** A passed finding without its severity, which is not pinned (see the header); an absent action reads `undefined`. */
function passedView(finding: SecurityFinding): Omit<SecurityFinding, 'severity'> {
    return {id: finding.id, messageKey: finding.messageKey, params: finding.params, action: finding.action, source: finding.source};
}

const ids = (findings: SecurityFinding[]): string[] => findings.map((finding) => finding.id);

// --- Fixtures: the ten checks of today, in the platform's order --------------------------------------------------------

const JWT_SHORT = check('platform.jwt_secret', 'warning', 'instance.checks.jwtSecret.short', {source: 'JWT_SECRET', length: 12, minimum: 32});
const SECRETS_TWICE = check('platform.secrets_set_twice', 'warning', 'instance.checks.secretsSetTwice.found', {variables: 'JWT_SECRET'});
const KEY_UNUSABLE = check('platform.instance_key', 'error', 'instance.checks.instanceKey.unusable', {source: 'LIBREFOLIO_INSTANCE_KEY_FILE', reason: 'the file cannot be read'});
const COOKIE_OK = check('platform.session_cookie', 'ok', 'instance.checks.sessionCookie.ok');
const LOG_VERBOSE = check('platform.log_level', 'info', 'instance.checks.logLevel.verbose', {log_level: 'DEBUG'});
const LOGIN_LIMIT_OFF = check('accounts.login_limit', 'warning', 'auth.checks.loginLimit.off');
const SMTP_OK = check('email.smtp', 'ok', 'email.checks.smtp.ok');
const SMTP_PLAIN = check('email.smtp_encryption', 'warning', 'email.checks.smtpEncryption.plain');
const LINKS_MISSING = check('email.links', 'info', 'email.checks.links.missing');
const SECRETS_UNREADABLE = check('platform.plugin_secrets', 'error', 'instance.checks.pluginSecrets.unreadable', {count: 2});

/** Every severity, several per severity, in the platform's order. */
const MIXED: SecurityCheck[] = [JWT_SHORT, SECRETS_TWICE, KEY_UNUSABLE, COOKIE_OK, LOG_VERBOSE, LOGIN_LIMIT_OFF, SMTP_OK, SMTP_PLAIN, LINKS_MISSING, SECRETS_UNREADABLE];

/** MIXED as the tab must list it, with nothing to warn about in the browser. */
const MIXED_ATTENTION: SecurityFinding[] = [server(KEY_UNUSABLE), server(SECRETS_UNREADABLE, OPEN_PLUGINS), server(JWT_SHORT), server(SECRETS_TWICE), server(LOGIN_LIMIT_OFF), server(SMTP_PLAIN, OPEN_EMAIL), server(LOG_VERBOSE), server(LINKS_MISSING, OPEN_EMAIL)];

/** The ten checks, all fine. */
const ALL_OK: SecurityCheck[] = [
    check('platform.jwt_secret', 'ok', 'instance.checks.jwtSecret.ok'),
    check('platform.secrets_set_twice', 'ok', 'instance.checks.secretsSetTwice.ok'),
    check('platform.instance_key', 'ok', 'instance.checks.instanceKey.ok', {source: 'generated'}),
    check('platform.session_cookie', 'ok', 'instance.checks.sessionCookie.ok'),
    check('platform.log_level', 'ok', 'instance.checks.logLevel.ok'),
    check('accounts.login_limit', 'ok', 'auth.checks.loginLimit.ok'),
    check('email.smtp', 'ok', 'email.checks.smtp.off'),
    check('email.smtp_encryption', 'ok', 'email.checks.smtpEncryption.ok'),
    check('email.links', 'ok', 'email.checks.links.ok'),
    check('platform.plugin_secrets', 'ok', 'instance.checks.pluginSecrets.ok'),
];

/** Frozen all the way down: a sort in place, or a write into a detail, throws instead of passing. */
function deepFreeze<T>(value: T): T {
    if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
        Object.freeze(value);
        for (const child of Object.values(value as Record<string, unknown>)) deepFreeze(child);
    }
    return value;
}

describe('securityFindings — attention: what is not ok', () => {
    // red until A8b
    it('every check that is not ok, mapped to a finding of the server, most severe first and in the server’s order within a severity', async () => {
        const {securityFindings} = await loadFindings();

        const {attention} = securityFindings(structuredClone(MIXED), SILENT);

        expect(attention).toEqual(MIXED_ATTENTION);
    });

    // red until A8b
    it('error → warning → info, whatever the order they came in', async () => {
        const {securityFindings} = await loadFindings();
        const shuffled = [LINKS_MISSING, SMTP_PLAIN, SECRETS_UNREADABLE, COOKIE_OK, LOG_VERBOSE, JWT_SHORT, KEY_UNUSABLE];

        const {attention} = securityFindings(structuredClone(shuffled), SILENT);

        expect(attention.map((finding) => finding.severity)).toEqual(['error', 'error', 'warning', 'warning', 'info', 'info']);
    });

    // red until A8b
    it('within one severity the order received is kept, neither alphabetical nor reversed', async () => {
        const {securityFindings} = await loadFindings();
        const errors = [
            check('platform.plugin_secrets', 'error', 'instance.checks.pluginSecrets.unreadable', {count: 1}),
            check('accounts.login_limit', 'error', 'auth.checks.loginLimit.invalid', {value: 'maybe'}),
            check('platform.instance_key', 'error', 'instance.checks.instanceKey.unusable', {source: 'LIBREFOLIO_INSTANCE_KEY', reason: 'not a key'}),
        ];
        const warnings = [check('email.smtp_encryption', 'warning', 'email.checks.smtpEncryption.plain'), check('accounts.login_limit', 'warning', 'auth.checks.loginLimit.off'), check('platform.session_cookie', 'warning', 'instance.checks.sessionCookie.never')];

        expect(ids(securityFindings(structuredClone(errors), SILENT).attention)).toEqual(['platform.plugin_secrets', 'accounts.login_limit', 'platform.instance_key']);
        expect(ids(securityFindings(structuredClone(warnings), SILENT).attention)).toEqual(['email.smtp_encryption', 'accounts.login_limit', 'platform.session_cookie']);
    });

    // red until A8b
    it('the message key and its ICU values come from the check: a count stays a number', async () => {
        const {securityFindings} = await loadFindings();

        const {attention} = securityFindings(structuredClone([SECRETS_UNREADABLE, JWT_SHORT]), SILENT);

        expect(attention.map(({id, messageKey, params, source}) => ({id, messageKey, params, source}))).toEqual([
            {id: 'platform.plugin_secrets', messageKey: 'instance.checks.pluginSecrets.unreadable', params: {count: 2}, source: 'server'},
            {id: 'platform.jwt_secret', messageKey: 'instance.checks.jwtSecret.short', params: {source: 'JWT_SECRET', length: 12, minimum: 32}, source: 'server'},
        ]);
        expect(typeof attention[0].params.count, 'the plural of instance.checks.pluginSecrets.unreadable needs a number').toBe('number');
    });
});

describe('securityFindings — passed: what is ok', () => {
    // red until A8b
    it('the ok checks, in the server’s order, mapped the same way, never among the attention findings', async () => {
        const {securityFindings} = await loadFindings();

        const {attention, passed} = securityFindings(structuredClone(MIXED), SILENT);

        expect(passed.map(passedView)).toEqual([passedView(server(COOKIE_OK)), passedView(server(SMTP_OK))]);
        expect(ids(attention), 'an ok check is passed, not listed for attention').not.toContain('platform.session_cookie');
        expect(ids(attention)).not.toContain('email.smtp');
    });

    // red until A8b
    it('all ten ok: nothing for attention, ten passed in the platform’s order, none with an action — not even those that link when they fail', async () => {
        const {securityFindings} = await loadFindings();

        const {attention, passed} = securityFindings(structuredClone(ALL_OK), SILENT);

        expect(attention).toEqual([]);
        expect(passed.map(passedView)).toEqual(ALL_OK.map((ok) => passedView(server(ok))));
        expect(
            passed.filter((finding) => finding.action !== undefined).map((finding) => finding.id),
            'a passed check needs no link to where it would be fixed',
        ).toEqual([]);
    });

    // red until A8b
    it('no check and nothing to warn about: two empty lists', async () => {
        const {securityFindings} = await loadFindings();

        expect(securityFindings([], SILENT)).toEqual({attention: [], passed: []});
    });
});

describe('securityFindings — the link to where a problem is fixed', () => {
    const LINKED: Array<[label: string, source: SecurityCheck, action: FindingAction]> = [
        ['email.smtp, an error', check('email.smtp', 'error', 'email.checks.smtp.invalid', {problem: 'PORT_INVALID', variable: 'LIBREFOLIO_SMTP_PORT'}), OPEN_EMAIL],
        ['email.smtp_encryption, a warning', SMTP_PLAIN, OPEN_EMAIL],
        ['email.links, a warning', check('email.links', 'warning', 'email.checks.links.invalid'), OPEN_EMAIL],
        ['email.links, an info', LINKS_MISSING, OPEN_EMAIL],
        ['platform.plugin_secrets, an error', SECRETS_UNREADABLE, OPEN_PLUGINS],
        ['platform.plugin_secrets, should it ever be a warning', check('platform.plugin_secrets', 'warning', 'instance.checks.pluginSecrets.unreadable', {count: 1}), OPEN_PLUGINS],
    ];

    // red until A8b
    it.each(LINKED)('%s: linked to its tab', async (_label, source, action) => {
        const {securityFindings} = await loadFindings();

        const {attention} = securityFindings(structuredClone([source]), SILENT);

        expect(attention).toEqual([server(source, action)]);
    });

    const UNLINKED: Array<[label: string, source: SecurityCheck]> = [
        ['platform.jwt_secret', JWT_SHORT],
        ['platform.secrets_set_twice', SECRETS_TWICE],
        ['platform.instance_key', KEY_UNUSABLE],
        ['platform.session_cookie', check('platform.session_cookie', 'warning', 'instance.checks.sessionCookie.never')],
        ['platform.log_level', LOG_VERBOSE],
        ['accounts.login_limit', LOGIN_LIMIT_OFF],
        ['a check the platform may add tomorrow', check('platform.backup_key', 'warning', 'instance.checks.backupKey.missing')],
    ];

    // red until A8b
    it.each(UNLINKED)('%s: no action', async (_label, source) => {
        const {securityFindings} = await loadFindings();

        const {attention} = securityFindings(structuredClone([source]), SILENT);

        expect(attention, 'premise: the check is listed for attention').toHaveLength(1);
        expect(attention[0].action).toBeUndefined();
        expect(attention).toEqual([server(source)]);
    });
});

describe('securityFindings — the browser’s own check: registration open to anyone, reached from outside', () => {
    // red until A8b
    it('open, reached from outside: the warning with the link to the setting, after the server’s warnings and before the infos', async () => {
        const {securityFindings} = await loadFindings();

        const {attention, passed} = securityFindings(structuredClone(MIXED), OPEN_EXTERNAL);

        expect(attention).toEqual([...MIXED_ATTENTION.slice(0, 6), BROWSER_OPEN, ...MIXED_ATTENTION.slice(6)]);
        expect(ids(passed), 'the browser’s finding is never passed').toEqual(['platform.session_cookie', 'email.smtp']);
    });

    // red until A8b
    it('pinned by LIBREFOLIO_REGISTRATION: the locked message, and no action', async () => {
        const {securityFindings} = await loadFindings();

        const {attention} = securityFindings([], OPEN_LOCKED_EXTERNAL);

        expect(attention).toEqual([BROWSER_LOCKED]);
        expect(attention[0].action, 'nothing in the app can change a pinned mode').toBeUndefined();
    });

    // red until A8b
    it('with no server warning it still sits between the errors and the infos', async () => {
        const {securityFindings} = await loadFindings();

        const {attention} = securityFindings(structuredClone([LOG_VERBOSE, KEY_UNUSABLE]), OPEN_EXTERNAL);

        expect(ids(attention)).toEqual(['platform.instance_key', BROWSER_ID, 'platform.log_level']);
    });

    // red until A8b
    it('alone: every server check ok, the browser’s warning is the one thing to look at', async () => {
        const {securityFindings} = await loadFindings();

        const {attention, passed} = securityFindings(structuredClone(ALL_OK), OPEN_EXTERNAL);

        expect(attention).toEqual([BROWSER_OPEN]);
        expect(passed).toHaveLength(10);
    });

    const SILENT_BROWSERS: Array<[label: string, browser: BrowserState]> = [
        ['an instance on invitation only', SILENT],
        ['an instance closed to registration', {registrationMode: 'disabled', registrationLocked: false, hostname: EXTERNAL_HOST}],
        ['a mode not known yet (the public configuration has not answered)', {registrationMode: '', registrationLocked: false, hostname: EXTERNAL_HOST}],
        ['open, reached through localhost', {registrationMode: 'open', registrationLocked: false, hostname: 'localhost'}],
        ['open, reached through an address of the local network', {registrationMode: 'open', registrationLocked: false, hostname: '192.168.1.10'}],
    ];

    // red until A8b
    it.each(SILENT_BROWSERS)('nothing to warn about (%s): no browser finding', async (_label, browser) => {
        const {securityFindings} = await loadFindings();

        const {attention, passed} = securityFindings(structuredClone(ALL_OK), browser);

        expect(attention).toEqual([]);
        expect(passed, 'premise: the server checks are all there').toHaveLength(10);
    });

    // red until A8b
    it('for every mode, pin and host, the browser’s finding is what openRegistrationNoticeFor answers for an administrator', async () => {
        const {securityFindings} = await loadFindings();
        const hosts = [EXTERNAL_HOST, 'nas.tail1234.ts.net', 'localhost', '192.168.1.10', '[::1]'];
        let warned = 0;
        let silent = 0;

        for (const registrationMode of ['open', 'invite', 'disabled', '']) {
            for (const registrationLocked of [false, true]) {
                for (const hostname of hosts) {
                    const browser = {registrationMode, registrationLocked, hostname};
                    const notice = openRegistrationNoticeFor({isAdmin: true, ...browser});
                    const expected: SecurityFinding[] = notice ? [{id: notice.id, severity: 'warning', messageKey: notice.messageKey, params: {}, ...(notice.action ? {action: notice.action} : {}), source: 'browser'}] : [];
                    if (notice) warned += 1;
                    else silent += 1;

                    expect(securityFindings([], browser).attention, `${JSON.stringify(browser)}`).toEqual(expected);
                }
            }
        }
        expect([warned > 0, silent > 0], 'premise: the table holds states that warn and states that do not').toEqual([true, true]);
    });
});

describe('securityFindings — its inputs', () => {
    // red until A8b
    it('changes neither the checks nor the browser state: frozen all the way down, they come out as they went in', async () => {
        const {securityFindings} = await loadFindings();
        const checks = deepFreeze(structuredClone([LINKS_MISSING, SMTP_PLAIN, SECRETS_UNREADABLE, COOKIE_OK, JWT_SHORT, KEY_UNUSABLE]));
        const browser = deepFreeze({...OPEN_EXTERNAL});
        const before = structuredClone(checks);

        let findings: Findings | undefined;
        expect(() => {
            findings = securityFindings(checks, browser);
        }, 'a sort in place or a write into a check throws on a frozen input').not.toThrow();

        expect(checks).toEqual(before);
        expect(browser).toEqual(OPEN_EXTERNAL);
        expect(ids(findings?.attention ?? []), 'premise: there was something to sort').toEqual(['platform.plugin_secrets', 'platform.instance_key', 'email.smtp_encryption', 'platform.jwt_secret', BROWSER_ID, 'email.links']);
    });
});

describe('attentionCount — what needs doing', () => {
    // red until A8b
    it('counts the errors and the warnings among the attention findings, the browser’s included, never an info', async () => {
        const {securityFindings, attentionCount} = await loadFindings();

        expect(attentionCount(securityFindings(structuredClone(MIXED), SILENT)), '2 errors and 4 warnings; 2 infos listed, not counted').toBe(6);
        expect(attentionCount(securityFindings(structuredClone(MIXED), OPEN_EXTERNAL)), 'and the browser’s warning').toBe(7);
        expect(attentionCount(securityFindings(structuredClone([LOG_VERBOSE, LINKS_MISSING]), SILENT)), 'infos only: listed, nothing to count').toBe(0);
        expect(attentionCount(securityFindings(structuredClone(ALL_OK), SILENT))).toBe(0);
    });

    // red until A8b
    it('reads the attention list alone, whatever made it', async () => {
        const {attentionCount} = await loadFindings();
        const finding = (id: string, severity: FindingSeverity): SecurityFinding => ({id, severity, messageKey: `test.${id}`, params: {}, source: 'server'});

        expect(attentionCount({attention: []})).toBe(0);
        expect(attentionCount({attention: [finding('a', 'info'), finding('b', 'warning'), finding('c', 'error'), finding('d', 'info'), finding('e', 'warning')]})).toBe(3);
    });
});

/**
 * attentionSeverity (N69b): the colour of the dot an administrator sees on the sidebar's connection line and on the
 * phone's menu button. It reads the attention list alone, like `attentionCount`, and is passed lists in any order: the
 * error is placed after the warnings on purpose, so that «the first one decides» cannot pass.
 */
describe('attentionSeverity — how serious the attention is (N69b)', () => {
    const finding = (id: string, severity: FindingSeverity): SecurityFinding => ({id, severity, messageKey: `test.${id}`, params: {}, source: 'server'});

    // red until N69b
    it('an error beats any number of warnings, wherever it sits in the list', async () => {
        const attentionSeverity = await loadAttentionSeverity();

        expect(attentionSeverity({attention: [finding('a', 'warning'), finding('b', 'warning'), finding('c', 'error'), finding('d', 'info')]}), 'two warnings, then an error').toBe('error');
        expect(attentionSeverity({attention: [finding('d', 'info'), finding('c', 'error')]}), 'an info, then an error').toBe('error');
        expect(attentionSeverity({attention: [finding('c', 'error')]}), 'an error alone').toBe('error');
    });

    // red until N69b
    it('warnings and no error: warning, with or without infos around them', async () => {
        const attentionSeverity = await loadAttentionSeverity();

        expect(attentionSeverity({attention: [finding('a', 'warning')]}), 'one warning').toBe('warning');
        expect(attentionSeverity({attention: [finding('d', 'info'), finding('a', 'warning'), finding('e', 'info'), finding('b', 'warning')]}), 'warnings among infos').toBe('warning');
    });

    // red until N69b
    it('infos only: null — an info is listed, never counted', async () => {
        const attentionSeverity = await loadAttentionSeverity();

        expect(attentionSeverity({attention: [finding('d', 'info')]})).toBeNull();
        expect(attentionSeverity({attention: [finding('d', 'info'), finding('e', 'info')]})).toBeNull();
    });

    // red until N69b
    it('nothing to look at: null', async () => {
        const attentionSeverity = await loadAttentionSeverity();

        expect(attentionSeverity({attention: []})).toBeNull();
    });

    // red until N69b
    it('on what securityFindings lists: the browser’s warning counts like the server’s, and it is null exactly when attentionCount is 0', async () => {
        const {securityFindings, attentionCount} = await loadFindings();
        const attentionSeverity = await loadAttentionSeverity();
        const CASES: Array<[label: string, checks: SecurityCheck[], browser: BrowserState, expected: 'error' | 'warning' | null]> = [
            ['the ten of today, every severity', MIXED, SILENT, 'error'],
            ['the same, the browser warning too', MIXED, OPEN_EXTERNAL, 'error'],
            ['every check ok, open registration reached from outside', ALL_OK, OPEN_EXTERNAL, 'warning'],
            ['every check ok, open registration pinned', ALL_OK, OPEN_LOCKED_EXTERNAL, 'warning'],
            ['a warning and an info', [SMTP_PLAIN, LOG_VERBOSE], SILENT, 'warning'],
            ['an error alone', [KEY_UNUSABLE], SILENT, 'error'],
            ['infos only', [LOG_VERBOSE, LINKS_MISSING], SILENT, null],
            ['every check ok, nothing to warn about', ALL_OK, SILENT, null],
            ['no check at all', [], SILENT, null],
        ];

        for (const [label, checks, browser, expected] of CASES) {
            const findings = securityFindings(structuredClone(checks), browser);
            expect(attentionSeverity(findings), label).toBe(expected);
            expect(attentionSeverity(findings) === null, `${label}: null exactly when the badge counts nothing`).toBe(attentionCount(findings) === 0);
        }
    });

    // red until N69b
    it('changes nothing it reads: a frozen list, the error last, comes out as it went in', async () => {
        const attentionSeverity = await loadAttentionSeverity();
        const attention = deepFreeze([finding('a', 'warning'), finding('d', 'info'), finding('c', 'error')]);
        const before = structuredClone(attention);

        let severity: 'error' | 'warning' | null | undefined;
        expect(() => {
            severity = attentionSeverity({attention});
        }, 'a sort in place throws on a frozen list').not.toThrow();

        expect(severity).toBe('error');
        expect(attention).toEqual(before);
    });
});

/**
 * The browser's second check (H-55 v2, step 4): `platform.blockedScript`, a warning while the tab holds a source of a script
 * the policy blocked. Fed as `blockedScripts` of the browser state — the sources `cspNotice.ts` notes in the tab's
 * `sessionStorage`. Not pinned: the message key (a catalogue key of the lot), its params' names, an action.
 */
describe('securityFindings — the browser’s second check: a script the policy blocked (H-55 v2)', () => {
    const BLOCKED_ID = 'platform.blockedScript';
    const CDN = 'https://cdn.example.com';
    const withBlocked = (blockedScripts: readonly string[], base: BrowserState = SILENT): BrowserState => ({...base, blockedScripts});
    const blockedOf = (findings: Findings): SecurityFinding[] => findings.attention.filter((finding) => finding.id === BLOCKED_ID);
    /** What a finding says of its params, as one string: the sources it names are found in it, whatever the param is called. */
    const paramsText = (finding: SecurityFinding): string => Object.values(finding.params).map(String).join(' | ');

    // red until H-55 v2 step 4
    it('BSC-01: a source noted: one warning of the browser, `platform.blockedScript`, naming it — after nothing else is needed to see it', async () => {
        const {securityFindings} = await loadFindings();

        const {attention, passed} = securityFindings([], withBlocked(['inline']));

        expect(attention, 'one finding, the browser’s').toHaveLength(1);
        const [finding] = attention;
        expect({id: finding.id, severity: finding.severity, source: finding.source}).toEqual({id: BLOCKED_ID, severity: 'warning', source: 'browser'});
        expect(typeof finding.messageKey === 'string' && finding.messageKey.length > 0, 'a catalogue key for the message').toBe(true);
        expect(finding.messageKey, 'not the open-registration warning’s').not.toBe(BROWSER_OPEN.messageKey);
        expect(paramsText(finding), 'the message names the source').toContain('inline');
        expect(passed, 'a browser finding is never passed').toEqual([]);
        expect(
            Object.keys(finding).filter((key) => !['id', 'severity', 'messageKey', 'params', 'action', 'source'].includes(key)),
            'a finding is its fields, nothing else',
        ).toEqual([]);
    });

    // red until H-55 v2 step 4
    it('BSC-02: several sources: still one finding, naming every one of them', async () => {
        const {securityFindings} = await loadFindings();

        const findings = securityFindings([], withBlocked([CDN, 'inline', 'eval']));

        const blocked = blockedOf(findings);
        expect(blocked, 'one finding for the tab, not one per source').toHaveLength(1);
        for (const source of [CDN, 'inline', 'eval']) expect(paramsText(blocked[0]), `names ${source}`).toContain(source);
    });

    // red until H-55 v2 step 4
    it.each<[string, BrowserState]>([
        ['an empty list', withBlocked([])],
        ['no list at all (nothing noted, or a storage that cannot be read)', SILENT],
        ['an undefined list', {...SILENT, blockedScripts: undefined}],
    ])('BSC-03: with %s, no finding — and with a source, the same state has one', async (_label, silent) => {
        const {securityFindings} = await loadFindings();

        expect(blockedOf(securityFindings(structuredClone(ALL_OK), {...silent})), 'nothing noted: nothing to warn about').toEqual([]);
        expect(securityFindings([], {...silent}).attention, 'and no other finding either').toEqual([]);
        expect(blockedOf(securityFindings([], {...silent, blockedScripts: ['inline']})), 'control: one source makes the finding').toHaveLength(1);
    });

    // red until H-55 v2 step 4
    it('BSC-04: after the server’s errors and warnings and before its infos — beside the open-registration warning, in either order', async () => {
        const {securityFindings} = await loadFindings();

        const {attention} = securityFindings(structuredClone(MIXED), withBlocked(['inline'], OPEN_EXTERNAL));

        expect(
            ids(attention).filter((id) => id !== BLOCKED_ID && id !== BROWSER_ID),
            'the server’s findings keep their order',
        ).toEqual(ids(MIXED_ATTENTION));
        const isBrowser = (finding: SecurityFinding): boolean => finding.id === BLOCKED_ID || finding.id === BROWSER_ID;
        expect(
            attention
                .filter(isBrowser)
                .map((finding) => finding.id)
                .sort(),
            'both of the browser’s warnings are listed',
        ).toEqual([BROWSER_ID, BLOCKED_ID].sort());
        const lastServerWarning = Math.max(...attention.map((finding, index) => (!isBrowser(finding) && finding.severity !== 'info' ? index : -1)));
        const firstServerInfo = attention.findIndex((finding) => !isBrowser(finding) && finding.severity === 'info');
        attention.forEach((finding, index) => {
            if (!isBrowser(finding)) return;
            expect(index, `${finding.id}: after the server’s warnings`).toBeGreaterThan(lastServerWarning);
            expect(index, `${finding.id}: before its infos`).toBeLessThan(firstServerInfo);
        });
    });

    // red until H-55 v2 step 4
    it('BSC-05: it counts, as a warning: the badge and the dot see it', async () => {
        const {securityFindings, attentionCount} = await loadFindings();
        const attentionSeverity = await loadAttentionSeverity();

        expect(attentionCount(securityFindings(structuredClone(MIXED), SILENT)), 'premise: 2 errors and 4 warnings').toBe(6);
        expect(attentionCount(securityFindings(structuredClone(MIXED), withBlocked(['inline']))), 'and the blocked script’s warning').toBe(7);
        expect(attentionCount(securityFindings(structuredClone(MIXED), withBlocked(['inline'], OPEN_EXTERNAL))), 'and both of the browser’s').toBe(8);
        expect(attentionSeverity(securityFindings(structuredClone(ALL_OK), withBlocked(['inline']))), 'every check ok: it alone makes the dot a warning').toBe('warning');
    });

    // red until H-55 v2 step 4
    it('BSC-06: reads the list without changing it: a frozen list of sources comes out as it went in', async () => {
        const {securityFindings} = await loadFindings();
        const sources = deepFreeze([CDN, 'inline']);
        const browser = deepFreeze({...SILENT, blockedScripts: sources});

        let findings: Findings | undefined;
        expect(() => {
            findings = securityFindings([], browser);
        }, 'a write into the list throws on a frozen input').not.toThrow();

        expect(sources).toEqual([CDN, 'inline']);
        expect(blockedOf(findings ?? {attention: [], passed: []}), 'premise: it was read').toHaveLength(1);
    });
});
