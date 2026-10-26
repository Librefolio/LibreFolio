<script lang="ts">
    /**
     * What a link page shows instead of its form: the wait for the server, why the link cannot be used (expired, used,
     * withdrawn, unknown, incomplete, registration closed), or a check that failed — and the way back to the sign-in.
     */
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import AuthCard from './AuthCard.svelte';
    import type {LinkPageStatus} from './linkToken';

    interface Props {
        status: LinkPageStatus;
        onretry?: () => void;
        /** The line under a link that cannot be used: who issues a new one. The setup link (F02) has no administrator yet. */
        hintKey?: string;
        /** Where «contact support» goes, for a dead link whose remedy is the hosting provider (A5-6); none draws no link. */
        supportHref?: string | null;
    }

    let {status, onretry, hintKey = 'auth.link.askAdmin', supportHref = null}: Props = $props();

    const MESSAGE_KEYS: Record<LinkPageStatus, string> = {
        checking: 'common.loading',
        expired: 'auth.link.expired',
        consumed: 'auth.link.consumed',
        revoked: 'auth.link.revoked',
        unknown: 'auth.link.unknown',
        missing: 'auth.link.missing',
        closed: 'auth.registrationDisabled',
        error: 'auth.link.checkFailed',
    };

    /** The link itself is spent or broken: only an administrator can issue a new one. */
    const NEEDS_NEW_LINK = new Set<LinkPageStatus>(['expired', 'consumed', 'revoked', 'unknown', 'missing']);
</script>

<AuthCard data-status={status} testId="link-status">
    <div class="space-y-5 text-center">
        <p class="text-sm text-lf-primary" data-testid="link-status-message">{$_(MESSAGE_KEYS[status])}</p>
        {#if NEEDS_NEW_LINK.has(status)}
            <p class="text-xs text-lf-secondary" data-testid="link-status-hint">{$_(hintKey)}</p>
            {#if supportHref}
                <a class="inline-block text-xs font-semibold text-lf-link hover:text-lf-primary underline decoration-1 underline-offset-2" data-testid="link-status-support" href={supportHref} rel="noopener noreferrer" target={supportHref.startsWith('mailto:') ? undefined : '_blank'}>
                    {$_('auth.setup.supportLink')}
                </a>
            {/if}
        {/if}

        {#if status === 'error' && onretry}
            <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98]" data-testid="link-status-retry" onclick={onretry} type="button">
                {$_('common.retry')}
            </button>
        {/if}

        <button class="text-xs font-semibold text-lf-link hover:text-lf-primary underline decoration-1 underline-offset-2" data-testid="link-status-goto-login" onclick={() => goto('/')} type="button">
            {$_('auth.backToLogin')}
        </button>
    </div>
</AuthCard>
