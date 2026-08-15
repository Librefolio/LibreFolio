<script lang="ts">
    import '../app.css';
    import {onMount} from 'svelte';
    import {DEFAULT_LOCALE, i18nLoading, initI18n, locale} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';

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

    // Keep <html lang> on the language actually being shown. app.html hardcodes
    // "en" and nothing ever updated it, so screen readers, browser translation
    // and search engines were told the wrong language for every non-English user.
    //
    // `data-i18n-ready` is the companion signal: `locale` flips the moment the
    // user picks a language, but the dictionary lands later, so "the strings on
    // screen are in that language" was previously unobservable — which is exactly
    // why tests waited a fixed 300ms for it instead of asking.
    $: if (typeof document !== 'undefined') {
        document.documentElement.lang = $locale ?? DEFAULT_LOCALE;
        document.documentElement.dataset.i18nReady = String(!$i18nLoading);
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
