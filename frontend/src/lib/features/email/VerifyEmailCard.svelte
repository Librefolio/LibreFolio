<!--
  VerifyEmailCard — what the page of a verification link shows (workstream E, lot E5): the wait for the server, why the
  link cannot be used, or a check that failed, and the way back to the sign-in. A dead verification link is never the
  end: signing in offers a new one, so this card, unlike the invitation's, never sends anyone to an administrator.
-->
<script lang="ts">
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import AuthCard from '$lib/features/auth/AuthCard.svelte';
    import {VERIFY_PAGE_KEYS, type VerifyPageStatus} from './emailText';

    interface Props {
        status: VerifyPageStatus;
        onretry?: () => void;
    }

    let {status, onretry}: Props = $props();
</script>

<AuthCard data-status={status} testId="verify-email-status">
    <div class="space-y-5 text-center">
        <p aria-live="polite" class="text-sm text-lf-primary" data-testid="verify-email-message">{$_(VERIFY_PAGE_KEYS[status])}</p>
        {#if status === 'error' && onretry}
            <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98]" data-testid="verify-email-retry" onclick={onretry} type="button">
                {$_('common.retry')}
            </button>
        {/if}
        {#if status !== 'checking'}
            <button class="text-xs font-semibold text-lf-link hover:text-lf-primary underline decoration-1 underline-offset-2" data-testid="verify-email-goto-login" onclick={() => goto('/')} type="button">
                {$_('auth.backToLogin')}
            </button>
        {/if}
    </div>
</AuthCard>
