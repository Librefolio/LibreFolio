<script lang="ts">
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';

    interface Props {
        open?: boolean;
        trapFocus?: boolean;
        restoreFocus?: boolean;
        onRequestClose?: () => void;
    }

    let {open = true, trapFocus = false, restoreFocus = false, onRequestClose = () => {}}: Props = $props();
</script>

<ModalBase {open} {trapFocus} {restoreFocus} {onRequestClose} testId="review-support-modal-base" noTransition={true}>
    <div data-testid="review-support-modal-body">
        <button type="button" data-testid="review-support-hidden" style="visibility: hidden;">Hidden</button>
        <button type="button" data-testid="review-support-disabled" disabled>Disabled</button>
        <button type="button" data-testid="review-support-first">First</button>
        <input data-testid="review-support-middle" type="text" value="middle" />
        <button type="button" data-testid="review-support-last">Last</button>
    </div>
</ModalBase>
