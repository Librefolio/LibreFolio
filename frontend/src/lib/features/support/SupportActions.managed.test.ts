// @vitest-environment jsdom
/**
 * SupportActions on a managed instance (F05, lot A9 of workstream A): the «Buy me a coffee» action shows only when
 * `donationsVisible()` — the server has answered (`instanceConfig.loaded`) and said `profile: 'selfhosted'` —, under
 * its test id (`coffeeTestId`, `support-coffee` by default; the donation popup passes `donation-popup-donate`). The
 * social share buttons (`support-share-*`) always stay: sharing the project is not a donation (D-A8).
 *
 * The contract under test:
 *   - SAM-01 (positive control, green today): answered self-hosted, the coffee is there, on the donation page;
 *   - SAM-02: before the answer, no coffee — the defaults say self-hosted, but a managed instance must not flash one
 *     while its `GET /system/instance` is in flight —, and every share button is there;
 *   - SAM-03: answered managed, no coffee, every share button there;
 *   - SAM-04/05: drawn before the answer, the component follows it in place: the coffee appears once the answer says
 *     self-hosted, never when it says managed.
 * "No coffee" is asserted twice: by test id, and as no link to the donation page anywhere in the component — an absence
 * by test id alone would also hold for a coffee that merely lost its test id.
 *
 * Mocks, all owned here: `$lib/features/instance/instanceConfig.svelte` is a fake with the real store's shape —
 * enumerable getters over a `$state` box (`reactiveBox`) — so a test lands the server's answer by writing the box, as
 * `load()` does, and the component (through `donationsVisible()` or directly) reads it; `load` is a spy answering
 * nothing of its own. `$lib/i18n`: `_` marks each key (`⟦key⟧`), so no assertion depends on a language.
 *
 * The component is loaded once, in a guarded `beforeAll` with its own budget: its first transform pulls the
 * `lucide-svelte` barrel, which is cold and slow under load (the pattern of `GapFixStep.test.ts`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import type SupportActionsComponent from './SupportActions.svelte';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, render, screen} from '$test/component';
import {BUY_ME_A_COFFEE_URL, SOCIAL_SHARE_ORDER} from './supportLinks';

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

// Keys, not prose: the component renders `⟦key⟧`, the same in every language.
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const marked = readable((key: string) => `⟦${key}⟧`);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: marked, t: marked};
});

const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
const MANAGED: InstanceConfig = {...SELFHOSTED, profile: 'managed'};

/** The test id the coffee carries: the default, and the donation popup's own. */
const COFFEE_IDS: Array<{label: string; coffeeTestId: string | undefined; id: string}> = [
    {label: 'the default test id', coffeeTestId: undefined, id: 'support-coffee'},
    {label: 'the donation popup’s test id', coffeeTestId: 'donation-popup-donate', id: 'donation-popup-donate'},
];

// ---------------------------------------------------------------------------
// Loading the component under test
// ---------------------------------------------------------------------------

const COMPONENT_MODULES = import.meta.glob<{default: typeof SupportActionsComponent}>('./SupportActions.svelte');

/** What the loading hook found: the component, or why it could not be loaded. */
let loaded: {SupportActions: typeof SupportActionsComponent} | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = COMPONENT_MODULES['./SupportActions.svelte'];
        if (!load) throw new Error('SupportActions.svelte cannot be found next to this test');
        loaded = {SupportActions: (await load()).default};
    } catch (error) {
        loaded = {error};
    }
}, 120_000);

function component(): typeof SupportActionsComponent {
    if (loaded === undefined) throw new Error('the component under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.SupportActions;
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

function mount(coffeeTestId?: string): void {
    render(component(), {props: {onShare: () => {}, ...(coffeeTestId === undefined ? {} : {coffeeTestId})}});
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

/** The barrier of every absence below: the component is drawn, every share button on view (D-A8). */
function expectShareButtonsOnView(): void {
    expect(screen.getByTestId('support-actions'), 'premise: the component is drawn').toBeInTheDocument();
    for (const platform of SOCIAL_SHARE_ORDER) {
        expect(screen.getByTestId(`support-share-${platform}`), `the ${platform} share button stays (D-A8)`).toBeVisible();
    }
}

function expectNoCoffee(id: string): void {
    expect(screen.queryByTestId(id), `no coffee under ${id}`).toBeNull();
    expect(donationLinks(screen.getByTestId('support-actions')), 'no link to the donation page, under any test id').toEqual([]);
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

describe('SupportActions — the coffee only on a self-hosted instance that has answered (F05)', () => {
    it.each(COFFEE_IDS)('SAM-01: answered self-hosted — the coffee under $label, on the donation page (positive control)', async ({coffeeTestId, id}) => {
        await serverAnswers(SELFHOSTED);

        mount(coffeeTestId);

        const coffee = screen.getByTestId(id);
        expect(coffee).toHaveAttribute('href', BUY_ME_A_COFFEE_URL);
        const scanned = donationLinks(screen.getByTestId('support-actions'));
        expect(scanned, 'the scan finds the coffee: it can see one').toHaveLength(1);
        expect(scanned[0]).toBe(coffee);
        expectShareButtonsOnView();
    });

    // red until A9
    it.each(COFFEE_IDS)('SAM-02: before the answer — no coffee under $label, every share button there', ({coffeeTestId, id}) => {
        mount(coffeeTestId);

        expectShareButtonsOnView();
        expectNoCoffee(id);
    });

    // red until A9
    it.each(COFFEE_IDS)('SAM-03: answered managed — no coffee under $label, every share button there (D-A8)', async ({coffeeTestId, id}) => {
        await serverAnswers(MANAGED);

        mount(coffeeTestId);

        expectShareButtonsOnView();
        expectNoCoffee(id);
    });
});

describe('SupportActions — drawn before the answer, it follows it in place', () => {
    // red until A9
    it('SAM-04: the coffee appears once the answer says self-hosted; the share buttons were there all along', async () => {
        mount();
        expectShareButtonsOnView();
        expectNoCoffee('support-coffee');

        await serverAnswers(SELFHOSTED);

        expect(screen.getByTestId('support-coffee'), 'the answer said self-hosted').toHaveAttribute('href', BUY_ME_A_COFFEE_URL);
        expectShareButtonsOnView();
    });

    // red until A9
    it('SAM-05: an answer that says managed never shows the coffee', async () => {
        mount();
        expectShareButtonsOnView();
        expectNoCoffee('support-coffee');

        await serverAnswers(MANAGED);

        expectShareButtonsOnView();
        expectNoCoffee('support-coffee');
    });
});
