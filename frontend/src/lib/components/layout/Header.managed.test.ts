// @vitest-environment jsdom
/**
 * Header on a managed instance (F05, lot A9 of workstream A): the «Buy me a coffee» link of the app header
 * (`header-donate-link`) shows only when `donationsVisible()` — the server has answered (`instanceConfig.loaded`) and
 * said `profile: 'selfhosted'`.
 *
 * The contract under test:
 *   - HDM-01 (positive control, green today): answered self-hosted, the link is in the header, on the donation page;
 *   - HDM-02: before the answer, no link — the defaults say self-hosted, but a managed instance must not flash one
 *     while its `GET /system/instance` is in flight (the (app) layout asks it on mount) —; the header and its own
 *     controls are there;
 *   - HDM-03: answered managed, no link;
 *   - HDM-04/05: drawn before the answer, the header follows it in place: the link appears once the answer says
 *     self-hosted, never when it says managed.
 * "No link" is asserted twice: by test id, and as no link to the donation page anywhere in the header.
 *
 * Mocks, all owned here: `$lib/features/instance/instanceConfig.svelte` is a fake with the real store's shape —
 * enumerable getters over a `$state` box (`reactiveBox`) — so a test lands the server's answer by writing the box, as
 * `load()` does; `load` is a spy answering nothing of its own. `$lib/i18n`: `_` marks each key (`⟦key⟧`). The four
 * controls of the header (PrivacyToggle, ThemeToggle, LanguageSelector, HelpMenu) are no-op components: HelpMenu's own
 * coffee is `HelpMenu.managed.test.ts`'s subject, and the scroll machinery is `Header.test.ts`'s.
 *
 * The component is loaded once, in a guarded `beforeAll` with its own budget: its first transform pulls the
 * `lucide-svelte` barrel, which is cold and slow under load (the pattern of `GapFixStep.test.ts`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import type HeaderComponent from './Header.svelte';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, render, screen, within} from '$test/component';
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

// Keys, not prose: the header renders `⟦key⟧`, the same in every language.
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const marked = readable((key: string) => `⟦${key}⟧`);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: marked, t: marked};
});
vi.mock('$lib/components/ui/PrivacyToggle.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/ui/ThemeToggle.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/layout/LanguageSelector.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/layout/HelpMenu.svelte', () => ({default: () => {}}));

const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
const MANAGED: InstanceConfig = {...SELFHOSTED, profile: 'managed'};

// ---------------------------------------------------------------------------
// Loading the component under test
// ---------------------------------------------------------------------------

const COMPONENT_MODULES = import.meta.glob<{default: typeof HeaderComponent}>('./Header.svelte');

/** What the loading hook found: the component, or why it could not be loaded. */
let loaded: {Header: typeof HeaderComponent} | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = COMPONENT_MODULES['./Header.svelte'];
        if (!load) throw new Error('Header.svelte cannot be found next to this test');
        loaded = {Header: (await load()).default};
    } catch (error) {
        loaded = {error};
    }
}, 120_000);

function component(): typeof HeaderComponent {
    if (loaded === undefined) throw new Error('the component under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.Header;
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

async function mount(): Promise<void> {
    render(component(), {props: {}});
    await tick();
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

/** The barrier of every absence below: the header is drawn, with its own menu toggle. */
function expectHeaderDrawn(): void {
    expect(screen.getByTestId('app-header'), 'premise: the header is drawn').toBeInTheDocument();
    expect(within(screen.getByTestId('app-header')).getByTestId('mobile-menu-toggle'), 'premise: a sibling control of the link is drawn').toBeInTheDocument();
}

function expectNoDonationLink(): void {
    expect(screen.queryByTestId('header-donate-link'), 'no header-donate-link').toBeNull();
    expect(donationLinks(screen.getByTestId('app-header')), 'no link to the donation page anywhere in the header').toEqual([]);
}

beforeEach(() => {
    mocks.instance.config = mocks.BEFORE_ANSWER;
    mocks.instance.loaded = false;
    mocks.instance.failed = false;
    flushSync();
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockImplementation(() => Promise.resolve());
});

afterEach(() => {
    cleanup();
});

describe('Header — the coffee link only on a self-hosted instance that has answered (F05)', () => {
    it('HDM-01: answered self-hosted — header-donate-link in the header, on the donation page (positive control)', async () => {
        await serverAnswers(SELFHOSTED);

        await mount();

        expectHeaderDrawn();
        const link = within(screen.getByTestId('app-header')).getByTestId('header-donate-link');
        expect(link).toHaveAttribute('href', BUY_ME_A_COFFEE_URL);
        const scanned = donationLinks(screen.getByTestId('app-header'));
        expect(scanned, 'the scan finds the link: it can see one').toHaveLength(1);
        expect(scanned[0]).toBe(link);
    });

    // red until A9
    it('HDM-02: before the answer — no coffee link; the header and its menu toggle are there', async () => {
        await mount();

        expectHeaderDrawn();
        expectNoDonationLink();
    });

    // red until A9
    it('HDM-03: answered managed — no coffee link; the header and its menu toggle are there', async () => {
        await serverAnswers(MANAGED);

        await mount();

        expectHeaderDrawn();
        expectNoDonationLink();
    });
});

describe('Header — drawn before the answer, it follows it in place', () => {
    // red until A9
    it('HDM-04: the link appears once the answer says self-hosted', async () => {
        await mount();
        expectHeaderDrawn();
        expectNoDonationLink();

        await serverAnswers(SELFHOSTED);

        expect(within(screen.getByTestId('app-header')).getByTestId('header-donate-link'), 'the answer said self-hosted').toHaveAttribute('href', BUY_ME_A_COFFEE_URL);
    });

    // red until A9
    it('HDM-05: an answer that says managed never shows it', async () => {
        await mount();
        expectHeaderDrawn();
        expectNoDonationLink();

        await serverAnswers(MANAGED);

        expectHeaderDrawn();
        expectNoDonationLink();
    });
});
