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
 *     (`instance.restoreInterrupted.adminHint`), the docs link `instance-restore-interrupted-docs` named
 *     `instance.restoreInterrupted.docs`, the note `instance-restore-interrupted-auto`
 *     (`instance.restoreInterrupted.autoReload`) and the button `instance-restore-interrupted-retry` named
 *     `instance.awaitingRestore.retry` (the key of the awaiting page, reused);
 *   - the docs link is an anchor to the admin CLI page's anchor `#backup-pending-unreadable`, built by the app's docs-URL
 *     rule — the one of `DocsLink` and of `connectionSecurityDocsUrl` (`$lib/utils/security/connectionSecurity`):
 *     `/mkdocs/` + the language prefix (none in English, `<lang>/` otherwise, from `currentLanguage`) + the path
 *     `admin/cli_tools/#backup-pending-unreadable` — opened in a new tab (`target="_blank"`,
 *     `rel="noopener noreferrer"`);
 *   - nothing else to act on: the retry is the only button, no form, no field, no logout; the docs link is the only
 *     link, and, when the instance has a usable support address, the support link (D7) is the other one;
 *   - the five new keys have a string in all four shipped catalogues (`$lib/i18n/{en,it,fr,es}.json`);
 *   - D7, the support link: when the instance has a support address — the prop `supportUrl`, by default
 *     `instanceConfig.config.support_url` (`GET /system/instance`) — the page shows the anchor
 *     `instance-restore-interrupted-support` named `instance.restoreInterrupted.support` (a sixth key, all four
 *     catalogues). The address is read through the app's `supportChannel(value, {githubFallback: false})`
 *     (`$lib/components/assets/assetSearchReport`): a mailto gives `href="mailto:<address>"`, a page its normalized
 *     `url`, opened in a new tab (`target="_blank"`, `rel="noopener noreferrer"`). Without a usable address (null,
 *     empty, `javascript:…`, a mailto with two addresses) there is no support link at all, and no GitHub fallback;
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
import {CONNECTION_SECURITY_DOCS_PATH, connectionSecurityDocsUrl} from '$lib/utils/security/connectionSecurity';
import {supportChannel} from '$lib/components/assets/assetSearchReport';
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

/** The five keys of this page. */
const NEW_KEYS = {
    title: 'instance.restoreInterrupted.title',
    message: 'instance.restoreInterrupted.message',
    adminHint: 'instance.restoreInterrupted.adminHint',
    docs: 'instance.restoreInterrupted.docs',
    autoReload: 'instance.restoreInterrupted.autoReload',
} as const;
/** The retry label: the awaiting page's key, reused. */
const RETRY_KEY = 'instance.awaitingRestore.retry';
/** D7: the label of the support link, a sixth key of this page. */
const SUPPORT_KEY = 'instance.restoreInterrupted.support';

/** A usable address the store holds in the support cases: a link to it means the page ignored its prop. */
const STORE_SUPPORT_URL = 'mailto:store-support@example.org';

/** The default interval of the contract: 30 s. */
const DEFAULT_POLL_MS = 30_000;
/** A short interval for the injected cases: the arithmetic stays readable. */
const POLL_MS = 1_000;

/** The admin guide's section on an unreadable restore state: a path below `/mkdocs/`, no language, no leading `/`. */
const DOCS_PATH = 'admin/cli_tools/#backup-pending-unreadable';
const DOCS_ANCHOR = '#backup-pending-unreadable';

/**
 * The app's docs-URL rule (`DocsLink`'s `getDocsUrl`, `connectionSecurityDocsUrl`): `/mkdocs/`, the language prefix,
 * the path. Each case checks first that it is the rule of the exported helper, so a change of the app's rule shows here.
 */
const docsUrl = (lang: string, path: string): string => `/mkdocs/${lang && lang !== 'en' ? `${lang}/` : ''}${path}`;

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
    for (const key of [...Object.values(NEW_KEYS), RETRY_KEY, SUPPORT_KEY]) messages[key] = marked(key);
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

/** Mount with an injected `fetchInterrupted` and `onretry`, and return them; `extra` adds props (the support address). */
function mountPolling(fetchInterrupted: () => Promise<boolean | undefined>, pollMs = POLL_MS, extra: Record<string, unknown> = {}) {
    const spy = vi.fn(fetchInterrupted).mockName('fetchInterrupted');
    const onretry = vi.fn().mockName('onretry');
    const view = render(InstanceRestoreInterruptedPage, {props: {fetchInterrupted: spy, onretry, pollMs, ...extra}});
    flushSync();
    expect(screen.getByTestId('instance-restore-interrupted'), 'Barrier: the page is mounted').toBeInTheDocument();
    return {fetchInterrupted: spy, onretry, view};
}

/** The docs link of the page: an anchor to `href`, in a new tab, without a window.opener nor a referrer. */
function expectDocsLink(link: HTMLElement, href: string): void {
    expect(link.tagName, 'the docs link is an anchor').toBe('A');
    expect(link.getAttribute('href'), 'the admin guide, at the unreadable-state section').toBe(href);
    expect(link.getAttribute('href') ?? '', 'the anchor of the section').toMatch(/#backup-pending-unreadable$/);
    expect(link, 'in a new tab').toHaveAttribute('target', '_blank');
    const rel = (link.getAttribute('rel') ?? '').split(/\s+/);
    expect(rel, 'without a window.opener').toContain('noopener');
    expect(rel, 'without a referrer').toContain('noreferrer');
}

/** The real store, loaded with an injected answer: `support_url` is the instance's support address. */
async function useInstanceSupportUrl(supportUrl: string | null): Promise<void> {
    await instanceConfig.load({force: true, fetchConfig: async () => ({...DEFAULT_INSTANCE_CONFIG, support_url: supportUrl})});
    expect(instanceConfig.config.support_url, 'precondition: the store holds the support address').toBe(supportUrl);
}

/** The support link of the page: an anchor named by its key, to `href`. */
function expectSupportLink(link: HTMLElement, href: string): void {
    expect(link.tagName, 'the support link is an anchor').toBe('A');
    expect(link).toHaveAccessibleName(marked(SUPPORT_KEY));
    expect(link.getAttribute('href'), 'where the instance says support is').toBe(href);
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
    it('has a string for each of its five keys in all four shipped catalogues', () => {
        expect(catalogueGaps(Object.values(NEW_KEYS))).toEqual({});
    });

    it('D7: has a string for the support link key in all four shipped catalogues', () => {
        expect(catalogueGaps([SUPPORT_KEY])).toEqual({});
    });

    it('reuses the retry key of the awaiting page, present in all four catalogues', () => {
        expect(catalogueGaps([RETRY_KEY])).toEqual({});
    });

    it('control: the marker locale is live', () => {
        expect(get(translate)(NEW_KEYS.title)).toBe(marked(NEW_KEYS.title));
    });
});

describe('InstanceRestoreInterruptedPage — what it shows', () => {
    it('reads its title, message, admin hint, docs label, note and retry label from the catalogue', () => {
        mountPolling(neverAnswers);
        expect(get(translate)(NEW_KEYS.title), 'control: the marker locale is live').toBe(marked(NEW_KEYS.title));
        const root = screen.getByTestId('instance-restore-interrupted');

        expect(text(within(root).getByRole('heading', {level: 1}))).toBe(marked(NEW_KEYS.title));
        expect(text(within(root).getByTestId('instance-restore-interrupted-message'))).toBe(marked(NEW_KEYS.message));
        expect(text(within(root).getByTestId('instance-restore-interrupted-admin'))).toBe(marked(NEW_KEYS.adminHint));
        expect(within(root).getByTestId('instance-restore-interrupted-docs')).toHaveAccessibleName(marked(NEW_KEYS.docs));
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

    it('links the admin guide at #backup-pending-unreadable, in English, by the app’s docs-URL rule', () => {
        expect(docsUrl('en', CONNECTION_SECURITY_DOCS_PATH), 'premise: the rule is the exported helper’s').toBe(connectionSecurityDocsUrl('en'));
        expect(get(currentLanguage), 'premise: the documentation language is English').toBe('en');
        mountPolling(neverAnswers);

        const link = within(screen.getByTestId('instance-restore-interrupted')).getByTestId('instance-restore-interrupted-docs');

        expectDocsLink(link, docsUrl('en', DOCS_PATH));
        expect(docsUrl('en', DOCS_PATH), 'the expected English href, spelled out').toBe(`/mkdocs/admin/cli_tools/${DOCS_ANCHOR}`);
    });

    it('the docs link follows the current language', async () => {
        expect(docsUrl('it', CONNECTION_SECURITY_DOCS_PATH), 'premise: the rule is the exported helper’s').toBe(connectionSecurityDocsUrl('it'));
        currentLanguage.set('it');
        await waitLocale('it');
        try {
            mountPolling(neverAnswers);

            const link = within(screen.getByTestId('instance-restore-interrupted')).getByTestId('instance-restore-interrupted-docs');

            expectDocsLink(link, docsUrl('it', DOCS_PATH));
            expect(docsUrl('it', DOCS_PATH), 'the expected Italian href, spelled out').toBe(`/mkdocs/it/admin/cli_tools/${DOCS_ANCHOR}`);
        } finally {
            currentLanguage.set('en');
            await waitLocale('en');
        }
    });

    it('offers nothing to act on but the retry and the docs link when there is no support address: no logout, no form, no field', async () => {
        await useInstanceSupportUrl(null);
        mountPolling(neverAnswers);
        const root = screen.getByTestId('instance-restore-interrupted');
        // Presence barrier: the page painted its two controls, so the absences below are not "nothing rendered yet".
        const retry = within(root).getByTestId('instance-restore-interrupted-retry');
        const docs = within(root).getByTestId('instance-restore-interrupted-docs');
        expect(retry).toBeVisible();
        expect(docs).toBeVisible();

        expect(within(root).getAllByRole('button'), 'the retry is the only button').toEqual([retry]);
        expect([...document.body.querySelectorAll('a')], 'no support address: the docs link is the only link').toEqual([docs]);
        expect(document.body.querySelectorAll('form, input, select, textarea'), 'no form, no field').toHaveLength(0);
        expect(screen.queryByTestId('instance-blocked-logout'), 'no logout button').toBeNull();
    });

    it('D7: with a support address, the docs link and the support link are the only links, the retry still the only button', () => {
        mountPolling(neverAnswers, POLL_MS, {supportUrl: 'mailto:help@example.org'});
        const root = screen.getByTestId('instance-restore-interrupted');
        const retry = within(root).getByTestId('instance-restore-interrupted-retry');
        const docs = within(root).getByTestId('instance-restore-interrupted-docs');
        const support = within(root).getByTestId('instance-restore-interrupted-support');
        expect(retry).toBeVisible();
        expect(docs).toBeVisible();
        expect(support).toBeVisible();

        expect(within(root).getAllByRole('button'), 'the retry is the only button').toEqual([retry]);
        const links = [...document.body.querySelectorAll('a')];
        expect(links, 'two links').toHaveLength(2);
        expect(new Set(links), 'the docs link and the support link').toEqual(new Set([docs, support]));
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
});

describe('InstanceRestoreInterruptedPage — D7, the support link', () => {
    beforeEach(async () => {
        // The store holds a different, usable address: a link to it means the page did not read its prop.
        await useInstanceSupportUrl(STORE_SUPPORT_URL);
    });

    it('links a mailto support address as mailto:<address>', () => {
        const value = 'mailto:help@example.org';
        expect(supportChannel(value, {githubFallback: false}), 'premise: the app reads it as one mail address').toEqual({kind: 'mailto', address: 'help@example.org'});
        mountPolling(neverAnswers, POLL_MS, {supportUrl: value});

        const link = within(screen.getByTestId('instance-restore-interrupted')).getByTestId('instance-restore-interrupted-support');

        expectSupportLink(link, 'mailto:help@example.org');
    });

    it('links a support page at its normalized address, in a new tab, without a window.opener nor a referrer', () => {
        const value = '  https://Support.Example.org  ';
        const channel = supportChannel(value, {githubFallback: false});
        expect(channel, 'premise: the app reads it as a page, normalized').toEqual({kind: 'page', url: 'https://support.example.org/'});
        mountPolling(neverAnswers, POLL_MS, {supportUrl: value});

        const link = within(screen.getByTestId('instance-restore-interrupted')).getByTestId('instance-restore-interrupted-support');

        expectSupportLink(link, 'https://support.example.org/');
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

        expectSupportLink(link, 'https://help.example.org/librefolio');
        expect(link, 'a page: in a new tab').toHaveAttribute('target', '_blank');
    });

    it('by default shows no support link when the instance names no support address', async () => {
        await useInstanceSupportUrl(null);
        render(InstanceRestoreInterruptedPage, {props: {fetchInterrupted: neverAnswers, onretry: vi.fn()}});
        flushSync();
        const root = screen.getByTestId('instance-restore-interrupted');
        // Presence barrier: the page painted its docs link, so the absence below is not "nothing rendered yet".
        const docs = within(root).getByTestId('instance-restore-interrupted-docs');
        expect(docs).toBeVisible();

        expect(within(root).queryByTestId('instance-restore-interrupted-support'), 'no support link').toBeNull();
        expect([...document.body.querySelectorAll('a')], 'no GitHub fallback either: the docs link is the only link').toEqual([docs]);
    });

    const UNUSABLE: ReadonlyArray<readonly [string, string | null]> = [
        ['null', null],
        ['empty', ''],
        ['blank', '   '],
        ['a javascript: URL', 'javascript:alert(1)'],
        ['a mailto with two addresses', 'mailto:help@example.org,other@example.org'],
    ];

    it.each(UNUSABLE)('shows no support link at all for %s, and no GitHub fallback', (_label, value) => {
        expect(supportChannel(value, {githubFallback: false}), 'premise: the app finds no usable address').toBeNull();
        expect(supportChannel(value, {githubFallback: true})?.kind, 'premise: a GitHub fallback would exist, so its absence means something').toBe('github');
        mountPolling(neverAnswers, POLL_MS, {supportUrl: value});
        const root = screen.getByTestId('instance-restore-interrupted');
        // Presence barrier: the page painted its docs link, so the absence below is not "nothing rendered yet".
        const docs = within(root).getByTestId('instance-restore-interrupted-docs');
        expect(docs).toBeVisible();

        expect(within(root).queryByTestId('instance-restore-interrupted-support'), 'no support link').toBeNull();
        expect([...document.body.querySelectorAll('a')], 'no fallback link: the docs link is the only link').toEqual([docs]);
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
