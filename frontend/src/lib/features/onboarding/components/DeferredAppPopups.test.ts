// @vitest-environment jsdom
/**
 * DeferredAppPopups — automatic versus requested update prompts (Vitest + jsdom), R3.
 *
 * DeferredAppPopups arbitrates the popups nobody asked for — the donation popup and an update
 * found automatically — and holds them while a modal is open (`data-modal-scroll-lock-count` on
 * `<body>`, the counter every ModalBase maintains) or while the onboarding guide runs. The
 * admin's manual update check, though, runs from inside the changelog modal, so its answer was
 * held too and appeared only once the changelog closed, which read as a modal opening
 * underneath. `updateAvailable.show(release, {requested: true})` now marks a prompt as asked
 * for, and the arbiter shows a requested prompt at once, whatever the modal depth or the guide.
 *
 * Locked here:
 *   - automatic: held at depth 1, shown when the depth returns to 0; held while the guide is
 *     active, shown when it ends;
 *   - requested: shown at once at depth 1, and at once while the guide is active;
 *   - `updateAvailable.close()` after a requested prompt returns the arbiter to `none` and
 *     clears `requested`, so a later automatic prompt is held again.
 * The older priority cases — donation first, and a popup's own ModalBase lock not closing it —
 * are the "DeferredAppPopups — priority arbiter" block of OnboardingCoachmark.test.ts.
 *
 * Depth is simulated, not produced: the test writes the body counter itself, as an open
 * modal's ModalBase would, and the component reads it through its MutationObserver. The shared
 * `$app/environment` mock reports `browser: false`, so the update modal's own ModalBase locks
 * nothing here and the counter holds exactly what the test wrote. Every "held" assertion is
 * preceded by a barrier on `data-modal-depth`: a held prompt must not be confused with a depth
 * the component has not read yet. Every "held" case also ends by releasing the hold and seeing
 * the same prompt appear, so a `none` cannot mean the prompt was never armed.
 *
 * `donationPopup` is driven through its real store and kept dismissed, with a control that it
 * is, so no `none` or `update` below is a donation popup contending for the slot.
 *
 * Assertions read the component's own `data-active-popup` / `data-modal-depth` attributes and
 * the modal's `data-testid` (`update-available-modal`); nothing reads translated text.
 * `localStorage` is stubbed because UpdateAvailableModal reads the locale from it while
 * rendering its guide link.
 *
 * C-54 adds a third automatic popup, «What's new since your last version» (`'whats-new'`,
 * `WhatsNewModal`), first among the automatic ones — the block at the end of this file. Its store,
 * `$lib/features/changelog/whatsNewStore.svelte`, is mocked: a test-owned reactive state the cases
 * arm and `whatsNew.dismiss()` disarms, the seam the donation store offers with `trigger()` and
 * `dismiss()` (the store's own rule is whatsNewStore.test.ts's subject). The changelog module is a
 * fixture, as in every jsdom test of the changelog: its `?raw` import of the repository's
 * CHANGELOG.md is refused by the jsdom pipeline. Both mocks are inert for the R3 cases above —
 * nothing arms what's new there, and the fake starts disarmed.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';

const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
});

/** C-54: the what's-new store's stand-in. `state` exists once something imports the store — the arbiter, or its modal. */
const whatsNewFake = vi.hoisted(() => {
    const fake = {
        /** The reactive state the mocked store reads (a `reactiveBox`, so the arbiter's `$effect` follows it). */
        state: null as {pending: boolean} | null,
        /** `whatsNew.dismiss()`: closes it at once, as the real store does. */
        dismiss: vi.fn(() => {
            if (fake.state) fake.state.pending = false;
        }),
    };
    return fake;
});

/** C-54: the bundled changelog the real WhatsNewModal reads — English, newest first. */
const whatsNewChangelog = vi.hoisted(() => {
    const chapter = (version: string, date: string) => {
        const body = `- what changed in ${version}\n`;
        return {version, date, body, sections: [{title: null, body, subsections: []}]};
    };
    const chapters = [chapter('Unreleased', ''), chapter('1.2.1', '2026-10-15'), chapter('1.2.0', '2026-10-14')];
    return {chapters, shown: chapters.map((c) => ({...c, lang: 'en'})), pending: chapters.slice(1, 2)};
});

vi.mock('$lib/features/changelog/changelog', () => ({
    changelogChapters: whatsNewChangelog.chapters,
    CHANGELOG_REMOTE_URL: 'https://github.com/Librefolio/LibreFolio/blob/main/CHANGELOG.md',
    baseLanguage: (locale: string | null | undefined) => (locale ?? '').trim().toLowerCase().split(/[-_]/)[0] || 'en',
    localizedChangelog: {peek: () => whatsNewChangelog.shown, load: async () => whatsNewChangelog.shown},
}));

vi.mock('$lib/features/changelog/whatsNewStore.svelte', async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const state = reactiveBox({pending: false});
    whatsNewFake.state = state;
    return {
        whatsNew: {
            get shouldShow() {
                return state.pending;
            },
            get chapters() {
                return state.pending ? whatsNewChangelog.pending : [];
            },
            dismiss: whatsNewFake.dismiss,
        },
    };
});

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {updateAvailable} from '$lib/features/update-check/updateCheckStore.svelte';
import {donationPopup} from '$lib/stores/app/donationPopupStore.svelte';
import DeferredAppPopups from './DeferredAppPopups.svelte';

const RELEASE = {version: '9.9.9', tag: 'v9.9.9', url: 'https://example.com/release-9.9.9', name: 'Test release'};
const CURRENT_VERSION = '1.0.0';

const host = () => screen.getByTestId('deferred-app-popups');
const updateModal = () => screen.queryByTestId('update-available-modal');

/** Write the body counter the way an opening or closing ModalBase does: removed at zero. */
function setModalDepth(depth: number): void {
    if (depth > 0) document.body.dataset.modalScrollLockCount = String(depth);
    else delete document.body.dataset.modalScrollLockCount;
}

/** Barrier: the component has read the depth the test wrote, through its MutationObserver. */
async function depthRead(depth: number): Promise<void> {
    await waitFor(() => expect(host()).toHaveAttribute('data-modal-depth', String(depth)));
}

/** Flush a store change: synchronously, then through the microtask the app itself waits on. */
async function flush(): Promise<void> {
    flushSync();
    await tick();
}

/** The slot is empty and no update modal is mounted. */
function expectNone(step: string): void {
    expect(host(), `${step} — data-active-popup`).toHaveAttribute('data-active-popup', 'none');
    expect(updateModal(), `${step} — no update modal`).toBeNull();
}

/** The slot holds the update prompt and its modal is mounted. */
function expectUpdate(step: string): void {
    expect(host(), `${step} — data-active-popup`).toHaveAttribute('data-active-popup', 'update');
    expect(updateModal(), `${step} — the update modal`).toBeInTheDocument();
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    storage.clear();
    donationPopup.dismiss();
    setModalDepth(0);
});

afterEach(() => {
    // Module-level stores and a body attribute: all shared by every test in this file.
    updateAvailable.close();
    donationPopup.dismiss();
    setModalDepth(0);
});

describe('DeferredAppPopups — automatic prompts wait, requested prompts do not (R3)', () => {
    it('holds an automatic prompt while a modal is open, and shows it once the depth returns to 0', async () => {
        setModalDepth(1);
        render(DeferredAppPopups, {currentVersion: CURRENT_VERSION});
        await depthRead(1);

        updateAvailable.show(RELEASE);
        await flush();
        // Controls: an automatic prompt is armed, and the donation popup is not contending.
        expect(updateAvailable.release).toEqual(RELEASE);
        expect(updateAvailable.requested).toBe(false);
        expect(donationPopup.shouldShow).toBe(false);
        expect(host()).toHaveAttribute('data-modal-depth', '1');
        expectNone('depth 1');

        setModalDepth(0);
        await depthRead(0);
        await waitFor(() => expect(host()).toHaveAttribute('data-active-popup', 'update'));
        expectUpdate('depth back to 0');
    });

    it('holds an automatic prompt while the guide is active, and shows it once the guide ends', async () => {
        const {rerender} = render(DeferredAppPopups, {guideActive: true, currentVersion: CURRENT_VERSION});
        await depthRead(0);

        updateAvailable.show(RELEASE);
        await flush();
        expect(updateAvailable.release).toEqual(RELEASE);
        expect(updateAvailable.requested).toBe(false);
        expect(donationPopup.shouldShow).toBe(false);
        expectNone('guide active');

        // The same armed prompt appears as soon as the guide ends: the `none` above was the guide.
        rerender({guideActive: false});
        await waitFor(() => expect(host()).toHaveAttribute('data-active-popup', 'update'));
        expectUpdate('guide ended');
    });

    it('shows a requested prompt at once while a modal is open', async () => {
        setModalDepth(1);
        render(DeferredAppPopups, {currentVersion: CURRENT_VERSION});
        await depthRead(1);

        updateAvailable.show(RELEASE, {requested: true});
        await flush();

        expect(updateAvailable.requested, 'control: the prompt is requested').toBe(true);
        expect(donationPopup.shouldShow).toBe(false);
        // At once: one flush, no retry, and the modal that asked is still open underneath.
        expect(host()).toHaveAttribute('data-modal-depth', '1');
        expectUpdate('requested at depth 1');
    });

    it('shows a requested prompt at once while the guide is active', async () => {
        render(DeferredAppPopups, {guideActive: true, currentVersion: CURRENT_VERSION});
        await depthRead(0);

        updateAvailable.show(RELEASE, {requested: true});
        await flush();

        expect(updateAvailable.requested, 'control: the prompt is requested').toBe(true);
        expect(donationPopup.shouldShow).toBe(false);
        expectUpdate('requested with the guide active');
    });

    it('returns to none and clears requested when a requested prompt is closed, so the next automatic one is held again', async () => {
        setModalDepth(1);
        render(DeferredAppPopups, {currentVersion: CURRENT_VERSION});
        await depthRead(1);
        updateAvailable.show(RELEASE, {requested: true});
        await flush();
        expectUpdate('precondition: requested at depth 1');

        updateAvailable.close();
        await flush();
        expect(updateAvailable.release).toBeNull();
        expect(updateAvailable.requested).toBe(false);
        expect(host()).toHaveAttribute('data-active-popup', 'none');
        await waitFor(() => expect(updateModal()).toBeNull());

        // `requested` did not stick: the modal is still open, so an automatic prompt waits again…
        updateAvailable.show(RELEASE);
        await flush();
        expect(updateAvailable.requested).toBe(false);
        expectNone('automatic after the close, depth still 1');

        // …and is shown when that modal closes.
        setModalDepth(0);
        await depthRead(0);
        await waitFor(() => expect(host()).toHaveAttribute('data-active-popup', 'update'));
        expectUpdate('depth back to 0');
    });
});

/**
 * C-54 — «What's new since your last version» (`data-active-popup="whats-new"`, `WhatsNewModal`), the first of the
 * automatic popups. Locked here:
 *   - DAP-WN-01: with the donation and an automatic update also pending, what's new shows first; once it is dismissed,
 *     the donation; once that is dismissed, the update — one popup at a time, at every step;
 *   - DAP-WN-02: it waits while the guide is active, and shows once the guide ends;
 *   - DAP-WN-03: it waits while a modal is open, and shows once the depth returns to 0;
 *   - DAP-WN-04: closed from its own modal (`whats-new-close`), `whatsNew.dismiss()` runs once and the next pending
 *     popup shows;
 *   - DAP-WN-05: a requested update still goes on top at once; what's new is interrupted, not dismissed, and comes back
 *     once the update prompt closes.
 * The real WhatsNewModal is mounted, over the mocked store and the fixture changelog, as the two other popups are mounted
 * for real. Every case arms what's new before the arbiter decides, with the same controls as the cases above; "held"
 * cases end by releasing the hold and seeing what's new appear, so a `none` cannot mean it was never armed. Assertions
 * read `data-active-popup` and the three modals' test ids — never two of them at once.
 */
describe("DeferredAppPopups — what's new since the last version, first of the automatic popups (C-54)", () => {
    const whatsNewModal = () => screen.queryByTestId('whats-new-modal');
    const donationModal = () => screen.queryByTestId('donation-popup-modal');

    /** Arms what's new, as a signed-in payload with chapters to show does. Fails, naming the gap, while nothing imports the store. */
    function armWhatsNew(): void {
        if (!whatsNewFake.state) throw new Error("nothing imports $lib/features/changelog/whatsNewStore.svelte: DeferredAppPopups has no 'whats-new' popup yet (C-54)");
        whatsNewFake.state.pending = true;
    }

    const whatsNewPending = () => whatsNewFake.state?.pending === true;

    /** The slot holds `kind`, and only its modal is mounted. */
    function expectOnly(kind: 'whats-new' | 'donation' | 'update', step: string): void {
        expect(host(), `${step} — data-active-popup`).toHaveAttribute('data-active-popup', kind);
        expect(whatsNewModal() !== null, `${step} — the what's-new modal mounted`).toBe(kind === 'whats-new');
        expect(donationModal() !== null, `${step} — the donation modal mounted`).toBe(kind === 'donation');
        expect(updateModal() !== null, `${step} — the update modal mounted`).toBe(kind === 'update');
    }

    /** The slot is empty and none of the three modals is mounted. */
    function expectNoPopup(step: string): void {
        expectNone(step);
        expect(whatsNewModal(), `${step} — no what's-new modal`).toBeNull();
        expect(donationModal(), `${step} — no donation modal`).toBeNull();
    }

    beforeEach(() => {
        if (whatsNewFake.state) whatsNewFake.state.pending = false;
        whatsNewFake.dismiss.mockClear();
    });

    afterEach(() => {
        // A module-level state, shared by every case of this file.
        if (whatsNewFake.state) whatsNewFake.state.pending = false;
        flushSync();
    });

    it("DAP-WN-01: with the donation and an automatic update also pending, what's new shows first — then the donation, then the update, one at a time", async () => {
        updateAvailable.show(RELEASE);
        donationPopup.trigger();
        armWhatsNew();
        // Controls: all three are pending before the arbiter decides, and the update is an automatic one.
        expect(whatsNewPending()).toBe(true);
        expect(donationPopup.shouldShow).toBe(true);
        expect(updateAvailable.release).toEqual(RELEASE);
        expect(updateAvailable.requested).toBe(false);

        render(DeferredAppPopups, {currentVersion: CURRENT_VERSION});
        await depthRead(0);
        await waitFor(() => expectOnly('whats-new', 'all three pending'));

        whatsNewFake.dismiss();
        await flush();
        await waitFor(() => expectOnly('donation', "what's new dismissed"));

        donationPopup.dismiss();
        await flush();
        await waitFor(() => expectOnly('update', 'the donation dismissed'));
    });

    it('DAP-WN-02: waits while the guide is active, and shows once the guide ends', async () => {
        armWhatsNew();
        const {rerender} = render(DeferredAppPopups, {guideActive: true, currentVersion: CURRENT_VERSION});
        await depthRead(0);
        await flush();
        expect(whatsNewPending(), "control: what's new is pending").toBe(true);
        expect(donationPopup.shouldShow).toBe(false);
        expectNoPopup('guide active');

        // The same armed popup appears as soon as the guide ends: the `none` above was the guide.
        rerender({guideActive: false});
        await waitFor(() => expectOnly('whats-new', 'guide ended'));
    });

    it('DAP-WN-03: waits while a modal is open, and shows once the depth returns to 0', async () => {
        setModalDepth(1);
        armWhatsNew();
        render(DeferredAppPopups, {currentVersion: CURRENT_VERSION});
        await depthRead(1);
        await flush();
        expect(whatsNewPending(), "control: what's new is pending").toBe(true);
        expect(donationPopup.shouldShow).toBe(false);
        expect(host()).toHaveAttribute('data-modal-depth', '1');
        expectNoPopup('depth 1');

        setModalDepth(0);
        await depthRead(0);
        await waitFor(() => expectOnly('whats-new', 'depth back to 0'));
    });

    it('DAP-WN-04: closed from its own modal, it is dismissed once and the next pending popup shows', async () => {
        updateAvailable.show(RELEASE);
        armWhatsNew();
        render(DeferredAppPopups, {currentVersion: CURRENT_VERSION});
        await waitFor(() => expectOnly('whats-new', 'an automatic update also pending'));

        await fireEvent.click(screen.getByTestId('whats-new-close'));

        expect(whatsNewFake.dismiss, 'the close dismissed it').toHaveBeenCalledTimes(1);
        await waitFor(() => expectOnly('update', "what's new closed"));
        expect(whatsNewFake.dismiss, 'once').toHaveBeenCalledTimes(1);
    });

    it("DAP-WN-05: a requested update still goes on top at once; what's new is interrupted, not dismissed, and comes back after it", async () => {
        armWhatsNew();
        render(DeferredAppPopups, {currentVersion: CURRENT_VERSION});
        await waitFor(() => expectOnly('whats-new', 'shown'));

        updateAvailable.show(RELEASE, {requested: true});
        await flush();

        // At once: one flush, no retry.
        expect(updateAvailable.requested, 'control: the prompt is requested').toBe(true);
        expectOnly('update', "requested, over what's new");
        expect(whatsNewFake.dismiss, 'interrupted, not dismissed').not.toHaveBeenCalled();
        expect(whatsNewPending(), 'still pending').toBe(true);

        updateAvailable.close();
        await flush();
        await waitFor(() => expectOnly('whats-new', 'the requested prompt closed'));
    });
});
