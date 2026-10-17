// @vitest-environment jsdom
/**
 * LegalLinks — the compact legal notice (workstream A, lot A9, F09): the line at the foot of the sign-in pages
 * (`AuthPageFrame`) and of the sidebar, where `LegalNotice` would not fit.
 *
 * The contract under test (approved by the coordinator; the disclaimer wording is pending the developer):
 *   - the root `legal-links` is always rendered, with the short disclaimer `$_('legal.disclaimerShort')` and not the
 *     full one, which is `LegalNotice`'s;
 *   - the same two links as `LegalNotice`, with the same test ids and the same attributes: `legal-terms-link` when
 *     `instanceConfig.config.legal.terms_url` is set (an `<a>` to that very URL, named `$_('legal.terms')`,
 *     `target="_blank"`, `rel="noopener noreferrer"`), `legal-privacy-link` the same for `privacy_url`
 *     (`$_('legal.privacy')`);
 *   - a link is absent when its URL is null or absent, and both are without a `legal` block (the default
 *     configuration, in force until the server answers, and an older server);
 *   - the component follows the store: an answer landing after mount adds, retargets and removes the links;
 *   - colour roles only: no palette class and no `dark:` on anything it renders.
 * The five `legal.*` keys, `legal.disclaimerShort` included, are checked in the catalogues by `LegalNotice.test.ts`.
 *
 * Texts are never compared with a sentence: `$lib/i18n` is mocked with a translator that answers `⟦<key>⟧`. The
 * instance configuration is the real store, its answer set per test by a forced `load` whose `fetchConfig` the test
 * owns; the generated alias of `GET /system/instance` is spied and refuses, so no case reaches a network.
 *
 * Written red-first, before `LegalLinks.svelte` exists: the component is imported once, in a guarded `beforeAll` with a
 * long budget (a first `lucide-svelte` import may take ~27 s under load), through a specifier Vite does not resolve
 * while compiling this file, so each case fails on its own with the reason instead of the file failing whole. A guard
 * loads an existing component (`../auth/AuthCard.svelte`) the same way: the red is the absence, not the loader.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, type Component} from 'svelte';
import {cleanup, render, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const i18n = vi.hoisted(() => ({mark: (key: string): string => `⟦${key}⟧`}));

vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const translator = readable(i18n.mark);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator};
});

import {zodiosApi} from '$lib/api';
import {DEFAULT_INSTANCE_CONFIG, instanceConfig, type InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

// --- Loading the component ------------------------------------------------

/** Where the component will live. A variable, so that Vite does not try to resolve it while compiling this file. */
const LEGAL_LINKS_MODULE = './LegalLinks.svelte';
/** The loader's positive control: an existing component of a sibling feature, reached the same way. */
const LOADER_CONTROL_MODULE = '../auth/AuthCard.svelte';
let LegalLinks: Component | null = null;
let loadFailure = 'not attempted';

async function loadComponent(specifier: string): Promise<Component> {
    return ((await import(/* @vite-ignore */ specifier)) as {default: Component}).default;
}

function legalLinks(): Component {
    if (!LegalLinks) throw new Error(`src/lib/features/legal/LegalLinks.svelte cannot be loaded yet (red until A9): ${loadFailure}`);
    return LegalLinks;
}

// --- Fixtures -------------------------------------------------------------

const INSTANCE_ALIAS = 'get_instance_config_api_v1_system_instance_get';
/** The generated client seen through that one alias: spying through the full client type sends TS into an excessively deep instantiation. */
const instanceEndpoint = zodiosApi as unknown as Record<typeof INSTANCE_ALIAS, () => Promise<InstanceConfig>>;
const TERMS = 'https://legal.example.org/terms?edition=2026';
const PRIVACY = 'https://legal.example.org/privacy#data';
const PRIVACY_MOVED = 'https://policies.example.net/privacy';

/** The legal block as the A9 backend serves it; a key left out stands for a field an answer lacks. */
interface LegalBlock {
    terms_url?: string | null;
    privacy_url?: string | null;
}

/** An answer of `GET /system/instance`; without `legal`, a server that predates the block. Cast: see LegalNotice.test.ts. */
function answerWith(legal?: LegalBlock): InstanceConfig {
    const base = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
    return (legal === undefined ? base : {...base, legal}) as unknown as InstanceConfig;
}

/** The configuration in force, as if the page's own request had answered `config`. */
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

/** The link `testId` inside `root`: absent when `url` is null, otherwise an external link to `url` named `labelKey`. */
function expectLink(root: HTMLElement, testId: string, url: string | null, labelKey: string): void {
    const links = within(root).queryAllByTestId(testId);
    if (url === null) {
        expect(links, `no ${testId} while its URL is not set`).toHaveLength(0);
        return;
    }
    expect(links, `exactly one ${testId} while its URL is set`).toHaveLength(1);
    const [link] = links;
    expect(link.tagName, `${testId} is a link`).toBe('A');
    expect(link, `${testId} goes to the URL the instance sets`).toHaveAttribute('href', url);
    expect(link, `${testId} opens in a new tab`).toHaveAttribute('target', '_blank');
    expect((link.getAttribute('rel') ?? '').split(/\s+/), `${testId} gives the page no opener and no referrer`).toEqual(expect.arrayContaining(['noopener', 'noreferrer']));
    expect(text(link), `${testId} is named by ${labelKey}`).toContain(i18n.mark(labelKey));
}

function expectLinks(root: HTMLElement, {terms, privacy}: {terms: string | null; privacy: string | null}): void {
    expectLink(root, 'legal-terms-link', terms, 'legal.terms');
    expectLink(root, 'legal-privacy-link', privacy, 'legal.privacy');
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

// --- Lifecycle --------------------------------------------------------------

beforeAll(async () => {
    // The reactivity case and every absence below would pass vacuously where effects never run.
    assertEffectsRun();
    try {
        LegalLinks = await loadComponent(LEGAL_LINKS_MODULE);
    } catch (error) {
        loadFailure = String(error);
    }
}, 180_000);

beforeEach(() => {
    vi.spyOn(instanceEndpoint, INSTANCE_ALIAS).mockRejectedValue(new Error('no network in this test'));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

// =========================================================================
describe('LegalLinks — the loader', () => {
    // guard — the red of the cases below is the component's absence, not the loader: a component that exists loads
    it('LGL-00: an existing component of a sibling feature loads through the same variable specifier', async () => {
        expect(typeof (await loadComponent(LOADER_CONTROL_MODULE)), 'a Svelte 5 component is a function').toBe('function');
    });
});

describe('LegalLinks — the short disclaimer, and a link for each URL the instance sets', () => {
    const CASES: Array<{label: string; config: InstanceConfig; terms: string | null; privacy: string | null}> = [
        {label: 'the default configuration, in force until the server answers', config: DEFAULT_INSTANCE_CONFIG, terms: null, privacy: null},
        {label: 'an older server: no legal block', config: answerWith(), terms: null, privacy: null},
        {label: 'both URLs null', config: answerWith({terms_url: null, privacy_url: null}), terms: null, privacy: null},
        {label: 'the terms only', config: answerWith({terms_url: TERMS, privacy_url: null}), terms: TERMS, privacy: null},
        {label: 'the privacy policy only', config: answerWith({terms_url: null, privacy_url: PRIVACY}), terms: null, privacy: PRIVACY},
        {label: 'the privacy policy, terms_url absent from the block', config: answerWith({privacy_url: PRIVACY}), terms: null, privacy: PRIVACY},
        {label: 'both URLs set', config: answerWith({terms_url: TERMS, privacy_url: PRIVACY}), terms: TERMS, privacy: PRIVACY},
    ];

    // red until A9
    it.each(CASES)('LGL-01: $label — legal-links with legal.disclaimerShort, and exactly the links whose URL is set', async ({config, terms, privacy}) => {
        const Links = legalLinks();
        await answered(config);

        render(Links);

        const links = exactlyOne(document.body, 'legal-links', 'the page');
        expect(text(links), 'the short disclaimer is always there').toContain(i18n.mark('legal.disclaimerShort'));
        expectLinks(links, {terms, privacy});
    });

    // red until A9
    it('LGL-02: compact — the full disclaimer is not part of it', async () => {
        const Links = legalLinks();
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));

        render(Links);

        const links = exactlyOne(document.body, 'legal-links', 'the page');
        // Presence barrier: the compact line is drawn, with its own disclaimer and its links.
        expect(text(links)).toContain(i18n.mark('legal.disclaimerShort'));
        expectLinks(links, {terms: TERMS, privacy: PRIVACY});
        expect(text(links), 'the long disclaimer belongs to LegalNotice').not.toContain(i18n.mark('legal.disclaimer'));
    });
});

describe('LegalLinks — follows the instance configuration', () => {
    // red until A9
    it('LGL-03: an answer landing after mount adds the links, retargets one, and removes them, the short disclaimer staying', async () => {
        const Links = legalLinks();
        await answered(answerWith({terms_url: null, privacy_url: null}));
        render(Links);
        expectLinks(exactlyOne(document.body, 'legal-links', 'the page'), {terms: null, privacy: null});

        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        flushSync();
        expectLinks(exactlyOne(document.body, 'legal-links', 'the page'), {terms: TERMS, privacy: PRIVACY});

        await answered(answerWith({terms_url: null, privacy_url: PRIVACY_MOVED}));
        flushSync();
        expectLinks(exactlyOne(document.body, 'legal-links', 'the page'), {terms: null, privacy: PRIVACY_MOVED});

        await answered(answerWith());
        flushSync();
        const links = exactlyOne(document.body, 'legal-links', 'the page');
        expectLinks(links, {terms: null, privacy: null});
        expect(text(links)).toContain(i18n.mark('legal.disclaimerShort'));
    });
});

describe('LegalLinks — colour roles only', () => {
    // red until A9
    it('LGL-04: no palette class and no dark: variant on the line or on anything inside it, links included', async () => {
        const Links = legalLinks();
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        render(Links);
        const links = exactlyOne(document.body, 'legal-links', 'the page');
        // Presence barrier: the scan below covers the links, not a line drawn without them.
        expectLinks(links, {terms: TERMS, privacy: PRIVACY});

        expect(colourOffences(links), 'palette classes or dark: variants rendered').toEqual([]);
    });
});
