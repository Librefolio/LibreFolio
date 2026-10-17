// @vitest-environment jsdom
//
// The docblock above is load-bearing. Under the default `node` environment `$effect` never runs, so the reactivity
// cases would pass on a store nothing can follow (`$test/runes.svelte`). `freshGraph()` runs `assertEffectsRun()` first.
/**
 * securityChecks — the store of Settings › Security (accounts lot A8b): the checks of `GET /api/v1/security/checks`,
 * asked once per page and again on demand, and what the tab lists from them.
 *
 * The contract under test (approved for A8b):
 *   1. `createSecurityChecks(deps?)` makes a store with reactive getters — `status` (`idle` | `loading` | `ready` |
 *      `error`), `checks`, `findings` (`securityFindings(checks, browser())`; while not ready, two empty lists) and
 *      `attentionCount` — and two methods. Creating it asks nothing.
 *   2. `ensureLoaded()` asks once: from `idle` or `error` it fetches, while `loading` or `ready` it does nothing; calls
 *      that overlap share one request.
 *   3. `reload()` always fetches; the last checks stay while it runs; when it fails the status is `error` and the last
 *      checks stay.
 *   4. The defaults: `fetch` is `fetchSecurityChecks` (the generated client); `browser` reads the registration of
 *      `instanceConfig` only once `instanceConfig.loaded` — before, `registrationMode` is `''` — and the host of the page,
 *      `window.location.hostname`. `securityChecks` is the app's store: `createSecurityChecks()` with those defaults.
 *
 * How the cases read it. Requests are deferreds the test answers by hand (`scriptedFetch`): no clock, and «loading» is a
 * state the case holds open. The findings of a ready store are compared with `securityFindings` itself — its own file
 * pins what it lists —, anchored by literal ids so that two empty answers cannot agree. The defaults are read on the real
 * stores of a fresh module graph (`vi.resetModules()` + `import()`): `instanceConfig` answered by a forced `load()` with
 * the case's `fetchConfig`, jsdom pointed at the page (`jsdom.reconfigure({url})`), the generated client a mock.
 *
 * Read as pinned, where the contract leaves a word to interpret:
 *   - `ensureLoaded()` and `reload()` start the request and set `loading` before they return: a second call, and the
 *     tab's disabled button, must see the request at once;
 *   - `findings` follows the browser's state, like any getter of the store: the open-registration warning appears when
 *     `instanceConfig` answers after the checks, and goes when the registration changes — a page opened on the tab
 *     before `/system/instance` has answered must not miss it.
 * Not pinned: whether a failed request also rejects at the caller of `ensureLoaded()` or `reload()` — every call is
 * awaited through `settle()`, and the status says what happened —; whether a concurrent caller's promise waits for the
 * shared answer; which of two overlapping requests wins; and `findings` while a reload runs or after it failed («while
 * not ready: empty lists» against the tab's «previous findings still listed»: `SecurityTab.test.ts` pins what the
 * administrator sees).
 *
 * Red until A8b: `securityChecks.svelte.ts` and `securityFindings.ts` do not exist yet. They are loaded by computed
 * specifiers, so each case fails on its own with the contract in its message rather than the whole file at import, and
 * the type check does not depend on the modules landing first.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

const api = vi.hoisted(() => ({
    operation: 'list_security_checks_api_v1_security_checks_get',
    listSecurityChecks: vi.fn().mockName('zodiosApi.list_security_checks_api_v1_security_checks_get'),
}));

// `$lib/api`: the one operation the store's default fetch asks, programmed by the cases; any other an inert spy pending
// forever, so that nothing a transitive import starts can settle behind the assertions or reach the network.
vi.mock('$lib/api', () => {
    const inert = new Map<string, unknown>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, operation) {
                if (typeof operation !== 'string' || operation === 'then') return undefined;
                if (operation === api.operation) return api.listSecurityChecks;
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
vi.mock('$lib/debug', () => ({debug: {log: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn()}, isDebugEnabled: () => false}));

// --- The contract's shapes, written here: the type check does not wait for the modules --------------------------------

type Severity = 'ok' | 'info' | 'warning' | 'error';
type Status = 'idle' | 'loading' | 'ready' | 'error';

interface SecurityCheck {
    check_id: string;
    severity: Severity;
    i18n_key: string;
    detail: Record<string, string | number>;
}

interface SecurityFinding {
    id: string;
    severity: string;
    messageKey: string;
    params: Record<string, string | number>;
    action?: {labelKey: string; href: string};
    source: 'server' | 'browser';
}

interface Findings {
    attention: SecurityFinding[];
    passed: SecurityFinding[];
}

interface BrowserState {
    registrationMode: string;
    registrationLocked: boolean;
    hostname: string;
}

interface SecurityChecksStore {
    readonly status: Status;
    readonly checks: SecurityCheck[];
    readonly findings: Findings;
    readonly attentionCount: number;
    ensureLoaded(): Promise<void>;
    reload(): Promise<void>;
}

interface StoreDependencies {
    fetch?: () => Promise<SecurityCheck[]>;
    browser?: () => BrowserState;
}

interface StoreModule {
    createSecurityChecks(deps?: StoreDependencies): SecurityChecksStore;
    securityChecks: SecurityChecksStore;
}

interface FindingsModule {
    securityFindings(checks: SecurityCheck[], browser: BrowserState): Findings;
}

// --- The modules of a page load that has just begun ----------------------------------------------------------------------

const STORE_MODULE = './securityChecks.svelte';
const FINDINGS_MODULE = './securityFindings';

async function importOrExplain(specifier: string, file: string, missing: string): Promise<Record<string, unknown>> {
    try {
        return (await import(/* @vite-ignore */ specifier)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`${file} cannot be loaded (red until A8b: it does not exist yet): ${missing} — ${String(error)}`);
    }
}

/** The store's module and `securityFindings` of a fresh graph, with `flushSync`, the rune helpers and `instanceConfig` of the same graph. */
async function freshGraph() {
    vi.resetModules();
    const store = await importOrExplain(STORE_MODULE, 'src/lib/features/settings/security/securityChecks.svelte.ts', 'the Security tab has no store');
    expect(typeof store.createSecurityChecks, 'securityChecks.svelte.ts exports no createSecurityChecks()').toBe('function');
    expect(typeof store.securityChecks, 'securityChecks.svelte.ts exports no securityChecks store').toBe('object');
    const findings = await importOrExplain(FINDINGS_MODULE, 'src/lib/features/settings/security/securityFindings.ts', 'nothing turns the checks into findings');
    expect(typeof findings.securityFindings, 'securityFindings.ts exports no securityFindings()').toBe('function');
    const runes = await import('$test/runes.svelte');
    const {flushSync} = await import('svelte');
    const {instanceConfig} = await import('$lib/features/instance/instanceConfig.svelte');
    runes.assertEffectsRun();
    return {...(store as unknown as StoreModule), ...(findings as unknown as FindingsModule), ...runes, flushSync, instanceConfig};
}

/** A `fetch` whose requests the test answers by hand, the n-th request answered by `answers[n]`. */
function scriptedFetch() {
    const answers: Array<{resolve: (checks: SecurityCheck[]) => void; reject: (error: unknown) => void}> = [];
    const fetch: Mock<() => Promise<SecurityCheck[]>> = vi.fn(
        () =>
            new Promise<SecurityCheck[]>((resolve, reject) => {
                answers.push({resolve: (checks) => resolve(structuredClone(checks)), reject});
            }),
    );
    return {fetch, answers};
}

/** Awaits a call of the store whatever its outcome: whether a failure also rejects at the caller is not pinned. */
async function settle(call: unknown): Promise<void> {
    await Promise.resolve(call).then(
        () => undefined,
        () => undefined,
    );
}

/** The JSDOM instance vitest exposes in this environment: its URL is the page's `window.location`. */
const dom = (globalThis as unknown as {jsdom: {reconfigure(settings: {url: string}): void}}).jsdom;
const INITIAL_URL = window.location.href;

/** A page load at `url`, before `freshGraph()`: even a module that read the host at import would read this one. */
function loadPageAt(url: string): void {
    dom.reconfigure({url});
    expect(window.location.href, 'premise: jsdom serves the page at this address').toBe(new URL(url).href);
}

// --- Fixtures -------------------------------------------------------------------------------------------------------------

function check(check_id: string, severity: Severity, i18n_key: string, detail: Record<string, string | number> = {}): SecurityCheck {
    return {check_id, severity, i18n_key, detail};
}

/** Every severity, several per severity, in the platform's order: 2 errors, 4 warnings, 2 infos, 2 ok. */
const MIXED: SecurityCheck[] = [
    check('platform.jwt_secret', 'warning', 'instance.checks.jwtSecret.short', {source: 'JWT_SECRET', length: 12, minimum: 32}),
    check('platform.secrets_set_twice', 'warning', 'instance.checks.secretsSetTwice.found', {variables: 'JWT_SECRET'}),
    check('platform.instance_key', 'error', 'instance.checks.instanceKey.unusable', {source: 'LIBREFOLIO_INSTANCE_KEY_FILE', reason: 'the file cannot be read'}),
    check('platform.session_cookie', 'ok', 'instance.checks.sessionCookie.ok'),
    check('platform.log_level', 'info', 'instance.checks.logLevel.verbose', {log_level: 'DEBUG'}),
    check('accounts.login_limit', 'warning', 'auth.checks.loginLimit.off'),
    check('email.smtp', 'ok', 'email.checks.smtp.ok'),
    check('email.smtp_encryption', 'warning', 'email.checks.smtpEncryption.plain'),
    check('email.links', 'info', 'email.checks.links.missing'),
    check('platform.plugin_secrets', 'error', 'instance.checks.pluginSecrets.unreadable', {count: 2}),
];

/** MIXED for attention, most severe first, with nothing to warn about in the browser. */
const MIXED_ATTENTION_IDS = ['platform.instance_key', 'platform.plugin_secrets', 'platform.jwt_secret', 'platform.secrets_set_twice', 'accounts.login_limit', 'email.smtp_encryption', 'platform.log_level', 'email.links'];

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

const EMPTY: Findings = {attention: [], passed: []};

const EXTERNAL_HOST = 'librefolio.example.com';
const EXTERNAL_PAGE = `https://${EXTERNAL_HOST}/settings?tab=security`;
const LOCAL_PAGE = 'http://localhost:5173/settings?tab=security';

/** Nothing to warn about: an instance on invitation only. */
const SILENT: BrowserState = {registrationMode: 'invite', registrationLocked: false, hostname: EXTERNAL_HOST};
/** An instance open to registration, reached from outside the local network: the browser's warning. */
const OPEN_EXTERNAL: BrowserState = {registrationMode: 'open', registrationLocked: false, hostname: EXTERNAL_HOST};

const BROWSER_ID = 'accounts.openRegistration';
const BROWSER_OPEN: SecurityFinding = {
    id: BROWSER_ID,
    severity: 'warning',
    messageKey: 'auth.notices.openRegistration',
    params: {},
    action: {labelKey: 'auth.notices.openRegistrationAction', href: '/settings?tab=admin'},
    source: 'browser',
};
const BROWSER_LOCKED: SecurityFinding = {id: BROWSER_ID, severity: 'warning', messageKey: 'auth.notices.openRegistrationLocked', params: {}, source: 'browser'};

function instanceAt(mode: 'open' | 'invite' | 'disabled', locked = false): InstanceConfig {
    return {profile: 'selfhosted', accounts: {registration_mode: mode, registration_locked: locked}};
}

const ids = (findings: SecurityFinding[]): string[] => findings.map((finding) => finding.id);

/**
 * The values an effect recorded, a value equal to the one before it dropped: whether a getter re-runs its reader for a
 * dependency that changed without changing the answer (a plain getter does, a `$derived` does not) is not pinned.
 */
function changes<T>(values: T[]): T[] {
    return values.filter((value, index) => index === 0 || JSON.stringify(value) !== JSON.stringify(values[index - 1]));
}

beforeAll(async () => {
    // The graph the store pulls in — the auth store behind `openRegistrationNoticeFor`, `instanceConfig`, the rune
    // helpers — is a cold transform on its first import: done once here, within a hook's budget, so no case spends its
    // own 5 s on it. `vi.resetModules()` re-evaluates these modules in each case; their transforms stay cached.
    await import('$lib/features/auth/openRegistrationNotice.svelte');
    await import('$lib/features/instance/instanceConfig.svelte');
    await import('$test/runes.svelte');
}, 60_000);

beforeEach(() => {
    api.listSecurityChecks.mockReset();
});

afterEach(() => {
    dom.reconfigure({url: INITIAL_URL});
});

describe('createSecurityChecks — before the first answer', () => {
    // red until A8b
    it('starts idle, without a check or a finding — even when the browser would warn — and creating it asks nothing', async () => {
        const graph = await freshGraph();
        const {fetch} = scriptedFetch();

        const store = graph.createSecurityChecks({fetch, browser: () => OPEN_EXTERNAL});

        expect(store.status).toBe('idle');
        expect(store.checks).toEqual([]);
        expect(store.findings, 'no finding before the server’s checks are in: not even the browser’s own').toEqual(EMPTY);
        expect(store.attentionCount).toBe(0);
        expect(fetch, 'the store asks only when ensureLoaded() or reload() is called').not.toHaveBeenCalled();
    });
});

describe('ensureLoaded — asks once', () => {
    // red until A8b
    it('from idle: loading before it returns, nothing listed while the request runs, then ready with the checks of the answer', async () => {
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch, browser: () => OPEN_EXTERNAL});

        const loading = store.ensureLoaded();

        expect(fetch).toHaveBeenCalledTimes(1);
        expect(store.status, 'the request runs from the call: a second caller and the tab must see it at once').toBe('loading');
        expect(store.checks).toEqual([]);
        expect(store.findings).toEqual(EMPTY);
        expect(store.attentionCount).toBe(0);

        answers[0].resolve(MIXED);
        await settle(loading);

        expect(store.status).toBe('ready');
        expect(store.checks).toEqual(MIXED);
        expect(fetch).toHaveBeenCalledTimes(1);
    });

    // red until A8b
    it('calls that overlap share one request', async () => {
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch, browser: () => SILENT});

        const first = store.ensureLoaded();
        const second = store.ensureLoaded();
        expect(fetch, 'a call while the request runs starts none of its own').toHaveBeenCalledTimes(1);

        answers[0].resolve(MIXED);
        await settle(first);
        await settle(second);

        expect(fetch).toHaveBeenCalledTimes(1);
        expect(store.status).toBe('ready');
        expect(store.checks).toEqual(MIXED);
    });

    // red until A8b
    it('once ready, does nothing: no new request, the same checks', async () => {
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch, browser: () => SILENT});
        const first = store.ensureLoaded();
        answers[0].resolve(MIXED);
        await settle(first);

        const again = store.ensureLoaded();
        expect(store.status, 'a ready store stays ready').toBe('ready');
        await settle(again);

        expect(fetch, 'the page asks once; asking again is reload()').toHaveBeenCalledTimes(1);
        expect(store.checks).toEqual(MIXED);
    });

    // red until A8b
    it('a first request that fails: error, still nothing listed; the next ensureLoaded() asks again', async () => {
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch, browser: () => OPEN_EXTERNAL});
        const failing = store.ensureLoaded();
        answers[0].reject(new Error('503 Service Unavailable'));
        await settle(failing);

        expect(store.status).toBe('error');
        expect(store.checks).toEqual([]);
        expect(store.findings, 'no answer, so nothing to list — not even the browser’s warning').toEqual(EMPTY);
        expect(store.attentionCount).toBe(0);

        const retry = store.ensureLoaded();
        expect(fetch, 'from error, ensureLoaded() asks again').toHaveBeenCalledTimes(2);
        expect(store.status).toBe('loading');
        answers[1].resolve(MIXED);
        await settle(retry);

        expect(store.status).toBe('ready');
        expect(store.checks).toEqual(MIXED);
    });
});

describe('reload — always asks', () => {
    // red until A8b
    it('once ready: a new request, the last checks still there while it runs, then the new answer', async () => {
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch, browser: () => SILENT});
        const first = store.ensureLoaded();
        answers[0].resolve(MIXED);
        await settle(first);

        const reloading = store.reload();

        expect(fetch, 'reload() asks even a ready store').toHaveBeenCalledTimes(2);
        expect(store.status).toBe('loading');
        expect(store.checks, 'the last checks stay visible while the new request runs').toEqual(MIXED);

        answers[1].resolve(ALL_OK);
        await settle(reloading);

        expect(store.status).toBe('ready');
        expect(store.checks).toEqual(ALL_OK);
        expect(store.findings.attention).toEqual([]);
        expect(ids(store.findings.passed)).toEqual(ALL_OK.map((ok) => ok.check_id));
        expect(store.attentionCount).toBe(0);
    });

    // red until A8b
    it('a reload that fails: error, and the last checks stay', async () => {
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch, browser: () => SILENT});
        const first = store.ensureLoaded();
        answers[0].resolve(MIXED);
        await settle(first);

        const reloading = store.reload();
        answers[1].reject(new Error('timeout'));
        await settle(reloading);

        expect(store.status).toBe('error');
        expect(store.checks, 'a failed reload must not throw away what the last answer said').toEqual(MIXED);
        expect(fetch).toHaveBeenCalledTimes(2);
    });

    // red until A8b
    it('from idle, and again after a failure: it asks each time', async () => {
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch, browser: () => SILENT});

        const fromIdle = store.reload();
        expect(store.status).toBe('loading');
        answers[0].reject(new Error('502 Bad Gateway'));
        await settle(fromIdle);
        expect(store.status).toBe('error');

        const fromError = store.reload();
        expect(fetch).toHaveBeenCalledTimes(2);
        expect(store.status).toBe('loading');
        answers[1].resolve(MIXED);
        await settle(fromError);

        expect(store.status).toBe('ready');
        expect(store.checks).toEqual(MIXED);
    });
});

describe('findings — securityFindings(checks, browser()) once there is an answer', () => {
    // red until A8b
    it('ready: the findings are securityFindings of the checks and of the browser’s state, and attentionCount counts their errors and warnings', async () => {
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch, browser: () => OPEN_EXTERNAL});
        const loading = store.ensureLoaded();
        answers[0].resolve(MIXED);
        await settle(loading);

        expect(store.findings).toEqual(graph.securityFindings(structuredClone(MIXED), OPEN_EXTERNAL));
        expect(ids(store.findings.attention), 'the browser’s warning after the server’s').toEqual([...MIXED_ATTENTION_IDS.slice(0, 6), BROWSER_ID, ...MIXED_ATTENTION_IDS.slice(6)]);
        expect(ids(store.findings.passed)).toEqual(['platform.session_cookie', 'email.smtp']);
        expect(store.attentionCount, '2 errors, 4 warnings and the browser’s: the 2 infos are listed, not counted').toBe(7);
    });

    // red until A8b
    it('they follow the browser’s state: the open-registration warning appears and goes as the registration changes', async () => {
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const world = graph.reactiveBox<BrowserState>({...SILENT});
        const store = graph.createSecurityChecks({fetch, browser: () => ({registrationMode: world.registrationMode, registrationLocked: world.registrationLocked, hostname: world.hostname})});
        const loading = store.ensureLoaded();
        answers[0].resolve(ALL_OK);
        await settle(loading);
        const reads = graph.recordReads(() => [store.attentionCount, ids(store.findings.attention)]);
        expect(store.findings.attention, 'premise: nothing to look at').toEqual([]);

        world.registrationMode = 'open';
        graph.flushSync();
        expect(store.findings.attention).toEqual([BROWSER_OPEN]);
        expect(store.attentionCount).toBe(1);

        world.registrationLocked = true;
        graph.flushSync();
        expect(store.findings.attention, 'pinned by LIBREFOLIO_REGISTRATION: the locked message').toEqual([BROWSER_LOCKED]);

        world.registrationMode = 'invite';
        graph.flushSync();
        reads.stop();

        expect(store.findings.attention).toEqual([]);
        expect(changes(reads.values), 'a consumer reading the findings re-runs when they change').toEqual([
            [0, []],
            [1, [BROWSER_ID]],
            [0, []],
        ]);
        expect(fetch, 'none of this asks the server again').toHaveBeenCalledTimes(1);
    });
});

describe('the getters are reactive', () => {
    // red until A8b
    it('a consumer reading status and checks re-runs at each step: idle, loading, ready, loading again, error with the last checks', async () => {
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch, browser: () => SILENT});
        const steps = graph.recordReads(() => [store.status, store.checks.length]);
        const counts = graph.recordReads(() => store.attentionCount);

        const loading = store.ensureLoaded();
        graph.flushSync();
        answers[0].resolve(MIXED);
        await settle(loading);
        graph.flushSync();
        counts.stop();
        const reloading = store.reload();
        graph.flushSync();
        answers[1].reject(new Error('timeout'));
        await settle(reloading);
        graph.flushSync();
        steps.stop();

        expect(changes(steps.values)).toEqual([
            ['idle', 0],
            ['loading', 0],
            ['ready', 10],
            ['loading', 10],
            ['error', 10],
        ]);
        expect(changes(counts.values), '2 errors and 4 warnings once the answer is in').toEqual([0, 6]);
    });
});

describe('the defaults: the generated client, instanceConfig and the page', () => {
    // red until A8b
    it('without fetch, a store asks GET /api/v1/security/checks through the generated client', async () => {
        const graph = await freshGraph();
        api.listSecurityChecks.mockResolvedValueOnce({items: structuredClone(MIXED)});

        const store = graph.createSecurityChecks({browser: () => SILENT});
        expect(api.listSecurityChecks, 'creating it asks nothing').not.toHaveBeenCalled();
        await settle(store.ensureLoaded());

        expect(api.listSecurityChecks).toHaveBeenCalledTimes(1);
        expect(store.status).toBe('ready');
        expect(store.checks).toEqual(MIXED);
        expect(ids(store.findings.attention)).toEqual(MIXED_ATTENTION_IDS);
    });

    // red until A8b
    it('securityChecks is the app’s store: idle until asked, nothing asked at import, then the generated client', async () => {
        const graph = await freshGraph();
        const {securityChecks} = graph;

        expect(securityChecks.status).toBe('idle');
        expect(securityChecks.checks).toEqual([]);
        expect(api.listSecurityChecks, 'importing the module asks nothing').not.toHaveBeenCalled();

        api.listSecurityChecks.mockResolvedValueOnce({items: structuredClone(MIXED)});
        await settle(securityChecks.ensureLoaded());

        expect(api.listSecurityChecks).toHaveBeenCalledTimes(1);
        expect(securityChecks.status).toBe('ready');
        expect(securityChecks.checks).toEqual(MIXED);
    });

    // red until A8b
    it('without browser: the registration is read from instanceConfig only once it has answered — the default in force before is open, and must not warn', async () => {
        loadPageAt(EXTERNAL_PAGE);
        const graph = await freshGraph();
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch});
        expect(graph.instanceConfig.loaded, 'premise: /system/instance has not answered on this page load').toBe(false);
        expect(graph.instanceConfig.config.accounts?.registration_mode, 'premise: the configuration in force until then says open').toBe('open');

        const loading = store.ensureLoaded();
        answers[0].resolve(ALL_OK);
        await settle(loading);
        expect(store.status).toBe('ready');
        expect(store.findings.attention, 'before /system/instance answers the mode is unknown: an invite-only instance would warn for nothing').toEqual([]);

        await graph.instanceConfig.load({force: true, fetchConfig: async () => instanceAt('open')});
        expect(graph.instanceConfig.loaded, 'premise: /system/instance answered').toBe(true);

        expect(store.findings.attention, 'answered open, on a page reached from outside: the warning').toEqual([BROWSER_OPEN]);
        expect(store.attentionCount).toBe(1);
        expect(fetch, 'the browser’s state is read again, the server is not asked again').toHaveBeenCalledTimes(1);
    });

    const ANSWERED: Array<[label: string, page: string, config: InstanceConfig, expected: SecurityFinding[]]> = [
        ['open, a page reached from outside', EXTERNAL_PAGE, instanceAt('open'), [BROWSER_OPEN]],
        ['open and pinned by LIBREFOLIO_REGISTRATION, from outside', EXTERNAL_PAGE, instanceAt('open', true), [BROWSER_LOCKED]],
        ['invite only, from outside', EXTERNAL_PAGE, instanceAt('invite'), []],
        ['open, a page on localhost', LOCAL_PAGE, instanceAt('open'), []],
    ];

    // red until A8b
    it.each(ANSWERED)('without browser, instanceConfig answered %s: the host is the page’s', async (_label, page, config, expected) => {
        loadPageAt(page);
        const graph = await freshGraph();
        await graph.instanceConfig.load({force: true, fetchConfig: async () => config});
        const {fetch, answers} = scriptedFetch();
        const store = graph.createSecurityChecks({fetch});

        const loading = store.ensureLoaded();
        answers[0].resolve(ALL_OK);
        await settle(loading);

        expect(store.status).toBe('ready');
        expect(store.findings.attention).toEqual(expected);
        expect(store.findings.passed, 'premise: the server’s checks are all there').toHaveLength(10);
    });
});
