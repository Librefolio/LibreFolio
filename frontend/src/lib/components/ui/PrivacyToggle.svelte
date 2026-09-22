<script lang="ts">
    /**
     * PrivacyToggle — hide or show every monetary amount in the app.
     *
     * Sits in the header rather than in Settings because the need is contextual:
     * someone walks up to the screen. A control reachable only after navigating
     * would arrive after the moment it exists for.
     */
    import {Eye, EyeOff} from 'lucide-svelte';
    import {isPrivacyEnabled, togglePrivacy} from '$lib/stores/app/privacyStore.svelte';

    const hidden = $derived(isPrivacyEnabled());
    const label = $derived(hidden ? 'Show amounts' : 'Hide amounts');
</script>

<button
    aria-label={label}
    aria-pressed={hidden}
    class="p-2 rounded-lg transition-colors duration-200
           text-gray-600 dark:text-gray-300 hover:bg-white/20 dark:hover:bg-slate-600"
    data-testid="privacy-toggle"
    onclick={togglePrivacy}
    title={label}
    type="button"
>
    {#if hidden}
        <EyeOff size={20} />
    {:else}
        <Eye size={20} />
    {/if}
</button>
