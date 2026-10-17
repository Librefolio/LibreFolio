<!--
  SendLinkByEmail — «Send by email» next to a shared link (workstream E, lot E4): one of the extra actions of the share
  dialogs (`settings/users/linkShareActions.ts`, workstream A). An invitation goes to the address typed here, else to the
  one written in it; a password-reset link only to the address of its account. An invitation's email goes in the
  language chosen here, the instance's default language unless another is picked; a reset link's in the account's
  (decision N69). The outcome says which language the email went in, as the server answered it.

  Only the token travels: the email's link starts with `LIBREFOLIO_PUBLIC_URL` (developer decision 45), whatever address
  the dialog shows. Colours are roles only.
-->
<script lang="ts">
    import {Mail} from 'lucide-svelte';
    import {_, LANGUAGE_OPTIONS, LOCALE_NAMES, type SupportedLocale} from '$lib/i18n';
    import {SimpleSelect, type SelectOption} from '$lib/components/ui/select';
    import {notify} from '$lib/stores/app/notify.svelte';
    import type {LinkShareActionProps} from '$lib/features/settings/users/linkShareActions';
    import {linkSendFailureMessage, OUTCOME_CLASSES} from './emailText';
    import {readLinkSendFailure, sendLinkByEmail, tokenFromLink, type LinkSendFailure} from './sendLinkApi';

    let {link, purpose, context}: LinkShareActionProps = $props();

    const uid = $props.id();
    const token = $derived(tokenFromLink(link));
    /** The address typed by the administrator; until then, the one the dialog knows. */
    let edited = $state<string | null>(null);
    const to = $derived(edited ?? context.email ?? '');
    /** The language of an invitation's email; '' leaves it to the instance's default language (decision N69). */
    let language = $state<SupportedLocale | ''>('');
    const languageOptions: SelectOption[] = $derived([{value: '', label: $_('email.sendLink.languageInstance')}, ...LANGUAGE_OPTIONS.map((option) => ({value: option.code, label: option.name, icon: option.flag}))]);
    let sending = $state(false);
    /** The last request's outcome; its text is rendered from it, so it follows a change of language. */
    let outcome = $state<{kind: 'sent'; to: string; language: string} | {kind: 'failed'; failure: LinkSendFailure} | null>(null);

    function chosenLanguage(value: string): SupportedLocale | '' {
        return LANGUAGE_OPTIONS.find((option) => option.code === value)?.code ?? '';
    }

    /** A language as the selector names it, in its own language; a code the interface does not know, as it is. */
    function languageName(code: string): string {
        return LANGUAGE_OPTIONS.find((option) => option.code === code) ? LOCALE_NAMES[code as SupportedLocale] : code;
    }

    async function send(): Promise<void> {
        if (sending || token === null) return;
        sending = true;
        outcome = null;
        const address = purpose === 'invite' ? to.trim() : '';
        const chosen = purpose === 'invite' && language ? language : undefined;
        try {
            // No language key at all for the instance's language: the backend decides, as before N69
            const sent = await sendLinkByEmail({purpose, token, to: address || undefined, ...(chosen ? {language: chosen} : {})});
            outcome = {kind: 'sent', to: sent.to, language: sent.language};
            notify({name: 'email.link.sent', detail: {purpose, language: sent.language}});
        } catch (error) {
            const failure = readLinkSendFailure(error);
            outcome = {kind: 'failed', failure};
            notify({name: 'email.link.sendFailed', detail: {purpose, ...failure}});
        } finally {
            sending = false;
        }
    }
</script>

<div class="w-full space-y-2 rounded-lg border border-lf-subtle bg-lf-panel p-3 text-lf-primary" data-testid="send-link-email" data-purpose={purpose} data-busy={sending ? 'true' : 'false'} aria-busy={sending}>
    {#if purpose === 'invite'}
        <label class="block text-sm font-medium text-lf-secondary" for="{uid}-to">{$_('email.sendLink.toLabel')}</label>
        <input
            autocomplete="off"
            class="w-full rounded-md border border-lf-input bg-lf-field px-3 py-2 text-sm text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:ring-2 focus:ring-lf-focus"
            data-testid="send-link-email-to"
            disabled={sending}
            id="{uid}-to"
            oninput={(event) => (edited = event.currentTarget.value)}
            placeholder={$_('email.sendLink.toPlaceholder')}
            type="email"
            value={to}
        />
        <p class="block text-sm font-medium text-lf-secondary">{$_('email.sendLink.languageLabel')}</p>
        <SimpleSelect
            ariaLabel={$_('email.sendLink.languageLabel')}
            disabled={sending}
            dropdownPosition="auto"
            onchange={(value) => (language = chosenLanguage(value))}
            optionTestId={(option) => `send-link-email-language-option-${option.value || 'instance'}`}
            options={languageOptions}
            testId="send-link-email-language"
            value={language}
        />
    {:else}
        <p class="text-sm text-lf-secondary" data-testid="send-link-email-target">{$_('email.sendLink.resetTarget')}</p>
    {/if}
    <p class="text-xs text-lf-muted">{$_('email.sendLink.publicUrlHint')}</p>
    <button
        class="inline-flex items-center gap-1.5 rounded-md bg-lf-action px-3 py-2 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50"
        data-testid="send-link-email-button"
        disabled={sending || token === null}
        onclick={send}
        type="button"
    >
        <Mail class="h-4 w-4" aria-hidden="true" />
        {sending ? $_('email.sendLink.sending') : $_('email.sendLink.button')}
    </button>
    {#if outcome}
        <p aria-live="polite" class={OUTCOME_CLASSES[outcome.kind]} data-language={outcome.kind === 'sent' ? outcome.language : undefined} data-outcome={outcome.kind} data-testid="send-link-email-outcome">
            {outcome.kind === 'sent' ? $_('email.sendLink.sent', {values: {to: outcome.to, language: languageName(outcome.language)}}) : linkSendFailureMessage($_, outcome.failure)}
        </p>
    {/if}
</div>
