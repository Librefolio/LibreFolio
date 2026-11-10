// @vitest-environment jsdom
/**
 * LegalNotice — the legal notice of the instance (workstream A, lot A9, F09): the disclaimer, and the links to the
 * terms of service and to the privacy policy when the instance sets them (`LIBREFOLIO_TOS_URL`,
 * `LIBREFOLIO_PRIVACY_URL`, served by `GET /system/instance` as `legal: {terms_url, privacy_url}`).
 *
 * The contract under test (approved by the coordinator; the disclaimer wording is pending the developer):
 *   - the root `legal-notice` is always rendered, with the disclaimer `$_('legal.disclaimer')`;
 *   - `legal-terms-link` when `instanceConfig.config.legal.terms_url` is set: an `<a>` to that very URL, named
 *     `$_('legal.terms')`, with `target="_blank"` and `rel="noopener noreferrer"`; `legal-privacy-link` the same for
 *     `privacy_url`, named `$_('legal.privacy')`;
 *   - a link is absent when its URL is null or absent, and both are without a `legal` block: under the default
 *     configuration (what is in force until the server answers) and from an older server;
 *   - the component follows the store: an answer landing after mount adds, retargets and removes the links;
 *   - colour roles only: no palette class and no `dark:` on anything it renders;
 *   - the five `legal.*` keys (the compact `LegalLinks`' `legal.disclaimerShort` included) are sentences in the four
 *     generated catalogues;
 *   - the generated client keeps the `legal` block: zod drops a key its schema lacks, so without a regenerated client
 *     (`./dev.py api sync`) the links never reach the component in the app, whatever the backend serves.
 *
 * Texts are never compared with a sentence: `$lib/i18n` is mocked with a translator that answers `⟦<key>⟧`, so what is
 * asserted is the key the component asked for. The instance configuration is the real store, its answer set per test
 * by a forced `load` whose `fetchConfig` the test owns; the generated alias of `GET /system/instance` is spied and
 * refuses, so no case reaches a network even if the component calls `load()` itself. The store is imported statically
 * (no `vi.resetModules()`, which would give the component a second Svelte runtime).
 *
 * Written red-first, before `LegalNotice.svelte` exists: the component is imported once, in a guarded `beforeAll` with
 * a long budget (its first import may pull `lucide-svelte`, ~27 s under load), through a specifier Vite does not
 * resolve while compiling this file, so each case fails on its own with the reason instead of the file failing whole.
 * A guard loads an existing component (`../auth/AuthCard.svelte`) the same way: the red is the absence, not the loader.
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
import {schemas} from '$lib/api/generated';
import {DEFAULT_INSTANCE_CONFIG, instanceConfig, type InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
// The real generated catalogues, read only by the catalogue block: the component renders through the marking translator.
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

// --- Loading the component ------------------------------------------------

/** Where the component will live. A variable, so that Vite does not try to resolve it while compiling this file. */
const LEGAL_NOTICE_MODULE = './LegalNotice.svelte';
/** The loader's positive control: an existing component of a sibling feature, reached the same way. */
const LOADER_CONTROL_MODULE = '../auth/AuthCard.svelte';
let LegalNotice: Component | null = null;
let loadFailure = 'not attempted';

async function loadComponent(specifier: string): Promise<Component> {
    return ((await import(/* @vite-ignore */ specifier)) as {default: Component}).default;
}

function legalNotice(): Component {
    if (!LegalNotice) throw new Error(`src/lib/features/legal/LegalNotice.svelte cannot be loaded yet (red until A9): ${loadFailure}`);
    return LegalNotice;
}

// --- Fixtures -------------------------------------------------------------

const INSTANCE_ALIAS = 'get_instance_config_api_v1_system_instance_get';
/** The generated client seen through that one alias: spying through the full client type sends TS into an excessively deep instantiation. */
const instanceEndpoint = zodiosApi as unknown as Record<typeof INSTANCE_ALIAS, () => Promise<InstanceConfig>>;
const TERMS = 'https://legal.example.org/terms?edition=2026';
const PRIVACY = 'https://legal.example.org/privacy#data';
const TERMS_MOVED = 'https://policies.example.net/tos';

/** The legal block as the A9 backend serves it; a key left out stands for a field an answer lacks. */
interface LegalBlock {
    terms_url?: string | null;
    privacy_url?: string | null;
}

/**
 * An answer of `GET /system/instance`. Without `legal`, the answer of a server that predates the block. Cast because
 * the generated type gains `legal` only once the client is regenerated from the A9 backend.
 */
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
        LegalNotice = await loadComponent(LEGAL_NOTICE_MODULE);
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
describe('LegalNotice — the loader', () => {
    // guard — the red of the cases below is the component's absence, not the loader: a component that exists loads
    it('LGN-00: an existing component of a sibling feature loads through the same variable specifier', async () => {
        expect(typeof (await loadComponent(LOADER_CONTROL_MODULE)), 'a Svelte 5 component is a function').toBe('function');
    });
});

describe('LegalNotice — the disclaimer, and a link for each URL the instance sets', () => {
    const CASES: Array<{label: string; config: InstanceConfig; terms: string | null; privacy: string | null}> = [
        {label: 'the default configuration, in force until the server answers', config: DEFAULT_INSTANCE_CONFIG, terms: null, privacy: null},
        {label: 'an older server: no legal block', config: answerWith(), terms: null, privacy: null},
        {label: 'both URLs null', config: answerWith({terms_url: null, privacy_url: null}), terms: null, privacy: null},
        {label: 'the terms only', config: answerWith({terms_url: TERMS, privacy_url: null}), terms: TERMS, privacy: null},
        {label: 'the privacy policy only', config: answerWith({terms_url: null, privacy_url: PRIVACY}), terms: null, privacy: PRIVACY},
        {label: 'the terms, privacy_url absent from the block', config: answerWith({terms_url: TERMS}), terms: TERMS, privacy: null},
        {label: 'both URLs set', config: answerWith({terms_url: TERMS, privacy_url: PRIVACY}), terms: TERMS, privacy: PRIVACY},
    ];

    // red until A9
    it.each(CASES)('LGN-01: $label — the notice with legal.disclaimer, and exactly the links whose URL is set', async ({config, terms, privacy}) => {
        const Notice = legalNotice();
        await answered(config);

        render(Notice);

        const notice = exactlyOne(document.body, 'legal-notice', 'the page');
        expect(text(notice), 'the disclaimer is always there').toContain(i18n.mark('legal.disclaimer'));
        expectLinks(notice, {terms, privacy});
    });
});

describe('LegalNotice — follows the instance configuration', () => {
    // red until A9
    it('LGN-02: an answer landing after mount adds the links, retargets one, and removes them, the disclaimer staying', async () => {
        const Notice = legalNotice();
        await answered(answerWith());
        render(Notice);
        expectLinks(exactlyOne(document.body, 'legal-notice', 'the page'), {terms: null, privacy: null});

        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        flushSync();
        expectLinks(exactlyOne(document.body, 'legal-notice', 'the page'), {terms: TERMS, privacy: PRIVACY});

        await answered(answerWith({terms_url: TERMS_MOVED, privacy_url: null}));
        flushSync();
        expectLinks(exactlyOne(document.body, 'legal-notice', 'the page'), {terms: TERMS_MOVED, privacy: null});

        await answered(answerWith());
        flushSync();
        const notice = exactlyOne(document.body, 'legal-notice', 'the page');
        expectLinks(notice, {terms: null, privacy: null});
        expect(text(notice)).toContain(i18n.mark('legal.disclaimer'));
    });
});

describe('LegalNotice — colour roles only', () => {
    // red until A9
    it('LGN-03: no palette class and no dark: variant on the notice or on anything inside it, links included', async () => {
        const Notice = legalNotice();
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        render(Notice);
        const notice = exactlyOne(document.body, 'legal-notice', 'the page');
        // Presence barrier: the scan below covers the links, not a notice drawn without them.
        expectLinks(notice, {terms: TERMS, privacy: PRIVACY});

        expect(colourOffences(notice), 'palette classes or dark: variants rendered').toEqual([]);
    });
});

// =========================================================================
describe('the legal.* keys — sentences in the four generated catalogues', () => {
    const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};
    const LEGAL_KEYS = ['legal.title', 'legal.disclaimer', 'legal.disclaimerShort', 'legal.terms', 'legal.privacy'];

    /** The leaf at a dotted key, read from the catalogue itself. */
    function leafOf(catalogue: unknown, key: string): unknown {
        let node = catalogue;
        for (const part of key.split('.')) node = node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined;
        return node;
    }

    /** The languages whose catalogue has no sentence at `key`. */
    function missingIn(key: string): string[] {
        return Object.keys(CATALOGUES).filter((language) => {
            const message = leafOf(CATALOGUES[language], key);
            return typeof message !== 'string' || message.trim() === '';
        });
    }

    // guard — the reader's positive control: keys the About tab renders today are found in all four
    it.each(['settings.license', 'settings.credits'])('LGN-04: %s, rendered today, is a sentence in the four catalogues', (key) => {
        expect(missingIn(key), 'the catalogues without it').toEqual([]);
    });

    // red until A9
    it.each(LEGAL_KEYS)('LGN-05: %s is a sentence in the four catalogues', (key) => {
        expect(missingIn(key), 'the catalogues without it').toEqual([]);
    });
});

describe('the generated client keeps the legal block of GET /system/instance', () => {
    // red until A9
    it('LGN-06: InstanceConfigResponse parses legal {terms_url, privacy_url} instead of dropping it', () => {
        const parsed = schemas.InstanceConfigResponse.parse(answerWith({terms_url: TERMS, privacy_url: null})) as {legal?: unknown};

        expect(parsed.legal, 'zod drops a key its schema lacks: the client must be regenerated (./dev.py api sync) from the A9 backend').toEqual(expect.objectContaining({terms_url: TERMS, privacy_url: null}));
    });
});
