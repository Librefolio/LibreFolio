<script lang="ts">
    /**
     * ServerUnreachable — what a full load of an app page shows when the server has not said who is
     * signed in: slow (past the layout's wait), down, or answering 5xx. It is not a sign-out: the URL
     * stays the one asked for, and Retry runs the check again. Only a 401 leads to the login.
     */
    import {_} from '$lib/i18n';
    import {ServerCrash} from 'lucide-svelte';

    interface Props {
        /** A check is in flight: Retry would only overtake it. */
        busy: boolean;
        onretry: () => void;
    }

    let {busy, onretry}: Props = $props();
</script>

<div class="min-h-screen flex items-center justify-center bg-lf-page text-lf-primary p-4" role="alert" data-testid="server-unreachable" data-busy={busy ? 'true' : 'false'}>
    <div class="max-w-md text-center space-y-4">
        <ServerCrash size={40} class="mx-auto text-lf-link" aria-hidden="true" />
        <h1 class="text-xl font-semibold text-lf-primary">{$_('auth.serverUnreachable.title')}</h1>
        <p class="text-sm text-lf-secondary">{$_('auth.serverUnreachable.body')}</p>
        <button type="button" class="px-4 py-2 text-sm font-medium text-lf-on-action bg-lf-action rounded-lg hover:bg-lf-action-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed" disabled={busy} onclick={onretry} data-testid="server-unreachable-retry">
            {$_('common.retry')}
        </button>
    </div>
</div>
