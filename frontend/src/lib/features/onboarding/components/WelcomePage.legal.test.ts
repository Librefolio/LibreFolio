// @vitest-environment jsdom
/**
 * WelcomePage — the instance's legal notice on the welcome page (workstream A, lot A9, F09; decision D-A11: the
 * Welcome is one of its places, «una riga»).
 *
 * The contract under test (approved by the coordinator; the disclaimer wording is pending the developer):
 *   - `welcome-page` holds one `legal-notice`, the full notice (its disclaimer is `legal.disclaimer`), whatever the
 *     page shows — the form while the welcome is pending, the banner once it is completed or skipped;
 *   - the links are the notice's: none without a `legal` block; with both URLs set, `legal-terms-link` and
 *     `legal-privacy-link` inside the notice, to those URLs, in a new tab, without opener or referrer;
 *   - the notice follows the instance configuration: the (app) layout's request answering after the page is drawn
 *     brings the links;
 *   - colour roles only in the notice: no palette class and no `dark:`.
 *
 * Mocks follow `WelcomePage.test.ts`: `SettingCurrency` (inside `WelcomeForm`) and `ImagePickerWrapper` are the harness
 * probes, so neither the currency search nor the image picker graph loads. `$lib/i18n` answers `⟦<key>⟧`, so a text is
 * read as the key the component asked for; the page's own copy is the `*_TOKEN` props. `LegalNotice` is the real one,
 * reached through the page. The instance configuration is the real store, its answer set per test by a forced `load`
 * whose `fetchConfig` the test owns; the generated alias of `GET /system/instance` is spied and refuses.
 *
 * Written red-first, before the notice is on the page. The page is imported once, in a `beforeAll` with a long budget:
 * its first `lucide-svelte` import (through `WelcomeForm`) may take ~27 s under load.
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
vi.mock('$lib/features/settings/SettingCurrency.svelte', async () => ({
    default: (await import('$test/harness/SettingCurrencyProbe.svelte')).default,
}));
vi.mock('$lib/components/ui/media/ImagePickerWrapper.svelte', async () => ({
    default: (await import('$test/harness/ImagePickerWrapperProbe.svelte')).default,
}));

import {zodiosApi} from '$lib/api';
import {instanceConfig, type InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import type {WelcomeCopy} from '$lib/features/onboarding/welcome';

let WelcomePage: typeof import('./WelcomePage.svelte').default;

// --- Fixtures -------------------------------------------------------------

const INSTANCE_ALIAS = 'get_instance_config_api_v1_system_instance_get';
/** The generated client seen through that one alias: spying through the full client type sends TS into an excessively deep instantiation. */
const instanceEndpoint = zodiosApi as unknown as Record<typeof INSTANCE_ALIAS, () => Promise<InstanceConfig>>;
const TERMS = 'https://legal.example.org/terms?edition=2026';
const PRIVACY = 'https://legal.example.org/privacy#data';

const COPY: WelcomeCopy = {
    productName: 'PRODUCT_TOKEN',
    title: 'TITLE_TOKEN',
    description: 'DESCRIPTION_TOKEN',
    defaultsHint: 'DEFAULTS_HINT_TOKEN',
    avatarLabel: 'AVATAR_LABEL_TOKEN',
    avatarHint: 'AVATAR_HINT_TOKEN',
    chooseAvatar: 'CHOOSE_AVATAR_TOKEN',
    removeAvatar: 'REMOVE_AVATAR_TOKEN',
    avatarAlt: 'AVATAR_ALT_TOKEN',
    languageLabel: 'LANGUAGE_LABEL_TOKEN',
    languageHint: 'LANGUAGE_HINT_TOKEN',
    currencyLabel: 'CURRENCY_LABEL_TOKEN',
    currencyHint: 'CURRENCY_HINT_TOKEN',
    themeHint: 'THEME_HINT_TOKEN',
    skip: 'SKIP_TOKEN',
    skipHint: 'SKIP_HINT_TOKEN',
    continue: 'CONTINUE_TOKEN',
    logout: 'LOGOUT_TOKEN',
    completed: 'COMPLETED_TOKEN',
    skipped: 'SKIPPED_TOKEN',
};

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

/** Draw the page as the welcome route does; `outcome` null is the pending welcome, with its form. */
function mountWelcome(outcome: 'completed' | 'skipped' | null = null): HTMLElement {
    render(WelcomePage, {
        copy: COPY,
        username: 'Jane Doe',
        language: 'en',
        baseCurrency: 'EUR',
        avatarUrl: null,
        outcome,
        oncomplete: vi.fn(),
        onskip: vi.fn(),
        onlogout: vi.fn(),
    });
    return screen.getByTestId('welcome-page');
}

/** The page's notice: one full `legal-notice` inside `welcome-page`. */
function noticeOf(page: HTMLElement): HTMLElement {
    const notice = exactlyOne(page, 'legal-notice', 'welcome-page');
    expect(text(notice), 'the full notice: its disclaimer is legal.disclaimer').toContain(i18n.mark('legal.disclaimer'));
    return notice;
}

// --- Lifecycle --------------------------------------------------------------

beforeAll(async () => {
    // The reactivity case and the absences below would pass vacuously where effects never run.
    assertEffectsRun();
    WelcomePage = (await import('./WelcomePage.svelte')).default;
}, 180_000);

beforeEach(() => {
    vi.spyOn(instanceEndpoint, INSTANCE_ALIAS).mockRejectedValue(new Error('no network in this test'));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

// =========================================================================
describe('WelcomePage — the legal notice', () => {
    const STATES: Array<{label: string; outcome: 'completed' | 'skipped' | null; shown: string}> = [
        {label: 'pending, with the form', outcome: null, shown: 'welcome-form'},
        {label: 'completed, with the banner', outcome: 'completed', shown: 'welcome-outcome'},
        {label: 'skipped, with the banner', outcome: 'skipped', shown: 'welcome-outcome'},
    ];

    // red until A9
    it.each(STATES)('WLG-01: $label — welcome-page holds one full legal-notice, without links while the instance sets none', async ({outcome, shown}) => {
        await answered(answerWith());

        const page = mountWelcome(outcome);

        // Premise: the page is in the state the case names.
        expect(within(page).getByTestId(shown)).toBeInTheDocument();
        const notice = noticeOf(page);
        expectLink(notice, 'legal-terms-link', null);
        expectLink(notice, 'legal-privacy-link', null);
    });

    // red until A9
    it('WLG-02: with both URLs set, the notice links to the terms and to the privacy policy', async () => {
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));

        const notice = noticeOf(mountWelcome());

        expectLink(notice, 'legal-terms-link', TERMS);
        expectLink(notice, 'legal-privacy-link', PRIVACY);
    });

    // red until A9
    it('WLG-03: the notice follows the instance configuration — an answer landing after the page is drawn brings the links', async () => {
        await answered(answerWith({terms_url: null, privacy_url: null}));
        const page = mountWelcome();
        const before = noticeOf(page);
        expectLink(before, 'legal-terms-link', null);
        expectLink(before, 'legal-privacy-link', null);

        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        flushSync();

        const after = noticeOf(page);
        expectLink(after, 'legal-terms-link', TERMS);
        expectLink(after, 'legal-privacy-link', PRIVACY);
    });

    // red until A9
    it('WLG-04: colour roles only — no palette class and no dark: variant in the notice, links included', async () => {
        await answered(answerWith({terms_url: TERMS, privacy_url: PRIVACY}));
        const notice = noticeOf(mountWelcome());
        // Presence barrier: the scan below covers the links, not a notice drawn without them.
        expectLink(notice, 'legal-terms-link', TERMS);
        expectLink(notice, 'legal-privacy-link', PRIVACY);

        expect(colourOffences(notice), 'palette classes or dark: variants rendered').toEqual([]);
    });
});
