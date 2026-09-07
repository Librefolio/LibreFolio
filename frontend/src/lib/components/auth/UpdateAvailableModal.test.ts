// @vitest-environment jsdom
/**
 * UpdateAvailableModal — light render test (Vitest + jsdom), F14/F12 batch.
 *
 * The modal is driven by the module-level `updateAvailable` store: it is only
 * mounted at all while `updateAvailable.release` is set. Locked here: showing
 * a release renders the modal with the release link pointing at the probed
 * URL; "later" hides without forgetting; "skip" persists the dismissal via
 * `dismissVersion` (asserted through `readCache`, the public read seam — never
 * through a storage key string re-typed here).
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (k: string) => storage.get(k) ?? null,
    setItem: (k: string, v: string) => void storage.set(k, v),
    removeItem: (k: string) => void storage.delete(k),
});

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import UpdateAvailableModal from './UpdateAvailableModal.svelte';
import {updateAvailable} from '$lib/features/update-check/updateCheckStore.svelte';
import {readCache} from '$lib/features/update-check/updateCheck';

const RELEASE = {version: '9.9.9', url: 'https://example.com/release-9.9.9', name: 'Test release'};

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    storage.clear();
    updateAvailable.close();
});

describe('UpdateAvailableModal (F14)', () => {
    it('is absent with no release and renders when one is shown', async () => {
        render(UpdateAvailableModal, {currentVersion: '1.0.0'});

        expect(screen.queryByTestId('update-available-modal')).not.toBeInTheDocument();

        updateAvailable.show(RELEASE);

        await waitFor(() => expect(screen.getByTestId('update-available-modal')).toBeInTheDocument());
        expect(screen.getByTestId('update-available-message')).toBeInTheDocument();
        expect(screen.getByTestId('update-available-release')).toHaveAttribute('href', RELEASE.url);
        expect(screen.getByTestId('update-available-release')).toHaveAttribute('target', '_blank');
        // Locale-prefixed updating guide, deep-linked to the {#updating} anchor
        // (added to all four locales' installation pages for exactly this).
        expect(screen.getByTestId('update-available-guide').getAttribute('href')).toMatch(/^\/mkdocs\/([a-z]{2}\/)?user\/installation\/#updating$/);
    });

    it('"later" hides the modal without dismissing the version', async () => {
        render(UpdateAvailableModal, {currentVersion: '1.0.0'});
        updateAvailable.show(RELEASE);
        await waitFor(() => expect(screen.getByTestId('update-available-modal')).toBeInTheDocument());

        await fireEvent.click(screen.getByTestId('update-available-later'));

        await waitFor(() => expect(screen.queryByTestId('update-available-modal')).not.toBeInTheDocument());
        expect(readCache()?.dismissedVersion ?? null).toBeNull();
    });

    it('"skip" persists the dismissal for the shown version', async () => {
        render(UpdateAvailableModal, {currentVersion: '1.0.0'});
        updateAvailable.show(RELEASE);
        await waitFor(() => expect(screen.getByTestId('update-available-modal')).toBeInTheDocument());

        await fireEvent.click(screen.getByTestId('update-available-skip'));

        await waitFor(() => expect(screen.queryByTestId('update-available-modal')).not.toBeInTheDocument());
        expect(readCache()?.dismissedVersion).toBe('9.9.9');
    });
});
