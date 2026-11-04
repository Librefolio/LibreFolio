<script lang="ts">
    /**
     * The compact legal notice (F09, lot A9): one line — the short disclaimer and the instance's legal pages, when it
     * links them — at the foot of the sign-in pages (`AuthPageFrame`) and of the sidebar, where `LegalNotice` would not
     * fit. `tone` follows the surface it sits on: the page, or the sidebar's bar.
     */
    import {_} from '$lib/i18n';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';

    interface Props {
        tone?: 'page' | 'bar';
    }

    let {tone = 'page'}: Props = $props();

    const legal = $derived(instanceConfig.config.legal);
    // The generated type widens `str | None` (the client generator); the response's validator lets only a string or null in.
    const termsUrl = $derived(typeof legal?.terms_url === 'string' ? legal.terms_url : null);
    const privacyUrl = $derived(typeof legal?.privacy_url === 'string' ? legal.privacy_url : null);
    // Whole literals, so Tailwind generates each class
    const textClass = $derived(tone === 'bar' ? 'text-lf-bar-muted' : 'text-lf-muted');
    const linkClass = $derived(tone === 'bar' ? 'text-lf-bar-text hover:text-lf-on-bar-active' : 'text-lf-secondary hover:text-lf-primary');
</script>

<p class="text-xs leading-relaxed {textClass}" data-testid="legal-links">
    <span>{$_('legal.disclaimerShort')}</span>
    {#if termsUrl}
        <span aria-hidden="true">·</span>
        <a href={termsUrl} target="_blank" rel="noopener noreferrer" class="underline-offset-2 hover:underline {linkClass}" data-testid="legal-terms-link">{$_('legal.terms')}</a>
    {/if}
    {#if privacyUrl}
        <span aria-hidden="true">·</span>
        <a href={privacyUrl} target="_blank" rel="noopener noreferrer" class="underline-offset-2 hover:underline {linkClass}" data-testid="legal-privacy-link">{$_('legal.privacy')}</a>
    {/if}
</p>
