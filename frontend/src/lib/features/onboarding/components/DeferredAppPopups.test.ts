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
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';

const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
});

import {render, screen, setupI18n, waitFor} from '$test/component';
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
