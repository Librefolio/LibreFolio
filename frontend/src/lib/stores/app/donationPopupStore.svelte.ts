/**
 * Donation Popup Store (Svelte 5 Runes)
 *
 * Holds the transient "show the support/donation popup" signal. Set once right after a
 * successful login when the backend's AuthLoginResponse.show_donation_popup is true (see
 * $lib/stores/app/auth.ts). Ephemeral by design — not persisted, not re-shown on reload.
 *
 * Usage:
 *   import { donationPopup } from '$lib/stores/app/donationPopupStore.svelte';
 *   donationPopup.trigger();   // called from auth.ts after login
 *   donationPopup.dismiss();   // called by DonationPopupModal on either button
 *   donationPopup.forceShow(); // debug-only override, see window.librefolioDebug
 */

let shouldShow = $state(false);

function trigger() {
    shouldShow = true;
}

function dismiss() {
    shouldShow = false;
}

export const donationPopup = {
    get shouldShow() {
        return shouldShow;
    },

    trigger,
    dismiss,

    /** Debug-only: force the popup open without a real login (see (app)/+layout.svelte). */
    forceShow: trigger,
};
