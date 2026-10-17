// @vitest-environment jsdom
/**
 * AuthPageFrame on a managed instance (F05, lot A9 of workstream A): the «Buy me a coffee» link in the bar of the
 * signed-out pages (`auth-page-controls`: login, setup, invitation, reset, email verification) shows only when
 * `donationsVisible()` — the server has answered (`instanceConfig.loaded`) and said `profile: 'selfhosted'`. The link
 * gets the test id `auth-donate-link` (new in A9).
 *
 * The contract under test:
 *   - APM-01: answered self-hosted, the link is in the bar, on the donation page, in a new tab with
 *     `rel="noopener noreferrer"`;
 *   - APM-02: before the answer, no link — the defaults say self-hosted, but a managed instance must not flash one
 *     while its `GET /system/instance` is in flight —; the bar and the page's card are there;
 *   - APM-03: answered managed, no link;
 *   - APM-04/05: drawn before the answer, the frame follows it in place: the link appears once the answer says
 *     self-hosted, never when it says managed.
 * "No link" is asserted twice: by test id, and as no link to the donation page anywhere in the frame — today's link
 * has no test id, so an absence by test id alone would hold already.
 *
 * Mocks, all owned here: `$lib/features/instance/instanceConfig.svelte` is a fake with the real store's shape —
 * enumerable getters over a `$state` box (`reactiveBox`) — so a test lands the server's answer by writing the box, as
 * `load()` does; `load` is a spy answering nothing of its own. `$lib/i18n`: `_` marks each key (`⟦key⟧`). The three
 * controls of the bar (ThemeToggle, LanguageSelector, HelpMenu) are no-op components, as in `AuthPageFrame.test.ts`:
 * HelpMenu's own coffee is `HelpMenu.managed.test.ts`'s subject.
 *
 * The component is loaded once, in a guarded `beforeAll` with its own budget: its first transform pulls the
 * `lucide-svelte` barrel, which is cold and slow under load (the pattern of `GapFixStep.test.ts`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {createRawSnippet, flushSync, tick} from 'svelte';
import type AuthPageFrameComponent from './AuthPageFrame.svelte';
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

// Keys, not prose: the frame renders `⟦key⟧`, the same in every language.
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const marked = readable((key: string) => `⟦${key}⟧`);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: marked, t: marked};
});
vi.mock('$lib/components/ui/ThemeToggle.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/layout/LanguageSelector.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/layout/HelpMenu.svelte', () => ({default: () => {}}));

const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
const MANAGED: InstanceConfig = {...SELFHOSTED, profile: 'managed'};

// ---------------------------------------------------------------------------
// Loading the component under test
// ---------------------------------------------------------------------------

const COMPONENT_MODULES = import.meta.glob<{default: typeof AuthPageFrameComponent}>('./AuthPageFrame.svelte');

/** What the loading hook found: the component, or why it could not be loaded. */
let loaded: {AuthPageFrame: typeof AuthPageFrameComponent} | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = COMPONENT_MODULES['./AuthPageFrame.svelte'];
        if (!load) throw new Error('AuthPageFrame.svelte cannot be found next to this test');
        loaded = {AuthPageFrame: (await load()).default};
    } catch (error) {
        loaded = {error};
    }
}, 120_000);

function component(): typeof AuthPageFrameComponent {
    if (loaded === undefined) throw new Error('the component under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.AuthPageFrame;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** The page's card, as a stand-in the test owns. */
const card = createRawSnippet(() => ({render: () => `<div data-testid="probe-page-card">a card</div>`}));

/** The server's answer lands, as `instanceConfig.load()` lands it. */
async function serverAnswers(config: InstanceConfig): Promise<void> {
    mocks.instance.config = config;
    mocks.instance.loaded = true;
    mocks.instance.failed = false;
    flushSync();
    await tick();
}

function mount(): void {
    render(component(), {props: {testId: 'probe-page', children: card}});
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

/** The barrier of every absence below: the bar of controls and the page's card are drawn. */
function expectFrameDrawn(): void {
    expect(screen.getByTestId('auth-page-controls'), 'premise: the bar of controls is drawn').toBeInTheDocument();
    expect(within(screen.getByTestId('probe-page')).getByTestId('probe-page-card'), 'premise: the page’s card is inside the frame').toBeInTheDocument();
}

function expectNoDonationLink(): void {
    expect(screen.queryByTestId('auth-donate-link'), 'no auth-donate-link').toBeNull();
    expect(donationLinks(document.body), 'no link to the donation page anywhere in the frame').toEqual([]);
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

describe('AuthPageFrame — the coffee link only on a self-hosted instance that has answered (F05)', () => {
    // red until A9
    it('APM-01: answered self-hosted — auth-donate-link in the bar, on the donation page, in a new tab, noopener noreferrer', async () => {
        await serverAnswers(SELFHOSTED);

        mount();

        expectFrameDrawn();
        const link = within(screen.getByTestId('auth-page-controls')).getByTestId('auth-donate-link');
        expect(link).toHaveAttribute('href', BUY_ME_A_COFFEE_URL);
        expect(link).toHaveAttribute('target', '_blank');
        expect(link.getAttribute('rel')?.split(/\s+/)).toEqual(expect.arrayContaining(['noopener', 'noreferrer']));
        const scanned = donationLinks(document.body);
        expect(scanned, 'the one donation link of the frame is the one under the test id').toHaveLength(1);
        expect(scanned[0]).toBe(link);
    });

    // red until A9
    it('APM-02: before the answer — no coffee link; the bar and the card are there', () => {
        mount();

        expectFrameDrawn();
        expectNoDonationLink();
    });

    // red until A9
    it('APM-03: answered managed — no coffee link; the bar and the card are there', async () => {
        await serverAnswers(MANAGED);

        mount();

        expectFrameDrawn();
        expectNoDonationLink();
    });
});

describe('AuthPageFrame — drawn before the answer, it follows it in place', () => {
    // red until A9
    it('APM-04: the link appears in the bar once the answer says self-hosted', async () => {
        mount();
        expectFrameDrawn();
        expectNoDonationLink();

        await serverAnswers(SELFHOSTED);

        expect(within(screen.getByTestId('auth-page-controls')).getByTestId('auth-donate-link'), 'the answer said self-hosted').toHaveAttribute('href', BUY_ME_A_COFFEE_URL);
    });

    // red until A9
    it('APM-05: an answer that says managed never shows it', async () => {
        mount();
        expectFrameDrawn();
        expectNoDonationLink();

        await serverAnswers(MANAGED);

        expectFrameDrawn();
        expectNoDonationLink();
    });
});
