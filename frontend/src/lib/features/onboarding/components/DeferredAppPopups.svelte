<script lang="ts">
    import {onMount} from 'svelte';
    import WhatsNewModal from '$lib/features/changelog/WhatsNewModal.svelte';
    import {whatsNew} from '$lib/features/changelog/whatsNewStore.svelte';
    import DonationPopupModal from '$lib/features/support/DonationPopupModal.svelte';
    import UpdateAvailableModal from '$lib/features/update-check/UpdateAvailableModal.svelte';
    import {updateAvailable} from '$lib/features/update-check/updateCheckStore.svelte';
    import {donationPopup} from '$lib/stores/app/donationPopupStore.svelte';

    interface Props {
        guideActive?: boolean;
        currentVersion: string;
    }

    let {guideActive = false, currentVersion}: Props = $props();

    let modalDepth = $state(0);
    let activePopup = $state<'whats-new' | 'donation' | 'update' | null>(null);

    function updateModalDepth() {
        modalDepth = Number(document.body.dataset.modalScrollLockCount || '0');
    }

    onMount(() => {
        updateModalDepth();
        const observer = new MutationObserver(updateModalDepth);
        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ['data-modal-scroll-lock-count'],
        });
        return () => observer.disconnect();
    });

    $effect(() => {
        // A manual check answers a question the user just asked, from inside another
        // modal: it is shown at once, above that modal. Everything below is for popups
        // nobody asked for, which wait until no modal and no guide is on screen.
        if (updateAvailable.release !== null && updateAvailable.requested) {
            activePopup = 'update';
            return;
        }
        if (guideActive) {
            activePopup = null;
            return;
        }
        if (activePopup === 'whats-new' && whatsNew.shouldShow) return;
        if (activePopup === 'donation' && donationPopup.shouldShow) return;
        if (activePopup === 'update' && updateAvailable.release !== null) return;

        activePopup = null;
        if (modalDepth > 0) return;
        // «What's new» first (C-54): it tells what changed in the version the user is now using.
        if (whatsNew.shouldShow) {
            activePopup = 'whats-new';
        } else if (donationPopup.shouldShow) {
            activePopup = 'donation';
        } else if (updateAvailable.release !== null) {
            activePopup = 'update';
        }
    });
</script>

<div class="contents" data-testid="deferred-app-popups" data-active-popup={activePopup ?? 'none'} data-modal-depth={modalDepth}>
    {#if activePopup === 'whats-new'}
        <WhatsNewModal />
    {:else if activePopup === 'donation'}
        <DonationPopupModal />
    {:else if activePopup === 'update'}
        <UpdateAvailableModal {currentVersion} />
    {/if}
</div>
