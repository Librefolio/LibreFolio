// @vitest-environment jsdom
/**
 * InstanceRestoreInterruptedPage — what everyone sees when the state of a restore cannot be read (workstream H, lot
 * B-33, the start's part).
 *
 * When `.restore/restore.json` cannot be read the backend serves no data: `GET /api/v1/system/instance` answers
 * `restore_interrupted: true` and every other route answers `423 {"detail": {"code": "instance_restore_interrupted"}}`
 * to anyone. The root layout's `AwaitingRestoreGate` then shows this page instead of the app or the login: the restore
 * stopped half way, the administrator must run `./dev.py backup pending --recover previous`.
 *
 * The contract under test:
 *   - the root `instance-restore-interrupted` holds a `role="alert"` section (an error: something is broken) with an
 *     `h1` reading `instance.restoreInterrupted.title` and the paragraph `instance-restore-interrupted-message`
 *     reading `instance.restoreInterrupted.message`; the root also holds the paragraph `instance-restore-interrupted-admin`
 *     (`instance.restoreInterrupted.adminHint`), the note `instance-restore-interrupted-auto`
 *     (`instance.restoreInterrupted.autoReload`) and the button `instance-restore-interrupted-retry` named
 *     `instance.awaitingRestore.retry` (the key of the awaiting page, reused);
 *   - FB-27 + checkpoint 2 triage (who can solve an interrupted restore alone?): the recovery is a CLI command on the
 *     server, so the help depends on WHO reads the page. The prop `selfHosted?: boolean`, by default
 *     `selfHostedConfirmed()` (`$lib/features/instance/profile`: true only once the server answered `selfhosted`), picks it:
 *       - `selfHosted: false` (a managed instance, or the server has not answered): NO docs link
 *         (`instance-restore-interrupted-docs` absent: the customer cannot run the command, support is the help) and the
 *         support link with the report, or the `instance-restore-interrupted-support-missing` line without an address;
 *       - `selfHosted: true`: the docs link is BACK, `<a data-testid="instance-restore-interrupted-docs" target="_blank"
 *         rel="noopener noreferrer">` named `instance.restoreInterrupted.docs`, to `/mkdocs/<lang prefix>admin/<anchor>`
 *         (prefix `it/`, `fr/`, `es/`, none in English, from `currentLanguage`; anchor `cli_backup/#backup-pending-unreadable`
 *         for reason restore_state / null / absent, no link for owner_assignment: that case has no guide).
 *         The support link with the report is still there when the instance has a usable address; there is NEVER the
 *         support-missing line (the administrator IS the host);
 *   - nothing else to act on: the retry is the only button, no form, no field, no logout; the links are the docs link
 *     (self-hosted only) and the support link (D7, only with a usable support address);
 *   - the four keys have a string in all four shipped catalogues (`$lib/i18n/{en,it,fr,es}.json`);
 *   - D7, the support link: when the instance has a support address — the prop `supportUrl`, by default
 *     `instanceConfig.config.support_url` (`GET /system/instance`) — the page shows the anchor
 *     `instance-restore-interrupted-support` named `instance.restoreInterrupted.support` (a sixth key, all four
 *     catalogues). The address is read through the app's `supportChannel(value, {githubFallback: false})`
 *     (`$lib/features/support/supportChannel`). FB-27: the link carries the report of the problem: its href is
 *     `reportHref(channel, buildCheckReport({checkId: 'platform.restore_interrupted', severity: 'error', instanceAddress:
 *     window.location.origin, appVersion: APP_VERSION, date: new Date()}))` — a `mailto:` with subject and body for a mail
 *     address, the page with `title` and `body` in its query for a page, opened in a new tab (`target="_blank"`,
 *     `rel="noopener noreferrer"`) — and the report is in the href only, never in the text. Without a usable address (null,
 *     empty, `javascript:…`, a mailto with two addresses) there is no link at all, and no GitHub fallback: the paragraph
 *     `instance-restore-interrupted-support-missing`, named `instance.restoreInterrupted.supportMissing`, says so instead;
 *   - the background is the login page's own `AnimatedBackground` (`$lib/components/ui/AnimatedBackground.svelte`,
 *     `data-testid="animated-background"`), mounted inside the page and imported from that module, never a copy;
 *   - clicking retry calls `onretry`; by default `onretry` is `window.location.reload()`;
 *   - every `pollMs` (default 30 000) the page calls `fetchInterrupted()`: on `false` it calls `onretry()` once and
 *     stops polling; `true`, `undefined`, and a failed fetch keep the polling going (a failure is swallowed, never an
 *     unhandled rejection); unmounting stops the polling. By default `fetchInterrupted` reads `GET /system/instance`
 *     (through the generated client) and returns its `restore_interrupted`.
 *
 * Labels are read in a marker locale (the pattern of `InstanceAwaitingRestorePage.test.ts`): a private-use language
 * where every key reads `⟦key⟧`, so a label taken from the catalogue reads its marker and a literal reads as itself.
 * Nothing reads what a language says. Whether the catalogues hold the keys is asked of the JSON files. The docs link's
 * language is `currentLanguage` (`$lib/stores/app/language`), the store `DocsLink` reads; the case of another language
 * sets it and puts English back after itself.
 *
 * Polling runs on fake timers (`setTimeout`/`setInterval` and their clears only, so Svelte's microtask scheduling stays
 * real), advanced with `advanceTimersByTimeAsync`, which also drains the promise of each answer: no real wait. A case
 * counts the calls made before it advances, so it holds whether or not the page also asks once at mount.
 *
 * `$lib/api` is a mock whose generated method is the spy of the default `fetchInterrupted`; nothing reaches the network.
 *
 * The support cases give the page its address through the prop, while the real `instanceConfig` store (loaded with an
 * injected answer, the pattern of `AssetModal.test.ts`, no module mock) holds a different, usable one: a link to the
 * store's address, or a link where the prop says there is none, shows the page did not read the prop. The default case
 * mounts without the prop and reads the store. The store is put back to its defaults after each case.
 *
 * Red until B-33 (the start's part): the component does not exist (the whole file fails to import), and the catalogues
 * have no `instance.restoreInterrupted` keys. The D7 cases are red until the support link (contract §3): the page has
 * no `supportUrl` prop nor support link, and the catalogues have no `instance.restoreInterrupted.support`.
 *
 * Lot H5-3 (the owner's choice after a restore from the app on a managed instance): `GET /system/instance` also answers
 * `restore_interrupted_reason: 'restore_state' | 'owner_assignment' | null`. The page gains the prop
 * `reason?: 'restore_state' | 'owner_assignment' | null`. Absent, null and `'restore_state'` are today's page (same keys,
 * same docs link `admin/cli_backup/#backup-pending-unreadable`). `'owner_assignment'` reads
 * `instance.restoreInterrupted.ownerTitle` (the h1), `.ownerMessage` (`instance-restore-interrupted-message`) and
 * `.ownerAdminHint` (`instance-restore-interrupted-admin`), and it has no docs link
 * (the owner's account has no guide). Support link, retry button and the polling are the
 * same for both reasons. The three keys exist in the `instance` subsystem source of all four languages (the generated
 * catalogue fills a missing translation from English, so the sources themselves are read: no generic parity gate
 * would catch a missing it/fr/es entry). Red until H5-3: the page has no `reason` prop (the owner cases read today's
 * keys and link) and the sources have no owner keys.
 *
 * FB-27 (a «guide or support» help for the checks): the docs cases of this file are now «no docs link» cases, the support
 * cases check the report in the href (the date is frozen, only `Date` is faked, so the href can be compared whole), and the
 * new key `instance.restoreInterrupted.supportMissing` is read in the four catalogues and in the four `instance` sources.
 * Red until FB-27: the page still links the documentation, its support link is the bare address and it has no missing note.
 *
 * The real store holds `profile: 'selfhosted'` once loaded (its defaults), so every case about the managed page passes
 * `selfHosted: false` explicitly (`mountPolling` does by default): none depends on the store's profile or on the order of
 * the cases. The cases of the prop's DEFAULT load the store with the profile they need.
 * Red until the self-hosted help lands: the page has no `selfHosted` prop, so the docs link never appears and the
 * support-missing line stays where a self-hosted administrator must not see it.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, onTestFinished, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {addMessages, waitLocale} from 'svelte-i18n';
import {readFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import {_ as translate} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {supportChannel, reportHref} from '$lib/features/support/supportChannel';
import {buildCheckReport} from '$lib/features/instance/checkSupportReport';
import {APP_VERSION} from '$lib/version';
import {DEFAULT_INSTANCE_CONFIG, instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import InstanceRestoreInterruptedPage from './InstanceRestoreInterruptedPage.svelte';

const mocks = vi.hoisted(() => ({
    getInstanceConfig: vi.fn().mockName('zodiosApi.get_instance_config_api_v1_system_instance_get'),
}));

vi.mock('$lib/api', () => ({zodiosApi: {get_instance_config_api_v1_system_instance_get: mocks.getInstanceConfig}}));

/** The four keys of the page's text. */
const NEW_KEYS = {
    title: 'instance.restoreInterrupted.title',
    message: 'instance.restoreInterrupted.message',
    adminHint: 'instance.restoreInterrupted.adminHint',
    autoReload: 'instance.restoreInterrupted.autoReload',
} as const;
/** H5-3: the three keys of the `owner_assignment` reason. */
const OWNER_KEYS = {
    title: 'instance.restoreInterrupted.ownerTitle',
    message: 'instance.restoreInterrupted.ownerMessage',
    adminHint: 'instance.restoreInterrupted.ownerAdminHint',
} as const;
/** The label of the docs link, shown to the administrator of a self-hosted instance. */
const DOCS_KEY = 'instance.restoreInterrupted.docs';
/** The retry label: the awaiting page's key, reused. */
const RETRY_KEY = 'instance.awaitingRestore.retry';
/** D7: the label of the support link, a sixth key of this page. */
const SUPPORT_KEY = 'instance.restoreInterrupted.support';
/** FB-27: the note shown instead of the support link when the instance names no usable address. */
const SUPPORT_MISSING_KEY = 'instance.restoreInterrupted.supportMissing';

/** A usable address the store holds in the support cases: a link to it means the page ignored its prop. */
const STORE_SUPPORT_URL = 'mailto:store-support@example.org';

/** The default interval of the contract: 30 s. */
const DEFAULT_POLL_MS = 30_000;
/** A short interval for the injected cases: the arithmetic stays readable. */
const POLL_MS = 1_000;

/** FB-27: the instant the report is written at (only `Date` is faked), so a href can be compared whole. */
const FROZEN = new Date('2026-10-28T09:30:15.250Z');

function freezeDate(): void {
    vi.useFakeTimers({toFake: ['Date']});
    vi.setSystemTime(FROZEN);
}

/** FB-27: the href the contract builds for the support link of this page, from the channel of `address`. */
function reportLink(address: string): string {
    const channel = supportChannel(address, {githubFallback: false});
    if (channel === null) throw new Error(`premise: ${address} is not a usable support address`);
    return reportHref(channel, buildCheckReport({checkId: 'platform.restore_interrupted', severity: 'error', instanceAddress: window.location.origin, appVersion: APP_VERSION, date: new Date(FROZEN)}));
}

// ---------------------------------------------------------------------------
// Marker locale — the pattern of DataEditor.test.ts (W-B8).

/** A private-use language (BCP 47 reserves qaa–qtz): Intl accepts it, and it is none of the app's catalogues. */
const MARKER_LOCALE = 'qaa';
/** The four shipped catalogues, by language. */
const SHIPPED_CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

/** How a label reads in the marker locale: `⟦key⟧`. */
const marked = (key: string): string => `⟦${key}⟧`;

/** The value behind a dotted key of a catalogue, if any. */
const leafOf = (catalogue: unknown, key: string): unknown => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);

/** Every dotted key of a catalogue that holds a string. */
function stringKeysOf(node: unknown, prefix = ''): string[] {
    if (typeof node === 'string') return [prefix];
    if (node === null || typeof node !== 'object') return [];
    return Object.entries(node).flatMap(([part, child]) => stringKeysOf(child, prefix ? `${prefix}.${part}` : part));
}

/** Each of `keys` that some catalogue has no string for, with those catalogues: `{}` when all four have all of them. */
function catalogueGaps(keys: readonly string[]): Record<string, string[]> {
    const gaps = keys.map((key) => [key, Object.entries(SHIPPED_CATALOGUES).flatMap(([lang, catalogue]) => (typeof leafOf(catalogue, key) === 'string' ? [] : [lang]))] as const);
    return Object.fromEntries(gaps.filter(([, langs]) => langs.length > 0));
}

/** Switch svelte-i18n to the marker locale: every key of the English catalogue, and each key of this page, reads as its marker. */
async function useMarkerLocale(): Promise<void> {
    const messages: Record<string, string> = Object.fromEntries(stringKeysOf(en).map((key) => [key, marked(key)]));
    for (const key of [...Object.values(NEW_KEYS), ...Object.values(OWNER_KEYS), RETRY_KEY, SUPPORT_KEY, SUPPORT_MISSING_KEY, DOCS_KEY]) messages[key] = marked(key);
    addMessages(MARKER_LOCALE, messages);
    await setupI18n(MARKER_LOCALE);
}

function text(element: Element): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** Fake only the timers: Svelte schedules on microtasks, which stay real. */
function useFakeTimers(): void {
    vi.useFakeTimers({toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval']});
}

/** A `fetchInterrupted` that never answers: the cases about what the page shows. */
const neverAnswers = (): Promise<boolean | undefined> => new Promise(() => {});

/**
 * Mount with an injected `fetchInterrupted` and `onretry`, and return them; `extra` adds props (the support address, the
 * reason, `selfHosted`). `selfHosted` is false unless `extra` says otherwise: the managed page, whatever the store's profile.
 */
function mountPolling(fetchInterrupted: () => Promise<boolean | undefined>, pollMs = POLL_MS, extra: Record<string, unknown> = {}) {
    const spy = vi.fn(fetchInterrupted).mockName('fetchInterrupted');
    const onretry = vi.fn().mockName('onretry');
    const view = render(InstanceRestoreInterruptedPage, {props: {fetchInterrupted: spy, onretry, pollMs, selfHosted: false, ...extra}});
    flushSync();
    expect(screen.getByTestId('instance-restore-interrupted'), 'Barrier: the page is mounted').toBeInTheDocument();
    return {fetchInterrupted: spy, onretry, view};
}

/** The sources of the `instance` subsystem, by language: what the catalogue build reads (no fallback applied). */
const INSTANCE_SOURCE_DIR = join(dirname(fileURLToPath(import.meta.url)), '../i18n');
const SOURCE_LANGUAGES = ['en', 'it', 'fr', 'es'] as const;

/** Each language of the subsystem source that has no non-empty string for `key`. */
function sourceGaps(key: string): string[] {
    return SOURCE_LANGUAGES.filter((lang) => {
        const leaf = leafOf(JSON.parse(readFileSync(join(INSTANCE_SOURCE_DIR, `${lang}.json`), 'utf8')), key);
        return typeof leaf !== 'string' || leaf.trim() === '';
    });
}

/** The real store, loaded with an injected answer: `support_url` is the instance's support address. */
async function useInstanceSupportUrl(supportUrl: string | null): Promise<void> {
    await instanceConfig.load({force: true, fetchConfig: async () => ({...DEFAULT_INSTANCE_CONFIG, support_url: supportUrl})});
    expect(instanceConfig.config.support_url, 'precondition: the store holds the support address').toBe(supportUrl);
}

/** The support link of the page: an anchor named by its key, to `href` (the report is in it). */
function expectSupportLink(link: HTMLElement, href: string): void {
    expect(link.tagName, 'the support link is an anchor').toBe('A');
    expect(link).toHaveAccessibleName(marked(SUPPORT_KEY));
    expect(link.getAttribute('href'), 'where the instance says support is, with the report').toBe(href);
}

/** FB-27: no way out but the retry: no link of any kind, and the paragraph that says the instance names no support. */
function expectSupportMissing(root: HTMLElement): void {
    const missing = within(root).getByTestId('instance-restore-interrupted-support-missing');
    expect(missing.tagName, 'a paragraph, not a link').toBe('P');
    expect(text(missing)).toBe(marked(SUPPORT_MISSING_KEY));
    expect(within(root).queryByTestId('instance-restore-interrupted-support'), 'no support link').toBeNull();
    expect(document.body.querySelectorAll('a'), 'no link of any kind: no docs, no GitHub fallback').toHaveLength(0);
    expect(document.body.innerHTML, 'no GitHub fallback').not.toContain('github.com');
}

/** The app's docs-URL rule (`DocsLink`): `/mkdocs/`, the language prefix (none in English), the path. */
const docsUrl = (lang: string, path: string): string => `/mkdocs/${lang && lang !== 'en' ? `${lang}/` : ''}${path}`;
/** The guide's section on an unreadable restore state (reason restore_state, null or absent). The owner's account has no guide. */
const RESTORE_STATE_DOCS_PATH = 'admin/cli_backup/#backup-pending-unreadable';
const DOCS_LANGUAGES = ['en', 'it', 'fr', 'es'] as const;

/** The docs link of the self-hosted page: an anchor to `href`, in a new tab, without a window.opener nor a referrer. */
function expectDocsLink(link: HTMLElement, href: string): void {
    expect(link.tagName, 'the docs link is an anchor').toBe('A');
    expect(link.getAttribute('href'), 'the guide section of the reason, in the interface language').toBe(href);
    expect(link, 'in a new tab').toHaveAttribute('target', '_blank');
    const rel = (link.getAttribute('rel') ?? '').split(/\s+/);
    expect(rel, 'without a window.opener').toContain('noopener');
    expect(rel, 'without a referrer').toContain('noreferrer');
}

/** The managed page: no docs link, no link to the documentation anywhere; the retry painted first so the absence means something. */
function expectNoDocs(root: HTMLElement, why: string): void {
    expect(within(root).getByTestId('instance-restore-interrupted-retry'), `${why}: Barrier: the page painted`).toBeVisible();
    expect(within(root).queryByTestId('instance-restore-interrupted-docs'), `${why}: no docs link`).toBeNull();
    expect(
        [...document.body.querySelectorAll('a')].filter((link) => (link.getAttribute('href') ?? '').includes('/mkdocs/')),
        `${why}: no link to the documentation`,
    ).toEqual([]);
}

beforeAll(async () => {
    await setupI18n('en');
    // Negative assertions below (no further poll, no reload) would pass vacuously where effects never run.
    assertEffectsRun();
});

beforeEach(async () => {
    mocks.getInstanceConfig.mockReset();
    await useMarkerLocale();
});

afterEach(async () => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    // The store's defaults again (no support address) for whatever runs next; `loaded` has no way back to false.
    await instanceConfig.load({force: true, fetchConfig: async () => DEFAULT_INSTANCE_CONFIG});
    await setupI18n('en');
});

describe('InstanceRestoreInterruptedPage — the catalogues', () => {
    it('has a string for each of its four keys in all four shipped catalogues', () => {
        expect(catalogueGaps(Object.values(NEW_KEYS))).toEqual({});
    });

    it('D7: has a string for the support link key in all four shipped catalogues', () => {
        expect(catalogueGaps([SUPPORT_KEY])).toEqual({});
    });

    it('FB-27: has a string for the support-missing key in all four shipped catalogues', () => {
        expect(catalogueGaps([SUPPORT_MISSING_KEY])).toEqual({});
    });

    it('has a string for the docs link key (shown to a self-hosted administrator) in all four shipped catalogues', () => {
        expect(catalogueGaps([DOCS_KEY])).toEqual({});
    });

    it('reuses the retry key of the awaiting page, present in all four catalogues', () => {
        expect(catalogueGaps([RETRY_KEY])).toEqual({});
    });

    it('control: the marker locale is live', () => {
        expect(get(translate)(NEW_KEYS.title)).toBe(marked(NEW_KEYS.title));
    });
});

describe('InstanceRestoreInterruptedPage — what it shows', () => {
    it('reads its title, message, admin hint, note and retry label from the catalogue', () => {
        mountPolling(neverAnswers);
        expect(get(translate)(NEW_KEYS.title), 'control: the marker locale is live').toBe(marked(NEW_KEYS.title));
        const root = screen.getByTestId('instance-restore-interrupted');

        expect(text(within(root).getByRole('heading', {level: 1}))).toBe(marked(NEW_KEYS.title));
        expect(text(within(root).getByTestId('instance-restore-interrupted-message'))).toBe(marked(NEW_KEYS.message));
        expect(text(within(root).getByTestId('instance-restore-interrupted-admin'))).toBe(marked(NEW_KEYS.adminHint));
        expect(text(within(root).getByTestId('instance-restore-interrupted-auto'))).toBe(marked(NEW_KEYS.autoReload));
        const retry = within(root).getByTestId('instance-restore-interrupted-retry');
        expect(retry.tagName, 'a real button').toBe('BUTTON');
        expect(retry).toHaveAccessibleName(marked(RETRY_KEY));
    });

    it('announces the title and the message as an alert: the restore stopped half way', () => {
        mountPolling(neverAnswers);
        const root = screen.getByTestId('instance-restore-interrupted');

        const alert = within(root).getByRole('alert');
        expect(within(alert).getByRole('heading', {level: 1}), 'the h1 is inside the alert').toBeInTheDocument();
        expect(within(alert).getByTestId('instance-restore-interrupted-message'), 'the message is inside the alert').toBeInTheDocument();
    });

    it('selfHosted false: has no docs link, in English or in another language: the customer is sent to support, not to a MkDocs page', async () => {
        for (const language of ['en', 'it'] as const) {
            currentLanguage.set(language);
            await waitLocale(language);
            try {
                mountPolling(neverAnswers, POLL_MS, {supportUrl: 'mailto:help@example.org'});
                const root = screen.getByTestId('instance-restore-interrupted');
                // Presence barrier: the page painted its controls, so the absences below are not "nothing rendered yet"
                expect(within(root).getByTestId('instance-restore-interrupted-retry')).toBeVisible();
                expect(within(root).getByTestId('instance-restore-interrupted-support')).toBeVisible();

                expect(within(root).queryByTestId('instance-restore-interrupted-docs'), `${language}: no docs link`).toBeNull();
                expect(
                    [...document.body.querySelectorAll('a')].filter((link) => (link.getAttribute('href') ?? '').includes('/mkdocs/')),
                    `${language}: no link to the documentation`,
                ).toEqual([]);
            } finally {
                cleanup();
                currentLanguage.set('en');
                await waitLocale('en');
            }
        }
    });

    it('offers nothing to act on but the retry when there is no support address: no link at all, no logout, no form, no field', async () => {
        await useInstanceSupportUrl(null);
        mountPolling(neverAnswers);
        const root = screen.getByTestId('instance-restore-interrupted');
        // Presence barrier: the page painted its control and the note, so the absences below are not "nothing rendered yet".
        const retry = within(root).getByTestId('instance-restore-interrupted-retry');
        expect(retry).toBeVisible();
        expectSupportMissing(root);

        expect(within(root).getAllByRole('button'), 'the retry is the only button').toEqual([retry]);
        expect(document.body.querySelectorAll('form, input, select, textarea'), 'no form, no field').toHaveLength(0);
        expect(screen.queryByTestId('instance-blocked-logout'), 'no logout button').toBeNull();
    });

    it('D7: with a support address, the support link is the only link, the retry still the only button, and there is no missing note', () => {
        mountPolling(neverAnswers, POLL_MS, {supportUrl: 'mailto:help@example.org'});
        const root = screen.getByTestId('instance-restore-interrupted');
        const retry = within(root).getByTestId('instance-restore-interrupted-retry');
        const support = within(root).getByTestId('instance-restore-interrupted-support');
        expect(retry).toBeVisible();
        expect(support).toBeVisible();

        expect(within(root).getAllByRole('button'), 'the retry is the only button').toEqual([retry]);
        expect([...document.body.querySelectorAll('a')], 'the support link is the only link').toEqual([support]);
        expect(within(root).queryByTestId('instance-restore-interrupted-support-missing'), 'no missing note when there is a link').toBeNull();
        expect(document.body.querySelectorAll('form, input, select, textarea'), 'no form, no field').toHaveLength(0);
        expect(screen.queryByTestId('instance-blocked-logout'), 'no logout button').toBeNull();
    });

    it("uses the login page's animated background, mounted inside the page", () => {
        mountPolling(neverAnswers);
        const root = screen.getByTestId('instance-restore-interrupted');

        expect(within(root).getByTestId('animated-background')).toBeInTheDocument();
        expect(screen.getAllByTestId('animated-background'), 'one background').toHaveLength(1);
    });

    it('imports that background from the shared component, never a copy', () => {
        const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'InstanceRestoreInterruptedPage.svelte'), 'utf8');

        expect(source).toMatch(/import\s+AnimatedBackground\s+from\s+['"]\$lib\/components\/ui\/AnimatedBackground\.svelte['"]/);
        expect(source).toMatch(/<AnimatedBackground\b[^>]*\/?>/);
    });

    it('decides the help from the prop selfHosted, whose default is selfHostedConfirmed(), never from a hand-made profile comparison', () => {
        const source = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'InstanceRestoreInterruptedPage.svelte'), 'utf8');

        expect(source).toMatch(/import\s+\{[^}]*\bselfHostedConfirmed\b[^}]*\}\s+from\s+['"]\$lib\/features\/instance\/profile['"]/);
        expect(source).toMatch(/selfHosted\s*=\s*selfHostedConfirmed\(\)/);
        expect(source, 'the profile is read through the shared helper').not.toMatch(/\.profile\s*[!=]==/);
    });
});

describe('InstanceRestoreInterruptedPage — D7, the support link', () => {
    beforeEach(async () => {
        freezeDate();
        // The store holds a different, usable address: a link to it means the page did not read its prop.
        await useInstanceSupportUrl(STORE_SUPPORT_URL);
    });

    it('links a mailto support address as a mailto: with the report of the problem as subject and body', () => {
        const value = 'mailto:help@example.org';
        expect(supportChannel(value, {githubFallback: false}), 'premise: the app reads it as one mail address').toEqual({kind: 'mailto', address: 'help@example.org'});
        mountPolling(neverAnswers, POLL_MS, {supportUrl: value});

        const link = within(screen.getByTestId('instance-restore-interrupted')).getByTestId('instance-restore-interrupted-support');

        expectSupportLink(link, reportLink(value));
        const href = link.getAttribute('href') ?? '';
        expect(href, 'a mailto to the instance’s address').toMatch(/^mailto:help@example\.org\?subject=/);
        const body = decodeURIComponent(/&body=(.*)$/.exec(href)?.[1] ?? '').split('\r\n');
        expect(body).toContain('Check: platform.restore_interrupted');
        expect(body).toContain('Severity: error');
        expect(body).toContain(`Instance: ${window.location.origin}`);
        expect(body).toContain(`LibreFolio ${APP_VERSION}`);
        expect(body).toContain(`Date: ${FROZEN.toISOString()}`);
        expect(link, 'a mailto opens in this tab').not.toHaveAttribute('target');
    });

    it('links a support page at its normalized address with the report as title and body, in a new tab, without a window.opener nor a referrer', () => {
        const value = '  https://Support.Example.org  ';
        const channel = supportChannel(value, {githubFallback: false});
        expect(channel, 'premise: the app reads it as a page, normalized').toEqual({kind: 'page', url: 'https://support.example.org/'});
        mountPolling(neverAnswers, POLL_MS, {supportUrl: value});

        const link = within(screen.getByTestId('instance-restore-interrupted')).getByTestId('instance-restore-interrupted-support');

        expectSupportLink(link, reportLink(value));
        const url = new URL(link.getAttribute('href') ?? '');
        expect(`${url.origin}${url.pathname}`).toBe('https://support.example.org/');
        expect(url.searchParams.get('title')).toContain('platform.restore_interrupted');
        expect(url.searchParams.get('body')?.split('\n')).toContain('Check: platform.restore_interrupted');
        expect(link, 'in a new tab').toHaveAttribute('target', '_blank');
        const rel = (link.getAttribute('rel') ?? '').split(/\s+/);
        expect(rel, 'without a window.opener').toContain('noopener');
        expect(rel, 'without a referrer').toContain('noreferrer');
    });

    it('by default reads the support address of the instance configuration (GET /system/instance)', async () => {
        await useInstanceSupportUrl('https://help.example.org/librefolio');
        render(InstanceRestoreInterruptedPage, {props: {fetchInterrupted: neverAnswers, onretry: vi.fn()}});
        flushSync();

        const link = within(screen.getByTestId('instance-restore-interrupted')).getByTestId('instance-restore-interrupted-support');

        expectSupportLink(link, reportLink('https://help.example.org/librefolio'));
        expect(link, 'a page: in a new tab').toHaveAttribute('target', '_blank');
    });

    it('by default shows no support link, and the missing note, when the instance names no support address (managed page)', async () => {
        await useInstanceSupportUrl(null);
        render(InstanceRestoreInterruptedPage, {props: {fetchInterrupted: neverAnswers, onretry: vi.fn(), selfHosted: false}});
        flushSync();
        const root = screen.getByTestId('instance-restore-interrupted');
        // Presence barrier: the page painted its retry, so the absences below are not "nothing rendered yet".
        expect(within(root).getByTestId('instance-restore-interrupted-retry')).toBeVisible();

        expectSupportMissing(root);
    });

    it('the report is only in the href: never in the text, a title or a label', () => {
        mountPolling(neverAnswers, POLL_MS, {supportUrl: 'mailto:help@example.org'});
        const root = screen.getByTestId('instance-restore-interrupted');
        // Presence barrier: the link is there
        expect(within(root).getByTestId('instance-restore-interrupted-support')).toBeVisible();

        const attributes = [root, ...root.querySelectorAll('*')].flatMap((element) => [...element.attributes].filter((attribute) => ['title', 'aria-label', 'alt'].includes(attribute.name)).map((attribute) => attribute.value));
        const shown = [root.textContent ?? '', ...attributes].join('\n');
        for (const piece of ['Check:', 'Severity:', 'Instance:', 'Date:', FROZEN.toISOString(), 'platform.restore_interrupted']) {
            expect(shown, `«${piece}» belongs to the report, which is only in the href`).not.toContain(piece);
        }
    });

    const UNUSABLE: ReadonlyArray<readonly [string, string | null]> = [
        ['null', null],
        ['empty', ''],
        ['blank', '   '],
        ['a javascript: URL', 'javascript:alert(1)'],
        ['a mailto with two addresses', 'mailto:help@example.org,other@example.org'],
    ];

    it.each(UNUSABLE)('shows no link at all for %s, the missing note instead, and no GitHub fallback', (_label, value) => {
        expect(supportChannel(value, {githubFallback: false}), 'premise: the app finds no usable address').toBeNull();
        expect(supportChannel(value, {githubFallback: true})?.kind, 'premise: a GitHub fallback would exist, so its absence means something').toBe('github');
        mountPolling(neverAnswers, POLL_MS, {supportUrl: value});
        const root = screen.getByTestId('instance-restore-interrupted');
        // Presence barrier: the page painted its retry, so the absences below are not "nothing rendered yet".
        expect(within(root).getByTestId('instance-restore-interrupted-retry')).toBeVisible();

        expectSupportMissing(root);
    });
});

describe('InstanceRestoreInterruptedPage — the retry button', () => {
    it('calls onretry when clicked', async () => {
        const {onretry} = mountPolling(neverAnswers);

        await fireEvent.click(screen.getByTestId('instance-restore-interrupted-retry'));

        expect(onretry).toHaveBeenCalledTimes(1);
    });

    it('reloads the page by default', async () => {
        const reload = vi.fn().mockName('location.reload');
        vi.stubGlobal('location', {href: 'http://librefolio.test/', pathname: '/', search: '', hash: '', origin: 'http://librefolio.test', reload});
        render(InstanceRestoreInterruptedPage, {props: {fetchInterrupted: neverAnswers}});
        flushSync();

        await fireEvent.click(screen.getByTestId('instance-restore-interrupted-retry'));

        expect(reload, 'the app starts again from a clean page').toHaveBeenCalledTimes(1);
    });
});

describe('InstanceRestoreInterruptedPage — polling the state', () => {
    it('asks once every pollMs while the restore stays interrupted', async () => {
        useFakeTimers();
        const {fetchInterrupted, onretry} = mountPolling(() => Promise.resolve(true));
        const atMount = fetchInterrupted.mock.calls.length;

        await vi.advanceTimersByTimeAsync(POLL_MS - 1);
        expect(fetchInterrupted, 'not before pollMs has elapsed').toHaveBeenCalledTimes(atMount);
        await vi.advanceTimersByTimeAsync(1);
        expect(fetchInterrupted, 'one call at pollMs').toHaveBeenCalledTimes(atMount + 1);
        await vi.advanceTimersByTimeAsync(POLL_MS * 2);
        expect(fetchInterrupted, 'one more call per interval').toHaveBeenCalledTimes(atMount + 3);
        expect(onretry, 'still interrupted: no reload').not.toHaveBeenCalled();
    });

    it('polls every 30 seconds by default', async () => {
        useFakeTimers();
        const fetchInterrupted = vi.fn(() => Promise.resolve<boolean | undefined>(true)).mockName('fetchInterrupted');
        render(InstanceRestoreInterruptedPage, {props: {fetchInterrupted, onretry: vi.fn()}});
        flushSync();
        const atMount = fetchInterrupted.mock.calls.length;

        await vi.advanceTimersByTimeAsync(DEFAULT_POLL_MS - 1);
        expect(fetchInterrupted).toHaveBeenCalledTimes(atMount);
        await vi.advanceTimersByTimeAsync(1);
        expect(fetchInterrupted).toHaveBeenCalledTimes(atMount + 1);
    });

    it('calls onretry once when the answer turns false, and stops polling', async () => {
        useFakeTimers();
        const answers = [true, false];
        const {fetchInterrupted, onretry} = mountPolling(() => Promise.resolve(answers.shift() ?? false));
        const atMount = fetchInterrupted.mock.calls.length;
        // A mount-time call (if any) consumes the first answer; advance until `false` has been answered.
        await vi.advanceTimersByTimeAsync(POLL_MS * (2 - atMount));
        expect(answers, 'Barrier: false has been answered').toEqual([]);

        expect(onretry, 'the administrator recovered: the app starts again').toHaveBeenCalledTimes(1);
        const afterFalse = fetchInterrupted.mock.calls.length;
        await vi.advanceTimersByTimeAsync(POLL_MS * 5);
        expect(fetchInterrupted, 'no polling after false').toHaveBeenCalledTimes(afterFalse);
        expect(onretry, 'onretry once, not once per interval').toHaveBeenCalledTimes(1);
    });

    it('keeps polling, without reloading, when the answer is undefined', async () => {
        useFakeTimers();
        const {fetchInterrupted, onretry} = mountPolling(() => Promise.resolve(undefined));
        const atMount = fetchInterrupted.mock.calls.length;

        await vi.advanceTimersByTimeAsync(POLL_MS * 3);

        expect(fetchInterrupted).toHaveBeenCalledTimes(atMount + 3);
        expect(onretry).not.toHaveBeenCalled();
    });

    it('ignores a failed fetch and keeps polling until the answer turns false', async () => {
        useFakeTimers();
        // A failure the page lets escape is an unhandled rejection: Node reports it once the microtasks have drained,
        // so the case listens for it and yields one macrotask (`setImmediate`, not faked, no clock) before reading.
        const unhandled: unknown[] = [];
        const onUnhandled = (reason: unknown) => unhandled.push(reason);
        process.on('unhandledRejection', onUnhandled);
        onTestFinished(() => {
            process.off('unhandledRejection', onUnhandled);
        });
        let call = 0;
        const {fetchInterrupted, onretry} = mountPolling(() => {
            call += 1;
            // Every call before the third fails; the third answers false.
            return call < 3 ? Promise.reject(new Error('network down')) : Promise.resolve(false);
        });

        await vi.advanceTimersByTimeAsync(POLL_MS * 3);
        await new Promise<void>((resolve) => setImmediate(resolve));

        expect(fetchInterrupted.mock.calls.length, 'Barrier: the third call happened').toBeGreaterThanOrEqual(3);
        expect(unhandled, 'a failed fetch is swallowed, never an unhandled rejection').toEqual([]);
        expect(onretry, 'the failures were swallowed, and the false after them still reloads').toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('instance-restore-interrupted'), 'a failure never tears the page down').toBeInTheDocument();
    });

    it('stops polling when unmounted', async () => {
        useFakeTimers();
        const {fetchInterrupted, onretry, view} = mountPolling(() => Promise.resolve(true));
        const atMount = fetchInterrupted.mock.calls.length;
        await vi.advanceTimersByTimeAsync(POLL_MS);
        expect(fetchInterrupted, 'Barrier: the page polls while mounted').toHaveBeenCalledTimes(atMount + 1);

        view.unmount();
        await vi.advanceTimersByTimeAsync(POLL_MS * 5);

        expect(fetchInterrupted, 'no call after unmount').toHaveBeenCalledTimes(atMount + 1);
        expect(onretry).not.toHaveBeenCalled();
    });

    it('reads restore_interrupted from GET /system/instance through the generated client by default: false ends the wait', async () => {
        useFakeTimers();
        mocks.getInstanceConfig.mockResolvedValue({profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}, mode: 'normal', restore_interrupted: false});
        const onretry = vi.fn().mockName('onretry');
        render(InstanceRestoreInterruptedPage, {props: {onretry, pollMs: POLL_MS}});
        flushSync();

        await vi.advanceTimersByTimeAsync(POLL_MS);
        await tick();

        expect(mocks.getInstanceConfig, 'GET /system/instance').toHaveBeenCalled();
        expect(onretry, 'its restore_interrupted: false ends the wait').toHaveBeenCalledTimes(1);
    });

    it('by default keeps waiting while GET /system/instance still answers restore_interrupted: true', async () => {
        useFakeTimers();
        mocks.getInstanceConfig.mockResolvedValue({profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}, mode: 'normal', restore_interrupted: true});
        const onretry = vi.fn().mockName('onretry');
        render(InstanceRestoreInterruptedPage, {props: {onretry, pollMs: POLL_MS}});
        flushSync();
        const atMount = mocks.getInstanceConfig.mock.calls.length;

        await vi.advanceTimersByTimeAsync(POLL_MS * 2);
        await tick();

        expect(mocks.getInstanceConfig, 'Barrier: GET /system/instance was asked at each interval').toHaveBeenCalledTimes(atMount + 2);
        expect(onretry, 'still interrupted: no reload').not.toHaveBeenCalled();
    });
});

describe('InstanceRestoreInterruptedPage — H5-3, the reason', () => {
    it.each(SOURCE_LANGUAGES)('has a string for each of the three owner keys in the instance source of %s', (lang) => {
        expect(
            Object.values(OWNER_KEYS).filter((key) => sourceGaps(key).includes(lang)),
            `owner keys missing in the ${lang} source`,
        ).toEqual([]);
    });

    it('has a string for each of the three owner keys in all four generated catalogues', () => {
        expect(catalogueGaps(Object.values(OWNER_KEYS))).toEqual({});
    });

    it.each(SOURCE_LANGUAGES)('FB-27: has a string for the support-missing key in the instance source of %s', (lang) => {
        expect(sourceGaps(SUPPORT_MISSING_KEY), `${SUPPORT_MISSING_KEY} missing in the ${lang} source`).not.toContain(lang);
    });

    describe.each([
        ['no reason', undefined],
        ['reason null', null],
        ["reason 'restore_state'", 'restore_state'],
    ] as const)('%s: today’s page', (_label, reason) => {
        const extra = (): Record<string, unknown> => (reason === undefined ? {} : {reason});

        it('reads the restore-state title, message and admin hint, never the owner’s', () => {
            mountPolling(neverAnswers, POLL_MS, extra());
            const root = screen.getByTestId('instance-restore-interrupted');

            expect(text(within(root).getByRole('heading', {level: 1}))).toBe(marked(NEW_KEYS.title));
            expect(text(within(root).getByTestId('instance-restore-interrupted-message'))).toBe(marked(NEW_KEYS.message));
            expect(text(within(root).getByTestId('instance-restore-interrupted-admin'))).toBe(marked(NEW_KEYS.adminHint));
            expect(root.textContent ?? '', 'no owner key on screen').not.toMatch(/ownerTitle|ownerMessage|ownerAdminHint/);
        });

        it('selfHosted false: has no docs link', () => {
            mountPolling(neverAnswers, POLL_MS, {...extra(), supportUrl: 'mailto:help@example.org', selfHosted: false});
            const root = screen.getByTestId('instance-restore-interrupted');
            // Presence barrier: the page painted its support link, so the absence below is not "nothing rendered yet".
            expect(within(root).getByTestId('instance-restore-interrupted-support')).toBeVisible();

            expect(within(root).queryByTestId('instance-restore-interrupted-docs')).toBeNull();
        });
    });

    describe("reason 'owner_assignment'", () => {
        const OWNER = {reason: 'owner_assignment'};

        it('reads the owner title (the h1), message and admin hint from the catalogue, in the same testids', () => {
            mountPolling(neverAnswers, POLL_MS, OWNER);
            const root = screen.getByTestId('instance-restore-interrupted');

            expect(text(within(root).getByRole('heading', {level: 1}))).toBe(marked(OWNER_KEYS.title));
            expect(text(within(root).getByTestId('instance-restore-interrupted-message'))).toBe(marked(OWNER_KEYS.message));
            expect(text(within(root).getByTestId('instance-restore-interrupted-admin'))).toBe(marked(OWNER_KEYS.adminHint));
        });

        it('shows none of the restore-state keys', () => {
            mountPolling(neverAnswers, POLL_MS, OWNER);
            const root = screen.getByTestId('instance-restore-interrupted');
            // Presence barrier: the owner page painted, so the absence below is not "nothing rendered yet".
            expect(text(within(root).getByRole('heading', {level: 1}))).toBe(marked(OWNER_KEYS.title));

            const shown = text(root);
            expect(shown, 'not the restore-state title').not.toContain(marked(NEW_KEYS.title));
            expect(shown, 'not the restore-state message').not.toContain(marked(NEW_KEYS.message));
            expect(shown, 'not the restore-state admin hint').not.toContain(marked(NEW_KEYS.adminHint));
        });

        it('announces the owner title and message as an alert, as today', () => {
            mountPolling(neverAnswers, POLL_MS, OWNER);
            const alert = within(screen.getByTestId('instance-restore-interrupted')).getByRole('alert');

            expect(within(alert).getByRole('heading', {level: 1}), 'the h1 is inside the alert').toBeInTheDocument();
            expect(within(alert).getByTestId('instance-restore-interrupted-message'), 'the message is inside the alert').toBeInTheDocument();
        });

        it('keeps the reload note and the retry label of the page', () => {
            mountPolling(neverAnswers, POLL_MS, OWNER);
            const root = screen.getByTestId('instance-restore-interrupted');
            // Presence barrier: the owner page painted.
            expect(text(within(root).getByRole('heading', {level: 1}))).toBe(marked(OWNER_KEYS.title));

            expect(text(within(root).getByTestId('instance-restore-interrupted-auto'))).toBe(marked(NEW_KEYS.autoReload));
            expect(within(root).getByTestId('instance-restore-interrupted-retry')).toHaveAccessibleName(marked(RETRY_KEY));
        });

        it('selfHosted false: has no docs link, the owner section of the panel guide included', () => {
            mountPolling(neverAnswers, POLL_MS, {...OWNER, supportUrl: 'mailto:help@example.org'});
            const root = screen.getByTestId('instance-restore-interrupted');
            expect(text(within(root).getByRole('heading', {level: 1})), 'Barrier: the owner page painted').toBe(marked(OWNER_KEYS.title));

            expect(within(root).queryByTestId('instance-restore-interrupted-docs')).toBeNull();
            expect(
                [...document.body.querySelectorAll('a')].filter((link) => (link.getAttribute('href') ?? '').includes('/mkdocs/')),
                'no link to the documentation',
            ).toEqual([]);
        });

        it('has the same controls: retry the only button, no link at all and the missing note without a support address', async () => {
            await useInstanceSupportUrl(null);
            mountPolling(neverAnswers, POLL_MS, OWNER);
            const root = screen.getByTestId('instance-restore-interrupted');
            expect(text(within(root).getByRole('heading', {level: 1})), 'Barrier: the owner page painted').toBe(marked(OWNER_KEYS.title));
            const retry = within(root).getByTestId('instance-restore-interrupted-retry');

            expect(within(root).getAllByRole('button'), 'the retry is the only button').toEqual([retry]);
            expectSupportMissing(root);
            expect(document.body.querySelectorAll('form, input, select, textarea'), 'no form, no field').toHaveLength(0);
        });

        it('shows the support link, from the prop, with the same report, when the instance names one', () => {
            freezeDate();
            mountPolling(neverAnswers, POLL_MS, {...OWNER, supportUrl: 'mailto:help@example.org'});
            const root = screen.getByTestId('instance-restore-interrupted');
            expect(text(within(root).getByRole('heading', {level: 1})), 'Barrier: the owner page painted').toBe(marked(OWNER_KEYS.title));

            expectSupportLink(within(root).getByTestId('instance-restore-interrupted-support'), reportLink('mailto:help@example.org'));
        });

        it('calls onretry when retry is clicked', async () => {
            const {onretry} = mountPolling(neverAnswers, POLL_MS, OWNER);
            expect(text(within(screen.getByTestId('instance-restore-interrupted')).getByRole('heading', {level: 1})), 'Barrier: the owner page painted').toBe(marked(OWNER_KEYS.title));

            await fireEvent.click(screen.getByTestId('instance-restore-interrupted-retry'));

            expect(onretry).toHaveBeenCalledTimes(1);
        });

        it('polls as today: false ends the wait with onretry once, and stops polling', async () => {
            useFakeTimers();
            const answers = [true, false];
            const {fetchInterrupted, onretry} = mountPolling(() => Promise.resolve(answers.shift() ?? false), POLL_MS, OWNER);
            expect(text(within(screen.getByTestId('instance-restore-interrupted')).getByRole('heading', {level: 1})), 'Barrier: the owner page painted').toBe(marked(OWNER_KEYS.title));
            const atMount = fetchInterrupted.mock.calls.length;
            await vi.advanceTimersByTimeAsync(POLL_MS * (2 - atMount));
            expect(answers, 'Barrier: false has been answered').toEqual([]);

            expect(onretry, 'the administrator recovered: the app starts again').toHaveBeenCalledTimes(1);
            const afterFalse = fetchInterrupted.mock.calls.length;
            await vi.advanceTimersByTimeAsync(POLL_MS * 5);
            expect(fetchInterrupted, 'no polling after false').toHaveBeenCalledTimes(afterFalse);
            expect(onretry, 'onretry once, not once per interval').toHaveBeenCalledTimes(1);
        });

        it('keeps polling while the instance still answers true', async () => {
            useFakeTimers();
            const {fetchInterrupted, onretry} = mountPolling(() => Promise.resolve(true), POLL_MS, OWNER);
            expect(text(within(screen.getByTestId('instance-restore-interrupted')).getByRole('heading', {level: 1})), 'Barrier: the owner page painted').toBe(marked(OWNER_KEYS.title));
            const atMount = fetchInterrupted.mock.calls.length;

            await vi.advanceTimersByTimeAsync(POLL_MS * 3);

            expect(fetchInterrupted).toHaveBeenCalledTimes(atMount + 3);
            expect(onretry).not.toHaveBeenCalled();
        });
    });
});

describe('InstanceRestoreInterruptedPage — selfHosted: the help of an administrator who has the server', () => {
    const SUPPORT = 'mailto:help@example.org';
    const REASONS = [
        ['no reason', undefined, RESTORE_STATE_DOCS_PATH],
        ['reason null', null, RESTORE_STATE_DOCS_PATH],
        ["reason 'restore_state'", 'restore_state', RESTORE_STATE_DOCS_PATH],
    ] as const;

    const reasonProps = (reason: string | null | undefined): Record<string, unknown> => (reason === undefined ? {} : {reason});

    describe.each(REASONS)('%s', (_label, reason, path) => {
        it('shows the docs link, named by its key, to the guide section in English', () => {
            mountPolling(neverAnswers, POLL_MS, {...reasonProps(reason), selfHosted: true, supportUrl: SUPPORT});
            const root = screen.getByTestId('instance-restore-interrupted');

            const link = within(root).getByTestId('instance-restore-interrupted-docs');
            expectDocsLink(link, docsUrl('en', path));
            expect(link).toHaveAccessibleName(marked(DOCS_KEY));
            expect(docsUrl('en', path), 'the expected English href, spelled out').toBe(`/mkdocs/${path}`);
        });

        it.each(DOCS_LANGUAGES)('the docs link follows the current language: %s', async (language) => {
            currentLanguage.set(language);
            await waitLocale(language);
            try {
                mountPolling(neverAnswers, POLL_MS, {...reasonProps(reason), selfHosted: true, supportUrl: SUPPORT});
                const link = within(screen.getByTestId('instance-restore-interrupted')).getByTestId('instance-restore-interrupted-docs');

                expectDocsLink(link, docsUrl(language, path));
            } finally {
                cleanup();
                currentLanguage.set('en');
                await waitLocale('en');
            }
        });

        it('keeps the support link with the report next to the docs link, and the retry as the only button', () => {
            freezeDate();
            mountPolling(neverAnswers, POLL_MS, {...reasonProps(reason), selfHosted: true, supportUrl: SUPPORT});
            const root = screen.getByTestId('instance-restore-interrupted');
            const docs = within(root).getByTestId('instance-restore-interrupted-docs');
            const support = within(root).getByTestId('instance-restore-interrupted-support');

            expectSupportLink(support, reportLink(SUPPORT));
            expect([...document.body.querySelectorAll('a')], 'the docs link and the support link are the only links').toEqual([docs, support]);
            expect(within(root).getAllByRole('button'), 'the retry is the only button').toEqual([within(root).getByTestId('instance-restore-interrupted-retry')]);
            expect(within(root).queryByTestId('instance-restore-interrupted-support-missing'), 'no missing note').toBeNull();
        });

        it.each([
            ['null', null],
            ['empty', ''],
            ['a javascript: URL', 'javascript:alert(1)'],
        ])('has no support link and NO missing line without a usable address (%s): the administrator is the host', (_what, value) => {
            expect(supportChannel(value, {githubFallback: false}), 'premise: the app finds no usable address').toBeNull();
            mountPolling(neverAnswers, POLL_MS, {...reasonProps(reason), selfHosted: true, supportUrl: value});
            const root = screen.getByTestId('instance-restore-interrupted');
            // Presence barrier: the docs link painted, so the absences below are not "nothing rendered yet".
            expect(within(root).getByTestId('instance-restore-interrupted-docs')).toBeVisible();

            expect(within(root).queryByTestId('instance-restore-interrupted-support-missing'), 'no «contact whoever provides the service» line').toBeNull();
            expect(within(root).queryByTestId('instance-restore-interrupted-support'), 'no support link').toBeNull();
            expect(document.body.innerHTML, 'no GitHub fallback').not.toContain('github.com');
        });
    });

    it("reason 'owner_assignment' has no «Guide» button, even for the administrator who has the server; the support link stays", () => {
        mountPolling(neverAnswers, POLL_MS, {reason: 'owner_assignment', selfHosted: true, supportUrl: SUPPORT});
        const root = screen.getByTestId('instance-restore-interrupted');

        expect(within(root).getByTestId('instance-restore-interrupted-support'), 'Barrier: the support link painted').toBeVisible();
        expectNoDocs(root, 'owner_assignment, self-hosted');
    });

    it('the managed page of the same reasons has no docs link: control that selfHosted is what shows it', () => {
        for (const [, reason] of REASONS) {
            mountPolling(neverAnswers, POLL_MS, {...reasonProps(reason), selfHosted: false, supportUrl: SUPPORT});
            expectNoDocs(screen.getByTestId('instance-restore-interrupted'), `reason ${String(reason)}`);
            cleanup();
        }
    });

    describe('the default of the prop: selfHostedConfirmed(), from the instance store', () => {
        /** The real store, answered with `profile`; the page is mounted WITHOUT the prop. */
        async function mountWithStoreProfile(profile: 'selfhosted' | 'managed', extra: Record<string, unknown> = {}) {
            await instanceConfig.load({force: true, fetchConfig: async () => ({...DEFAULT_INSTANCE_CONFIG, profile, support_url: null})});
            expect(instanceConfig.config.profile, 'precondition: the store holds the profile').toBe(profile);
            render(InstanceRestoreInterruptedPage, {props: {fetchInterrupted: neverAnswers, onretry: vi.fn(), ...extra}});
            flushSync();
            return screen.getByTestId('instance-restore-interrupted');
        }

        it('shows the docs link when the server answered selfhosted', async () => {
            const root = await mountWithStoreProfile('selfhosted');

            expectDocsLink(within(root).getByTestId('instance-restore-interrupted-docs'), docsUrl('en', RESTORE_STATE_DOCS_PATH));
            expect(within(root).queryByTestId('instance-restore-interrupted-support-missing'), 'the administrator is the host: no missing line').toBeNull();
        });

        it('shows no docs link when the server answered selfhosted and the reason is owner_assignment: that case has no guide', async () => {
            const root = await mountWithStoreProfile('selfhosted', {reason: 'owner_assignment'});

            expectNoDocs(root, 'owner_assignment');
        });

        it('shows no docs link, and the missing line without an address, when the server answered managed', async () => {
            const root = await mountWithStoreProfile('managed');

            expectNoDocs(root, 'managed');
            expectSupportMissing(root);
        });

        it('an explicit selfHosted: false wins over a self-hosted store', async () => {
            const root = await mountWithStoreProfile('selfhosted', {selfHosted: false});

            expectNoDocs(root, 'prop false');
        });

        it('an explicit selfHosted: true wins over a managed store', async () => {
            const root = await mountWithStoreProfile('managed', {selfHosted: true});

            expectDocsLink(within(root).getByTestId('instance-restore-interrupted-docs'), docsUrl('en', RESTORE_STATE_DOCS_PATH));
        });
    });
});
