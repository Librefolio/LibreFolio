// @vitest-environment jsdom
/**
 * HelpMenu on a managed instance (F05, lot A9 of workstream A): the «Buy me a coffee» item of the help menu shows only
 * when `donationsVisible()` — the server has answered (`instanceConfig.loaded`) and said `profile: 'selfhosted'`. The
 * item gets the test id `help-donate-link` (new in A9). The GitHub issues item («report a bug») stays always.
 *
 * The contract under test, the menu open (`help-menu-button` → `help-menu-panel`):
 *   - HMM-01: answered self-hosted, the item is in the panel, on the donation page, in a new tab with
 *     `rel="noopener noreferrer"`, next to the GitHub issues item;
 *   - HMM-02: before the answer, no item — the defaults say self-hosted, but a managed instance must not flash one
 *     while its `GET /system/instance` is in flight —; the GitHub issues item is there;
 *   - HMM-03: answered managed, no item; the GitHub issues item is there;
 *   - HMM-04/05: the menu open before the answer, the panel follows it in place: the item appears once the answer
 *     says self-hosted, never when it says managed.
 * "No item" is asserted twice: by test id, and as no link to the donation page anywhere in the panel — today's item
 * has no test id, so an absence by test id alone would hold already. The GitHub issues item has no test id either: it
 * is found by its destination (`GITHUB_ISSUES_URL`, the menu's own constant), never by its text.
 *
 * Mocks, all owned here: `$lib/features/instance/instanceConfig.svelte` is a fake with the real store's shape —
 * enumerable getters over a `$state` box (`reactiveBox`) — so a test lands the server's answer by writing the box, as
 * `load()` does; `load` is a spy answering nothing of its own. `$lib/i18n`: `_` marks each key (`⟦key⟧`).
 *
 * The component is loaded once, in a guarded `beforeAll` with its own budget: its first transform pulls the
 * `lucide-svelte` barrel, which is cold and slow under load (the pattern of `GapFixStep.test.ts`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import type HelpMenuComponent from './HelpMenu.svelte';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, fireEvent, render, screen, within} from '$test/component';
import {BUY_ME_A_COFFEE_URL} from '$lib/features/support/supportLinks';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    /** What the real store holds until the server answers: `DEFAULT_INSTANCE_CONFIG`, a self-hosted instance. */
    const BEFORE_ANSWER = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}} as InstanceConfig;
    return {
        BEFORE_ANSWER,
        instance: reactiveBox<{config: InstanceConfig; loaded: boolean; failed: boolean}>({config: BEFORE_ANSWER, loaded: false, failed: false}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
    };
});

vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: mocks.BEFORE_ANSWER,
    fetchInstanceConfigFromApi: () => Promise.reject(new Error('no network in this test')),
    instanceConfig: {
        get config() {
            return mocks.instance.config;
        },
        get loaded() {
            return mocks.instance.loaded;
        },
        get failed() {
            return mocks.instance.failed;
        },
        load: mocks.instanceLoad,
    },
}));

// Keys, not prose: the menu renders `⟦key⟧`, the same in every language.
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const marked = readable((key: string) => `⟦${key}⟧`);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: marked, t: marked};
});

const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
const MANAGED: InstanceConfig = {...SELFHOSTED, profile: 'managed'};

/** The destination of the «report a bug» item (`githubIssuesUrl` in HelpMenu.svelte): the item has no test id. */
const GITHUB_ISSUES_URL = 'https://github.com/Librefolio/LibreFolio/issues';

// ---------------------------------------------------------------------------
// Loading the component under test
// ---------------------------------------------------------------------------

const COMPONENT_MODULES = import.meta.glob<{default: typeof HelpMenuComponent}>('./HelpMenu.svelte');

/** What the loading hook found: the component, or why it could not be loaded. */
let loaded: {HelpMenu: typeof HelpMenuComponent} | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = COMPONENT_MODULES['./HelpMenu.svelte'];
        if (!load) throw new Error('HelpMenu.svelte cannot be found next to this test');
        loaded = {HelpMenu: (await load()).default};
    } catch (error) {
        loaded = {error};
    }
}, 120_000);

function component(): typeof HelpMenuComponent {
    if (loaded === undefined) throw new Error('the component under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.HelpMenu;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** The server's answer lands, as `instanceConfig.load()` lands it. */
async function serverAnswers(config: InstanceConfig): Promise<void> {
    mocks.instance.config = config;
    mocks.instance.loaded = true;
    mocks.instance.failed = false;
    flushSync();
    await tick();
}

/** Draws the menu and opens it; ends on the open panel. */
async function mountOpen(): Promise<void> {
    render(component(), {props: {}});
    await fireEvent.click(screen.getByTestId('help-menu-button'));
    expect(screen.getByTestId('help-menu-panel'), 'premise: the menu is open').toBeVisible();
}

function panel(): HTMLElement {
    return screen.getByTestId('help-menu-panel');
}

const DONATION_HOST = new URL(BUY_ME_A_COFFEE_URL).hostname;

/** Every link inside `root` that leads to the donation page, whatever its test id. */
function donationLinks(root: HTMLElement): HTMLAnchorElement[] {
    return [...root.querySelectorAll<HTMLAnchorElement>('a[href]')].filter((anchor) => {
        try {
            return new URL(anchor.getAttribute('href') ?? '', 'http://localhost/').hostname === DONATION_HOST;
        } catch {
            return false;
        }
    });
}

/** The barrier of every absence below, and the item that stays always: «report a bug», on GitHub issues. */
function expectIssuesItem(): void {
    const issues = [...panel().querySelectorAll<HTMLAnchorElement>('a[href]')].filter((anchor) => anchor.getAttribute('href') === GITHUB_ISSUES_URL);
    expect(issues, 'the GitHub issues item stays, whatever the profile').toHaveLength(1);
    expect(issues[0]).toBeVisible();
}

function expectNoDonationItem(): void {
    expect(screen.queryByTestId('help-donate-link'), 'no help-donate-link').toBeNull();
    expect(donationLinks(panel()), 'no link to the donation page anywhere in the open menu').toEqual([]);
}

beforeEach(() => {
    mocks.instance.config = mocks.BEFORE_ANSWER;
    mocks.instance.loaded = false;
    mocks.instance.failed = false;
    flushSync();
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockImplementation(() => Promise.resolve());
    // The menu builds its documentation links from the stored language (`mkdocsUrl`): a Storage it can read, empty —
    // under this Node, the `localStorage` jsdom would give is shadowed by Node's own, unusable without a file.
    vi.stubGlobal('localStorage', {getItem: () => null, setItem: () => {}, removeItem: () => {}});
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

describe('HelpMenu — the coffee item only on a self-hosted instance that has answered (F05)', () => {
    // red until A9
    it('HMM-01: answered self-hosted — help-donate-link in the open menu, on the donation page, in a new tab, noopener noreferrer; the issues item too', async () => {
        await serverAnswers(SELFHOSTED);

        await mountOpen();

        expectIssuesItem();
        const item = within(panel()).getByTestId('help-donate-link');
        expect(item).toHaveAttribute('href', BUY_ME_A_COFFEE_URL);
        expect(item).toHaveAttribute('target', '_blank');
        expect(item.getAttribute('rel')?.split(/\s+/)).toEqual(expect.arrayContaining(['noopener', 'noreferrer']));
        const scanned = donationLinks(panel());
        expect(scanned, 'the one donation link of the menu is the one under the test id').toHaveLength(1);
        expect(scanned[0]).toBe(item);
    });

    // red until A9
    it('HMM-02: before the answer — no coffee item; the GitHub issues item is there', async () => {
        await mountOpen();

        expectIssuesItem();
        expectNoDonationItem();
    });

    // red until A9
    it('HMM-03: answered managed — no coffee item; the GitHub issues item is there', async () => {
        await serverAnswers(MANAGED);

        await mountOpen();

        expectIssuesItem();
        expectNoDonationItem();
    });
});

describe('HelpMenu — open before the answer, the panel follows it in place', () => {
    // red until A9
    it('HMM-04: the coffee item appears once the answer says self-hosted', async () => {
        await mountOpen();
        expectIssuesItem();
        expectNoDonationItem();

        await serverAnswers(SELFHOSTED);

        expect(within(panel()).getByTestId('help-donate-link'), 'the answer said self-hosted').toHaveAttribute('href', BUY_ME_A_COFFEE_URL);
        expectIssuesItem();
    });

    // red until A9
    it('HMM-05: an answer that says managed never shows it; the issues item stays', async () => {
        await mountOpen();
        expectIssuesItem();
        expectNoDonationItem();

        await serverAnswers(MANAGED);

        expectIssuesItem();
        expectNoDonationItem();
    });
});
