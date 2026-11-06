<script lang="ts">
    /**
     * PageBackButton — the ← of a main page (Brokers, Transactions, Assets, FX).
     *
     * Looks and sits like the ← of the detail pages, but is drawn only while there is a page to return to: the user
     * arrived from an in-app link («see all», a card, a row). Entered from the sidebar or by typing the address,
     * the stack holds this page alone, and a ← would lead nowhere. `canGoBack` (navigationStore) says which it is;
     * the page does not keep any logic of its own.
     */
    import {ArrowLeft} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {canGoBack, goBack} from '$lib/stores/app/navigationStore';

    interface Props {
        /** Where ← goes if the stack turns out empty by the time it is pressed (a race, never the normal case). */
        fallback: string;
        /** The test id of the button: one per page, so a spec names the page it asks about. */
        testId: string;
    }

    let {fallback, testId}: Props = $props();
</script>

{#if $canGoBack}
    <button class="p-2 rounded-lg hover:bg-lf-hover text-lf-muted transition-colors" data-testid={testId} onclick={() => goBack(fallback)} title={$_('common.back')} aria-label={$_('common.back')}>
        <ArrowLeft size={20} />
    </button>
{/if}
