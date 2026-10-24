<!--
  EmailChangeCard — what the page of an owner's email-change link shows (lot A5-1b): the click that confirms the new
  address, the wait for the server, why the link cannot be used, or a check that failed, and the way back to the
  sign-in. It is `VerifyEmailCard` for another link: the address changes only after the click, never by opening the page.
-->
<script lang="ts">
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import AuthCard from '$lib/features/auth/AuthCard.svelte';
    import type {VerifyPageStatus} from './emailText';

    interface Props {
        status: VerifyPageStatus;
        /** Spends the link: only the owner's click does, never the opening of the page. */
        onconfirm?: () => void;
        onretry?: () => void;
    }

    let {status, onconfirm, onretry}: Props = $props();

    /** Whole keys, so the i18n audit sees each one. */
    const KEYS: Record<VerifyPageStatus, string> = {
        ready: 'email.emailChange.page.ready',
        checking: 'email.emailChange.page.checking',
        expired: 'email.emailChange.page.expired',
        consumed: 'email.emailChange.page.consumed',
        revoked: 'email.emailChange.page.revoked',
        unknown: 'email.emailChange.page.unknown',
        blocked: 'email.emailChange.page.blocked',
        missing: 'email.emailChange.page.missing',
        error: 'email.emailChange.page.error',
    };
</script>

<AuthCard data-status={status} testId="email-change-status">
    <div class="space-y-5 text-center">
        <p aria-live="polite" class="text-sm text-lf-primary" data-testid="email-change-message">{$_(KEYS[status])}</p>
        {#if status === 'ready' && onconfirm}
            <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98]" data-testid="email-change-confirm" onclick={onconfirm} type="button">
                {$_('email.emailChange.page.confirm')}
            </button>
        {/if}
        {#if status === 'ready'}
            <p class="text-xs text-lf-secondary" data-testid="email-change-hint">{$_('email.emailChange.page.notExpected')}</p>
        {/if}
        {#if status === 'error' && onretry}
            <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98]" data-testid="email-change-retry" onclick={onretry} type="button">
                {$_('common.retry')}
            </button>
        {/if}
        {#if status !== 'checking' && status !== 'ready'}
            <button class="text-xs font-semibold text-lf-link hover:text-lf-primary underline decoration-1 underline-offset-2" data-testid="email-change-goto-login" onclick={() => goto('/')} type="button">
                {$_('auth.backToLogin')}
            </button>
        {/if}
    </div>
</AuthCard>
