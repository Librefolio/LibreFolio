// @vitest-environment jsdom
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import DonationPopupModal from './DonationPopupModal.svelte';
import {donationPopup} from '$lib/stores/app/donationPopupStore.svelte';

const DONATION_URL = 'https://www.buymeacoffee.com/librefolio';

function popup(): HTMLElement | null {
    return screen.queryByTestId('donation-popup-modal');
}

function shareModal(): HTMLElement | null {
    return screen.queryByTestId('support-social-share-modal');
}

async function openPopup(): Promise<HTMLElement> {
    render(DonationPopupModal);
    donationPopup.trigger();
    await waitFor(() => expect(popup()).not.toBeNull());
    return popup()!;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(
        () =>
            [
                {
                    x: 0,
                    y: 0,
                    width: 1,
                    height: 1,
                    top: 0,
                    right: 1,
                    bottom: 1,
                    left: 0,
                },
            ] as unknown as DOMRectList,
    );
});

afterEach(() => {
    donationPopup.dismiss();
    vi.restoreAllMocks();
    cleanup();
});

describe('DonationPopupModal — when it appears', () => {
    it('stays out of the way until login says to show it', () => {
        render(DonationPopupModal);

        expect(popup()).toBeNull();
    });

    it('appears when the store is triggered', async () => {
        await openPopup();

        expect(popup()).toBeInTheDocument();
    });

    it('appears for the debug override too, which is the same door', async () => {
        render(DonationPopupModal);
        donationPopup.forceShow();

        await waitFor(() => expect(popup()).not.toBeNull());
    });
});

describe('DonationPopupModal — the original two dismissal hooks', () => {
    it('keeps the later button, the donate link and the support card test handles', async () => {
        const dialog = await openPopup();

        expect(within(dialog).getByTestId('donation-popup-later')).toBeInTheDocument();
        expect(within(dialog).getByTestId('donation-popup-donate')).toBeInTheDocument();
        expect(within(dialog).getByTestId('donation-popup-support-card')).toBeInTheDocument();
    });

    it('closes on "later"', async () => {
        const dialog = await openPopup();

        await fireEvent.click(within(dialog).getByTestId('donation-popup-later'));

        await waitFor(() => expect(popup()).toBeNull());
        expect(donationPopup.shouldShow).toBe(false);
    });

    it('closes on "donate" as well, so the user does not come back to it', async () => {
        const dialog = await openPopup();

        await fireEvent.click(within(dialog).getByTestId('donation-popup-donate'));

        await waitFor(() => expect(popup()).toBeNull());
        expect(donationPopup.shouldShow).toBe(false);
    });
});

describe('DonationPopupModal — the escape hatches that were removed on purpose', () => {
    it('ignores Escape', async () => {
        const dialog = await openPopup();

        await fireEvent.keyDown(dialog, {key: 'Escape'});

        expect(popup()).toBeInTheDocument();
        expect(donationPopup.shouldShow).toBe(true);
    });

    it('ignores a click on the backdrop', async () => {
        const dialog = await openPopup();

        await fireEvent.mouseDown(dialog);
        await fireEvent.click(dialog);

        expect(popup()).toBeInTheDocument();
        expect(donationPopup.shouldShow).toBe(true);
    });
});

describe('DonationPopupModal — support actions', () => {
    it('keeps the donation link on the project page and opens it in an isolated new tab', async () => {
        const donate = within(await openPopup()).getByTestId('donation-popup-donate');

        expect(donate).toHaveAttribute('href', DONATION_URL);
        expect(donate).toHaveAttribute('target', '_blank');
        expect(donate.getAttribute('rel')).toContain('noopener');
        expect(donate.getAttribute('rel')).toContain('noreferrer');
    });

    it('uses the unified share buttons and opens the nested share modal without dismissing the popup', async () => {
        const dialog = await openPopup();

        expect(within(dialog).queryByTestId('support-share-x-manual')).toBeNull();
        expect(within(dialog).queryByTestId('support-share-reddit-direct')).toBeNull();

        await fireEvent.click(within(dialog).getByTestId('support-share-reddit'));

        await waitFor(() => expect(shareModal()).not.toBeNull());
        expect(shareModal()?.querySelector('[data-social-icon="reddit"]')).not.toBeNull();
        expect(popup()).toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('support-social-share-close'));

        await waitFor(() => expect(shareModal()).toBeNull());
        expect(popup()).toBeInTheDocument();
        expect(donationPopup.shouldShow).toBe(true);
    });

    it('drops an open share overlay when the store dismisses the popup, and keeps it closed on the next popup', async () => {
        const dialog = await openPopup();

        await fireEvent.click(within(dialog).getByTestId('support-share-x'));
        await waitFor(() => expect(shareModal()).not.toBeNull());

        donationPopup.dismiss();

        await waitFor(() => expect(popup()).toBeNull());
        expect(shareModal()).toBeNull();

        donationPopup.trigger();
        await waitFor(() => expect(popup()).not.toBeNull());
        expect(shareModal()).toBeNull();
    });
});
