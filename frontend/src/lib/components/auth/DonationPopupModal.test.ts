// @vitest-environment jsdom
/**
 * DonationPopupModal — component test (Vitest + jsdom).
 *
 * This popup is the one place in the app where the usual escape hatches are
 * deliberately removed: no X, no Escape, no backdrop click. Its own header
 * comment says so in five lines, ending "intentional, not a bug" — which is
 * exactly the kind of statement that survives in a comment and dies in a
 * refactor, because every other modal in the codebase behaves the other way and
 * `closeOnEscape` defaults to `true` in `ModalBase`.
 *
 * So this file is not chasing branches: `DonationPopupModal.svelte` has none. It
 * exists to turn that comment into something that fails. Delete
 * `closeOnEscape={false}` and a test goes red naming the rule that was dropped.
 *
 * Visibility is owned by `donationPopup`, a module-level rune store shared by
 * every test in the process, so each test resets it.
 *
 * `$lib/i18n` is mocked with an identity translator: the two labels render as
 * their keys, which are the same in EN/IT/FR/ES, so nothing here asserts a
 * sentence.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));

import DonationPopupModal from './DonationPopupModal.svelte';
import {donationPopup} from '$lib/stores/app/donationPopupStore.svelte';

const DONATION_URL = 'https://www.buymeacoffee.com/librefolio';

function modal(): HTMLElement | null {
    return screen.queryByTestId('donation-popup-modal');
}

/** Mounts the popup already open, the state it spends its whole life in. */
async function open(): Promise<HTMLElement> {
    render(DonationPopupModal);
    donationPopup.trigger();
    await waitFor(() => expect(modal()).not.toBeNull());
    return modal()!;
}

afterEach(() => {
    donationPopup.dismiss();
    cleanup();
});

describe('DonationPopupModal — when it appears', () => {
    it('stays out of the way until login says to show it', () => {
        render(DonationPopupModal);

        expect(modal()).toBeNull();
    });

    it('appears when the store is triggered', async () => {
        await open();

        expect(modal()).toBeInTheDocument();
    });

    it('appears for the debug override too, which is the same door', async () => {
        render(DonationPopupModal);
        donationPopup.forceShow();

        await waitFor(() => expect(modal()).not.toBeNull());
    });
});

describe('DonationPopupModal — the only two ways out', () => {
    it('closes on "later"', async () => {
        const dialog = await open();

        await fireEvent.click(within(dialog).getByTestId('donation-popup-later'));

        await waitFor(() => expect(modal()).toBeNull());
        expect(donationPopup.shouldShow).toBe(false);
    });

    it('closes on "donate" as well, so the user does not come back to it', async () => {
        const dialog = await open();

        await fireEvent.click(within(dialog).getByTestId('donation-popup-donate'));

        await waitFor(() => expect(modal()).toBeNull());
        expect(donationPopup.shouldShow).toBe(false);
    });

    it('offers no third one: one button and one link, and no close control', async () => {
        const dialog = await open();

        const buttons = within(dialog).getAllByRole('button');
        expect(buttons).toHaveLength(1);
        expect(buttons[0]).toHaveAttribute('data-testid', 'donation-popup-later');

        const links = within(dialog).getAllByRole('link');
        expect(links).toHaveLength(1);
        expect(links[0]).toHaveAttribute('data-testid', 'donation-popup-donate');
    });
});

describe('DonationPopupModal — the escape hatches that were removed on purpose', () => {
    it('ignores Escape', async () => {
        const dialog = await open();

        await fireEvent.keyDown(dialog, {key: 'Escape'});

        expect(modal()).toBeInTheDocument();
        expect(donationPopup.shouldShow).toBe(true);
    });

    it('ignores a click on the backdrop', async () => {
        const dialog = await open();

        // The full gesture: ModalBase only treats a click as a backdrop click
        // when the mousedown landed there too.
        await fireEvent.mouseDown(dialog);
        await fireEvent.click(dialog);

        expect(modal()).toBeInTheDocument();
        expect(donationPopup.shouldShow).toBe(true);
    });
});

describe('DonationPopupModal — the donation link', () => {
    it('points at the project donation page', async () => {
        const dialog = await open();

        expect(within(dialog).getByTestId('donation-popup-donate')).toHaveAttribute('href', DONATION_URL);
    });

    it('opens it in a new tab, without handing the app over to it', async () => {
        // `rel="noopener"` is what stops the opened page from reaching back
        // through `window.opener` into a session that has just logged in.
        const donate = within(await open()).getByTestId('donation-popup-donate');

        expect(donate).toHaveAttribute('target', '_blank');
        expect(donate.getAttribute('rel')).toContain('noopener');
        expect(donate.getAttribute('rel')).toContain('noreferrer');
    });
});
