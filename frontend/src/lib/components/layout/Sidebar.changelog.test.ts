// @vitest-environment jsdom
/**
 * Sidebar — the app's one changelog window (lot A-CL1; the developer's decision: «one window, two entry points»).
 *
 * The contract under test (approved by the coordinator):
 *   - the Sidebar mounts the only `ChangelogModal` of the app (`currentVersion={APP_VERSION}`, outside `<nav>`), bound
 *     to the shared state of `changelogModalStore.svelte.ts`: the window is open exactly while `changelogModal.open` is;
 *   - every entry point opens that window through `changelogModal.show()`: the sidebar's version (`sidebar-version`)
 *     and the version in Settings → About (`about-version`, pinned in `AboutTab.test.ts`), which this file stands for
 *     by calling `show()` itself;
 *   - closing the window (its `onClose`: Escape, a click outside) closes the shared state;
 *   - the Sidebar closes the shared state when it unmounts: the window lives as long as the app shell, as the Sidebar's
 *     local state did, so it never reopens by itself after a new login.
 * Why: the About tab mounted a second window of its own, which could stay «loading» for good. The other half of the
 * lot, the modal's stale read of the translation cache, is pinned in `ChangelogModal.test.ts` (M1, M2).
 *
 * The setup follows `Sidebar.legal.test.ts`, with one difference: the `ChangelogModal` here is the REAL one, since the
 * window the Sidebar draws is the subject. Only the changelog feature module it imports is stubbed, as `AboutTab.test.ts`
 * does: jsdom denies its `?raw` import of the repo-root CHANGELOG.md, and English with an empty changelog is enough, as
 * no case reads a chapter. `ConnectionSecurityIndicator` is a no-op component (it reads the connection store and has
 * its own test). `$app/stores` and `$app/environment` are the aliases of `vitest.config.ts` (a fixed root page, not a
 * browser). `$lib/i18n` answers `⟦<key>⟧`. The shared state is the real store: every case checks that it starts closed,
 * and the `afterEach` closes it. The generated alias of `GET /system/instance` is spied and refuses, so no case reaches
 * a network.
 *
 * Written red-first, before the Sidebar reads the shared state. The sidebar is imported once, in a `beforeAll` with a
 * long budget: its first `lucide-svelte` import may take ~27 s under load.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const i18n = vi.hoisted(() => ({mark: (key: string): string => `⟦${key}⟧`}));

vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const translator = readable(i18n.mark);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator};
});
// Every export the real modal imports — a vitest mock throws on any export it lacks.
vi.mock('$lib/features/changelog/changelog', () => ({
    changelogChapters: [],
    baseLanguage: () => 'en',
    localizedChangelog: {peek: () => [], load: () => Promise.resolve([])},
    CHANGELOG_REMOTE_URL: 'https://example.invalid/CHANGELOG.md',
}));
vi.mock('$lib/components/layout/ConnectionSecurityIndicator.svelte', () => ({default: () => {}}));

import {zodiosApi} from '$lib/api';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {changelogModal} from '$lib/features/changelog/changelogModalStore.svelte';

let Sidebar: typeof import('./Sidebar.svelte').default;

// --- Fixtures -------------------------------------------------------------

const INSTANCE_ALIAS = 'get_instance_config_api_v1_system_instance_get';
/** The generated client seen through that one alias: spying through the full client type sends TS into an excessively deep instantiation. */
const instanceEndpoint = zodiosApi as unknown as Record<typeof INSTANCE_ALIAS, () => Promise<InstanceConfig>>;

/** Draw the expanded sidebar, whose footer holds `sidebar-version`. */
function mountSidebar() {
    const view = render(Sidebar, {props: {collapsed: false, isOpen: false}});
    // Presence barrier: the sidebar is drawn, its version included, before any absence below is read.
    expect(screen.getByTestId('sidebar-version'), 'the expanded sidebar draws its version').toBeInTheDocument();
    return view;
}

/** The changelog window on screen, or null. */
function changelogWindow(): HTMLElement | null {
    return screen.queryByTestId('changelog-modal');
}

/** What the About tab's version does: open the app's window through the shared state. */
function showFromAnotherEntryPoint(): void {
    changelogModal.show();
    flushSync();
}

// --- Lifecycle --------------------------------------------------------------

beforeAll(async () => {
    // The waits below for the window to follow the shared state mean nothing where effects never run.
    assertEffectsRun();
    Sidebar = (await import('./Sidebar.svelte')).default;
}, 180_000);

beforeEach(() => {
    vi.spyOn(instanceEndpoint, INSTANCE_ALIAS).mockRejectedValue(new Error('no network in this test'));
    expect(changelogModal.open, 'precondition: the shared changelog window starts closed').toBe(false);
});

afterEach(() => {
    cleanup();
    changelogModal.close();
    vi.restoreAllMocks();
});

// =========================================================================
describe("the Sidebar mounts the app's one changelog window, bound to the shared state", () => {
    // red until A-CL1
    it("an entry point outside the sidebar opens the sidebar's window", async () => {
        mountSidebar();
        expect(changelogWindow(), 'no window while the shared state is closed').toBeNull();

        showFromAnotherEntryPoint();

        await waitFor(() => expect(changelogWindow(), 'changelogModal.show() opens the window the sidebar mounts').not.toBeNull(), {timeout: 1_000});
        // Outside <nav> (F12 round 2): the drawer's transform and overflow would trap the window's fixed position.
        expect(changelogWindow()?.closest('nav'), 'the window is drawn outside the <nav> drawer').toBeNull();
    });

    // red until A-CL1
    it("the sidebar's version opens the same window and the shared state", async () => {
        mountSidebar();
        expect(changelogWindow(), 'no window before the click').toBeNull();

        await fireEvent.click(screen.getByTestId('sidebar-version'));

        await waitFor(() => expect(changelogWindow(), "the sidebar's version opens the window").not.toBeNull(), {timeout: 1_000});
        expect(screen.queryAllByTestId('changelog-modal'), 'one window: the app has no other').toHaveLength(1);
        expect(changelogModal.open, "the sidebar's version opens it through the shared state").toBe(true);
    });

    // red until A-CL1
    it('closing the window closes the shared state', async () => {
        mountSidebar();
        showFromAnotherEntryPoint();
        await waitFor(() => expect(changelogWindow(), 'precondition: changelogModal.show() opens the window').not.toBeNull(), {timeout: 1_000});

        // Escape on the dialog: ModalBase asks the window to close, through its onClose.
        await fireEvent.keyDown(screen.getByTestId('changelog-modal'), {key: 'Escape'});

        await waitFor(() => expect(changelogWindow(), 'Escape closes the window').toBeNull(), {timeout: 1_000});
        expect(changelogModal.open, 'closing the window closes the shared state').toBe(false);
    });

    // red until A-CL1
    it('the window does not outlive the sidebar', async () => {
        const view = mountSidebar();
        // The window is open when the sidebar goes; that it is drawn is the first case's subject, not this one's.
        showFromAnotherEntryPoint();
        expect(changelogModal.open, 'precondition: the shared state is open').toBe(true);

        view.unmount();

        await waitFor(() => expect(changelogModal.open, 'unmounting the sidebar closes the shared state: the window lives as long as the app shell').toBe(false), {timeout: 1_000});
    });
});
