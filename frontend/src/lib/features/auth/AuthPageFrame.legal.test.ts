// @vitest-environment jsdom
/**
 * AuthPageFrame — the compact legal notice at the foot of the sign-in side (workstream A, lot A9, F09; decision D-A11:
 * «in fondo alle pagine di login, registrazione, setup, invito e reset»).
 *
 * The frame is shared by every page a visitor reaches signed out — `login-page` (the login, register and
 * forgot-password views of `/`), `invite-page`, `setup-page`, `reset-password-page`, `verify-email-page` — so the line
 * lives in the frame, once, and every page gets it.
 *
 * The contract under test (approved by the coordinator; the disclaimer wording is pending the developer):
 *   - the frame draws one `auth-legal-links` holding one `legal-links` (the compact notice: its disclaimer is
 *     `legal.disclaimerShort`), under the page content: after it in the document, outside the page's card; on every
 *     page it frames, and without a test id too;
 *   - the links are the compact notice's: none without a `legal` block; with both URLs set, `legal-terms-link` and
 *     `legal-privacy-link` inside `auth-legal-links`, to those URLs, in a new tab, without opener or referrer;
 *   - the line follows the instance configuration: the sign-in page's request answering after the frame is drawn
 *     brings the links;
 *   - colour roles only in the new line: no palette class and no `dark:`.
 *
 * Mocks follow `AuthPageFrame.test.ts`: the bar's controls (ThemeToggle, LanguageSelector, HelpMenu) are no-op
 * components, and the page's card is a raw snippet the test owns; `$lib/i18n` answers `⟦<key>⟧`, so a text is read as
 * the key the component asked for. `LegalLinks` is the real one, reached through the frame. The instance configuration
 * is the real store, its answer set per test by a forced `load` whose `fetchConfig` the test owns; the generated alias
 * of `GET /system/instance` is spied and refuses, so no case reaches a network.
 *
 * Written red-first, before the line exists. The frame is imported once, in a `beforeAll` with a long budget: its first
 * `lucide-svelte` import may take ~27 s under load.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {createRawSnippet, flushSync} from 'svelte';
import {cleanup, render, screen, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const i18n = vi.hoisted(() => ({mark: (key: string): string => `⟦${key}⟧`}));

vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const translator = readable(i18n.mark);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator};
});
vi.mock('$lib/components/ui/ThemeToggle.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/layout/LanguageSelector.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/layout/HelpMenu.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/ui/AnimatedBackground.svelte', () => ({default: () => {}}));

import {zodiosApi} from '$lib/api';
import {instanceConfig, type InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

let AuthPageFrame: typeof import('./AuthPageFrame.svelte').default;

// --- Fixtures -------------------------------------------------------------

const INSTANCE_ALIAS = 'get_instance_config_api_v1_system_instance_get';
/** The generated client seen through that one alias: spying through the full client type sends TS into an excessively deep instantiation. */
const instanceEndpoint = zodiosApi as unknown as Record<typeof INSTANCE_ALIAS, () => Promise<InstanceConfig>>;
const TERMS = 'https://legal.example.org/terms?edition=2026';
const PRIVACY = 'https://legal.example.org/privacy#data';

/** The test ids the route pages framed by `AuthPageFrame` give it. */
const FRAMED_PAGES = ['login-page', 'invite-page', 'setup-page', 'reset-password-page', 'verify-email-page'];

/** The page's card, as a stand-in the test owns. */
const card = createRawSnippet(() => ({render: () => `<div data-testid="probe-page-card">a card</div>`}));

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

/** The configuration in force, as if the sign-in page's own request had answered `config`. */
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

/** Draw the frame around the probe card; the frame's own output is what `container` holds. */
function mountFrame(testId?: string): HTMLElement {
    const {container} = render(AuthPageFrame, {props: testId === undefined ? {children: card} : {testId, children: card}});
    return container;
}

/** The line of the frame: one `auth-legal-links`, after the page content and outside the card, holding one compact `legal-links`. */
function legalLine(frame: HTMLElement): {line: HTMLElement; links: HTMLElement} {
    const pageCard = screen.getByTestId('probe-page-card');
    const line = exactlyOne(frame, 'auth-legal-links', 'the frame');
    expect(pageCard.contains(line), 'the legal line is not part of the page card').toBe(false);
    expect(line.contains(pageCard), 'the legal line does not wrap the page card').toBe(false);
    expect(Boolean(pageCard.compareDocumentPosition(line) & Node.DOCUMENT_POSITION_FOLLOWING), 'the legal line comes under the page content').toBe(true);
    const links = exactlyOne(line, 'legal-links', 'auth-legal-links');
    expect(text(links), 'the compact notice: its disclaimer is legal.disclaimerShort').toContain(i18n.mark('legal.disclaimerShort'));
    return {line, links};
}

// --- Lifecycle --------------------------------------------------------------

beforeAll(async () => {
    // The reactivity case and the absences below would pass vacuously where effects never run.
    assertEffectsRun();
    AuthPageFrame = (await import('./AuthPageFrame.svelte')).default;
}, 180_000);

beforeEach(() => {
    vi.spyOn(instanceEndpoint, INSTANCE_ALIAS).mockRejectedValue(new Error('no network in this test'));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

// =========================================================================
describe('AuthPageFrame — the compact legal notice under the page content', () => {
    // red until A9
    it.each(FRAMED_PAGES)('APL-01: %s — one auth-legal-links with the compact legal-links, under the card', async (testId) => {
        await answered(answerWith());

        const frame = mountFrame(testId);

        // Premise: the page's own container is drawn, with its card inside.
        expect(within(screen.getByTestId(testId)).getByTestId('probe-page-card')).toBeInTheDocument();
        legalLine(frame);
    });

    // red until A9
    it('APL-02: a frame given no test id draws the line too', async () => {
        await answered(answerWith());

        legalLine(mountFrame());
    });

    // red until A9
    it('APL-03: no link while the instance sets none — an older server, no legal block', async () => {
        await answered(answerWith());

        const {line} = legalLine(mountFrame('login-page'));

        expectLink(line, 'legal-terms-link', null);
        expectLink(line, 'legal-privacy-link', null);
    });

    // red until A9
    it('APL-04: with both URLs set, the line links to the terms and to the privacy policy', async () => {
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));

        const {links} = legalLine(mountFrame('login-page'));

        expectLink(links, 'legal-terms-link', TERMS);
        expectLink(links, 'legal-privacy-link', PRIVACY);
    });
});

describe('AuthPageFrame — the line follows the instance configuration', () => {
    // red until A9
    it('APL-05: the request of the sign-in page answering after the frame is drawn brings the links', async () => {
        await answered(answerWith({terms_url: null, privacy_url: null}));
        const frame = mountFrame('login-page');
        const {line} = legalLine(frame);
        expectLink(line, 'legal-terms-link', null);
        expectLink(line, 'legal-privacy-link', null);

        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        flushSync();

        const {links} = legalLine(frame);
        expectLink(links, 'legal-terms-link', TERMS);
        expectLink(links, 'legal-privacy-link', PRIVACY);
    });
});

describe('AuthPageFrame — colour roles only in the legal line', () => {
    // red until A9
    it('APL-06: no palette class and no dark: variant in auth-legal-links, links included', async () => {
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        const {line} = legalLine(mountFrame('login-page'));
        // Presence barrier: the scan below covers the links, not a line drawn without them.
        expectLink(line, 'legal-terms-link', TERMS);
        expectLink(line, 'legal-privacy-link', PRIVACY);

        expect(colourOffences(line), 'palette classes or dark: variants rendered').toEqual([]);
    });
});
