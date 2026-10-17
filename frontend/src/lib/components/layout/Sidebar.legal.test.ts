// @vitest-environment jsdom
/**
 * Sidebar — the compact legal notice at the foot of the sidebar (workstream A, lot A9, F09; decision D-A11: «una riga
 * in fondo alla sidebar», mounted in H's file).
 *
 * The contract under test (approved by the coordinator; the disclaimer wording is pending the developer):
 *   - the expanded sidebar draws one `sidebar-legal-links` holding one `legal-links` (the compact notice: its disclaimer
 *     is `legal.disclaimerShort`), in its footer next to `sidebar-version`: a sibling of it, after the logout button;
 *   - the links are the compact notice's: none without a `legal` block; with both URLs set, `legal-terms-link` and
 *     `legal-privacy-link` inside `sidebar-legal-links`, to those URLs, in a new tab, without opener or referrer;
 *   - the line follows the instance configuration: the (app) layout's request answering after the sidebar is drawn
 *     brings the links;
 *   - colour roles only in the new line: no palette class and no `dark:`.
 * The collapsed sidebar (icons only, no `sidebar-version`) is left out: the contract does not say what it shows.
 *
 * No other test mounts the real Sidebar (the layout tests replace it). What is replaced here, as `AuthPageFrame.test.ts`
 * replaces the bar's controls: `ChangelogModal` (the bundled changelog's `?raw` import is denied in tests, and the
 * modal is closed anyway) and `ConnectionSecurityIndicator` (it reads the connection store and has its own test) are
 * no-op components. `$app/stores` and `$app/environment` are the aliases of `vitest.config.ts` (a fixed root page, not
 * a browser: the collapsed state is not read from storage). `$lib/i18n` answers `⟦<key>⟧`, so a text is read as the
 * key the component asked for. `LegalLinks` is the real one, reached through the sidebar. The instance configuration is
 * the real store, its answer set per test by a forced `load` whose `fetchConfig` the test owns; the generated alias of
 * `GET /system/instance` is spied and refuses, so no case reaches a network.
 *
 * Written red-first, before the line exists. The sidebar is imported once, in a `beforeAll` with a long budget: its
 * first `lucide-svelte` import may take ~27 s under load.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {cleanup, render, screen, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const i18n = vi.hoisted(() => ({mark: (key: string): string => `⟦${key}⟧`}));

vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const translator = readable(i18n.mark);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator};
});
vi.mock('$lib/components/layout/ChangelogModal.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/layout/ConnectionSecurityIndicator.svelte', () => ({default: () => {}}));

import {zodiosApi} from '$lib/api';
import {instanceConfig, type InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

let Sidebar: typeof import('./Sidebar.svelte').default;

// --- Fixtures -------------------------------------------------------------

const INSTANCE_ALIAS = 'get_instance_config_api_v1_system_instance_get';
/** The generated client seen through that one alias: spying through the full client type sends TS into an excessively deep instantiation. */
const instanceEndpoint = zodiosApi as unknown as Record<typeof INSTANCE_ALIAS, () => Promise<InstanceConfig>>;
const TERMS = 'https://legal.example.org/terms?edition=2026';
const PRIVACY = 'https://legal.example.org/privacy#data';

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

/** Draw the expanded sidebar; its output is what `container` holds. */
function mountSidebar(): HTMLElement {
    const {container} = render(Sidebar, {props: {collapsed: false, isOpen: false}});
    return container;
}

/** The footer line: one `sidebar-legal-links`, a sibling of `sidebar-version` after the logout button, holding one compact `legal-links`. */
function legalLine(sidebar: HTMLElement): {line: HTMLElement; links: HTMLElement} {
    // Presence barrier: the footer the line belongs to is drawn, version included (the sidebar is expanded).
    const version = exactlyOne(sidebar, 'sidebar-version', 'the sidebar');
    const logout = screen.getByTestId('logout-button');
    const line = exactlyOne(sidebar, 'sidebar-legal-links', 'the sidebar');
    expect(line.parentElement, 'the legal line sits next to sidebar-version, in the same footer block').toBe(version.parentElement);
    expect(Boolean(logout.compareDocumentPosition(line) & Node.DOCUMENT_POSITION_FOLLOWING), 'the legal line is in the footer, after the logout button').toBe(true);
    const links = exactlyOne(line, 'legal-links', 'sidebar-legal-links');
    expect(text(links), 'the compact notice: its disclaimer is legal.disclaimerShort').toContain(i18n.mark('legal.disclaimerShort'));
    return {line, links};
}

// --- Lifecycle --------------------------------------------------------------

beforeAll(async () => {
    // The reactivity case and the absences below would pass vacuously where effects never run.
    assertEffectsRun();
    Sidebar = (await import('./Sidebar.svelte')).default;
}, 180_000);

beforeEach(() => {
    vi.spyOn(instanceEndpoint, INSTANCE_ALIAS).mockRejectedValue(new Error('no network in this test'));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

// =========================================================================
describe('Sidebar — the compact legal notice in the footer', () => {
    // red until A9
    it('SLG-01: one sidebar-legal-links with the compact legal-links, next to sidebar-version, without links while the instance sets none', async () => {
        await answered(answerWith());

        const {line} = legalLine(mountSidebar());

        expectLink(line, 'legal-terms-link', null);
        expectLink(line, 'legal-privacy-link', null);
    });

    // red until A9
    it('SLG-02: with both URLs set, the line links to the terms and to the privacy policy', async () => {
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));

        const {links} = legalLine(mountSidebar());

        expectLink(links, 'legal-terms-link', TERMS);
        expectLink(links, 'legal-privacy-link', PRIVACY);
    });

    // red until A9
    it('SLG-03: the line follows the instance configuration — an answer landing after the sidebar is drawn brings the links', async () => {
        await answered(answerWith({terms_url: null, privacy_url: null}));
        const sidebar = mountSidebar();
        const {line} = legalLine(sidebar);
        expectLink(line, 'legal-terms-link', null);
        expectLink(line, 'legal-privacy-link', null);

        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        flushSync();

        const {links} = legalLine(sidebar);
        expectLink(links, 'legal-terms-link', TERMS);
        expectLink(links, 'legal-privacy-link', PRIVACY);
    });

    // red until A9
    it('SLG-04: colour roles only — no palette class and no dark: variant in sidebar-legal-links, links included', async () => {
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        const {line} = legalLine(mountSidebar());
        // Presence barrier: the scan below covers the links, not a line drawn without them.
        expectLink(line, 'legal-terms-link', TERMS);
        expectLink(line, 'legal-privacy-link', PRIVACY);

        expect(colourOffences(line), 'palette classes or dark: variants rendered').toEqual([]);
    });
});
