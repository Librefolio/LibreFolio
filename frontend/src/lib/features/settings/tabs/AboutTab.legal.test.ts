// @vitest-environment jsdom
/**
 * AboutTab — the instance's legal notice (workstream A, lot A9, F09; decision D-A11: the About tab is one of its
 * places, in a card of its own, «Note legali»).
 *
 * The contract under test (approved by the coordinator; the disclaimer wording is pending the developer):
 *   - `about-tab` holds one card `about-legal-card`, and the card holds one `legal-notice`: the full notice, whose
 *     disclaimer is `legal.disclaimer`;
 *   - the links are the notice's: none without a `legal` block; with both URLs set, `legal-terms-link` and
 *     `legal-privacy-link` inside the card, to those URLs, in a new tab, without opener or referrer;
 *   - the card follows the instance configuration: an answer landing after the tab is drawn brings its links;
 *   - the card does not depend on the diagnostics: it is there when `GET /system/info` fails;
 *   - colour roles only in the new card: no palette class and no `dark:` (the rest of the tab is not this lot's).
 *
 * Mocks follow `AboutTab.test.ts` — the generated client is a proxy of per-endpoint `vi.fn`s, the theme store, the
 * signal registry and its mapper, and the changelog feature (its `?raw` import is denied in tests) are stubs, and
 * `localStorage` is a stand-in — with one difference: `$lib/i18n` answers `⟦<key>⟧`, so a text is read as the key the
 * component asked for, never as a sentence. `LegalNotice` is the real one, reached through the tab. The instance
 * configuration is the real store, its answer set per test by a forced `load` whose `fetchConfig` the test owns; the
 * proxy's `GET /system/instance` refuses, so a `load()` of the component's own would reach no network either.
 *
 * Written red-first, before the card exists. The tab is imported once, in a `beforeAll` with a long budget: its first
 * `lucide-svelte` import may take ~27 s under load.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {cleanup, render, screen, waitFor, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const i18n = vi.hoisted(() => ({mark: (key: string): string => `⟦${key}⟧`}));

vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable, writable} = await import('svelte/store');
    const translator = readable(i18n.mark);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator, locale: writable('en')};
});

vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

vi.mock('$lib/stores/app/themeStore', () => ({
    getStoredThemePreference: () => 'light',
    getCurrentResolvedTheme: () => 'light',
    applyTheme: vi.fn(),
}));
vi.mock('$lib/charts/signals/registry', () => ({getRegisteredSignalTypes: () => []}));
vi.mock('$lib/charts/signals/catalogMapper', () => ({mapBackendSignalDefinition: (raw: unknown) => raw}));
vi.mock('$lib/features/changelog/changelog', () => ({
    changelogChapters: [],
    baseLanguage: () => 'en',
    localizedChangelog: {peek: () => [], load: () => Promise.resolve([])},
    CHANGELOG_REMOTE_URL: 'https://example.invalid/CHANGELOG.md',
}));

import {zodiosApi} from '$lib/api';
import {instanceConfig, type InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

let AboutTab: typeof import('./AboutTab.svelte').default;

// --- Fixtures -------------------------------------------------------------

const TERMS = 'https://legal.example.org/terms?edition=2026';
const PRIVACY = 'https://legal.example.org/privacy#data';

const SYSTEM_INFO = {
    app_version: '2.4.1',
    python_version: '3.12.2',
    os_name: 'Linux',
    os_version: '6.8.0',
    platform: 'Linux-6.8.0-x86_64',
    deployment_mode: 'local',
    backend_dependencies: [{name: 'fastapi', version: '0.115.0'}],
    frontend_dependencies: [{name: 'svelte', version: '5.0.0'}],
};

/** The proxy's `vi.fn` for one generated alias. */
function endpoint(alias: string): ReturnType<typeof vi.fn> {
    return (zodiosApi as unknown as Record<string, ReturnType<typeof vi.fn>>)[alias];
}

/** The legal block as the A9 backend serves it. */
interface LegalBlock {
    terms_url?: string | null;
    privacy_url?: string | null;
}

/** An answer of `GET /system/instance`; without `legal`, a server that predates the block. Cast: the generated type gains `legal` with the regenerated client. */
function answerWith(legal?: LegalBlock): InstanceConfig {
    const base = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
    return (legal === undefined ? base : {...base, legal}) as unknown as InstanceConfig;
}

/** The configuration in force, as if the (app) layout's request had answered `config`. */
async function answered(config: InstanceConfig): Promise<void> {
    await instanceConfig.load({force: true, fetchConfig: () => Promise.resolve(config)});
}

function text(element: Element): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

function exactlyOne(root: ParentNode, testId: string, where: string): HTMLElement {
    const found = root.querySelectorAll<HTMLElement>(`[data-testid="${testId}"]`);
    if (found.length !== 1) throw new Error(`expected exactly one [data-testid="${testId}"] in ${where}, found ${found.length}`);
    return found[0];
}

/** The link `testId` inside `root`: absent when `url` is null, otherwise an external link to `url`. */
function expectLink(root: HTMLElement, testId: string, url: string | null): void {
    const links = within(root).queryAllByTestId(testId);
    if (url === null) {
        expect(links, `no ${testId} while its URL is not set`).toHaveLength(0);
        return;
    }
    expect(links, `exactly one ${testId} while its URL is set`).toHaveLength(1);
    expect(links[0], `${testId} goes to the URL the instance sets`).toHaveAttribute('href', url);
    expect(links[0]).toHaveAttribute('target', '_blank');
    expect((links[0].getAttribute('rel') ?? '').split(/\s+/)).toEqual(expect.arrayContaining(['noopener', 'noreferrer']));
}

const PALETTE = /\b(bg|text|border)-(red|green|yellow|amber|orange|blue|gray|slate|zinc|neutral|stone|emerald|rose|sky)-\d/;

/** Every class token of `root` or of a descendant that is a palette colour or a `dark:` variant, with its element. */
function colourOffences(root: Element): string[] {
    return [root, ...Array.from(root.querySelectorAll('*'))].flatMap((element) => {
        const where = `${element.tagName.toLowerCase()}${element.getAttribute('data-testid') ? `[${element.getAttribute('data-testid')}]` : ''}`;
        return (element.getAttribute('class') ?? '')
            .split(/\s+/)
            .filter((token) => PALETTE.test(token) || token.includes('dark:'))
            .map((token) => `${where}: ${token}`);
    });
}

/**
 * A local-storage stand-in: jsdom under this Node build exposes no usable `localStorage`, and the tab reads the stored
 * locale from it on mount (as in `AboutTab.test.ts`).
 */
const stored = new Map<string, string>();
const localStorageStub = {
    getItem: (key: string) => stored.get(key) ?? null,
    setItem: (key: string, value: string) => void stored.set(key, String(value)),
    removeItem: (key: string) => void stored.delete(key),
    clear: () => stored.clear(),
    key: (index: number) => [...stored.keys()][index] ?? null,
    get length() {
        return stored.size;
    },
};

/** Draw the tab and wait for the state it publishes: every answer of its mount is in once `data-busy` is false. */
async function mountAboutTab(): Promise<HTMLElement> {
    render(AboutTab);
    const tab = screen.getByTestId('about-tab');
    await waitFor(() => expect(tab).toHaveAttribute('data-busy', 'false'));
    return tab;
}

// --- Lifecycle --------------------------------------------------------------

beforeAll(async () => {
    // The reactivity case and the absences below would pass vacuously where effects never run.
    assertEffectsRun();
    AboutTab = (await import('./AboutTab.svelte')).default;
}, 180_000);

beforeEach(() => {
    vi.clearAllMocks();
    stored.clear();
    Object.defineProperty(globalThis, 'localStorage', {value: localStorageStub, configurable: true, writable: true});
    Object.defineProperty(window, 'localStorage', {value: localStorageStub, configurable: true, writable: true});
    endpoint('get_system_info_api_v1_system_info_get').mockResolvedValue(SYSTEM_INFO);
    endpoint('list_providers_api_v1_assets_provider_get').mockResolvedValue([]);
    endpoint('list_providers_api_v1_fx_providers_get').mockResolvedValue([]);
    endpoint('list_plugins_api_v1_brokers_import_plugins_get').mockResolvedValue([]);
    endpoint('get_plugin_diagnostics_api_v1_system_plugin_diagnostics_get').mockResolvedValue([]);
    endpoint('list_asset_signal_catalog_api_v1_assets_prices_signals_get').mockResolvedValue({items: []});
    endpoint('list_fx_signal_catalog_api_v1_fx_currencies_signals_get').mockResolvedValue({items: []});
    endpoint('get_instance_config_api_v1_system_instance_get').mockRejectedValue(new Error('no network in this test'));
});

afterEach(() => {
    cleanup();
});

// =========================================================================
describe('AboutTab — the legal card', () => {
    // red until A9
    it('ALG-01: the tab holds one about-legal-card with one full legal-notice, and no link while the instance sets none', async () => {
        await answered(answerWith());

        const tab = await mountAboutTab();

        const card = exactlyOne(tab, 'about-legal-card', 'the About tab');
        const notice = exactlyOne(card, 'legal-notice', 'the legal card');
        expect(text(notice), 'the full notice: its disclaimer is legal.disclaimer').toContain(i18n.mark('legal.disclaimer'));
        expectLink(card, 'legal-terms-link', null);
        expectLink(card, 'legal-privacy-link', null);
    });

    // red until A9
    it('ALG-02: with both URLs set, the card links to the terms and to the privacy policy', async () => {
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));

        const tab = await mountAboutTab();

        const notice = exactlyOne(exactlyOne(tab, 'about-legal-card', 'the About tab'), 'legal-notice', 'the legal card');
        expectLink(notice, 'legal-terms-link', TERMS);
        expectLink(notice, 'legal-privacy-link', PRIVACY);
    });

    // red until A9
    it('ALG-03: the card follows the instance configuration — an answer landing after the tab is drawn brings the links', async () => {
        await answered(answerWith({terms_url: null, privacy_url: null}));
        const tab = await mountAboutTab();
        const card = exactlyOne(tab, 'about-legal-card', 'the About tab');
        expectLink(card, 'legal-terms-link', null);
        expectLink(card, 'legal-privacy-link', null);

        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        flushSync();

        const notice = exactlyOne(exactlyOne(tab, 'about-legal-card', 'the About tab'), 'legal-notice', 'the legal card');
        expectLink(notice, 'legal-terms-link', TERMS);
        expectLink(notice, 'legal-privacy-link', PRIVACY);
    });

    // red until A9
    it('ALG-04: the card does not depend on the diagnostics — it is there, links included, when GET /system/info fails', async () => {
        endpoint('get_system_info_api_v1_system_info_get').mockRejectedValue(new Error('boom'));
        await answered(answerWith({terms_url: TERMS, privacy_url: null}));

        const tab = await mountAboutTab();

        // Premise: the failure did happen — the copy button stays unusable without a report.
        expect(screen.getByTestId('about-copy-report')).toBeDisabled();
        const notice = exactlyOne(exactlyOne(tab, 'about-legal-card', 'the About tab'), 'legal-notice', 'the legal card');
        expect(text(notice)).toContain(i18n.mark('legal.disclaimer'));
        expectLink(notice, 'legal-terms-link', TERMS);
        expectLink(notice, 'legal-privacy-link', null);
    });

    // red until A9
    it('ALG-05: colour roles only — no palette class and no dark: variant in the card, links included', async () => {
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        const tab = await mountAboutTab();
        const card = exactlyOne(tab, 'about-legal-card', 'the About tab');
        // Presence barrier: the scan below covers the links, not a card drawn without them.
        expectLink(card, 'legal-terms-link', TERMS);
        expectLink(card, 'legal-privacy-link', PRIVACY);

        expect(colourOffences(card), 'palette classes or dark: variants rendered').toEqual([]);
    });
});
