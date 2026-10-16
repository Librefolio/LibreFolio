<!--
  VerificationNotice — the sign-in of an account that waits for its verification link (workstream E, lot E5; developer
  decision 44): «verify your email», and «send the link again» with the credentials just typed in the sign-in form.

  The sign-in hosts it when the login answers 403 `EMAIL_NOT_VERIFIED`. Colours are roles only.
-->
<script lang="ts">
    import {MailCheck} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {OUTCOME_CLASSES, resendFailureMessage} from './emailText';
    import {readResendFailure, resendEmailVerification, type ResendFailure} from './verificationApi';

    interface Props {
        /** The username or email address typed in the sign-in form. */
        username: string;
        /** The password typed in the sign-in form. */
        password: string;
    }

    let {username, password}: Props = $props();

    let sending = $state(false);
    /** The last request's outcome; its text is rendered from it, so it follows a change of language. */
    let outcome = $state<{kind: 'sent'} | {kind: 'failed'; failure: ResendFailure} | null>(null);

    async function resend(): Promise<void> {
        if (sending || !username || !password) return;
        sending = true;
        outcome = null;
        try {
            const language = await resendEmailVerification(username, password);
            outcome = {kind: 'sent'};
            notify({name: 'email.verification.resent', detail: {language}});
        } catch (error) {
            const failure = readResendFailure(error);
            outcome = {kind: 'failed', failure};
            notify({name: 'email.verification.resendFailed', detail: {...failure}});
        } finally {
            sending = false;
        }
    }
</script>

<div class="space-y-3 text-lf-primary" data-testid="email-verification-notice" data-busy={sending ? 'true' : 'false'} aria-busy={sending}>
    <div class="space-y-3 rounded-lg border border-lf-info-line bg-lf-info-soft px-4 py-3 text-sm text-lf-info-on-soft" role="alert">
        <p class="flex items-start gap-2">
            <MailCheck class="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{$_('email.verification.loginRequired')}</span>
        </p>
        <button
            class="inline-flex items-center gap-1.5 rounded-md border border-lf-input bg-lf-card px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="email-verification-resend"
            disabled={sending || !username || !password}
            onclick={resend}
            type="button"
        >
            {sending ? $_('email.verification.resending') : $_('email.verification.resend')}
        </button>
    </div>
    {#if outcome}
        <p aria-live="polite" class={OUTCOME_CLASSES[outcome.kind]} data-testid="email-verification-outcome" data-outcome={outcome.kind}>
            {outcome.kind === 'sent' ? $_('email.verification.resent') : resendFailureMessage($_, outcome.failure)}
        </p>
    {/if}
</div>
