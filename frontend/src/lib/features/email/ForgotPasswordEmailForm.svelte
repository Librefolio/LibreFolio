<!--
  ForgotPasswordEmailForm — «forgot password» by email (workstream E, lot E4): a username or an email address, and a
  reset link goes to the account's address if an active account matches. The answer is the same for everyone, so the
  form never tells which accounts exist.

  Meant for the sign-in's «Forgot password?» card, which hosts it from lot E4b when emails with a link can go out
  (`GET /system/instance` → `email.links`). Colours are roles only.

  After an accepted request the submit waits `FORGOT_RESEND_WAIT_S` (the server's minimum interval between two reset
  emails) with a visible countdown, the same for every identifier, kept across a reload (`forgotCooldown.ts`; lot UA1).
-->
<script lang="ts">
    import {Send} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {notify} from '$lib/stores/app/notify.svelte';
    import {forgotFailureMessage, NOTICE_CLASSES, OUTCOME_CLASSES} from './emailText';
    import {readForgotFailure, requestPasswordResetEmail, type ForgotFailure} from './forgotPasswordApi';
    import {formatWait, readForgotCooldown, secondsLeft, startForgotCooldown} from './forgotCooldown';

    const uid = $props.id();
    let identifier = $state('');
    let sending = $state(false);
    /** The last request's outcome; its text is rendered from it, so it follows a change of language. */
    let outcome = $state<{kind: 'accepted'} | {kind: 'failed'; failure: ForgotFailure} | null>(null);
    /** When the next request may go (epoch ms), or `null`: read back from `sessionStorage`, so a reload keeps it. */
    let nextRequestAt = $state<number | null>(readForgotCooldown());
    let now = $state(Date.now());
    const waitS = $derived(nextRequestAt === null ? 0 : secondsLeft(nextRequestAt, now));
    const waiting = $derived(waitS > 0);

    // One tick a second while a wait runs; the interval stops with it, or with the form.
    $effect(() => {
        if (nextRequestAt === null) return;
        now = Date.now();
        const timer = setInterval(() => {
            now = Date.now();
            if (nextRequestAt !== null && now >= nextRequestAt) nextRequestAt = null;
        }, 1000);
        return () => clearInterval(timer);
    });

    async function submit(event: SubmitEvent): Promise<void> {
        event.preventDefault();
        const value = identifier.trim();
        if (sending || waiting || !value) return;
        sending = true;
        outcome = null;
        try {
            await requestPasswordResetEmail(value);
            outcome = {kind: 'accepted'};
            nextRequestAt = startForgotCooldown();
            now = Date.now();
            notify({name: 'email.forgot.accepted'});
        } catch (error) {
            const failure = readForgotFailure(error);
            outcome = {kind: 'failed', failure};
            notify({name: 'email.forgot.refused', detail: {...failure}});
        } finally {
            sending = false;
        }
    }
</script>

<form class="space-y-3 text-lf-primary" data-testid="forgot-email-form" data-busy={sending ? 'true' : 'false'} aria-busy={sending} onsubmit={submit}>
    <label class="block text-sm font-medium text-lf-secondary" for="{uid}-identifier">{$_('email.forgot.label')}</label>
    <input
        autocomplete="username"
        bind:value={identifier}
        class="w-full rounded-lg border border-lf-input bg-lf-field px-3 py-2.5 text-sm text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:ring-2 focus:ring-lf-focus"
        data-testid="forgot-email-identifier"
        disabled={sending}
        id="{uid}-identifier"
        maxlength="254"
        type="text"
    />
    <button
        class="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-lf-action py-3 font-bold text-lf-on-action shadow-md hover:bg-lf-action-hover disabled:cursor-not-allowed disabled:opacity-50"
        data-testid="forgot-email-submit"
        disabled={sending || waiting || !identifier.trim()}
        type="submit"
    >
        <Send class="h-4 w-4" aria-hidden="true" />
        {#if sending}
            {$_('email.forgot.sending')}
        {:else if waiting}
            <!-- Not a live region: a value that changes every second would flood a screen reader. -->
            <span data-testid="forgot-email-countdown" data-seconds={waitS}>{$_('email.forgot.wait', {values: {time: formatWait(waitS)}})}</span>
        {:else}
            {$_('email.forgot.submit')}
        {/if}
    </button>
    {#if outcome}
        <p aria-live="polite" class={outcome.kind === 'accepted' ? NOTICE_CLASSES.info : OUTCOME_CLASSES.failed} data-testid="forgot-email-outcome" data-outcome={outcome.kind}>
            {outcome.kind === 'accepted' ? $_('email.forgot.accepted') : forgotFailureMessage($_, outcome.failure)}
        </p>
    {/if}
</form>
