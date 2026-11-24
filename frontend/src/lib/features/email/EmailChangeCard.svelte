<!--
  EmailChangeCard — what the page of an email-change link shows (lot A5-1b; release 1.4, project 71): the click that
  confirms the new address, the wait for the server, why the link cannot be used, or a check that failed, and the way
  back to the sign-in. It is `VerifyEmailCard` for another link: the address changes only after the click, never by
  opening the page. A link asked from Profile confirms only with the session of its account (D10): `signin` says so, and
  its button is the one way to the sign-in — the «back to the sign-in» link is not shown beside it. Clicked with another
  account's session, `otheraccount` says the link belongs to another account and its button signs out and opens the
  sign-in the same way; neither ever names the account. With `ready` the page shows the address the click would confirm,
  on a line of its own (81 U46): the double check of whoever confirms. The texts carry their line breaks and their words that matter
  (`EmphasisText`, lot E4).
-->
<script lang="ts">
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import EmphasisText from '$lib/components/ui/display/EmphasisText.svelte';
    import AuthCard from '$lib/features/auth/AuthCard.svelte';
    import type {EmailChangePageStatus} from './emailChangeApi';

    interface Props {
        status: EmailChangePageStatus;
        /** The address the click would confirm, shown with `ready` as a double check (81 U46); none: no line. */
        newEmail?: string | null;
        /** Spends the link: only the owner's click does, never the opening of the page. */
        onconfirm?: () => void;
        onretry?: () => void;
        /** `signin` and `otheraccount`: end any session of this browser, then open the sign-in that comes back to this page. */
        onsignin?: () => void;
    }

    let {status, newEmail = null, onconfirm, onretry, onsignin}: Props = $props();

    /** Whole keys, so the i18n audit sees each one. */
    const KEYS: Record<EmailChangePageStatus, string> = {
        ready: 'email.emailChange.page.ready',
        checking: 'email.emailChange.page.checking',
        expired: 'email.emailChange.page.expired',
        consumed: 'email.emailChange.page.consumed',
        revoked: 'email.emailChange.page.revoked',
        unknown: 'email.emailChange.page.unknown',
        blocked: 'email.emailChange.page.blocked',
        missing: 'email.emailChange.page.missing',
        error: 'email.emailChange.page.error',
        signin: 'email.emailChange.page.signin',
        otheraccount: 'email.emailChange.page.otherAccount',
    };
</script>

<AuthCard data-status={status} testId="email-change-status">
    <div class="space-y-5 text-center">
        <p aria-live="polite" class="text-sm leading-relaxed text-lf-primary" data-testid="email-change-message"><EmphasisText text={$_(KEYS[status])} /></p>
        {#if status === 'ready' && newEmail}
            <!-- The address is the server's, shown as text on its own line (never inside the markup of a message) -->
            <p class="break-all rounded-lg bg-lf-panel px-3 py-2 font-mono text-sm font-semibold text-lf-primary" data-testid="email-change-address">{newEmail}</p>
        {/if}
        {#if status === 'ready' && onconfirm}
            <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98]" data-testid="email-change-confirm" onclick={onconfirm} type="button">
                {$_('email.emailChange.page.confirm')}
            </button>
        {/if}
        {#if status === 'ready'}
            <p class="text-xs text-lf-secondary" data-testid="email-change-hint"><EmphasisText text={$_('email.emailChange.page.notExpected')} /></p>
        {/if}
        {#if status === 'error' && onretry}
            <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98]" data-testid="email-change-retry" onclick={onretry} type="button">
                {$_('common.retry')}
            </button>
        {/if}
        {#if status === 'signin' && onsignin}
            <div data-testid="email-change-signin">
                <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98] focus-visible:outline-lf-focus" data-testid="email-change-signin-action" onclick={onsignin} type="button">
                    {$_('email.emailChange.page.signinAction')}
                </button>
            </div>
        {/if}
        {#if status === 'otheraccount' && onsignin}
            <div data-testid="email-change-other-account">
                <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98] focus-visible:outline-lf-focus" data-testid="email-change-switch-account" onclick={onsignin} type="button">
                    {$_('email.emailChange.page.otherAccountAction')}
                </button>
            </div>
        {/if}
        {#if status !== 'checking' && status !== 'ready' && status !== 'signin' && status !== 'otheraccount'}
            <button class="text-xs font-semibold text-lf-link hover:text-lf-primary underline decoration-1 underline-offset-2" data-testid="email-change-goto-login" onclick={() => goto('/')} type="button">
                {$_('auth.backToLogin')}
            </button>
        {/if}
    </div>
</AuthCard>
