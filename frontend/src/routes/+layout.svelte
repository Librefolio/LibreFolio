<script lang="ts">
    import '../app.css';
    import {onMount} from 'svelte';
    import {i18nLoading, initI18n} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/language';

    // Initialize i18n
    initI18n();

    function removeSplash() {
        const splash = document.getElementById('app-splash');
        if (splash) {
            splash.classList.add('fade-out');
            setTimeout(() => splash.remove(), 350);
        }
    }

    onMount(() => {
        // Sync language store with i18n after mount
        currentLanguage.init();
    });

    // Remove splash when i18n is ready (reactive)
    $: if (!$i18nLoading && typeof document !== 'undefined') {
        removeSplash();
    }
</script>

{#if $i18nLoading}
    <!-- Splash screen is visible in app.html; keep a minimal placeholder here -->
    <div></div>
{:else}
    <div class="min-h-screen">
        <slot />
    </div>
{/if}
