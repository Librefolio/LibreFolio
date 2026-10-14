<script lang="ts">
    import '../app.css';
    import {onMount} from 'svelte';
    import {DEFAULT_LOCALE, i18nLoading, initI18n, locale} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';

    // Initialize i18n
    initI18n();

    // Only the first dictionary gates the app. svelte-i18n also raises `isLoading` for a
    // later language switch whose dictionary takes more than 200 ms; tearing the app down
    // for it rebuilt every page from scratch, and Welcome lost the language being chosen.
    let i18nBooted = false;
    $: if (!$i18nLoading) i18nBooted = true;

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

    // Keep <html lang> on the language actually being shown. app.html hardcodes
    // "en" and nothing ever updated it, so screen readers, browser translation
    // and search engines were told the wrong language for every non-English user.
    //
    // `data-i18n-ready` is the companion signal: it is "false" while any dictionary
    // is loading. svelte-i18n moves `locale` to a new language only once its
    // dictionary has loaded, or at once when a load of it is already in flight,
    // so "the strings on screen are in that language" is `lang` plus
    // `data-i18n-ready="true"` — which is what tests wait for, never a fixed delay.
    $: if (typeof document !== 'undefined') {
        document.documentElement.lang = $locale ?? DEFAULT_LOCALE;
        document.documentElement.dataset.i18nReady = String(!$i18nLoading);
    }
</script>

{#if !i18nBooted}
    <!-- Splash screen is visible in app.html; keep a minimal placeholder here -->
    <div></div>
{:else}
    <div class="min-h-screen">
        <slot />
    </div>
{/if}
