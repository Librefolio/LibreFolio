<script lang="ts">
    /**
     * The legal notice of the instance (F09, lot A9): the disclaimer, and the links to the instance's own terms of
     * service and privacy policy when it sets them (`LIBREFOLIO_TOS_URL`, `LIBREFOLIO_PRIVACY_URL`, published by
     * `GET /system/instance` as `legal`). Its places: the About tab and the welcome page; the compact one is `LegalLinks`.
     */
    import {_} from '$lib/i18n';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';

    const legal = $derived(instanceConfig.config.legal);
    // The generated type widens `str | None` (the client generator); the response's validator lets only a string or null in.
    const termsUrl = $derived(typeof legal?.terms_url === 'string' ? legal.terms_url : null);
    const privacyUrl = $derived(typeof legal?.privacy_url === 'string' ? legal.privacy_url : null);
</script>

<div class="space-y-2 text-sm text-lf-secondary" data-testid="legal-notice">
    <p class="leading-relaxed">{$_('legal.disclaimer')}</p>
    {#if termsUrl || privacyUrl}
        <p class="flex flex-wrap gap-x-4 gap-y-1">
            {#if termsUrl}
                <a href={termsUrl} target="_blank" rel="noopener noreferrer" class="font-medium text-lf-link underline-offset-2 hover:underline" data-testid="legal-terms-link">{$_('legal.terms')}</a>
            {/if}
            {#if privacyUrl}
                <a href={privacyUrl} target="_blank" rel="noopener noreferrer" class="font-medium text-lf-link underline-offset-2 hover:underline" data-testid="legal-privacy-link">{$_('legal.privacy')}</a>
            {/if}
        </p>
    {/if}
</div>
