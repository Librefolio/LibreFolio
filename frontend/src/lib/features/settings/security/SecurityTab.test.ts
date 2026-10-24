// @vitest-environment jsdom
/**
 * SecurityTab — Settings › Security, for administrators (accounts lot A8b): what the instance's configuration and this
 * browser say about its security, the problems first, each linked to where it is fixed.
 *
 * The contract under test (approved for A8b):
 *   - the tab reads the store it is given (`checks`, the app's `securityChecks` when absent): its root `security-tab`
 *     publishes the store's status in `data-status`, and on mount it asks the store with `ensureLoaded()` — a store that
 *     has already answered is not asked again;
 *   - while the first answer is awaited: `security-loading`, and nothing to read;
 *   - a load that fails: `security-load-error` (role alert, `settings.securityTab.loadError`) with `security-retry`,
 *     which asks again (`reload()`); the findings of the last answer, if any, still listed under the banner;
 *   - once answered: one `security-finding` per attention finding, in their order, with `data-check-id` and
 *     `data-severity`, saying `$_(messageKey, {values: params})` and its severity in words
 *     (`settings.securityTab.severity.<severity>`), and its action when it has one: a link `security-finding-action` to
 *     `href`, named `$_(labelKey)`; with no attention finding, `security-all-clear` (`settings.securityTab.allClear`);
 *   - the passed checks in a `<details data-testid="security-passed">` whose `<summary>` counts them
 *     (`settings.securityTab.passed` with `count`), one `security-passed-check` with `data-check-id` each; no details
 *     when nothing passed;
 *   - `security-refresh` («check again») asks again (`reload()`), disabled while a request runs;
 *   - colour roles only: no palette class and no `dark:` in the markup.
 *
 * The store is the real one, `createSecurityChecks({fetch, browser})`, given to the tab through its `checks` prop: its
 * requests are deferreds the test answers by hand (no clock: «loading» is a state the case holds open), its browser state
 * the case's. So «the tab calls ensureLoaded() / reload()» is read where it shows — a request starts, or does not — and
 * what is listed is the store's findings as an administrator sees them. The store's own rules, and `securityFindings`'s,
 * have their files; here they are the tab's input. The app's store is not used: the generated client, its default
 * fetch, is a spy pending forever that no case may reach.
 *
 * Selectors are the contract's test ids and data attributes. `$lib/i18n` is the real module with a marking translator
 * for `_` and `t`: `[en] <key> {<values>}`, so an assertion names the key and the values the tab chose, never a sentence
 * of the catalogue. Every wait is on a state (`data-status`, a request made, a deferred the test settles).
 *
 * Read as pinned, where the contract leaves a word to interpret:
 *   - the prop is named `checks`;
 *   - an `info` finding is an attention finding: listed, and the tab is not «all clear» while one is there;
 *   - `security-loading` only while there is no check yet: a reload keeps the last findings on screen, without it;
 *   - «under the banner»: the banner comes first in the document;
 *   - a failed load is not asked again by itself: only `security-retry` or `security-refresh` ask again;
 *   - a failed request never escapes the tab as an unhandled rejection (Vitest fails the run on one): whether the store
 *     rejects at its caller is the store's choice, not letting it through is the tab's.
 * Not pinned: wording and layout; that the severity label is visually hidden (jsdom has no stylesheet, and a class is
 * not a contract); what a passed check says; `security-refresh` while the banner shows; the all-clear while a reload runs.
 *
 * Red until A8b: `SecurityTab.svelte`, `securityChecks.svelte.ts` (and `securityFindings.ts` behind it) and the
 * `settings.securityTab.*` messages do not exist yet. The modules are loaded through lazy globs, once, in a hook with its
 * own budget (see «The modules under test»), so each case fails on its own with the contract in its message rather than
 * the whole file at import, and the type check does not depend on the modules landing first.
 */
import {beforeAll, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import {tick, type Component} from 'svelte';
import {fireEvent, render, screen, waitFor, within} from '$test/component';
import guides from '$lib/features/instance/checkGuides.json';
import {currentLanguage} from '$lib/stores/app/language';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

const fake = vi.hoisted(() => {
    /** `[en] <key> {a=1, b=2}`: the key the tab chose and the values it filled, for both call shapes of `$_`. */
    function translate(input: unknown, options?: {values?: Record<string, unknown>}): string {
        const asObject = typeof input === 'object' && input !== null ? (input as {id?: unknown; values?: Record<string, unknown>}) : null;
        const key = asObject ? String(asObject.id ?? '') : String(input);
        const values = asObject?.values ?? options?.values ?? {};
        const shown = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return shown.length > 0 ? `[en] ${key} {${shown.join(', ')}}` : `[en] ${key}`;
    }
    return {
        translate,
        operation: 'list_security_checks_api_v1_security_checks_get',
        listSecurityChecks: vi.fn(() => new Promise(() => {})).mockName('zodiosApi.list_security_checks_api_v1_security_checks_get'),
    };
});

vi.mock('$lib/i18n', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>();
    const {readable} = await import('svelte/store');
    const marking = readable(fake.translate);
    return {...actual, _: marking, t: marking};
});

// `$lib/api`: the operation of the app's store, pending forever and asserted untouched; any other an inert spy, so that
// nothing a transitive import starts can settle behind the assertions or reach the network.
vi.mock('$lib/api', () => {
    const inert = new Map<string, unknown>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, operation) {
                if (typeof operation !== 'string' || operation === 'then') return undefined;
                if (operation === fake.operation) return fake.listSecurityChecks;
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

// --- The contract's shapes, written here: the type check does not wait for the modules --------------------------------

type Severity = 'ok' | 'info' | 'warning' | 'error';
type Status = 'idle' | 'loading' | 'ready' | 'error';

interface SecurityCheck {
    check_id: string;
    severity: Severity;
    i18n_key: string;
    detail: Record<string, string | number>;
}

interface BrowserState {
    registrationMode: string;
    registrationLocked: boolean;
    hostname: string;
    blockedScripts?: readonly string[];
}

interface SecurityChecksStore {
    readonly status: Status;
    readonly checks: SecurityCheck[];
    readonly attentionCount: number;
    ensureLoaded(): Promise<void>;
    reload(): Promise<void>;
}

interface StoreDependencies {
    fetch?: () => Promise<SecurityCheck[]>;
    browser?: () => BrowserState;
}

type TabComponent = Component<{checks?: SecurityChecksStore}>;

// --- The modules under test, loaded once, in a hook with its own budget --------------------------------------------------

// Lazy globs rather than literal imports, as in `GapFixStep.test.ts`. The first transform of the tab is cold: its icons
// come from the `lucide-svelte` barrel, whose first import was measured at ~27 s on this machine (1-minute load ~31) —
// far past a test's 5 s, within a hook's budget. A budget for transforming modules, not a wait on the product. A
// missing module fails each test on its own, naming it; the type check does not depend on the modules landing first.
const STORE_MODULES = import.meta.glob<Record<string, unknown>>('./securityChecks.svelte.ts');
const TAB_MODULES = import.meta.glob<Record<string, unknown>>('./SecurityTab.svelte');

interface Subjects {
    SecurityTab: TabComponent;
    createSecurityChecks: (deps?: StoreDependencies) => SecurityChecksStore;
}

async function loadSubjects(): Promise<Subjects> {
    const loadStore = STORE_MODULES['./securityChecks.svelte.ts'];
    if (!loadStore) throw new Error('src/lib/features/settings/security/securityChecks.svelte.ts does not exist yet (red until A8b): the Security tab has no store to read');
    const store = await loadStore();
    if (typeof store.createSecurityChecks !== 'function') throw new Error('securityChecks.svelte.ts exports no createSecurityChecks()');
    const loadTab = TAB_MODULES['./SecurityTab.svelte'];
    if (!loadTab) throw new Error('src/lib/features/settings/security/SecurityTab.svelte does not exist yet (red until A8b): Settings has no Security tab');
    const tab = await loadTab();
    if (typeof tab.default !== 'function') throw new Error('SecurityTab.svelte has no default export');
    return {SecurityTab: tab.default as TabComponent, createSecurityChecks: store.createSecurityChecks as Subjects['createSecurityChecks']};
}

/** What the loading hook found: the modules, or why they could not be loaded. */
let loaded: Subjects | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        loaded = await loadSubjects();
    } catch (error) {
        loaded = {error};
    }
}, 120_000);

function subjects(): Subjects {
    if (loaded === undefined) throw new Error('the Security tab was never loaded: its beforeAll did not run');
    if ('error' in loaded) throw loaded.error;
    return loaded;
}

interface Answer {
    resolve(checks: SecurityCheck[]): void;
    reject(error: unknown): void;
}

interface Mounted {
    store: SecurityChecksStore;
    fetch: Mock<() => Promise<SecurityCheck[]>>;
    answers: Answer[];
    container: HTMLElement;
}

/**
 * The tab mounted on a store of its own: requests answered by hand, the browser's state `browser`. `before` runs on the
 * store before the mount, as a page that already read the checks would.
 */
async function mountTab(browser: BrowserState, before?: (store: SecurityChecksStore, answers: Answer[]) => Promise<void>): Promise<Mounted> {
    const {SecurityTab, createSecurityChecks} = subjects();
    const answers: Answer[] = [];
    const fetch: Mock<() => Promise<SecurityCheck[]>> = vi.fn(
        () =>
            new Promise<SecurityCheck[]>((resolve, reject) => {
                answers.push({resolve: (checks) => resolve(structuredClone(checks)), reject});
            }),
    );
    const store = createSecurityChecks({fetch, browser: () => browser});
    if (before) await before(store, answers);
    const {container} = render(SecurityTab, {props: {checks: store}});
    return {store, fetch, answers, container};
}

/** Answers the `request`-th request (0-based) once the tab has made it. */
async function answer(mounted: Mounted, request: number, outcome: SecurityCheck[] | Error): Promise<void> {
    await waitFor(() => expect(mounted.fetch).toHaveBeenCalledTimes(request + 1));
    const pending = mounted.answers[request];
    if (outcome instanceof Error) pending.reject(outcome);
    else pending.resolve(outcome);
}

/** Awaits a call of the store whatever its outcome: whether a failure also rejects at the caller is the store's file's. */
async function settle(call: unknown): Promise<void> {
    await Promise.resolve(call).then(
        () => undefined,
        () => undefined,
    );
}

const tabRoot = (): HTMLElement => screen.getByTestId('security-tab');

async function waitForStatus(status: Status): Promise<void> {
    await waitFor(() => expect(tabRoot()).toHaveAttribute('data-status', status));
}

const findingIds = (): Array<string | null> => screen.queryAllByTestId('security-finding').map((element) => element.getAttribute('data-check-id'));

function finding(id: string): HTMLElement {
    const element = screen.queryAllByTestId('security-finding').find((candidate) => candidate.getAttribute('data-check-id') === id);
    if (!element) throw new Error(`no security-finding with data-check-id="${id}" is rendered (rendered: ${JSON.stringify(findingIds())})`);
    return element;
}

/** What the tab must render for `key` with `values`: this file's translator, never the catalogue. */
function say(key: string, values?: Record<string, string | number>): string {
    return fake.translate(key, values ? {values} : undefined);
}

/** A pattern matching `text` anywhere: for an accessible name that may carry an icon's or an arrow's text beside it. */
function containing(text: string): RegExp {
    return new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
}

// --- Fixtures -------------------------------------------------------------------------------------------------------------

function check(check_id: string, severity: Severity, i18n_key: string, detail: Record<string, string | number> = {}): SecurityCheck {
    return {check_id, severity, i18n_key, detail};
}

const LOG_VERBOSE = check('platform.log_level', 'info', 'instance.checks.logLevel.verbose', {log_level: 'DEBUG'});

/** Every severity, several per severity, in the platform's order: 2 errors, 4 warnings, 2 infos, 2 ok. */
const MIXED: SecurityCheck[] = [
    check('platform.jwt_secret', 'warning', 'instance.checks.jwtSecret.short', {source: 'JWT_SECRET', length: 12, minimum: 32}),
    check('platform.secrets_set_twice', 'warning', 'instance.checks.secretsSetTwice.found', {variables: 'JWT_SECRET'}),
    check('platform.instance_key', 'error', 'instance.checks.instanceKey.unusable', {source: 'LIBREFOLIO_INSTANCE_KEY_FILE', reason: 'the file cannot be read'}),
    check('platform.session_cookie', 'ok', 'instance.checks.sessionCookie.ok'),
    LOG_VERBOSE,
    check('accounts.login_limit', 'warning', 'auth.checks.loginLimit.off'),
    check('email.smtp', 'ok', 'email.checks.smtp.ok'),
    check('email.smtp_encryption', 'warning', 'email.checks.smtpEncryption.plain'),
    check('email.links', 'info', 'email.checks.links.missing'),
    check('platform.plugin_secrets', 'error', 'instance.checks.pluginSecrets.unreadable', {count: 2}),
];

/** MIXED for attention, with nothing to warn about in the browser: most severe first, the server's order within. */
const MIXED_ATTENTION: Array<[id: string, severity: Exclude<Severity, 'ok'>]> = [
    ['platform.instance_key', 'error'],
    ['platform.plugin_secrets', 'error'],
    ['platform.jwt_secret', 'warning'],
    ['platform.secrets_set_twice', 'warning'],
    ['accounts.login_limit', 'warning'],
    ['email.smtp_encryption', 'warning'],
    ['platform.log_level', 'info'],
    ['email.links', 'info'],
];

/** The same, with the browser's warning after the server's warnings. */
const MIXED_ATTENTION_WITH_BROWSER: Array<[id: string, severity: Exclude<Severity, 'ok'>]> = [...MIXED_ATTENTION.slice(0, 6), ['accounts.openRegistration', 'warning'], ...MIXED_ATTENTION.slice(6)];

const MIXED_PASSED = ['platform.session_cookie', 'email.smtp'];

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

/** Nothing passed: every check of MIXED that is not ok. */
const NONE_OK: SecurityCheck[] = MIXED.filter((item) => item.severity !== 'ok');

/** All fine but the log level: one info, nothing to do. */
const INFO_ONLY: SecurityCheck[] = ALL_OK.map((item) => (item.check_id === LOG_VERBOSE.check_id ? LOG_VERBOSE : item));

const EXTERNAL_HOST = 'librefolio.example.com';
/** Nothing to warn about in the browser: an instance on invitation only. */
const SILENT: BrowserState = {registrationMode: 'invite', registrationLocked: false, hostname: EXTERNAL_HOST};
/** An instance open to registration, reached from outside the local network. */
const OPEN_EXTERNAL: BrowserState = {registrationMode: 'open', registrationLocked: false, hostname: EXTERNAL_HOST};

describe('SecurityTab — the store it reads', () => {
    // red until A8b
    it('reads the store it is given: on mount it asks that store once, never the generated client, and its root publishes the store’s status', async () => {
        const mounted = await mountTab(SILENT);

        await waitFor(() => expect(mounted.fetch, 'on mount the tab asks its store (ensureLoaded)').toHaveBeenCalledTimes(1));
        await waitForStatus('loading');
        expect(mounted.store.status).toBe('loading');

        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');
        await tick();

        expect(mounted.fetch, 'asked once: the mount does not ask again when the answer lands').toHaveBeenCalledTimes(1);
        expect(fake.listSecurityChecks, 'the tab given a store must not reach the app’s own').not.toHaveBeenCalled();
        expect(findingIds()).toEqual(MIXED_ATTENTION.map(([id]) => id));
    });

    // red until A8b
    it('a store that has already answered is not asked again: the mount calls ensureLoaded(), not reload()', async () => {
        const mounted = await mountTab(SILENT, async (store, answers) => {
            const loading = store.ensureLoaded();
            await waitFor(() => expect(answers, 'premise: the store asked').toHaveLength(1));
            answers[0].resolve(MIXED);
            await settle(loading);
            expect(store.status, 'premise: the store answered before the tab was opened').toBe('ready');
        });

        expect(tabRoot()).toHaveAttribute('data-status', 'ready');
        expect(findingIds()).toEqual(MIXED_ATTENTION.map(([id]) => id));
        await tick();

        expect(mounted.fetch, 'one request for the page, made before the tab was opened').toHaveBeenCalledTimes(1);
        expect(tabRoot()).toHaveAttribute('data-status', 'ready');
    });
});

describe('SecurityTab — waiting for the first answer', () => {
    // red until A8b
    it('security-loading and nothing to read, «check again» disabled; the answer takes the placeholder down', async () => {
        const mounted = await mountTab(SILENT);
        await waitForStatus('loading');

        expect(screen.getByTestId('security-loading')).toBeVisible();
        expect(screen.queryAllByTestId('security-finding')).toEqual([]);
        expect(screen.queryByTestId('security-all-clear'), 'nothing is all clear before the answer').toBeNull();
        expect(screen.queryByTestId('security-passed')).toBeNull();
        expect(screen.queryByTestId('security-load-error')).toBeNull();
        expect(screen.getByTestId('security-refresh'), 'a request runs: nothing to ask again yet').toBeDisabled();

        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        expect(findingIds(), 'premise: the answer is on screen').toEqual(MIXED_ATTENTION.map(([id]) => id));
        expect(screen.queryByTestId('security-loading')).toBeNull();
        expect(screen.getByTestId('security-refresh')).toBeEnabled();
    });
});

describe('SecurityTab — the findings', () => {
    // red until A8b
    it('one security-finding per attention finding: most severe first, the server’s order within a severity, the browser’s warning after the server’s warnings', async () => {
        const mounted = await mountTab(OPEN_EXTERNAL);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        const shown = screen.getAllByTestId('security-finding').map((element) => [element.getAttribute('data-check-id'), element.getAttribute('data-severity')]);

        expect(shown).toEqual(MIXED_ATTENTION_WITH_BROWSER);
    });

    // red until A8b
    it('each finding says its message with its parameters as values, and its severity in words', async () => {
        const mounted = await mountTab(OPEN_EXTERNAL);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        const SAID: Array<[id: string, severity: Exclude<Severity, 'ok'>, message: string]> = [
            ['platform.instance_key', 'error', say('instance.checks.instanceKey.unusable', {source: 'LIBREFOLIO_INSTANCE_KEY_FILE', reason: 'the file cannot be read'})],
            ['platform.plugin_secrets', 'error', say('instance.checks.pluginSecrets.unreadable', {count: 2})],
            ['platform.jwt_secret', 'warning', say('instance.checks.jwtSecret.short', {source: 'JWT_SECRET', length: 12, minimum: 32})],
            ['platform.secrets_set_twice', 'warning', say('instance.checks.secretsSetTwice.found', {variables: 'JWT_SECRET'})],
            ['accounts.login_limit', 'warning', say('auth.checks.loginLimit.off')],
            ['email.smtp_encryption', 'warning', say('email.checks.smtpEncryption.plain')],
            ['accounts.openRegistration', 'warning', say('auth.notices.openRegistration')],
            ['platform.log_level', 'info', say('instance.checks.logLevel.verbose', {log_level: 'DEBUG'})],
            ['email.links', 'info', say('email.checks.links.missing')],
        ];
        for (const [id, severity, message] of SAID) {
            expect(finding(id), `${id}: its message, with the values of its detail`).toHaveTextContent(message);
            expect(finding(id), `${id}: its severity in words, not by colour alone`).toHaveTextContent(say(`settings.securityTab.severity.${severity}`));
        }
    });

    // red until A8b
    it('an action is a link to where the problem is fixed, named by its label; a finding without one has no link', async () => {
        const mounted = await mountTab(OPEN_EXTERNAL);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        const LINKED: Array<[id: string, href: string, labelKey: string]> = [
            ['platform.plugin_secrets', '/settings?tab=plugins', 'settings.securityTab.openPlugins'],
            ['email.smtp_encryption', '/settings?tab=email', 'settings.securityTab.openEmail'],
            ['email.links', '/settings?tab=email', 'settings.securityTab.openEmail'],
            ['accounts.openRegistration', '/settings?tab=admin', 'auth.notices.openRegistrationAction'],
        ];
        for (const [id, href, labelKey] of LINKED) {
            const link = within(finding(id)).getByTestId('security-finding-action');
            expect(link.tagName, `${id}: the action is a link`).toBe('A');
            expect(link).toHaveAttribute('href', href);
            expect(link, `${id}: named by its label`).toHaveAccessibleName(containing(say(labelKey)));
        }
        for (const id of ['platform.instance_key', 'platform.jwt_secret', 'platform.secrets_set_twice', 'accounts.login_limit', 'platform.log_level']) {
            expect(within(finding(id)).queryByTestId('security-finding-action'), `${id}: nothing in the app fixes it, so no link`).toBeNull();
        }
    });

    // red until A8b
    it('no attention finding: security-all-clear, and no finding', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, ALL_OK);
        await waitForStatus('ready');

        const allClear = screen.getByTestId('security-all-clear');
        expect(allClear).toBeVisible();
        expect(allClear).toHaveTextContent(say('settings.securityTab.allClear'));
        expect(screen.queryAllByTestId('security-finding')).toEqual([]);
        expect(screen.getAllByTestId('security-passed-check'), 'the ten checks passed').toHaveLength(10);
    });

    // red until A8b
    it('an info is listed, so the tab is not all clear', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, INFO_ONLY);
        await waitForStatus('ready');

        expect(screen.getAllByTestId('security-finding').map((element) => [element.getAttribute('data-check-id'), element.getAttribute('data-severity')])).toEqual([['platform.log_level', 'info']]);
        expect(screen.queryByTestId('security-all-clear')).toBeNull();
    });

    // red until A8b
    it('the browser’s warning alone: every server check passed, and still not all clear', async () => {
        const mounted = await mountTab(OPEN_EXTERNAL);
        await answer(mounted, 0, ALL_OK);
        await waitForStatus('ready');

        expect(findingIds()).toEqual(['accounts.openRegistration']);
        expect(screen.queryByTestId('security-all-clear')).toBeNull();
        expect(screen.getAllByTestId('security-passed-check')).toHaveLength(10);
    });
});

describe('SecurityTab — the passed checks', () => {
    // red until A8b
    it('in a <details> whose summary counts them, one security-passed-check per ok check in the server’s order — not among the findings', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        const passed = screen.getByTestId('security-passed');
        expect(passed.tagName).toBe('DETAILS');
        const summary = passed.querySelector(':scope > summary');
        expect(summary, 'the count is in the summary, seen with the list closed').not.toBeNull();
        expect(summary).toHaveTextContent(say('settings.securityTab.passed', {count: 2}));
        const items = within(passed).getAllByTestId('security-passed-check');
        expect(items.map((element) => element.getAttribute('data-check-id'))).toEqual(MIXED_PASSED);
        expect(screen.getAllByTestId('security-passed-check'), 'every passed check is inside the details').toHaveLength(items.length);
        for (const id of MIXED_PASSED) expect(findingIds(), `${id} passed: not listed for attention`).not.toContain(id);
    });

    // red until A8b
    it('nothing passed: no security-passed', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, NONE_OK);
        await waitForStatus('ready');

        expect(findingIds(), 'premise: the answer is on screen').toEqual(MIXED_ATTENTION.map(([id]) => id));
        expect(screen.queryByTestId('security-passed')).toBeNull();
        expect(screen.queryAllByTestId('security-passed-check')).toEqual([]);
    });
});

describe('SecurityTab — asking again', () => {
    // red until A8b
    it('«check again» asks even once answered, is disabled while the request runs — the last findings staying, without the placeholder — and the new answer replaces them', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');
        expect(screen.getByTestId('security-refresh')).toBeEnabled();

        await fireEvent.click(screen.getByTestId('security-refresh'));

        await waitFor(() => expect(mounted.fetch, '«check again» is reload(): a new request').toHaveBeenCalledTimes(2));
        await waitForStatus('loading');
        expect(screen.getByTestId('security-refresh'), 'one request at a time').toBeDisabled();
        expect(findingIds(), 'the last findings stay on screen while the new request runs').toEqual(MIXED_ATTENTION.map(([id]) => id));
        expect(screen.queryByTestId('security-loading'), 'there are checks already: no placeholder over them').toBeNull();

        await answer(mounted, 1, ALL_OK);
        await waitForStatus('ready');

        expect(screen.getByTestId('security-all-clear')).toBeVisible();
        expect(screen.queryAllByTestId('security-finding')).toEqual([]);
        expect(screen.getByTestId('security-refresh')).toBeEnabled();
        expect(mounted.fetch).toHaveBeenCalledTimes(2);
    });
});

describe('SecurityTab — a load that fails', () => {
    // red until A8b
    it('a first load that fails: the banner (role alert) with its retry, nothing else to read, nothing asked again by itself; retry asks again and the answer takes the banner down', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, new Error('503 Service Unavailable'));
        await waitForStatus('error');
        await tick();

        const banner = screen.getByTestId('security-load-error');
        expect(banner).toBeVisible();
        expect(banner).toHaveAttribute('role', 'alert');
        expect(banner).toHaveTextContent(say('settings.securityTab.loadError'));
        expect(screen.getByTestId('security-retry')).toBeEnabled();
        expect(screen.queryAllByTestId('security-finding')).toEqual([]);
        expect(screen.queryByTestId('security-all-clear'), 'a failed load is not all clear').toBeNull();
        expect(screen.queryByTestId('security-passed')).toBeNull();
        expect(screen.queryByTestId('security-loading')).toBeNull();
        expect(mounted.fetch, 'a failure is not asked again by itself').toHaveBeenCalledTimes(1);

        await fireEvent.click(screen.getByTestId('security-retry'));

        await waitFor(() => expect(mounted.fetch, 'retry is reload(): a new request').toHaveBeenCalledTimes(2));
        await waitForStatus('loading');
        expect(screen.getByTestId('security-loading'), 'still no check: the placeholder').toBeVisible();

        await answer(mounted, 1, MIXED);
        await waitForStatus('ready');

        expect(findingIds()).toEqual(MIXED_ATTENTION.map(([id]) => id));
        expect(screen.queryByTestId('security-load-error')).toBeNull();
    });

    // red until A8b
    it('a reload that fails: the banner, and the last findings still listed under it', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        await fireEvent.click(screen.getByTestId('security-refresh'));
        await answer(mounted, 1, new Error('timeout'));
        await waitForStatus('error');

        const banner = screen.getByTestId('security-load-error');
        expect(banner).toHaveAttribute('role', 'alert');
        expect(banner).toHaveTextContent(say('settings.securityTab.loadError'));
        expect(screen.getByTestId('security-retry')).toBeInTheDocument();
        expect(findingIds(), 'what the last answer said is still worth reading').toEqual(MIXED_ATTENTION.map(([id]) => id));
        expect(
            within(screen.getByTestId('security-passed'))
                .getAllByTestId('security-passed-check')
                .map((element) => element.getAttribute('data-check-id')),
        ).toEqual(MIXED_PASSED);
        const firstFinding = screen.getAllByTestId('security-finding')[0];
        expect(banner.compareDocumentPosition(firstFinding) & Node.DOCUMENT_POSITION_FOLLOWING, 'the findings are under the banner').toBeTruthy();
    });
});

describe('SecurityTab — colours', () => {
    /** A palette class of the legacy families, as the contract words it. */
    const PALETTE_CLASS = /\b(bg|text|border)-(red|green|yellow|amber|orange|blue|gray|slate|zinc|neutral|stone|emerald|rose|sky)-\d/;
    /** A colour role utility: `bg-lf-danger-soft`, `text-lf-warning`, `border-lf-subtle`. */
    const ROLE_UTILITY = /(?:^|[\s:])[a-z]+(?:-[a-z]+)*-lf-[a-z]/;

    function expectRolesOnly(container: HTMLElement, state: string): void {
        const markup = container.innerHTML;
        expect(markup.match(new RegExp(PALETTE_CLASS.source, 'g')) ?? [], `${state}: palette classes in the markup`).toEqual([]);
        expect(markup.includes('dark:'), `${state}: a dark: variant in the markup — a role changes value under html.dark by itself`).toBe(false);
    }

    // red until A8b
    it('colour roles only: no palette class and no dark: while loading, with every severity listed, and under the load-error banner', async () => {
        // Positive controls: the detectors see what they must, and nothing else.
        expect(PALETTE_CLASS.test('rounded bg-red-50 px-2'), 'premise: a palette class is detected').toBe(true);
        expect(PALETTE_CLASS.test('text-gray-500'), 'premise: a palette class is detected').toBe(true);
        expect(PALETTE_CLASS.test('border-lf-danger-line bg-lf-danger-soft text-lf-danger-on-soft'), 'premise: a role is not a palette class').toBe(false);
        expect(ROLE_UTILITY.test('flex bg-lf-warning-soft'), 'premise: a role is detected').toBe(true);

        const mounted = await mountTab(OPEN_EXTERNAL);
        await waitForStatus('loading');
        expect(screen.getByTestId('security-loading'), 'premise: the loading state is on screen').toBeInTheDocument();
        expectRolesOnly(mounted.container, 'loading');

        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');
        expect(
            screen.getAllByTestId('security-finding').map((element) => element.getAttribute('data-severity')),
            'premise: every severity is on screen',
        ).toEqual(expect.arrayContaining(['error', 'warning', 'info']));
        expect(screen.getAllByTestId('security-finding-action').length, 'premise: the links are on screen').toBeGreaterThan(0);
        expect(screen.getByTestId('security-passed'), 'premise: the passed checks are on screen').toBeInTheDocument();
        expectRolesOnly(mounted.container, 'ready');
        const classes = [...mounted.container.querySelectorAll('[class]')].map((element) => element.getAttribute('class') ?? '');
        expect(
            classes.some((value) => ROLE_UTILITY.test(value)),
            'the severities are coloured, and their colours are roles',
        ).toBe(true);

        await fireEvent.click(screen.getByTestId('security-refresh'));
        await answer(mounted, 1, new Error('timeout'));
        await waitForStatus('error');
        expect(screen.getByTestId('security-load-error'), 'premise: the banner is on screen').toBeInTheDocument();
        expectRolesOnly(mounted.container, 'error');
    });
});

describe('SecurityTab — its words', () => {
    const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

    function messageOf(catalogue: unknown, key: string): unknown {
        return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    }

    /** The ICU arguments a message names: `count` for «{count, plural, …}». */
    function placeholdersOf(message: string): string[] {
        return [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();
    }

    /** The keys the tab renders, with the values it fills each one with. */
    const TAB_KEYS: Array<[key: string, filled: string[]]> = [
        ['settings.securityTab.loadError', []],
        ['settings.securityTab.allClear', []],
        ['settings.securityTab.passed', ['count']],
        ['settings.securityTab.severity.error', []],
        ['settings.securityTab.severity.warning', []],
        ['settings.securityTab.severity.info', []],
        ['settings.securityTab.openEmail', []],
        ['settings.securityTab.openPlugins', []],
        ['settings.securityTab.guide', []],
    ];

    // red until A8b
    it('every key it renders is a message of the four catalogues, naming exactly the values it is filled with', () => {
        for (const [language, catalogue] of Object.entries(CATALOGUES)) {
            for (const [key, filled] of TAB_KEYS) {
                const message = messageOf(catalogue, key);
                expect(typeof message === 'string' && message.trim() !== '', `${language}: ${key} is not a message of the catalogue`).toBe(true);
                expect(placeholdersOf(message as string), `${language}: ${key} names other values than the tab fills`).toEqual(filled);
            }
        }
    });
});

// Lot N69d (release 1.3, workstream A — decision D9 «Guida», with the book; D10 as the developer changed it: the guide of each
// check comes from workstream H's map, `features/instance/checkGuides.ts`, pinned by `checkGuides.test.ts`). Every row of the
// tab — a finding, a passed check, the browser's own — whose id the map knows gets a «Guide» button (`security-guide`, the
// shared `DocsLink`: a book, its label visible, opened in a new tab) to the page and anchor the map holds, in the user's
// language (`/mkdocs/<lang>/<path>`, none for English). A row whose id the map lacks has no button, and says nothing else. The
// button is added to the row: the in-app link of a finding (`security-finding-action`) stays. Red until N69d.
describe('SecurityTab — the guide of each check (SGUIDE-01…08, N69d)', () => {
    const GUIDE = 'settings.securityTab.guide';
    const SERVER_IDS = Object.keys(guides.server);
    const guideOf = (row: HTMLElement) => within(row).getByTestId('security-guide');

    /** Clicks the button and returns what the browser was asked to open. */
    async function opened(button: HTMLElement): Promise<unknown[]> {
        const open = vi.spyOn(window, 'open').mockImplementation(() => null);
        try {
            await fireEvent.click(button);
            return open.mock.calls[0] ?? [];
        } finally {
            open.mockRestore();
        }
    }

    function passedCheck(id: string): HTMLElement {
        const row = screen.queryAllByTestId('security-passed-check').find((candidate) => candidate.getAttribute('data-check-id') === id);
        if (!row) throw new Error(`no security-passed-check with data-check-id="${id}" is rendered`);
        return row;
    }

    beforeEach(() => {
        currentLanguage.set('en');
    });

    it('SGUIDE-01: a finding the map knows has a «Guide» button — a book, named by the label — that opens its page and anchor in a new tab', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        const button = guideOf(finding('accounts.login_limit'));

        expect(button.tagName).toBe('BUTTON');
        expect(button).toHaveAccessibleName(containing(say(GUIDE)));
        expect(button.querySelector('svg'), 'the book').not.toBeNull();
        expect(await opened(button)).toEqual(['/mkdocs/admin/configuration_accounts/#login-limit', '_blank', 'noopener']);
    });

    it('SGUIDE-02: in another language the page is the translated one — /mkdocs/<lang>/… — and the anchor is the same', async () => {
        currentLanguage.set('it');
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        expect(await opened(guideOf(finding('email.smtp_encryption')))).toEqual(['/mkdocs/it/admin/email/#encryption-modes', '_blank', 'noopener']);
    });

    it('SGUIDE-03: a passed check has its guide too — the same page serves every state of a check', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        expect(await opened(guideOf(passedCheck('platform.session_cookie')))).toEqual(['/mkdocs/admin/connection_checks/#session-cookie', '_blank', 'noopener']);
    });

    it('SGUIDE-04: the finding only the browser knows — open registration — has its guide as well', async () => {
        const mounted = await mountTab(OPEN_EXTERNAL);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        expect(await opened(guideOf(finding('accounts.openRegistration')))).toEqual(['/mkdocs/admin/settings/#open-registration-warning', '_blank', 'noopener']);
    });

    it('SGUIDE-05: a check the map does not know has no button — and the rows around it keep theirs', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, [check('plugin.future_check', 'warning', 'instance.checks.futureCheck.warn'), check('plugin.future_ok', 'ok', 'instance.checks.futureCheck.ok'), check('accounts.login_limit', 'warning', 'auth.checks.loginLimit.off')]);
        await waitForStatus('ready');

        expect(within(finding('plugin.future_check')).queryByTestId('security-guide'), 'no entry in the map, no button').toBeNull();
        expect(within(passedCheck('plugin.future_ok')).queryByTestId('security-guide'), 'the same for a passed check').toBeNull();
        expect(guideOf(finding('accounts.login_limit'))).toBeInTheDocument();
        expect(screen.getAllByTestId('security-guide'), 'one button for the one check the map knows').toHaveLength(1);
    });

    it('SGUIDE-06: every check of the server the map lists has a button on its row — the map and the tab agree on all of them', async () => {
        const mounted = await mountTab(SILENT);
        await answer(
            mounted,
            0,
            SERVER_IDS.map((id) => check(id, 'ok', `instance.checks.${id}`)),
        );
        await waitForStatus('ready');

        const missing = SERVER_IDS.filter((id) => within(passedCheck(id)).queryByTestId('security-guide') === null);
        expect(missing, 'checks of the map with no button').toEqual([]);
        expect(screen.getAllByTestId('security-guide')).toHaveLength(SERVER_IDS.length);
    });

    it('SGUIDE-07: the button is added to the in-app link of a finding, not put in its place', async () => {
        const mounted = await mountTab(SILENT);
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        const row = finding('email.smtp_encryption');

        expect(within(row).getByTestId('security-finding-action')).toHaveAttribute('href', '/settings?tab=email');
        expect(guideOf(row)).toBeInTheDocument();
    });

    it('SGUIDE-08: the script the Content-Security-Policy blocked — a finding of the browser — has its guide', async () => {
        const mounted = await mountTab({...SILENT, blockedScripts: ['https://cdn.example.com/x.js']});
        await answer(mounted, 0, MIXED);
        await waitForStatus('ready');

        expect(await opened(guideOf(finding('platform.blockedScript')))).toEqual(['/mkdocs/admin/configuration_security/#csp', '_blank', 'noopener']);
    });
});
