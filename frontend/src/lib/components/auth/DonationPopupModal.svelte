<!--
  DonationPopupModal — "support LibreFolio" popup shown after login.

  Triggered by the backend's AuthLoginResponse.show_donation_popup signal (see
  $lib/stores/app/auth.ts) or, for manual testing, via the debug console command
  registered in routes/(app)/+layout.svelte (window.librefolioDebug.showDonationPopup()).

  Interaction rules (intentional, not a bug):
  - No close ("X") button.
  - Clicking the backdrop does nothing (closeOnBackdropClick={false}).
  - Pressing Escape does nothing (closeOnEscape={false}).
  - The ONLY ways to dismiss it are the coffee action and the "Maybe later" button.
  - Sharing buttons open the social tab / manual dialog and never dismiss the popup.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {Coffee} from 'lucide-svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {donationPopup} from '$lib/stores/app/donationPopupStore.svelte';
    import SupportActions from '$lib/components/support/SupportActions.svelte';
    import SocialShareModal from '$lib/components/support/SocialShareModal.svelte';
    import type {SocialPlatform} from '$lib/components/support/supportLinks';

    let sharePlatform = $state<SocialPlatform | null>(null);

    $effect(() => {
        if (!donationPopup.shouldShow) sharePlatform = null;
    });

    function handleLater() {
        sharePlatform = null;
        donationPopup.dismiss();
    }

    function handleDonateClick() {
        sharePlatform = null;
        // The <a> handles the navigation (target="_blank"); we just also close the popup.
        donationPopup.dismiss();
    }

    function openSocialShare(platform: SocialPlatform) {
        sharePlatform = platform;
    }

    function closeSocialShare() {
        sharePlatform = null;
    }
</script>

<ModalBase open={donationPopup.shouldShow} closeOnBackdropClick={false} closeOnEscape={false} maxWidth="xl" testId="donation-popup-modal">
    <!-- Header: LibreFolio logo + name, same style as LoginCard.svelte -->
    <div class="bg-libre-green px-6 py-5 flex items-center justify-center gap-3 shrink-0">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center p-1 shrink-0" style="background:#fff">
            <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
        </div>
        <span class="text-xl font-bold tracking-wide text-white">LibreFolio</span>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto">
        <!-- Body -->
        <div class="px-6 py-6 flex flex-col items-center text-center gap-3 bg-libre-beige dark:bg-slate-800">
            <Coffee size={36} class="text-amber-600 dark:text-amber-400" />
            <h2 class="text-lg font-semibold text-libre-dark dark:text-slate-100">{$_('donationPopup.title')}</h2>
            <p class="text-sm text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">{$_('donationPopup.message')}</p>
            <p class="text-sm font-medium text-libre-green dark:text-green-400 leading-relaxed">{$_('donationPopup.donationNote')}</p>
        </div>

        <!-- Support actions: coffee + social share -->
        <div class="px-6 pb-4 bg-libre-beige dark:bg-slate-800" data-testid="donation-popup-support-card">
            <div class="rounded-xl border border-black/5 bg-white/70 p-4 shadow-sm dark:border-white/10 dark:bg-slate-900/20">
                <SupportActions onCoffeeClick={handleDonateClick} coffeeTestId="donation-popup-donate" onShare={openSocialShare} />
            </div>
        </div>
    </div>

    <!-- Footer: exactly 1 button; the coffee action above also closes the popup -->
    <div class="flex flex-col gap-2 border-t border-black/5 bg-libre-beige px-6 py-4 dark:border-white/10 dark:bg-slate-800 shrink-0">
        <button type="button" class="flex-1 rounded-lg bg-gray-200 px-4 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-300 dark:bg-slate-600 dark:text-gray-200 dark:hover:bg-slate-500" onclick={handleLater} data-testid="donation-popup-later">
            {$_('donationPopup.laterButton')}
        </button>
    </div>
</ModalBase>

<SocialShareModal open={donationPopup.shouldShow && sharePlatform !== null} platform={sharePlatform ?? 'x'} onClose={closeSocialShare} />
