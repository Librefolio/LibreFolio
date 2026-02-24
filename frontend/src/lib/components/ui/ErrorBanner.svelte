<!--
  ErrorBanner - Reusable error message banner

  Displays a red-themed banner with optional icon and dismiss button.
  Used across modals, forms, and pages for consistent error display.
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {AlertCircle, X} from 'lucide-svelte';

    /** Error message to display (empty/null hides the banner) */
    export let message: string | null = '';
    /** Whether to show the AlertCircle icon */
    export let showIcon: boolean = true;
    /** Whether to show dismiss (X) button */
    export let dismissible: boolean = true;
    /** Additional CSS class */
    export let className: string = '';

    const dispatch = createEventDispatcher<{ dismiss: void }>();

    function handleDismiss() {
        dispatch('dismiss');
    }
</script>

{#if message}
    <div class="error-banner {className}" role="alert">
        {#if showIcon}
            <AlertCircle size={16} class="error-icon" />
        {/if}
        <span class="error-text">{message}</span>
        {#if dismissible}
            <button type="button" class="dismiss-btn" on:click={handleDismiss} aria-label="Dismiss">
                <X size={14} />
            </button>
        {/if}
    </div>
{/if}

<style>
    .error-banner {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem;
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 0.5rem;
        color: #b91c1c;
        font-size: 0.875rem;
    }

    :global(.dark) .error-banner {
        background: rgba(185, 28, 28, 0.15);
        border-color: #991b1b;
        color: #fca5a5;
    }

    :global(.error-icon) {
        flex-shrink: 0;
    }

    .error-text {
        flex: 1;
    }

    .dismiss-btn {
        flex-shrink: 0;
        padding: 0.125rem;
        border: none;
        background: transparent;
        color: inherit;
        cursor: pointer;
        opacity: 0.6;
        border-radius: 0.25rem;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: opacity 0.15s;
    }

    .dismiss-btn:hover {
        opacity: 1;
    }
</style>

