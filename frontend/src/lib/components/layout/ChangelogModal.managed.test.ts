// @vitest-environment jsdom
/**
 * ChangelogModal on a managed instance (F05, lot A9 of workstream A): the manual update check of the changelog modal
 * (`changelog-check-update`) is absent when the instance is managed — for an admin as for a user: a managed instance
 * is updated by its hoster (the coordinator's decision of 17/10, 07:05: «nel profilo gestito sparisce anche
 * "controlla aggiornamenti" del ChangelogModal») —, and follows the donations' rule (`donationsVisible()`, decision of
 * 17/10, 10:03): present only once the server has answered (`instanceConfig.loaded`) and said self-hosted. Before any
 * answer, and after a request that failed before any answer, the store holds its self-hosted defaults: a managed
 * instance must show no button then either, or it would show one until its answer, and for good when the request fails.
 *
 * The contract under test:
 *   - CLM-01 (positive control, green today): answered self-hosted, the button is in the header of the modal;
 *   - CLM-02: answered managed, no button, for a user and for an admin; the modal and the button's siblings (search,
 *     remote link) are there;
 *   - CLM-03: opened before the answer, the modal follows it in place: once the answer says managed, no button;
 *   - CLM-04 (positive control of the same path, green today): once the answer says self-hosted, the button;
 *   - CLM-05: opened before any answer, no button; the search and the remote link are there;
 *   - CLM-06: the request failed before any answer (`failed`, not `loaded`, the defaults in force): no button.
 * Under this rule the button is absent before the answer too, so CLM-03 pins only where a managed answer leaves the
 * modal: that the modal follows the answer in place is CLM-04's to prove.
 *
 * Mocks, all owned here: `$lib/features/instance/instanceConfig.svelte` is a fake with the real store's shape —
 * enumerable getters over a `$state` box (`reactiveBox`) — so a test lands the server's answer, or the request's
 * failure, by writing the box, as `load()` does; `load` is a spy answering nothing of its own. The changelog module is stubbed with one English
 * chapter (the real one imports the repo-root CHANGELOG.md through `?raw`, which the jsdom pipeline refuses — see
 * `ChangelogModal.test.ts`); `$lib/api` is a proxy refusing every alias (no network); `$lib/stores/app/auth` a store
 * the test sets (a user or an admin); `$lib/i18n`: `_` marks each key (`⟦key⟧`), the rest is the real module.
 *
 * The component is loaded once, in a guarded `beforeAll` with its own budget: its first transform pulls the
 * `lucide-svelte` barrel, which is cold and slow under load (the pattern of `GapFixStep.test.ts`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import type ChangelogModalComponent from './ChangelogModal.svelte';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, render, screen, within} from '$test/component';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const {writable} = await import('svelte/store');
    /** What the real store holds until the server answers: `DEFAULT_INSTANCE_CONFIG`, a self-hosted instance. */
    const BEFORE_ANSWER = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}} as InstanceConfig;
    return {
        BEFORE_ANSWER,
        instance: reactiveBox<{config: InstanceConfig; loaded: boolean; failed: boolean}>({config: BEFORE_ANSWER, loaded: false, failed: false}),
        instanceLoad: vi.fn<(options?: {force?: boolean}) => Promise<void>>().mockName('instanceConfig.load'),
        /** Who is signed in: the modal reads `$auth.user?.is_superuser`. */
        auth: writable<{user: {id: number; username: string; is_superuser: boolean} | null}>({user: null}),
        /** One English chapter, as the modal displays it. */
        chapters: [{version: '1.2.0', date: '2026-08-07', body: 'Intro notes.\n', sections: [{title: null, body: 'Intro notes.\n', subsections: []}], lang: 'en'}],
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

vi.mock('$lib/features/changelog/changelog', () => ({
    changelogChapters: mocks.chapters,
    localizedChangelog: {peek: () => mocks.chapters, load: async () => mocks.chapters},
    baseLanguage: (locale: string | null | undefined) => (locale ?? '').split('-')[0].toLowerCase() || 'en',
    CHANGELOG_REMOTE_URL: 'https://github.com/Librefolio/LibreFolio/blob/main/CHANGELOG.md',
}));

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (typeof property !== 'string' || property === 'then') return undefined;
                return () => Promise.reject(new Error(`no network in this test: ${property}`));
            },
        },
    ),
    ApiError: class ApiError extends Error {},
    axiosInstance: {},
}));

vi.mock('$lib/stores/app/auth', () => ({auth: {subscribe: mocks.auth.subscribe}}));

// Keys, not prose: the modal renders `⟦key⟧`, the same in every language.
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const marked = readable((key: string) => `⟦${key}⟧`);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: marked, t: marked};
});

const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
const MANAGED: InstanceConfig = {...SELFHOSTED, profile: 'managed'};

const WHO: Array<{who: string; user: {id: number; username: string; is_superuser: boolean} | null}> = [
    {who: 'a user', user: {id: 2, username: 'probe-user', is_superuser: false}},
    {who: 'an admin', user: {id: 1, username: 'probe-admin', is_superuser: true}},
];

// ---------------------------------------------------------------------------
// Loading the component under test
// ---------------------------------------------------------------------------

const COMPONENT_MODULES = import.meta.glob<{default: typeof ChangelogModalComponent}>('./ChangelogModal.svelte');

/** What the loading hook found: the component, or why it could not be loaded. */
let loaded: {ChangelogModal: typeof ChangelogModalComponent} | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = COMPONENT_MODULES['./ChangelogModal.svelte'];
        if (!load) throw new Error('ChangelogModal.svelte cannot be found next to this test');
        loaded = {ChangelogModal: (await load()).default};
    } catch (error) {
        loaded = {error};
    }
}, 120_000);

function component(): typeof ChangelogModalComponent {
    if (loaded === undefined) throw new Error('the component under test was never loaded: its beforeAll did not run');
    if ('error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded.ChangelogModal;
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

/** The request fails, as `instanceConfig.load()` lands a failure: `failed`, the configuration in force and `loaded` untouched. */
async function requestFails(): Promise<void> {
    mocks.instance.failed = true;
    flushSync();
    await tick();
}

/** Opens the modal; ends on its header drawn, the search box and the remote link on view. */
async function mountOpen(): Promise<void> {
    render(component(), {props: {open: true, onClose: () => {}}});
    const modal = await screen.findByTestId('changelog-modal');
    expect(within(modal).getByTestId('changelog-search'), 'premise: the header of the modal is drawn').toBeVisible();
    expect(within(modal).getByTestId('changelog-remote-link'), 'premise: a sibling of the button is drawn').toBeVisible();
}

beforeEach(() => {
    mocks.instance.config = mocks.BEFORE_ANSWER;
    mocks.instance.loaded = false;
    mocks.instance.failed = false;
    flushSync();
    mocks.instanceLoad.mockReset();
    mocks.instanceLoad.mockImplementation(() => Promise.resolve());
    mocks.auth.set({user: null});
});

afterEach(() => {
    cleanup();
});

describe('ChangelogModal — the manual update check only on a self-hosted instance (F05)', () => {
    it('CLM-01: answered self-hosted — changelog-check-update in the header of the modal (positive control)', async () => {
        await serverAnswers(SELFHOSTED);

        await mountOpen();

        expect(within(screen.getByTestId('changelog-modal')).getByTestId('changelog-check-update')).toBeVisible();
    });

    // red until A9
    it.each(WHO)('CLM-02: answered managed, $who signed in — no changelog-check-update; the search and the remote link are there', async ({user}) => {
        mocks.auth.set({user});
        await serverAnswers(MANAGED);

        await mountOpen();

        expect(screen.queryByTestId('changelog-check-update')).toBeNull();
    });
});

describe('ChangelogModal — open before the answer, it follows it in place', () => {
    // red until A9
    it('CLM-03: once the answer says managed, no changelog-check-update', async () => {
        await mountOpen();

        await serverAnswers(MANAGED);

        expect(screen.getByTestId('changelog-search'), 'the header is still drawn').toBeVisible();
        expect(screen.queryByTestId('changelog-check-update')).toBeNull();
    });

    it('CLM-04: once the answer says self-hosted, changelog-check-update (positive control)', async () => {
        await mountOpen();

        await serverAnswers(SELFHOSTED);

        expect(within(screen.getByTestId('changelog-modal')).getByTestId('changelog-check-update')).toBeVisible();
    });
});

describe('ChangelogModal — no answer yet, or none coming: no manual update check (the donations’ rule)', () => {
    // red until A9 (changelog gate)
    it('CLM-05: opened before any answer — no changelog-check-update; the search and the remote link are there', async () => {
        await mountOpen();

        expect(screen.queryByTestId('changelog-check-update'), 'before any answer: the defaults say self-hosted, but the server has not said it').toBeNull();
    });

    // red until A9 (changelog gate)
    it('CLM-06: the request failed before any answer — no changelog-check-update', async () => {
        await requestFails();

        await mountOpen();

        expect(screen.queryByTestId('changelog-check-update'), 'the request failed before any answer: the defaults in force are not an answer').toBeNull();
    });
});
