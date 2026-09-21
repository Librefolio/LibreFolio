<script lang="ts">
    import {onMount} from 'svelte';
    import DonationPopupModal from '$lib/components/auth/DonationPopupModal.svelte';
    import UpdateAvailableModal from '$lib/components/auth/UpdateAvailableModal.svelte';
    import {updateAvailable} from '$lib/features/update-check/updateCheckStore.svelte';
    import {donationPopup} from '$lib/stores/app/donationPopupStore.svelte';

    interface Props {
        guideActive?: boolean;
        currentVersion: string;
    }

    let {guideActive = false, currentVersion}: Props = $props();

    let modalDepth = $state(0);
    let activePopup = $state<'donation' | 'update' | null>(null);

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
        if (guideActive) {
            activePopup = null;
            return;
        }
        if (activePopup === 'donation' && donationPopup.shouldShow) return;
        if (activePopup === 'update' && updateAvailable.release !== null) return;

        activePopup = null;
        if (modalDepth > 0) return;
        if (donationPopup.shouldShow) {
            activePopup = 'donation';
        } else if (updateAvailable.release !== null) {
            activePopup = 'update';
        }
    });
</script>

<div class="contents" data-testid="deferred-app-popups" data-active-popup={activePopup ?? 'none'} data-modal-depth={modalDepth}>
    {#if activePopup === 'donation'}
        <DonationPopupModal />
    {:else if activePopup === 'update'}
        <UpdateAvailableModal {currentVersion} />
    {/if}
</div>
