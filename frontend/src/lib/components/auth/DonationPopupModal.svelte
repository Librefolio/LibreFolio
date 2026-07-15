<!--
  DonationPopupModal — "support LibreFolio" popup shown after login.

  Triggered by the backend's AuthLoginResponse.show_donation_popup signal (see
  $lib/stores/app/auth.ts) or, for manual testing, via the debug console command
  registered in routes/(app)/+layout.svelte (window.librefolioDebug.showDonationPopup()).

  Interaction rules (intentional, not a bug):
  - No close ("X") button.
  - Clicking the backdrop does nothing (closeOnBackdropClick={false}).
  - Pressing Escape does nothing (closeOnEscape={false}).
  - The ONLY ways to dismiss it are the two buttons below.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Coffee} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {donationPopup} from '$lib/stores/app/donationPopupStore.svelte';

    const BUY_ME_A_COFFEE_URL = 'https://www.buymeacoffee.com/librefolio';

    function handleLater() {
        donationPopup.dismiss();
    }

    function handleDonateClick() {
        // The <a> handles the navigation (target="_blank"); we just also close the popup.
        donationPopup.dismiss();
    }
</script>

<ModalBase open={donationPopup.shouldShow} closeOnBackdropClick={false} closeOnEscape={false} maxWidth="xl" testId="donation-popup-modal">
    <!-- Header: LibreFolio logo + name, same style as LoginCard.svelte -->
    <div class="bg-libre-green px-6 py-5 flex items-center justify-center gap-3">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center p-1 shrink-0" style="background:#fff">
            <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
        </div>
        <span class="text-xl font-bold tracking-wide text-white">LibreFolio</span>
    </div>

    <!-- Body -->
    <div class="px-6 py-6 flex flex-col items-center text-center gap-3 bg-libre-beige dark:bg-slate-800">
        <Coffee size={36} class="text-amber-600 dark:text-amber-400" />
        <h2 class="text-lg font-semibold text-libre-dark dark:text-slate-100">{$_('donationPopup.title')}</h2>
        <p class="text-sm text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">{$_('donationPopup.message')}</p>
        <p class="text-sm font-medium text-libre-green dark:text-green-400 leading-relaxed">{$_('donationPopup.donationNote')}</p>
    </div>

    <!-- Footer: exactly 2 buttons, no other way to close -->
    <div class="flex flex-col sm:flex-row gap-2 px-6 py-4 bg-libre-beige dark:bg-slate-800 border-t border-black/5 dark:border-white/10">
        <button type="button" class="order-2 sm:order-1 flex-1 px-4 py-2.5 text-sm font-medium rounded-lg bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-gray-200 hover:bg-gray-300 dark:hover:bg-slate-500 transition-colors" onclick={handleLater} data-testid="donation-popup-later">
            {$_('donationPopup.laterButton')}
        </button>
        <a
            href={BUY_ME_A_COFFEE_URL}
            target="_blank"
            rel="noopener noreferrer"
            class="order-1 sm:order-2 flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm font-medium rounded-lg bg-amber-500 text-white hover:bg-amber-600 transition-colors"
            onclick={handleDonateClick}
            data-testid="donation-popup-donate"
        >
            <Coffee size={16} />
            {$_('help.buyMeACoffee')}
        </a>
    </div>
</ModalBase>
